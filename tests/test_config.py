"""Tests for application configuration."""

import os

from collections.abc import Generator
from pathlib import Path

import pytest

from tablo_legacy_m3u.config import (
    CONFIG_ENV_VARS,
    Config,
    _check_var_name,
    _env,
    _env_bool,
    _env_int,
    load_config,
)

DEFAULT_HOST: str = "127.0.0.1"
DEFAULT_PORT: int = 5004
DEFAULT_CACHE_TTL: int = 900
DEFAULT_LOG_LEVEL: str = "INFO"


@pytest.fixture(autouse=True)
def _isolate_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Prevent project .env from leaking into config tests.

    On cleanup, also remove any keys that load_dotenv() may have injected into
    `os.environ` that monkeypatch doesn't track.
    """
    monkeypatch.chdir(tmp_path)

    for var in CONFIG_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    yield

    for var in CONFIG_ENV_VARS:
        os.environ.pop(var, None)


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

    def test_defaults_when_no_env_vars(self) -> None:
        """Ensure no value mutations when environment variables are not set."""
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

    def test_loads_values_from_dotenv_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Values in a .env file are loaded when no env var is set."""
        monkeypatch.chdir(tmp_path)

        test_ttl: int = 42

        Path(".env").write_text(f"CACHE_TTL={test_ttl}\n", encoding="utf-8")

        config = load_config()

        assert config.cache_ttl == test_ttl

    def test_env_var_takes_precedence_over_dotenv(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """An explicit env var wins over the same key in .env."""
        monkeypatch.chdir(tmp_path)

        test_ttl: int = 600

        Path(".env").write_text("CACHE_TTL=42\n", encoding="utf-8")

        monkeypatch.setenv("CACHE_TTL", str(test_ttl))

        config = load_config()

        assert config.cache_ttl == test_ttl


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


class TestCheckVarName:
    """Tests for `_check_var_name()` validation of environment variable names."""

    def test_rejects_unknown_var(self) -> None:
        with pytest.raises(ValueError, match="Unknown config env var"):
            _check_var_name("NOT_A_REAL_VAR")

    def test_accepts_known_var(self) -> None:
        _check_var_name("CACHE_TTL")


class TestEnv:
    """Tests for `_env()` environment variable loading and validation."""

    def test_falls_back_to_default_when_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HOST", "")
        assert _env("HOST", default="fallback") == "fallback"

    def test_strips_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOST", "  myhost  ")
        assert _env("HOST", default="default") == "myhost"

    def test_whitespace_only_uses_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HOST", "   ")
        assert _env("HOST", default="fallback") == "fallback"

    def test_case_lower(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "PRODUCTION")
        assert _env("ENVIRONMENT", default="fallback", case="lower") == "production"

    def test_case_upper(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOG_LEVEL", "debug")
        assert _env("LOG_LEVEL", default="fallback", case="upper") == "DEBUG"

    def test_case_none_preserves(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEVICE_NAME", "My Tablo")
        assert _env("DEVICE_NAME", default="fallback") == "My Tablo"

    def test_rejects_unknown_var(self) -> None:
        with pytest.raises(ValueError, match="Unknown config env var"):
            _env("BOGUS", default="fallback")


class TestEnvBool:
    """Tests for `_env_bool()` boolean environment variable parsing and validation."""

    @pytest.mark.parametrize("value", ["true", "1", "yes", "TRUE", "Yes"])
    def test_truthy_values(self, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
        monkeypatch.setenv("ENABLE_EPG", value)
        assert _env_bool("ENABLE_EPG", default=False) is True

    @pytest.mark.parametrize("value", ["false", "0", "no", "FALSE", "No"])
    def test_falsy_values(self, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
        monkeypatch.setenv("ENABLE_EPG", value)
        assert _env_bool("ENABLE_EPG", default=True) is False

    def test_empty_uses_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ENABLE_EPG", raising=False)
        assert _env_bool("ENABLE_EPG", default=True) is True

    def test_invalid_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENABLE_EPG", "maybe")
        with pytest.raises(ValueError, match="Invalid boolean"):
            _env_bool("ENABLE_EPG", default=True)


class TestEnvInt:
    """Tests for `_env_int()` integer environment variable parsing and validation."""

    def test_valid_int(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PORT", "8080")
        assert _env_int("PORT", 5004) == 8080  # noqa: PLR2004, Value here is more readable raw.

    def test_empty_uses_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PORT", raising=False)
        assert _env_int("PORT", 5004) == 5004  # noqa: PLR2004, Value here is more readable raw.

    def test_invalid_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PORT", "abc")
        with pytest.raises(ValueError, match="Invalid integer"):
            _env_int("PORT", 5004)
