@echo off
rem Build the vendored Lua 5.1.5 (the scripting VM the GUI/HUD FSMs run -- CgsFsm::ScriptedFsm)
rem into b5-decomp\vendor\lua\lua515.lib. Vanilla upstream source (lua.org, MIT); the same
rem Lua 5.1 the X360 ARTIST build statically links. Compiled as C (MSVC /TC).
rem   - cl : resolved by tools\build\msvc_env.bat (VCVARS64 env override supported)
setlocal
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set LUASRC=%ROOT%\b5-decomp\vendor\lua\src
set OBJ=%ROOT%\b5-decomp\vendor\lua\obj
set OUT=%ROOT%\b5-decomp\vendor\lua\lua515.lib

call "%~dp0msvc_env.bat"
if errorlevel 1 exit /b 1

if not exist "%OBJ%" mkdir "%OBJ%"
rem Object files land in the CWD (avoids the /Fo"dir\" trailing-backslash quote-escape gotcha).
cd /d "%OBJ%"
rem Lua core + standard libraries. Excludes the standalone interpreter/compiler (lua.c, luac.c, print.c).
cl /nologo /c /O2 /I"%LUASRC%" ^
 "%LUASRC%\lapi.c" "%LUASRC%\lcode.c" "%LUASRC%\ldebug.c" "%LUASRC%\ldo.c" "%LUASRC%\ldump.c" ^
 "%LUASRC%\lfunc.c" "%LUASRC%\lgc.c" "%LUASRC%\llex.c" "%LUASRC%\lmem.c" "%LUASRC%\lobject.c" ^
 "%LUASRC%\lopcodes.c" "%LUASRC%\lparser.c" "%LUASRC%\lstate.c" "%LUASRC%\lstring.c" "%LUASRC%\ltable.c" ^
 "%LUASRC%\ltm.c" "%LUASRC%\lundump.c" "%LUASRC%\lvm.c" "%LUASRC%\lzio.c" ^
 "%LUASRC%\lauxlib.c" "%LUASRC%\lbaselib.c" "%LUASRC%\ldblib.c" "%LUASRC%\liolib.c" "%LUASRC%\lmathlib.c" ^
 "%LUASRC%\loadlib.c" "%LUASRC%\loslib.c" "%LUASRC%\lstrlib.c" "%LUASRC%\ltablib.c" "%LUASRC%\linit.c"
if errorlevel 1 ( echo LUA_COMPILE_FAILED & exit /b 1 )
lib /nologo /out:"%OUT%" "%OBJ%\*.obj"
if errorlevel 1 ( echo LUA_LIB_FAILED & exit /b 1 )
echo Lua build complete: %OUT%
endlocal & exit /b 0
