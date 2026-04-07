"""Application configuration from environment variables."""

import os

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

DEFAULT_CHANNEL_REFRESH_INTERVAL: int = 86400  # 24 hours
DEFAULT_GUIDE_REFRESH_INTERVAL: int = 3600  # 1 hour
MINIMUM_REFRESH_INTERVAL: int = 60  # 1 minute

VALID_ENV_VARS: frozenset[str] = frozenset({
    "ENVIRONMENT",
    "TABLO_IP",
    "AUTODISCOVER_TABLO",
    "LOG_LEVEL",
    "HOST",
    "PORT",
    "DEVICE_NAME",
    "ENABLE_EPG",
    "CHANNEL_REFRESH_INTERVAL",
    "GUIDE_REFRESH_INTERVAL",
    "TZ",
})
VALID_ENVIRONMENTS: frozenset[str] = frozenset({"production", "development"})
VALID_LOG_LEVELS: frozenset[str] = frozenset({
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
})


@dataclass(frozen=True)
class Config:
    """Application configuration loaded from environment variables."""

    environment: str = "production"
    tz: ZoneInfo = field(default_factory=lambda: ZoneInfo("UTC"))

    @property
    def is_dev(self) -> bool:
        """Convenience property to check if environment is development."""
        return self.environment == "development"

    log_level: str = "INFO"

    # Tablo device
    tablo_ip: str = ""
    autodiscover: bool = True

    # Server
    host: str = "127.0.0.1"
    port: int = 5004

    # Device identity (for discover.json)
    device_name: str = ""

    # Feature flags
    enable_epg: bool = True

    # Caching
    channel_refresh_interval: int = DEFAULT_CHANNEL_REFRESH_INTERVAL
    guide_refresh_interval: int = DEFAULT_GUIDE_REFRESH_INTERVAL

    @property
    def cache_ttl(self) -> int:
        """Convenience property to get the cache TTL."""
        return _add_cache_buffer(
            max(self.channel_refresh_interval, self.guide_refresh_interval)
        )


def _add_cache_buffer(interval: int) -> int:
    """Add a buffer to the refresh interval to determine cache TTL."""
    return interval * 2


def _check_var_name(name: str) -> None:
    if name not in VALID_ENV_VARS:
        msg = f"Unknown config env var {name!r}; add it to VALID_ENV_VARS"
        raise ValueError(msg)


def _env(
    name: str,
    default: object,
    *,
    case: Literal["lower", "upper"] | None = None,
    choices: frozenset[str] | None = None,
) -> str:
    """Get a string-like environment variable.

    Validates and falls back to the dataclass default when necessary.
    """
    _check_var_name(name)

    value = os.environ.get(name, "").strip()
    result = value if value else str(default)
    if case == "lower":
        result = result.lower()
    elif case == "upper":
        result = result.upper()
    if choices and result not in choices:
        choices_str = ", ".join(sorted(choices))
        msg = f"Invalid value for {name}: {result!r}; expected one of: {choices_str}"
        raise ValueError(msg)

    return result


def _env_bool(name: str, default: bool) -> bool:
    """Get a boolean environment variable.

    Validates and falls back to the dataclass default when necessary.
    """
    _check_var_name(name)

    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    if raw in {"true", "1", "yes"}:
        return True
    if raw in {"false", "0", "no"}:
        return False

    msg = f"Invalid boolean for {name}: {raw!r}"
    raise ValueError(msg)


def _env_int(
    name: str,
    default: int,
    *,
    min_val: int | None = None,
    max_val: int | None = None,
) -> int:
    """Get an integer environment variable.

    Validates and falls back to the dataclass default when necessary.
    """
    _check_var_name(name)

    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        result = int(raw)
    except ValueError:
        msg = f"Invalid integer for {name}: {raw!r}"
        raise ValueError(msg) from None

    if min_val is not None and result < min_val:
        msg = f"Value for {name} too low: {result} (minimum: {min_val})"
        raise ValueError(msg)
    if max_val is not None and result > max_val:
        msg = f"Value for {name} too high: {result} (maximum: {max_val})"
        raise ValueError(msg)

    return result


def _env_tz(name: str, default: str) -> ZoneInfo:
    """Get a timezone environment variable and return a ZoneInfo object."""
    _check_var_name(name)

    raw = os.environ.get(name, "").strip()
    tz_str = raw if raw else default

    try:
        return ZoneInfo(tz_str)
    except ZoneInfoNotFoundError:
        msg = f"Invalid timezone for {name}: {tz_str!r}"
        raise ValueError(msg) from None


def load_config() -> Config:
    """Load configuration from environment variables and `.env` file."""
    env_file = Path.cwd() / ".env"
    if env_file.is_file():
        load_dotenv(env_file)

    tablo_ip = _env("TABLO_IP", Config.tablo_ip)
    autodiscover = _env_bool("AUTODISCOVER_TABLO", Config.autodiscover)

    return Config(
        environment=_env(
            "ENVIRONMENT", Config.environment, case="lower", choices=VALID_ENVIRONMENTS
        ),
        tz=_env_tz("TZ", "UTC"),
        log_level=_env(
            "LOG_LEVEL", Config.log_level, case="upper", choices=VALID_LOG_LEVELS
        ),
        tablo_ip=tablo_ip,
        autodiscover=autodiscover or not tablo_ip,
        host=_env("HOST", Config.host),
        port=_env_int("PORT", Config.port, min_val=1, max_val=65535),
        device_name=_env("DEVICE_NAME", Config.device_name),
        enable_epg=_env_bool("ENABLE_EPG", Config.enable_epg),
        channel_refresh_interval=_env_int(
            "CHANNEL_REFRESH_INTERVAL",
            Config.channel_refresh_interval,
            min_val=MINIMUM_REFRESH_INTERVAL,
        ),
        guide_refresh_interval=_env_int(
            "GUIDE_REFRESH_INTERVAL",
            Config.guide_refresh_interval,
            min_val=MINIMUM_REFRESH_INTERVAL,
        ),
    )


DEFAULT_CACHE_TTL: int = Config().cache_ttl
