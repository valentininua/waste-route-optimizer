from __future__ import annotations

from pydantic import BaseModel, Field


class RouteMetricsDto(BaseModel):
    original_distance_km: float = Field(description="Original route distance in kilometers", examples=[163.647])
    optimized_distance_km: float = Field(description="Optimized route distance in kilometers", examples=[66.952])
    saved_distance_km: float = Field(description="Distance saved in kilometers", examples=[96.694])
    saved_percent: float = Field(description="Distance saving percentage", examples=[59.09])
    original_duration_min: float = Field(description="Original route duration in minutes", examples=[331.7])
    optimized_duration_min: float = Field(description="Optimized route duration in minutes", examples=[159.9])
