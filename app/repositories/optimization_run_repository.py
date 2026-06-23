from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import OptimizationRun


class OptimizationRunRepository:
    """Database access for background optimization runs."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, run_id: int) -> OptimizationRun | None:
        return self.db.get(OptimizationRun, run_id)

    def latest_active_for_route(self, route_job_id: int) -> OptimizationRun | None:
        return (
            self.db.query(OptimizationRun)
            .filter(OptimizationRun.route_job_id == route_job_id, OptimizationRun.status.in_(["queued", "running"]))
            .order_by(OptimizationRun.id.desc())
            .first()
        )

    def create_queued(self, route_job_id: int, *, commit: bool = True) -> OptimizationRun:
        run = OptimizationRun(
            route_job_id=route_job_id,
            status="queued",
            stage="queued",
            progress_percent=0,
            message="Optimization is queued.",
        )
        self.db.add(run)
        if commit:
            self.db.commit()
            self.db.refresh(run)
        else:
            self.db.flush()
        return run

    def list_for_route(self, route_job_id: int, limit: int = 25) -> list[OptimizationRun]:
        return (
            self.db.query(OptimizationRun)
            .filter(OptimizationRun.route_job_id == route_job_id)
            .order_by(OptimizationRun.id.desc())
            .limit(limit)
            .all()
        )

    def count(self) -> int:
        return self.db.query(OptimizationRun).count()

    def running_count(self) -> int:
        return self.db.query(OptimizationRun).filter(OptimizationRun.status.in_(["queued", "running"])).count()
