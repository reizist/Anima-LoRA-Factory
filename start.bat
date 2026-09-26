@echo off
setlocal
set PYTHONUTF8=1
cd /d %~dp0

:: Change this number if the port is already in use.
set APP_PORT=8000

echo [Anima LoRA Factory] Initializing...

:: Create virtual environment if it doesn't exist
if not exist venv\ (
    echo [INFO] Creating virtual environment venv...
    python -m venv venv
)

:: Set absolute path to venv python to prevent global Python interference
set VENV_PYTHON=%~dp0venv\Scripts\python.exe

:: Run setup check using the explicit venv python
"%VENV_PYTHON%" backend/setup_check.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Setup check failed. Please check the messages above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [Anima LoRA Factory] Starting backend server...
echo Access the GUI at http://localhost:%APP_PORT%
echo.

:: Start browser
start http://localhost:%APP_PORT%

:: Run backend using the explicit venv python
cd backend
"%VENV_PYTHON%" main.py

pause
