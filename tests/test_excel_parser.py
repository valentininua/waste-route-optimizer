from pathlib import Path
import pandas as pd
from app.services.excel_parser import parse_excel_routes


def test_parse_excel_with_shifted_header_without_route_blocks(tmp_path: Path):
    path = tmp_path / "route.xlsx"
    rows = [
        [None, None, None, None],
        ["Date", "Order number of the route", "Address", "Volume of bin", "Number of containers", "Day of week when service provided", "Number of weeks when service provided"],
        ["01.01.26", 1, "Dobeles iela 41A", 0.24, 1, "xxx4xxx", "1xn"],
        ["01.01.26", 2, "Kungu iela 25", 1.1, 1, "xx3xxx7", "1x2n"],
    ]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)
    routes = parse_excel_routes(path)
    assert len(routes) == 1
    assert routes[0].route_code == "ROUTE 1"
    points = routes[0].points
    assert len(points) == 2
    assert points[0].address == "Dobeles iela 41A"
    assert points[0].service_days == ["Thursday"]
    assert points[1].frequency_weeks == 2


def test_parse_excel_routes_separates_realistic_ml_blocks(tmp_path: Path):
    path = tmp_path / "routes.xlsx"
    rows = [
        [None] * 10,
        ["Date", "Date", "Time spent in object", "Code of bin", "Day of week when service provided", "Number of weeks when service provided", "Order number of the route", "Address", "Volume of bin", "Niumber of containers"],
        ["ML  11840 no 01.01.26", "01.01.26", None, None, None, None, None, "Kopā ML:", 1.34, 2],
        [None, "01.01.26", "11.29", "04844", "xxx4xxx", "1xn", "1", "Dobeles iela 41A", 0.24, 1],
        [None, "01.01.26", "11.30", "04851", "xx3xxx7", "1x2n", "2", "Dobeles iela 48", 1.10, 1],
        ["ML  11885 no 01.01.26", "01.01.26", None, None, None, None, None, "Kopā ML:", "", 0],
        ["ML  11845 no 02.01.26", "02.01.26", None, None, None, None, None, "Kopā ML:", 0.24, 1],
        [None, "02.01.26", "08.00", "05000", "xxx4xxx", "1xn", "1", "Kungu iela 25", 0.24, 1],
    ]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)

    routes = parse_excel_routes(path)
    assert len(routes) == 2
    assert routes[0].route_code == "ML 11840"
    assert routes[0].route_date == "2026-01-01"
    assert len(routes[0].points) == 2
    assert routes[0].declared_total_containers == 2
    assert routes[1].route_code == "ML 11845"
    assert len(routes[1].points) == 1
