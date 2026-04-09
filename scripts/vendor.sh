#!/usr/bin/env bash
set -euo pipefail

VENDOR_DIR="tablo_legacy_m3u/static/vendor"
mkdir -p "$VENDOR_DIR"

cp node_modules/htmx.org/dist/htmx.min.js "$VENDOR_DIR/htmx.min.js"
cp node_modules/htmx-ext-sse/dist/sse.min.js "$VENDOR_DIR/htmx-ext-sse.min.js"

mkdir -p "$VENDOR_DIR/LICENSES"
cp node_modules/htmx.org/LICENSE "$VENDOR_DIR/LICENSES/htmx.txt"
cp node_modules/htmx-ext-sse/LICENSE "$VENDOR_DIR/LICENSES/htmx-ext-sse.txt"

echo "Vendored htmx $(node -p "require('htmx.org/package.json').version")"
echo "Vendored htmx-ext-sse $(node -p "require('htmx-ext-sse/package.json').version")"
