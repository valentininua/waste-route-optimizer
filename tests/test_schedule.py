from app.services.schedule import parse_frequency_weeks, parse_service_days


def test_parse_service_days():
    assert parse_service_days("xx3xxx7") == ["Wednesday", "Sunday"]
    assert parse_service_days("xxx4xxx") == ["Thursday"]
    assert parse_service_days(None) == []


def test_parse_frequency_weeks():
    assert parse_frequency_weeks("1xn") == 1
    assert parse_frequency_weeks("1x2n") == 2
    assert parse_frequency_weeks("1x4n") == 4
    assert parse_frequency_weeks("") is None
