@echo off
rem Build the real-chain game exe: BrnMain -> CgsHardwareInit -> BrnGameModule ->
rem BrnRendererModule -> LoadingScreenRenderer (Option B loading-screen boot). Replaces the
rem throwaway BrnLoadingScreenHost + pc/WinMain with the reconstructed boot/render chain.
setlocal
set ROOT=%~dp0..
set SRC=%ROOT%\b5-decomp\src
set VEN=%ROOT%\b5-decomp\vendor
set OUT=%ROOT%\build

call "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
if not exist "%OUT%\obj" mkdir "%OUT%\obj"

cl /nologo /EHsc /std:c++17 /permissive- /DWIN32 /D_WINDOWS ^
  /I"%SRC%" /I"%VEN%\EABase\include\Common" /I"%VEN%\EASTL\include" /I"%VEN%\EAThread\include" /I"%VEN%\renderware\include" ^
  "%SRC%\GameSource\Main\BrnMain.cpp" ^
  "%SRC%\GameShared\GameClasses\System\PC\CgsHardwareInitPC.cpp" ^
  "%SRC%\GameShared\GameClasses\System\PC\CgsHardwareSkuPC.cpp" ^
  "%SRC%\GameShared\GameClasses\Core\CgsStringUtils.cpp" ^
  "%SRC%\GameSource\Game\BrnGameModule.cpp" ^
  "%SRC%\GameSource\GameFlowController\TopLevel\BrnGameMainFlowStates.cpp" ^
  "%SRC%\GameSource\Graphics\BrnRendererModule.cpp" ^
  "%SRC%\GameSource\Graphics\BrnShaderConstantsFrame.cpp" ^
  "%SRC%\GameSource\Game\BrnLoadingScreenRenderer.cpp" ^
  "%SRC%\GameShared\GameClasses\Graphics\ImmediateMode\CgsIm2d.cpp" ^
  "%SRC%\pc\gcm\renderengine\device.cpp" ^
  "%SRC%\pc\gcm\renderengine\texture.cpp" ^
  "%SRC%\GameShared\GameClasses\Memory\CgsLinearMalloc.cpp" ^
  "%SRC%\GameShared\GameClasses\System\Timer\CgsTimeUtils.cpp" ^
  /Fo"%OUT%\obj\\" /Fe"%OUT%\BrnGame.exe" ^
  /link /SUBSYSTEM:WINDOWS d3d9.lib user32.lib gdi32.lib kernel32.lib winmm.lib shell32.lib ole32.lib

endlocal
exit /b %ERRORLEVEL%
