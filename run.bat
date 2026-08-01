@echo off
REM ============================================================
REM  Friction Modelling - ONE-CLICK start
REM  Run this instead of setup.bat / run_website.bat / etc by hand.
REM  It will:
REM    1. Create + populate cmerivenv on Python 3.13 (only the first time)
REM    2. Show a menu to launch website / dashboard / pipeline / all
REM ============================================================

setlocal
cd /d "%~dp0"

if exist cmerivenv\Scripts\python.exe (
    goto :menu
)

echo.
echo ============================================================
echo  First run detected - setting up cmerivenv (this only happens once)
echo ============================================================

echo.
echo === Looking for Python 3.13 via the "py" launcher ===
py -3.13 --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python 3.13 was not found on this machine.
    echo Go to https://www.python.org/downloads/release/python-3130/
    echo install it, then re-run this script.
    echo.
    pause
    exit /b 1
)
py -3.13 --version

echo.
echo === Creating virtual environment in cmerivenv ===
py -3.13 -m venv cmerivenv

echo.
echo === Installing dependencies (this can take a few minutes) ===
call cmerivenv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip. See error above.
    pause
    exit /b 1
)

pip install --prefer-binary -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] A package failed to install ^(see error above^).
    pause
    exit /b 1
)

pip install -e .
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install the friction_modelling package itself.
    pause
    exit /b 1
)

if not exist outputs\params  mkdir outputs\params
if not exist outputs\figures mkdir outputs\figures
if not exist outputs\models  mkdir outputs\models

echo.
echo ============================================================
echo  Setup complete - moving on to the menu.
echo ============================================================
timeout /t 2 >nul

:menu
cls
call cmerivenv\Scripts\activate.bat
echo ============================================================
echo   Friction Modelling - what do you want to run?
echo ============================================================
echo   1. Website          (FastAPI + JS site   - http://localhost:8501)
echo   2. Dashboard        (Streamlit           - http://localhost:8502)
echo   3. Pipeline         (CLI: preprocess + all 3 models, no server)
echo   4. Website + Dashboard together (2 windows)
echo   5. Re-run setup / reinstall dependencies
echo   6. Exit
echo ============================================================
set /p choice="Enter choice (1-6): "

if "%choice%"=="1" (
    echo Starting website at http://localhost:8501 ...
    python -m friction_modelling.webapp --port 8501 --reload
    goto :menu
)
if "%choice%"=="2" (
    echo Starting Streamlit dashboard at http://localhost:8502 ...
    streamlit run dashboard\streamlit_app.py --server.port 8502
    goto :menu
)
if "%choice%"=="3" (
    set /p stage="Run which stage? (blank = all): "
    if "%stage%"=="" (
        python -m friction_modelling.cli all
    ) else (
        python -m friction_modelling.cli %stage%
    )
    pause
    goto :menu
)
if "%choice%"=="4" (
    start "Friction Modelling - Website" cmd /k "cd /d %~dp0 && call cmerivenv\Scripts\activate.bat && python -m friction_modelling.webapp --port 8501 --reload"
    start "Friction Modelling - Dashboard" cmd /k "cd /d %~dp0 && call cmerivenv\Scripts\activate.bat && streamlit run dashboard\streamlit_app.py --server.port 8502"
    echo Both launched in separate windows:
    echo   Website:   http://localhost:8501
    echo   Dashboard: http://localhost:8502
    pause
    goto :menu
)
if "%choice%"=="5" (
    rmdir /s /q cmerivenv
    call "%~f0"
    exit /b 0
)
if "%choice%"=="6" (
    exit /b 0
)

echo Invalid choice.
timeout /t 1 >nul
goto :menu