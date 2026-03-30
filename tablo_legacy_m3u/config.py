"""Application configuration from environment variables."""

import os

from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_CACHE_TTL = 900  # 15 minutes


@dataclass(frozen=True)
class Config:
    """Application configuration loaded from environment variables."""

    environment: str = "production"

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
    cache_ttl: int = DEFAULT_CACHE_TTL


def _env(name: str, default: object) -> str:
    """Get an environment variable, falling back to the dataclass default."""
    return os.environ.get(name, str(default))


def load_config() -> Config:
    """Load configuration from environment variables."""
    load_dotenv()

    tablo_ip = _env("TABLO_IP", Config.tablo_ip)
    autodiscover = _env("AUTODISCOVER_TABLO", Config.autodiscover).lower() == "true"

    return Config(
        environment=_env("ENVIRONMENT", Config.environment).strip().lower(),
        log_level=_env("LOG_LEVEL", Config.log_level).upper(),
        tablo_ip=tablo_ip,
        autodiscover=autodiscover or not tablo_ip,
        host=_env("HOST", Config.host),
        port=int(_env("PORT", Config.port)),
        device_name=_env("DEVICE_NAME", Config.device_name),
        enable_epg=_env("ENABLE_EPG", Config.enable_epg).lower() == "true",
        cache_ttl=int(_env("CACHE_TTL", Config.cache_ttl)),
    )
