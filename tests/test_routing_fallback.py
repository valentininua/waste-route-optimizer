import pytest

from app.services import routing
from app.services.routing import OSRMProviderError, distance_duration_matrix, route_for_order


@pytest.mark.asyncio
async def test_large_public_osrm_matrix_uses_configured_estimate(monkeypatch):
    monkeypatch.setattr(routing.settings, "osrm_url", "https://router.project-osrm.org")
    monkeypatch.setattr(routing.settings, "max_public_osrm_table_points", 2)
    monkeypatch.setattr(routing.settings, "allow_approximate_matrix_for_large_routes", True)
    coords = [(56.65, 23.72), (56.66, 23.73), (56.67, 23.74)]
    distances, durations, source = await distance_duration_matrix(coords)
    assert source == "haversine_matrix_large_route"
    assert distances[0][1] > 0
    assert durations[0][1] > 0


@pytest.mark.asyncio
async def test_route_for_order_falls_back_when_osrm_route_fails(monkeypatch):
    monkeypatch.setattr(routing.settings, "allow_haversine_fallback", True)

    async def fail(*_args, **_kwargs):
        raise OSRMProviderError("OSRM unavailable")

    monkeypatch.setattr(routing, "_osrm_route_chunk", fail)
    coords = [(56.65, 23.72), (56.66, 23.73)]
    distance, duration, geometry, source = await route_for_order(coords, [0, 1], overview="full")
    assert distance > 0
    assert duration > 0
    assert geometry == [[23.72, 56.65], [23.73, 56.66]]
    assert source == "haversine_estimate"
