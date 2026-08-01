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
  rem ---- / WorldBridgeCrashToEntityModules / WorldBridgeInputToEntityModules /  ---
  rem ---- WorldBridgePhysicsToScene) are NOT mounted: each drags 1-23 unresolved  ---
  rem ---- module-IO accessors/setters that are declaration-only (cost rule), so   ---
  rem ---- their bridges stay boot-gated in WorldLinkStubs.cpp. Mount them with    ---
  rem ---- the entity-module IO pass that lands those accessors.                   ---
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnRaceCarEntityModule.cpp"
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
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnActiveRaceCarRenderParams.cpp"
  rem (pose wave 2026-08-01: RaceCar::Construct/Prepare/AddToWorld/UpdatePositioningData/
  rem  AssignActiveRaceCar/ToBeRenderedDamaged are now called by the real attach chain.)
  echo "%SRC%\GameSource\World\EntityModules\RaceCarEntityModule\BrnRaceCar.cpp"
  echo "%SRC%\SharedClasses\World\BrnWorldRegion.cpp"
  echo "%SRC%\GameSource\World\EntityModules\TrafficEntityModule\BrnTrafficEntityModule.cpp"
  echo "%SRC%\GameSource\World\Trigger\BrnTriggerEntityModule.cpp"
  echo "%SRC%\GameSource\World\AI\BrnAIModule.cpp"
  echo "%SRC%\GameSource\World\CrashModule\BrnCrashModule.cpp"
  echo "%SRC%\GameSource\World\EnvironmentManager\BrnEnvironmentManager.cpp"
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
  echo "%SRC%\pc\gcm\renderengine\SkyDomeProgramsPC.cpp"
  echo "%SRC%\GameShared\GameClasses\Graphics\ImmediateMode\CgsIm3dSkyDome.cpp"
  echo "%SRC%\GameSource\Graphics\ImmediateMode\BrnIm3d.cpp"
  echo "%SRC%\GameSource\Graphics\BrnSkyDomeManager.cpp"
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
  rem  ⚠️ ICEFile.cpp is mountable only because FileClose was split into ICEFileClose.cpp:
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
  echo "%SRC%\GameSource\World\WorldLinkStubs.cpp"
  echo "%SRC%\GameSource\Director\Camera\BrnCameraState.cpp"
  echo "%SRC%\GameSource\Director\Camera\BrnDepthOfField.cpp"
  echo "%SRC%\GameSource\Director\Camera\BrnCameraValidityAccount.cpp"
  echo "%SRC%\GameSource\Director\Camera\Utils\CameraUtils.cpp"
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
  rem ⭐ FINAL PRODUCER WAVE (2026-08-01) -- THE JUNKYARD CAR-SELECT FSM ITSELF.
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
  echo "%SRC%\SharedClasses\Progression\BrnProgressionData.cpp"
  rem ⭐ TRIGGERS wave (2026-08-01) -- THE TRIGGERS.DAT LOADER.
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
  echo "%SRC%\GameSource\GameState\TriggerQueryManager\BrnTriggerQueryManager_Prepare.cpp"
  rem intro wave (2026-07-30): the live BrnProgression::Profile TU. Needed by
  rem BrnGuiModule::Prepare (Profile::Construct seeds mbIsNewProfile = true, the
  rem first-boot INTRO gate) and by the licence component (GetLicenceIssuedDate /
  rem SetLicenceIssuedDateAsNow).
  echo "%SRC%\GameSource\GameState\Progression\BrnProfile.cpp"
  rem ...and the two TUs BrnProfile::SetPlayerLicencePicture links against (the licence
  rem mugshot wrapper + the RGB->A1R5G5B5 converter).
  echo "%SRC%\GameShared\GameClasses\Network\Texture\CgsNetworkTexture.cpp"
  echo "%SRC%\GameShared\GameClasses\Network\Utilities\CgsNetworkImageConverter.cpp"
  echo "%SRC%\GameSource\Director\Camera\SharedIO\BrnPlayerInfo.cpp"
  echo "%SRC%\GameSource\Replays\BrnReplayStatusInterface.cpp"
  echo "%SRC%\GameSource\World\CrashModule\SharedIO\NetworkInputInterface.cpp"
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
  rem (Each cam's Parameters::Serialise<S> visitor stays OUT of the link, in its own
  rem  *Parameters.cpp sibling -- it drags the three camera-tunings serialisers in and none
  rem  of them is on the runtime director path.)
  echo "%SRC%\GameSource\Director\Arbitrator\BrnDirectorArbitrator.cpp"
  echo "%SRC%\GameSource\Director\Arbitrator\BrnDirectorArbitratorState.cpp"
  echo "%SRC%\GameSource\Director\Arbitrator\BrnDirectorArbitratorStateContainer.cpp"
  echo "%SRC%\GameSource\Director\Arbitrator\BrnDirectorArbitratorSharedCameraContainer.cpp"
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
  rem  ⭐ ArbStateRoaming::Update @0x822643A0 is now WRITTEN (it did not exist anywhere in the
  rem  tree, and BrnArbStateRoaming.h deliberately omitted the override, so vtable slot 2 fell
  rem  through to ArbitratorState::Update's empty body -- meState froze at E_STATE_PREPARING
  rem  for the whole session and ProcessPossibleStateChanges, the ONLY writer of
  rem  E_STATE_CHANGING_TO_CAR_SELECT, was never called). Its four LNK2005 stubs are gone from
  rem  DirectorLinkStubs.cpp.
  rem  ⚠️ BrnArbStateRoaming.cpp DID NOT COMPILE before this wave (its Construct called a
  rem  two-argument MomentSelector::AddMoment that does not exist and its Prepare passed a
  rem  GameState where a BehaviourManager& is required) -- the ledger said `reviewed`.
  rem  MEASURED with scratchpad\ice5_list.py + ice5_net.py against the object list DERIVED FROM
  rem  THIS BAT: these four together are NET +0 unresolved. The order matters --
  rem  BrnArbStateRoaming alone is +7, +MomentSelector/+MomentController/+EffectTrigger is +4,
  rem  and the last 4 (MomentController::NewMoment, MomentHandle::Release,
  rem  MomentSelector::Update, SelectBestMomentWithExclusion) are the GROUP F stubs at the foot
  rem  of DirectorLinkStubs.cpp, which is where the moment sub-system's DELETE-WHEN lives.
  echo "%SRC%\GameSource\Director\Arbitrator\States\BrnArbStateRoaming.cpp"
  echo "%SRC%\GameSource\Director\MomentController\BrnMomentSelector.cpp"
  echo "%SRC%\GameSource\Director\MomentController\BrnMomentController.cpp"
  rem  BrnDirectorEffectTrigger.cpp joins the link at last: the note further down claiming it
  rem  costs two real unresolved externals is now STALE -- EffectInterface::HookExists is
  rem  bodied in it (from @0x8221E268) and RegisterStartingBackgroundEffectWithName from the
  rem  three stores the console inlines at @0x82232F20. Camera::StopCurrentEffect @0x82205BB8
  rem  and Camera::RequestStartEffectHook are bodied there too.
  echo "%SRC%\GameSource\Director\Utils\BrnDirectorEffectTrigger.cpp"
  rem ---- TENTH PASS (2026-08-01): ArbStateCarSelect -- THE REAL CAMERAS --------------------
  rem  ⭐⭐ The state that owns the junkyard shot-group setup, the three authored ICE intro
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
  rem  ⚠️ The FOURTH/FIFTH/SIXTH-PASS notes below quoting 54 / 31 / 13 / 12 unresolved for this
  rem  same set are ALL STALE: that was before CameraReference::Setup was bodied, before the
  rem  BehaviourInterpolate ODR fork was retired, and before the EIGHTH PASS closure set.
  echo "%SRC%\GameSource\Director\Arbitrator\States\BrnArbStateCarSelect.cpp"
  echo "%SRC%\GameSource\Director\Camera\Behaviours\BrnBehaviourIceAnim.cpp"
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
  rem  ⛔⛔ THE "no body anywhere" LIST ABOVE IS RETRACTED (2026-08-01, ICE take-runtime wave).
  rem  It was a NAME search, and the X360 export set does not carry these under a name. Every
  rem  entry on it is now bodied and the whole ICE data layer is MOUNTED (see the take-runtime
  rem  block near the top of this file for the recovery). ⭐ THE LESSON, which generalises far
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
  rem  ⚠️ The "13" in the FOURTH PASS above is ArbStateCarSelect ALONE; 31 is all three camera
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
  rem  ⛔⛔ THE BIGGER FINDING: ArbStateCarSelect can never leave E_STATE_INACTIVE on this build,
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
  rem  ⚠️ Do not read "-8" as "-8 net": count the SET, not the closures.
  rem  ⭐ GetSelectedGameplayCamera -- the one the FIFTH PASS singled out as un-stubbable
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
  rem  ⚠️⚠️ A LIVE ODR FORK found on the way, NOT fixed: there are TWO
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
  rem  ⭐ AND ClearBaseFirstFrameGate IS MIS-NAMED. The store IS verified -- ArbStateCarSelect::
  rem  Prepare emits `stb r23, 0x28(behaviour)` at 0x8226F0C4 and 0x8226F1A8 (pseudocode
  rem  `*(GetBehaviour(handle) + 40) = 0`). But BehaviourIceAnim's canonical Behaviour base ends
  rem  well before +0x28 (vptr, meTimestepType @+4, five flag bytes @+8..+0xC, mpcDebugParametersName
  rem  @+0x10) and GetCollisionPolicy returns `this + 0x20`, so byte +0x28 is mCollisionPolicy
  rem  +0x08 -- a VisibilityCollisionPolicy field, inside maReservedToVehiclePredictor
  rem  [+0x08, +0x70). It is NOT a base gate. Name it on the POLICY when that span is carved.
  rem
  rem  ⭐ THE iceanim ShotReference HAZARD IS NOW SETTLED (what the right answer is, not the fix):
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
  rem  ⚠️ MOUNTING THE THREE CAMERA TUs IS STILL BLOCKED. Twelve is not zero, and an exe does
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
  rem  ⛔⛔ AND THE REAL NEWS, WHICH IS NOT ABOUT LINK CLOSURE:
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
  rem      ⚠️ Case 13 (CHANGING_TO_CAR_SELECT, @0x8226548C) MUST be in the slice: if
  rem      ArbStateCarSelect::Prepare declines, meState parks on 0xD and case 13 is the retry.
  rem    - COST: two unmounted prerequisites are called UNCONDITIONALLY from the DRIVING arm --
  rem      MomentSelector::Update @0x82239FC0 (425 asm lines, no PC body) and
  rem      ArbStateRoaming::ProcessPossiblePaybackEffects @0x82208BA8 (117 lines, no PC body;
  rem      BrnArbStateRoaming.h:82 wrongly records it as "not in this TU's X360 set").
  rem    - ⛔ AND ArbUtils::ChangeToStateWithoutRelease -- the function that performs the
  rem      hand-off -- is a __debugbreak() TRAP STUB in BrnDirectorArbitratorUtils.h:50. Even a
  rem      perfect ladder would trap there. Body it from @0x821FE2B8 FIRST.
  rem      ⚠️ Its console parameter order is INVERTED vs the committed declaration: the console
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
  echo "%SRC%\GameSource\Gui\Flow\Shared\Components\BrnTextSelection.cpp"
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
