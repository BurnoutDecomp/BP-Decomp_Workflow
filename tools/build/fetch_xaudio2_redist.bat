@echo off
rem Fetch the Microsoft XAudio2 Redistributable (Microsoft.XAudio2.Redist on nuget.org)
rem into b5-decomp\vendor\xaudio2redist.
rem
rem WHY: CgsSystem::AudioOutputPC is an XAudio2 2.9 backend. The in-box xaudio2_9.dll only
rem exists on Windows 10 1803+; the redist is that same 2.9 engine shipped as
rem xaudio2_9redist.dll, supported down to Windows 7 SP1. Redistributing the DLL beside the
rem game exe is what its LICENSE.txt grants (a copy lands in the vendor dir).
rem
rem Layout produced (gitignored, like vendor\ffmpeg-build):
rem   vendor\xaudio2redist\include\*Redist.h      the real headers (NOT the xaudio2.h etc.
rem                                               shims -- those would shadow the Windows
rem                                               SDK copies for every TU in the build)
rem   vendor\xaudio2redist\bin\x64\xaudio2_9redist.dll   copied beside Burnout_PC.exe
rem   vendor\xaudio2redist\lib\x64\xaudio2_9redist.lib   import lib (unused: the backend
rem                                               LoadLibrary/GetProcAddress's XAudio2Create
rem                                               so a missing DLL degrades to "muted")
rem   vendor\xaudio2redist\LICENSE.txt
rem
rem Usage:  tools\build\fetch_xaudio2_redist.bat [version] [--force]   (default version below)
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "VER=1.2.13"
set "FORCE="
for %%A in (%*) do (
  if /I "%%~A"=="--force" ( set "FORCE=1" ) else ( set "VER=%%~A" )
)
set "DEST=%ROOT%\b5-decomp\vendor\xaudio2redist"
set "STAGE=%TEMP%\xaudio2redist-%VER%"

if not defined FORCE if exist "%DEST%\bin\x64\xaudio2_9redist.dll" if exist "%DEST%\include\xaudio2Redist.h" (
  echo XAudio2 redist already present in "%DEST%" -- pass --force to re-fetch.
  endlocal & exit /b 0
)

rem curl.exe + tar.exe (bsdtar, reads zip) ship with Windows 10 1803+; a .nupkg IS a zip.
if exist "%STAGE%" rd /s /q "%STAGE%"
mkdir "%STAGE%" 2>nul
echo Downloading Microsoft.XAudio2.Redist %VER% from nuget.org ...
curl.exe -L --fail --retry 3 -o "%STAGE%\pkg.zip" "https://api.nuget.org/v3-flatcontainer/microsoft.xaudio2.redist/%VER%/microsoft.xaudio2.redist.%VER%.nupkg"
if errorlevel 1 ( echo ERROR: XAudio2 redist download failed. & endlocal & exit /b 1 )
tar.exe -xf "%STAGE%\pkg.zip" -C "%STAGE%"
if errorlevel 1 ( echo ERROR: XAudio2 redist extract failed. & endlocal & exit /b 1 )

set "NAT=%STAGE%\build\native"
if not exist "%NAT%\release\bin\x64\xaudio2_9redist.dll" (
  echo ERROR: package lacked build\native\release\bin\x64\xaudio2_9redist.dll
  endlocal & exit /b 1
)
for %%D in ("%DEST%\include" "%DEST%\bin\x64" "%DEST%\lib\x64") do if not exist "%%~D" mkdir "%%~D"
rem Only the *Redist.h headers: the package's xaudio2.h / xapo.h / xapobase.h / x3daudio.h /
rem xaudio2fx.h / xapofx.h are one-line shims that would shadow the SDK headers of the same
rem name for the whole build once this dir is on the /I list.
copy /Y "%NAT%\include\*Redist.h" "%DEST%\include\" >nul
if errorlevel 1 ( echo ERROR: header copy failed. & endlocal & exit /b 1 )
copy /Y "%NAT%\release\bin\x64\xaudio2_9redist.dll" "%DEST%\bin\x64\" >nul
copy /Y "%NAT%\release\lib\x64\xaudio2_9redist.lib" "%DEST%\lib\x64\" >nul
copy /Y "%STAGE%\LICENSE.txt" "%DEST%\" >nul
echo %VER%> "%DEST%\VERSION.txt"
rd /s /q "%STAGE%" 2>nul

if not exist "%DEST%\include\xaudio2Redist.h" ( echo ERROR: xaudio2Redist.h missing after copy. & endlocal & exit /b 1 )
echo XAudio2 redist %VER% installed to "%DEST%".
endlocal & exit /b 0
