@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 csv_merger.py
    if errorlevel 1 pause
    exit /b
)
where python >nul 2>nul
if not errorlevel 1 (
    python csv_merger.py
    if errorlevel 1 pause
    exit /b
)
echo Python 3.10+ is required. Install Python with Tcl/Tk support, then try again.
pause
