@echo off
rem Build the real-chain game exe: BrnMain -> CgsHardwareInit -> BrnGameModule ->
rem BrnRendererModule -> LoadingScreenRenderer (Option B loading-screen boot), now with the
rem resource/font subsystem so a loaded Default.font drives the bitmap debug text.
rem
rem The source list exceeds cmd's ~8191-char command-line limit, so the cl arguments (flags,
rem include dirs, sources, /Fo, /Fe) are written to a response file and passed via cl @file.
setlocal
set ROOT=%~dp0..\..
set SRC=%ROOT%\b5-decomp\src
set VEN=%ROOT%\b5-decomp\vendor
set RES=%ROOT%\b5-decomp\res
rem FFmpeg (movie player VP6/MP4 decode) - built by tools\build\build_ffmpeg.bat into vendor\ffmpeg-build\.
set FFM=%ROOT%\b5-decomp\vendor\ffmpeg-build
rem Game build output lives under build\game\ (build\tools\ holds tool binaries; see tools\build\build_tools.ps1).
set OUT=%ROOT%\build\game
set RSP=%OUT%\obj\build.rsp

rem Always initialize the VS 2022 x64 toolchain -- do NOT trust a stray cl already on PATH.
rem On a machine with the Xbox 360 SDK installed, ITS cl.exe is on PATH (and lacks the
rem standard/Windows headers), so a "where cl" shortcut picks the wrong compiler and the
rem build fails on <cstdint>/<Windows.h>. vcvars64 is idempotent + prepends the VS 2022
rem bin, so cl always resolves to VS 2022's cl, never the 360 SDK's. (Set VCVARS64 to
rem override which vcvars64.bat is used.)
rem Exception: if a modern MSVC (cl 19.x) is already on PATH -- e.g. CI ran
rem ilammy/msvc-dev-cmd -- trust it and skip the vcvars search. The 360 SDK's cl is
rem 14.x and won't match "Version 19.", so the guard above still holds locally.
rem IMPORTANT: probe with "where cl" FIRST. Piping a command that is not on PATH
rem (cl 2>&1 | findstr ...) aborts the whole batch with exit 255 -- and locally there is
rem NO cl until vcvars runs, so the bare pipe killed the build instantly before setup.
where cl >nul 2>&1
if errorlevel 1 goto need_vcvars
cl 2>&1 | findstr /C:"Version 19." >nul 2>&1
if not errorlevel 1 goto toolchain_ready
:need_vcvars
set "VCVARS="
if defined VCVARS64 if exist "%VCVARS64%" set "VCVARS=%VCVARS64%"
for %%P in (
  "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
  "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat"
  "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat"
  "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
) do if not defined VCVARS if exist "%%~P" set "VCVARS=%%~P"

if not defined VCVARS (
  echo ERROR: Visual Studio 2022 vcvars64.bat not found. Set VCVARS64 to its full path.
  exit /b 1
)
call "%VCVARS%" >nul 2>&1
if errorlevel 1 (
  echo ERROR: Failed to initialize the MSVC toolchain from "%VCVARS%".
  exit /b 1
)

:toolchain_ready
if not exist "%OUT%\obj" mkdir "%OUT%\obj"

echo Using environment: %VCVARS%

rc /fo"%OUT%\\obj\\burnout.res" "%RES%\burnout.rc"

