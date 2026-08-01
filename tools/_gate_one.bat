@echo off
rem Race-safe single-TU compile gate (unique obj per input file, for parallel agents).
rem Usage: _gate_one.bat <abs-path-to.cpp>
setlocal
set ROOT=%~dp0..
set SRC=%ROOT%\b5-decomp\src
set VEN=%ROOT%\b5-decomp\vendor
set FFM=%ROOT%\b5-decomp\vendor\ffmpeg-build
rem Find vcvars64 across every VS 2022 edition, not just Enterprise. Hard-coding
rem Enterprise made this silently fail on a Community box -- the call was swallowed and
rem every run then died with "'cl' is not recognized", which reads as a broken TU rather
rem than a broken gate. Same fix as _gate_tu.bat.
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
cl /nologo /EHsc /std:c++17 /permissive- /DWIN32 /D_WINDOWS /c /Fo"%TEMP%\gate_%~n1.obj" ^
  /I"%SRC%" /I"%VEN%\EABase\include\Common" /I"%VEN%\EASTL\include" /I"%VEN%\EAThread\include" /I"%VEN%\renderware\include" /I"%VEN%\PPMalloc\include" /I"%VEN%\coreallocator\include" /I"%FFM%\include" /I"%VEN%\lua\src" ^
  "%~1"
