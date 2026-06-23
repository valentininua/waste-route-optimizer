from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import CollectionPoint, GeocodeCache, OptimizationRun, RouteJob
from app.resources import job_to_resource
from app.services.excel_parser import ParsedRoute, parse_excel_routes
from app.services.geocoding import geocode_address, geocode_cache_key
from app.services.optimizer import optimize_open_route
from app.services.routing import distance_duration_matrix, polyline_for_order, route_for_order

settings = get_settings()
logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _update_run(
    db: Session,
    run_id: int | None,
    *,
    status: str | None = None,
    stage: str | None = None,
    progress_percent: int | None = None,
    message: str | None = None,
    error: str | None = None,
    started: bool = False,
    finished: bool = False,
) -> None:
    if run_id is None:
        return
    run = db.get(OptimizationRun, run_id)
    if run is None:
        return
    if status is not None:
        run.status = status
    if stage is not None:
        run.stage = stage
    if progress_percent is not None:
        run.progress_percent = max(0, min(100, progress_percent))
    if message is not None:
        run.message = message
    if error is not None:
        run.error = error
    if started and run.started_at is None:
        run.started_at = _utcnow()
    if finished:
        run.finished_at = _utcnow()
    db.add(run)
    db.commit()


def _load_geocode_cache_for_points(
    db: Session, points: list[CollectionPoint]
) -> dict[str, tuple[float, float, str]]:
    """
    Load existing geocode cache entries for route points in one query.
    """
    cache_keys = {geocode_cache_key(point.address) for point in points if point.address}
    if not cache_keys:
        return {}

    cached_items = db.query(GeocodeCache).filter(GeocodeCache.query.in_(cache_keys)).all()
    return {
        item.query.lower(): (float(item.lat), float(item.lng), item.quality or "cache")
        for item in cached_items
    }


def _apply_points(db: Session, job: RouteJob, parsed_route: ParsedRoute) -> None:
    for item in parsed_route.points:
        point = CollectionPoint(
            job_id=job.id,
            original_order=item.original_order,
            address=item.address,
            bin_code=item.bin_code,
            service_day_code=item.service_day_code,
            service_days=", ".join(item.service_days),
            frequency_code=item.frequency_code,
            frequency_weeks=item.frequency_weeks,
            service_date=item.service_date,
            time_spent=item.time_spent,
            volume=item.volume,
            containers=item.containers,
            lat=item.lat,
            lng=item.lng,
            geocode_quality="provided" if item.lat is not None and item.lng is not None else None,
        )
        db.add(point)


def create_jobs_from_excel(db: Session, path: str | Path, filename: str) -> list[RouteJob]:
    parsed_routes = parse_excel_routes(path)
    jobs: list[RouteJob] = []

    for parsed_route in parsed_routes:
        if not parsed_route.points:
            continue
        total_volume = sum(p.volume for p in parsed_route.points)
        total_containers = sum(p.containers for p in parsed_route.points)
        job = RouteJob(
            filename=filename,
            route_code=parsed_route.route_code,
            route_date=parsed_route.route_date,
            source_row=parsed_route.source_row,
            status="parsed",
            total_volume=total_volume,
            total_containers=total_containers,
            declared_total_volume=parsed_route.declared_total_volume,
            declared_total_containers=parsed_route.declared_total_containers,
        )
        db.add(job)
        db.flush()
        _apply_points(db, job, parsed_route)
        jobs.append(job)

    db.commit()
    for job in jobs:
        db.refresh(job)
    return jobs


