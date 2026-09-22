@echo off
echo Starting Placement Preparation Agent - FastAPI Backend...
python -m uvicorn backend.app.main:app --reload --port 8000
pause
