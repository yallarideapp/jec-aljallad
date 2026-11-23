#!/usr/bin/env bash
# Browser tests (tests/browser_test.py), twice: against `wrangler dev` on a fresh database (the real version), and
# against dist/ on a plain static server under /jec-aljallad/ (the GitHub Pages preview, where the demo runs).
# Usage, from Source/: bash tests/run-browser-tests.sh
set -euo pipefail
cd "$(dirname "$0")/.."
STATE="$(mktemp -d)"; PAGES="$(mktemp -d)"
npm run build >/dev/null
npx wrangler dev --port 8788 --ip 127.0.0.1 --persist-to "$STATE" --var ADMIN_SETUP_CODE:test-setup-code-123 >"$STATE/wrangler.log" 2>&1 &
WPID=$!
ln -s "$PWD/dist" "$PAGES/jec-aljallad"
python3 -m http.server 8090 --bind 127.0.0.1 --directory "$PAGES" >/dev/null 2>&1 &
SPID=$!
trap 'kill $WPID $SPID 2>/dev/null; rm -rf "$STATE" "$PAGES"' EXIT
for _ in $(seq 1 60); do curl -sf http://127.0.0.1:8788/api/health >/dev/null && break; sleep 1; done
echo "== live"; python3 tests/browser_test.py live http://127.0.0.1:8788/
echo "== demo"; python3 tests/browser_test.py demo http://127.0.0.1:8090/jec-aljallad/
