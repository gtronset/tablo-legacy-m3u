"""Tests for the XMLTV EPG generator."""

import xml.etree.ElementTree as ET

from typing import TYPE_CHECKING

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
    from tablo_legacy_m3u.tablo_types import Airing


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

    def test_multiple_channels_and_airings(self) -> None:
        ch1 = make_channel(100, "WABC", 7, 1)
        ch2 = make_channel(200, "WCBS", 2, 1, network="CBS")

        airings: list[Airing] = [
            make_episode_airing(500, "Show A", ch1),
            make_movie_airing(600, "Movie B", ch2),
            make_sport_event_airing(700, "Sports C", ch1),
        ]

        xml = generate_xmltv([ch1, ch2], airings)
        root = ET.fromstring(xml)

        assert len(root.findall("channel")) == 2  # noqa: PLR2004, Value here is more readable raw.
        assert len(root.findall("programme")) == 3  # noqa: PLR2004, Value here is more readable raw.
