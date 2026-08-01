@echo off
rem Single-TU compile gate. Usage: _gate_tu.bat <abs-path-to.cpp>
setlocal
set ROOT=%~dp0..
set SRC=%ROOT%\b5-decomp\src
set VEN=%ROOT%\b5-decomp\vendor
set FFM=%ROOT%\b5-decomp\vendor\ffmpeg-build
rem Find vcvars64 across every VS 2022 edition, not just Enterprise. This file used to
rem hard-code Enterprise; on a Community box the call silently failed and every gate run
rem then died with "'cl' is not recognized" -- which reads as a broken TU, not a broken
rem gate. Honour VCVARS64 if the caller sets it, and skip entirely if cl is already live.
where cl >nul 2>&1
if not errorlevel 1 goto have_cl
if defined VCVARS64 if exist "%VCVARS64%" call "%VCVARS64%" >nul 2>&1
where cl >nul 2>&1
if not errorlevel 1 goto have_cl
for %%E in (Community Professional Enterprise BuildTools) do (
  if exist "C:\Program Files\Microsoft Visual Studio\2022\%%E\VC\Auxiliary\Build\vcvars64.bat" (
    call "C:\Program Files\Microsoft Visual Studio\2022\%%E\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
    where cl >nul 2>&1
    if not errorlevel 1 goto have_cl
  )
)
echo ERROR: no VS 2022 vcvars64.bat found. Set VCVARS64 to its full path.
exit /b 1
:have_cl
cl /nologo /EHsc /std:c++17 /permissive- /DWIN32 /D_WINDOWS /c /Fo"%TEMP%\gate_tu.obj" ^
  /I"%SRC%" /I"%VEN%\EABase\include\Common" /I"%VEN%\EASTL\include" /I"%VEN%\EAThread\include" /I"%VEN%\renderware\include" /I"%VEN%\PPMalloc\include" /I"%VEN%\coreallocator\include" /I"%FFM%\include" /I"%VEN%\lua\src" ^
  %1
