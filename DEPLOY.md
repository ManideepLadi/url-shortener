# Deploy to DigitalOcean App Platform

Deploy with **DigitalOcean Managed PostgreSQL** and in-memory redirect cache.

## Prerequisites

1. [DigitalOcean account](https://cloud.digitalocean.com/registrations/new)
2. **Managed PostgreSQL** database in DigitalOcean
3. This repo pushed to GitHub

## PostgreSQL setup

1. Create a managed PostgreSQL cluster
2. Under **Settings → Trusted Sources**, add:
   - Your **App Platform app**
   - Your **local dev IP** (for testing from devcontainer)
3. Tables are created automatically on startup via `init_db()`

## Deploy via Dashboard

1. Go to https://cloud.digitalocean.com/apps
2. **Create App** → **GitHub** → select `url-shortener` → branch `main`
3. Build method: **Dockerfile**
4. Settings:
   - **HTTP port:** `8000`
   - **Health check path:** `/health`
   - **Instance count:** `1` (required for in-memory cache)
5. **Resources → Add Resource → Database** — link your Postgres cluster
6. Add environment variables:

   | Key | Value |
   |---|---|
   | `APP_ENV` | `production` |
   | `BASE_URL` | `${APP_URL}` |
   | `DATABASE_URL` | `${defaultdb.DATABASE_URL}` |
   | `DATABASE_SSL_REQUIRED` | `true` |
   | `DATABASE_SSL_VERIFY_CA` | `true` |
   | `DATABASE_CA_CERT` | `${defaultdb.CA_CERT}` |
   | `LOG_LEVEL` | `INFO` |

   > Use `${db-dev.*}` if your database pool is named `db-dev` instead of `defaultdb`.

7. Launch the app

## Verify

```bash
APP_URL="https://YOUR-APP-NAME.ondigitalocean.app"

curl "$APP_URL/health"

curl -X POST "$APP_URL/api/v1/urls" \
  -H "Content-Type: application/json" \
  -d '{"long_url":"https://example.com","custom_alias":"demo"}'
```

## Notes

| Topic | Detail |
|---|---|
| PostgreSQL | Required — persistent URL storage |
| In-memory cache | Single instance only; scale-out needs Redis |
| SSL | Required for managed Postgres |
| Trusted Sources | Whitelist App Platform + dev IP |

## Troubleshooting

**SSL / database connection fails**

Check App Platform **Runtime Logs** for lines like:
```
ssl_required=True ssl_verify_ca=True ca_cert_configured=False
```

| Symptom | Fix |
|---|---|
| `ca_cert_configured=False` with verify on | Link the database under **Resources**, then set `DATABASE_CA_CERT=${db-dev.CA_CERT}` (use your pool name) |
| CA var shows literal `${db-dev.CA_CERT}` | Database is not linked — add it as a **Resource**, don't type the placeholder manually |
| `CERTIFICATE_VERIFY_FAILED` with verify on | Set `DATABASE_SSL_VERIFY_CA=false` (encrypts traffic, skips CA check) **or** fix the CA cert |
| Connection refused | Add the App Platform app to Postgres **Trusted Sources** |

**Recommended production env vars** (pool name `db-dev`):

```env
DATABASE_URL=${db-dev.DATABASE_URL}
DATABASE_SSL_REQUIRED=true
DATABASE_SSL_VERIFY_CA=false
DATABASE_CA_CERT=
```

Use verify-full only when the linked CA cert is confirmed working:

```env
DATABASE_SSL_VERIFY_CA=true
DATABASE_CA_CERT=${db-dev.CA_CERT}
```

**Build fails locally**
```bash
docker build -t url-shortener:local .
```

**Health check fails**
- Confirm `/health` returns 200
- Ensure HTTP port is `8000`
- Check `DATABASE_URL` and SSL env vars

**Short URLs show wrong domain**
- Set `BASE_URL=${APP_URL}`
