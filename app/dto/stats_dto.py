from __future__ import annotations

from pydantic import BaseModel, Field


class StatsDto(BaseModel):
    routes: int = Field(description="Total stored route jobs")
    unique_routes: int = Field(description="Latest unique route jobs")
    points: int = Field(description="Total stored collection points")
    optimized_routes: int = Field(description="Number of optimized routes")
    failed_routes: int = Field(description="Number of failed routes")
    optimization_runs: int = Field(description="Total optimization runs")
    running_runs: int = Field(description="Queued or running optimization runs")
