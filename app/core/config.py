from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://waste:waste@localhost:5439/waste_routes"
    nominatim_url: str = "https://nominatim.openstreetmap.org/search"
    nominatim_email: str | None = None
    osrm_url: str = "https://router.project-osrm.org"
    default_city: str = "Jelgava"
    default_country: str = "Latvia"
    app_user_agent: str = "waste-route-optimizer/1.16 (contact: work@valentin.in.ua)"

    allow_approximate_geocoding_fallback: bool = True
    allow_haversine_fallback: bool = True
    allow_approximate_matrix_for_large_routes: bool = True

    max_public_osrm_table_points: int = 100
    max_osrm_route_waypoints: int = 80
    max_points_to_optimize: int = 450
    max_routes_in_upload_response: int = 100

    osrm_route_timeout_seconds: float = 120.0
    osrm_table_timeout_seconds: float = 180.0
    osrm_retry_attempts: int = 2
    osrm_retry_backoff_seconds: float = 1.0

    max_upload_size_bytes: int = 25 * 1024 * 1024
    upload_cleanup_age_seconds: int = 60 * 60

    cors_enabled: bool = True
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    allow_sqlite_runtime: bool = False

    geocoding_sleep_seconds: float = 1.1
    approximate_center_lat: float = 56.6511
    approximate_center_lng: float = 23.7214

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
