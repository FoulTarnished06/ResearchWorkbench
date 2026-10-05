@echo off
title ResearchWorkbench - Comparative Study Web App
echo ======================================================================
echo    Starting ResearchWorkbench Comparative Study Harness (Port 8501)
echo ======================================================================
echo.
echo Launching your web browser...
start http://127.0.0.1:8501
echo.
python evals\ui_server.py
pause
