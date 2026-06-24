@echo off
rem Build a minimal SHARED FFmpeg (MSVC toolchain) into b5-decomp\vendor\ffmpeg-build\ for the movie
rem player (Phase 3 / VP6 + MP4). The actual build steps are in build_ffmpeg.sh (run under MSYS2 bash);
rem this wrapper puts the right toolchain on PATH:
rem   - cl/link  : VS2022 vcvars64
rem   - nasm/gcc : Strawberry Perl (C:\Strawberry\c\bin)   [asm is disabled, but configure probes it]
rem   - make/bash: MSYS2 (C:\msys64\usr\bin), appended so MSVC's link.exe wins over MSYS2's /usr/bin/link
setlocal
set ROOT=%~dp0..\..

where cl >nul 2>&1
if not errorlevel 1 goto toolchain_ready

set "VCVARS="
if defined VCVARS64 if exist "%VCVARS64%" set "VCVARS=%VCVARS64%"
for %%P in (
  "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
  "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat"
  "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat"
  "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
) do if not defined VCVARS if exist "%%~P" set "VCVARS=%%~P"

if not defined VCVARS (
  echo ERROR: Visual Studio 2022 vcvars64.bat not found. Set VCVARS64 to its full path.
  exit /b 1
)
call "%VCVARS%" >nul 2>&1
if errorlevel 1 (
  echo ERROR: Failed to initialize the MSVC toolchain from "%VCVARS%".
  exit /b 1
)

:toolchain_ready
set "PATH=C:\Strawberry\c\bin;%PATH%;C:\msys64\usr\bin"
set "MSYS2_PATH_TYPE=inherit"

C:\msys64\usr\bin\bash.exe "%~dp0build_ffmpeg.sh" "%ROOT%"

endlocal & exit /b %ERRORLEVEL%
