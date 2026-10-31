#!/usr/bin/env bash
# Creates .venv on first run, installs requirements, starts the server, and opens the browser.
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  "${PYTHON:-python3}" -m venv .venv
fi
.venv/bin/python -m pip install -q -r requirements.txt
exec .venv/bin/python app.py --open
