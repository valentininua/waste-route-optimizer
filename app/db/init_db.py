from sqlalchemy import text

from app.db.session import Base, engine
from app.models import CollectionPoint, GeocodeCache, OptimizationRun, RouteJob  # noqa: F401


# create_all() creates missing tables, but it does not alter existing tables.
# This project evolved during the technical-test implementation, so a user may
# already have a Docker PostgreSQL volume created by an older version of the app.
# The lightweight migration below makes the app restart-safe and avoids errors
# like: column "route_code" of relation "route_jobs" does not exist.
POSTGRES_MIGRATIONS = [
    "ALTER TABLE route_jobs ADD COLUMN IF NOT EXISTS route_code VARCHAR(64)",
    "ALTER TABLE route_jobs ADD COLUMN IF NOT EXISTS route_date VARCHAR(32)",
    "ALTER TABLE route_jobs ADD COLUMN IF NOT EXISTS source_row INTEGER",
    "ALTER TABLE route_jobs ADD COLUMN IF NOT EXISTS declared_total_volume DOUBLE PRECISION",
    "ALTER TABLE route_jobs ADD COLUMN IF NOT EXISTS declared_total_containers INTEGER",
    "ALTER TABLE route_jobs ADD COLUMN IF NOT EXISTS metrics_source TEXT",
    "ALTER TABLE route_jobs ALTER COLUMN metrics_source TYPE TEXT",
    "ALTER TABLE collection_points ADD COLUMN IF NOT EXISTS service_date VARCHAR(32)",
    "ALTER TABLE collection_points ADD COLUMN IF NOT EXISTS time_spent VARCHAR(32)",
    "ALTER TABLE collection_points ADD COLUMN IF NOT EXISTS geocode_quality VARCHAR(64)",
    "CREATE INDEX IF NOT EXISTS ix_route_jobs_route_code ON route_jobs (route_code)",
    "CREATE INDEX IF NOT EXISTS ix_route_jobs_route_date ON route_jobs (route_date)",
    "CREATE INDEX IF NOT EXISTS ix_route_jobs_status ON route_jobs (status)",
    "CREATE INDEX IF NOT EXISTS ix_optimization_runs_route_job_id ON optimization_runs (route_job_id)",
    "CREATE INDEX IF NOT EXISTS ix_optimization_runs_status ON optimization_runs (status)",
    "CREATE INDEX IF NOT EXISTS ix_collection_points_original_order ON collection_points (original_order)",
    "CREATE INDEX IF NOT EXISTS ix_collection_points_optimized_order ON collection_points (optimized_order)",
    "CREATE INDEX IF NOT EXISTS ix_route_jobs_import_identity ON route_jobs (filename, route_code, route_date, source_row, id DESC)",
    "DELETE FROM optimization_runs a USING optimization_runs b WHERE a.route_job_id = b.route_job_id AND a.status IN ('queued', 'running') AND b.status IN ('queued', 'running') AND a.id < b.id",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_active_optimization_run_per_route ON optimization_runs (route_job_id) WHERE status IN ('queued', 'running')",
    "DELETE FROM geocode_cache a USING geocode_cache b WHERE a.query = b.query AND a.id < b.id",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_geocode_query ON geocode_cache (query)",
]

SQLITE_MIGRATIONS = [
    # SQLite has no ADD COLUMN IF NOT EXISTS. These commands are executed one by
    # one and duplicate-column errors are ignored in _apply_sqlite_migrations().
    "ALTER TABLE route_jobs ADD COLUMN route_code VARCHAR(64)",
    "ALTER TABLE route_jobs ADD COLUMN route_date VARCHAR(32)",
    "ALTER TABLE route_jobs ADD COLUMN source_row INTEGER",
    "ALTER TABLE route_jobs ADD COLUMN declared_total_volume FLOAT",
    "ALTER TABLE route_jobs ADD COLUMN declared_total_containers INTEGER",
    "ALTER TABLE route_jobs ADD COLUMN metrics_source TEXT",
    "ALTER TABLE collection_points ADD COLUMN service_date VARCHAR(32)",
    "ALTER TABLE collection_points ADD COLUMN time_spent VARCHAR(32)",
    "ALTER TABLE collection_points ADD COLUMN geocode_quality VARCHAR(64)",
    "CREATE INDEX IF NOT EXISTS ix_route_jobs_import_identity ON route_jobs (filename, route_code, route_date, source_row, id DESC)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_active_optimization_run_per_route ON optimization_runs (route_job_id) WHERE status IN ('queued', 'running')",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_geocode_query ON geocode_cache (query)",
]


def _table_exists(conn, table_name: str) -> bool:
    if engine.dialect.name == "postgresql":
        result = conn.execute(
            text("SELECT to_regclass(:table_name) IS NOT NULL"),
            {"table_name": f"public.{table_name}"},
        )
        return bool(result.scalar())
    if engine.dialect.name == "sqlite":
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"),
            {"table_name": table_name},
        )
        return result.first() is not None
    return True


def _apply_postgres_migrations() -> None:
    with engine.begin() as conn:
        if not _table_exists(conn, "route_jobs") or not _table_exists(conn, "collection_points"):
            return
        for statement in POSTGRES_MIGRATIONS:
            conn.execute(text(statement))


def _apply_sqlite_migrations() -> None:
    with engine.begin() as conn:
        if not _table_exists(conn, "route_jobs") or not _table_exists(conn, "collection_points"):
            return
        for statement in SQLITE_MIGRATIONS:
            try:
                conn.execute(text(statement))
            except Exception as exc:  # pragma: no cover - defensive compatibility path
                if "duplicate column" not in str(exc).lower():
                    raise


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "postgresql":
        _apply_postgres_migrations()
    elif engine.dialect.name == "sqlite":
        _apply_sqlite_migrations()
