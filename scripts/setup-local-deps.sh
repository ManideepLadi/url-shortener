#!/usr/bin/env bash
# One-time local setup when Docker is unavailable.
# Requires sudo (postgres system user access).

set -euo pipefail

echo "Starting PostgreSQL and Redis..."
sudo service postgresql start
sudo service redis-server start

echo "Configuring PostgreSQL..."
sudo -u postgres psql -v ON_ERROR_STOP=1 <<'SQL'
ALTER USER postgres WITH PASSWORD 'postgres';
SELECT 'CREATE DATABASE urlshortener'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'urlshortener')\gexec
SQL

echo "Verifying services..."
redis-cli ping
PGPASSWORD=postgres psql -h localhost -U postgres -d urlshortener -c "SELECT 1"

echo
echo "Done. Start the API with:"
echo "  cd /workspaces/url-shortener"
echo "  source .venv/bin/activate"
echo "  uvicorn app.main:app --reload"
