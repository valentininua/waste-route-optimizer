from __future__ import annotations

from app.models import RouteJob
from app.resources.collection_point_resource import point_to_resource
from app.resources.route_metrics_resource import metrics_to_resource


def job_to_resource(job: RouteJob, include_points: bool = False) -> dict:
    points_count = len(job.points) if job.points is not None else 0
    payload = {
        "id": job.id,
        "filename": job.filename,
        "route_code": job.route_code,
        "route_date": job.route_date,
        "source_row": job.source_row,
        "status": job.status,
        "points_count": points_count,
        "total_volume": job.total_volume,
        "total_containers": job.total_containers,
        "declared_total_volume": job.declared_total_volume,
        "declared_total_containers": job.declared_total_containers,
        "error": job.error,
        "metrics_source": job.metrics_source,
        "metrics": metrics_to_resource(job),
    }
    if include_points:
        payload["points"] = [point_to_resource(point) for point in job.points]
    return payload
