# URL Shortener API

Production-oriented REST API that shortens URLs, supports custom aliases with safe concurrent creation, redirects with an in-memory cache, and exposes link metadata. Persistent storage uses **PostgreSQL** (DigitalOcean Managed PostgreSQL in production).

## Architecture

```
app/
├── routers/        # HTTP handlers (thin)
├── services/       # Business logic
├── repositories/   # PostgreSQL access
├── strategies/     # Pluggable alias generation (random, base62)
├── models/         # SQLAlchemy entities
├── schemas/        # Pydantic request/response validation
├── db/             # Database session, SSL, in-memory cache
├── utils/          # Alias validation, Base62, exceptions
├── middleware/     # Request logging, Prometheus HTTP metrics
├── metrics/        # Prometheus metric definitions
├── config.py       # Environment-based settings
└── dependencies.py # FastAPI dependency injection

scripts/
├── check-db.sh     # Verify PostgreSQL connectivity
└── run-dev.sh      # Start dev server on :8000
```

### Storage model

| Layer | Role |
|---|---|
| **PostgreSQL** | Source of truth — stores alias, long URL, access count, timestamps |
| **InMemoryUrlCache** | Speed layer — caches redirect targets and buffers hit counts |

Redis is not used. The in-memory cache is per-process; keep App Platform instance count at **1** while using it.

### Write architecture — create short URL

`POST /api/v1/urls` persists a new mapping to PostgreSQL and warms the in-memory redirect cache.

```mermaid
flowchart TD
    subgraph Client
        A[POST /api/v1/urls<br/>long_url + optional custom_alias]
    end

    subgraph API["FastAPI layer"]
        B[urls router]
        C[CreateUrlRequest<br/>Pydantic validation]
    end

    subgraph Service["Business logic"]
        D[UrlService.create_short_url]
        E{custom_alias<br/>provided?}
        F[RandomAliasStrategy<br/>or Base62AliasStrategy]
        G[UrlRepository.create]
        H[UrlRepository.create_and_flush<br/>→ finalize_alias]
    end

    subgraph Storage
        I[("PostgreSQL<br/>url_mappings INSERT")]
        J[InMemoryUrlCache<br/>set_long_url]
    end

    K[201 CreateUrlResponse<br/>alias + short_url]

    A --> B --> C --> D --> E
    E -->|Yes| G
    E -->|No| F
    F -->|random| G
    F -->|base62| H
    G --> I
    H --> I
    I --> J --> K
```

| Step | Component | Action |
|---|---|---|
| 1 | `CreateUrlRequest` | Validates URL format, custom alias rules, reserved words |
| 2 | `UrlService` | Routes to custom alias path or configured strategy |
| 3 | `RandomAliasStrategy` | Generates random alias; retries on DB collision |
| 3 | `Base62AliasStrategy` | Inserts row, encodes autoincrement `id` as Base62 alias |
| 4 | `UrlRepository` | Commits to PostgreSQL; enforces unique `alias` constraint |
| 5 | `InMemoryUrlCache` | Stores `alias → long_url` for fast future redirects |
| 6 | Response | Returns `201` with `short_url`, `access_count: 0` |

---

### Read architecture — redirect & metadata

Read paths are separate. Redirects favour the cache; metadata reads flush buffered hit counts back to PostgreSQL.

```mermaid
flowchart TD
    subgraph Client
        R1[GET /{alias}]
        R2[GET /{alias}?preview=true]
        R3[GET /api/v1/urls/{alias}]
    end

    subgraph API["FastAPI layer"]
        B1[redirect router]
        B2[urls router]
    end

    subgraph Service["Business logic"]
        S1[UrlService.resolve_redirect]
        S2[UrlService.get_metadata]
    end

    subgraph Cache["InMemoryUrlCache"]
        C1{redirect cache<br/>hit?}
        C2[increment_hits]
        C3[set_long_url]
        C4[get_pending_hits]
        C5[reset_pending_hits]
    end

    subgraph Storage
        PG[("PostgreSQL<br/>url_mappings SELECT / UPDATE")]
    end

    subgraph Response
        O1[307 Redirect<br/>Location: long_url]
        O2[200 JSON preview<br/>redirect_url]
        O3[200 JSON metadata<br/>access_count + long_url]
    end

    R1 --> B1 --> S1
    R2 --> B1 --> S1
    R3 --> B2 --> S2

    S1 --> C1
    C1 -->|Yes| C2
    C1 -->|No| PG
    PG -->|found| C3 --> C2
    PG -->|not found| E404[404 Not Found]
    C2 --> O1
    C2 --> O2

    S2 --> PG
    PG -->|not found| E404
    PG -->|found| C4
    C4 -->|pending hits > 0| C5
    C5 --> PG
    PG --> O3
```

