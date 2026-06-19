from __future__ import annotations

from app.models import CollectionPoint


def point_to_resource(point: CollectionPoint) -> dict:
    return {
        "id": point.id,
        "original_order": point.original_order,
        "optimized_order": point.optimized_order,
        "address": point.address,
        "bin_code": point.bin_code,
        "service_day_code": point.service_day_code,
        "service_days": point.service_days,
        "frequency_code": point.frequency_code,
        "frequency_weeks": point.frequency_weeks,
        "service_date": point.service_date,
        "time_spent": point.time_spent,
        "volume": point.volume,
        "containers": point.containers,
        "lat": point.lat,
        "lng": point.lng,
        "geocode_quality": point.geocode_quality,
    }
