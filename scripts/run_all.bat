@echo off
echo Initializing Database and Seeding Data...
python scripts\seed_data.py
echo Starting Backend in new window...
start "Placement Prep Backend" cmd /k "python -m uvicorn backend.app.main:app --reload --port 8000"
echo Starting Frontend in new window...
start "Placement Prep Frontend" cmd /k "python -m streamlit run frontend\app.py"
echo Both services launched!
echo Backend: http://127.0.0.1:8000/docs
echo Frontend: http://localhost:8501
pause
