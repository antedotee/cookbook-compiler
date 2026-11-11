@echo off
rem Sets up .venv on first run (or if it is broken), installs requirements, starts the server, and opens the browser.
cd /d "%~dp0"

set PY=
py -3 -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>&1 && set PY=py -3
if not defined PY python -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>&1 && set PY=python
if not defined PY (
  echo Python 3.9 or newer is needed. Install it from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" during setup, then run this again.
  pause
  exit /b 1
)

.venv\Scripts\python.exe -c "import sys" >nul 2>&1 || (
  if exist .venv rmdir /s /q .venv
  %PY% -m venv .venv || goto failed
)
.venv\Scripts\python.exe -m pip install -q --disable-pip-version-check -r requirements.txt || goto failed
.venv\Scripts\python.exe app.py --open || goto failed
exit /b 0

:failed
echo.
echo Something went wrong. Read the message above.
pause
exit /b 1
