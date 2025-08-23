# ndimensionalspectra

Multi-dimensional spectra Q&A system with CLI and API interfaces for survey processing, scoring, and continuum placement.

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

## Docker

### Build and Run

```bash
# Build the image
docker build -t ndimensionalspectra .

# Run API mode (default)
docker run -p 8080:8080 ndimensionalspectra

# Run CLI mode
docker run -e OM_MODE=cli -e OM_ARGS="schema" ndimensionalspectra

# Run CLI with specific command
docker run -e OM_MODE=cli -e OM_ARGS="survey" ndimensionalspectra
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8080:8080"
    environment:
      - OM_MODE=api
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

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
```

## License

See [LICENSE](LICENSE) file.
