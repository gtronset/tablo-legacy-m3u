# tablo-legacy-m3u

## _[Tablo TV] M3U & EPG generator for legacy devices._

[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

> [!WARNING]
> This is for Network-Connected Legacy Tablo units (2-port, 4-port, Dual Lite, Quad)
> and not the TV-connected "HDMI" models or Gen 4.

[Tablo TV]: https://www.tablotv.com/

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Quick Start

```bash
uv sync
uv run python -m tablo_legacy_m3u
```

Or with Docker:

```bash
docker compose up --build
```

## Endpoints

| Route                 | Description                                            |
| --------------------- | ------------------------------------------------------ |
| `/discover.json`      | HDHomeRun-style device descriptor                      |
| `/device.xml`         | Fallback to `discover.json` for older HDHomeRun device |
| `/lineup.m3u`         | M3U playlist                                           |
| `/lineup.m3u8`        | M3U8 alias                                             |
| `/lineup.xml`         | HDHomeRun XML lineup                                   |
| `/lineup.json`        | HDHomeRun JSON lineup                                  |
| `/lineup_status.json` | HDHomeRun lineup scan status                           |
| `/watch/<channel_id>` | Redirect to live stream                                |

## Contributing

See [CONTRIBUTING.md].

[CONTRIBUTING.md]: CONTRIBUTING.md

## AI Disclosure

This project is human-designed and human-maintained. All architecture decisions, code
review, and project direction are the responsibility of a person.

[GitHub Copilot] is used as a development aid and accelerator. Specifically, for
autocompletion, reasoning through bugs, and as a second opinion during code review. AI
is **not** used to independently author features or make design choices.

[GitHub Copilot]: https://github.com/features/copilot
