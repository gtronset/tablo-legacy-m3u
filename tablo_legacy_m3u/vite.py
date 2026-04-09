"""Vite manifest integration for Flask."""

import json

from pathlib import Path
from typing import Any

from flask import Flask
from markupsafe import Markup


def init_vite(app: Flask) -> None:
    """Register a Jinja2 global that resolves Vite asset paths."""
    dist_dir = Path(app.static_folder or "") / "dist"
    manifest_path = dist_dir / ".vite" / "manifest.json"

    manifest: dict[str, dict[str, Any]] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())

    def vite_asset(entry: str) -> Markup:
        """Return HTML tags for a Vite entry point's CSS and JS assets."""
        chunk = manifest.get(entry)

        if chunk is None:
            return Markup("<!-- vite: {} not found -->").format(entry)

        tags: list[str] = [
            Markup('<link rel="stylesheet" href="/static/dist/{}">').format(css_file)
            for css_file in chunk.get("css", [])
        ]

        js_file = chunk.get("file", "")
        if js_file.endswith(".css"):
            tags.append(
                Markup('<link rel="stylesheet" href="/static/dist/{}">').format(js_file)
            )
        elif js_file:
            tags.append(
                Markup('<script defer src="/static/dist/{}"></script>').format(js_file)
            )

        return Markup("\n").join(tags)

    app.jinja_env.globals["vite_asset"] = vite_asset
