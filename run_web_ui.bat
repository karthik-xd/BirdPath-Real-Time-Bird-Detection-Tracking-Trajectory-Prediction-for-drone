@echo off
title BirdPath // Computer Learning Studio
cd /d "%~dp0computer learning"
echo Starting FastAPI Web Server at http://localhost:8000 ...
start http://localhost:8000
python server.py
pause
