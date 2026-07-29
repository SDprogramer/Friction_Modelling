@echo off
REM ============================================================
REM  Friction Modelling - local (no Docker) setup for Windows
REM  Creates a venv PINNED TO PYTHON 3.13 (not your system 3.14)
REM  because TensorFlow does not ship 3.14 wheels yet.
REM ============================================================

setlocal

echo.
echo === Step 1/4: Looking for Python 3.13 via the "py" launcher ===
py -3.13 --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python 3.13 was not found on this machine.
    echo Your system Python 3.14 is fine to keep - we just need 3.13
    echo ALSO installed side-by-side, purely for this project's venv.
    echo.
    echo 1. Go to https://www.python.org/downloads/release/python-3130/
    echo 2. Download "Windows installer (64-bit)"
    echo 3. During install, check "Add python.exe to PATH" is NOT required
    echo    - the "py" launcher will find it automatically.
    echo 4. Re-run this setup.bat after installing.
    echo.
    pause
    exit /b 1
)
echo Found:
py -3.13 --version

echo.
echo === Step 2/4: Creating virtual environment in .venv ===
if exist .venv (
    echo .venv already exists, skipping creation.
) else (
    py -3.13 -m venv .venv
)

echo.
echo === Step 3/4: Upgrading pip and installing dependencies ===
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip. See the error above.
    pause
    exit /b 1
)

pip install --prefer-binary -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] A package failed to install ^(see error above^).
    echo This usually means pip tried to compile something from source
    echo instead of using a prebuilt wheel. Copy the error and send it
    echo back for a fix - do not trust the "Setup complete" message below.
    pause
    exit /b 1
)

pip install -e .
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install the friction_modelling package itself.
    echo See the error above - this is why run_website.bat would fail
    echo with "ModuleNotFoundError: No module named 'friction_modelling'".
    pause
    exit /b 1
)

echo.
echo === Step 4/4: Creating output folders ===
if not exist outputs\params  mkdir outputs\params
if not exist outputs\figures mkdir outputs\figures
if not exist outputs\models  mkdir outputs\models

echo.
echo ============================================================
echo  Setup complete! The .venv now runs Python 3.13 with all
echo  dependencies (incl. TensorFlow) installed.
echo.
echo  Next steps:
echo    run_website.bat    -^> FastAPI + JS site  (http://localhost:8501)
echo    run_dashboard.bat  -^> Streamlit dashboard (http://localhost:8502)
echo    run_pipeline.bat   -^> run preprocessing + all 3 models from CLI
echo ============================================================
pause
