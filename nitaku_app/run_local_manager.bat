@echo off
setlocal
cd /d "%~dp0"

REM Try to use pythonw.exe from the project virtual environment (.venv)
set "VENV_PYTHONW=..\.venv\Scripts\pythonw.exe"
if exist "%VENV_PYTHONW%" (
    start "" "%VENV_PYTHONW%" "local_manager.py"
    goto :success
)

REM Fallback to python.exe from the virtual environment
set "VENV_PYTHON=..\.venv\Scripts\python.exe"
if exist "%VENV_PYTHON%" (
    start "" "%VENV_PYTHON%" "local_manager.py"
    goto :success
)

REM If no virtual environment is found, try system Python
where py >nul 2>nul
if %errorlevel%==0 (
    REM Use start to launch Python as a detached process
    start "" pyw -3 "local_manager.py"
    goto :success
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "local_manager.py"
    goto :success
)

where python >nul 2>nul
if %errorlevel%==0 (
    REM Detach completely using start "" without /b
    start "" python "local_manager.py"
    goto :success
)

echo Python was not found.
echo Please install Python 3 and try again.
pause
goto :error

:success
REM Close this batch window immediately on success
exit