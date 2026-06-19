from __future__ import annotations

from pydantic import BaseModel, Field


class CollectionPointDto(BaseModel):
    id: int = Field(description="Collection point identifier", examples=[478612])
    original_order: int = Field(description="Point order from the Excel file", examples=[1])
    optimized_order: int | None = Field(default=None, description="Point order after optimization", examples=[1])
    address: str = Field(description="Collection point address from Excel", examples=["Dobeles iela 41A"])
    bin_code: str | None = Field(default=None, description="Bin identifier from Excel", examples=["04844"])
    service_day_code: str | None = Field(default=None, description="Compact service schedule code", examples=["xxx4xxx"])
    service_days: str | None = Field(default=None, description="Human-readable service days", examples=["Thursday"])
    frequency_code: str | None = Field(default=None, description="Compact service frequency code", examples=["1xn"])
    frequency_weeks: int | None = Field(default=None, description="Service period in weeks", examples=[1])
    service_date: str | None = Field(default=None, description="Route service date", examples=["2026-01-01"])
    time_spent: str | None = Field(default=None, description="Source Excel time value", examples=["11.29"])
    volume: float = Field(description="Bin/container volume", examples=[0.24])
    containers: int = Field(description="Number of containers", examples=[1])
    lat: float | None = Field(default=None, description="Latitude", examples=[56.6525798])
    lng: float | None = Field(default=None, description="Longitude", examples=[23.7135755])
    geocode_quality: str | None = Field(default=None, description="Geocoder match quality", examples=["building"])
