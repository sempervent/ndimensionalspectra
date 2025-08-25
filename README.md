# ndimensionalspectra

Multi-dimensional spectra Q&A system with CLI, API, and web interfaces for survey processing, scoring, and continuum placement.

## Architecture

```
[Browser] → NGINX :80
    ├─ /api/* → FastAPI (api:8080)
    └─ /      → NiceGUI (ui:8081)
```

## Installation

```bash
# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

## Usage

### CLI Interface

The CLI provides commands for survey operations:

```bash
# Get JSON schema for models
om schema --model all

# Generate survey JSON
om survey

# Score responses from file
om score --responses responses.json

# Score responses from stdin
echo '{"1": 5, "2": 3}' | om score --responses -

# Place on continuum
om place --responses responses.json

# Run post-survey install & glyph engine
om run --responses responses.json --passes 3
```

### API Interface

Start the API server:

```bash
# Using the module entrypoint
python -m ndimensionalspectra --api

# Using the helper script
om-api

# Using uvicorn directly
uvicorn ndimensionalspectra.ontogenic_api:app --host 0.0.0.0 --port 8080
```

#### API Endpoints

- `GET /health` - Health check
- `GET /schema/{model}` - Get JSON schema for models
- `GET /survey` - Get survey specification
- `POST /score` - Score Likert responses
- `POST /place` - Place on continuum
- `POST /run` - Run post-survey install & glyph engine

#### Example API Usage

```bash
# Get survey
curl http://localhost:8080/survey

# Score responses
curl -X POST http://localhost:8080/score \
  -H "Content-Type: application/json" \
  -d '{"responses": {"1": 5, "2": 3, "3": 4}}'

# Run post-survey
curl -X POST http://localhost:8080/run \
  -H "Content-Type: application/json" \
  -d '{"responses": {"1": 5, "2": 3, "3": 4}, "passes": 3}'
```

### Web Interface

Start the NiceGUI web interface:

```bash
# Run the web interface
python -m ndimensionalspectra.nicegui_app

# Or set custom API base for local development
API_BASE=http://127.0.0.1:8080 python -m ndimensionalspectra.nicegui_app
```

## Docker

### Build and Run with Docker Compose (Recommended)

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Build and Run Individual Containers

```bash
# Build all images with buildx bake
docker buildx bake

# Run API container
docker run -d --name api -p 8080:8080 ghcr.io/your-org/ndimensionalspectra-api:latest

# Run UI container
docker run -d --name ui -e API_BASE=http://nginx/api ghcr.io/your-org/ndimensionalspectra-ui:latest

# Run NGINX container
docker run -d --name nginx -p 80:80 --link api --link ui ghcr.io/your-org/ndimensionalspectra-nginx:latest
```

### Docker Buildx Bake

```bash
# Build all images locally
docker buildx bake

# Build specific images
docker buildx bake api
docker buildx bake ui
docker buildx bake nginx

# Push to registry
docker buildx bake push

# Build and push with custom settings
docker buildx bake push \
  --set *.platforms=linux/amd64,linux/arm64 \
  --set api.tags=ghcr.io/your-org/ndimensionalspectra-api:0.1.0 \
  --set ui.tags=ghcr.io/your-org/ndimensionalspectra-ui:0.1.0 \
  --set nginx.tags=ghcr.io/your-org/ndimensionalspectra-nginx:0.1.0
```

### Endpoints Behind NGINX

When running with Docker Compose or the unified setup:

- `GET /` → NiceGUI web interface
- `GET /api/survey` → Survey specification
- `POST /api/run` → Run survey analysis (legacy, optionally persists)
- `POST /api/runs` → Create persistent run
- `GET /api/runs` → List runs with filtering and pagination
- `GET /api/runs/{id}` → Get specific run
- `GET /api/compare` → Compare runs across users
- `GET /health` → NGINX health check

### Environment Variables

- `API_BASE` - API base URL for UI (default: `http://api:8080` in docker, `http://127.0.0.1:8080` for local)
- `HOST` - FastAPI host (default: `0.0.0.0`)
- `PORT` - FastAPI port (default: `8080`)
- `UI_PORT` - NiceGUI port (default: `8081`)
- `DATABASE_URL` - Database connection string (default: SQLite at `./data/om.db`)

### Database Persistence

The API persists runs to Postgres when `DATABASE_URL` is set, otherwise to `./data/om.db` (SQLite).

**Postgres (recommended for production):**
```bash
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db
```

**SQLite (default for development):**
```bash
# No DATABASE_URL needed - automatically uses ./data/om.db
```

### Enhanced UI Features

The NiceGUI interface now includes:

- **Survey Configuration**: User ID, notes, and passes input
- **Tabbed Interface**: Survey, Results, History, and Compare tabs
- **Interactive Plots**: 
  - 2D placement scatter plots over time
  - 3D PAD coordinate visualization
  - Stability over time line charts
  - Multi-user comparison plots
- **History Management**: View and refresh user run history
- **User Comparison**: Compare runs across multiple users

## Development

```bash
# Install development dependencies
uv sync --dev

# Run tests
pytest

# Format code
black src/

# Lint code
flake8 src/

# Build Docker images
make docker-build

# Run with Docker Compose
make docker-compose-up
```

## Health Checks & Monitoring

All services include health checks:

- **API**: `GET /health` endpoint
- **UI**: HTTP endpoint on port 8081
- **NGINX**: `GET /health` endpoint

View service status:

```bash
# Docker Compose
docker-compose ps

# Individual containers
docker ps

# Health check logs
docker-compose logs api | grep health
```

## License

See [LICENSE](LICENSE) file.
