@echo off
REM Methylation Studio v4 on port 8769.
REM v3 is unchanged and still starts from start-studio.bat on 8767 - both can
REM run at the same time.
cd /d "%~dp0"
python server\app_v4.py --port 8769
pause
