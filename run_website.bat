@echo off
REM Launches the FastAPI backend + static JS/HTML/CSS frontend.
REM No Node.js needed - FastAPI serves the static/ folder directly.
call .venv\Scripts\activate.bat
set FRICTION_DATA_ROOT=%~dp0data
set FRICTION_OUTPUT_ROOT=%~dp0outputs
echo Starting website at http://localhost:8501 ...
python -m friction_modelling.webapp --port 8501 --reload
