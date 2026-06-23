from __future__ import annotations

import asyncio
import hashlib
import math
import re
from collections import OrderedDict

import httpx
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import GeocodeCache

settings = get_settings()

_ADDRESS_NOTE_PATTERNS = [
    re.compile(r"/[^/]+/"),          # Dobeles iela 48/IVENS/ -> Dobeles iela 48
    re.compile(r"\([^)]*\)"),       # address (comment)
    re.compile(r"\[[^]]*\]"),       # address [comment]
]

_STREET_KEYWORDS = (
    "iela",
    "gatve",
    "prospekts",
    "prosp",
    "bulvāris",
    "bulv",
    "šoseja",
    "ceļš",
    "laukums",
    "krastmala",
)

# Common abbreviations found in the real Jelgava export. They are expanded before
# calling Nominatim because OSM usually stores official street names, not internal
# operational abbreviations from route sheets.
_ABBREVIATION_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bPulkv\.?\s*O\.?\s*Kalpaka\b", re.IGNORECASE), "Pulkveža Oskara Kalpaka"),
    (re.compile(r"\bPulkv\.?\s*Brieža\b", re.IGNORECASE), "Pulkveža Brieža"),
    (re.compile(r"\bKr\.?\s*Barona\b", re.IGNORECASE), "Krišjāņa Barona"),
    (re.compile(r"\bJ\.?\s*Čakstes\b", re.IGNORECASE), "Jāņa Čakstes"),
    (re.compile(r"\bČakstes\b", re.IGNORECASE), "Jāņa Čakstes"),
    (re.compile(r"\bJ\.?\s*Asara\b", re.IGNORECASE), "Jāņa Asara"),
    (re.compile(r"\bS\.?\s*Edžus\b", re.IGNORECASE), "Sudrabu Edžus"),
    (re.compile(r"\bBlaumana\b", re.IGNORECASE), "Blaumaņa"),
    (re.compile(r"\bZemgales\s+prosp\.?\b", re.IGNORECASE), "Zemgales prospekts"),
    (re.compile(r"\bbulv\.?\b", re.IGNORECASE), "bulvāris"),
    (re.compile(r"\bprosp\.?\b", re.IGNORECASE), "prospekts"),
]

_HOUSE_NUMBER_RE = re.compile(r"\b\d+[A-Za-zĀ-ž]?(?:[-/]\d+[A-Za-zĀ-ž]?)?\b")
_TRAILING_HOUSE_RE = re.compile(r"\s+\d+[A-Za-zĀ-ž]?(?:[-/]\d+[A-Za-zĀ-ž]?)?\s*$")
_NAME_AND_HOUSE_RE = re.compile(r"^(?P<name>[A-Za-zĀ-ž.\-\s]+?)\s+(?P<number>\d+[A-Za-zĀ-ž]?)$", re.IGNORECASE)


class GeocodingProviderError(RuntimeError):
    """Raised when the external geocoding provider blocks or fails the request."""


def _squash_spaces(value: str) -> str:
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s+([,;])", r"\1", value)
    value = re.sub(r"([,;])\s+", r"\1 ", value)
    return value.strip(" ,;\t\n\r")


def expand_known_abbreviations(address: str) -> str:
    value = str(address or "")
    for pattern, replacement in _ABBREVIATION_REPLACEMENTS:
        value = pattern.sub(replacement, value)
    # Operational exports sometimes omit a space before house number:
    # "Zemgales prosp.2" -> "Zemgales prospekts 2".
    value = re.sub(r"(?<=[A-Za-zĀ-ž.])(?=\d)", " ", value)
    return _squash_spaces(value)


def normalize_address_for_geocoding(address: str) -> str:
    """Remove route-sheet notes that are not part of a postal address."""
    value = str(address or "").strip()
    for pattern in _ADDRESS_NOTE_PATTERNS:
        value = pattern.sub(" ", value)
    # Handles half-open comments, e.g. "Raiņa iela 1/LLU".
    value = re.sub(r"/[A-Za-zĀ-ž].*$", " ", value)
    value = value.replace("|", " ")
    return _squash_spaces(value)