#### Redirect read path (`GET /{alias}`)

| Step | Component | Action |
|---|---|---|
| 1 | `InMemoryUrlCache` | Look up `alias → long_url` (TTL-based) |
| 2 | Cache hit | Increment buffered hit count; return long URL |
| 3 | Cache miss | `UrlRepository.get_by_alias()` → PostgreSQL |
| 4 | Found | Populate cache, increment hits, return long URL |
| 5 | Router | `307 Redirect` or `200 JSON` when `?preview=true` |

#### Metadata read path (`GET /api/v1/urls/{alias}`)

| Step | Component | Action |
|---|---|---|
| 1 | `UrlRepository` | Always reads mapping from PostgreSQL |
| 2 | `InMemoryUrlCache` | Adds pending buffered hits to displayed count |
| 3 | Flush | Writes buffered hits to PostgreSQL via `increment_access_count` |
| 4 | Response | Returns full metadata including accurate `access_count` |

### Design trade-offs

| Decision | Why | Trade-off |
|---|---|---|
| Strategy pattern for aliases | Swap random vs Base62 without changing service code | One extra abstraction layer |
| DB unique constraint on `alias` | Correct collision handling under concurrency | Requires catching `IntegrityError` |
| In-memory redirect cache | Faster redirects, fewer DB reads on hot links | Cache is lost on restart; not shared across instances |
| Buffered hit counts | Fewer DB writes on every redirect | Access counts are eventually consistent until metadata is read |
| Async SQLAlchemy + asyncpg | Fits FastAPI concurrency model | SSL setup required for managed Postgres |
| 307 redirects | Preserves HTTP method on redirect | Swagger cannot follow external redirects (CORS) |

## Requirements

- Python 3.12+
- PostgreSQL (DigitalOcean Managed PostgreSQL or local via Docker)

## Quick start

### 1. Configure environment

```bash
cd url-shortener
cp .env.example .env
# Edit .env with your DATABASE_URL and credentials
```

For **DigitalOcean Managed PostgreSQL**:
- Add your dev IP to **Databases → Settings → Trusted Sources**
- Set `DATABASE_SSL_VERIFY_CA=false` for local dev (no CA file needed)
- Set `DATABASE_SSL_VERIFY_CA=true` + `DATABASE_CA_CERT` for production verify-full

See [DEPLOY.md](./DEPLOY.md) for App Platform deployment.

### 2. Install and run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

./scripts/check-db.sh   # verify PostgreSQL connectivity
./scripts/run-dev.sh    # start on http://localhost:8000
```

### Option — local Postgres via Docker

```bash
docker compose --profile full up -d postgres
# Update DATABASE_URL in .env to point at localhost:5432
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

---

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/urls` | Create a short URL |
| `GET` | `/api/v1/urls/{alias}` | Get metadata (alias, long URL, hit count) |
| `GET` | `/{alias}` | Redirect to long URL (307) |
| `GET` | `/{alias}?preview=true` | Preview redirect target as JSON (Swagger-friendly) |
| `GET` | `/health` | Health check (database + cache status) |
| `GET` | `/metrics` | Prometheus metrics (when `METRICS_ENABLED=true`) |

### Create short URL

```http
POST /api/v1/urls
Content-Type: application/json

