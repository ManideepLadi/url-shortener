# Deploy to DigitalOcean App Platform

Deploy with **DigitalOcean Managed PostgreSQL** and in-memory redirect cache (Redis disabled for now).

## Prerequisites

1. [DigitalOcean account](https://cloud.digitalocean.com/registrations/new)
2. **Managed PostgreSQL** database created in DigitalOcean
3. [GitHub account](https://github.com) with this repo pushed
4. [doctl CLI](https://docs.digitalocean.com/reference/doctl/how-to/install/) (optional, for CLI deploy)

## DigitalOcean PostgreSQL setup

1. Create a managed PostgreSQL cluster in DigitalOcean
2. Under **Settings → Trusted Sources**, add:
   - Your **App Platform app** (when deployed)
   - Your **local IP** for devcontainer testing
3. Copy the connection details into `.env` (never commit `.env`):

```env
DATABASE_URL=postgresql+asyncpg://db-dev:YOUR_PASSWORD@YOUR_HOST:25060/db-dev
DATABASE_SSL_REQUIRED=true
```

Tables are created automatically on startup via `init_db()`.

## Step 1 — Push code to GitHub

```bash
cd /workspaces/url-shortener
git init
git add .
git commit -m "Initial URL shortener for DigitalOcean deploy"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/url-shortener.git
git push -u origin main
```

## Step 2 — Update the app spec

Edit `.do/app.yaml` and replace:

```yaml
repo: your-github-username/url-shortener
```

with your actual GitHub repo path.

## Step 3 — Authenticate doctl (CLI path)

```bash
doctl auth init
```

Generate a token at: https://cloud.digitalocean.com/account/api/tokens

## Step 4 — Deploy

### Option A — CLI (recommended)

```bash
chmod +x scripts/deploy-digitalocean.sh
./scripts/deploy-digitalocean.sh
```

### Option B — DigitalOcean Dashboard

1. Go to https://cloud.digitalocean.com/apps
2. Click **Create App**
3. Choose **GitHub** → select your `url-shortener` repo → branch `main`
4. Select **Dockerfile** as the build method
5. Set:
   - **HTTP port:** `8000`
   - **Health check path:** `/health`
   - **Instance count:** `1` (required for in-memory storage)
6. Add environment variables:

   | Key | Value |
   |---|---|
   | `APP_ENV` | `production` |
   | `BASE_URL` | `${APP_URL}` |
   | `DATABASE_URL` | `postgresql+asyncpg://db-dev:PASSWORD@HOST:25060/db-dev` |
   | `DATABASE_SSL_REQUIRED` | `true` |
   | `LOG_LEVEL` | `INFO` |

7. Choose plan: **Basic** → `$5/mo` (512 MB RAM)
8. Click **Launch App**

## Step 5 — Verify

After deploy (~3–5 min), open:

```
https://YOUR-APP-NAME.ondigitalocean.app/docs
```

Test:

```bash
APP_URL="https://YOUR-APP-NAME.ondigitalocean.app"

curl "$APP_URL/health"

curl -X POST "$APP_URL/api/v1/urls" \
  -H "Content-Type: application/json" \
  -d '{"long_url":"https://example.com","custom_alias":"demo"}'
```

## Important notes

| Topic | Detail |
|---|---|
| PostgreSQL | Required — stores URLs persistently |
| Redis | Disabled — using in-memory cache (single instance) |
| SSL | Required for DO managed Postgres (`DATABASE_SSL_REQUIRED=true`) |
| Trusted Sources | Must whitelist App Platform + your dev IP in DO dashboard |
| Single instance | Keep instance count at 1 while using in-memory cache |

## Upgrade path (production)

When ready for persistent storage:

1. Add **Managed PostgreSQL** and **Managed Redis** in DigitalOcean
2. Uncomment PostgreSQL/Redis code in `app/dependencies.py`, `app/main.py`, etc.
3. Add env vars in App Platform: `DATABASE_URL`, `REDIS_URL`
4. Uncomment deps in `requirements-prod.txt`

## Cost estimate

| Resource | Cost |
|---|---|
| App Platform (basic) | ~$5/month |
| Managed Postgres | ~$15/month (when added) |
| Managed Redis | ~$15/month (when added) |

## Troubleshooting

**Build fails**
```bash
docker build -t url-shortener:local .
```

**Health check fails**
- Confirm `/health` returns 200 locally
- Ensure `http_port` is `8000`

**Short URLs show wrong domain**
- Set `BASE_URL=${APP_URL}` in App Platform env vars

**doctl not authenticated**
```bash
doctl auth init
doctl account get
```
