@echo off
rem Race-safe single-TU compile gate (unique obj per input file, for parallel agents).
rem Usage: _gate_one.bat <abs-path-to.cpp>
rem CONTRACT: %TEMP%\gate_<basename>.obj EXISTS after the run  <=>  the TU compiled
rem clean (a stale obj from an earlier pass is deleted up front). Exit code = cl's.
rem Flags + include dirs are the canonical set in tools\build\msvc_flags.txt and
rem tools\build\msvc_includes.txt -- the same set the full exe build uses, including
rem /O2 /Gy, so the gate compiles exactly what ships.
setlocal
if "%~1"=="" ( echo usage: _gate_one.bat ^<abs-path-to.cpp^> & exit /b 2 )
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
call "%~dp0build\msvc_env.bat"
if errorlevel 1 exit /b 1
del /q "%TEMP%\gate_%~n1.obj" 2>nul
> "%TEMP%\gate_%~n1.rsp" (
  for /f "usebackq eol=# delims=" %%F in ("%ROOT%\tools\build\msvc_flags.txt") do echo %%F
  for /f "usebackq eol=# delims=" %%D in ("%ROOT%\tools\build\msvc_includes.txt") do echo /I"%ROOT%\%%D"
)
cl @"%TEMP%\gate_%~n1.rsp" /c /Fo"%TEMP%\gate_%~n1.obj" "%~1"
