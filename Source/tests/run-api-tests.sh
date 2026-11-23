#!/usr/bin/env bash
# Runs the server tests (tests/api_test.py) against `wrangler dev` on a fresh, throw-away local database.
# The test-only variables below make the Worker send email and phone alerts to fake services on 127.0.0.1;
# a real deployment never has them. Usage, from Source/: bash tests/run-api-tests.sh
set -euo pipefail
cd "$(dirname "$0")/.."
STATE="$(mktemp -d)"
PORT=8788
npm run build >/dev/null
npx wrangler dev --port "$PORT" --ip 127.0.0.1 --persist-to "$STATE" \
  --var ADMIN_SETUP_CODE:test-setup-code-123 --var TEST_PUSH_LOOPBACK:1 \
  --var TEST_FAKE_BASE:http://127.0.0.1:8799 --var RESEND_API_KEY:re_dummy_for_tests >"$STATE/wrangler.log" 2>&1 &
WPID=$!
trap 'kill $WPID 2>/dev/null; rm -rf "$STATE"' EXIT
for _ in $(seq 1 60); do curl -sf "http://127.0.0.1:$PORT/api/health" >/dev/null && break; sleep 1; done
JEC_BASE="http://127.0.0.1:$PORT" python3 tests/api_test.py
