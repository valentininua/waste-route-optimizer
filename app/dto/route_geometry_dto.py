from __future__ import annotations

from pydantic import BaseModel, Field


class RouteGeometryDto(BaseModel):
    distance_m: float = Field(description="Route distance in meters", examples=[66952.0])
    duration_s: float = Field(description="Route duration in seconds", examples=[9594.0])
    geometry: list[list[float]] = Field(description="GeoJSON-style coordinates: [lng, lat]")
