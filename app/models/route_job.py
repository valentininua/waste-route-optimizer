from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class RouteJob(Base):
    __tablename__ = "route_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    route_code: Mapped[str | None] = mapped_column(String(64), index=True)
    route_date: Mapped[str | None] = mapped_column(String(32), index=True)
    source_row: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="parsed", index=True)
    total_volume: Mapped[float] = mapped_column(Float, default=0)
    total_containers: Mapped[int] = mapped_column(Integer, default=0)
    declared_total_volume: Mapped[float | None] = mapped_column(Float)
    declared_total_containers: Mapped[int | None] = mapped_column(Integer)
    original_distance_m: Mapped[float | None] = mapped_column(Float)
    optimized_distance_m: Mapped[float | None] = mapped_column(Float)
    original_duration_s: Mapped[float | None] = mapped_column(Float)
    optimized_duration_s: Mapped[float | None] = mapped_column(Float)
    metrics_source: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    points: Mapped[list["CollectionPoint"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", order_by="CollectionPoint.original_order"
    )
    optimization_runs: Mapped[list["OptimizationRun"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", order_by="OptimizationRun.id"
    )
