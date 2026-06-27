#!/usr/bin/env bash
# Deploy url-shortener to DigitalOcean App Platform.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SPEC="$ROOT/.do/app.yaml"

echo "==> DigitalOcean App Platform deploy"
echo

if ! command -v doctl >/dev/null 2>&1; then
  echo "Install doctl: https://docs.digitalocean.com/reference/doctl/how-to/install/"
  exit 1
fi

if ! doctl account get >/dev/null 2>&1; then
  echo "Authenticate first:"
  echo "  doctl auth init"
  exit 1
fi

if grep -q "your-github-username/url-shortener" "$SPEC"; then
  echo "Update .do/app.yaml with your GitHub repo:"
  echo "  repo: your-github-username/url-shortener"
  echo
  echo "Then push this project to GitHub before deploying."
  exit 1
fi

echo "==> Validating Docker build locally"
docker build -t url-shortener:local "$ROOT"

echo
echo "==> Creating/updating App Platform app"
if doctl apps list --format ID,Spec.Name --no-header | awk '{print $2}' | grep -qx "url-shortener"; then
  APP_ID="$(doctl apps list --format ID,Spec.Name --no-header | awk '$2=="url-shortener"{print $1; exit}')"
  echo "Updating existing app: $APP_ID"
  doctl apps update "$APP_ID" --spec "$SPEC"
else
  echo "Creating new app"
  doctl apps create --spec "$SPEC" --wait
fi

APP_ID="$(doctl apps list --format ID,Spec.Name --no-header | awk '$2=="url-shortener"{print $1; exit}')"
APP_URL="$(doctl apps get "$APP_ID" --format DefaultIngress --no-header)"

echo
echo "Deployed successfully!"
echo "  App URL:  https://$APP_URL"
echo "  Docs:     https://$APP_URL/docs"
echo "  Health:   https://$APP_URL/health"
