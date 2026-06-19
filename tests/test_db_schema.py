from sqlalchemy import Text

from app.db.init_db import POSTGRES_MIGRATIONS
from app.models import RouteJob
from app.resources import job_to_resource


def test_metrics_source_is_text_not_short_varchar():
    assert isinstance(RouteJob.__table__.c.metrics_source.type, Text)
    assert any("ALTER COLUMN metrics_source TYPE TEXT" in stmt for stmt in POSTGRES_MIGRATIONS)


def test_job_resource_preserves_long_metrics_source():
    job = RouteJob(
        id=1,
        filename="routes.xlsx",
        route_code="ML 1",
        route_date="2026-01-01",
        source_row=1,
        status="optimized",
        total_volume=1.0,
        total_containers=1,
        original_distance_m=192177.446,
        optimized_distance_m=93647.8,
        original_duration_s=23070.52,
        optimized_duration_s=13134.3,
        metrics_source="haversine_estimate/osrm_road; optimizer_matrix=haversine_matrix_large_route",
    )

    payload = job_to_resource(job)

    assert payload["metrics_source"] == "haversine_estimate/osrm_road; optimizer_matrix=haversine_matrix_large_route"
    assert payload["metrics"]["original_distance_km"] == 192.177
    assert payload["metrics"]["optimized_distance_km"] == 93.648