def _has_street_keyword(value: str) -> bool:
    lower = value.lower()
    return any(keyword in lower for keyword in _STREET_KEYWORDS)


def _looks_like_street_without_type(value: str) -> bool:
    return bool(_NAME_AND_HOUSE_RE.match(value.strip())) and not _has_street_keyword(value)


def _infer_missing_iela(value: str) -> str:
    match = _NAME_AND_HOUSE_RE.match(value.strip())
    if not match or _has_street_keyword(value):
        return value
    return f"{match.group('name').strip()} iela {match.group('number').strip()}"


def _street_prefix(address: str) -> str | None:
    value = _squash_spaces(address)
    if not _has_street_keyword(value):
        return None
    without_house = _TRAILING_HOUSE_RE.sub("", value).strip()
    return without_house if without_house and without_house != value else None


def _street_level_candidate(address: str) -> str | None:
    value = _squash_spaces(address)
    candidate = _street_prefix(value)
    if candidate and _has_street_keyword(candidate):
        return candidate
    return None


_MULTI_HOUSE_RE = re.compile(
    r"^(?P<street>.+?\b(?:iela|gatve|prospekts|bulvāris|šoseja|ceļš|laukums|krastmala)\b)\s+"
    r"(?P<numbers>\d+[A-Za-zĀ-ž]?(?:\s*,\s*\d+[A-Za-zĀ-ž]?)+)$",
    re.IGNORECASE,
)


def _expand_comma_house_numbers(address: str) -> list[str]:
    value = _squash_spaces(address)
    match = _MULTI_HOUSE_RE.match(value)
    if not match:
        return [value] if value else []
    street = _squash_spaces(match.group("street"))
    numbers = [number.strip() for number in match.group("numbers").split(",") if number.strip()]
    return [f"{street} {number}" for number in numbers]


def _split_multi_address(raw_address: str) -> list[str]:
    """Split grouped route-sheet addresses into geocodable candidates.

    Example: "Pulkv.O.Kalpaka iela 7;9;Svētes iela 35" becomes
    "Pulkveža Oskara Kalpaka iela 7", "... iela 9", "Svētes iela 35".
    """
    cleaned = normalize_address_for_geocoding(raw_address)
    if not cleaned:
        return []

    pieces = [_squash_spaces(part) for part in re.split(r";", cleaned) if _squash_spaces(part)]
    if not pieces:
        return []

    candidates: list[str] = []
    previous_street: str | None = None

    for piece in pieces:
        piece = expand_known_abbreviations(piece)
        piece = _infer_missing_iela(piece)

        if _has_street_keyword(piece):
            expanded_pieces = _expand_comma_house_numbers(piece)
            candidates.extend(expanded_pieces)
            previous_street = _street_prefix(expanded_pieces[-1]) or previous_street
            continue

        # A naked house number after a full street means the same street.
        if previous_street and _HOUSE_NUMBER_RE.fullmatch(piece):
            candidates.append(f"{previous_street} {piece}")
            continue

        if _looks_like_street_without_type(piece):
            inferred = expand_known_abbreviations(_infer_missing_iela(piece))
            inferred_values = _expand_comma_house_numbers(inferred)
            candidates.extend(inferred_values)
            previous_street = _street_prefix(inferred_values[-1]) or previous_street
            continue

        candidates.append(piece)

    return [_squash_spaces(candidate) for candidate in candidates if _squash_spaces(candidate)]


def build_geocode_query(address: str) -> str:
    parts = [_squash_spaces(address)]
    base_lower = parts[0].lower()
    if settings.default_city and settings.default_city.lower() not in base_lower:
        parts.append(settings.default_city)
    joined_lower = ", ".join(parts).lower()
    if settings.default_country and settings.default_country.lower() not in joined_lower:
        parts.append(settings.default_country)
    return ", ".join(p for p in parts if p)


