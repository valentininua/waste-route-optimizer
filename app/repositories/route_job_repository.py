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

    def _deduplicated_route_ids_query(self, *, route_date: str | None = None, route_code: str | None = None):
        """Return SQL query with the latest row per imported route identity.

        Route identity is defined by the fields that come from the Excel import:
        filename, route_code, route_date and source_row. Older implementation did
        this in Python after loading a large candidate set. Using row_number() keeps
        deduplication in the database and scales better for large imports.
        """
        row_number = func.row_number().over(
            partition_by=(RouteJob.filename, RouteJob.route_code, RouteJob.route_date, RouteJob.source_row),
            order_by=RouteJob.id.desc(),
        ).label("row_number")

        query = self.db.query(RouteJob.id.label("id"), row_number)
        if route_date:
            query = query.filter(RouteJob.route_date == route_date)
        if route_code:
            query = query.filter(func.lower(RouteJob.route_code) == route_code.lower())
        return query.subquery()

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

        latest_ids = self._deduplicated_route_ids_query(route_date=route_date, route_code=route_code)
        return (
            self.db.query(RouteJob)
            .join(latest_ids, RouteJob.id == latest_ids.c.id)
            .filter(latest_ids.c.row_number == 1)
            .order_by(RouteJob.route_date.asc(), RouteJob.route_code.asc(), RouteJob.id.asc())
            .limit(limit)
            .all()
        )

    def count(self) -> int:
        return self.db.query(RouteJob).count()

    def unique_count(self) -> int:
        latest_ids = self._deduplicated_route_ids_query()
        return int(
            self.db.query(func.count())
            .select_from(latest_ids)
            .filter(latest_ids.c.row_number == 1)
            .scalar()
            or 0
        )

    def optimized_count(self) -> int:
        return self.db.query(RouteJob).filter(RouteJob.status == "optimized").count()

    def failed_count(self) -> int:
        return self.db.query(RouteJob).filter(RouteJob.status == "failed").count()
