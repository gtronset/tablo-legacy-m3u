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

| Variable                   | Default      | Description                                                                       |
| -------------------------- | ------------ | --------------------------------------------------------------------------------- |
| `TABLO_IP`                 | _(empty)_    | Tablo device IP; leave blank for autodiscovery. Should be a valid IP or hostname. |
| `AUTODISCOVER_TABLO`       | `true`       | Discover Tablo IP via cloud API (boolean).                                        |
| `HOST`                     | `127.0.0.1`  | Server bind address. Should be a valid IP or hostname.                            |
| `PORT`                     | `5004`       | Server port (1–65535). Defaults to standard HDHomeRun port.                       |
| `LOG_LEVEL`                | `INFO`       | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).                  |
| `ENVIRONMENT`              | `production` | `development` for Flask dev server with reloader; `production` for `waitress`.    |
| `DEVICE_NAME`              | _(empty)_    | Override advertised device name ("FriendlyName").                                 |
| `ENABLE_EPG`               | `true`       | Enable EPG generation (boolean).                                                  |
| `CHANNEL_REFRESH_INTERVAL` | `86400`      | How often to refresh channel data, in seconds (default: 24 hours, minimum: 60).   |
| `GUIDE_REFRESH_INTERVAL`   | `3600`       | How often to refresh guide/EPG data, in seconds (default: 1 hour, minimum: 60).   |

Copy `.env.example` to `.env` and adjust for your setup:

```bash
cp .env.example .env
```

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

## Running CI Locally

GitHub Actions workflows can be run locally with [Act]:

```bash
act -j typecheck
act -j lint
act -j test
```

Act configuration is stored in `.actrc`. See the [Act documentation] for setup instructions.

[Act]: https://github.com/nektos/act
[Act documentation]: https://github.com/nektos/act

## Pull Requests

- Branch from `main`
- Fill out the PR template
- Ensure CI passes (lint, type check, test, Docker build)
- Update [CHANGELOG.md] and [README.md] if applicable

[CHANGELOG.md]: CHANGELOG.md
[README.md]: README.md
