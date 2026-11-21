#!/bin/bash
# macOS launcher for Source/tools/package-store.ps1 (PowerShell 7).
# If double-click says "no permission": open Terminal and run  bash UPDATE-PACKAGE.command
cd "$(dirname "$0")" || exit 1
if ! command -v pwsh >/dev/null 2>&1; then
  echo "PowerShell 7 (pwsh) is not installed. Install it with:  brew install --cask powershell"
  read -r -n1 -p "Press any key to close..."; echo; exit 1
fi
pwsh -NoLogo -NoProfile -File "Source/tools/package-store.ps1" || { read -r -n1 -p "Packaging failed. Press any key to close..."; echo; exit 1; }
