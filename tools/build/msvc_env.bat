@echo off
rem tools\build\msvc_env.bat -- THE one MSVC locator for this repo. `call` this from a
rem consumer batch; it configures the CALLER's environment (deliberately no setlocal).
rem Resolution order:
rem   a) cl already on PATH *and* reporting "Version 19." -> trust it. Preserves the CI
rem      fast path (ilammy/msvc-dev-cmd) and rejects the Xbox 360 SDK's ancient cl 14.x
rem      that shadows PATH on 360-SDK machines.
rem   b) VCVARS64 env var -> that vcvars64.bat.
rem   c) Default VS2022 install paths (Community/Enterprise/Professional/BuildTools).
rem   d) vswhere.exe (the VS installer's locator) -> newest install with the C++ x64
rem      toolset. Rescues non-C:\ / renamed installs. Preview-only boxes: set VCVARS64.
rem On success: sets MSVC_ENV_SOURCE (path-cl|vcvars64-env|probed|vswhere) and
rem MSVC_VCVARS (vcvars used; empty for path-cl), prints one "[msvc_env] using" line,
rem exit /b 0. On failure: named error, exit /b 1.
rem IMPORTANT: probe with "where cl" BEFORE piping cl into findstr. Piping a command
rem that is not on PATH (cl 2>&1 | findstr ...) aborts the whole batch with exit 255.

where cl >nul 2>&1
if errorlevel 1 goto find_vcvars
cl 2>&1 | findstr /C:"Version 19." >nul 2>&1
if errorlevel 1 goto find_vcvars
set "MSVC_ENV_SOURCE=path-cl"
set "MSVC_VCVARS="
echo [msvc_env] using cl already on PATH -- MSVC 19.x
exit /b 0

:find_vcvars
set "MSVC_VCVARS="
set "MSVC_ENV_SOURCE="
if not defined VCVARS64 goto try_probes
if exist "%VCVARS64%" (
  set "MSVC_VCVARS=%VCVARS64%"
  set "MSVC_ENV_SOURCE=vcvars64-env"
  goto call_vcvars
)
echo [msvc_env] WARNING: VCVARS64 is set but not found: "%VCVARS64%" -- auto-detecting instead.

:try_probes
for %%P in (
  "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
  "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat"
  "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat"
  "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
) do if not defined MSVC_VCVARS if exist "%%~P" set "MSVC_VCVARS=%%~P"
if not defined MSVC_VCVARS goto try_vswhere
set "MSVC_ENV_SOURCE=probed"
goto call_vcvars

:try_vswhere
set "MSVC_VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%MSVC_VSWHERE%" goto fail
set "MSVC_VSDIR="
for /f "usebackq delims=" %%I in (`"%MSVC_VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "MSVC_VSDIR=%%I"
if not defined MSVC_VSDIR goto fail
if not exist "%MSVC_VSDIR%\VC\Auxiliary\Build\vcvars64.bat" goto fail
set "MSVC_VCVARS=%MSVC_VSDIR%\VC\Auxiliary\Build\vcvars64.bat"
set "MSVC_ENV_SOURCE=vswhere"
goto call_vcvars

:call_vcvars
call "%MSVC_VCVARS%" >nul 2>&1
if errorlevel 1 (
  echo [msvc_env] ERROR: vcvars64 failed to initialize: "%MSVC_VCVARS%"
  exit /b 1
)
where cl >nul 2>&1
if errorlevel 1 (
  echo [msvc_env] ERROR: vcvars64 ran but cl is still not on PATH: "%MSVC_VCVARS%"
  exit /b 1
)
cl 2>&1 | findstr /C:"Version 19." >nul 2>&1
if errorlevel 1 (
  echo [msvc_env] ERROR: cl on PATH is not MSVC 19.x after vcvars ^(Xbox 360 SDK cl shadowing?^) -- check "%MSVC_VCVARS%"
  exit /b 1
)
set "MSVC_VSWHERE="
set "MSVC_VSDIR="
echo [msvc_env] using %MSVC_ENV_SOURCE%: "%MSVC_VCVARS%"
exit /b 0

:fail
echo [msvc_env] ERROR: no MSVC 19.x toolchain found. Tried, in order:
echo   1. cl already on PATH reporting "Version 19."
echo   2. the VCVARS64 environment variable
echo   3. default VS2022 paths (Community/Enterprise/Professional/BuildTools)
echo   4. vswhere.exe (no install with the C++ x64 toolset)
echo Install VS2022 "Desktop development with C++", or set VCVARS64, e.g.:
echo   set "VCVARS64=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
echo (VS Preview-only machines must use VCVARS64 -- vswhere is queried without -prerelease.)
exit /b 1
