# Contributing

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- [prek](https://github.com/jdx/prek) (pre-commit hook runner)
- [Docker](https://www.docker.com/) (optional)

## Setup

```bash
git clone git@github.com:gtronset/tablo-legacy-m3u.git
cd tablo-legacy-m3u
uv sync
prek install
```

## Running Locally

```bash
uv run python -m tablo_legacy_m3u
```

Or with Docker:

```bash
docker compose -f docker-compose.dev.yaml up --build
```

## Environment Variables

| Variable             | Default     | Description                                    |
| -------------------- | ----------- | ---------------------------------------------- |
| `TABLO_IP`           | _(empty)_   | Tablo device IP; leave blank for autodiscovery |
| `AUTODISCOVER_TABLO` | `true`      | Discover Tablo IP via cloud API                |
| `HOST`               | `127.0.0.1` | Server bind address                            |
| `PORT`               | `5004`      | Server port                                    |
| `LOG_LEVEL`          | `DEBUG`     | Logging level                                  |
| `DEBUG`              | `true`      | Enable Flask debug mode and reloader           |
| `DEVICE_NAME`        | _(empty)_   | Override advertised device name (FriendlyName) |
| `ENABLE_EPG`         | `true`      | Enable EPG generation                          |
| `CACHE_TTL`          | `60`        | Cache TTL in seconds                           |

## Checks

Run all checks before submitting a PR:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
```

Or let pre-commit handle lint, format, and type checking on each commit:

```bash
prek run
```

## Pull Requests

- Branch from `main`
- Fill out the PR template
- Ensure CI passes (lint, type check, test, Docker build)
- Update [CHANGELOG.md] and [README.md] if applicable

[CHANGELOG.md]: CHANGELOG.md
[README.md]: README.md
