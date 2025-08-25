# syntax=docker/dockerfile:1.7

#############################
# Builder (uv)
#############################
FROM ghcr.io/astral-sh/uv:python3.11-bookworm AS builder
WORKDIR /app

# Speedy layer caching: copy metadata first
COPY pyproject.toml uv.lock README.md ./
# Copy source last
COPY src ./src

# Create a local venv and install (frozen to lockfile)
# --no-editable for lean wheels, --compile-bytecode for startup gains
RUN uv sync --frozen --no-editable --compile-bytecode

#############################
# Runtime
#############################
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/app/.venv/bin:${PATH}"
WORKDIR /app

# Create non-root user
RUN useradd -m -u 10001 appuser

# Copy venv and code
COPY --from=builder /app/.venv ./.venv
COPY --from=builder /app/src ./src
COPY pyproject.toml README.md LICENSE ./

# Runtime defaults
EXPOSE 8080
USER appuser

# Environment variables for mode control
ENV OM_MODE=api
ENV OM_ARGS=""

# Entrypoint script to handle both CLI and API modes
RUN echo '#!/bin/bash' > /app/entrypoint.sh && \
    echo 'set -e' >> /app/entrypoint.sh && \
    echo '' >> /app/entrypoint.sh && \
    echo 'case "${OM_MODE}" in' >> /app/entrypoint.sh && \
    echo '    "api")' >> /app/entrypoint.sh && \
    echo '        exec uvicorn ndimensionalspectra.ontogenic_api:app --host 0.0.0.0 --port 8080' >> /app/entrypoint.sh && \
    echo '        ;;' >> /app/entrypoint.sh && \
    echo '    "cli")' >> /app/entrypoint.sh && \
    echo '        exec python -m ndimensionalspectra $OM_ARGS' >> /app/entrypoint.sh && \
    echo '        ;;' >> /app/entrypoint.sh && \
    echo '    *)' >> /app/entrypoint.sh && \
    echo '        echo "Invalid OM_MODE: ${OM_MODE}. Use '\''api'\'' or '\''cli'\''"' >> /app/entrypoint.sh && \
    echo '        exit 1' >> /app/entrypoint.sh && \
    echo '        ;;' >> /app/entrypoint.sh && \
    echo 'esac' >> /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

# Default: run API; override for CLI with: docker run -e OM_MODE=cli -e OM_ARGS="schema" ...
ENTRYPOINT ["/app/entrypoint.sh"]