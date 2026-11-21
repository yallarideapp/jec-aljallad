@echo off
pwsh.exe -NoLogo -NoProfile -File "%~dp0Source\tools\package-store.ps1"
if errorlevel 1 pause
