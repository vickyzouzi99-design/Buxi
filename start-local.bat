@echo off
cd /d "%~dp0"
python scripts\local_preview.py
if errorlevel 1 (
 echo Install dependencies first: python -m pip install -r server\requirements.txt
 pause
)
