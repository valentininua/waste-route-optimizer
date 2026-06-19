from __future__ import annotations

import math

import httpx
from app.core.config import get_settings

settings = get_settings()
Coord = tuple[float, float]  # lat, lng


def haversine_m(a: Coord, b: Coord) -> float:
    r = 6371000
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _fallback_matrix(coords: list[Coord]) -> tuple[list[list[float]], list[list[float]]]:
    distances = [[0.0] * len(coords) for _ in coords]
    durations = [[0.0] * len(coords) for _ in coords]
    for i, a in enumerate(coords):
        for j, b in enumerate(coords):
            if i == j:
                continue
            d = haversine_m(a, b) * 1.35
            distances[i][j] = d
            durations[i][j] = d / 8.33  # about 30 km/h
    return distances, durations


def _fallback_order_total(coords: list[Coord], order: list[int]) -> tuple[float, float, list[list[float]], str]:
    total_d = 0.0
    geometry: list[list[float]] = []
    for left, right in zip(order, order[1:]):
        a = coords[left]
        b = coords[right]
        total_d += haversine_m(a, b) * 1.35
        if not geometry:
            geometry.append([a[1], a[0]])
        geometry.append([b[1], b[0]])
    return total_d, total_d / 8.33, geometry, "haversine_estimate"


def _is_public_osrm() -> bool:
    return "router.project-osrm.org" in settings.osrm_url.lower()


async def route_leg(a: Coord, b: Coord) -> tuple[float, float, list[list[float]]]:
    distance, duration, geometry, _source = await route_for_order([a, b], [0, 1], overview="full")
    return distance, duration, geometry


async def _osrm_route_chunk(chunk_coords: list[Coord], overview: str = "false") -> tuple[float, float, list[list[float]]]:
    coord_text = ";".join(f"{lng},{lat}" for lat, lng in chunk_coords)
    url = f"{settings.osrm_url.rstrip('/')}/route/v1/driving/{coord_text}"
    params = {"overview": overview, "geometries": "geojson"}
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError(f"OSRM route error: {data}")
    route = data["routes"][0]
    geometry = route.get("geometry", {}).get("coordinates") or []
    return float(route["distance"]), float(route["duration"]), geometry


async def route_for_order(
    coords: list[Coord],
    order: list[int],
    overview: str = "false",
) -> tuple[float, float, list[list[float]], str]:
    """Calculate route total through OSRM, chunking long waypoint lists.

    Public OSRM has practical waypoint and URL-size limits. Chunking preserves
    road-based final metrics while avoiding a request with hundreds of waypoints.
    """
    if len(order) < 2:
        return 0.0, 0.0, [], "osrm_road"

    max_waypoints = max(2, settings.max_osrm_route_waypoints)
    total_d = 0.0
    total_t = 0.0
    geometry: list[list[float]] = []

    try:
        start = 0
        while start < len(order) - 1:
            chunk_indices = order[start : start + max_waypoints]
            if len(chunk_indices) < 2:
                break
            chunk_coords = [coords[index] for index in chunk_indices]
            d, t, chunk_geometry = await _osrm_route_chunk(chunk_coords, overview=overview)
            total_d += d
            total_t += t
            if overview != "false" and chunk_geometry:
                if geometry:
                    geometry.extend(chunk_geometry[1:])
                else:
                    geometry.extend(chunk_geometry)
            start += max_waypoints - 1
        return total_d, total_t, geometry, "osrm_road"
    except Exception as exc:
        if settings.allow_haversine_fallback:
            return _fallback_order_total(coords, order)
        raise ValueError(
            "OSRM route request failed. Road-based route totals are required by strict mode. "
            "For demo/local development set ALLOW_HAVERSINE_FALLBACK=true. Original error: " + str(exc)
        ) from exc


async def distance_duration_matrix(coords: list[Coord]) -> tuple[list[list[float]], list[list[float]], str]:
    if not coords:
        return [], [], "empty"
    if len(coords) == 1:
        return [[0.0]], [[0.0]], "single_point"
    if len(coords) > settings.max_points_to_optimize:
        raise ValueError(
            f"Route has {len(coords)} points. The configured safety limit is "
            f"{settings.max_points_to_optimize}. Split the route or increase MAX_POINTS_TO_OPTIMIZE."
        )

    if _is_public_osrm() and len(coords) > settings.max_public_osrm_table_points:
        if settings.allow_approximate_matrix_for_large_routes or settings.allow_haversine_fallback:
            distances, durations = _fallback_matrix(coords)
            return distances, durations, "haversine_matrix_large_route"
        raise ValueError(
            f"Public OSRM table is limited for large requests. Route has {len(coords)} points, "
            f"configured public-table limit is {settings.max_public_osrm_table_points}. "
            "Use a local OSRM instance or enable ALLOW_APPROXIMATE_MATRIX_FOR_LARGE_ROUTES=true."
        )

    coord_text = ";".join(f"{lng},{lat}" for lat, lng in coords)
    url = f"{settings.osrm_url.rstrip('/')}/table/v1/driving/{coord_text}"
    params = {"annotations": "distance,duration"}

    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        if data.get("code") == "Ok" and data.get("distances") and data.get("durations"):
            distances = [[float(v or 0) for v in row] for row in data["distances"]]
            durations = [[float(v or 0) for v in row] for row in data["durations"]]
            return distances, durations, "osrm_table"
        raise ValueError(f"OSRM table error: {data}")
    except Exception as exc:
        if settings.allow_haversine_fallback:
            distances, durations = _fallback_matrix(coords)
            return distances, durations, "haversine_matrix_fallback"
        raise ValueError(
            "OSRM table request failed. Road-based distances are required by strict mode, so the "
            "application does not silently use straight-line fallback. For local development only, "
            "set ALLOW_HAVERSINE_FALLBACK=true. Original error: " + str(exc)
        ) from exc


async def polyline_for_order(coords: list[Coord], order: list[int]) -> tuple[float, float, list[list[float]]]:
    distance_m, duration_s, geometry, _source = await route_for_order(coords, order, overview="full")
    return distance_m, duration_s, geometry
