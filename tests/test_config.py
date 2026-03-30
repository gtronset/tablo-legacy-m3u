"""Tests for application configuration."""

import pytest

from tablo_legacy_m3u.config import Config, load_config

DEFAULT_HOST: str = "127.0.0.1"
DEFAULT_PORT: int = 5004
DEFAULT_CACHE_TTL: int = 900
DEFAULT_LOG_LEVEL: str = "INFO"


class TestConfigDefaults:
    """Tests for `Config` dataclass defaults."""

    def test_default_values(self) -> None:
        config = Config()

        assert config.environment == "production"
        assert config.is_dev is False
        assert config.log_level == DEFAULT_LOG_LEVEL
        assert not config.tablo_ip
        assert config.autodiscover is True
        assert config.host == DEFAULT_HOST
        assert config.port == DEFAULT_PORT
        assert not config.device_name
        assert config.enable_epg is True
        assert config.cache_ttl == DEFAULT_CACHE_TTL

    def test_config_is_frozen_and_immutable(self) -> None:
        config = Config()

        with pytest.raises(AttributeError):
            config.port = 9999  # type: ignore[misc]


class TestLoadConfig:
    """Tests for `load_config()` environment variable loading."""

    def test_defaults_when_no_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure no value mutations when environment variables are not set."""
        monkeypatch.delenv("DEBUG", raising=False)
        monkeypatch.delenv("TABLO_IP", raising=False)
        monkeypatch.delenv("AUTODISCOVER_TABLO", raising=False)
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        monkeypatch.delenv("HOST", raising=False)
        monkeypatch.delenv("PORT", raising=False)
        monkeypatch.delenv("DEVICE_NAME", raising=False)
        monkeypatch.delenv("ENABLE_EPG", raising=False)
        monkeypatch.delenv("CACHE_TTL", raising=False)

        config = load_config()

        assert config.log_level == DEFAULT_LOG_LEVEL
        assert config.host == DEFAULT_HOST
        assert config.port == DEFAULT_PORT
        assert config.enable_epg is True
        assert config.cache_ttl == DEFAULT_CACHE_TTL

    def test_env_vars_override_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        new_host: str = "localhost"
        new_port: int = 8080
        new_cache_ttl: int = 120
        new_tablo_ip: str = "192.168.1.50"
        new_device_name: str = "Living Room Tablo"

        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LOG_LEVEL", "warning")
        monkeypatch.setenv("TABLO_IP", new_tablo_ip)
        monkeypatch.setenv("AUTODISCOVER_TABLO", "false")
        monkeypatch.setenv("HOST", new_host)
        monkeypatch.setenv("PORT", str(new_port))
        monkeypatch.setenv("DEVICE_NAME", new_device_name)
        monkeypatch.setenv("ENABLE_EPG", "false")
        monkeypatch.setenv("CACHE_TTL", str(new_cache_ttl))

        config = load_config()

        assert config.environment == "development"
        assert config.is_dev is True
        assert config.log_level == "WARNING"
        assert config.tablo_ip == new_tablo_ip
        assert config.autodiscover is False
        assert config.host == new_host
        assert config.port == new_port
        assert config.device_name == new_device_name
        assert config.enable_epg is False
        assert config.cache_ttl == new_cache_ttl

    def test_log_level_uppercased(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOG_LEVEL", "info")

        config = load_config()

        assert config.log_level == "INFO"


class TestAutodiscoverLogic:
    """Tests for the autodiscover resolution logic."""

    def test_autodiscover_true_when_no_ip(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("TABLO_IP", raising=False)
        monkeypatch.delenv("AUTODISCOVER_TABLO", raising=False)

        config = load_config()

        assert config.autodiscover is True
        assert not config.tablo_ip

    def test_autodiscover_forced_true_when_ip_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AUTODISCOVER_TABLO", "false")
        monkeypatch.delenv("TABLO_IP", raising=False)

        config = load_config()

        assert config.autodiscover is True

    def test_autodiscover_false_when_ip_provided(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        new_tablo_ip: str = "10.0.0.123"

        monkeypatch.setenv("TABLO_IP", new_tablo_ip)
        monkeypatch.setenv("AUTODISCOVER_TABLO", "false")

        config = load_config()

        assert config.autodiscover is False
        assert config.tablo_ip == new_tablo_ip

    def test_autodiscover_true_overrides_manual_ip(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        new_tablo_ip: str = "10.0.0.123"

        monkeypatch.setenv("TABLO_IP", new_tablo_ip)
        monkeypatch.setenv("AUTODISCOVER_TABLO", "true")

        config = load_config()

        assert config.autodiscover is True
        assert config.tablo_ip == new_tablo_ip
