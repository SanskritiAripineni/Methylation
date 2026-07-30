@echo off
REM Starts the run console (sidebar launcher) and opens it in your browser.
REM Serves BOTH interfaces: /console-v2.html and the original /index.html.
REM start.bat is unchanged and still starts the original builder on its own.
cd /d "%~dp0"
python server\app_v2.py --port 8765
pause
