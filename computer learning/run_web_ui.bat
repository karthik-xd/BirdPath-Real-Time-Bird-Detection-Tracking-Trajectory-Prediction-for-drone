@echo off
title BirdPath // Computer Learning Studio
cd /d "%~dp0"
echo =====================================================================
echo          BirdPath // Computer Learning Studio (YouTube Web UI)
echo =====================================================================
echo Starting FastAPI Web Server at http://localhost:8000 ...
start http://localhost:8000
python server.py
pause
