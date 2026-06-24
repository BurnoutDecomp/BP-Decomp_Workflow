@echo off
rem Build a minimal SHARED FFmpeg (MSVC toolchain) into b5-decomp\vendor\ffmpeg-build\ for the movie
rem player (Phase 3 / VP6 + MP4). The actual build steps are in build_ffmpeg.sh (run under MSYS2 bash);
rem this wrapper puts the right toolchain on PATH:
rem   - cl/link  : VS2022 vcvars64
rem   - nasm/gcc : Strawberry Perl (C:\Strawberry\c\bin)   [asm is disabled, but configure probes it]
rem   - make/bash: MSYS2 (C:\msys64\usr\bin), appended so MSVC's link.exe wins over MSYS2's /usr/bin/link
setlocal
set ROOT=%~dp0..\..

call "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 (
    echo ERROR: vcvars64 not found - adjust the path in build_ffmpeg.bat.
    exit /b 1
)

set "PATH=C:\Strawberry\c\bin;%PATH%;C:\msys64\usr\bin"
set "MSYS2_PATH_TYPE=inherit"

C:\msys64\usr\bin\bash.exe "%~dp0build_ffmpeg.sh" "%ROOT%"

endlocal & exit /b %ERRORLEVEL%
