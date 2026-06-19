from __future__ import annotations

from app.models import RouteJob


def metrics_to_resource(job: RouteJob) -> dict | None:
    if job.status != "optimized":
        return None
    original_km = (job.original_distance_m or 0) / 1000
    optimized_km = (job.optimized_distance_m or 0) / 1000
    saved_km = original_km - optimized_km
    saved_percent = (saved_km / original_km * 100) if original_km > 0 else 0
    return {
        "original_distance_km": round(original_km, 3),
        "optimized_distance_km": round(optimized_km, 3),
        "saved_distance_km": round(saved_km, 3),
        "saved_percent": round(saved_percent, 2),
        "original_duration_min": round((job.original_duration_s or 0) / 60, 1),
        "optimized_duration_min": round((job.optimized_duration_s or 0) / 60, 1),
    }
