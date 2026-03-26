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

CMD ["uv", "run", "python", "-m", "tablo_legacy_m3u"]