def _add_candidate(result: OrderedDict[str, None], value: str) -> None:
    value = _squash_spaces(value)
    if value:
        result[build_geocode_query(value)] = None


def geocode_query_candidates(address: str) -> list[str]:
    """Return ordered Nominatim query candidates from strict to broad.

    Grouped addresses are split before trying the whole string. This avoids bad
    requests like "Street 7;9;Other Street 35" as the first Nominatim query.
    """
    raw = _squash_spaces(str(address or ""))
    cleaned = normalize_address_for_geocoding(raw)
    expanded_cleaned = expand_known_abbreviations(cleaned)
    candidates: OrderedDict[str, None] = OrderedDict()

    # 1) Split operational grouped addresses first.
    split_candidates = _split_multi_address(raw)
    for value in split_candidates:
        expanded = expand_known_abbreviations(value)
        _add_candidate(candidates, expanded)
        if expanded != value:
            _add_candidate(candidates, value)
        street_level = _street_level_candidate(expanded)
        if street_level:
            _add_candidate(candidates, street_level)

    # 2) Cleaned whole string for simple dirty addresses. For grouped values this
    # is useful only as a later fallback, not as the primary candidate.
    _add_candidate(candidates, expanded_cleaned)
    if expanded_cleaned != cleaned:
        _add_candidate(candidates, cleaned)

    # 3) Conservative first-part fallback.
    if ";" in raw:
        first_part = normalize_address_for_geocoding(raw.split(";", 1)[0])
        first_part = expand_known_abbreviations(_infer_missing_iela(first_part))
        _add_candidate(candidates, first_part)
        street_level = _street_level_candidate(first_part)
        if street_level:
            _add_candidate(candidates, street_level)

    # 4) Additional slash fallback: keep only the part before a malformed slash.
    if "/" in raw:
        before_slash = normalize_address_for_geocoding(raw.split("/", 1)[0])
        before_slash = expand_known_abbreviations(_infer_missing_iela(before_slash))
        _add_candidate(candidates, before_slash)
        street_level = _street_level_candidate(before_slash)
        if street_level:
            _add_candidate(candidates, street_level)

    # 5) Raw query last. It is useful for traceability but should not be tried
    # before cleaned/split candidates.
    _add_candidate(candidates, raw)

    return list(candidates.keys())


def geocode_cache_key(address: str) -> str:
    candidates = geocode_query_candidates(address)
    return candidates[0] if candidates else build_geocode_query(address)


def _nominatim_headers() -> dict[str, str]:
    return {
        "User-Agent": settings.app_user_agent,
        "Accept-Language": "lv,en;q=0.8",
    }


