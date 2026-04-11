"""Tests for version check utilities."""

import responses

from tablo_legacy_m3u.version_check import (
    RELEASES_URL,
    VersionChecker,
    check_latest_version,
    is_update_available,
)


class TestCheckLatestVersion:
    """Fetching the latest version from GitHub."""

    @responses.activate
    def test_returns_version_from_tag(self) -> None:
        responses.add(
            responses.GET,
            RELEASES_URL,
            json={"tag_name": "v2.0.0"},
            status=200,
        )

        assert check_latest_version() == "2.0.0"

    @responses.activate
    def test_strips_v_prefix(self) -> None:
        responses.add(
            responses.GET,
            RELEASES_URL,
            json={"tag_name": "v1.5.3"},
            status=200,
        )

        assert check_latest_version() == "1.5.3"

    @responses.activate
    def test_returns_none_on_http_error(self) -> None:
        responses.add(
            responses.GET,
            RELEASES_URL,
            status=500,
        )

        assert check_latest_version() is None

    @responses.activate
    def test_returns_none_on_network_error(self) -> None:
        responses.add(
            responses.GET,
            RELEASES_URL,
            body=ConnectionError("network down"),
        )

        assert check_latest_version() is None

    @responses.activate
    def test_returns_empty_string_when_no_tag(self) -> None:
        responses.add(
            responses.GET,
            RELEASES_URL,
            json={},
            status=200,
        )

        assert not check_latest_version()


class TestIsUpdateAvailable:
    """Comparing versions to detect updates."""

    CURRENT_VERSION = "1.1.0"

    def test_newer_version_available(self) -> None:
        assert (
            is_update_available(current=self.CURRENT_VERSION, latest="99.0.0") is True
        )

    def test_same_version(self) -> None:
        assert (
            is_update_available(
                current=self.CURRENT_VERSION, latest=self.CURRENT_VERSION
            )
            is False
        )

    def test_older_version(self) -> None:
        assert (
            is_update_available(current=self.CURRENT_VERSION, latest="1.0.0") is False
        )

    def test_none_returns_false(self) -> None:
        assert is_update_available(current=self.CURRENT_VERSION, latest=None) is False

    def test_invalid_version_returns_false(self) -> None:
        assert (
            is_update_available(current=self.CURRENT_VERSION, latest="not-a-version")
            is False
        )

    def test_empty_string_returns_false(self) -> None:
        assert is_update_available(current=self.CURRENT_VERSION, latest="") is False


class TestVersionChecker:
    """Cached version check with background refresh."""

    @responses.activate
    def test_returns_none_on_first_call(self) -> None:
        responses.add(
            responses.GET,
            RELEASES_URL,
            json={"tag_name": "v99.0.0"},
            status=200,
        )

        checker = VersionChecker()
        assert checker.get_latest_version() is None

    @responses.activate
    def test_returns_cached_version_after_refresh(self) -> None:
        """Triggers the background fetch and waits before checking the cached value."""
        responses.add(
            responses.GET,
            RELEASES_URL,
            json={"tag_name": "v99.0.0"},
            status=200,
        )

        checker = VersionChecker()
        checker.get_latest_version()

        checker._executor.submit(lambda: None).result(timeout=5)

        assert checker.get_latest_version() == "99.0.0"

    @responses.activate
    def test_no_cache_when_no_update(self) -> None:
        responses.add(
            responses.GET,
            RELEASES_URL,
            json={"tag_name": "v0.1.0"},
            status=200,
        )

        checker = VersionChecker()
        checker.get_latest_version()

        checker._executor.submit(lambda: None).result(timeout=5)

        assert checker.get_latest_version() is None

    @responses.activate
    def test_no_cache_on_failure(self) -> None:
        responses.add(
            responses.GET,
            RELEASES_URL,
            status=500,
        )

        checker = VersionChecker()
        checker.get_latest_version()

        checker._executor.submit(lambda: None).result(timeout=5)

        assert checker.get_latest_version() is None

    def test_disabled_returns_none(self) -> None:
        checker = VersionChecker(enabled=False)

        assert checker.get_latest_version() is None
