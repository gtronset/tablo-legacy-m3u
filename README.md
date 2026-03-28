# tablo-legacy-m3u

## _[Tablo TV] M3U & EPG generator for legacy devices._

[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

> [!WARNING]
> This is for Network-Connected Legacy Tablo units (2-port, 4-port, Dual Lite, Quad)
> and not the TV-connected "HDMI" models or Gen 4.

[Tablo TV]: https://www.tablotv.com/

## What It Does

`tablo-legacy-m3u` connects to a legacy Tablo device on your local network, reads its
channel lineup and guide data, and serves it as an [HDHomeRun]-compatible HTTP server
with [XMLTV] EPG support (if "guide" subscription is available). This allows media apps
like [Plex], [Jellyfin], and [Emby] to discover and stream live TV channels from your
Tablo as if it were an HDHomeRun tuner. This also allows IPTV helpers/proxies such as
[Dispatcharr] and [Threadfin] to aggregate Tablo channels.

[HDHomeRun]: https://www.silicondust.com/
[XMLTV]: https://wiki.xmltv.org/index.php/XMLTVFormat
[Plex]: https://www.plex.tv/
[Emby]: https://emby.media/
[Jellyfin]: https://jellyfin.org/
[Dispatcharr]: https://github.com/dispatcharr/dispatcharr
[Threadfin]: https://github.com/Threadfin/Threadfin

## Why

Tablo's [legacy transition] encourages users to adopt 4th Generation apps, which
currently lack support for remote/out-of-home streaming ([Tablo Connect]). While legacy
apps continue to work, users need another option if they want the best of both worlds
(new apps but still be able to stream remotely).

`tablo-legacy-m3u` makes your Tablo's live channels accessible to any
HDHomeRun-compatible app or IPTV client, including those that support remote access
natively (e.g., Plex, Jellyfin). This allows remote streaming that doesn't depend on
Tablo Connect or legacy app availability.

> [!NOTE]
> This project relies on the Tablo's local HTTP API. If Tablo changes or removes this
> API in a future firmware update, this tool may stop working.

[legacy transition]: https://www.tablotv.com/legacy-transition/
[Tablo Connect]: https://www.tablotv.com/tablo-connect/

## How It Works

1. On startup, the app discovers your Tablo device (via cloud API or manual IP)
2. It queries the Tablo for device info, channel data, and guide airings (if subscribed)
3. It starts an HTTP server that emulates HDHomeRun endpoints
4. Media clients connect and see it as a standard HDHomeRun tuner

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- A legacy Tablo device on your local network

## Quick Start

```bash
uv sync
uv run python -m tablo_legacy_m3u
```

Or with Docker:

```bash
docker compose up --build
```

The server starts on `http://localhost:5004` by default.

## Configuration

All settings are configured via environment variables:

| Variable             | Default     | Description                                    |
| -------------------- | ----------- | ---------------------------------------------- |
| `TABLO_IP`           | _(empty)_   | Tablo device IP; leave blank for autodiscovery |
| `AUTODISCOVER_TABLO` | `true`      | Discover Tablo IP via cloud API                |
| `HOST`               | `127.0.0.1` | Server bind address                            |
| `PORT`               | `5004`      | Server port                                    |
| `LOG_LEVEL`          | `DEBUG`     | Logging level                                  |
| `DEBUG`              | `true`      | Enable Flask debug mode and reloader           |
| `DEVICE_NAME`        | _(empty)_   | Override advertised device name (FriendlyName) |
| `ENABLE_EPG`*        | `true`      | Enable EPG generation                          |
| `CACHE_TTL`*         | `60`        | Cache TTL in seconds                           |

_*Not yet implemented and/or currently have no effect._

## Client Setup

Add this app as an HDHomeRun tuner in your media server:

- __Plex__: Settings → Live TV & DVR → Set Up → Enter `http://<host>:5004`
- __Jellyfin__: Live TV → Add Tuner Device → HDHomeRun → `http://<host>:5004`
- __Emby__: Live TV → Add Tuner Device → HDHomeRun → `http://<host>:5004`
- Any app that supports HDHomeRun tuners or M3U playlists should work (Dispatcharr,
  Threadfin, etc.). For M3U-only clients, point to `http://<host>:5004/lineup.m3u`.
- For EPG/guide data, point your client to `http://<host>:5004/xmltv.xml`.

## Endpoints

| Route                 | Description                                             |
| --------------------- | ------------------------------------------------------- |
| `/discover.json`      | HDHomeRun-style device descriptor                       |
| `/device.xml`         | HDHomeRun-style device descriptor (XML)                 |
| `/lineup.m3u`         | M3U playlist                                            |
| `/lineup.m3u8`        | M3U8 alias                                              |
| `/lineup.xml`         | HDHomeRun XML lineup                                    |
| `/lineup.json`        | HDHomeRun JSON lineup                                   |
| `/lineup_status.json` | HDHomeRun lineup scan status                            |
| `/watch/<channel_id>` | Redirect to live stream                                 |
| `/xmltv.xml`          | XMLTV EPG guide data (requires guide subscription)      |

## Contributing

See [CONTRIBUTING.md].

[CONTRIBUTING.md]: CONTRIBUTING.md

## AI Disclosure

This project is human-designed and human-maintained. All architecture decisions, code
review, and project direction are the responsibility of a person.

[GitHub Copilot] is used as a development aid and accelerator. Specifically, for
autocompletion, reasoning through bugs, and as a second opinion during code review. AI
is __not__ used to independently author features or make design choices.

[GitHub Copilot]: https://github.com/features/copilot
