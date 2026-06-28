@echo off
REM Convenience shim so you can type `work <cmd>` from the repo root.
REM Detect an available Python launcher: python, python3, then py.
set "PY_CMD="
for %%P in (python python3 py) do (
    if not defined PY_CMD (
        where %%P >nul 2>nul && set "PY_CMD=%%P"
    )
)
if not defined PY_CMD (
    echo work: could not find a Python interpreter ^(tried python, python3, py^). 1>&2
    exit /b 1
)
%PY_CMD% "%~dp0tools\work\work.py" %*
