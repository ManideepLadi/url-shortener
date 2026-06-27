#!/usr/bin/env bash
# Bind to 0.0.0.0 so the app is reachable from your host browser via port forwarding.
set -euo pipefail
cd "$(dirname "$0")/.."
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
