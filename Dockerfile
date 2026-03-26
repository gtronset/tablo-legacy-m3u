FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source and install the project itself
COPY src/ src/
COPY README.md ./
RUN uv sync --frozen --no-dev

# Production defaults
ENV DEBUG=false \
    HOST=0.0.0.0 \
    LOG_LEVEL=INFO

EXPOSE 5004

ENV PATH="/app/.venv/bin:$PATH"

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", 5004)}/discover.json')" \
    || exit 1

CMD ["python", "-m", "tablo_legacy_m3u"]
