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
with [XMLTV] EPG support (requires an active guide subscription). This allows media apps
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
2. It fetches channel data and guide airings (if subscribed), then refreshes them on a
   configurable interval in the background
3. It starts an HTTP server that emulates HDHomeRun endpoints
4. Media clients connect and see it as a standard HDHomeRun tuner

## Installation

### Docker (recommended)

```bash
docker run -d \
  --name tablo-legacy-m3u \
  -p 5004:5004 \
  -e AUTODISCOVER_TABLO=true \
  ghcr.io/gtronset/tablo-legacy-m3u:latest
```

Or with Docker Compose (see also [docker-compose.yaml]):

```yaml
services:
  tablo-legacy-m3u:
    image: ghcr.io/gtronset/tablo-legacy-m3u:latest
    ports:
      - "5004:5004"
    environment:
      AUTODISCOVER_TABLO: true
    restart: unless-stopped
```

Available tags:

- `latest`: latest release
- `0.x`: general version
- `0.x.x`: specific version
- `edge`: latest from `main` (may be unstable)

[docker-compose.yaml]: docker-compose.yaml

### From source

#### Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- [Node.js](https://nodejs.org/) 24+ (for frontend build)
- A legacy Tablo device on your local network

#### Running from source

```bash
uv sync
npm ci
npm run build
uv run python -m tablo_legacy_m3u
```

The server starts on `http://localhost:5004` by default.

## Configuration

All settings are configured via environment variables:

| Variable                   | Default      | Description                                                                       |
| -------------------------- | ------------ | --------------------------------------------------------------------------------- |
| `TABLO_IP`                 | _(empty)_    | Tablo device IP; leave blank for autodiscovery. Should be a valid IP or hostname. |
| `AUTODISCOVER_TABLO`       | `true`       | Discover Tablo IP via cloud API (boolean).                                        |
| `HOST`                     | `127.0.0.1`  | Server bind address. Should be a valid IP or hostname.                            |
| `PORT`                     | `5004`       | Server port (1–65535). Defaults to standard HDHomeRun port.                       |
| `LOG_LEVEL`                | `INFO`       | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).                  |
| `ENVIRONMENT`              | `production` | `development` for Flask dev server with reloader; `production` for `waitress`.    |
| `TZ`                       | `UTC`        | IANA timezone for display timestamps (e.g. `America/Chicago`).                    |
| `DEVICE_NAME`              | _(empty)_    | Override advertised device name ("FriendlyName").                                 |
| `ENABLE_EPG`               | `true`       | Enable EPG generation (boolean).                                                  |
| `CHANNEL_REFRESH_INTERVAL` | `86400`      | How often to refresh channel data, in seconds (default: 24 hours, minimum: 60).   |
| `GUIDE_REFRESH_INTERVAL`   | `3600`       | How often to refresh guide/EPG data, in seconds (default: 1 hour, minimum: 60).   |

A `.env` file in the current working directory is also supported, useful when running
from source. See [.env.example] for available variables.

> Cache TTL is derived automatically from the longest refresh interval.

In Docker environments, `HOST` should almost always be set to `0.0.0.0`.

[.env.example]: .env.example

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
