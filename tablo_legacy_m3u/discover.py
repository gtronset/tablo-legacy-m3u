"""Device discovery descriptors in JSON and XML formats."""

from xml.etree.ElementTree import Element, SubElement, tostring  # noqa: S405

from tablo_legacy_m3u.config import Config
from tablo_legacy_m3u.tablo_types import ServerInfo


def device_info(
    config: Config, server_info: ServerInfo, base_url: str
) -> dict[str, str | int]:
    """Build the common device descriptor fields."""
    friendly_name = config.device_name or server_info["name"]

    return {
        "FriendlyName": friendly_name,
        "Manufacturer": "Tablo",
        "ModelNumber": server_info["model"]["name"],
        "FirmwareVersion": server_info["version"],
        "DeviceID": server_info["server_id"],
        "DeviceAuth": friendly_name,
        "BaseURL": base_url,
        "LineupURL": f"{base_url}/lineup.json",
        "TunerCount": server_info["model"]["tuners"],
    }


def generate_device_xml(config: Config, server_info: ServerInfo, base_url: str) -> str:
    """Generate an HDHomeRun-style device descriptor XML."""
    info = device_info(config, server_info, base_url)
    root = Element("root")

    for key, value in info.items():
        SubElement(root, key).text = str(value)

    return tostring(root, encoding="unicode", xml_declaration=True) + "\n"
