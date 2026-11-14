#!/usr/bin/env bash
# Real desktop E2E: drives the debug Kiko.app binary against a LOCAL Kiko API.
# Usage: KIKO_API_URL=http://127.0.0.1:8765 API_PYTHON=/path/to/python e2e/run-journey.sh
# Requires: a debug build (pnpm tauri build --debug --no-bundle), the API, outbox
# dispatcher and Celery worker running without a usable AI provider (AI_PROVIDER=fake, or
# openai without a key as in scripts/local/kiko-local.sh), and API env vars exported
# (for the token helper). Uses the login Keychain for session persistence and removes the
# item again by logging out.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
APP="${KIKO_DESKTOP_BINARY:-$HERE/../src-tauri/target/debug/kiko-desktop}"
API_URL="${KIKO_API_URL:?set KIKO_API_URL to the local API origin}"
case "$API_URL" in http://127.0.0.1:*|http://localhost:*) ;; *) echo "local API only" >&2; exit 2;; esac
PY="${API_PYTHON:-python3}"
WORK="$(mktemp -d)"
EMAIL="desktop-e2e-$(date +%s)@example.com"
PASSWORD="Desktop-E2E-$(openssl rand -hex 6)1a"
KEYCHAIN_ACCOUNT="$(python3 -c "import sys,urllib.parse as u;p=u.urlsplit(sys.argv[1]);print(f'{p.scheme}://{p.netloc}')" "$API_URL")"
RESULTS="$WORK/results.log"
: > "$RESULTS"

# Start and end without a stored session for this local test server only.
clear_test_session() {
  security delete-generic-password -s pt.pixart.kiko.session -a "$KEYCHAIN_ACCOUNT" >/dev/null 2>&1 || true
}
clear_test_session
trap clear_test_session EXIT

run_phase() { # name script ephemeral(0|1) extra-json
  local name="$1" script="$2" ephemeral="$3" extra="${4:-}"
  local file="$WORK/$name.js"
  {
    printf 'window.__KIKO_SMOKE__ = {"email": "%s", "password": "%s"%s};\n' "$EMAIL" "$PASSWORD" "$extra"
    cat "$HERE/lib.js" "$HERE/$script"
  } > "$file"
  local env_flag=()
  [ "$ephemeral" = "1" ] && env_flag=(KIKO_DESKTOP_EPHEMERAL_SESSION=1)
  local started=$(python3 -c 'import time;print(time.time())')
  set +e
  env ${env_flag[@]+"${env_flag[@]}"} KIKO_API_URL="$API_URL" KIKO_DESKTOP_SMOKE_SCRIPT="$file" \
    timeout 180 "$APP" > "$WORK/$name.log" 2>&1
  local code=$?
  set -e
  grep '^SMOKE \(PASS\|DONE\|FAIL\)' "$WORK/$name.log" | sed "s/^SMOKE /[$name] /" | tee -a "$RESULTS"
  if [ $code -ne 0 ]; then
    echo "[$name] app exited with $code (log: $WORK/$name.log)" | tee -a "$RESULTS"
    exit 1
  fi
}

keychain_has_session() {
  security find-generic-password -s pt.pixart.kiko.session -a "$KEYCHAIN_ACCOUNT" >/dev/null 2>&1
}

run_phase register phase-1-register.js 1
TOKEN="$(cd "$HERE/../../api" && "$PY" "$HERE/outbox_token.py" "$EMAIL")"
[ -n "$TOKEN" ] || { echo "no verification token" >&2; exit 1; }
run_phase verify phase-2-verify-onboard.js 0 ", \"token\": \"$TOKEN\""
keychain_has_session && echo "[keychain] refresh token stored after sign-in" | tee -a "$RESULTS" \
  || { echo "[keychain] FAIL no session item after sign-in" | tee -a "$RESULTS"; exit 1; }
run_phase work phase-3-work.js 0
run_phase persist phase-4-persist-logout.js 0
keychain_has_session && { echo "[keychain] FAIL item still present after logout" | tee -a "$RESULTS"; exit 1; } \
  || echo "[keychain] session item removed by logout" | tee -a "$RESULTS"
run_phase after-logout phase-5-after-logout.js 0
echo "ALL PHASES PASSED ($EMAIL). Logs: $WORK" | tee -a "$RESULTS"
