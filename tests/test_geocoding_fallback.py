import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import GeocodeCache
from app.services import geocoding
from app.services.geocoding import GeocodingProviderError, geocode_address, geocode_query_candidates


def _memory_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_grouped_address_does_not_try_whole_semicolon_value_first():
    candidates = geocode_query_candidates("Pulkv.O.Kalpaka iela 7;9;Svētes iela 35")
    assert candidates[0] == "Pulkveža Oskara Kalpaka iela 7, Jelgava, Latvia"
    assert candidates[1] == "Pulkveža Oskara Kalpaka iela, Jelgava, Latvia"
    assert "Pulkveža Oskara Kalpaka iela 7;9;Svētes iela 35, Jelgava, Latvia" in candidates
    assert candidates.index("Pulkveža Oskara Kalpaka iela 7;9;Svētes iela 35, Jelgava, Latvia") > 3


@pytest.mark.asyncio
async def test_geocode_uses_deterministic_approximate_fallback_on_provider_403(monkeypatch):
    db = _memory_session()
    monkeypatch.setattr(geocoding.settings, "allow_approximate_geocoding_fallback", True)

    async def blocked(_query: str):
        raise GeocodingProviderError("Nominatim rejected the request with HTTP 403")

    monkeypatch.setattr(geocoding, "_request_nominatim", blocked)

    lat, lng, quality = await geocode_address(db, "Savienības iela 1")
    assert 56.5 < lat < 56.8
    assert 23.5 < lng < 24.0
    assert quality == "approximate_fallback"
    assert db.query(GeocodeCache).count() >= 1

    lat2, lng2, quality2 = await geocode_address(db, "Savienības iela 1")
    assert (lat2, lng2) == (lat, lng)
    assert "approximate" in quality2
