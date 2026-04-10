"""Tests for Vite manifest integration."""

import json

from collections.abc import Callable, Generator
from pathlib import Path

import pytest

from flask import Flask
from markupsafe import Markup

from tablo_legacy_m3u.vite import init_vite

type ViteAssetFn = Callable[[str], Markup]

JS_OUTPUT_FILE = "main-abc123.js"
CSS_OUTPUT_FILE = "main-abc123.css"
WEBFONT_CSS_OUTPUT_FILE = "webfonts-def456.css"
MANIFEST = {
    "main.js": {
        "file": f"assets/{JS_OUTPUT_FILE}",
        "css": [f"assets/{CSS_OUTPUT_FILE}"],
    },
    "webfonts.css": {
        "file": f"assets/{WEBFONT_CSS_OUTPUT_FILE}",
    },
}


@pytest.fixture
def vite_asset(
    tmp_path: Path,
) -> Generator[ViteAssetFn]:
    """Vite asset resolver with a fake manifest."""
    app = _create_app(tmp_path)
    with app.app_context():
        fn = app.jinja_env.globals["vite_asset"]
        assert callable(fn)
        yield fn


def _create_app(tmp_path: Path, *, debug: bool = False) -> Flask:
    """Create a minimal Flask app with a fake Vite manifest."""
    static_folder = tmp_path / "static"
    manifest_dir = static_folder / "dist" / ".vite"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.json").write_text(json.dumps(MANIFEST))

    app = Flask(__name__, static_folder=str(static_folder))
    app.debug = debug
    init_vite(app)
    return app


class TestViteAssetJS:
    """JS entry points emit a script tag and associated CSS link tags."""

    def test_emits_script_tag(self, vite_asset: ViteAssetFn) -> None:
        html = vite_asset("main.js")

        assert (
            f'<script defer src="/static/dist/assets/{JS_OUTPUT_FILE}"></script>'
            in html
        )

    def test_emits_css_link(self, vite_asset: ViteAssetFn) -> None:
        html = vite_asset("main.js")

        assert (
            f'<link rel="stylesheet" href="/static/dist/assets/{CSS_OUTPUT_FILE}">'
            in html
        )

    def test_css_before_js(self, vite_asset: ViteAssetFn) -> None:
        html = vite_asset("main.js")

        assert html.index(CSS_OUTPUT_FILE) < html.index(JS_OUTPUT_FILE)


class TestViteAssetCSS:
    """CSS-only entries emit a link tag (no script)."""

    def test_emits_link_tag(self, vite_asset: ViteAssetFn) -> None:
        html = vite_asset("webfonts.css")

        assert (
            f'<link rel="stylesheet" '
            f'href="/static/dist/assets/{WEBFONT_CSS_OUTPUT_FILE}">' in html
        )

    def test_no_script_tag(self, vite_asset: ViteAssetFn) -> None:
        html = vite_asset("webfonts.css")

        assert "<script" not in html


class TestViteAssetMissing:
    """Missing entries produce an HTML comment."""

    def test_missing_entry(self, vite_asset: ViteAssetFn) -> None:
        html = vite_asset("nope.js")

        assert "<!-- vite: nope.js not found -->" in html

    def test_missing_manifest(self, tmp_path: Path) -> None:
        static_folder = tmp_path / "static"
        static_folder.mkdir()
        app = Flask(__name__, static_folder=str(static_folder))
        init_vite(app)

        with app.app_context():
            vite_asset = app.jinja_env.globals["vite_asset"]
            assert callable(vite_asset)
            html = vite_asset("main.js")

        assert "not found" in html


class TestViteAssetReturnType:
    """Return values are Markup (safe for Jinja2)."""

    def test_returns_markup(self, vite_asset: ViteAssetFn) -> None:
        result = vite_asset("main.js")

        assert isinstance(result, Markup)


class TestViteDebugMode:
    """Debug mode reloads the manifest on each call."""

    def test_reflects_manifest_changes(self, tmp_path: Path) -> None:
        app = _create_app(tmp_path, debug=True)
        manifest_path = tmp_path / "static" / "dist" / ".vite" / "manifest.json"

        with app.app_context():
            vite_asset = app.jinja_env.globals["vite_asset"]

            assert callable(vite_asset)

            assert "main-abc123.js" in vite_asset("main.js")

            updated = {
                "main.js": {"file": "assets/main-NEW.js", "css": []},
            }
            manifest_path.write_text(json.dumps(updated))

            assert "main-NEW.js" in vite_asset("main.js")

    def test_production_caches_manifest(self, tmp_path: Path) -> None:
        app = _create_app(tmp_path, debug=False)
        manifest_path = tmp_path / "static" / "dist" / ".vite" / "manifest.json"

        with app.app_context():
            vite_asset = app.jinja_env.globals["vite_asset"]

            assert callable(vite_asset)

            assert JS_OUTPUT_FILE in vite_asset("main.js")

            manifest_path.write_text(json.dumps({}))

            # Still serves the cached version
            assert JS_OUTPUT_FILE in vite_asset("main.js")