rem ---- build the cl response file ----
> "%RSP%" (
  rem /Gy: function-level linking, so /OPT:REF (link line) can strip the never-called
  rem sibling controller bridges (Director/World/GameState) whose IO callees are unlinked.
  rem /O2: the exe had NO optimisation flag at all until the culling wave measured it --
  rem every per-entity frustum test, every dispatch walk and every VMX-derived math helper
  rem was running unoptimised, which is why culling cost more than the draws it saved.
  echo /nologo /EHsc /std:c++17 /permissive- /O2 /Gy /DWIN32 /D_WINDOWS
  echo /I"%SRC%" /I"%VEN%\EABase\include\Common" /I"%VEN%\EASTL\include" /I"%VEN%\EAThread\include" /I"%VEN%\renderware\include" /I"%VEN%\PPMalloc\include" /I"%VEN%\coreallocator\include" /I"%VEN%\zlib\src" /I"%FFM%\include" /I"%VEN%\lua\src"
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
  echo "%SRC%\GameShared\GameClasses\System\PC\CgsHardwareSkuPC.cpp"
  echo "%SRC%\GameShared\GameClasses\System\PC\CgsAudioOutputPC.cpp"
  echo "%SRC%\GameShared\GameClasses\System\PC\CgsMovieAudioPC.cpp"
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
  rem ---- / WorldBridgeCrashToEntityModules / WorldBridgeInputToEntityModules /  ---
  rem ---- WorldBridgePhysicsToScene) are NOT mounted: each drags 1-23 unresolved  ---
  rem ---- module-IO accessors/setters that are declaration-only (cost rule), so   ---
  rem ---- their bridges stay boot-gated in WorldLinkStubs.cpp. Mount them with    ---
  rem ---- the entity-module IO pass that lands those accessors.                   ---
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnRaceCarEntityModule.cpp"
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule.cpp"
  echo "%SRC%\GameSource\World\Trigger\BrnTriggerEntityModule.cpp"
  echo "%SRC%\GameSource\World\AI\BrnAIModule.cpp"
  echo "%SRC%\GameSource\World\CrashModule\BrnCrashModule.cpp"
  echo "%SRC%\GameSource\World\EnvironmentManager\BrnEnvironmentManager.cpp"
  rem (sky wave: the environment utils; the sky-dome draw TUs are held
  rem  out of the link until the renderengine VertexDescriptor/ImRendererBase
  rem  closure lands -- see the sky wave log section 5)
  echo "%SRC%\SharedClasses\World\BrnEnvironmentUtil.cpp"
  echo "%SRC%\GameSource\World\EnvironmentMap\BrnEnvironmentMap.cpp"
  echo "%SRC%\GameSource\World\ShadowMap\BrnShadowMap.cpp"
  echo "%SRC%\GameSource\World\BrnPlaceOnTrackManager.cpp"
  echo "%SRC%\GameSource\Physics\BrnPhysicsModule.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsSceneManagerModule.cpp"
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
  echo "%SRC%\GameShared\GameClasses\Graphics\CgsBufferedDispatchFrame.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\CgsMaterialAssembly.cpp"
  echo "%SRC%\pc\gcm\renderengine\VertexProgramState.cpp"
  echo "%SRC%\pc\gcm\renderengine\XenonD3D9Shims.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CacheManager\CgsTriangleCacheManager.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsEntityManager.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsSceneManagerIO_InputBuffer_Update.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\CgsSceneManagerIO_SceneUpdate.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\ContactGen\CgsOverlapCullingModule.cpp"
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
  echo "%SRC%\SharedClasses\Physics\Props\BrnPropGraphicsListResourceType.cpp"
  echo "%SRC%\SharedClasses\Physics\Props\BrnPropInstanceDataResourceType.cpp"
  echo "%SRC%\SharedClasses\Sound\World\BrnStaticSoundMapResourceType.cpp"
  echo "%SRC%\GameSource\Physics\BrnPhysicsModuleIO_InputBuffer.cpp"
  echo "%SRC%\GameSource\Physics\BrnPhysicsModuleIO_InputBuffer_Accessors.cpp"
  echo "%SRC%\GameSource\Physics\DeformationManager\SharedIO\BrnDeformationOutputInterface.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BrnVehicleManagerOutputInterface.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BrnVehicleOutputInterface.cpp"
  echo "%SRC%\GameSource\Resource\SharedIO\BrnAssetIds.cpp"
  echo "%SRC%\GameSource\Resource\SharedIO\BrnGameDataRequestQueue.cpp"
  echo "%SRC%\GameSource\World\AI\Route\BrnRouteMapModule.cpp"
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeEntityModulesToScene.cpp"
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeSceneToEntityModules.cpp"
  echo "%SRC%\GameSource\World\Bridges\WorldBridgeToEntityModules.cpp"
  echo "%SRC%\GameSource\World\BrnBaseStreamer.cpp"
  echo "%SRC%\GameSource\World\BrnWorldModuleIO_DispatchInputBuffer.cpp"
  echo "%SRC%\GameSource\World\BrnWorldModuleIO_DispatchOutputBuffer.cpp"
  echo "%SRC%\GameSource\World\BrnWorldModuleIO_UpdateOutputBuffer.cpp"
  echo "%SRC%\GameSource\World\CrashModule\BrnRaceCarCrash.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropEntityModuleIO_InputBuffer_Dispatch.cpp"
  echo "%SRC%\GameSource\World\EntityModules\PropEntityModule\BrnPropEntityModuleIO_OutputBuffer_Prepare.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnRaceCarEntityModuleIO.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\SharedIO\BrnRCEntityActiveRaceCarOutputInterface.cpp"
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\SharedIO\BrnRCEntityGlobalRaceCarOutputInterface.cpp"
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModuleIO_InputBuffer_Getters.cpp"
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\SharedIO\BrnTrafficNetworkOutputInterface.cpp"
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\SharedIO\BrnTrafficSoundInterfaces.cpp"
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
  echo "%SRC%\GameSource\World\EntityModules\WorldEntityModule\SharedIO\BrnWorldEntityRequestInterface.cpp"
  echo "%SRC%\vendor\renderware\collision\BitTable.cpp"
  echo "%SRC%\GameSource\World\WorldLinkStubs.cpp"
  echo "%SRC%\GameSource\Director\Camera\BrnCameraState.cpp"
  echo "%SRC%\GameSource\Director\Camera\BrnDepthOfField.cpp"
  echo "%SRC%\GameSource\Director\Camera\BrnCameraValidityAccount.cpp"
  echo "%SRC%\GameSource\Director\Camera\Utils\CameraUtils.cpp"
  echo "%SRC%\GameSource\GameState\BrnGameStateModuleIO.cpp"
  echo "%SRC%\GameSource\Director\Camera\SharedIO\BrnPlayerInfo.cpp"
  echo "%SRC%\GameSource\Replays\BrnReplayStatusInterface.cpp"
  echo "%SRC%\GameSource\World\CrashModule\SharedIO\NetworkInputInterface.cpp"
  echo "%SRC%\GameSource\Network\BrnNetworkModuleIO.cpp"
  echo "%SRC%\GameSource\Network\SharedIO\BrnNetworkModuleGameStateIOInterfaces.cpp"
  echo "%SRC%\GameSource\Network\SharedIO\BrnNetworkModuleInGamePlayerStatusInterface.cpp"
  echo "%SRC%\GameSource\Physics\VehicleManager\SharedIO\BrnVehicleEvents.cpp"
  echo "%SRC%\GameSource\Game\BrnGlobalCpuMonitors.cpp"
  echo "%SRC%\GameSource\GameFlowController\TopLevel\BrnGameMainFlowStates.cpp"
  echo "%SRC%\GameSource\GameFlowController\TopLevel\BrnGameMainFlowInGameState.cpp"
  echo "%SRC%\GameSource\Sound\Module\BrnRootSoundModule.cpp"
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
  echo "%SRC%\GameShared\GameClasses\Development\PerfMon\Cpu\CgsPerfMonCpu.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\PerfMon\DebugComponent\CgsDebugComponentPerfMonCpu.cpp"
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
  echo "%SRC%\SDKs\EATech\include\Apt\AptRenderHooks.cpp"
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
  echo "%SRC%\SDKs\EATech\rw\math\vpu\vector3.cpp"
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
  echo "%SRC%\SDKs\EATech\AptRenderLinkStubs.cpp"
  echo "%SRC%\SDKs\EATech\AptGlobals.cpp"
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
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\CgsDebugFontBringUp.cpp"
  echo "%SRC%\GameShared\GameClasses\Development\DebugSystem\Render\CgsDebug3DImmediateRender.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\CgsRwRasterResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\CgsRwTextureStateResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\RenderWare\CgsMaterialStateResourceType.cpp"

  echo "%SRC%\GameShared\GameClasses\RenderWare\cross\CgsModelResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\Instances\CgsInstanceListResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\Instances\CgsInstance.cpp"
  echo "%SRC%\GameShared\GameClasses\System\Resource\CgsEntryListResource.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\View\AptInterface\CgsAptDataHeader.cpp"
  echo "%SRC%\SharedClasses\Gui\Flapt\BrnFlaptFile.cpp"
  echo "%SRC%\SharedClasses\Gui\Flapt\BrnFlaptFileResourceType.cpp"
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
  echo "%SRC%\GameShared\GameClasses\Geometric\Primitives\PolygonSoup\CgsPolygonSoupListResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\Geometric\Primitives\PolygonSoup\CgsPolygonSoupListSpatialMap.cpp"
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
  echo "%SRC%\GameShared\GameClasses\SceneManager\Contactgen\CgsSceneSweeperDebugComponent.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\TriangleCollision\CgsTriangleCollisionDebugComponent.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\Zones\Resources\ZoneListResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\SceneManager\Zones\Zone.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\CgsSoundUtils.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\CgsMemBase.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Logic\CgsMicrophone.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Logic\CgsStateManager.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Logic\CgsEnvironment.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Logic\CgsVoiceHierarchy.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Logic\CgsVoiceHierarchyResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\AEMS\CgsAemsFactory.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\CgsCommon.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\CgsRegistry.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\Plugins\Streaming\internal\sndplayer1.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\Plugins\Streaming\internal\sndplayer1shared.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\RWAC\CgsSnrResourceType.cpp"
  echo "%SRC%\GameShared\GameClasses\Sound\Playback\Splicer\CgsSplicerFactory.cpp"
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
  echo "%SRC%\GameShared\GameClasses\System\Timer\CgsTimerStatusInterface.cpp"
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
  rem  NOTE: %SRC%\GameSource\Director\BrnDirectorResourceManager.cpp is NOT mounted either.
  rem  It is the same reverted pattern: it declares its OWN local `struct
  rem  DirectorResourceManager { DirectorResourceManager(); }` and writes the real object
  rem  through raw console byte offsets (552/568..1592/1608/1616/1624). Those offsets are the
  rem  4-byte-pointer CONSOLE layout, so on x64 the ctor would scribble across the live class
  rem  (and across the DirectorModule that embeds it). It also collides at link with the
  rem  header's implicit default ctor (LNK2005 vs BrnGameModule.obj). The real class in
  rem  BrnDirectorResourceManager.h default-constructs correctly; its Prepare is stubbed in
  rem  DirectorLinkStubs.cpp. DELETE-WHEN: that TU is rewritten against named members.
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
  rem (Each cam's Parameters::Serialise<S> visitor stays OUT of the link, in its own
  rem  *Parameters.cpp sibling -- it drags the three camera-tunings serialisers in and none
  rem  of them is on the runtime director path.)
  echo "%SRC%\GameSource\Director\Arbitrator\BrnDirectorArbitrator.cpp"
  echo "%SRC%\GameSource\Director\Arbitrator\BrnDirectorArbitratorState.cpp"
  echo "%SRC%\GameSource\Director\Arbitrator\BrnDirectorArbitratorStateContainer.cpp"
  echo "%SRC%\GameSource\Director\Arbitrator\BrnDirectorArbitratorSharedCameraContainer.cpp"
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
  echo "%SRC%\SharedClasses\Trigger\BrnGenericRegion.cpp"
  echo "%SRC%\SharedClasses\Trigger\BrnTriggerData.cpp"
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
  echo "%SRC%\GameShared\GameClasses\Gui\CgsSaveLoad.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\CgsGuideIntegration.cpp"
  echo "%SRC%\GameShared\GameClasses\Gui\CgsGuiModuleIO_OutputBuffer.cpp"
  echo "%SRC%\GameSource\Gui\SaveLoad\BrnGuiSaveLoadProfile.cpp"
  echo "%SRC%\GameSource\Gui\SaveLoad\BrnGuiSaveLoadProfileDLC1.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiOptionsDataProfileDLC1.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiEventTypeDefs.cpp"
  echo "%SRC%\GameSource\Gui\CustomRenderer\Renderers\BrnBoostBarRenderer.cpp"
  echo "%SRC%\GameSource\Gui\CustomRenderer\Renderers\BrnCrashNavIconRenderer.cpp"
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
  rem ---- l2-into-dev merge link closure (dev waves grew shared TUs; their homes join;
  rem      the cascade-heavy waves -- ScreenFlow/HudFlow new states, CgsRegistry schema
  rem      web, Attrib node web -- are reverted-in-merge to l2 pending integration) ----
  echo "%SRC%\SDKs\EATech\include\NFSMix\NFSMixMapLinkStubs.cpp"
  echo "%VEN%\renderware\src\rw\core\stdc\stdc.cpp"
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
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCarSelectVehicle.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnScreenLoading.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCrashNavOptions.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCrashNavColourCalibrate.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\BrnCrashNavEnterOnlineMod.cpp"
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
  echo "%SRC%\GameSource\Gui\Flow\PostEvent\States\Offline\BrnCompletedGame.cpp"
  echo "%SRC%\GameSource\Gui\Flow\PostEvent\States\Showtime\BrnShowtimeInstantResults.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\Components\Replays\BrnReplayHudMessageComponent.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\States\Shared\BrnScreenShared.cpp"
  echo "%SRC%\GameSource\Gui\BrnGuiOptionsDataProfile.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\Components\BrnImageGalleryCarouselItem.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Screen\Components\BrnImageGallerySelectable.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnTextSelection.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnIcon.cpp"
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
  rem header-homed (Paused/Idle + the TextField component they embed), the link
  rem scaffold for the rest (see BrnHudStatesLinkStubs.cpp).
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnPausedHudState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnIdleHudState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnFBurnMainHudState.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnFriendsList.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\Components\BrnFriendsListChangeIcon.cpp"
  echo "%SRC%\GameSource\Gui\View\BrnDistrictMarkerComponent.cpp"
  echo "%SRC%\GameSource\Gui\Flow\HUD\States\BrnHudStatesLinkStubs.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnTextField.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnButtonIcon.cpp"
  rem The real title-menu frontend (replaces the retired MenuComponent facade).
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnSelectable.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnSelectableGroup.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnMenuItem.cpp"
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnMenuComponent.cpp"
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
  echo "%SRC%\SDKs\EATech\include\Apt\AptRandom.cpp"
  echo "%SRC%\SDKs\EATech\include\Apt\AptActionInterpreterParseStream.cpp"
  echo /Fo"%OUT%\\obj\\" /Fe"%OUT%\\Burnout_PC.exe"
)

