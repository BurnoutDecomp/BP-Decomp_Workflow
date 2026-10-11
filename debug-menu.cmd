@echo off
setlocal
cd /d "%~dp0"
set "MENU_SEARCH_PY="
for %%P in (python python3 py) do (
    if not defined MENU_SEARCH_PY (
        %%P -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
        if not errorlevel 1 set "MENU_SEARCH_PY=%%P"
    )
)
if not defined MENU_SEARCH_PY (
    echo Python 3.11 or newer is required. Install Python and add it to PATH.
    pause
    exit /b 1
)
%MENU_SEARCH_PY% -u "%~dp0tools\debug_menu\search.py" %*
set "MENU_SEARCH_RESULT=%ERRORLEVEL%"
if not "%MENU_SEARCH_RESULT%"=="0" pause
exit /b %MENU_SEARCH_RESULT%
