@echo off
rem Build the real-chain game exe: BrnMain -> CgsHardwareInit -> BrnGameModule ->
rem BrnRendererModule -> LoadingScreenRenderer (Option B loading-screen boot), now with the
rem resource/font subsystem so a loaded Default.font drives the bitmap debug text.
rem
rem The source list exceeds cmd's ~8191-char command-line limit, so the cl arguments (flags,
rem include dirs, sources, /Fo, /Fe) are written to a response file and passed via cl @file.
rem Compile+link runs through tools\build\compile_exe.py -- incremental per-TU objs with
rem header-dep tracking, parallel cl, and an end-of-build warnings-and-errors summary --
rem falling back to the legacy single serial cl @file when no Python is present.
setlocal
rem Normalized ROOT: cl's command line, __FILE__/assert strings, the .map and the
rem .cgsmap all embed this spelling -- D:\...\BP-Decomp_Workflow\... instead of the
rem historical D:\...\tools\build\..\..\... (string-only change; code is identical).
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
set "SRC=%ROOT%\b5-decomp\src"
set "VEN=%ROOT%\b5-decomp\vendor"
set "RES=%ROOT%\b5-decomp\res"
rem FFmpeg (movie player VP6/MP4 decode) - tools\build\build_ffmpeg.bat (or --prebuilt).
set "FFM=%ROOT%\b5-decomp\vendor\ffmpeg-build"
rem XAudio2 Redistributable (CgsSystem::AudioOutputPC's 2.9 engine, Win7 SP1 and up)
rem - tools\build\fetch_xaudio2_redist.bat.
set "XA2=%ROOT%\b5-decomp\vendor\xaudio2redist"
rem Game build output lives under build\game\ (build\tools\ holds tool binaries; see tools\build\build_tools.ps1).
set "OUT=%ROOT%\build\game"
set "RSP=%OUT%\obj\build.rsp"
set "BASERSP=%OUT%\obj\base.rsp"
set "FLAGS_TXT=%~dp0msvc_flags.txt"
set "INCS_TXT=%~dp0msvc_includes.txt"

rem ---- prerequisites: fail fast with a named cause + the command that fixes it ----
if not exist "%SRC%\GameSource\Main\BrnMain.cpp" (
  echo ERROR: b5-decomp sources missing -- "%SRC%\GameSource\Main\BrnMain.cpp" not found.
  echo        Run: git submodule update --init b5-decomp   then re-run this script.
  exit /b 1
)
if not exist "%FFM%\include\libavcodec\avcodec.h" (
  echo ERROR: FFmpeg dev tree missing -- "%FFM%\include\libavcodec\avcodec.h" not found.
  echo        Run tools\build\build_ffmpeg.bat first, or fetch the CI prebuilt:
  echo        tools\build\build_ffmpeg.bat --prebuilt
  exit /b 1
)
if not exist "%FFM%\bin\avcodec.lib" (
  echo ERROR: FFmpeg import libs missing -- "%FFM%\bin\avcodec.lib" not found.
  echo        Run tools\build\build_ffmpeg.bat first ^(or --prebuilt^).
  exit /b 1
)
if not exist "%VEN%\lua\lua515.lib" (
  echo ERROR: Lua static lib missing -- "%VEN%\lua\lua515.lib" not found.
  echo        Run tools\build\build_lua.bat first.
  exit /b 1
)
if not exist "%XA2%\include\xaudio2Redist.h" (
  echo ERROR: XAudio2 redist missing -- "%XA2%\include\xaudio2Redist.h" not found.
  echo        CgsAudioOutputPC.cpp includes it. Run: tools\build\fetch_xaudio2_redist.bat
  exit /b 1
)
if not exist "%FLAGS_TXT%" ( echo ERROR: missing "%FLAGS_TXT%" & exit /b 1 )
if not exist "%INCS_TXT%" ( echo ERROR: missing "%INCS_TXT%" & exit /b 1 )

rem ---- LNK1104 trap: a RUNNING exe holds a write lock the linker will hit at the
rem very end of the build. Probe by opening for append (writes nothing) -- that is
rem the exact access the linker needs. NB a running exe CAN be renamed on Windows,
rem so a rename probe would NOT detect this; a write-open does.
if exist "%OUT%\Burnout_PC.exe" (
  2>nul >> "%OUT%\Burnout_PC.exe" (call )
  if errorlevel 1 (
    echo ERROR: "%OUT%\Burnout_PC.exe" is locked for writing -- the link would fail with LNK1104.
    tasklist /FI "IMAGENAME eq Burnout_PC.exe" /NH 2>nul | find /I "Burnout_PC.exe" >nul && echo        Burnout_PC.exe is RUNNING -- close the game and re-run.
    exit /b 1
  )
)

rem ---- toolchain: one shared resolver (fast path when cl 19.x is already live -- CI;
rem VCVARS64 override; probed/vswhere otherwise). See tools\build\msvc_env.bat.
call "%~dp0msvc_env.bat"
if errorlevel 1 exit /b 1

if not exist "%OUT%\obj" mkdir "%OUT%\obj"

rc /fo"%OUT%\\obj\\burnout.res" "%RES%\burnout.rc"
if errorlevel 1 (
  echo ERROR: rc failed on "%RES%\burnout.rc" -- burnout.res not produced.
  exit /b 1
)

rem ---- canonical flags + include dirs -> base.rsp (shared by the main RSP and the
rem device.cpp precompile; flag rationale lives in tools\build\msvc_flags.txt) ----
> "%BASERSP%" (
  for /f "usebackq eol=# delims=" %%F in ("%FLAGS_TXT%") do echo %%F
  for /f "usebackq eol=# delims=" %%D in ("%INCS_TXT%") do echo /I"%ROOT%\%%D"
)

rem ---- build the cl response file ----
copy /y "%BASERSP%" "%RSP%" >nul
>> "%RSP%" (
  echo "%SRC%\GameSource\Main\BrnMain.cpp"
  echo "%SRC%\GameSource\BrnBaselineLinkStubs.cpp"
  echo "%VEN%\coreallocator\source\icoreallocator_interface.cpp"
  echo "%VEN%\zlib\src\inflate.c"
  echo "%VEN%\zlib\src\inftrees.c"
  echo "%VEN%\zlib\src\inffast.c"
  echo "%VEN%\zlib\src\adler32.c"
  echo "%VEN%\zlib\src\crc32.c"
  echo "%VEN%\zlib\src\zutil.c"
  echo "%VEN%\zlib\src\uncompr.c"
  echo "%SRC%\GameShared\GameClasses\System\PC\CgsHardwareInitPC.cpp"
  echo "%SRC%\GameShared\GameClasses\System\PC\CgsCrashHandlerPC.cpp"
  echo "%SRC%\GameShared\GameClasses\System\PC\CgsHardwareSkuPC.cpp"
  echo "%SRC%\GameShared\GameClasses\System\PC\CgsAudioOutputPC.cpp"
  rem  CgsDacOutputPC.cpp -- the phase-D engine-to-device bridge: the rw Dac plug-in's
  rem  external fill callback standing in for the console XenonThread packet loop
  echo "%SRC%\GameShared\GameClasses\System\PC\CgsDacOutputPC.cpp"
  echo "%SRC%\GameShared\GameClasses\System\PC\CgsMovieAudioPC.cpp"
  echo "%SRC%\GameShared\GameClasses\System\PC\CgsXboxPlatformPC.cpp"
  echo "%SRC%\GameShared\GameClasses\System\PC\CgsXmaHardwarePC.cpp"
  rem dirtysdk vendor leaves (2026-08-26): LobbyNameCmp @0x82B10050, the table-driven
  rem name comparator the friends-list tranche promoted to extern "C".
  echo "%VEN%\dirtysdk\src\lobbyname.cpp"
  rem rw audio core -- the faithful mix engine. Minimal RWAC-init subset mounted
  rem 2026-08-25 faithful-audio-engine phase A2. Snd9Service stays unmounted -- its
  rem SNDSYS driver entries are console-only.
  echo "%VEN%\renderware\src\rw\audio\core\System.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\PlugIn.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\PlugInRegistry.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\Voice.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\TimerManager.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\TimerHandle.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\Profiler.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\DecoderRegistry.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\Decoder.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\EaXmaDec.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\EaXmaDec_wG_02.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\EaXmaDec_wG_03.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\EaXmaDec_wG_04.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\Pcm16BigDec.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\Xas1Dec.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\XasDec.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\Collection.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\Unpack0.cpp"
  rem  BitGetter.cpp -- the MSB-first bit reader the packed sample headers are parsed
  rem  with; its GetBits body was already reconstructed but the TU was never mounted.
  echo "%VEN%\renderware\src\rw\audio\core\BitGetter.cpp"
  rem ---- AEMS-cascade wave 2026-08-28: the RWAC factory registration pass plug-ins. ---------
  rem  GenericRwacFactory::GenericRwacFactory @0x826C17A0 registers every runtime plug-in
  rem  descriptor in console order -- these vendor TUs carry the getters plus the plug-in
  rem  bodies. Absent vendor homes -- SndPlayer1 and SubMix -- and the three custom game
  rem  descriptors are FLAG-skipped at the registration site.
  echo "%VEN%\renderware\src\rw\audio\core\AiffWriter.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\Iir2.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\BandPassIir2.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\HighPassIir2.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\HighShelfIir2.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\LowPassIir2.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\LowShelfIir2.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\PeakingIir2.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\Gain.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\Butterworth.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\plugins\HighPassButterworth.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\CompressorLimiter1.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\plugins\Limiter1.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\plugins\LowPassButterworth.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\plugins\Pan2D.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\plugins\Pan2D1.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\plugins\Pan2D1_embed_check.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\plugins\Pause.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\Rechannel.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\Resample.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\ReverbFilters.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\plugins\ReverbModel1.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\Send.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\Send_wL_01.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\MixKernels.cpp"
  rem  Delay.cpp + RawPuller2.cpp -- the ICF-shared GetSize bodies three Iir2 records and
  rem  the Gain record dispatch through (descriptor-record wave).
  echo "%VEN%\renderware\src\rw\audio\core\plugins\Delay.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\RawPuller2.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\DelayFilter.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\DelayLine.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\SubMixConnector.cpp"
  rem  SubMix.cpp -- the real SubMix plug-in home: the named mix bus, its by-name
  rem  registry statics, and the deferred create handler that pushes into them.
  echo "%VEN%\renderware\src\rw\audio\core\SubMix.cpp"
  rem  Mixer.cpp -- the mix executive: the per-audio-frame voice walk plus the typed
  rem  StackAllocator seeding. Dac.cpp -- the engine output plug-in, phase D
  echo "%VEN%\renderware\src\rw\audio\core\Mixer.cpp"
  rem  CpuLoadBalancer.cpp -- the CPU-load governor the Dac drives every mix frame
  echo "%VEN%\renderware\src\rw\audio\core\CpuLoadBalancer.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\plugins\Dac.cpp"
  echo "%VEN%\renderware\src\rw\audio\core\plugins\GainFader.cpp"
  rem  SinePlayer.cpp -- the debug sine source plug-in. It carried the phase-D audible
  rem  probe, since removed after the ear confirmation
  echo "%VEN%\renderware\src\rw\audio\core\plugins\SinePlayer.cpp"
  rem  SndPlayer1.cpp -- the engine sample player: the SOURCE stage of every splice
  rem  voice. Construction half only; the streaming half waits on the Stream surface.
  echo "%VEN%\renderware\src\rw\audio\core\plugins\SndPlayer1.cpp"
  rem  AEMS-cascade slice 2: the AemsRWSampleFactory MI home + its ctor and the Snd9 AEMS
  rem  layer -- AemsFactory::Create at stage 3 needs all three.
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\AEMS\CgsAemsInterfaceImplementation.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\AEMS\CgsAemsInterfaceImplementationFactoryDtor.cpp"
  echo "%SRC%\SDKs\EATech\include\snd\sndaems.cpp"
  echo "%SRC%\SDKs\EATech\include\snd\sndaems_linkclosure.cpp"
  echo "%SRC%\GameShared\GameClasses\System\PC\CgsStreamHeadersPC.cpp"
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
  rem GameBridgeControllerToX also carries the Director/World/GameState bridges; their IO
  rem callees (and those TUs' interface operator= homes) are linked below so the whole
  rem controller-bridge family resolves.
  echo "%SRC%\GameSource\Game\GameBridgeControllerToX.cpp"
  rem ---- tutorial-ticker leg (2026-08-16): the training-tip STRING-ID MAP. ----------------
  rem  BrnGame::ConvertTrainingTypeToStringId @0x823AA3B8 turns a BrnProgression::ETrainingType
  rem  into the GUI string id the bottom-of-screen tutorial ticker looks up in the language
  rem  data (type 2 -> "TRAINING_START_ENGINE" -> "Okay, let's just check this thing still
  rem  starts. Hold the accelerator (right trigger) to fire up the engine.").
  rem  ??? IT WAS BLOCKED ON DATA NOBODY HAD: the two rodata tables it indexes (off_82CDBF40 x77
  rem  and dword_82FAE290 x128) were `extern`-only, banner-marked "UNRECOVERABLE from this TU's
  rem  dossier". They are recovered now, straight out of the unpacked X360 image, and gated on
  rem  three independent controls (see the TU banner). MEASURED with cl /c + dumpbin /SYMBOLS
  rem  against build\game\obj: ZERO new unresolved externals -- the only UNDEFs are the three
  rem  CgsDev::Assert entry points already in the link.
  rem  ??? [tut-ticker] 2026-08-24: IT HAS A CALLER NOW -- TranslateGameActionsToGuiEvents case
  rem  148 (GameBridgeGameStateToX_StuntGuiEvents.cpp), fed by the mounted TrainingManager's
  rem  Update; the 537 consumer side is CustomRendererManager::RecvEvent (InGameMessageRenderer
  rem  itself still pending -- but its old wall, CgsGraphics::TextRenderer, is reconstructed in
  rem  CgsFontRenderer.cpp since the gateui waves).
  rem  SIBLING SPLIT: its owning GameBridgeGameStateToX.cpp DOES NOT COMPILE and did not before
  rem  this leg either (control-measured against HEAD's own copy: an ODR fork on
  rem  BrnGui::GuiTakedownEvent + a stale mpCgsGuiModule, both inside TranslateTakedownsToGuiEvents).
  rem  The function was MOVED, not copied, so folding it back later is a delete.
  echo "%SRC%\GameSource\Game\GameBridgeGameStateToX_TrainingStringIds.cpp"
  rem ---- P1 sim-pause (2026-08-25): the GUI --to-- GAME-STATE event bridge. -----------------
  rem  BridgeGuiToGameState @0x823DDB78 was reconstructed but had NO CALLER (the tree FLAGged
  rem  it "DELETE-WHEN it has a caller"). It has one now -- DoUpdate_GameStatePostWorld -- and
  rem  it is the ONLY producer of game event 93, the crash-nav pause event that reaches
  rem  RequestPause/RequestUnpause, actions 86/87, CheckGameActions, the sim timer.
  rem  SIBLING SPLIT: the parent GameBridgeGUIToX.cpp CANNOT be mounted -- its other two
  rem  members need six symbols with no home in the linked set (measured: exactly 6 LNK2019,
  rem  none of them from BridgeGuiToGameState), and TelemetryData::AddParameter has no home
  rem  at all. The function was MOVED, not copied, so folding it back later is a delete.
  echo "%SRC%\GameSource\Game\GameBridgeGUIToX_GameState.cpp"
  rem ---- faithful-audio phase C4 2026-08-28: the sound spine bridges go LIVE. ----------------
  rem  GameBridgeSoundToX.cpp carries BridgeSoundToTraining @0x823C63C0 and BridgeSoundToWorld
  rem  @0x823CDC98 -- both called every frame now by the C4 spine wiring in
  rem  BrnGameMainFlowStates.cpp -- DoPreUpdate_Sound plus DriveWorldUpdateFrame staging.
  echo "%SRC%\GameSource\Game\GameBridgeSoundToX.cpp"
  rem  SIBLING SPLIT of GameBridgeGUIToX.cpp -- BridgeGuiToSound @0x823C0A58 MOVED to its own
  rem  TU so it mounts without the parent TU's six un-homed symbols. Caller: the C4 spine.
  echo "%SRC%\GameSource\Game\GameBridgeGUIToX_Sound.cpp"
  rem  SIBLING SPLIT of GameBridgeGameStateToX.cpp -- BridgeGameStateToSound @0x823CDE50 MOVED
  rem  to its own TU, phase C4b: DoUpdate_Sound @0x823DCEC0 is its only console caller and the
  rem  in-game sound frame now drives it every frame.
  echo "%SRC%\GameSource\Game\GameBridgeGameStateToX_Sound.cpp"
  rem  Replay pre-sim OUTPUT buffer IO -- Construct + the GetStatusInterface pair. Mounted
  rem  for phase C4b: DoUpdate_Sound references the accessor for its replay-status install
  rem  seam even while the PC passes a null buffer.
  echo "%SRC%\GameSource\Replays\BrnReplayModuleIO.cpp"
  rem ---- camera wave (2026-08-01): the WORLD -> DIRECTOR seam. BridgeWorldToDirector --
  rem ---- @0x823E3AB0 is the only caller of InputBuffer::SetRaceCarInfo in the image;  --
  rem ---- without it every camera VehicleRef resolves to a zero transform.             --
  echo "%SRC%\GameSource\Game\GameBridgeWorldToX.cpp"
  rem ---- world-drive wave (2026-07-27): GameBridgeRendererToX.cpp carries the REAL --
  rem ---- BridgeRendererToWorld @0x823CDD20 (renderer-output -> world-dispatch-input --
  rem ---- handle copy) but is NOT mounted: the seven RendererIO::OutputBuffer getters --
  rem ---- it reads are declaration-only in the linked set (cost rule). Mount it with  --
  rem ---- BrnRendererModule::Update + the renderer-output accessor bodies.            --
  echo "%SRC%\GameShared\GameClasses\System\Input\CgsInputModuleIO.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Input\PC\CgsInputPadsPC.cpp"
  echo "%SRC%\GameShared\GameClasses\System\PC\CgsGuiSoundPC.cpp"
  echo "%SRC%\GameSource\Director\DirectorModule\BrnDirectorModuleIOInputBuffer.cpp"
  echo "%SRC%\GameSource\World\BrnWorldModuleIO.cpp"
  rem ---- world-render campaign: the real WorldModule + streaming producer ----
  rem (link-surface probe; the fleet TUs join as their link gaps are filled)
  rem (seam wave: the real ZoneList FixUp/FixDown home the ZoneListResourceType now calls)
  echo "%SRC%\GameShared\GameClasses\SceneManager\Zones\ZoneList.cpp"
  echo "%SRC%\GameSource\World\BrnWorldModule.cpp"
  echo "%SRC%\GameSource\World\EntityModules\WorldEntityModule\BrnWorldEntityModule.cpp"
  echo "%SRC%\GameSource\World\BrnWorldGraphicsStreamer.cpp"
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeEntityModulesToOutput.cpp"
  rem ---- world-drive wave (2026-07-27): the six sibling bridge TUs with REAL   ----
  rem ---- bodies (WorldBridgeEntityModulesToEntityModules / ...ToAI / ...ToCrash ---
  rem ---- / WorldBridgeCrashToEntityModules / WorldBridgeInputToEntityModules    ---
  rem ---- [MOUNTED 2026-08-11, see the driving-input wave note below] /           ---
  rem ---- WorldBridgePhysicsToScene) are NOT mounted: each drags 1-23 unresolved  ---
  rem ---- module-IO accessors/setters that are declaration-only (cost rule), so   ---
  rem ---- their bridges stay boot-gated in WorldLinkStubs.cpp. Mount them with    ---
  rem ---- the entity-module IO pass that lands those accessors.                   ---
  rem ---- car-select hand-off wave (2026-08-01): ONE of those six bridges is      ---
  rem ---- fully closed on its own -- BridgeRaceCarModuleToWorldModule_PreScene    ---
  rem ---- @0x827A52B0, the ONLY producer of WorldModule::                         ---
  rem ---- meLocalPlayerActiveRaceCarIndex. It shared a TU with two bridges that   ---
  rem ---- need 3 declaration-only IO accessors (MEASURED: +3 unresolved for the   ---
  rem ---- whole TU, 0 for this function alone), so the inert WorldLinkStubs copy  ---
  rem ---- is what linked and the player index stayed -1 all session. Split into   ---
  rem ---- its own TU and mounted. Fold back when those 3 accessors land.          ---
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeRaceCarToWorldModule.cpp"
  rem ---- feed wave (2026-08-09): the SECOND split-out bridge, same reason as the one ----
  rem ---- above. WorldModule::BridgeInputToPhysicsModule @0x827AB830 (an address that   ----
  rem ---- had to be recovered from the image -- it is a HOLE in the IDA export set) is  ----
  rem ---- the physics module's per-frame INPUT FEED and is fully closed on its own,     ----
  rem ---- while its DWARF file-mate BridgeInputToEntityModules still is not. Fold back  ----
  rem ---- when WorldBridgeInputToEntityModules.cpp can be mounted whole.                ----
  rem ---- (2026-08-11: it now IS mounted -- see the next block. The two are still split ----
  rem ----  TUs; folding them back into one DWARF-home TU is a follow-up.)               ----
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeInputToPhysicsModule.cpp"
  rem ---- driving-input wave (2026-08-11): the DWARF file-mate above is now MOUNTED WHOLE. ----
  rem ---- WorldModule::BridgeInputToEntityModules @0x827ADF88 is the ONLY caller in the    ----
  rem ---- image of RaceCarEntityModuleIO::InputBuffer_PreScene::SetPlayerVehicleControls,  ----
  rem ---- i.e. the last hop between the wired keyboard/pad input and the player car; while ----
  rem ---- it was a WorldLinkStubs gate the controls stopped at the world input buffer.     ----
  rem ---- MEASURED closure (dumpbin over the linked obj set): the TU raised 21 unresolved  ----
  rem ---- project externals; all 21 are bodied this wave (4 BrnWorldIO::UpdateInputBuffer  ----
  rem ---- const getters, 15 RaceCarEntityModuleIO PreScene/PrePhysics setters -- 6 of them ----
  rem ---- X360 header-inlines, now header-inline here too -- the prop replay-status setter ----
  rem ---- in its new home TU below, and TriggerEntityModuleIO::InputBuffer_PreScene::      ----
  rem ---- GetInputInterface, which was already committed in a TU nobody had mounted.       ----
  rem ---- The WorldLinkStubs gate is retired (tombstoned there); leaving both = LNK2005.   ----
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeInputToEntityModules.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropEntityModuleIO_InputBuffer_PreScene.cpp"
  echo "%SRC%\GameSource\World\EntityModules\TriggerEntityModule\BrnTriggerEntityModuleIO_Accessors.cpp"
  rem ---- root-cause wave (2026-08-10): the PRE-SCENE entity-modules -> physics bridge  ----
  rem ---- @0x827AADB8. It is the ONLY caller in the image of InputBuffer::              ----
  rem ---- SetSolverMaxIterations, so while it was a boot gate the solver iteration cap  ----
  rem ---- stayed 0 and the whole MaxIterations chain asserted. Its file-mate            ----
  rem ---- _PrePhysics @0x827AAEC0 is still a gate and stays in WorldLinkStubs.          ----
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeEntityModulesToPhysics.cpp"
  echo "%SRC%\GameSource\World\Bridges\WorldBridgePropModule.cpp"
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeCrashPostScene.cpp"
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeCrashInputs.cpp"
  rem ---- physics->output publish wave (2026-08-11): the RETURN direction of the same    ----
  rem ---- handover. WorldModule::BridgePhysicsModuleToRaceCarModule_PostPhysics          ----
  rem ---- @0x827AE9D0 is the ONLY thing in the image that copies the physics module's    ----
  rem ---- output buffer into the race-car module's post-physics INPUT buffer, so while   ----
  rem ---- it was a WorldLinkStubs gate the landed readback (ReadUpdatedActiveRaceCar-    ----
  rem ---- DataFromPhysics) could never see a set mUsedRaceCars bit and every active car  ----
  rem ---- fell through to the bring-up pose stand-in. Two of its six legs are live; the  ----
  rem ---- other four are parked LOUDLY in the TU (opaque physics-output seats).          ----
  rem ---- Its WorldLinkStubs gate is DELETED; leaving both = LNK2005.                    ----
  echo "%SRC%\GameSource\World\Bridges\WorldBridgePhysicsToEntityModules.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnRaceCarEntityModule.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnRaceCarEntityModule_CrashExit.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnRaceCarEntityModule_ResetPump.cpp"
  rem UpdateRaceCarCollisionTagging + UpdateActiveRaceCarTransforms -- the two per-frame
  rem drivers of ActiveRaceCar::mPrevTransforms (the reset-on-track ring).
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnRaceCarEntityModule_ResetOnTrack.cpp"
  rem START_PLAYING_MODE's exact boost-enabling arm first puts attached cars in
  rem racing state through SetAllCarsOnStartLine, homed in this split TU.
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnRaceCarEntityModule_ModeArming.cpp"
  rem ---- crash play / Showtime (crash-play wave 2026-08-29). BrnCrashPlayManager.cpp is  ----
  rem ---- the boost CONSUMER; the debug component is its first member BY VALUE, so its    ----
  rem ---- vtable has to resolve too or Update cannot call mCrashPlayDebugComponent.Update.----
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\CrashPlay\BrnCrashPlayManager.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\CrashPlay\BrnCrashPlayDebugComponent.cpp"
  rem ---- race-car streamer wave (2026-07-31): the per-car asset director +   ----
  rem ---- its shared component-streamer base + the five concrete leaves. These ----
  rem ---- are what post the first VEH_ load requests.                          ----
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnRaceCarStreamer.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnRaceCarBaseComponentStreamer.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnRaceCarComponentStreamers.cpp"
  rem ---- race-car RENDER wave (2026-07-31): RenderRaceCar + GenerateDispatchLists ----
  rem ---- plus the ActiveRaceCar / RenderParams homes the render leg reads.        ----
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnRaceCarEntityModule_Render.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnActiveRaceCar.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnActiveRaceCar_wQ5_01.cpp"
  rem ---- non-Showtime boost pipeline: exact base vtable, manager, and all three ----
  rem ---- concrete ARTIST strategies. BoostManager embeds B2/B3/B5 by value, so ----
  rem ---- omitting any of these part TUs leaves the selected B5 vtable incomplete. ----
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BrnBoostStrategy.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BrnBoostManager.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout2_wP_01.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout2_wP_02.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout2_wP_03.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout2_wP_04.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout2_wP_05.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout2_wP_06.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout2_wP_11.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout2_wP_16.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout3_wP_01.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout3_wP_02.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout3_wP_03.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout3_wP_04.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout3_wP_06.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout3_wP_07.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout3_wP_11.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout3_wP_15.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout3_wP_16.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout3_wP_17.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout5_wP_01.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout5_wP_02.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout5_wP_03.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout5_wP_04.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout5_wP_05.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout5_wP_06.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout5_wP_11.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostBurnout5_wP_16.cpp"
  rem ---- source identities restored from the exact ARTIST B2/B3/B5 vtable targets. ----
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\Boost\BoostFoldedVirtualBodies.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnActiveRaceCarRenderParams.cpp"
  rem (pose wave 2026-08-01: RaceCar::Construct/Prepare/AddToWorld/UpdatePositioningData/
  rem  AssignActiveRaceCar/ToBeRenderedDamaged are now called by the real attach chain.)
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnRaceCar.cpp"
  rem  2026-08-17 (ghost-car wave): RemoveRaceCar / DetachActiveRaceCar are the first callers of
  rem  RaceCarAIInterface::DetachAIControl @0x822FD768 and ::DeactivateRaceCar @0x822FD6E0. Both
  rem  bodies were already committed in this TU; the TU had simply never been mounted (same shape
  rem  as the BrnBoostManager line above). dumpbin: 74 DEF / 19 UNDEF, all 19 already resolved.
  echo "%SRC%\GameSource\World\AI\SharedIO\BrnRaceCarAIInterfaces.cpp"
  echo "%SRC%\SharedClasses\World\BrnWorldRegion.cpp"
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule.cpp"
  echo "%SRC%\GameSource\World\Trigger\BrnTriggerEntityModule.cpp"
  echo "%SRC%\GameSource\World\AI\BrnAIModule.cpp"
  rem ---- aimodule wave (2026-08-25): the AI MODULE LIFECYCLE. BrnAIModule.cpp above grew the
  rem   real Construct/Prepare/LoadMapData (the four WorldLinkStubs gates are retired), which
  rem   is what makes AI.dat load, "WorldMapData" resolve and BrnAI::ResetOnTrackManager get
  rem   Constructed at last. These are its link closure: the AI output buffer (now carrying
  rem   real typed members instead of this+offset into a 1-byte object), the reset-on-track
  rem   manager and its container instantiations. (BrnAStar.cpp is deliberately NOT here: it is
  rem   not link-complete -- AStarNodePool::FindNode and AStar::IsBlockSection have no body
  rem   anywhere, and Route::AddNode / Portal::GetLinkSectionIndex need the route TUs. So
  rem   RouteMapModule::Prepare parks its AStar::Construct call, flagged at the site.)
  echo "%SRC%\GameSource\World\AI\SharedIO\BrnAIModuleIO_OutputBuffer.cpp"
  rem ResetOnTrackResult / PlaceOnTrackRequest element constructors (the AI RESULT side).
  echo "%SRC%\GameSource\World\AI\SharedIO\BrnAIModuleResultInterface.cpp"
  echo "%SRC%\GameSource\World\AI\SharedIO\BrnAIModuleIO_OutputBuffer_Accessors.cpp"
  rem ON DISK BUT UNLISTED until 2026-08-26: the AI INPUT buffer's accessors, including its own
  rem Construct -- which is what points the reset-on-track request queue at its inline storage.
  rem A source list is a transitive closure and only the LINK walks it.
  echo "%SRC%\GameSource\World\AI\SharedIO\BrnAIModuleIO_InputBuffer_Accessors.cpp"
  echo "%SRC%\GameSource\World\AI\SharedIO\BrnAICarOutputInterface.cpp"
  echo "%SRC%\GameSource\World\AI\ResetOnTrack\BrnResetOnTrackManager.cpp"
  echo "%SRC%\GameSource\World\AI\SharedIO\Array_ResetOnTrackRequest_35.cpp"
  rem SIXTH unlisted TU, found by the LINK: ResetOnTrackRequest::Construct @0x822A0438 has been
  rem bodied here since the aicar_reset wave and this file was never on the list. Nothing had
  rem noticed because its only caller (RCEM::SendResetOnTrackRequests) did not exist yet.
  echo "%SRC%\GameSource\World\AI\SharedIO\BrnAIModuleRequestInterface.cpp"
  echo "%SRC%\GameSource\World\AI\ResetOnTrack\RingBuffer_RecentResetEntry.cpp"
  echo "%SRC%\GameSource\World\AI\SharedIO\EventQueue_ResetOnTrackResult_128.cpp"
  echo "%SRC%\GameSource\World\AI\SharedIO\EventQueue_ResetOnTrackResult_Methods.cpp"
  echo "%SRC%\GameSource\World\AI\SharedIO\EventQueue_PlaceOnTrackRequest_128.cpp"
  echo "%SRC%\GameSource\World\AI\Route\EventQueue_RouteResponse_16.cpp"
  rem ---- IO-buffer construction wave (2026-08-15): DestroyIOBuffer<T> now runs T::Destruct like the
  rem ---- console template; AIModuleIO::InputBuffer_PostPhysics::Construct @0x8277BCD0 / Destruct
  rem ---- @0x8277BCE8 were already reconstructed in this TU (never mounted; WorldLinkStubs carried a
  rem ---- memset gate for Construct instead -- retired the same day).
  echo "%SRC%\GameSource\World\AI\SharedIO\BrnAIModuleIO_InputBuffer_PostPhysics.cpp"
  rem ---- resetpump wave (2026-08-26): THE RESET-ON-TRACK PUMP, plumbed end to end. Three mounts:
  rem   * BrnAIModule_ResetPump.cpp -- AIModule::{Update (a minimal-complete SLICE),
  rem     ProcessRequestInterface, UpdateResetOnTrackManager, GetAICar}. Retires the
  rem     AIModule::Update boot gate in WorldLinkStubs.cpp.
  rem   * BrnRaceCarEntityModule_ResetPump.cpp -- RCEM::{WriteUpdatedAIData (which is what sets
  rem     mbPlayerDataSet, the flag AIModule::Update wraps its ENTIRE body in),
  rem     SendResetOnTrackRequests, ProcessResetOnTrackResultQueue}.
  rem   * WorldBridgeEntityModulesToAI.cpp -- ON DISK SINCE THE WORLD-DRIVE WAVE AND NEVER LISTED.
  rem     Its BridgeRaceCarModuleToAIModule_PreScene has been real, correct and complete all along
  rem     and the linker took the WorldLinkStubs stub instead. Both its bridges are retired from
  rem     WorldLinkStubs.cpp by this wave. FIFTH sighting of an unlisted TU in three waves.
  echo "%SRC%\GameSource\World\AI\BrnAIModule_ResetPump.cpp"
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeEntityModulesToAI.cpp"
  echo "%SRC%\GameSource\World\CrashModule\BrnCrashModule.cpp"
  echo "%SRC%\GameSource\World\CrashModule\BrnCrashModule_Lifecycle.cpp"
  echo "%SRC%\GameSource\World\CrashModule\BrnCrashModule_RaceCarCrashes.cpp"
  echo "%SRC%\GameSource\World\EnvironmentManager\BrnEnvironmentManager.cpp"
  rem ---- POST-FX RUNG 10 "environment live" (2026-08-16, irradiance group): the ambient-light
  rem   solver. This TU was never on the list -- it held only GetIrradianceMatrix. ComputeIrradiance
  rem   / ComputeFrameCoeffs / UpdateCoefficients / ComputeIrradianceMatrix are now real bodies and
  rem   EnvironmentManager::GenerateShaderConstants @0x827D0098 calls two of them.
  echo "%SRC%\GameSource\World\EnvironmentManager\BrnGlobalIrradianceManager.cpp"

  rem ---- POST-FX RUNG 10 "environment live" -- envfix round (2026-08-16). THE FIVE
  rem   ENVIRONMENT-SETTINGS TUs THAT WERE NEVER ON THIS LIST. Until now every symbol they
  rem   define was served by an inert WorldLinkStubs.cpp gate, which is why PerformBlend was
  rem   two thirds dead: ScatteringData/LightingData/CloudsData::SetToBlend all returned
  rem   without writing anything, so mScattering / mLighting / mClouds stayed at whatever
  rem   EnvironmentManager::Construct zero-seeded and a live GenerateShaderConstants would
  rem   have read an all-zero lighting block (= the world goes dark). Those 8 gates are
  rem   DELETED in WorldLinkStubs.cpp in the same step -- leaving one beside a mounted TU is
  rem   LNK2005 (measured, 8 duplicate definitions).
  rem   Link cost measured with dumpbin over the five objs + WorldLinkStubs.obj: the set
  rem   drags in NO new external. Everything it needs is already mounted --
  rem   CgsCore::SPrintf (CgsStringUtils.cpp, line 102 of this file) and the
  rem   BrnEffects::{Bloom,Vignette}Data default statics (BrnEffectsData.cpp, line 257) --
  rem   or is the CRT (fopen/fscanf/fgetc/ungetc/feof/fclose/atoi/strcmp/strncmp/strlen).
  rem   The 15 `KAF_*` default-template vectors these three TUs read had NO DEFINITION
  rem   anywhere in the tree (a latent unresolved external `cl /c` cannot see); they are
  rem   defined in them now, from the shipped image.
  echo "%SRC%\GameSource\World\EnvironmentSettings\BrnEnvScatteringData.cpp"
  echo "%SRC%\GameSource\World\EnvironmentSettings\BrnEnvLightingData.cpp"
  echo "%SRC%\GameSource\World\EnvironmentSettings\BrnEnvCloudsData.cpp"
  rem   NEW TU: Keyframe::Construct @0x82676298 (the six sub-block Constructs). Its only
  rem   caller is EnvironmentManager::SetupUpdateFromToolBlend (the dev d:\LightSetup.txt
  rem   path), but the symbol is link-required because that function is in the mounted
  rem   BrnEnvironmentManager.cpp.
  echo "%SRC%\GameSource\World\EnvironmentSettings\BrnEnvironmentKeyframe.cpp"
  rem   FindKeyframeInds @0x827B0418 (SetupTimeOfDayBlend calls it every frame), HH_MM_SS,
  rem   BuildTimeOfDay, ParseTimeOfDay, the six ConsumeFieldValue readers and all five
  rem   ConsumeFieldValue<T> instantiations, and ParseEnvironmentFile @0x8267CD70.
  echo "%SRC%\GameSource\World\EnvironmentSettings\BrnEnvironmentSettings.cpp"
  rem ---- POST-FX RUNG 5 "bloom lit" (2026-08-15): the effects-frame chain. BrnEffectsData.cpp
  rem   (BloomData/VignetteData/BlurData::SetToBlend + the default-constant statics the header declares)
  rem   and the renderer effects arbitrator (BrnGraphics::EffectsArbitrator: Construct/EndOfFrame/Eval*)
  rem   were never on the list; EnvironmentManager::GenerateEffects @0x827BE698, BrnEffectsFrame::Construct
  rem   and BrnRendererModule::Render's apply block all need them.
  echo "%SRC%\SharedClasses\Graphics\BrnEffectsData.cpp"
  echo "%SRC%\GameSource\Graphics\BrnEffectsArbitrator.cpp"
  rem   BrnRendererModulePostFx.cpp = the Render apply block (X360 Render @0x8240BFA8 lines 964-1260) homed
  rem   in a sibling TU because BrnRendererModule.h still carries the EA::Jobs::Job placeholder (see its banner).
  echo "%SRC%\GameSource\Graphics\BrnRendererModulePostFx.cpp"
  rem ---- POST-FX RUNG 10 "motion blur moves" (2026-08-16): the ParticleRenderData PRODUCER.
  rem   [FLAG PC bring-up] ParticleModuleBringUp.cpp stands in for BrnParticle::ParticleModule::Update
  rem   @0x822817D8 + ::GenerateRenderRequests @0x82281BD8, whose module (ParticleModule.cpp) and whose
  rem   driver (EffectsModule::Update / ::GenerateDispatchLists) are BOTH still off this list. Without it
  rem   DispatchThreadInputBuffer::mParticleRenderData is never written and BrnRendererModule::Render has
  rem   to pass a NULL to BrnRendererUpdatePostFxMotionBlur -- which is why motion blur was alive but
  rem   motionless. Its only new link requirements are already mounted: CgsCamera.cpp (Camera::operator=),
  rem   Camera.cpp (CopyToCgsCamera / GetTransform), BrnDispatchThreadInputBuffer.cpp
  rem   (GetParticleRenderData) and CgsIOBuffer.cpp / CgsLog.cpp.
  rem   DELETE this line when ParticleModule.cpp + EffectsModule.cpp land.
  echo "%SRC%\GameSource\Effects\Particles\ParticleModuleBringUp.cpp"
  rem ---- SKY WAVE (2026-07-31): the sky-dome draw path, MOUNTED. ----------------
  rem The closure was measured with dumpbin over the linked object set: the three
  rem sky TUs raise 67 externals / 45 already provided / 22 unresolved; the two
  rem existing renderengine TUs below resolve 2 and drag nothing, and
  rem ImmediateModePCLeaf.cpp (a new PC leaf) defines the other 20. Mounting the
  rem existing VertexBuffer.cpp / IndexBuffer.cpp / CgsImRenderer.cpp instead makes
  rem it WORSE (29 / 23 unresolved + an LNK2005 against the linked CgsIm2d.cpp).
  echo "%SRC%\pc\gcm\renderengine\VertexDescriptorParameters.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\PS3\CgsRwVertexDescResourceType.cpp"
  echo "%SRC%\pc\gcm\renderengine\ImmediateModePCLeaf.cpp"
  rem ---- RETAINED WORLD GEOMETRY (2026-08-15 perf wave) ----------------------
  rem The dispatch-path world/car/caster draws used to re-expand DEC3N and re-cut
  rem every strip run inside DrawIndexedPrimitiveUP, PER DRAW CALL -- measured at
  rem 36 pct self / 69 pct inclusive of the main thread. This PC leaf mirrors each
  rem static bundle buffer into a D3D9 vertex/index buffer ONCE and submits with
  rem SetStreamSource/SetIndices/DrawIndexedPrimitive; CgsResourcePool's free path
  rem evicts a mirror together with the bundle memory it was built from.
  echo "%SRC%\pc\gcm\renderengine\WorldGeometryPCLeaf.cpp"
  echo "%SRC%\pc\gcm\renderengine\SkyDomeProgramsPC.cpp"
  rem ---- CORONAS WAVE (2026-08-17, step 1): THE LIGHT-FLARE PASS, MOUNTED. ----
  rem   BrnCoronaManager + renderengine::CoronaRenderer were reconstructed but UNMOUNTED; this
  rem   wave lands the whole chain. Link closure, measured with dumpbin (wave report section 4):
  rem     rwgcoronarenderer.cpp -> ProgramBufferPC_Adopt / ProgramBuffer::GetVariableHandleByName
  rem       (programbuffer.cpp + ImmediateModePCLeaf.cpp), VertexDescriptor::Parameters::Parameters
  rem       + VertexDescriptor::Initialize (VertexDescriptorParameters.cpp + ImmediateModePCLeaf
  rem       .cpp), the shadow::Device binders (shadowingdevice.cpp) and D3DDevice_Begin/EndVertices
  rem       (XenonD3D9Shims.cpp) -- ALL already on this list -- plus the corona program pair below.
  rem     BrnCoronaManager.cpp  -> Curves.cpp + RwRGBA.cpp + rwgcoronabufferiterator.cpp +
  rem       BrnCoronaTypeParams.cpp, which are the four lines added with it.
  rem   The corona VS/PS pair is AUTHORED for D3D9 (the Xenos blobs at unk_8200F1B8 / unk_8200F2A0
  rem   cannot execute here) -- the same treatment SkyDomeProgramsPC.cpp on the line above gets.
  echo "%SRC%\pc\gcm\renderengine\CoronaProgramsPC.cpp"
  echo "%SRC%\SDKs\RenderEngineClub\MAIN\components\src\coronas\rwgcoronarenderer.cpp"
  echo "%SRC%\SDKs\RenderEngineClub\MAIN\components\src\coronas\rwgcoronabuffer.cpp"
  echo "%SRC%\SDKs\RenderEngineClub\MAIN\components\src\coronas\rwgcoronabufferiterator.cpp"
  echo "%SRC%\GameSource\Graphics\BrnCoronaManager.cpp"
  echo "%SRC%\GameSource\Graphics\BrnCoronaTypeParams.cpp"
  echo "%SRC%\GameSource\Effects\Curves.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\RwRGBA.cpp"
  rem ---- CORONAS WAVE (2026-08-18, step 2): THE SUN CORONA. ----
  rem   BrnSunCorona.cpp was reconstructed but UNMOUNTED (and its two committed bodies were a
  rem   phantom construction surface -- see the file's own banner). This wave lands the object and
  rem   its two draw passes. Link closure, measured with dumpbin (wave report section 4):
  rem     BrnSunCorona.cpp -> ProgramBufferPC_Adopt / ProgramBuffer::GetVariableHandleByName
  rem       (ImmediateModePCLeaf.cpp + states/programbuffer.cpp), VertexDescriptor::Parameters::
  rem       Parameters + VertexDescriptor::Initialize / ::Release (VertexDescriptorParameters.cpp +
  rem       ImmediateModePCLeaf.cpp), the shadow::Device binders (shadowingdevice.cpp),
  rem       D3DDevice_Begin/EndVertices (XenonD3D9Shims.cpp), CgsRenderTarget::Begin/End
  rem       (CgsRenderTarget.cpp), RenderTarget::GetDepthTextureState (PostFxRenderTargetPCLeaf.cpp)
  rem       and the three state factories -- ALL already on this list -- plus the four sun-corona
  rem       programs below.
  rem   The four VS/PS programs are AUTHORED for D3D9 (the Xenos blobs at unk_8203E118 / E208 /
  rem   E438 / E528 cannot execute here) -- the same treatment CoronaProgramsPC.cpp above gets.
  echo "%SRC%\pc\gcm\renderengine\SunCoronaProgramsPC.cpp"
  echo "%SRC%\GameSource\Graphics\BrnSunCorona.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\ImmediateMode\CgsIm3dSkyDome.cpp"
  echo "%SRC%\GameSource\Graphics\ImmediateMode\BrnIm3d.cpp"
  echo "%SRC%\GameSource\Graphics\BrnSkyDomeManager.cpp"
  echo "%SRC%\SharedClasses\World\BrnEnvironmentUtil.cpp"
  rem ---- NEW TU (envstream wave 2026-08-16). Dictionary::BuildResourceName @0x827B03B8 (the
  rem  name EnvironmentManager::Prepare hashes to acquire the environment dictionary) plus the
  rem  BLOCKED TimeLine::BuildResourceName stub. Prepare now REFERENCES the first symbol, so the
  rem  mount is required for the link, not optional.
  echo "%SRC%\SharedClasses\World\BrnEnvironmentDictionary.cpp"
  rem ---- ENVIRONMENT-SETTINGS RESOURCE TYPES (env wave, 2026-08-16) ----------------------
  rem  The three handlers for build\game\ENVIRONMENTSETTINGS (Keyframe 0x10012, TimeLine
  rem  0x10013, Dictionary 0x10014) have existed since the post-fx rung-5 wave and were NEVER
  rem  ON THIS LIST, so the exe carried no code for them at all -- which is the other half of
  rem  why EnvironmentManager::Prepare had to be stubbed inert. Registered in
  rem  CgsResourceTypeRegistration.cpp in the same step; BundleLoader::LoadBundle gates FixUp,
  rem  ResolveImportsForEntry and PostFixUp on `mpResourceType != 0`, so an unmounted /
  rem  unregistered type leaves the TimeLine's three pointer slots as serialised offsets AND
  rem  leaves its nine keyframe imports unresolved.
  rem  Link cost measured with dumpbin over the three objs: ZERO new externals -- their only
  rem  UNDEFs are CgsDev::Assert::{Begin,Fire,End}Assert (CgsAssert.cpp, line 103 of this
  rem  file), rw::BaseResourceDescriptor::BaseResourceDescriptor (BaseResourceDescriptor.cpp,
  rem  line 3530) and CRT memset.
  echo "%SRC%\SharedClasses\World\BrnEnvironmentKeyframeResourceType.cpp"
  echo "%SRC%\SharedClasses\World\BrnEnvironmentTimeLineResourceType.cpp"
  echo "%SRC%\SharedClasses\World\BrnEnvironmentDictionaryResourceType.cpp"
  rem  ResourcePtr<TimeLine>::GetMemoryResource @0x827C3048 -- the season timeline pointer the
  rem  EnvironmentManager instances in RequestNextSeason / StreamOut / StreamIn / SetupBlend
  rem  (maSeasonPtrs). Declared-and-never-defined until now = a latent unresolved external the
  rem  per-TU `cl /c` gate cannot see.
  echo "%SRC%\GameSource\World\EnvironmentSettings\CgsResourcePtr_BrnWorld_EnvironmentSettings_TimeLine.cpp"
  echo "%SRC%\GameSource\World\EnvironmentMap\BrnEnvironmentMap.cpp"
  echo "%SRC%\GameSource\World\ShadowMap\BrnShadowMap.cpp"
  echo "%SRC%\GameSource\World\BrnPlaceOnTrackManager.cpp"
  echo "%SRC%\GameSource\Physics\BrnPhysicsModule.cpp"
  rem ---- PhysicsModule LAYOUT GATE (task #123, 2026-08-03) --------------------------------
  rem  MUST STAY MOUNTED. BrnPhysicsModule.h was re-seated from an opaque 26KB-short tail into
  rem  seven real typed sub-objects + the DWARF state/perf-mon block; this TU is the only place
  rem  the console arithmetic behind that is checked. It emits NOTHING at link time (a single
  rem  never-called static _AssertLayout, discarded by /OPT:REF) -- but the static_asserts only
  rem  run if it is COMPILED. BrnVehicleManager.h's _AssertLayout sat in an UNMOUNTED TU for ten
  rem  waves and was therefore a comment, not a gate; do not repeat that here.
  echo "%SRC%\GameSource\Physics\BrnPhysicsModule_layout_check.cpp"
  rem ---- PhysicsSimulationModule (physics wave 6, 2026-08-03) ------------------------------
  rem  BrnPhysicsModule.h now embeds CgsPhysics::PhysicsSimulationModule BY VALUE at +0x230
  rem  (the 18544-byte opaque placeholder folded), so BrnPhysicsModule.cpp -- which IS on the
  rem  live boot path, PhysicsModule::Construct is reached by the WorldModule cascade --
  rem  instantiates the class and therefore needs its vtable and its constructor. That makes
  rem  this TU a HARD link dependency, not a closure-only mount: PhysicsSimulationModule::
  rem  Construct @0x828A1EE8, the class constructor @0x827DF1E0 and RigidBodyData::
  rem  RigidBodyData @0x827DB728 all live here.
  echo "%SRC%\GameShared\GameClasses\Physics\CgsPhysicsSimulationModule.cpp"
  rem  ??? 2026-08-04 (task #140): the InputBuffer TU is now a HARD dependency of the TU above.
  rem  ProcessAddRigidBodyQueue -- the first of the nineteen input drains -- calls
  rem  InputBuffer::GetAddRigidBodyQueue() const @0x8289E408, which is defined here. Mounted
  rem  after reading the link (ONE unresolved external, this symbol, nothing else came with
  rem  it): the TU adds no further unresolved symbols of its own.
  echo "%SRC%\GameShared\GameClasses\Physics\CgsPhysicsSimulationModuleIO_InputBuffer.cpp"
  rem  ??? 2026-08-06 (the game-side six + the two virtuals): the OutputBuffer TUs are now HARD
  rem  dependencies of the module TU above. PhysicsSimulationModule::Update and its four
  rem  output emitters call SetTimeStepUsed/SetMaxIterationsUsed and the four write-side
  rem  queue accessors (GetUpdateRigidBodyQueue @0x8289F130, GetContactSpyQueue @0x8259F120,
  rem  GetJointSpyQueue @0x8259F1C8, GetDriveSpyQueue @0x8259F270), all defined in the first
  rem  TU; the second holds OutputBuffer::Destruct @0x828A5F38 (rewritten off its local
  rem  slice-fork the same day). /OPT:REF strips all of it until PhysicsModule::Update lands.
  echo "%SRC%\GameShared\GameClasses\Physics\CgsPhysicsSimulationModuleIO_OutputBuffer.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\CgsPhysicsSimulationModuleIO.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsSceneManagerModule.cpp"
  rem  ---- wave Q5 round 3 (2026-08-19): the scene-collision middle closes -- the drain legs,
  rem  the scene manager bridge family and their callees. Mounted in the same commit as the
  rem  WorldLinkStubs gate retirements for OverlapGenerationModule and the three BridgeOverlap*.
  rem  CgsSceneManagerModule_wQ5_01.cpp : UpdateCollisionBody @0x828C7528 + the three padding events.
  rem  CgsSceneManagerBridgeFunctions.cpp : BridgeOverlapGenerationToOverlapCulling @0x828BA538,
  rem    BridgeOverlapGenerationToOutputBuffer @0x828BA6A0, BridgeOverlapCullerToOutputBuffer
  rem    @0x828BA8C8 -- the only writer of SceneManagerIO::OutputBuffer mPotentialContactQueue.
  rem  CgsCullingGroupManager.cpp : SetCullingGroupPair @0x828AA580, the CARS x PROPS adjacency writer.
  rem  CgsSceneManagerContact.cpp : Contact::Construct @0x828A9E30, called twice by DoPairQuery.
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsSceneManagerModule_wQ5_01.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsSceneManagerBridgeFunctions.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsCullingGroupManager.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsSceneManagerContact.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\CgsCamera.cpp"
  echo "%SRC%\GameSource\Director\Camera\Camera.cpp"
  rem ---- world-fleet link-mount closure (2026-07-26): committed TUs picked by ----
  rem ---- offline dumpbin closure analysis; leftovers stubbed in WorldLinkStubs ----
  echo "%SRC%\GameShared\GameClasses\Graphics\Dispatch\CgsDispatcher.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\Dispatch\CgsGraphicsDispatchList.cpp"
  rem ---- renderer world-pass wave (2026-07-27): the render-dispatch walk ----------
  rem ---- (object->mesh expansion, the sorted mesh walk, the shadowing device) ----
  echo "%SRC%\GameShared\GameClasses\Graphics\Dispatch\CgsDispatcherCommands.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\Dispatch\CgsDrawRenderableFrustumTest.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\Dispatch\CgsPackedOobb.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\Dispatch\CgsOcclusionCullManager.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\Dispatch\shadowingdevice.cpp"
  rem ---- SHADOW-MAP RENDER TARGET wave (2026-08-12): the four TUs that make the shadow ----
  rem ---- pass's target EXIST. BRN_SHADOW_MAP_TARGET_AVAILABLE in BrnRendererModule.cpp ----
  rem ---- is now 1 and these are its link closure.                                     ----
  rem
  rem  The blocker was never these files -- it was the layer beneath them. postfx::RenderTarget
  rem  (Initialize / Parameters::Parameters / Begin / End / GetTexture / GetDepthStencilTexture /
  rem  Get,SetSectionRenderTargetState / GetRenderTargetState), postfx::gpDefaultRenderTargetState
  rem  and renderengine::Device::SetState(const RenderTargetState*) were declared everywhere and
  rem  DEFINED NOWHERE (the only Device::SetState in the tree was shadow::Device::SetState(void*,
  rem  u32), a different class). PostFxRenderTargetPCLeaf.cpp is the new PC leaf that defines all
  rem  of them over Direct3D 9: a real depth-sampleable INTZ texture (1280x1920 = the 1x3 cascade
  rem  atlas the recovered ShadowMap_* constants encode) bound as the depth-stencil surface.
  rem
  rem  ??? THE CONSOLE SIBLING STAYS OUT.
  rem  SDKs\RenderEngineClub\MAIN\components\src\postfx\src\rwgpfxrendertarget.cpp is the FAITHFUL
  rem  X360 reconstruction of this same surface, and it is deliberately NOT mounted: it is EDRAM
  rem  end to end (PixelBuffer::Initialize / Xbox2ResolveTo / Xbox2SetBaseEDRAM /
  rem  Xbox2SetBaseHierarchicalZ / Texture::Xbox2CheckPhysicalMemoryFlags / AllocateAndInitializeTexture
  rem  / TextureState::GetResourceDescriptor / RenderTargetState__{GetResourceDescriptor,Initialize}
  rem  -- none of which has a body in the tree), and it would ALSO LNK2005 against the leaf, since
  rem  both define RenderTarget::Begin/End/Resolve/Initialize and Target::Resolve. It stays parked
  rem  as the console record until the renderengine PixelBuffer layer exists.
  rem
  rem  MEASURED CLOSURE (a real trial link over the 1,139-object set + these five, NOT `cl /c`):
  rem  the five TUs raise 101 distinct externals; 84 are satisfied by the object set and the
  rem  remaining 17 are CRT / import-lib symbols (operator new/delete, type_info, __security_*,
  rem  memset, __imp_GetEnvironmentVariableA, ...). link exit 0, zero LNK2019/LNK2005.
  rem  BrnRendererMemory::Construct is COMPILED OUT behind BRN_RENDERER_MEMORY_FULL_POOL_AVAILABLE
  rem  (its 14 unresolvable pool/blit symbols are listed in that banner) -- do not un-gate it here.
  echo "%SRC%\GameShared\GameClasses\Graphics\CgsRenderTarget.cpp"
  echo "%SRC%\GameSource\Graphics\BrnRendererMemory.cpp"
  echo "%SRC%\GameSource\Graphics\BrnShadowMapRenderManager.cpp"
  echo "%SRC%\pc\gcm\renderengine\PostFxRenderTargetPCLeaf.cpp"
  rem  The post-fx composite's D3D9 programs -- ALL TWELVE PERMUTATIONS since the
  rem  step-5 wave: ONE shared vertex image (the twelve X360 vertex packages are
  rem  byte-identical, md5 a47e7e9943a3570c484e1724d6dff763) plus twelve pixel
  rem  images, generated from tools\assets\shaders\brn_postfx_composite.fx
  rem  compiled twelve ways. Same situation as SkyDomeProgramsPC.cpp above:
  rem  executable-embedded Xenos microcode with no SHADERS.BNDL entry and no PC
  rem  counterpart, so every program is rebuilt for D3D9 and carried as a
  rem  generated leaf. Data only: twenty-six symbols defined (thirteen arrays +
  rem  thirteen sizes), zero externals raised.
  echo "%SRC%\pc\gcm\renderengine\PostFxProgramsPC.cpp"
  rem  The six BLOOM D3D9 programs (down-sample vs/ps, "new" blur vs/ps, "old"
  rem  separable-blur vs/ps), generated from tools\assets\shaders\brn_postfx_bloom.fx
  rem  -- the same situation as the composite leaf above: six executable-embedded
  rem  Xenos microcode packages (X360 0x8203E6F8 / 0x8203E858 / 0x8203EA60 /
  rem  0x8203EBD0 / 0x8203ED78 / 0x8203EF10) with no SHADERS.BNDL entry and no PC
  rem  counterpart, so all six are rebuilt for D3D9 and carried as a generated
  rem  leaf. Data only: twelve symbols defined, zero externals raised. Consumed by
  rem  BrnPostFxBloom.cpp's six CreateProgram call sites with
  rem  BRN_POSTFX_BLOOM_PROGRAMS_PC_AVAILABLE at its default 1.
  echo "%SRC%\pc\gcm\renderengine\PostFxBloomProgramsPC.cpp"
  rem  The four PfxHelper D3D9 programs (the shared quad's vertex program, and the
  rem  9-tap / 16-tap / 4-tap blur pixel programs) plus the DepthOfField pixel
  rem  program, generated from tools\assets\shaders\brn_postfx_helper.fx -- the
  rem  same situation as the composite and bloom leaves above: five
  rem  executable-embedded Xenos microcode packages (X360 0x82044240 / 0x820444F8
  rem  / 0x820447A8 / 0x82044360 / 0x82043FB8) with no SHADERS.BNDL entry and no PC
  rem  counterpart, so all five are rebuilt for D3D9 and carried as a generated
  rem  leaf. Data only: ten symbols defined, zero externals raised. Consumed by
  rem  rwgpfxhelper.cpp's four CreateProgram call sites (PfxHelper::PfxHelper) and
  rem  rwgpfxdof.cpp's one (DepthOfField::DepthOfField); both TUs are already on
  rem  this list below, and those ten are the ONLY new externals either of them
  rem  raises.
  echo "%SRC%\pc\gcm\renderengine\PostFxHelperProgramsPC.cpp"
  rem  The SEVEN B4Blur D3D9 programs (the blur quad's vertex program, the shared
  rem  scatter/radial vertex program, the scatter / radial / texture / down-sample
  rem  / blur pixel programs), generated from tools\assets\shaders\brn_postfx_b4blur.fx
  rem  -- the same situation as the composite, bloom and helper leaves above: EIGHT
  rem  executable-embedded Xenos microcode packages (X360 0x82045148 / 0x82045600 /
  rem  0x82045748 / 0x82045AC0 / 0x82045C08 / 0x820459B8 / 0x820454E0 / 0x820452A8)
  rem  with no SHADERS.BNDL entry and no PC counterpart. SEVEN images for EIGHT
  rem  packages: 0x82045600 and 0x82045AC0 are byte-identical, so one array serves
  rem  both call sites. Data only: fourteen symbols defined, zero externals raised.
  rem  Consumed by rwgpfxb4blur.cpp's eight CreateProgram call sites
  rem  (B4Blur::B4Blur); that TU is already on this list below, and those fourteen
  rem  are the ONLY new externals it raises.
  echo "%SRC%\pc\gcm\renderengine\PostFxB4BlurProgramsPC.cpp"
  rem  The post-fx SHADER CLASS (BrnPostFxShader::{Construct,Destruct,Render}, Shader::{Construct,
  rem  Destruct,SetProgram}) with BRN_POSTFX_SHADER_PROGRAMS_AVAILABLE and
  rem  BRN_POSTFX_COMPOSITE_DRAW_AVAILABLE both 1: ALL TWELVE slots adopt their PostFxProgramsPC
  rem  image pair through ProgramBufferPC_Adopt -- no slot is empty, and Render no longer refuses
  rem  any index but 0 (it refuses only a slot whose programs are null). Its callers
  rem  (BrnPostFx::Construct/Render in BrnPostFx.cpp) are NOT mounted yet -- BrnPostFx.cpp's own
  rem  closure (the RenderEngineClub post-fx effect TUs) is the next wave -- so /OPT:REF strips
  rem  every byte of this today. Mounted anyway to ENFORCE the link closure over the flipped arms
  rem  (LNK2019 resolves before /OPT:REF discards): its dependencies are the two state TUs below
  rem  (samplerstate.cpp, DepthStencilState.cpp), VertexDescriptor::Release (ImmediateModePCLeaf.cpp),
  rem  and shadow::Device::SetState(const TextureState*, u32) (shadowingdevice.cpp).
  echo "%SRC%\GameSource\Graphics\PostFx\BrnPostFxShader.cpp"
  rem  renderengine::DepthStencilState::{GetResourceDescriptor,Initialize} -- the PC leaf the
  rem  shader class's Construct builds its ZOFF/ZWRITEOFF state through.
  echo "%SRC%\pc\gcm\renderengine\DepthStencilState.cpp"
  rem ---- THE POST-FX DRIVER + THE RENDERENGINECLUB EFFECT TUs (gate-flip wave, 2026-08-15) ----
  rem  BrnPostFx::{Construct,Destruct,PrepareDownSampleBuffers,Render} + the two PC seams
  rem  (PCBringUpConstructPostFx / PCBringUpRenderPostFxComposite) BrnRendererModule reaches the
  rem  composite through, and BrnPostFxBloom. Link-closed by the effect wave below: measured by a
  rem  full-object-set probe link whose ONLY residue was the seven Xenon shims of the console
  rem  VertexBuffer.cpp -- which is why VertexBuffer::Release is a PC leaf in ImmediateModePCLeaf.cpp
  rem  and that TU is NOT mounted (its Initialize would duplicate the leaf's).
  echo "%SRC%\GameSource\Graphics\PostFx\BrnPostFx.cpp"
  echo "%SRC%\GameSource\Graphics\PostFx\BrnPostFxBloom.cpp"
  rem  The five effect TUs (PfxHelper / DepthOfField / Vignette / Tint / B4Blur) + the render-target
  rem  debugger PfxHelper::PfxHelper builds once. Every embedded-microcode program build is gated
  rem  honest-EMPTY behind RW_GPFX_PROGRAM_MICROCODE_AVAILABLE (rwgpfxhelper.cpp's CreateProgram is
  rem  the one funnel) and the helper's quad geometry behind RW_GPFX_HELPER_QUAD_GEOMETRY_AVAILABLE;
  rem  the vignette / dof / bloom program gates are their TUs' own. None of the effects can DRAW on
  rem  this build (every m_enabledFx bit is clear); they exist so BrnPostFx::Construct's carves and
  rem  Destruct's releases run the console's own bodies.
  echo "%SRC%\SDKs\RenderEngineClub\MAIN\components\src\postfx\src\rwgpfxhelper.cpp"
  echo "%SRC%\SDKs\RenderEngineClub\MAIN\components\src\postfx\src\rwgpfxdof.cpp"
  echo "%SRC%\SDKs\RenderEngineClub\MAIN\components\src\postfx\src\rwgpfxvignette.cpp"
  echo "%SRC%\SDKs\RenderEngineClub\MAIN\components\src\postfx\src\rwgpfxtint.cpp"
  rem  rw::graphics::postfx::ColourCube::GetResourceDescriptor @0x82402C48 -- the sizing the
  rem  colour-cube resource-type handler forwards to. Added by the post-fx step-10 tint wave:
  rem  registering RwColourCubeResourceType makes CgsResourceTypeRegistration.obj reference the
  rem  handler, and the handler references this. Measured, not assumed -- dumpbin on
  rem  CgsRwColourCubeResourceType.obj lists exactly one game-side UNDEF:
  rem    ?GetResourceDescriptor@ColourCube@postfx@graphics@rw@@SAPEAU?$BaseResourceDescriptors@$04@4@...
  echo "%SRC%\SDKs\RenderEngineClub\MAIN\components\src\postfx\src\rwgpfxcolourcube.cpp"
  echo "%SRC%\SDKs\RenderEngineClub\MAIN\components\src\postfx\src\rwgpfxb4blur.cpp"
  echo "%SRC%\SDKs\RenderEngineClub\MAIN\components\src\postfx\src\rwgpfxrendertargetdebugger.cpp"
  rem  renderengine::RasterizerState::{GetResourceDescriptor,Initialize} -- moved here out of
  rem  CgsRasterizerStateFactory.cpp (they were the PC leaf's, defined in the wrong TU) and the
  rem  file's maState[] rot repaired; zero externals of its own.
  echo "%SRC%\pc\gcm\renderengine\RasterizerState.cpp"
  rem  The depth-stencil / rasterizer state factories: their tables are the DWARF's private statics
  rem  behind a static GetState(slot); BrnPostFx::Render and BrnPostFxBloom::Render read slots
  rem  saDepthStencilStates[1] / saRasterizerStates[2] (the two the step-2 driver had as undefined
  rem  gpPostFx* globals -- no such globals exist on the console). CgsStateFactoryLinkStubs supplies
  rem  both factories' Destruct/Prepare vtable slots. NOTE: nothing CONSTRUCTS either factory on this
  rem  build yet, so both tables read null and the composite's SetState pushes skip (compare-then-
  rem  apply on null) -- disclosed at the BrnPostFx.cpp call site.
  echo "%SRC%\GameShared\GameClasses\Graphics\CgsRasterizerStateFactory.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\CgsDepthStencilStateFactory.cpp"
  rem  ...and the blend factory (Construct @0x827EB2D8, landed 2026-08-13 from the export hole):
  rem  all three are REAL by-value members of BrnRendererModule now (the placeholder structs in
  rem  BrnRendererModule.h are gone), constructed once from the PC bring-up in Render, so their
  rem  three vtables must resolve -- Construct here, Destruct/Prepare in the link stubs.
  echo "%SRC%\GameShared\GameClasses\Graphics\CgsBlendStateFactory.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\CgsStateFactoryLinkStubs.cpp"
  rem  TintBlendEntry @0x82AD2CE8 / TintBlend @0x82AD4860 -- the EA::Jobs entry BrnPostFx::Construct
  rem  arms (on X360 the PPU pair of what is an SPU ELF on PS3). TintBlend's variant table is BLOCKED
  rem  (dword_82F7238C undumped) and unreachable while the tint bit is clear.
  echo "%SRC%\GameShared\Jobs\TintBlend\TintBlend.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\CgsBufferedDispatchFrame.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\CgsMaterialAssembly.cpp"
  echo "%SRC%\pc\gcm\renderengine\VertexProgramState.cpp"
  echo "%SRC%\pc\gcm\renderengine\XenonD3D9Shims.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CacheManager\CgsTriangleCacheManager.cpp"
  rem  ????????? 2026-08-10 (fill-worker wave): CachedTriangleList::Prepare @0x828BE520 (79) -- THE
  rem  SHARED TRIANGLE ARENA'S ALLOCATION. Its WorldLinkStubs gate returned true WITHOUT
  rem  allocating, so mpaTriangleCache was NULL and every one of the 298 slot windows indexed
  rem  off a null base. Found by forcing the console's own mbDEBUGForceAllDirty for one
  rem  instrumented boot, which fired the never-before-executed shipped tripwire
  rem  "mpaTriangleCache != NULL" (CgsTriangleCacheManager.h:172) 862 times.
  rem  ??? 0x828BE520 is an X360 export HOLE; name from the caller's xrefs_from, signature from
  rem  the PS3 DWARF mangle @0xC7B30C. Allocates 13112 * sizeof(Triangle4) == 2,937,088 bytes.
  echo "%SRC%\GameShared\GameClasses\SceneManager\CacheManager\CgsCachedTriangleList.cpp"
  rem  Triangle-cache SLOT BOOKKEEPING (triangle-cache wave 2026-08-10): the write side of
  rem  the cache's 298-slot table -- ProcessRemoveFromCacheEvents @0x828B2710 /
  rem  ProcessAddToCacheEvents @0x828B2C78 / ProcessUpdateCachedPositionEvents @0x828BE898 /
  rem  CacheSlot::UpdateCachedObject @0x828BE660. UNREACHABLE today: their only caller,
  rem  SceneManagerModule::StartUpdateTriangleCache, is still a WorldLinkStubs gate, so
  rem  /OPT:REF strips every byte. Mounted anyway to enforce the link closure over them.
  echo "%SRC%\GameShared\GameClasses\SceneManager\CacheManager\CgsTriangleCacheManager_Events.cpp"
  rem  ...and its layout gate, which was UNMOUNTED until this wave -- i.e. every
  rem  static_assert in it was submit-time only and had never run in a build.
  echo "%SRC%\GameShared\GameClasses\SceneManager\CacheManager\CgsTriangleCacheManager_embed_check.cpp"
  rem  ?????? 2026-08-10 (cache-fill wave): THE FILL HALF -- StartUpdateTriangleCaches @0x828BECF8
  rem  (278) + EndUpdateTriangleCaches @0x828BF150 (475). Both WorldLinkStubs gates DELETED.
  rem  ??? ASYMMETRIC REACHABILITY: End is LIVE from the frame it lands (SceneManagerModule::
  rem  EndUpdateTriangleCache @0x828C7500 is real and WorldModule::Update calls it every frame)
  rem  and takes its own null guard; Start is still only reached through SceneManagerModule::
  rem  StartUpdateTriangleCache, which stays gated because TriangleCollisionManager::Prepare
  rem  @0x828D0C40 is inert and BuildSpacialPartition @0x82841740 (2,255 insns) is absent.
  echo "%SRC%\GameShared\GameClasses\SceneManager\CacheManager\CgsTriangleCacheManager_Update.cpp"
  rem  ?????? 2026-08-10 (producer wave): the InEventAddToCache queue APPEND instantiation
  rem  (BaseEventQueue<InEventAddToCache>::AddEvent @0x825E4620). Reconstructed long ago and
  rem  never mounted -- a pure mount gap. It is the single producer edge that VehicleManager::
  rem  PrepareTriangleCache and PhysicalTrafficManager::PrepareTriangleCache both call, i.e. the
  rem  only path by which TriangleCacheManager::mUsedCacheSlots can ever become non-zero.
  echo "%SRC%\GameShared\GameClasses\SceneManager\CacheManager\BaseEventQueue_InEventAddToCache_AddEvent.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsEntityManager.cpp"
  rem  ---- wave Q5 cluster A1 (2026-08-18): the scene VOLUME store -- CgsSceneManager::VolumeManager
  rem  Prepare @0x828CFD38 / RemoveVolume @0x828CFDC8 / ReplaceDynamicVolume @0x828CFEE8 /
  rem  AddDynamicVolume @0x828D1708 / GetRwVolume @0x828C5E68 -- the WorldLinkStubs Prepare gate is retired.
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsVolumeManager.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsVolumeStore.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\ObjectPool_VolumeManagerVolume_5048.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\ObjectPool_VolumeSlot_4608.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\ObjectPool_VolumeInstance_5048.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\CgsResourcePtr_CgsPhysics_CollisionMeshData.cpp"
  rem  ---- create-path wave 2026-08-11 ----
  rem  CgsSceneManager::VolumeInstanceId::SetEntityIDOwner @0x822B0E00 /
  rem  ::SetEntityIDEntityIndex @0x822B0E70. Bodied since their own wave, never linked -- no
  rem  mounted caller existed. ActiveRaceCar::Attach now seeds mHandlingBodyVolumeId through
  rem  them (the console step that was flagged "omitted"), which is what gives
  rem  VehicleManager::ProcessCreateEvents its owner byte and its race-car slot index.
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsVolumeInstanceId.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsSceneManagerIO_InputBuffer_Update.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsSceneManagerIO_SceneUpdate.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\ContactGen\CgsOverlapCullingModule.cpp"
  rem  ---- wave Q5 round 3 / E3b: the culler INTERNAL-collision half -- IsInsideEscapeVolume
  rem  @0x828CB0A8, DoInternalCollision @0x828CB1D8, ProcessInternalCollisions @0x828CB308.
  echo "%SRC%\GameShared\GameClasses\SceneManager\ContactGen\CgsOverlapCullingModule_wQ5_01.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\ContactGen\CgsOverlapCullingModuleIO.cpp"
  rem  ---- wave Q5 cluster B1 (2026-08-18): the sweep-and-prune broadphase (keystone: layout +
  rem  Prepare @0x828C2000 / Clear @0x828B57A0; IntervalList 8 bodies + SweepIntervals @0x828C1328 +
  rem  SweepAgainstList @0x828C1520; IntervalStack). Mount all three or none.
  echo "%SRC%\GameShared\GameClasses\SceneManager\ContactGen\CgsSceneSweeper.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\ContactGen\CgsIntervalList.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\ContactGen\CgsIntervalStack.cpp"
  rem  ---- wave Q5 round 2 (2026-08-18): the sweeper mutators + the OverlapGeneration IO buffers.
  echo "%SRC%\GameShared\GameClasses\SceneManager\ContactGen\CgsSceneSweeper_wQ5_01.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\ContactGen\CgsIntervalList_wQ5_01.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\ContactGen\CgsSceneSweeper_wQ5_02.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\ContactGen\CgsSceneSweeper_wQ5_03.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\ContactGen\CgsOverlapGenerationModuleIO_InputBuffer.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\ContactGen\CgsOverlapGenerationModuleIO_OutputBuffer.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\ContactGen\EventQueue_OverlapGenerationInAddBody_16384_Construct.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\ContactGen\EventQueue_OverlapGenerationInUpdateBody_16384_Construct.cpp"
  rem  ---- wave Q5 round 3 / E2: the overlap generator + sweeper driver -- Update @0x828CB878,
  rem  GenerateOverlaps @0x828D5C08, ProcessForceNoPaddingQueue @0x828B56D8, OutputCollidingPairs
  rem  @0x828C1F58 + the six Construct/Prepare/Release/Process*BodyQueue bodies. BRN_PROP_DIAG Q5-sweep.
  echo "%SRC%\GameShared\GameClasses\SceneManager\ContactGen\CgsOverlapGenerationModule.cpp"
  rem ---- the broad phase (culling wave 2026-07-28): the loose octree + its manager ----
  echo "%SRC%\GameShared\GameClasses\SceneManager\SpatialPartitionModule\SpatialPartitions\CgsSpatialPartition.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\SpatialPartitionModule\SpatialPartitions\CgsLooseOctree.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\SpatialPartitionModule\CgsSpatialPartitionManager.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\SpatialPartitionModule\CgsSpatialPartitionManagerIO.cpp"
  echo "%SRC%\GameShared\GameClasses\System\AttribSys\CgsAttribSysModuleIO.cpp"
  echo "%SRC%\GameShared\GameClasses\System\AttribSys\CgsAttribSysModule.cpp"
  echo "%SRC%\GameShared\GameClasses\System\AttribSys\CgsAttribSysMemoryManager.cpp"
  echo "%SRC%\GameShared\GameClasses\System\AttribSys\CgsAttribSysPackageAllocator.cpp"
  echo "%SRC%\GameShared\GameClasses\System\AttribSys\CgsAttribSysVaultArray.cpp"
  echo "%SRC%\GameShared\GameClasses\System\AttribSys\CgsAttribSysVaultSlot.cpp"
  echo "%SRC%\GameShared\GameClasses\System\AttribSys\CgsAttribSysVaultLoad.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\common\attribhash64.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\common\attribarray.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\AttribVector_TypeDescPtr_operator_index.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\CgsShaderConstantTable.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\common\attribloadandgo.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\common\attribdatabase.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\common\attribdatabaseprivate.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\common\attribclassprivate.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\common\attribhashmap.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\common\attribcollection.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\common\attribsupport.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\common\attribgarbagecollector.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\common\AttribHashMapTablePolicy.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\vechashmap.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\attribsys.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\attribsysallochooks.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\export\attribexportmanager.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\export\attribiexportpolicy.cpp"
  rem (data-seam wave: the three world prop/sound resource types + the graphics list home)
  echo "%SRC%\SharedClasses\Physics\Props\BrnPropGraphicsList.cpp"
  rem (world-render resource-type handlers: registered 2026-07-27)
  echo "%SRC%\SDKs\RenderEngineClub\MAIN\components\src\states\programbuffer.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\cross\CgsMaterialResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\Resources\CgsShaderTechniqueResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\x360\materialstates\CgsRwShaderProgramBufferResourceTypeX360.cpp"
  rem (textures/shaders wave 2026-07-28: MaterialTechniqueResourceType::PostFixUp now really
  rem  runs -- SHADERS.BNDL is staged -- and calls renderengine::BlendState::GetParameters
  rem  @0x82B60A50, whose real home is this SDK TU. Its local __debugbreak placeholder is gone.)
  echo "%SRC%\SDKs\RenderEngineClub\MAIN\components\src\states\blendstate.cpp"
  rem  renderengine::SamplerState::{GetResourceDescriptor @0x82B63588, Initialize @0x82B62630} --
  rem  the sibling of blendstate.cpp above; BrnPostFxShader::Construct builds its point / linear /
  rem  anisotropic sampler states through it (post-fx gate-flip wave, 2026-08-14). The TU has no
  rem  header of its own yet -- its three consumers (BrnIm3d.cpp, BrnRendererMemory.cpp,
  rem  BrnPostFxShader.cpp) each carry a byte-identical local declaration block; the mangled names
  rem  match (measured in the shader-class verify), which is what makes this a link and not a fork.
  echo "%SRC%\SDKs\RenderEngineClub\MAIN\components\src\states\samplerstate.cpp"
  echo "%SRC%\SharedClasses\Physics\Props\BrnPropGraphicsListResourceType.cpp"
  echo "%SRC%\SharedClasses\Physics\Props\BrnPropInstanceDataResourceType.cpp"
  echo "%SRC%\SharedClasses\Sound\World\BrnStaticSoundMapResourceType.cpp"
  rem ---- vehicle/wheel LIST data (vehicle-load wave, 2026-07-31) -------------------------
  rem  GameDataModule::Prepare stages 9 and 12 (PrepareVehicleList @0x8266C410 /
  rem  PrepareWheelList @0x8266D1F8) stream Vehicles/VehicleList.bundle + Wheels/WheelList.bundle
  rem  into pool 5 and hand the acquired resources to the two embedded list managers. Without
  rem  the two ResourceType handlers registered the pool stores a NULL mpResourceType and the
  rem  entry-array pointer is never rebased (same trap ZoneList/0xB000 hit on the PVS wave).
  rem  BrnVehicleGraphicsSpecResourceType (65542) joins them: MEASURED over
  rem  build/game/VEHICLES/VEH_PUSMC01_GR.BIN, it was the ONLY type in that bundle's
  rem  {0,1,10,12,13,14,15,42,65542} set without a registered handler.
  echo "%SRC%\SharedClasses\World\BrnVehicleGraphicsSpecResourceType.cpp"
  echo "%SRC%\SharedClasses\DataLists\VehicleList.cpp"
  echo "%SRC%\SharedClasses\DataLists\VehicleListEntry.cpp"
  echo "%SRC%\SharedClasses\DataLists\VehicleListResourceType.cpp"
  echo "%SRC%\SharedClasses\DataLists\WheelList.cpp"
  echo "%SRC%\SharedClasses\DataLists\WheelListResourceType.cpp"
  rem  [challenge-list wave 2026-08-27] the THIRD member of the same family, and load-bearing
  rem  for the same reason: Prepare stage 10 (PrepareFreeburnChallengeList @0x8266C088) streams
  rem  "OnlineChallenges.bndl" into POOL 26 and acquires "B5ChallengeList". MEASURED against
  rem  build/game/ONLINECHALLENGES.BNDL: one resource, id 0x0D82D720 == HashString of that name,
  rem  type 0x1001F (65567), 458 challenges. With no registered handler the pool stores a NULL
  rem  mpResourceType, skips FixUp, and every record is reached through an un-rebased offset.
  echo "%SRC%\SharedClasses\DataLists\ChallengeListResourceType.cpp"
  rem  BrnWheelGraphicsSpecResourceType (65546) is the wheel twin of the vehicle spec above,
  rem  mounted by the LoadWheel wave (2026-08-03). Its body was reconstructed long ago and
  rem  simply never linked. It is LOAD-BEARING, not cosmetic: BundleLoader::LoadBundle gates
  rem  FixUp *and* ResolveImportsForEntry *and* PostFixUp on `mpResourceType != 0`, and the
  rem  shipped WHEELS/WHE_51916650_GR.BNDL's single 0x1000A resource carries TWO imports
  rem  (+0x04 / +0x08) that both point at type-42 CgsGraphics::Model resources in the same
  rem  bundle -- +0x04 is the wheel model RenderRaceCar's wheel block reads.
  echo "%SRC%\SharedClasses\World\BrnWheelGraphicsSpecResourceType.cpp"
  rem  ---- the player-car colour palette (colour-picker wave, 2026-08-02) -------------------
  rem  VEHICLELIST.BUNDLE's SECOND resource is a PlayerCarColours payload, type 0x1001E
  rem  (65566). With no registered handler the pool logged "[bundle] UNREGISTERED resource
  rem  type id 65566" and skipped FixUp, the "CarColours" acquire replied with a NULL memory
  rem  pointer ("carColours=0"), and the car-livery colour picker was empty. The handler was
  rem  already reconstructed; it simply did not compile for x64 (it spelled the load-base
  rem  truncations as reinterpret_cast<u32>(pointer)). Both colour-array columns inside the
  rem  record stay 32-BIT SERIALISED SLOTS -- proven twice in BrnGlobalColourPalette.h, from
  rem  the shipped platform-4 bytes and from GetColourPaletteFromType's own 12-byte stride.
  echo "%SRC%\SharedClasses\Graphics\PlayerCarColoursResourceType.cpp"
  rem  ---- the offline progression resource (progression-load wave, 2026-08-11) ------------
  rem  PROGRESSION.DAT's single resource is id 0x988F38C0 == HashString("ProgressionData"),
  rem  type 0x1000E (65550) -- the exact name+id ProgressionManager::LoadProgressionData
  rem  @0x82399ED0 loads the bundle for and then acquires from pool 5. The handler TU existed
  rem  but was never in this list and was never registered, so the acquire would have taken
  rem  the null-mpResourceType path and BundleLoader would have skipped all three fix-up
  rem  passes -- and EVERY table base in a ProgressionData payload is a serialised 32-bit
  rem  offset that only ProgressionData::FixUp rebases. Registered in
  rem  CgsResourceTypeRegistration.cpp; FixUp/FixDown live in the already-mounted
  rem  SharedClasses\Progression\BrnProgressionData.cpp, so this costs no new externals.
  echo "%SRC%\SharedClasses\Progression\BrnProgressionResourceType.cpp"
  rem  ---- the ICE take-dictionary list (2026-08-01, ICEList wave) --------------------------
  rem  The THIRD resident data table beside VehicleList/WheelList (X360 GameDataModule member
  rem  +457664, attested twice: PrepareICEList's AddListResource target and
  rem  ProcessGetICEListRequest's reply payload both spell `this + 0x70000 - 0x440`).
  rem  Whole TU already reconstructed; it was simply never in this list.
  echo "%SRC%\SharedClasses\DataLists\ICEList.cpp"
  rem  DictionaryBase::FixUp/FixDown -- the untyped dictionary relocation pass. FixUp
  rem  @0x828157F8 is ABSENT from the .ida-exports set (the gap between
  rem  BaseLinkedList::InternalRemoveNode 0x82815708 and FixDown 0x82815848); recovered
  rem  from the ARTIST IDA database with headless IDA 9.3. Links clean on its own.
  echo "%SRC%\GameShared\GameClasses\Containers\CgsDictionary.cpp"
  rem  ---- THE ICE TAKE RUNTIME (2026-08-01, ICE take-runtime wave) -------------------------
  rem  MOUNTED. The previous wave measured this group at 15 unresolved externals and left it
  rem  out; ELEVEN of those fifteen were bodies the X360 export set already carries -- just
  rem  not under a NAME, so a name-based search found nothing. Recovered as unnamed subs,
  rem  each pinned by its caller set (see the GROUP 5 banner in ICEData.cpp):
  rem    sub_8252F848 = ICETake::GetValueFloat(s32,u16)  sub_8252F8F0 = GetValueInt(s32,u16)
  rem    sub_82534118 = ICETake::SetParameter(f32,bool,bool)  <- the take-level playback driver
  rem    sub_82533360 = ICETake::SetSubTake(s32,bool)   (its assert names ICEData.cpp:2575)
  rem  plus IsEditable / GetKeyIndex / GetNumKeys / GetNumIntervals / GetKeyData /
  rem  GetParameterData / ICETakeData::GetName, which the console INLINES everywhere (bodied
  rem  in the headers beside the other trivial accessors, each cited to the inlined asm),
  rem  ICE_EPSILON (the value is X360 flt_8207AB94 == 1e-5f, read out of two pseudocode sites
  rem  that folded the literal) and spICEMemory. ICEMath.cpp + ICEDataEnums.cpp +
  rem  ICEDataICETake.cpp came along and closed Round / ICEParameter::SetValue /
  rem  MarkChannelFromSubTake / FlushUndo.
  rem  MEASURED: 15 -> 14 (5 TUs) -> 0 (6 TUs + the recovered bodies). No compile errors.
  rem  ?????? ICEFile.cpp is mountable only because FileClose was split into ICEFileClose.cpp:
  rem  it is the sole EA::GameTalk user in the ICE package (measured at +5, and +3 even with
  rem  GameTalk.cpp mounted) and it serves a debug XML dumper. See that file's header.
  echo "%SRC%\GameShared\GameClasses\Containers\CgsDictionaryResourceType.cpp"
  echo "%SRC%\SDKs\Packages\ICE\ICEData.cpp"
  echo "%SRC%\SDKs\Packages\ICE\ICEDataICETake.cpp"
  echo "%SRC%\SDKs\Packages\ICE\ICEDataEnums.cpp"
  echo "%SRC%\SDKs\Packages\ICE\ICEMath.cpp"
  echo "%SRC%\SDKs\Packages\ICE\ICEFile.cpp"
  echo "%SRC%\GameSource\Physics\BrnPhysicsModuleIO_InputBuffer.cpp"
  echo "%SRC%\GameSource\Physics\BrnPhysicsModuleIO_InputBuffer_Accessors.cpp"
  rem  ---- CLOSURE-ENFORCEMENT MOUNTS (PhysicsModule::Update closure wave 2026-08-06) ----
  rem  Both TUs are bodied ('done' in the ledger) and were measured link-GREEN this wave; mounted
  rem  so their closure stays enforced (mount-gap doctrine: /OPT:REF strips the bytes, the link
  rem  keeps the contract). NOTE: BrnPhysicsModuleBridgeFunctions.cpp was trial-mounted the same
  rem  day and is NOT green: 18 LNK2019 (its own facade helpers -- GetOutContactSpy,
  rem  4x SortAndCreateRunList, DeformationManager_Fixup*, StoreContact, ... see the wave report).
  echo "%SRC%\GameSource\Physics\BrnPhysicsModuleIO_OutputBuffer.cpp"
  echo "%SRC%\GameSource\Physics\BrnPhysicsQueueFacades.cpp"
  rem  ---- BRIDGE DE-FACADE MOUNTS (2026-08-06, step 1 of the PhysicsModule::Update subtree) ----
  rem  BrnPhysicsModuleBridgeFunctions.cpp is REWRITTEN as the real private PhysicsModule members
  rem  (the 18-LNK2019 facade note above is retired); its closure TUs mount with it:
  echo "%SRC%\GameSource\Physics\BrnPhysicsModuleBridgeFunctions.cpp"
  echo "%SRC%\GameSource\Physics\BrnPhysicsModuleIO_PotentialContactInterface.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\BrnContactSpyEvents.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\ContactSpyQueue_RaceCarContact_300_SortAndCreateRunList_8.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\ContactSpyQueue_TrafficContact_400_SortAndCreateRunList_64.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\ContactSpyQueue_PhysicalCarPartContact_150_SortAndCreateRunList_50.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\ContactSpyQueue_PropContact_100_SortAndCreateRunList_100.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\BrnContactSpyRunList.cpp"
  rem  ---- PHYSICS MOUNT-GAP WAVE B1 (2026-08-24): GameShared/Physics 46/46 ----
  rem  Small explicit-instantiation/accessor TUs (EventQueue_*/BaseEventQueue_* et al),
  rem  census-verified at definition level; the 16 apparent clashes vs mounted
  rem  IO/interface TUs are comment cross-refs only. The link is the real test.
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_InAddJoint.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_InAddJoint_GetEvent.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_InAddPotentialContact_AddEventSafe.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_InApplyForce.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_InChangeRigidBodyInertia_Append.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_InRemoveJoint.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_InRemoveRigidBody_Append.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_InUpdateExternalBody_Append.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_InUpdateRigidBody_AddEvent.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_OutContactSpy_AddEvent.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_OutContactSpy_AddEventSafe.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_OutContactSpy_GetEvent.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_OutDriveSpy_AddEvent.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_OutJointSpy_AddEvent.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_OutJointSpy_GetEvent.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_OutUpdateRigidBody_AddEvent.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\CgsCollisionMeshData_embed_check.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\CgsInstanceCollisionListResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\Deformation\BrnWheelPhysicalStates.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InAddDrive_1.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InAddJoint_10.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InAddPotentialContact_1024.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InAddRigidBody_1.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InAddRigidBody_200.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InAddRigidBody_50.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InApplyForce_250.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InChangeRigidBodyInertia_200.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InRemoveAllRigidBodies_8.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InRemoveDrive_1.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InRemoveJoint_10.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InRemoveJoint_36.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InRemoveRigidBody_200.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InRemoveRigidBody_50.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InSetDriveSpy_1.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InSetJointSpy_36.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InSetRigidBodySpy_200.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InUpdateDriveDynamics_1.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InUpdateDriveFrames_1.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InUpdateExternalBody_200.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InUpdateExternalBody_60.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InUpdateJointFrames_36.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InUpdateJointLimits_36.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_InUpdateRigidBody_200.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_OutContactSpy_800.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_OutDriveSpy_1.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\EventQueue_OutJointSpy_64.cpp"
  rem  BrnDeformationManager_Contacts.cpp itself STAYS UNMOUNTED (its SolvePenetration /
  rem  UpdateTriangleCache / spatial-query tail carries ~19 unresolved of its own); the four
  rem  bridge callees were split into the _ContactFixups slice below (fold back when it mounts).
  echo "%SRC%\GameSource\Physics\DeformationManager\BrnDeformationManager_ContactFixups.cpp"
  rem  ??? 2026-08-14 (walls leg 1): the per-car collision-query slice DoRaceCarWorldContact-
  rem  Generation needs per frame -- IsUsingSweptSpheres @0x825C2338 + GetSweptSpheresForCar
  rem  @0x825C22D0 (MOVED out of the still-unmounted _Contacts.cpp, same precedent as the
  rem  _ContactFixups slice above) + GetSpheresForCar @0x825C2260 (EXPORT HOLE, lifted from the
  rem  image; returns -1 gracefully, no assert -- NOT the swept sibling's shape).
  echo "%SRC%\GameSource\Physics\DeformationManager\BrnDeformationManager_ContactQueries.cpp"
  rem  2026-08-06 (big-five #2, contact-generation wave): the contact-BRIDGE slice consumed by
  rem  PhysicsModule::BridgeContactsToSimulation -- ReadPotentialVehicleWorldContact +
  rem  FindModelIndexByGlobalEntityID (moved out of the still-unmounted _Contacts.cpp),
  rem  the NEW ReadPotentialContact, and the two Bridge*CarContactsToSimulation trap stubs.
  echo "%SRC%\GameSource\Physics\DeformationManager\BrnDeformationManager_ContactBridges.cpp"
  rem  ...and its storage callee, sliced out of the still-unmounted BrnDeformationSensor.cpp:
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnDeformationSensor_ValidateAndAddContact.cpp"
  rem  2026-08-06 (big-five #2, contact-generation wave, slice B): StartVehicleContactGeneration's
  rem  home TU + its closure -- the pair-list builder bodies, the contact-gen list bodies, the
  rem  producer Begin slice (home TU still carries DataStreamCommandPoster::Construct demands),
  rem  and the collide-stream trap-stub TU.
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManagerContactGeneration.cpp"
  rem  ?????? 2026-08-14 (walls leg 3): THE VALIDATION WHALE -- ValidateRaceCarWorldContact
  rem  @0x825C6088 (988; PS3 0x70AB20) in its own slice TU (home BrnVehicleManager.cpp still
  rem  unmounted). Every constant image-read (cull height 0.4 @0x82F2A148; wall-normal
  rem  threshold 0.5, dynamic-init @0x82C5BBD8; curb 0.25 / wall-Y 0.3 / 25 / 10 mph statics;
  rem  mph factor @0x8208F820); the two VMX-dense blocks raw-word decoded (the vperm operand
  rem  trap + the console's local-Y lower-bound quirk live there, both settled from the words).
  rem  Also carries Vehicle::DebugComponent::SetLastWallTriangle @0x825B4D60 (see its banner:
  rem  the declared home TU stays unmounted on purpose -- vtable/base-surface risk).
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_ValidateRaceCarWorldContact.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\Collision\Primitives\CgsPrimitivePairListBuilder.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\Collision\Primitives\CgsPrimitivePairList.cpp"
  echo "%SRC%\GameSource\Physics\BrnContactGenerationList.cpp"
  echo "%SRC%\GameShared\GameClasses\Memory\DataStream\CgsSimpleDataStreamProducer_Begin.cpp"
  rem  ?????? 2026-08-14 (walls leg 1): THE COLLIDE-STREAM FAMILY IS REAL -- six of the seven
  rem  StreamStubs retired into CgsCollisionGenerator_CollideStreams.cpp (three Create* proved
  rem  byte-identical bar assert lines; three Run* dispatchers wiring ContactGeneratorEntry over
  rem  desc types 6/14/8 whose workers stay LOUD NAMED GATES; the two Add* posters + the
  rem  PrepareNewPrimitiveTestResultsList result-list carve). StreamStubs kept ONLY the
  rem  CollidePrimitivePairList @0x82814138 gate until wave Q7 (2026-08-19) landed it for real (40 insns).
  rem  DoRaceCarWorldContactGeneration @0x825EB140 is REAL in BrnVehicleManagerContactGeneration
  rem  .cpp (its log-once gate + Start's null-producer guard both deleted); its query callees
  rem  live in the new mounted slice BrnDeformationManager_ContactQueries.cpp below.
  rem  ?????? RUNTIME STATE (walls leg 2, 2026-08-14): CONTACTS EXIST. The case-6 gate is GONE --
  rem  ExecuteSphereListWithTriangleListStream @0x829235C8 (100) + ExecuteSphereListWithTriangleList
  rem  @0x829226A8 (967) + LoadPrimitives @0x829210F0 / LoadResultList @0x829211E8 are REAL in
  rem  ContactGeneratorJob.cpp, and the kernel IntersectTriangle4Sphere_HackyBurnoutVersion
  rem  @0x8283D2E0 (497) is REAL in CgsTriangleSphere.cpp (mounted at the Intersection block).
  rem  ?????? RUNTIME STATE (walls leg 3, 2026-08-14): THE HARVEST + VALIDATION ARE REAL. Landed:
  rem  EndVehicleContactGeneration @0x8261AC38 (661; the HIDE_ONLINE network-unhide tail is a
  rem  loud gate, provably dead offline -- needs Box::Set @0x825E6918 + BoxOverlappingTest) +
  rem  AddContactResultsToQueue @0x825EB350 (222) + DoRaceCarWorldContactValidation @0x825EB6C8
  rem  (416) in BrnVehicleManagerContactGeneration.cpp; ValidateRaceCarWorldContact @0x825C6088
  rem  (988) in its slice TU (see the mount line below); StartPartContactGeneration @0x8262C220
  rem  PARTIAL (the miFirstPartContactGenEntry boundary stamp the harvest reads is real, the
  rem  part-contact tail is a named gate); PotentialContactInterface::AddEvent(u32,...)
  rem  @0x825E73D0; RaceCarPhysics::GetHeightAboveRoad @0x825B3998 signature FIXED (the dropped
  rem  Vector3 query-point argument -- PS3 mangle + DWARF :310 authority). Boot witnesses,
  rem  log-once, all three on one boot: "sphere-vs-triangle CONTACTS LIVE: 24" -> "world
  rem  contacts HARVESTED: 24 PotentialContact(s) in the race-car-vs-world queue [5]" -> "world
  rem  contacts VALIDATED: 24 of 24 raw contact(s) accepted into the Validated queue [6]"
  rem  (24/24 == the sub-10-mph accept-all path; the resting car). Queue [6] feeds the ALREADY-
  rem  LANDED bridge (BridgeContactsToSimulation -> ReadPotentialVehicleWorldContact ->
  rem  DeformationSensor::ValidateAndAddContact) -- real world contacts now reach the car's
  rem  deformation sensors every frame.
  rem  RUNTIME STATE (walls leg 4, 2026-08-14): THE PENETRATION-SOLVER LEG IS LIVE. The whole
  rem  deformation conductor runs per frame (mgr Update @0x82649B40 -> obj Update @0x82649160 ->
  rem  UpdateContacts @0x826478B0 -> ApplyCarWorldImpulse (PS3 0x746D68; X360 hole) ->
  rem  ApplySensorImpulse; post-physics mgr UpdatePostPhysics @0x82630420 -> SolvePenetration
  rem  @0x82621B08 with Solve() x2 per BOTH consoles + obj UpdatePostPhysics @0x825DFEB0 +
  rem  AddArticulatedJointContacts @0x825DB190). Boot witness (log-once): 'penetration solver
  rem  LIVE: 22 world contact(s); pos ... -> <identical>' == ~zero correction at rest, the
  rem  invariant the leg was gated on. KA_IMPULSE_DIRECTIONS recovered (PS3 init 22) -- the two
  rem  flagged-zero direction tables that silently zeroed every impulse are RETIRED.
  rem  WHAT IS LEFT: DeformationSensor::ApplyLocalImpulse (PS3 0x74D3A0, 569 -- the sensor
  rem  point-displacement/absorption whale, LOUD GATE; deformation visuals also need the
  rem  _Output closure) ; obj UpdateWheels @0x826254C0 (1125) + the UpdateGlass leg of
  rem  UpdateIKAndLocators (both log-once gates); the module-output scene interface is
  rem  UNPREPARED on PC (SetEntityRadius guarded, [marked deviation]); the detach paths carry
  rem  named gates (dead at 0 parts). The swept twins
  rem  (ExecuteSweptSphereListWithTriangleListStream 1620 / IntersectTriangle4SweptSphere 896 /
  rem  Intersect2DCircleWithTriangleSOA 156) stay a LATER leg. A verified head-on WALL-FACE stop
  rem  was NOT captured this wave: full-lock drives circle the junkyard floor for 190s with
  rem  contacts held and NO tunnel-through; straight/loose drives exit via the junkyard's OPEN
  rem  side into unstreamed world and hit the PRE-EXISTING long-drive fallthrough (streamer
  rem  asserts), which is NOT a wall tunnel.
  rem  ?????? RUNTIME STATE CORRECTED (walls leg 5, 2026-08-15) -- MEASURED with a new opt-in
  rem  BRN_WALL_PROBE=1 instrument in SolvePenetration phase 3 (per-model world/wall contact
  rem  counts, the solver correction, EDGE-TOUCH/EDGE-CLEAR transitions):
  rem   * THE SOLVER IS NOT A SILENT ZERO. Driving the car into the wall face at z~-2039 gives
  rem     the DRIVEN model 21 wall contacts and a real positional correction (corr 0.1707 /
  rem     0.2399 on separate runs). Solve()'s world arm clamps depth at zero, so the permanent
  rem     0.000000 seen at rest is the correct "nothing is penetrating" output.
  rem   * ?????? BUT THE WALL TAKES NO MOMENTUM. Through a 14 m/s impact the car's velocity is
  rem     UNCHANGED (vz -14.09 -> -14.17 -> -14.12 -> -13.87) and it passes through: the full
  rem     contact face registers for only TWO frames at that speed. The momentum change rides
  rem     DeformationSensor::ApplyLocalImpulse, which is still the GATED whale below. So leg 4's
  rem     "zero at-rest correction" invariant was real but CANNOT distinguish a correct idle
  rem     solver from a silently-zero one -- only a real penetration can, and now one has.
  rem   * ?????? leg 4's "full-lock drives circle the junkyard floor with contacts held and NO
  rem     tunnel-through" is TRUE BUT NOT EVIDENCE OF THE SOLVER: what holds the car on the
  rem     floor is the wheel/traction system, the car never met a wall on that path, and the
  rem     circling is a YAW INSTABILITY (heading rotates a full turn every ~1 s after any
  rem     steering input is released), not a controlled turn.
  rem   * MAP (measured): junkyard staging bay at (2987.0, -3.2, -2011.4) with TWO parked
  rem     deformation models sitting against its walls; the handover TELEPORTS the driven car to
  rem     the gameplay spawn (3007.97, -2.89, -1945.21) facing +Z. Straight ahead (+Z) is the
  rem     OPEN side -- it falls out at z~-1842. Straight REVERSE is dead-straight and stable and
  rem     meets a real wall face at z~-2039 before the world edge at z~-2055.
  rem   * ??? TWO PROBE ARTIFACTS CAUGHT AND FIXED IN THE INSTRUMENT, both of which had produced
  rem     confident wrong readings: (a) counting the solver's WHOLE GetWorldContacts() array
  rem     attributed the PARKED car's wall contacts to the driven one (both models printed
  rem     identical counts -- world contacts are keyed miIndexA == model index); (b) a single
  rem     shared sample counter ALIASES against the live model count, so with 3 models only one
  rem     is ever sampled and the others read as absent.
  rem   * PenetrationSolver::GetWorldContacts / GetVehicleContacts were DECLARED-ONLY with no
  rem     body since the header was written -- no link had ever caught it because no committed
  rem     caller existed. Bodied.
  rem  ????????? THE OVERSTEER IS SOLVED (2026-08-15) -- and the culprit was a PLACEHOLDER'S VALUE,
  rem  not the tyre model. VehiclePhysics::GetSurfaceGrip @0x825D51B8 computes
  rem  `1 - (1 - gripTable[id]) * blend` -- a LERP FROM 1.0 toward the surface's grip, whose
  rem  IDENTITY ELEMENT IS 1.0. The per-surface tables are runtime-loaded scratch globals this
  rem  tree cannot yet recover, and all three of them shared ONE flagged-zero placeholder. For
  rem  roughness and drag (`table * scale * blend`) zero IS the identity and the stand-in was
  rem  right; for grip it collapses the expression to `1 - blend` and hands the car's raw
  rem  surface-sensitivity factor through as a permanent grip CUT -- and that factor is a
  rem  DIFFERENT LANE PER AXLE (.x SurfaceFrontGripFactor, .y SurfaceRearGripFactor). So the
  rem  placeholder did not merely reduce grip, it reduced the two axles by different amounts.
  rem   * MEASURED with a new opt-in BRN_TYRE_PROBE=1 instrument in HandleWheelPairFriction
  rem     (per-wheel enable/load/lateral speed/lateral+longitudinal force pre- and post-cone/
  rem     cone latch/arm/yaw moments, plus the body's yaw rate, steering angle and inverse yaw
  rem     inertia). On the Hunter Cavalry, with the zero placeholder:
  rem         front wheels   sGrip 0.736000   adhCap 19872.000000
  rem         rear  wheels   sGrip 0.200000   adhCap  5399.999512
  rem     -- a 3.68x FRONT/REAR ASYMMETRY IN THE FRICTION CONE. Every capped rear sample landed
  rem     on 5400.0 N exactly; the front never once reached its own ceiling. Under a held lock
  rem     the rear cone was exceeded on 95% of frames against the front's 4%, and rear
  rem     |longitudinal slip| averaged 13.2 -- a permanent burnout. A rear axle spending its
  rem     whole force budget on drive torque has nothing left to resist yaw.
  rem   * THE FIX is one value: the grip lookup gets its OWN placeholder returning 1.0, so an
  rem     un-recovered table is INERT. No maths changed, no term added, no damper, no clamp.
  rem     Both axles then read sGrip 1.0 / adhCap 27000 and neither binds; the cone falls back to
  rem     `dynamicFrictionCo * (N + downForce)` ~8767..9120 N, front and rear alike, which is
  rem     what the console computes on a full-grip surface. DELETE-WHEN unk_82FB8890 is recovered.
  rem   * CONTROLLED, because "it drives better now" is not evidence. The identical drive script
  rem     was re-run against a build with the value flipped back to 0.0. Same schedule, one value
  rem     apart: peak sideslip through the turn 112.6 deg vs 8.9 deg; the control rotated 240 deg
  rem     while covering 8 m and scrubbed to a standstill, the fixed build tracked a clean 11 m
  rem     radius arc; and 4 s of full throttle in a straight line reached 11.54 m/s vs 19.83 m/s
  rem     -- the rear cone was throttling STRAIGHT-LINE traction by 42% as well.
  rem   * ??? leg 5's "the heading rotates a full turn every ~1 s" is now a SETTLED YAW RATE: under
  rem     a steady lock the probe reads yaw 1.06 / 1.16 / 1.21 / 1.27 / 1.20 / 1.34 / 1.43 / 1.37
  rem     / 1.29 / 1.19 / 1.09 rad/s -- a plateau that then decays with the speed -- against a
  rem     pre-fix mean of 1.887 and max 3.526 with no plateau at all. On release the yaw rate
  rem     falls to -0.0004 and the heading holds -16.3 deg for 250 frames while the car coasts to
  rem     rest. The car drives straight, turns on an arc, and stops pointing where it was aimed.
  rem   * CLEARED BY THE SAME PROBE, so nobody re-chases them: the wheel force arms are correct
  rem     (front local z +1.4237, rear -1.4237 -- opposite signs about the COM); the yaw inertia
  rem     is real (invYaw 0.000273 => I_yaw 3663 kg m^2 for 1589 kg), built by
  rem     SimpleVehiclePhysics::SwitchAttribs/SetAttributes from mHalfExtent, not a placeholder;
  rem     and the per-corner load is real (397.17..397.33 kg, N 3895..3898) via
  rem     CalculateWeightTransfer. ?????? HandleWheelPairFriction's own 18-line "NOTHING IN THIS TREE
  rem     WRITES massOnWheel" banner is STALE -- that writer landed in the leg-4 wave.
  echo "%SRC%\GameShared\GameClasses\SceneManager\Collision\ContactGenerator\CgsCollisionGenerator_CollideStreams.cpp"
  rem  2026-08-19 (wave Q7, cluster pairlist): CgsCollisionGenerator_StreamStubs.cpp is EMPTY and UNMOUNTED --
  rem  its last gate, CollidePrimitivePairList @0x82814138 (40 insns, not 92), is a real body in
  rem  CgsCollisionGenerator.cpp beside CollidePrimitiveListAgainstTriangleList (seven of seven birth
  rem  stubs retired; dumpbin measures 0 external symbols). Its type-10 worker
  rem  ContactGeneratorJob::ExecutePrimitivePairList @0x82925798 landed in the same wave (cluster arms).
  rem  ??? 2026-08-14 (walls leg 2): the result-record TU mounts -- PrimitiveTestResult::IsValid
  rem  @0x82921378 is REAL (its "unrecoverable rodata threshold" floor fell to the .rdata unlock:
  rem  unk_821016C0 word 0 == 0x34000000 == 2^-23; the check is finite-xyz + non-degenerate
  rem  normals) and the sphere contact worker calls it per queued record. Also carries
  rem  CollisionResultList::SetNumResults @0x8280FFE8 / GetResult @0x828A9EF8.
  echo "%SRC%\GameShared\GameClasses\SceneManager\Collision\Primitives\CgsCollisionResult.cpp"
  rem  ?????? 2026-08-10 (cache-fill wave): the BaseCollisionGenerator HOME finally mounts. It has
  rem  been fully reconstructed since 2026-08-06 (Construct / Prepare / Finish / FinishBatch /
  rem  CreateNewBatch / AllocateJob / GetResultList / CreateStreamProducer) but stayed off the
  rem  link, so WorldModule::Update's per-frame generator was carved and never initialised behind
  rem  two WorldLinkStubs gates -- BOTH NOW DELETED. This is a LIVE behaviour change: the frame's
  rem  collision generator is really Construct()ed and Prepare()d from the frame it lands.
  rem  wave Q6 / worldc (2026-08-19): CgsCollisionBatch.cpp MOUNTED -- CollisionGenerator::
  rem  CollidePrimitiveListAgainstTriangleList (real now) calls CollisionBatch::SetupJob out of line
  rem  exactly as the console does (bl at 0x82814304).
  echo "%SRC%\GameShared\GameClasses\SceneManager\Collision\ContactGenerator\CgsCollisionBatch.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\Collision\ContactGenerator\CgsCollisionGenerator.cpp"
  rem  2026-08-06 (big-five #1, FixUpVehicleContacts wave): the driver's home TU + the
  rem  DeformationManager vehicle-contact fix-up slice (ByInterpolation / WithBoxes /
  rem  FixUpVehicleContact / GetInterpolatedContactPointAndNormal / CalculateTangentPoints /
  rem  the two Project* helpers), its DeformableObject accessor slice, and the _BBox slice
  rem  that owns GetDeformationSphereFromVolumeInstance. All strip under /OPT:REF until
  rem  PhysicsModule::Update lands -- mounted for closure enforcement only.
  echo "%SRC%\GameSource\Physics\BrnPhysicsModuleUpdateFunctions.cpp"
  rem  ADDED 2026-08-27 (showtime S3 wave): PhysicsModule::HandleGameActions @0x825A72F0 (185)
  rem  -- the physics side of the game-action pipe, and the ONLY console road into
  rem  VehicleManager::SetPlayerCarToShowtimeMode @0x8259C108. Its conductor gate is deleted in
  rem  the same commit; its five VehicleManager leaves live in BrnVehicleManagerPlayerStats.cpp
  rem  (already mounted). HandleGameActionsPostScene @0x825A70C0 stays gated -- zero of its five
  rem  callees exists; see the boundary note in BrnPhysicsConductorGates.cpp.
  echo "%SRC%\GameSource\Physics\BrnPhysicsModuleGameActions.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\BrnDeformationManager_VehicleContactFixUp.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnDeformableObject_Accessors.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnDeformableObject_BBox.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnPhysicalBodyPartPool_Accessors.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnDetachedWheelManager_Accessors.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_ValidateSimulationContacts.cpp"
  rem  ---- PHYSICS MOUNT-GAP WAVE B3a (2026-08-24): VehicleManager clean set 61 ----
  rem  SharedIO event-queue instantiation TUs + event payload TUs + embed_checks,
  rem  census-verified at definition level (dataclear_log Q4). The specials (monolith,
  rem  CrashPrediction, DebugUI family) are handled individually below/after.
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnPhysicalTrafficManager_embed_check.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_CreateArticulatedTrafficEvent_AppendAddEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_CreatePhysicalTrafficEvent_AppendAddEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_CreateRaceCarEvent_AppendAddEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_ImpactEvent_GetEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_ImpactEvent_GetEvent_const.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_PhysicalTrafficState_AddEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_PhysicalTrafficState_Append.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_PhysicalTrafficState_GetEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_RaceCarCrashEvent_AppendAddEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_RaceCarCrashEvent_GetEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_RaceCarResetEvent_AddEventAppend.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_RemoveTrafficEvent_Append.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_ResetVehicleEvent_AppendAddEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_SetRaceCarCollisionEvent_AppendAddEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_SetRaceCarCullingGroupEvent_AppendAddEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_SetTrafficCrashingEvent_AppendAddEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_TrafficCrashedEvent_AppendAddEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_TrafficRemovedEvent_AddEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_TrafficRemovedEvent_Append.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_TrafficRemovedEvent_GetEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_TrafficSlammedEvent_AppendAddEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_UpdateNetworkTrafficEvent_AddEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_UpdateNetworkTrafficEvent_Append.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_ValidateRaceCarEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_VehicleAddedForCollisionEvent_AppendAddEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_VehicleAddedForCollisionEvent_GetEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_VehicleEvents_embed_check.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BrnPhysicalTrafficState.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\CreateArticulatedTrafficEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\CreatePhysicalTrafficEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_CreateAirRamEvent_20_Construct.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_CreateArticulatedTrafficEvent_10.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_CreatePhysicalTrafficEvent_25.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_CreateRaceCarEvent_8.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_CreateSpinEvent_10_Construct.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_CreateVehicleResult_8.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_CreateWorldEvent_1.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_ImpactEvent_16.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_PhysicalTrafficState_20.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_RaceCarCrashEvent_8.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_RaceCarResetEvent_8_Construct.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_RemoveRaceCarEvent_8.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_RemoveTrafficEvent_25.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_ResetVehicleEvent_16.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_SetRaceCarCollisionEvent_10.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_SetRaceCarCullingGroupEvent_10.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_SetTrafficCrashingEvent_25.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_TrafficCrashedEvent_10_Construct.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_TrafficCrashedEvent_20_Construct.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_TrafficRemovedEvent_25.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_TrafficSlammedEvent_20_Construct.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_UpdateNetworkTrafficEvent_20.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_ValidateRaceCarEvent_8.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_VehicleAddedForCollisionEvent_64.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_VehicleAddedForCollisionEvent_8.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\EventQueue_unsigned_short_32_Construct.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\TinyStructs_embed_check.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\VehicleEvents_embed_check.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\B5PhysicsHandlingDebugComponent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\BrnGripCurveDebugGraph.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\BrnGripCurveDebugWindow.cpp"
  rem  ---- PHYSICS MOUNT-GAP WAVE B3b (2026-08-24): the VehicleManager MONOLITH flip ----
  rem  BrnVehicleManager.cpp (12 real bodies incl. the 923-insn SetRaceCarCrashing @0x82634C90;
  rem  the LinkStubs trap is DELETED) + BrnVehicleManager_ImpactHelpers.cpp, the NEW slice with
  rem  the six declared-only helpers reconstructed from asm (IsPointBetweenTwoParallelPlanes,
  rem  CheckForVerticalTakedownSituation, CheckForGrindingAndRubbing, GenerateContactSituation,
  rem  ApplySlam, ApplyShunt) plus their callees (CalculateSlamData/CalculateShuntData/
  rem  SendImpactMessage, HasRaceCarHadRecentImpact). Both geometry helpers had WRONG inferred
  rem  signatures in the header; the T-bone and vertical-takedown call sites are rebuilt from
  rem  the caller asm (@0x8263D480 / @0x8263D728).
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_ImpactHelpers.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\Engine_embed_check.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\RaceCarPhysics_embed_check.cpp"
  rem  2026-08-06 (PhysicsModule::Update leaves wave): the four small per-frame leaves of
  rem  PhysicsModule::Update (FreeAllocations / UpdateVehicleEffects / ReadUpdatedBodyProperties /
  rem  ProcessDeformationStates) -- slice TU, home BrnVehicleManager.cpp still unmounted.
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_PerFrameLeaves.cpp"
  rem  ?????? 2026-08-10 (create-path wave): THE PER-FRAME GRAVITY + INTEGRATION STEP --
  rem  VehicleManager::ReadUpdatedBodies @0x82619A10 (198) + PhysicalTrafficManager::
  rem  ReadUpdatedBodies @0x825EF608 (334). Deletes the conductor gate of the same name.
  rem  Despite the name neither reads a body back: it is the only place gravity enters a car
  rem  and the only place a car's pose advances.
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_ReadUpdatedBodies.cpp"
  rem  ?????? 2026-08-11 (PHYSICS->OUTPUT PUBLISH WAVE): THE LEG THAT PUTS A SIMULATED CAR WHERE
  rem  THE WORLD CAN SEE IT. VehicleManager::WriteOutVehicleStats @0x8263F460 (380, conductor
  rem  gate DELETED) + VehicleManager::IsRaceCarHidden @0x825C2EA0 (104, trap stub DELETED --
  rem  it was mis-recorded as an .ida-exports hole; pulled headless from the IDB). It copies
  rem  mUsedRaceCars into the VehicleOutputInterface -- the single store the whole world-side
  rem  readback is gated on -- and drives the per-car publish below.
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_WriteOutVehicleStats.cpp"
  rem  ...and the function that actually WRITES a RaceCarState. VehicleOutputInterface::
  rem  UpdateRaceCarState @0x825EC808 (535) + the three inlined DWARF setters (SetEntityID /
  rem  SetRaceCarHidden / SetWheelTransform). It was ABSENT FROM THE TREE ALTOGETHER -- not
  rem  gated, not stubbed, not declared -- which is why the readback had nothing to read.
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BrnVehicleOutputInterface_UpdateRaceCarState.cpp"
  rem  ?????? 2026-08-10 (producer wave): THE LEG THAT REGISTERS A CAR WITH THE TRIANGLE CACHE.
  rem  VehicleManager::Prepare @0x8263C688 (75, WorldLinkStubs gate DELETED) + VehicleManager::
  rem  PrepareTriangleCache @0x82615BA0 (37). Slice TU; home BrnVehicleManager.cpp still unmounted.
  rem  Its stage-1 arm VehicleManager::PrepareData @0x82633568 (161) stays a NAMED stub -- see
  rem  WorldLinkStubs.cpp for the two measured reasons and exactly what is dropped.
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_Prepare.cpp"
echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_PrepareData.cpp"
  rem  ?????? 2026-08-10 (create-path wave): THE MAINTENANCE SPINE -- the leg that finally gives the
  rem  create path a caller. VehicleManager::ProcessVehicleMaintenanceEvents @0x8264AB38 (118) is
  rem  real here; its five arms + the traffic twin are NAMED one-shot gates.
  rem  ??? STALE NOTE CORRECTED (create-drain wave): this line used to say "ProcessCreateEvents
  rem  @0x82616770 (1067) stays a gate ON PURPOSE ... the traction-line chain must land first",
  rem  and that the gate PRINTS the undrained CreateRaceCarEvent queue length. NOT TRUE ANY MORE --
  rem  the real ProcessCreateEvents body is mounted below (see the CREATE DRAIN block), so the
  rem  create queue is drained, not counted. Slice TU; home BrnVehicleManager.cpp still unmounted.
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_MaintenanceEvents.cpp"
  rem  (BrnVehicleManager_CreateRemoveEvents.cpp was git rm'd in the dev merge 42d98158 -- its one
  rem  body duplicated the SetAllNetworkRaceCarsHidden already in _MaintenanceEvents.cpp above.)
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_InRemoveRigidBody_AddEvent.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\BaseEventQueue_DeactivateDeformationModelEvent_AddEvent.cpp"
  rem  ??? 2026-08-10 (create-path wave): PURE MOUNT GAP, found by an LNK2019 and not by a grep.
  rem  PostSceneUpdate calls VehicleManager::SetPlayerActiveRaceCarIndex @0x8259C028, which has
  rem  been BODIED in BrnVehicleManagerPlayerStats.cpp all along in a TU nothing ever compiled
  rem  (this file's own note at the _layout_check mount already said "NEITHER of those TUs is in
  rem  the build list"). Mounting it also finally COMPILES VehicleManager::_AssertLayoutPlayerStats,
  rem  a layout gate that had never once run, and brings ApplyPlayerStats / SetShowtimeBehaviour /
  rem  SetPlayerCarToShowtimeMode / HasRaceCarHadRecentImpact / GetVehiclePhysi with it.
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManagerPlayerStats.cpp"
  rem  ?????? 2026-08-10 (ground wave): THE TRACTION-LINE PRODUCER LIFECYCLE + THE RACE-CAR HARVEST.
  rem  DoVehicleTractionLineAllocations @0x825B5098 / RunTractionLineTestJobs @0x825B5168 /
  rem  DoVehicleTractionLineDecallocations @0x825B5268 / ReadRaceCarTractionLineTestResults
  rem  @0x82618058 (the one that reaches AddTractionPoint -> mbIsOnGround).
  rem  ??? NOT WIRED IN: their only callers (StartVehicleTractionLineTests, EndVehicleTraction-
  rem  LineTests) stay gated -- the generation half needs the absent TriangleCacheManager, and
  rem  the two halves are lifetime-coupled through mpTractionLineStreamProducer. Mounted so the
  rem  LINK closure is enforced; /OPT:REF keeps the bytes out until they are called.
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_TractionLineTests.cpp"
  rem  ?????? 2026-08-11 (lifetime wave): the SceneManagerIO leaf TU mounts, and the LINK is what
  rem  found it. AddRaceCarTractionLineTests calls TriangleCacheInterface::GetNumCachedTriangleBatches
  rem  @0x82277880 -- declared since its own wave, bodied since its own wave, and never once linked,
  rem  because its home TU had no mounted caller. Two functions, both already reconstructed
  rem  (SceneQueryInterface::HasData @0x82204E48 is the other).
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsSceneManagerModuleIO.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\SharedIO\EventQueue_PotentialContact_2048.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\SharedIO\BaseEventQueue_PotentialContact_AddEvent.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\BaseEventQueue_OutOverlapPair_AddEvent.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\EventQueue_OverlappingPair_128_Construct.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\EventQueue_Contact_16384_Construct.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\EventQueue_ErrorEvent_128_Construct.cpp"
  rem  Its floor: the line-vs-triangle stream factory + the job dispatcher, plus the result-cursor
  rem  slice the harvest walks.
  rem  ????????? 2026-08-11 (traction-line wave): RunLineWithTriangleListStream @0x82810E80 (89,
  rem  export hole, lifted from the image) is now a REAL BODY and its boot gate is DELETED.
  echo "%SRC%\GameShared\GameClasses\SceneManager\Collision\ContactGenerator\CgsCollisionGenerator_LineStream.cpp"
  echo "%SRC%\GameShared\GameClasses\Memory\DataStream\CgsSimpleDataStreamProducer_ResultIterator.cpp"
  rem  ????????? 2026-08-11 (traction-line wave): THE DRAIN. Until this TU, the triangle cache filled
  rem  with real Paradise City geometry every frame and nothing read it.
  rem    ContactGeneratorEntry                             @0x82920F10  (80, EXPORT HOLE, lifted)
  rem    ContactGeneratorJob::Execute                      @0x829267E0  (77)
  rem    ContactGeneratorJob::ExecuteLineWithTriangleListStream @0x82921968 (589) -- Moller-
  rem      Trumbore, single-sided, SoA over four triangles per Triangle4 block, t clamped to the
  rem      segment. The whole kernel is INLINED in the console (xrefs_from has no CgsGeometric
  rem      call at all), so this needs neither IntersectLinePolygonSoupNearestSingleSided nor
  rem      PolygonSoupListSpatialMap::RunQuery -- both of which earlier costings put on this leg.
  rem    ContactGeneratorJob::AllocateMemory               @0x829212A0  (54)
  rem    ContactGeneratorJob::RestoreMemory                @0x82921050  (39)
  rem  ALL ELEVEN worker arms are real as of wave Q7 (2026-08-19): nine in ContactGeneratorJob.cpp,
  rem  two in ContactGeneratorJob_wQ7_01.cpp (no gate left in the TU). ??? NOT WIRED INTO THE CONDUCTOR: StartVehicleTractionLineTests /
  rem  EndVehicleTractionLineTests stay gated -- they are lifetime-coupled through
  rem  mpTractionLineStreamProducer and must land together, in a later wave.
  echo "%SRC%\GameShared\Jobs\ContactGenerator\ContactGenerator.cpp"
  echo "%SRC%\GameShared\Jobs\ContactGenerator\ContactGeneratorJob.cpp"
  rem  2026-08-19 (wave Q6 round 3, pvt + gpi): THE PROP NARROW PHASE. ExecutePrimitiveListWithTriangleList
  rem  @0x82925908 (849) is a REAL BODY (its BRN_CONTACT_JOB_GATE deleted) and its two callees
  rem  BuildGPInstance @0x829222A0 / CollideGPInstances @0x829253C8 live in the partfile -- mount as a pair.
  echo "%SRC%\GameShared\Jobs\ContactGenerator\ContactGeneratorJob_wQ6_01.cpp"
  rem  2026-08-19 (wave Q7, clusters ss + arms): THE CAR-vs-CAR SPHERE NARROW PHASE -- job types 7 and 8.
  rem  ExecuteSphereListWithSphereList @0x829215B0 (193) and its Stream twin @0x82923758 (100, export hole
  rem  closed with headless idat), the last two BRN_CONTACT_JOB_GATE arms. Declared in ContactGeneratorJob.h,
  rem  defined here; ContactGeneratorJob.cpp has NO gate for them any more, so this line is load-bearing
  rem  (two LNK2019s without it). The producer VehicleManager::DoCarCarContactGeneration @0x8261BB38 and its
  rem  poster AddSphereListWithSphereListToStream @0x828119F0 landed in the same wave (cluster carcar).
  echo "%SRC%\GameShared\Jobs\ContactGenerator\ContactGeneratorJob_wQ7_01.cpp"
  rem  ??? 2026-08-10 (ground wave): the SimpleDataStreamProducer HOME finally mounts.
  rem  ?????? 2026-08-10 (cache-fill wave): its one unresolved edge since 2026-08-06 --
  rem  DataStreamCommandPoster::Construct @0x82869E08, an export-set hole -- is now a REAL
  rem  BODY lifted from the image into the poster's own home TU, so the trap TU
  rem  CgsDataStreamCommandPoster_LinkStub.cpp is DELETED (was mounted here).
  echo "%SRC%\GameShared\GameClasses\Memory\DataStream\CgsSimpleDataStreamProducer.cpp"
  rem  ?????? 2026-08-06 (big-five #3, UpdateVehiclePhysics wave): the per-frame FORCE PRODUCER
  rem  VehicleManager::UpdateVehiclePhysics @0x82644FA8 (1,038 insns) FULL body + four in-TU
  rem  siblings (IsRaceCarCrashing / ForceRaceCarCrash-5arg==sub_82635B78 / ProcessAboveGround-
  rem  LineTestsResults / ProcessAftertouchEvents) -- slice TU, home BrnVehicleManager.cpp still
  rem  unmounted. Its honest-closure remainder is NAMED trap stubs in BrnVehicleManagerLinkStubs
  rem  (all dead until PhysicsModule::Update lands -- that wave must resolve every stub there).
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_UpdateVehiclePhysics.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManagerLinkStubs.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleConstants.cpp"
  rem  ?????? 2026-08-11 (prepare-chain wave): the DRIVER-CONTROLS CONSUMER, VehicleManager::
  rem  UpdateDrivers @0x82642C68 (120 insns) -- slice TU, home BrnVehicleManager.cpp still
  rem  unmounted. ??? THIS MOUNT IS MANDATORY, NOT OPTIONAL: the same commit DELETES the
  rem  UpdateDrivers gate from BrnPhysicsConductorGates.cpp, and its caller
  rem  (BrnPhysicsModuleUpdateFunctions.cpp's driver stage) is already mounted and live -- so
  rem  without this line the build loses the symbol outright (LNK2019).
  rem  Its own link closure is already here: the five dispatch arms (UpdatePlayer/AI/Network-
  rem  Driver, PhysicalTrafficManager::UpdateTrafficDriver, DoHornTakedowns -- 1,346 console
  rem  instructions, all still BODYLESS) are named gates in BrnPhysicsConductorGates.cpp above,
  rem  msPlayerParams comes from RaceCarPhysics.cpp below, and GetTargetAssistParams from
  rem  SharedIO\BrnVehicleDriverInputInterface.cpp. Nothing new is dragged in.
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_UpdateDrivers.cpp"
  rem  ?????? 2026-08-11 (create-drain wave, same day): the FIVE driver dispatch arms
  rem  (UpdatePlayer/AI/NetworkDriver + DoHornTakedowns; traffic twin in its own slice below) --
  rem  their five gates are DELETED from BrnPhysicsConductorGates.cpp, and UpdateDrivers above is
  rem  live every frame, so BOTH mounts are mandatory (LNK2019 otherwise). Note DoHornTakedowns
  rem  -> InstantTakedown, whose only body is in the UNMOUNTED BrnVehicleManager.cpp -- if the
  rem  link 2019s on it, split the body into a slice TU (RaceCarPhysics_Construct precedent);
  rem  its own callee SetRaceCarCrashing resolves to the loud LinkStubs trap, which is the
  rem  honest state for the horn-cheat edge path.
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_DriverArms.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnPhysicalTrafficManager_UpdateTrafficDriver.cpp"
  rem  ...and the InstantTakedown split the note above predicted: the link DID 2019 on it, so the
  rem  body moved byte-identical from the unmounted BrnVehicleManager.cpp into its own slice
  rem  (RaceCarPhysics_Construct precedent). Its callee SetRaceCarCrashing = the loud LinkStubs trap.
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_InstantTakedown.cpp"
  rem  ????????? THE CREATE DRAIN MOUNTS (create-drain wave): ProcessCreateEvents @0x82616770 -- the
  rem  ONLY writer of mUsedRaceCars in the XEX. Setting that bit switches on the four already-
  rem  mounted per-frame loops (ReadUpdatedBodies gravity, UpdateVehiclePhysics force path,
  rem  contact generation, traction harvest) against the car the Prepare chain just filled.
  rem  The author deliberately left this line to the conductor: the mount belongs to a commit
  rem  whose gated run is actually BOOTED. This is that commit -- do not cherry-pick the line
  rem  out of it.
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_ProcessCreateEvents.cpp"
  rem  ?????? RaceCarPhysics.cpp MOUNTS (same wave): the per-car dispatch target RaceCarPhysics::
  rem  Update + ~40 showtime/aftertouch bodies. Its banner's five measured LNK2019s resolve as:
  rem  ??? STALE NOTE CORRECTED 2026-08-11 (orchestrator re-audit). This line used to say
  rem  "VehiclePhysics::Update + UpdateSteering -> trap stubs in VehiclePhysicsLinkStubs.cpp (the
  rem  integrator orchestrator seam, still THE wall)". THAT IS NO LONGER TRUE and it has now sent
  rem  one wave at an already-closed hole. All THREE of that LNK triple are resolved in-tree:
  rem    VehiclePhysics::Update       @0x826412C0 (200) -- BODIED, VehiclePhysics.cpp:5849.
  rem      Re-verified against the ARTIST asm this wave: callee set 16/16 exact vs xrefs_from,
  rem      call ORDER exact, no absent callee.
  rem    VehiclePhysics::UpdateSteering @0x825D3720 (577) -- BODIED, VehiclePhysics.cpp:5661,
  rem      to the DWARF signature (f32, f32, VecFloat, bool).
  rem    VehiclePhysics::AddTractionPoint(s32,u32) -- NEVER EXISTED. The DWARF carries
  rem      AddTractionPoint only on SimpleVehiclePhysics and RaceCarPhysics, both 4-arg; the
  rem      2-arg symbol was a mangling artifact of a since-deleted stand-in decl in
  rem      VehiclePhysics.h that HID the base overload. Both real bodies are landed.
  rem  THE WALL MOVED UPSTREAM: it is now VehicleManager::UpdatePlayerDriver @0x825E9F38 (401),
  rem  the BRN_CONDUCTOR_GATE in BrnPhysicsConductorGates.cpp where the player's controls record
  rem  stops -- so the orchestrator below runs every frame on an all-zero controls record.
  rem  GetAftertouchValues -> overload fork DELETED
  rem  (the 4-arg ref form @0x825B2E88 is the leaf; BrnPlayerDriverControls.cpp mounts below);
  rem  gbVehicleBounceBoosting -> extern RETIRED (it was a data fork of msPlayerParams
  rem  .mbLaunchActive -- one console byte, two PC names; see RaceCarPhysics.cpp).
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\RaceCarPhysics.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BrnPlayerDriverControls.cpp"
  rem  ...and its two link dependencies: UpdateShowtimeBounceModifiers + the msPlayerParams
  rem  singleton (split out of the still-unmounted RaceCarPhysics.cpp, RaceCarPhysics_Construct
  rem  precedent), and DeformationState::GetCarStateF (bodied SharedIO slice, never mounted).
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\RaceCarPhysics_ShowtimeBounce.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\BrnDeformationState_DeformationState.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\BrnDeformationOutputInterface.cpp"
  rem  StreamedDeformationSpec (wheel-render wave, 2026-08-03): the car's authored WheelSpec
  rem  table -- GetWheelSpec is what RaceCarEntityModule::PublishRenderPoseWithoutPhysicsBringUp
  rem  reads the four wheel positions/scales out of. The body has existed since the deformation
  rem  wave and was simply never on this list (LNK2019 on first attempt).
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnStreamedDeformationSpec.cpp"
  rem  ...and its one link dependency, BodyPartBBoxSpec::HackCheckHandedness (called from the
  rem  spec's FixUp). Same story: body committed, never on the list.
  echo "%SRC%\SharedClasses\Physics\Deformation\BrnBodyPartBBoxSpec.cpp"
  rem  2026-08-14 (deformation-mount wave): the streamed-deformation-spec RESOURCE TYPE handler
  rem  (0x1001C / 65564, the deformation resource in every Vehicles\VEH_*_AT.bin). It existed,
  rem  unmounted AND unregistered -- the loader skipped FixUp and the first real spec walk after
  rem  the manager mount AV'd on an un-rebased serialised offset. Registered in
  rem  CgsResourceTypeRegistration.cpp with the IdList/ICETake/PlayerCarColours precedents.
  echo "%SRC%\SharedClasses\Physics\Deformation\Resources\StreamedDeformationSpecResourceType.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BrnVehicleManagerOutputInterface.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BrnVehicleOutputInterface.cpp"
  rem  ?????? 2026-08-09 (CONDUCTOR WAVE): PhysicsModule::Update @0x825B0640 IS REAL
  rem  (BrnPhysicsModuleUpdateFunctions.cpp). Three new mounts:
  rem    * BrnVehicleManagerIO.cpp -- the DWARF-true VehicleManagerOutputBuffer (the
  rem      "VehManager" stack buffer Update creates; the old invented VehicleManagerIO
  rem      class is retired by the same commit).
  rem    * BrnVehicleManager_ConductorLeaves.cpp -- UpdateCameraMatrix + the
  rem      empty-as-shipped ProcessWheelContacts.
  rem    * BrnPhysicsConductorGates.cpp -- THE NAMED DEFERRALS: every not-yet-reconstructed
  rem      direct callee of the conductor as a LOUD one-shot boot gate (symbol + X360
  rem      address + insn count, once per boot). Reconstruct each and DELETE its gate.
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManagerIO.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_ConductorLeaves.cpp"
  echo "%SRC%\GameSource\Physics\BrnPhysicsConductorGates.cpp"
  rem ---- VEHICLE-DYNAMICS CORE (physics wave 3, 2026-08-02) --------------------------------
  rem  The first vehicle-physics translation units ever mounted. Before this the whole domain
  rem  was unmounted: 119 reconstructed bodies, ZERO of them in the build.
  rem
  rem  MEASURED link closure of the full core (the eight below + VehiclePhysics.cpp + Engine.cpp):
  rem  17 unresolved externals. Fourteen were closed this wave -- six were SHADOWING
  rem  redeclarations in VehiclePhysics.h of members ExternalPhysicsBody/SimpleVehiclePhysics
  rem  already own (deleted), three were the rw::physics::RigidBody read accessors (bodied in
  rem  vendor/renderware/physics/RigidBody.cpp), and two callers of genuinely-unbodyable callees
  rem  were split into their own unmounted TUs (ExternalPhysicsBody_ReadPropertiesFromRenderware.cpp
  rem  and BrnSimpleVehiclePhysics_Construct.cpp -- see each file's banner).
  rem
  rem  ?????? UPDATE 2026-08-03 (CheckForEnteringDrift wave): **VehiclePhysics.cpp IS NOW MOUNTED.**
  rem  Its last unresolved external, VehiclePhysics::CheckForEnteringDrift, is bodied. That symbol
  rem  is ABSENT from `.ida-exports/BURNOUT_X360_ARTIST.XEX/` -- the third confirmed hole in that
  rem  export set -- but it is an ordinary named function inside the IDB (headless IDA 9.3:
  rem  `0x825FA448..0x825FA748`, 192 instructions), and the hole is visible from fn_index.txt alone
  rem  (EnterDrift @0x825FA268 is 120 instrs, so it ends exactly at 0x825FA448; the next indexed
  rem  symbol is UpdateDriftScale @0x825FA748).
  rem  The LNK2019's signature complaint was real AND bigger than one function: the DecFIGS DWARF
  rem  declares the WHOLE drift family with a trailing `VecFloat` time-step that the tree had
  rem  dropped from all five (UpdateDrift / UpdateDriftState / CheckForEnteringDrift /
  rem  ApplyDriftForces / UpdateDriftScale). All five are corrected; the dt turns out to have two
  rem  real consumers that had been written as `(void)` no-ops.
  rem  (RESOLVED, for the record: sizeof(BrnPlayerDriverControls) is 0x48, not 0x44 -- the X360
  rem  UpdateDriving does memcpy(&local, controls, 0x48) -- and +0x44 is meDriverType, so the
  rem  "==1" test is `driver type == E_DRIVER_TYPE_AI`. +0x4D and +0x4E are two DIFFERENT members
  rem  of BrnAIDriverControls. The committed comment and this one were each right about a
  rem  different call site.)
  rem  ?????? CLOSED 2026-08-03. Engine.cpp and VehicleAttribs.cpp were ONE mount, not two, and the
  rem  measured gap between them and the build was 32 unresolved externals:
  rem      29 x  BrnPhysics::Vehicle::EngineDefaults::KF_DEFAULT_*   <- VehicleAttribs.obj
  rem       2 x  BrnPhysics::InterpedParam3::Construct / ::Prepare   <- VehicleAttribs.obj
  rem       1 x  BrnPhysics::Vehicle::Engine::Reset(Vector4)         <- Engine.obj
  rem  All 32 are now defined and all three TUs are on the source list below.
  rem    * the 29 constants were read out of the image TWICE (a self-calibrating .id1 reader,
  rem      delta -1594 with 9/9 prologue witnesses, and headless IDA 9.3 on the .i64 -- identical).
  rem      WHICH .rdata slot lands in WHICH (register, lane) had to be settled by symbolically
  rem      SIMULATING EngineAttribs::Construct @0x825B7B90: 267 instructions that reuse eight stack
  rem      slots as scratch between lvlx/vspltw/vrlimi128 lane inserts. Hex-Rays decodes nine of
  rem      the constants inline and all nine match. Gear ratios come out -2.5 (reverse), 3.21,
  rem      1.93, 1.30, 1.00, 0.75 -- a real gearbox, which is the role check.
  rem    * InterpedParam3 got its DecFIGS home (GameSource/Physics/PhysicsUtilities/
  rem      InterpedParam3.{h,cpp}); VehicleAttribs.h had been carrying a private declaration with
  rem      the member typed Vector4 where the DWARF says Vector3. Its vperm mask table
  rem      unk_8327F140 is `.data` and reads ALL ZEROS, so the lane mapping came instead from
  rem      Frustum::SetPlaneByIndex @0x827BAA48 decoding the table index as `(i & 3) << 6`, plus
  rem      the DWARF's `Vector3 mvParams` and its "exactly three VecFloatRefIndex::operator=".
  rem    * Engine::Reset @0x825CF130..0x825CF274 (82 items) is the FOURTH confirmed export-set
  rem      hole (ComputeGear @0x825CF010 is 72 instrs so it ends exactly at 0x825CF130, and the
  rem      next indexed symbol is 0x825CF278); pulled with headless IDA 9.3.
  rem
  rem  ??? AND IT SETTLED TWO LIVE PLACEHOLDER BUGS IN THE ALREADY-COMMITTED Engine.cpp. Both were
  rem  `.data` slots that read zero in the image and are filled by IDA-unmarked static
  rem  initialisers; scratch/GVM/init_map_table.txt reports NO source for one and two
  rem  contradictory sources for the other, so both were recovered by disassembling the
  rem  initialiser thunks (0x82C5B0C8 and 0x82C5C050 -- the second is a COMPUTED initialiser,
  rem  1000.0 / flt_82F2A3E0):
  rem      unk_82FB9110 = 9.54929638   == 60/(2*pi), rad/s -> RPM
  rem      unk_82FB9B10 = 104.719757   == 1000 RPM in rad/s (Reset's idle flywheel speed)
  rem      flt_82F2A3E0 = 9.54929638   -- in `.data` but INITIALISED IN THE IMAGE, and no writer
  rem  ComputeGear carried the first as a FLAGGED 0.0f, which made its up-shift metric identically
  rem  zero and welded the gearbox in gear 1 forever; GetMaxWheelAngularVelocity carried the third
  rem  as a FLAGGED 1.0f, making the rev limiter 9.55x too permissive. ComputeGear was also missing
  rem  the asm's `vandc` sign-clear (fabs) and had its parameter declared `f32` when the asm plainly
  rem  uses vector register v1.
  rem
  rem  ??? CORRECTED, and this is why the count moved: the previous note blamed
  rem  "EngineAttribs::Construct, owned by VehicleAttribs.cpp, which cannot be mounted as-is
  rem  (rw::math::vpu ODR fork)". Mounting VehicleAttribs.cpp would NOT have closed it. The
  rem  console symbol is NESTED -- VehicleAttribs::EngineAttribs::Construct @0x825B7B90, which is
  rem  what Engine::Construct @0x825F3EE8 actually calls -- but Engine.h declared its own
  rem  EngineAttribs at NAMESPACE scope, so Engine.cpp emitted a call to
  rem  BrnPhysics::Vehicle::EngineAttribs::Construct, a symbol the console never had and no TU
  rem  could ever define. Engine.h's slice was a third fork, not a stand-in. It is retired now
  rem  (typedef to the nested type) and that LNK2019 is GONE from the measured list above.
  rem  Also stale in that note: "its mangled name says the parameter is a VecFloat, not the
  rem  Vector4 declared". In this tree VecFloat IS rw::math::vpu::Vector4 (BrnCommonTypes.h:23),
  rem  so the two mangle identically and the committed declaration is already correct.
  rem
  rem  ???????????? AND THE LAYOUT UNDER ALL OF THIS WAS WRONG UNTIL 2026-08-03. VehicleAttribs.cpp had
  rem  mDriftAttribs and mEngineAttribs TRANSPOSED against the DWARF, with static_asserts baking
  rem  it in. Referee: SetupAttribsForDonutAI @0x825F6298 writes [this+0x110].x = 0 and
  rem  [this+0x1B0].x = flt_8205820C; under the old layout that is "MinSpeedForDrift = 700,
  rem  Differential = 0" (a car that must do 700 mph to drift and cannot drive), under the DWARF
  rem  layout it is "MinSpeedForDrift = 0, MaxTorque = 700". Every mpAttribs read in the MOUNTED
  rem  VehiclePhysics.cpp (32 distinct offsets) lands on a name-matching DWARF field only under
  rem  the corrected layout. See VehicleAttribs.h's banner.
  rem
  rem  ???????????? MOUNTING THESE PUTS **ZERO BYTES** IN THE EXE TODAY, and that is expected, not a bug:
  rem  nothing calls any of them yet, so /OPT:REF strips every function (VERIFIED -- grep
  rem  Burnout_PC.map for ExternalPhysicsBody.obj / Wheel.obj / Spring1D.obj returns 0 symbols;
  rem  only BrnSimpleVehiclePhysics.obj's KV_ZERO datum survives). They are mounted anyway so the
  rem  closure is CONTINUOUSLY ENFORCED -- any future edit that re-opens it now fails the build --
  rem  and so the first real caller pulls the whole subsystem in with no mount work at all.
  rem  Do not read "mounted" here as "running".
  echo "%SRC%\vendor\renderware\physics\RigidBody.cpp"
  rem  rw::physics SOLVER SPINE (2026-08-04, task #121). Six read-only waves reconstructed the
  rem  EATech RenderWare rigid-body solver; this is where it lands.
  rem    Quaternion.cpp  -- Quaternion::UnitQuaternionToMatrix @0x82BC3EC0 (an EXPORT HOLE,
  rem                       recovered from the copy inlined into DynamicUpdate).
  rem    Simulation.cpp  -- GetResourceDescriptor / SetWorkspace / BatchIntegrator /
  rem                       Activate / Freeze / RemoveRigidBody.
  rem    RigidBody.cpp   -- now carries DynamicUpdate @0x82BC2B78, the per-body integrator.
  rem  ??? 2026-08-06: the Simulation_SimulationUpdate.cpp quarantine TU is DELETED -- all
  rem  eleven solver stages (ContactBatchBuild, the four pipelines, the three Spy* dumps)
  rem  are bodied and SimulationUpdate moved home into Simulation.cpp. Nothing calls it yet
  rem  (PhysicsSimulationModule::Update is unbodied), so /OPT:REF strips the cluster.
  rem  ?????? 2026-08-04 (task #135) -- THE "ZERO BYTES ENTER THE EXE" NOTE THAT USED TO STAND HERE
  rem  IS RETIRED. It said "nothing constructs a rw::physics::Simulation anywhere in the tree
  rem  (CgsPhysicsSimulationModule::mpSimulation is declared and never assigned), so this code
  rem  LINKS and cannot RUN." That is fixed at the ROOT: PhysicsSimulationModule::Prepare and
  rem  AllocateMemoryAndInitialiseRW are bodied, BrnPhysics::PhysicsModule::Prepare is bodied
  rem  (its stage 3 is what calls them), and Simulation::Initialize now exists. The simulation
  rem  is built at world-prepare time and mpSimulation is non-null from then on.
  rem    Simulation.cpp also gained Initialize @0x82BC5158 + RemoveJoint/RemoveDrive.
  rem    SimulationWorkspace.cpp gained Initialize (IDA calls it AptDisplayListState::GetFirstItem).
  rem    PairSet.cpp gained ClearAll @0x82BC6DC0 (a FOURTH confirmed export-set hole, pulled
  rem    out of the .i64 headless) -- and two console-stride bugs were fixed in it and in the
  rem    workspace sizer; see each function's banner.
  rem  ?????? The simulation EXISTS, is populated-capable and (2026-08-06) fully solvable, but it
  rem  still does NOT STEP: SimulationUpdate's caller chain is the remaining wall.
  echo "%VEN%\renderware\src\rw\physics\Quaternion.cpp"
  echo "%VEN%\renderware\src\rw\physics\Simulation.cpp"
  echo "%VEN%\renderware\src\rw\physics\SimulationWorkspace.cpp"
  echo "%VEN%\renderware\src\rw\physics\PairSet.cpp"
  rem    Jacobian.cpp -- Jacobian_RQD::Create @0x82BC0FA8 and DriveJacobian::GetMatIBT
  rem                    @0x82BC1128, plus the 384-byte jacobian RECORD declaration the two
  rem                    constraint builders write into.
  rem    FatBoxInertia.cpp -- rw::physics::ComputeFatBoxInertia @0x82BC6C80. MOUNTED 2026-08-27
  rem                    (detach-2 wave). The body has been committed and correct since the
  rem                    rw::physics landing; it was simply never in this list and had no
  rem                    declaration in any header, so no caller could reach it. Its first real
  rem                    caller is PhysicalBodyPart::AddToSim, which needs a shed panel's
  rem                    diagonal inertia before it can hand the part to the simulation.
  echo "%SRC%\vendor\renderware\physics\FatBoxInertia.cpp"
  rem  ============================================================================
  rem  MOUNTED 2026-08-27 (detach-2 wave). Twenty-seven one-function TUs -- explicit
  rem  template instantiations of BaseEventQueue<T>::{AddEvent,AddEventSafe,GetEvent,
  rem  Append} and EventQueue<T,N>::Construct over the contact-spy and prop event
  rem  records, plus their three small facade/embed-check TUs.
  rem  WHY MOUNT THEM AT ALL, stated honestly: /OPT:REF strips every one of them today,
  rem  because the contact-spy arm is dead (VehicleManager::ProcessContactSpies
  rem  @0x82646C98 is a boot gate) and nothing calls the prop queue facades yet. They
  rem  are mounted so the CLOSURE IS CONTINUOUSLY ENFORCED -- a mount is the only thing
  rem  that can find a shadowing redeclaration or an ODR fork in a header these TUs
  rem  share, and a link is the only tool that sees either. Do not read "mounted" as
  rem  "running": this buys a gate, not a behaviour.
  rem  ============================================================================
  rem  CONTACT-SPY EVENT-QUEUE CLOSURE (13 TUs)
  echo "%SRC%\GameSource\Physics\ContactSpies\BaseEventQueue_ContactSpyRunData_AddEvent.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\BaseEventQueue_DiscardedContact_AddEventSafe.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\BaseEventQueue_DiscardedContact_GetEvent.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\BaseEventQueue_HingedPartContact_AddEvent.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\BaseEventQueue_HingedPartContact_GetEvent.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\BaseEventQueue_PhysicalCarPartContact_AddEventSafe.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\BaseEventQueue_PropContact_AddEventSafe.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\BaseEventQueue_PropContact_GetEvent.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\BaseEventQueue_RaceCarContact_GetEvent.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\BaseEventQueue_TrafficContact_AddEventSafe.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\BrnContactSpyQueue.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\ContactSpyQueue_RaceCarContact_300_GetBaseContact.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\ContactSpyRunList_GetRunDataWithEntityID_8.cpp"
  rem  PROP SHARED-IO EVENT-QUEUE CLOSURE (14 TUs)
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\BaseEventQueue_AddPhysicalPartEvent_AddEvent.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\BaseEventQueue_AddPhysicalPropEvent_AddEvent.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\BaseEventQueue_UpdatePropEvent_AddEvent.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\BaseEventQueue_UpdatePropEvent_Append.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\BrnPropEvents.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\BrnPropEvents_GetEntityId_embed_check.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\BrnPropQueueFacades.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\EventQueue_AddPhysicalPartEvent_50.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\EventQueue_AddPhysicalPropEvent_50.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\EventQueue_PropRaceCarContact_30.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\EventQueue_PropUpdateNotification_200.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\EventQueue_PropUpdateNotification_Append.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\EventQueue_RemovePhysicalPartEvent_100.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\EventQueue_RemovePhysicalPropEvent_300.cpp"
  echo "%SRC%\vendor\renderware\physics\Jacobian.cpp"
  rem    The two constraint builders -- the largest functions in the closure and the last
  rem    thing standing between the solver and a real constraint:
  rem      DriveJacobian::Build @0x82BC5590 (1320 X360 insn)
  rem      JointJacobian::Build @0x82BC42E8  (873 X360 insn)
  rem    Mounting them also closes Simulation::Joint/DriveBatchBuild, which call them.
  echo "%SRC%\vendor\renderware\physics\DriveJacobian_Build.cpp"
  echo "%SRC%\vendor\renderware\physics\JointJacobian_Build.cpp"
  echo "%SRC%\GameSource\Physics\PhysicsUtilities\ExternallySimulatedBody.cpp"
  echo "%SRC%\GameSource\Physics\PhysicsUtilities\ExternalPhysicsBody.cpp"
  rem  ReadPropertiesFromRenderware: unmounted since physics wave 3 because
  rem  RigidBody::GetLocalInvInertiaDiagonal() could not be bodied while the Inertia pointer was
  rem  modelled as a float lane. The rw::physics landing promoted that lane to a real member, so
  rem  the blocker is gone and the TU links. Its only caller (BrnPhysicalBodyPart.cpp) is still
  rem  unmounted, so this too is closure only, not behaviour.
  echo "%SRC%\GameSource\Physics\PhysicsUtilities\ExternalPhysicsBody_ReadPropertiesFromRenderware.cpp"
  echo "%SRC%\GameSource\Physics\PhysicsUtilities\Spring1D.cpp"
  echo "%SRC%\GameSource\Physics\PhysicsUtilities\SuspensionSpring.cpp"
  rem  VehicleDriver (driver-controls layout wave, 2026-08-03): the per-car driver. Construct
  rem  @0x825B83C8 is bodied; the class is now the real type behind VehicleManager's
  rem  maRaceCarDrivers[8] and mPlayerAiDriver, replacing a 224-byte stand-in record.
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\BrnVehicleDriver.cpp"
  rem  VehiclePhysics.cpp (2026-08-03): 2600 lines, ~54 force/handling bodies -- drift, boost,
  rem  suspension, weight transfer, wheel friction, contact impulses. Mounted the moment its last
  rem  unresolved external (CheckForEnteringDrift) was bodied; see the block above.
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\VehiclePhysics.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\VehiclePhysics_embed_check.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\Wheel.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\ShuntEffect.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\BrnSimpleVehiclePhysics.cpp"
  rem  ??? 2026-08-03 -- THE 32 ARE CLOSED. VehicleAttribs.cpp and Engine.cpp are MOUNTED, together
  rem  with InterpedParam3.cpp (new: the DecFIGS home for BrnPhysics::InterpedParam3, whose two
  rem  leaves were 2 of the 32 and which VehicleAttribs.h had been carrying as a private
  rem  declaration). See the note above the vehicle-dynamics core for the breakdown.
  echo "%SRC%\GameSource\Physics\PhysicsUtilities\InterpedParam3.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\VehicleAttribs.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\Engine.cpp"
  rem  ??? 2026-08-03 (W-C wave) -- the two debug components VehicleManager::Construct @0x8263B7C8
  rem  and PhysicalTrafficManager::Construct @0x82636CA8 build. Both were empty/opaque slices
  rem  until now; both now carry their FULL DecFIGS member layout with the offsets asm-derived
  rem  from those two Constructs.
  rem    BrnVehicleManagerDebugComponent.cpp  -- NEW. VehicleManagerDebugComponent::Construct
  rem      @0x825B5A78 (194 instrs) + GetName @0x825B5D80 + a tamper-tested (5/5) _AssertLayout.
  rem      The class closes to 1296 bytes == BrnVehicleManager.h's mDebugComponent span.
  rem    BrnPhysicalTrafficManagerDebugComponent.cpp -- existed, but its ONLY include
  rem      ("DebugSystem/Core/CgsDebugComponent.h") resolved against no -I directory, so the file
  rem      had never compiled. Include fixed; Construct added (inlined at 0x82636DF8).
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManagerDebugComponent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnPhysicalTrafficManagerDebugComponent.cpp"
  rem  ???????????? 2026-08-03 (tuning-bank wave) -- BrnVehicleManager_layout_check.cpp is NEW and must
  rem  stay mounted. BrnVehicleManager.h claims its ~172 KB layout is "pinned by the offsetof
  rem  asserts in _AssertLayout / _AssertLayoutPlayerStats" -- but those live in
  rem  BrnVehicleManager.cpp and BrnVehicleManagerPlayerStats.cpp, and NEITHER of those TUs is in
  rem  this list. A static_assert in an uncompiled TU is a comment, not a gate, so that whole class
  rem  layout had never once been checked by a build. This TU is compile-only (one never-called
  rem  static member full of static_asserts, zero link closure) and pins the +171464..+172616
  rem  tuning bank that VehicleManager::Construct @0x8263B7C8 seeds.
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_layout_check.cpp"
  rem  ???????????? 2026-08-03 (RaceCarPhysics own-block wave) -- RaceCarPhysics_layout_check.cpp is NEW and
  rem  must stay mounted, for exactly the reason above one level down. RaceCarPhysics.h now carries
  rem  all sixteen of that class's DWARF members at their X360 seats, and the claim that makes it a
  rem  derivation rather than sixteen guesses is that the DWARF's member ORDER and the asm's member
  rem  OFFSETS close, with zero slack, on sizeof == 5216 -- the same 5216 BrnVehicleManager.h pins as
  rem  its per-car stride. Neither RaceCarPhysics.cpp nor RaceCarPhysics_embed_check.cpp is in this
  rem  list (grep: zero hits for RaceCarPhysics.cpp before this line), so a static_assert in either
  rem  of them would be compiled by nothing. This TU is compile-only -- one never-called static
  rem  member full of static_asserts, zero link closure -- and it also carries the record-side seats
  rem  for BrnVehicleManager's RaceCarVehicleRecord, which had the same hole.
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\RaceCarPhysics_layout_check.cpp"
  rem  ??? 2026-08-03 (VehicleManager::Construct wave) -- RaceCarPhysics_Construct.cpp is NEW.
  rem  RaceCarPhysics::Construct split out of RaceCarPhysics.cpp so it can be mounted: the eight-car
  rem  loop of VehicleManager::Construct calls it, and RaceCarPhysics.cpp itself must stay unmounted
  rem  while flt_820037C8 / unk_82FB8880 are unread. Its only callee is VehiclePhysics::Construct,
  rem  already mounted above. Same split precedent as BrnSimpleVehiclePhysics_Construct.cpp.
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\RaceCarPhysics_Construct.cpp"
  rem  ??? 2026-08-03 (task #110, the BrnVehicleManager mount survey) -- the articulation-joint pair
  rem  is MOUNTED. BrnArticulatedJointPool.cpp had never been in this list and had therefore never
  rem  been linked; mounting it exposed that its private re-declaration of ArticulatedJoint asked
  rem  for `int Construct()` while the real BrnArticulatedJoint.h declares `void Construct()` --
  rem  two different mangled names, so no TU could ever have satisfied its call site. That fork is
  rem  retired (see the banner in BrnArticulatedJointPool.cpp) and ArticulatedJoint::Construct
  rem  @0x825B8DC0 is now bodied in BrnArticulatedJoint.cpp (identity transform + invalid joint id).
  rem  ?????? SAME CAVEAT AS THE BLOCKS ABOVE: nothing calls either of these yet, so /OPT:REF strips
  rem  them and they put ZERO BYTES in the exe. Mounted so the closure stays enforced.
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\BrnArticulatedJoint.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\BrnArticulatedJointPool.cpp"
  rem  ?????? 2026-08-03 (task #112, the TrafficPhysics de-fork) -- TWO NEW FILES, BOTH REQUIRED.
  rem  BrnPhysicalTrafficManager.h no longer declares its own opaque `struct TrafficPhysics
  rem  { void Construct(); u8[5168]; }`; it includes the real class and embeds
  rem  `TrafficPhysics maFullTrafficPhysics[20]`. That was a CORRECTNESS item, not tidiness: the
  rem  mangled name ?Construct@TrafficPhysics@Vehicle@BrnPhysics@@QEAAXXZ encodes neither the
  rem  class-key nor the bases, so a body written against the real class would have linked against
  rem  the sliced call site silently, writing host-offset members into console-strided storage.
  rem    TrafficPhysics_Construct.cpp   -- NEW. TrafficPhysics::Construct @0x8262E980 (an
  rem      `.ida-exports` HOLE -- the JSON set jumps 0x8262E848 -> 0x8262EBE8; pulled with headless
  rem      IDA 9.3, 154 instructions) + SetFreakedOut @0x825B8948. Split out of TrafficPhysics.cpp
  rem      for the same reason as RaceCarPhysics_Construct.cpp. TrafficPhysics.cpp itself mounts
  rem      since wave T3 (VehiclePhysics::Prepare / UpdateShunt / UpdateCrashing are all bodied).
  rem    TrafficPhysics_layout_check.cpp -- NEW, compile-only, and it REPLACES a gate that had gone
  rem      vacuous. BrnVehicleManager_layout_check.cpp used to "check" the 0x1430 stride with
  rem      `static_assert(sizeof(TrafficPhysics) == 5168)` -- a HOST sizeof gate that only ever
  rem      asserted the stand-in was still a stand-in. The console 0x1430 is now derived as
  rem      arithmetic over the recovered seats, closing with zero slack from 0x13F0.
  rem      Tamper-tested 8 cases, 7 fire (the 8th is the documented 3-byte pad hole).
  rem    VehiclePhysicsLinkStubs.cpp -- NEW, and it is the MEASURED price of the fold, not a
  rem      convenience. Making maFullTrafficPhysics the real class puts TrafficPhysics's VTABLE on
  rem      the link's critical path (BrnPhysicsModule.obj emits the ctor chain that seats twenty
  rem      vptrs -- which is what the console ctor @0x827E42E8 does too), and the link named exactly
  rem      one missing slot: TrafficPhysics::Update, the only virtual the class introduces. Defining
  rem      it drags VehiclePhysics::UpdateShunt (@0x825FC748, 100 instrs) and ::UpdateCrashing
  rem      (@0x82638810, 732 instrs), neither of which has a body anywhere. Both are LOUD
  rem      CGS_ASSERT(false) traps, both are dead today, and bodying either one will fail with a
  rem      hard LNK2005 until the stub is deleted -- which is the point.
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\TrafficPhysics_Construct.cpp"
echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\TrafficPhysics.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\TrafficPhysics_layout_check.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\VehiclePhysicsLinkStubs.cpp"
  rem  ?????? 2026-08-03 (task #113, the ArticulatedJointPool de-fork) -- BrnPhysicalTrafficManager.cpp
  rem  IS NOW MOUNTED, together with the IO TU that owns its buffer accessors. What made it
  rem  mountable was NOT bodying one more function: it was retiring the last TWO ODR forks in
  rem  BrnPhysicalTrafficManager.h, and the second of those was never counted by any wave --
  rem    * ArticulatedJointPool          -- the real class had no header at all (it was declared
  rem      inside BrnArticulatedJointPool.cpp), which is why the fork existed. It has one now:
  rem      VehiclePhysics/BrnArticulatedJointPool.h. The fold is LAYOUT-NEUTRAL (the class is
  rem      pointer-free and 832 bytes on both targets), so nothing in the manager's layout moved --
  rem      unlike the TrafficPhysics fold, which moved everything behind it by -4160.
  rem    * ArticulatedJointCreateBuffer  -- a 16-byte opaque standing in for the 2032-byte class
  rem      BrnPhysicalTrafficManagerIO.h has owned since its own wave. ?????? NOT a layout-neutral
  rem      stand-in: AllocateInternalBuffers instantiates CreateIOBuffer<ArticulatedJointCreateBuffer>
  rem      on it, so mounting this TU with the fork in place would have allocated 16 bytes for a
  rem      2032-byte IO buffer. The fuse had not lit only because the TU had never been mounted.
  rem  ?????? The previous wave's "UNRESOLVED COUNT = 1, one body away" was measured correctly and
  rem  concluded wrongly: that one symbol was the FORK's mangled name
  rem  (?SendCreateRemoveJointEvents@...@@QEAAXPEBXPEAU..., i.e. `const void*` + non-const buffer),
  rem  while the DWARF signature is (VehicleOutputRequestInterface*, const ArticulatedJointCreateBuffer*).
  rem  No faithful body could ever have defined the symbol that call site asked for.
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnPhysicalTrafficManager.cpp"
rem  wave T3 physical traffic: Prepare @0x8262CA48 (the only seater of the 3 arrays),
rem  create/remove drain, UpdateTrafficPhysics @0x82644418, traction pair, WriteOutVehicleStats
rem  @0x825F0308 -- each retires its conductor gate in the same change.
echo "%SRC%\GameSource\Physics\VehicleManager\BrnPhysicalTrafficManager_Prepare.cpp"
echo "%SRC%\GameSource\Physics\VehicleManager\BrnPhysicalTrafficManager_Create.cpp"
echo "%SRC%\GameSource\Physics\VehicleManager\BrnPhysicalTrafficManager_Remove.cpp"
echo "%SRC%\GameSource\Physics\VehicleManager\BrnPhysicalTrafficManager_UpdateTrafficPhysics.cpp"
echo "%SRC%\GameSource\Physics\VehicleManager\BrnPhysicalTrafficManager_TractionLineTests.cpp"
echo "%SRC%\GameSource\Physics\VehicleManager\BrnPhysicalTrafficManager_WriteOutVehicleStats.cpp"
rem  wave T3 r2: the race-car-vs-physical-traffic response chain -- potential-contact averager,
rem  DoCrashPrediction @0x82645FE0 (its ConductorGates gate deleted in the same change),
rem  HandleCrashPredictionForRaceCarAndTrafficVehicle -> HandleRaceCarTrafficCarPotentialContact
rem  @0x8263FA50 -> the traffic crashing/slammed/checked response arms.
echo "%SRC%\GameSource\Physics\VehicleManager\BrnPotentialContactAverager.cpp"
echo "%SRC%\GameSource\Physics\VehicleManager\BrnPhysicalTrafficManager_CrashResponse.cpp"
echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_RaceCarTrafficContact.cpp"
echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_DoCrashPrediction.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnPhysicalTrafficManagerIO.cpp"
  rem  ????????? 2026-08-03 (task #116) -- UN-STUBBING BrnPhysics::PhysicsModule::Construct @0x825AE308.
  rem  That function had been a LIVE EMPTY STUB in WorldLinkStubs.cpp since 2026-07-26: a quiet
  rem  no-op reached every boot by the WorldModule::Construct cascade, so NOTHING in the physics
  rem  module was ever constructed -- every physics Construct this campaign landed hung off it.
  rem  Its X360 xrefs_from is a CLOSED set of ten callees, ALL of which already had bodies; only
  rem  three TUs were unmounted. The four lines below are the whole cost.
  rem
  rem  ?????? THE PREVIOUS PLAN ("mount BrnVehicleManager.cpp, close its 14 unresolved externals") WAS
  rem  NOT THE STEP. VehicleManager::Construct @0x8263B7C8 calls only SIX functions, five of them
  rem  already mounted; the 14 belong to the REST of BrnVehicleManager.cpp (HandleRaceCarRaceCar-
  rem  Contact / ApplySlam / ApplyShunt / SetRaceCarCrashing). Split-TU instead -- the same
  rem  precedent as RaceCarPhysics_Construct.cpp / TrafficPhysics_Construct.cpp.
  echo "%SRC%\GameSource\Physics\VehicleManager\BrnVehicleManager_Construct.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\StuntOffences\BrnStuntOffencesManager_Construct.cpp"
  rem  StuntOffencesManager's per-frame body is now closed over the exact DecFIGS APIs whose
  rem  inline Breaker sites arbitrate them (GetTimeDrifting/GetSpeed/GetSpeedMPH/GetPosition/
  rem  GetLinearVelocityDirection/GetPreviousControls/HasAir/GetAllWheelsHaveTraction).
  echo "%SRC%\GameSource\Physics\VehicleManager\StuntOffences\BrnStuntOffencesManager.cpp"
  rem  The deformation leg of PhysicsModule::Construct. Each of these is the SPLIT-OUT Construct of a
  rem  TU that cannot be mounted whole; every count below is a MEASURED trial link, not an estimate:
  rem     BrnDeformationManager.cpp        (2026-08-14: "25 unresolved" RETIRED -- re-measured 37
  rem                                       for the 4-TU family; full census at the walls-wave
  rem                                       block above)
  rem     BrnDeformationDebugComponent.cpp 53 unresolved (25 OnActivate, 12 RenderWorld, ...)
  rem     BrnPhysicalBodyPart.cpp          16 unresolved (TestJointForBreaking/RemoveFromScene/...)
  rem     BrnPhysicalBodyPartPool.cpp       9 unresolved (CreatePart/UpdateRWBodies/UpdateJoinedParts)
  rem  ??? Across all four, exactly ONE of those 103 was referenced from a Construct:
  rem  ExternalPhysicsBody::SetMass, now bodied in ExternalPhysicsBody.cpp (already mounted).
  echo "%SRC%\GameSource\Physics\DeformationManager\BrnDeformationManager_Construct.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\BrnDeformationConstructShims.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\BrnDeformationDebugComponent_Construct.cpp"
  rem  ---- PHYSICS MOUNT-GAP WAVE B2 (2026-08-24): DeformationManager 22/23 ----
  rem  The 22 census-clean TUs (SharedIO/instantiation + embed_checks + BrnDeformationState).
  rem  The intended 23rd (the BrnDeformationDebugComponent.cpp flip) was TRIED and REVERTED --
  rem  see its measured 39-unresolved banner below; the _Construct.cpp trap stubs stay.
  rem  ⛔ BrnDeformationDebugComponent.cpp DOES NOT MOUNT (RE-MEASURED 2026-08-24, wave B2): 39
  rem  unresolved -- 6 Debug3DImmediateRender::Draw* bodies (header-declared only; its .cpp
  rem  carries just SetDebugFont, the 3D draw path is the render follow-on), 7 of the component
  rem  OWN private methods (CompressSelectedRig, OnSensorPositionChange, the 3 tuning callbacks,
  rem  ResetSensors/ResetSelectedRig -- reconstructed NOWHERE), the IKDrivenPoint/TagPoint/
  rem  IKBodyPart accessors (no bodies anywhere), DeformableObject::GetDeformedBoundingBox +
  rem  RenderSensors, and 19 BrnPhysics::Deformation k*/gi* tuning globals homed in the
  rem  UNMOUNTED BrnPhysicalBodyPart.cpp (itself 16-unresolved, see below). The census marker
  rem  scan called it CLEAN-ish; the LINK says otherwise. The loud vtable trap stubs in
  rem  _Construct.cpp stay -- exactly the failure mode their banner designed for.
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnBurnoutBodyPartID.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnBurnoutWheelBodyID.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnIKDrivenPoint_embed_check.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnPhysicsDeform_embed_check.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\BaseEventQueue_BrokenJointNotificationEvent_Append.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\BaseEventQueue_DetachedPartCurrentPositionEvent_AddEventSafe.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\BaseEventQueue_DetachedPartCurrentPositionEvent_Append.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\BaseEventQueue_DetachedPartNotificationEvent_AddEventSafeAppend.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\BaseEventQueue_SetModelCollisionEvent_AddEvent.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\BaseEventQueue_SetModelCullingGroupEvent_AddEvent.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\BrnDeformationState.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\EventQueue_AddDeformationModelEvent_20.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\EventQueue_BrokenJointNotificationEvent_10.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\EventQueue_DeactivateDeformationModelEvent_28.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\EventQueue_DetachedPartCurrentPositionEvent_50.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\EventQueue_DetachedPartNotificationEvent_50.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\EventQueue_DetachedPartRenderEvent_50.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\EventQueue_GlassSmashOrCrackEvent_20.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\EventQueue_JointedPartStateEvent_50.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\EventQueue_RemoveDeformationModelEvent_20.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\EventQueue_SetModelCollisionEvent_28.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\EventQueue_SetModelCullingGroupEvent_28.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnPhysicalBodyPartPool_Construct.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnPhysicalBodyPart_Construct.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\BrnDeformationInputInterface.cpp"
  rem ????????? 2026-08-14 (deformation-mount wave): THE MOUNT IS EXECUTED. The walls-wave census's
  rem landing plan, carried out line for line:
  rem   * the 4-TU family mounts (home manager TU with OutputData SPLIT OUT to the unmounted
  rem     BrnDeformationManager_Output.cpp -- its conductor gate stays; the PostSceneUpdate gate
  rem     and the WorldLinkStubs Prepare stub are DELETED with the mount);
  rem   * the MOUNT-CLOSABLE set mounts (VehicleRigidBody / IKBodyPart / TagPoint / IKDrivenPoint /
  rem     the whole BrnDeformationSensor.cpp -- whose ctor+Prepare the census's "still to write"
  rem     row wrongly listed as absent; GetPlayerCarModel MOVED to the home TU from _Contacts);
  rem   * the STILL-TO-WRITE set is WRITTEN: ResetSensors @0x82623D60 (the whale, both-console
  rem     decode; sensor mVolInstId promoted at +0x190; J-offset/timestep constants image-read),
  rem     GetInitialCompressionScalesAndLimits @0x825DF6F8 (export HOLE -- recovered via the BL
  rem     word + ppcdis; the three KV3P ratio vectors were DYNAMIC-INIT, initializers found
  rem     @0x82C5D700/740/778: EVENT=(1,1,1,0.8) CAR_SELECT=(0.8,0.7,0.8,0.75) DEFAULT=0),
  rem     ResetJointVelocities @0x825DF810 (?????? the census note "zero xyz keep w" was INVERTED --
  rem     both consoles zero the W lane == SetJointVelocity(0)), RemovePhysicalPartsAndJoints
  rem     @0x82625250 + Pool::RemovePart @0x8260CA30 + Part::RemoveFromScene @0x825E7818 (dead at
  rem     runtime this wave, link-real), the write-side InputBuffer::GetRemoveRigidBodyQueue
  rem     @0x825BCF58, ImpulsePasser::SetCollidableBodyMap + SweptSphere::Set (new TUs, both
  rem     inline-attested at their ResetSensors call sites);
  rem   * the DEFERRABLE set keeps its gates: OutputData conductor gate; UpdateLocator @0x825E0EC8
  rem     log-once gate in the new IKSkinning slice (dead at runtime -- DeformationManager::Update
  rem     is still a gate); the two per-frame contact-generation traps DEGRADED to log-once gates.
  rem  FOLLOW-ON ROWS the mount surfaced (next wave's list, measured not guessed):
  rem   * DeformationSensor::ApplyLocalImpulse -- PS3 0x74D3A0 (569 insns), X360 export hole;
  rem     tonight a LOUD log-once gate (vtable satisfied); dead until contacts exist. Write it
  rem     with the (c) walls wave.
  rem   * FOUR sensor rodata rows are DYNAMIC-INIT (image-zero, probed): unk_82FB82C0 /
  rem     unk_82FB9F20 (sensor Prepare's per-direction displacement rows -- (d)'s FIRST missing
  rem     piece: with them at 0 the seeded sensors sit at REST, so authored initial damage cannot
  rem     displace a sphere), unk_82FB9680 (hit directions), unk_82FB9560 (absorption rows).
  rem     RECOVERY METHOD PROVEN TONIGHT: their initializers live in the 0x82C5Bxxx..0x82C5Dxxx
  rem     static-init region (the three KV3P ratio vectors + KVF_MIN/MAX_IMPULSE precedents were
  rem     all recovered exactly that way with ppcdis.py + x360rd.py).
  rem   * (d)'s SECOND missing piece: the damaged look cannot reach the RENDERER until the
  rem     _Output slice closure lands (OutputData's skinned-model tables are not homed).
  rem   * StreamedDeformationSpecResourceType.cpp carries a LOCAL 40-byte StreamedDeformationSpec
  rem     slice (pad+3 locator lists) in namespace Deformation -- a silent ODR fork whose
  rem     FixUp/FixDown calls happen to link against the real bodies. Retire it onto the real
  rem     header (the odr-forks-link-silently shape).
  rem   * PhysicsModule::Prepare stage 4's fourteen deformation-IO clears are STILL the documented
  rem     drop (no member maps for the two IO interfaces). Fresh-boot-equivalent to zero-init;
  rem     a REAL dropped clear on re-prepare now that the consumer is live.
  echo "%SRC%\GameSource\Physics\DeformationManager\BrnDeformationManager.cpp"
  rem  2026-08-24 (deform-land wave): the OUTPUT slice mounts -- OutputData's real body + the
  rem  newly-landed OutputSensorState @0x82605618 (export hole, pulled headless); its closure
  rem  (UpdateAndOutputJointStates @0x82609AE8 in _GlassState.cpp, pool OutputEvents @0x8260DBE8
  rem  in BrnPhysicalBodyPartPool.cpp, the DetachedPartManager wrapper) landed with it, and the
  rem  OutputData conductor gate in BrnPhysicsConductorGates.cpp is DELETED by the same commit.
  echo "%SRC%\GameSource\Physics\DeformationManager\BrnDeformationManager_Output.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnDeformableObject_Lifecycle.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnDeformableObject_Update.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnDeformableObject_GlassState.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnDeformableObject_IKSkinning.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnDeformationSensor.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnVehicleRigidBody.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnIKBodyPart.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnTagPoint.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnIKDrivenPoint.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnImpulsePasser.cpp"
  rem  (post-trial closure, 14 unresolved -> 0): the sensor TU's impulse/contact legs need the
  rem  absorption table + the penetration solver (both bodied, previously unmounted; the solver
  rem  gained its inline-on-console AddWorldContact/GetNumWorldContacts siblings this wave), and
  rem  seven console-inline accessors were header-inlined (GetNumSensors == spec count + 4,
  rem  IKBodyPart::GetNumberOfDrivenPoints, IKBodyPartSpec::GetJointSpec, TagPoint(Spec)::
  rem  GetDetachThresholdSquared, IKDrivenPoint x4). ImpulsePasser::PassOnImpulse written from the
  rem  PS3 body @0x6B4FB8; DeformationSensor::ApplyLocalImpulse (PS3 0x74D3A0, 569 insns, X360
  rem  hole) is a LOUD log-once gate -- dead at runtime until contact generation lands.
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnAbsorptionTable.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnPenetrationSolver.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnPhysicalBodyPart_Remove.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnPhysicalBodyPartPool_Remove.cpp"
  echo "%SRC%\GameShared\GameClasses\Geometric\Primitives\CgsSweptSphere.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CacheManager\BaseEventQueue_InEventRemoveFromCache_AddEvent.cpp"
  rem  ?????? 2026-08-14 (walls leg 4): THE PENETRATION-SOLVER LEG MOUNTS. The manager contact/solve
  rem  slice (SolvePenetration -- now Solve()x2 per both consoles -- + UpdateTriangleCache +
  rem  GetDeformedBBox), the DeformableObject home (ApplyCarCarImpulse + the NEW ApplyCarWorld-
  rem  Impulse from the PS3 0x746D68 body), the object contact slice (AddContactsToPenetration-
  rem  Solver + GetVehicleWorldRestitution + the world-contact-gen legs), the detach slice
  rem  (UpdateSpinningDetachment / CheckFor*Detachment), the two detached managers (part: Make/
  rem  UpdatePostPhysics/NEW UpdateTriangleCache; wheel: Remove*/UpdateTriangleCache/NEW filtered
  rem  UpdatePostPhysics + the two Emit* hook gates), the pool home (UpdateRWBodies/UpdateJoined-
  rem  Parts/NEW AddPartsToScene), the part home, and the NEW BrnCollidableBody.cpp (the RECOVERED
  rem  KA_IMPULSE_DIRECTIONS six-axis table + GetDirectionVector -- retires the two flagged-zero
  rem  direction tables that silently zeroed every impulse).
  echo "%SRC%\GameSource\Physics\DeformationManager\BrnDeformationManager_Contacts.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnCollidableBody.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnDeformableObject.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnDeformableObject_Contacts.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnDeformableObject_Detach.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnDetachedPartManager.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnDetachedWheelManager.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnPhysicalBodyPartPool.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnPhysicalBodyPart.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\DeformationPhysics\BrnPhysicalWheel.cpp"
  rem ?????? 2026-08-14 (walls wave): THE DEFORMATION-MANAGER MOUNT WAS TRIAL-LINKED AND MEASURED.
  rem The stale "25 unresolved" note (2026-08-03) below at the Construct leg is RETIRED -- mounting
  rem {BrnDeformationManager.cpp + BrnDeformableObject_{Lifecycle,Update,GlassState}.cpp} at the
  rem merged tip gives *** 37 unresolved *** (build\game\trial2_build.log), AFTER this wave fixed
  rem the two defects the trial surfaced (both committed):
  rem   * BrnDeformableObject.h fwd-declared the two Detached*Manager + PhysicalBodyPart as
  rem     `struct` while their homes say `class` -- a PEAU/PEAV mangle fork that made
  rem     DeformableObject::{Prepare,Release,ResetDeformation,OutputWheelData} defined-but-
  rem     unmatchable (the shadowing-redeclaration shape; only a link finds it, this one did).
  rem   * BrnDeformableObject_Update.cpp:456 called the pre-2026-08-02 3-arg
  rem     ApplyShowtimeContactImpulse (this TU had never compiled).
  rem THE REMAINING 37 SPLIT (addresses + sizes in the census; PS3 twins named where X360 lacks):
  rem   MOUNT-CLOSABLE (bodied, unmounted): VehicleRigidBody 2 virtuals (BrnVehicleRigidBody.cpp),
  rem     IKBodyPart x5 (BrnIKBodyPart.cpp), GetPlayerCarModel (BrnDeformationManager_Contacts.cpp
  rem     slice-out), TagPoint::Construct / IKDrivenPoint (their TUs).
  rem   BODIED THIS WAVE in the unmounted TUs (link tonight-ready): PostSceneUpdate @0x82644F40,
  rem     ProcessValidateDeformationModelEvents @0x825DB0E0, DeformableObject::Prepare's spec
  rem     resolve + mGlobalEntityId + mpAttachedVehicle binds (were pinned-null/dropped).
  rem   STILL TO WRITE (the next wave's list, in dependency order):
  rem     DeformationSensor default ctor (PS3 ClearVariables @0x6B5F28 is the shape),
  rem     DeformableObject::UpdateIK @0x82608858 (61; PS3 0x6D374C has the names),
  rem     SetLastLinearVelocity/SetEntitySphereSize/GetNumSensors (tiny),
  rem     TagPoint accessors x4 + TagPointSpec::IsSkinned (tiny, header-inline on console),
  rem     GetInitialCompressionScalesAndLimits (PS3 0x6C90C0, 89),
  rem     ResetJointVelocities (PS3 0x6F8AE8, 330),
  rem     RemovePhysicalPartsAndJoints @0x82625250 (155, decoded in walls_log) + the
  rem       PhysicalBodyPartPool::RemovePart @0x8260CA30 (54) + PhysicalBodyPart::RemoveFromScene
  rem       @0x825E7818 (43) slice pair,
  rem     ?????? ResetSensors @0x82623D60 (718; PS3 0x7446FC) -- THE WHALE: seeds the 20 sensors +
  rem       spheres from StreamedDeformationSpec::maDeformationSensorSpecs; without it a
  rem       registered car is a HOLLOW SHELL (no spheres -> no contact tests -> walls stay
  rem       immaterial even with the table live),
  rem     UpdateSkinningOffsets' TagPoint closure, then UN-PIN ResetDeformation's tag/driven/IK
  rem       rebuild loops (the spec accessors EXIST now -- BrnStreamedDeformationSpec.h is
  rem       complete and shipped-spec-verified; the _Lifecycle "not exposed" FLAGs were stale).
  rem   DEFERRABLE with a kept gate: OutputData's closure (OutputSensorState @0x82605618 is an
  rem     X360 EXPORT HOLE, PS3 0x6F3E10; UpdateAndOutputJointStates @0x82609AE8 183;
  rem     OutputWheelData @0x82608E28 276; DetachedPartManager::OutputEvents -> pool OutputEvents
  rem     @0x8260DBE8 237) -- split OutputData to an unmounted _Output slice at mount time and
  rem     keep its conductor gate; likewise the _Update.cpp UpdateLocators leg (UpdateLocator
  rem     @0x825E0EC8 204; PS3 0x7A8498) via an IKSkinning slice.
  rem   ?????? AND THE MOUNT'S RUNTIME PRECONDITIONS, measured on the live path: degrade the
  rem     DoRaceCarWorldContactGeneration / DoCarCarContactGeneration TRAP STUBS
  rem     (BrnVehicleManagerContactGeneration.cpp) to log-once gates FIRST -- the moment the model
  rem     table != -1 they are REACHED PER FRAME and would assert-storm; and note
  rem     BrnPhysicsModule.cpp Prepare stage 4's fourteen deferred deformation-IO clears become
  rem     live the same moment.
  rem  ??? BrnVehicleManager.cpp IS STILL NOT MOUNTED. 2026-08-03 (task #110) RE-MEASURED the whole
  rem  closure from a fresh link rather than trusting the previous wave's note, and the numbers here
  rem  REPLACE the "15 unresolved externals" recorded before. Three separate builds:
  rem
  rem    M1  group A only (BrnStuntOffencesManager.cpp + BrnPhysicalTrafficManager.cpp, no
  rem        BrnVehicleManager.cpp)                                   -> 10 unresolved.
  rem        ??? the previous note's "one mount line each" is FALSE: both group-A TUs drag their own
  rem        closure. RETIRED 2026-08-20: the seven apparent RaceCarPhysics stunt accessors were
  rem        project-only inventions, not DecFIGS declarations. The Breaker inlined loads now use
  rem        their exact inherited/member APIs, and BrnStuntOffencesManager.cpp is mounted above.
  rem        BrnPhysicalTrafficManager wants TrafficPhysics::Construct, ArticulatedJointPool::
  rem        Construct and ArticulatedJointPool::SendCreateRemoveJointEvents.
  rem
  rem    M2  group A + BrnVehicleManager.cpp + BrnVehicleManagerPlayerStats.cpp +
  rem        BrnArticulatedJointPool.cpp                              -> 23 unresolved, of which
  rem        BrnVehicleManager.obj owns exactly TWELVE:
  rem          VehicleManagerOutputInterface::GetEventQueue / AddRaceCarCrashEvent /
  rem          AddRemappedEntityIdEvent / FlagTakedownScoredForDriver ; RaceCarPhysics::SetCrashing ;
  rem          and SEVEN of VehicleManager's own -- ApplySlam, ApplyShunt, GenerateContactSituation,
  rem          CheckForGrindingAndRubbing, CheckForVerticalTakedownSituation,
  rem          ShouldRaceCarCrashOnCarImpact, IsPointBetweenTwoParallelPlanes.
  rem        ??? HasRaceCarHadRecentImpact is NOT among them: it is ALREADY BODIED, at
  rem        BrnVehicleManagerPlayerStats.cpp:207 (X360 @0x825B4EB8). The old note listed it as
  rem        "bodied nowhere"; it is an unmounted TU, not a missing body. That is the whole of the
  rem        old note's seven-vs-eight arithmetic contradiction.
  rem        ??? ADDRESSES for the twelve, so the next wave does not re-hunt them:
  rem          ApplySlam 0x8261A738 (101 instr) ; ApplyShunt 0x8261A5B0 (98) ;
  rem          GenerateContactSituation 0x825B5520 (91) ; CheckForGrindingAndRubbing 0x825B5450 (52) ;
  rem          ShouldRaceCarCrashOnCarImpact 0x825C6FF8 (42) ;
  rem          IsPointBetweenTwoParallelPlanes 0x825C5660 (30) ;
  rem          RaceCarPhysics::SetCrashing 0x825B8A70 (31) ;
  rem          VehicleManagerOutputInterface::AddRaceCarCrashEvent 0x825E6F60 (132).
  rem        ?????? CheckForVerticalTakedownSituation is @0x825C56D8 and is ANOTHER export hole: it is
  rem        absent from progress/identity.json AND has no 0x825C56D8.json, but the caller
  rem        CheckForVerticalTakedown @0x8263D728 names it in its own `xrefs_from` and calls it
  rem        twice (0x8263D7AC / 0x8263D85C). Absent-from-JSON is not absent-from-image.
  rem        ??? AND THREE OF THE TWELVE ARE NOT X360 FUNCTIONS AT ALL. GetEventQueue,
  rem        AddRemappedEntityIdEvent and FlagTakedownScoredForDriver appear nowhere in
  rem        identity.json: they are accessor names minted over raw sink offsets, and TWO of them
  rem        were hung on the wrong class (0x65F0 / 0x6C00 are VehicleOutputInterface's, ~24 KB
  rem        outside VehicleManagerOutputInterface). Proof and the asm lines are recorded at their
  rem        declarations in SharedIO/BrnVehicleOutputInterface.h. Fix the class before bodying.
  rem        ??? The seven RaceCarPhysics stunt accessors that block group A are likewise NOT free:
  rem        FOUR of their offsets contradict the committed member map in VehiclePhysics.h -- see
  rem        the ?????? block at VehiclePhysics/RaceCarPhysics.h:262.
  rem
  rem    M3  as shipped (the two joint TUs above only)               -> 0 unresolved, exe unchanged.
  rem
  rem  ?????? THE REAL BLOCKER IS NOT IN BrnVehicleManager.cpp AT ALL. VehicleManager::Construct
  rem  @0x8263B7C8 calls PhysicalTrafficManager::Construct, which calls TrafficPhysics::Construct
  rem  @0x8262E980 -- and that address is an .ida-exports HOLE (the X360 JSON set jumps
  rem  0x8262E848 -> 0x8262EBE8; the caller's asm still names the symbol, so it exists, it is just
  rem  not exported). ??? IT IS RECOVERABLE: the PS3 DecFIGS export set HAS it, at
  rem  .ida-exports\DecFIGS_Burnout_Internal_PS3.ELF\0x6EB440.json
  rem  (_ZN10BrnPhysics7Vehicle14TrafficPhysics9ConstructEv, 47 instructions).
  rem  ?????? But landing it is gated on the OPEN `TrafficPhysics` ODR fork, and NOT merely for tidiness:
  rem  BrnPhysicalTrafficManager.h slices TrafficPhysics as `struct { u8[5168]; }` and strides
  rem  maFullTrafficPhysics[20] by that console size, while the real
  rem  `class TrafficPhysics : public VehiclePhysics` is LARGER on the host (pointer widening --
  rem  the same +176 drift this header already tabulates for its own members). The mangled name
  rem  ?Construct@TrafficPhysics@Vehicle@BrnPhysics@@QEAAXXZ encodes neither the class-key nor the
  rem  bases, so a body written against the real class WOULD link against the sliced call site --
  rem  silently, with the array stride 5168 and the constructor writing past it. Do not do that.
  rem  De-fork first (that is finding (2) in BrnPhysicalTrafficManager.h), then body Construct.
  rem  ??? The standing rule again: a mount's closure is the static reference graph of the WHOLE TU,
  rem  not of the one function you care about. Mounting this file is still its own wave -- and the
  rem  wave AHEAD of it is the TrafficPhysics de-fork, not the takedown chain.
  rem  ???????????? 2026-08-03 (VehiclePhysics own-block wave) -- VehiclePhysics_layout_check.cpp is NEW and
  rem  must stay mounted, one level DOWN from the file above. BrnSimpleVehiclePhysics.h and
  rem  VehiclePhysics.h now carry those two classes' own-member blocks at their X360 seats, and the
  rem  claim that makes them derivations is that the DWARF's ORDER and the asm's OFFSETS close with
  rem  zero slack at BOTH ends: 0x720 (== VehiclePhysics::mpAttribs, a different function) and
  rem  0x13F0 (== RaceCarPhysics::mPropCollisionImpulseSum, a different wave). This gate is console
  rem  ARITHMETIC, not host offsetof -- the block owns two pointers and several of its embedded
  rem  sub-types are reconstructions, so an absolute offsetof gate here would be false or vacuous.
  rem  It also asserts the host sizeof of every pointer-free sub-struct the arithmetic depends on.
  rem  Compile-only: one never-called static member, zero link closure.
  echo "%SRC%\GameSource\Physics\VehicleManager\VehiclePhysics\VehiclePhysics_layout_check.cpp"
  rem ---- end vehicle-dynamics core ---------------------------------------------------------
  rem ---- CONTACT-SPY DATA + PROP-MANAGER PERF MONITORS (physics wave 4, 2026-08-02) --------
  rem  Two of the sub-constructors BrnPhysics::PhysicsModule::Construct @0x825AE308 calls:
  rem      BrnPhysics::ContactSpy::ContactSpyData::Construct            @0x825AE010
  rem      BrnPhysics::Props::PropManager::ConstructPreScenePerfMonitors @0x825BAC70
  rem      BrnPhysics::Props::PropManager::ConstructContactGenerationPerfMonitors @0x825BAC60
  rem  ContactSpyData::Construct needs its ten owned queues' EventQueue<T,N>::Construct
  rem  instantiations, so those explicit-instantiation TUs are mounted with it (they were all
  rem  already written; none of them was in the build).
  rem
  rem  ???????????? SAME CAVEAT AS THE BLOCK ABOVE: nothing calls any of this yet, so /OPT:REF strips it
  rem  and it puts ZERO BYTES in the exe. It is mounted so the closure is continuously enforced.
  rem ---- root-cause wave (2026-08-10) mount closure. All three bodies were already ----
  rem ---- reconstructed and simply not in the exe:                                  ----
  rem ----  * ContactSpyInterface::Construct  -- PhysicsModuleIO::OutputBuffer::Construct ----
  rem ----  * PropInputInterface Append/Construct/Clear -- both prop->physics bridges ----
  rem ----  * PropEntityIO::OutputBuffer_PreScene accessors -- the PreScene bridge     ----
  echo "%SRC%\GameSource\Physics\ContactSpies\BrnContactSpyInterface.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\BrnPropInputInterface.cpp"
  rem  ---- wave Q6 / seat (2026-08-19): the PROP OUTPUT seat -- Props::PropOutputInterface::Construct
  rem  @0x825A9658 + AppendUpdatedProps @0x826153A0, real but never in the build; PhysicsModuleIO::
  rem  OutputBuffer::Construct now calls it and the +71792 seat is the real type: the unblock for
  rem  PropManager::OutputUpdatedProps, the sole producer of smashed-prop poses back to the world.
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\BrnPropOutputInterface.cpp"
  rem ----  * PropEntityID::AssertIsProp -- the owner tripwire every prop enqueue runs ----
  echo "%SRC%\SharedClasses\Physics\Props\BrnPropEntityID.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropEntityModuleIO_OutputBuffer_PreScene.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\BrnContactSpyData.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\EventQueue_RaceCarContact_300.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\EventQueue_TrafficContact_400.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\EventQueue_PhysicalCarPartContact_150.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\EventQueue_HingedPartContact_50.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\EventQueue_PropContact_100.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\EventQueue_DiscardedContact_20.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\EventQueue_ContactSpyRunData_8.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\EventQueue_ContactSpyRunData_50.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\EventQueue_ContactSpyRunData_64.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\EventQueue_ContactSpyRunData_100.cpp"
  echo "%SRC%\GameSource\Physics\ContactSpies\BaseEventQueue_RaceCarContact_AddEventSafe.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\BrnPropManager.cpp"
  rem  2026-08-18 wave Q4: the physics PropManager is MOUNTED (mount option C, smash-first): parts go
  rem  physical, contacts validated (SetupAndValidatePropContact REAL, its trap stub deleted); wQ_03 and
  rem  wQ2_02 are MOUNTED since wave Q6 round 2 (below, after wQ2_03); Prepare/ProcessInputsPreScene/
  rem  ReadUpdatedBodies/OutputUpdatedProps/Begin/End/UpdateTriangleCache gates all retired.
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ4_01.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ4_02.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ4_03.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ4_03_embed_check.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ4_04.cpp"
  rem  ---- wave Q5 round-3 integration: PropManager::ProcessInputs_Prepare @0x825E3400, the prop-physics
  rem  data handle pickup PhysicsModule::PropPrepareTypes @0x825A14A8 calls (its gate retired).
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ5_01.cpp"
  rem  ---- wave Q6 / rmall: PropManager::RemoveAllPropsAndParts @0x8260F010 (331), the world-unload
  rem  teardown; export hole closed with headless idat; its conductor gate retired in this change.
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ6_01.cpp"
  rem  ---- wave Q6 round 2 / lean: the JOINTED-PROP contact response -- HandleContactWithLeanProp
  rem  @0x8260FB60 (854) + HandleContactWithTiltProp @0x826108B8 (720); their conductor gates retire
  rem  in this change. Unblocked by ExternalPhysicsBody::GetLinearMomentum, Wheel::GetRoadLongSpeed
  rem  and six rw::math::vpu helpers; ExternallySimulatedBody::Translate landed at integration.
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ6_02.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\BrnPropManager_PropInstanceQueries.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\BrnPropManager_RoutePropVsRaceCarContactToDummyCar.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\PropPhysics\BrnPropInstance.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\PropPhysics\BrnPropPartInstance.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ_01.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ_02.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ2_01.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ2_03.cpp"
  rem  ---- wave Q6 round 2 / pstream: the PROP-vs-WORLD contact generation pair -- wQ2_02 (Begin/End
  rem  PropWorldContactGeneration @0x82628CB0/@0x82628E18 + GetTriangleCacheSlotAndRadius) and wQ_03
  rem  (UpdateTriangleCache @0x826119A0). MOUNT AS A PAIR (wQ_03 alone is an LNK2019). Their three
  rem  conductor gates retire in this change; the primitive-list-vs-triangle-list STREAM job family
  rem  (CgsCollisionGenerator.cpp) + AddPrimitive(Volume*) landed this round.
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ2_02.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ_03.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ2_04.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ2_05.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ2_06.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ2_07.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ2_08.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\PropManager_wQ2_09.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsEntityId.cpp"
  rem ---- end contact-spy / prop perf-monitor block -----------------------------------------
  rem ---- PROP MANAGER CONSTRUCT + ITS DEBUG COMPONENT (physics wave 5, 2026-08-02) ---------
  rem  BrnPhysics::Props::PropManager::Construct @0x82627390 is now real, which needed the whole
  rem  PropDebugComponent TU: the component is embedded BY VALUE at PropManager+0x00, so any TU
  rem  that instantiates a PropManager needs its vtable, i.e. bodies for RenderHUD / GetName /
  rem  OnActivate / OnRegister, and RenderHUD needs RenderStats @0x826131E8 and OnActivate needs
  rem  the seven OnChange* statics @0x825BAEF0..0x825BB040.
  rem  BrnPropManager.cpp (mounted just above) now also DEFINES the twelve prop tuning globals
  rem  (KVF_* / KF_PROP_*) that OnActivate registers -- the DWARF homes them in that .cpp.
  rem  The two EventQueue<UpdatePropEvent,N> explicit-instantiation TUs Construct calls had never
  rem  been in the build at all; they are mounted here.
  rem
  rem  ???????????? SAME CAVEAT AS THE TWO BLOCKS ABOVE: PhysicsModule::Construct is still a stub (it
  rem  additionally needs VehicleManager::Construct and PhysicsSimulationModule::Construct, both
  rem  of which have no body and no type), so NOTHING calls PropManager::Construct yet and
  rem  /OPT:REF strips all of this. ZERO BYTES IN THE EXE. Mounted so the closure is enforced.
  echo "%SRC%\GameSource\Physics\PropManager\BrnPropDebugComponent.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\EventQueue_UpdatePropEvent_200.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\EventQueue_UpdatePropEvent_15.cpp"
  rem ---- end prop-manager construct block ---------------------------------------------------

  rem ==== PROP SPAWN WAVE (2026-08-12) =======================================================
  rem  WHY THIS BLOCK EXISTS: no prop had ever spawned in the PC build. Props are SCENE
  rem  ENTITIES emitted by BrnWorld::PropEntityModule, and that module was a shell -- every
  rem  entry point was a one-shot inert gate in WorldLinkStubs.cpp, and BrnPropEntityModule.cpp
  rem  did not exist at all. Worse, a large amount of REAL prop code (PropZoneManager 821
  rem  lines, PropCellManager, PropEntityInstance) was already committed but had never been
  rem  added to this file, so it was dead source rather than link stubs -- `Burnout_PC.map`
  rem  carried ZERO PropZoneManager / PropCellManager / PropEntityInstance symbols. The world
  rem  octree took 10,752 entities last run and not one of them was a prop.
  rem
  rem  The data side was never the problem and is untouched: 396 TRK_UNIT<n>_GR.BNDL each carry
  rem  one PropGraphicsList (0x10010) + one PropInstanceData (0x10011), 24,047 prop instances
  rem  total, correctly transcoded to platform 4 / x64, all 11,616 Model imports resolving, and
  rem  demonstrably loaded + fixed-up at runtime. It was sitting in pool 3 with no reader.
  rem
  rem  The one real data defect WAS PROPS\PROPPHYSICS.BUNDLE -- still a raw big-endian X360
  rem  platform-2 file with no transcoder and no registered handler. PropZoneManager::LoadZone
  rem  takes a `const PropPhysicsDataHeader*`, so that was a CO-REQUISITE of the code work, not
  rem  a follow-up. It now has a real transcoder + manifest rule and a regenerated platform-4
  rem  file, and its resource type (0x1000F) is registered in CgsResourceTypeRegistration.cpp.
  rem
  rem  ---- the prop type table + its resource type (0x1000F) ----
  echo "%SRC%\SharedClasses\Physics\Props\BrnPropPhysicsListResourceType.cpp"
  echo "%SRC%\SharedClasses\Physics\Props\BrnPropPhysicsDataHeader.cpp"
  echo "%SRC%\SharedClasses\Physics\Props\BrnPhysicsPropTypeData.cpp"
  rem  ---- the instance/cell/zone machinery: real bodies that were never mounted ----
  rem  BrnPropZoneManager.cpp could not have linked before this wave even if it had been
  rem  mounted: it calls PropCellManager::Construct, which was declared and defined nowhere.
  rem  `cl /c` cannot see unresolved externals, which is exactly why that went unnoticed.
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropEntityInstance.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropCellManager.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropCellManager_wQ4.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropZoneManager.cpp"
  rem  ---- the module itself: lifecycle + streaming (PreScene/render land with their TUs) ----
  rem  PropEntityModule::Construct was THE earliest break in the whole chain: it is the only
  rem  writer of mauStartIndexOfZone[0..499] = KU_UNLOADED_ZONE (65535). While it was an empty
  rem  stub the zero-initialised module made IsZoneLoaded() return TRUE FOR EVERY ZONE, so no
  rem  zone could ever load no matter what else was fixed.
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropEntityModule.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropEntityModule_Streaming.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropEntityModule_PreScene.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropEntityModule_Render.cpp"
  rem  2026-08-18 breakable-props wave Q: THE BREAK PIPELINE IS MOUNTED -- ProcessContacts,
  rem  ProcessPotentialContact*, BreakPropIntoParts/ChangePropState, ProcessBrokenProps,
  rem  BrokenPropEvent, plus PrePhysics/PostPhysics/PostSceneUpdate, the replay set, and the
  rem  IO buffers those legs read. The WorldLinkStubs gates for PrePhysicsUpdate/PostSceneUpdate/
  rem  PostPhysicsUpdate/InputBuffer_PostPhysics::Construct/InputBuffer_PrePhysics::Construct
  rem  are retired in the same change.
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\PropEntityModule_wQ_01.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\PropEntityModule_wQ_02.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\PropEntityModule_wQ_03.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\PropEntityModule_wQ_04.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\PropEntityModule_wQ_05.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\PropEntityModule_wQ_06.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\PropEntityModule_wQ_07.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\PropEntityModule_wQ2_01.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\PropEntityModule_wQ2_02.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\PropEntityModule_wQ2_03.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\PropEntityModule_wQ3_01.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropEntityModuleIO_InputBuffer_PostPhysics.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropEntityModuleIO_InputBuffer_PrePhysics.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropEntityModuleIO_InputBuffer_PostScene.cpp"
  echo "%SRC%\GameSource\Replays\Serialisers\BrnReplayPropSerialiserFrame_wQ2_owner.cpp"
  echo "%SRC%\GameSource\Replays\BrnReplayRequestInterface.cpp"
  rem  BrnReplayPropSerialiserFrame_wQ2_keyframe.cpp is NOT mounted: KeyFrameRead needs the per-T
  rem  BrnReplayArray Read instantiations the u32-only generic cannot provide yet; its gate stays.
  rem  ---- the replay serialiser LoadProp threads through the whole load path ----
  echo "%SRC%\GameSource\Replays\Serialisers\BrnReplayPropEntitySerialiser.cpp"
  echo "%SRC%\GameSource\Replays\Serialisers\BrnReplayPropSerialiserFrame.cpp"
  echo "%SRC%\GameSource\Replays\Serialisers\BrnReplayPropSerialiserFrame_operator_assign.cpp"
  echo "%SRC%\GameSource\Replays\Array_PropLoadedZoneRecord_9_operator_index.cpp"
  rem  ---- LINK CLOSURE: TUs that already held real bodies but had never been mounted -------
  rem  Found by running the real link (cl /c cannot see unresolved externals, so the compile
  rem  gate was green with all of these missing). Each supplies symbols the block above calls:
  rem    BrnPropVolumeID / BrnPropVolumeInstanceID  -- the volume-id setters LoadProp and the
  rem       cell manager use to key props into the scene manager
  rem    BrnPhysicsPropZoneData  -- PropZoneData::GetCellId / GetRespawnTypeForProp, read by
  rem       LoadProp for every single prop instance
  rem    BrnPropEntityDebugComponent  -- embedded BY VALUE in PropEntityModule, so its vtable
  rem       (GetName / OnActivate / RenderHUD / RenderWorld) is required the moment the module
  rem       is constructed, whether or not the debug menu is ever opened
  rem    BrnPropToTrafficInterface  -- RequestTrafficLightRestore, from the traffic-light
  rem       restore path in PropZoneManager
  rem    BrnPropEntityModuleIO_OutputBuffer_PostPhysics  -- GetSceneInputInterface
  rem    FixableVolume  -- FixUp/FixDown on the prop collision volumes
  rem    BrnGameDataRequestInterface_1024  -- the explicit instantiation carrying
  rem       AcquireResource / GetPropInstances / LoadPropPhysics for the prop request queue
  echo "%SRC%\SharedClasses\Physics\Props\BrnPropVolumeID.cpp"
  echo "%SRC%\SharedClasses\Physics\Props\BrnPropVolumeInstanceID.cpp"
  echo "%SRC%\SharedClasses\Physics\Props\BrnPhysicsPropZoneData.cpp"
  rem  NOT MOUNTED -- BrnPropEntityDebugComponent.cpp. Measured 2026-08-12: mounting it
  rem  RAISED the unresolved count, because its Render{HUD,World} bodies drag in the whole
  rem  CgsDev debug-render stack (Debug3DImmediateRender::DrawBox/DrawSphere/DrawText/...,
  rem  Debug2DImmediateRender::DrawCircle, rw::RGBA's ctor, Volume::GetRelativeTransform),
  rem  none of which is reconstructed. The component is embedded BY VALUE at PropEntityModule
  rem  +0xCD900 so its VTABLE is still required; per the precedent set by the 2026-08-11
  rem  baseline wave, the four out-of-line virtuals are served as gates in WorldLinkStubs.cpp
  rem  (real GetName, inert OnActivate/RenderHUD/RenderWorld) instead. Mount the real TU when
  rem  the debug-render stack lands -- it is dev-menu-only and cannot affect prop spawning.
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\SharedIO\BrnPropToTrafficInterface.cpp"
  rem  wave Q6 / bridges: TrafficToRaceCarInterface_PreScene::Construct (the traffic OutputBuffer_PreScene
  rem  seat is the committed type now, not a 544-byte reserved fork).
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\SharedIO\BrnTrafficToRaceCarInterface.cpp"
  rem  BrnTrafficConstants.cpp: MakeTrafficEntityId @0x827048C0 (real, never mounted; AddPotentialStompee calls it).
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficConstants.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropEntityModuleIO_OutputBuffer_PostPhysics.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\FixableVolume.cpp"
  echo "%SRC%\GameSource\Resource\SharedIO\BrnGameDataRequestInterface_1024.cpp"
  rem  ---- the two PreScene bridges that FEED the prop module ------------------------------
  rem  Without these the whole subsystem is inert no matter how much of it is reconstructed:
  rem  BridgeWorldModuleToPropModule_PreScene is what copies the PropInstancesNeededForZone /
  rem  PropGraphicsLoaded / PropGraphicsUnloaded queues (and the player zone number) into the
  rem  module's InputBuffer_PreScene, and BridgeRaceCarModuleToPropModule_PreScene publishes
  rem  the player position/index/flags plus the 8-slot race-car velocity array. While both were
  rem  gates every queue read length 0 and miPlayerZoneNumber read 0, so the streaming machine
  rem  had nothing to ask for. Their DWARF home (WorldBridgeEntityModulesToEntityModules.cpp)
  rem  is still unmounted -- 3 of its other bridges have declaration-only IO accessors -- so
  rem  they are split out per the WorldBridgeRaceCarToWorldModule.cpp precedent.
  rem  BridgePropToOutput_PreScene went into the already-mounted WorldBridgeEntityModulesToOutput.cpp.
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeWorldModuleToPropModule.cpp"
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeRaceCarToPropModule.cpp"
  rem ==== end prop spawn wave ================================================================
  echo "%SRC%\GameSource\Resource\SharedIO\BrnAssetIds.cpp"
  echo "%SRC%\GameSource\Resource\SharedIO\BrnGameDataRequestQueue.cpp"
  echo "%SRC%\GameSource\World\AI\Route\BrnRouteMapModule.cpp"
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeEntityModulesToScene.cpp"
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeSceneToEntityModules.cpp"
  rem  ?????? 2026-08-11 (create-drain wave, triangle-cache wiring): the two bridges that carry the
  rem  scene's TriangleCacheInterface to physics (@0x827A8E88) and to the world output (@0x827A5700)
  rem  -- crash-measured: without them AddRaceCarTractionLineTests dereferences a NULL
  rem  mpTriangleCacheManager on the first live car. Their WorldLinkStubs gates are deleted in the
  rem  same wave (LNK2005 tripwire otherwise).
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeSceneToPhysics.cpp"
  rem  ---- wave Q5 round 3 / F2: the PHYSICS to SCENE direction, BridgePhysicsSceneUpdateToScene
  rem  @0x827ABA40 -- PhysicsModuleIO::OutputBuffer now seats the real InSceneUpdateInterface.
  echo "%SRC%\GameSource\World\Bridges\WorldBridgePhysicsToScene.cpp"
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeSceneToOutput.cpp"
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeToEntityModules.cpp"
  echo "%SRC%\GameSource\World\BrnBaseStreamer.cpp"
  echo "%SRC%\GameSource\World\BrnWorldModuleIO_DispatchInputBuffer.cpp"
  echo "%SRC%\GameSource\World\BrnWorldModuleIO_DispatchOutputBuffer.cpp"
  echo "%SRC%\GameSource\World\BrnWorldModuleIO_UpdateOutputBuffer.cpp"
  echo "%SRC%\GameSource\World\CrashModule\BrnRaceCarCrash.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropEntityModuleIO_InputBuffer_Dispatch.cpp"
  rem ---- IO-buffer construction wave (2026-08-15): CreateIOBuffer<T> now runs T::Construct like the
  rem ---- console template, so BrnTrafficIO::InputBuffer_Dispatch::Construct @0x8275CF40 (in this
  rem ---- already-reconstructed, never-mounted TU) became a hard reference from WorldModule.obj.
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModuleIO_InputBuffer_Dispatch.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropEntityModuleIO_OutputBuffer_Prepare.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnRaceCarEntityModuleIO.cpp"
  rem ---- PRE-PHYSICS BRIDGE wave (2026-08-10). WorldModule::BridgeEntityModulesToPhysicsModule_ ----
  rem ---- PrePhysics @0x827AAEC0 is real now; it is the ONLY carrier of a staged                ----
  rem ---- CreateRaceCarEvent into the physics input buffer. Its closure needs these TUs, every  ----
  rem ---- one of which was already reconstructed and simply never on the build list:            ----
  rem ----  * BrnTrafficEntityModuleIO.cpp  -- OutputBuffer_PrePhysics Construct + 6 accessors,  ----
  rem ----    and its three interfaces are REAL types now (they were `unsigned char[1]`).        ----
  rem ----  * BrnPropEntityModuleIO_OutputBuffer_PrePhysics.cpp -- GetPropInputInterface() const ----
  rem ----  * VariableEventQueue_5040_16.cpp -- the driver-controls queue's out-of-line methods  ----
  rem ----  * the six event-queue Append instantiations the bridge's inlined merges reach.       ----
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModuleIO.cpp"
  rem ----  * BrnTrafficNetworkInputInterface.cpp -- the three accessors mounting the IO TU  ----
  rem ----    turned into LNK2019s (Get/Set/HasDiverged, bodied in the same commit).         ----
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\SharedIO\BrnTrafficNetworkInputInterface.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropEntityModuleIO_OutputBuffer_PrePhysics.cpp"
  echo "%SRC%\GameShared\GameClasses\Module\VariableEventQueue_5040_16.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_CreateAirRamEvent_AddEventSafeAppend.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_CreateSpinEvent_Append.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\BaseEventQueue_AddPhysicalPropEvent_Append.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\BaseEventQueue_AddPhysicalPartEvent_Append.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\BaseEventQueue_RemovePhysicalPropEvent_AddEventAppend.cpp"
  echo "%SRC%\GameSource\Physics\PropManager\SharedIO\BaseEventQueue_RemovePhysicalPartEvent_AddEventAppend.cpp"
  rem ---- end pre-physics bridge block ---------------------------------------------------------
  rem ---- create-path wave 2026-08-11: the FOUR event-queue instantiations
  rem ---- VehicleManager::ProcessCreateEvents @0x82616770 reaches. NOTHING CALLS THEM YET -- the
  rem ---- drain is still a named gate -- and they are mounted anyway, per the standing
  rem ---- [[shadowing-redeclarations]] mitigation: /OPT:REF strips every byte, but the LINK
  rem ---- closure over the create body's queue API is enforced NOW rather than discovered by the
  rem ---- wave that writes it. GetEvent is the truncated export "BrnPhysics::Vehic" @0x825BB7F0
  rem ---- (console element stride 0xA0 == sizeof(CreateRaceCarEvent)).
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_CreateRaceCarEvent_GetEvent.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BaseEventQueue_CreateVehicleResult_AppendAddEvent.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\BaseEventQueue_AddDeformationModelEvent_AddEvent.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\BaseEventQueue_InAddRigidBody.cpp"
  rem ---- reset-player-car wave (2026-08-01): the game-action-0 consumer chain.        ----
  rem ---- Each of these was already committed and NEVER LINKED BY ANYTHING.            ----
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnRaceCarEntityModuleIO_PreSceneAccessors.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnRaceCarEntityModule_ScoringMapping.cpp"
  echo "%SRC%\GameSource\Math\BrnMathUtils.cpp"
  echo "%SRC%\GameShared\GameClasses\System\AttribSys\CgsAttribSysCollectionKey.cpp"
  echo "%SRC%\GameSource\GameState\BrnGameActions.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\SharedIO\BrnRCEntityActiveRaceCarOutputInterface.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\SharedIO\BrnRCEntityGlobalRaceCarOutputInterface.cpp"
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModuleIO_InputBuffer_Getters.cpp"
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\SharedIO\BrnTrafficNetworkOutputInterface.cpp"
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\SharedIO\BrnTrafficSoundInterfaces.cpp"
  rem  2026-08-19 (wave Q7, cluster traffic): THE TRAFFIC-LIGHT KNOCKDOWN CONSUMER. wQ7_01 = PrePhysicsUpdate
  rem  @0x8274C690 (documented PARTIAL: PerfMon + lock brackets + SetPlayingShowtime + the 3-way state machine +
  rem  BitArray<601> + HandlePropModuleRequests REAL; 8 other legs = named one-shot gates inside the body) and
  rem  HandlePropModuleRequests @0x82720A90 (118, REAL: drains the knock-down + restore rings into
  rem  TrafficLightManager::TrafficLightGot{Smashed,Restored}). wQ7_02 = the BRING-UP: Prepare @0x8274A578 PARTIAL
  rem  (stages 0/2/5 real, 1/3/4 gates) + LoadData @0x82746A88 PARTIAL (resource stages 0/1 SEAT mpData via the
  rem  LoadTrafficLanes GameData round trip; 2..11 one gate) + 3 named DELETE-WHEN bring-up latches (mReceiverQueue
  rem  Construct relocated from the gated TrafficEntityModule::Construct @0x82740220; meState latched RUNNING).
  rem  Both WorldLinkStubs gates (PrePhysicsUpdate, Prepare) retired in the same change -- BrnUpdateSet is u16 so the
  rem  gate signature is token-identical to the real one (LNK2005 cl cannot see). BrnTrafficLightManager.cpp carries
  rem  GetLightState / TrafficLightGotSmashed @0x827519A0 / TrafficLightGotRestored @0x82751A40 (export hole, idat);
  rem  it needs TrafficLightCollection::GetInstanceIndexForInstanceID from SharedClasses\Traffic\Junctions (below).
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wQ7_01.cpp"
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wQ7_02.cpp"
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficLightManager.cpp"
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficLightRuntimeState.cpp"
rem  2026-08-21 wave T1 parked traffic cars -- module half. C3 vehicle+param runtime
rem  incl. the 13 container instantiation TUs; C4 spawn legs in _wT1_01 which retires the
rem  WorldLinkStubs Construct / EnterTearingDownState / PostPhysicsUpdate gates and the
rem  wQ7_02 meState bring-up latch; C5 car streamer -- SetAssetList @0x82753A38 is the
rem  function whose absence the boot log named. BrnTrafficParam.cpp mounts because
rem  BrnTrafficVehicle.cpp needs Param::GetHistoryEntry. KF_VEHICLE_UPDATE_MATRIX_OLD_
rem  UP_FACTOR = splat 20.0f recovered from dyn-init thunk @0x82C67830 -- the "no writer
rem  anywhere" banner was the export-scan blind spot, wave-Q lesson.
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT1_01.cpp"
rem  R2 round: _wT1_02 = PreSceneUpdate @0x8274A968 (blocker B2, export hole, leak-shaped with
rem  ship-attested callee inventory; its WorldLinkStubs gate is retired in the same change).
rem  _wT1_03 = TrafficPhysicsInfo::Construct @0x82751E88 PARTIAL. _Render = the render trio:
rem  PreDispatchUpdate @0x8274D900, GenerateDispatchLists @0x8273B280 DWARF 10-arg,
rem  RenderTrafficCar @0x82728B08; both render gates retired with the bodies.
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT1_02.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT1_03.cpp"
rem  R3 closure item 1: _wT1_04 = UpdateStreaming @0x82748848 + AddVehiclesToTargetList
rem  @0x82722470 -- THE STREAMER PUMP that finally requests the VEH_T*_GR bundles.
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT1_04.cpp"
rem  R4: _wT1_05 = CreateNewVehicleEntities @0x8272FA30 + IsVehiclesParamAZombie -- the
rem  per-vehicle scene registration. _wT1_06 = UpdateTimers @0x82715858 + UpdateDecision/
rem  NonDecisionFrame @0x8274E508/@0x8274C1A8 -- the decision-frame steady-state loop
rem  whose only mbDecisionFrame writer is UpdateTimers. WorldBridgeRaceCarToTrafficModule
rem  = BridgeRaceCarModuleToTrafficModule_PreScene @0x827A50E0, THE activeHulls==0 fix:
rem  the sole producer priming the traffic input buffers with race-car state.
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT1_05.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT1_06.cpp"
rem  _wT1_07 -- SpawnShowtimeTraffic @0x82743038 (the showtime top-up UpdateDecisionFrame
rem  calls in _wT1_06) plus its two spacing helpers IsParamTooClose @0x82726470 and
rem  CountParamsOnSection @0x82723D10.
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT1_07.cpp"
rem  wave T2 driving traffic: generation (_wT2_01), param sim (_wT2_02/03), vehicle+scene
rem  wire (_wT2_04), fuzzy behaviours, and the UpdateVehiclesJob family (the ship moved the
rem  per-vehicle driving update into an EA::Jobs job: TrafficJobStub + UpdateVehiclesJob).
rem  _wT2_06 = THE CRASH SURFACE: UpdateParams_BuildListOfCrashingThings (the shared
rem  producer) plus its two consumers, TryAvoidCrashing (traffic SWERVES) and
rem  TryStartSympatheticCrashing (chain-reaction crashes). _wT2_02 calls all three.
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT2_01.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT2_02.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT2_03.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT2_04.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT2_05.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT2_06.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_KillDyingVehicleEntities.cpp"
rem  wave T3 physical traffic: _wT3_00 shared leaves, _wT3_01 world promotion path,
rem  _wT3_02 GenerateDriverInputs, _wT3_04 publish/readback + physical render arm.
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT3_00.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT3_01.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT3_02.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT3_04.cpp"
rem  wave T4 crash-into-traffic: _wT4_01 UpdateCollidableVehicles (collision-volume producer),
rem  _wT4_02 BuildPotentialCollisionList + HandleHalfPotentialContact (overlap-pair promoter).
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT4_01.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT4_02.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT5_01.cpp"
rem  wT6_01 -- NukeTrafficJams @0x827353E8, the traffic-jam relief valve. Marks every
rem  third param in a stalled run SetShouldBeRemoved; UpdateParams KillParam consumer
rem  in _wT2_02.cpp is already live, so this closes the valve end to end.
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT6_01.cpp"
rem  wT6_02 -- HandlePrepareForModeAction @0x827480D8, the per-event arming handler and
rem  the ONLY non-debug writer of mbPlayingShowtimeMode (+0x717DD).
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT6_02.cpp"
rem  wT6_03 -- HandleExternalRequests @0x8274B660, PARTIAL. Only its action-23 arm is
rem  real, but that arm is the ONLY caller of HandlePrepareForModeAction -- without this
rem  TU /OPT:REF discards the showtime gate entirely.
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_wT6_03.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficMiscRuntimeClasses.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficFuzzyLogicBehaviours.cpp"
echo "%SRC%\SharedClasses\Traffic\BrnTrafficFuzzyEnvelopeSet.cpp"
echo "%SRC%\GameSource\Jobs\Traffic\TrafficCommon.cpp"
echo "%SRC%\GameSource\Jobs\Traffic\BrnTrafficJob.cpp"
echo "%SRC%\GameSource\Jobs\Traffic\BrnUpdateVehiclesJob.cpp"
echo "%SRC%\GameSource\Jobs\Traffic\BrnUpdateVehiclesJob_MoveToTarget.cpp"
echo "%SRC%\GameSource\World\Bridges\WorldBridgeRaceCarToTrafficModule.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule_Render.cpp"
rem  BrnVehicleSoaData.cpp: real Construct body existed unmounted -- Reset calls it.
echo "%SRC%\GameSource\World\Traffic\BrnVehicleSoaData.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficCarStreamer.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModuleIO_InputBuffer_PostPhysics.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficVehicle.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficParam.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficStaticParam.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficHullRuntime.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficPatternGenerator.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficVehicleTypeRuntime_PickPaintColour.cpp"
rem  R3 closure item 3: VehicleTypeRuntime::Prepare @0x82761B10 -- the boot fix for the
rem  90 zero-extent CgsVolumeManager asserts (seats mBBoxHalfSize from the physics spec).
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficVehicleTypeRuntime_Prepare.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\Array_CollidableVehicleInfo4_16.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\Array_CrashingThingData_168.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\Array_FiredKillZoneInfo_8.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\Array_HullChangeInfo_400.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\Array_PhysicalVehicleInfo_33.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\Array_PurgatoryInfo_1.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\Array_PurgatoryInfo_199.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\Array_PurgatoryInfo_400.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\Array_TrafficCrashInfo_160.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\Array_VehicleRenderInfo_64.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\Array_char_16.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\Array_short_64.cpp"
echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\Array_short_9.cpp"
  echo "%SRC%\GameSource\World\EntityModules\TriggerEntityModule\BrnTriggerEntityModuleIO_QueueAccessors.cpp"
  rem ---- world-IO Construct family (2026-07-27): the trigger pre/post-scene +      ----
  rem ---- pre-physics buffer Constructs (X360 0x822EED48/0x822DA168/0x822DA180/      ----
  rem ---- 0x822DA198/0x822DA1B0) and the vehicle driver input interface Construct.   ----
  echo "%SRC%\GameSource\World\EntityModules\TriggerEntityModule\BrnTriggerEntityModuleIO.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BrnVehicleDriverInputInterface.cpp"
  echo "%SRC%\GameSource\World\EntityModules\WorldEntityModule\Bridges\WorldEntityBridgePVSToOutput.cpp"
  echo "%SRC%\GameSource\World\EntityModules\WorldEntityModule\BrnWorldEntityModuleIO_InputBuffer_GenerateDispatchLists.cpp"
  echo "%SRC%\GameSource\World\EntityModules\WorldEntityModule\BrnWorldEntityModuleIO_InputBuffer_PostPhysics.cpp"
  echo "%SRC%\GameSource\World\EntityModules\WorldEntityModule\BrnWorldEntityModuleIO_InputBuffer_PreScene.cpp"
  echo "%SRC%\GameSource\World\EntityModules\WorldEntityModule\BrnWorldEntityModuleIO_OutputBuffer_PostPhysics.cpp"
  echo "%SRC%\GameSource\World\EntityModules\WorldEntityModule\BrnWorldEntityModuleIO_OutputBuffer_PreScene.cpp"
  echo "%SRC%\GameSource\World\EntityModules\WorldEntityModule\BrnWorldEntityModuleIO_OutputBuffer_Prepare.cpp"
  echo "%SRC%\GameSource\World\EntityModules\WorldEntityModule\PVSModule\BrnPVSModule.cpp"
  rem ---- world-module mount (2026-07-26): WorldDebugComponent::GetName home TU     ----
  rem ---- (vtable-pulled by the mounted by-value fleet; tiny, no closure drag).     ----
  rem ---- BrnPVSDebugComponent.cpp / BrnTriggerEntityModuleDebugComponent.cpp were  ----
  rem ---- tried and REVERTED: they drag Debug2D/3DImmediateRender draw primitives + ----
  rem ---- rw::RGBA + partial PVS bodies (RenderPVS/RenderPvsCentrePosition          ----
  rem ---- unrecovered) -- stubbed at the vtable seam in WorldLinkStubs instead.     ----
  echo "%SRC%\GameSource\World\DebugComponents\BrnWorldDebugComponent.cpp"
  echo "%SRC%\GameSource\World\EntityModules\WorldEntityModule\PVSModule\BrnPVSModuleIO.cpp"
  rem ---- PVS wave (2026-07-27): the real BrnWorld::PVSModule::Update/Prepare pulls  ----
  rem ---- the zone point query, the GetZoneRequest velocity getter and the           ----
  rem ---- RequestInterface<512>::LoadPVS request builder.                            ----
  echo "%SRC%\GameShared\GameClasses\SceneManager\Zones\ZoneList_GetFirstZoneForPoint.cpp"
  rem (CgsFrustum: BrnShadowMap's ComputeOptimalViewVolume calls Get/SetPlaneByIndex)
  echo "%SRC%\GameShared\GameClasses\Geometric\Primitives\CgsFrustum.cpp"
  echo "%SRC%\GameSource\World\EntityModules\WorldEntityModule\PVSModule\SharedIO\BrnPVSModuleEvents.cpp"
  echo "%SRC%\GameSource\Resource\SharedIO\BrnGameDataRequestInterface_512.cpp"
  rem (textures/shaders wave 2026-07-28: BrnGameModule::GamePrepare's three one-time
  rem  LoadBundle requests go through RequestInterface<32768> -- X360 0x823CE558.)
  echo "%SRC%\GameSource\Resource\SharedIO\BrnGameDataRequestInterface_32768.cpp"
  rem (race-car global-resource wave 2026-07-31: RaceCarEntityModule::LoadGlobalResources
  rem  @0x82300730 posts LoadBundle/GetVehicleList/GetWheelList through RequestInterface<8192>.)
  echo "%SRC%\GameSource\Resource\SharedIO\BrnGameDataRequestInterface_8192.cpp"
  rem (TRIGGERS wave 2026-08-01: the GameStateModuleIO::OutputBuffer's +0x3414 request
  rem  interface IS RequestInterface<3072> -- TriggerQueryManager::Prepare @0x82398218 calls
  rem  LoadBundle/AcquireResource/LoadTrafficLanes on it, and GameStateModule::Prepare's list
  rem  stages call GetVehicleList/GetWheelList/GetFreeburnChallengeList. The instance TU
  rem  existed but was never mounted.)
  echo "%SRC%\GameSource\Resource\SharedIO\BrnGameDataRequestInterface_3072.cpp"
  echo "%SRC%\GameSource\World\EntityModules\WorldEntityModule\SharedIO\BrnWorldEntityRequestInterface.cpp"
  echo "%SRC%\vendor\renderware\collision\BitTable.cpp"
  rem  Self-contained (its own header only) -- a FREE mount. It owns the single Frustum
  rem  function the X360 defines, rw::collision::Frustum::IsBoxInFrustum @0x82BA7FA0, which is
  rem  the leaf BrnDirector::Camera::IsLookingAtTarget @0x822331F0 needs.
  echo "%SRC%\vendor\renderware\collision\Frustum.cpp"
  rem  ---- wave Q5 C1 (2026-08-18): the rw::collision NARROW PHASE (SAT + contact points + volume query) ----
  echo "%SRC%\vendor\renderware\collision\AABBox.cpp"
  echo "%SRC%\vendor\renderware\collision\AALineClipper.cpp"
  echo "%SRC%\vendor\renderware\collision\Aggregate.cpp"
  echo "%SRC%\vendor\renderware\collision\AggregateVolume.cpp"
  echo "%SRC%\vendor\renderware\collision\BoxVolume.cpp"
  echo "%SRC%\vendor\renderware\collision\CapsuleVolume.cpp"
  echo "%SRC%\vendor\renderware\collision\ClusteredMeshCluster.cpp"
  echo "%SRC%\vendor\renderware\collision\ClusteredMeshQuery.cpp"
  echo "%SRC%\vendor\renderware\collision\CylinderVolume.cpp"
  echo "%SRC%\vendor\renderware\collision\Feature.cpp"
  echo "%SRC%\vendor\renderware\collision\FeatureEdge.cpp"
  echo "%SRC%\vendor\renderware\collision\FeaturePrism.cpp"
  echo "%SRC%\vendor\renderware\collision\GPBox.cpp"
  echo "%SRC%\vendor\renderware\collision\GPCapsule.cpp"
  echo "%SRC%\vendor\renderware\collision\GPCylinder.cpp"
  echo "%SRC%\vendor\renderware\collision\GPSphere.cpp"
  echo "%SRC%\vendor\renderware\collision\GPTriangle.cpp"
  echo "%SRC%\vendor\renderware\collision\GPRegistration.cpp"
  echo "%SRC%\vendor\renderware\collision\KdTreeBBoxQuery.cpp"
  echo "%SRC%\vendor\renderware\collision\KdTreeLineQuery.cpp"
  echo "%SRC%\vendor\renderware\collision\LineSegIntersect.cpp"
  echo "%SRC%\vendor\renderware\collision\PrimitiveIntersect.cpp"
  echo "%SRC%\vendor\renderware\collision\SeparatingDirection.cpp"
  echo "%SRC%\vendor\renderware\collision\TriangleVolume.cpp"
  echo "%SRC%\vendor\renderware\collision\TriangleVolume_wN_01.cpp"
  echo "%SRC%\vendor\renderware\collision\VolRef.cpp"
  echo "%SRC%\vendor\renderware\collision\VolumeBBoxQuery.cpp"
  echo "%SRC%\vendor\renderware\collision\VolumeQuery.cpp"
  rem  ---- wave Q5 round 3 / vtbind: the six Volume descriptor RECORDS with their method slots
  rem  bound. REQUIRED: SDKs rwcollision volume.cpp has six undefined gVolumeHandler_* externals
  rem  that only this TU defines.
  echo "%SRC%\vendor\renderware\collision\VolumeVTables.cpp"
  echo "%SRC%\vendor\renderware\collision\CapsuleVolume_embed_check.cpp"
  echo "%SRC%\vendor\renderware\collision\Feature_embed_check.cpp"
  echo "%SRC%\vendor\renderware\collision\FeatureEdge_embed_check.cpp"
  echo "%SRC%\GameSource\World\WorldLinkStubs.cpp"
  echo "%SRC%\GameSource\Director\Camera\BrnCameraState.cpp"
  echo "%SRC%\GameSource\Director\Camera\BrnDepthOfField.cpp"
  echo "%SRC%\GameSource\Director\Camera\BrnCameraValidityAccount.cpp"
  echo "%SRC%\GameSource\Director\Camera\Utils\CameraUtils.cpp"
  rem ---- ORBIT-CAMERA WAVE (2026-08-01): the free-look stick the car-select camera reads ----
  rem  BehaviourRotateAboutVehicle::Update calls CameraSphericalRotationController::Update
  rem  every frame (the stick-driven yaw/pitch the player spins the car with). Its body
  rem  already existed in a TU nothing had ever mounted; mounting it also makes
  rem  CameraSphericalRotationController::Construct real, retiring the EMPTY STUB that used to
  rem  stand in for it in DirectorLinkStubs.cpp. It drags exactly two callees, both of which
  rem  are bodied and are mounted with it:
  rem      SmoothMover::Update                    -> Utils\BrnCameraSmoothMover.cpp (mounted below)
  rem      GetSmallestDifferenceBetweenDegsAngles -> BODIED this wave in CameraUtils.cpp. It was
  rem          declaration-only; BrnCamera2DRotationController.cpp only CALLS it, and mounting
  rem          that TU to reach it opens more than it closes (it needs the
  rem          Camera2DRotationController::kfDeadZoneRadius static, which has no definition
  rem          anywhere in the tree). MEASURED both ways.
  rem  ?????? BrnLooker.cpp is deliberately NOT mounted: it DOES NOT COMPILE (BrnLooker.cpp:189
  rem  calls the three-argument rw::math::vpu::SLerp that was replaced by the four-argument
  rem  form long ago and never re-fitted -- a stale TU nobody noticed because nothing ever
  rem  linked it). Looker::Parameters::Construct, the one function this wave needs out of it,
  rem  moved to BrnLooker.h as an inline. DELETE-WHEN: BrnLooker.cpp is re-fitted.
  rem  ??? BrnCameraShake.cpp (the Parameters::Serialise<S> slice) is STILL not mounted: its
  rem  three explicit instantiations drag DebugMenuSerialiser / TextFileWriteSerialiser /
  rem  TextFileReadSerialiser, whose Serialise(const char*, f32&) are all out-of-line in TUs
  rem  that are not on this list -- three unresolved externals opened to close one.
  rem  ??? ROTATE-HELPER WAVE (2026-08-02): CameraShake::Update was file-split OUT of that TU
  rem  into BrnCameraShakeUpdate.cpp and is mounted below, which RETIRES the empty `{}` stub
  rem  DirectorLinkStubs.cpp used to resolve it to. Its three blockers are all closed:
  rem      Utils::RotateMatrix44AffineByEulerAnglesZXY  -> BODIED in CameraUtils.cpp
  rem      CgsNumeric::Random::RandomFloat(f32,f32)     -> BODIED in Numeric\CgsRandom.cpp
  rem      CgsNumeric::Random::RandomVector(V3,V3)      -> BODIED in Numeric\CgsRandom.cpp
  rem  (both of those TUs are already on this list, so the mount cost is this ONE file).
  rem  ?????? ICE-SHAKE WAVE (2026-08-02): the SAME split again, for the other class in that
  rem  header -- BrnCameraShakeICEController.cpp carries CameraShakeICEController::Construct
  rem  (COMPLETE) and ::Update (head + the three gates; the authored-take arm is a documented,
  rem  self-announcing partial). It RETIRES the second and last DirectorLinkStubs.cpp group-E
  rem  stub, and that one was ARMED: Construct's job is to set mMatrix to the IDENTITY, and
  rem  BehaviourGameplayExternal::Update inlines GetMatrix() into a post-multiply on the camera
  rem  transform -- the zero-initialised matrix the stub left behind would have ANNIHILATED it.
  rem  Everything it calls was already on this list (shotgroup.cpp, CgsRandom.cpp,
  rem  BrnDirectorResourceManager*.cpp), so the mount cost is this ONE file.
  rem  ??? AND WITH IT, BrnBoostShakeController.cpp -- the FIFTH "body exists, nothing links it"
  rem  in this cluster. BoostShakeController::Update @0x8220E548 has been bodied at
  rem  Camera\BrnBoostShakeController.cpp:47 all along; the link was green only because nothing
  rem  reached it. BehaviourGameplayExternal::Update calls it directly at 0x822422B0.
  rem  MEASURED cascade: the TU includes only its own header, which includes only types.hpp
  rem  and <cstddef>. Zero new unresolved.
  echo "%SRC%\GameSource\Director\Camera\Utils\BrnCameraSphericalRotationController.cpp"
  echo "%SRC%\GameSource\Director\Camera\Utils\BrnCameraShakeUpdate.cpp"
  echo "%SRC%\GameSource\Director\Camera\Utils\BrnCameraShakeICEController.cpp"
  rem  ---- CRASH-CAMERA WAVE (2026-08-29): THE TWO IMPACT CONTROLLERS ARE NOW LINKABLE. ----
  rem  BehaviourBystanderCamImpactControllers.cpp is a PARTFILE of
  rem  Camera\Behaviours\BehaviourBystanderCam.cpp, carrying ImpactSlomoController::Update
  rem  @0x82227230 (THE CRASH SLOW MOTION -- it writes Camera::mEffects.mfSimTimeScale =
  rem  0.2857143 for a 2.0 s burst) and ImpactShakeController::Update @0x82243720.
  rem  ==> IT IS NOT THE PARENT TU. Do NOT "simplify" this by mounting BehaviourBystanderCam.cpp
  rem  instead. MEASURED, not assumed: that TU reaches every foreign object through a
  rem  `namespace detail` layer of ~30 free-function shims that are DECLARED AND NEVER DEFINED
  rem  anywhere in the tree, so mounting it opens ~28 unresolved externals -- and the one that
  rem  carries the whole feature (Camera_SetTimeScale) is the ONLY observable effect of the
  rem  slow-motion controller, so a quiet stub for it would link green and produce NO SLOW
  rem  MOTION. The partfile is written against the real types instead (Camera / AllVehicleData
  rem  / VehicleTracker / VehicleRef / CameraImpactEffect / CameraShake).
  rem  MEASURED mount cost: its only project-specific callees are CameraShake::Update
  rem  (BrnCameraShakeUpdate.cpp, mounted two lines up), CameraImpactEffect::RegisterImpact
  rem  (BrnCameraImpactEffect.cpp) and Utils::GetZoomFromFOVDegs (CameraUtils.cpp) -- all three
  rem  already on this list; AllVehicleData::GetPlayer and VehicleRef::Get are header inlines.
  echo "%SRC%\GameSource\Director\Camera\Behaviours\BehaviourBystanderCamImpactControllers.cpp"
  rem  ... and its ONE unresolved external: CameraImpactEffect::RegisterImpact @0x821F3648.
  rem  Split into its own partfile for the SAME reason BrnCameraShakeUpdate.cpp exists -- the
  rem  parent BrnCameraImpactEffect.cpp carries three explicit Parameters::Serialise<S>
  rem  instantiations over DebugMenuSerialiser / TextFile{Read,Write}Serialiser, none of which
  rem  is on this list. MEASURED: with the partfile the link is clean; the partfile includes
  rem  nothing but its own header.
  echo "%SRC%\GameSource\Director\Camera\Utils\BrnCameraImpactEffectRegisterImpact.cpp"
  echo "%SRC%\GameSource\Director\Camera\BrnBoostShakeController.cpp"
  echo "%SRC%\GameSource\Director\Camera\Utils\BrnCameraSmoothMover.cpp"
  rem  Camera::Utils::Tweaker::Construct @0x821F8588 ONLY -- file-split out of
  rem  BrnCameraTweaker.cpp on 2026-08-01 (see that file's banner). MEASURED: mounting the
  rem  whole tweaker TU closes 1 unresolved and opens 5 (KAAC_AXIS_NAMES / KAAC_CONTROL_NAMES
  rem  rodata + DebugController::GetControllerInfo + DebugInterface::Get2dRender +
  rem  DebugRender::Draw2DTextJustified); the Construct body alone touches nothing but its own
  rem  binding arrays, so this costs zero and pre-closes one of the camera family's 31.
  echo "%SRC%\GameSource\Director\Camera\Utils\BrnCameraTweakerConstruct.cpp"
  echo "%SRC%\GameSource\GameState\BrnGameStateModuleIO.cpp"
  rem  BridgeGameStateToWorld wave (2026-08-01): OutputBuffer::Construct now runs the console's
  rem  own RaceCarRaceDistanceInterface::Clear (X360 0x82357470) on its +173196 member, whose
  rem  body lives here. MEASURED mount cost: ZERO -- the object's only UNDEF externals are CRT
  rem  plus the assert/StrStream trio the exe already links (dumpbin /SYMBOLS, 17 UNDEFs, none
  rem  project-specific).
  echo "%SRC%\GameSource\GameState\BrnGameStateSharedIO.cpp"
  rem producer wave (2026-08-01): the GameState module itself + its progression manager.
  rem  BrnGameStateModule.cpp had SEVEN finished X360 reconstructions that DID NOT COMPILE --
  rem  it was written against a richer BrnGameStateModule.h that was later reduced to the
  rem  "minimal slice", and because the TU was never mounted nobody noticed (15 cl errors).
  rem  Growing the header back (the members those bodies bind to + the module's OutputBuffer)
  rem  makes them real. MEASURED: mounting both of these costs SEVEN unresolved, all trivial
  rem  accessors (ModeManager::GetCurrentGameMode[Type], ProgressionManager::GetProfile,
  rem  Profile::GetCarCount / SetRoadRule*, CarData::GetId) -- all now bodied.
  rem  This is what gives the game-state module a REAL GameStateModuleIO::OutputBuffer, i.e.
  rem  the queue BridgeGameStateToDirector appends into the director every frame.
  echo "%SRC%\GameSource\GameState\BrnGameStateModule.cpp"
  echo "%SRC%\GameSource\GameState\Progression\BrnProgressionManager.cpp"
  rem *** DRIVE-THRU LINK CLOSURE (2026-08-27): the two partfiles that close the last
  rem  unresolved external. BrnProgressionManager_Unlocks.cpp bodies UnlockCarFromTrophy
  rem  @0x8237B0E8, UnlockSpecialCars @0x8237AF38, OnTrophyUnlock @0x82389740 and OnDriveThru
  rem  @0x82399DD0; BrnProgressionManager_Completion.cpp bodies the percentage subtree
  rem  ComputeCompletionPercentage @0x8238A198 + GetPercentageOfEventsCompleted @0x8237B390 +
  rem  GetNumberOfBeatenRivals @0x8236FBC8 + GetTrueNumberOfRivals @0x8236FB10, plus the two
  rem  consumers CheckForSpecialCarUnlocks @0x82396058 / SendGameCompletionResults @0x82395C28.
  rem  They MUST mount together: OnDriveThru calls into the Completion partfile and the
  rem  Completion partfile calls UnlockSpecialCars back in the Unlocks one.
  echo "%SRC%\GameSource\GameState\Progression\BrnProgressionManager_Unlocks.cpp"
  echo "%SRC%\GameSource\GameState\Progression\BrnProgressionManager_Completion.cpp"
  rem *** PAUSE-SCREEN STAT PANEL (2026-08-29): the producer of game action 180. Bodies
  rem  ProgressionManager::GetGameStats @0x8238A6A0 (566 insns) + GetTotalWinsForNextRank
  rem  @0x82370510, the middle hop of GUI 435 -> event 79 -> action 180 -> GUI 436. Its
  rem  caller is GameStateModule_gUI_00.cpp's case-79 arm (already mounted); without this
  rem  partfile that call is an LNK2019 and the Driver Details stat panel stays blank.
  echo "%SRC%\GameSource\GameState\Progression\BrnProgressionManager_GameStats.cpp"
  rem  BrnGameActionData.cpp -- GameStats::Construct @0x82354F38 (+ PlayerInfo::Construct
  rem  @0x82355038), the record GetGameStats fills. Reconstructed long ago, never mounted
  rem  because nothing called it until now. A pure leaf (CgsAssert + strncpy).
  echo "%SRC%\GameSource\GameState\SharedIO\BrnGameActionData.cpp"
  rem ??? PREPARE2 SUB-OBJECT WAVE (2026-08-11) -- the two legs GameStateModule::Prepare2
  rem  @0x8239ED10 left parked. The module now EMBEDS both sub-objects by value, exactly as the
  rem  console does (X360 Construct @0x82380388 / ctor @0x827E44B8): the achievement manager at
  rem  this+181680 and the street manager at this+284520.
  rem
  rem  ---- leg 1: the achievement manager ------------------------------------------------
  rem  ProgressionManager::Prepare2's faithful console assert `lpAchievementManager`
  rem  (BrnProgressionManager.cpp:265) fired every boot because GameStateModule::Prepare2 passed
  rem  0 where the X360 passes r8 = this+181680. The concrete type is the X360 leaf, attested four
  rem  ways in the asm (Prepare @0x8239E578 -> AchievementManagerX360::Prepare, Release
  rem  @0x823756A8 -> ::Release, PreWorldUpdate @0x823A5328 -> ::Update, and the ctor stores that
  rem  class's vtable off_820CE768 at +181680). PC reuses the X360 leaf -- the same precedent as
  rem  CgsSaveLoadX360.cpp below and CgsNetwork::BuddyManagerX360 standing in as the platform
  rem  buddy leaf; no build has an AchievementManagerPC.
  rem  MEASURED (cl /c + dumpbin /SYMBOLS): this TU costs exactly ONE new symbol,
  rem  CgsSystem::CgsXOverlapped::Construct (the embedded XOVERLAPPED its Prepare/Release build),
  rem  hence CgsXOverlappedX360.cpp joining right after -- which in turn wanted ONE XDK import,
  rem  XGetOverlappedExtendedError, now a PC leaf beside its twin XGetOverlappedResult in
  rem  BrnBaselineLinkStubs.cpp. Net new unresolved after both: ZERO.
  rem  ??? BrnGameStateAchievementManagerBase.cpp is deliberately NOT here: mounting it costs EIGHT
  rem  unresolved externals that have no definition anywhere in the tree (ScoringSystem::
  rem  GetPlayerScore / GetPlayerModeCrashes / GetPlayerModeTakedowns / GetNewlyWreckedCarCount /
  rem  GetNumberOfTakedownsAgainst, ProgressionManager::GetCarChallengeWinCount /
  rem  GetCollectedStuntElementCount / GetProfileTotalTakedowns), all pulled in by the base's
  rem  gameplay-event hooks. ?????? AND "nothing calls them, /OPT:REF strips them" IS NOT A DEFENCE --
  rem  VERIFIED this wave with a minimal repro: an unreferenced COMDAT that calls an undefined
  rem  symbol still fails LNK2019 under /Gy + /OPT:REF (the linker resolves before it discards).
  rem  Several rem blocks further up in this file assume otherwise; they are about CODE SIZE, not
  rem  about unresolved externals. Mount the base TU when those eight land.
  echo "%SRC%\GameSource\GameState\AchievementManager\X360\BrnGameStateAchievementManagerX360.cpp"
  echo "%SRC%\GameShared\GameClasses\System\X360\CgsXOverlappedX360.cpp"
  rem  ---- leg 2: the street manager / STREETDATA.DAT loader -------------------------------
  rem  Prepare2 case 2 is `StreetManager::Prepare2(this+284520, out, this+232384, this+42320)`
  rem  @0x823509D8 == LoadStreetData then SetupParRivals. LoadStreetData @0x8234F630 was the ONE
  rem  function of that family with no body on disk (the ledger had it `reviewed` -- the
  rem  reviewed != implemented trap); it is reconstructed this wave into the sibling loads
  rem  partfile, and it is the only writer of mpStreetData in the whole image.
  rem  MEASURED: these three TUs add ZERO unresolved externals -- every callee
  rem  (RequestInterface<3072>::LoadBundle/AcquireResource, EventReceiverQueue<3072,16>,
  rem  BaseResourcePtr::CreateFromHandle, ID::HashString + its StrStream operator<<) is already in
  rem  the link.
  rem  ??? The REST of the StreetManager family stays out. BrnGameStateStreetManager.cpp
  rem  (Prepare2/SetupParRivals) and BrnStreetManagerDebugComponent.cpp are the expensive ones:
  rem  the debug component has a vtable, so mounting it hard-references its virtual
  rem  Update/OnActivate/RenderHUD and ~15 still-unhomed StreetManager/ScoringSystem/
  rem  ProgressionManager/OutputBuffer symbols. That is also why GameStateModule::Construct does
  rem  not call StreetManager::Construct yet (its first statement constructs that component) --
  rem  see the DELETE-WHEN block there.
  echo "%SRC%\GameSource\GameState\StreetData\BrnGameStateStreetManager_wB_01.cpp"
  rem  ---- leg 3: THE DISTRICT MAP (2026-08-11) --------------------------------------------
  rem  GameStateModule::Prepare @0x8239E578 stage 23 (E_PREPARESTAGE_STREET_MANAGER) is
  rem  `StreetManager::Prepare(this+284520, out, this+232384)` @0x82350900 == LoadAIData &&
  rem  LoadDistrictMap. LoadDistrictMap @0x8234FB98 is the ONLY writer of
  rem  mDistrictMapResourceHandle, which SetupParRivals dereferences unconditionally -- so this
  rem  is the leg the Prepare2 SetupParRivals park was blocked on. Its bind is real now (the
  rem  acquire response's handle pair, read BY MEMBER off AcquireResourceResponse).
  rem  ?????? IT ONLY ACQUIRES. The console never loads Districts.dat here -- stage 4
  rem  (StuntManager::Prepare -> LoadDistrictMap @0x82399458) did that 19 stages earlier. There is
  rem  no reconstructed StuntManager sub-object on this module, so stage 4 now issues the
  rem  console's own LoadBundle("Districts.dat", pool 5) itself, latched by
  rem  meDistrictsBundleStage (declared + flagged in BrnGameStateModule.h).
  rem  SIBLING TU, MEASURED (cl /c with THESE flags + dumpbin /SYMBOLS against the linked obj
  rem  set): mounting the owning wB_00 partfile costs ONE unresolved external,
  rem  BrnStreetData::operator++(ScoreType&, int) (street-DATA side,
  rem  SharedClasses\StreetData\BrnChallengeData.cpp), pulled in by Construct's/Destruct's
  rem  score-type loops. Prepare touches none of it, so the split costs ZERO. Net new unresolved
  rem  for this whole wave (module + wB_01 + this): ZERO. Fold back into wB_00 when that lands.
  echo "%SRC%\GameSource\GameState\StreetData\BrnGameStateStreetManager_Prepare.cpp"
  rem  ---- leg 4: PAR RIVALS (2026-08-11) -- the body gap that leg 3 left behind ------------
  rem  GameStateModule::Prepare2 case 2 is `StreetManager::Prepare2(out, &rq, &tqm)` @0x823509D8
  rem  == `if (LoadStreetData(out, rq)) { SetupParRivals(tqm); return 1; }`. The SetupParRivals
  rem  half was PARKED because it closed over four symbols with no body anywhere in the tree.
  rem  All four are homed now:
  rem    * Road::GetRoadLimitId0()        -> header inline in SharedClasses\StreetData\BrnStreetData.h
  rem    * ProgressionData::GetRival(s32) -> SharedClasses\Progression\BrnProgressionData.cpp (mounted below)
  rem    * Random::RandomInt(s32,s32)     -> GameShared\GameClasses\Numeric\CgsRandom.cpp (mounted elsewhere)
  rem    * Rival::GetDistrict()           -> header inline in SharedClasses\Progression\BrnRival.h
  rem  THREE SIBLING SPLITS, each MEASURED (cl /c with THESE flags + dumpbin /SYMBOLS against the
  rem  defined-symbol set of build\game\obj) -- the _Prepare.cpp precedent, one function per TU:
  rem    * _Prepare2.cpp             out of BrnGameStateStreetManager.cpp, which costs SIX
  rem      (BrnStreetData::operator++, ChallengeHighScoreEntry::Construct,
  rem       ChallengePlayerScoreEntry::Construct, ChallengeData::SetScore, ScoreList::
  rem       KAI_MIN_SCORES/KAI_MAX_SCORES -- all from its two score-entry factories).
  rem    * _SetupParRivals.cpp       out of _wC_02.cpp, which costs THIRTEEN (the whole
  rem      score-entry + PlayerName + SPrintf + StrStream chain, all ProcessScoreRequestEvent's).
  rem    * _FindRivalsByDistrict.cpp out of _wC_04.cpp, which costs FOUR (StreetManager::
  rem      GetStreetData / HasPlayerBeatenParScore / HasPlayerBeatenFriendScore, plus
  rem      Rival::GetDistrict -- the first three are FillInRoadRulesQuery's and
  rem      GetNumberOfCompleteRoadsRuledByLocalPlayer's).
  rem  Each function was MOVED, not copied, so folding a split back in later is a delete, not a
  rem  duplicate-symbol hunt. NET NEW UNRESOLVED FOR THESE THREE TUs: ZERO.
  echo "%SRC%\GameSource\GameState\StreetData\BrnGameStateStreetManager_Prepare2.cpp"
  echo "%SRC%\GameSource\GameState\StreetData\BrnGameStateStreetManager_SetupParRivals.cpp"
  echo "%SRC%\GameSource\GameState\StreetData\BrnGameStateStreetManager_FindRivalsByDistrict.cpp"
  rem *** PAUSE-SCREEN STAT PANEL (2026-08-29): the three roads-ruled tallies
  rem  ProgressionManager::GetGameStats reads. wC_05 bodies GetNumberOfParShowTimeRoadsRuled
  rem  ByLocalPlayer @0x8233F230 + GetNumberOfParTimeTrialRoadsRuledByLocalPlayer @0x8233F2C0
  rem  (+ GetChallengeParScore); wC_04 bodies GetNumberOfCompleteRoadsRuledByLocalPlayer
  rem  @0x8233F350 (+ FillInRoadRulesQuery). FindRivalsByDistrict was already split out of
  rem  wC_04 into its own mounted partfile, so there is no duplicate definition.
  echo "%SRC%\GameSource\GameState\StreetData\BrnGameStateStreetManager_wC_04.cpp"
  echo "%SRC%\GameSource\GameState\StreetData\BrnGameStateStreetManager_wC_05.cpp"
  rem  wC_06 (NEW) bodies the two predicates all three tallies count with --
  rem  HasPlayerBeatenParScore @0x823361D0 + HasPlayerBeatenFriendScore @0x823362A0 -- and
  rem  wB_02 supplies the two score-table fetches they call (GetChallengeUserScore
  rem  @0x82335E08 / GetChallengeFriendHighScore @0x82335F30). All four MUST mount together.
  echo "%SRC%\GameSource\GameState\StreetData\BrnGameStateStreetManager_wC_06.cpp"
  echo "%SRC%\GameSource\GameState\StreetData\BrnGameStateStreetManager_wB_02.cpp"
  rem  ??? STILL OUT: the rest of BrnGameStateStreetManager.cpp (the two score-entry
  rem  factories), _wC_02.cpp (ProcessScoreRequestEvent) and _wC_04.cpp (the two road-rules
  rem  tallies). Their costs are the measured numbers above; mounting any of them anyway is
  rem  LNK2019, not a stripped COMDAT (/OPT:REF resolves before it discards -- see the
  rem  achievement-manager note above).
  rem ---- (2026-08-11) the embedded StreetManagerDebugComponent's vtable is emitted by ----
  rem ---- BrnGameModule.obj's implicit ctor chain; its real TUs stay UNMOUNTED (they   ----
  rem ---- close over the road-rules cheat set: StreetManager score setters, ScoreList  ----
  rem ---- tables, ProgressionManager trophy hooks -- 16 link-measured externals). The  ----
  rem ---- two vtable slots are gated in BrnBaselineLinkStubs.cpp until that wave.      ----
  rem  ...and the resource type STREETDATA.DAT's one resource carries (id 0xBC9CC502 ==
  rem  HashString("StreetData"), type 0x10018 == 65560, measured on the shipped bundle). Newly
  rem  REGISTERED in CgsResourceTypeRegistration.cpp: without a handler the pool stores a null
  rem  mpResourceType, BundleLoader skips FixUp, and the acquire hands back a record whose table
  rem  bases are still file offsets -- the same defect that made ProgressionData/PlayerCarColours
  rem  look loaded but read as garbage.
  echo "%SRC%\SharedClasses\StreetData\BrnStreetDataResourceType.cpp"
  echo "%SRC%\SharedClasses\StreetData\BrnStreetData.cpp"
  rem ??? FINAL PRODUCER WAVE (2026-08-01) -- THE JUNKYARD CAR-SELECT FSM ITSELF.
  rem  The previous wave measured these two TUs at FOURTEEN unresolved externals (7 x
  rem  GameStateModule, 5 x ProgressionManager, 2 x CarSelectManager privates). All fourteen
  rem  are bodied now, plus the three console callees they pull in (GameStateModule::
  rem  ApplyCarStats @0x82381188 + GetOriginalCarId @0x823758E8, ProgressionManager::
  rem  OnPlayerCarChange @0x8237AC38). MEASURED after that: 14 -> 1 -> 0, the one being
  rem  ProgressionData::FindCarOpponentSet, which is why BrnProgressionData.cpp joins them
  rem  (it in turn wanted OpponentBalanceData's four graph accessors -- the X360 has no
  rem  symbol for any of them, they are header-inline now).
  rem  THIS IS THE PRODUCER: CarSelectManager posts game action 73 onto the GameState
  rem  OutputBuffer's queue, BridgeGameStateToDirector appends it, MainDirector::
  rem  ProcessInputQueue case 73 moves meJunkyardState 0 -> 2.
  echo "%SRC%\GameSource\GameState\CarSelect\BrnCarSelectManager.cpp"
  echo "%SRC%\GameSource\GameState\CarSelect\BrnCarSelectManager_CarChange.cpp"
  rem ??? [tut-ticker] wave (2026-08-24) -- THE TRAINING-TIP MANAGER, whole. Construct (PS3
  rem  0x241DE0), Update @0x823937D0 (the FSM that turns a queued tip into GameAction 148 ->
  rem  GUI event 537 -> the bottom-of-screen tutorial ticker), RequestTraining @0x82365B20,
  rem  IsTipAllowedInGameMode @0x823590A0, PlayNewAtomikaFreeburnVO @0x82365FC8 + the
  rem  previously-bodied ticker/pause/follow-on set. Every raw offset it reads is identified
  rem  against named members (see the TU banner); its tick site is GameStateModule::
  rem  PreWorldUpdateTrainingBringUp, its request feed is ProcessGameEvents case 113.
  echo "%SRC%\GameSource\GameState\TrainingManager\BrnTrainingManager.cpp"
  echo "%SRC%\SharedClasses\Progression\BrnProgressionData.cpp"
  rem ??? TRIGGERS wave (2026-08-01) -- THE TRIGGERS.DAT LOADER.
  rem  TriggerQueryManager::Prepare @0x82398218 is the console's own loader: LoadBundle
  rem  ("Triggers.dat", pool 5) -> acquire("TriggerData") -> LoadTrafficLanes. It is driven by
  rem  GameStateModule::Prepare @0x8239E578 stage 3, whose sole caller is BrnGameModule::
  rem  GamePrepare @0x823EFBD0 stage 4 -- which the PC build had stubbed out, which is why
  rem  the boot log said `[WorldMap] LOADED -- traffic=1 trigger=0 ai=0`.
  rem  SIBLING TU, MEASURED: mounting the owning BrnTriggerQueryManager.cpp costs 13
  rem  unresolved externals, every one of them pulled in by UpdateTriggers /
  rem  ProcessPlayerTriggers (RoadRulesManager x2, DriveThruManager::HandleDriveThru,
  rem  StuntManager::LatchJumpElement, TriggerManagementInputInterface x2, Killzone::GetTrigger,
  rem  GenericRegion::GetGroupId, BoxRegion::ComputeDirection, 3 x
  rem  RCEntityActiveRaceCarOutputInterface). Prepare touches NONE of them, so the split costs
  rem  zero. Fold back into the owning TU when those 13 land.
  rem gateui wave 2026-08-20: the full TU adds Construct/UpdateTriggers/accessors; the _Prepare split STAYS (it owns Prepare; 10 shared COMDATs, no LNK2005).
  echo "%SRC%\GameSource\GameState\TriggerQueryManager\BrnTriggerQueryManager.cpp"
  echo "%SRC%\GameSource\GameState\TriggerQueryManager\BrnTriggerQueryManager_Prepare.cpp"
  rem *** DRIVE-THRU wave (2026-08-27) -- THE GAS STATION / BODY SHOP / PAINT SHOP MANAGER.
  rem  The 13-unresolved-externals note above lists "DriveThruManager::HandleDriveThru" as one of
  rem  the reasons ProcessPlayerTriggers' drive-thru arm was parked. That is PAID: the TU compiles
  rem  (it needed one #include for the GameActionQueue typedef and one `::` on EActiveRaceCarIndex),
  rem  and its two previously-bodiless callees -- SetPlayerCarDriver @0x823867A0 and
  rem  PlayAutoRepairTraining @0x82378848, both of which the console's own assert strings place in
  rem  THIS file -- are bodied in it now, so mounting costs zero new externals.
  rem  Its Construct/Prepare/Update call sites are GameStateModule's (mDriveThruManager, the
  rem  console's this+44240); ProcessDriveThru posts action 100, whose consumer chain is
  rem  BridgeGameStateToWorld -> BridgeActionsToRaceCarModule -> RaceCarEntityModule::
  rem  HandleGameActions @0x8230BE08 -> boost strategy vtable slot 46 (OnDriveThru ->
  rem  UpdateMaxBoost(true)) -- every link of which is already mounted.
  echo "%SRC%\GameSource\GameState\Offences\BrnDriveThruManager.cpp"
  rem  ---- the achievement hooks the drive-thru chain link-requires ------------------------
  rem  A SPLIT of BrnGameStateAchievementManagerBase.cpp (the four bodies were MOVED, not
  rem  copied), so the deliberately-unmounted parent TU above stays unmounted while
  rem  HandleDriveThru/ProcessDriveThru's OnFindAllCarParks + OnBodyShop and
  rem  GameStateModule::CheckForAllEventsBeingFound's OnFindAllEvents all resolve.
  rem  MEASURED: ZERO new unresolved externals -- the only non-virtual callee is
  rem  ScoringSystem::GetNewlyWreckedCarCount, bodied this wave in BrnScoringSystem_Queries.cpp.
  echo "%SRC%\GameSource\GameState\AchievementManager\BrnGameStateAchievementManagerBase_DriveThru.cpp"
  rem  !!!!!! THE LINK IS STILL RED, ON EXACTLY ONE SYMBOL (save-verify wave, 2026-08-27).
  rem  BrnProgression::ProgressionManager::OnDriveThru @0x82399DD0 -- referenced by
  rem  DriveThruManager::HandleDriveThru, no body anywhere. It is NOT stubbed: it cascades three
  rem  functions deep into work with no bodies (OnTrophyUnlock @0x82389740, 379 lines of
  rem  pseudocode; CheckForSpecialCarUnlocks @0x82396058, 111; SendGameCompletionResults
  rem  @0x82395C28, 40), and a quiet stub on a path this hot is exactly the defect class
  rem  STRATEGY.md forbids.
  rem  MEASURED with a __debugbreak() trap in its place: it fires ~10 s into a plain junkyard ->
  rem  car-select -> free-burn drive (HandleDriveThru <- ProcessPlayerTriggers), so it is not a
  rem  cold path -- land the body, do not paper over it.
  rem  This block took the link from FIVE unresolved DriveThruManager::* externals (the state
  rem  before it, from the mounted call sites in BrnGameStateModule / BrnTriggerQueryManager /
  rem  GameStateModule_gUI_00) down to this one. Removing these two echoes puts it back to five;
  rem  it does NOT make the build green.
  rem intro wave (2026-07-30): the live BrnProgression::Profile TU. Needed by
  rem BrnGuiModule::Prepare (Profile::Construct seeds mbIsNewProfile = true, the
  rem first-boot INTRO gate) and by the licence component (GetLicenceIssuedDate /
  rem SetLicenceIssuedDateAsNow).
  echo "%SRC%\GameSource\GameState\Progression\BrnProfile.cpp"
  rem save-image codec wave (2026-08-11): Profile::Serialise @0x8237C1F0 + Profile::Deserialise
  rem @0x8237D308, split out of BrnProfile.cpp as a per-function TU (they are ~700 lines of
  rem console code sharing ONE serialised-layout table, so they stay in one TU together).
  rem Needed by BrnGuiProfile.cpp's ProgressionProfile_Serialise/_Deserialise shims, which
  rem previously stood in with BrnGuiSaveLoad::Profile/ProfileDLC1::ConstructImage() and a
  rem no-op respectively. New externals: none beyond BrnProfile.cpp's own (the four
  rem SplitArray specialisations live there, CgsNetworkTexture.cpp is already mounted below).
  echo "%SRC%\GameSource\GameState\Progression\BrnProfile_SaveImage.cpp"
  rem ...and the two TUs BrnProfile::SetPlayerLicencePicture links against (the licence
  rem mugshot wrapper + the RGB->A1R5G5B5 converter).
  echo "%SRC%\GameShared\GameClasses\Network\Texture\CgsNetworkTexture.cpp"
  echo "%SRC%\GameShared\GameClasses\Network\Utilities\CgsNetworkImageConverter.cpp"
  echo "%SRC%\GameSource\Director\Camera\SharedIO\BrnPlayerInfo.cpp"
  echo "%SRC%\GameSource\Replays\BrnReplayStatusInterface.cpp"
  echo "%SRC%\GameSource\World\CrashModule\SharedIO\NetworkInputInterface.cpp"
  rem  wave Q6 / bridges: BrnWorld::CrashIO::TrafficInputInterface::Construct -- called by the traffic
  rem  OutputBuffer_PostPhysics::Construct landed this wave.
  echo "%SRC%\GameSource\World\CrashModule\SharedIO\TrafficInputInterface.cpp"
  echo "%SRC%\GameSource\World\CrashModule\SharedIO\BrnCrashModuleIO_OutputBuffer_PreScene.cpp"
  echo "%SRC%\GameSource\World\CrashModule\SharedIO\BrnCrashModuleIO_InputBuffers.cpp"
  echo "%SRC%\GameSource\Network\BrnNetworkModuleIO.cpp"
  echo "%SRC%\GameSource\Network\SharedIO\BrnNetworkModuleGameStateIOInterfaces.cpp"
  echo "%SRC%\GameSource\Network\SharedIO\BrnNetworkModuleInGamePlayerStatusInterface.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BrnVehicleEvents.cpp"
  rem drivable wave 2026-08-01: ActiveRaceCar::AddHandlingModel calls VehicleInputInterface::CreateRaceCar
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BrnVehicleInputInterface.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\CreateRaceCarEvent.cpp"
  echo "%SRC%\GameSource\Game\BrnGlobalCpuMonitors.cpp"
  echo "%SRC%\GameSource\GameFlowController\TopLevel\BrnGameMainFlowStates.cpp"
  echo "%SRC%\GameSource\GameFlowController\TopLevel\BrnGameMainFlowInGameState.cpp"
  echo "%SRC%\GameSource\Sound\Module\BrnRootSoundModule.cpp"
  rem ---- the root sound module IO accessors (b5-decomp 922b2f53, audit F-P6-17/F-P5-10): the
  rem  four RootInput/OutputBuffer getters LoadingScriptedState::LoadSoundModule + Update call.
  echo "%SRC%\GameSource\Sound\Module\BrnRootSoundModuleIO.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\CgsTestBedAllocator.cpp"
  echo "%SRC%\GameSource\Sound\BrnResourceRegistrar.cpp"
  echo "%SRC%\GameSource\Sound\Module\LogicModule\BrnSoundLogicModule.cpp"
  echo "%SRC%\GameSource\Sound\Module\LogicModule\BrnSoundLogicModuleIo.cpp"
  echo "%SRC%\GameSource\Sound\Module\LogicModule\BrnStateManager.cpp"
  echo "%SRC%\GameSource\Sound\Module\LogicModule\BrnEmitterStateManager.cpp"
  echo "%SRC%\GameSource\Sound\Passby\BrnPassbyStateManager.cpp"
  echo "%SRC%\GameSource\Sound\Vehicles\BrnVehicleStateManager.cpp"
  echo "%SRC%\GameSource\Sound\Vehicles\BrnAIVehicleStateManager.cpp"
  echo "%SRC%\GameSource\Sound\Vehicles\BrnPlayerVehicleStateManager.cpp"
  echo "%SRC%\GameSource\Sound\Traffic\BrnTrafficStateManager.cpp"
  echo "%SRC%\GameSource\Sound\Streaming\BrnStreamingStateManager.cpp"
  echo "%SRC%\GameSource\Sound\Collision\BrnCollisionStateManager.cpp"
  echo "%SRC%\GameSource\Sound\Collision\BrnCollisionDataStructures.cpp"
  echo "%SRC%\GameSource\Sound\Global\BrnGlobalStateManager.cpp"
  echo "%SRC%\GameSource\Sound\BrnDebugComponent.cpp"
  echo "%SRC%\GameSource\Sound\Debug\BrnSoundDebugStatistics.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Logic\CgsVoice.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\UI\CgsWindow.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\UI\Windows\CgsCustomWindow.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\UI\Windows\CgsLogWindow.cpp"
  echo "%SRC%\GameSource\GameFlowController\TopLevel\BrnGameMainFlowController.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Timer\CgsFrameRate.cpp"
  rem  ---- FLAG PC quality-of-life: the 60Hz-simulation / uncapped-render blend layer.
  rem  CgsFrameRate.cpp publishes the interpolation alpha; this is what the render legs read.
  echo "%SRC%\GameShared\GameClasses\System\Timer\CgsFrameInterpolation.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\PerfMon\Cpu\CgsPerfMonCpu.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\PerfMon\DebugComponent\CgsDebugComponentPerfMonCpu.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\PerfMon\Gpu\CgsPerfMonGpu.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\PerfMon\Gpu\PS3\CgsPerfMonGpuPS3.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\PerfMon\DebugComponent\CgsDebugComponentPerfMonGpu.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\MessageSystem\DebugComponent\CgsDebugComponentMessageFilter.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\CgsDebugManager.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\CgsDebugCollections.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Core\CgsDebugComponent.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Interface\CgsDebugInterface.cpp"
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
  echo "%SRC%\GameShared\GameClasses\Module\CgsIOBuffer.cpp"
  echo "%SRC%\GameShared\GameClasses\Module\CgsModule.cpp"
  echo "%SRC%\GameShared\GameClasses\Module\CgsModuleSingleBuffered.cpp"
  echo "%SRC%\GameShared\GameClasses\Module\CgsBaseEventReceiverQueue.cpp"
  echo "%SRC%\GameShared\GameClasses\Containers\CgsPriorityQueue.cpp"
  echo "%SRC%\GameShared\GameClasses\Containers\CgsLinkedList.cpp"
  echo "%SRC%\GameShared\GameClasses\Containers\CgsHashTableTextureState25.cpp"
  echo "%SRC%\GameShared\GameClasses\Module\CgsDataBuffer.cpp"
  echo "%SRC%\GameShared\GameClasses\Module\CgsDataStructure.cpp"
  echo "%VEN%\EAThread\source\eathread_rwmutex.cpp"
  echo "%VEN%\EAThread\source\eathread.cpp"
  echo "%VEN%\EAThread\source\eathread_mutex.cpp"
  echo "%VEN%\EAThread\source\eathread_condition.cpp"
  echo "%VEN%\EAThread\source\pc\eathread_thread_pc.cpp"
  echo "%VEN%\EAThread\source\pc\eathread_semaphore_pc.cpp"
  echo "%VEN%\EAThread\source\pc\eathread_callstack_win64.cpp"
  echo "%VEN%\EAThread\source\pc\eathread_x360align.cpp"
  echo "%SRC%\GameSource\Graphics\BrnRendererModule.cpp"
  rem ---- RendererIO PAIR (2026-08-17, boot audit F-P2-4 / b5-decomp 888a6cbf): the OutputBuffer/
  rem  InputBuffer accessors + both Constructs. BrnRendererModule::Update publishes through them and
  rem  BrnGameModule::GamePrepare creates the pair (CreateIOBuffer<T> calls T::Construct). NOT
  rem  BrnRendererModuleIO.cpp beside it -- that older TU defines the same two Constructs (ODR).
  echo "%SRC%\GameSource\Graphics\BrnRendererModuleIO_OutputBuffer_Accessors.cpp"
  rem ---- BLOBBY SHADOW COLLECTOR (2026-08-12): the AddShadow TU, ledger-`done` since its
  rem  reconstruction but never actually mounted -- so its three data defects (a 0.0f reject
  rem  threshold that dropped every car off the ground, a missing 3 cm mvPos lift, and the
  rem  extents bias landing on the wrong field) were never compiled, let alone run.
  rem  MEASURED closure, not assumed: cl /c on both TUs then dumpbin /SYMBOLS gives exactly
  rem  ONE unresolved external between them -- AddShadow itself, defined by the first file
  rem  (plus _fltused, CRT). The header pulls only header-only types, and BrnRendererModule.h
  rem  already embeds BrnBlobbyShadowManager BY VALUE, so the type is in the linked set anyway.
  rem  The two CgsSceneManager::EntityId / CgsPhysics::RigidBodyId ctors they emit are COMDAT
  rem  "pick any" -> no LNK2005. Both basenames are unique in this list.
  rem  NOTE: mounting this does NOT put a blob on screen -- the Im3d/shader hop that consumes
  rem  the buffer (ImRenderer<BasicColouredTexturedVertex> + the PC program pair) is still
  rem  missing. This mounts the COLLECTOR and makes its layout pins real.
  echo "%SRC%\GameSource\Graphics\BrnBlobbyShadowManager.cpp"
  echo "%SRC%\GameSource\Sound\Module\BrnRootSoundModuleIO.cpp"
  echo "%SRC%\GameSource\Graphics\BrnRendererModuleIO_OutputBuffer_Accessors.cpp"
  rem  ...and the embed check beside it: never called (discarded by /OPT:REF), but it is the
  rem  only place the ShadowStruct/buffer static_asserts actually execute. Same trap as
  rem  BrnVehicleManager.h's _AssertLayout, which sat in an unmounted TU for ten waves.
  echo "%SRC%\GameSource\Graphics\BrnBlobbyShadowManager_embed_check.cpp"
  echo "%SRC%\GameSource\Graphics\BrnShaderConstantsFrame.cpp"
  echo "%SRC%\GameSource\Game\BrnLoadingScreenRenderer.cpp"
  echo "%SRC%\GameSource\Game\BrnDispatchThreadInputBuffer.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\ImmediateMode\CgsIm2d.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\ImmediateMode\ImRenderBuffer\CgsImRenderBufferTemplate.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptRenderHandler.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptCallbackRender.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptCallbackRenderAllocateString.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptString.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptAux.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptDataHandler.cpp"
  rem ---- wave49 link dep: the CgsNumeric::Random out-of-line draws ----
  echo "%SRC%\GameShared\GameClasses\Numeric\CgsRandom.cpp"
  rem ---- the faithful AptCommunicator delivery chain (Layer 2) ----
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptCommunicator.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptObjectController.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptComponentList.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\State\CgsGuiComponent.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\CgsGuiShared.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptRenderHooks.cpp"
  rem ---- EATech Apt engine: re-added to LINK BootLegal's title_screen02 Apt render ----
  echo "%SRC%\SDKs\EATech\AptRenderLinkStubs.cpp"
  echo "%SRC%\SDKs\EATech\AptGlobals.cpp"
  echo "%SRC%\SDKs\EATech\Apt\AptActionDefineFunction2.cpp"
  echo "%SRC%\SDKs\EATech\Apt\AptActionTryCatchFinallyBlock.cpp"
  echo "%SRC%\SDKs\EATech\Apt\AptKeyMembersIndex.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\PC\CgsAptRenderBackendPC.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\PC\CgsAptStreamLoaderPC.cpp"
  echo "%SRC%\SDKs\EATech\Apt\AptInit.cpp"
  echo "%SRC%\SDKs\EATech\Apt\Apt.cpp"
  echo "%SRC%\SDKs\EATech\Apt\AptUpdate.cpp"
  echo "%SRC%\SDKs\EATech\Apt\AptMath.cpp"
  echo "%SRC%\SDKs\EATech\Apt\AptObjectIndex.cpp"
  echo "%SRC%\SDKs\EATech\Apt\AptSpriteMembersIndex.cpp"
  echo "%SRC%\SDKs\EATech\Apt\AptStringPool.cpp"
  echo "%SRC%\SDKs\EATech\Apt\AptTextFormatMembersIndex.cpp"
  echo "%SRC%\SDKs\EATech\Apt\AptTextMembersIndex.cpp"
  echo "%SRC%\SDKs\EATech\Apt\AptValueGCAllocator.cpp"
  echo "%SRC%\SDKs\EATech\Apt\AptValueGCPoolManager.cpp"
  echo "%SRC%\SDKs\EATech\Apt\DogmaAllocator.cpp"
  echo "%SRC%\SDKs\EATech\eajobs\bucket_list_node.cpp"
  echo "%SRC%\SDKs\EATech\eajobs\detail.cpp"
  echo "%SRC%\SDKs\EATech\eajobs\entrypoint.cpp"
  echo "%SRC%\SDKs\EATech\eajobs\event.cpp"
  echo "%SRC%\SDKs\EATech\eajobs\job.cpp"
  echo "%SRC%\SDKs\EATech\eajobs\job_instance_handle.cpp"
  echo "%SRC%\SDKs\EATech\eajobs\job_scheduler.cpp"
  echo "%SRC%\SDKs\EATech\eajobs\job_thread.cpp"
  echo "%SRC%\SDKs\EATech\eajobs\job_thread_parameters.cpp"
  echo "%SRC%\SDKs\EATech\eajobs\jobs.cpp"
  echo "%SRC%\SDKs\EATech\eajobs\local_backend.cpp"
  echo "%SRC%\SDKs\EATech\eajobs\reference_count.cpp"
  rem NOTE: the reconstructed EATech\eathread\* set (BrnEAThreadX360.cpp + eathread_*.cpp)
  rem is DELIBERATELY NOT linked -- it duplicates the forked vendor EAThread (eathread.obj/
  rem eathread_mutex.obj/eathread_semaphore_pc.obj/eathread_thread_pc.obj/eathread_x360align.obj)
  rem and causes LNK2005. Per the eathread-strategy decision we fork the vendor + add the
  rem X360-aligned overloads there, NOT swap to the reconstructed X360 set. Any EA::Thread
  rem symbol the Apt engine needs (RWMutex/ThreadLocalStorage) is served from the forked vendor.
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionDispatch.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreter.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterArith.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterBitwise.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterBranch.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterBuiltins.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterCompare.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterContext.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterControlOps.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterDefineLocal.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterDelete.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterEcmaOps.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterInterpHelpers.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterLogic.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterMemberOps.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterProtoOps.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterSetVariable.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterSpecialOps.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterParseStream.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterStackOps.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterStringOps2.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterUnary.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterValueOps.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterVarOps.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterVariable.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionQueue.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionRun.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptAnimationTarget.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptArray.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptCIH.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptCIHBehaviour.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptCIHMembers.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptCIHText.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptCIHNativeFunctionHelper.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptCIHNone.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptCharacter.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptCharacterAnimation.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptCharacterAnimationInst.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptCharacterHelper.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptCharacterInst.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptCharacterSpriteInstBase.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptCharacterTextInst.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptDate.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptDefine.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptDisplayList.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptDisplayListState.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptError.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptExtObject.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptFile.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptFileSavedInputState.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptFrameStack.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptGC.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptGlobal.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptGlobalExtensionObject.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptIntervalTimer.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptKey.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptLinker.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptLinkerThingy.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptListenerSlotListCIH.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptLoader.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptMathObj.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptMovie.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptMovieClip.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptNativeFunction.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptNativeHash.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptObject.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptPrototype.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptPseudoCIH.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptPseudoData.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptPseudoDisplayList.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptRenderItem.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptRenderItemAnimation.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptRenderItemButton.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptRenderItemCustomControl.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptRenderItemDynamicText.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptRenderItemLevel.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptRenderItemMorph.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptRenderItemShape.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptRenderItemSprite.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptRenderItemStaticText.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptRenderManagerItem.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptRenderManagerQueue.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptRenderTreeManager.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptRenderWalk.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptRenderingContext.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptSavedInputCheckpoints.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptScriptColour.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptScriptFunction1.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptScriptFunction2.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptScriptFunctionBase.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptScriptFunctionByteCodeBlock.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptSharedPtr.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptSingleListPolicy.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\StringAsVectorPolicy.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptSound.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptStage.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptStd\AptCXForm.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptString\EAString.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptTarget.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptTextFormat.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptValueFactory.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptValueWithHash.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptValue\AptBoolean.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptValue\AptExtern.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptValue\AptFloat.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptValue\AptInteger.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptValue\AptLookup.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptValue\AptNone.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptValue\AptRegister.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptValue\AptString.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptValue\AptStringObject.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptValue\AptValue.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptValue\AptValueConvert.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptValue\AptValueFindChild.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptValue\AptValueVector.cpp"
  rem NOTE the un-migrated Packages/Apt/2.00.00 remnants (AptSprite.cpp / AptString.cpp)
  rem stay OUT of the link: both are full duplicates of symbols already linked here
  rem (SpriteMembersIndex from EATech\Apt\AptSpriteMembersIndex.cpp; StringMembersIndex
  rem from the EATech AptValue\AptString.cpp above -- LNK2005-measured 2026-08-10). They
  rem also share the AptString.cpp basename, which silently CLOBBERS the EATech obj via
  rem /Fo"obj\" if ever re-added -- use a unique /Fo like renderengine_device.obj then.
  echo "%SRC%\SDKs\EATech\include\Apt\AptXml.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptXmlNode.cpp"
  echo "%SRC%\SDKs\EATech\include\NFSMix\MixerAllocator.cpp"
  echo "%SRC%\SDKs\EATech\include\NFSMix\NFSMixMap.cpp"
  echo "%SRC%\SDKs\EATech\include\NFSMix\NFSMixMapState.cpp"
  echo "%SRC%\SDKs\EATech\include\NFSMix\NFSMixMaster.cpp"
  echo "%SRC%\SDKs\EATech\include\NFSMix\NFSMixShape.cpp"
  echo "%SRC%\SDKs\EATech\include\Nicotine\DMixIO.cpp"
  echo "%SRC%\SDKs\EATech\include\Nicotine\IDynamicMixer.cpp"
  echo "%SRC%\SDKs\EATech\include\Nicotine\SnapshotChannel.cpp"
  echo "%SRC%\SDKs\EATech\include\Nicotine\SnapshotMixer.cpp"
  echo "%SRC%\SDKs\EATech\include\snd\CShortDestDecoder.cpp"
  echo "%SRC%\SDKs\EATech\include\snd\CSign16BigIntDecS16.cpp"
  echo "%SRC%\SDKs\EATech\include\snd\CSign16IntDecS16.cpp"
  echo "%SRC%\SDKs\EATech\include\snd\CSign24IntDecS16.cpp"
  echo "%SRC%\SDKs\EATech\include\snd\CSign24bIntDecS16.cpp"
  echo "%SRC%\SDKs\EATech\include\snd\CSign8IntDecS16.cpp"
  echo "%SRC%\SDKs\EATech\include\snd\CUnSign8IntDecS16.cpp"
  echo "%SRC%\SDKs\EATech\include\snd\sndo.cpp"
  echo "%SRC%\SDKs\EATech\rw\math\vpu\vecfloat.cpp"
  echo "%SRC%\SDKs\EATech\rw\math\vpu\vector2.cpp"
  rem  (SDKs/EATech/rw/math/vpu/vector3.cpp DROPPED 2026-08-18, wave Q5: it strong-defined the inline Vector3 float ctor and LNK2005s against the mounted collision TUs)
  echo "%SRC%\SDKs\EATech\rw\math\vpu\vector4.cpp"
  echo "%SRC%\SDKs\EATech\rwcollision\volume.cpp"
  echo "%SRC%\SDKs\EATech\rwcollision\volumelinequery.cpp"
  echo "%SRC%\SDKs\EATech\rwcore\filesys\asyncop.cpp"
  echo "%SRC%\SDKs\EATech\rwcore\filesys\device.cpp"
  echo "%SRC%\SDKs\EATech\rwcore\filesys\devicedriver.cpp"
  echo "%SRC%\SDKs\EATech\rwcore\filesys\handle.cpp"
  echo "%SRC%\SDKs\EATech\rwcore\filesys\manager.cpp"
  echo "%SRC%\SDKs\EATech\rwmovie\CRct.cpp"
  echo "%SRC%\SDKs\EATech\rwmovie\CTwoPassInfoList.cpp"
  echo "%SRC%\SDKs\EATech\rwmovie\CTwoPassStatsList.cpp"
  echo "%SRC%\SDKs\EATech\rwmovie\CWMVMBMode.cpp"
  echo "%SRC%\SDKs\EATech\rwmovie\ivideorenderer.cpp"
  echo "%SRC%\SDKs\EATech\rwmovie\videorenderable.cpp"
  echo "%SRC%\SDKs\EATech\rwmovie\vp6.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptRandom.cpp"
  echo "%SRC%\pc\gcm\renderengine\device.cpp"
  echo "%SRC%\pc\gcm\renderengine\texture.cpp"
  echo "%SRC%\pc\gcm\renderengine\texturestate.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\MoviePlayer\CgsMoviePlayer.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\MoviePlayer\CgsMoviePlayerCtor.cpp"
  echo "%SRC%\GameShared\GameClasses\Fonts\CgsFont.cpp"
  echo "%SRC%\GameShared\GameClasses\Fonts\CgsUnicode.cpp"
  echo "%SRC%\GameShared\GameClasses\Fonts\Resources\CgsFontResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\Font\CgsFontRenderer.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\CgsGuiFontCollection.cpp"
  echo "%SRC%\GameShared\GameClasses\Language\CgsLanguageManager.cpp"
  echo "%SRC%\GameShared\GameClasses\Language\Resources\CgsLanguageResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\Language\CgsLanguageManagerDebugComponent.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Render\CgsDebug3DImmediateRender.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\CgsRwRasterResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\CgsRwTextureStateResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\CgsMaterialStateResourceType.cpp"
  rem  The post-fx colour-cube (3D tint LUT) resource-type handler, resource type 0x2B. Added by
  rem  the step-10 tint wave together with its TypeRegistry::Register line in
  rem  CgsResourceTypeRegistration.cpp -- without it the boot log says
  rem    [bundle] UNREGISTERED resource type id 43 in 'PostFx/colourcubedictionary.bin'
  rem  and every colour cube in the game is refused. Defines the two virtuals the registration
  rem  TU leaves UNDEF (GetTypeID / GetSerialisedResourceDescriptor).
  echo "%SRC%\GameShared\GameClasses\RenderWare\CgsRwColourCubeResourceType.cpp"

  echo "%SRC%\GameShared\GameClasses\RenderWare\cross\CgsModelResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\Instances\CgsInstanceListResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\Instances\CgsInstance.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsEntryListResource.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptDataHeader.cpp"
  echo "%SRC%\SharedClasses\Gui\Flapt\BrnFlaptFile.cpp"
  echo "%SRC%\SharedClasses\Gui\Flapt\BrnFlaptFileResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourcePtr_BrnFlapt_FlaptFile.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceTypeRegistration.cpp"
  rem ---- bulk sweep: 128 reconstructed (done) TUs, linker-verified self-consistent ----
  echo "%SRC%\GameShared\GameClasses\Containers\CgsHash.cpp"
  echo "%SRC%\GameShared\GameClasses\Containers\CgsHash12.cpp"
  echo "%SRC%\GameShared\GameClasses\Containers\CgsHash16.cpp"
  echo "%SRC%\GameShared\GameClasses\Core\CgsID.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Controller\CgsDebugController.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Render\CgsDebugRenderStreamReader.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\Log\CgsLogCombined.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\Log\CgsLogFile.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\Log\CgsLogFileBuffered.cpp"
  echo "%SRC%\GameShared\GameClasses\Fsm\CgsFsm.cpp"
  echo "%SRC%\GameShared\GameClasses\Fsm\CgsScriptedState.cpp"
  echo "%SRC%\GameShared\GameClasses\Fsm\CgsLuaState.cpp"
  echo "%SRC%\GameShared\GameClasses\Fsm\CgsScriptedFsm.cpp"
  echo "%SRC%\GameShared\GameClasses\Fsm\CgsEvent.cpp"
  echo "%SRC%\GameShared\GameClasses\Fsm\Resources\CgsLuaCodeResource.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsBinaryFileResource.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\State\CgsGuiStateMachine.cpp"
  echo "%SRC%\GameShared\GameClasses\Geometric\Primitives\PolygonSoup\CgsPolygonSoupList.cpp"
  rem  ?????? 2026-08-10 (fill-worker wave) -- PURE MOUNT GAP. These TUs were reconstructed long ago
  rem  and never once compiled into anything; all are prerequisites of the triangle-cache FILL
  rem  worker (PolygonSoupTesterJob), so they are mounted now to enforce the link closure over
  rem  them BEFORE the worker lands rather than after:
  rem    CgsLineTests.cpp          -- TestAxisAlignedBoxAxisAlignedBox @0x82812460, the per-leaf
  rem                                 filter PolygonSoupTesterJob::FillTriangleCache @0x82915FD0 runs.
  rem    CgsSimpleDataStreamConsumer.cpp  -- ReadCo, the consumer side of the fill stream...
  rem    CgsDataStreamCommandReader.cpp   -- ...and DataStreamCommandReader::ReadCom @0x82867920,
  rem                                 which ReadCo tail-calls. BODIED all along, never mounted --
  rem                                 the mount is what found it (LNK2019, invisible to every gate).
  rem    CgsReadOnlyObjectCache_PolygonSoupLeafNode.cpp -- the leaf-node cache instantiation
  rem                                 (Construct @0x829170F8 / Release @0x829172D0) FillTriangleCache
  rem                                 walks the query results through.
  rem  ????????? 2026-08-11 (THE EXTRACTOR wave). The "NOT MOUNTED" note that stood here -- two hard
  rem  LNK2019s from CgsPolygonSoupTests.cpp for PolySoupCopyTriangleBufferIntoTriangle4 and
  rem  Triangle4::AssertIsValid -- is RESOLVED on both counts and the TU is mounted below.
  rem  AssertIsValid landed with CgsTriangle4.cpp last wave; Copy is bodied this wave.
  echo "%SRC%\GameShared\GameClasses\Geometric\Intersection\CgsLineTests.cpp"
  echo "%SRC%\GameShared\GameClasses\Memory\DataStream\CgsSimpleDataStreamConsumer.cpp"
  echo "%SRC%\GameShared\GameClasses\Memory\DataStream\CgsDataStreamCommandReader.cpp"
  echo "%SRC%\GameShared\GameClasses\Containers\CgsReadOnlyObjectCache_PolygonSoupLeafNode.cpp"
  echo "%SRC%\GameShared\GameClasses\Geometric\Primitives\PolygonSoup\CgsPolygonSoupListResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\Geometric\Primitives\PolygonSoup\CgsPolygonSoupListSpatialMap.cpp"
  rem  Spatial-partition wave 2026-08-10: BuildSpacialPartition @0x82841740 (2,255) and the
  rem  two types it carves, plus the layout gate MOUNTED with the code it guards.
  rem  ??? 2026-08-10 (fill-worker wave 2): PURE MOUNT GAP again -- both bodied long ago, both
  rem  never linked. FillTriangleCache needs Sphere::GetPosition @0x825B27F8 /
  rem  Sphere::GetRadius @0x825BD1F8 and AxisAlignedBox::Set @0x823A6108 to turn the fill
  rem  command's cache sphere into the box the query runs on. Found by the LINK, as always.
  echo "%SRC%\GameShared\GameClasses\Geometric\Primitives\CgsSphere.cpp"
  rem  2026-08-19 (wave Q7, cluster box): Box::IsValid @0x825BEB80 (264) + both BoxOverlappingTest overloads
  rem  (@0x825BEFA0, @0x825BF090) + the inlined GetBoxExtentsAlongAxis. Box::Set is an inline in CgsBox.h that
  rem  now CALLS IsValid (the console's streamed validity assert restored), and CgsBox.h is reached by 56 TUs
  rem  including the mounted CgsPrimitivePairListBuilder.cpp -- without this line every one of them is an
  rem  LNK2019 that cl /c cannot see.
  echo "%SRC%\GameShared\GameClasses\Geometric\Primitives\CgsBox.cpp"
  echo "%SRC%\GameShared\GameClasses\Geometric\Primitives\CgsAxisAlignedBox.cpp"
  echo "%SRC%\GameShared\GameClasses\Geometric\Primitives\CgsAxisAlignedBox4.cpp"
  echo "%SRC%\GameShared\GameClasses\Geometric\Primitives\PolygonSoup\CgsPolygonSoupListSpatialMap_Build.cpp"
  echo "%SRC%\GameShared\GameClasses\Geometric\Primitives\PolygonSoup\CgsPolygonSoupSpacialNode_embed_check.cpp"
  rem  =============================================================================================
  rem  ????????? 2026-08-10 (fill-worker wave 2) -- THE TRIANGLE-CACHE FILL WORKER, front half.
  rem  This is the FIRST EA::Jobs dispatch this PC port has ever performed (before it, `grep
  rem  AddTree` outside SDKs/EATech/eajobs found ZERO call sites). RunFillTriangleCacheStream
  rem  @0x82810D38 is no longer a gate; it wires a real batch, a real descriptor and a real job
  rem  and runs the entry inline (FLAG PC-platform leaf -- there is no JobScheduler singleton on
  rem  PC, CgsHardwareInitPC.cpp:40; same precedent as CgsLooseOctree::StartFrustumTestJobs).
  rem    PolygonSoupTester.cpp     -- PolygonSoupTesterEntry @0x829157B8 (80)
  rem    PolygonSoupTesterJob.cpp  -- Execute @0x82915930 (107) / ExecuteFillTriangleCacheStream
  rem                                 @0x82915D88 (145) / FillTriangleCache @0x82915FD0 (219) /
  rem                                 AllocateMemory @0x82916B98 (99) / RunBoxQuery @0x82916D28
  rem                                 (46) / LoadPrimitive @0x82916AB8 (8)
  rem    CgsPolygonSoupListSpatialMap_Query.cpp -- ??? RunJobQuery @0x82844680 (316). NOT the
  rem                                 RunQuery @0x82843A80 every earlier costing named: the job
  rem                                 side takes its ping/pong buffers as a parameter so the map
  rem                                 stays const. X360 export HOLE; name + full signature
  rem                                 recovered from the PS3 mangle @0xB63F20.
  rem  ????????? 2026-08-11 -- THE EXTRACTOR. The gate named on this line since the fill worker landed
  rem  is GONE: ExtractTriangle4ListIntersectingSphere @0x82844C80 (602) +
  rem  PolygonSoupPoly::LoadEdgeCosines @0x8283A120 (534) + TestSphereTriangle4SOA @0x8283FD50
  rem  (144) + PolySoupCopyTriangleBufferIntoTriangle4 @0x82839690 (97) +
  rem  UnpackPolygonSoupVertices @0x8283B480 (40) are all bodied, and GetPolygon/GetVertex
  rem  (29+29, CgsPolygonSoup.cpp) + Add/FinishToTriangleBuffer (68+49, CgsPolygonSoupTests.cpp)
  rem  were PURE MOUNT GAPS -- bodied long ago, never once on the link.
  rem  ??? It was not "1,475 instructions of dense VMX": the extractor itself is a loop driver, and
  rem  every one of the twelve vector constants those five functions load is ZERO in the image
  rem  because they are built at runtime by C++ dynamic initialisers (0x82C6DA98..0x82C6DC10).
  rem  Each was resolved through its writer, not guessed.
  rem  =============================================================================================
  echo "%SRC%\GameShared\GameClasses\Geometric\Primitives\PolygonSoup\CgsPolygonSoup.cpp"
  echo "%SRC%\GameShared\GameClasses\Geometric\Primitives\PolygonSoup\CgsPolygonSoupPoly.cpp"
  echo "%SRC%\GameShared\GameClasses\Geometric\Intersection\CgsPolygonSoupTests.cpp"
  rem  ?????? 2026-08-14 (walls leg 2): THE SPHERE CONTACT KERNEL --
  rem  IntersectTriangle4Sphere_HackyBurnoutVersion @0x8283D2E0 (497). Home TU per the DecFIGS
  rem  dwarfdump (CgsTriangleSphere.cpp:715). Derived by decoding the 497 words from the image
  rem  (78 IDA "+32" operand misprints corrected) and executing them numerically; the scalar
  rem  lowering fuzz-matched that execution 2600/2600 (see wallsleg2 log). KF_MIN_PLANE_DIST =
  rem  0.001f splat (dynamic-init: X360 sub_82C6DCF0, PS3 initializer identical). The sibling
  rem  IntersectTriangle4Sphere (DWARF :490, PS3 @0xB59F6C) is NOT reconstructed -- no caller
  rem  on the vehicle path.
  echo "%SRC%\GameShared\GameClasses\Geometric\Intersection\CgsTriangleSphere.cpp"
  echo "%SRC%\GameShared\Jobs\PolygonSoupTester\PolygonSoupTesterJob.cpp"
  echo "%SRC%\GameShared\Jobs\PolygonSoupTester\PolygonSoupTester.cpp"
  echo "%SRC%\GameShared\GameClasses\Geometric\Primitives\PolygonSoup\CgsPolygonSoupListSpatialMap_Query.cpp"
  rem  ?????? ODR FORK #2 RETIRED. CgsTriangle4.cpp was reconstructed long ago (GetAOSTriangle
  rem  @0x825B2808, AOSTriangle::IsValid @0x825BD208) and never mounted, which is the ONLY reason
  rem  the tree believed Triangle4::AssertIsValid had no body. It does: X360 0x825BD808 (46), plus
  rem  AOSTriangle::AssertIsValid @0x825BD648 (112), both landed this wave. With the TU mounted the
  rem  `namespace Triangle4 { int AssertIsValid(void*); } = { return 0; }` fork in
  rem  CgsTriangleList.h / CgsTriangleList_embed_check.cpp is deleted and CgsTriangleList.cpp
  rem  validates for real for the first time.
  echo "%SRC%\GameShared\GameClasses\Geometric\Primitives\CgsTriangle4.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\Collision\Primitives\CgsTriangleList.cpp"
  rem  ...and the registration leg they unblock. BOTH of these were fully reconstructed
  rem  already and had simply never been on the link (mount gap, not a reconstruction gap).
  echo "%SRC%\GameShared\GameClasses\SceneManager\TriangleCollision\CgsTriangleCollisionManager.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\TriangleCollision\BaseEventQueue_InEventAddPolySoupList_GetEvent.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\CgsModel.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\CgsShaderConstantHashTable.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\CgsShaderConstants.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\Dispatch\parameter.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\Dispatch\parametersemantic.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\CgsGuiModuleIO.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\CgsGuiModuleIO_InputBuffer.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\CgsEventInterpreterModuleIO.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\CgsModelModuleIO.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\Resources\CgsAptDataHeaderType.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\Resources\CgsGuiGeometryObjects.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\Resources\CgsGuiHudMessage.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\Resources\CgsGuiHudMessageList.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\Resources\CgsGuiHudMessageListType.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\Resources\CgsGuiPopupResource.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptAnimData.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptInterpolator.cpp"
  rem ---- the CgsAptAnim* container-instantiation TUs: reconstructed in the flapt wave ----
  rem ---- but never registered here (the standing "flapt .cpp need adding" flag).      ----
  rem ---- PARKED (link-measured 2026-08-10, honest out-of-tree): CgsAptAnimator.cpp    ----
  rem ---- (needs AnimChannel::Stop + AnimData::GetChannelData -- no reconstructed      ----
  rem ---- bodies anywhere in src) and CgsAptAnimChannel.cpp (needs the Interpolator    ----
  rem ---- SetInterpolator/Update/Reset virtuals; CgsAptInterpolator.cpp only has       ----
  rem ---- GetCurrentValue). Mount them when those bodies land.                          ----
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptAnimChannelArray6.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptAnimChannelDataArray2.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptAnimChannelDataArray6.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptAnimDataAnimatorChannelArray6.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptAnimDataAnimData.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptAnimDataArray2.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\CustomRenderer\CgsCustomRenderer.cpp"
  echo "%SRC%\GameShared\GameClasses\Memory\DataStream\CgsDataStreamCommandPoster.cpp"
  echo "%SRC%\GameShared\GameClasses\Memory\DataStream\CgsDataStreamResultPoster.cpp"
  echo "%SRC%\GameShared\GameClasses\Memory\DataStream\CgsDataStreamResultReader.cpp"
  echo "%SRC%\GameShared\GameClasses\Memory\MemoryMap\CgsMemoryMap.cpp"
  echo "%SRC%\GameShared\GameClasses\Network\Packeting\BitStream\CgsBitStream.cpp"
  echo "%SRC%\GameShared\GameClasses\Network\Packeting\BitStream\CgsFloatQuantiser.cpp"
  echo "%SRC%\GameShared\GameClasses\Network\Packeting\BitStream\CgsIntQuantiser.cpp"
  echo "%SRC%\GameShared\GameClasses\Network\Packeting\BitStream\CgsFloatQuantiser.cpp"
  echo "%SRC%\GameShared\GameClasses\Network\Packeting\BitStream\CgsSmartBitStream.cpp"
  echo "%SRC%\GameShared\GameClasses\Network\Packeting\Messages\CgsMessage.cpp"
  echo "%SRC%\GameShared\GameClasses\Network\Packeting\Messages\CgsNewHostMessage.cpp"
  echo "%SRC%\GameShared\GameClasses\Network\Packeting\Messages\CgsSignalMessage.cpp"
  echo "%SRC%\GameShared\GameClasses\Network\Packeting\Messages\CgsTestConnectionMessage.cpp"
  echo "%SRC%\GameShared\GameClasses\Network\Players\CgsConnectionStatusMessage.cpp"
  echo "%SRC%\GameShared\GameClasses\Network\Players\CgsPlayerManager.cpp"
  echo "%SRC%\GameShared\GameClasses\Network\Players\CgsPlayersConnectionManager.cpp"
  echo "%SRC%\GameShared\GameClasses\Network\Time\CgsStartTimeMessage.cpp"
  echo "%SRC%\GameShared\GameClasses\Network\Time\CgsSyncTimeMessage.cpp"
  echo "%SRC%\GameShared\GameClasses\Numeric\CgsPerlinNoise.cpp"
  echo "%SRC%\GameShared\GameClasses\Numeric\CgsVPUConstantInitializers.cpp"
  echo "%SRC%\GameShared\GameClasses\Physics\CgsCollisionMeshData.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\PS3\CgsRwMaterialCRC32ResourceTypePS3.cpp"
  rem  world-pixels wave: homes RwRenderableResourceType::FixUpRenderableMesh (@0x828A8968),
  rem  which the newly-overridden RwRenderableResourceType::FixUp calls per mesh.
  echo "%SRC%\GameShared\GameClasses\RenderWare\PS3\CgsRwRenderableResourceTypePS3.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\PS3\materialstates\CgsRwShaderParameterResourceTypePS3.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\cross\CgsClusteredMeshResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\cross\CgsKdTreeResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\cross\CgsMaterialTechniqueResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\cross\CgsRwRenderableResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsSceneManagerDebugComponent.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\Collision\ContactGenerator\JobDescription\CgsPrimitiveListWithTriangleListJobDesc.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\Collision\ContactGenerator\JobDescription\CgsPrimitivePairListJobDesc.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\Collision\ContactGenerator\JobDescription\CgsSphereListWithSphereListJobDesc.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\Collision\ContactGenerator\JobDescription\CgsSphereListWithTriangleListJobDesc.cpp"
  rem  swept leg (2026-08-16): the NON-stream swept descriptor's Prepare @0x828103E0 -- an
  rem  export HOLE recovered from the image bytes. Needed by the swept stream arm, which builds
  rem  one of these per command.
  echo "%SRC%\GameShared\GameClasses\SceneManager\Collision\ContactGenerator\JobDescription\CgsSweptSphereListWithTriangleListJobDesc.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\Contactgen\CgsSceneSweeperDebugComponent.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\TriangleCollision\CgsTriangleCollisionDebugComponent.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\Zones\Resources\ZoneListResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\Zones\Zone.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\CgsSoundUtils.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\CgsMemBase.cpp"
  rem helpers and stay gate-only. Mounted 2026-08-25 faithful-audio-engine phase A1.
  rem SetAllocator; the handle-family TUs have unreconstructed cross-TU template
  rem Csis SDK -- only CsisSystem is mounted: the RWAC init needs Lock/Unlock/Init/
  echo "%SRC%\SDKs\Csis\CsisSystem.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Logic\CgsMicrophone.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Logic\CgsStateManager.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Logic\CgsEnvironment.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Logic\CgsVoiceHierarchy.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Logic\CgsVoiceHierarchyResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\AEMS\CgsAemsFactory.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\CgsCommon.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\CgsRegistry.cpp"
  rem ---- audio-faithfulness wave 3: the canonical Playback Object home. The CgsContent.h
  rem  Object fold makes its consumers reference the out-of-line asserting Object dtor 0x826916F0.
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\CgsObject.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Logic\CgsSoundLogicModule.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\CgsEnvironment.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\Module\CgsSoundPlaybackModule.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\Module\CgsSoundPlaybackModuleIO.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\RWAC\CgsGenericRwacFactory.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\CgsFactory.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\CgsVoice.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\CgsContentSpec.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\Plugins\Streaming\internal\sndplayer1.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\Plugins\Streaming\internal\sndplayer1shared.cpp"
  rem  CgsGainArrayPlugin.cpp -- the game-side JGA0 gain-array plug-in; its three
  rem  callbacks are bodied and its descriptor registers with the RWAC pass.
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\Plugins\GainArray\CgsGainArrayPlugin.cpp"
  rem  GinsuPlayer.cpp -- the granular engine-sound synthesizer Gns0: the car-engine
  rem  audio heart. Source-stage plug-in plus its GinsuSynthData content decoder.
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\Plugins\Ginsu\GinsuPlayer.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\RWAC\CgsSnrResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\Splicer\CgsSplicerFactory.cpp"
  rem  AEMS-cascade slice 3: the SplicerFactory dtor TU + the SpliceManager home -- the
  rem  stage-3 create [3/3] constructs the trailing-arena manager.
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\Splicer\CgsSplicerFactoryDtor.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\Splicer\SpliceManager.cpp"
  echo "%SRC%\GameShared\GameClasses\System\AttribSys\CgsAttribSysSchemaResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\System\AttribSys\CgsAttribSysVaultResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\World\Resources\CgsWorldPainter2DResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\System\AttribSys\CgsAttribSysVaultAllocator.cpp"
  echo "%SRC%\GameShared\GameClasses\System\FileSystem\CgsDeviceManager.cpp"
  echo "%SRC%\GameShared\GameClasses\System\FileSystem\CgsFileLog.cpp"
  echo "%SRC%\GameShared\GameClasses\System\FileSystem\Devices\CgsRemapDevice.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceDebugComponent.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceHandle.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceIdListResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourcePtr.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsTextFileResource.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\PoolModuleStates\CgsBaseDefragPoolModuleState.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Timer\CgsTimer.cpp"
  rem pace wave (b5 dev 261a5303, upstream) landed CgsSystem::FrameInterpolation callers in BrnGameModule/BrnWorldModule without the mount; added here (cars step 1c)
  echo "%SRC%\GameShared\GameClasses\System\Timer\CgsFrameInterpolation.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Timer\CgsTimerStatusInterface.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Timer\CgsTimerRequestInterface.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Timer\PS3\CgsDateAndTimePS3.cpp"
  echo "%SRC%\GameShared\GameClasses\World\CgsWorldMap2D.cpp"
  echo "%SRC%\GameShared\Jobs\Relocator\CgsRelocator.cpp"
  echo "%SRC%\GameSource\AttribSys\Generated\codegen.cpp"
  echo "%SRC%\GameSource\Director\Camera\BrnCameraEffects.cpp"
  echo "%SRC%\GameSource\Director\Camera\Utils\BrnDebugController.cpp"
  echo "%SRC%\GameSource\Director\MomentController\BrnMomentParameterBank.cpp"
  echo "%SRC%\GameSource\Director\Utils\BrnAbstractPool.cpp"
  echo "%SRC%\GameSource\Director\Utils\BrnVehicleRef.cpp"
  rem ---- DirectorModule mount (2026-07-29, DJ fly-by campaign) -------------------------
  rem  The director spine: module -> MainDirector -> Arbitrator -> AttractMode ->
  rem  BehaviourManager -> BehaviourRoadRunner -> CameraFinaliser -> OutputBuffer.
  rem  NOTE: %SRC%\GameSource\Director\BrnDirectorModule.cpp is the REVERTED raw-offset
  rem  duplicate and must NOT be mounted -- the live TU is the one under DirectorModule\.
  echo "%SRC%\GameSource\Director\DirectorModule\BrnDirectorModule.cpp"
  echo "%SRC%\GameSource\Director\DirectorModule\BrnDirectorModuleIOOutputBuffer.cpp"
  echo "%SRC%\GameSource\Director\DirectorModule\BrnDirectorModuleIOSceneQuery.cpp"
  echo "%SRC%\GameSource\Director\BrnMainDirector.cpp"
  rem  MOUNTED 2026-08-02 (camera parameter-chain wave). BrnDirectorVehicleInputInterface --
  rem  the world -> director "a car entered the simulation" seam (Construct /
  rem  GetNewVehicleEventQueue / NewVehicle @0x822CBA90). It is the first link that actually
  rem  carries data toward the two SHARED gameplay cameras' Parameters::mbIsValid, which is
  rem  the byte their whole Update body sits behind. Self-contained: the queue template is
  rem  header-only and the only other dependencies are the already-mounted generated
  rem  Attrib::Gen classes (burnoutcarasset / camerabumperbehaviour / cameraexternalbehaviour,
  rem  all header-inline) plus Attrib::FindCollection / RefSpec::GetCollection, which
  rem  attribsupport.cpp already provides.
  echo "%SRC%\GameSource\Director\SharedIO\BrnDirectorVehicleInputInterface.cpp"
  rem  MOUNTED 2026-08-01 (junkyard chain wave). BrnDirector::GameState -- the director's
  rem  per-event snapshot. MainDirector now carries it as a REAL named member (it was three
  rem  opaque byte spans), so GameState::Clear @0x82218930 finally runs from
  rem  MainDirector::Construct and GameState::ResetPerFrameData runs every frame from
  rem  ProcessInputQueue. Self-contained: DataJournal<T,N> is header-only and the TU's only
  rem  other dependencies are memset/memcpy. Measured link cost: ZERO new unresolved.
  echo "%SRC%\GameSource\Director\DirectorModule\BrnDirectorGameState.cpp"
  rem  MOUNTED 2026-08-01. This TU was the reverted raw-console-offset ctor over a LOCAL
  rem  re-declaration of the class; the shot-group wave rewrote it against named members and
  rem  this wave added the real DirectorResourceManager::Prepare @0x8225CA08 (the 65
  rem  shot-group slot builds + the CameraVault register). Its DirectorLinkStubs `return true`
  rem  stub is deleted with it. It carries five ICE-cone leaves (GetKeyAnim x2 /
  rem  GetShakeTakes / GetICEAuthor / GetKeyAnimFromGuid reach ICEWrapper + ICEAuthor +
  rem  ICEList); those resolve through the existing Director/ICE link stubs.
  echo "%SRC%\GameSource\Director\BrnDirectorResourceManager.cpp"
  rem  MOUNTED 2026-08-01 (ICE-anim transform wave). ?????? ICEWrapper::Prepare @0x8253DD90 -- a
  rem  FILE SPLIT out of the un-mounted BrnDirectorICEWrapper.cpp (same pattern as
  rem  BrnCameraTweakerConstruct.cpp above), because that TU still costs the link two
  rem  unresolved externals (ICEManager::GetCameraTake / ICECameraMover::Construct) that
  rem  Prepare itself does not need. This retires the `return true` stub that was the ONLY
  rem  thing standing between the ICE take evaluator and its element schedules: Prepare's
  rem  stage 0 is the whole image's single caller of ICE::InitICEDescriptions(), so without it
  rem  gaICEElementChannels stayed empty, ICETake::SetParameter evaluated zero elements and
  rem  every authored ICE camera value read 0. Self-contained: it reaches only
  rem  ICEElementDescription::Prepare + InitICEDescriptions, both already in the link via
  rem  ICEData.cpp / ICEDataEnums.cpp. Measured link cost: ZERO new unresolved.
  echo "%SRC%\GameSource\Director\BrnDirectorICEWrapperPrepare.cpp"
  echo "%SRC%\GameSource\Director\Camera\BrnCameraFinaliser.cpp"
  echo "%SRC%\GameSource\Director\Camera\BrnBehaviourManager.cpp"
  echo "%SRC%\GameSource\Director\Camera\Behaviours\Behaviour.cpp"
  echo "%SRC%\GameSource\Director\Camera\Behaviours\BrnBehaviourRoadRunner.cpp"
  rem The two SHARED gameplay cameras SharedCameraContainer::Prepare allocates. Mounted
  rem 2026-07-29 with their RE-BASE onto Camera::Behaviour: they now carry real virtuals
  rem (Construct/Prepare/GetName, + the external's SetParameters), so their vtables need a
  rem home. Before the re-base they were non-polymorphic offset slices and placement-new
  rem installed no vtable -- BehaviourHelper::Prepare's slot-0 dispatch then faulted.
  echo "%SRC%\GameSource\Director\Camera\Behaviours\BrnBehaviourGameplayBumper.cpp"
  echo "%SRC%\GameSource\Director\Camera\Behaviours\BrnBehaviourGameplayExternal.cpp"
  rem  ---- 2026-08-01, SEVENTH PASS: the BehaviourInterpolate ODR reconcile ------------------
  rem  BrnBehaviourManager.h used to carry a SECOND definition of BehaviourInterpolate -- no
  rem  base, no members, sizeof == 1 -- and because that header is the one every arbitrator
  rem  state includes, the slice was what the whole tree saw while the real home
  rem  (Behaviours/BrnBehaviourInterpolate.h) sat unreachable behind a C2011. Six symbols could
  rem  never be closed because there were no members to write. The slice is retired.
  rem  Mounting the real TU is FREE (0 new unresolved) and it makes AllocateBehaviour<
  rem  BehaviourInterpolate> book a bucket for the real size instead of for one byte.
  echo "%SRC%\GameSource\Director\Camera\Behaviours\BrnBehaviourInterpolate.cpp"
  rem ---- camera-blend in-between wave (2026-08-20): THE RAMP. BehaviourInterpolate used to
  rem  CUT at t == 1 because its mInterpolator was a 4-byte opaque stand-in. These two TUs are
  rem  the real evaluator (CameraInterpolationController::Update @0x822513D8 plus the whole
  rem  rotate-about-pivot family) and the remembered-axis Interpolater the blends share.
  echo "%SRC%\GameSource\Director\Shots\ShotControllers\BrnCameraInterpolationController.cpp"
  echo "%SRC%\GameSource\Director\Camera\Utils\BrnInterpolater.cpp"
  rem (Each cam's Parameters::Serialise<S> visitor stays OUT of the link, in its own
  rem  *Parameters.cpp sibling -- it drags the three camera-tunings serialisers in and none
  rem  of them is on the runtime director path.)
  echo "%SRC%\GameSource\Director\Arbitrator\BrnDirectorArbitrator.cpp"
  echo "%SRC%\GameSource\Director\Arbitrator\BrnDirectorArbitratorState.cpp"
  echo "%SRC%\GameSource\Director\Arbitrator\BrnDirectorArbitratorStateContainer.cpp"
  echo "%SRC%\GameSource\Director\Arbitrator\BrnDirectorArbitratorSharedCameraContainer.cpp"
  rem  MOUNTED 2026-08-02 (camera parameter-chain wave). BehaviourPassengerCam's four REAL
  rem  virtuals (Construct/Update/Release/GetName, 57 lines, only CgsAssert). Needed because
  rem  BrnBehaviourManager.cpp:965's explicit AllocateBehaviour<BehaviourPassengerCam>() now
  rem  binds to the DWARF-verbatim class instead of the stale 0x18-byte
  rem  BrnBehaviourPassengerCam.h slice, so it emits a vtable. Its two declaration-only
  rem  virtuals (Prepare/SetupTweaker) are in DirectorLinkStubs.cpp.
  echo "%SRC%\GameSource\Director\Camera\Behaviours\BehaviourPassengerCam.cpp"
  rem ---- EIGHTH PASS (2026-08-01): the camera-family closure set. -----------------------
  rem  Measured against the object list DERIVED FROM THIS BAT, not by scanning
  rem  build\game\obj -- that directory held 43 STALE objects from TUs no longer on the
  rem  source list (including all three camera TUs), so any measurement that scans the
  rem  directory silently treats unmounted code as linked. Scanning it, the camera TUs
  rem  appear to open ONE symbol; the true figure was 13. Tooling: scratchpad\ice5_list.py
  rem  (bat -> object list, prints the stale set) and ice5_net.py (closes/opens diff).
  rem  These four each open ZERO after their own leaves were bodied in place:
  echo "%SRC%\SDKs\Packages\ICE\ICECameraSpaceHandler.cpp"
  echo "%SRC%\SDKs\Packages\ICE\ICEAuthorTakeOps.cpp"
  echo "%SRC%\GameSource\Director\DirectorModule\BrnDirectorModuleDebugPrinter.cpp"
  echo "%SRC%\GameSource\Director\BrnDirectorResourceManagerICE.cpp"
  rem  BrnDirectorEffectTrigger.cpp is NOT mounted yet, deliberately. It now DOES define
  rem  Camera::EnsureEffectIsPlaying @0x821F2720 (the note further down claiming otherwise
  rem  is STALE), but mounting it costs two REAL unresolved externals --
  rem  EffectInterface::HookExists and RegisterStartingBackgroundEffectWithName, both
  rem  declaration-only in BrnDirectorEffectTrigger.h with no body anywhere in the tree.
  rem  They are reached only by BackgroundEffectRequest::RegisterAndUpdateRequest, which is
  rem  off the camera path. The camera TUs are not mounted either, so EnsureEffectIsPlaying
  rem  is not needed for today's link: mount this TU together with them, once those two
  rem  leaves are recovered from asm. Bodying them by guess would have been the wrong trade.
  rem      %SRC%\GameSource\Director\Utils\BrnDirectorEffectTrigger.cpp
  rem  Adds ZERO new unresolved: every callee is a header inline and
  rem  mRotationController.Construct() resolves against the existing DirectorLinkStubs symbol.
  echo "%SRC%\GameSource\Director\Camera\Behaviours\BrnBehaviourRotateAboutVehicle.cpp"
  rem  NOT mounted, deliberately -- these two hold the blocked bodies (SaveTake's
  rem  ICEFileHandler::FileClose costs +5 as the sole EA::GameTalk user; the ICE-wrapper
  rem  getters need MakeICEMovieId / GetICETakeData / GetShakeGroup):
  rem      %SRC%\SDKs\Packages\ICE\ICEAuthorSaveTake.cpp
  rem      %SRC%\GameSource\Director\BrnDirectorResourceManagerICEWrapper.cpp
  rem  ONLY the attract-mode state is mounted -- it is the DJ fly-by's own state, and the one
  rem  the arbitrator drives on this path. The other nine states (CrashMode / CrashNav /
  rem  DriveThru / OnlineCarSelect / OnlineRaceIntro / PostEvent / RaceIntro / RankUp /
  rem  Roaming) are RECONSTRUCTED but each drags a different un-landed sub-system with it
  rem  (ICEMoviePlayer, MomentSelector, BehaviourIceAnim, BehaviourInterpolate, the
  rem  DirectorResourceManager shot-group getters, the Attrib shot vault, ...) -- mounting all
  rem  ten took the link from 47 to 137 unresolved externals, most of them functions that
  rem  return REFERENCES and therefore cannot be honestly stubbed. Their vtables are stubbed
  rem  in DirectorLinkStubs.cpp instead (void/bool/const char* only), so the state container
  rem  still builds and the arbitrator can still refuse to enter them.
  rem  DELETE-WHEN: each state's own sub-system lands; mount the state and drop its stubs.
  echo "%SRC%\GameSource\Director\Arbitrator\States\BrnArbStateAttractMode.cpp"
  rem ---- NINTH PASS (2026-08-01): ArbStateRoaming -- THE DIRECTOR'S ENTRY GATE ------------
  rem  ??? ArbStateRoaming::Update @0x822643A0 is now WRITTEN (it did not exist anywhere in the
  rem  tree, and BrnArbStateRoaming.h deliberately omitted the override, so vtable slot 2 fell
  rem  through to ArbitratorState::Update's empty body -- meState froze at E_STATE_PREPARING
  rem  for the whole session and ProcessPossibleStateChanges, the ONLY writer of
  rem  E_STATE_CHANGING_TO_CAR_SELECT, was never called). Its four LNK2005 stubs are gone from
  rem  DirectorLinkStubs.cpp.
  rem  ?????? BrnArbStateRoaming.cpp DID NOT COMPILE before this wave (its Construct called a
  rem  two-argument MomentSelector::AddMoment that does not exist and its Prepare passed a
  rem  GameState where a BehaviourManager& is required) -- the ledger said `reviewed`.
  rem  MEASURED with scratchpad\ice5_list.py + ice5_net.py against the object list DERIVED FROM
  rem  THIS BAT: these four together are NET +0 unresolved. The order matters --
  rem  BrnArbStateRoaming alone is +7, +MomentSelector/+MomentController/+EffectTrigger is +4,
  rem  and the last 4 (MomentController::NewMoment, MomentHandle::Release,
  rem  MomentSelector::Update, SelectBestMomentWithExclusion) are the GROUP F stubs at the foot
  rem  of DirectorLinkStubs.cpp, which is where the moment sub-system's DELETE-WHEN lives.
  echo "%SRC%\GameSource\Director\Arbitrator\States\BrnArbStateRoaming.cpp"
  rem  ---- CRASH-CAMERA WAVE (2026-08-29): THE CRASH CAMERA ITSELF. -------------------------
  rem  BrnArbStateCrashing.cpp is E_STATE_CRASHING -- the state ArbStateRoaming ENTERS on a
  rem  crash (it only TESTS crash mode). Its container slot was
  rem  `class ArbStateCrashing : public ArbitratorState {};`, an empty shell whose inherited
  rem  Update never wrote meState and had no exit edge, which is why every crash kept the
  rem  ordinary chase camera and never slowed down.
  rem  ==> IT IS ATOMIC WITH MainDirector::ProcessInputQueue's mbCrashActive leg, in the same
  rem  b5-decomp commit. Never mount one without the other: the writer alone hands the first
  rem  crash to the shell and freezes the camera for the rest of the session.
  rem  BehaviourSpirallingDeathcam.cpp comes with it: the crash camera allocates the
  rem  spiralling deathcam when the player has been totalled, so its SetParameters /
  rem  Start / Parameters::Construct all become live symbols. MEASURED mount cost: zero
  rem  new unresolved -- that TU includes only its own header plus BrnLooker.h and
  rem  BrnCameraShake.h, both header-inline.
  rem  ??? BrnMomentBystanderSeesAction.cpp is deliberately NOT mounted with it, although
  rem  ArbStateCrashing DOES register BYSTANDER_SEES_ACTION as one of its four crash
  rem  moments. MEASURED: mounting it opens NINE unresolved externals of its own -- seven
  rem  `detail::MomentSharedInfo_*` free-function shims that are declared and never
  rem  defined, plus BehaviourParameterBank::GetBystanderCam{,Close}MomentParams. That is
  rem  the same shim disease BehaviourBystanderCam.cpp has. Its ONE function this state
  rem  needs (SetPerceivedDistanceModificationFactor) is trap-stubbed in
  rem  DirectorLinkStubs.cpp GROUP F instead, with the DELETE-WHEN there.
  echo "%SRC%\GameSource\Director\Arbitrator\States\BrnArbStateCrashing.cpp"
  echo "%SRC%\GameSource\Director\Camera\Behaviours\BehaviourSpirallingDeathcam.cpp"
  rem  ---- ...AND THE SIXTH BREAK: THE PLAYER TRACKER (2026-08-29). ------------------------
  rem  BrnDirectorVehicleTracker.cpp mounts here, and MainDirector::PreSceneQueryUpdate now
  rem  actually CALLS VehicleTracker::Update (X360 line 5 of its guarded body, gated until now).
  rem  ==> IT IS THE SLOW MOTION'S DATA SOURCE. ImpactSlomoController::Update decides whether to
  rem  start a burst from the tracked car's LINEAR-VELOCITY JOURNAL alone, and that journal is
  rem  written nowhere else. MEASURED with the whole rest of the crash chain already landed: a
  rem  forced player crash held mbCrashing for 900+ frames and the sim scale never left 1.0.
  rem  Nothing asserted; the camera simply never slowed down.
  rem  The TU could not link before because its Update reached a private ODR fork of
  rem  DirectorIO::InputBuffer whose accessors nothing defined; that fork is retired and the
  rem  body is re-fitted to the real InputBuffer (GetUsedRaceCars / GetRaceCarInfo /
  rem  GetTimerStatusInterface). MEASURED mount cost: zero new unresolved.
  echo "%SRC%\GameSource\Director\Utils\BrnDirectorVehicleTracker.cpp"
  echo "%SRC%\GameSource\Director\MomentController\BrnMomentSelector.cpp"
  echo "%SRC%\GameSource\Director\MomentController\BrnMomentController.cpp"
  rem ---- [momentcam] jump/stunt CUTAWAY-CAMERA wave, 2026-08-23 --------------------------
  rem  ⭐ NO NEW MOUNTS ARE ADDED BY THIS WAVE, ON PURPOSE. This block exists so the next
  rem  person to plan a "mount the moments" pass starts from measured numbers instead of the
  rem  stale "+9 unresolved" note further up.
  rem
  rem  WHAT THE WAVE FIXED IN PLACE (already-mounted TUs above; zero new unresolved externals,
  rem  verified by archiving build\game\obj into one .lib and diffing symbol tables):
  rem    * MomentSelector::SelectBestMomentWithExclusion @0x82250FC8 and its LRU arm
  rem      SelectBestLRUMomentWithExclusion @0x8221BE50 are REAL now, in BrnMomentSelector.cpp.
  rem      Both were `return false` GROUP F stubs sitting on the cutaway path.
  rem    * BrnMomentParameterBank.cpp was a six-type local fork (the class-vs-struct
  rem      Moment::Parameters ODR fork). De-forked; every byte it writes is unchanged.
  rem    * BrnMomentSubclasses.h was an ELEVEN-class ODR fork; ten are retired.
  rem    * BrnMomentPlayerJumping.cpp and BrnMomentTumbling.cpp now COMPILE (they did not).
  rem    * The moment pool bucket (AbstractPool 70,20,Vector4 == 1120 B) is TOO SMALL on x64
  rem      (MomentPlayerJumping is 1296 B). Widened + static_assert-ratcheted in
  rem      BrnMomentController.h. Inert today; a heap smash the day the closure mounts.
  rem
  rem  WHY NOTHING IS MOUNTED (MEASURED 2026-08-23, not estimated):
  rem    * BrnMomentControllerNewMoment.cpp + BrnMoment.cpp + all 14 Moments\*.cpp costs
  rem      142 NON-CRT unresolved externals. Trimming NewMoment to only the two cutaway
  rem      moment types still costs ~50. ~44 of the 142 are the `detail::MomentSharedInfo_*`
  rem      reach shims -- that record has NO home in this tree and IS the keystone.
  rem    * ⛔ AND THE MOUNT ALONE WOULD NOT MAKE A CUTAWAY PLAY: nothing in this tree ticks a
  rem      moment. MomentController::UpdateAllMoments @0x82239DE8 has no body anywhere,
  rem      MainDirector::UpdateMoments @0x82250268 is declaration-only, and the call is
  rem      COMMENTED OUT at BrnMainDirector.cpp:1617 (`GATE: UpdateMoments(...)`).
  rem    * ⛔ BrnMainDirector.h:353 models the MomentController as a fixed 22,416-byte X360
  rem      span (`u8 maMomentController[0x1CA60 - 0x172D0]`) and reinterpret_casts to it. The
  rem      host object does not fit that span even before the bucket widening.
  rem
  rem  ORDER TO DO IT IN (each step is useless without the ones above it):
  rem    1. Home the MomentSharedInfo record.  2. Body UpdateAllMoments + UpdateMoments and
  rem    un-gate BrnMainDirector.cpp:1617.  3. Give MainDirector a real MomentController
  rem    member.  4. Body the six BehaviourCollection template methods + the ~38 one-liner
  rem    per-moment virtuals.  5. THEN add the mounts here and delete the GROUP F stubs.
  rem  Full reasoning: GROUP F at the foot of %SRC%\GameSource\Director\DirectorLinkStubs.cpp
  rem ---- [momentcam] end ----------------------------------------------------------------

  rem  BrnDirectorEffectTrigger.cpp joins the link at last: the note further down claiming it
  rem  costs two real unresolved externals is now STALE -- EffectInterface::HookExists is
  rem  bodied in it (from @0x8221E268) and RegisterStartingBackgroundEffectWithName from the
  rem  three stores the console inlines at @0x82232F20. Camera::StopCurrentEffect @0x82205BB8
  rem  and Camera::RequestStartEffectHook are bodied there too.
  echo "%SRC%\GameSource\Director\Utils\BrnDirectorEffectTrigger.cpp"
  rem ---- TENTH PASS (2026-08-01): ArbStateCarSelect -- THE REAL CAMERAS --------------------
  rem  ?????? The state that owns the junkyard shot-group setup, the three authored ICE intro
  rem  shots off mGameIntroGroup ("606002") and the rotate-about-car orbit camera. Its four
  rem  LNK2005 stubs are gone from DirectorLinkStubs.cpp. It only becomes REACHABLE because of
  rem  the NINTH PASS above -- ArbStateRoaming::Update is the only path that ever writes
  rem  E_STATE_CHANGING_TO_CAR_SELECT.
  rem  MEASURED 2026-08-01 (fresh --rescan against the NINTH-PASS object list): these four
  rem  together are NET +4, and TWO of the four are the CRT (atan2, fabs, which the measure
  rem  script's CRT filter does not cover). The last two:
  rem    * Utils::CameraShake::Update -- GATED at BrnBehaviourIceAnim.cpp's bystander-space
  rem      wobble, with the reason and the DELETE-WHEN there. Mounting its real TU
  rem      (Camera/Utils/BrnCameraShake.cpp) costs +5 today.
  rem    * BehaviourIceAnim's vector deleting destructor -- a COFF WeakExternal off its own
  rem      vtable.
  rem  ?????? The FOURTH/FIFTH/SIXTH-PASS notes below quoting 54 / 31 / 13 / 12 unresolved for this
  rem  same set are ALL STALE: that was before CameraReference::Setup was bodied, before the
  rem  BehaviourInterpolate ODR fork was retired, and before the EIGHTH PASS closure set.
  echo "%SRC%\GameSource\Director\Arbitrator\States\BrnArbStateCarSelect.cpp"
  echo "%SRC%\GameSource\Director\Camera\Behaviours\BrnBehaviourIceAnim.cpp"
  rem  ---- DRIVE-THRU CAMERA WAVE (2026-08-29): the drive-thru shop camera. --------------
  rem  BrnArbStateDriveThru.cpp is E_STATE_DRIVETHRU -- the state ArbStateRoaming enters on
  rem  mbDriveThruActive (BrnArbStateRoaming.cpp:1059). Its container slot was five stubs in
  rem  DirectorLinkStubs.cpp whose Prepare returned an unconditional `true` and whose Update
  rem  was empty -- the same empty-shell shape ArbStateCrashing had. Those five are removed in
  rem  the same b5-decomp commit; never mount one without the other (LNK2005 x5 otherwise).
  rem  ==> IT IS ATOMIC WITH BrnBehaviourManager_NewBehaviourFromShot.cpp below. The state's
  rem  Prepare allocates its camera through BehaviourManager::NewBehaviour @0x82267418, the
  rem  ATTRIBUTE-DRIVEN factory, which had no body anywhere in the tree -- so the state alone
  rem  is one unresolved external, and a quiet stub for it would link green and allocate
  rem  nothing (a drive-thru camera that never moves).
  rem  MEASURED mount cost: BrnArbStateDriveThru.cpp -> 25 referenced externals, 24 already
  rem  provided, 1 unresolved (that NewBehaviour); the factory TU -> 19 referenced, 19
  rem  provided, ZERO new unresolved.
  echo "%SRC%\GameSource\Director\Arbitrator\States\BrnArbStateDriveThru.cpp"
  rem  BrnBehaviourManager_NewBehaviourFromShot.cpp -- BehaviourManager::NewBehaviour
  rem  @0x82267418, the shot-attribute behaviour factory: it reads the shot RefSpec's class
  rem  key and allocates BehaviourIceAnim (authored takes -- every shotgroup shot, which is
  rem  the drive-thru's arm), or BehaviourAftertouchCam / BehaviourGyroCam. Isolated TU for
  rem  the same reason BrnBehaviourManager_AllocateBehaviour_IceAnim.cpp is: the real
  rem  BrnBehaviourIceAnim.h collides with the flat-slice behaviour headers that
  rem  BrnBehaviourManager.cpp includes. The other two arms are FLAG-gated at their asserts --
  rem  their Parameters blocks live inside BehaviourParameterBank::maReservedHead and are not
  rem  carved; see the banner in the TU.
  echo "%SRC%\GameSource\Director\Camera\BrnBehaviourManager_NewBehaviourFromShot.cpp"
  echo "%SRC%\GameSource\Director\Shots\ShotControllers\BrnKeyAnimController.cpp"
  echo "%SRC%\GameSource\Director\Camera\BrnCameraReference.cpp"
  rem ---- ICE-anim de-fork wave (2026-07-30) ------------------------------------------------
  rem  ArbStateCarSelect (the retail GAME-INTRO state -- it walks PREPARING ->
  rem  GAME_INTRO_PART_ONE/TWO/THREE off the DirectorResourceManager's mGameIntroGroup, vault
  rem  name key "606002") now COMPILES: the six CollisionPolicy / Utils C2011 forks inside
  rem  Behaviours/BrnBehaviourIceAnim.h are retired, and so do its six sibling ICE-anim states.
  rem  ---- 2026-07-31 UPDATE: the camera code itself is DONE. ----
  rem  BrnDirector::KeyAnimController (the ICE take evaluator: Prepare, Update,
  rem  UpdateCameraFromICE, UpdateTransformationMatrix, UpdateFocus, UpdateLens,
  rem  Get/SetParametricTime0To1 + the four accessors) is fully reconstructed in
  rem  Shots/ShotControllers/BrnKeyAnimController.cpp, and the ten declaration-only
  rem  BrnDirector::Camera::IceAnimCameraOps placeholders are RETIRED onto the real APIs
  rem  (Camera::operator=, Camera::RequestMotionBlur, Camera::Set/GetFOV,
  rem  DepthOfField::SetParams, Looker::Update, CameraShake::Update,
  rem  Behaviour::SetCantSwitchToMeNow, CollisionPolicyAttachedToVehicle::SetVehicleRef).
  rem  CAMERAS.BUNDLE is ported to platform 4 as well, so the data is there too.
  rem
  rem  The three TUs are STILL NOT MOUNTED, and the reason has changed again. Measured today
  rem  with all three in the link (BrnKeyAnimController.cpp + BrnBehaviourIceAnim.cpp +
  rem  BrnArbStateCarSelect.cpp): 0 compile errors, 54 unique unresolved externals --
  rem      17  DirectorResourceManager accessors (14 shot-group getters + GetICEAuthor /
  rem          GetICEList / GetKeyAnimFromGuid). These are the FORK's accessors in
  rem          Behaviours/BrnBehaviourIceAnim.h; retiring that fork needs the manager's 65
  rem          shot-group members DECLARED, which in turn needs Attrib::FindCollection's real
  rem          (classKey, collectionKey) signature and Attrib::Instance::operator= -- see the
  rem          recon map at the top of GameSource/Director/BrnDirectorResourceManager.h.
  rem       8  BehaviourInterpolate / BehaviourRotateAboutVehicle (two un-landed behaviours).
  rem       6  the ICE SDK take runtime (ICETake::Construct / SetDataPointers / SetParameter /
  rem          GetValueInt / GetValueFloat, CameraSpaceHandler::TransformToWorld).
  rem      the rest: Camera::RequestMotionBlur / GetDepthOfField, DepthOfField::GetBlurriness,
  rem          CameraShake::Update, Tweaker::Construct, VehicleRef::Get, ICEAuthor /
  rem          ICEList guid lookups, Attrib::Gen::{iceanim::GetAnimGuid, shotgroup::Num_ShotList},
  rem          SharedCameraContainer / AllVehicleData / DebugPrinter leaves.
  rem  None of that is camera code any more -- it is the surrounding subsystems.
  rem
  rem  ---- 2026-07-31, SECOND PASS: "just not in this source list" was WRONG. ----------------
  rem  The 6 ICE entries used to be annotated "all RECONSTRUCTED under SDKs/Packages/ICE/, just
  rem  not in this source list", and the DirectorResourceManager block above called that the
  rem  cheapest next win. It is not a packaging problem. MEASURED, four builds:
  rem      three camera TUs alone .......................... 54 unresolved   (baseline, confirmed)
  rem      + ICEData.cpp + ICECameraSpaceHandler.cpp ....... 64  (closes 5, opens 15)
  rem      + ICEDataICETake/ICEDataEnums/ICEMath/ICEFile/
  rem        ICECameraSpaceHandlerCtor ..................... 67  (closes 5 more, opens 8)
  rem      three camera TUs + BrnCameraTweaker + ICEList ... 58  (closes 2, opens 6)
  rem  Every candidate mount is NET NEGATIVE. ICEData.cpp is not self-consistent: its own
  rem  reconstructed bodies call ~11 siblings that have no body anywhere --
  rem      ICETake::SetParameter(f32,bool,bool)   <- the PUBLIC take-level driver KeyAnimController
  rem                                                calls; only the PRIVATE per-channel
  rem                                                SetParameter(s32,f32,bool) is bodied
  rem      ICETake::GetValueFloat(s32,u16) / GetValueInt(s32,u16) / GetParameterData / GetKeyData
  rem      ICETake::GetNumKeys(s32) / GetNumIntervals(s32) / IsEditable
  rem      ICEChannel::GetKeyIndex(u16) / GetIntervalBracket(f32*,f32*)
  rem      CameraSpaceHandler::GetTransformToWorld
  rem      the globals ICE::ICE_EPSILON and ICE::spICEMemory
  rem  and ICEFile.cpp drags EA::GameTalk's message API + rw::core::stdc::Vsprintf behind it.
  rem  Of the 32 non-DirectorResourceManager leaves, exactly THREE have a real body that is
  rem  merely unmounted -- ICEAuthorTakeOps.cpp (ICEAuthor::FindEditedTakeFromGuid),
  rem  SharedClasses/DataLists/ICEList.cpp (ICEList::GetICETakeDataFromGuid) and
  rem  Camera/Utils/BrnCameraTweaker.cpp (Tweaker::Construct); each still opens 2-4 new ones.
  rem  Everything else is declaration-only. The frontier is genuinely open, so nothing is
  rem  mounted here and no camera-adjacent symbol is stubbed to fake it.
  rem
  rem  ?????? THE "no body anywhere" LIST ABOVE IS RETRACTED (2026-08-01, ICE take-runtime wave).
  rem  It was a NAME search, and the X360 export set does not carry these under a name. Every
  rem  entry on it is now bodied and the whole ICE data layer is MOUNTED (see the take-runtime
  rem  block near the top of this file for the recovery). ??? THE LESSON, which generalises far
  rem  past ICE: `sub_XXXXXXXX` entries in .ida-exports ARE bodies. When a symbol "does not
  rem  exist", search the CALLERS' xref lists for unnamed subs and identify them by their
  rem  caller set and their asserts' __FILE__/__LINE__ strings -- ICETake::SetSubTake was
  rem  pinned to ICEData.cpp:2575 by its own assert. Two of the entries above were not even
  rem  missing: ICEChannel::GetIntervalBracket(f32*,f32*) and GetIntervalStart() were bodied
  rem  all along, attached to their interval-ARGUMENT overloads by mistake, because their only
  rem  real callers were not in the tree yet.
  rem
  rem  Two further notes for whoever picks this up:
  rem   * BehaviourIceAnim::ClearBaseFirstFrameGate is declared (BrnBehaviourIceAnim.h:476) and
  rem     never defined -- a hole in BrnBehaviourIceAnim.cpp itself, not in a dependency.
  rem   * DebugPrinter::ActualPrint is NOT a missing body: BrnBehaviourIceAnim.cpp:91 re-declares
  rem     a local `struct DebugPrinter` with a 3-arg STATIC ActualPrint, while the real body
  rem     (DirectorModule/BrnDirectorModuleDebugPrinter.cpp:52) is a 2-arg member. Different
  rem     mangling -- mounting that TU will not resolve it; drop the local re-declaration.
  rem
  rem  DELETE-WHEN: the DirectorResourceManager fork is retired and the ICE take runtime's own
  rem  ~11 missing bodies are reconstructed (then the SDKs/Packages/ICE data-layer TUs can join
  rem  this source list as a unit).
  rem
  rem  ---- 2026-07-31, THIRD PASS: the C2011 blocker is GONE; the number is now 27. ---------
  rem  Re-measured with dumpbin /SYMBOLS over build\game\obj (the linked object set) rather
  rem  than by trial builds, so the split is exact. FIRST: all three ArbState TUs now COMPILE
  rem  CLEAN -- 0 errors, real objects. The six C2011 redefinitions the old note (and the .cpp's
  rem  own banner) blamed on Behaviours/BrnBehaviourIceAnim.h are stale: that header now
  rem  #includes all six canonical homes. The AttribSys wave also closed the attribinstance.h
  rem  failure the previous probe hit.
  rem
  rem  What is left is pure LINK closure, and it still says DO NOT MOUNT:
  rem      BrnArbStateCarSelect.cpp alone .. 63 referenced / 26 provided / 10 CRT / 27 UNRESOLVED
  rem      + RaceIntro + OnlineCarSelect ... 81 referenced / 33 provided / 11 CRT / 37 UNRESOLVED
  rem  (The old '54' above was a different set -- three CAMERA TUs, not these -- so it is not
  rem  comparable; it is left in place as the record of that experiment.)
  rem
  rem  The 27 for CarSelect break down as:
  rem      14  DirectorResourceManager::GetCarSelect*Shots / GetCarUnlockShots /
  rem          GetGameIntroShots. Declaration-only in Behaviours/BrnBehaviourIceAnim.h, and NO
  rem          body exists anywhere: the fourteen mCarSelect*/mCarUnlock/mGameIntroGroup members
  rem          live only in the recon-map COMMENT in BrnDirectorResourceManager.h (they are not
  rem          declared), and that TU is not mounted. This is the dominant block and the one
  rem          real next step -- Attrib::FindCollection / Instance::operator= /
  rem          GetAttributePointer / shotgroup::Num_ShotList are all real now, so declaring the
  rem          member set and bodying Prepare is finally unblocked.
  rem       6  Camera::BehaviourInterpolate::{Setup, SetupDuration, SetupCameraAFromHelper,
  rem          SetupCameraBFromHelper, SetParameters, HasFinished}  -- un-landed behaviour.
  rem       2  Camera::BehaviourRotateAboutVehicle::{BecomeSimilarTo, SetParameters} -- ditto.
  rem       5  BehaviourIceAnim::ClearBaseFirstFrameGate (the known hole noted above),
  rem          Camera::EnsureEffectIsPlaying, SharedCameraContainer::
  rem          {ForcePrimaryGameplayBehaviourToFinish, GetSelectedGameplayCamera}, and
  rem          CgsDev::StrStreamBase's vector-deleting destructor.
  rem  Reproduce with scratchpad w10_unres2.py (dumpbin diff, seconds, no rebuild).
  rem
  rem  WARNING -- AND BEFORE MOUNTING: BrnBehaviourIceAnim.h typedefs ShotReference to
  rem  Attrib::Gen::iceanim, but SetParameters is handed the raw Attrib::RefSpec ShotList
  rem  element. The console wraps it in a TEMPORARY iceanim and reads that temporary's resolved
  rem  layout at +0xC; the committed C++ calls GetAnimGuid() straight on the RefSpec. Latent
  rem  only while these TUs stay unmounted. See Attrib::Gen::iceanim::GetAnimGuid.
  rem
  rem  ---- 2026-07-31, FOURTH PASS: the 14 shot-group accessors LANDED. 27 -> 13. --------
  rem  BrnDirectorResourceManager.h now declares all 65 shot-group members (64 shotgroup +
  rem  1 cameradefaults) plus the DWARF head members, and carries the whole public accessor
  rem  bank as header inlines under the DWARF NAMES. The second definition of
  rem  BrnDirector::DirectorResourceManager that lived in Behaviours/BrnBehaviourIceAnim.h is
  rem  DELETED (that header now includes the real one), and every call site was migrated --
  rem  GetCarSelectMotorCityShots -> GetCarSelect_MotorCity, GetGameIntroShots ->
  rem  GetGameIntro, GetTumblingCrashShots -> GetAfterCrash, and so on.
  rem
  rem  Re-measured with the same dumpbin diff (scratchpad w10_unres2.py), same method:
  rem      BrnArbStateCarSelect.cpp alone .. 49 referenced / 26 provided / 10 CRT / 13 UNRESOLVED
  rem      + RaceIntro + OnlineCarSelect ... 66 referenced / 33 provided / 11 CRT / 22 UNRESOLVED
  rem  (was 27 and 37.) All fourteen DirectorResourceManager symbols are gone from the set --
  rem  they are inlines over real members now, so they cost nothing at all.
  rem
  rem  VERDICT: STILL DO NOT MOUNT, and the reason is now a short, specific list.
  rem  The 13 left for CarSelect are:
  rem       6  Camera::BehaviourInterpolate::{Setup, SetupDuration, SetupCameraAFromHelper,
  rem          SetupCameraBFromHelper, SetParameters, HasFinished}
  rem       2  Camera::BehaviourRotateAboutVehicle::{BecomeSimilarTo, SetParameters}
  rem       1  BehaviourIceAnim::ClearBaseFirstFrameGate  (a hole in BrnBehaviourIceAnim.cpp)
  rem       1  Camera::EnsureEffectIsPlaying
  rem       2  SharedCameraContainer::{ForcePrimaryGameplayBehaviourToFinish,
  rem                                  GetSelectedGameplayCamera}   <- returns a REFERENCE
  rem       1  CgsDev::StrStreamBase's vector-deleting destructor
  rem
  rem  MEASURED, and it kills the obvious next idea: BrnBehaviourInterpolate.cpp and
  rem  BrnBehaviourRotateAboutVehicle.cpp DO exist and are self-contained (0 unresolved
  rem  each), but mounting them closes NONE of the 8 above. dumpbin says those two TUs
  rem  define only BehaviourInterpolate::{GetCollisionPolicy, GetParametricTime} and
  rem  BehaviourRotateAboutVehicle::{GetEmbeddedSubObject + its anchor helper} -- they are
  rem  accessor slices, not the behaviours. The 8 really are un-landed.
  rem  Measured combination: CarSelect + both behaviour TUs + BrnDirectorResourceManager.cpp
  rem  = 19 unresolved (the manager TU adds its own 5 ICE leaves; see below).
  rem
  rem  BrnDirectorResourceManager.cpp was REWRITTEN in the same wave (it used to be the
  rem  reverted raw-console-offset ctor; the ctor is now the compiler-generated one, member
  rem  by member, so that TU had nothing left to do). It now holds the manager's real
  rem  out-of-line bodies: GetKeyAnim x2, GetShakeTakes, GetICEAuthor, GetKeyAnimFromGuid
  rem  and -- fully reconstructed from the export's jump table -- GetEventIntroShots
  rem  @0x821F6AB8. It is STILL NOT MOUNTED: it costs 5 unresolved ICE leaves
  rem  (ICEWrapper::{GetICETakeData, GetShakeGroup, GetAuthor},
  rem  ICEAuthor::FindEditedTakeFromGuid, BrnResource::MakeICEMovieId), i.e. exactly the ICE
  rem  take-runtime group this note already says has to go in as a unit.
  rem  The old "NOT mounted -- raw console byte offsets, LNK2005" warning further up this
  rem  file is therefore STALE for that TU; only the mount decision still stands.
  rem
  rem  AND THE SECOND OBVIOUS IDEA IS DEAD TOO: BrnSharedCameraContainer.cpp and
  rem  BrnDirectorEffectTrigger.cpp also exist unmounted, and adding them to CarSelect takes
  rem  13 -> 16. They do NOT define ForcePrimaryGameplayBehaviourToFinish /
  rem  GetSelectedGameplayCamera / EnsureEffectIsPlaying -- those three stay unresolved --
  rem  and they open three NEW leaves (HookNameStringWrapper::operator==,
  rem  EffectInterface::{HookExists, RegisterStartingBackgroundEffectWithName}).
  rem  PATTERN WORTH REMEMBERING: four "the TU already exists, just mount it" candidates were
  rem  measured this wave and ALL FOUR are accessor SLICES whose file name matches the class
  rem  but whose object does not define the function that is missing. Check what an object
  rem  DEFINES (dumpbin /SYMBOLS, filter out UNDEF) before assuming a mount closes anything.
  rem
  rem  ---- 2026-08-01, FIFTH PASS: the ICE take runtime LANDED; the camera set is 31. -------
  rem  RE-MEASURED against the current source list (which now carries the whole ICE data layer
  rem  and BrnDirectorResourceManager.cpp), by trial build:
  rem      KeyAnimController + BehaviourIceAnim + ArbStateCarSelect = 31 UNRESOLVED, 0 compile
  rem      errors. (41 before the ICE runtime went in -- so it closed 10 outright: ICETake's
  rem      ctor / Construct / SetDataPointers / SetParameter / GetValueFloat / GetValueInt and
  rem      ICETakeData::FixUp/FixDown among them.)
  rem  ?????? The "13" in the FOURTH PASS above is ArbStateCarSelect ALONE; 31 is all three camera
  rem  TUs together, which is what actually has to go in for the retail intro camera. Not
  rem  comparable -- both are kept as the record.
  rem
  rem  THE 31 ARE A WAVE OF THEIR OWN, and the shape is now clear: ~15 of them have NO
  rem  definition anywhere in the tree (checked file by file), i.e. they need reconstruction,
  rem  not mounting --
  rem      Camera::{IsLookingAtTarget, GetDepthOfField, RequestMotionBlur,
  rem               CreateHeadingSpaceLookAt, GetVehicleWorldPosition, EnsureEffectIsPlaying}
  rem      DepthOfField::GetBlurriness,  BehaviourSharedInfo::{GetEyeTarget, GetLookTarget}
  rem      SharedCameraContainer::GetSelectedGameplayCamera  <- returns a const Camera& and
  rem                                                           CANNOT be honestly stubbed
  rem      AllVehicleData::GetNearestRaceCarIndexToPlayer
  rem      BehaviourIceAnim::ClearBaseFirstFrameGate  (still the hole in its own .cpp)
  rem      BehaviourInterpolate::{SetupCameraAFromHelper, SetupCameraBFromHelper, SetupDuration}
  rem      BehaviourRotateAboutVehicle::BecomeSimilarTo
  rem      CollisionPolicyAttachedToVehicle::SetVehicleRef
  rem  The remainder are real bodies in unmounted TUs (BrnDirectorResourceManagerICE.cpp,
  rem  ICEAuthorTakeOps.cpp, ICECameraSpaceHandler.cpp, BrnDirectorModuleDebugPrinter.cpp,
  rem  BrnCameraTweaker.cpp), each of which opens its own leaves.
  rem  The WARNING above about the iceanim ShotReference temporary still stands and must be
  rem  settled BEFORE that wave mounts anything.
  rem
  rem  ---- 2026-08-01, SIXTH PASS: 31 CONFIRMED -- and link closure is NOT the last blocker. --
  rem  Re-measured independently (scratchpad ice_measure.ps1 -Tag CAMW1): the three camera TUs
  rem  together are 31 unresolved / 0 compile errors, exactly as the FIFTH PASS says. One
  rem  correction to that list: CgsDev::StrStreamBase's vector-deleting destructor is NOT in the
  rem  set any more (the FOURTH PASS bullet is stale on it).
  rem
  rem  ?????? THE BIGGER FINDING: ArbStateCarSelect can never leave E_STATE_INACTIVE on this build,
  rem  at 31 unresolved OR at 0. Its Update's INACTIVE arm returns immediately; the state only
  rem  starts when something calls Prepare(), and the ONLY writer of E_STATE_CAR_SELECT in the
  rem  whole tree is ArbStateRoaming::ProcessActiveDrivingTransitions
  rem  (BrnArbStateRoaming.cpp:551, `meJunkyardState != E_JY_INACTIVE` -> ChangeToStateWithoutRelease).
  rem  THREE independent reasons that never runs today:
  rem    (a) BrnArbStateRoaming.cpp is NOT mounted -- Construct/Prepare/Release/GetName come from
  rem        DirectorLinkStubs.cpp:151-154;
  rem    (b) ArbStateRoaming::Update is not even an override in the linked set (its header
  rem        records Update/Destruct as living in their own X360 TUs), so roaming inherits
  rem        ArbitratorState::Update, which drives nothing;
  rem    (c) GameState::meJunkyardState has EXACTLY ONE writer in the tree -- GameState::Clear()
  rem        setting it to E_JY_INACTIVE (BrnDirectorGameState.cpp:87). Nothing makes it active.
  rem  mbNewProfileIntroActive (bridge 476) IS live and reaches GameState, but it is only read
  rem  INSIDE ArbStateCarSelect::Update's PREPARING arm -- i.e. downstream of that gate.
  rem  => Finishing the 31 is necessary but NOT sufficient. Budget the entry gate as a second,
  rem  independent blocker of comparable size.
  rem
  rem  MEASURED (CAMW2, same method): mounting the six "the TU exists, just mount it" candidates
  rem  the FIFTH PASS lists takes 31 -> 46. Closed 5, opened 20. Per-TU, from the diff:
  rem      BrnCameraTweaker.cpp            closes Tweaker::Construct;   opens 5 (KAAC_AXIS_NAMES,
  rem                                      KAAC_CONTROL_NAMES, DebugController::GetControllerInfo,
  rem                                      DebugInterface::Get2dRender, DebugRender::Draw2DTextJustified)
  rem      BrnDirectorModuleDebugPrinter   closes 0;  opens 6 (DebugLog::ActualAppend,
  rem                                      DebugPrinter::Print, DebugInterface::{En,Dis}ableConsole, ...)
  rem      BrnDirectorResourceManagerICE   closes 2;  opens 3 (MakeICEMovieId,
  rem                                      ICEWrapper::GetShakeGroup, ICEWrapper::GetICETakeData)
  rem      ICEAuthorTakeOps.cpp            closes 1;  opens 5 (bList::EndOfList,
  rem                                      ICEController::{EditorOn,SetState}, ICEFileHandler::FileClose)
  rem      ICECameraSpaceHandler.cpp       closes 1;  opens 1 (CameraSpaceHandler::GetTransformToWorld)
  rem      BrnDirectorICEWrapper.cpp       closes 1;  opens 2 (ICEManager::GetCameraTake,
  rem                                      ICECameraMover::Construct)
  rem  That is now SEVEN, EIGHT, NINE, TEN, ELEVEN and TWELVE measured mount candidates that are
  rem  net-negative. Treat "the TU exists, just mount it" as false by default in this subsystem.
  rem
  rem  WHAT THIS WAVE ACTUALLY LANDED against the 31 (all in TUs that are ALREADY mounted or
  rem  that mount WITH the camera family, so they cost zero, and all boot-verified):
  rem      DepthOfField::GetBlurriness / ::SetBlurriness   -> BrnDepthOfField.cpp
  rem      Camera::GetDepthOfField (both overloads)        -> Camera.cpp
  rem      Camera::RequestMotionBlur                       -> Camera.cpp
  rem      Utils::Tweaker::Construct                       -> NEW BrnCameraTweakerConstruct.cpp
  rem                                                         (file split; mounted above)
  rem      SharedCameraContainer::GetSelectedGameplayCamera-> BrnDirectorArbitratorSharedCameraContainer.cpp
  rem      Camera::CreateHeadingSpaceLookAt                -> BrnBehaviourIceAnim.cpp
  rem      Camera::GetVehicleWorldPosition                 -> BrnBehaviourIceAnim.cpp
  rem  RE-MEASURED after landing them (CAMW3, same method): **31 -> 24**. Eight symbols left
  rem  the set and ONE joined it -- the DebugPrinter fix below SWAPS an unresolvable symbol for
  rem  a resolvable one (the fabricated `static ActualPrint(void*, const char*, s32)` is gone;
  rem  the real `private: ActualPrint(const char*, unsigned int)` takes its place and is bodied
  rem  in BrnDirectorModuleDebugPrinter.cpp, waiting only on that TU's debug-render leaves).
  rem  ?????? Do not read "-8" as "-8 net": count the SET, not the closures.
  rem  ??? GetSelectedGameplayCamera -- the one the FIFTH PASS singled out as un-stubbable
  rem  because it returns a const Camera& -- has NO standalone X360 symbol: it is inlined at
  rem  every site (ArbStateCarSelect::Prepare @0x8226EFA0, ArbStateRaceIntro::Update
  rem  @0x8226E5B0 case 4, Arbitrator::Update @0x8226ADA0), all three emitting the same
  rem  select-bit + handle-resolve pair. The two callees are UNNAMED subs (sub_82212288 /
  rem  sub_82212438) and were pinned by their own assert -- "IsAllocated()",
  rem  BrnBehaviourManager.h, line 610 -- which is BehaviourHandle::GetProducedCamera's
  rem  tripwire; their sibling sub_821FD3E8 asserts at :589 and is GetBehaviour. That is the
  rem  seventh and eighth time an unnamed sub, not missing code, was the actual blocker.
  rem  ALSO FIXED, and it is a defect species worth naming: BrnBehaviourIceAnim.cpp declared its
  rem  own `struct DebugPrinter { static void ActualPrint(void*, const char*, s32); };`. The real
  rem  @0x821F71D8 is a NON-static PRIVATE member `ActualPrint(const char*, CgsDev::RGBA)` -- the
  rem  console's r3 there is the printer, not an argument. The forked spelling mangles to a symbol
  rem  NO TU CAN EVER DEFINE, so it would have sat in the unresolved list for ever looking like it
  rem  just needed its home mounted. Now goes through BehaviourSharedInfo::GetDebugPrinter() and
  rem  the public Print(text, colour) forwarder (bodied in the home header, which is what the
  rem  console inlines). ARITY/STATICNESS forks only ever surface as LNK2019 -- check the
  rem  signature, not just the name.
  rem
  rem  ???????????? A LIVE ODR FORK found on the way, NOT fixed: there are TWO
  rem  BrnDirector::Camera::BehaviourInterpolate. BrnBehaviourManager.h:114 is a slice with NO
  rem  base and NO members (sizeof == 1) -- the one ArbStateCarSelect reaches -- and
  rem  Behaviours/BrnBehaviourInterpolate.h:93 is the real one (: public Behaviour, with
  rem  mFromCamera/mToCamera/mfDuration/mbSetup/mbHasFinished and header-inline bodies for
  rem  SetupDuration/Setup/HasFinished). BrnBehaviourManager.cpp:755 explicitly instantiates
  rem  AllocateBehaviour<BehaviourInterpolate> over the EMPTY one: it books a 1600-byte small-pool
  rem  bucket by sizeof, placement-news a ONE-BYTE object into it, and BehaviourHelper::Prepare
  rem  then static_casts that to Behaviour* and dispatches vtable slot 0. Inert only because
  rem  nothing in the linked set allocates one. BehaviourRotateAboutVehicle (line 759) is the same
  rem  shape. Retiring the manager slice in favour of the real home is the highest-value next step
  rem  on the link side: it closes 3 of the 6 interpolate symbols outright (already header inlines
  rem  there) and removes the hazard. NOTE the real home ALSO carries its own local `class
  rem  Behaviour` fork (line 71), so the reconcile has to retire that too.
  rem
  rem  ??? AND ClearBaseFirstFrameGate IS MIS-NAMED. The store IS verified -- ArbStateCarSelect::
  rem  Prepare emits `stb r23, 0x28(behaviour)` at 0x8226F0C4 and 0x8226F1A8 (pseudocode
  rem  `*(GetBehaviour(handle) + 40) = 0`). But BehaviourIceAnim's canonical Behaviour base ends
  rem  well before +0x28 (vptr, meTimestepType @+4, five flag bytes @+8..+0xC, mpcDebugParametersName
  rem  @+0x10) and GetCollisionPolicy returns `this + 0x20`, so byte +0x28 is mCollisionPolicy
  rem  +0x08 -- a VisibilityCollisionPolicy field, inside maReservedToVehiclePredictor
  rem  [+0x08, +0x70). It is NOT a base gate. Name it on the POLICY when that span is carved.
  rem
  rem  ??? THE iceanim ShotReference HAZARD IS NOW SETTLED (what the right answer is, not the fix):
  rem  Camera.h:83-84 carries the DWARF-attested `typedef const Attrib::RefSpec ShotReference;`
  rem  (DWARF Camera.h:43) and Camera::mpSourceShot @+0x54 uses it. BrnBehaviourIceAnim.h:278's
  rem  `typedef Attrib::Gen::iceanim ShotReference;` is simply the WRONG one for the SAME console
  rem  field role (behaviour +0x0E24). The fix is to point the behaviour's typedef at
  rem  Camera::ShotReference and have SetParameters build the TEMPORARY iceanim over the RefSpec
  rem  the way @0x8220F5C0 does. COST, so the next wave budgets it: Attrib::Gen::iceanim's
  rem  RefSpec ctor (iceanim.h:34) is DECLARATION-ONLY, so doing this ADDS one unresolved until
  rem  that generated ctor is bodied. Not done here -- it cannot be boot-verified while the TU is
  rem  unmounted, and guessing the generated ctor's body is exactly the kind of fabrication this
  rem  file exists to prevent.
  rem
  rem  ---- 2026-08-01, SEVENTH PASS: 24 -> 12, and the entry gate is now MAPPED. -------------
  rem  RE-MEASURED baseline for KeyAnimController + BehaviourIceAnim + ArbStateCarSelect:
  rem  24 unresolved / 0 compile errors (the "30" in an earlier brief was stale; the SIXTH
  rem  PASS's 24 was right). After this wave: 12 unresolved / 0 compile errors, measured with
  rem  the same three TUs plus Frustum.cpp and BrnBehaviourInterpolate.cpp (both now mounted
  rem  for real, see their own notes above).
  rem
  rem  ?????? MOUNTING THE THREE CAMERA TUs IS STILL BLOCKED. Twelve is not zero, and an exe does
  rem  not link at twelve. DirectorLinkStubs.cpp also still defines ArbStateCarSelect's four
  rem  virtuals, so mounting the TU is an LNK2005 until those four stubs come out. Both are
  rem  next wave's first two jobs.
  rem
  rem  CLOSED THIS WAVE (12):
  rem    * the six BehaviourInterpolate symbols -- by RETIRING the member-less slice this
  rem      header used to carry (see the BrnBehaviourInterpolate.cpp mount note above) and
  rem      bodying SetParameters / SetupCameraA|BFromHelper against the real members. All three
  rem      are X360 HEADER-INLINES (their assert-file string is the .h, not the .cpp) recovered
  rem      from twelve identical call sites.
  rem    * VehicleRef::Get, AllVehicleData::{GetPlayer, GetRaceCar, GetNearestRaceCarIndexToPlayer},
  rem      NearestCarInfo::operator> -- all five are HEADER INLINES on the console (every assert
  rem      in them cites BrnDirectorAllVehicleData.h / BrnVehicleRef.h, and a function whose
  rem      asserts cite a header was defined in that header). GetNearestRaceCarIndexToPlayer had
  rem      been bodied out-of-line in a .cpp that is NOT on this build list, so every consumer
  rem      saw an unresolved external for code that was already written.
  rem    * BehaviourSharedInfo::{GetEyeTarget, GetLookTarget} -- the FLAG blocking them (a
  rem      SuspensionSpring ODR fork) was STALE; there is exactly one struct SuspensionSpring in
  rem      the tree now, so mPlayerInfo is embedded by value and both resolve to named members.
  rem    * Camera::IsLookingAtTarget -- bodied; Frustum.cpp mounted for its one leaf.
  rem    * CollisionPolicyAttachedToVehicle::{Construct, SetVehicleRef}.
  rem
  rem  ?????? AND THE REAL NEWS, WHICH IS NOT ABOUT LINK CLOSURE:
  rem  ArbStateCarSelect STILL CANNOT LEAVE E_STATE_INACTIVE AT ZERO UNRESOLVED. The SIXTH
  rem  PASS said so; this wave mapped the gate exactly, and it is SHALLOWER than feared:
  rem    - ArbitratorStateContainer::UpdateAll calls Update on ALL ELEVEN states every frame
  rem      (vtable slot 2, verified @0x821F5E70), so ArbStateCarSelect::Update runs regardless
  rem      of which state is current. The gate is purely that nothing calls its Prepare().
  rem    - The only writer of E_STATE_CAR_SELECT is ArbStateRoaming::ProcessPossibleStateChanges
  rem      @0x82219C58 (already reconstructed), whose only caller is ArbStateRoaming::Update
  rem      @0x822643A0 -- which has NO BODY ANYWHERE IN THE TREE (the ledger says `reviewed`;
  rem      that is the same drift that bit three functions last wave).
  rem    - Its critical path is ONE guard deep: `meState == E_STATE_PREPARING` -> the virtual
  rem      Prepare() returns true -> meState = E_STATE_DRIVING and the arm FALLS THROUGH into
  rem      the DRIVING body in the same frame, which reaches ProcessPossibleStateChanges
  rem      UNCONDITIONALLY (@0x8226464C). Then H1..H9 in that function, ending on
  rem      `meJunkyardState != E_JY_INACTIVE` -- which this build already satisfies (0 -> 2).
  rem    - Update is a flat 16-arm jump-table switch on meState. Arms 0/1/2 + the nine
  rem      CHANGING_TO_* arms + default are 41%% of the instructions and 100%% of the
  rem      transition-out paths; the four Picture-Paradise/idle arms are the other 59%% and are
  rem      unreachable in the junkyard scenario. A T2 slice is a recognisable SUBSET, not a
  rem      fiction -- every arm boundary is a jump-table entry with its own epilogue.
  rem      ?????? Case 13 (CHANGING_TO_CAR_SELECT, @0x8226548C) MUST be in the slice: if
  rem      ArbStateCarSelect::Prepare declines, meState parks on 0xD and case 13 is the retry.
  rem    - COST: two unmounted prerequisites are called UNCONDITIONALLY from the DRIVING arm --
  rem      MomentSelector::Update @0x82239FC0 (425 asm lines, no PC body) and
  rem      ArbStateRoaming::ProcessPossiblePaybackEffects @0x82208BA8 (117 lines, no PC body;
  rem      BrnArbStateRoaming.h:82 wrongly records it as "not in this TU's X360 set").
  rem    - ??? AND ArbUtils::ChangeToStateWithoutRelease -- the function that performs the
  rem      hand-off -- is a __debugbreak() TRAP STUB in BrnDirectorArbitratorUtils.h:50. Even a
  rem      perfect ladder would trap there. Body it from @0x821FE2B8 FIRST.
  rem      ?????? Its console parameter order is INVERTED vs the committed declaration: the console
  rem      passes whenBlocked in r6 and whenSwitched in r7; the header declares
  rem      leFromStateWhenSwitched 4th and leFromStateWhenBlocked 5th, and every call site in
  rem      the tree matches the header. Consistent today only because the body traps.
  echo "%SRC%\GameSource\Director\Utils\BrnDirectorWorldMap.cpp"
  echo "%SRC%\GameSource\Director\Utils\BrnSceneQueryInterface.cpp"
  echo "%SRC%\GameSource\Director\Utils\BrnDirectorTimestep.cpp"
  echo "%SRC%\GameSource\Director\Shots\ShotControllers\BrnInertiaController.cpp"
  rem  The TRAFFIC-LANE graph the fly-by rides. WorldMap::GetLanePositionNearestPoint walks
  rem  Pvs::GetHullIndexForPoint -> TrafficData::GetHull -> the section's rungs, and
  rem  TrafficLaneTruck::Update samples Section::Calc{Position,Direction,Transform}AtParameter.
  rem  These MUST be the real bodies -- a stubbed lane walk is a stationary camera.
  echo "%SRC%\SharedClasses\Traffic\BrnTrafficData.cpp"
  echo "%SRC%\SharedClasses\Traffic\BrnTrafficPvs.cpp"
  echo "%SRC%\SharedClasses\Traffic\BrnTrafficSection.cpp"
  rem  2026-08-19 (wave Q7, cluster traffic): the Junctions TrafficLightCollection TU -- GetInstanceIndexForInstanceID
  rem  (the id->dense-index hash TrafficLightGot{Smashed,Restored} resolve through), GetCoronaState @0x8274F510 (export
  rem  hole, idat) and ExpandPosPlusYRotToTransform @0x823610B8. First Junctions TU on the bat.
  echo "%SRC%\SharedClasses\Traffic\Junctions\BrnTrafficLightCollection.cpp"
  echo "%SRC%\SharedClasses\Trigger\BrnGenericRegion.cpp"
  echo "%SRC%\SharedClasses\Trigger\BrnTriggerData.cpp"
  rem producer wave (2026-08-01): SpawnLocation::GetType/GetJunkyardId -- the junkyard spawn
  rem points CarSelectManager::SetupSpawnLocations files and EnterJunkyardAtStartOfGame takes
  rem maSpawnLocations[1] from. Costs ZERO new unresolved.
  echo "%SRC%\SharedClasses\Trigger\BrnSpawnLocation.cpp"
  rem  The lane-data RESOURCE TYPE handlers (traffic-lane fetch wave, 2026-07-29).
  rem  Registered by CgsResourceTypeRegistration.cpp; without a registered handler the pool
  rem  stores a NULL mpResourceType for the bundle's resource and AllocateMemoryForResource
  rem  null-derefs it -- exactly the trap ZoneList/0xB000 hit on the PVS wave.
  rem  ALL THREE are mounted as of the lane-data widening wave (2026-07-29). The seven Fix*
  rem  bodies that used to be missing are reconstructed:
  rem      BrnTraffic::TrafficData::FixUp/FixDown   @0x827637D8 / @0x82763CB8  BrnTrafficData.cpp
  rem      BrnTraffic::Hull::FixUp/FixDown          @0x827620A0 / @0x827622E0  BrnTrafficHull.cpp
  rem      BrnTraffic::Pvs::FixUp/FixDown           @0x827623E8 / @0x827624A0  BrnTrafficPvs.cpp
  rem      BrnTraffic::{TrafficLightCollection,FlowType}::FixUp/FixDown        BrnTrafficData.cpp
  rem                                               (inlined on console, de-inlined here)
  rem      BrnAI::AISectionsData::FixUp/FixDown     @0x8267DA28 / @0x8267DAA0  AISectionsData.cpp
  rem      BrnAI::AISection::FixUp/FixDown/GetMiddle @0x8267D8C8 / @0x8267D978 / @0x826771D0
  rem                                                                          AISection.cpp
  rem      BrnAI::Portal::FixUp/FixDown             (inlined on console)       BrnAIPortal.cpp
  rem  The payloads are transcoded to platform 4 with WIDENED 64-bit pointer slots by
  rem  tools/assets/bundles/lane_transcode.py (X360 originals in build/game_x360_world/).
  echo "%SRC%\SharedClasses\Trigger\BrnTriggerResourceType.cpp"
  echo "%SRC%\SharedClasses\Traffic\BrnTrafficDataResourceType.cpp"
rem  2026-08-21 wave T1 parked traffic cars -- SharedClasses half. GraphicsStub = resource
rem  type 65557 / 0x10015 carried by all 42 VEHICLES\VEH_T*_GR.BIN; registered in
rem  CgsResourceTypeRegistration.cpp in the console slot after TrafficData. Both of the
rem  record words are BUNDLE IMPORTS -- an unmounted handler skips ResolveImportsForEntry
rem  and the streamer would hand the renderer NULL specs with no error.
rem  BrnTrafficGraphicsStub.cpp is a compile-only layout gate, sibling of
rem  TrafficPhysics_layout_check.cpp. StaticTraffic/VehicleAsset/VehicleType/VehicleTraits/
rem  SectionFlow = the parked-car data value types, cluster C2.
echo "%SRC%\SharedClasses\Traffic\BrnTrafficGraphicsStub.cpp"
echo "%SRC%\SharedClasses\Traffic\BrnTrafficGraphicsStubResourceType.cpp"
echo "%SRC%\SharedClasses\Traffic\CgsResourcePtr_BrnTraffic_GraphicsStub.cpp"
echo "%SRC%\SharedClasses\Traffic\BrnTrafficStaticTraffic.cpp"
echo "%SRC%\SharedClasses\Traffic\BrnTrafficSectionFlow.cpp"
echo "%SRC%\SharedClasses\Traffic\BrnTrafficVehicleAsset.cpp"
echo "%SRC%\SharedClasses\Traffic\BrnTrafficVehicleType.cpp"
echo "%SRC%\SharedClasses\Traffic\BrnTrafficVehicleTraits.cpp"
  echo "%SRC%\SharedClasses\Traffic\BrnTrafficHull.cpp"
  echo "%SRC%\SharedClasses\AI\AISectionsResourceType.cpp"
  echo "%SRC%\SharedClasses\AI\AISectionsData.cpp"
  echo "%SRC%\SharedClasses\AI\AISection.cpp"
  echo "%SRC%\GameSource\World\AI\BrnAIPortal.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsSceneManagerIO_SceneQueryInterface.cpp"
  echo "%SRC%\GameSource\Director\DirectorLinkStubs.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiCache.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiProfile.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\CgsSaveLoadPS3.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\PC\CgsSaveLoadPC.cpp"
  rem (2026-07-28: SaveLoadSystem::Save now builds the real Realmc records, so the two
  rem  self-contained RealmcIface record TUs that own those ctors/operators join the link.
  rem  RealmcIfaceSaveCheckParams.cpp stays OUT -- it calls the RealmcCore allocator
  rem  primitives, and RealmcCore.cpp brings the whole Message/RefCount/RealmcString
  rem  vendor closure with it; the two SaveCheckParams symbols are stubbed in
  rem  BrnBaselineLinkStubs.cpp until that closure is added.)
  echo "%SRC%\SDKs\Realmc\RealmcLoadEntryInfo.cpp"
  echo "%SRC%\SDKs\Realmc\RealmcTitleInfo.cpp"
  rem ---- ProfileManager link closure (2026-07-12): the committed save/load + profile ----
  rem ---- validation TUs the real BrnGui::ProfileManager references.                 ----
  echo "%SRC%\GameShared\GameClasses\Gui\CgsSaveLoadX360.cpp"
  rem ---- dev merge (2026-08-07): BrnGuiProfile's ProfileManager::CopyImageToBuffer now ----
  rem ---- forwards to the real SaveLoadSystem::CopyImageToBuffer body in wB_03.        ----
  echo "%SRC%\GameShared\GameClasses\Gui\CgsSaveLoadX360_wB_03.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\CgsSaveLoad.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\CgsGuideIntegration.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\CgsGuiModuleIO_OutputBuffer.cpp"
  echo "%SRC%\GameSource\Gui\SaveLoad\BrnGuiSaveLoadProfile.cpp"
  echo "%SRC%\GameSource\Gui\SaveLoad\BrnGuiSaveLoadProfileDLC1.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiOptionsDataProfileDLC1.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiEventTypeDefs.cpp"
  rem ---- the GuiPerfmons static counters CgsAptAux's audited Update/Render/          ----
  rem ---- UpdateFlashComponent bodies reference (apt-audit retired the shim path).    ----
  echo "%SRC%\GameSource\Gui\BrnGuiPerfmons.cpp"
  rem ---- BrnBoostBarRenderer.cpp UNMOUNTED (2026-08-25, per the TU's own          ----
  rem ---- TODO(boost-render-half) note): b5 f96e48b4 replaced the old minimal      ----
  rem ---- slice with the faithful lifecycle half, whose RENDER half               ----
  rem ---- (RenderComponent @0x82466638 + CalculateShardVertices @0x8244B248 ..)   ----
  rem ---- is still to land -- the TU does not link until it does (the H2 wave's   ----
  rem ---- merged build caught it; the bat could not ride the b5 commit).          ----
  rem ---- REMOUNTED (2026-08-25, hud H3b wave): the render half landed upstream   ----
  rem ---- (b5 6bf9728c "boost bar: the render half + the live slot-4 mount").    ----
  echo "%SRC%\GameSource\Gui\CustomRenderer\Renderers\BrnBoostBarRenderer.cpp"
  echo "%SRC%\GameSource\Gui\CustomRenderer\Renderers\BrnCrashNavIconRenderer.cpp"
  rem ---- boost-bar support (2026-08-25, upstream a545ebc9/6bf9728c): the 2D      ----
  rem ---- billboard renderer + the near-miss tracker + the world->GUI vehicle    ----
  rem ---- bridge TU (the 206 producer; H3b extends it with the 376/147/199      ----
  rem ---- satnav posts).                                                        ----
  echo "%SRC%\GameShared\GameClasses\Gui\View\ParticleSystem2d\CgsBillboardRenderer.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\NearMisses\BrnNearMissManager.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\NearMisses\BrnNearMissData.cpp"
  echo "%SRC%\GameSource\Game\GameBridgeWorldToGui.cpp"
  rem ---- hud H3b tracking slice (2026-08-25): the 207 record type the bridge     ----
  rem ---- Construct()s and the cache consumes (mRaceCarInfo SoA feed).            ----
  echo "%SRC%\GameSource\Gui\BrnGuiRaceCarInfoEvent.cpp"
  rem ---- custom-renderer layer (2026-08-16) -------------------------------------------
  rem  BrnGui::CustomRendererManager -- the GUI custom-renderer SET. It is the single
  rem  blocker under two separately-reported defects: the licence card's red player-photo
  rem  slot (the apt movie types it `_type='PlayerImage', _index=1`, and the engine resolves
  rem  that through gAptFuncs.pfnCustomControlRender -> AptRenderHandler::
  rem  mpCustomRendererManager -> GetComponentTexture) and the in-game tutorial ticker
  rem  (GUI event 537 -> RecvEvent -> the InGameMessage component).
  rem  ??? THE "10 COMPONENT VTABLES" BLOCKER WAS ONE DECLARATION BUG, NOT TEN. The base
  rem  CgsGui::CustomRenderComponentInterface had been grown from the manager's call sites
  rem  with four INVENTED method names (GetComponentTexture/GetComponentID/
  rem  GetNumTexturesForComponent/Prepare(void*,void*,void*)); the DWARF names are
  rem  GetRenderOutput/GetID/GetNumTextures/Prepare(GuiEventQueueSmall*,IResourceAllocator*,
  rem  IResourceAllocator*), which is what every concrete renderer overrides -- so none of
  rem  them bound and every component was a hollow shell. Fixed against
  rem  references/DecFIGS/dwarfdump/.../CgsCustomRenderer.h.
  rem  ??? Only slot 0 (NetworkPlayerImage) is a live component; slots 1..9 are NULL, not
  rem  stubs -- their renderers are minimal slices that would construct, prepare, report
  rem  success and draw nothing.
  echo "%SRC%\GameSource\Gui\CustomRenderer\BrnCustomRenderer.cpp"
  rem ??? [tut-ticker] wave (2026-08-24) -- THE BOTTOM-OF-SCREEN TICKER, whole (manager slot 8).
  rem  The consumer of GUI event 537: queues the training/custom lines, scrolls them with the
  rem  B5DotMat face over the fading black band (TextRenderer/Im2d substrate, gateui waves').
  echo "%SRC%\GameSource\Gui\CustomRenderer\Renderers\BrnInGameMessageRenderer.cpp"
  echo "%SRC%\GameSource\Gui\BrnCustomRendererManager.cpp"
  echo "%SRC%\GameSource\Gui\CustomRenderer\Renderers\BrnNetworkPlayerImageRenderer.cpp"
  echo "%SRC%\GameSource\Gui\Flapt\BrnFlaptMovieClipInstance.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnCrashNavOkCancelOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnCrashNavOkOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnCrashNavOnlineOkCancelOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnCrashNavOnlineOkOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnCrashNavOnlineWaitOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnCrashNavWaitOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnInGameOkCancelOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnInGameOkOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\PFX\BrnGuiEffectsArbitrator.cpp"
  echo "%SRC%\GameSource\Gui\PFX\BrnGuiPFXHooks.cpp"
  echo "%SRC%\GameSource\Network\Managers\BrnNetworkLiveRevengeRelationship.cpp"
  echo "%SRC%\GameSource\Network\Managers\BrnNetworkMatchMakingManager.cpp"
  echo "%SRC%\GameSource\Network\Managers\BrnNetworkNotificationManagerBase.cpp"
  echo "%SRC%\GameSource\Network\Managers\BrnNetworkPlayerStats.cpp"
  echo "%SRC%\GameSource\Network\Messages\BrnUpdateMessage.cpp"
  echo "%SRC%\GameSource\Network\Utilities\BrnNetworkRounder.cpp"
  echo "%SRC%\GameSource\Replays\BrnReplayBaseSerialiser.cpp"
  echo "%SRC%\GameSource\Replays\Stream\BrnReplayWriteStream.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\common\attribinstance.cpp"
  echo "%SRC%\SDKs\Packages\AttribSys\1.2.1.2\AttribSys\runtime\common\attribute.cpp"
  rem ---- generated-class out-of-line bodies (2026-07-31, attrib-chain wave) -------------
  rem  Same convention as the already-mounted songlist.cpp: one .cpp per generated class,
  rem  holding only the functions the X360 attests as out of line. shotgroup.cpp bodies
  rem  Num_ShotList @0x821F5948 (~20 committed callers, no body and no home before today);
  rem  iceanim.cpp bodies GetAnimGuid (no X360 symbol -- inlined -- but likewise homeless).
  echo "%SRC%\GameSource\AttribSys\Generated\classes\shotgroup.cpp"
  echo "%SRC%\GameSource\AttribSys\Generated\classes\iceanim.cpp"
  rem ---- l2-into-dev merge link closure (dev waves grew shared TUs; their homes join;
  rem      the cascade-heavy waves -- ScreenFlow/HudFlow new states, CgsRegistry schema
  rem      web, Attrib node web -- are reverted-in-merge to l2 pending integration) ----
  echo "%SRC%\SDKs\EATech\include\NFSMix\NFSMixMapLinkStubs.cpp"
  echo "%VEN%\renderware\src\rw\core\stdc\stdc.cpp"
  rem rw::math::vpu::Inverse @0x825B2628 -- general 4x4 inverse; replaces the
  rem WorldLinkStubs.cpp link stub retired 2026-08-12 (prop-render wave).
  echo "%VEN%\renderware\src\rw\math\vpu\Matrix44Operation.cpp"
  echo "%SRC%\SDKs\Packages\ICE\ICEMemory.cpp"
  echo "%SRC%\SDKs\Packages\ICE\ICEPoint.cpp"
  echo "%SRC%\SDKs\Packages\Lion\Final\eauk_lion\Dev\LionRuntime\include\LionBlockAlloc.cpp"
  echo "%SRC%\SDKs\Packages\Lion\Final\eauk_lion\Dev\LionRuntime\include\LionChunkManager.cpp"
  echo "%SRC%\SDKs\Packages\Lion\Final\eauk_lion\Dev\LionRuntime\include\LionSerialiser.cpp"
  echo "%SRC%\SDKs\Packages\Lion\Final\eauk_lion\Dev\LionRuntime\include\LionSmallAlloc.cpp"
  echo "%SRC%\SDKs\Packages\Lion\Final\eauk_lion\Dev\LionRuntime\include\LionTokeniser.cpp"
  echo "%SRC%\SDKs\Packages\Lion\Final\eauk_lion\Dev\LionRuntime\include\ParticleWaveForm.cpp"
  echo "%SRC%\SharedClasses\Gui\SatNav\Resources\BrnSatNavTileResourceType.cpp"

  echo "%SRC%\GameShared\GameClasses\Graphics\Resources\CgsVideoDataResource.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsBaseResourcePtr.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiMovieManager.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\CgsGuiViewModule.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\CgsGuiViewModuleIO.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiViewModule.cpp"
  echo "%SRC%\GameSource\Gui\Flapt\BrnFlaptManager.cpp"
  echo "%SRC%\GameSource\Gui\Flapt\BrnFlaptFileInstance.cpp"
  echo "%SRC%\GameSource\Gui\Flapt\BrnFlaptTextFieldInstance.cpp"
  echo "%SRC%\GameSource\Gui\Flapt\BrnFlaptRenderer.cpp"
  rem FLAG link stubs for the un-homed BrnFlapt engine bodies + tiny GUI output-queue
  rem lifecycle the real ViewModule slice references (see the file header audit).
  echo "%SRC%\GameSource\Gui\BrnGuiViewModuleLinkStubs.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiModule.cpp"
  rem ---- gateui wave 2026-08-20: smash-gate and billboard UI events. GameState StuntManager
  rem ---- embed, world-to-gamestate prop-hit feed, GameState-to-Gui stunt arms, the full HUD
  rem ---- message analyzer + director + controller resource, Apt in-game messages hop.
  echo "%SRC%\GameSource\GameState\Offences\BrnStuntManager.cpp"
  echo "%SRC%\GameSource\GameState\Offences\StuntManager_gUI_00.cpp"
  echo "%SRC%\GameSource\GameState\Offences\StuntManager_gUI_01.cpp"
  echo "%SRC%\GameSource\GameState\Offences\BrnStuntManagerDebugComponent.cpp"
  echo "%SRC%\GameSource\GameState\Offences\StuntManagerDebugComponent_gUI_00.cpp"
  echo "%SRC%\GameSource\GameState\Offences\BrnStuntManagerDebugComponent_GetTriggerWorldRegion.cpp"
  echo "%SRC%\GameSource\GameState\GameStateModule_gUI_00.cpp"
  rem  ADDED 2026-08-27 (showtime S7b-a): GameStateModule::StartCrashMode @0x8236B580 (80 insns)
  rem  -- the bottom of the showtime start chain, and what eventually makes PrepareForMode post
  rem  action 23 with KU_FLAG_USE_SHOWTIME_VEHICLE_BEHAVIOUR. Every callee it needs was already
  rem  mounted (StartGameModeParams::Construct, ModeManager::StartGameMode, IsOnlineGameMode,
  rem  IsOnlineFreeBurnLobby, GetPlayerPosition). The TU also carries HarnessInjectShowtimeBringUp,
  rem  the env-gated (BRN_START_SHOWTIME) one-shot standing in for ShouldStartShowtimeMode
  rem  @0x82356B18 -- its TRIGGER is the real both-bumpers byte, not an invented input.
  echo "%SRC%\GameSource\GameState\GameStateModule_Showtime.cpp"
  rem  ADDED 2026-08-27 (bounce wave): ONE ARM of GameStateModule::UpdateRoadRulesManager
  rem  @0x82381258 -- the ONLY producer of game action 42 (E_ACTION_IMPACT_TIME_START) in the
  rem  whole image, and the single missing link that kept the P6 showtime bounce chain from
  rem  ever executing. Zero new dependencies: every callee (GetCurrentGameModeType,
  rem  IsOnlineGameMode, mLastActiveRaceCarInterface.IsPlayerCarActive, GameActionQueue::
  rem  AddEvent) is already mounted, and the consumer arm landed with S3. The function is a
  rem  STATED PARTIAL -- its four other arms are deferred by name in the TU banner.
  echo "%SRC%\GameSource\GameState\GameStateModule_RoadRules.cpp"
  rem [stuntrace wave D 2026-08-26] the four event-start functions + GetEvent helpers.
  echo "%SRC%\GameSource\GameState\GameStateModule_gSR_00.cpp"
  rem [event-starts wave 2026-08-27] the event-start table producer + the interface it
  rem fills (AddEventStart/AppendEventStart -- had no callers until now).
  echo "%SRC%\GameSource\GameState\GameStateModule_SendSetUpAllEventStarts.cpp"
  echo "%SRC%\GameSource\GameState\Interface_SetUpAllEventStarts.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\ModeManager_gUI_00.cpp"
  rem ============================================================================
  rem [stuntrace wave B 2026-08-26] THE MODEMANAGER MOUNT -- the offline event core.
  rem ModeManager spine + all 15 game modes + params + the 7 mode states + the
  rem scoring subsystem (offline scorers full; online scorers partial, remainder in
  rem BrnBaselineLinkStubs' MUST-STAY block) + the progression event-finish TU.
  rem DELIBERATELY OUT: ChallengeManager/* (bounded ModeManager layout has no
  rem embedded member; freeburn challenges are not on the progression-event path),
  rem BrnBurnoutSkillzManager.cpp (GameActionQueue typedef clash, not a DWARF
  rem ModeManager member), Debug/* components, *_EmbedGate/_AssertLayout/_embed_check
  rem (compile-scaffolding, gate-only by convention).
  rem [mbRecentStunt wave 2026-08-27] Hud/BrnHUDMessageLogic.cpp JOINS the mount: its
  rem four callers were un-parked because GenerateStuntMessage's vtable-dispatched
  rem WasStuntRecentlyPerformed is the image's ONLY drain of StuntModeScoring's
  rem mbRecentStunt latch -- parked, the second banked stunt of any offline stunt race
  rem fired the !mbRecentStunt invariant every frame.
  echo "%SRC%\GameSource\GameState\ModeManager\Hud\BrnHUDMessageLogic.cpp"
  rem PAIRED EDIT: the 14-line RETIRE list in BrnBaselineLinkStubs.cpp (seam audit
  rem S7) died in the same change that adds these lines -- the two must never
  rem coexist (LNK2005) and HasStuntModeEnded's return-true stub would end every
  rem stunt run on frame 1.
  echo "%SRC%\GameSource\GameState\ModeManager\BrnModeManager.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\BrnModeManager_Accessors.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\BrnModeManager_CheckpointSetup.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\BrnModeManager_Finish.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\BrnModeManager_IntroPlay.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\BrnModeManager_Lifecycle.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\BrnModeManager_Prepare.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\BrnModeManager_Start.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\BrnModeManager_TransmitCrash.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\BrnModeManager_UpdateMode.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\BrnModeManager_WorldTick.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnGameMode.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnOfflineGameMode.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnOnlineGameMode.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnGameModeParams.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnRaceMode.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnFaceOffMode.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnCrashMode.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnRoadRageMode.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnPursuitMode.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnBurningRoute.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnStuntAttackMode.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnSurvivor.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnOnlineRaceMode.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnOnlineRoadRageMode.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnOnlineStuntRunMode.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnOnlineBurningHomeRunMode.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnOnlineFreeBurnMode.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnOnlineFreeBurnLobbyMode.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModes\BrnOnlineShowtimeMode.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModeStates\BrnCountdownState.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModeStates\BrnInProgressState.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModeStates\BrnIntroState.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModeStates\BrnOnlineLoadingState.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModeStates\BrnOutroState.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModeStates\BrnQuitState.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\GameModeStates\BrnResultsState.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnScoringSystem_Finish.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnScoringSystem_Lifecycle.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnScoringSystem_Lookup.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnScoringSystem_Queries.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnScoringSystem_Standings.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnScoringSystem_Timer.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnScoringSystem_UpdateA.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnScoringSystem_UpdateB.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnStuntModeScoring_Combo.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnStuntModeScoring_Lifecycle.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnStuntModeScoring_Queries.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnStuntModeScoring_Register.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnStuntModeScoring_StuntTypes.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnStuntModeScoring_UpdatePass.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnStuntModeScoringOnline.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnBaseOnlineModeScoring.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnOnlineRaceModeScoring.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnOnlineRoadRageModeScoring.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnOnlineStuntRunModeScoring.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnOnlineBurningHomeRunModeScoring.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnCarData.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnBurnoutSkillzData.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnCrashModeScoring.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\BrnRoadRageModeScoringLinkStubs.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\Array_EActiveRaceCarIndex_7.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\Array_RecentCrash_64.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\RingBuffer_CgsID.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\Scoring\RingBuffer_Vector3.cpp"
  echo "%SRC%\GameSource\GameState\Progression\BrnProgressionManager_EventFinish.cpp"
  echo "%SRC%\GameSource\GameState\NetworkRoundManager\BrnNetworkRoundManager.cpp"
  rem [stuntrace mount closure 2026-08-26] the measured link-hole closers -- each verified
  rem 0-new-externals / 0-ODR by the closure verifier's trial link. NOT mounted (refuted):
  rem BrnMapManager.cpp + BrnSatNavTile.cpp (two undefined hand-declared CRT helpers in
  rem MapManager's transliteration; ctor gated in BrnHudStatesLinkStubs.cpp instead).
  echo "%SRC%\GameSource\GameState\SharedIO\BrnGameStateToGuiIOInterfaces.cpp"
  echo "%SRC%\GameSource\GameState\ModeManager\BrnModeManager_OnlineGridStubs.cpp"
  echo "%SRC%\SharedClasses\Traffic\BrnTrafficLightTrigger.cpp"
  echo "%SRC%\GameSource\GameState\StreetData\BrnChallengeHighScoreEntry.cpp"
  echo "%SRC%\SharedClasses\StreetData\BrnChallengeData.cpp"
  rem (BrnAICarOutputInterface.cpp mounts with the aimodule slice above -- both
  rem sessions added it 2026-08-26; the duplicate died in the merge.)
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnPositionIndicator.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnFreeburnChallengeStartComponent.cpp"
  rem BrnSatNavTile alone (0 new externals standalone): the MapManager ctor gate's member
  rem chain needs SatNavTile::sRect::sRect(); only the MapManager.cpp HALF of the pair is out.
  echo "%SRC%\SharedClasses\Gui\SatNav\BrnSatNavTile.cpp"
  echo "%SRC%\GameSource\GameState\RoadRules\BrnRoadRulesManager.cpp"
  echo "%SRC%\GameSource\GameState\EventQueue_RecordPropHitEvent_50.cpp"
  echo "%SRC%\GameSource\GameState\BrnGameEvents.cpp"
  echo "%SRC%\GameShared\GameClasses\Module\VariableEventQueue_1536_16.cpp"
  echo "%SRC%\SharedClasses\Trigger\BrnRegion.cpp"
  echo "%SRC%\SharedClasses\Trigger\BrnKillzone.cpp"
  echo "%SRC%\GameSource\World\EntityModules\TriggerEntityModule\SharedIO\BrnTriggerEntityModuleInputInterface.cpp"
  echo "%SRC%\GameSource\Game\GameBridgeGameStateToX_StuntGuiEvents.cpp"
  rem [stuntrace wave E1 2026-08-26] the event-flow translate arms (23/37/38/39/44/47/200/201
  rem -> GUI 93/289/321/322/166/234/307/311) + the event score/timer status builds (492/424/428).
  echo "%SRC%\GameSource\Game\GameBridgeGameStateToX_EventFlowGuiEvents.cpp"
  echo "%SRC%\GameSource\Game\GameBridgeGameStateToX_EventStatusGuiEvents.cpp"
  rem [event-starts wave 2026-08-27] the event-start table hop (GUI event 203).
  echo "%SRC%\GameSource\Game\GameBridgeGameStateToX_EventStartsGuiEvents.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wB_00.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wB_01.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wB_02.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wB_03.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wB_04.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wB_05.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wB_06.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wB_07.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wB_08.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wB_09.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wB_10.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wB_11.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wB_12.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wB_res.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wC_00.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wC_01.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wC_02.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wC_03.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wO_00.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_wO_01.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_gUI_01.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_gUI_02.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_gUI_03.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageAnalyzer_gUI_04.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageDirector.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageDirector_gUI_00.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiHudMessageDirector_gUI_01.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiCache_wB_01.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiCache_wB_02.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiCache_wB_03.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiCache_wB_05.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiFreeburnChallengeManager.cpp"
  echo "%SRC%\GameSource\GameState\BrnCgsPlayerName.cpp"
  echo "%SRC%\SharedClasses\DataLists\BrnHudMessageController.cpp"
  echo "%SRC%\SharedClasses\DataLists\ChallengeList.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\CgsGuiModule_AddGuiEvent_Inst.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\Resources\CgsGuiHudMessageType.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnInGameMessagesComponent.cpp"
  rem ---- end gateui wave block
  echo "%SRC%\GameSource\Gui\BrnGuiColourCalibrationScreen.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiAlwaysAvailableComponentsManager.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Permanent\Components\BrnEATraxInGameComponent.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Permanent\Components\BrnAchievementPopupComponent.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Permanent\Components\BrnOnlineInviteMessageComponent.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Permanent\Components\BrnSaveIconComponent.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Permanent\Components\BrnShowtimeMessageComponent.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\FlaptComponents\BrnGuiFlaptComponentUtils.cpp"
  rem ---- the real GUI flow-controller chain (GuiFsmController + BrnHudFlow's 14-state pool) ----
  echo "%SRC%\GameSource\Gui\BrnGuiFsmController.cpp"
  echo "%SRC%\GameSource\Gui\Flow\BrnBaseFlow.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\BrnHudFlow.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\BrnOverlayFlow.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnBaseOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnBaseWaitOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnBaseOkOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnBaseOkCancelOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnInvisibleOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnPreloadOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnInGameWaitOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnInGameOnlineWaitOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnInGameOnlineOkOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnInGameOnlineOkCancelOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Overlay\States\BrnInGameOnlineEnterFreeBurnOverlayState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\FlaptComponents\BrnGuiFlaptIconComponent.cpp"
  rem ---- overlay-state closure (2026-07-12): the committed Flapt ref layer + the ----
  rem ---- overlay/help components the BrnBase* overlay states link against.        ----
  echo "%SRC%\GameSource\Gui\Flow\Overlay\Components\BrnOverlayComponent.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\FlaptComponents\BrnGuiFlaptComponent.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\FlaptComponents\BrnGuiFlaptHelpItem.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\FlaptComponents\BrnFlaptButtonIcon.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\FlaptComponents\BrnGuiFlaptInterpolatorComponent.cpp"
  rem ---- HUD H2 (2026-08-25): the 2026-08-10 park is RETIRED -- the closures landed  ----
  rem ---- (DisplayRoad(ERoadIcon,bool) + gapcRoadIconNames + the sign-text colours in ----
  rem ---- the RoadSignIcon TU; SetBoundaries + the colour/mode setters in the timer   ----
  rem ---- TU; TextFieldRef::SetColour + both bare-value SetLocalisedText forms in the ----
  rem ---- TextFieldRef TU). The full RoadRuleComponent TU + the road-rule event       ----
  rem ---- family TU mount with them.                                                  ----
  echo "%SRC%\GameSource\Gui\Flow\Shared\FlaptComponents\BrnGuiFlaptRoadSignIconComponent.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\FlaptComponents\BrnGuiFlaptTimerFieldComponent.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnRoadRuleComponent.cpp"
  rem ---- HUD H3b 2026-08-25: THE SATNAV MINIMAP -- component + render chain,      ----
  rem ---- mounted together. SatNavComponent = the id-212 render-payload producer;  ----
  rem ---- SatNavRenderer = manager slot 1, draws the map quad + mask + icons;      ----
  rem ---- MapTransform statics recovered off the image; MapIconManager = the owner ----
  rem ---- handshake + sat-nav info set, its apt icon-pool passes are NAMED GATES;  ----
  rem ---- plus the road-sign manager slice, the NorthIndicator compass, the        ----
  rem ---- GuiTracker free-roam positions and the SatNav icon TU whose local        ----
  rem ---- FlaptIconComponent ODR fork is retired.                                  ----
  echo "%SRC%\GameSource\Gui\SatNav\BrnSatNavComponent.cpp"
  echo "%SRC%\GameSource\Gui\SatNav\BrnSatNavIcon.cpp"
  echo "%SRC%\GameSource\Gui\SatNav\BrnMapIconManager.cpp"
  echo "%SRC%\GameSource\Gui\SatNav\BrnGuiTracker.cpp"
  echo "%SRC%\GameSource\Gui\View\BrnRoadSignIconManager.cpp"
  echo "%SRC%\GameSource\Gui\CustomRenderer\Renderers\BrnSatNavRenderer.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnNorthIndicator.cpp"
  echo "%SRC%\SharedClasses\Gui\SatNav\BrnMapUtils.cpp"
  rem ---- stunt-race UI wave 2026-08-27: the MainMapComponent bodies the PRE_FLY_BY ----
  rem ---- mount executes (Construct/Prepare/RecvEvent + the zoom tables), plus the  ----
  rem ---- FLAG'd gate TU covering its still-unreconstructed siblings (Update/SetZoom/----
  rem ---- the GuiCache landmark faces/ConstructPatternLiveryList/MapManager::RecvEvent).----
  echo "%SRC%\GameSource\Gui\SatNav\BrnMainMap.cpp"
  rem [map wave 2026-08-27, b5-decomp 8fc3718a] BrnMainMapLinkGates.cpp is DELETED (all ten
  rem DELETE-WHENs satisfied); its two real homes mount in its place.
  echo "%SRC%\GameSource\Gui\SatNav\BrnMapManager.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiCache_wMap.cpp"
  rem ---- H3b link closure: the Im2d mask/boost command writers TU, the GuiCache ----
  rem ---- accessor legs the renderer/manager link against, and the progression   ----
  rem ---- event-record accessors.                                                ----
  echo "%SRC%\GameShared\GameClasses\Graphics\ImmediateMode\ImRenderBuffer\CgsIm2dRenderBuffer.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiCache_wB_04.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiCache_wB_07.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiCache_wB_09.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiCache_wH3b.cpp"
  rem ---- H3c link closure (2026-08-25): the sat-nav icon pass. UpdateSatNavIcons reads the
  rem  embedded 2D event-icon bank (GetEventIconPositions) for the LARGE-map proximity fade,
  rem  and GetSatNavIconStateForRival reads GetEventPositionOfRaceCar for the race-mode filter.
  rem  Both homes were reconstructed and simply never mounted.
  echo "%SRC%\GameSource\Gui\SatNav\BrnEventIconManager.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiCache_wB_06.cpp"
  echo "%SRC%\SharedClasses\Progression\BrnRaceEventData.cpp"
  echo "%SRC%\GameSource\Gui\Events\BrnGuiEventRoadRuleUpcomingRoads.cpp"
  rem ---- [driver-details pause wave 2026-08-28] the rank-progress RESPONSE event. Its
  rem  Construct @0x824F62F8 is the last hop of the START-button pause screen's licence
  rem  ladder (game action 181 -> GUI 438); GameBridgeGameStateToX_StuntGuiEvents.cpp's
  rem  case-181 arm calls it, and CrashNavDriverDetails::UpdateSetupLicense calls
  rem  GetPlayerRank. Reconstructed long ago, never mounted.
  echo "%SRC%\GameSource\Gui\Events\BrnGuiEventRankProgressResponse.cpp"
  echo "%SRC%\GameSource\Gui\Flapt\BrnFlaptMovieClipRef.cpp"
  echo "%SRC%\GameSource\Gui\Flapt\BrnFlaptTextFieldRef.cpp"
  echo "%SRC%\GameSource\Gui\Flapt\BrnFlaptFileRef.cpp"
  rem ---- the SCREEN flow container + its committed state set (2026-07-12) ----
  echo "%SRC%\GameSource\Gui\Flow\Screen\BrnScreenFlow.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnScreenStatesLinkStubs.cpp"
  rem (the dev-wave state TUs -- CarSelectOnlineEnd/CrashNavStats/CrashNavEnterOnlineX360/
  rem  PreRaceFlyBy -- bind when the ScreenFlow/HudFlow pool growth is integrated)
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnIntro.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnInGame.cpp"
  rem ---- car-select screen (2026-08-02): CarSelectVehicle derives from CarSelectMain, so the
  rem      base TU + its three wave-G partfiles + the embedded component TUs all bind here.
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCarSelectMain.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCarSelectMain_wG_01.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCarSelectMain_wG_02.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCarSelectMain_wG_03.cpp"
  rem  CarSelectVehicle re-homed onto CarSelectMain (2026-08-02): three partfiles
  rem  (statics+FSM / the screen build / input+events) + the online player-list ROW TU the
  rem  re-homed player list now embeds by value.
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCarSelectVehicle.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCarSelectVehicle_Components.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCarSelectVehicle_Input.cpp"
  rem  CarSelectLivery -- the CS_LIVERY screen, RECONSTRUCTED 2026-08-02 (it was a
  rem  three-method shell in BrnScreenStatesLinkStubs). Three partfiles: statics+FSM /
  rem  the screen build / input+events. This is the ACCEPT PATH of the Junkyard handover.
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCarSelectLivery.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCarSelectLivery_Components.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCarSelectLivery_Input.cpp"
  rem  wave-J partfile 04 (2026-08-03): HandleLobbyPlayerList @0x824B5190. Landed by Niaz in
  rem  b5-decomp fd0925f4 WITHOUT this mount line -- CarSelectLivery::Update calls it, so the
  rem  exe did not link until this was added here (contributors have no parent-repo access).
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCarSelectLivery_wJ_01.cpp"
  echo "%SRC%\GameSource\Gui\Components\BrnCarSelectOnlinePlayerListItem.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\Components\BrnManufacturerIcon.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnPlayerStatsBar.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\Components\BrnRivalTableCell.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\Components\BrnCarouselSliderBar.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\Components\BrnCarSelectOnlineCountdown.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\Components\BrnCarSelectOnlinePlayerList.cpp"
  rem ---- dev merge (2026-08-07): dev's restored BrnOnlinePlay.h embeds GuiNetworkPlayerStats
  rem ---- BY VALUE, so the scaffolded OnlinePlay ctor materialises its vtable, which needs the
  rem ---- real virtuals (dev a1cad009). _wL_01 (FormatNetworkStats) stays OUT: its only caller
  rem ---- (SetInfo) has no body in the tree, and it pulls four undefined NetworkPlayerStats/
  rem ---- ChallengeList symbols.
  echo "%SRC%\GameSource\Gui\Flow\Screen\Components\BrnGuiNetworkPlayerStats.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnComplexBar.cpp"
  rem ---- menu-toggle / colour-picker component cluster (2026-08-02, CarSelectLivery wave).
  rem      BrnGui::CarSelectLivery embeds a MenuToggleGroupVarSize<2> and a ColourMenuToggle
  rem      BY VALUE, so both -- and the ColourSelection / ColourSelectionItem / ColourField
  rem      chain the toggle owns -- bind here. ?????? All six TUs were previously unmounted AND
  rem      dispatched their sub-components through raw `mppVTable[slot]` / `*(void***)storage`
  rem      reads on modelled heads that nothing ever initialises; every one of those would
  rem      have jumped through an uninitialised pointer on the first call. They are by-name
  rem      calls now (see the banners in BrnMenuToggleGroup.cpp / BrnColourMenuToggle.cpp).
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnMenuToggle.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnMenuToggleGroup.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnColourMenuToggle.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnColourSelection.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnColourSelectionItem.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnColourField.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiWorldDataController.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnScreenLoading.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCrashNavOptions.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCrashNavColourCalibrate.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCrashNavEnterOnlineMod.cpp"
  rem ==== [pause soft-lock wave 2026-08-29] CN_SETTINGS, THE PAUSE SCREEN'S RB TAB =====
  rem  MEASURED SOFT-LOCK, now closed. The Driver Details pause screen DRAWS LB/RB prompts;
  rem  its actions 54/55 post TOGGLE_LEFT/TOGGLE_RIGHT (faithful -- X360 @0x824CF3B8 cases
  rem  '6'/'7' are bare SendStateEvent), and BRNSCREENFSM sends TOGGLE_RIGHT to CN_SETTINGS.
  rem  CrashNavSettings was a HEADER-ONLY SHELL, so OnEnter/Update/OnLeave were the
  rem  do-nothing CgsGui::State base: it registered for nothing, received nothing, and never
  rem  posted the resume the pause screen had already skipped. Baseline on b5 cb80d9b7:
  rem  after RB, ZERO changed pixels across 16,290 dumped presents (200 s) with the throttle
  rem  held, and three GUI_CANCEL taps did nothing. This TU lands the nine linkable X360
  rem  bodies (the 45/50 GO_BACK+resume arm among them); the two SKU/keyboard ones are
  rem  PARKED on missing PC platform leaves and cannot re-create the lock -- see its banner.
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCrashNavSettings.cpp"
  rem ==== [driver-details pause wave 2026-08-28] THE START-BUTTON PAUSE SCREEN ==========
  rem  MEASURED: pressing START in free burn now draws the real Driver Details screen --
  rem  the title, the Paradise licence card (player name, issue date, "UPGRADE IN 1 WIN"),
  rem  the stat panel and "B RETURN TO GAME" -- with the world FROZEN under it (world-region
  rem  frame delta 0.000 over 15 s while the card keeps animating) and a clean resume on Stop.
  rem  asserts=0. InGame::HandleControllerInput case 45 -> PauseGame(true,TRUE) ->
  rem  OpenDriverDetails() -> "TO_D_DETAIL" -> CN_D_DETAIL; all 16 X360 bodies, every .rdata
  rem  table read from the image. It OWNS maResourcesToLoad (the stand-in in
  rem  BrnScreenStatesDataLinkStubs.cpp is deleted in the same change).
  rem
  rem  #### KNOWN, AND NOT A DEFECT OF THIS SCREEN: THE *SECOND* START PRESS CRASHES. ####
  rem  Re-entering the screen AVs reading 0x4CF8 in AptCharacterAnimation::IncCharacterList
  rem  (via MakeCharacterAnimationInst <- AptLinker::Update <- AptAux::Update). It is an APT
  rem  UNLOAD/RELOAD LIFECYCLE hole, not a defect of this screen: OnLeave releases the
  rem  licence/photo-booth apt bundles exactly as the console's
  rem  CrashNavDriverDetails::OnLeave @0x824CEF18 does, and this build had NOTHING behind
  rem  that release. THREE of its halves were repaired this wave and each one is real:
  rem    1. CgsGuiResourceModulePC.cpp -- the host lead/attributed registries were
  rem       APPEND-ONLY, so a re-acquire resolved to a released entry and handed AddAptData
  rem       a null (that was 'Invalid memory resource in ParseResource' + 'Invalid resource
  rem       pointer'). Now swept against the live pool on every streamed-apt unload.
  rem    2. CgsGuiViewModule.cpp -- ProcessIncomingUnloadRequestNotification (X360
  rem       0x828586E8) was an EMPTY BODY. Reconstructed.
  rem    3. CgsAptDataHandler.cpp -- AptDataHandler::RemoveAptData (X360 0x8284A338) did not
  rem       exist at all, and BrnGuiModule's notification bridge forwarded only the type-14
  rem       LOADS to the view, never the type-15 unload requests, so the removal end of the
  rem       pair could not run. Both reconstructed/wired.
  rem  Result: asserts went 2 -> 0 and the failure moved one layer down, but the AV REMAINS.
  rem  What is still open is inside the Apt engine itself: the linker keeps instantiated
  rem  characters for a movie whose data has been released (nothing calls an Apt-side
  rem  unmount/release for the movie when its bundle goes). That is the next wave's target;
  rem  start at AptLinker::Update / MakeCharacterAnimationInst and at what the console does
  rem  between StateInterface::PlayAptMovie("", level) and the bundle unload.
  rem  TO TURN THE PAUSE SCREEN BACK OFF: comment out the ONE echo line below. Nothing else
  rem  needs changing -- the tree links either way.
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCrashNavDriverDetails.cpp"
  rem =====================================================================================
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCredits.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnPauseScreen.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnImageGallery.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnOnlineMarkMan.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnOnlineViewChallenges.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnOnlineFBurnQuickCustomCreate.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnGenericForwardState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnReplayLoading.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnReplayMain.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnReplayOutro.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnBrnDebug.cpp"
  echo "%SRC%\GameSource\Gui\Flow\PostEvent\States\Offline\BrnOfflineInstantResults.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\Components\BrnLargeCarComponent.cpp"
  echo "%SRC%\GameSource\Gui\Flow\PostEvent\States\Offline\BrnCompletedGame.cpp"
  echo "%SRC%\GameSource\Gui\Flow\PostEvent\States\Showtime\BrnShowtimeInstantResults.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\Components\Replays\BrnReplayHudMessageComponent.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\Shared\BrnScreenShared.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiOptionsDataProfile.cpp"
  rem ---- intro wave (2026-07-30): the licence / photo-booth screen components. All four
  rem ---- link gaps that kept them out are now closed:
  rem ----   GuiCache::EnsureResourceIsUnloaded / EnsureResourcesAreUnloaded  -> BrnGuiCache.cpp
  rem ----   Profile::GetLicenceIssuedDate / SetLicenceIssuedDateAsNow        -> BrnProfile.cpp (mounted above)
  rem ----   NetworkTexture::Prepare(char*, s32, s32, s32, PixelFormat)       -> the SECOND
  rem ----     X360 overload @0x82893A80 (caller-owned buffer), a sibling of the allocating
  rem ----     Prepare @0x82893928 -- never a signature conflict with it.
  echo "%SRC%\GameSource\Gui\Flow\Screen\Components\BrnLicenseComponent.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\Components\BrnPhotoBoothComponent.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\Components\BrnImageGalleryCarouselItem.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\Components\BrnImageGallerySelectable.cpp"
  rem ---- text-selection widget (2026-08-02): BrnGui::TextSelection was re-homed onto
  rem      BrnGui::SelectableGroup and grew its 100 TextSelectionItem rows + display
  rem      TextField, so the row TU must bind here (TextSelectionItem is polymorphic --
  rem      it overrides Selectable::Select -- and embedding 100 of them by value emits
  rem      its vtable, which needs Select()'s definition).
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnTextSelection.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnTextSelectionItem.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnIcon.cpp"
  rem intro wave (2026-07-30): HelpItem declares a VIRTUAL Construct, so its vtable must be
  rem emitted for any TU that embeds one by value -- BrnGui::Intro does, through
  rem BrnGui::PhotoBoothComponent's two HelpItem members.
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnHelpItem.cpp"
  echo "%SRC%\GameSource\Replays\Serialisers\BrnReplayGuiModuleSerialiser.cpp"
  echo "%SRC%\GameSource\Replays\BrnReplayGuiModuleStaticLayout.cpp"
  rem FLAG link scaffold: the SCREEN states' unrecovered .rdata tables + partial-state
  rem lifecycle gaps (see the file header audit).
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnScreenStatesDataLinkStubs.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\CgsEventObserver.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\CgsModelModuleIO_InputBuffer.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\CgsModelModuleIO_OutputBuffer.cpp"
  rem The REAL GuiResourceModule (FSM-bundle loading migrated off BrnGuiAptRuntime's host stand-in).
  echo "%SRC%\GameShared\GameClasses\Gui\Model\Resources\CgsGuiResourceModule.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\Resources\CgsGuiResourceModulePC.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\Resources\CgsGuiResourceModuleIO.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\Resources\CgsGuiResourceModuleIO_InputBuffer.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\Resources\CgsGuiResourceModuleIO_OutputBuffer.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnBootPreload.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnBootAttract.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnPostTitleScreenLoad.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnBootProfile.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnBootVideos.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnBootLoading.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnBootLegal.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnBootLegalBoundary.cpp"
  rem The in-game HUD states the 14-state pool instantiates: real TUs where they are
  rem header-homed (Paused/Idle/Crashed + the TextField component they embed), the link
  rem scaffold for the rest (see BrnHudStatesLinkStubs.cpp).
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnPausedHudState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnIdleHudState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnFBurnMainHudState.cpp"
  rem ---- ADDED 2026-08-27 (endcrash wave): BrnCrashedHudState.cpp was ON DISK since the
  rem   impact-time slice landed but was NEVER in this list -- the 8th sighting of that
  rem   class. It stayed invisible because its three functions were non-virtual helpers
  rem   nothing called; the moment the state got its OnEnter/OnLeave/Update overrides the
  rem   link broke with 3 LNK2001s from BrnHudFlow.obj. It is NOT covered by
  rem   BrnHudStatesLinkStubs.cpp (that file scaffolds RACE_MAIN / FBURN_MAIN /
  rem   CRASHEDSTNT only), so there was no ODR fork to retire -- just an absent TU.
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnCrashedHudState.cpp"
  rem ---- ADDED 2026-08-27 (crashed-stunt HUD wave): CRASHEDSTNT becomes REAL. The real
  rem   TU carries the recovered 4-entry resource table (.rdata 0x82F26488, count 4 at
  rem   0x82F264A8 -- the FLAG placeholder is paid off), the 12-entry event table at
  rem   0x8205B17C, the OnEnter/OnLeave/Update lifecycle and the COMPLETE UpdatePermenant
  rem   -- including the "END_CSTNT" arm the lua FSM maps back to state 2 RACE_MAIN.
  rem   The CRASHEDSTNT stub block in BrnHudStatesLinkStubs.cpp died in the same change.
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnCrashedStuntHudState.cpp"
  rem ---- stunt-race UI wave 2026-08-27: PRE_FLY_BY becomes REAL. The 7 wJ partfiles
  rem   (the complete PreRaceFlyByState) mount; the inert PRE_FLY_BY block in
  rem   BrnHudStatesLinkStubs.cpp was deleted in the same change (LNK2005 otherwise).
  rem   Their measured closure = BrnMainMap.cpp + BrnMainMapLinkGates.cpp (SatNav block).
  echo "%SRC%\GameSource\Gui\Flow\PreEvent\States\BrnPreRaceFlyBy_wJ_01.cpp"
  echo "%SRC%\GameSource\Gui\Flow\PreEvent\States\BrnPreRaceFlyBy_wJ_02.cpp"
  echo "%SRC%\GameSource\Gui\Flow\PreEvent\States\BrnPreRaceFlyBy_wJ_03.cpp"
  echo "%SRC%\GameSource\Gui\Flow\PreEvent\States\BrnPreRaceFlyBy_wJ_04.cpp"
  echo "%SRC%\GameSource\Gui\Flow\PreEvent\States\BrnPreRaceFlyBy_wJ_05.cpp"
  echo "%SRC%\GameSource\Gui\Flow\PreEvent\States\BrnPreRaceFlyBy_wJ_06.cpp"
  echo "%SRC%\GameSource\Gui\Flow\PreEvent\States\BrnPreRaceFlyBy_wJ_07.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnFriendsList.cpp"
  rem ---- LINK CLOSURE for the friends-list / boost-message landings (added 2026-08-26).
  rem   MEASURED: origin/dev c0dc4af2 does NOT link -- 15 unresolved externals. Two of its
  rem   own TUs were on disk but never added to this list (BrnBoostMessageManager.cpp,
  rem   BrnFriendsListEntry.cpp); the remaining seven symbols have no body anywhere and are
  rem   gated in BrnFriendsListLinkGates.cpp. See that file's banner.
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnFriendsListEntry.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnFriendsListLinkGates.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnBoostMessageManager.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnBoostMessageSlot.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnBoostMessageItem.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnFriendsListChangeIcon.cpp"
  rem (FriendsListEntry / the BoostMessage trio mount ABOVE with the friends-list
  rem tranche block -- both sessions added them 2026-08-26; the duplicates died in
  rem the merge. Select + the six other bodiless symbols live in
  rem BrnFriendsListLinkGates.cpp; LobbyNameCmp is the REAL vendor body in
  rem vendor\dirtysdk\src\lobbyname.cpp.)
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnDistrictMarker.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnJunctionInfoComponent.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnOdometerComponent.cpp"
  rem ---- stunt-race UI wave 2026-08-27: the EventInfoComponent (the in-event goal/
  rem   score/timer readout) -- base TU + two partfiles, mounted together (Construct
  rem   is the only path into the partfiles; ClearEventSpecificData is in the base).
  rem   TextFieldRef::GetText landed in the already-mounted BrnFlaptTextFieldRef.cpp.
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnEventInfo.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnEventInfo_wS1.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnEventInfo_wS2.cpp"
  rem ---- stunt-race UI wave 2026-08-27: RoadRuleShotComponent was fully bodied on
  rem   disk all along; its link residual (the two GuiCache accessors) lives in
  rem   BrnGuiCache_wS1.cpp. The Construct scaffold in BrnHudStatesLinkStubs.cpp was
  rem   deleted in the same change.
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnRoadRuleShotComponent.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiCache_wS1.cpp"
  rem ---- stunt-race UI wave 2026-08-27: RACE_MAIN becomes REAL. The base TU (the
  rem   21-entry resource table + OnEnter/OnLeave/UpdateSetupState family) + three
  rem   partfiles (wS2 Update/WFInit/Permenant/Reveal; wS3 Running/EventInfo/countdown;
  rem   wS4 ProcessAptEvents/BoostInfo/SatNav + the freeburn-challenge tickers). The
  rem   RACE_MAIN stub block in BrnHudStatesLinkStubs.cpp was deleted in the same change.
  rem   ChallengeListEntry.cpp joins for ChallengeListEntryAction::GetTargetValue (bodied
  rem   on disk, never listed -- the ticker's per-action target values).
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnRaceMainHudState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnRaceMainHudState_wS2.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnRaceMainHudState_wS3.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnRaceMainHudState_wS4.cpp"
  echo "%SRC%\SharedClasses\DataLists\ChallengeListEntry.cpp"
  rem   RACE_MAIN's measured link closure (2026-08-27 trial links): the online-timeout
  rem   timer (0 new externals) and the sat-nav zoom cache leg (wB_08; its duplicate
  rem   assert-less IsRoadRuleActive twin in BrnGuiCache.cpp was retired). The compass
  rem   TU and the player-position table pair were TRIED and REVERTED -- each opens more
  rem   holes than it closes (Compass: ShowPositionOnCompass/FormatDirectionLetters/
  rem   GetNumLocations; table pair: SingleComponent::SetCache/SetTitleText/SetSkillsText/
  rem   UsernameCompare/GetCurrentSkill) -- their RACE_MAIN-facing symbols are gated in
  rem   BrnHudStatesLinkStubs.cpp instead, all runtime-dead on the mode-7 path.
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnOnlineTimeoutTimerComponent.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiCache_wB_08.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnHudStatesLinkStubs.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnTextField.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnButtonIcon.cpp"
  rem The real title-menu frontend (replaces the retired MenuComponent facade).
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnSelectable.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnSelectableGroup.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnMenuItem.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnMenuComponent.cpp"
  rem  GUI table component family (2026-08-03). BrnOnlineCustomMatch.h embeds a BrnGui::Table
  rem  BY VALUE, so BrnScreenFlow's NewPoolState<OnlineCustomMatch> needs Table::Table(), which
  rem  needs TableRow's implicit ctor, which needs TableCell::TableCell(). All three TUs were
  rem  in the tree and none was mounted.
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnTable.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnTableRow.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnTableCell.cpp"
  rem  BrnGuiTextField.cpp homes TextField::SetColour @0x82481E48 + operator= @0x824470F0 and
  rem  had NEVER been mounted -- the mounted BrnTextField.cpp defines neither (no overlap, so
  rem  no LNK2005). TableCell::SetColourValue is the first mounted caller of SetColour.
  echo "%SRC%\GameSource\Gui\BrnGuiTextField.cpp"
  rem  GuiCache::GetOnlinePlayerInfoFromPlayerId, split out of BrnGuiCache.cpp for that TU's
  rem  documented include clash (same reason as BrnGuiCache_GetNumEventStarts.cpp).
  echo "%SRC%\GameSource\Gui\BrnGuiCache_GetOnlinePlayerInfoFromPlayerId.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\State\CgsGuiStateInterface.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\Model\State\CgsGuiState.cpp"
  echo "%SRC%\GameShared\GameClasses\Fsm\CgsState.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceID.cpp"
  echo "%SRC%\GameShared\GameClasses\Language\CgsLanguageManager.cpp"
  echo "%SRC%\GameShared\GameClasses\Language\Resources\CgsLanguageResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceTypeRegistry.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceBundleLoader.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourcePool.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceScratchPool.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourcePoolModule.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsPoolModuleIO_OutputBuffer.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceBundleLoaderModule.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceIOEvents.cpp"
  echo "%SRC%\GameShared\GameClasses\System\FileSystem\CgsFileSystem.cpp"
  echo "%SRC%\GameShared\GameClasses\System\FileSystem\CgsDeviceManager.cpp"
  echo "%SRC%\GameShared\GameClasses\System\FileSystem\CgsDeviceOperationPool.cpp"
  echo "%SRC%\GameShared\GameClasses\System\FileSystem\CgsFileLog.cpp"
  echo "%SRC%\GameShared\GameClasses\System\FileSystem\CgsFile_embed_check.cpp"
  echo "%SRC%\GameShared\GameClasses\System\FileSystem\Devices\CgsDevice.cpp"
  echo "%SRC%\GameShared\GameClasses\System\FileSystem\Devices\CgsDeviceAsyncOp.cpp"
  echo "%SRC%\GameShared\GameClasses\System\FileSystem\Devices\CgsDeviceMemFileSystem.cpp"
  echo "%SRC%\GameShared\GameClasses\System\FileSystem\Devices\CgsRemapDevice.cpp"
  echo "%SRC%\GameShared\GameClasses\System\FileSystem\Devices\CgsDevicePhysicalPC.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceModule.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceModuleIO.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceModuleIO_InputBuffer_GetResourceQueue.cpp"
  echo "%SRC%\GameSource\Resource\BrnGameDataModule.cpp"
  echo "%SRC%\GameSource\Resource\BrnResourceAllocator.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceHeap.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceBundle2.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsSmallResource.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsResourceTypeBase.cpp"
  echo "%SRC%\GameShared\GameClasses\Memory\CgsLinearMalloc.cpp"
  echo "%VEN%\PPMalloc\src\EAGeneralAllocator.cpp"
  echo "%VEN%\renderware\src\rwcore_alloc.cpp"
  echo "%VEN%\renderware\src\rw\ResourceAllocatorRegistry.cpp"
  echo "%VEN%\renderware\src\rw\DefaultSystemAllocatorInitializer.cpp"
  echo "%VEN%\renderware\src\rw\BaseResourceDescriptor.cpp"
  echo "%VEN%\renderware\src\rw\core\debug\DebugCriticalSection.cpp"
  echo "%VEN%\renderware\src\rw\core\debug\Manager.cpp"
  echo "%VEN%\renderware\src\rw\core\debug\Formatter.cpp"
  echo "%SRC%\GameShared\GameClasses\Memory\CgsDistributionStream.cpp"
  echo "%SRC%\GameShared\GameClasses\Memory\CgsScatterStream.cpp"
  echo "%SRC%\GameShared\GameClasses\Memory\CgsGatherStream.cpp"
  echo "%SRC%\GameShared\GameClasses\Memory\CgsHeapMalloc.cpp"
  rem PC-platform leaf: the low-4GB root reservation the serialised PointerFromU32 slots need.
  echo "%SRC%\GameShared\GameClasses\Memory\PC\CgsLowMemoryPC.cpp"
  echo "%SRC%\GameShared\GameClasses\Memory\CgsMemoryModule.cpp"
  echo "%SRC%\GameShared\GameClasses\Memory\CgsMemoryModuleIO.cpp"
  echo "%SRC%\GameSource\Resource\SharedIO\BrnGameDataAllocatorList.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Timer\CgsTimeUtils.cpp"
  rem ---- link-resolution: small self-contained reconstructed-body TUs the exe references ----
  echo "%SRC%\GameShared\GameClasses\Sound\Logic\CgsLogicContentDtor.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\CgsTestBedAllocator.cpp"
  echo "%SRC%\GameShared\GameClasses\Language\CgsLanguageManagerDebugComponent.cpp"
  echo "%SRC%\GameSource\Resource\BrnGameDataModuleIO.cpp"
  echo "%SRC%\GameSource\GameFlowController\TopLevel\BrnGameMainFlowCheckDiskSpace.cpp"
  echo /Fo"%OUT%\\obj\\" /Fe"%OUT%\\Burnout_PC.exe"
)

rem ---- deliberate source drop -- BOTH compile paths: rw-filesys device.cpp ------------------
rem The source list carries %SRC%\SDKs\EATech\rwcore\filesys\device.cpp, but its
rem rw::core::filesys::Device symbols are provided by AptRenderLinkStubs.obj, and compiling it
rem would add duplicate symbols plus an unlinked EA::Thread::Condition dependency. So it is
rem filtered out of the RSP here, before either compile path below runs.
findstr /v /c:"rwcore\filesys\device.cpp" "%RSP%" > "%RSP%.tmp"
move /y "%RSP%.tmp" "%RSP%" >nul

rem ---- compile + link: incremental parallel driver when a Python is available ---------------
rem tools\build\compile_exe.py compiles each TU to its own uniquely-named obj under obj\tu\
rem -- basename.crc32-of-path.obj, which retires the same-basename obj-clobber class the
rem legacy path below patches case by case -- tracks header deps via cl /showIncludes, and
rem recompiles ONLY the TUs whose source, headers or flags changed, in parallel. It then
rem links -- skipped too when nothing feeding the link changed -- and ends with a summary
rem repeating every warning and error, so diagnostics are never lost in the scroll.
rem Knobs: BRN_EXE_REBUILD=1 forces a full recompile. BRN_EXE_JOBS=N caps parallel cl count.
rem The probe RUNS each candidate rather than `where`-ing it: the Windows Store python
rem alias sits on PATH but is not a real interpreter, and `where` would pick it.
set "PY_CMD="
for %%P in (python python3 py) do (
    if not defined PY_CMD (
        %%P -c "raise SystemExit(0)" >nul 2>nul && set "PY_CMD=%%P"
    )
)
if defined PY_CMD goto driver_compile
echo WARNING: no Python interpreter found -- using the legacy serial full-rebuild path.
goto legacy_compile

:driver_compile
%PY_CMD% "%~dp0compile_exe.py" --base "%BASERSP%" --rsp "%RSP%" --out "%OUT%" -- /SUBSYSTEM:WINDOWS /MAP /OPT:REF /LIBPATH:"%FFM%\bin" "%OUT%\obj\burnout.res" d3d9.lib user32.lib gdi32.lib gdiplus.lib kernel32.lib ntdll.lib winmm.lib shell32.lib ole32.lib advapi32.lib avformat.lib avcodec.lib avutil.lib swscale.lib swresample.lib "%VEN%\lua\lua515.lib"
set "BUILD_ERR=%ERRORLEVEL%"
goto post_build

:legacy_compile
rem ---- OBJECT-NAME COLLISION FIX -- basename device.cpp appears twice -----------------------
rem The source list carried two device.cpp files with the SAME basename -- the rw-filesys one
rem is dropped above, this one remains:
rem   %SRC%\pc\gcm\renderengine\device.cpp          -- renderengine D3D9 Device
rem With /Fo pointing at a single obj dir, cl writes BOTH to obj\device.obj -- the second-compiled
rem one CLOBBERS the first, so which set of symbols survives depends on compile ORDER. Fix: the
rem renderengine device.cpp is compiled separately to a UNIQUE object and linked in below.
findstr /v /c:"pc\gcm\renderengine\device.cpp" "%RSP%" > "%RSP%.tmp"
move /y "%RSP%.tmp" "%RSP%" >nul
cl @"%BASERSP%" /c "%SRC%\pc\gcm\renderengine\device.cpp" /Fo"%OUT%\\obj\\renderengine_device.obj"
if errorlevel 1 ( echo ERROR: renderengine device.cpp precompile failed. & exit /b 1 )

rem ---- OBJECT-NAME COLLISION FIX -- Sound Logic vs Sound Playback basenames --------------------
rem CgsEnvironment.cpp and CgsVoice.cpp exist in BOTH Sound\Logic and Sound\Playback; with the
rem single obj dir the second compile clobbers the first and the linker drops one TU entirely.
rem Same fix as device.cpp above: the Playback pair is filtered out of the RSP and compiled
rem separately to UNIQUE objects, linked in below.
findstr /v /c:"Sound\Playback\CgsEnvironment.cpp" "%RSP%" > "%RSP%.tmp"
move /y "%RSP%.tmp" "%RSP%" >nul
findstr /v /c:"Sound\Playback\CgsVoice.cpp" "%RSP%" > "%RSP%.tmp"
move /y "%RSP%.tmp" "%RSP%" >nul
cl @"%BASERSP%" /c "%SRC%\GameShared\GameClasses\Sound\Playback\CgsEnvironment.cpp" /Fo"%OUT%\\obj\\playback_environment.obj"
if errorlevel 1 ( echo ERROR: Sound Playback CgsEnvironment.cpp precompile failed. & exit /b 1 )
cl @"%BASERSP%" /c "%SRC%\GameShared\GameClasses\Sound\Playback\CgsVoice.cpp" /Fo"%OUT%\\obj\\playback_voice.obj"
if errorlevel 1 ( echo ERROR: Sound Playback CgsVoice.cpp precompile failed. & exit /b 1 )

cl /nologo @"%RSP%" "%OUT%\\obj\\renderengine_device.obj" "%OUT%\\obj\\playback_environment.obj" "%OUT%\\obj\\playback_voice.obj" /link /SUBSYSTEM:WINDOWS /MAP /OPT:REF /LIBPATH:"%FFM%\bin" "%OUT%\\obj\\burnout.res" d3d9.lib user32.lib gdi32.lib gdiplus.lib kernel32.lib ntdll.lib winmm.lib shell32.lib ole32.lib advapi32.lib avformat.lib avcodec.lib avutil.lib swscale.lib swresample.lib "%VEN%\lua\lua515.lib"

set "BUILD_ERR=%ERRORLEVEL%"

:post_build
rem Convert the linker .map into the binary CgsMapFile the assert call-stack resolver reads.
if "%BUILD_ERR%"=="0" if exist "%OUT%\Burnout_PC.map" (
  where py >nul 2>&1
  if not errorlevel 1 (
    py "%ROOT%\tools\build\make_cgsmap.py" "%OUT%\Burnout_PC.map" "%OUT%\Burnout_PC.cgsmap"
  ) else (
    echo WARNING: Python launcher 'py' not found -- Burnout_PC.cgsmap NOT generated.
    echo          The assert call-stack resolver needs it. Install Python, or run:
    echo          python "%ROOT%\tools\build\make_cgsmap.py" "%OUT%\Burnout_PC.map" "%OUT%\Burnout_PC.cgsmap"
  )
)
rem Stage the FFmpeg runtime DLLs next to the exe so the movie player loads at runtime.
if "%BUILD_ERR%"=="0" copy /Y "%FFM%\bin\*.dll" "%OUT%\" >nul
rem Stage the XAudio2 redistributable next to the exe. AudioOutputPC::Open LoadLibrary's
rem xaudio2_9redist.dll by name and the exe directory is searched first, so this copy IS
rem the audio engine the game runs on (without it it falls back to the in-box xaudio2_9,
rem and on a pre-1803 Windows to nothing at all -- the game then runs muted).
if "%BUILD_ERR%"=="0" copy /Y "%XA2%\bin\x64\xaudio2_9redist.dll" "%OUT%\" >nul

endlocal & exit /b %BUILD_ERR%
