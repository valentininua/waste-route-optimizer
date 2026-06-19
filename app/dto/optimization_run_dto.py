from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.dto.route_job_dto import RouteJobDto


class OptimizationRunDto(BaseModel):
    id: int = Field(description="Optimization run identifier", examples=[10])
    route_job_id: int = Field(description="Related route job identifier", examples=[1294])
    status: str = Field(description="Run status", examples=["completed"])
    stage: str | None = Field(default=None, description="Current processing stage", examples=["completed"])
    progress_percent: int = Field(description="Approximate progress percent", examples=[100])
    message: str | None = Field(default=None, description="Current run message")
    error: str | None = Field(default=None, description="Run error, if failed")
    route: RouteJobDto | None = Field(default=None, description="Related route summary or full route after completion")
    created_at: datetime | None = Field(default=None, description="Run creation timestamp")
    started_at: datetime | None = Field(default=None, description="Run start timestamp")
    finished_at: datetime | None = Field(default=None, description="Run finish timestamp")

    model_config = ConfigDict(from_attributes=True)
