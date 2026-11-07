@echo off
cd /d "%~dp0"
python scripts\local_preview.py
if errorlevel 1 (
  echo.
  echo Please check Python 3.10+ is installed, or read LOCAL_RUN.md.
  pause
)
