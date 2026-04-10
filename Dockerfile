FROM node:24-alpine AS frontend

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY vite.config.js postcss.config.js ./
COPY tablo_legacy_m3u/static/src/ tablo_legacy_m3u/static/src/
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application source
COPY tablo_legacy_m3u/ tablo_legacy_m3u/
COPY --from=frontend /app/tablo_legacy_m3u/static/dist/ tablo_legacy_m3u/static/dist/

# Production defaults
ENV ENVIRONMENT=production \
    HOST=0.0.0.0 \
    LOG_LEVEL=INFO

EXPOSE 5004

ENV PATH="/app/.venv/bin:$PATH"

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", 5004)}/health')" \
    || exit 1

CMD ["python", "-m", "tablo_legacy_m3u"]
