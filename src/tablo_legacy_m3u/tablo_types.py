"""Type definitions for Tablo API responses.

See https://github.com/jessedp/tablo-api-docs for details on the legacy Tablo API.
"""

from typing import TypedDict


class ChannelInfo(TypedDict):
    """Channel tuning and metadata from a channel detail object."""

    call_sign: str
    name: str
    call_sign_src: str
    major: int
    minor: int
    network: str
    flags: list[str]
    resolution: str
    favourite: bool
    tms_station_id: str
    tms_affiliate_id: str
    channel_identifier: str
    source: str
    logos: list[str]


class Channel(TypedDict):
    """A single hydrated channel from /guide/channels/<id> or /batch."""

    object_id: int
    path: str
    channel: ChannelInfo


type BatchChannelResponse = dict[str, Channel]


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


class Subscription(TypedDict):
    """A single subscription entry from /account/subscription."""

    kind: str
    state: str
    name: str
    title: str
    deprecated: str
    expires: str | None
    registration_url: str
    registration_identifier: str
    subtitle: str
    description: str
    actions: list[str]
    warnings: list[str]


class SubscriptionResponse(TypedDict):
    """Response from /account/subscription."""

    state: str
    trial: str | None
    subscriptions: list[Subscription]


class WatchResponse(TypedDict):
    """Response from a channel /watch endpoint."""

    token: str
    expires: str
    keepalive: int
    playlist_url: str
    bif_url_sd: str | None
    bif_url_hd: str | None
    canRecord: bool


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
