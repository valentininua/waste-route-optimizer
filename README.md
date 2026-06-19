# Waste Route Optimizer

Production-oriented technical-test implementation for waste collection route optimization.

The system imports a multi-route Excel file, splits it into individual ML route blocks, geocodes collection-point addresses, calculates road-based route metrics, optimizes a selected route, compares original vs optimized distance/time, and exposes the result through a REST API and a React + OpenStreetMap web UI.

## Technical-task coverage

| Requirement | Status |
|---|---:|
| Read and process the provided Excel file | Done |
| Geocode addresses if coordinates are missing | Done |
| Calculate distances between collection points using roads | Done via OSRM; demo fallback is explicit |
| Generate an optimized route | Done |
| Compare original route with optimized route | Done |
| Expose results through REST API or CLI | Done through REST API + Swagger/OpenAPI |
| Service-day code parsing such as `xx3xxx7`, `xxx4xxx` | Done |
| Frequency parsing such as `1xn`, `1x2n` | Done |

## Stack

- Python 3.12
- FastAPI
- PostgreSQL 16
- SQLAlchemy 2
- Pydantic DTOs / response models
- Resource/serializer layer
- Repository layer for persistence rules
- FastAPI BackgroundTasks for optimization runs
- REST polling for progress tracking, no WebSocket
- Pandas / OpenPyXL
- OpenStreetMap Nominatim geocoding
- OSRM road-based routing
- React + Vite frontend
- Leaflet + OpenStreetMap map visualization
- Docker / Docker Compose
- Alembic migration skeleton
- Pytest

## Architecture notes

The code is split by responsibility:

```text
app/api             FastAPI controllers only
app/dto             API schemas and response contracts
app/resources       ORM model -> API payload serialization
app/repositories    database access and persistence rules
app/models          SQLAlchemy ORM models
app/services        domain/application logic
app/tasks           background task entry points
frontend            React UI that consumes the REST API
```

This keeps controllers thin and improves SOLID alignment:

- Single Responsibility: parsing, geocoding, routing, optimization, persistence and serialization are separated.
- Open/Closed: routing/geocoding fallback behavior is controlled through settings without changing API handlers.
- Dependency Inversion direction: API depends on repositories/services, not raw business logic embedded in handlers.
- Interface Segregation at project scale: DTOs/resources are split by use case instead of one large schema file.

## Quick start locally

```bash
cp .env.example .env
docker compose up --build
```

Open:

```text
http://localhost:8000
```

API docs:

```text
Swagger UI:     http://localhost:8000/docs
API Reference:  http://localhost:8000/redoc

`/redoc` is a no-CDN API Reference generated from the OpenAPI schema, so it does not depend on external ReDoc JavaScript availability.
OpenAPI JSON:   http://localhost:8000/openapi.json
Health:         http://localhost:8000/health
GitHub link:    available in the top menu
Help:           available in the top menu
```

## Manual test flow

1. Open `http://localhost:8000`.
2. Upload `Routes 01.01.2026-31.03.2026 tech test.xlsx`.
3. Select one route, for example `2026-01-01 | ML 11840`.
4. Click **Load Selected Route**.
5. Click **Optimize Selected Route**.
6. The React UI starts a background optimization run and polls `/api/optimization-runs/{run_id}`. A visible progress bar shows the current stage and percentage.
7. Verify:
   - status becomes `optimized`;
   - metrics are not null;
   - original route is red dashed;
   - optimized route is green;
   - collection points have original and optimized order;
   - map contains OpenStreetMap tiles and route lines.


## Upload-file cleanup

Uploaded Excel files are saved only as temporary files while the backend parses them.
After routes and collection points are persisted to PostgreSQL, the temporary upload file is removed in a `finally` block.
This prevents the `uploads/` directory from growing during repeated imports.

## Backend cleanup and performance notes

The API exposes only the background optimization flow; the old synchronous optimization endpoint was removed to avoid long blocking HTTP requests.

Repeated imports of the same file are replaced using bulk deletion of dependent `collection_points`, `optimization_runs`, and `route_jobs` rows. This avoids N separate ORM delete calls for large Excel files.

During optimization, existing geocoding cache entries are loaded in one bulk query before any external Nominatim calls are attempted. This reduces PostgreSQL round-trips for routes with hundreds of points.

The 2-opt optimizer avoids rebuilding and fully recalculating a candidate route on every inner-loop trial. For asymmetric OSRM-style matrices, it recalculates only the changed reversed segment and boundary edges.

## Automated tests

Inside Docker:

