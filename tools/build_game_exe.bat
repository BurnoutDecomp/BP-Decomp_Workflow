@echo off
rem Compatibility entry point. The implementation lives under tools\build\.
call "%~dp0build\build_game_exe.bat" %*
exit /b %ERRORLEVEL%
