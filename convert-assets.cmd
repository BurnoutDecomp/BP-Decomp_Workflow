@echo off
setlocal
title Paradise Asset Converter
cd /d "%~dp0"
REM Test the actual interpreter, including its version, instead of trusting PATH.
set "ASSET_PY="
for %%P in (python python3 py) do (
    if not defined ASSET_PY (
        %%P -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
        if not errorlevel 1 set "ASSET_PY=%%P"
    )
)
if not defined ASSET_PY (
    echo Python 3.11 or newer is required.
    echo Install Python from https://www.python.org/downloads/windows/
    echo Enable "Add python.exe to PATH", then launch this script again.
    pause
    exit /b 1
)
%ASSET_PY% -u "%~dp0tools\assets\converter_ui\server.py" %*
if errorlevel 1 pause
endlocal
