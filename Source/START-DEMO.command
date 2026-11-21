#!/bin/bash
# Opens the site on http://localhost:8080 (Node needed for the local server).
# Without Node it opens index.html directly; the film still plays but seeks less precisely.
# If double-click says "no permission": open Terminal and run  bash START-DEMO.command
cd "$(dirname "$0")" || exit 1
if command -v node >/dev/null 2>&1; then
  (sleep 2; open "http://localhost:8080/") &
  node server.cjs "$(pwd)" 8080
else
  open index.html
fi
