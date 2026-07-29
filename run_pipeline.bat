@echo off
REM Runs preprocessing + physics + neural net + PINN models from the CLI,
REM without needing the website or dashboard running.
call .venv\Scripts\activate.bat
set FRICTION_DATA_ROOT=%~dp0data
set FRICTION_OUTPUT_ROOT=%~dp0outputs

if "%~1"=="" (
    echo Running full pipeline: preprocess -^> physics -^> nn -^> pinn
    python -m friction_modelling.cli all
) else (
    echo Running stage: %1
    python -m friction_modelling.cli %1
)
pause
