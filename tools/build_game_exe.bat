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
  "%SRC%\GameShared\GameClasses\Core\CgsAssert.cpp" ^
  "%SRC%\GameShared\GameClasses\Development\AssertSystem\CgsAssertManager.cpp" ^
  "%SRC%\GameShared\GameClasses\Development\CgsStrStream.cpp" ^
  "%SRC%\GameShared\GameClasses\Development\Log\CgsLog.cpp" ^
  "%SRC%\GameSource\Game\BrnGameModule.cpp" ^
  "%SRC%\GameSource\Game\BrnGlobalCpuMonitors.cpp" ^
  "%SRC%\GameSource\GameFlowController\TopLevel\BrnGameMainFlowStates.cpp" ^
  "%SRC%\GameSource\GameFlowController\TopLevel\BrnGameMainFlowController.cpp" ^
  "%SRC%\GameShared\GameClasses\System\Timer\CgsFrameRate.cpp" ^
  "%SRC%\GameShared\GameClasses\Development\PerfMon\Cpu\CgsPerfMonCpu.cpp" ^
  "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\CgsDebugManager.cpp" ^
  "%SRC%\GameShared\GameClasses\Module\CgsIOBufferStack.cpp" ^
  "%SRC%\GameShared\GameClasses\Module\CgsModule.cpp" ^
  "%SRC%\GameShared\GameClasses\Module\CgsModuleSingleBuffered.cpp" ^
  "%SRC%\GameShared\GameClasses\Module\CgsDataBuffer.cpp" ^
  "%SRC%\GameShared\GameClasses\Module\CgsDataStructure.cpp" ^
  "%VEN%\EAThread\source\eathread_rwmutex.cpp" ^
  "%VEN%\EAThread\source\eathread.cpp" ^
  "%VEN%\EAThread\source\eathread_mutex.cpp" ^
  "%VEN%\EAThread\source\eathread_condition.cpp" ^
  "%VEN%\EAThread\source\pc\eathread_thread_pc.cpp" ^
  "%VEN%\EAThread\source\pc\eathread_semaphore_pc.cpp" ^
  "%VEN%\EAThread\source\pc\eathread_callstack_win64.cpp" ^
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
