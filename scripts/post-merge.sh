#!/bin/bash
set -euo pipefail

echo "[post-merge] syncing Python deps with uv"
uv sync --frozen

echo "[post-merge] installing root npm deps"
npm install --no-audit --no-fund --no-progress

echo "[post-merge] installing frontend npm deps"
npm install --prefix frontend --no-audit --no-fund --no-progress

echo "[post-merge] done"
