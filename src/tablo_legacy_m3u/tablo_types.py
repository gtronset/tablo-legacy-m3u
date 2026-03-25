"""Type definitions for Tablo API responses.

See https://github.com/jessedp/tablo-api-docs for details on the legacy Tablo API.
"""

from typing import TypedDict


class TabloModel(TypedDict):
    """Model information from the Tablo API."""

    wifi: bool
    tuners: int
    type: str
    name: str


class ServerInfo(TypedDict):
    """Server information from the Tablo API."""

    server_id: str
    name: str
    timezone: str
    deprecated: str
    version: str
    local_address: str
    setup_completed: bool
    build_number: int
    model: TabloModel
    availability: str
    cache_key: str
    product: str


class DiscoveryCpe(TypedDict):
    """A single Tablo device from the cloud discovery API.

    Customer Premises Equipment (CPE) is a telecom/networking term for devices at the
    end-user's location (routers, set-top boxes, DVRs, etc.)
    """

    serverid: str
    host: str
    name: str
    board: str
    server_version: str
    public_ip: str
    private_ip: str
    http: int
    ssl: int
    slip: int
    roku: int
    last_seen: str
    modified: str
    inserted: str


class DiscoveryResponse(TypedDict):
    """Response from the Tablo cloud discovery API."""

    success: bool
    cpes: list[DiscoveryCpe]
