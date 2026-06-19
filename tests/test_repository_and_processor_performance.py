from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import CollectionPoint, GeocodeCache, OptimizationRun, RouteJob
from app.repositories.route_job_repository import RouteJobRepository
from app.services.route_processor import _load_geocode_cache_for_points


def _memory_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_delete_by_filename_bulk_deletes_related_rows():
    db = _memory_session()
    keep = RouteJob(filename="keep.xlsx", route_code="ML 1", route_date="2026-01-01")
    delete_a = RouteJob(filename="routes.xlsx", route_code="ML 2", route_date="2026-01-01")
    delete_b = RouteJob(filename="routes.xlsx", route_code="ML 3", route_date="2026-01-02")
    db.add_all([keep, delete_a, delete_b])
    db.flush()
    db.add_all([
        CollectionPoint(job_id=delete_a.id, original_order=1, address="A"),
        CollectionPoint(job_id=delete_b.id, original_order=1, address="B"),
        OptimizationRun(route_job_id=delete_a.id, status="queued", progress_percent=0),
        OptimizationRun(route_job_id=delete_b.id, status="queued", progress_percent=0),
    ])
    db.commit()

    deleted = RouteJobRepository(db).delete_by_filename("routes.xlsx")

    assert deleted == 2
    assert db.query(RouteJob).count() == 1
    assert db.query(RouteJob).one().filename == "keep.xlsx"
    assert db.query(CollectionPoint).count() == 0
    assert db.query(OptimizationRun).count() == 0


def test_geocode_cache_is_loaded_in_bulk_for_pending_points():
    db = _memory_session()
    db.add_all([
        GeocodeCache(
            query="Dobeles iela 41A, Jelgava, Latvia",
            lat=56.6525798,
            lng=23.7135755,
            quality="building",
        ),
        GeocodeCache(
            query="Dobeles iela 48, Jelgava, Latvia",
            lat=56.6531656,
            lng=23.7143121,
            quality="yes",
        ),
    ])
    db.commit()
    points = [
        CollectionPoint(original_order=1, address="Dobeles iela 41A"),
        CollectionPoint(original_order=2, address="Dobeles iela 48/IVENS/"),
        CollectionPoint(original_order=3, address="Unknown iela 1"),
    ]

    cache_map = _load_geocode_cache_for_points(db, points)

    assert cache_map["dobeles iela 41a, jelgava, latvia"] == (56.6525798, 23.7135755, "building")
    assert cache_map["dobeles iela 48, jelgava, latvia"] == (56.6531656, 23.7143121, "yes")
    assert "unknown iela 1, jelgava, latvia" not in cache_map
