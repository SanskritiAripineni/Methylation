@echo off
REM Starts Methylation Studio - the simple interface - and opens it in your browser.
REM Also serves the advanced console (/console-v2.html) and the original
REM pipeline builder (/index.html) on the same port. Both older start scripts
REM still work on their own.
cd /d "%~dp0"
python server\app_v3.py --port 8765
pause
