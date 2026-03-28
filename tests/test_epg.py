"""Tests for the XMLTV EPG generator."""

import xml.etree.ElementTree as ET

from typing import TYPE_CHECKING

import pytest

from tablo_legacy_m3u.epg import (
    _stop_time,
    _xmltv_datetime,
    generate_xmltv,
)
from tests.helpers import (
    make_channel,
    make_episode_airing,
    make_movie_airing,
    make_sport_event_airing,
)

if TYPE_CHECKING:
    from tablo_legacy_m3u.tablo_types import Airing, Channel


@pytest.fixture
def channels() -> list["Channel"]:
    """Provide a sample list of channels for testing."""
    return [
        make_channel(100, "WABC", 7, 1),
        make_channel(200, "WCBS", 2, 1, network="CBS"),
    ]


class TestXmltvDatetime:
    """Tests for `_xmltv_datetime()`."""

    def test_converts_iso_to_xmltv_format(self) -> None:
        result = _xmltv_datetime("2026-03-28T01:00Z")

        assert result == "20260328010000 +0000"

    def test_handles_midnight(self) -> None:
        result = _xmltv_datetime("2026-01-01T00:00Z")

        assert result == "20260101000000 +0000"


class TestStopTime:
    """Tests for `_stop_time()`."""

    def test_adds_duration_seconds(self) -> None:
        result = _stop_time("2026-03-28T01:00Z", 3600)

        assert result == "20260328020000 +0000"

    def test_crosses_midnight(self) -> None:
        result = _stop_time("2026-03-28T23:00Z", 7200)

        assert result == "20260329010000 +0000"


class TestGenerateXmltvChannels:
    """Tests for channel elements in `generate_xmltv()`."""

    def test_includes_channel_element(self, channels: list["Channel"]) -> None:
        xml = generate_xmltv(channels, [])
        root = ET.fromstring(xml)

        channel_els = root.findall("channel")

        assert len(channel_els) == len(channels)
        assert channel_els[0].get("id") == "7.1"
        assert channel_els[1].get("id") == "2.1"

    def test_channel_has_display_names(self, channels: list["Channel"]) -> None:
        xml = generate_xmltv(channels, [])
        root = ET.fromstring(xml)

        names = root.findall("channel/display-name")

        assert len(names) == 4  # noqa: PLR2004, Value here is more readable raw.
        assert names[0].text == "WABC"
        assert names[1].text == "7.1 WABC"
        assert names[2].text == "WCBS"
        assert names[3].text == "2.1 WCBS"


class TestGenerateXmltvStructure:
    """Tests for overall XMLTV document structure."""

    def test_root_element(self) -> None:
        xml = generate_xmltv([], [])
        root = ET.fromstring(xml)

        assert root.tag == "tv"
        assert root.get("generator-info-name") == "tablo-legacy-m3u"

    def test_xml_declaration(self) -> None:
        xml = generate_xmltv([], [])

        assert xml.startswith("<?xml version='1.0' encoding='utf-8'?>")

    def test_multiple_channels_and_airings(self, channels: list["Channel"]) -> None:
        airings: list[Airing] = [
            make_episode_airing(500, "Show A", channels[0]),
            make_movie_airing(600, "Movie B", channels[1]),
            make_sport_event_airing(700, "Sports C", channels[0]),
        ]

        xml = generate_xmltv(channels, airings)
        root = ET.fromstring(xml)

        assert len(root.findall("channel")) == len(channels)
        assert len(root.findall("programme")) == len(airings)
