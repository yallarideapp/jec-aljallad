@echo off
rem Opens the site on http://localhost:8080 (Node needed for the local server).
rem Without Node it opens index.html directly; the film still plays but seeks less precisely.
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  start "" "%~dp0index.html"
  exit /b
)
start "" cmd /c "timeout /t 2 >nul & start "" http://localhost:8080/"
node "%~dp0server.cjs" "%~dp0." 8080
