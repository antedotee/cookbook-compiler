#!/usr/bin/env bash
# Sets up .venv on first run (or if it is broken), installs requirements, starts the server, and opens the browser.
set -e
cd "$(dirname "$0")"

PY=""
for candidate in "${PYTHON:-}" python3 python3.13 python3.12 python3.11 python3.10 python; do
  if [ -n "$candidate" ] && command -v "$candidate" >/dev/null 2>&1 \
     && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
    PY="$candidate"
    break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.9 or newer is needed. Install it from https://www.python.org/downloads/ and run this again."
  exit 1
fi

if ! .venv/bin/python -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
  rm -rf .venv
  "$PY" -m venv .venv
fi
.venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt
exec .venv/bin/python app.py --open
