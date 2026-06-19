from __future__ import annotations

from pydantic import BaseModel, Field

from app.dto.route_job_dto import RouteJobDto


class UploadResponseDto(BaseModel):
    filename: str = Field(description="Uploaded Excel filename")
    routes_count: int = Field(description="Total route blocks parsed from the file", examples=[430])
    returned_routes_count: int = Field(description="Number of route summaries included in this response", examples=[100])
    points_count: int = Field(description="Total collection points parsed from the file", examples=[79552])
    replace_existing: bool = Field(description="Whether previous jobs for the same filename were removed before import", examples=[True])
    routes: list[RouteJobDto] = Field(description="Route summaries. The response is capped to the first 100 routes for UI usability.")
    message: str = Field(description="Human-readable import result")
