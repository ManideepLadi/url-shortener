#!/usr/bin/env bash
# Verify PostgreSQL connectivity using settings from .env
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Checking PostgreSQL connection..."
.venv/bin/python - <<'PY'
import asyncio

from app.config import masked_database_url, settings
from app.db.session import close_db, init_db


async def main() -> None:
    print(f"Database URL: {masked_database_url(settings.database_url)}")
    print(f"SSL required: {settings.database_ssl_required}")
    await init_db()
    print("Connection OK — tables ready")
    await close_db()


asyncio.run(main())
PY
