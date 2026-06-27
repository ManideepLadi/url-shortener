# URL Shortener API

Production-oriented REST API that shortens URLs, supports custom aliases with safe concurrent creation, redirects with Redis caching, and exposes link metadata.

## Architecture

```
app/
├── routers/        # HTTP handlers (thin)
├── services/       # Business logic
├── repositories/   # PostgreSQL access
├── models/         # SQLAlchemy entities
├── schemas/        # Pydantic request/response validation
├── db/             # Database and Redis clients
├── middleware/     # Request logging
├── config.py       # Environment-based settings
└── dependencies.py # FastAPI dependency injection
```

### Design trade-offs

| Decision | Why | Trade-off |
|---|---|---|
| DB unique constraint on `alias` | Correct collision handling under concurrency | Requires catching `IntegrityError` |
| Redis for redirect cache + hit buffer | Faster redirects, fewer DB writes | Access counts are eventually consistent until metadata read |
| Async SQLAlchemy + asyncpg | Fits FastAPI concurrency model | Slightly more setup than sync ORM |
| 307 redirects | Preserves HTTP method on redirect | Some clients treat 302/307 differently |

## Requirements

- Python 3.12+
- PostgreSQL and Redis (via Docker **or** native install)

## Quick start

### Option A — with Docker

```bash
cd url-shortener
cp .env.example .env
docker compose up -d postgres redis
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Option B — without Docker (e.g. devcontainer / WSL)

If `docker` is not available, install and start Postgres + Redis natively:

```bash
# Install (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib redis-server

# One-time setup (creates DB, sets postgres password to match .env)
chmod +x scripts/setup-local-deps.sh
./scripts/setup-local-deps.sh

# Run the API
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload
```

If the setup script cannot use sudo, run these manually:

```bash
sudo service postgresql start
sudo service redis-server start
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'postgres';"
sudo -u postgres createdb urlshortener
redis-cli ping   # should return PONG
```

API docs: http://localhost:8000/docs

## API

### Create short URL

```http
POST /api/v1/urls
Content-Type: application/json

{
  "long_url": "https://example.com/very/long/path",
  "custom_alias": "optional-alias"
}
```

Response `201 Created`:

```json
{
  "alias": "optional-alias",
  "long_url": "https://example.com/very/long/path",
  "short_url": "http://localhost:8000/optional-alias",
  "access_count": 0,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Get metadata

```http
GET /api/v1/urls/{alias}
```

### Redirect

```http
GET /{alias}
```

Returns `307 Temporary Redirect` to the original URL.

### Health

```http
GET /health
```

## Error handling

| Status | Scenario |
|---|---|
| `201` | URL created |
| `307` | Redirect |
| `404` | Unknown alias |
| `409` | Custom alias collision |
| `422` | Invalid input |
| `503` | Could not generate unique auto alias |

## Testing

Start dependencies:

```bash
docker compose up -d postgres redis
docker compose exec postgres psql -U postgres -c "CREATE DATABASE urlshortener_test;"
```

Run tests:

```bash
pytest
pytest -m integration
pytest --cov=app
```

Unit tests cover alias validation and service logic with mocks. Integration tests verify create, redirect, collision handling, and health checks against Postgres and Redis.

## Environment variables

See `.env.example` for all settings.

## Run with Docker

```bash
docker compose up --build
```