rem ---- OBJECT-NAME COLLISION FIX (basename `device.cpp` appears twice) ----------------------
rem The source list carries two `device.cpp` files with the SAME basename:
rem   %SRC%\SDKs\EATech\rwcore\filesys\device.cpp   (rw filesys Device)
rem   %SRC%\pc\gcm\renderengine\device.cpp          (renderengine D3D9 Device)
rem With /Fo pointing at a single obj dir, cl writes BOTH to obj\device.obj -- the second-compiled
rem one CLOBBERS the first, so which set of symbols survives depends on compile ORDER (fragile: it
rem flips when the source list changes, then the link fails with unresolved renderengine::Device*
rem OR duplicate rw::filesys::Device* symbols). The build was only "passing" because the renderengine
rem device.obj was clobbering the rw-filesys one (whose rw::core::filesys::Device symbols are provided
rem by AptRenderLinkStubs.obj + which drags an unlinked EA::Thread::Condition dependency). Fix: keep
rem the renderengine device.cpp (compiled separately to a UNIQUE object, linked in) and DROP the
rem rw-filesys device.cpp from the build (its symbols come from AptRenderLinkStubs -- the prior state).
findstr /v /c:"pc\gcm\renderengine\device.cpp" "%RSP%" > "%RSP%.tmp"
move /y "%RSP%.tmp" "%RSP%" >nul
findstr /v /c:"rwcore\filesys\device.cpp" "%RSP%" > "%RSP%.tmp"
move /y "%RSP%.tmp" "%RSP%" >nul
cl /nologo /EHsc /std:c++17 /permissive- /DWIN32 /D_WINDOWS ^
  /I"%SRC%" /I"%VEN%\EABase\include\Common" /I"%VEN%\EASTL\include" /I"%VEN%\EAThread\include" /I"%VEN%\renderware\include" /I"%VEN%\PPMalloc\include" /I"%VEN%\coreallocator\include" /I"%FFM%\include" /I"%VEN%\lua\src" ^
  /c "%SRC%\pc\gcm\renderengine\device.cpp" /Fo"%OUT%\\obj\\renderengine_device.obj"
