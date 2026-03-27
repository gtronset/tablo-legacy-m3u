"""Tests for the device discovery descriptors."""

import xml.etree.ElementTree as ET

import pytest

from tablo_legacy_m3u.config import Config
from tablo_legacy_m3u.discover import device_info, generate_device_xml
from tablo_legacy_m3u.tablo_types import ServerInfo

type JSON_TYPE = dict[str, str | int]

BASE_URL = "http://localhost:5004"


class TestDeviceInfo:
    """Tests for device_info()."""

    @pytest.fixture
    def device_info_fixture(
        self,
        request: pytest.FixtureRequest,
        server_info: ServerInfo,
    ) -> JSON_TYPE:
        """Device info with configurable app config."""
        config = getattr(request, "param", Config())

        return device_info(config, server_info, BASE_URL)

    def test_friendly_name_defaults_to_server_name(
        self, device_info_fixture: JSON_TYPE
    ) -> None:
        assert device_info_fixture["FriendlyName"] == "Test Tablo"

    @pytest.mark.parametrize(
        "device_info_fixture", [Config(device_name="My Custom Name")], indirect=True
    )
    def test_friendly_name_uses_device_name_from_config(
        self, device_info_fixture: JSON_TYPE
    ) -> None:
        assert device_info_fixture["FriendlyName"] == "My Custom Name"

    def test_device_fields_from_server_info(
        self, device_info_fixture: JSON_TYPE
    ) -> None:
        assert device_info_fixture["Manufacturer"] == "Tablo"
        assert device_info_fixture["ModelNumber"] == "TABLO_QUAD"
        assert device_info_fixture["FirmwareVersion"] == "2.2.42"
        assert device_info_fixture["DeviceID"] == "SID_TEST123"
        assert device_info_fixture["TunerCount"] == 4  # noqa PLR2004, Value here is more readable raw

    def test_device_auth_matches_friendly_name(
        self, device_info_fixture: JSON_TYPE
    ) -> None:
        assert device_info_fixture["DeviceAuth"] == device_info_fixture["FriendlyName"]

    def test_urls_use_base_url(self, device_info_fixture: JSON_TYPE) -> None:
        assert device_info_fixture["BaseURL"] == BASE_URL
        assert device_info_fixture["LineupURL"] == f"{BASE_URL}/lineup.json"


class TestGenerateDeviceXml:
    """Tests for generate_device_xml()."""

    @pytest.fixture
    def device_xml(self, server_info: ServerInfo) -> str:
        """Generated device XML with default config."""
        return generate_device_xml(Config(), server_info, BASE_URL)

    def test_is_valid_xml(self, device_xml: str) -> None:
        assert device_xml.startswith("<?xml")
        ET.fromstring(device_xml)

    def test_root_element_is_root(self, device_xml: str) -> None:
        root = ET.fromstring(device_xml)

        assert root.tag == "root"

    def test_contains_all_device_fields(self, device_xml: str) -> None:
        root = ET.fromstring(device_xml)

        assert root.findtext("FriendlyName") == "Test Tablo"
        assert root.findtext("Manufacturer") == "Tablo"
        assert root.findtext("ModelNumber") == "TABLO_QUAD"
        assert root.findtext("FirmwareVersion") == "2.2.42"
        assert root.findtext("DeviceID") == "SID_TEST123"
        assert root.findtext("BaseURL") == BASE_URL
        assert root.findtext("LineupURL") == f"{BASE_URL}/lineup.json"
        assert root.findtext("TunerCount") == "4"

    def test_ends_with_newline(self, device_xml: str) -> None:
        assert device_xml.endswith("\n")
