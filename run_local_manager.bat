@echo off
cd /d "%~dp0"

REM Try to use pythonw.exe from the virtual environment first
set "VENV_PYTHONW=.venv\Scripts\pythonw.exe"
if exist "%VENV_PYTHONW%" (
    start "" "%VENV_PYTHONW%" "local_manager.py"
    goto :success
)

REM Fallback to python.exe from the virtual environment
set "VENV_PYTHON=.venv\Scripts\python.exe"
if exist "%VENV_PYTHON%" (
    start "" "%VENV_PYTHON%" "local_manager.py"
    goto :success
)

REM If no virtual environment is found, try the system pythonw
start "" pythonw local_manager.py

:success
exit
