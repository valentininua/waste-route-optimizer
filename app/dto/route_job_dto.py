from __future__ import annotations

from pydantic import BaseModel, Field

from app.dto.collection_point_dto import CollectionPointDto
from app.dto.route_metrics_dto import RouteMetricsDto


class RouteJobDto(BaseModel):
    id: int = Field(description="Route job identifier", examples=[1294])
    filename: str = Field(description="Original Excel filename", examples=["Routes 01.01.2026-31.03.2026 tech test.xlsx"])
    route_code: str | None = Field(default=None, description="Route code extracted from Excel", examples=["ML 11840"])
    route_date: str | None = Field(default=None, description="Route date extracted from Excel", examples=["2026-01-01"])
    source_row: int | None = Field(default=None, description="1-based row number where this route starts in Excel", examples=[4])
    status: str = Field(description="Current route processing status", examples=["optimized"])
    points_count: int = Field(description="Number of collection points", examples=[119])
    total_volume: float = Field(description="Calculated total volume", examples=[117.45])
    total_containers: int = Field(description="Calculated total number of containers", examples=[191])
    declared_total_volume: float | None = Field(default=None, description="Total volume declared by Excel summary row", examples=[117.45])
    declared_total_containers: int | None = Field(default=None, description="Container count declared by Excel summary row", examples=[191])
    error: str | None = Field(default=None, description="Last processing error, if any")
    metrics_source: str | None = Field(default=None, description="Source of distance metrics and optimization matrix")
    metrics: RouteMetricsDto | None = Field(default=None, description="Route comparison metrics after optimization")
    points: list[CollectionPointDto] | None = Field(default=None, description="Collection points, included for route detail responses")
