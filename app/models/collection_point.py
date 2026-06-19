from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class CollectionPoint(Base):
    __tablename__ = "collection_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("route_jobs.id", ondelete="CASCADE"), index=True)
    original_order: Mapped[int] = mapped_column(Integer, index=True)
    optimized_order: Mapped[int | None] = mapped_column(Integer, index=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    bin_code: Mapped[str | None] = mapped_column(String(64))
    service_day_code: Mapped[str | None] = mapped_column(String(32))
    service_days: Mapped[str | None] = mapped_column(String(128))
    frequency_code: Mapped[str | None] = mapped_column(String(32))
    frequency_weeks: Mapped[int | None] = mapped_column(Integer)
    service_date: Mapped[str | None] = mapped_column(String(32))
    time_spent: Mapped[str | None] = mapped_column(String(32))
    volume: Mapped[float] = mapped_column(Float, default=0)
    containers: Mapped[int] = mapped_column(Integer, default=0)
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    geocode_quality: Mapped[str | None] = mapped_column(String(64))

    job: Mapped["RouteJob"] = relationship(back_populates="points")
