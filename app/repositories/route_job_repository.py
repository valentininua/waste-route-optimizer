from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import CollectionPoint, OptimizationRun, RouteJob


class RouteJobRepository:
    """Database access for route jobs.

    The API layer should not own filtering, deletion, or deduplication rules. Keeping those
    operations here makes controllers thin and keeps persistence concerns isolated.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, job_id: int) -> RouteJob | None:
        return self.db.get(RouteJob, job_id)

    def delete_by_filename(self, filename: str) -> int:
        """Delete all imported jobs for a file using bulk SQL statements.

        The upload endpoint replaces previous imports for the same filename. Doing
        this with ORM ``delete(job)`` in a loop issues one DELETE per route and
        becomes slow for large Excel files. We explicitly remove dependent rows
        first, then delete route jobs in bulk. This keeps the behaviour portable
        across PostgreSQL and SQLite-based tests, without relying on runtime FK
        cascade settings.
        """
        route_ids = [
            row[0]
            for row in self.db.query(RouteJob.id)
            .filter(RouteJob.filename == filename)
            .all()
        ]
        if not route_ids:
            return 0

        self.db.query(CollectionPoint).filter(
            CollectionPoint.job_id.in_(route_ids)
        ).delete(synchronize_session=False)
        self.db.query(OptimizationRun).filter(
            OptimizationRun.route_job_id.in_(route_ids)
        ).delete(synchronize_session=False)
        deleted = (
            self.db.query(RouteJob)
            .filter(RouteJob.id.in_(route_ids))
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return int(deleted or 0)

    def list(
        self,
        *,
        route_date: str | None = None,
        route_code: str | None = None,
        limit: int = 100,
        include_duplicates: bool = False,
    ) -> list[RouteJob]:
        query = self.db.query(RouteJob)
        if route_date:
            query = query.filter(RouteJob.route_date == route_date)
        if route_code:
            query = query.filter(func.lower(RouteJob.route_code) == route_code.lower())

        if include_duplicates:
            return (
                query.order_by(RouteJob.route_date.asc(), RouteJob.route_code.asc(), RouteJob.id.asc())
                .limit(limit)
                .all()
            )

        raw_jobs = query.order_by(RouteJob.id.desc()).limit(limit * 20).all()
        return self.deduplicate_latest(raw_jobs)[:limit]

    @staticmethod
    def deduplicate_latest(jobs: list[RouteJob]) -> list[RouteJob]:
        seen: set[tuple[str | None, str | None, str | None, int | None]] = set()
        result: list[RouteJob] = []
        for job in sorted(jobs, key=lambda item: item.id, reverse=True):
            key = (job.filename, job.route_code, job.route_date, job.source_row)
            if key in seen:
                continue
            seen.add(key)
            result.append(job)
        return sorted(result, key=lambda item: (item.route_date or "", item.route_code or "", item.id))

    def count(self) -> int:
        return self.db.query(RouteJob).count()

    def unique_count(self, scan_limit: int = 20000) -> int:
        jobs = self.db.query(RouteJob).order_by(RouteJob.id.desc()).limit(scan_limit).all()
        return len(self.deduplicate_latest(jobs))

    def optimized_count(self) -> int:
        return self.db.query(RouteJob).filter(RouteJob.status == "optimized").count()

    def failed_count(self) -> int:
        return self.db.query(RouteJob).filter(RouteJob.status == "failed").count()