{
  "long_url": "https://example.com/very/long/path",
  "custom_alias": "optional-alias",
  "ttl_seconds": 3600
}
```

- `ttl_seconds` (optional) — link expires after this many seconds (stored as `expires_at` in PostgreSQL)
- Omit `ttl_seconds` for permanent links, or set `DEFAULT_LINK_TTL_SECONDS` to apply a server default

Response `201 Created`:

```json
{
  "alias": "optional-alias",
  "long_url": "https://example.com/very/long/path",
  "short_url": "http://localhost:8000/optional-alias",
  "access_count": 0,
  "created_at": "2024-01-01T00:00:00Z",
  "expires_at": "2024-01-01T01:00:00Z"
}
```

Omit `custom_alias` to auto-generate an alias using the configured strategy (`random` or `base62`).

### Get metadata

```http
GET /api/v1/urls/{alias}
```

Returns alias, `long_url`, `short_url`, `access_count`, and `created_at`. Flushes buffered redirect hits into PostgreSQL.

### Redirect

```http
GET /{alias}
```

Returns **307 Temporary Redirect** to the original URL.

Preview mode (returns JSON instead of redirecting):

```http
GET /{alias}?preview=true
```

```json
{
  "alias": "manideep",
  "redirect_url": "https://example.com/",
  "status_code": 307
}
```

**Testing redirects**

| Method | Works in Swagger? | Example |
|---|---|---|
| Browser address bar | — | `https://your-app.ondigitalocean.app/manideep` |
| curl | — | `curl -I https://your-app.ondigitalocean.app/manideep` |
| Preview mode | Yes | `GET /manideep?preview=true` |
| Metadata API | Yes | `GET /api/v1/urls/manideep` |
| Direct redirect in Swagger | No | Browser CORS blocks following 307 to external sites |

### Health

```http
GET /health
```

```json
{
  "status": "ok",
  "database": "ok",
  "cache": "in-memory"
}
```

### Prometheus metrics

```http
GET /metrics
```

Exposes Prometheus text format for scraping. Disable with `METRICS_ENABLED=false`.

| Metric | Type | Labels | Description |
|---|---|---|---|
| `http_requests_total` | Counter | `method`, `path`, `status` | HTTP requests (low-cardinality paths) |
| `http_request_duration_seconds` | Histogram | `method`, `path` | Request latency |
| `url_shortener_urls_created_total` | Counter | `alias_source`, `strategy` | Short URLs created (`custom`/`auto`, `random`/`base62`/`none`) |
| `url_shortener_redirects_total` | Counter | `cache_result` | Redirects resolved (`hit`/`miss`) |
| `url_shortener_metadata_requests_total` | Counter | — | Metadata API calls |
| `url_shortener_redirect_cache_entries` | Gauge | — | Cached alias→URL mappings |
| `url_shortener_redirect_cache_pending_hits` | Gauge | — | Buffered hit counts awaiting flush |

Example scrape config:

```yaml
scrape_configs:
  - job_name: url-shortener
    metrics_path: /metrics
    static_configs:
      - targets: ["your-app.ondigitalocean.app:443"]
    scheme: https
```

---

## How it works

### Create URL flow

```mermaid
flowchart TD
    A[POST /api/v1/urls] --> B{Valid JSON?}
    B -->|No| E422[422 Validation Error]
    B -->|Yes| C{custom_alias provided?}
    C -->|Yes| D[Use custom alias]
    C -->|No| F[Alias strategy: random or base62]
    D --> G[Save to PostgreSQL]
    F --> H{Unique after retries?}
    H -->|No| E503[503 Alias Generation Failed]
    H -->|Yes| G
    G --> I{DB unique constraint OK?}
    I -->|No custom alias| E409[409 Alias Already Exists]
    I -->|No auto alias| H
    I -->|Yes| J[Cache alias → long_url]
    J --> K[201 Created response]
```

```
POST /api/v1/urls
       │
       ▼
CreateUrlRequest (Pydantic validation)
       │
       ▼
UrlService.create_short_url()
       │
       ├── custom_alias provided? ──Yes──► UrlRepository.create() ──► PostgreSQL
       │                                         │
       No                                        │ IntegrityError → 409
       ▼                                         ▼
AliasGenerationStrategy.create_auto_alias()  InMemoryUrlCache.set_long_url()
  (random or base62)                              │
       │                                          ▼
       └── collision ──► retry or 503       201 Created response
```

