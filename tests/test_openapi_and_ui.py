from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_swagger_openapi_contains_documented_tags():
    schema = app.openapi()
    tag_names = {tag["name"] for tag in schema["tags"]}
    assert {"Files", "Routes", "Optimization Runs", "System"} <= tag_names
    assert "/api/files/upload" in schema["paths"]
    assert "/api/routes/{job_id}/optimization-runs" in schema["paths"]
    assert "/api/routes/{job_id}/optimize" not in schema["paths"]


def test_swagger_and_redoc_routes_are_available():
    client = TestClient(app)

    docs_response = client.get("/docs")
    assert docs_response.status_code == 200
    assert "Swagger UI" in docs_response.text
    assert "/openapi.json" in docs_response.text

    redoc_response = client.get("/redoc")
    assert redoc_response.status_code == 200
    assert "Waste Route Optimizer API" in redoc_response.text
    assert "/openapi.json" in redoc_response.text
    assert "api reference" in redoc_response.text.lower()
    assert "cdn.jsdelivr" not in redoc_response.text
    assert "redoc.standalone.js" not in redoc_response.text


def test_react_ui_is_built_and_served_from_root():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert '<div id="root"></div>' in response.text
    assert '/assets/' in response.text

    index_html = Path("app/static/index.html").read_text()
    assert '<div id="root"></div>' in index_html
    assert '/assets/' in index_html


def test_react_source_contains_api_menu_and_route_styles():
    header = Path("frontend/src/components/Header.jsx").read_text()
    route_styles = Path("frontend/src/routeStyles.js").read_text()
    map_view = Path("frontend/src/components/MapView.jsx").read_text()
    css = Path("frontend/src/styles.css").read_text()

    assert "/docs" in header
    assert "/redoc" in header
    assert "/openapi.json" in header
    assert "/health" in header
    assert "GitHub" in header
    assert "How to use this tool" in header
    assert "#ef4444" in route_styles
    assert "#22c55e" in route_styles
    assert "routeStyle('original')" in map_view
    assert "routeStyle('optimized')" in map_view
    assert "route-line-original" in css
    assert "route-line-optimized" in css
    assert "progress-track" in css
    assert "modal-backdrop" in css


def test_upload_ui_uses_summary_not_raw_json():
    source = Path("frontend/src/format.js").read_text()
    assert "renderUploadSummary" in source
    assert "Previous imports for this filename replaced" in source
    assert "JSON.stringify" not in source


def test_progress_bar_and_help_are_present_in_react_source():
    app = Path("frontend/src/App.jsx").read_text()
    upload_panel = Path("frontend/src/components/UploadPanel.jsx").read_text()
    progress_bar = Path("frontend/src/components/ProgressBar.jsx").read_text()
    header = Path("frontend/src/components/Header.jsx").read_text()

    assert "progressPercent" in app
    assert "progressStage" in app
    assert "ProgressBar" in upload_panel
    assert 'role="progressbar"' in progress_bar
    assert "https://github.com/valentininua/waste-route-optimizer" in header
    assert "How to use this tool" in header
