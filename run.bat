@echo off
cd /d "%~dp0"

if exist .venv\installed goto run

echo First-time setup, this takes a minute or two...
python -m venv .venv
if errorlevel 1 goto nopython
.venv\Scripts\python -m pip install --quiet -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python -m playwright install chromium
if errorlevel 1 goto failed
echo done > .venv\installed

:run
.venv\Scripts\python auto_enroll.py
pause
exit /b

:nopython
echo.
echo Python wasn't found. Install it from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" in the installer, then run this again.
pause
exit /b 1

:failed
echo.
echo Setup failed - see the error above. Fix it and run this again.
pause
exit /b 1