#### Step 1 — Request validation

Handled by `CreateUrlRequest` before any business logic runs.

**`long_url`**

| Rule | Failure |
|---|---|
| Must be a valid HTTP/HTTPS URL (`AnyHttpUrl`) | `422` |

**`custom_alias`** (optional)

| Rule | Failure |
|---|---|
| 3–32 characters | `422` |
| Letters, numbers, hyphens, underscores only | `422` |
| Not a reserved word | `422` |
| Whitespace trimmed | — |

Reserved aliases: `api`, `docs`, `health`, `openapi`, `redoc`, `metrics`, `admin`

#### Step 2 — Custom alias path

When `custom_alias` is provided:

1. Insert into PostgreSQL with the given alias.
2. On duplicate alias → `409 Conflict` (no retry).
3. On success → cache the mapping and return `201`.

The database enforces uniqueness via a unique index on `alias`. Concurrent requests that race for the same alias are resolved safely by catching `IntegrityError`.

#### Step 3 — Auto-generated alias path (strategy pattern)

When `custom_alias` is omitted, `UrlService` delegates to the configured **alias generation strategy**:

| Strategy | Class | How it works |
|---|---|---|
| **Random** (default) | `RandomAliasStrategy` | `secrets`-based random string; retries on DB collision |
| **Base62** | `Base62AliasStrategy` | Insert row → flush to get autoincrement `id` → encode as Base62 → finalize alias |

Configured via `AUTO_ALIAS_STRATEGY`:

```env
# Random (default) — unpredictable 8-char alias
AUTO_ALIAS_STRATEGY=random
AUTO_ALIAS_LENGTH=8
AUTO_ALIAS_MAX_RETRIES=5

# Base62 — deterministic alias from record ID
AUTO_ALIAS_STRATEGY=base62
AUTO_ALIAS_LENGTH=3    # minimum encoded length (id=5 → "005")
```

Base62 alphabet: `0-9`, `A-Z`, `a-z`. Implementation in `app/utils/base62.py`, strategies in `app/strategies/`.

#### Step 4 — Cache and response

After a successful insert:

- `InMemoryUrlCache.set_long_url(alias, long_url)` stores the mapping for fast redirects.
- Response includes `short_url` built from `BASE_URL/{alias}`.

#### Example outcomes

| Request | Result |
|---|---|
| Valid URL, no alias | `201` with auto-generated alias |
| Valid URL + custom alias | `201` with that alias |
| Invalid URL | `422` |
| Alias too short / bad characters | `422` |
| Reserved alias (`health`, `api`, …) | `422` |
| Custom alias already taken | `409` |
| Auto alias: max retries exhausted (random) | `503` |

---

### Redirect flow

```
GET /{alias}                          GET /{alias}?preview=true
       │                                       │
       ▼                                       ▼
UrlService.resolve_redirect()          UrlService.resolve_redirect()
       │                                       │
       ├── cache hit? ──Yes──► increment hits  ├── same lookup path
       │                                       │
       No                                       ▼
       ▼                                  200 JSON { redirect_url }
UrlRepository.get_by_alias() ──► PostgreSQL
       │
       ├── not found ──► 404
       │
       └── found ──► cache alias ──► increment hits ──► 307 redirect
```

- Redirects use **307 Temporary Redirect** so the HTTP method is preserved.
- Hit counts are buffered in memory on each redirect (including preview mode).
- Cache entries expire after `REDIRECT_CACHE_TTL_SECONDS` (default 3600).

---

### Metadata flow

```
GET /api/v1/urls/{alias}
       │
       ▼
UrlService.get_metadata()
       │
       ├── alias not in DB ──► 404
       │
       └── found ──► flush buffered hits to PostgreSQL
                     ──► return alias, long_url, short_url, access_count, created_at
```

Reading metadata flushes any pending buffered hit counts from the in-memory cache into PostgreSQL, so `access_count` reflects recent redirects.

---

## Error handling

