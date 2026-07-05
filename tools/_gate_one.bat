@echo off
rem Race-safe single-TU compile gate (unique obj per input file, for parallel agents).
rem Usage: _gate_one.bat <abs-path-to.cpp>
setlocal
set ROOT=%~dp0..
set SRC=%ROOT%\b5-decomp\src
set VEN=%ROOT%\b5-decomp\vendor
set FFM=%ROOT%\b5-decomp\vendor\ffmpeg-build
call "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cl /nologo /EHsc /std:c++17 /permissive- /DWIN32 /D_WINDOWS /c /Fo"%TEMP%\gate_%~n1.obj" ^
  /I"%SRC%" /I"%VEN%\EABase\include\Common" /I"%VEN%\EASTL\include" /I"%VEN%\EAThread\include" /I"%VEN%\renderware\include" /I"%VEN%\PPMalloc\include" /I"%VEN%\coreallocator\include" /I"%FFM%\include" /I"%VEN%\lua\src" ^
  "%~1"
