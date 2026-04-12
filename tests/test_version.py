"""Tests for version consistency between `_version.py` and `pyproject.toml`."""

import tomllib

from pathlib import Path

from tablo_legacy_m3u._version import __version__


def test_version_matches_pyproject() -> None:
    """Ensure _version.py stays in sync with pyproject.toml."""
    pyproject = Path("pyproject.toml")
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert data["project"]["version"] == __version__
