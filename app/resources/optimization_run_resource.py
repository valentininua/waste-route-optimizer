from __future__ import annotations

from app.models import OptimizationRun
from app.resources.route_job_resource import job_to_resource


def optimization_run_to_resource(run: OptimizationRun, include_route: bool = False) -> dict:
    payload = {
        "id": run.id,
        "route_job_id": run.route_job_id,
        "status": run.status,
        "stage": run.stage,
        "progress_percent": run.progress_percent,
        "message": run.message,
        "error": run.error,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "route": None,
    }
    if include_route and run.job is not None:
        payload["route"] = job_to_resource(run.job, include_points=run.status == "completed")
    return payload
