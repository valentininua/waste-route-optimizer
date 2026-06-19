from pathlib import Path

import yaml


def test_docker_compose_has_restart_policy_and_healthchecks():
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())
    services = compose["services"]
    assert services["app"]["restart"] == "unless-stopped"
    assert services["postgres"]["restart"] == "unless-stopped"
    assert "healthcheck" in services["app"]
    assert "healthcheck" in services["postgres"]


def test_legacy_vanilla_frontend_was_removed():
    assert not Path("app/templates/index.html").exists()
    assert not Path("app/static/app.js").exists()
    assert not Path("app/static/app.css").exists()
    assert Path("frontend/src/App.jsx").exists()
    assert Path("app/static/index.html").exists()


def test_no_common_cache_or_build_trash_in_repository():
    forbidden_names = {"node_modules"}
    bad_paths = [path for path in Path(".").rglob("*") if path.name in forbidden_names]
    assert bad_paths == []


def test_api_layer_uses_repositories_for_persistence_rules():
    routes_source = Path("app/api/routes.py").read_text()
    assert "RouteJobRepository" in routes_source
    assert "OptimizationRunRepository" in routes_source
    assert "def _deduplicate_latest_jobs" not in routes_source
    assert "def _delete_existing_jobs_for_filename" not in routes_source


def test_legacy_sync_optimization_endpoint_was_removed():
    routes_source = Path("app/api/routes.py").read_text()
    assert '"/routes/{job_id}/optimize"' not in routes_source
    assert "Synchronously optimize" not in routes_source


def test_legacy_parse_excel_wrapper_was_removed():
    parser_source = Path("app/services/excel_parser.py").read_text()
    assert "def parse_excel(" not in parser_source
    tests_source = Path("tests/test_excel_parser.py").read_text()
    assert "parse_excel(" not in tests_source


def test_upload_endpoint_removes_temporary_files():
    routes_source = Path("app/api/routes.py").read_text()
    assert "finally:" in routes_source
    assert "path.unlink(missing_ok=True)" in routes_source
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())
    assert "volumes" not in compose["services"]["app"]


def test_redoc_is_no_cdn_api_reference():
    main_source = Path("app/main.py").read_text()
    reference_source = Path("app/core/api_reference.py").read_text()
    assert "_render_api_reference_html" not in main_source
    assert "_operation_badges" not in main_source
    assert "redoc_url=None" in main_source
    assert "render_api_reference_html" in main_source
    assert "cdn.jsdelivr" not in reference_source
    assert "redoc.standalone.js" not in reference_source


def test_route_repository_uses_bulk_delete_not_orm_delete_loop():
    repository_source = Path("app/repositories/route_job_repository.py").read_text()
    assert ".delete(synchronize_session=False)" in repository_source
    assert "for job in jobs:" not in repository_source
    assert "self.db.delete(job)" not in repository_source


def test_route_processor_bulk_loads_geocode_cache_before_external_calls():
    processor_source = Path("app/services/route_processor.py").read_text()
    assert "def _load_geocode_cache_for_points" in processor_source
    assert "GeocodeCache.query.in_(cache_keys)" in processor_source
    assert "geocoded_by_address = _load_geocode_cache_for_points(db, pending)" in processor_source