```bash
docker compose run --rm app pytest -q
```

Locally:

```bash
pip install -r requirements.txt
pytest -q
```

Expected for this package:

```text
40 passed
```

## React frontend development

Production Docker uses the prebuilt React assets committed under `app/static`. This avoids network-dependent `npm install` during server deployment. The React source remains in `frontend/` for development.

If you change the React source, rebuild assets locally and copy `frontend/dist` into `app/static` before packaging/deployment.

For local frontend development:

```bash
cd frontend
npm install --no-audit --no-fund
npm run dev
```

For local production build:

```bash
cd frontend
npm install --no-audit --no-fund
npm run build
rm -rf ../app/static/*
cp -a dist/* ../app/static/
```

## Important fallback modes

The public Nominatim and public OSRM services are rate-limited. For a demo/test task, `.env.example` enables safe fallbacks so the app does not break when public services return 403/429 or reject large matrices.

For strict production validation, use self-hosted Nominatim/OSRM and disable approximate fallbacks:

```env
ALLOW_APPROXIMATE_GEOCODING_FALLBACK=false
ALLOW_HAVERSINE_FALLBACK=false
ALLOW_APPROXIMATE_MATRIX_FOR_LARGE_ROUTES=false
OSRM_URL=http://your-osrm-host:5000
NOMINATIM_URL=http://your-nominatim-host/search
```

`metrics_source` explains what was used, for example:

```text
osrm_road; optimizer_matrix=haversine_matrix_large_route
```

Meaning: final route metrics were calculated with OSRM road routing, while the optimizer matrix used an approximate matrix because the route was too large for the public OSRM table endpoint.

## Server deployment

Recommended minimal deployment on a VPS:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker

mkdir -p /opt/waste-route-optimizer
cd /opt/waste-route-optimizer
unzip waste-route-optimizer-final-fixed-v16.zip
cd waste-route-optimizer
cp .env.example .env
nano .env

docker compose up -d --build
```

The compose file includes:

```yaml
restart: unless-stopped
```

for both `app` and `postgres`. That means containers automatically restart if the process crashes or the server reboots, unless you stopped them manually.

Useful commands:

```bash
docker compose ps
docker compose logs -f app
docker compose logs -f postgres
docker compose restart app
docker compose pull
docker compose up -d --build
```

Clean reset during testing:

```bash
docker compose down -v
docker compose up -d --build
```

Do not use `down -v` in production unless you intentionally want to delete PostgreSQL data.

## Reverse proxy recommendation

For public deployment, put Nginx, Caddy, or Traefik in front of the app and keep the app bound to the server/private network.

Example Caddyfile:

```text
your-domain.com {
    reverse_proxy 127.0.0.1:8000
}
```

Then run Caddy as a system service or another Docker container. For a real production deployment also add HTTPS, backups for the PostgreSQL volume, log rotation, and preferably self-hosted OSRM/Nominatim.

## Main API endpoints

```http
POST /api/files/upload
GET  /api/routes
GET  /api/routes/{job_id}
POST /api/routes/{job_id}/optimization-runs
GET  /api/optimization-runs/{run_id}
GET  /api/routes/{job_id}/geometry/original
GET  /api/routes/{job_id}/geometry/optimized
GET  /api/stats
```

## Notes for interview explanation

This is a strong technical-test solution, not a fully hardened municipal production platform. For production I would add:

- self-hosted OSRM and Nominatim;
- persistent queue worker instead of FastAPI BackgroundTasks;
- backups and monitoring;
- authentication/authorization;
- more advanced VRP constraints: vehicle capacity, working time, time windows, multiple trucks;
- CI/CD pipeline.


## Docker build note

The Dockerfile intentionally does not run `npm ci` during production image build. The project ships with prebuilt React static assets in `app/static`, and the FastAPI container serves them directly. This makes deployment deterministic on VPS environments where npm registry access can be slow, blocked, or unstable.

If the frontend source changes, rebuild it before deployment:

```bash
cd frontend
npm install --no-audit --no-fund
npm run build
rm -rf ../app/static/*
cp -a dist/* ../app/static/
```


## UI additions

The top menu includes:

- **GitHub** — link to the source repository location: `https://github.com/valentininua/waste-route-optimizer`;
- **Help** — opens a short usage popup directly in the UI;
- **Swagger UI**, **API Reference**, **OpenAPI JSON**, and **Health** links.

Optimization progress is displayed with a visible progress bar. Upload/parsing operations show an indeterminate bar, while optimization runs show the percentage reported by the REST polling endpoint.
