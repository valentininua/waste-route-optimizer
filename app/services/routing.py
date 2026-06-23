from __future__ import annotations

import asyncio
import math

import httpx
from app.core.config import get_settings

settings = get_settings()
LatLng = tuple[float, float]  # internal convention: (lat, lng)
Coord = LatLng  # backward-compatible alias for tests/imports


class OSRMProviderError(RuntimeError):
    """Raised when OSRM cannot return a valid road-based route/matrix."""


def haversine_m(a: LatLng, b: LatLng) -> float:
    r = 6371000
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _fallback_matrix(coords: list[LatLng]) -> tuple[list[list[float]], list[list[float]]]:
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


def _fallback_order_total(coords: list[LatLng], order: list[int]) -> tuple[float, float, list[list[float]], str]:
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


async def _request_with_retries(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, str],
    operation: str,
) -> httpx.Response:
    attempts = max(1, settings.osrm_retry_attempts + 1)
    last_error: OSRMProviderError | None = None

    for attempt in range(1, attempts + 1):
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            last_error = OSRMProviderError(f"OSRM {operation} HTTP {status}: {exc}")
            # 4xx errors are usually deterministic request/provider limits; retrying
            # them just burns time. Retry only transient/server-side failures.
            if status < 500 and status not in {408, 409, 425, 429}:
                raise last_error from exc
        except httpx.TimeoutException as exc:
            last_error = OSRMProviderError(f"OSRM {operation} timed out: {exc}")
        except httpx.RequestError as exc:
            last_error = OSRMProviderError(f"OSRM {operation} request failed: {exc}")

        if attempt < attempts:
            await asyncio.sleep(settings.osrm_retry_backoff_seconds * attempt)

    assert last_error is not None
    raise last_error


async def route_leg(a: LatLng, b: LatLng) -> tuple[float, float, list[list[float]]]:
    distance, duration, geometry, _source = await route_for_order([a, b], [0, 1], overview="full")
    return distance, duration, geometry


async def _osrm_route_chunk(chunk_coords: list[LatLng], overview: str = "false") -> tuple[float, float, list[list[float]]]:
    coord_text = ";".join(f"{lng},{lat}" for lat, lng in chunk_coords)
    url = f"{settings.osrm_url.rstrip('/')}/route/v1/driving/{coord_text}"
    params = {"overview": overview, "geometries": "geojson"}
    async with httpx.AsyncClient(timeout=settings.osrm_route_timeout_seconds) as client:
        response = await _request_with_retries(client, url, params=params, operation="route")

    try:
        data = response.json()
    except ValueError as exc:
        raise OSRMProviderError("OSRM route response is not valid JSON") from exc

    if data.get("code") != "Ok" or not data.get("routes"):
        raise OSRMProviderError(f"OSRM route error: {data}")
    route = data["routes"][0]
    try:
        geometry = route.get("geometry", {}).get("coordinates") or []
        return float(route["distance"]), float(route["duration"]), geometry
    except (KeyError, TypeError, ValueError) as exc:
        raise OSRMProviderError(f"OSRM route response has unexpected shape: {data}") from exc


async def route_for_order(
    coords: list[LatLng],
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
    except OSRMProviderError as exc:
        if settings.allow_haversine_fallback:
            return _fallback_order_total(coords, order)
        raise ValueError(
            "OSRM route request failed. Road-based route totals are required by strict mode. "
            "For demo/local development set ALLOW_HAVERSINE_FALLBACK=true. Original error: " + str(exc)
        ) from exc


async def distance_duration_matrix(coords: list[LatLng]) -> tuple[list[list[float]], list[list[float]], str]:
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
        async with httpx.AsyncClient(timeout=settings.osrm_table_timeout_seconds) as client:
            response = await _request_with_retries(client, url, params=params, operation="table")
        try:
            data = response.json()
        except ValueError as exc:
            raise OSRMProviderError("OSRM table response is not valid JSON") from exc

        if data.get("code") == "Ok" and data.get("distances") and data.get("durations"):
            try:
                distances = [[float(v or 0) for v in row] for row in data["distances"]]
                durations = [[float(v or 0) for v in row] for row in data["durations"]]
            except (TypeError, ValueError) as exc:
                raise OSRMProviderError(f"OSRM table response has unexpected shape: {data}") from exc
            return distances, durations, "osrm_table"
        raise OSRMProviderError(f"OSRM table error: {data}")
    except OSRMProviderError as exc:
        provider_error = exc

    if settings.allow_haversine_fallback:
        distances, durations = _fallback_matrix(coords)
        return distances, durations, "haversine_matrix_fallback"
    raise ValueError(
        "OSRM table request failed. Road-based distances are required by strict mode, so the "
        "application does not silently use straight-line fallback. For local development only, "
        "set ALLOW_HAVERSINE_FALLBACK=true. Original error: " + str(provider_error)
    ) from provider_error


async def polyline_for_order(coords: list[LatLng], order: list[int]) -> tuple[float, float, list[list[float]]]:
    distance_m, duration_s, geometry, _source = await route_for_order(coords, order, overview="full")
    return distance_m, duration_s, geometry
