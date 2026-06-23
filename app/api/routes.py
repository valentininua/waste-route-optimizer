from __future__ import annotations

from pathlib import Path
from time import time
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.dto import OptimizationRunDto, RouteGeometryDto, RouteJobDto, StatsDto, UploadResponseDto
from app.models import CollectionPoint
from app.repositories import OptimizationRunRepository, RouteJobRepository
from app.resources import job_to_resource, optimization_run_to_resource
from app.services.route_processor import create_jobs_from_excel, route_geometry
from app.tasks.optimization_tasks import run_optimization_task

router = APIRouter()
UPLOAD_DIR = Path("/app/uploads")
CHUNK_SIZE = 1024 * 1024


def cleanup_stale_uploads() -> None:
    """Remove orphaned upload temp files left by a previous crash/restart."""
    settings = get_settings()
    if not UPLOAD_DIR.exists():
        return
    cutoff = time() - settings.upload_cleanup_age_seconds
    for path in UPLOAD_DIR.iterdir():
        if path.is_file() and path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)


async def _save_upload_with_size_limit(file: UploadFile, path: Path) -> int:
    settings = get_settings()
    max_size = settings.max_upload_size_bytes
    total = 0
    with path.open("wb") as handle:
        while chunk := await file.read(CHUNK_SIZE):
            total += len(chunk)
            if total > max_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"Uploaded file is too large. Max size is {max_size} bytes.",
                )
            handle.write(chunk)
    return total


