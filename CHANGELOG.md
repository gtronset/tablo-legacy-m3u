<!-- markdownlint-configure-file { "MD024": { "siblings_only": true } } -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog], and this project adheres to [Semantic Versioning].

[Keep a Changelog]: https://keepachangelog.com/en/1.1.0/
[Semantic Versioning]: https://semver.org/spec/v2.0.0.html

## [Unreleased]

### Added

- Add Brotli & gzip response compression <https://github.com/gtronset/tablo-legacy-m3u/pull/32>

### Changed

- Refresh tuner status on watch with short-TTL coalesced cache <https://github.com/gtronset/tablo-legacy-m3u/pull/30>
- Add HTMX with SSE to make status page live <https://github.com/gtronset/tablo-legacy-m3u/pull/31>

## [1.1.0] - 2026-04-07

### Added

- Add background scheduled refresh for channel and guide data <https://github.com/gtronset/tablo-legacy-m3u/pull/22>
- Add dedicated/fallback `favicon.ico` <https://github.com/gtronset/tablo-legacy-m3u/pull/23>

### Changed

- Handle Tablo server_busy responses with retry hints <https://github.com/gtronset/tablo-legacy-m3u/pull/25>
- Defer app initialization to accommodate Tablo being temporarily unavailable during
  startup <https://github.com/gtronset/tablo-legacy-m3u/pull/26>
- Add scheduled device probe, TZ ENV, and improve status page <https://github.com/gtronset/tablo-legacy-m3u/pull/27>
- Add cache coalescing and sequential startup warming <https://github.com/gtronset/tablo-legacy-m3u/pull/28>

## [1.0.0] - 2026-03-30

### Added

- Add Initial CI Workflows <https://github.com/gtronset/tablo-legacy-m3u/pull/2>
- Initial Docker Setup and CONTRIBUTING <https://github.com/gtronset/tablo-legacy-m3u/pull/3>
- Flatten package layout and adopt app factory pattern <https://github.com/gtronset/tablo-legacy-m3u/pull/4>
- Refactor lineup generation, include XML and M3U8 based lineups <https://github.com/gtronset/tablo-legacy-m3u/pull/5>
- Add `device.xml` endpoint and extract discover module <https://github.com/gtronset/tablo-legacy-m3u/pull/6>
- Improve README <https://github.com/gtronset/tablo-legacy-m3u/pull/7>
- Add status page at root and djlint linting <https://github.com/gtronset/tablo-legacy-m3u/pull/8>
- Add XMLTV EPG endpoint <https://github.com/gtronset/tablo-legacy-m3u/pull/9>
- Add `tvg-id` to EPG <https://github.com/gtronset/tablo-legacy-m3u/pull/10>
- Add simple cache for multi-batch requests via `cachetools.cachedmethod` <https://github.com/gtronset/tablo-legacy-m3u/pull/11>
- Add `act` for local GitHub Actions running <https://github.com/gtronset/tablo-legacy-m3u/pull/12>
- Add "release" action for docker builds <https://github.com/gtronset/tablo-legacy-m3u/pull/13>
- Use connection pool for Tablo Client with retries <https://github.com/gtronset/tablo-legacy-m3u/pull/16>
- Add `waitress` WSGI server for non-dev environments <https://github.com/gtronset/tablo-legacy-m3u/pull/17>
- Add access logs to `waitress` <https://github.com/gtronset/tablo-legacy-m3u/pull/18>
- Convert `DEBUG` ENV to `ENVIRONMENT` and Load `.env` when present <https://github.com/gtronset/tablo-legacy-m3u/pull/19>
- Add config validation <https://github.com/gtronset/tablo-legacy-m3u/pull/20>

## [0.1.0] - 2026-03-26

### Added

- Implement initial M3U-exporting app <https://github.com/gtronset/tablo-legacy-m3u/pull/1>

<!-- Release Links -->

[unreleased]: https://github.com/gtronset/tablo-legacy-m3u/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/gtronset/tablo-legacy-m3u/releases/tag/v1.1.0
[1.0.0]: https://github.com/gtronset/tablo-legacy-m3u/releases/tag/v1.0.0
[0.1.0]: https://github.com/gtronset/tablo-legacy-m3u/releases/tag/v0.1.0
