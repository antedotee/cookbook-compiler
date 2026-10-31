@echo off
rem Creates .venv on first run, installs requirements, starts the server, and opens the browser.
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv || exit /b 1
)
.venv\Scripts\python -m pip install -q -r requirements.txt || exit /b 1
.venv\Scripts\python app.py --open