async def _request_nominatim(query: str) -> dict | None:
    params = {"q": query, "format": "json", "limit": 1, "addressdetails": 1}
    if settings.nominatim_email:
        params["email"] = settings.nominatim_email
    async with httpx.AsyncClient(timeout=30, headers=_nominatim_headers()) as client:
        try:
            response = await client.get(settings.nominatim_url, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in {403, 429}:
                raise GeocodingProviderError(
                    f"Nominatim rejected the request with HTTP {status}. "
                    "This usually means public-service rate limiting or User-Agent/contact policy enforcement."
                ) from exc
            raise GeocodingProviderError(f"Nominatim HTTP error {status}: {exc}") from exc
        except httpx.HTTPError as exc:
            raise GeocodingProviderError(f"Nominatim request failed: {exc}") from exc
        data = response.json()
    await asyncio.sleep(settings.geocoding_sleep_seconds)
    return data[0] if data else None


def _stable_unit_interval(text: str, salt: str) -> float:
    digest = hashlib.sha256(f"{salt}:{text}".encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(0xFFFFFFFFFFFF)


def approximate_geocode(address: str) -> tuple[float, float, str]:
    """Deterministic emergency fallback for demo/test environments.

    It keeps generated coordinates inside the Jelgava area so the UI and route
    optimization remain testable when public Nominatim blocks requests. It is
    explicitly marked as approximate and cached with that quality flag.
    """
    base = geocode_cache_key(address)
    u = _stable_unit_interval(base, "lat")
    v = _stable_unit_interval(base, "lng")
    # Rough city-sized envelope around central Jelgava. Cosine correction keeps
    # longitudinal spread visually comparable to latitudinal spread.
    lat_offset = (u - 0.5) * 0.055
    lng_offset = (v - 0.5) * 0.075 / max(math.cos(math.radians(settings.approximate_center_lat)), 0.2)
    lat = settings.approximate_center_lat + lat_offset
    lng = settings.approximate_center_lng + lng_offset
    return round(lat, 7), round(lng, 7), "approximate_fallback"


def _store_cache_aliases(
    db: Session,
    candidates: list[str],
    lat: float,
    lng: float,
    display_name: str | None,
    quality: str,
    successful_query: str | None = None,
) -> None:
    """Store geocoding result for all candidate aliases without a read/write race.

    The previous implementation checked whether an alias existed and then inserted
    it. Two parallel optimization runs could pass that check at the same time and
    then one of them would fail on the unique query constraint. Here the database
    owns deduplication through INSERT .. ON CONFLICT DO NOTHING where supported.
    """
    rows = []
    for alias in candidates:
        alias_quality = quality if alias == successful_query or successful_query is None else f"alias:{quality}"
        rows.append({
            "query": alias,
            "lat": lat,
            "lng": lng,
            "display_name": display_name,
            "quality": alias_quality,
        })

    if not rows:
        return

    dialect_name = db.get_bind().dialect.name
    if dialect_name == "postgresql":
        statement = postgres_insert(GeocodeCache).values(rows)
        statement = statement.on_conflict_do_nothing(index_elements=["query"])
        db.execute(statement)
        db.commit()
        return

    if dialect_name == "sqlite":
        statement = sqlite_insert(GeocodeCache).values(rows)
        statement = statement.on_conflict_do_nothing(index_elements=["query"])
        db.execute(statement)
        db.commit()
        return

    # Fallback for other SQLAlchemy dialects: preserve correctness even if the
    # dialect does not expose ON CONFLICT syntax. A concurrent insert may still
    # trigger IntegrityError, in which case the cache row already exists and can
    # be safely ignored.
    try:
        db.add_all([GeocodeCache(**row) for row in rows])
        db.commit()
    except IntegrityError:
        db.rollback()


async def geocode_address(db: Session, address: str) -> tuple[float, float, str]:
    candidates = geocode_query_candidates(address)
    if not candidates:
        raise ValueError("Address is empty and cannot be geocoded")

    for query in candidates:
        cached = db.query(GeocodeCache).filter(GeocodeCache.query == query).one_or_none()
        if cached:
            return cached.lat, cached.lng, cached.quality or "cache"

    attempted: list[str] = []
    provider_error: str | None = None

    for query in candidates:
        attempted.append(query)
        try:
            item = await _request_nominatim(query)
        except GeocodingProviderError as exc:
            provider_error = str(exc)
            # 403/429 usually applies to all immediate follow-up candidates, so
            # stop hammering the public service and use the configured fallback.
            break

        if not item:
            continue

        lat = float(item["lat"])
        lng = float(item["lon"])
        quality = item.get("type") or item.get("class") or "nominatim"
        display_name = item.get("display_name")
        _store_cache_aliases(db, candidates, lat, lng, display_name, quality, successful_query=query)
        return lat, lng, quality

    if settings.allow_approximate_geocoding_fallback:
        lat, lng, quality = approximate_geocode(address)
        reason = provider_error or "Nominatim did not return a result"
        display_name = f"Approximate fallback for {address}. Reason: {reason}"
        _store_cache_aliases(db, candidates, lat, lng, display_name, quality)
        return lat, lng, quality

    reason = f" Provider error: {provider_error}" if provider_error else ""
    raise ValueError("Address was not geocoded. Tried: " + " | ".join(attempted) + reason)
