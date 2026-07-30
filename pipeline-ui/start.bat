@echo off
REM Starts the methylation pipeline builder and opens it in your browser.
cd /d "%~dp0"
python server\app.py --port 8765
pause
