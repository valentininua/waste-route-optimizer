from app.services.geocoding import (
    expand_known_abbreviations,
    normalize_address_for_geocoding,
    geocode_query_candidates,
    geocode_cache_key,
)


def test_normalize_address_removes_route_operator_notes():
    assert normalize_address_for_geocoding("Dobeles iela 48/IVENS/") == "Dobeles iela 48"
    assert normalize_address_for_geocoding(" Dobeles   iela 48 (comment) ") == "Dobeles iela 48"
    assert normalize_address_for_geocoding("Raiņa iela 1/LLU") == "Raiņa iela 1"


def test_geocode_candidates_try_clean_address_first():
    candidates = geocode_query_candidates("Dobeles iela 48/IVENS/")
    assert candidates[0] == "Dobeles iela 48, Jelgava, Latvia"
    assert "Dobeles iela 48/IVENS/, Jelgava, Latvia" in candidates
    assert geocode_cache_key("Dobeles iela 48/IVENS/") == "Dobeles iela 48, Jelgava, Latvia"


def test_geocode_candidates_for_multiple_addresses_try_first_address():
    candidates = geocode_query_candidates("Rūpniecības iela 1;Pasta iela 52;54/NEBRUK/")
    assert "Rūpniecības iela 1, Jelgava, Latvia" in candidates
    assert "Pasta iela 52, Jelgava, Latvia" in candidates
    assert "Pasta iela 54, Jelgava, Latvia" in candidates


def test_pulkveza_oskara_kalpaka_group_address_candidates():
    candidates = geocode_query_candidates("Pulkv.O.Kalpaka iela 7;9;Svētes iela 35")
    assert "Pulkveža Oskara Kalpaka iela 7, Jelgava, Latvia" in candidates
    assert "Pulkveža Oskara Kalpaka iela 9, Jelgava, Latvia" in candidates
    assert "Svētes iela 35, Jelgava, Latvia" in candidates
    assert "Pulkveža Oskara Kalpaka iela, Jelgava, Latvia" in candidates


def test_abbreviation_expansion():
    assert expand_known_abbreviations("Pulkv.O.Kalpaka iela 7") == "Pulkveža Oskara Kalpaka iela 7"
    assert expand_known_abbreviations("Kr.Barona iela 6") == "Krišjāņa Barona iela 6"
    assert expand_known_abbreviations("Zemgales prosp.2") == "Zemgales prospekts 2"
    assert expand_known_abbreviations("Čakstes bulv.9") == "Jāņa Čakstes bulvāris 9"


def test_missing_iela_is_inferred_for_short_street_forms():
    candidates = geocode_query_candidates("Pētera 9;11;13;Raiņa 22;24")
    assert "Pētera iela 9, Jelgava, Latvia" in candidates
    assert "Pētera iela 11, Jelgava, Latvia" in candidates
    assert "Pētera iela 13, Jelgava, Latvia" in candidates
    assert "Raiņa iela 22, Jelgava, Latvia" in candidates
    assert "Raiņa iela 24, Jelgava, Latvia" in candidates


def test_comma_separated_house_numbers_are_expanded():
    candidates = geocode_query_candidates("Uzvaras iela 3,7,11;Blaumana 8;10;Dobeles iela 8,10,12,14")
    assert "Uzvaras iela 3, Jelgava, Latvia" in candidates
    assert "Uzvaras iela 7, Jelgava, Latvia" in candidates
    assert "Uzvaras iela 11, Jelgava, Latvia" in candidates
    assert "Blaumaņa iela 8, Jelgava, Latvia" in candidates
    assert "Blaumaņa iela 10, Jelgava, Latvia" in candidates
    assert "Dobeles iela 8, Jelgava, Latvia" in candidates
    assert "Dobeles iela 14, Jelgava, Latvia" in candidates
