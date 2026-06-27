# Deploy to DigitalOcean App Platform

Deploy the **in-memory basic version** as a single container. Data resets on redeploy/restart.

## Prerequisites

1. [DigitalOcean account](https://cloud.digitalocean.com/registrations/new)
2. [GitHub account](https://github.com) with this repo pushed
3. [doctl CLI](https://docs.digitalocean.com/reference/doctl/how-to/install/) (optional, for CLI deploy)

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

## Important limitations (basic version)

| Limitation | Detail |
|---|---|
| In-memory storage | Short URLs are lost on restart/redeploy |
| Single instance only | Do not scale beyond 1 instance |
| No HTTPS custom domain setup | Included in DO default URL; add custom domain in App Platform settings |

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