if errorlevel 1 ( echo ERROR: renderengine device.cpp precompile failed. & exit /b 1 )

cl /nologo @"%RSP%" "%OUT%\\obj\\renderengine_device.obj" /link /SUBSYSTEM:WINDOWS /MAP /OPT:REF /LIBPATH:"%FFM%\bin" "%OUT%\\obj\\burnout.res" d3d9.lib user32.lib gdi32.lib kernel32.lib ntdll.lib winmm.lib shell32.lib ole32.lib avformat.lib avcodec.lib avutil.lib swscale.lib swresample.lib "%VEN%\lua\lua515.lib"

set "BUILD_ERR=%ERRORLEVEL%"
rem Convert the linker .map into the binary CgsMapFile the assert call-stack resolver reads.
if "%BUILD_ERR%"=="0" if exist "%OUT%\Burnout_PC.map" py "%ROOT%\tools\build\make_cgsmap.py" "%OUT%\Burnout_PC.map" "%OUT%\Burnout_PC.cgsmap"
rem Stage the FFmpeg runtime DLLs next to the exe so the movie player loads at runtime.
if "%BUILD_ERR%"=="0" copy /Y "%FFM%\bin\*.dll" "%OUT%\" >nul
rem Stage locally converted native-x64 FLApt HUD bundles when present. These are
rem generated/licensed assets and remain outside source control.
if "%BUILD_ERR%"=="0" if exist "%OUT%\_staging_uiassets\FLAPTHUD.BUNDLE" copy /Y "%OUT%\_staging_uiassets\FLAPTHUD.BUNDLE" "%OUT%\" >nul
if "%BUILD_ERR%"=="0" if exist "%OUT%\_staging_uiassets\FLAPTHUDSD.BUNDLE" copy /Y "%OUT%\_staging_uiassets\FLAPTHUDSD.BUNDLE" "%OUT%\" >nul

endlocal & exit /b %BUILD_ERR%
