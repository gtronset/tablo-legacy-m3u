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
    """A single hydrated channel from `/guide/channels/<id>` or `/batch`."""

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


class TunerStatus(TypedDict):
    """A single tuner from `/server/tuners`."""

    in_use: bool
    channel: str | None
    recording: str | None
    channel_identifier: str | None


class HarddriveInfo(TypedDict):
    """A storage device from `/server/harddrives`."""

    name: str
    connected: bool
    format_state: str
    busy_state: str
    kind: str
    size: int
    usage: int
    free: int
    error: str | None


class GuideStatus(TypedDict):
    """Guide data status from `/guide/status`."""

    guide_seeded: bool
    last_update: str
    limit: str
    download_progress: int | None


class Subscription(TypedDict):
    """A single subscription entry from `/account/subscription`."""

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
    """Response from `/account/subscription`."""

    state: str
    trial: str | None
    subscriptions: list[Subscription]


class WatchResponse(TypedDict):
    """Response from a channel `/watch` endpoint."""

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


class AiringDetails(TypedDict):
    """Common airing schedule block shared by all guide airing types."""

    datetime: str
    duration: int
    channel_path: str
    channel: Channel
    show_title: str


class EpisodeInfo(TypedDict):
    """Episode metadata from a series episode airing."""

    title: str | None
    description: str
    number: int
    season_number: int
    orig_air_date: str


class EpisodeAiring(TypedDict):
    """A hydrated series episode from `/guide/series/episodes/<id>`."""

    path: str
    object_id: int
    series_path: str
    season_path: str
    episode: EpisodeInfo
    airing_details: AiringDetails
    qualifiers: list[str]


class MovieAiringInfo(TypedDict):
    """Movie-specific metadata from a movie airing."""

    release_year: int
    film_rating: str | None
    quality_rating: int | None


class MovieAiring(TypedDict):
    """A hydrated movie airing from `/guide/movies/airings/<id>`."""

    path: str
    object_id: int
    movie_path: str
    movie_airing: MovieAiringInfo
    airing_details: AiringDetails
    qualifiers: list[str]


class SportTeam(TypedDict):
    """A team entry in a sport event."""

    name: str
    team_id: int


class SportEventInfo(TypedDict):
    """Sport event metadata from a sport event airing."""

    title: str
    description: str
    season: str | None
    season_type: str | None
    venue: str | None
    teams: list[SportTeam]
    home_team_id: int | None


class SportEventAiring(TypedDict):
    """A hydrated sport event from `/guide/sports/events/<id>`."""

    path: str
    object_id: int
    sport_path: str
    event: SportEventInfo
    airing_details: AiringDetails
    qualifiers: list[str]


type Airing = EpisodeAiring | MovieAiring | SportEventAiring