@router.post(
    "/files/upload",
    response_model=UploadResponseDto,
    status_code=status.HTTP_201_CREATED,
    tags=["Files"],
    summary="Upload and parse an Excel route file",
    description=(
        "Uploads an Excel file, extracts individual route blocks, stores them in PostgreSQL, "
        "and returns route summaries for selection. By default, previous jobs for the same "
        "filename are deleted to keep repeated test uploads clean."
    ),
    responses={400: {"description": "Invalid Excel file or parsing error"}},
)
async def upload_file(
    file: UploadFile = File(description="Excel file with waste collection route data"),
    db: Session = Depends(get_db),
    replace_existing: bool = Query(default=True, description="Delete previous jobs from the same filename before import"),
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Upload an Excel file: .xlsx or .xls")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_stale_uploads()
    path = UPLOAD_DIR / f"{uuid4()}_{Path(file.filename).name}"

    try:
        await _save_upload_with_size_limit(file, path)
        route_jobs = RouteJobRepository(db)
        deleted_count = route_jobs.delete_by_filename(file.filename) if replace_existing else 0
        jobs = create_jobs_from_excel(db, path, file.filename)
        visible_jobs = jobs[: get_settings().max_routes_in_upload_response]
        suffix = f" Previous jobs removed: {deleted_count}." if replace_existing else " Duplicate imports are allowed."
        return {
            "filename": file.filename,
            "routes_count": len(jobs),
            "returned_routes_count": len(visible_jobs),
            "points_count": sum(len(job.points) for job in jobs),
            "replace_existing": replace_existing,
            "routes": [job_to_resource(job, include_points=False) for job in visible_jobs],
            "message": (
                "File parsed successfully. Select one route from the list and run optimization for that route only."
                + suffix
            ),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        path.unlink(missing_ok=True)


@router.get(
    "/routes",
    response_model=list[RouteJobDto],
    tags=["Routes"],
    summary="List route jobs",
    description="Returns latest route jobs, deduplicated by filename, route code, route date, and source row by default.",
)
def list_routes(
    db: Session = Depends(get_db),
    route_date: str | None = Query(default=None, description="Filter by YYYY-MM-DD"),
    route_code: str | None = Query(default=None, description="Filter by route code, e.g. ML 11840"),
    limit: int = Query(default=100, ge=1, le=500),
    include_duplicates: bool = Query(default=False, description="Show older duplicate imports too"),
):
    jobs = RouteJobRepository(db).list(
        route_date=route_date,
        route_code=route_code,
        limit=limit,
        include_duplicates=include_duplicates,
    )
    return [job_to_resource(job, include_points=False) for job in jobs]


@router.get(
    "/routes/{job_id}",
    response_model=RouteJobDto,
    tags=["Routes"],
    summary="Get route details",
    description="Returns a route job including all collection points.",
    responses={404: {"description": "Route job not found"}},
)
def get_route(job_id: int, db: Session = Depends(get_db)):
    job = RouteJobRepository(db).get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Route job not found")
    return job_to_resource(job, include_points=True)


@router.post(
    "/routes/{job_id}/optimization-runs",
    response_model=OptimizationRunDto,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Optimization Runs"],
    summary="Start background optimization",
    description=(
        "Creates an optimization run and executes route optimization in a FastAPI background task. "
        "Clients should poll GET /api/optimization-runs/{run_id}; WebSocket is intentionally not required."
    ),
    responses={404: {"description": "Route job not found"}},
)
def start_optimization_run(job_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    route_jobs = RouteJobRepository(db)
    optimization_runs = OptimizationRunRepository(db)

    try:
        job = route_jobs.get_for_update(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Route job not found")

        active_run = optimization_runs.latest_active_for_route(job_id)
        if active_run:
            return optimization_run_to_resource(active_run, include_route=True)

        run = optimization_runs.create_queued(job_id, commit=False)
        db.commit()
        db.refresh(run)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        # Final protection for concurrent requests: a partial unique index allows
        # only one queued/running optimization run per route. If another request
        # created it first, return that active run instead of failing.
        db.rollback()
        active_run = optimization_runs.latest_active_for_route(job_id)
        if active_run:
            return optimization_run_to_resource(active_run, include_route=True)
        raise HTTPException(status_code=409, detail="Optimization run already exists for this route")

    background_tasks.add_task(run_optimization_task, job_id, run.id)
    return optimization_run_to_resource(run, include_route=True)


@router.get(
    "/optimization-runs/{run_id}",
    response_model=OptimizationRunDto,
    tags=["Optimization Runs"],
    summary="Get optimization run status",
    description="Returns background optimization status, progress, and related route summary.",
    responses={404: {"description": "Optimization run not found"}},
)
def get_optimization_run(run_id: int, db: Session = Depends(get_db)):
    run = OptimizationRunRepository(db).get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Optimization run not found")
    return optimization_run_to_resource(run, include_route=True)


@router.get(
    "/routes/{job_id}/optimization-runs",
    response_model=list[OptimizationRunDto],
    tags=["Optimization Runs"],
    summary="List optimization runs for a route",
    responses={404: {"description": "Route job not found"}},
)
def list_optimization_runs(job_id: int, db: Session = Depends(get_db)):
    route_jobs = RouteJobRepository(db)
    job = route_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Route job not found")
    runs = OptimizationRunRepository(db).list_for_route(job_id)
    return [optimization_run_to_resource(run, include_route=False) for run in runs]


@router.get(
    "/routes/{job_id}/geometry/{kind}",
    response_model=RouteGeometryDto,
    tags=["Routes"],
    summary="Get route geometry",
    description="Returns road geometry for the original or optimized route. Coordinates are [lng, lat].",
    responses={400: {"description": "Invalid kind or route geometry error"}},
)
async def get_geometry(job_id: int, kind: str, db: Session = Depends(get_db)):
    if kind not in {"original", "optimized"}:
        raise HTTPException(status_code=400, detail="kind must be original or optimized")
    try:
        return await route_geometry(db, job_id, kind)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/stats",
    response_model=StatsDto,
    tags=["System"],
    summary="Get aggregate API statistics",
)
def stats(db: Session = Depends(get_db)):
    route_jobs = RouteJobRepository(db)
    optimization_runs = OptimizationRunRepository(db)
    return {
        "routes": route_jobs.count(),
        "unique_routes": route_jobs.unique_count(),
        "points": db.query(CollectionPoint).count(),
        "optimized_routes": route_jobs.optimized_count(),
        "failed_routes": route_jobs.failed_count(),
        "optimization_runs": optimization_runs.count(),
        "running_runs": optimization_runs.running_count(),
    }
