@echo off
rem Build the real-chain game exe: BrnMain -> CgsHardwareInit -> BrnGameModule ->
rem BrnRendererModule -> LoadingScreenRenderer (Option B loading-screen boot), now with the
rem resource/font subsystem so a loaded Default.font drives the bitmap debug text.
rem
rem The source list exceeds cmd's ~8191-char command-line limit, so the cl arguments (flags,
rem include dirs, sources, /Fo, /Fe) are written to a response file and passed via cl @file.
setlocal
set ROOT=%~dp0..
set SRC=%ROOT%\b5-decomp\src
set VEN=%ROOT%\b5-decomp\vendor
set RES=%ROOT%\b5-decomp\res
rem FFmpeg (movie player VP6/MP4 decode) - built by tools\build_ffmpeg.bat into vendor\ffmpeg-build\.
set FFM=%ROOT%\b5-decomp\vendor\ffmpeg-build
rem Game build output lives under build\game\ (build\tools\ holds the tool binaries; see build_tools.ps1).
set OUT=%ROOT%\build\game
set RSP=%OUT%\obj\build.rsp

call "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
if not exist "%OUT%\obj" mkdir "%OUT%\obj"

rc /fo"%OUT%\\obj\\burnout.res" "%RES%\burnout.rc"

rem ---- build the cl response file ----
> "%RSP%" (
  echo /nologo /EHsc /std:c++17 /permissive- /DWIN32 /D_WINDOWS
  echo /I"%SRC%" /I"%VEN%\EABase\include\Common" /I"%VEN%\EASTL\include" /I"%VEN%\EAThread\include" /I"%VEN%\renderware\include" /I"%FFM%\include"
  echo "%SRC%\GameSource\Main\BrnMain.cpp"
  echo "%SRC%\GameShared\GameClasses\System\PC\CgsHardwareInitPC.cpp"
  echo "%SRC%\GameShared\GameClasses\System\PC\CgsHardwareSkuPC.cpp"
  echo "%SRC%\GameShared\GameClasses\Core\CgsStringUtils.cpp"
  echo "%SRC%\GameShared\GameClasses\Core\CgsAssert.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\AssertSystem\CgsAssertManager.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\StackUnpick\CgsStackUnpick.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\MapFile\CgsMapFile.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\MapFile\Reader\CgsMapFileReader.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\MapFile\Reader\CgsMapFileReaderMinimalMemory.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\CgsStrStream.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\Log\CgsLog.cpp"
  echo "%SRC%\GameSource\Game\BrnGameModule.cpp"
  echo "%SRC%\GameSource\Game\BrnGlobalCpuMonitors.cpp"
  echo "%SRC%\GameSource\GameFlowController\TopLevel\BrnGameMainFlowStates.cpp"
  echo "%SRC%\GameSource\GameFlowController\TopLevel\BrnGameMainFlowController.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Timer\CgsFrameRate.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\PerfMon\Cpu\CgsPerfMonCpu.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\PerfMon\DebugComponent\CgsDebugComponentPerfMonCpu.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\CgsDebugManager.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\CgsDebugCollections.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\CgsDebugComponent.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\Internal\CgsDebugInternal.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\UI\CgsTypes.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\UI\CgsDebugUI.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\UI\Menu\CgsMenuItem.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\UI\Menu\CgsMenu.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\UI\Menu\CgsMenuManager.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\UI\Variables\CgsVariable.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\UI\Variables\CgsVariableManager.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\UI\Variables\CgsMenuItemVariable.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\UI\Functions\CgsFunction.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\UI\Functions\CgsFunctionManager.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\UI\Functions\CgsMenuItemFunction.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Render\CgsDebug2DImmediateRender.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Render\CgsDebugRender.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\VectorFont\CgsVectorFont.cpp"
  echo "%SRC%\GameShared\GameClasses\Module\CgsIOBufferStack.cpp"
  echo "%SRC%\GameShared\GameClasses\Module\CgsModule.cpp"
  echo "%SRC%\GameShared\GameClasses\Module\CgsModuleSingleBuffered.cpp"
  echo "%SRC%\GameShared\GameClasses\Module\CgsDataBuffer.cpp"
  echo "%SRC%\GameShared\GameClasses\Module\CgsDataStructure.cpp"
  echo "%VEN%\EAThread\source\eathread_rwmutex.cpp"
  echo "%VEN%\EAThread\source\eathread.cpp"
  echo "%VEN%\EAThread\source\eathread_mutex.cpp"
  echo "%VEN%\EAThread\source\eathread_condition.cpp"
  echo "%VEN%\EAThread\source\pc\eathread_thread_pc.cpp"
  echo "%VEN%\EAThread\source\pc\eathread_semaphore_pc.cpp"
  echo "%VEN%\EAThread\source\pc\eathread_callstack_win64.cpp"
  echo "%SRC%\GameSource\Graphics\BrnRendererModule.cpp"
  echo "%SRC%\GameSource\Graphics\BrnShaderConstantsFrame.cpp"
  echo "%SRC%\GameSource\Game\BrnLoadingScreenRenderer.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\ImmediateMode\CgsIm2d.cpp"
  echo "%SRC%\pc\gcm\renderengine\device.cpp"
  echo "%SRC%\pc\gcm\renderengine\texture.cpp"
  echo "%SRC%\pc\gcm\renderengine\texturestate.cpp"
  echo "%SRC%\pc\gcm\movie\MoviePlayer.cpp"
  echo "%SRC%\GameShared\GameClasses\Fonts\CgsFont.cpp"
  echo "%SRC%\GameShared\GameClasses\Fonts\CgsUnicode.cpp"
  echo "%SRC%\GameShared\GameClasses\Fonts\Resources\CgsFontResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\Font\CgsFontRenderer.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\CgsDebugFontBringUp.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Render\CgsDebug3DImmediateRender.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\CgsRwRasterResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\CgsRwTextureStateResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\CgsMaterialStateResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceTypeRegistration.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\Resources\CgsVideoDataResource.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceTypeRegistry.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceBundleLoader.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourcePool.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceHeap.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceBundle2.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsSmallResource.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceTypeBase.cpp"
  echo "%SRC%\GameShared\GameClasses\Memory\CgsLinearMalloc.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Timer\CgsTimeUtils.cpp"
  echo /Fo"%OUT%\\obj\\" /Fe"%OUT%\\Burnout_PC.exe"
)

cl /nologo @"%RSP%" /link /SUBSYSTEM:WINDOWS /MAP /LIBPATH:"%FFM%\bin" "%OUT%\\obj\\burnout.res" d3d9.lib user32.lib gdi32.lib kernel32.lib winmm.lib shell32.lib ole32.lib avformat.lib avcodec.lib avutil.lib swscale.lib swresample.lib

set "BUILD_ERR=%ERRORLEVEL%"
rem Convert the linker .map into the binary CgsMapFile the assert call-stack resolver reads.
if "%BUILD_ERR%"=="0" if exist "%OUT%\Burnout_PC.map" py "%ROOT%\tools\_make_cgsmap.py" "%OUT%\Burnout_PC.map" "%OUT%\Burnout_PC.cgsmap"
rem Stage the FFmpeg runtime DLLs next to the exe so the movie player loads at runtime.
if "%BUILD_ERR%"=="0" copy /Y "%FFM%\bin\*.dll" "%OUT%\" >nul

endlocal & exit /b %BUILD_ERR%
