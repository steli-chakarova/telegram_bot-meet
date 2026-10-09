#!/usr/bin/env bash
# Deploy Telegram Meet bot to Railway. Run in your own terminal (not Cursor sandbox).
set -euo pipefail
cd "$(dirname "$0")"

export RAILWAY_API_TOKEN="${RAILWAY_API_TOKEN:-0190c2bc-b598-4d26-b250-923010ab4b21}"
RAILWAY=./bin/railway

if [[ ! -f .env ]]; then
  echo "Missing .env with TELEGRAM_BOT_TOKEN"
  exit 1
fi
if [[ ! -f credentials.json || ! -f token.json ]]; then
  echo "Missing credentials.json or token.json"
  exit 1
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

echo "==> Railway whoami"
"$RAILWAY" whoami

if [[ ! -f .railway/config.json ]] && [[ ! -d .railway ]]; then
  echo "==> Creating project"
  "$RAILWAY" init -n telegram-meet-bot || "$RAILWAY" init
fi

echo "==> Setting variables"
# Compact JSON on one line for env vars
CRED_JSON=$(python3 -c 'import json;print(json.dumps(json.load(open("credentials.json")),separators=(",",":")))')
TOKEN_JSON=$(python3 -c 'import json;print(json.dumps(json.load(open("token.json")),separators=(",",":")))')

"$RAILWAY" variables set \
  TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" \
  GOOGLE_CREDENTIALS_JSON="$CRED_JSON" \
  GOOGLE_TOKEN_JSON="$TOKEN_JSON"

echo "==> Deploy"
"$RAILWAY" up --detach

echo "==> Done. Check logs with: ./bin/railway logs"
echo "Remember: Service Settings → Serverless OFF"
echo "BotFather: /setprivacy → Disable"
