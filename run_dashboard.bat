@echo off
REM Launches the Streamlit dashboard on a different port than the website
REM so you can run both at once if you want to compare them.
call .venv\Scripts\activate.bat
set FRICTION_DATA_ROOT=%~dp0data
set FRICTION_OUTPUT_ROOT=%~dp0outputs
echo Starting Streamlit dashboard at http://localhost:8502 ...
streamlit run dashboard\streamlit_app.py --server.port 8502
