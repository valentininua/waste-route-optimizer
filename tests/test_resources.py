from app.models import OptimizationRun, RouteJob
from app.resources import job_to_resource, optimization_run_to_resource


def test_job_resource_keeps_metrics_null_until_optimized():
    job = RouteJob(
        id=1,
        filename="routes.xlsx",
        route_code="ML 1",
        route_date="2026-01-01",
        source_row=1,
        status="parsed",
        total_volume=1.0,
        total_containers=1,
    )
    payload = job_to_resource(job)
    assert payload["metrics"] is None


def test_optimization_run_resource_can_embed_route_summary():
    job = RouteJob(
        id=1,
        filename="routes.xlsx",
        route_code="ML 1",
        route_date="2026-01-01",
        source_row=1,
        status="optimized",
        total_volume=1.0,
        total_containers=1,
        original_distance_m=1000,
        optimized_distance_m=700,
        original_duration_s=600,
        optimized_duration_s=420,
        metrics_source="osrm_road",
    )
    run = OptimizationRun(
        id=10,
        route_job_id=1,
        job=job,
        status="completed",
        stage="completed",
        progress_percent=100,
    )
    payload = optimization_run_to_resource(run, include_route=True)
    assert payload["route"]["metrics"]["saved_percent"] == 30
    assert payload["progress_percent"] == 100