async def optimize_job(db: Session, job_id: int, run_id: int | None = None) -> dict:
    job = db.get(RouteJob, job_id)
    if not job:
        raise ValueError("Route job not found")

    try:
        _update_run(
            db,
            run_id,
            status="running",
            stage="preparing",
            progress_percent=5,
            message="Preparing selected route for optimization.",
            started=True,
        )
        job.status = "geocoding"
        job.error = None
        job.original_distance_m = None
        job.optimized_distance_m = None
        job.original_duration_s = None
        job.optimized_duration_s = None
        job.metrics_source = None
        db.commit()

        points = db.query(CollectionPoint).filter(CollectionPoint.job_id == job.id).order_by(CollectionPoint.original_order).all()
        if len(points) < 2:
            raise ValueError("At least two collection points are required")
        if len(points) > settings.max_points_to_optimize:
            raise ValueError(
                f"Route has {len(points)} points. Safety limit is {settings.max_points_to_optimize}. "
                "This prevents accidental optimization of the whole Excel file instead of one route."
            )

        _update_run(
            db,
            run_id,
            stage="geocoding",
            progress_percent=15,
            message="Geocoding unique addresses and reusing PostgreSQL cache.",
        )
        pending = [point for point in points if point.lat is None or point.lng is None]
        geocoded_by_address = _load_geocode_cache_for_points(db, pending)

        for index, point in enumerate(pending, start=1):
            normalized_address = geocode_cache_key(point.address).lower()
            if normalized_address not in geocoded_by_address:
                geocoded_by_address[normalized_address] = await geocode_address(db, point.address)

            lat, lng, quality = geocoded_by_address[normalized_address]
            point.lat = lat
            point.lng = lng
            point.geocode_quality = quality
            db.add(point)

            if pending and (index == len(pending) or index % 10 == 0):
                progress = 15 + int(index / len(pending) * 25)
                _update_run(
                    db,
                    run_id,
                    stage="geocoding",
                    progress_percent=progress,
                    message=f"Geocoded {index}/{len(pending)} addresses.",
                )
        db.commit()

        coords = [(float(p.lat), float(p.lng)) for p in points if p.lat is not None and p.lng is not None]
        if len(coords) != len(points):
            raise ValueError("Some points have no coordinates after geocoding")

        _update_run(
            db,
            run_id,
            stage="routing_matrix",
            progress_percent=45,
            message="Building distance/duration matrix.",
        )
        job.status = "routing"
        db.commit()
        distance_matrix, _duration_matrix, matrix_source = await distance_duration_matrix(coords)

        _update_run(
            db,
            run_id,
            stage="optimizing",
            progress_percent=65,
            message="Optimizing point order.",
        )
        job.status = "optimizing"
        db.commit()
        original_order = list(range(len(points)))
        optimized_order = optimize_open_route(distance_matrix, start=0)

        _update_run(
            db,
            run_id,
            stage="comparison",
            progress_percent=80,
            message="Calculating original and optimized road-based route totals.",
        )
        original_distance, original_duration, _original_geometry, original_source = await route_for_order(
            coords, original_order, overview="false"
        )
        optimized_distance, optimized_duration, _optimized_geometry, optimized_source = await route_for_order(
            coords, optimized_order, overview="false"
        )
        metrics_source = original_source if original_source == optimized_source else f"{original_source}/{optimized_source}"
        if matrix_source != "osrm_table":
            metrics_source = f"{metrics_source}; optimizer_matrix={matrix_source}"

        for position, point_index in enumerate(optimized_order, start=1):
            points[point_index].optimized_order = position
            db.add(points[point_index])

        job.original_distance_m = original_distance
        job.optimized_distance_m = optimized_distance
        job.original_duration_s = original_duration
        job.optimized_duration_s = optimized_duration
        job.metrics_source = metrics_source
        job.status = "optimized"
        job.error = None
        db.commit()
        db.refresh(job)

        _update_run(
            db,
            run_id,
            status="completed",
            stage="completed",
            progress_percent=100,
            message="Optimization completed.",
            finished=True,
        )
        return job_to_resource(job, include_points=True)
    except Exception as exc:
        failure_message = str(exc)
        logger.exception(
            "Route optimization failed before recovery status update",
            extra={"route_job_id": job_id, "optimization_run_id": run_id},
        )
        db.rollback()
        try:
            failed_job = db.get(RouteJob, job_id)
            if failed_job is not None:
                failed_job.status = "failed"
                failed_job.error = failure_message
                db.add(failed_job)
                db.commit()
        except Exception:
            logger.exception(
                "Failed to persist RouteJob failure status",
                extra={"route_job_id": job_id, "optimization_run_id": run_id},
            )
            db.rollback()
        try:
            _update_run(
                db,
                run_id,
                status="failed",
                stage="failed",
                progress_percent=100,
                message="Optimization failed.",
                error=failure_message,
                finished=True,
            )
        except Exception:
            logger.exception(
                "Failed to persist OptimizationRun failure status",
                extra={"route_job_id": job_id, "optimization_run_id": run_id},
            )
            db.rollback()
        raise


async def route_geometry(db: Session, job_id: int, kind: str) -> dict:
    points = db.query(CollectionPoint).filter(CollectionPoint.job_id == job_id).order_by(CollectionPoint.original_order).all()
    if not points:
        raise ValueError("Route job not found")
    coords = [(float(p.lat), float(p.lng)) for p in points if p.lat is not None and p.lng is not None]
    if len(coords) != len(points):
        raise ValueError("Route has points without coordinates")
    if kind == "optimized":
        if any(p.optimized_order is None for p in points):
            raise ValueError("Route is not optimized yet")
        ordered_points = sorted(points, key=lambda p: p.optimized_order or 10**9)
        id_to_index = {p.id: idx for idx, p in enumerate(points)}
        order = [id_to_index[p.id] for p in ordered_points]
    else:
        order = list(range(len(points)))
    distance_m, duration_s, geometry = await polyline_for_order(coords, order)
    return {"distance_m": distance_m, "duration_s": duration_s, "geometry": geometry}
