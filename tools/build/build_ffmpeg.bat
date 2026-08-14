@echo off
rem Build a minimal SHARED FFmpeg (MSVC toolchain) into b5-decomp\vendor\ffmpeg-build\
rem for the movie player (VP6 + MP4 + EA XMA). Build steps live in build_ffmpeg.sh
rem (run under MSYS2 bash); this wrapper puts the right toolchain on PATH:
rem   - cl/link  : resolved by tools\build\msvc_env.bat (VCVARS64 env override supported)
rem   - nasm/gcc : Strawberry Perl  [asm is disabled, but configure probes it]
rem   - make/bash: MSYS2, appended so MSVC's link.exe wins over MSYS2's /usr/bin/link
rem Env overrides: MSYS2_ROOT (default C:\msys64), STRAWBERRY_ROOT (default C:\Strawberry).
rem NO-COMPILER ALTERNATIVE:  build_ffmpeg.bat --prebuilt   downloads the CI-proven
rem prebuilt (release "ffmpeg-prebuilt" of BurnoutDecomp/FFmpeg-Xenia-new) instead.
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
if /I "%~1"=="--prebuilt" goto prebuilt

if not defined MSYS2_ROOT set "MSYS2_ROOT=C:\msys64"
if not defined STRAWBERRY_ROOT set "STRAWBERRY_ROOT=C:\Strawberry"
if not exist "%MSYS2_ROOT%\usr\bin\bash.exe" (
  echo ERROR: MSYS2 not found -- "%MSYS2_ROOT%\usr\bin\bash.exe" is missing.
  echo   Install MSYS2 from https://www.msys2.org/ or set MSYS2_ROOT to your install dir.
  echo   OR skip the source build entirely:  tools\build\build_ffmpeg.bat --prebuilt
  exit /b 1
)
if not exist "%STRAWBERRY_ROOT%\c\bin" (
  echo ERROR: Strawberry Perl not found -- "%STRAWBERRY_ROOT%\c\bin" is missing.
  echo   Install Strawberry Perl from https://strawberryperl.com/ or set STRAWBERRY_ROOT.
  echo   OR skip the source build entirely:  tools\build\build_ffmpeg.bat --prebuilt
  exit /b 1
)
if not exist "%ROOT%\b5-decomp\vendor\FFmpeg\configure" (
  echo ERROR: FFmpeg source submodule not populated: b5-decomp\vendor\FFmpeg
  echo   Run: git -C b5-decomp submodule update --init vendor/FFmpeg
  echo   OR skip the source build entirely:  tools\build\build_ffmpeg.bat --prebuilt
  exit /b 1
)

call "%~dp0msvc_env.bat"
if errorlevel 1 exit /b 1

set "PATH=%STRAWBERRY_ROOT%\c\bin;%PATH%;%MSYS2_ROOT%\usr\bin"
set "MSYS2_PATH_TYPE=inherit"

"%MSYS2_ROOT%\usr\bin\bash.exe" "%~dp0build_ffmpeg.sh" "%ROOT%"

endlocal & exit /b %ERRORLEVEL%

:prebuilt
rem Same asset CI uses (.github\workflows\build-and-publish.yml). curl.exe + tar.exe
rem ship with Windows 10 1803+; tar (bsdtar) extracts zip archives.
set "DEST=%ROOT%\b5-decomp\vendor\ffmpeg-build"
if not exist "%DEST%" mkdir "%DEST%"
curl.exe -L --fail --retry 3 -o "%TEMP%\ffmpeg-build.zip" "https://github.com/BurnoutDecomp/FFmpeg-Xenia-new/releases/download/ffmpeg-prebuilt/ffmpeg-build.zip"
if errorlevel 1 ( echo ERROR: prebuilt FFmpeg download failed. & exit /b 1 )
tar.exe -xf "%TEMP%\ffmpeg-build.zip" -C "%DEST%"
if errorlevel 1 ( echo ERROR: prebuilt FFmpeg extract failed. & exit /b 1 )
del /q "%TEMP%\ffmpeg-build.zip" 2>nul
if not exist "%DEST%\bin\avcodec.lib" ( echo ERROR: prebuilt zip lacked bin\avcodec.lib & exit /b 1 )
echo Prebuilt FFmpeg installed to "%DEST%".
endlocal & exit /b 0