| Status | Scenario |
|---|---|
| `200` | Redirect preview (`?preview=true`) |
| `201` | URL created |
| `307` | Redirect to long URL |
| `404` | Unknown alias |
| `409` | Custom alias collision |
| `410` | Link has expired |
| `422` | Invalid input (bad URL, bad alias, reserved alias, ttl too large) |
| `503` | Could not generate unique auto alias after retries |

---

## Environment variables

See `.env.example` for all settings.

### Local development

```env
APP_NAME=url-shortener
APP_ENV=development
LOG_LEVEL=INFO

DATABASE_URL=postgresql+asyncpg://db-dev:YOUR_PASSWORD@YOUR_HOST:25060/db-dev
DATABASE_SSL_REQUIRED=true
DATABASE_SSL_VERIFY_CA=false
DATABASE_CA_CERT=

BASE_URL=http://localhost:8000
AUTO_ALIAS_STRATEGY=random
AUTO_ALIAS_LENGTH=8
AUTO_ALIAS_MAX_RETRIES=5
REDIRECT_CACHE_TTL_SECONDS=3600
DB_INIT_MAX_RETRIES=10
DB_INIT_RETRY_DELAY_SECONDS=2.0
```

### Production (DigitalOcean App Platform)

Link the database under **Resources**, then set:

```env
APP_ENV=production
BASE_URL=${APP_URL}
DATABASE_URL=${db-dev.DATABASE_URL}
DATABASE_SSL_REQUIRED=true
DATABASE_SSL_VERIFY_CA=false
DATABASE_CA_CERT=
LOG_LEVEL=INFO
METRICS_ENABLED=true
AUTO_ALIAS_STRATEGY=random
```

For verify-full SSL (recommended once CA cert is linked):

```env
DATABASE_SSL_VERIFY_CA=true
DATABASE_CA_CERT=${db-dev.CA_CERT}
```

> Replace `db-dev` with your actual database pool name if different.

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (auto-converted to `postgresql+asyncpg://`; `sslmode` stripped) |
| `DATABASE_SSL_REQUIRED` | Enable SSL for managed Postgres (`true`) |
| `DATABASE_SSL_VERIFY_CA` | `false` = encrypt only; `true` = verify-full with CA cert |
| `DATABASE_CA_CERT` | PEM content for verify-full; use `${db-dev.CA_CERT}` on App Platform |
| `BASE_URL` | Public base URL for generated short links (`${APP_URL}` in production) |
| `AUTO_ALIAS_STRATEGY` | `random` (default) or `base62` |
| `AUTO_ALIAS_LENGTH` | Random alias length, or Base62 minimum length (default 8) |
| `AUTO_ALIAS_MAX_RETRIES` | Max collision retries for random strategy (default 5) |
| `DEFAULT_LINK_TTL_SECONDS` | Optional default link TTL when request omits `ttl_seconds` |
| `MAX_LINK_TTL_SECONDS` | Maximum allowed `ttl_seconds` per link (default 31536000) |
| `REDIRECT_CACHE_TTL_SECONDS` | In-memory cache TTL (default 3600) |
| `DB_INIT_MAX_RETRIES` | Startup DB connection retries (default 10) |
| `DB_INIT_RETRY_DELAY_SECONDS` | Delay between startup retries (default 2.0) |
| `METRICS_ENABLED` | Expose `/metrics` and collect Prometheus metrics (default `true`) |

---

## Testing

```bash
pytest                  # all tests
pytest tests/unit       # unit tests (no DB required)
pytest -m integration   # integration tests (requires live PostgreSQL)
pytest --cov=app
```

Unit tests cover alias validation, Base62 encode/decode, alias strategies (random + base62), service logic, and config normalization. Integration tests verify create, redirect, preview mode, collision handling, and health checks against PostgreSQL.

---

## Deployment

See [DEPLOY.md](./DEPLOY.md) for DigitalOcean App Platform setup, SSL troubleshooting, and environment variables.

## Run with Docker

```bash
docker compose up --build
```

Uses `requirements.txt` (production deps). Dev/test dependencies are in `requirements-dev.txt`.
