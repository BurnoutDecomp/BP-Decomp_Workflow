#include "GameShared/GameClasses/Development/PerfMon/Gpu/CgsPerfMonGpu.h"
#include "pc/gcm/renderengine/FrameProfile.h"
#include "GameShared/GameClasses/Core/CgsAssertProbePC.h"
#ifdef AddMonitor
#undef AddMonitor
#endif
#include "SharedClasses/DataLists/VehicleListEntry.h"
#include "GameSource/Gui/Events/BrnGuiPFXEvents.h"                     // BrnGui::GuiPFXHookEnumeration (case 501 size pin)
#include "GameShared/GameClasses/Containers/CgsArray.h"
#include "GameSource/Game/BrnGameModule.hpp"
#include "GameSource/Input/GameInputActions.h" // E_GAMEINPUTACTIONS_START (X360 action slot 8)
#include "GameSource/Resource/BrnResourceAllocator.h"
#include "GameShared/GameClasses/Core/CgsAssert.h"   // CgsDev::Assert
#include "GameShared/GameClasses/Development/BrnDiagFilmLatch.h" // [diag] BrnDiag::gFilmLatch (time-dilation capture arm)
#include "SDKs/EA/GameTalk/GameTalk.h"               // EA::GameTalk::GameTalkMessage (RenderMetricsMessageHandler)
#include "GameSource/Gui/BrnGuiEventTypeDefs.h"      // BrnGui::GuiAudioTriggerEvent (GUI-out event 201) + GuiEventProgressionProfileData (350)
#include "GameSource/Game/GameBridgeGameStateToX.h"  // BrnGame::BridgeGameStateToGui_EventStatus (the GUI-leg status seam)
#include "GameSource/GameState/Progression/BrnProfile.h" // BrnProgression::Profile (the action-193 payload's first word)

#include <cstring>   // memset
#include <string.h>  // _stricmp (RenderMetricsMessageHandler; MSVC canonical, not declared by <cstring>)
#include <chrono>    // the ToGui repeat-clock feed (FLAG PC time source: wall clock)
#include <cstdlib>   // getenv / strtol -- BridgeGuiToGame's BRN_POSTFX_CALIBRATION_TEST hook
#include <cstdio>    // snprintf -- BridgeGuiToGame's [calib] change line
#include <cstddef>   // offsetof -- the 545/546 payload layout pins in BridgeGuiToGame
#include "rw/math/vpu/matrix44affine_operation.h"

#include "GameShared/GameClasses/System/Input/PC/CgsInputPadsPC.h" // CgsInput::InputPadsPC (the PC pad-fill leaf)
#include "GameShared/GameClasses/Module/CgsModuleIOHelper.h"       // [FX-RUMBLE3] CgsModule::IOHelper (DoUpdate_InputPreWorld's "InputPreWorld")
#include "GameShared/GameClasses/Gui/CgsGuiModule.h" // CgsGui::GuiModule::AddGuiEvent (the world-load report below)
#include "GameShared/GameClasses/Gui/CgsGuiEventTypeDefs.h" // CgsGui::GuiEventTimeInfo (the per-frame GUI timestep)
#include "GameSource/Game/BrnLoadingScreenRenderer.h" // BrnGame::ELoadingScreenCommand (BridgeGuiToGame's command slot)
#include "GameSource/Resource/BrnGameDataModuleIO.h" // GameDataIO::InputBuffer/OutputBuffer (GamePrepare's request bracket)
#include "GameShared/GameClasses/System/Resource/CgsResourceIOEvents.h" // CgsResource::Events::AcquireResourceResponse (GamePrepare's acquire drain)
#include "rw/rwcore_structs.h"                       // rw::ResourceAllocatorRegistry::GetDefaultAllocator (the debug-font texture state)
#include "pc/gcm/renderengine/device.h"               // renderengine::GetDisplayRefreshRate (the step-9 timer rate)
#include "GameShared/GameClasses/System/Timer/CgsFrameInterpolation.h" // ⚠️ FLAG PC QoL: the 60Hz-sim / uncapped-render blend
#include "GameShared/GameClasses/Development/DebugSystem/Interface/CgsDebugInterface.h" // RegisterFunction (the Debug/Sim actions)
#include "GameShared/GameClasses/Development/DebugSystem/Render/CgsDebugRender.h"
#include "GameSource/GameState/BrnGameEvents.h"
#include "GameSource/Graphics/BrnRendererModuleIO.h"    // RendererIO::InputBuffer/OutputBuffer (GamePrepare's renderer pair)
#include "GameSource/Director/DirectorModule/BrnDirectorModuleIO.h"          // DirectorIO::InputBuffer (DoUpdate_Director)
#include "GameSource/Director/DirectorModule/BrnDirectorModuleIOOutputBuffer.hpp" // DirectorIO::OutputBuffer::GetCameraOutput (DoUpdate_Sound)
#include "GameSource/Replays/BrnReplayModuleIO.h"                            // ReplayIO::OutputBuffer_PreSim::GetStatusInterface (DoUpdate_Sound)
#include "GameSource/Effects/SharedIO/BrnEffectsModuleIO_OutputBuffer.h"     // EffectsIO::OutputBuffer (DoUpdate_Sound lock-only participant)
#include "GameSource/World/BrnWorldModuleIO_DispatchInputBuffer.h"
#include "GameSource/World/BrnWorldModuleIO_DispatchOutputBuffer.h"
#include "GameSource/Effects/SharedIO/BrnEffectsModuleIO_DispatchInputBuffer.h"
#include "GameSource/Effects/SharedIO/BrnEffectsModuleIO_InputBuffer.h"
#include "GameSource/Sound/Module/SharedIO/BrnPreUpdateSharedIo.h"   // AudioEffectsMessageQueue (the empty-queue construct in DoUpdate_Effects)      // EffectsIO::InputBuffer (DoUpdate_Effects / BridgeEntityToEffects)
#include "GameSource/GameState/BrnGameStateModuleIO.h" // GameStateModuleIO::OutputBuffer (BridgeGameStateToDirector)
#include "GameSource/Director/DirectorModule/BrnDirectorModuleIOSceneQuery.h" // DirectorIO::SceneQuery{Input,Output}Buffer
#include "GameShared/GameClasses/SceneManager/CgsSceneManagerIO.h"   // SceneManagerIO::InputBuffer_Query / OutputBuffer (the external query leg)
#include "GameShared/GameClasses/Module/CgsModuleUtils.h"            // CgsModule::LockBuffersForIO / UnlockBuffersForIO
#include "GameSource/Director/Camera/SharedIO/BrnPlayerInfo.h"       // [DIAG BRN_CAMCOLLIDE_DIAG] Camera::VehicleInfo
#include "vendor/renderware/collision/CollisionVolume.hpp"          // [DIAG BRN_CAMCOLLIDE_DIAG] rw::collision::SphereVolume
#include "GameSource/Effects/Particles/ParticleModuleBringUp.h"               // BrnParticle::PCBringUpProduceParticleRenderData (DoDispatch's particle-render-data seam)
#include "GameSource/World/EntityModules/RaceCarEntityModule/SharedIO/BrnRaceCarEntityModuleOutputInterface.h" // RCEntityActiveRaceCarOutputInterface + BrnPhysics::Vehicle::RaceCarState (DoDispatch's TempRaceCarStateCache seam)
#include "GameShared/GameClasses/System/PC/BrnNetHarnessPC.h" // BrnNetHarnessPC::InjectGuiEvents (the LAN test harness hook)

// The in-game flow-state latch (BrnGameMainFlowInGameState.cpp) -- the world-load
// stand-in below keys its loading-complete report on it.
namespace renderengine { void PublishPresentDiagnosticsPC(); }
namespace BrnGameMainFlowController { extern bool gBrnInGameStateActive; }

// ---- Xbox 360 XDK entry point (real prototype lives in the XDK). Displays the system
// "dirty disc" error UI for the given signed-in user. ------------------------------------
extern "C" unsigned long XShowDirtyDiscErrorUI(unsigned long dwUserIndex);

// The high-resolution frame timer DebugManagerRender's fps ring reads (defined in
// CgsTimeUtils.cpp; declared locally by convention -- see that TU's note).
namespace CgsSystem { u32 GetSystemTimerBaseTime(); u32 GetSystemTimerFrequency(); }

// [DIAG] The time-dilation film latch (BrnDiagFilmLatch.h). Defined here because
// BrnGameModule::UpdateTimers is its only writer; read by the back-buffer writer in
// pc/gcm/renderengine/device.cpp under BRN_FRAME_DUMP_ARM=slomo. NOT in the X360 binary.
// The trailing -1.0f is mfLiveBoostFraction's "nothing published yet" sentinel; its one
// writer is BridgeWorldVehicleDataToGui (GameBridgeWorldToGui.cpp).
// The last five fields are the TYRE-MARK latch/telemetry (muSkidLatched, muTrailSegments and
// the last laid segment's contact point); their one writer is EffectsModule::HandleWheels,
// beside its AddTrailSegment call.
namespace BrnDiag
{
    FilmLatch gFilmLatch = { 0u, 0.0f, 0.0f, 1.0f, 0.0f, -1.0f,
                             0u, 0u, 0.0f, 0.0f, 0.0f,
                             0.0f, 0.0f, 0.0f,
                             0u, 0u, 0u, 0.0f };   // the [dv] one-step velocity latch
}

namespace BrnGame
{
    // File-scope globals the X360 GameMain references:
    //   byte_82FAEB90  - the debug force-assert toggle (_lbForceAssert); fires a guarded
    //                    assert when set so a build can be forced to break into the assert path.
    //   dword_83084890 - a gate cleared while the simulation sub-steps run and set once they
    //                    complete; the dispatch/render side reads it. File-scope here, promoted
    //                    to a shared global when its other readers are reconstructed.
    static bool         _lbForceAssert = false;
    static volatile s32 sbSimUpdateComplete = 0;
    bool                sbShowStreamStallMessage = false; // byte_82FAE28A
    // Mutable UI latch from ARTIST byte_82FAE28C. Its original symbol and startup writer are
    // unresolved; findinit finds only the BridgeGuiToGame read/clear sites.
    static bool         sbForceQuitToStartMenu;
    // ARTIST 0x823BCF40 passes the exact 28-row console table at 0x82CDBEB8 to
    // PostMappingRequest(port=-1). These bytes match the recovered rows in CgsInputPadsPC.cpp;
    // keep them typed as the ActionMapping records consumed by the real IO.
    static const CgsInput::InputIO::ActionMapping KA_CONSOLE_DEFAULT_GAME_INPUT_MAPPING[28] =
    {
        { { 37, 41, 58, 14 } }, { { 38, 42, 60, 15 } },
        { { 39, 43, 59, 16 } }, { { 40, 44, -1, 17 } },
        { { 8, 45, -1, -1 } }, { { 50, 46, -1, 36 } },
        { { 13, 47, -1, 34 } }, { { 12, 48, -1, 35 } },
        { { 3, 49, -1, 19 } }, { { 11, 53, 50, 21 } },
        { { 2, 51, -1, 20 } }, { { 5, 52, -1, 18 } },
        { { 6, 54, -1, 24 } }, { { 7, 55, -1, 25 } },
        { { 1, 56, -1, 22 } }, { { 0, 57, -1, 23 } },
        { { -1, 41, -1, 26 } }, { { -1, 42, -1, 27 } },
        { { -1, 43, -1, 28 } }, { { -1, 44, -1, 29 } },
        { { -1, -1, -1, 30 } }, { { -1, -1, -1, 31 } },
        { { -1, -1, -1, 32 } }, { { -1, -1, -1, 33 } },
        { { 0, 41, -1, 30 } }, { { 1, 42, -1, 31 } },
        { { -1, 43, -1, 32 } }, { { -1, 44, -1, 33 } }
    };
    static bool sbInitialInputMappingPosted = false; // ARTIST byte_82FAE28B, BSS-zeroed.

    BrnGameModule::BrnGameModule()
        : mpUpdateInputBufferStack(0)
        , mpUpdateOutputBufferStack(0)
        , mbSimPaused(false)
        , mbDiskError(false)
        , mbControllerDisconnected(false)
        , mbSkipVideos(false)
        , mpReusableLoadingScreenAllocator(0)
        , mbPrevStalled(false)
        , mbStalled(false)
        , mbRequestDoStepFrame(false)
        , mbRequestDoPlayFrame(false)
        , mbWorldStreamingRequestedStall(false)
        , mbStreamingStalled(false)
        , mbIsLoadingScreenVisible(false)
        // ⭐ SEEDED 2026-08-17 (boot audit F-P1-6). Construct's step 3 stores 7 at
        // gm+0x9A0650, and E_RELEASESTAGE_DONE is 7 -- the console parks the release ladder
        // at DONE so a Release() reached before Prepare has armed it answers true and walks
        // away. Ours was never initialised at all: it only worked because the game module is
        // a file-scope static and zero-inits to E_RELEASESTAGE_START, which is the OPPOSITE
        // meaning -- a Release() from there walks straight into releasing unprepared modules.
        // Same seed BrnBaseFlow::Construct already applies to its own release stage, and the
        // precondition the teardown loop (F-P0-8) needs before it can ever be wired.
        , meReleaseStage(E_RELEASESTAGE_DONE)
        , meGamePrepareStage(E_GAMEPREPARESTAGE_START)
        , meGameUpdateStage(E_GAMEUPDATESTAGE_PREPARE)
        , miNumSimFramesRequired(0)
        // ⭐ CONSOLE SEEDS RESTORED 2026-08-16 (boot audit F-P1-13). Construct @0x823C9EA8's
        // frame-rate block stores type 1 (MULTIPLE_CAPPED) at gm+0x9A0B88 and the four step
        // bytes 1, 3, 1, 1 -- i.e. one simulation step minimum, up to THREE per rendered
        // frame. We seeded SINGLE/max 1, which is a different machine: capped at one sim
        // step, a frame that overruns its budget makes the SIMULATION run slow instead of
        // catching up over the next few frames. Everything downstream that reads
        // GetCurrentTimeStep -- physics, the director's behaviour advance, the streamer's
        // per-frame budget -- inherits that.
        , meFrameRateManagerType(CgsSystem::E_FRAMERATEMANAGER_MULTIPLE_CAPPED)
        // ⚠️ FLAG PC QUALITY-OF-LIFE, 2026-08-17: THE CONSOLE SEED IS 1, AND THIS IS 0.
        //
        // This single byte is the whole "60 Hz simulation, uncapped renderer" switch, and it
        // is the ONE deliberate departure from the frame-rate block restored above.
        //
        // The console is vsync-locked at the rate its simulation runs at, so demanding at
        // least one simulation step per rendered frame is not a policy there -- it is a
        // restatement of the hardware. On a PC it is not: with VSync=0 in config.ini (or any
        // panel above 60 Hz) the renderer runs as fast as it can, and a mandatory step per
        // frame made the ENTIRE simulation run at the render rate. Measured on a 144 Hz
        // panel: 144 ticks a second, i.e. the game, its physics, its timers, its cameras and
        // its streaming budget all at 2.4x speed.
        //
        // A minimum of ZERO lets CgsSystem::FrameRateManager::UpdatePostRenderWait pace the
        // simulation off the real-time clock instead -- exactly 60 steps per second however
        // many frames get drawn -- and publish the leftover fraction of a step as the
        // interpolation alpha the render legs blend with (CgsFrameInterpolation.h). The
        // maximum of 3 is unchanged and still the console's: that is the catch-up budget for
        // a frame that overran, and it is what stops a hitch turning into a death spiral.
        //
        // Everything else about the machine -- MULTIPLE_CAPPED, the max, the cumulative
        // accounting, the backlog repair -- is the console's, untouched. Restore 1 here and
        // the whole build reverts to console-locked pacing with no other change (the alpha
        // pins at 1.0 and every blend degenerates to "use the current state").
        , mi8FrameRateMinSteps(0)
        , mi8FrameRateMaxSteps(3)
        , mi8ActualFrameRateMinStepsThisFrame(1)
        , mi8ActualFrameRateMaxStepsThisFrame(1)
        , mbSteppingFrames(false)
        , mbDoStep(false)
        , mbStopStepping(false)
        , mpGuiInputBuffer(0)
        , mpGuiViewInputBuffer(0)
        , mpGuiModelOutputBuffer(0)
        , mpGuiOutputBuffer(0)
        , mpDirectorOutputBuffer(0)
        , mpWorldUpdateOutputBuffer(0)
        , mpEffectsOutputBuffer(0)
        , mpNetworkOutputBuffer(0)
        , mbDispatchCameraPublished(false)
        , miInputModuleState(0)
        , miPlayer0ControllerPort(0)
        , miSecondaryControllerPort(0)
        , mbGuiAcceptsControllerInput(false)
        , mbGuiSuppressMenuAccept(false)
        , miLanguageCycleTimerLo(0)
        , mfLanguageCycleTimerFrac(0.0f)
        , mfLookbackHoldTimer(0.0f)
        , miRenderMetricsRequested(0)
    {
        // (The X360 ctor does not touch mCpuMonitors -- Construct() sentinel-fills and
        // registers the monitors, at its X360 position.)
    }

    BrnGameModule::~BrnGameModule()
    {
    }

    // @ BrnGameModule.cpp:155 (X360 0x823C9EA8) - construct the game module: base, debug
    // systems, the CPU monitor registrations, then EVERY engine module (X360 order), then the
    // flow state machine. Sites the X360 body has that are still gated on unreconstructed
    // members/subsystems are flagged inline.
    void BrnGameModule::Construct()
    {
        // X360 step 1: the module base (resets the prepare/release stages + constructs the two
        // DataBuffers -- flag/pointer init only).
        CgsModule::ModuleSingleBuffered::Construct();

        // [gated] X360 steps 2-3: CheckClassSizes, then the game-state field seeds at
        // +10094156..+10097260 (release stage = 7, module counts 11/4, the engine-modules-loaded
        // flag = 0) -- those words fall in this layout's omitted member ranges.

        // Per-frame IO buffer stacks the update spine + the scripted module loads allocate their
        // per-frame IO buffers on. [PC stand-in] On the X360 these five stacks are OWNED BY main()
        // (0x827E60D8) -- UpdateInput/UpdateOutput 0x780000, ResourceInput 0x40000, ResourceOutput
        // 0x20000, Dispatch 0x18000 bytes, align 128, carved from the boot allocator -- and handed
        // to BrnGameModule::Prepare (vtable +64, 0x823DB848), which stores them at +10055424..
        // Until that Prepare + the allocator layer land, two fixed scratch blocks stand in.
        static CgsModule::IOBufferStack sUpdateInputStack;
        static CgsModule::IOBufferStack sUpdateOutputStack;
        // FLAG PC-platform leaf: sizing. The DOCUMENTED X360 value is 0x780000 each (main()
        // @0x827E60D8), but that is a 32-bit-pointer budget: on this LLP64 host every IO
        // buffer carrying pointers/handles is wider than its console twin, and
        // WorldModule::Update pushes ~30 of them (several ~800 KB) in one frame. With
        // 0x780000 the world drive overflowed the stacks mid-frame -- CreateIOBuffer then
        // returns NULL and the failure only surfaces later as a "not Constructed" assert on
        // the buffer that was never allocated (IOBufferStack::Alloc now names the overflow
        // when it happens). Doubled to 0x1000000 each; the console ratio is documented above.
        static u8 saUpdateInputMem[0x1000000];
        static u8 saUpdateOutputMem[0x1000000];
        // ⭐ ALIGNMENT CORRECTED 2026-08-16 (boot audit F-P0-5). main @0x827E60D8 prepares ALL
        // FIVE of its IOBufferStacks with alignment 0x80; this pair passed 16 while the
        // dispatch stack below already passed 128. Latent -- nothing in the current buffer
        // set needs more than 16 -- but it is the console's value, and an under-aligned
        // stack is the kind of thing that only shows up when a vector-typed member lands in
        // a buffer somewhere downstream.
        sUpdateInputStack.Construct("UpdateInput");
        sUpdateInputStack.Prepare(saUpdateInputMem, sizeof(saUpdateInputMem), 128);
        sUpdateOutputStack.Construct("UpdateOutput");
        sUpdateOutputStack.Prepare(saUpdateOutputMem, sizeof(saUpdateOutputMem), 128);
        mpUpdateInputBufferStack = &sUpdateInputStack;
        mpUpdateOutputBufferStack = &sUpdateOutputStack;

        // The dispatch-thread input pair (X360: DispatchThreadInputBufferManager::Construct
        // @0x823CBCE0 from Prepare @0x823DB848, on the dedicated Dispatch stack main() carves
        // -- 0x18000 bytes, see the stack note above). [PC stand-in placement: constructed
        // here with the other stack scaffolding until the real Prepare stage-machine lands;
        // the stack size is the documented console value.]
        static CgsModule::IOBufferStack sDispatchStack;
        static u8 saDispatchMem[0x18000];
        sDispatchStack.Construct("Dispatch");
        sDispatchStack.Prepare(saDispatchMem, sizeof(saDispatchMem), 128);
        mDispatchThreadInputBufferManager.Construct(&sDispatchStack);

        // The calibration settings BridgeGuiToGame publishes every frame -- Construct @0x823C9EA8
        // seeds them (`*(v9 + 10096740) = 50; *(v9 + 10096744) = 50; *(v9 + 10096748) = 1;`): the
        // game's default slider position, i.e. the post-fx composite's NEUTRAL brightness/contrast.
        miBrightness                        = 50;
        miContrast                          = 50;
        mbEnableCalibrationUnfriendlyPostFx = true;

        // X360 step 4: the debug manager (params block seeded from unk_820DC120 = the real
        // DebugManagerConstructParameters::DEFAULT + the six overrides below +
        // Allocators::mpInternalDebugAllocator as the RW allocator). Construct runs the console's
        // full bring-up itself - assert system, rw debug manager, critical section, buffered
        // renderer, UI, the three built-in components, CalculateBuildDate and ConstructRenderer -
        // so no separate ConstructRenderer call exists here, exactly as @0x823C9F44-90.
        // [gated] the "Force Quit to Start Menu" debug toggle + the FOPEN "%sMAP_ARTIST.BIN"
        // memory-map name globals that follow on the X360.
        // ⭐ THE REAL CONSTRUCT PARAMS, RECOVERED 2026-08-17 (boot audit F-P1-7). We passed
        // DebugManagerConstructParameters::DEFAULT straight through. The console does NOT:
        // @0x823C9F44-84 it copies DEFAULT onto the stack (the bdnz word loop) and then
        // OVERRIDES six fields before calling Construct. Read off the stores, with the struct
        // offsets from the declaration:
        //
        //   sth 0x300 -> +0    miPerfMonCpuCount          = 768
        //   stw 0     -> +4    miPerfMonLogBufferSize     = 0
        //   sth 0x78  -> +12   miFunctionPoolSize         = 120
        //   sth 0x190 -> +14   miVariablePoolSize         = 400
        //   sth 0x1F4 -> +16   miVariableMetadataPoolSize = 500
        //   stb 0xF   -> +18   miConsoleLineCount         = 15
        //   stw <alloc> -> +20 mpRwAllocator (Allocators::mpInternalDebugAllocator, asserted
        //                      non-null @0x823C9F8C -- still the allocator follow-on here)
        //
        // miMenuWindowPoolSize / miMenuPoolSize are the only two it leaves at DEFAULT.
        //
        // The perfmon count is the one that mattered: DEFAULT carried 256, which had already
        // been raised 64 -> 256 once when the world module's ~60 extra monitors overflowed it
        // and AddMonitor started returning -1. The console's own figure is 768 -- three times
        // that headroom -- so the ceiling this build kept bumping into was never the console's.
        {
            CgsDev::DebugManagerConstructParameters lParams =
                CgsDev::DebugManagerConstructParameters::DEFAULT;
            lParams.miPerfMonCpuCount          = 768;   // 0x300
            lParams.miPerfMonLogBufferSize     = 0;
            lParams.miFunctionPoolSize         = 120;   // 0x78
            lParams.miVariablePoolSize         = 400;   // 0x190
            lParams.miVariableMetadataPoolSize = 500;   // 0x1F4
            lParams.miConsoleLineCount         = 15;    // 0xF
            // FLAG PC-platform leaf: reserve space for the opt-in reflection
            // and small-caster controls in addition to the original UI pools.
            lParams.miVariablePoolSize         += 128;
            lParams.miVariableMetadataPoolSize += 256;
            // ARTIST823C9FC8 supplies the public GlobalDebug allocator wrapper.
            // It is separate from the temporary default used during memory-map setup.
            lParams.mpRwAllocator = BrnResource::GetDebugAllocator();
            mDebugManager.Construct(&lParams);
        }

        // X360 Construct @0x823CA000 registers this mutable bool with an empty path. The raw
        // path pointer (0x820046A7) is the NUL terminator at the end of "%s%s%s".
        {
            CgsDev::DebugInterface lDebugInterface(&mDebugManager);
            lDebugInterface.RegisterVariable(&sbForceQuitToStartMenu, "", "Force Quit to Start Menu");
        }

        // X360 step 5: sentinel-fill the CPU monitor handle block (BrnCpuMonitors::Construct
        // 0x823A90A8), then register all 40 monitors. Rows are (name, page, minimum, budget-ms,
        // libperf-tagged), transcribed store-for-store from 0x823C9EA8 (the 5-arg AddMonitor:
        // on PPC the float budget occupies the r6 slot, so r7 is the libperf flag).
        mCpuMonitors.Construct();
        {
            using CgsDev::PerfMonCpu::AddMonitor;
            typedef CgsDev::PerfMonCpuPage EPage;
            mCpuMonitors.miUT_TotalUpdate      = AddMonitor("UT: Total simulation",          (EPage)0,  false, 210.0f, false);
            mCpuMonitors.miUT_EachUpdate       = AddMonitor("UT: Each sim step",             (EPage)0,  false,  70.0f, true);
            mCpuMonitors.miUT_NetworkAIRaceCar = AddMonitor("      Network + AI + Racecar",  (EPage)0,  false,  10.0f, true);
            mCpuMonitors.miUT_Network          = AddMonitor("         Network",              (EPage)0,  false,   3.0f, true);
            mCpuMonitors.miUT_AI               = AddMonitor("         AI",                   (EPage)0,  false,   5.0f, true);
            mCpuMonitors.miUT_RaceCar          = AddMonitor("         RaceCar",              (EPage)0,  false,   3.0f, true);
            mCpuMonitors.miUT_GameState        = AddMonitor("      GameState",               (EPage)0,  false,   3.0f, true);
            mCpuMonitors.miUT_Replay           = AddMonitor("      Replay",                  (EPage)0,  false,   3.0f, true);
            mCpuMonitors.miUT_GUI              = AddMonitor("      GUI",                     (EPage)0,  false,   2.0f, true);
            mCpuMonitors.miUT_Director         = AddMonitor("      Director",                (EPage)0,  false,   5.0f, true);
            mCpuMonitors.miUT_Sound            = AddMonitor("      Sound",                   (EPage)0,  false,   5.0f, true);
            mCpuMonitors.miUT_Effects          = AddMonitor("      Effects",                 (EPage)0,  false,   0.5f, true);
            mCpuMonitors.miUT_Traffic          = AddMonitor("      Traffic",                 (EPage)0,  false,   8.0f, true);
            mCpuMonitors.miUT_Triggers         = AddMonitor("      Triggers",                (EPage)0,  false,   0.5f, true);
            mCpuMonitors.miUT_CrashManager     = AddMonitor("      CrashManager",            (EPage)0,  false,   1.0f, true);
            mCpuMonitors.miUT_Physics          = AddMonitor("      Physics",                 (EPage)0,  false,  28.0f, true);
            mCpuMonitors.miUT_World            = AddMonitor("      World",                   (EPage)0,  false,   4.0f, true);
            mCpuMonitors.miUT_Resource         = AddMonitor("UT: ResourceSystem",            (EPage)0,  false,   5.0f, false);
            mCpuMonitors.miUT_RenderAll        = AddMonitor("UT: Render",                    (EPage)0,  false,  15.0f, false);
            mCpuMonitors.miUT_FrustumTesting   = AddMonitor("      FrustumTests",            (EPage)0,  false,   2.0f, false);
            mCpuMonitors.miUT_RenderMainScreen = AddMonitor("      RenderMainScreen",        (EPage)0,  false,   7.0f, false);
            mCpuMonitors.miUT_RenderShadowMap  = AddMonitor("      RenderShadows",           (EPage)0,  false,   1.5f, false);
            mCpuMonitors.miUT_RenderEnvMap     = AddMonitor("      RenderEnvMap",            (EPage)0,  false,   1.5f, false);
            mCpuMonitors.miUT_RenderFX         = AddMonitor("      RenderEffects",           (EPage)0,  false,   1.0f, false);
            mCpuMonitors.miUT_RenderGUI        = AddMonitor("      RenderGUI",               (EPage)0,  false,   2.0f, false);
            mCpuMonitors.miDT_DispatchToGpu    = AddMonitor("DT: DispatchToGPU",             (EPage)0,  false,  95.0f, false);
            mCpuMonitors.miUT_ThreadSync       = AddMonitor("UT: Thread sync",               (EPage)0,  false,  10.0f, false);
            mCpuMonitors.miUT_WaitOnDispatch   = AddMonitor("      WaitOnDispatch",          (EPage)0,  false,  10.0f, false);
            mCpuMonitors.miUT_DebugManager     = AddMonitor("UT: Debug manager",             (EPage)0,  false,   0.0f, false);
            mCpuMonitors.miUT_RaceCar_SQ       = AddMonitor("RC SceneQueries",               (EPage)12, false,   0.5f, true);
            mCpuMonitors.miUT_Traffic_SQ       = AddMonitor("Traf SceneQueries",             (EPage)2,  false,   0.5f, true);
            mCpuMonitors.miUT_Triggers_SQ      = AddMonitor("Trigger SceneQueries",          (EPage)5,  false,   0.5f, true);
            mCpuMonitors.miUT_GameState_Bridge = AddMonitor("GameState Bridges",             (EPage)11, false,   0.1f, true);
            mCpuMonitors.miUT_GUI_Bridge       = AddMonitor("GUI Bridges",                   (EPage)11, false,   0.1f, true);
            mCpuMonitors.miUT_AI_Bridge        = AddMonitor("AI Bridges",                    (EPage)11, false,   0.1f, true);
            mCpuMonitors.miUT_RaceCar_Bridge   = AddMonitor("RaceCar Bridges",               (EPage)11, false,   0.1f, true);
            mCpuMonitors.miUT_Traffic_Bridge   = AddMonitor("Traffic Bridges",               (EPage)11, false,   0.1f, true);
            mCpuMonitors.miUT_Director_Bridge  = AddMonitor("Bridges",                       (EPage)13, false,   0.1f, true);
            mCpuMonitors.miUT_Director_SQ      = AddMonitor("Scene Queries",                 (EPage)13, false,   1.0f, true);
            mCpuMonitors.miUT_SoundUpdate      = AddMonitor("Sound",                         (EPage)14, false,  10.0f, true);
        }

        // X360 step 6: construct EVERY engine module, in the X360 call order. Modules whose real
        // Construct exists run it; the placeholder modules run the module base's Construct (which
        // is also what makes their Release/Destruct paths well-defined).
        //
        // ⭐ OFFSETS CORRECTED 2026-08-16 (boot audit F-P1-18): NINE of these ten comments were
        // wrong. They had been inferred from GameRelease @0x823F03C8's typed IO buffers; the
        // values below are the MEASURED module bases (`*off_830102D0 + <off>` as the console
        // itself spells them at each call site). They are documentation only -- every access
        // here is by member name -- but they are the numbers the next reader will trust when
        // they cross-check a raw offset out of the disassembly, so a wrong one costs an hour.
        //
        // ⭐ AND THE DIRECTOR'S ASPECT IS REAL NOW (boot audit F-P1-3). The console's renderer
        // Construct hands back an ASPECT RATIO (1.7777778) and a video-mode bool, and passes
        // the aspect straight into DirectorModule::Construct. We passed a fabricated 0.0f --
        // an invented value, not a marked deferral. 16:9 is what the console computes for
        // every mode this build renders.
        mSoundModule.Construct();        // +0x8A7D00  RootSoundModule::Construct 0x826AF350 (slot 0)
        mRenderModule.Construct();       // +0x004400  BrnRendererModule::Construct (direct call)
        mGameDataModule.Construct();     // +0x5F4B00  GameDataModule::Construct 0x82671B90 (slot 0, NO args)
        mWorldModule.Construct(mCpuMonitors); // +0x010E80  WorldModule::Construct 0x827CF540
                                         //            (slot +64, const BrnCpuMonitors& -- the
                                         //            handle block filled above). REAL module
                                         //            mounted 2026-07-26 (world-render campaign).
        mInputModule.Construct();        // +0x6E9630  InputModule::Construct 0x828F83D0 (slot 0) --
                                         //            the real CgsInput::InputModule since FX-RUMBLE3
                                         //            2026-09-24 (was an empty ODR stub -> the base)
        // [gateui r4] +0x6EAA20. X360 slot +84 takes TWO sub-objects out of the GameData
        // module -- gm+0x65A1D0 (lpHudMessageController) and gm+0x65A1F4 (lpPopupController).
        // The FIRST one is now passed for real: 0x65A1D0 - 0x5F4B00 (the GameData module's
        // own base) == 0x65950 == 416080, which is exactly the member
        // BrnResource::GameDataModule::mHudMessageController that PrepareHudMessages fills
        // (GameDataModule::Construct @0x82671B90 constructs it at `this + 0x65950`). It is
        // reached here through the additive `GetHudMessageController()` accessor because the
        // console reaches it by offset and this tree does not use offsets.
        // The second, lpPopupController (+0x65A1F4 == GameData +0x65974), is the popup table
        // PreparePopups fills; it reaches the overlays director through the GuiCache.
        //
        // ⭐ THE HIGH-DEFINITION FLAG (BurnoutDecomp/b5-decomp#11, 2026-09-07). The console's
        // last argument to GuiModule::Construct @0x82518028 is the video-mode HD bool that
        // BrnRendererModule::Construct @0x8240A778 handed back through its `bool*` out-param
        // (`*v6 = XVIDEO_MODE.fIsHiDef != 0`); GuiModule stores it into the GUI cache
        // (`*(gm + 1024649) = a6` == GuiCache +0x4B49) and every HD/SD layout choice in the
        // GUI reads that byte. It was never passed here, so the cache said SD: the title
        // screen revealed the SD-only "HD compatible" composite, the map ran the SD zoom
        // table, the licence card sat at its SD position. The renderer now derives the class
        // from the real front buffer (see its Construct) and the module reads it back.
        //
        // [FLAG PC data-set gate] The PC repack ships ONLY the HD apt/flapt/font bundles
        // (build\game\GUIAPT, FLAPTHUD.BUNDLE, LANGUAGE\FONTS; there is no GUIAPTSD
        // directory), so a sub-720 display cannot be given the console's SD path -- the GUI
        // would have nothing to load. It is forced HD and the log says so. DELETE-WHEN the
        // repack carries the SD set (or the maintainers drop SD outright, per issue #11).
        bool lbHighDef = mRenderModule.IsHD();
        if (!lbHighDef)
        {
            CgsDev::Log::WriteToLog("[GameModule] [FLAG PC] display is standard-definition "
                                    "(front buffer < 720 rows) but the PC data set has no SD GUI "
                                    "bundles -- forcing the HD GUI path\n");
            lbHighDef = true;
        }
        mGuiModule.Construct(mGameDataModule.GetHudMessageController(),
                             mGameDataModule.GetPopupController(), lbHighDef);
        mGameStateModule.Construct();    // +0x669500  (slot 0; placeholder -> base)
        mEffectsModule.Construct();      // +0x878700  (slot 0; placeholder -> base)
        // (The interim ValidityAccount::SetupFailFlagMask bridge that used to sit here was
        // retired 2026-09-07: CameraState::Construct @0x82252348 performs the setup itself
        // -- BrnCameraState.cpp:133 -- and DirectorModule::Construct reaches it through
        // mCamera.Construct() (BrnDirectorModule.cpp:108) before anything reads the mask.)
        mDirectorModule.Construct(1.7777778f); // +0x6B0B10  X360 slot +64 @0x8225C590 (REAL module,
                                         //            mounted 2026-07-29 -- DJ fly-by campaign).
        mReplayModule.Construct();       // +0x8BD300  (slot 0; ReplayModule -> base)
        mNetworkModule.Construct(false);      // +0x8C3600  [gated] X360 slot +64 with arg 0; placeholder -> base.

        // ⭐ 2026-08-16 (boot audit F-P1-11 / F-P2-6). The GamePrepare receiver queue is
        // Constructed HERE on the console -- it is part of step 7-9's queue setup
        // (gm+0x9A06BC, capacity 1024, align 16) and it already exists by the time
        // GamePrepare @0x823EFBD0 first runs, which is why that body contains no construct.
        // We built it lazily on the first GamePrepare call behind a bool. No observable
        // difference, but the bool was a member the console does not have, and "constructed
        // before the frame loop" is the invariant the async seam will rely on.
        mGamePrepareReceiverQueue.Construct();

        // ⭐ THE PAGE-NAME TABLE, RECOVERED 2026-08-17 (boot audit F-P1-10). Construct
        // @0x823C9EA8 calls DebugComponentPerfMonCpu::SetPageName twenty-four times; the
        // names are read out of that body in call order and are reproduced here exactly,
        // including the two the console repeats (pages 10/11 both "Graphics", 13/14 both
        // "Director" -- not a transcription slip).
        //
        static const char* const KAPC_PERFMON_PAGE_NAMES[24] =
        {
            "General",              // 0
            "Resource",             // 1
            "Traffic",              // 2
            "Gui",                  // 3
            "World",                // 4
            "GameState",            // 5
            "Physics",              // 6
            "AI",                   // 7
            "Network",              // 8
            "Network Detail",       // 9
            "Graphics",             // 10
            "Graphics",             // 11  (repeated on the console)
            "Race Car",             // 12
            "Director",             // 13
            "Director",             // 14  (repeated on the console)
            "Deformation",          // 15
            "SceneManager ContactGen", // 16
            "SceneManager",         // 17
            "More Network Detail",  // 18
            "Sound: Aems Detail",   // 19
            "Particles",            // 20
            "Lion",                 // 21
            "Video",                // 22
            "Flapt",                // 23
        };
        for (s32 liPage = 0; liPage < CgsDev::E_PMP_MAX; ++liPage)
            mDebugManager.mDebugComponentPerfMonCpu.SetPageName(
                static_cast<CgsDev::PerfMonCpuPage>(liPage), KAPC_PERFMON_PAGE_NAMES[liPage]);

        // [gated] The event-receiver queue at +10094268 and the two replay serialisers
        // (DirectorBridgeSerialiser/GameModuleSerialiser::Construct) still need their exact
        // typed storage. The remaining menu controls are registered after timer setup below;
        // the Force shutdown and Take screen shots bool readers/backends remain unproven.

        // NOTE: the bitmap debug font is NOT brought up here -- it arrives through GamePrepare's
        // id-5 AcquireResource reply (the console's own path: Font::CreateTextureState +
        // DebugManager::SetDebugFont once "Language\Fonts\Default.font" resolves out of pool 0).

        // ---- X360 step 9 (the part that matters to every timed subsystem) -----------------
        // Construct @0x823C9EA8, verbatim:
        //     CgsSystem::TimerStatusInterface::Clear(gm + 10095372);
        //     lfRate = 1.0 / <vsync refresh rate>;               // the 50/60 the step above checks
        //     CgsSystem::Timer::Prepare(gm + 10095316, lfRate);  // the GAME timer
        //     CgsSystem::Timer::Prepare(gm + 10095344, lfRate);  // the SIM timer
        //     *(gm + 10095340) = 1;                              // gameTimer.mbRunning (+24)
        //     *(gm + 10095368) = 1;                              // simTimer.mbRunning  (+24)
        // ⭐ THE RATE IS READ, NOT ASSUMED, since 2026-08-16 (boot audit F-P1-9). The console
        // takes the refresh rate out of the display mode it validated one step earlier
        // (asserting 50 or 60); we hardcoded 1/60, which is right on a 60Hz panel and
        // silently wrong on anything else -- and the timer rate is the time base every
        // simulation sub-step, camera advance and streaming budget is derived from.
        // renderengine::GetDisplayRefreshRate is the PC's mode query. It answers 0 for some
        // windowed modes (D3D's "whatever the desktop is doing"), and anything outside the
        // console's own 50/60 range means we are on hardware the console never saw, so both
        // fall back to 60 -- the value this build assumed unconditionally until now.
        //
        // X360 step 10 (the flow controller) is constructed BEFORE this block, not after:
        // Construct @0x823C9EA8 runs GameMainFlowController::Construct and then the timer
        // seeds. Both are pure init so the order was not observable, but it was inverted
        // (boot audit F-P1-12).
        mMainFlowStateMachine.Construct();

        // X360 Construct clears the registered bool at gm+10097332 (0x9A12B4) before timer
        // setup and later exposes it as "Take screen shots". Its reader/backend is unresolved.
        mbTakeScreenShots = false;

        {
            // ⚠️ FLAG PC QUALITY-OF-LIFE, 2026-08-17: THE SIMULATION RATE IS NOW FIXED AT
            // 60 Hz AND NO LONGER FOLLOWS THE DISPLAY.
            //
            // The console derives this rate from the display it validated one step earlier
            // (asserting 50 or 60) because the two are the same clock there -- the frame it
            // draws and the step it simulates are one event. This build has broken that
            // identity on purpose (see mi8FrameRateMinSteps in the ctor): the renderer is
            // free to run at whatever the panel and VSync setting allow, and the simulation
            // is paced against the real-time clock instead. That only works if the step size
            // is a CONSTANT -- it is the divisor CgsSystem::FrameRateManager counts real
            // elapsed cycles against, and it is the timestep every consumer downstream
            // (physics, the director's behaviour advance, the streamer budget, every GUI
            // dwell) reads out of GetCurrentTimeStep.
            //
            // 60 is the console's own NTSC rate and the rate the game's handling, timers and
            // animation were authored at. A PAL console ran the simulation at 50 and was
            // correspondingly slower in real time; matching the panel here would reintroduce
            // exactly the coupling this change removes.
            //
            // The refresh rate is still queried and still logged -- it is worth seeing, and
            // it is what the console read -- it just no longer sets the simulation rate.
            const u32 luRefreshHz = renderengine::GetDisplayRefreshRate();
            const u32 luRateHz    = KU_SIMULATION_RATE_HZ;
            const f32 lfTimerRate = 1.0f / static_cast<f32>(luRateHz);
            CgsDev::PerfMonCpu::SetGameFrequency(CgsDev::E_PMF_60HZ);
            if (CgsDev::Message::gxMessageFilterFlags & 1)
                *CgsDev::Log::gpDebugPrint
                    << "[timers] display refresh " << (s32)luRefreshHz
                    << "Hz -> simulation rate 1/" << (s32)luRateHz
                    << " (fixed; render rate is decoupled)\n";
            mTimerStatusInterface.Clear();
            mGameTimer.Prepare(lfTimerRate);
            mSimTimer.Prepare(lfTimerRate);
            mGameTimer.SetRunning(true);
            mSimTimer.SetRunning(true);

            // The debug fps-readout state DebugManagerRender keeps (gm+0x9A0B85..0x9A0BC8; on
            // the console these sit at the static game module's zero-init, which DebugMemoryInit
            // re-zeroes). Seeded explicitly here because this build's module is not zero-cleared.
            // [FLAG] mbDebugSimulationIsRealtime's console writer is unrecovered (see the header);
            // seeded true so the readout shows the plain "%d fps" line.
            mbDebugSimulationIsRealtime    = true;
            mu8DebugFpsFrameStampIndex     = 0;
            mau32DebugFpsFrameStamps[0]    = 0;
            mau32DebugFpsFrameStamps[1]    = 0;
            mau32DebugFpsFrameStamps[2]    = 0;
            mu32DebugFpsAverageWindowStamp = 0;
            mfDebugFpsAccumulator          = 0.0f;
            mfDebugFpsAverage              = 0.0f;
            mfDebugFpsSampleCount          = 0.0f;

            // ⭐ THE FRAME-RATE MANAGER IS CONSTRUCTED, 2026-08-17. It never was on this
            // build -- the call was listed among the "[gated] rest of steps 7-9" items -- so
            // every one of its fields sat at the static game module's zero-init and its
            // UpdatePostRenderWait was a stub that answered "the minimum, at least one"
            // without ever reading a clock. That stub is what tied the simulation to the
            // render rate.
            //
            // Position and arguments are the console's, verbatim: Construct @0x823C9EA8 runs
            // it at 0x823CAE68, immediately after the two Timer::Prepare calls above, with
            // `this = gm + 0x9A0B50` and the two floats formed at 0x823CAE3C-64 as
            //     a2 = simTimer.mfRate * simTimer.mfScaleCurrent * flt_82009E10 (1000.0)
            //     a3 = simTimer.mfRate * simTimer.mfScaleCurrent * flt_820049E0 ( 100.0)
            // i.e. one simulation step in MILLISECONDS, and a framerate tolerance of one
            // tenth of it. (Both constants read out of the decrypted ARTIST image at
            // 0x82009E10 / 0x820049E0.) mfScaleCurrent is 1.0 straight out of Timer::Prepare,
            // so this is the console's own expression, not a simplification of it.
            {
                const f32 lfSimulationStepMs = mSimTimer.GetRate() * mSimTimer.GetScaleCurrent() * 1000.0f;
                const f32 lfToleranceMs      = mSimTimer.GetRate() * mSimTimer.GetScaleCurrent() * 100.0f;
                mFrameRateManager.Construct(lfSimulationStepMs, lfToleranceMs);
            }

            // ⚠️ FLAG PC quality-of-life: apply the config.ini pacing switch. The ctor seeded
            // the decoupled value (0); config.ini can put the console's 1 back. Applied HERE
            // because this module is a static -- its constructor ran before LoadConfig did.
            mi8FrameRateMinSteps = gbDecoupleSimulationFromRenderRate ? 0 : 1;
            if (CgsDev::Message::gxMessageFilterFlags & 1)
                *CgsDev::Log::gpDebugPrint
                    << "[timers] pacing: "
                    << (gbDecoupleSimulationFromRenderRate
                            ? "DECOUPLED (fixed 60Hz simulation, free-running renderer)"
                            : "CONSOLE-LOCKED (one simulation step per rendered frame)")
                    << ", min/max steps " << (s32)mi8FrameRateMinSteps << "/"
                    << (s32)mi8FrameRateMaxSteps << "\n";
        }

        // X360 Construct @0x823CAEBC-F48 registers the Framerate variable, its 0..2 range and
        // options, then the two simulation actions. The option pairs are the raw table at
        // 0x8203525C: {0,"Single"}, {1,"Multiple Capped"}, {2,"Multiple Uncapped"}.
        {
            static const CgsDev::DebugUI::StringList KAC_FRAMERATE_OPTIONS[] = {
                {0, "Single"},
                {1, "Multiple Capped"},
                {2, "Multiple Uncapped"},
            };

            CgsDev::DebugInterface lDebugInterface(&mDebugManager);
            s32* const lpiFrameRateType = reinterpret_cast<s32*>(&meFrameRateManagerType);
            lDebugInterface.RegisterVariable(lpiFrameRateType, "Debug/Framerate", "Framerate type");
            lDebugInterface.SetRange(lpiFrameRateType, 0, 2);
            lDebugInterface.SetOptions(lpiFrameRateType, KAC_FRAMERATE_OPTIONS);
            lDebugInterface.RegisterFunction(&BrnGameModule::StepFrameCB, this, "Debug/Sim", "Step");
            lDebugInterface.RegisterFunction(&BrnGameModule::PlayFrameCB, this, "Debug/Sim", "Play");
            lDebugInterface.RegisterVariable(&mbForceShutdown, "Debug/Sim", "Force shutdown");
            lDebugInterface.RegisterVariable(&mbTakeScreenShots,
                                             "Core/Debug/Performance/CPU Monitors",
                                             "Take screen shots");
        }

        // ⭐ CORRECTED 2026-08-16 (boot audit F-P1-2). Construct already leaves the
        // controller in state 0 by a RAW store (@0x823C6508) and the X360 caller issues no
        // SetState, so the console never runs state 0's OnLeave OR its OnEnter -- SendEvent's
        // transition set never targets state 0 either. The PC's explicit SetState fired an
        // OnLeave+OnEnter pair the console never issues; with the state bytes now wired
        // (F4) that phantom OnEnter would also have raised mbSaveLoadState, making the
        // initial-load update set 0xC1 instead of the console's 0x80.

        // ⭐ THE GUI PREPARE IS GONE FROM HERE, 2026-08-16 (boot audit F-P1-1, the S1
        // exemplar). It used to run `mGuiModule.Prepare()` on this line -- which meant the
        // whole ~24MB GUI/Apt bring-up (VIDEOLIST, the Apt runtime, PERSISTENTAPT,
        // GUITEXTURES, the fonts, FLAPTHUD, the profiles, the flow pools, the FSM
        // controller) completed BEFORE the loading screen existed. The log said so plainly:
        // every GUI/Apt line came out before "loading screen shown".
        //
        // Construct @0x823C9EA8 contains no GuiModule::Prepare at all. The console drives it
        // from the loading-screen stage machine: InitialLoadingScreen::Update @0x823EF688
        // stage 2 -> LoadingScriptedState::LoadGUIModule @0x823EF310, which pumps the GUI
        // module's Prepare (vtable+0x58) once per frame and only posts the two id-144 RunFsm
        // records when it finally reports done. That is now where ours runs.

        // ARTIST 0x823C9EA8 clears the disk-error, controller-disconnect, and loading-screen
        // latches at gm+10094114, +10094116, and +10094125. Use their owned members here.
        mbDiskError = false;
        mbControllerDisconnected = false;
        mbIsLoadingScreenVisible = false;

        // FLAG PC-platform leaf: retain the persistent host input buffer and existing
        // GUI-enable policy. Player selection follows the recovered original bind chain.
        mPcInputOutputBuffer.Construct();
        // ARTIST823CAA14/7C/AC: both port words start at4; bind state starts at0.
        // BootLegal90 arms state1; only a real START selection advances it to2.
        miPlayer0ControllerPort   = CgsInput::KU_NUMBER_OF_PADS;
        miSecondaryControllerPort = CgsInput::KU_NUMBER_OF_PADS;
        miInputModuleState        = 0;
        mbGuiAcceptsControllerInput = true;

        // ---- the GUI flow-FSM bridge state ------------------------------------------
        // ⭐ CORRECTED 2026-08-17 (boot audit F-P1-8). The note said "X360 Construct zeroes
        // the slots; the bridge parks the stage at 6 after the first pass". It does zero the
        // neighbouring bytes, but NOT this word: @0x823CAAD0-DC it loads `li r11, 6` and
        // `stwx r11, r30, r24` with r24 = 0x9A0644 -- the stage slot -- so Construct seeds it
        // to SIX. Our own header already documents 6 as "idle" (BrnGameModule.hpp:738), so
        // the two sources agree and only the code disagreed.
        //
        // Seeding 0 is not merely untidy: the reset just below is `if (miGuiFsmStage != 6)`,
        // which from 0 is TRUE on the first pass and clears mbGuiPhaseComplete -- and that
        // byte is what InitialLoadingScreen's preload latch and CheckDiskSpace::Update both
        // read since F-P5-4/F-P4-8. Starting idle is the console's initial condition.
        miGuiFsmStage      = 6;
        mbGuiPhaseComplete = false;
        mbGuiPreAccept     = false;
        mbDispatchCameraPublished = false;
        mbPlayerCarCrashing    = false;
        mbWorldDataPrepared    = false;
        mbCarSelectionPublished = false;

        // ARTIST 823CB1C4 / 823CB1D0; DecFIGS BrnGameModule.h:524/525.
        mDirectorBridgeSerialiser.Construct();
        mGameModuleSerialiser.Construct();
    }

    // @ 0x823DCA10 -- the game->GUI flow-FSM bridge (see BrnGameModule.hpp). Posts each
    // pending stage's GuiEventRunFsm record(s) as raw 24-byte event-144 AddEvents (the
    // X360 posts these raw, not through the AddGuiEvent<T> template), then parks the
    // stage and clears the phase-complete flag.
    void BrnGameModule::BridgeGameToGui(CgsGui::CgsGuiModuleIO::InputBuffer* lpGuiInputBuffer)
    {
        if (lpGuiInputBuffer == 0)
            return;

        struct RunFsmPost
        {
            static void Post(CgsGui::CgsGuiModuleIO::InputBuffer* lpBuffer, const char* lpacFsmName,
                             const char* lpacInitialState, s32 liFsmToRun, s32 liFlowToUse)
            {
                BrnGui::GuiEventRunFsm lEvent;
                lEvent.mFsmId          = CgsIDCompress(lpacFsmName);
                lEvent.mInitialStateId = (lpacInitialState != 0) ? CgsIDCompress(lpacInitialState)
                                                                 : static_cast<CgsID>(0);
                lEvent.meFsmToRun      = static_cast<BrnGui::EHUDFSMs>(liFsmToRun);
                lEvent.meFlowToUse     = static_cast<BrnGui::GuiFlow>(liFlowToUse);
                lpBuffer->GetGuiEvents()->AddEvent(
                    reinterpret_cast<const CgsModule::Event*>(&lEvent), lEvent.GetEventType(),
                    static_cast<s32>(sizeof(lEvent)));
            }
        };

        switch (miGuiFsmStage)
        {
            case 1:
                RunFsmPost::Post(lpGuiInputBuffer, "BrnVideoFsm", 0,
                                 BrnGui::E_GUI_HUD_BOOT, BrnGui::E_GUIFLOW_HUD);
                break;
            case 2:
                RunFsmPost::Post(lpGuiInputBuffer, "BrnLegalFsm", 0,
                                 BrnGui::E_GUI_HUD_BOOT, BrnGui::E_GUIFLOW_HUD);
                break;
            case 3:
                RunFsmPost::Post(lpGuiInputBuffer, "BrnCmpLdFsm", 0,
                                 BrnGui::E_GUI_HUD_BOOT, BrnGui::E_GUIFLOW_HUD);
                break;
            case 4:
                RunFsmPost::Post(lpGuiInputBuffer, "BrnBFProFsm", 0,
                                 BrnGui::E_GUI_HUD_BOOT, BrnGui::E_GUIFLOW_HUD);
                break;
            case 5:
                // The in-game handoff: the front-end SCREEN flow at its LOADING state plus
                // the freeburn HUD FSM.
                RunFsmPost::Post(lpGuiInputBuffer, "BrnScreenFsm", "LOADING",
                                 BrnGui::E_GUI_HUD_BOOT, BrnGui::E_GUIFLOW_SCREEN);
                RunFsmPost::Post(lpGuiInputBuffer, "BrnFBFsm", 0,
                                 BrnGui::E_GUI_HUD_FREEBURN, BrnGui::E_GUIFLOW_HUD);
                break;
            default:
                break;
        }

        if (miGuiFsmStage != 6)
        {
            miGuiFsmStage      = 6;
            mbGuiPhaseComplete = false;
        }
    }

    // @ 0x823CB758 -- the GUI->game out-event consumer (see BrnGameModule.hpp). The PC
    // consumers map the console's dispatch-buffer render states onto the renderer's
    // loading-screen signal; the quit-to-dash (86/87/89 -> XLaunchNewImage) and the
    // brightness/contrast forwards (545/546) are platform follow-ons.
    void BrnGameModule::BridgeGuiToGame(CgsModule::VariableEventQueue<18432, 16>* lpGuiOutQueue)
    {
        // The calibration TEXTURE handle the console keeps as a FUNCTION LOCAL, re-seeded from
        // the null-handle sentinel on every call: @0x823CB764-0x823CB774
        //     lis r11, qword_82FAE900@ha ; ld r11, qword_82FAE900@l(r11) ; std r11, var_A0(r1)
        // i.e. `ResourceHandle lTextureHandle = CgsResource::NULLResourceHandle;` (DWARF
        // BrnGameModule.cpp:3105; qword_82FAE900 is the {NULL,NULL} handle the SetDebugFont
        // family compares against -- BrnGameModule::Construct @0x823CA970, DebugManagerRender
        // @0x823BCBD0, CgsDev::DebugManager::SetDebugFont @0x823B14FC all read the same word).
        // GUI event 546 overwrites it for THIS frame only and the publish tail below stores
        // whatever it then holds -- so the calibration texture goes away again the moment
        // ColourCalibrationScreen stops posting. That per-frame reset is the console's, not ours.
        CgsResource::ResourceHandle lhCalibrationTextureHandle = CgsResource::NULLResourceHandle;

        // The event walk is skipped without a queue (a PC guard: the console always has the GUI
        // output buffer's queue); the publish tail below runs regardless, as on the console.
        const CgsModule::Event* lpEvent = 0;
        s32 liSize = 0;
        s32 liId = (lpGuiOutQueue != 0) ? lpGuiOutQueue->GetFirstEvent(&lpEvent, &liSize) : -1;
        // X360 BridgeGuiToGame @0x823CB7A8/B8 polls and clears byte_82FAE28C before walking
        // GUI events, then sets the game-flow return latch at gm+10094118.
        if (sbForceQuitToStartMenu)
        {
            sbForceQuitToStartMenu = false;
            BrnGameMainFlowController::gBrnReturnToFrontEndRequested = true;
        }

        while (liId >= 0 && lpEvent != 0)
        {
            const s32 liCommand = liId;
            const u8* const lpuPayload = reinterpret_cast<const u8*>(lpEvent);
            const s32 liPayloadSize = liSize;

            // ---- the DISPLAY-CALIBRATION events, 545 and 546 -------------------------------
            // X360 BridgeGuiToGame @0x823CB758 handles these two ids in its one switch:
            //   case 0x221 (545) BrnGui::GuiOptionsBrightnessContrast          @0x823CB9FC
            //       assert "NULL != lpBrightnessContrast" (BrnGameModule.cpp:3194), then
            //         lwz r11,0(r29) ; stwx r11,r31,r15   -> +10096740 == miBrightness
            //         lwz r11,4(r29) ; stwx r11,r31,r16   -> +10096744 == miContrast
            //   case 0x222 (546) BrnGui::GuiOptionsBrightnessContrastPostFxControl @0x823CBAAC
            //       assert "lpBrightnessContrastPostFxControl" (BrnGameModule.cpp:3205), then
            //         lbz r11,8(r29) ; stbx r11,r31,r17   -> +10096748 ==
            //                                                mbEnableCalibrationUnfriendlyPostFx
            //         ld  r11,0(r29) ; std r11,var_A0(r1) -> the local texture handle above
            // The producers are BrnGui::ScreenLoading::ApplyOptionsDataProfileSettings and
            // BrnGui::CrashNavColourCalibrate::ApplySettings (545, the saved profile / the
            // options slider) and BrnGui::ColourCalibrationScreen::Update (546, the calibration
            // ramp screen showing and hiding).
            //
            // ⚠ THE PAYLOAD IS READ BY NAME, NOT AT THE CONSOLE'S BYTE OFFSETS. The 546 payload
            // leads with a CgsResource::ResourceHandle -- two POINTERS, 8 bytes on the X360 and
            // 16 bytes here -- so the console's `+8` for the bool is a guest offset and using it
            // would read the middle of mpSourceEntry. The struct is the tree's own
            // BrnGui::GuiOptionsBrightnessContrastPostFxControl and the members are reached by
            // name; the size check below is against the HOST sizeof for the same reason.
            {
                // Payload layout pins (event payloads are the classic byte-layout trap).
                // 545: two words, brightness first -- swap them and the frame goes dark
                // instead of bright, silently. 546: the handle LEADS and the flag follows
                // it, which on the host means +16, not the console's +8.
                static_assert(offsetof(BrnGui::GuiOptionsBrightnessContrast, mBrightness) == 0,
                              "GUI 545 payload: mBrightness is the X360 payload +0 word");
                static_assert(offsetof(BrnGui::GuiOptionsBrightnessContrast, mContrast) == 4,
                              "GUI 545 payload: mContrast is the X360 payload +4 word");
                static_assert(sizeof(BrnGui::GuiOptionsBrightnessContrast) == 8,
                              "GUI 545 payload is two words (X360 record 20B = 12B header + 8)");
                static_assert(offsetof(BrnGui::GuiOptionsBrightnessContrastPostFxControl,
                                       mColourCalibrationTextureHandle) == 0,
                              "GUI 546 payload: the calibration handle leads (X360 payload +0)");
                static_assert(offsetof(BrnGui::GuiOptionsBrightnessContrastPostFxControl,
                                       mbEnablePostFx)
                                  == sizeof(CgsResource::ResourceHandle),
                              "GUI 546 payload: the post-fx flag follows the handle "
                              "(X360 payload +8; host +16 -- the handle is two pointers)");

                if (liCommand == 545)
                {
                    CGS_ASSERT(lpuPayload != 0, "NULL != lpBrightnessContrast");
                    if (lpuPayload != 0
                        && liPayloadSize >= static_cast<s32>(
                               sizeof(BrnGui::GuiOptionsBrightnessContrast)))
                    {
                        const BrnGui::GuiOptionsBrightnessContrast* const lpSettings =
                            reinterpret_cast<const BrnGui::GuiOptionsBrightnessContrast*>(
                                lpuPayload);
                        miBrightness = lpSettings->mBrightness;
                        miContrast   = lpSettings->mContrast;
                    }
                }
                else if (liCommand == 546)
                {
                    CGS_ASSERT(lpuPayload != 0, "lpBrightnessContrastPostFxControl");
                    if (lpuPayload != 0
                        && liPayloadSize >= static_cast<s32>(
                               sizeof(BrnGui::GuiOptionsBrightnessContrastPostFxControl)))
                    {
                        const BrnGui::GuiOptionsBrightnessContrastPostFxControl* const lpControl =
                            reinterpret_cast<
                                const BrnGui::GuiOptionsBrightnessContrastPostFxControl*>(
                                    lpuPayload);
                        // mbEnablePostFx is the console's byte at payload +8 -- false while
                        // the calibration ramp is on screen, true when it hides. The game module
                        // stores it verbatim; BrnRendererModule::Render ANDs
                        // GetCalibrationUnfriendlyEnablePostFx() into every effect's active flag,
                        // so the ramp is graded by nothing while you calibrate against it.
                        // (Renamed from the tree's placeholder mbRestoreDefaults to the DWARF
                        // name, BrnGuiEventTypeDefs.h:6441 -- step-11 `guiwire`; polarity and
                        // member order are unchanged.)
                        mbEnableCalibrationUnfriendlyPostFx = lpControl->mbEnablePostFx;
                        lhCalibrationTextureHandle =
                            lpControl->mColourCalibrationTextureHandle;
                    }
                }
            }

            switch (liCommand)
            {
                    case 19:   // PlayAptLoadingMovie -> ShowLoadingScreen (X360 write buffer [9828] = 1)
                        mDispatchThreadInputBufferManager.GetWriteBuffer()->ShowLoadingScreen();
                        break;
                    case 20:   // StopAptLoadingMovie -> HideLoadingScreen ([9828] = 2)
                        mDispatchThreadInputBufferManager.GetWriteBuffer()->HideLoadingScreen();
                        break;
                    case 70:   // GUI phase complete -- the main flow advances on it
                        mbGuiPhaseComplete = true;
                        break;
                    case 71:   // pre-accept -- resume the world load during the accept dwell
                        mbGuiPreAccept = true;
                        break;
                    case 90:   // profile-first-boot flag (X360 +10094136: 0 -> 1)
                        if (miInputModuleState == 0)
                            miInputModuleState = 1;
                        break;
                    case 65:
                        // The SCREEN flow's in-game entry notice (InGame::OnEnter posts
                        // {1,65,12,flag=1}). X360: BridgeGuiToGameState @0x823DDB78
                        // forwards it as GameState action 106; the GameState/world side
                        // then closes the boot loading-screen lifecycle as its streaming
                        // settles. [FLAG world-load stand-in: with no world modules on PC
                        // the "world" is ready the moment gameplay owns the screen, so the
                        // in-game notice retires the boot loading screen here -- the same
                        // observable the console produces at this point. The real
                        // GameState consumer replaces this when the world side lands.]
                        mDispatchThreadInputBufferManager.GetWriteBuffer()->HideLoadingScreen();
                        CgsDev::Log::WriteToLog("[GameModule] in-game screen entered (65) -> "
                                                "loading screen retired (world-load stand-in).\n");
                        break;
                    case 405:
                        // ⭐ THE CAR-SELECT SCREEN'S OWN DATA REQUEST. Every car-select screen
                        // state posts command 405 from CarSelectMain::OnEnter @0x824C8920 --
                        // it is the console's "this screen is up, send me the car-select
                        // data" request, and the 406 / 412 / 413 records are its answers.
                        // Re-arming the publish latch here is what makes the answers arrive
                        // ONCE PER SCREEN instead of once per boot.
                        //
                        // ⚠️ THIS MATTERS AND IT WAS FOUND BY BOOT: every screen state is its
                        // OWN object with its OWN mCurrentSetupInfo / car list. Publishing once
                        // per boot fed CS_VEHICLE and left CS_LIVERY with mCarId == (CgsID)-1
                        // and an EMPTY livery selector -- five asserts a frame from
                        // CanCarBePainted and GetHighlighted(). The latch is armed by the
                        // request now, exactly as the console's producer is.
                        mbCarSelectionPublished = false;
                        break;
                    case 86: case 87: case 89:
                        // Quit-to-dash (X360: XGetLaunchData + XLaunchNewImage). [FLAG PC
                        // platform: no dash relaunch; logged so the request is visible.]
                        CgsDev::Log::WriteToLog("[GameModule] GUI quit-to-dash command (86/87/89) -- "
                                                "PC platform no-op (FLAG).\n");
                        break;
                    // The "render states" ARE the loading-screen commands: the console
                    // BridgeGuiToGame @0x823CB758 writes the dispatch write buffer's
                    // meLoadingScreenCommand (+39312 == [9828]) that Render forwards into
                    // LoadingScreenRenderer::AddCommand. 138 = the save/load prompt
                    // background (BootProfile posts it right before playing
                    // SaveLoadComponent: the loading screen renders BEHIND the GUI,
                    // dimmed); 589/590 = the black-overlay fades BootLegal posts around
                    // the title screen and the menu accept.
                    case 138:  // -> ShowLoadingScreenSaveLoadBG ([9828] = 3)
                        mDispatchThreadInputBufferManager.GetWriteBuffer()->ShowLoadingScreenSaveLoadBG();
                        break;
                    case 589:  // -> BlackOverlayFadeIn ([9828] = 4: reveal from black)
                        mDispatchThreadInputBufferManager.GetWriteBuffer()->BlackOverlayFadeIn();
                        break;
                    case 590:  // -> BlackOverlayFadeOut ([9828] = 5: the accept fade to black)
                        mDispatchThreadInputBufferManager.GetWriteBuffer()->BlackOverlayFadeOut();
                        break;
                    default:
                        break;
            }
            const CgsModule::Event* lpNext = 0;
            liId = lpGuiOutQueue->GetNextEvent(lpEvent, &lpNext, &liSize);
            lpEvent = lpNext;
        }
        // ⚠️ The Clear moved OUT of this function (fly-by wave). The console does not clear
        // here either -- BridgeGuiToDirector @0x823CBF70 walks the SAME queue later in the same
        // frame, and clearing it in the first consumer would drop every director command on the
        // floor. DoUpdate now clears once, after both bridges have run.

        // ---- the console's UNCONDITIONAL publish tail (@0x823CB758, after the event loop) -----
        //     CgsModule::IOBuffer::LockForWrite(v4);                                  v4 = the WRITE buffer
        //     DispatchThreadInputBuffer::SetBrightness(v4, *(a1 + 10096740));         miBrightness
        //     DispatchThreadInputBuffer::SetContrast(v4, *(a1 + 10096744));           miContrast
        //     DispatchThreadInputBuffer::SetCalibrationUnfriendlyEnablePostFx(v4, *(a1 + 10096748));
        //     DispatchThreadInputBuffer::SetCalibrationTextureHandle(v4, v15);       v15 = qword_82FAE900
        //     CgsModule::IOBuffer::UnlockForWrite(v4);                                (the null handle;
        //                                                                              event 546 overrides)
        // This is how the options-menu brightness / contrast reach the renderer: BrnRendererModule::
        // Render reads them off the READ buffer for the post-fx composite (GetBrightness @0x8240DCC8 /
        // GetContrast @0x8240DCFC). Landed 2026-08-15 with the composite: without it the buffer read
        // 0 / 0 and the frame came out at contrast 0.5 / brightness -0.5 -- black. The texture handle
        // is the FUNCTION LOCAL seeded at the top of this walk (the console's qword_82FAE900
        // null handle, the same word the SetDebugFont family compares against), overwritten for
        // this frame only by GUI event 546.
        //
        // [FLAG PC bring-up TEST HOOK -- OFF BY DEFAULT, DELETE WHEN the colour-calibration
        //  screen is reachable in the boot flow] BRN_POSTFX_CALIBRATION_TEST stands in for the
        // options slider so the composite's response can be proven without the GUI: it pins
        // (brightness, contrast) every frame, overriding whatever the profile published.
        //   BRN_POSTFX_CALIBRATION_TEST=1        -> (80, 50)   the brief's default probe
        //   BRN_POSTFX_CALIBRATION_TEST=80,20    -> (80, 20)   any pair, comma or semicolon
        // The composite turns them into brightness*0.01-0.5 / contrast*0.01+0.5, so 80/50 is
        // +0.3 brightness at neutral contrast -- a plainly brighter frame. This writes ONLY the
        // two members the console's own 545 arm writes; it fabricates no new state.
        {
            static const char* const spcCalibrationTest = getenv("BRN_POSTFX_CALIBRATION_TEST");
            if (spcCalibrationTest != 0)
            {
                s32         liTestBrightness = 80;
                s32         liTestContrast   = 50;
                const char* lpcSeparator     = spcCalibrationTest;
                while (*lpcSeparator != 0 && *lpcSeparator != ',' && *lpcSeparator != ';')
                    ++lpcSeparator;
                if (*lpcSeparator != 0)
                {
                    liTestBrightness =
                        static_cast<s32>(strtol(spcCalibrationTest, 0, 10));
                    liTestContrast = static_cast<s32>(strtol(lpcSeparator + 1, 0, 10));
                }
                miBrightness = liTestBrightness;
                miContrast   = liTestContrast;
            }
        }

        // [FLAG PC bring-up diagnostic -- DELETE with the hook above] one line whenever the
        // published calibration state CHANGES (so the boot log shows the Construct seed once and
        // every slider / profile / calibration-screen move after it). The composite's own
        // [postfx-composite] line only samples calls 1 / 100 / 1000, which cannot show a change.
        {
            static bool sbCalibrationLogged   = false;
            static s32  siLastBrightness      = 0;
            static s32  siLastContrast        = 0;
            static bool sbLastEnablePostFx    = false;
            static const void* spLastCalibTex = 0;
            if (!sbCalibrationLogged
                || siLastBrightness   != miBrightness
                || siLastContrast     != miContrast
                || sbLastEnablePostFx != mbEnableCalibrationUnfriendlyPostFx
                || spLastCalibTex     != lhCalibrationTextureHandle.mpResourceMemory)
            {
                sbCalibrationLogged = true;
                siLastBrightness    = miBrightness;
                siLastContrast      = miContrast;
                sbLastEnablePostFx  = mbEnableCalibrationUnfriendlyPostFx;
                spLastCalibTex      = lhCalibrationTextureHandle.mpResourceMemory;

                char lacMsg[192];
                std::snprintf(lacMsg, sizeof(lacMsg),
                              "[calib] brightness=%d contrast=%d unfriendlyPostFx=%d "
                              "calibTex=%p\n",
                              static_cast<int>(miBrightness), static_cast<int>(miContrast),
                              mbEnableCalibrationUnfriendlyPostFx ? 1 : 0,
                              lhCalibrationTextureHandle.mpResourceMemory);
                CgsDev::Log::WriteToLog(lacMsg);
            }
        }

        {
            BrnGame::DispatchThreadInputBuffer* const lpWrite = mDispatchThreadInputBufferManager.GetWriteBuffer();
            lpWrite->LockForWrite();
            lpWrite->SetBrightness(miBrightness);
            lpWrite->SetContrast(miContrast);
            lpWrite->SetCalibrationUnfriendlyEnablePostFx(mbEnableCalibrationUnfriendlyPostFx);
            // @0x823CBB58 `ld r4, 0x100+var_A0(r1)` / bl SetCalibrationTextureHandle -- the
            // console's fourth setter, restored now that event 546 can move the local. Until
            // this arm existed the handle could only ever be the buffer's own Clear()'d null,
            // so the call was omitted as a no-op.
            lpWrite->SetCalibrationTextureHandle(lhCalibrationTextureHandle);
            lpWrite->UnlockForWrite();
        }
    }

    // ------------------------------------------------------------------------------------
    // BridgeGuiToDirector  @ 0x823CBF70   -- ⭐ THE GUI -> DIRECTOR SEAM
    //
    // The console walks the GUI module's out-event queue and, for each recognised command,
    // raises the matching published flag on the DIRECTOR's input buffer. Every store is a
    // literal 1 (or a payload word) into the buffer's flag tail; MainDirector::PostGuiUpdate
    // @0x82236F88 reads them all back one pass later and folds them into the director's
    // GameState. Reconstructed arm-for-arm from the X360 switch; each `case` below carries the
    // console's own offset so the mapping is checkable.
    //
    // ⭐ 476 / 477 / 478 are the whole point of this function for the intro: BrnGui::Intro
    // posts 477 at START_FLYBY and 478 when its 7.67 s dwell expires, and until this bridge
    // existed NOTHING carried them anywhere -- the director never learned the front-end had
    // asked for a fly-by. Their meanings are NOT assumed: 477 -> +0x7ABE ->
    // GameState::mbGameIntroFlybyActive is pinned by ArbStateCarSelect::Update's own assert
    // string, and 476/478 fall either side of it in both the DWARF member order and the asm.
    //
    // FLAG PC-ABI adapter (identical to BridgeGuiToGame's): on the console the GUI out queue
    // re-keys each record by its GuiEventWrapper type, so GetFirstEvent returns 477 directly
    // and hands back the boxed payload. The PC GuiModule keeps the records on their CHANNEL
    // (40) and forwards them verbatim, so the type is read out of the record's own header word
    // and the payload is taken at the record's own miOutEventOffset -- which is exactly what
    // the console's GuiEventWrapper::GetRawEvent() does, so the payload words the arms read are
    // the same words.
    // ------------------------------------------------------------------------------------
    void BrnGameModule::BridgeGuiToDirector(BrnDirector::DirectorIO::InputBuffer* lpDirectorInput,
                                            CgsModule::VariableEventQueue<18432, 16>* lpGuiOutQueue)
    {
        if (lpDirectorInput == 0 || lpGuiOutQueue == 0)
            return;

        const CgsModule::Event* lpEvent = 0;
        s32 liSize = 0;
        s32 liId = lpGuiOutQueue->GetFirstEvent(&lpEvent, &liSize);
        while (liId >= 0 && lpEvent != 0)
        {
            // ---- resolve (command, payload) -- see the PC-ABI FLAG above ------------------
            const u32* lpuRecord  = reinterpret_cast<const u32*>(lpEvent);
            s32        liCommand  = liId;
            const u32* lpuPayload = lpuRecord;
            if (liId == 40 && liSize >= 12)
            {
                liCommand = static_cast<s32>(lpuRecord[1]);
                const u32 luOffset = lpuRecord[2];
                if (luOffset >= 12u && static_cast<s32>(luOffset) < liSize)
                {
                    lpuPayload = reinterpret_cast<const u32*>(
                        reinterpret_cast<const u8*>(lpEvent) + luOffset);
                }
            }
            const s32 liPayload0 = static_cast<s32>(lpuPayload[0]);

            switch (liCommand)
            {
                case 77:    // +0x7ACC  the car-select ticker closed
                    lpDirectorInput->SetCarSelectTickerClosedThisFrame();
                    break;

                case 94:    // the shortcut menu opened/closed (payload word = the new state)
                    lpDirectorInput->SetShortcutMenuEvent(liPayload0 != 0);
                    break;

                case 191:   // crash-nav shown/hidden -- ignored entirely when payload[1] == 2
                    if (static_cast<s32>(lpuPayload[1]) != 2)
                    {
                        if (liPayload0 == 0)
                            lpDirectorInput->SetGotCrashNavShownEvent();
                        else if (liPayload0 == 1)
                            lpDirectorInput->SetGotCrashNavHiddenEvent();
                    }
                    break;

                case 192:   // +0x7AC2  end of car select (only for payload {4, 1})
                    if (liPayload0 == 4 && static_cast<s32>(lpuPayload[1]) == 1)
                        lpDirectorInput->SetEndOfCarSelect();
                    break;

                case 290:   // +0x7AD0  entered the online post-event flow
                    lpDirectorInput->SetEnteredOnlinePostEvent();
                    break;

                case 294:   // +0x7ACF  left the online post-event flow
                    lpDirectorInput->SetLeftOnlinePostEvent();
                    break;

                case 298:   // the console's own "over to you, Big E..." placeholder -- a debug
                            // print and nothing else. Kept because it is real console output.
                    if ((CgsDev::Message::gxMessageFilterFlags & 1) != 0
                        && CgsDev::Log::gpDebugPrint != 0)
                    {
                        *CgsDev::Log::gpDebugPrint
                            << "Handle new rival camera presentation stuff here - over to you, Big E...\n";
                    }
                    break;

                case 303:   // +0x7ABC / +0x7AB4  rank up this frame + the new rank. The X360
                            // also runs the colour-calibration-shown store on this arm (the
                            // compiler merged the two tails); reproduced.
                    lpDirectorInput->SetRankUp(liPayload0);
                    lpDirectorInput->SetGotColourCalibrationShownEvent();
                    break;

                case 415:   // +0x7ACB  the car selection changed
                    lpDirectorInput->SetCarSelectionChangedThisFrame();
                    break;

                case 469:   // +0x7AD3 / +0x7AD4  the 100%-completion sequence start/finish
                case 470:   // (the two ids share one body on the console)
                    if (liPayload0 != 0)
                        lpDirectorInput->SetStarting100PercentSequence();
                    else
                        lpDirectorInput->SetFinished100PercentSequence();
                    break;

                case 475:   // +0x7AC9 / +0x7AA4  new director profile data + its payload word
                    lpDirectorInput->SetDirectorProfileData(liPayload0);
                    break;

                case 476:   // +0x7ABD  ⭐ start the NEW-PROFILE intro
                    lpDirectorInput->SetStartNewProfileIntro();
                    break;

                case 477:   // +0x7ABE  ⭐ START the GAME-INTRO FLY-BY
                    lpDirectorInput->SetStartGameIntroFlyby();
                    break;

                case 478:   // +0x7ABF  ⭐ STOP the game-intro fly-by (clears both latches)
                    lpDirectorInput->SetStopGameIntroFlyby();
                    break;

                case 479:   // +0x7AD2  online event loading started
                    lpDirectorInput->SetStartedOnlineEventLoading();
                    break;

                case 480:   // +0x7AD1  online event loading finished
                    lpDirectorInput->SetFinishedOnlineEventLoading();
                    break;

                case 501:   // Original count plus100 pointers, at native host width.
                            // Retain the existing host record-bound/legacy-wrapper guard.
                    static_assert(sizeof(BrnGui::GuiPFXHookEnumeration) ==
                                  BrnDirector::DirectorIO::InputBuffer::KU_HOOK_ENUMERATION_BYTES,
                                  "the director copies the canonical501 payload");
                    if (liSize >= static_cast<s32>(BrnDirector::DirectorIO::InputBuffer::KU_HOOK_ENUMERATION_BYTES
                                                   + (reinterpret_cast<const u8*>(lpuPayload)
                                                          - reinterpret_cast<const u8*>(lpEvent))))
                    {
                        lpDirectorInput->SetHookEnumeration(
                            reinterpret_cast<const BrnGui::GuiPFXHookEnumeration*>(lpuPayload));
                        if (getenv("BRN_PFX_DIAG") != 0 && CgsDev::Log::gpDebugPrint != 0)
                            *CgsDev::Log::gpDebugPrint << "[pfx-dir] 501 record (" << liSize << " bytes) -> director input\n";
                    }
                    break;

                case 514:
                    lpDirectorInput->SetGotColourCalibrationShownEvent();
                    break;

                case 515:
                    lpDirectorInput->SetGotColourCalibrationHiddenEvent();
                    break;

                case 591:   // +0x7AB8  the requested camera type. The console stores 0 or 1 and
                            // fires "Unhandled camera type : <n>" for anything else WITHOUT
                            // storing (GameBridgeGUIToX.cpp:1657).
                    CGS_ASSERT(liPayload0 == 0 || liPayload0 == 1, "Unhandled camera type");
                    if (liPayload0 == 0 || liPayload0 == 1)
                        lpDirectorInput->SetCameraType(liPayload0);
                    break;

                default:
                    break;
            }

            const CgsModule::Event* lpNext = 0;
            liId = lpGuiOutQueue->GetNextEvent(lpEvent, &lpNext, &liSize);
            lpEvent = lpNext;
        }
    }



    // The per-frame spines the in-game flow state drives (MainGameFlowStateInGame::
    // Update -> DoUpdate, ::Render -> DoDispatch). On the X360 these run the game
    // module's owned-module update/dispatch walk; the PC host loop (EngineUpdate ->
    // BrnGameModule::DispatchThread) already drives that walk once per frame, so a
    // second walk here would double-update every module.
    // FLAG PC-platform leaf: no-op returns until the module scheduler ownership moves
    // under the game module's own spines (the host loop is the current driver).
    int BrnGameModule::DoUpdate()
    {
        return 0;
    }

    // ARTIST 823EE0E8..823EE4D4; DecFIGS BrnGameModuleUpdateFunctions.cpp:156.
    // The input belongs to this call, including its original failure assertions
    // and destruction after the outer GameState monitor has stopped.
    void BrnGameModule::DoUpdate_GameStatePreWorld(
        CgsModule::IOBufferStack* lpInputBufferStack,
        CgsModule::IOBufferStack* lpOutputBufferStack,
        const CgsInput::InputIO::OutputBuffer* lpInputModuleOutput,
        const BrnNetwork::BrnNetworkModuleIO::OutputBuffer* lpNetworkOutput,
        BrnGameState::GameStateModuleIO::OutputBuffer* lpGameStateOutput,
        BrnUpdateSet lUpdateSet)
    {
        using namespace BrnGameState::GameStateModuleIO;
        CgsDev::PerfMonCpu::StartMonitor(mCpuMonitors.miUT_GameState);
        CgsModule::IOHelper<PreWorldInputBuffer> lInput(lpInputBufferStack, "GameStatePreWorld");
        PreWorldInputBuffer* const lpInput = lInput;
        CgsDev::PerfMonCpu::StartMonitor(mCpuMonitors.miUT_GameState_Bridge);
        // sub_823B6FE0 checks both pointers before taking W(input)/R(input output).
        CGS_ASSERT(lpInput != 0, "lpInputBuffer");
        CGS_ASSERT(lpInputModuleOutput != 0, "lpOutputBuffer0");
        CgsModule::LockBuffersForIO(lpInput, lpInputModuleOutput);
        const bool lbWasStalled = mbStreamingStalled;

        if (mbSteppingFrames)
        {
            if (mbStopStepping)
            {
                if (mbSimPaused)
                {
                    PlayerPauseStateChangedEvent lEvent;
                    lEvent.mbActivated = false;
                    lEvent.mbStalled = false;
                    lEvent.mbWasStalled = lbWasStalled;
                    lpInput->GetGameEventQueue()->AddEvent(&lEvent,
                        E_EVENT_PLAYER_PAUSE_STATE_CHANGED);
                }
                mbStopStepping = false;
                mbSteppingFrames = false;
                mbDoStep = false;
            }
            else if (mbDoStep)
            {
                PlayerPauseStateChangedEvent lEvent;
                lEvent.mbActivated = !mbSimPaused;
                lEvent.mbStalled = false;
                lEvent.mbWasStalled = lbWasStalled;
                if (!mbSimPaused)
                    mbDoStep = false;
                lpInput->GetGameEventQueue()->AddEvent(&lEvent,
                    E_EVENT_PLAYER_PAUSE_STATE_CHANGED);
            }
        }

        if (mbWorldStreamingRequestedStall)
        {
            if (!mbSimPaused)
            {
                if (!mbOnline)
                {
                    PlayerPauseStateChangedEvent lEvent;
                    lEvent.mbActivated = true;
                    lEvent.mbStalled = true;
                    lEvent.mbWasStalled = lbWasStalled;
                    lpInput->GetGameEventQueue()->AddEvent(&lEvent,
                        E_EVENT_PLAYER_PAUSE_STATE_CHANGED);
                }
                mbStreamingStalled = true;
            }
        }
        else if (mbStreamingStalled)
        {
            if (!mbOnline)
            {
                PlayerPauseStateChangedEvent lEvent;
                lEvent.mbActivated = false;
                lEvent.mbStalled = false;
                lEvent.mbWasStalled = lbWasStalled;
                lpInput->GetGameEventQueue()->AddEvent(&lEvent,
                    E_EVENT_PLAYER_PAUSE_STATE_CHANGED);
            }
            mbStreamingStalled = false;
        }

        if (mbStreamingStalled && sbShowStreamStallMessage)
        {
            CgsDev::DebugInterface lDebug;
            lDebug.Get2dRender().Draw2DText(
                "STREAM STALL: Stalling game while streaming catches up",
                Vector2{200.0f, 40.0f}, 16.0f, 0xFF0000FFu);
        }

        lpNetworkOutput->LockForRead();
        BridgeNetworkToGameState(lpInput, lpNetworkOutput);
        BridgeControllerToGameState(lpInput, lpInputModuleOutput, lpNetworkOutput->IsPlaying());
        lpNetworkOutput->UnlockForRead();
        if (mMainFlowStateMachine.IsVideoState())
        {
            CgsModule::UnlockBuffersForIO(lpInput, lpInputModuleOutput);
            CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_GameState_Bridge);
        }
        else
        {
            if (mbRequestStreamingWait)
            {
                mbRequestStreamingWait = false;
                // The original empty game-start tag copies one unspecified byte.
                GameEvent<E_EVENT_GAME_START> lEvent;
                lpInput->GetGameEventQueue()->AddEvent(&lEvent, E_EVENT_GAME_START);
            }
            lpInput->SetTimerStatusInterface(&mTimerStatusInterface);
            CgsModule::UnlockBuffersForIO(lpInput, lpInputModuleOutput);
            CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_GameState_Bridge);
            if (!mbDiskError)
                mGameStateModule.PreWorldUpdate(lpInputBufferStack, lpOutputBufferStack,
                    lpInput, lpGameStateOutput, lUpdateSet);
            CheckGameActions(lpGameStateOutput);
        }
        CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_GameState);
    }

    // @ 0x823EE4D8 -- the SOUND pre-update leg (faithful-audio-engine phase C4). Called by
    // BOTH console spines ahead of the network/game-state/world drives: the loading spine
    // @0x823F2714 and the full DoUpdate cascade. Statement for statement against the 42-instr
    // X360 body (progress/scratch_dossiers/spine_sound_leg_0x823F22D8.md section 4):
    //   * the miUT_Sound + miUT_SoundUpdate monitor pair brackets the WHOLE body (the only
    //     sound perfmon anywhere on the loading spine);
    //   * RootSoundModule::PreUpdate publishes the logic module's pre-update block into the
    //     caller's RootPreUpdateOutputBuffer (the stack arg is only forwarded there);
    //   * under the console's W(guiIn)+R(preUpdateOut) helper bracket (sub_823B6FE0 /
    //     sub_823B7060, reproduced inline -- the per-source idiom this repo already uses),
    //     the pre-update GuiOut queue (VariableEventQueue<256,16>) is bulk-appended into the
    //     GUI input buffer's 32768 event queue (Append<256,16> @0x823DAF20), then
    //     BridgeSoundToTraining walks the audio-effects message queue.
    void BrnGameModule::DoPreUpdate_Sound(CgsModule::IOBufferStack* lpUpdateOutputBufferStack,
                                          BrnSound::Module::Io::RootPreUpdateOutputBuffer* lpSoundPreUpdateOutputBuffer,
                                          CgsGui::CgsGuiModuleIO::InputBuffer* lpGuiInputBuffer)
    {
        CgsDev::PerfMonCpu::StartMonitor(mCpuMonitors.miUT_Sound);
        CgsDev::PerfMonCpu::StartMonitor(mCpuMonitors.miUT_SoundUpdate);

        mSoundModule.PreUpdate(lpUpdateOutputBufferStack, lpSoundPreUpdateOutputBuffer);

        // Console lock-pair helper sub_823B6FE0: assert both, W(dest guiIn), R(src preUpdateOut).
        CGS_ASSERT(lpGuiInputBuffer != 0, "lpInputBuffer");
        CGS_ASSERT(lpSoundPreUpdateOutputBuffer != 0, "lpOutputBuffer0");
        lpGuiInputBuffer->LockForWrite();
        lpSoundPreUpdateOutputBuffer->LockForRead();

        lpGuiInputBuffer->GetGuiEvents()->Append<256, 16>(
            lpSoundPreUpdateOutputBuffer->GetGuiEventQueue());

        BridgeSoundToTraining(lpSoundPreUpdateOutputBuffer);

        // sub_823B7060: unlock in reverse.
        lpSoundPreUpdateOutputBuffer->UnlockForRead();
        lpGuiInputBuffer->UnlockForWrite();

        CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_SoundUpdate);
        CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_Sound);
    }

    // @ 0x823DCEC0 -- the SOUND leg of the full cascade (faithful-audio-engine phase C4b).
    // Statement for statement against the 121-instr X360 body; the full register-level
    // decode is progress/scratch_dossiers/doupdate_sound_0x823DCEC0.md. Console facts
    // honored here: the RootInputBuffer is SELF-CARVED per call ("Sound", off the
    // update-INPUT stack -- the same instantiation the loading spine uses); the six-buffer
    // lock helper sub_823B7620 takes W(rootIn) + R(director/world/gamestate/gui/replays)
    // and the effects output is a LOCK-ONLY participant on an interleaved bracket (nothing
    // reads it -- keep the pair); the bridge order is WorldToSound -> SetCameraInput ->
    // GameStateToSound -> GuiToSound -> SetReplayStatusInterface (a DIFFERENT order from
    // the loading spine, plus the two installs it never does); every leg is UNCONDITIONAL
    // on console; all locks release BEFORE RootSoundModule::Update (it takes its own); the
    // perfmon pair covers everything but the DestroyIOBuffer; NO resource forward here
    // (the caller drains the root output in its own tail).
    // FLAG PC null-tolerance: the console lock helper asserts every buffer non-null. On
    // this build the replay pre-sim output (module not driven per-frame yet) and the
    // effects output (module unmounted) arrive null, and the world/director/game-state/gui
    // statics can be null on defensive frames -- each leg skips its absent source rather
    // than faking one. Retire the guards as the modules come live.
    void BrnGameModule::DoUpdate_Sound(CgsModule::IOBufferStack* lpInputBufferStack,
                                       CgsModule::IOBufferStack* lpOutputBufferStack,
                                       BrnGameState::GameStateModuleIO::OutputBuffer* lpGameStateOutputBuffer,
                                       BrnWorldIO::UpdateOutputBuffer* lpWorldOutputBuffer,
                                       BrnDirector::DirectorIO::OutputBuffer* lpDirectorOutputBuffer,
                                       BrnReplays::ReplayIO::OutputBuffer_PreSim* lpReplaysPreSimOutputBuffer,
                                       BrnSound::Module::Io::RootOutputBuffer* lpSoundOutputBuffer,
                                       CgsGui::CgsGuiModuleIO::OutputBuffer* lpGuiOutputBuffer,
                                       BrnEffects::EffectsIO::OutputBuffer* lpEffectsOutputBuffer,
                                       BrnUpdateSet leUpdateSet)
    {
        typedef BrnSound::Module::Io::RootInputBuffer RootIn;

        CgsDev::PerfMonCpu::StartMonitor(mCpuMonitors.miUT_Sound);
        CgsDev::PerfMonCpu::StartMonitor(mCpuMonitors.miUT_SoundUpdate);

        // The self-carved "Sound" root input (console @0x823DCF20, the CgsModuleIOHelper
        // create/destroy pair with the h:52/h:57 asserts).
        RootIn* lpSoundInputBuffer = 0;
        const bool lbCreated = lpInputBufferStack->CreateIOBuffer(&lpSoundInputBuffer, "Sound");
        CGS_ASSERT(lbCreated, "mpStack->CreateIOBuffer( &mpBuffer, lpcName )");  // CgsModuleIOHelper.h:52
        (void)lbCreated;

        // sub_823B7620 (bracket A), then the effects read lock (bracket B, interleaved).
        lpSoundInputBuffer->LockForWrite();
        if (lpDirectorOutputBuffer != 0)     lpDirectorOutputBuffer->LockForRead();
        if (lpWorldOutputBuffer != 0)        lpWorldOutputBuffer->LockForRead();
        if (lpGameStateOutputBuffer != 0)    lpGameStateOutputBuffer->LockForRead();
        if (lpGuiOutputBuffer != 0)          lpGuiOutputBuffer->LockForRead();
        if (lpReplaysPreSimOutputBuffer != 0) lpReplaysPreSimOutputBuffer->LockForRead();
        if (lpEffectsOutputBuffer != 0)      lpEffectsOutputBuffer->LockForRead();

        // @0x823DCF98 -- the world -> sound copy + installs (the update set feeds the
        // bit-0x100 replay-source select).
        if (lpWorldOutputBuffer != 0)
            BridgeWorldToSound(lpSoundInputBuffer, lpWorldOutputBuffer, leUpdateSet);

        // @0x823DCFA0/AC -- the director camera into the root input (+0x2F20 on console).
        // SetCameraInput invokes Camera::operator= on the complete by-value camera,
        // matching the console root-input member at +0x2F20.
        if (lpDirectorOutputBuffer != 0)
            lpSoundInputBuffer->SetCameraInput(lpDirectorOutputBuffer->GetCameraOutput());

        // @0x823DCFBC -- the game-state bridge (this leg is its ONLY console caller).
        if (lpGameStateOutputBuffer != 0)
            BridgeGameStateToSound(lpSoundInputBuffer, lpGameStateOutputBuffer);

        // @0x823DCFD4 -- the GUI out-queue install (console reloads the gm+0x9A0BD8
        // member; on PC the caller passes the same static buffer).
        if (lpGuiOutputBuffer != 0)
            BridgeGuiToSound(lpSoundInputBuffer, lpGuiOutputBuffer);

        // @0x823DCFDC/E8 -- the replay status interface into the root input (+0x4).
        if (lpReplaysPreSimOutputBuffer != 0)
            lpSoundInputBuffer->SetReplayStatusInterface(
                reinterpret_cast<const RootIn::ReplayStatusInterface*>(
                    lpReplaysPreSimOutputBuffer->GetStatusInterface()));

        // sub_823B7760 (reverse of bracket A), then the effects unlock (bracket B).
        if (lpReplaysPreSimOutputBuffer != 0) lpReplaysPreSimOutputBuffer->UnlockForRead();
        if (lpGuiOutputBuffer != 0)          lpGuiOutputBuffer->UnlockForRead();
        if (lpGameStateOutputBuffer != 0)    lpGameStateOutputBuffer->UnlockForRead();
        if (lpWorldOutputBuffer != 0)        lpWorldOutputBuffer->UnlockForRead();
        if (lpDirectorOutputBuffer != 0)     lpDirectorOutputBuffer->UnlockForRead();
        lpSoundInputBuffer->UnlockForWrite();
        if (lpEffectsOutputBuffer != 0)      lpEffectsOutputBuffer->UnlockForRead();

        // @0x823DD054 -- the pump, with the console's exact timer products (identical to
        // the loading spine's @0x823F2AC8; cross-confirmed in the decode).
        {
            const CgsSystem::Timer& lrGameTimer = mGameTimer;
            const CgsSystem::Timer& lrSimTimer  = mSimTimer;
            mSoundModule.Update(
                lrGameTimer.GetScaleCurrent() * lrGameTimer.GetRate(),
                lrSimTimer.GetScaleCurrent() * lrSimTimer.GetRate(),
                lpInputBufferStack,
                lpOutputBufferStack,
                lpSoundInputBuffer,
                lpSoundOutputBuffer,
                leUpdateSet);
        }

        CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_SoundUpdate);
        CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_Sound);

        const bool lbDestroyed = lpInputBufferStack->DestroyIOBuffer(&lpSoundInputBuffer);
        CGS_ASSERT(lbDestroyed, "mpStack->DestroyIOBuffer( &mpBuffer )");  // CgsModuleIOHelper.h:57
        (void)lbDestroyed;
    }

    // ARTIST 0x823DD2A0. The update thread creates the phase input, merges the game-action
    // queue and timer snapshot, calls ReplayModule::Update_PreSim through virtual slot +0x44,
    // then serialises this frame's SIM TimerStatus through GameModuleSerialiser.
    void BrnGameModule::DoUpdate_ReplaysPreSim(
        CgsModule::IOBufferStack* lpUpdateInputBufferStack,
        CgsModule::IOBufferStack* /*lpUpdateOutputBufferStack*/,
        const BrnGameState::GameStateModuleIO::OutputBuffer* lpGameStateOutputBuffer,
        BrnReplays::ReplayIO::OutputBuffer_PreSim* lpReplaysPreSimOutputBuffer,
        BrnUpdateSet lUpdateSet)
    {
        CgsDev::PerfMonCpu::StartMonitor(mCpuMonitors.miUT_Replay);

        CgsModule::IOHelper<BrnReplays::ReplayIO::InputBuffer_PreSim> lReplayInput(
            lpUpdateInputBufferStack, "ReplaysPreSim");
        BrnReplays::ReplayIO::InputBuffer_PreSim* const lpReplayInputBuffer = lReplayInput;

        // ARTIST sub_823B6FE0 pointer assertions (CgsModuleUtils.h:259-260).
        if (lpReplayInputBuffer == 0)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert(
                "lpInputBuffer",
                "d:\\p4\\b5_main\\burnout\\main\\code\\gameshared\\gameclasses\\module\\CgsModuleUtils.h",
                259);
            CgsDev::Assert::EndAssert();
        }
        if (lpGameStateOutputBuffer == 0)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert(
                "lpOutputBuffer0",
                "d:\\p4\\b5_main\\burnout\\main\\code\\gameshared\\gameclasses\\module\\CgsModuleUtils.h",
                260);
            CgsDev::Assert::EndAssert();
        }
        CgsModule::LockBuffersForIO(lpReplayInputBuffer, lpGameStateOutputBuffer);
        lpReplayInputBuffer->AppendGameActionQueue(lpGameStateOutputBuffer->GetGameActionQueue());
        lpReplayInputBuffer->SetTimerStatusInterface(&mTimerStatusInterface);
        // ARTIST sub_823B7060 pointer assertions (CgsModuleUtils.h:272-273).
        if (lpReplayInputBuffer == 0)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert(
                "lpInputBuffer",
                "d:\\p4\\b5_main\\burnout\\main\\code\\gameshared\\gameclasses\\module\\CgsModuleUtils.h",
                272);
            CgsDev::Assert::EndAssert();
        }
        if (lpGameStateOutputBuffer == 0)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert(
                "lpOutputBuffer0",
                "d:\\p4\\b5_main\\burnout\\main\\code\\gameshared\\gameclasses\\module\\CgsModuleUtils.h",
                273);
            CgsDev::Assert::EndAssert();
        }
        CgsModule::UnlockBuffersForIO(lpReplayInputBuffer, lpGameStateOutputBuffer);

        mReplayModule.Update_PreSim(lpReplayInputBuffer, lpReplaysPreSimOutputBuffer, lUpdateSet);

        mGameModuleSerialiser.Lock();
        mGameModuleSerialiser.Serialise(
            mTimerStatusInterface.GetSimTimerStatus(),
            static_cast<s32>(sizeof(CgsSystem::TimerStatus)));
        mGameModuleSerialiser.Unlock();
        mGameModuleSerialiser.SetDataReady(true);
        mGameModuleSerialiser.SetDataRestored(true);

        CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_Replay);
    }

    // ARTIST 0x823DD408. Merge the five producer request interfaces and GUI events into a
    // Replay PostSim input, register the two game-owned serialisers, then call virtual slot +0x48.
    void BrnGameModule::DoUpdate_ReplaysPostSim(
        CgsModule::IOBufferStack* lpUpdateInputBufferStack,
        CgsModule::IOBufferStack* /*lpUpdateOutputBufferStack*/,
        const BrnWorldIO::UpdateOutputBuffer* lpWorldOutputBuffer,
        const BrnEffects::EffectsIO::OutputBuffer* lpEffectsOutputBuffer,
        const BrnSound::Module::Io::RootOutputBuffer* lpSoundOutputBuffer,
        BrnDirector::DirectorIO::OutputBuffer* lpDirectorOutputBuffer,
        const CgsGui::CgsGuiModuleIO::OutputBuffer* lpGuiOutputBuffer,
        BrnReplays::ReplayIO::OutputBuffer_PostSim* lpReplaysPostSimOutputBuffer,
        BrnUpdateSet lUpdateSet)
    {
        CgsDev::PerfMonCpu::StartMonitor(mCpuMonitors.miUT_Replay);

        CgsModule::IOHelper<BrnReplays::ReplayIO::InputBuffer_PostSim> lReplayInput(
            lpUpdateInputBufferStack, "ReplaysPostSim");
        BrnReplays::ReplayIO::InputBuffer_PostSim* const lpReplayInputBuffer = lReplayInput;

        // ARTIST sub_823B7620 pointer assertions (CgsModuleUtils.h:403-408).
        if (lpReplayInputBuffer == 0)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert(
                "lpInputBuffer",
                "d:\\p4\\b5_main\\burnout\\main\\code\\gameshared\\gameclasses\\module\\CgsModuleUtils.h",
                403);
            CgsDev::Assert::EndAssert();
        }
        if (lpWorldOutputBuffer == 0)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert(
                "lpOutputBuffer0",
                "d:\\p4\\b5_main\\burnout\\main\\code\\gameshared\\gameclasses\\module\\CgsModuleUtils.h",
                404);
            CgsDev::Assert::EndAssert();
        }
        if (lpEffectsOutputBuffer == 0)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert(
                "lpOutputBuffer1",
                "d:\\p4\\b5_main\\burnout\\main\\code\\gameshared\\gameclasses\\module\\CgsModuleUtils.h",
                405);
            CgsDev::Assert::EndAssert();
        }
        if (lpSoundOutputBuffer == 0)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert(
                "lpOutputBuffer2",
                "d:\\p4\\b5_main\\burnout\\main\\code\\gameshared\\gameclasses\\module\\CgsModuleUtils.h",
                406);
            CgsDev::Assert::EndAssert();
        }
        if (lpDirectorOutputBuffer == 0)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert(
                "lpOutputBuffer3",
                "d:\\p4\\b5_main\\burnout\\main\\code\\gameshared\\gameclasses\\module\\CgsModuleUtils.h",
                407);
            CgsDev::Assert::EndAssert();
        }
        if (lpGuiOutputBuffer == 0)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert(
                "lpOutputBuffer4",
                "d:\\p4\\b5_main\\burnout\\main\\code\\gameshared\\gameclasses\\module\\CgsModuleUtils.h",
                408);
            CgsDev::Assert::EndAssert();
        }
        CgsModule::LockBuffersForIO(lpReplayInputBuffer, lpWorldOutputBuffer, lpEffectsOutputBuffer,
                                    lpSoundOutputBuffer, lpDirectorOutputBuffer, lpGuiOutputBuffer);
        lpReplayInputBuffer->AppendRequestInterface(lpWorldOutputBuffer->GetReplayRequestInterface());
        lpReplayInputBuffer->AppendRequestInterface(lpEffectsOutputBuffer->GetReplayRequestInterface());
        lpReplayInputBuffer->AppendRequestInterface(lpSoundOutputBuffer->GetReplayRequestInterface());
        const BrnReplays::ReplayIO::RequestInterface* const lpcDirectorRequests =
            reinterpret_cast<const BrnReplays::ReplayIO::RequestInterface*>(
                lpDirectorOutputBuffer->GetReplayRe());
        lpReplayInputBuffer->AppendRequestInterface(lpcDirectorRequests);
        BridgeGuiToReplay_PostSim(lpReplayInputBuffer, lpGuiOutputBuffer);

        BrnReplays::ReplayIO::RequestInterface* const lpRequestInterface =
            lpReplayInputBuffer->GetRequestInterface();
        lpRequestInterface->RegisterSerialiser(&mDirectorBridgeSerialiser);
        lpRequestInterface->RegisterSerialiser(&mGameModuleSerialiser);
        // ARTIST sub_823B7760 pointer assertions (CgsModuleUtils.h:428-433).
        if (lpReplayInputBuffer == 0)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert(
                "lpInputBuffer",
                "d:\\p4\\b5_main\\burnout\\main\\code\\gameshared\\gameclasses\\module\\CgsModuleUtils.h",
                428);
            CgsDev::Assert::EndAssert();
        }
        if (lpWorldOutputBuffer == 0)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert(
                "lpOutputBuffer0",
                "d:\\p4\\b5_main\\burnout\\main\\code\\gameshared\\gameclasses\\module\\CgsModuleUtils.h",
                429);
            CgsDev::Assert::EndAssert();
        }
        if (lpEffectsOutputBuffer == 0)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert(
                "lpOutputBuffer1",
                "d:\\p4\\b5_main\\burnout\\main\\code\\gameshared\\gameclasses\\module\\CgsModuleUtils.h",
                430);
            CgsDev::Assert::EndAssert();
        }
        if (lpSoundOutputBuffer == 0)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert(
                "lpOutputBuffer2",
                "d:\\p4\\b5_main\\burnout\\main\\code\\gameshared\\gameclasses\\module\\CgsModuleUtils.h",
                431);
            CgsDev::Assert::EndAssert();
        }
        if (lpDirectorOutputBuffer == 0)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert(
                "lpOutputBuffer3",
                "d:\\p4\\b5_main\\burnout\\main\\code\\gameshared\\gameclasses\\module\\CgsModuleUtils.h",
                432);
            CgsDev::Assert::EndAssert();
        }
        if (lpGuiOutputBuffer == 0)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert(
                "lpOutputBuffer4",
                "d:\\p4\\b5_main\\burnout\\main\\code\\gameshared\\gameclasses\\module\\CgsModuleUtils.h",
                433);
            CgsDev::Assert::EndAssert();
        }
        CgsModule::UnlockBuffersForIO(lpReplayInputBuffer, lpWorldOutputBuffer, lpEffectsOutputBuffer,
                                      lpSoundOutputBuffer, lpDirectorOutputBuffer, lpGuiOutputBuffer);

        mReplayModule.Update_PostSim(lpReplayInputBuffer, lpReplaysPostSimOutputBuffer, lUpdateSet);

        CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_Replay);
    }

    // @ 0x823E8BD0 -- DoUpdate's WORLD leg. Reconstructed against the X360 body; the
    // per-frame world drive itself (the vtable +76 dispatch and the boot-video variant) is
    // REAL here. NOTE the caller DoUpdate is still the PC-platform leaf above (the PC host
    // loop owns the module drive), so today the world is driven per frame by the scripted
    // loading spine's LoadingScriptedState::UpdateWorldModule instead; this entry is the
    // in-game cascade's hook and goes live with the DoUpdate reconstruction.
    //
    // X360 order:
    //   StartMonitor(gm+10055508);
    //   CreateIOBuffer<BrnWorldIO::UpdateInputBuffer>(inStack, &worldIn, "World")
    //     (asserting "mpStack->CreateIOBuffer( &mpBuffer, lpcName )", CgsModuleIOHelper.h:52);
    //   sub_823B7620(worldIn, controllerOut, gameStateOut, guiOut, replayOut, soundOut)
    //     == LockBuffersForIO with FIVE sources;
    //   UpdateInputBuffer::SetTimerStatusInterface(worldIn, gm+10095372);
    //   LockForRead(networkOut);
    //   BridgeControllerToWorld / BridgeNetworkToWorld / BridgeGameStateToWorld /
    //   BridgeGuiToWorld; SetReplayStatusInterface(ReplayIO::OutputBuffer_PreSim::
    //   GetStatusInterface(replayOut)); BridgeSoundToWorld; UnlockForRead(networkOut);
    //   sub_823B7760(...) == the matching UnlockBuffersForIO;
    //   StopMonitor;
    //   (updateSet & 0x20) ? WorldModule::UpdateForBootUpVideo(updateSet, inStack, outStack,
    //                            worldIn, worldOut)
    //                      : world->vtbl+76(updateSet, inStack, outStack, worldIn, worldOut,
    //                            gm->mpWorldUpdateFrameAllocator);
    //   LockForRead(worldOut);
    //   gm+10094123 = (worldOut->GetWorldEntityStatusInterface()->GetImmediateStreamed() == 0);
    //   UnlockForRead(worldOut);
    //   DestroyIOBuffer(inStack, &worldIn) (asserting CgsModuleIOHelper.h:57).
    void BrnGameModule::DoUpdate_World(CgsModule::IOBufferStack* lpUpdateInputBufferStack,
                                       CgsModule::IOBufferStack* lpUpdateOutputBufferStack,
                                       const CgsInput::InputIO::OutputBuffer* lpInputOutputBuffer,
                                       BrnWorldIO::UpdateOutputBuffer* lpWorldUpdateOutputBuffer,
                                       CgsMemory::LinearMalloc* lpWorldFrameAllocator,
                                       BrnUpdateSet lUpdateSet)
    {
        BrnWorldIO::UpdateInputBuffer* lpWorldInput = 0;
        const bool lbCreated = lpUpdateInputBufferStack->CreateIOBuffer(&lpWorldInput, "World");
        CGS_ASSERT(lbCreated, "mpStack->CreateIOBuffer( &mpBuffer, lpcName )");  // CgsModuleIOHelper.h:52
        (void)lbCreated;

        // Three of the six X360 input-staging bridges are committed now: the CONTROLLER leg,
        // (2026-08-01) the GAME-STATE leg, and (phase C3a/C4) the SOUND leg -- BridgeSoundToWorld
        // @0x823CDC98 is bodied (GameBridgeSoundToX.cpp) and the live world drive
        // (DriveWorldUpdateFrame) stages it when the spine threads the pre-update buffer through.
        // The NETWORK leg (below) is the fourth.
        // [FLAG PC boot gate] BridgeGuiToWorld and the replay-status latch
        // (ReplayIO::OutputBuffer_PreSim::GetStatusInterface) are still not reconstructed; their
        // source modules' output buffers are not threaded into this leg on the PC yet, so that
        // staging is omitted rather than faked. The console's SetTimerStatusInterface
        // (mTimerStatusInterface) is part of the same staging. Restore them with the DoUpdate
        // cascade.
        lpWorldInput->LockForWrite();
        BridgeControllerToWorld(lpWorldInput, lpInputOutputBuffer);
        lpWorldInput->UnlockForWrite();

        // The network -> world bridge, between the controller and game-state bridges under a
        // read lock on the network output (console order). DriveWorldUpdateFrame carries the
        // same call; both sites move together.
        if (mpNetworkOutputBuffer != 0)
        {
            mpNetworkOutputBuffer->LockForRead();
            lpWorldInput->LockForWrite();
            BridgeNetworkToWorld(lpWorldInput, mpNetworkOutputBuffer);
            lpWorldInput->UnlockForWrite();
            mpNetworkOutputBuffer->UnlockForRead();
        }

        // ⭐⭐ THE GAME-STATE -> WORLD BRIDGE (X360 BridgeGameStateToWorld @0x823E1890), the
        // only producer of the world update input buffer's game-action queue. The console gets
        // the game-state output buffer from DoUpdate's own LockBuffersForIO five-source call
        // (sub_823B7620); this leg reaches the module it owns directly, exactly as the director
        // leg does for BridgeGameStateToDirector.
        // ⚠️ NOTE this entry is currently UNREACHED -- DoUpdate is a PC-platform leaf, so the
        // live world drive is DriveWorldUpdateFrame (BrnGameMainFlowStates.cpp), which runs the
        // same bridge. Both sites move together.
        {
            BrnGameState::GameStateModuleIO::OutputBuffer* lpGameStateOutput =
                mGameStateModule.GetOutputBuffer();
            if (lpGameStateOutput != 0)
            {
                lpGameStateOutput->LockForRead();
                lpWorldInput->LockForWrite();
                BridgeGameStateToWorld(lpWorldInput, lpGameStateOutput);
                lpWorldInput->UnlockForWrite();
                lpGameStateOutput->UnlockForRead();
            }
        }

        if ((lUpdateSet & 0x20) != 0)
        {
            mWorldModule.UpdateForBootUpVideo(lUpdateSet, lpUpdateInputBufferStack,
                                              lpUpdateOutputBufferStack,
                                              lpWorldInput, lpWorldUpdateOutputBuffer);
        }
        else
        {
            mWorldModule.Update(lUpdateSet, lpUpdateInputBufferStack, lpUpdateOutputBufferStack,
                                lpWorldInput, lpWorldUpdateOutputBuffer, lpWorldFrameAllocator);
        }

        // ARTIST 823E8D70..823E8DA0: publish the streaming-stall request for
        // the following original GameState pre-world pass under the output read lock.
        lpWorldUpdateOutputBuffer->LockForRead();
        mbWorldStreamingRequestedStall =
            !lpWorldUpdateOutputBuffer->GetWorldEntityStatusInterface()->GetImmediateStreamed();
        lpWorldUpdateOutputBuffer->UnlockForRead();

        const bool lbDestroyed = lpUpdateInputBufferStack->DestroyIOBuffer(&lpWorldInput);
        CGS_ASSERT(lbDestroyed, "mpStack->DestroyIOBuffer( &mpBuffer )");        // CgsModuleIOHelper.h:57
        (void)lbDestroyed;
    }

    // ------------------------------------------------------------------------------------
    // DoUpdate_GameStatePostWorld -- the game-state post-world leg of the update step.
    //
    // Console order:
    //   StartMonitor(miUT_GameState);
    //   IOHelper<PostWorldInputBuffer>(inStack, "GameStatePostWorld")   (asserting
    //     "mpStack->CreateIOBuffer( &mpBuffer, lpcName )", CgsModuleIOHelper.h:52);
    //   StartMonitor(miUT_GameState_Bridge);
    //   LockBuffersForIO(buffer, input, world, gui, replaysPostSim, director);
    //   BridgeGuiToGameState(buffer, gui);
    //   if (!(updateSet & 0x20)) BridgeWorldToGameState(buffer, world);
    //   if (director->GetDirectorOutputInterface()->GetPauseRequest())
    //       game event 43 { GetPauseRequestState() } (1 byte);
    //   the replay post-sim game events appended onto the buffer's game-event queue;
    //   if (!mbIsLoadingScreenVisible && !mbDiskError
    //       && updateSet bit 0x4 != mbControllerDisconnected)
    //       latch it into mbControllerDisconnected and post game event 10 { it } (1 byte);
    //   buffer->SetInPictureParadise(the director camera's E_FLAG_IS_PICTURE_PARADISE);
    //   UnlockBuffersForIO (the same six); StopMonitor(miUT_GameState_Bridge);
    //   if (!(updateSet & 0x20) && !mbDiskError)
    //       GameStateModule::PostWorldUpdate(inStack, outStack, buffer, updateSet);
    //   StopMonitor(miUT_GameState);
    //   the helper's DestroyIOBuffer (asserting "mpStack->DestroyIOBuffer( &mpBuffer )",
    //     CgsModuleIOHelper.h:57).
    //
    // The director pause-request and controller-disconnect producers below are source-recovered.
    // The Replay append remains null-guarded because the active caller still passes null; its
    // PostSim dispatch and lifetime are a separate prerequisite. The current PC full-cascade
    // caller also supplies ConstructUpdateSetFromFsm(), whose body never sets bit 0x4, so the
    // event-10 transition remains dormant until the existing incomplete late-set path is wired.
    // BridgeGuiToGameState takes the GUI module's own out-event queue and the game-state module
    // (its signature is adapted, see its declaration), so its game events reach the module's
    // carry queue directly rather than through this buffer's game-event queue. They land ahead
    // of the buffer's events either way, which is the console's order.
    // ------------------------------------------------------------------------------------
    void BrnGameModule::DoUpdate_GameStatePostWorld(CgsModule::IOBufferStack* lpUpdateInputBufferStack,
                                                    CgsModule::IOBufferStack* lpUpdateOutputBufferStack,
                                                    const CgsInput::InputIO::OutputBuffer* lpInputOutputBuffer,
                                                    const BrnWorldIO::UpdateOutputBuffer* lpWorldUpdateOutputBuffer,
                                                    const CgsGui::CgsGuiModuleIO::OutputBuffer* lpGuiOutputBuffer,
                                                    const BrnReplays::ReplayIO::OutputBuffer_PostSim* lpReplaysPostSimOutputBuffer,
                                                    const BrnDirector::DirectorIO::OutputBuffer* lpDirectorOutputBuffer,
                                                    BrnUpdateSet lUpdateSet)
    {
        CgsDev::PerfMonCpu::StartMonitor(mCpuMonitors.miUT_GameState);

        CgsModule::IOHelper<BrnGameState::GameStateModuleIO::PostWorldInputBuffer> lPostWorldInput(
            lpUpdateInputBufferStack, "GameStatePostWorld");
        BrnGameState::GameStateModuleIO::PostWorldInputBuffer* lpPostWorldInput = lPostWorldInput;

        CgsDev::PerfMonCpu::StartMonitor(mCpuMonitors.miUT_GameState_Bridge);

        // LockBuffersForIO: the buffer write-locked, the five sources read-locked. The replay
        // post-sim source is the only one this build can pass as null.
        lpPostWorldInput->LockForWrite();
        lpInputOutputBuffer->LockForRead();
        lpWorldUpdateOutputBuffer->LockForRead();
        lpGuiOutputBuffer->LockForRead();
        if (lpReplaysPostSimOutputBuffer != 0) lpReplaysPostSimOutputBuffer->LockForRead();
        lpDirectorOutputBuffer->LockForRead();

        // [PC HARNESS, not console code] scheduled GUI records (BRN_NET_SCRIPT); inert unless set.
        BrnNetHarnessPC::InjectGuiEvents(mGuiModule.GetGuiOutQueue());
        BridgeGuiToGameState(&mGameStateModule, mGuiModule.GetGuiOutQueue());

        if ((lUpdateSet & 0x20) == 0)
        {
            BridgeWorldToGameState(lpPostWorldInput, lpWorldUpdateOutputBuffer);
        }

        // ARTIST 0x823E9390..0x823E93CC: event 43 follows the World bridge and precedes
        // Replay's queue append. The typed accessor asserts the Director output read lock.
        const BrnDirector::DirectorOutputInterface* lpDirectorOutputInterface =
            lpDirectorOutputBuffer->GetDirectorOutputInterface();
        if (lpDirectorOutputInterface->GetPauseRequest())
        {
            BrnGameState::GameStateModuleIO::TrainingPauseStateChangedEvent lPauseEvent;
            lPauseEvent.mbActivated = lpDirectorOutputInterface->GetPauseRequestState();
            lpPostWorldInput->GetGameEventQueue()->AddEvent(
                &lPauseEvent,
                BrnGameState::GameStateModuleIO::E_EVENT_TRAINING_PAUSE_STATE_CHANGED);
        }

        // ARTIST 0x823E93D0..0x823E93E4: append Replay events after event 43 and before
        // event 10. The active PC caller currently passes null for this output.
        if (lpReplaysPostSimOutputBuffer != 0)
        {
            lpPostWorldInput->GetGameEventQueue()->Append(
                *lpReplaysPostSimOutputBuffer->GetGameEventQueue());
        }

        // ARTIST 0x823E93F8..0x823E9450: sample update-set bit 0x4 only when neither
        // loading-screen visibility nor disk error suppresses the controller event.
        const bool lbControllerDisconnected = (lUpdateSet & 0x4) != 0;
        if (!mbIsLoadingScreenVisible && !mbDiskError &&
            lbControllerDisconnected != mbControllerDisconnected)
        {
            mbControllerDisconnected = lbControllerDisconnected;
            BrnGameState::GameStateModuleIO::ControllerDisconnectedEvent lDisconnectEvent;
            lDisconnectEvent.mbDisconnected = lbControllerDisconnected;
            lpPostWorldInput->GetGameEventQueue()->AddEvent(
                &lDisconnectEvent,
                BrnGameState::GameStateModuleIO::E_EVENT_CONTROLLER_DISCONNECTED);
        }

        // The picture-paradise byte is the director camera's own state flag (+0x144 bit 14 on the
        // console). Construct leaves it unset, so it is written on every pass.
        lpPostWorldInput->SetInPictureParadise(
            lpDirectorOutputBuffer->GetCameraOutput()->GetState().IsFlagSet(
                BrnDirector::Camera::CameraState::E_FLAG_IS_PICTURE_PARADISE));

        lpDirectorOutputBuffer->UnlockForRead();
        if (lpReplaysPostSimOutputBuffer != 0) lpReplaysPostSimOutputBuffer->UnlockForRead();
        lpGuiOutputBuffer->UnlockForRead();
        lpWorldUpdateOutputBuffer->UnlockForRead();
        lpInputOutputBuffer->UnlockForRead();
        lpPostWorldInput->UnlockForWrite();

        CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_GameState_Bridge);

        if ((lUpdateSet & 0x20) == 0 && !mbDiskError)
        {
            mGameStateModule.PostWorldUpdate(lpUpdateInputBufferStack, lpUpdateOutputBufferStack,
                                             lpPostWorldInput, lUpdateSet);
        }

        CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_GameState);
    }

    // ------------------------------------------------------------------------------------
    // The per-frame DIRECTOR leg (2026-07-29, DJ fly-by campaign).
    //
    // The console drives the director module through the module scheduler in three passes per
    // sub-step, bracketing the GUI update:
    //     DirectorModule::PreSceneQueryUpdate @0x8225C768   (before the scene query)
    //     <the scene manager services the queries>
    //     DirectorModule::Update              @0x82275300   (consumes the answers, runs
    //                                                        MainDirector -> the arbitrator ->
    //                                                        CameraFinaliser, PUBLISHES)
    //     <the GUI update>
    //     DirectorModule::PostGuiUpdate       @0x82250DD0
    //
    // [FLAG PC placement] the PC has no module scheduler yet (BrnGameModule::DoUpdate is a
    // documented no-op -- the host loop owns the module walk), so the three passes are driven
    // straight from the sim loop in the same ORDER, with the scene-query step between passes 1
    // and 2 being whatever the scene manager already did this frame. The two scene-query IO
    // buffers are created per sub-step on the update stacks (the console's own lifetime); the
    // OUTPUT buffer is the frame's mpDirectorOutputBuffer so the published camera is still
    // alive when DoDispatch runs.
    //
    // [FLAG PC input staging] the director INPUT buffer is created and Constructed here but
    // NOT staged: the X360 fills it through BridgeControllerToDirector / the race-car entity
    // module's global output interface / the world's contact + timer publishes, none of which
    // is threaded on the PC. A zero-staged input reports NO live player car
    // (GetPlayerCarIndex + GetUsedRaceCars), which MainDirector::Update reads as its
    // "no player" branch -- so the director carries its last finalised camera forward instead
    // of driving a fabricated one. That is the console's own no-player behaviour, and it is
    // why the published camera is currently STATIC.
    // ------------------------------------------------------------------------------------
    // ------------------------------------------------------------------------------------
    // UpdateTimers  @ 0x823BCFD0
    //
    // The console body is:
    //     LockForRead(gameStateOut); LockForRead(directorOut);
    //     TimerRequests::Append(gm+10095420, GameStateModuleIO::OutputBuffer::GetTimerR(...));
    //     TimerRequests::Append(gm+10095428, ... + 8);
    //     if ( !((GetTimerR(...)[2] >> 2) & 1) )      // the "director owns the timers" bit
    //     {
    //         lpIn = DirectorIO::OutputBuffer::GetTimerRequestIn(directorOut);
    //         TimerRequests::Append(gm+10095420, lpIn);
    //         TimerRequests::Append(gm+10095428, lpIn + 8);
    //     }
    //     UnlockForRead(directorOut); UnlockForRead(gameStateOut);
    //     TimerRequestInterface::ApplyToTimers(gm+10095420, gm+10095316, gm+10095344);
    //     CgsSystem::Timer::Update(gm+10095316);
    //     CgsSystem::Timer::Update(gm+10095344);
    //
    // ⭐⭐ THE REQUEST HALF IS LIVE (2026-08-28, crash-slomo transport wave). THE OLD GATE NOTE
    // WAS STALE IN BOTH OF ITS CLAIMS, and it was load-bearing: it said "the two producers are
    // BOTH un-staged on this build (the GameState module is a placeholder, and the director
    // output's timer request interface is never written)". Measured against the tree:
    //   * The GameState producer is REAL and SHIPPING. DriveThruManager::SetPlayerCarDriver
    //     (BrnDriveThruManager.cpp, mounted 2026-08-27) calls
    //     `GetSimTimerRequests()->SetTimestepMultiplier(0.52631581f)` -- the drive-thru's own
    //     slow-motion presentation -- off exactly this buffer's GetTimerRequestInterface(),
    //     handed to it by GameStateModule_gUI_00.cpp:751. ModeManager::FinishCurrentMode
    //     (BrnModeManager_Finish.cpp:460) posts the 1.0f restore on the same slot.
    //   * The director producer is written as of this wave (MainDirector::Update's
    //     SetTimestepMultiplier publish, previously gated -- see BrnMainDirector.cpp).
    // ⛔ THIS FUNCTION IS THE SINGLE CHOKE POINT FOR EVERY SLOW-MOTION REQUEST IN THE GAME.
    // The X360 has exactly four callers of TimerRequests::SetTimestepMultiplier (checked
    // against the whole export set): MainDirector::Update, ModeManager::SetupGameMode,
    // ModeManager::FinishCurrentMode and DriveThruManager::SetPlayerCarDriver. All four post
    // into one of the two request interfaces this function drains, so while the Appends were
    // commented out NO producer anywhere in the game could dilate time -- the writes landed
    // and were dropped on the floor, with green logs and a plausible 1.0.
    //
    // The `(GetTimerR(...)[2] >> 2) & 1` test is `lwz r11, 8(r3); extrwi r11, r11, 1, 29`
    // @0x823BD02C-0x823BD030: the word at interface+8 is mSimTimer.muFlags and bit 2 is
    // KU_FLAG_MULTIPLIER -- i.e. the GAME-STATE module's sim slow-mo request WINS, and the
    // director's is folded in only when the game state did not ask for one this frame. (The
    // old comment glossed it as "the director owns the timers" bit, which reads the priority
    // backwards.)
    //
    // [FLAG PC bring-up] TWO stated deviations, neither of which changes what is applied:
    //  1. NO PARAMETERS. The console signature is
    //     UpdateTimers(GameStateModuleIO::OutputBuffer*, DirectorIO::OutputBuffer*) and its
    //     caller passes exactly the two objects reached below as members. Reaching them
    //     directly keeps the one call site (DoUpdate's sub-step loop) unchanged.
    //  2. THE DRAIN IS GATED ON THE DIRECTOR MODULE BEING PREPARED (and on both buffers
    //     existing). The reset half of the cycle, BridgeTimers, now runs at the start of EVERY
    //     sub-step (the console's 0x823F0DE4, see GameMain), so the accumulator starts each step
    //     cleared whether or not this drain runs -- nothing can latch. Nothing posts a request
    //     before the director is prepared (all four producers are in-game).
    //
    // ⭐⭐ ORDER -- CORRECTED 2026-09-25 (FX-DIRECTOR2): this now runs where the console runs it,
    // at the END of the step (DoUpdate @0x823F0AF8 calls it at 0x823F1CFC, after
    // DoUpdate_NetworkPostSim), so it drains the request MainDirector::Update published in THIS
    // step's DoUpdate_Director (0x82275148) and the next step's BridgeTimers snapshot carries it
    // to the world. It used to run mid-step, between the world leg and the director (boot audit
    // F-P3-13 had flagged the position and deferred the move): every director time-scale request
    // was drained one step late and integrated one step after that. Measured on the h225 s80
    // crash cell: the hard stop's 0.000125 reached the world on the crash's FOURTH frame instead
    // of its third, so the impact frame that takes the car from 197 to 102 mph ran at full dt.
    // The game-state requests were never affected (their legs run before this one either way).
    // ------------------------------------------------------------------------------------
    void BrnGameModule::UpdateTimers()
    {
        BrnGameState::GameStateModuleIO::OutputBuffer* const lpGameStateOutput =
            mGameStateModule.GetOutputBuffer();

        if (lpGameStateOutput != 0 && mpDirectorOutputBuffer != 0 && mDirectorModule.IsPrepared())
        {
            lpGameStateOutput->LockForRead();
            mpDirectorOutputBuffer->LockForRead();

            // Fold the game-state module's game/sim requests into this sub-step's accumulator.
            // ⚠️ THE CONST OVERLOAD, DELIBERATELY. GetTimerRequestInterface() comes in a pair:
            // the non-const one (X360 0x8231D608) asserts the WRITE lock, the const one
            // (X360 0x823B98E8) the READ lock -- and this function holds a READ lock, so the
            // console's call here is the const half. Measured: taking the non-const overload
            // fired "Not locked for writing" 7,800 times in one 135 s boot and stalled the flow
            // before the fly-by. A `const` that is load-bearing, not stylistic.
            const BrnGameState::GameStateModuleIO::OutputBuffer* const lpcGameStateOutput =
                lpGameStateOutput;
            const CgsSystem::TimerRequestInterface* const lpGameStateRequests =
                lpcGameStateOutput->GetTimerRequestInterface();

            mTimerRequestInterface.GetGameTimerRequests()->Append(
                *lpGameStateRequests->GetGameTimerRequests());
            mTimerRequestInterface.GetSimTimerRequests()->Append(
                *lpGameStateRequests->GetSimTimerRequests());

            // ...and the director's, but only when the game state has not already claimed the
            // sim multiplier this frame (asm @0x823BD02C: test mSimTimer.muFlags bit 2).
            if (!lpGameStateRequests->GetSimTimerRequests()->IsMultiplierRequested())
            {
                CgsSystem::TimerRequestInterface* const lpDirectorRequests =
                    mpDirectorOutputBuffer->GetTimerRequestIn();

                mTimerRequestInterface.GetGameTimerRequests()->Append(
                    *lpDirectorRequests->GetGameTimerRequests());
                mTimerRequestInterface.GetSimTimerRequests()->Append(
                    *lpDirectorRequests->GetSimTimerRequests());
            }

            mpDirectorOutputBuffer->UnlockForRead();
            lpGameStateOutput->UnlockForRead();

            // Drain the accumulator onto the two timers (start/stop/scale target).
            mTimerRequestInterface.ApplyToTimers(&mGameTimer, &mSimTimer);
        }

        mGameTimer.Update();
        mSimTimer.Update();

        // ---- [DIAG] the time-dilation film latch (see BrnDiagFilmLatch.h) ------------------
        // Unconditional three-word write, no environment read on the hot path; the READER
        // (pc/gcm/renderengine/device.cpp) is the side that is gated, and it does nothing unless
        // BRN_FRAME_DUMP_ARM=slomo. Sticky by design.
        // ⚠️ IT COUNTS EPISODES, AND THAT IS NOT A LUXURY. Measured 2026-08-28: the FIRST
        // dilation of a free-burn session is the JUNKYARD-EXIT drive-thru, which fires while
        // the car is parked -- so an unconditional latch spends the whole 300-frame budget on a
        // stationary car and films nothing. BRN_SLOMO_LATCH_SKIP=<n> skips the first n episodes
        // (an episode is one 1.0 -> non-1.0 transition), so a capture can land on the drive-thru
        // that actually moves the car.
        {
            const f32  lfSimScale = mSimTimer.GetScaleCurrent();
            const bool lbDilated  = (lfSimScale != 1.0f);

            // The LIVE pair the frame writer stamps beside every dumped frame, so a captured
            // strip carries the timestep each of its frames was rendered under.
            BrnDiag::gFilmLatch.mfLiveSimScale = lfSimScale;
            BrnDiag::gFilmLatch.mfLiveSimStep  = mSimTimer.GetRate() * lfSimScale;

            static bool sbWasDilated  = false;
            static u32  suEpisode     = 0u;
            static s32  siSkip        = -1;
            if (siSkip < 0)
            {
                const char* const lpcSkip = getenv("BRN_SLOMO_LATCH_SKIP");
                siSkip = (lpcSkip != 0) ? atoi(lpcSkip) : 0;
                if (siSkip < 0) { siSkip = 0; }
            }

            if (lbDilated && !sbWasDilated)
            {
                ++suEpisode;
                if (BrnDiag::gFilmLatch.muSlomoLatched == 0u &&
                    suEpisode > static_cast<u32>(siSkip))
                {
                    BrnDiag::gFilmLatch.mfLatchedSimScale = lfSimScale;
                    BrnDiag::gFilmLatch.mfLatchedSimStep  = mSimTimer.GetRate() * lfSimScale;
                    BrnDiag::gFilmLatch.muSlomoLatched    = 1u;
                    if (CgsDev::Log::gpDebugPrint != 0)
                    {
                        *CgsDev::Log::gpDebugPrint
                            << "[slomo] FILM LATCH raised on dilation episode " << suEpisode
                            << " (scale " << lfSimScale << ")\n";
                    }
                }
            }
            sbWasDilated = lbDilated;
        }

        // ---- BRN_SLOMO_DIAG (opt-in, edge-triggered) ---------------------------------------
        // ⚠️ NOT A CONSOLE ARM. The measurement hook for the time-dilation transport: it prints
        // the SIM timer's live scale only when it MOVES, so a run either shows the dilation
        // arriving or it does not. Edge-triggered on purpose -- a per-frame print would be
        // 60 lines/second of noise and would itself perturb a frame-coupled sim.
        if (getenv("BRN_SLOMO_DIAG") != 0 && CgsDev::Log::gpDebugPrint != 0)
        {
            static f32 sfLastSimScale  = -1.0f;
            static f32 sfLastGameScale = -1.0f;

            const f32 lfSimScale  = mSimTimer.GetScaleCurrent();
            const f32 lfGameScale = mGameTimer.GetScaleCurrent();

            if (lfSimScale != sfLastSimScale || lfGameScale != sfLastGameScale)
            {
                sfLastSimScale  = lfSimScale;
                sfLastGameScale = lfGameScale;
                *CgsDev::Log::gpDebugPrint
                    << "[slomo] simScale=" << lfSimScale
                    << " gameScale=" << lfGameScale
                    << " simStep=" << (mSimTimer.GetRate() * lfSimScale)
                    << " gameStep=" << (mGameTimer.GetRate() * lfGameScale)
                    << "\n";
            }
        }
    }

    // ------------------------------------------------------------------------------------
    // BridgeTimers  @ 0x823BD150   -- ⭐ THE FRAME TIMESTEP PUBLISH
    //
    //     *(gm+10095424) = 1.0f;  *(gm+10095420) = 0;      // the game TimerRequests reset
    //     *(gm+10095432) = 1.0f;  *(gm+10095428) = 0;      // the sim  TimerRequests reset
    //     TimerStatusInterface::StoreTimers(gm+10095372, gm+10095316, gm+10095344);
    //     LockForWrite(directorInput);
    //       <48-byte copy of gm+10095372 into DirectorIO::InputBuffer::GetTimerStatusInterface()>
    //     UnlockForWrite(directorInput);
    //
    // ⭐ THE TWO RESETS ARE LIVE (2026-08-28, crash-slomo transport wave). They are the RESET
    // half of the accumulate-and-reset cycle whose accumulate half UpdateTimers above now runs;
    // the old note gated them on "with no producers there is nothing to clear", which stopped
    // being true the moment the drive-thru and the director started posting. Without them the
    // accumulator's KU_FLAG_MULTIPLIER latches on the first request and the last multiplier
    // sticks for the rest of the session.
    // The four console stores ARE TimerRequests::Clear inlined twice (asm @0x823BD198..0x823BD1A4;
    // see the body now in CgsTimerRequestInterface.h) -- mfMultiplier = 1.0f, muFlags = 0, per
    // half. ⚠️ 1.0f, not 0.0f: a zero here would drive the sim timer's scale target to zero and
    // stop the world.
    // The StoreTimers snapshot and the copy into the director input are the other live half:
    // without them the director input's timer status stays at DoUpdate_Director's zero-fill,
    // every TimerStatus::GetCurrentTimeStep() reads 0, and the whole camera-behaviour middle
    // advances by `speed * 0` per frame.
    //
    // ⭐ POSITION (2026-09-25, FX-DIRECTOR2): the console calls this FIRST in DoUpdate @0x823F0AF8
    // (0x823F0DE4, before DoUpdate_InputPreWorld), so the snapshot every leg of the step reads --
    // the world's included (DoUpdate_World hands gm+0x9A0B0C to the world input at 0x823E8C78..
    // 0x823E8C84) -- is the timers as the PREVIOUS step's UpdateTimers left them. GameMain now calls
    // it there, with a NULL director input.
    // [FLAG PC split] the director input buffer does not exist yet at the start of a sub-step on
    // this build (DoUpdate_Director creates it), so the copy half runs only when a buffer is
    // passed; DoUpdate_Director copies the same snapshot in itself.
    // ------------------------------------------------------------------------------------
    void BrnGameModule::BridgeTimers(BrnDirector::DirectorIO::InputBuffer* lpDirectorInput)
    {
        mTimerRequestInterface.Clear();

        mTimerStatusInterface.StoreTimers(&mGameTimer, &mSimTimer);

        if (lpDirectorInput != 0)
        {
            lpDirectorInput->LockForWrite();
            *lpDirectorInput->GetTimerStatusInterface() = mTimerStatusInterface;
            lpDirectorInput->UnlockForWrite();
        }
    }

    // ------------------------------------------------------------------------------------
    // BrnGameModule::BridgeGameStateToDirector  @ X360 0x823CD170
    // (console home GameSource/Game/GameBridgeGameStateToX.cpp; body kept here with the other
    //  DoUpdate_Director bridges -- the BridgeGuiToDirector precedent.)
    //
    // ⭐ THE GAME-ACTION LEG (the whole reason this bridge exists, and the only leg whose two
    // ends are real today):
    //     lpDirectorInput->GetGameActionQueue()->Append( *lpGameStateOutput->GetGameActionQueue() )
    // The X360 renders it as
    //     v29 = sub_823B96F0(a3);                                  // gameStateOut->GetGameActionQueue() const
    //     v30 = BrnDirector::DirectorIO::InputBuffe(a2);           // directorIn->GetGameActionQueue()
    //     CgsModule::VariableEventQueue<13312,16>::Append<13312,16>(v30, v29);
    // -- the console itself proving both queues are the SAME instantiated type.
    //
    // ⚠️ THE BRIEF'S "TWO-LINER" IS WRONG, and it matters: 0x823CD170 is a ~150-line function
    // whose OTHER legs are, in console order --
    //   * a BrnReplays::DirectorBridgeSerialiser state machine wrapped round the whole body
    //     (Lock / GetStaticLayout / Unlock; on replay PLAYBACK the game actions are Appended
    //     from the SERIALISED layout at +10128 instead of from the live buffer, and on RECORD
    //     they are Appended into it as well);
    //   * a walk of the game-state output buffer's takedown-event queue (this+0x4040) matching
    //     each record's race-car index against the player's, publishing mbPlayerTakenDown /
    //     mePlayerKillerCarIndex into the director input (+31424 / +31404) with the verbatim
    //     assert "lePlayerKillerRaceCarIndex != E_ACTIVE_RACE_CAR_INDEX_INVALID"
    //     (GameBridgeGameStateToX.cpp:228) -- ⭐ RECONSTRUCTED 2026-09-24 (crash parity FX-BRIDGES
    //     CC-8), see the body: both of its reasons had expired (the queue is walked by name for
    //     the world and GUI bridges, and MainDirector::ProcessInputQueue / ArbStateCrashing are its
    //     consumers);
    //   * the player's vehicle TEAM into the director input (+31408) and all 8 teams through
    //     DirectorIO::InputBuffer::SetVehicleTeam -- ⭐ RECONSTRUCTED 2026-09-25 (crash parity
    //     FX-DIRECTOR2), see the body: the input's +0x7AB0 word is miPlayerTeam now and the
    //     +0x3238 team words feed AllVehicleData::Update;
    //   * a CarScoreData::operator= of the player's score record (gameStateOut+173240 + 296*i)
    //     into the director input at +12560, plus +12888;
    //   * the player's end-of-event pair at +31445 / +31446 (@0x7AD5 / @0x7AD6) -- ⭐
    //     RECONSTRUCTED 2026-09-24 (crash parity FX-DIRECTOR), see the body.
    // The score leg is still not reconstructed: its director-input destination is opaque storage
    // in this model and it is not on the crash path. Writing it against opaque zeroes would be the
    // "data arrives wrong-but-plausible" failure mode, so it is documented, not faked.
    // DELETE-WHEN: the score span of the input buffer is typed.
    // ------------------------------------------------------------------------------------
    void BrnGameModule::BridgeGameStateToDirector(
        BrnDirector::DirectorIO::InputBuffer* lpDirectorInput,
        const BrnGameState::GameStateModuleIO::OutputBuffer* lpGameStateOutput)
    {
        // ---- the player-taken-down leg (X360 live arm 0x823CD330..0x823CD3C8) ----------------
        //   0x823CD330  r25 = `lwzx gameStateOut + 0x2AEEC` == ScoringOutputInterface
        //               (+173240) ::mePlayerRaceCarIndex (+0xA34)
        //   0x823CD340  r27 = GetTakedownEventOutputQueue() const (sub_823B9840)->miLength, read ONCE
        //   0x823CD36C  per event: the queue is re-fetched and GetEvent(i) (0x822AC660) taken;
        //               `lwz 4` (meVictimIndex) == r25 -> killer = `lwz 0` (meAggressorIndex),
        //               the :228 assert, then `stb 1, 0x7AC0` + `stw killer, 0x7AAC` (the inlined
        //               SetPlayerKiller). A later match overwrites an earlier one.
        // The cast is the documented cross-home one the world and GUI bridges carry:
        // GameStateModuleIO::TakedownEventOutputQueueType is still a forward-declared class and the
        // payload behind it is the committed EventQueue<BrnGameState::TakedownEvent,8>.
        // The director input is a fresh, Construct()ed buffer every sub-step on this build too
        // (DoUpdate_Director), so the pair starts cleared exactly as the console's does.
        {
            const EActiveRaceCarIndex lePlayerRaceCarIndex =
                lpGameStateOutput->GetScoringOutputInterface()->mePlayerRaceCarIndex;
            const s32 liNumTakedowns = reinterpret_cast<const CgsModule::BaseEventQueue<BrnGameState::TakedownEvent>*>(
                lpGameStateOutput->GetTakedownEventOutputQueue())->GetLength();
            for (s32 liTakedown = 0; liTakedown < liNumTakedowns; ++liTakedown)
            {
                const BrnGameState::TakedownEvent& lrTakedownEvent =
                    reinterpret_cast<const CgsModule::BaseEventQueue<BrnGameState::TakedownEvent>*>(
                        lpGameStateOutput->GetTakedownEventOutputQueue())->GetEvent(liTakedown);
                if (lrTakedownEvent.meVictimIndex == lePlayerRaceCarIndex)
                {
                    const EActiveRaceCarIndex lePlayerKillerRaceCarIndex = lrTakedownEvent.meAggressorIndex;
                    CGS_ASSERT(lePlayerKillerRaceCarIndex != E_ACTIVE_RACE_CAR_INDEX_INVALID,
                               "lePlayerKillerRaceCarIndex != E_ACTIVE_RACE_CAR_INDEX_INVALID");   // GameBridgeGameStateToX.cpp:228
                    lpDirectorInput->SetPlayerKiller(lrTakedownEvent.meAggressorIndex);

                    // [DIAG] NOT IN THE X360 BINARY -- BRN_CRASHCAM_DIAG (the crash-camera gate):
                    // the takedown camera's input as published (at most 30 lines).
                    static const bool sbTakenDownDiag = (getenv("BRN_CRASHCAM_DIAG") != 0);
                    static s32 siTakenDownLinesLeft = 30;
                    if (sbTakenDownDiag && siTakenDownLinesLeft > 0 && CgsDev::Log::gpDebugPrint != 0)
                    {
                        --siTakenDownLinesLeft;
                        *CgsDev::Log::gpDebugPrint
                            << "[takedown-cam] BridgeGameStateToDirector: player slot "
                            << static_cast<s32>(lePlayerRaceCarIndex) << " taken down by slot "
                            << static_cast<s32>(lePlayerKillerRaceCarIndex)
                            << " (takedown type " << static_cast<s32>(lrTakedownEvent.meType)
                            << ") -> director input mbPlayerTakenDown 1\n";
                    }
                }
            }
        }

        lpDirectorInput->GetGameActionQueue()->Append(*lpGameStateOutput->GetGameActionQueue());

        // ---- the player's TEAM word (X360 live arm 0x823CD428..0x823CD454) -------------------
        // ⭐ 2026-09-25 (crash parity FX-DIRECTOR2). With the player slot r25 of the takedown leg
        // (the scoring snapshot's mePlayerRaceCarIndex):
        //   0x823CD440  `addis r11, r25, 1 ; addi r11, r11, -0x540E ; slwi 2` == 4 * r25 + 0x2AFC8
        //   0x823CD450  `lwzx r11, r11, r31` -- gameStateOut + 0x2AFC8 + 4 * player ==
        //               OnlineScoringOutputInterface (+0x2AF68) ::maePlayerTeam (+0x60) [player]
        //   0x823CD454  `stw r11, 0x7AB0(r23)` -- the director input's player team, which
        //               ProcessInputQueue copies into GameState::miPlayerTeam (+0x1CC).
        // No bounds test: a -1 slot reads the word before the array, maiOnlineAwardVariables[7]
        // (gameStateOut + 0x2AFC4); that read is reproduced by name rather than by a negative index.
        // (The score record copy into +0x3110 and the +0x3258 byte that follow it, 0x823CD458..
        //  0x823CD46C, stay open: the input's score span is still opaque.)
        {
            const BrnGameState::GameStateModuleIO::OnlineScoringOutputInterface* const lpOnlineScoring =
                lpGameStateOutput->GetOnlineScoringOutputInterface();
            const s32 liPlayerSlot =
                static_cast<s32>(lpGameStateOutput->GetScoringOutputInterface()->mePlayerRaceCarIndex);
            const s32 liPlayerTeam = (liPlayerSlot == -1)
                ? lpOnlineScoring->maiOnlineAwardVariables[7]
                : static_cast<s32>(lpOnlineScoring->maePlayerTeam[liPlayerSlot]);
            lpDirectorInput->SetPlayerTeam(liPlayerTeam);                                        // @0x7AB0
        }

        // ---- the player's end-of-event pair (X360 live arm 0x823CD4A0..0x823CD510) -----------
        // ⭐ 2026-09-24 (crash parity FX-DIRECTOR). The console reads both out of the scoring
        // snapshot (gameStateOut + 0x2A4B8, the inlined GetScoringOutputInterface()) with the
        // player slot it loaded for the takedown leg (r25, `lwzx +0x2AEEC` @0x823CD33C ==
        // mePlayerRaceCarIndex), and stores them without a lock-bit test:
        //   0x823CD4A0  `add. r11, r31, 0x2A4B8` -- the accessor's non-gating assert
        //               "lpGameStateOutput->GetScoringOutputInterface()" (GameBridgeGameStateToX.cpp:256)
        //   0x823CD4D8  `lbzx +0x2AEB8 + player` == mabPlayerEliminated[player] (+0xA00), with no
        //               bounds test -> `stb 0x7AD5`
        //   0x823CD4E4  `lfsx +0x2AF4C` == mfModeTimeRemaining (+0xA94) `fcmpu` flt_82001CC0 (0.0f):
        //               `bgt` -> 0; else `lbzx +0x2AF60` == mbTimerActive (+0xAA8) != 0 -> r19 (1,
        //               `li r19, 1` @0x823CD1A8) else 0 -> `stb 0x7AD6`. An unordered compare (NaN)
        //               is not `gt`, so NaN takes the mbTimerActive arm; `!(x > 0.0f)` keeps that.
        // (The console's team word @0x7AB0 -- landed above -- the score record and the +0x3258 byte
        //  sit between the Append and this arm, 0x823CD428..0x823CD49C; the last two are still open.)
        // MainDirector::ProcessInputQueue copies the pair into GameState +0x1D0 / +0x1D1. Its one
        // reader, ArbStateRoaming::ProcessPossibleFX, plays "Damage_Crit" / "Wrecked" on it in the
        // online modes 12 / 14 / 17 only; offline, @0x7AD6 rises when a Road Rage or Stunt Run
        // clock runs out.
        {
            const BrnGameState::GameStateModuleIO::ScoringOutputInterface* const lpScoringOutputInterface =
                lpGameStateOutput->GetScoringOutputInterface();
            CGS_ASSERT(lpScoringOutputInterface != 0,
                       "lpGameStateOutput->GetScoringOutputInterface()");       // GameBridgeGameStateToX.cpp:256
            const EActiveRaceCarIndex lePlayerRaceCarIndex = lpScoringOutputInterface->mePlayerRaceCarIndex;
            lpDirectorInput->SetPlayerEliminated(
                lpScoringOutputInterface->mabPlayerEliminated[lePlayerRaceCarIndex]);            // @0x7AD5
            lpDirectorInput->SetModeTimeExpired(
                !(lpScoringOutputInterface->mfModeTimeRemaining > 0.0f) &&                       // flt_82001CC0
                lpScoringOutputInterface->mbTimerActive);                                         // @0x7AD6
        }

        // ---- the per-car TEAMS (X360 live arm 0x823CD514..0x823CD56C, the bridge's last leg) ----
        // ⭐ 2026-09-25 (crash parity FX-DIRECTOR2). r31 = gameStateOut + 0x2AFC8 (`addis 3 ; addi
        // -0x5038` @0x823CD518 / 0x823CD528) == OnlineScoringOutputInterface::maePlayerTeam, then for
        // each active race-car slot i = 0..7 (the EActiveRaceCarIndex iteration, its
        // "leEnumIndex <= E_ACTIVE_RACE_CAR_INDEX_COUNT" tripwire BurnoutConstants.h:39 at 0x823CD550):
        //   `lwz r5, 0(r31)` then DirectorIO::InputBuffer::SetVehicleTeam @0x823B2938 (input, i, team)
        //   -- `stw team, 0x3238 + 4 * i`, behind its own two index asserts and the write-lock test.
        // Their one reader is AllVehicleData::Update's fifth argument (lpaVehicleTeams): the team on
        // each nearest-car row, which SqDistanceOfNearestOpposingTeamMember compares.
        {
            const BrnGameState::GameStateModuleIO::OnlineScoringOutputInterface* const lpOnlineScoring =
                lpGameStateOutput->GetOnlineScoringOutputInterface();
            for (s32 liCar = 0; liCar < E_ACTIVE_RACE_CAR_INDEX_COUNT; ++liCar)
            {
                lpDirectorInput->SetVehicleTeam(static_cast<EActiveRaceCarIndex>(liCar),
                                                static_cast<s32>(lpOnlineScoring->maePlayerTeam[liCar]));
            }
        }
    }

    // ------------------------------------------------------------------------------------
    // ⭐⭐ BridgeGameStateToWorld  @ 0x823E1890
    //
    // Twelve transfers, no branches -- the entire console body is `mr r3,r30 / bl <getter> /
    // mr r4,r3 / mr r3,r31 / bl <setter>` twelve times over. Called by DoUpdate_World
    // @0x823E8BD0 with this sub-step's world UPDATE INPUT buffer (r4) and the game-state
    // module's OUTPUT buffer (r5). The caller owns both locks (world input write-locked,
    // game-state output read-locked); every accessor below asserts one or the other, which is
    // how the console proves that bracket.
    //
    // WHY THE FIRST LINE IS THE POINT OF THE WHOLE FUNCTION. It is the ONLY producer of the
    // world update input buffer's game-action queue in the entire image.
    // WorldModule::HandleGameActions (0x827C44D8), WorldModule::BridgeInputToEntityModules
    // (0x827ADF88) and WorldModule::BridgeActionsTo{Physics,Traffic}Module all DRAIN
    // UpdateInputBuffer::GetGameActionQueue(); nothing else ever fills it. Until now every one
    // of them was draining a queue that could not be non-empty, so no game action reached the
    // world at all -- including ResetPlayerCarAction (type 0), the record CarSelectManager
    // builds to place the player's car at a junkyard spawn location.
    //
    // FIVE of the twelve getters are UNNAMED in the ARTIST exports (sub_823B96F0 /
    // sub_823B9840 / the truncated "BrnGameState::GameStateM" @0x823B9AE0 / sub_823B9B88 /
    // sub_823BA038) and TWO are INLINED (the bridge computes `+173240` and `+175976` itself,
    // asm 0x823E1938 and 0x823E1948). All seven are identified at their accessors in
    // BrnGameStateModuleIO.h by the member offset each returns plus its assert's own
    // __FILE__/__LINE__ -- the same recovery route GetGameActionQueue() const already used.
    //
    // FLAG (home): the declared home is GameSource/Game/GameBridgeGameStateToX.cpp, alongside
    // its five siblings. The body sits HERE for the same reason BridgeGameStateToDirector's
    // does. Re-home both bridges there when this file's bridge family is consolidated.
    //
    // ⚠️ ONE DELIBERATE DEVIATION FROM A LITERAL TRANSCRIPTION, and it is load-bearing. The
    // console passes the scoring snapshots as raw addresses because there the source span and
    // the destination slice are both 2736 bytes. MEASURED on this x64 build:
    // sizeof(GameStateModuleIO::ScoringOutputInterface) == 2672, while
    // BrnWorldIO::SetScoringInterface still memcpy's the console's 2736. So the source goes
    // through GetScoringOutputInterface(), whose storage is deliberately kept at the CONSOLE's
    // width -- see the ⚠️ at that accessor. Without that the bridge would over-read the source
    // by 64 bytes every frame.
    // ------------------------------------------------------------------------------------
    void BrnGameModule::BridgeGameStateToWorld(
        BrnWorldIO::UpdateInputBuffer* lpWorldInput,
        const BrnGameState::GameStateModuleIO::OutputBuffer* lpGameStateOutput)
    {
        CGS_ASSERT(lpWorldInput != 0, "lpWorldInput");
        CGS_ASSERT(lpGameStateOutput != 0, "lpGameStateOutput");

        // 1. the GAME-ACTION queue (sub_823B96F0 -> AppendGameActionQueue 0x823C8B80). Both
        //    sides are the same CgsModule::VariableEventQueue<13312,16> instantiation.
        lpWorldInput->AppendGameActionQueue(lpGameStateOutput->GetGameActionQueue());

        // 2. the takedown-event queue (sub_823B9840 -> AppendTakedownEventQueue 0x823C8C38).
        //    FLAG cross-home cast: GameStateModuleIO::TakedownEventOutputQueueType is still a
        //    forward-declared incomplete class; BrnWorldIO names the same X360 payload as the
        //    committed EventQueue<BrnGameState::TakedownEvent,8>.
        lpWorldInput->AppendTakedownEventQueue(
            reinterpret_cast<const BrnWorldIO::TakedownEventQueue*>(
                lpGameStateOutput->GetTakedownEventOutputQueue()));

        // 3/4. the active-payback pair (0x823B9E28 / 0x823B9ED8 -> 0x823B4F50 / 0x823B5000)
        lpWorldInput->SetActivePaybackType(lpGameStateOutput->GetActivePaybackType());
        lpWorldInput->SetActivePaybackAggressor(lpGameStateOutput->GetActivePaybackAggressor());

        // 5. the trigger-management interface (0x823B9AE0 -> 0x823DB778). Both sides are the
        //    committed BrnWorld::TriggerEntityModuleIO::TriggerManagementInputInterface now.
        lpWorldInput->AppendTriggerManagementInputInterface(
            lpGameStateOutput->GetTriggerManagementInputInterface());

        // 6. the trigger-query interface (sub_823B9B88 -> 0x823C8CF0). Both sides are the same
        //    VariableEventQueue<4096,16> instantiation.
        lpWorldInput->AppendTriggerQueryInputInterface(
            lpGameStateOutput->GetTriggerQueryInputInterface());

        // 7. the race-car race-distance interface (sub_823BA038 -> 0x823B4A58).
        //    FLAG cross-home cast: BrnWorldIO models this payload as its own 10-word slice.
        lpWorldInput->SetRaceCarRaceDistanceInterface(
            reinterpret_cast<const BrnWorldIO::RaceCarRaceDistanceInterface*>(
                lpGameStateOutput->GetRaceCarRaceDistanceInterface()));

        // 8/9. the two scoring snapshots (INLINED on X360 -> 0x823B4B28 / 0x823B4BE0).
        //      FLAG cross-home casts; see the ⚠️ in the banner for the 2736-vs-2672 span.
        lpWorldInput->SetScoringInterface(
            reinterpret_cast<const BrnWorldIO::ScoringInterface*>(
                lpGameStateOutput->GetScoringOutputInterface()));
        lpWorldInput->SetOnlineScoringInterface(
            reinterpret_cast<const BrnWorldIO::OnlineScoringInterface*>(
                lpGameStateOutput->GetOnlineScoringOutputInterface()));

        // 10. the controller-active flag (0x823B9F88 -> 0x823B4C98)
        lpWorldInput->SetControllerActive(lpGameStateOutput->GetControllerActive());
    }

    // =========================================================================================
    // BridgeEntityToEffects  @0x823CDF00 -- the WORLD -> EFFECTS bridge.
    //
    // Register decode (the pseudocode's argument numbering is scrambled; the asm is not):
    //   r3 this, r4 the world UpdateOutputBuffer, r5 the effects InputBuffer, r6 the update set.
    // Six installs, in the console's order, plus the eight-slot boost copy:
    //   SetContactSpyInterface(world->GetContactSpyInterface())
    //   SetDeformationInterface(world->GetDeformationOutputInterface())
    //   SetPropVFXLocatorQueue(world->GetPropVFXLocatorQueue())
    //   SetActiveRaceCarInterface( (updateSet & 0x100) ? GetReplayActiveRaceCarOutputInterface()
    //                                                  : GetActiveRaceCarOutputInterface() )
    //   -- then for i in 0..7: nine words from (interface + 0x210) + i*0x24 into
    //      (effectsIn + 4) + i*0x24. That is SetBoostInfoN(i, GetBoostOutputInfoN(i)) inlined:
    //      the two asserts the loop carries are GetBoostOutputInfoN's own bound checks
    //      (BrnRaceCarEntityModuleOutputInterface.h:1157/:1158), and 0x210 == 528 is exactly
    //      RCEntityActiveRaceCarOutputInterface::maBoostOutputInfo.
    //   SetVehiclePhysicalStateQueue(world->GetVehicleOutputInterface() + 0x2620)
    //   SetEffectsEnvironmentInterface(world->GetEffectsEnvironmentInterface())
    //   SetTriangleCacheInterface(world->GetTriangleCacheInterface())
    // =========================================================================================
    void BrnGameModule::BridgeEntityToEffects(const BrnWorldIO::UpdateOutputBuffer* lpWorldOutputBuffer,
                                              BrnEffects::EffectsIO::InputBuffer* lpEffectsInputBuffer,
                                              BrnUpdateSet leUpdateSet)
    {
        typedef BrnWorld::RaceCarEntityModuleIO::RCEntityActiveRaceCarOutputInterface ActiveRaceCars;

        lpEffectsInputBuffer->SetContactSpyInterface(lpWorldOutputBuffer->GetContactSpyInterface());
        lpEffectsInputBuffer->SetDeformationInterface(lpWorldOutputBuffer->GetDeformationOutputInterface());
        lpEffectsInputBuffer->SetPropVFXLocatorQueue(lpWorldOutputBuffer->GetPropVFXLocatorQueue());

        // `rlwinm r11, r31, 0,23,23` == the update set's bit 8 (0x100): the replay source select.
        const ActiveRaceCars* lpActiveRaceCars =
            ((static_cast<u32>(leUpdateSet) & 0x100u) != 0)
                ? lpWorldOutputBuffer->GetReplayActiveRaceCarOutputInterface()
                : lpWorldOutputBuffer->GetActiveRaceCarOutputInterface();
        lpEffectsInputBuffer->SetActiveRaceCarInterface(lpActiveRaceCars);

        for (s32 liCar = 0;
             liCar < static_cast<s32>(BrnEffects::EffectsIO::InputBuffer::KU_NUM_BOOST_INFOS);
             ++liCar)
        {
            const EActiveRaceCarIndex leIndex = static_cast<EActiveRaceCarIndex>(liCar);
            lpEffectsInputBuffer->SetBoostInfoN(liCar, lpActiveRaceCars->GetBoostOutputInfoN(leIndex));
        }

        // `addi r4, r11, 0x2620` -- the vehicle output interface's own physical-traffic queue.
        lpEffectsInputBuffer->SetVehiclePhysicalStateQueue(
            lpWorldOutputBuffer->GetVehicleOutputInterface()->GetTrafficStateQueue());   // +0x2620
        lpEffectsInputBuffer->SetEffectsEnvironmentInterface(
            lpWorldOutputBuffer->GetEffectsEnvironmentInterface());
        lpEffectsInputBuffer->SetTriangleCacheInterface(
            reinterpret_cast<const BrnEffects::EffectsIO::InputBuffer::InTriangleCacheInterface*>(
                lpWorldOutputBuffer->GetTriangleCacheInterface()));
    }

    // =========================================================================================
    // DoUpdate_Effects  @0x823DD0A8 -- the EFFECTS leg of the per-frame cascade.
    //
    // The console order (asm 0x823DD0A8-0x823DD29C), statement for statement. The lock helper
    // sub_823B78A0 is LockBuffersForIO(effectsIn, out0..out5) -- W(effectsIn) then R(out0..out5)
    // in argument order, with sub_823B7A10 the exact reverse; both are reproduced inline, the
    // same idiom DoUpdate_Sound already uses in this file.
    //
    // FLAG PC null-tolerance: the console helper asserts every buffer non-null. On this build
    // the replay pre-sim output and the sound pre-update output are not driven per frame, and
    // the game-state / world / director statics can be null on defensive frames -- each leg
    // skips its absent source rather than faking one. Retire the guards as the modules come live.
    // =========================================================================================
    void BrnGameModule::DoUpdate_Effects(CgsModule::IOBufferStack* lpInputBufferStack,
                                         CgsModule::IOBufferStack* lpOutputBufferStack,
                                         const CgsInput::InputIO::OutputBuffer* lpInputOutputBuffer,
                                         BrnGameState::GameStateModuleIO::OutputBuffer* lpGameStateOutputBuffer,
                                         BrnWorldIO::UpdateOutputBuffer* lpWorldOutputBuffer,
                                         BrnDirector::DirectorIO::OutputBuffer* lpDirectorOutputBuffer,
                                         BrnReplays::ReplayIO::OutputBuffer_PreSim* lpReplaysPreSimOutputBuffer,
                                         BrnSound::Module::Io::RootPreUpdateOutputBuffer* lpSoundPreUpdateOutputBuffer,
                                         BrnEffects::EffectsIO::OutputBuffer* lpEffectsOutputBuffer,
                                         bool lbSuspendEffects,
                                         BrnUpdateSet leUpdateSet)
    {
        typedef BrnEffects::EffectsIO::InputBuffer EffectsIn;

        CgsDev::PerfMonCpu::StartMonitor(mCpuMonitors.miUT_Effects);

        // The self-carved "Effects" input (console @0x823DD0F8, the CgsModuleIOHelper
        // create/destroy pair with the h:52/h:57 asserts).
        EffectsIn* lpEffectsInputBuffer = 0;
        const bool lbCreated = lpInputBufferStack->CreateIOBuffer(&lpEffectsInputBuffer, "Effects");
        CGS_ASSERT(lbCreated, "mpStack->CreateIOBuffer( &mpBuffer, lpcName )");  // CgsModuleIOHelper.h:52
        (void)lbCreated;
        if (lpEffectsInputBuffer == 0)
        {
            CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_Effects);
            return;
        }

        // sub_823B78A0(effectsIn, director, input, world, gameState, replays, soundPreUpdate)
        lpEffectsInputBuffer->LockForWrite();
        if (lpDirectorOutputBuffer != 0)       lpDirectorOutputBuffer->LockForRead();
        if (lpInputOutputBuffer != 0)          const_cast<CgsInput::InputIO::OutputBuffer*>(lpInputOutputBuffer)->LockForRead();
        if (lpWorldOutputBuffer != 0)          lpWorldOutputBuffer->LockForRead();
        if (lpGameStateOutputBuffer != 0)      lpGameStateOutputBuffer->LockForRead();
        if (lpReplaysPreSimOutputBuffer != 0)  lpReplaysPreSimOutputBuffer->LockForRead();
        if (lpSoundPreUpdateOutputBuffer != 0) lpSoundPreUpdateOutputBuffer->LockForRead();

        // @0x823DD154/60 -- the game module own timer status (gm + 0x9A0B0C).
        lpEffectsInputBuffer->SetTimerStatusInterface(&mTimerStatusInterface);

        // @0x823DD164/74 -- the director finalised camera.
        if (lpDirectorOutputBuffer != 0)
            lpEffectsInputBuffer->SetCameraInput(lpDirectorOutputBuffer->GetCameraOutput());

        // @0x823DD178/A0 -- pad 0 button word bit 1 raises the QA "restart effects" latch:
        //   `lwz r11, 0x34(padInfo); extrwi r11, r11, 1,30` == (buttons >> 1) & 1.
        if (lpInputOutputBuffer != 0)
        {
            // `lwz r11, 0x34(padInfo)` == maActionInfo[3].muStatus (+0x18 + 3*8 + 4), and
            // `extrwi r11,r11,1,30` is its bit 1 == pressed-this-frame.
            const CgsInput::InputIO::PadOutputInformation* lpPad = lpInputOutputBuffer->GetPadInfo(0);
            if (lpPad != 0 && ((lpPad->maActionInfo[3].muStatus >> 1) & 1u) != 0)
                BrnEffects::EffectsModule::RestartEffects();
        }

        // ---- THE SOUND -> EFFECTS AUDIO MESSAGE QUEUE ------------------------------------
        // ⚠ FLAG PC bring-up, and it is a CONSTRUCT, not a value. EffectsIO::InputBuffer::
        // Construct @0x82293618 deliberately does NOT construct mAudioEffectsMessageQueue --
        // its own banner says so -- because on the console the sound bridge always writes it
        // (SetAudioEffectsMessageQueue @0x823BA9E0, a 144-byte copy of BrnSound's own
        // constructed queue) before EffectsModule::Update reads it. This build has no sound
        // pre-update output buffer to bridge from (the leg goes in null, three arguments up),
        // so the member stayed as CreateIOBuffer left it and
        // VariableEventQueue<128,16>::GetNextEvent asserted "Not Constructed" from
        // EffectsModule::UpdateActiveRaceCars -- 3,860 firings in one run, which stalled the
        // boot at BOOT phase (measured, run 13).
        //
        // A CONSTRUCTED EMPTY queue is exactly what a silent sound module produces: the
        // exhaust-pop walk reads "no events" and every lafExhaustPopIntensity stays at its
        // frame default. That is a real value, not a placeholder zero -- the console's own
        // behaviour on a frame where no car popped.
        // DELETE-WHEN the sound pre-update output buffer is bridged in here: then the real
        // queue arrives by copy and this construct goes with the null argument.
        if (lpSoundPreUpdateOutputBuffer == 0)
        {
            BrnSound::Module::Io::AudioEffectsMessageQueue lEmptyAudioEffects;
            lEmptyAudioEffects.Construct();
            lpEffectsInputBuffer->SetAudioEffectsMessageQueue(&lEmptyAudioEffects);
        }

        // @0x823DD1A4/B8 -- the world -> effects bridge (it takes the update set, not the
        // buffer own copy).
        if (lpWorldOutputBuffer != 0)
            BridgeEntityToEffects(lpWorldOutputBuffer, lpEffectsInputBuffer, leUpdateSet);

        // @0x823DD1BC/D4 -- the game-state action queue, appended (NOT replaced).
        if (lpGameStateOutputBuffer != 0)
        {
            // ⚠ THE CONST OVERLOAD, DELIBERATELY. MEASURED (runs 4-6, 2026-09-02): the
            // non-const GetGameActionQueue @0x8231D4B8 asserts "Not locked for writing" and
            // this buffer is read-locked three lines up -- 15,333 firings in one boot, which
            // by themselves slowed the boot roughly four-fold (13.6s -> 53s to the new-profile
            // mark) and left the flow parked at CARSELECT. The console calls the READ-lock
            // accessor here (sub_823B96F0, BrnGameStateModuleIO.h:265): this leg only COPIES
            // the queue out of the game-state output buffer.
            const BrnGameState::GameStateModuleIO::OutputBuffer* lpcGameStateOutputBuffer =
                lpGameStateOutputBuffer;
            lpEffectsInputBuffer->GetGameActionQueue()->Append<13312, 16>(
                *lpcGameStateOutputBuffer->GetGameActionQueue());
        }

        // @0x823DD1D8/E8 -- the replay status interface.
        if (lpReplaysPreSimOutputBuffer != 0)
        {
            lpEffectsInputBuffer->SetReplayStatusInterface(
                lpReplaysPreSimOutputBuffer->GetStatusInterface());
        }

        // @0x823DD1EC/200 -- the sound pre-update block audio-effects message queue
        // (`addi r4, r11, 0x2A0`).
        if (lpSoundPreUpdateOutputBuffer != 0)
        {
            lpEffectsInputBuffer->SetAudioEffectsMessageQueue(
                &lpSoundPreUpdateOutputBuffer->GetPreUpdateOutput().GetAudioEffectsMessageQueue());
        }

        // @0x823DD228 -- `stbx r10, r31, 0xE494`: the suspend flag.
        lpEffectsInputBuffer->SetSuspendEffects(lbSuspendEffects);

        // sub_823B7A10 -- the exact reverse of the lock helper.
        if (lpSoundPreUpdateOutputBuffer != 0) lpSoundPreUpdateOutputBuffer->UnlockForRead();
        if (lpReplaysPreSimOutputBuffer != 0)  lpReplaysPreSimOutputBuffer->UnlockForRead();
        if (lpGameStateOutputBuffer != 0)      lpGameStateOutputBuffer->UnlockForRead();
        if (lpWorldOutputBuffer != 0)          lpWorldOutputBuffer->UnlockForRead();
        if (lpInputOutputBuffer != 0)          const_cast<CgsInput::InputIO::OutputBuffer*>(lpInputOutputBuffer)->UnlockForRead();
        if (lpDirectorOutputBuffer != 0)       lpDirectorOutputBuffer->UnlockForRead();
        lpEffectsInputBuffer->UnlockForWrite();

        // @0x823DD234/58 -- the module own step, through vtable +0x44.
        mEffectsModule.Update(lpInputBufferStack, lpOutputBufferStack,
                              lpEffectsInputBuffer, lpEffectsOutputBuffer, leUpdateSet);

        CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_Effects);

        const bool lbDestroyed = lpInputBufferStack->DestroyIOBuffer(&lpEffectsInputBuffer);
        CGS_ASSERT(lbDestroyed, "mpStack->DestroyIOBuffer( &mpBuffer )");  // CgsModuleIOHelper.h:57
        (void)lbDestroyed;
    }

    // ============================================================================
    // [DIAG BRN_CAMCOLLIDE_DIAG] [FLAG PC witness] -- NOT IN THE X360 BINARY. Default off; inert unset.
    // (owner's list 2026-09-27, lane L2 CAMCOLLIDE: "the camera tends to be behind walls or below the map for
    // things like crashes / takedowns / junkyard".)
    //
    // Once per director update, AFTER DirectorModule::Update has published the frame's camera, the PUBLISHED eye
    // is put through the console's own WORLD tests. These diagnostic queries are staged separately from
    // the director's camera queries on a private SceneManagerIO::InputBuffer_Query and
    // answered by the same WorldModule::ExternalSceneQueriesUpdate the closure uses, so every answer comes from
    // SceneManagerModule::ProcessVolumeTestDeepest / ProcessLineTestNearest's world arms (flags 2, world only --
    // no entity candidates, so no fine-module kernel is reached by the lines):
    //   in     the 0.1 m sphere (flt_82004014, VisibilityCollisionPolicy's own camera-in-geometry test) at the eye
    //          intersects the world;
    //   above  a nearest line from 200 m above the eye DOWN to the eye hits a surface (the world is single-sided:
    //          a hit means a surface facing up lies above the eye);
    //   below  a nearest line from the eye DOWN 200 m hits a surface;
    //   occA / occB  a nearest line eye -> player car / car -> eye hits the world (both directions, as
    //          VisibilityTest does, because a single-sided wall only answers from its front);
    // UNDER (below the map) = above && !below; OCC = occA || occB. One line per update, capped. The arbitrator
    // state that owns each frame is read off BRN_CRASHCAM_DIAG's "[crashcam] container current state" lines.
    // DELETE-WHEN: the owner's camera-collision item is closed.
    // ============================================================================
    namespace
    {
        const s32 KI_CAMCOLLIDE_MAX_LINES    = 30000;
        const f32 KF_CAMCOLLIDE_PROBE_METRES = 200.0f;

        void BrnDiag_CamCollideWitness(CgsModule::IOBufferStack* lpInputStack,
                                       CgsModule::IOBufferStack* lpOutputStack,
                                       WorldModule& lrWorldModule,
                                       const BrnDirector::DirectorIO::InputBuffer* lpDirectorInput,
                                       BrnDirector::DirectorIO::OutputBuffer* lpDirectorOutput,
                                       BrnUpdateSet lUpdateSet)
        {
            static const bool sbOn = (getenv("BRN_CAMCOLLIDE_DIAG") != 0);
            static s32 siLine = 0;
            if (!sbOn || CgsDev::Log::gpDebugPrint == 0 || siLine >= KI_CAMCOLLIDE_MAX_LINES
                || lpDirectorInput == 0 || lpDirectorOutput == 0)
            {
                return;
            }

            lpDirectorOutput->LockForRead();
            const rw::math::vpu::Matrix44Affine lCameraTransform = lpDirectorOutput->GetCameraOutput()->GetTransform();
            lpDirectorOutput->UnlockForRead();

            lpDirectorInput->LockForRead();
            const s32 liPlayer = static_cast<s32>(lpDirectorInput->GetPlayerCarIndex());
            const BrnDirector::Camera::VehicleInfo* lpRaceCars = lpDirectorInput->GetRaceCarInfo();
            Vector3 lCarPosition;
            lCarPosition.SetZero();
            if (lpRaceCars != 0 && liPlayer >= 0)
            {
                lCarPosition = lpRaceCars[liPlayer].mRaceCarState.mTransform.wAxis;
            }
            lpDirectorInput->UnlockForRead();

            const Vector3& lEye = lCameraTransform.wAxis;
            if (lEye.x == 0.0f && lEye.y == 0.0f && lEye.z == 0.0f)
            {
                return;   // no camera published yet (the boot frames): nothing to classify
            }

            CgsSceneManager::SceneManagerIO::InputBuffer_Query* lpQuery   = 0;
            CgsSceneManager::SceneManagerIO::OutputBuffer*      lpResults = 0;
            lpInputStack->CreateIOBuffer(&lpQuery, "CamCollideQ");
            if (lpQuery == 0)
            {
                return;
            }
            lpOutputStack->CreateIOBuffer(&lpResults, "CamCollideR");
            if (lpResults == 0)
            {
                lpInputStack->DestroyIOBuffer(&lpQuery);
                return;
            }

            // The query ids: owner 0xEE (no game owner uses it), index = the test.
            enum { E_TEST_IN = 0, E_TEST_ABOVE, E_TEST_BELOW, E_TEST_OCC_A, E_TEST_OCC_B, E_NUM_TESTS };
            CgsSceneManager::SceneQueryId laIds[E_NUM_TESTS];
            for (s32 liTest = 0; liTest < E_NUM_TESTS; ++liTest)
            {
                laIds[liTest].Set(0xEEu, static_cast<u16>(liTest));
            }

            Vector3 lAbove = lEye;
            lAbove.y += KF_CAMCOLLIDE_PROBE_METRES;
            Vector3 lBelow = lEye;
            lBelow.y -= KF_CAMCOLLIDE_PROBE_METRES;

            alignas(16) u8 laVolumeMemory[0x80];
            rw::Resource lVolumeResource = {};
            lVolumeResource.m_baseResources[0] = laVolumeMemory;
            const rw::collision::SphereVolume* lpSphere =
                rw::collision::SphereVolume::Initialize(lVolumeResource, 0.1f);

            const CgsSceneManager::EntityId lNoEntity(0xFFFFFFFFu);
            lpQuery->LockForWrite();
            CgsSceneManager::SceneManagerIO::SceneQueryInterface* lpInterface = lpQuery->GetSceneQueryInterface();
            lpInterface->VolumeTestDeepest(laIds[E_TEST_IN].mId, 2u, 0xFFu, lpSphere, &lCameraTransform, 0xFFFFFFFFu,
                                           CgsSceneManager::SceneManagerIO::E_EXCLUDE_ENTITY_ONLY);
            lpInterface->LineTestNearest(lAbove, lEye, laIds[E_TEST_ABOVE], 2u, 0xFFu, lNoEntity,
                                         CgsSceneManager::SceneManagerIO::E_NEAREST_EXCLUDE_ENTITY_ONLY);
            lpInterface->LineTestNearest(lEye, lBelow, laIds[E_TEST_BELOW], 2u, 0xFFu, lNoEntity,
                                         CgsSceneManager::SceneManagerIO::E_NEAREST_EXCLUDE_ENTITY_ONLY);
            lpInterface->LineTestNearest(lEye, lCarPosition, laIds[E_TEST_OCC_A], 2u, 0xFFu, lNoEntity,
                                         CgsSceneManager::SceneManagerIO::E_NEAREST_EXCLUDE_ENTITY_ONLY);
            lpInterface->LineTestNearest(lCarPosition, lEye, laIds[E_TEST_OCC_B], 2u, 0xFFu, lNoEntity,
                                         CgsSceneManager::SceneManagerIO::E_NEAREST_EXCLUDE_ENTITY_ONLY);
            lpQuery->UnlockForWrite();

            lrWorldModule.ExternalSceneQueriesUpdate(lpInputStack, lpOutputStack, lpQuery, lpResults, lUpdateSet);

            s32 laHit[E_NUM_TESTS] = { -1, -1, -1, -1, -1 };
            lpResults->LockForRead();
            const CgsModule::Event* lpEvent = 0;
            s32 liSize = 0;
            const CgsSceneManager::SceneManagerIO::OutputBuffer* lpConstResults = lpResults;
            const auto* lpQueue = lpConstResults->GetResultsQueue();
            for (s32 liType = lpQueue->GetFirstEvent(&lpEvent, &liSize); lpEvent != 0;
                 liType = lpQueue->GetNextEvent(lpEvent, &lpEvent, &liSize))
            {
                if (liType == 2)
                {
                    const CgsSceneManager::SceneManagerIO::OutEventLineTestNearestResult* lpNearest =
                        reinterpret_cast<const CgsSceneManager::SceneManagerIO::OutEventLineTestNearestResult*>(lpEvent);
                    if (lpNearest->mQueryId.GetOwner() == 0xEEu && lpNearest->mQueryId.GetIndex() < E_NUM_TESTS)
                    {
                        laHit[lpNearest->mQueryId.GetIndex()] = lpNearest->mbIntersection ? 1 : 0;
                    }
                }
                else if (liType == 5)
                {
                    const CgsSceneManager::SceneManagerIO::OutEventVolumeTestDeepestResult* lpDeepest =
                        reinterpret_cast<const CgsSceneManager::SceneManagerIO::OutEventVolumeTestDeepestResult*>(lpEvent);
                    if (lpDeepest->mQueryId.GetOwner() == 0xEEu && lpDeepest->mQueryId.GetIndex() == E_TEST_IN)
                    {
                        laHit[E_TEST_IN] = lpDeepest->mbIntersection ? 1 : 0;
                    }
                }
            }
            lpResults->UnlockForRead();
            lpOutputStack->DestroyIOBuffer(&lpResults);
            lpInputStack->DestroyIOBuffer(&lpQuery);

            const s32 liOccluded = (laHit[E_TEST_OCC_A] == 1 || laHit[E_TEST_OCC_B] == 1) ? 1 : 0;
            const s32 liUnder    = (laHit[E_TEST_ABOVE] == 1 && laHit[E_TEST_BELOW] == 0) ? 1 : 0;
            char lacLine[320];
            std::snprintf(lacLine, sizeof(lacLine),
                          "[camcol] f=%d eye=%.3f,%.3f,%.3f car=%.3f,%.3f,%.3f in=%d above=%d below=%d occA=%d occB=%d"
                          " UNDER=%d OCC=%d\n",
                          static_cast<int>(siLine),
                          static_cast<double>(lEye.x), static_cast<double>(lEye.y), static_cast<double>(lEye.z),
                          static_cast<double>(lCarPosition.x), static_cast<double>(lCarPosition.y),
                          static_cast<double>(lCarPosition.z),
                          static_cast<int>(laHit[E_TEST_IN]), static_cast<int>(laHit[E_TEST_ABOVE]),
                          static_cast<int>(laHit[E_TEST_BELOW]), static_cast<int>(laHit[E_TEST_OCC_A]),
                          static_cast<int>(laHit[E_TEST_OCC_B]), static_cast<int>(liUnder),
                          static_cast<int>(liOccluded));
            *CgsDev::Log::gpDebugPrint << lacLine;
            ++siLine;
        }
    }

    void BrnGameModule::DoUpdate_Director(bool lbPostGui)
    {
        if (mpDirectorOutputBuffer == 0)
            return;

        // The console's module scheduler only dispatches a module's per-frame entry points once
        // its staged Prepare has reported done; the PC drives them by hand, so it asks here.
        // Skipping this is not cosmetic: DirectorModule::Prepare stage 7 is what carves the
        // BehaviourManager's helper/behaviour pools, and an arbitrator running before that
        // allocates out of an un-carved pool (BehaviourManager.h:782 `lHelperID >= 0` fires).
        if (!mDirectorModule.IsPrepared())
            return;

        // ARTIST DoUpdate_Director823E8E1C..2C skips the pre-GUI camera
        // producer during the boot video. PostGuiUpdate still consumes GUI events.
        if (!lbPostGui && (ConstructUpdateSetFromFsm() & 0x20) != 0)
            return;

        BrnDirector::DirectorIO::InputBuffer* lpDirectorInput = 0;
        mpUpdateInputBufferStack->CreateIOBuffer(&lpDirectorInput, "Director");
        if (lpDirectorInput == 0)
            return;
        // [FLAG PC bring-up] Zero the staged region. The IO stack hands back RE-USED memory
        // and CreateIOBuffer<T> does not zero it (neither does the console), so every
        // published member (mePlayerCarIndex, mUsedRaceCars, the per-car VehicleInfo array, the
        // control block) would otherwise hold the PREVIOUS tenant's bytes. That is not a
        // cosmetic risk here: MainDirector::GetLivePlayerCarIndex reads mePlayerCarIndex and
        // mUsedRaceCars to decide whether a player car exists, so stale bytes could hand the
        // arbitrator a car index whose VehicleInfo is garbage. Zeroing gives the console's own
        // "no live player car" answer deterministically (index 0 with its used-race-car bit
        // clear -> GetLivePlayerCarIndex returns -1).
        // DELETE-WHEN: the real per-frame staging lands (BridgeControllerToDirector + the
        // race-car entity module's global output interface + the world contact/timer publishes),
        // at which point every one of these fields is written before it is read.
        memset(lpDirectorInput, 0, sizeof(*lpDirectorInput));
        // RE-Construct after the bring-up memset; the template already Constructed once.
        // CreateIOBuffer<T> above runs T::Construct itself now (2026-08-15), so this is the
        // SECOND Construct of this buffer -- and it is deliberate, because the memset in between
        // wiped what the first one wrote. It re-seeds the -1 sentinels: the buffer's OWN
        // Construct @0x822393D0 (not just the IOBuffer base) sets mePlayerCarIndex and
        // miCameraType to -1, and without the re-run the zero-fill would publish camera-type 0
        // as a live request every single frame. Delete this line together with the memset above,
        // not before it.
        lpDirectorInput->Construct();

        // ⭐ THE FRAME TIMESTEP -- the copy half of BridgeTimers @0x823BD150 (0x823BD1AC..
        // 0x823BD22C). It is the ONLY producer of the director input's timer status, and every
        // camera behaviour's per-frame advance is `<speed> * GetCurrentTimeStep()`.
        // CORRECTED 2026-09-25 (FX-DIRECTOR2): the snapshot is the one GameMain took at the START
        // of this sub-step (BridgeTimers there -- the console's 0x823F0DE4); this used to call
        // BridgeTimers itself, i.e. snapshot and reset the accumulator HERE, after the mid-step
        // UpdateTimers. Copied, not re-taken: the pause consumer (CheckGameActions) may have
        // started or stopped the sim timer since, and the console's director sees the status as
        // the step began. Staged on the pre-GUI call (the post-GUI pass consumes the same buffer
        // contents).
        if (!lbPostGui)
        {
            lpDirectorInput->LockForWrite();
            *lpDirectorInput->GetTimerStatusInterface() = mTimerStatusInterface;
            lpDirectorInput->UnlockForWrite();
        }

        // ⭐ [FLAG PC lifecycle, 2026-08-28 crash-slomo transport wave] RETIRE LAST SUB-STEP'S
        // DIRECTOR TIMER REQUEST, immediately before MainDirector::Update publishes this one.
        // Console equivalence: the module scheduler builds a fresh DirectorIO::OutputBuffer per
        // frame, so its TimerRequestInterface starts cleared and MainDirector::Update's
        // SetTimestepMultiplier is always the FIRST write of the frame -- which is what that
        // function's `!IsMultiplierRequested()` assert ("Attempt to change slowmo multiple
        // times") is asserting. On PC the buffer is the persistent mpDirectorOutputBuffer, so
        // the clear is explicit, immediately before the publish. (UpdateTimers() drains this slot
        // at the END of the sub-step, after the director wrote it -- the console's order since
        // 2026-09-25 -- so the request lives from its publish to its one consumer.)
        if (!lbPostGui)
        {
            mpDirectorOutputBuffer->LockForWrite();
            mpDirectorOutputBuffer->GetTimerRequestInterfac()->Clear();
            mpDirectorOutputBuffer->UnlockForWrite();
        }

        // ⭐ THE GUI -> DIRECTOR BRIDGE. X360 DoUpdate_DirectorPostGUI @0x823DCE38 runs it on
        // the POST-GUI pass, bracketed by the same write lock, immediately before
        // DirectorModule::PostGuiUpdate consumes what it published. This is the only path by
        // which BrnGui::Intro's fly-by START/END commands (477 / 478) reach the director.
        // (the IsPrepared test is the GUI out-queue's existence: it is Constructed by
        // GuiModule::Prepare, which since 2026-08-16 runs at loading stage 2 rather than at
        // BrnGameModule::Construct -- boot audit F-P1-1.)
        if (lbPostGui && mGuiModule.IsPrepared())
        {
            lpDirectorInput->LockForWrite();
            BridgeGuiToDirector(lpDirectorInput, mGuiModule.GetGuiOutQueue());
            lpDirectorInput->UnlockForWrite();
        }

        // ⭐⭐ THE WORLD -> DIRECTOR BRIDGE (X360 BridgeWorldToDirector @0x823E3AB0, run by
        // DoUpdate_Director on the PRE-GUI pass, right after BridgeControllerToDirector).
        // This is the ONLY caller of DirectorIO::InputBuffer::SetRaceCarInfo in the image --
        // it is what gives the director's cameras a REAL per-car VehicleInfo instead of the
        // zero-filled one every VehicleRef used to resolve to. The world output buffer is the
        // one the world leg (DriveWorldUpdateFrame, run earlier in this same sub-step by the
        // flow state) published into; see GetWorldUpdateOutputBuffer().
        //
        // ⛔ THE FAKE PLAYER CAR IS RETIRED. This block used to call SetPlayerCarIndex(0) +
        // SetRaceCarInUse(0, true) on a car whose VehicleInfo was ZEROED, purely so
        // MainDirector::GetLivePlayerCarIndex() != -1 and the attract-mode stand-in would
        // tick. VehicleRef::IsValid passed on it and any ICE-anim take framed against it was
        // an ORIGIN camera. Both fields now come from the real chain:
        //   RaceCarEntityModule::UpdateOutputInterfaces  (publishes the active-car interface)
        //     -> WorldModule::BridgeRaceCarEntityInfoToOutput_PostPhysics  (into the world out)
        //       -> BridgeWorldToDirector                                   (into the director)
        // If no player car is active the bridge publishes index -1, which is the console's own
        // "no live player car" answer -- an honest fail instead of a silently wrong camera.
        // ==== THE CONTROLLER -> DIRECTOR BRIDGE (X360 BridgeControllerToDirector
        // @0x823C0F70). THE PLAYER'S PAD NEVER REACHED THE DIRECTOR ON THIS BUILD.
        // The function was fully bodied, declared, and its TU mounted -- and it had ZERO
        // callers; its only reference in the whole tree was the _embed_check taking its
        // address. So DirectorIO::InputBuffer's 224-byte controller snapshot stayed at
        // DoUpdate_Director's zero-fill every frame, which means:
        //     mCameraModifier == (0,0)  -> the free-look / orbit stick is dead
        //     mbLookback      == false  -> the rear-view (L1) camera can never engage
        //     mbCycleCameras  == false  -> the camera-change button does nothing
        // Every consumer downstream was already complete and waiting on this one call:
        //   BehaviourManager::PublishControllerState  copies both into BehaviourSharedInfo
        //   BehaviourGameplayExternal::Update         -> CameraSphericalRotationController
        //                                               ::Update(stick, lookback, ...)
        //   BehaviourRotateAboutVehicle::Update       -> the car-select orbit
        //   Arbitrator                                -> mbLookbackOverride
        //
        // POSITION IS THE CONSOLE'S: DoUpdate_Director runs it on the PRE-GUI pass
        // immediately BEFORE BridgeWorldToDirector -- which is what the banner on that
        // bridge below has said all along ("run by DoUpdate_Director on the PRE-GUI pass,
        // right after BridgeControllerToDirector").
        //
        // The lock bracket matches the sibling BridgeControllerToGameState call: the pad
        // buffer read-locked, the director input write-locked.
        // [FLAG PC bring-up] the pad record is ONE SUB-STEP STALE here, exactly as the
        // game-state leg already documents -- InputPadsPC::UpdatePlayer0 refills
        // mPcInputOutputBuffer later in the frame. One frame of camera-stick latency.
        // DELETE-WHEN the input fill moves to the top of the frame where the console has it.
        if (!lbPostGui)
        {
            mPcInputOutputBuffer.LockForRead();
            lpDirectorInput->LockForWrite();
            BridgeControllerToDirector(lpDirectorInput, &mPcInputOutputBuffer);
            lpDirectorInput->UnlockForWrite();
            mPcInputOutputBuffer.UnlockForRead();
        }

        if (!lbPostGui && mpWorldUpdateOutputBuffer != 0)
        {
            mpWorldUpdateOutputBuffer->LockForRead();
            lpDirectorInput->LockForWrite();
            BridgeWorldToDirector(lpDirectorInput, mpWorldUpdateOutputBuffer);
            lpDirectorInput->UnlockForWrite();
            mpWorldUpdateOutputBuffer->UnlockForRead();
        }

        // ⭐⭐ THE GAME-STATE -> DIRECTOR BRIDGE (X360 BridgeGameStateToDirector @0x823CD170,
        // run by DoUpdate_Director on the PRE-GUI pass). Its Append is the ONLY producer of
        // the game actions MainDirector::ProcessInputQueue drains -- the only route by which
        // the junkyard / car-select ladder can ever start. All three links are real now:
        //   producer  GameStateModuleIO::OutputBuffer::GetGameActionQueue()  (X360 0x823B96F0)
        //   bridge    this call
        //   consumer  MainDirector::ProcessInputQueue                        (cases 62..85)
        // ⛔ WHAT IS STILL MISSING is a PRODUCER THAT POSTS: CarSelectManager (the TU that
        // posts entry action 73) is not mounted yet, so this queue is empty every frame today.
        // See the measured cost at the top of BrnCarSelectManager.cpp.
        if (!lbPostGui)
        {
            BrnGameState::GameStateModuleIO::OutputBuffer* lpGameStateOutput =
                mGameStateModule.GetOutputBuffer();
            // ⭐ RUNTIME-PROVEN 2026-08-01 (PROD_RUN1, 140 s, 0 asserts): a temporary probe that
            // posted game action 73 (E_ACTION_CAR_SELECT_TRANSITION_IN, payload {1,0}) onto
            // lpGameStateOutput->GetGameActionQueue() at frame 120 -- i.e. onto the CONSOLE'S OWN
            // producer surface, not forged into the director -- drove the director's
            // meJunkyardState 0 -> 2 (E_JY_INTRO_NO_CARS) and held it for 388 trace samples.
            // The probe was removed; the path it exercised is the code below.
            if (lpGameStateOutput != 0)
            {
                lpGameStateOutput->LockForRead();
                lpDirectorInput->LockForWrite();
                BridgeGameStateToDirector(lpDirectorInput, lpGameStateOutput);
                lpDirectorInput->UnlockForWrite();
                lpGameStateOutput->UnlockForRead();
            }
        }

        // ARTIST @0x823E8EF8..0x823E8F2C, after BridgeGameStateToDirector:
        // replay (update set 0x100) or online -> false; otherwise copy mbSimPaused.
        // The director uses this byte to hold simulation-driven camera behaviours.
        // FLAG: replay playback is not implemented; ConstructUpdateSetFromFsm does not
        // yet receive ConstructUpdateSet's replay bit (@0x823DCB40).
        if (!lbPostGui)
        {
            const u32 KU_UPDATE_SET_REPLAY_PLAYBACK = 0x100u;
            const bool lbReplayPlayback =
                (static_cast<u32>(ConstructUpdateSetFromFsm()) & KU_UPDATE_SET_REPLAY_PLAYBACK) != 0;

            lpDirectorInput->LockForWrite();
            lpDirectorInput->SetSimPaused(!lbReplayPlayback && !mbOnline && mbSimPaused);
            lpDirectorInput->UnlockForWrite();
        }

        // ------------------------------------------------------------------------------
        // ⛔ THE INTRO FLY-BY STAND-IN IS RETIRED (2026-08-01).
        //
        // What used to be here: the GUI's fly-by request (477) was intercepted and turned into
        // `Arbitrator::SetDoAttractMode(true)`, running ArbStateAttractMode's BehaviourRoadRunner
        // -- a real console camera, but the DEBUG one. The X360 image's only writer of
        // mbDoAttractMode besides Arbitrator::Construct is the debug-menu entry "Do attract mode"
        // (DebugComponent::OnActivate @0x82275F68), so that camera never ships.
        //
        // Its DELETE-WHEN ("ArbStateCarSelect + BehaviourIceAnim + the game-intro shot group are
        // real") is met, and the last link -- something that actually makes the director's
        // meJunkyardState non-zero so the roaming ladder hands over to ArbStateCarSelect -- landed
        // with ProcessGameEvents' case-78 arm (CarSelectManager::ReallyEnterJunkyardAtStartOfGame). The console's own
        // chain now runs end to end:
        //   BridgeGuiToDirector 477 -> InputBuffer::mbStartGameIntroFlyby
        //   MainDirector::PostGuiUpdate  -> GameState::mbGameIntroFlybyActive = true
        //   ArbStateCarSelect::Update    -> the authored ICE camera movies from the "game intro"
        //                                   shot group ("606002")
        //


        if (!lbPostGui)
        {
            // The console's scene-query leg (DoUpdate_Director @0x823E8DE0). The
            // director's cameras ASK during PreSceneQueryUpdate and READ THE ANSWERS in Update; the
            // world runs their queries in between, synchronously, in this order:
            //   1. IOHelper<SceneManagerIO::InputBuffer_Query>(input stack, "SceneQuery")   0x823C1A28
            //      IOHelper<DirectorIO::SceneQueryInputBuffer>(input stack, "DirectorSQ")   0x823C1A90
            //      (the console makes both at the head of the function; on this build the director
            //       input is made first, so they sit above it on the same LIFO stack)
            //      IOHelper<DirectorIO::SceneQueryOutputBuffer>(output stack, "DirectorSQ") 0x823C1AF8
            //   2. DirectorModule::PreSceneQueryUpdate                                        0x8225C768
            //   3. under the lock pair sub_823B6FE0 / sub_823B7060 (dest write, source read):
            //      external->GetSceneQueryInterface()->Append(*sqOutput->GetSceneQueryInterface())
            //                                         (SceneQueryInterface::Append @0x823C4FF8)
            //      then the SQ output buffer is destroyed
            //   4. IOHelper<SceneManagerIO::OutputBuffer>(output stack, "DirectorESQ")       0x823C1B60
            //      WorldModule::ExternalSceneQueriesUpdate(in stack, out stack, external, results,
            //                                              update set)                     0x827B06C8
            //   5. under the same lock pair: sqInput->GetResultsQueue()->Append(*results->GetResultsQueue())
            //      (VariableEventQueue<4032,16>::Append<32768,16> @0x823DA090), then the results
            //      buffer is destroyed
            //   6. a FRESH SceneQueryOutputBuffer ("DirectorSQ"), DirectorModule::Update 0x82275300 on it
            //      and the SQ input, then that buffer destroyed
            //   7. the SQ input and the external query buffer destroyed
            // The PC has no replay playback path; the framework arguments remain unread.
            CgsSceneManager::SceneManagerIO::InputBuffer_Query* lpExternalQuery   = 0;
            BrnDirector::DirectorIO::SceneQueryInputBuffer*     lpSceneQueryInput = 0;
            mpUpdateInputBufferStack->CreateIOBuffer(&lpExternalQuery, "SceneQuery");
            mpUpdateInputBufferStack->CreateIOBuffer(&lpSceneQueryInput, "DirectorSQ");

            BrnDirector::DirectorIO::SceneQueryOutputBuffer* lpSceneQueryOutput = 0;
            mpUpdateOutputBufferStack->CreateIOBuffer(&lpSceneQueryOutput, "DirectorSQ");

            if (lpExternalQuery != 0 && lpSceneQueryInput != 0 && lpSceneQueryOutput != 0)
            {
                mDirectorModule.PreSceneQueryUpdate(0, 0, lpDirectorInput, mpDirectorOutputBuffer,
                                                    lpSceneQueryOutput, false);

                CgsModule::LockBuffersForIO(lpExternalQuery, lpSceneQueryOutput);
                lpExternalQuery->GetSceneQueryInterface()->Append(
                    *static_cast<const BrnDirector::DirectorIO::SceneQueryOutputBuffer*>(lpSceneQueryOutput)
                         ->GetSceneQueryInterface());                              // the read-locked getter 0x823B25F0
                CgsModule::UnlockBuffersForIO(lpExternalQuery, lpSceneQueryOutput);
                mpUpdateOutputBufferStack->DestroyIOBuffer(&lpSceneQueryOutput);

                CgsSceneManager::SceneManagerIO::OutputBuffer* lpExternalResults = 0;
                mpUpdateOutputBufferStack->CreateIOBuffer(&lpExternalResults, "DirectorESQ");
                if (lpExternalResults != 0)
                {
                    mWorldModule.ExternalSceneQueriesUpdate(mpUpdateInputBufferStack, mpUpdateOutputBufferStack,
                                                            lpExternalQuery, lpExternalResults,
                                                            ConstructUpdateSetFromFsm());

                    CgsModule::LockBuffersForIO(lpSceneQueryInput, lpExternalResults);
                    lpSceneQueryInput->GetResultsQueue()->Append(
                        *static_cast<const CgsSceneManager::SceneManagerIO::OutputBuffer*>(lpExternalResults)
                            ->GetResultsQueue());
                    CgsModule::UnlockBuffersForIO(lpSceneQueryInput, lpExternalResults);
                    mpUpdateOutputBufferStack->DestroyIOBuffer(&lpExternalResults);
                }

                mpUpdateOutputBufferStack->CreateIOBuffer(&lpSceneQueryOutput, "DirectorSQ");
                if (lpSceneQueryOutput != 0)
                {
                    mDirectorModule.Update(0, 0, lpDirectorInput, mpDirectorOutputBuffer,
                                           lpSceneQueryInput, lpSceneQueryOutput);
                    mpUpdateOutputBufferStack->DestroyIOBuffer(&lpSceneQueryOutput);
                }
            }
            else if (lpSceneQueryOutput != 0)
            {
                mpUpdateOutputBufferStack->DestroyIOBuffer(&lpSceneQueryOutput);
            }

            if (lpSceneQueryInput != 0)
                mpUpdateInputBufferStack->DestroyIOBuffer(&lpSceneQueryInput);
            if (lpExternalQuery != 0)
                mpUpdateInputBufferStack->DestroyIOBuffer(&lpExternalQuery);
        }
        else
        {
            mDirectorModule.PostGuiUpdate(0, 0, lpDirectorInput, mpDirectorOutputBuffer);

            // [DIAG BRN_DIRECTOR_TRACE] Report what the director actually PUBLISHED this
            // frame. This is the measurement the fly-by campaign needs: whether the director
            // camera exists, where it is, and whether it MOVES. Off unless the env var is set;
            // remove with the bring-up path.
            static const bool sbTrace = (getenv("BRN_DIRECTOR_TRACE") != 0);
            if (sbTrace)
            {
                static s32 siTraceFrame = 0;
                if ((siTraceFrame % 30) == 0 && CgsDev::Log::gpDebugPrint != 0)
                {
                    mpDirectorOutputBuffer->LockForRead();
                    const BrnDirector::Camera::Camera* lpCamera =
                        mpDirectorOutputBuffer->GetCameraOutput();
                    const rw::math::vpu::Matrix44Affine& lXform = lpCamera->GetTransform();
                    // Also report WHERE THE ARBITRATOR IS. Without this the trace cannot tell
                    // "the camera is static because the arbitrator never ran" from "... because
                    // the behaviour it picked produced nothing" -- which is exactly the
                    // distinction the fly-by campaign keeps having to make. EState:
                    // 0 PREPARE / 1 PRE_NORMAL / 2 NORMAL / 3 CRASH_NAV / 4 CRASH_NAV_ICE /
                    // 5 CHANGING_TO_ATTRACT / 6 ATTRACT_MODE / 7 FINAL_ELITE / 8 RENDER_METRICS /
                    // 9 RELEASE.
                    const BrnDirector::Arbitrator& lrArbitrator =
                        mDirectorModule.GetMainDirector().GetArbitrator();
                    // ⭐ ALSO report the junkyard / car-select sub-state. It is the gate on the
                    // whole car-select ladder (ArbStateRoaming -> E_STATE_CAR_SELECT), and
                    // until MainDirector::ProcessInputQueue landed it could never be anything
                    // but 0 -- so "did the game-action seam actually run?" is exactly this
                    // number. EJunkyardState: 0 INACTIVE / 1 INTRO_UNLOCKING_CARS /
                    // 2 INTRO_NO_CARS / 3 CAR_UNLOCK / 4 CAR_SELECT / 5 WAITING_FOR_AUDIO.
                    const BrnDirector::GameState& lrGameState =
                        mDirectorModule.GetMainDirector().GetGameState();
                    *CgsDev::Log::gpDebugPrint
                        << "[director] f" << siTraceFrame
                        << " dt " << (mSimTimer.GetRate() * mSimTimer.GetScaleCurrent())
                        << " arb " << static_cast<s32>(lrArbitrator.GetState())
                        << " jy " << static_cast<s32>(lrGameState.meJunkyardState)
                        // ⭐ ADDED 2026-08-01 (ArbStateRoaming::Update wave). The roaming
                        // ladder in ProcessPossibleStateChanges STOPS at the
                        // `GetCurrentEventState() == E_EVENT_STATE_PRE_INTRO(0)` arm and never
                        // reaches the junkyard test below it, so "jy" alone cannot say whether
                        // the car-select transition was even eligible. These two are the gate:
                        // meEventType (-1 == free roam) and the event-state journal head
                        // (0 PRE_INTRO / 1 INTRO / 2 COUNTDOWN / 3 ACTIVE / 4 POST_EVENT).
                        << " evtype " << static_cast<s32>(lrGameState.meEventType)
                        << " evst " << static_cast<s32>(lrGameState.GetCurrentEventState())
                        << (lrArbitrator.GetDoAttractMode() ? " attract" : " -")
                        << " eye (" << lXform.wAxis.x << ", " << lXform.wAxis.y
                        << ", " << lXform.wAxis.z << ")"
                        << " at (" << lXform.zAxis.x << ", " << lXform.zAxis.y
                        << ", " << lXform.zAxis.z << ")"
                        << " fov " << lpCamera->GetFOV() << "\n";
                    mpDirectorOutputBuffer->UnlockForRead();
                }
                ++siTraceFrame;
            }
        }

        // [DIAG BRN_CAMCOLLIDE_DIAG] the published eye through the console's world tests (see the witness).
        if (!lbPostGui)
        {
            BrnDiag_CamCollideWitness(mpUpdateInputBufferStack, mpUpdateOutputBufferStack, mWorldModule,
                                      lpDirectorInput, mpDirectorOutputBuffer, ConstructUpdateSetFromFsm());
        }

        mpUpdateInputBufferStack->DestroyIOBuffer(&lpDirectorInput);
    }

    // PC retention extends the final completed substep's DirectorOutput lifetime
    // across render frames with no substep. Completion is the frame boundary,
    // including original branches that leave a default camera in the output.
    void BrnGameModule::LatchDispatchCamera()
    {
        if (mpDirectorOutputBuffer == 0)
            return;

        mpDirectorOutputBuffer->LockForRead();
        mDispatchCamera = *mpDirectorOutputBuffer->GetCameraOutput();
        mbDispatchCameraPublished = true;
        mpDirectorOutputBuffer->UnlockForRead();
    }

    const BrnDirector::Camera::Camera* BrnGameModule::GetDispatchCamera() const
    {
        return mbDispatchCameraPublished ? &mDispatchCamera : 0;
    }

    // ARTIST 823DC458: the original RendererIO -> WorldDispatch handoff.
    int BrnGameModule::DoDispatch()
    {
        DispatchThreadInputBuffer* const lpDispatchInput =
            mDispatchThreadInputBufferManager.GetWriteBuffer();
        // ARTIST 823DC484..4A0 invokes the original effects PreRenderUpdate
        // before even the resource-stall branch, through vtable slot 0x48.
        mEffectsModule.PreRenderUpdate(lpDispatchInput);
        lpDispatchInput->LockForWrite();
        lpDispatchInput->SetIsStalled(mbStalled);
        lpDispatchInput->UnlockForWrite();
        if (mbStalled)
            return 0;

        // Original cadence uses the final completed substep. Native PC presents
        // without a substep retain that same output, without pose interpolation.
        if (mpDirectorOutputBuffer == 0 && GetDispatchCamera() == 0)
            return 0;

        BrnUpdateSet lUpdateSet = ConstructUpdateSetFromFsm();
        CgsModule::IOHelper<BrnWorldIO::DispatchInputBuffer> lWorldInput(
            mpUpdateInputBufferStack, "WorldDispatch");
        CgsModule::IOHelper<BrnWorldIO::DispatchOutputBuffer> lWorldOutput(
            mpUpdateOutputBufferStack, "WorldDispatch");
        CgsModule::IOHelper<RendererIO::InputBuffer> lRendererInput(
            mpUpdateInputBufferStack, "Render");
        CgsModule::IOHelper<RendererIO::OutputBuffer> lRendererOutput(
            mpUpdateOutputBufferStack, "Render");
        CgsModule::IOHelper<BrnEffects::EffectsIO::DispatchInputBuffer> lEffectsInput(
            mpUpdateInputBufferStack, "Effects");

        RendererIO::InputBuffer* const lpRendererInput = lRendererInput;
        RendererIO::OutputBuffer* const lpRendererOutput = lRendererOutput;
        BrnWorldIO::DispatchInputBuffer* const lpWorldInput = lWorldInput;
        BrnWorldIO::DispatchOutputBuffer* const lpWorldOutput = lWorldOutput;
        BrnEffects::EffectsIO::DispatchInputBuffer* const lpEffectsInput = lEffectsInput;

        lpRendererInput->LockForWrite();
        if (mpDirectorOutputBuffer != 0)
            mpDirectorOutputBuffer->LockForRead();
        const BrnDirector::Camera::Camera* const lpCamera = mpDirectorOutputBuffer != 0
            ? mpDirectorOutputBuffer->GetCameraOutput() : GetDispatchCamera();
        lpRendererInput->SetBrnCamera(*lpCamera);
        if (mpDirectorOutputBuffer != 0)
            mpDirectorOutputBuffer->UnlockForRead();
        lpRendererInput->UnlockForWrite();

        if (mpDirectorOutputBuffer != 0)
            mpDirectorOutputBuffer->LockForRead();
        lpDispatchInput->LockForWrite();
        const BrnDirector::Camera::CameraState& lrState = lpCamera->GetState();
        lpDispatchInput->SetIsRenderingAtFullFrameRate(
            lrState.IsFlagSet(BrnDirector::Camera::CameraState::E_FLAG_RACING_GAMEPLAY_CAMERA)
            || lrState.IsFlagSet(BrnDirector::Camera::CameraState::E_FLAG_ROAD_FOLLOWING_CAM));
        lpDispatchInput->UnlockForWrite();
        if (mpDirectorOutputBuffer != 0)
            mpDirectorOutputBuffer->UnlockForRead();

        mRenderModule.Update(mpUpdateInputBufferStack, mpUpdateOutputBufferStack,
                             lpRendererInput, lpRendererOutput);

        // ARTIST 823DC670..700 locks all bridge destinations before reading
        // the renderer output, and holds that source through world/effects work.
        BrnResource::GameDataIO::InputBuffer* const lpGameDataInput =
            BrnGameMainFlowController::GetScriptedLoadGameDataInput();
        CgsGui::CgsGuiModuleIO::InputBuffer* const lpGuiRenderInput = mpGuiInputBuffer != 0
            ? mpGuiInputBuffer : mGuiModule.GetCompletedRenderInputPC();
        lpEffectsInput->LockForWrite();
        lpWorldInput->LockForWrite();
        if (lpGameDataInput != 0)
            lpGameDataInput->LockForWrite();
        lpRendererOutput->LockForRead();
        // Zero-substep native presents retain actual completed GUI input.
        // Refresh all five pointers from this dispatch's current renderer bank.
        if (lpGuiRenderInput != 0)
            lpGuiRenderInput->LockForWrite();
        BridgeRendererToWorld(lpWorldInput, lpRendererOutput);
        if (lpGuiRenderInput != 0)
            BridgeRendererToGui(lpGuiRenderInput, lpRendererOutput);
        BridgeRendererToEffects(lpEffectsInput, lpRendererOutput);
        if (lpGameDataInput != 0)
            lpGameDataInput->SetIm2dDebugRenderBuffer(lpRendererOutput->GetIm2dDebugRenderBuffer());
        lpEffectsInput->UnlockForWrite();
        lpWorldInput->UnlockForWrite();
        if (lpGameDataInput != 0)
            lpGameDataInput->UnlockForWrite();
        if (lpGuiRenderInput != 0)
            lpGuiRenderInput->UnlockForWrite();
        if (mpGuiInputBuffer != 0)
            mGuiModule.CaptureRenderInputPC(mpGuiInputBuffer);

        lpWorldInput->LockForWrite();
        lpWorldInput->SetDispatchThreadInputBuffer(lpDispatchInput);
        lpWorldInput->UnlockForWrite();
        lpEffectsInput->LockForWrite();
        if (mpDirectorOutputBuffer != 0)
            mpDirectorOutputBuffer->LockForRead();
        lpEffectsInput->SetCameraInput(lpCamera);
        lpEffectsInput->UnlockForWrite();
        if (mpDirectorOutputBuffer != 0)
            mpDirectorOutputBuffer->UnlockForRead();

        BrnResource::GameDataIO::OutputBuffer* const lpGameDataOutput =
            BrnGameMainFlowController::GetScriptedLoadGameDataOutput();
        if (lpGameDataOutput != 0)
        {
            lpGameDataOutput->LockForRead();
            if (*lpGameDataOutput->GetLiveUpdateStatus())
                lUpdateSet &= static_cast<BrnUpdateSet>(~0x80u);
            lpGameDataOutput->UnlockForRead();
        }

        mWorldModule.GenerateFrustumQueries(mpUpdateInputBufferStack, mpUpdateOutputBufferStack,
                                            lpWorldInput, lpWorldOutput, &lUpdateSet);

        if (!mbSteppingFrames && lpGuiRenderInput != 0)
            mGuiModule.Render(mGuiModule.GetViewInputBuffer(), lpGuiRenderInput, lpRendererOutput);

        lpDispatchInput->LockForWrite();
        lpDispatchInput->SetIsDiskError(mbDiskError);
        lpDispatchInput->UnlockForWrite();

        mWorldModule.GenerateDispatchLists(mpUpdateInputBufferStack, mpUpdateOutputBufferStack,
                                           lpWorldInput, lpWorldOutput, &lUpdateSet);
        mRenderModule.CompleteWorldDispatchFramePC((lUpdateSet & 0x80) != 0);

        lpWorldOutput->LockForRead();
        lpEffectsInput->LockForWrite();
        BridgeWorldToEffects_Dispatch(lpEffectsInput, lpWorldOutput);
        lpEffectsInput->UnlockForWrite();
        lpWorldOutput->UnlockForRead();
        lpEffectsInput->LockForRead();
        mEffectsModule.GenerateDispatchLists(mpUpdateInputBufferStack, lpEffectsInput,
                                             lpDispatchInput);
        lpEffectsInput->UnlockForRead();
        DebugManagerRender(lpRendererOutput);
        lpRendererOutput->UnlockForRead();
        mRenderModule.CompleteCommandFramePC(lpDispatchInput,
            BrnRendererModule::E_COMMAND_PRODUCER_WORLD_AND_EFFECTS);
        return 0;
    }

    // @ BrnGameModule.cpp:1047 (X360 0x823BC868) - tear down the owned modules + the module base.
    // The X360 first clears a terminated flag (off +10094134) and destructs an off-path collision
    // generator (off +10095440) - both fall in the omitted member ranges of this incremental
    // layout - then calls Destruct() on all 11 engine modules in the order below, the module base,
    // and finally the network module. Reconstructed faithfully (the two off-path subsystem touches
    // are noted, not declared here). Not on the boot/loading path.
    void BrnGameModule::Destruct()
    {
        // [+10094134 terminated flag = 0; +10095440 CgsCollision::BaseCollisionGenerator::Destruct
        //  - both off-path in this incremental layout, omitted]
        mEffectsModule.Destruct();
        mSoundModule.Destruct();
        mDirectorModule.Destruct();
        mRenderModule.Destruct();
        mGameStateModule.Destruct();
        mGuiModule.Destruct();
        mInputModule.Destruct();
        mWorldModule.Destruct();
        mReplayModule.Destruct();
        mGameDataModule.Destruct();
        CgsModule::ModuleSingleBuffered::Destruct();
        mNetworkModule.Destruct();
    }

    // @ BrnGameModule.cpp:925 (X360 0x823CB2A8) - resumable staged release (counterpart of
    // Prepare). meReleaseStage is the resume point; a failed sub-release returns false so the
    // caller re-drives from the same stage. The release SEQUENCE is GUI -> sound -> hardware
    // (+input) -> game-data -> module base -> network -> done; the cases are written in that
    // execution order with fallthrough (the same resumable-switch shape as the module base's
    // ModuleSingleBuffered::Release), so entering at any stage runs the rest. Note the enum
    // values along that path are not monotonic (HARDWARE = 5 sits between SOUND = 2 and
    // GAMEDATAMODULE = 3); C++ fallthrough follows source order, not case value, so this is
    // exact - the Hex-Rays output only used gotos because its jump table sorts by case value.
    // Off-path touches (the System360HW release + two terminated-flag fields) are in this
    // layout's omitted ranges and noted. Not on the boot/loading path.
    bool BrnGameModule::Release()
    {
        switch (meReleaseStage)
        {
            case E_RELEASESTAGE_START:
            case E_RELEASESTAGE_GUI:
                meReleaseStage = E_RELEASESTAGE_GUI;
                if (!mGuiModule.Release())
                    return false;
                // fall through
            case E_RELEASESTAGE_SOUND:
                meReleaseStage = E_RELEASESTAGE_SOUND;
                if (!mSoundModule.Release())
                    return false;
                // fall through
            case E_RELEASESTAGE_HARDWARE:
                meReleaseStage = E_RELEASESTAGE_HARDWARE;
                // [+10097088 BrnHW::System360HW::Release(&mHardware): off-path hardware, omitted;
                //  the X360 also returns false here if the hardware release fails]
                if (!mInputModule.Release())
                    return false;
                // fall through
            case E_RELEASESTAGE_GAMEDATAMODULE:
                meReleaseStage = E_RELEASESTAGE_GAMEDATAMODULE;
                if (!mGameDataModule.Release())
                    return false;
                // fall through
            case E_RELEASESTAGE_MANAGER:
                meReleaseStage = E_RELEASESTAGE_MANAGER;
                if (!CgsModule::ModuleSingleBuffered::Release())
                    return false;
                // fall through
            case E_RELEASESTAGE_NETWORK:
                meReleaseStage = E_RELEASESTAGE_NETWORK;
                if (!mNetworkModule.Release())
                    return false;
                // fall through
            case E_RELEASESTAGE_DONE:
                // [+10094134 terminated flag = 0: off-path, omitted]
                meReleaseStage = E_RELEASESTAGE_DONE;
                // [+10094156 = 0: off-path, omitted]
                return true;
            default:
                CGS_ASSERT(false, "0");
                return false;
        }
    }

    // operator++(EReleaseStage&, int) @ 0x823A8AD8 - POST-increment for the EReleaseStage stage
    // machine, used by Release() to advance meReleaseStage. X360 body: v1 = *a1; *a1 = *a1 + 1;
    // if (*a1 > 7) assert; return v1 -- save the old value, advance the stage, assert the advanced
    // value is still <= E_RELEASESTAGE_DONE (=7), and return the OLD value.
    //
    // FLAG (static-message assert): the X360 fires the assert with the literal expression string
    // "leEnumIndex <= BrnGameModule::E_RELEASESTAGE_DONE" at BrnGameModule.h:1443. We use the
    // committed CGS_ASSERT macro with that same expression text (the macro supplies __FILE__ /
    // __LINE__); the original's BrnGameModule.h:1443 site is NOT baked in.
    BrnGameModule::EReleaseStage operator++(BrnGameModule::EReleaseStage& leStage, int)
    {
        BrnGameModule::EReleaseStage leOld = leStage;
        leStage = static_cast<BrnGameModule::EReleaseStage>(leStage + 1);
        CGS_ASSERT(leStage <= BrnGameModule::E_RELEASESTAGE_DONE,
                   "leEnumIndex <= BrnGameModule::E_RELEASESTAGE_DONE");
        return leOld;
    }

    // @ BrnGameModule.cpp:1580 (X360 0x823EFBD0) - one-time per-game-instance prepare: under the
    // GameData IO buffer locks, a resumable stage machine that (1) queues LoadBundle requests for
    // "shaders.bndl", "GlobalTextureDictionary.bin" and "Language\\Fonts\\Default.font" through
    // the GameData input's RequestInterface<32768>, (2) waits for the 3 loads then posts the six
    // global-texture acquires, (3) waits for those and hands them to
    // BrnRendererModule::PrepareAgain, then (4) runs the GameState module's game-prepare.
    //
    // X360 stage-machine shape (switch on gm+10094164, reproduced exactly):
    //   case 0/1: stage=1; LoadBundle(&q, 2, 10, "shaders.bndl", true)
    //                      LoadBundle(&q, 1, 10, "GlobalTextureDictionary.bin", false)
    //                      LoadBundle(&q, 0,  0, "Language\\Fonts\\Default.font", false)   ->fall
    //   case 2:   stage=2; if (q.GetLength() < 3) return not-done;
    //                      q.Clear(); post the 6 acquire events (ids 0..5)                 ->fall
    //   case 3:   stage=3; if (q.GetLength() < 5) return not-done;
    //                      walk the queue (event type 4) -> the 5 texture pointers + the
    //                      font handle (id 5: Font::CreateTextureState + SetDebugFont);
    //                      assert each; BrnRendererModule::PrepareAgain(...); q.Clear()    ->fall
    //   case 4:   stage=4; GameStateModule game-prepare (vtable +64) on a scratch
    //                      GameStateModuleIO::OutputBuffer; done -> return true
    //   not-done tail (LABEL_36): create the RendererIO pair, BrnRendererModule::Update,
    //                      latch the reusable loading-screen allocator, publish
    //                      IsStalled/IsDiskError onto the dispatch input, CheckDiskError.
    //
    // RECONSTRUCTED HERE: all four stages. Stage 2 brings SHADERS.BNDL online, which is what
    // lets every streamed world Material resolve its ShaderTechnique / ShaderProgramBuffer
    // imports instead of falling back to the bring-up shader; stage 3 is the six-acquire
    // round trip (⭐ 2026-08-16, boot audit F-P2-2/F-P2-3 -- see the stage bodies); stage 4 is
    // the GameState module's game-prepare. The not-done tail is PARTIAL: its two
    // dispatch-input publishes are restored, its RendererIO/allocator-latch half is not
    // (F-P2-4, flagged at the tail).
    //
    // FLAG PC-platform leaf: the X360 services the GameData module on its own resource-update
    // thread (IThreadClass::ResourceUpdateThread) while this stage machine blocks the update
    // thread, and BrnGameModule::Prepare has already prepared the GameDataModule by the time
    // UpdateThread first runs. The single-threaded PC host has neither: GameDataModule::Prepare
    // is driven from the loading flow (which only runs once GamePrepare has returned done) and
    // nothing else pumps GameDataModule::Update. So this body drives BOTH inline -- the module
    // prepare first, then one Update pump per wait frame. Both are the module's own resumable
    // machines, so the flow's later GameDataModule::Prepare call still finds it done.
    bool BrnGameModule::GamePrepare()
    {
        // The X360 pair is gm+10055440 / gm+10055444 (see the accessors' note).
        BrnResource::GameDataIO::InputBuffer*  lpGameDataInput =
            BrnGameMainFlowController::GetScriptedLoadGameDataInput();
        BrnResource::GameDataIO::OutputBuffer* lpGameDataOutput =
            BrnGameMainFlowController::GetScriptedLoadGameDataOutput();

        // FLAG PC-platform leaf (see above): stand in for the X360's already-completed
        // module prepare + its concurrent resource thread.
        if (!mGameDataModule.Prepare(0, 0))
            return false;

        lpGameDataInput->LockForWrite();
        lpGameDataOutput->LockForRead();

        // The five gamedb paths are the X360's own literals (GamePrepare @0x823EFBD0's
        // case-2 HashString sites, BrnGameModule.cpp:1751-1755); every one hashes to an
        // entry present in the converted platform-4 GlobalTextureDictionary.bin that the
        // bundle stage above loads into pool 10.
        static const char* const KAPC_GLOBAL_TEXTURE_PATHS[5] =
        {
            "gamedb://burnout5/Playground/GlobalTextures/blobbyshadow.TextureConfig2d?ID=240931",
            "gamedb://burnout5/Playground/GlobalTextures/cloud1density.TextureConfig2d?ID=381388",
            "gamedb://burnout5/Playground/GlobalTextures/cloud1quadrant.TextureConfig2d?ID=381382",
            "gamedb://burnout5/Playground/GlobalTextures/corona_atlas.TextureConfig2d?ID=297312",
            "gamedb://burnout5/Playground/GlobalTextures/glass_fracture.TextureConfig2d?ID=440917"
        };
        const s32 KI_GLOBAL_TEXTURE_POOL = 10;   // the pool the bundle stage loaded into
        const s32 KI_DEBUG_FONT_POOL     = 0;    // "Language\\Fonts\\Default.font" went to pool 0

        bool lbDone = false;
        switch (meGamePrepareStage)
        {
        case E_GAMEPREPARESTAGE_START:
        case E_GAMEPREPARESTAGE_LOADBUNDLES:
        {
            meGamePrepareStage = E_GAMEPREPARESTAGE_LOADBUNDLES;

            // The three one-time bundle loads, in the X360's order/arguments. Pool 10 is
            // the game-wide "permanent" pool (GameDataModule's pool table); the font goes
            // to pool 0. Only shaders.bndl sets mbUseHDCache.
            lpGameDataInput->GetRequestInterface()->LoadBundle(
                &mGamePrepareReceiverQueue, 2, 10, "shaders.bndl", true);
            lpGameDataInput->GetRequestInterface()->LoadBundle(
                &mGamePrepareReceiverQueue, 1, 10, "GlobalTextureDictionary.bin", false);
            lpGameDataInput->GetRequestInterface()->LoadBundle(
                &mGamePrepareReceiverQueue, 0, 0, "Language\\Fonts\\Default.font", false);
        }
        // fall through

        case E_GAMEPREPARESTAGE_WAITBUNDLES:
        {
            meGamePrepareStage = E_GAMEPREPARESTAGE_WAITBUNDLES;

            if (mGamePrepareReceiverQueue.GetLength() < 3)
                break;

            mGamePrepareReceiverQueue.Clear();

            // ⭐ THE SIX ACQUIRES, restored 2026-08-16 (boot audit F-P2-2/F-P2-3). This
            // stage's whole job on the console is to turn the three finished bundle loads
            // into six ASYNC AcquireResource records (@0x823EFD50..0x823EFEA4) -- five
            // global textures out of pool 10 and, sixth, the debug FONT out of pool 0 --
            // and then to park stage 3 until the replies come back. The PC used to skip
            // the round trip entirely and resolve five FindResource calls inline in the
            // same pass, which (a) deleted the park, so nothing about this phase was ever
            // paced by I/O, and (b) dropped the font acquire on the floor, which is why
            // the debug font had to be brought up by an invented parallel loader
            // (CgsDev::LoadAndSetDebugFont, its own 3x4MB malloc'd pool) off the render
            // thread instead of out of the bundle this stage already loaded.
            //
            // The round trip is entirely real on PC: RequestInterface::AcquireResource
            // pushes a type-4 record, ResourceModule routes it to the pool as tag 4,
            // PoolModule::DoAcquireResourceRequest @0x828FCD48 answers it with the
            // resolved {mpResourceMemory, mpSourceEntry} pair, and
            // ProcessPoolOutputResponses maps pool tag 6 back to receiver id 4 -- the
            // console's own numbers, already calibrated against the ARTIST translation
            // table dword_820F7194.
            for (s32 liTexture = 0; liTexture < 5; ++liTexture)
            {
                lpGameDataInput->GetRequestInterface()->AcquireResource(
                    &mGamePrepareReceiverQueue, liTexture, KI_GLOBAL_TEXTURE_POOL,
                    KAPC_GLOBAL_TEXTURE_PATHS[liTexture]);
            }
            // @0x823EFE78-A4: id 5, pool 0, HashString("default") -- the debug font.
            lpGameDataInput->GetRequestInterface()->AcquireResource(
                &mGamePrepareReceiverQueue, 5, KI_DEBUG_FONT_POOL, "default");
        }
        // fall through

        case E_GAMEPREPARESTAGE_WAITACQUIRES:
        {
            meGamePrepareStage = E_GAMEPREPARESTAGE_WAITACQUIRES;

            // ⚠️ THE GATE IS FIVE, NOT SIX, and that is an asm fact, not a typo: the stage-3
            // test is `lwzx r11,[gm+0x9A06C4]; cmpwi cr6,r11,5; blt cr6 -> TAIL`
            // @0x823EFEB0-B4, even though the stage above posted SIX acquires. So the drain
            // below has to cope with the sixth reply not having landed yet -- which is
            // exactly why the console re-reads the queue rather than indexing it.
            //
            // THIS `break` IS THE PARK. It drops into the not-done tail, which pumps the
            // GameData module (and, on the console, renders the loading screen), and the
            // update thread re-enters this same stage next pass. It is the first place in
            // the whole boot where a phase actually waits on I/O rather than on a timer.
            if (mGamePrepareReceiverQueue.GetLength() < 5)
                break;

            // @0x823EFECC-0x823F003C -- drain the receiver queue. Each element is a type-4
            // AcquireResource reply; the payload is a CgsResource::Events::PoolEvent whose
            // miEventId is the 0..5 slot the request was posted under.
            renderengine::Texture* lapTextures[5] = { 0, 0, 0, 0, 0 };
            {
                const CgsModule::Event* lpEvent = 0;
                s32 liSize = 0;
                s32 liType = mGamePrepareReceiverQueue.GetFirstEvent(&lpEvent, &liSize);
                while (lpEvent != 0)
                {
                    // `cmpwi r3, 4` @0x823EFF20 -- the element TYPE, not the event id.
                    if (liType == 4)
                    {
                        // reinterpret_cast, not static_cast: CgsResource::Events::Event and
                        // CgsModule::Event are unrelated roots and the receiver queue hands
                        // out the module one (same idiom as BrnDirectorWorldMap.cpp:183).
                        const CgsResource::Events::AcquireResourceResponse* lpResponse =
                            reinterpret_cast<const CgsResource::Events::AcquireResourceResponse*>(lpEvent);

                        switch (lpResponse->miEventId)
                        {
                        case 0:
                        case 1:
                        case 2:
                        case 3:
                        case 4:
                            // `ld r11,0x18(r30); lwz rN,0(r11)` -- mpResourceMemory is the
                            // ADDRESS of the entry's main-memory slot, so the texture is one
                            // more dereference down. (The console's load is unconditional;
                            // the null test is ours, because an absent global texture on PC
                            // must reach the named assert below rather than fault here.)
                            if (lpResponse->mpResourceMemory != 0)
                            {
                                lapTextures[lpResponse->miEventId] =
                                    *reinterpret_cast<renderengine::Texture* const*>(
                                        lpResponse->mpResourceMemory);
                            }
                            break;

                        case 5:
                            // @0x823EFFC8-0x823F0000 -- the DEBUG FONT. Latch the handle pair
                            // into the module member (gm+0x99F150), build its texture state
                            // against rw's default allocator, and hand THE HANDLE to the
                            // debug manager.
                            mDebugFont.mpResourceMemory = lpResponse->mpResourceMemory;
                            mDebugFont.mpSourceEntry    = lpResponse->mpSourceEntry;
                            if (mDebugFont.mpResourceMemory != 0 &&
                                *reinterpret_cast<void* const*>(mDebugFont.mpResourceMemory) != 0)
                            {
                                rw::IResourceAllocator* lpFontAllocator =
                                    rw::ResourceAllocatorRegistry::GetDefaultAllocator();
                                CgsResource::Font* lpFont = mDebugFont;   // Font::operator* @0x823EFFE8
                                lpFont->CreateTextureState(lpFontAllocator);
                                mDebugManager.SetDebugFont(mDebugFont);
                            }
                            break;

                        default:
                            CGS_ASSERT(false, "Unexpected Event Id in BrnGameModule::GamePrepare");
                            break;
                        }
                    }

                    const CgsModule::Event* lpNext = 0;
                    liType = mGamePrepareReceiverQueue.GetNextEvent(lpEvent, &lpNext, &liSize);
                    lpEvent = lpNext;
                }
            }

            // @0x823F0048-0x823F00F0 -- the console's five named asserts. These replaced a
            // log-only status line: a missing global texture used to sail through silently
            // and only show up as a wrong-looking frame much later (boot audit F-P2-7).
            CGS_ASSERT(lapTextures[0] != 0, "lpBlobbyShadow");
            CGS_ASSERT(lapTextures[1] != 0, "lpCloudDensityTexture");
            CGS_ASSERT(lapTextures[2] != 0, "lpCloudLightingTexture");
            CGS_ASSERT(lapTextures[3] != 0, "lpCoronaAtlas != NULL");
            CGS_ASSERT(lapTextures[4] != 0, "lpGlassFractureTexture != NULL");

            if (CgsDev::Log::gpDebugPrint != 0)
            {
                *CgsDev::Log::gpDebugPrint
                    << "[GamePrepare] acquires drained: blobby=" << (lapTextures[0] != 0)
                    << " cloudDensity=" << (lapTextures[1] != 0)
                    << " cloudLighting=" << (lapTextures[2] != 0)
                    << " corona=" << (lapTextures[3] != 0)
                    << " glassFracture=" << (lapTextures[4] != 0)
                    << " debugFont=" << (mDebugFont.mpResourceMemory != 0) << "\n";
            }

            // @0x823F010C -- the argument ORDER is the console's.
            mRenderModule.PrepareAgain(lapTextures[0], lapTextures[1], lapTextures[2],
                                       lapTextures[3], lapTextures[4]);

            // @0x823F013C -- the SECOND Clear. Without it the sixth reply (and any that
            // arrive later) would still be sitting in the queue when the next phase looks.
            mGamePrepareReceiverQueue.Clear();
        }
        // fall through

        case E_GAMEPREPARESTAGE_GAMESTATE:
        {
            // ⭐ REAL since 2026-08-01 (was `[gated]`, which is why TRIGGERS.DAT never loaded).
            // X360 0x823EFBD0, LABEL_31:
            //     CreateIOBuffer<GameStateModuleIO::OutputBuffer>(mpUpdateOutputBufferStack,
            //                                                     &out, "GameState");
            //     prepared = (*(vtable+64))(&mGameStateModule, out, mpUpdateOutputBufferStack,
            //                               GameDataOutputBuffer::GetAllocatorList(gameDataOut));
            //     if (prepared) { DestroyIOBuffer(out); unlock both; return 1; }
            //     else { LockForRead(out);
            //            gameDataIn->AppendRequestInterface<3072>(*out->GetResourceRequestInterface());
            //            UnlockForRead(out); DestroyIOBuffer(out); }
            //
            // ⚠️ FLAG (PC deviation, ONE buffer instead of a per-pass scratch): the console
            // carves a FRESH GameStateModuleIO::OutputBuffer off the update-output IOBufferStack
            // on every pass, so its request queue starts empty each time and the append moves
            // exactly that pass's requests. The PC module owns ONE persistent buffer (see
            // GameStateModule::GetOutputBuffer's FLAG); its allocation site is host-only and
            // separate from the now-attested ModuleSingleBuffered base-constructor route. The
            // persistent output lifetime and request-queue reuse remain host adaptations.
            // Re-appending a persistent queue every pass would re-issue every request already
            // sent, so the queue is CLEARED after the append -- which is exactly the state the
            // console's next pass starts in. Retire this adaptation when the caller restores
            // the original per-pass IOBufferStack allocation/lifetime.
            meGamePrepareStage = E_GAMEPREPARESTAGE_GAMESTATE;

            BrnGameState::GameStateModuleIO::OutputBuffer* lpGameStateOutput =
                mGameStateModule.GetOutputBuffer();

            const bool lbGameStatePrepared = mGameStateModule.Prepare(
                lpGameStateOutput, mpUpdateOutputBufferStack, lpGameDataOutput->GetAllocatorList());

            if (!lbGameStatePrepared)
            {
                if (lpGameStateOutput != 0)
                {
                    // ⚠️ The CONST overload of GetResourceRequestInterface is the one the console
                    // calls here (X360 `OutputBu` @0x823B9798, "Not locked for reading" line 268);
                    // its non-const twin @0x8231D560 asserts the WRITE lock and would fire under
                    // this read lock. Same const-alias idiom as LoadDirectorModule's
                    // GetVaultRequestInterface read.
                    const BrnGameState::GameStateModuleIO::OutputBuffer* lpGameStateOutputRead =
                        lpGameStateOutput;
                    lpGameStateOutput->LockForRead();
                    lpGameDataInput->AppendRequestInterface<3072>(
                        *lpGameStateOutputRead->GetResourceRequestInterface());
                    lpGameStateOutput->UnlockForRead();

                    // [PC deviation, see the FLAG above] the console's per-pass buffer dies here.
                    lpGameStateOutput->LockForWrite();
                    lpGameStateOutput->GetResourceRequestInterface()->mRequestQueue.Clear();
                    lpGameStateOutput->UnlockForWrite();
                }
                break;   // still preparing -- the tail below pumps the GameData module
            }

            lbDone = true;
            break;
        }

        default:
        {
            CGS_ASSERT(false, "Got into an unknown state");   // X360 BrnGameModule.cpp:1807
            break;
        }
        }

        // @0x823F01E4/EC (done path) and @0x823F0338/40 (tail) -- the console unlocks the
        // INPUT (write) first and the OUTPUT (read) second, both times. The PC had the pair
        // reversed. It is invisible single-threaded, but it is the order the resource seam
        // needs the moment it goes concurrent (boot audit F-P2-8).
        lpGameDataInput->UnlockForWrite();
        lpGameDataOutput->UnlockForRead();

        if (!lbDone)
        {
            // ---- the not-done TAIL (loc_823F021C), run on EVERY not-done pass ------------
            // ⭐ PARTIALLY RESTORED 2026-08-16 (boot audit F-P2-4); was absent wholesale.
            //
            // The console does seven things here: creates the RendererIO buffer pair off the
            // two update stacks, runs BrnRendererModule::Update @0x82405E28 through them,
            // latches the allocator that Update publishes (GetReusableLoadingScreenAllocator
            // -> gm+0x9A0630), tells the dispatch thread to SHOW THE LOADING SCREEN and
            // republishes the disk-error byte, unlocks the GameData pair, runs
            // CheckDiskError, and destroys the pair.
            //
            // The two DISPATCH-INPUT publishes are what is restored. They matter more now
            // than they did an hour ago: stage 3 above genuinely parks on its acquires, so
            // GamePrepare really does span several passes, and this is what holds the
            // loading screen up across them instead of leaving the last frame on screen.
            //
            // [FLAG] STILL ABSENT -- the RendererIO pair, BrnRendererModule::Update, and the
            // gm+0x9A0630 allocator latch. Update's publication is
            // `SetReusableLoadingScreenAllocator(lpOutput, this + 51452)` @0x82405EC0: the
            // renderer module owns that CgsMemory::LinearMalloc as a member, and the game
            // module reads it back off the output buffer. None of the four dispatch IO
            // buffers is created on this build (see DoDispatch's banner), so the world frame
            // allocator stays the invented 512 KiB static in BrnGameMainFlowStates.cpp until
            // that pair is real. Tracked as boot-audit F-P2-4.
            // [FLAG] CheckDiskError @0x823BC798 reads the GameData output's filesystem-status
            // interface, a documented deferral in BrnGameDataModuleIO.h. The byte it would
            // act on is the one published just below, so nothing is lost but the thread spawn.
            // ⭐ THE RENDERER PAIR + THE ALLOCATOR LATCH, landed 2026-08-17 (boot audit
            // F-P2-4). @0x823F023C-2F4: create the RendererIO pair off the two update stacks,
            // run BrnRendererModule::Update through them, then read the reusable
            // loading-screen allocator back out of the output buffer and latch it at
            // gm+0x9A0630. That latch is what the world drive is supposed to use; its absence
            // is why BrnGameMainFlowStates.cpp still carries an invented 512 KiB static
            // (F-P6-12), which this unblocks.
            {
                RendererIO::InputBuffer*  lpRendererIn  = 0;
                RendererIO::OutputBuffer* lpRendererOut = 0;
                mpUpdateInputBufferStack->CreateIOBuffer(&lpRendererIn, "Render");
                mpUpdateOutputBufferStack->CreateIOBuffer(&lpRendererOut, "Render");
                if (lpRendererIn != 0 && lpRendererOut != 0)
                {
                    mRenderModule.Update(mpUpdateInputBufferStack, mpUpdateOutputBufferStack,
                                         lpRendererIn, lpRendererOut);

                    lpRendererOut->LockForRead();
                    mpReusableLoadingScreenAllocator =
                        lpRendererOut->GetReusableLoadingScreenAllocator();
                    lpRendererOut->UnlockForRead();
                }
                if (lpRendererOut != 0) mpUpdateOutputBufferStack->DestroyIOBuffer(&lpRendererOut);
                if (lpRendererIn  != 0) mpUpdateInputBufferStack->DestroyIOBuffer(&lpRendererIn);
            }

            {
                BrnGame::DispatchThreadInputBuffer* lpDispatchInput =
                    mDispatchThreadInputBufferManager.GetWriteBuffer();
                if (lpDispatchInput != 0)
                {
                    lpDispatchInput->LockForWrite();
                    lpDispatchInput->ShowLoadingScreen();            // +0x9990 := 1 @0x823F031C
                    lpDispatchInput->SetIsDiskError(mbDiskError);    // @0x823F0328
                    lpDispatchInput->UnlockForWrite();
                }
            }

            // FLAG PC-platform leaf (see above): the X360 pumps the GameData module from its
            // own resource thread; the single-threaded host has to do it here, and this is
            // the point in the pass where the locks are free -- the same point the console
            // reaches after its renderer update.
            if (mbFrameLayoutInitializedPC && mbInsideUpdatePC)
                mbPrepareResourceRequestedPC = true;
            else
                mGameDataModule.Update(lpGameDataInput, lpGameDataOutput);
        }

        return lbDone;
    }

    // @ BrnGameModule.cpp:2650 (X360 0x823F03C8) - teardown counterpart of GamePrepare: under the
    // GameData IO locks, an 11-stage resumable release that drives the per-module game releases
    // (incl. the World release with a scratch BrnWorldIO::UpdateOutputBuffer and the GameState
    // release with a scratch GameStateModuleIO::OutputBuffer, both on the update output stack).
    // [gated] same dependencies as GamePrepare. Returns done.
    bool BrnGameModule::GameRelease()
    {
        return true;
    }

    // @ BrnGameModule.cpp:1253 (X360 0x823A8BB0) - start-of-update-frame hook. The X360 body is
    // exactly two statements:
    //   1. EffectsModule::StartOfFrame -> ParticleModule::StartOfFrame (DWARF _compile/BrnGameUnity.cpp:392-395
    //      names the call; both are inline, EffectsModule.h:277 / ParticleModule.h:309), compiled to ONE store:
    //      `lis r10, 0x88 ; ori r9, r10, 0x194C ; lfs f0, flt_82001CC0 (0.0) ; stfsx f0, r11, r9`
    //      (0x823A8BB0..0x823A8BC8) -- *(this + 0x88194C) = 0.0f. The particle module is this + 0x878B40
    //      (OnEndOfUpdateFrame hands ParticleModule::EndOfFrame exactly that: `addis r3, r30, 0x88 ; addi r3, r3,
    //      -0x74C0` at 0x823DC378), so the store is its mRenderData.mfCurrentTimeStep (+0x8E0C): the clear of the
    //      sum ParticleModule::Update builds over the frame's sim sub-steps (`+= rate * step`,
    //      0x8228185C..0x82281870). Every reader of the published record -- the spark ring, the trails, the
    //      debris jobs, the motion blur -- gets the frame's step, and 0.0 on a frame that ran no sub-step.
    //   2. `BrnRendererModule::StartOfFrame(this + 15808)` (the tail call at 0x823A8BCC): it rewinds the
    //      game-side dispatch-list ring the world modules fill this frame and opens the shader-constant table's
    //      frame on its bin.
    // ⛔ CORRECTED 2026-09-25 (FX-CRASHVFX): this banner used to read the store as "the frame lookback timer ...
    // not in this layout yet" and the body dropped it. On PC the particle step then grew from boot: the debris
    // integrated 21.8 s steps (scratch/bugtest/runs/fxcrashvfx_glass/20260925_113502), the spark ring, the trails
    // and the debris each carried a first-difference workaround, and the motion blur's zero-step arm never ran.
    // The PC calls this once per UPDATE frame, ahead of that frame's sub-steps, as the console's ThreadLayout does:
    // BrnMain.cpp's EngineUpdate loop runs OnStartOfUpdateFrame -> OnCompletionOfVsyncWait -> UpdateThread
    // (GameMain's `do { ... DoUpdate_Effects ... } while (liStep < miNumSimFramesRequired)`, then the flow
    // state's Render -> DoDispatch, which publishes the record) -> OnEndOfUpdateFrame -> DispatchThread.
    void BrnGameModule::OnStartOfUpdateFrame()
    {
        renderengine::FrameProfile::Scope lFramePhaseProfile(renderengine::FrameProfile::UPDATE, renderengine::FrameProfile::UPDATE_START);
        mEffectsModule.StartOfFrame();   // *(this + 0x88194C) = 0.0f  (0x823A8BB0..0x823A8BC8)
        mRenderModule.StartOfFrame();    // the tail call (0x823A8BCC)
    }

    // ARTIST 823DBBA0. This entry receives the IThreadClass subobject at
    // GameModule+0x640 (ctor 827E5F68..70, vtable820D1498); its two stall
    // bytes are the actual mbStalled and mbPrevStalled, after that base shift.
    void BrnGameModule::OnEndOfUpdateFrame()
    {
        renderengine::FrameProfile::Scope lFramePhaseProfile(renderengine::FrameProfile::UPDATE, renderengine::FrameProfile::UPDATE_PUBLISH);
        const bool lbStalled = mbStalled || mbPrevStalled;
        mEffectsModule.ParticleModuleRef().EndOfFrame(lbStalled);

        // FLAG PC-platform leaf: rendering can run between 60 Hz GUI updates.
        // Swap reconstructs the next write buffer, including its default post-fx
        // enable byte. Republish the current display settings on every rendered
        // frame so a zero-simulation-step frame does not hide the calibration
        // card or restore effects. The handle remains a per-GUI-frame message;
        // the renderer retains it while calibration is enabled, as in ARTIST.
        {
            DispatchThreadInputBuffer* lpDisplayBuffer =
                mDispatchThreadInputBufferManager.GetWriteBuffer();
            lpDisplayBuffer->LockForWrite();
            lpDisplayBuffer->SetBrightness(miBrightness);
            lpDisplayBuffer->SetContrast(miContrast);
            lpDisplayBuffer->SetCalibrationUnfriendlyEnablePostFx(
                mbEnableCalibrationUnfriendlyPostFx);
            lpDisplayBuffer->UnlockForWrite();
        }

        mDispatchThreadInputBufferManager.Swap();

        // ⭐⭐⭐ THE GUI END-OF-FRAME NOTIFY, restored 2026-09-07 -- the SIBLING of the
        // particle hole above, named by the very same stale banner line, and found the same
        // way: `BrnGui::GuiModule::EndOfFrame @0x824F1008` was DECLARED NOWHERE, DEFINED
        // NOWHERE and CALLED BY NOTHING in this tree, which links in silence. The console
        // calls it HERE, after the dispatch swap and before the renderer's own end-of-frame,
        // exactly as the pseudocode above shows.
        //
        // It is three tail calls: GuiModule::EndOfFrame -> CustomRendererManager::EndOfFrame
        // (+311952) -> NetworkPlayerImageRenderer::SwapBuffers (+112192), and it is the ONLY
        // writer of that renderer's two ring cursors. Frozen, they sit at render=1 / copyTo=2
        // for the life of the process, so a picture RecvEvent copies into slot 2 is read back
        // from slot 1 and can never appear. Full derivation on the body in BrnGuiModule.cpp.
        mGuiModule.EndOfFrame();   // X360 @0x823DBBA0 calls it HERE, before mRenderModule's

        const u64 luPreviousCommandGeneration = mRenderModule.GetPublishedCommandGenerationPC();
        mRenderModule.EndOfFrame(lbStalled);
        CgsDev::PerfMonGpu::Swap(); // ARTIST823DC3F4, after renderer EndOfFrame.
        // FLAG PC-platform leaf: all draw snapshots follow the same completed
        // producer generation. An extra presentation preserves the last command
        // frame, while original control IO and trail EOF still run above.
        if (mRenderModule.GetPublishedCommandGenerationPC() != luPreviousCommandGeneration)
        {
            if (const BrnParticle::ParticleModule::ParticleRenderData* lpParticleRecord =
                mRenderModule.GetPublishedParticleRenderDataPC())
                mEffectsModule.ParticleModuleRef().PublishRenderCommandsPC(*lpParticleRecord);
        }
        mbPrevStalled = mbStalled;
        renderengine::PublishPresentDiagnosticsPC();
    }

    // @ 0x823BC9B8 (BrnGameModule.cpp:1533) - the resource-update worker-thread body. The X360
    // body is three statements:
    //
    //     mbResourceUpdateBusy = ( (*(*(this + 6243520) + 68))(   // GameDataModule::Update
    //                                  this + 6243520,
    //                                  *(this + 10053832),        // mpUpdateInputBufferStack
    //                                  *(this + 10053836),        // mpUpdateOutputBufferStack
    //                                  *(this + 10053840),        // the GameData INPUT buffer
    //                                  *(this + 10053844) )       // the GameData OUTPUT buffer
    //                            == 1 );
    //     CheckDiskError( this, *(this + 10053844) );
    //
    // (the thread's `this` is the game module + 1600 -- hence the `a1 - 1600` in the
    // CheckDiskError call and the 1600-byte-shifted member offsets; add it back and the four
    // arguments are exactly gm+10055432/36/40/44, i.e. the two update IO buffer stacks and THE
    // SAME GameData input/output pair BrnGameModule::Prepare stage 3 created and every
    // LoadXxxModule / GamePrepare / LoadingScriptedState brackets. There is no second pair and
    // no hand-off: the console synchronises the two threads purely with the IOBuffer
    // read/write locks.)
    //
    // ⭐ THIS IS THE PUMP. Nothing else services the GameData request queue: the requests every
    // module stages into the input buffer are drained, dispatched and answered here. The X360
    // runs it continuously on its own thread from BrnGameModule::Prepare onwards, which is why
    // a module's Prepare can stage a request at boot loading stage 3 and see the reply a frame
    // later.
    //
    // FLAG PC-platform leaf: the single-threaded PC host has no resource thread, so GameMain
    // calls this once per simulation sub-step, right after the flow state's Update (i.e. after
    // this sub-step's requests are staged and their IO locks released). Same work, same
    // buffers, same order -- serialised instead of concurrent.
    //
    // [deferred] CheckDiskError: the console's dirty-disc watch reads the GameData output's
    // filesystem-status interface, which is not reconstructed (the output buffer's status
    // member is a documented deferral in BrnGameDataModuleIO.h).
    // ============================================================================================
    // FLAG PC-platform leaf: publish the offline junkyard response at the existing
    // GUI subscription boundary. The filter is ARTIST GetListOfPlayerSelectableVehicles
    // 0x82376500's offline arm; flags/count are ProcessGameEvents case 88, and GUI
    // transport is TranslateGameActionsToGuiEvents cases 182/184. The online car-select
    // manager has a separate class-limit policy and is not driven by this host path.
    void BrnGameModule::PublishCarSelectionToGui()
    {
        // This stand-in publishes the junkyard's 406/412 pair. Online options
        // also observes 412, but binds cache 64 before requesting its list with 409.
        const bool lbListening = mGuiModule.IsScreenFlowObserving(406)
                              && mGuiModule.IsScreenFlowObserving(412);
        if (!lbListening)
        {
            mbCarSelectionPublished = false;   // re-arm for the next entry
            return;
        }
        if (mbCarSelectionPublished || mpGuiInputBuffer == 0)
            return;

        const CgsID lPlayerCarId = mGameStateModule.GetActivePlayerCarId();
        if (lPlayerCarId == 0)
            return;   // the junkyard entry has not committed a car yet; try again next sub-step

        mbCarSelectionPublished = true;

        // ---- GUI event 406 (GuiPlayerInfoResponse, 0x40 bytes; car id at +0x20) --------------
        // ⭐ [issue #3 wave 2026-09-15] byte +0x38 is the "car needs repair" word the livery
        // screen latches (CarSelectLivery::HandlePlayerInfoResponse @0x824C8758, `lbz 0x38`):
        // set, it disables the whole modify surface, fades the screen and posts the
        // CAR_REPAIR_REQUIRED ticker. The console computes it in ProcessGameEvents @0x823A0A18
        // case 81, right after PlayerInfo::Construct and before posting game action 182 (which
        // TranslateGameActionsToGuiEvents @0x823E9CE0 case 182 forwards as GUI 406, seven words
        // plus this byte):
        //     v547 = Profile::FindCar(profile, carId)
        //            ? (Profile::GetPlayerBaseDeformAmount(profile, carId) != 0.0) : 1;
        // It was left ZERO here, so a damaged car's paint screen was fully interactive.
        {
            u8 lu8CarNeedsRepair = 1;
            {
                BrnProgression::Profile* lpRepairProfile =
                    mGameStateModule.GetProgressionManager()->GetProfile();
                if (lpRepairProfile->FindCar(lPlayerCarId) != 0)
                {
                    lu8CarNeedsRepair =
                        (lpRepairProfile->GetPlayerBaseDeformAmount(lPlayerCarId) != 0.0f) ? 1 : 0;
                }
            }
            u8 laRecord[0x40];
            std::memset(laRecord, 0, sizeof(laRecord));
            *reinterpret_cast<CgsID*>(&laRecord[0x20]) = lPlayerCarId;
            laRecord[0x38] = lu8CarNeedsRepair;
            mpGuiInputBuffer->GetGuiEvents()->AddEvent(
                reinterpret_cast<const CgsModule::Event*>(laRecord), 406,
                static_cast<s32>(sizeof(laRecord)));
        }

        // GUI 412's native-width record retains the console offsets: ids/count,
        // driven bits at +0x408, damaged-on-unlock bits at +0x418, garage total at +0x428.
        struct CarSelectionResponse
        {
            Array<CgsID, 128> mCars;
            CgsContainers::BitArray<128> mDriven;
            CgsContainers::BitArray<128> mDamagedOnUnlock;
            s32 miCarsTotal;
        };
        static_assert(sizeof(CarSelectionResponse) == 0x430, "GUI 412 record size");
        CarSelectionResponse lSelection;
        lSelection.mCars.Clear();
        lSelection.mDriven.Prepare();
        lSelection.mDamagedOnUnlock.Prepare();
        auto* lpProgression = mGameStateModule.GetProgressionManager();
        auto* lpProfile = lpProgression->GetProfile();
        const auto* lpVehicles = mGameStateModule.GetVehicleList();
        lSelection.miCarsTotal = lpProgression->GetMaxCarCount();
        for (s32 liVehicle = 0; liVehicle < lpVehicles->GetVehicleCount(); ++liVehicle)
        {
            const auto* lpVehicle = lpVehicles->GetVehicleData(liVehicle);
            if (!lpVehicle->IsTrophyCar() || lpVehicle->IsLiveryColour())
                continue;
            const auto* lpCar = lpProfile->FindCar(lpVehicle->GetId());
            if (!lpCar || (lpCar->GetUnlockType() == BrnProgression::CarData::E_UNLOCK_TYPE_SPONSOR &&
                lpProgression->GetProgressionRank() < lpVehicle->GetUnlockRank()))
                continue;
            const u32 luIndex = lSelection.mCars.GetLength();
            lSelection.mCars.Append(lpVehicle->GetId());
            if (lpCar->GetUnlockDeformationAmount() > 0.0f)
                lSelection.mDamagedOnUnlock.SetBit(luIndex);
            const auto* lpLivery = lpProfile->GetChosenLiveryDataForBaseCar(lpVehicle->GetId());
            if (lpLivery && lpLivery->mfDistanceDriven > 0.0f)
                lSelection.mDriven.SetBit(luIndex);
        }
        mpGuiInputBuffer->GetGuiEvents()->AddEvent(
            reinterpret_cast<const CgsModule::Event*>(&lSelection), 412, sizeof(lSelection));

        // GUI 413 now answers the real case-82 livery request through game action 183.

        if (CgsDev::Log::gpDebugPrint != 0)
        {
            *CgsDev::Log::gpDebugPrint
                << "[CarSelectBridge] published GUI 406 + 412 for car id "
                << static_cast<u32>(lPlayerCarId) << " (" << lSelection.mCars.GetLength() << " selectable cars)\n";
        }
    }

    void BrnGameModule::ResourceUpdateThread(Mutex* /*lpMutex*/)
    {
        if (mbFrameLayoutInitializedPC)
        {
            if (mbInsideUpdatePC)
            {
                mbResourceRequestedPC = true;
                return;
            }
            const bool lbRuntimeRequest = mbResourceRequestedPC;
            const bool lbPrepareRequest = mbPrepareResourceRequestedPC;
            mbResourceRequestedPC = mbPrepareResourceRequestedPC = false;
            // Native zero-step frames must not produce another reply before
            // InternalBaseStreamer consumes the previous simulation step's one.
            if (!lbRuntimeRequest)
            {
                if (lbPrepareRequest)
                {
                    renderengine::FrameProfile::Scope lResourceProfile(renderengine::FrameProfile::UPDATE, renderengine::FrameProfile::UPDATE_RESOURCE);
                    mGameDataModule.Update(BrnGameMainFlowController::GetScriptedLoadGameDataInput(),
                                          BrnGameMainFlowController::GetScriptedLoadGameDataOutput());
                }
                return;
            }
        }
        renderengine::FrameProfile::Scope lResourceProfile(renderengine::FrameProfile::UPDATE, renderengine::FrameProfile::UPDATE_RESOURCE);
        BrnResource::GameDataIO::InputBuffer*  lpGameDataInput =
            BrnGameMainFlowController::GetScriptedLoadGameDataInput();
        BrnResource::GameDataIO::OutputBuffer* lpGameDataOutput =
            BrnGameMainFlowController::GetScriptedLoadGameDataOutput();

        // ---- X360 GuiModule::Prepare stage 14, driven from here -------------------------
        // BrnGui::WorldDataController::Prepare @0x82516770 stages its resource requests into
        // the GameData request interface and reads the replies out of its own receiver queue.
        // The console runs it from BrnGui::GuiModule::Prepare, which the module scheduler
        // calls with THIS SAME buffer pair; the PC's GuiModule::Prepare runs at Construct
        // time, long before the GameData IO exists, so the stage is driven here -- the one
        // place the pair is live and pumped -- immediately BEFORE the pump, so a request
        // staged this sub-step is serviced in the same call and its reply is waiting on the
        // next. (Same "stage then pump" order as GamePrepare's own stages.)
        // Stops re-entering once the machine reports done; while a stage is parked on a
        // request no PC producer answers it only re-checks its queue (it does not re-issue),
        // which is the console's own arm -- see the banner in BrnGuiWorldDataController.cpp.
        //
        // ⭐⭐ [event-starts wave 2026-08-27] AND THE SECOND MACHINE, WorldDataController::Prepare2
        // @0x82516CB8 -- the ONLY writer of the controller's mpProgressionData / mpStreetData, and
        // therefore the thing that makes GetEventInfoFromEventId answer with a real RaceEventData
        // instead of NULL (the sat-nav's `lpRaceEventData` assert, BrnSatNavRenderer.cpp:1307).
        //
        // ⛔ THE TWO MACHINES SHARE ONE RECEIVER QUEUE, so exactly one of them is pumped per
        // sub-step. THE ORDER IS THE CONSOLE'S OWN AND IS NO LONGER A WORKAROUND (corrected
        // 2026-08-27, challenge-list wave): Prepare runs to COMPLETION first, then Prepare2.
        //
        // ⚠️ WHAT THIS REPLACED, AND WHY IT HAD TO GO. The previous form handed the queue to
        // Prepare2 the moment Prepare merely PARKED at PREPARING_ACQUIRING_STREET_DATA, because
        // no PC producer answered its GetFreeburnChallengeList and parking was permanent. That
        // producer LANDED IN THIS WAVE (GameDataModule Prepare stage 10 +
        // ProcessGetFreeburnChallengeListRequest, id 53), so Prepare now parks at stage 9 only
        // until the reply arrives -- and the old "parked" test would have handed the queue away
        // in exactly that window and let Prepare2's ProgressionData acquire consume the reply
        // meant for Prepare. Each stage takes "the one event on the queue" WITHOUT checking what
        // it is, so that is not untidy, it is a cross-bind. Gating on mbWorldDataPrepared instead
        // makes the hand-off happen once, after Prepare has genuinely finished.
        //
        // ⚠️ AND PREPARE2 NEEDS A SECOND, INDEPENDENT PRECONDITION -- the root cause of the
        // "[GuiWorldData] Prepare2 done: mpProgressionData bound = 0" line this wave inherited.
        // Prepare2 does not stream anything: it ACQUIRES "ProgressionData" and "StreetData" BY
        // NAME out of pool 5, and the two bundles that put them there ("Progression.dat",
        // "STREETDATA.DAT") are loaded by the GAME-STATE lane's own second pass,
        // GameStateModule::Prepare2, which runs from the scripted-load flow much later than this
        // thread starts. An acquire for an absent resource is ANSWERED (with a null memory
        // pointer), not queued -- so running Prepare2 early does not retry: it completes, binds
        // NOTHING, and latches meState2 == 5 for the rest of the session, which is exactly what
        // the boot log showed (GUI Prepare2 done at log line 240; ProgressionManager LOADED at
        // line 518). IsPrepare2Complete() is the PC observer that says both bundles are resident.
        // DELETE-WHEN the module scheduler's real Prepare2 pass orders the two lanes (the console
        // has no such gate because the scheduler runs GameState's Prepare2 before the GUI's).
        if (!mbWorldDataPrepared && lpGameDataInput != 0)
        {
            lpGameDataInput->LockForWrite();
            mbWorldDataPrepared = mGuiModule.PrepareWorldData(lpGameDataInput);
            lpGameDataInput->UnlockForWrite();

            // [diagnostic, one-shot] the keystone this whole car-select campaign turned on:
            // print the vehicle list the GUI side ended up holding, from the GUI side.
            static bool s_bLoggedGuiVehicleList = false;
            if (!s_bLoggedGuiVehicleList
                && mGuiModule.GetWorldDataController().GetVehicleList() != 0)
            {
                s_bLoggedGuiVehicleList = true;
                *CgsDev::Log::gpDebugPrint
                    << "[GuiWorldData] mpVehicleList = "
                    << const_cast<void*>(static_cast<const void*>(
                           mGuiModule.GetWorldDataController().GetVehicleList()))
                    << " (" << mGuiModule.GetWorldDataController().GetVehicleList()->GetVehicleCount()
                    << " entries), state "
                    << static_cast<s32>(mGuiModule.GetWorldDataController().GetState()) << "\n";
            }

            // [diagnostic, one-shot] NOT IN THE X360 BINARY. Prepare reaching
            // WFPLAYERCARCOLOURS (11) is what un-gates the five meState-asserting accessors --
            // that is the whole point of the challenge-list wave -- but FOUR of them go straight
            // through mpTriggerData with no null path of their own, and the stage-2/3
            // "TriggerData" acquire is ANSWERED even when Triggers.dat is not yet resident. So
            // report which pointers the machine actually ended up holding, not just that it
            // finished. DELETE-WHEN the acquire reports a miss as a miss.
            static bool s_bLoggedGuiWorldDataDone = false;
            if (!s_bLoggedGuiWorldDataDone && mbWorldDataPrepared && CgsDev::Log::gpDebugPrint != 0)
            {
                s_bLoggedGuiWorldDataDone = true;
                const BrnGui::WorldDataController& lrWdc = mGuiModule.GetWorldDataController();
                *CgsDev::Log::gpDebugPrint
                    << "[GuiWorldData] Prepare done: state " << static_cast<s32>(lrWdc.GetState())
                    << ", triggerData bound = " << (lrWdc.HasTriggerData() ? 1 : 0)
                    << ", carColours bound = " << (lrWdc.HasPlayerCarColours() ? 1 : 0)
                    << ", challengeList = "
                    << const_cast<void*>(static_cast<const void*>(lrWdc.GetFreeburnChallengeList()))
                    << "\n";
            }
        }
        else if (!mbWorldData2Prepared && lpGameDataInput != 0
                 && mGameStateModule.IsPrepare2Complete())
        {
            lpGameDataInput->LockForWrite();
            mbWorldData2Prepared = mGuiModule.PrepareWorldData2(lpGameDataInput);
            lpGameDataInput->UnlockForWrite();

            // [diagnostic, one-shot] NOT IN THE X360 BINARY -- the line that proves the GUI lane's
            // progression binding took, which is the precondition for every event icon on the map.
            // DELETE-WHEN the sat-nav event-icon path has a regression test behind it.
            static bool s_bLoggedGuiProgression = false;
            if (!s_bLoggedGuiProgression && mbWorldData2Prepared
                && CgsDev::Log::gpDebugPrint != 0)
            {
                s_bLoggedGuiProgression = true;
                *CgsDev::Log::gpDebugPrint
                    << "[GuiWorldData] Prepare2 done: mpProgressionData bound = "
                    << (mGuiModule.GetWorldDataController().HasProgressionData() ? 1 : 0)
                    << ", state2 "
                    << static_cast<s32>(mGuiModule.GetWorldDataController().GetState2())
                    << ", state " << static_cast<s32>(mGuiModule.GetWorldDataController().GetState())
                    << "\n";
            }
        }

        // ⭐ THE STALL PUBLISH, restored 2026-08-16 (boot audit F-P3-3). @0x823BCA18-38:
        //     ret = (gameDataModule->vtable+0x44)(...);          // the Update above
        //     cmpwi cr6, r3, 1; li r10,1; beq; li r10,0
        //     stbx r10, r31, 0x99FFE8                            // (gm+1600)+0x99FFE8
        //                                                        //  == gm+0x9A0628
        // gm+0x9A0628 is the byte ConstructUpdateSetFromFsm turns into update-set bit 0x400,
        // the STALL bit. The PC threw the return value away and never wrote the member, so
        // the whole stall gate was dead: nothing downstream could ever tell that the
        // streamer had not caught up. The value is "the resource pump is still busy" --
        // Update returning 1 -- and it is republished every pass, not latched.
        mbStalled = mGameDataModule.Update(lpGameDataInput, lpGameDataOutput);
    }

    // @ BrnGameModule.cpp:1221 - the render/dispatch thread body. The threaded D3D
    // thread-ownership handshake and the per-module dispatch are reconstructed with the
    // threading core; for the boot loading screen this drives one render through the renderer
    // module.
    void BrnGameModule::DispatchThread()
    {
        // X360 DoDispatch @0x823DC458 runs DebugManagerRender between the module dispatch-list
        // generation and the ExternallyV copy -- i.e. the overlay QUEUEING happens on the
        // dispatch side, before the renderer consumes the frame. Same order here: queue first,
        // then render. (The queued text is flushed by DebugManager::Render at the renderer's
        // overlay point -- see the note at the end of DebugManagerRender.)
        renderengine::FrameProfile::CycleScope lDispatchProfile(renderengine::FrameProfile::DISPATCH);

        // ARTIST 823A8B6C: Update_Dispatch runs on the dispatch thread before renderer consumption.
        mReplayModule.Update_Dispatch();

        // The console dispatch thread hands the renderer the manager's READ buffer (the
        // frame the update side just published via OnEndOfUpdateFrame's swap).
        const DispatchThreadInputBuffer* lpRead = mDispatchThreadInputBufferManager.GetReadBuffer();
        // ARTIST 823A8B70..88 supplies the real effects owner. Render invokes
        // its original callback after GDL conversion/sorting on this control IO.
        mRenderModule.Render(&mEffectsModule, lpRead);
    }

    // ARTIST 823BCB88. The caller holds fresh RendererIO output for read;
    // all debug commands are recorded during the original producer phase.
    void BrnGameModule::DebugManagerRender(RendererIO::OutputBuffer* lpRendererOutput)
    {
        CgsDev::PerfMonCpu::AddPIXCounters();
        CgsGraphics::Im3dRenderBuffer* const lpIm3dDebug = lpRendererOutput->GetIm3dDebugRenderBuffer();
        CgsGraphics::Im2dRenderBuffer* const lpIm2dDebug = lpRendererOutput->GetIm2dDebugRenderBuffer();

        // 3. the gate (@0x823BCBCC-C20): the debug font must have arrived (GamePrepare's id-5
        // acquire writes the pair; both words NULL = not yet).
        if (mDebugFont.mpResourceMemory == 0 && mDebugFont.mpSourceEntry == 0)
            return;
        if (lpIm3dDebug == nullptr || lpIm2dDebug == nullptr)
            return;

        // 4. the fps state (@0x823BCC24-D44).
        const u32 lu32Now  = CgsSystem::GetSystemTimerBaseTime();
        const u32 lu32Freq = CgsSystem::GetSystemTimerFrequency();

        const f32 lfThreeFrameSeconds =
            static_cast<f32>(lu32Now - mau32DebugFpsFrameStamps[mu8DebugFpsFrameStampIndex]) /
            static_cast<f32>(lu32Freq);
        const f32 lfCurrentFps = 1.0f / (lfThreeFrameSeconds * 0.33333334f);   // flt_820065E0

        mfDebugFpsSampleCount = mfDebugFpsSampleCount + 1.0f;
        mfDebugFpsAccumulator = mfDebugFpsAccumulator + lfCurrentFps;
        mau32DebugFpsFrameStamps[mu8DebugFpsFrameStampIndex] = lu32Now;
        mu8DebugFpsFrameStampIndex = static_cast<u8>((mu8DebugFpsFrameStampIndex + 1) % 3);

        const f32 lfWindowSeconds =
            static_cast<f32>(lu32Now - mu32DebugFpsAverageWindowStamp) / static_cast<f32>(lu32Freq);
        if (lfWindowSeconds > 60.0f)   // flt_82004C6C
        {
            mu32DebugFpsAverageWindowStamp = lu32Now;
            mfDebugFpsAverage     = mfDebugFpsAccumulator / mfDebugFpsSampleCount;
            mfDebugFpsAccumulator = 0.0f;
            mfDebugFpsSampleCount = 0.0f;
        }

        // 5. queue the overlay under the debug lock (@0x823BCD48: Enter(dword_83019264) -- the
        // same per-manager section ThreadSafeAquire brackets).
        CgsDev::DebugManager* lpDebugManager = CgsDev::DebugManager::ThreadSafeAquire();

        lpDebugManager->RenderBuildInfo();

        // highlight = clamp(1 - secondsSinceAverage/30, 0, 1) (@0x823BCE7C-EE8, flt_82037210).
        f32 lfAverageHighlight = 1.0f - lfWindowSeconds * 0.033333335f;
        if (lfAverageHighlight < 0.0f) lfAverageHighlight = 0.0f;
        if (lfAverageHighlight > 1.0f) lfAverageHighlight = 1.0f;

        lpDebugManager->RenderFrameRateColouredWithAverage(
            lfCurrentFps, mfDebugFpsAverage,
            0xFF00FF00u /*high: green*/, 0xFF0000FFu /*low: red*/, 0xFF00FFFFu /*mid: yellow*/,
            60.0f, 30.0f,   // flt_82004C6C / flt_82004F5C
            "over last minute", lfAverageHighlight, mbDebugSimulationIsRealtime);

        lpDebugManager->RenderMemory();

        // ARTIST 823BCD48..CF14 inlines the general affine inverse of the
        // director module's actual graphics view, then records both debug banks.
        const CgsGraphics::Camera& lrCamera = mDirectorModule.GetGraphicsCameraForDebug();
        const Matrix44& lrView = lrCamera.mView;
        Matrix44Affine lView;
        lView.xAxis = Vector3{lrView.xAxis.x, lrView.xAxis.y, lrView.xAxis.z, lrView.xAxis.w};
        lView.yAxis = Vector3{lrView.yAxis.x, lrView.yAxis.y, lrView.yAxis.z, lrView.yAxis.w};
        lView.zAxis = Vector3{lrView.zAxis.x, lrView.zAxis.y, lrView.zAxis.z, lrView.zAxis.w};
        lView.wAxis = Vector3{lrView.wAxis.x, lrView.wAxis.y, lrView.wAxis.z, lrView.wAxis.w};
        const Matrix44Affine lInverseView = rw::math::vpu::Inverse(lView);
        lpDebugManager->Render(lrCamera.GetViewProjectionMatrix(), lInverseView.wAxis,
                               lpIm3dDebug, lpIm2dDebug);

        CgsDev::DebugManager::ThreadSafeRelease(lpDebugManager);
    }

    // @ BrnGameModule.cpp:3916 - clear the whole game-module object, then stamp each owned
    // module's memory region with 0x7FFFFFFF so any read of un-prepared module memory is caught.
    // NOTE: the memset uses the FULL X360 object size (0x9A1300); it overflows this
    // incrementally-populated layout, so it's only safe once the layout is complete - debug-only,
    // not called on the boot/loading path.
    void BrnGameModule::DebugMemoryInit(BrnGameModule* lpData)
    {
        std::memset(lpData, 0, 0x9A1300);
        DebugSetMemoryToInt(&lpData->mGameStateModule, 292368, 0x7FFFFFFF);
        DebugSetMemoryToInt(&lpData->mGuiModule, 1629392, 0x7FFFFFFF);
        DebugSetMemoryToInt(&lpData->mNetworkModule, 866560, 0x7FFFFFFF);
        DebugSetMemoryToInt(&lpData->mInputModule, 5096, 0x7FFFFFFF);
    }



    // @ BrnGameModule.cpp:1845 - the per-frame update spine.
    //
    // Latches this frame's simulation-step bounds (forcing a single step when single-stepping
    // frames), begins the frame-rate manager's frame, releases the input read-lock, ticks the
    // debug manager and polls the step-frame request. Then it runs the active flow state's
    // Update() once per required simulation sub-step (recreating the static IO buffers between
    // steps), and finally the active state's Render() once for the frame, before tearing down
    // this frame's GUI/director IO buffers. Returns false (the X360 returns 0).
    //
    // The mCpuMonitors.* handles are the CPU perfmon slots the original brackets each region
    // with; the field names follow the BrnCpuMonitors declaration order at the X360 offsets.
    bool BrnGameModule::GameMain()
    {
        using namespace CgsDev;

        PerfMonCpu::StartMonitor(mCpuMonitors.miUT_TotalUpdate);

        mi8ActualFrameRateMinStepsThisFrame = mi8FrameRateMinSteps;
        mi8ActualFrameRateMaxStepsThisFrame = mi8FrameRateMaxSteps;
        CgsSystem::EFrameRateManagerType leFrameRateType = meFrameRateManagerType;
        if (mbSteppingFrames)
        {
            leFrameRateType = CgsSystem::E_FRAMERATEMANAGER_SINGLE;
            mi8ActualFrameRateMinStepsThisFrame = 1;
            mi8ActualFrameRateMaxStepsThisFrame = 1;
        }

        CGS_ASSERT(!_lbForceAssert, "!_lbForceAssert");

        mFrameRateManager.StartUpdateFrame(leFrameRateType, false);
        UnlockInputForRead();

        PerfMonCpu::StopMonitor(mCpuMonitors.miUT_TotalUpdate);

        // FLAG: ARTIST 0x823CB498 brackets DebugManager::Update with the monitor at
        // mCpuMonitors+0x48 (=miUT_DebugManager), not +0x4C (miUT_RenderAll). Fixed.
        PerfMonCpu::StartMonitor(mCpuMonitors.miUT_DebugManager);
        // ⭐ TIMER CORRECTED 2026-08-17 (boot audit F-P3-15). The old note said this reads
        // *(gm+10095356) * *(gm+10095360) -- "the SIM timer's mfRate * mfScaleCurrent" -- and
        // the code duly read mSimTimer. Both were wrong, by one timer.
        //
        // @0x823CB584-98 the console reads the timer based at gm+0x9A0AD4, i.e. +0xC/+0x10 of
        // it = 0x9A0AE0/0x9A0AE4. And gm+0x9A0AD4 is 10095316, which Construct's own step-9
        // note names as THE GAME TIMER (the sim timer is 10095344 = 0x9A0AF0). The offsets
        // that were cited here, 10095356/10095360, are 28 bytes further on -- inside the SIM
        // timer -- so the comment named one timer, the asm another, and the code followed the
        // comment.
        //
        // It is not cosmetic: the two timers diverge whenever the sim is paused or scaled
        // (mbSimPaused, the 0x1 update-set bit, and the step/play frame controls all move the
        // SIM timer and leave the GAME timer running). Reading the sim timer makes the debug
        // overlay freeze with the simulation instead of continuing to tick -- which is the
        // opposite of what a debug overlay is for, and exactly the state you are in when you
        // most want it.
        mDebugManager.Update(mGameTimer.GetRate() * mGameTimer.GetScaleCurrent());
        // FLAG PC-platform leaf: opt-in maximum command at the original debug
        // callback phase (ARTIST823CB598), before flow/vehicle physics updates.
        static const bool sbMaxPresetProbePC = (std::getenv("BRN_PLAYTEST_MAX_DEFORM_AT") != nullptr);
        if (sbMaxPresetProbePC)
            BrnPhysics::Deformation::DeformationManager::RunMaxPresetProbePCDebugUpdate(
                mGameTimer.GetRate() * mGameTimer.GetScaleCurrent());
        UpdateRequestDoStepFrame();
        PerfMonCpu::StopMonitor(mCpuMonitors.miUT_DebugManager);

        PerfMonCpu::StartMonitor(mCpuMonitors.miUT_TotalUpdate);
        PerfMonCpu::SetNumIterationsTaken(miNumSimFramesRequired);
        sbSimUpdateComplete = 0;
        if (miNumSimFramesRequired > 0)
        {
            s32 liStep = 0;
            do
            {
                // ARTIST 0x823CB498 brackets Create/DestroyStaticIOBuffers with the monitor at
                // mCpuMonitors+0x10 -- under the corrected 40-field layout (no +0x08 hole,
                // miUT_Replay @+0x40) that handle is miUT_GameState.
                PerfMonCpu::StartMonitor(mCpuMonitors.miUT_GameState);
                CreateStaticIOBuffers();

                // FLAG PC-platform leaf: GuiModule owns its output queue. Match the
                // original fresh per-call output boundary, including skipped GUI frames.
                if (mGuiModule.IsPrepared())
                    mGuiModule.GetGuiOutQueue()->Clear();

                mFrameRateManager.miPrevNumSimulationStepsRequired = liStep + 1;
                PerfMonCpu::StopMonitor(mCpuMonitors.miUT_GameState);

                PerfMonCpu::StartMonitor(mCpuMonitors.miUT_EachUpdate);

                // ⭐ THE FRAME TIMESTEP SNAPSHOT -- before any leg reads a timestep. The console's
                // DoUpdate @0x823F0AF8 captures its update-set at 0x823F0B28, then calls BridgeTimers
                // @0x823BD150 at 0x823F0DE4 before DoUpdate_InputPreWorld (0x823F0F58): the
                // request accumulator is reset and TimerStatusInterface::StoreTimers @0x828D7518
                // snapshots both timers into mTimerStatusInterface -- the snapshot the world leg
                // integrates with (DoUpdate_World 0x823E8C78..0x823E8C84) and the director reads.
                // The timers were last moved by UpdateTimers at the END of the previous sub-step
                // (below), so a time-scale request the director made last step reaches the world
                // this step, as on the console. NULL: the director input does not exist yet on
                // this build; DoUpdate_Director copies this snapshot into it (see BridgeTimers).
                // CORRECTED 2026-09-25 (FX-DIRECTOR2) -- this ran inside DoUpdate_Director, after
                // a mid-step UpdateTimers, which put every director request one step late.
                const bool lbRunFullModuleCascade = (mpNetworkOutputBuffer != 0);
                BrnUpdateSet lFullModuleUpdateSet = static_cast<BrnUpdateSet>(0);
                if (lbRunFullModuleCascade)
                    lFullModuleUpdateSet = ConstructUpdateSetFromFsm();

                if (lbRunFullModuleCascade)
                    BridgeTimers(0);

                BrnGameMainFlowController::EMainGameFlowState leState = mMainFlowStateMachine.GetCurrentState();
                bool lbInputPreWorldFilledPC = false;
                u32 luStartPressedPort = CgsInput::KU_NUMBER_OF_PADS;

                // ⭐ [FX-RUMBLE3 2026-09-24, crash-parity G10-D4] THE INPUT PRE-WORLD LEG -- the first
                // leg of the console's update step, and the one that carries the game's rumble requests
                // to the pads. It has exactly two console callers (the dossier's xrefs_to):
                //   DoUpdate @0x823F0AF8 at 0x823F0F58 -- unconditional, first leg, before NetworkPreSim;
                //     DoUpdate runs from MainGameFlowStateInGame::Update and from LoadingScriptedState::
                //     Update once its load stage reads 8 (0x823F22F4 `cmpwi r11,8` -> 0x823F2304);
                //   LoadingScriptedState::Update @0x823F22D8 at 0x823F26F4 -- the partial spine it runs
                //     for load stages below 8, first leg after ConstructUpdateSetFromFsm.
                // So it runs in the in-game state and in every loading-scripted state, whatever the load
                // stage (the network buffer's gate below additionally needs stage 8). Arguments as the
                // console loads them: the update input/output buffer stacks and the input module's
                // output buffer (the PC keeps that one as mPcInputOutputBuffer). Preserve the
                // actual selected word for the original post-world bind and GUI143 producer.
                if (lbRunFullModuleCascade)
                {
                    // FLAG PC-platform leaf: these results live in a persistent buffer here;
                    // the original frame-owned OutputBuffer is freshly constructed each step.
                    // Last-step consumers have finished before this new producer pass.
                    mPcInputOutputBuffer.LockForWrite();
                    mPcInputOutputBuffer.GetBindResultQueue()->Clear();
                    mPcInputOutputBuffer.GetUnbindResultQueue()->Clear();
                    mPcInputOutputBuffer.UnlockForWrite();
                    luStartPressedPort = DoUpdate_InputPreWorld(
                        mpUpdateInputBufferStack, mpUpdateOutputBufferStack, &mPcInputOutputBuffer);
                    lbInputPreWorldFilledPC = !mbDiskError;
                }

                // THE NETWORK PRE-SIMULATION LEG. Console DoUpdate order: DoUpdate_InputPreWorld,
                // then this, then DoUpdate_GameStatePreWorld; unconditional whenever DoUpdate runs,
                // which on this build is exactly when the sub-step has a network output buffer
                // (CreateStaticIOBuffers). InputPreWorld publishes this sub-step's pad record
                // before this network leg and the GameState controller bridge.
                if (lbRunFullModuleCascade)
                {
                    DoUpdate_NetworkPreSim(mpUpdateInputBufferStack, mpUpdateOutputBufferStack,
                                           &mPcInputOutputBuffer, mpNetworkOutputBuffer,
                                           lFullModuleUpdateSet);
                    DoUpdate_GameStatePreWorld(mpUpdateInputBufferStack, mpUpdateOutputBufferStack,
                                               &mPcInputOutputBuffer, mpNetworkOutputBuffer,
                                               mGameStateModule.GetOutputBuffer(),
                                               lFullModuleUpdateSet);
                }

                if (leState != BrnGameMainFlowController::E_MGS_INVALID)
                {
                    MainGameFlowState* lpState = mMainFlowStateMachine.GetState(leState);
                    lpState->Update();
                    if (leState == BrnGameMainFlowController::E_MGS_IN_GAME)
                    {
                        // ARTIST823E8D70..823E8DA0, after the selected world's producer.
                        const BrnWorldIO::UpdateOutputBuffer* lpWorldOutput = mpWorldUpdateOutputBuffer;
                        lpWorldOutput->LockForRead();
                        mbWorldStreamingRequestedStall =
                            !lpWorldOutput->GetWorldEntityStatusInterface()->GetImmediateStreamed();
                        lpWorldOutput->UnlockForRead();
                    }
                }

                // ARTIST823F1554..156C: the same selected word feeds InputPostWorld
                // after the world's producer and before GUI. The existing helper owns the
                // mapping/bind requests; next PreWorld publishes its actual bind result.
                if (lbRunFullModuleCascade)
                    DoUpdate_InputPostWorld(mpUpdateInputBufferStack, mpUpdateOutputBufferStack,
                                           mGameStateModule.GetOutputBuffer(), mpWorldUpdateOutputBuffer,
                                           luStartPressedPort);

                // ---- the RESOURCE tick (FLAG PC placement: the console's own thread) -------
                // The X360 runs BrnGameModule::ResourceUpdateThread @0x823BC9B8 concurrently
                // with this loop; the single-threaded host serialises it here, immediately
                // after the flow state has staged this sub-step's requests and released the
                // GameData IO locks. Without it NOTHING drains the GameData request queue
                // outside GamePrepare, and any module Prepare that waits on a resource reply
                // (DirectorModule stage 3 = WorldMap::LoadData) wedges the loading flow.
                ResourceUpdateThread(0);
                // (The TIMER tick, UpdateTimers @0x823BCFD0, is NOT here any more: it runs at the
                //  end of the sub-step, after DoUpdate_NetworkPostSim -- the console's 0x823F1CFC.
                //  Boot audit F-P3-13's position note is retired there, with the measurement.)
                // ---- the DIRECTOR's pre-GUI passes (X360 module-scheduler order) ----------
                // PreSceneQueryUpdate + Update. The module publishes its finalised camera into
                // mpDirectorOutputBuffer, which stays alive through this frame's Render.
                if (lbRunFullModuleCascade)
                    DoUpdate_Director(false);

                // ARTIST DoUpdate_GUI823F0758 runs only in the full cascade.
                // Boot and the below-stage8 partial route own their GUI/time seats.
                // ⭐ FRAME-STEP GUARD, 2026-08-16 (boot audit F-P3-9). DoUpdate skips the
                // whole GUI leg while the frame-stepper is engaged (`lbzx` on gm+0x9A0B98);
                // ours ran it unconditionally, so single-stepping a frame also advanced the
                // GUI a frame and the two were never actually in step. mbSteppingFrames is
                // the PC's name for that byte.
                if (lbRunFullModuleCascade && !mbSteppingFrames)
                {
                // ⭐ CLEAR FIRST, 2026-08-16 (boot audit F-P3-8). DoUpdate_GUI @0x823F0758
                // opens by clearing BOTH out buffers, then runs its bridges; we cleared the
                // GUI out-queue at the END of the leg instead. Same net emptiness at every
                // point that reads it today -- which is why the inversion was masked -- but
                // "the leg starts with an empty queue" is the invariant the console relies
                // on, and clearing at the end only holds while nothing outside this leg can
                // post into the queue.
                mpGuiOutputBuffer->Clear();
                mpGuiModelOutputBuffer->Clear();
                if (mGuiModule.IsPrepared())
                    mGuiModule.GetGuiOutQueue()->Clear();

                // ---- controller -> GUI input pass (the console per-substep bridge) ---------
                // Fill the player-0 pad record (InputPadsPC, the PC stand-in for the input
                // module's own fill), then run the REAL BridgeControllerToGui: it synthesises
                // the GUI controller events from the pad record and pushes them through
                // CgsGui::GuiModule::AddGuiEvent into this sub-step's GUI input buffer. The
                // GUI module drains that buffer during its Update below.
                {
                    // Advance the ToGui repeat/language-cycle clock (FLAG PC time source: the
                    // console words ride the game module's timer pass, unreconstructed).
                    const s64 liNowMs = static_cast<s64>(
                        std::chrono::duration_cast<std::chrono::milliseconds>(
                            std::chrono::steady_clock::now().time_since_epoch()).count());
                    miLanguageCycleTimerLo   = static_cast<s32>(liNowMs / 1000);
                    mfLanguageCycleTimerFrac = static_cast<f32>(liNowMs % 1000) * 0.001f;

                    // Boot/GUI-only states have not run InputPreWorld. Preserve their fill;
                    // a normal input update has already polled once, even while single-stepping.
                    if (!lbInputPreWorldFilledPC)
                    {
                        mPcInputOutputBuffer.LockForWrite();
                        CgsInput::InputPadsPC::UpdatePlayer0(&mPcInputOutputBuffer);
                        mPcInputOutputBuffer.UnlockForWrite();
                    }

                    mpGuiInputBuffer->LockForWrite();
                    // ARTISTDoUpdate_GUI823F0920..0944: publish the actual selection,
                    // not the no-user sentinel and not a preselected virtual pad index.
                    if (luStartPressedPort != CgsInput::KU_NUMBER_OF_PADS)
                        mpGuiInputBuffer->GetGuiEvents()->AddEvent(
                            reinterpret_cast<const CgsModule::Event*>(&luStartPressedPort),
                            143, sizeof(luStartPressedPort));
                    // ⭐ [boost-bar 206 wave] the world->GUI vehicle bridge (the console's
                    // DoUpdate_GUI @0x823F0758 calls BridgeWorldToGui under its own GUI-input
                    // write bracket) -- the read bracket mirrors the BridgeWorldToDirector
                    // leg's. Publishes the per-frame boost-info record (206) the HUD boost
                    // bar keys on.
                    if (mpWorldUpdateOutputBuffer != 0)
                    {
                        mpWorldUpdateOutputBuffer->LockForRead();
                        BridgeWorldToGui(mpGuiInputBuffer, mpWorldUpdateOutputBuffer);
                        mpWorldUpdateOutputBuffer->UnlockForRead();
                    }

                    mPcInputOutputBuffer.LockForRead();
                    BridgeControllerToGui(mpGuiInputBuffer, &mPcInputOutputBuffer);
                    const BrnGameState::GameStateModuleIO::OutputBuffer* const lpGameStateOutput =
                        mGameStateModule.GetOutputBuffer();
                    lpGameStateOutput->LockForRead();
                    BridgeGameStateToGui(mpGuiInputBuffer, lpGameStateOutput);
                    lpGameStateOutput->UnlockForRead();

                    // X360 DoUpdate_GUI: BridgeDirectorToGui @0x823DD5C0 -- the camera's
                    // post-FX hook requests and the hook-enumeration request (495..500).
                    if (mpDirectorOutputBuffer != 0)
                    {
                        mpDirectorOutputBuffer->LockForRead();
                        BridgeDirectorToGui(mpGuiInputBuffer, mpDirectorOutputBuffer);
                        mpDirectorOutputBuffer->UnlockForRead();
                    }

                    // The network -> GUI bridge, under a read lock on the network output (console
                    // DoUpdate_GUI runs it after the replay bridge, before BridgeGameToGui).
                    if (mpNetworkOutputBuffer != 0)
                    {
                        mpNetworkOutputBuffer->LockForRead();
                        BridgeNetworkToGui(mpGuiInputBuffer, mpNetworkOutputBuffer);
                        mpNetworkOutputBuffer->UnlockForRead();
                    }

                    // The game->GUI flow-FSM bridge (X360 0x823DCA10, run under the same
                    // write bracket the console's LoadingScriptedState::Update uses): post
                    // any pending GuiEventRunFsm stage the main flow requested.
                    BridgeGameToGui(mpGuiInputBuffer);

                    // The wrapper has already posted snapshot time26 in the native order.

                    // FLAG world-load stand-in: the console's GameState side reports the
                    // world-load status as game action 191, which the game module's
                    // translator (GameBridgeGameStateToX @0x823E9CE0, case 191) forwards to
                    // the GUI as GuiEvent<136> (load started) / GuiEvent<137> (load
                    // complete). The SCREEN flow's LOADING state blocks on 137 before it
                    // hands the flow to the in-game state. The PC has no world streaming
                    // yet, so its "world load" completes trivially: report loading-complete
                    // each sub-step while the in-game flow state is live (delivery is
                    // registration-filtered, so the event only reaches a state that is
                    // actually waiting on it). The real action-191 producer replaces this
                    // when the world-streaming pipeline lands.
                    if (BrnGameMainFlowController::gBrnInGameStateActive)
                    {
                        CgsGui::GuiEvent<137> lWorldLoadComplete;
                        CgsGui::GuiModule::AddGuiEvent(lWorldLoadComplete, mpGuiInputBuffer);
                    }
                    // The real PreWorld action193 -> wrapper -> canonical GUI350 route
                    // replaces the direct stand-in (requires Traffic checkpoint04).
                    // Retain the existing read-only profile ownership diagnostic.
                    {
                        BrnProgression::ProgressionManager* const lpProgressionManager =
                            mGameStateModule.GetProgressionManager();

                        BrnGui::GuiEventProgressionProfileData lProgressionProfile;
                        lProgressionProfile.mpProfile          = lpProgressionManager->GetProfile();
                        lProgressionProfile.mpProgressionData  = lpProgressionManager->GetProgressionData();
                        lProgressionProfile.mbRoadRulesAvailable =
                            lpProgressionManager->AreRoadRulesAvailable();
                        // [DIAG one-profile] NOT IN THE X360 BINARY. The two candidate owners
                        // side by side, from the ONE place both are addressable, so the claim
                        // "there is a single Profile" is settled by POINTER IDENTITY and not by
                        // two log lines 57 apart. Three payload fields as well, because equal
                        // isNewProfile bytes can agree by coincidence and an event count of
                        // 120-vs-0 cannot. Reports only on a change of the tuple.
                        if (CgsDev::Log::gpDebugPrint != 0)
                        {
                            const BrnProgression::Profile* const lpcGameStateProfile =
                                lProgressionProfile.mpProfile;
                            const BrnProgression::Profile* const lpcProfileManagerProfile =
                                mGuiModule.GetProfileManager().GetProgressionProfile();

                            struct OneProfileSample
                            {
                                const void* mpGameState;
                                const void* mpProfileManager;
                                s32         miNewGs;
                                s32         miNewPm;
                                u32         muMedalsGs;
                                u32         muMedalsPm;
                                u32         muEventsGs;
                                u32         muEventsPm;
                                u64         muSpawnCarGs;
                                u64         muSpawnCarPm;
                                s32         miRoadRulesGs;
                                s32         miMaxCarsGs;
                            };
                            OneProfileSample lSample;
                            lSample.mpGameState       = lpcGameStateProfile;
                            lSample.mpProfileManager  = lpcProfileManagerProfile;
                            lSample.miNewGs     = (lpcGameStateProfile != 0)
                                                  ? (lpcGameStateProfile->GetIsNewProfile() ? 1 : 0) : -1;
                            lSample.miNewPm     = (lpcProfileManagerProfile != 0)
                                                  ? (lpcProfileManagerProfile->GetIsNewProfile() ? 1 : 0) : -1;
                            lSample.muMedalsGs  = (lpcGameStateProfile != 0)
                                                  ? lpcGameStateProfile->GetMedalCountFromTheStart() : 0xFFFFFFFFu;
                            lSample.muMedalsPm  = (lpcProfileManagerProfile != 0)
                                                  ? lpcProfileManagerProfile->GetMedalCountFromTheStart() : 0xFFFFFFFFu;
                            lSample.muEventsGs  = (lpcGameStateProfile != 0)
                                                  ? lpcGameStateProfile->GetEventCount() : 0xFFFFFFFFu;
                            lSample.muEventsPm  = (lpcProfileManagerProfile != 0)
                                                  ? lpcProfileManagerProfile->GetEventCount() : 0xFFFFFFFFu;
                            // ⭐ THE SECOND FIELD, chosen because it CANNOT agree by coincidence:
                            // Profile::Construct leaves mSpawnCarId zero and only
                            // ProgressionManager::OnPlayerCarChange (car select) or a Deserialise
                            // writes it, so a returning boot that reads back PUSMC01 read it off
                            // the save. mbIsNewProfile alone is a single byte with two states.
                            lSample.muSpawnCarGs = (lpcGameStateProfile != 0)
                                                   ? static_cast<u64>(lpcGameStateProfile->GetSpawnCarId()) : 0u;
                            lSample.muSpawnCarPm = (lpcProfileManagerProfile != 0)
                                                   ? static_cast<u64>(lpcProfileManagerProfile->GetSpawnCarId()) : 0u;
                            // [L4 boot order 2026-09-28] two more fields, the two a profile load has to
                            // put back: how many of the profile's 64 road-rule rows hold a score
                            // (StreetManager::Update copies its own tables INTO the profile every frame,
                            // so a session that never ran StreetManager::OnProfileLoaded drops this to 0)
                            // and the "CARS OWNED x/Y" denominator (ProgressionManager::OnLoadProfile).
                            lSample.miRoadRulesGs = -1;
                            if (lpcGameStateProfile != 0)
                            {
                                lSample.miRoadRulesGs = 0;
                                for (s32 liRow = 0; liRow < 64; ++liRow)
                                {
                                    if (lpcGameStateProfile->GetUserChallengeData(liRow)->ContainsData(
                                            BrnStreetData::E_SCORE_TYPE_COUNT))
                                    {
                                        ++lSample.miRoadRulesGs;
                                    }
                                }
                            }
                            lSample.miMaxCarsGs =
                                mGameStateModule.GetProgressionManager()->GetMaxCarCount();

                            static bool             sbHaveLast = false;
                            static OneProfileSample sLast;
                            if (!sbHaveLast
                                || std::memcmp(&sLast, &lSample, sizeof(lSample)) != 0)
                            {
                                sbHaveLast = true;
                                sLast      = lSample;
                                char lacProbe[448];
                                std::snprintf(
                                    lacProbe, sizeof(lacProbe),
                                    "[one-profile] gameState.mProgressionManager.mProfile=%p"
                                    " profileManager.mpProgressionProfile=%p same=%d |"
                                    " isNewProfile gs=%d pm=%d | medalsFromTheStart gs=%d pm=%d |"
                                    " eventCount gs=%d pm=%d | spawnCarId gs=%016llX pm=%016llX |"
                                    " roadRules gs=%d | maxCars gs=%d\n",
                                    lSample.mpGameState, lSample.mpProfileManager,
                                    (lSample.mpGameState == lSample.mpProfileManager) ? 1 : 0,
                                    lSample.miNewGs, lSample.miNewPm,
                                    static_cast<s32>(lSample.muMedalsGs),
                                    static_cast<s32>(lSample.muMedalsPm),
                                    static_cast<s32>(lSample.muEventsGs),
                                    static_cast<s32>(lSample.muEventsPm),
                                    static_cast<unsigned long long>(lSample.muSpawnCarGs),
                                    static_cast<unsigned long long>(lSample.muSpawnCarPm),
                                    lSample.miRoadRulesGs, lSample.miMaxCarsGs);
                                CgsDev::Log::WriteToLog(lacProbe);
                            }
                        }
                    }
                    // FLAG GameState stand-in (THE CAR-SELECT CAR LIST -- GUI events 406 + 412).
                    PublishCarSelectionToGui();
                    mpGuiInputBuffer->UnlockForWrite();
                    mPcInputOutputBuffer.UnlockForRead();

                    // Hand this sub-step's filled buffer to the GUI drive (FLAG bridge
                    // stand-in: the console passes it through the module scheduler's IO set).
                    mGuiModule.SetGuiEventInputBuffer(mpGuiInputBuffer);
                }
                // GUI module per-frame tick (drives the FSM controller + the HUD flow + the
                // MovieManager). The X360 ticks this through the module dispatch.
                //
                // ⭐ GATED 2026-08-16 (boot audit F-P1-1). The GUI module is no longer
                // prepared by the time the frame loop starts -- loading stage 2 builds it,
                // several frames in, with the loading screen up. Ticking an unprepared
                // module would drive a null FSM controller, flow and MovieManager. The
                // console never faces the question: its module scheduler does not dispatch
                // to a module until the module reports prepared, which is the same test.
                const bool lbGuiPrepared = mGuiModule.IsPrepared();
                if (lbGuiPrepared)
                {
                    // The scheduler's second argument to GuiModule::Update on the console: this
                    // frame's update set (bit 8 == in-game).
                    mGuiModule.SetFrameUpdateSet(ConstructUpdateSetFromFsm());
                    mGuiModule.Update();
                    // FLAG PC-platform leaf: export the batch just produced by this
                    // no-argument GUI port into the frame-owned native output object.
                    mpGuiOutputBuffer->Clear();
                    mpGuiOutputBuffer->LockForWrite();
                    mpGuiOutputBuffer->AddGuiOutEvents(mGuiModule.GetGuiOutQueue());
                    mpGuiOutputBuffer->UnlockForWrite();
                    // The GUI->game out-event consumer (X360 0x823CB758): latch the flow
                    // commands (70/71, the loading screen 19/20, ...) the states posted.
                    BridgeGuiToGame(mGuiModule.GetGuiOutQueue());
                }
                // ---- the DIRECTOR's post-GUI pass (X360 module-scheduler order) -----------
                // It runs BridgeGuiToDirector over the SAME out-queue, so the queue must still
                // be intact here -- that is why BridgeGuiToGame no longer clears it.
                DoUpdate_Director(true);
                // Both GUI out-event consumers have now run; retire this frame's records.
                // (The console's queue lifecycle is the module scheduler's IO-buffer teardown;
                // on PC the queue is a module member, so it is cleared explicitly.)
                // (the retiring Clear moved to the HEAD of this leg -- see F-P3-8 above.)
                }   // end of the frame-step guard opened above (boot audit F-P3-9)

                // ---- THE EFFECTS LEG (X360 DoUpdate @0x823F0AF8, call site line 862) ------
                // Console order inside DoUpdate: ... DoUpdate_Director -> DoUpdate_GUI ->
                // DoUpdate_DirectorPostGUI -> **DoUpdate_Effects** -> DoUpdate_Sound ->
                // DoUpdate_ReplaysPostSim. This is that position: right after the post-GUI
                // director pass, which is what publishes the camera the effects input reads.
                //
                // ⭐ THIS IS WHAT DRIVES THE TYRE MARK. EffectsModule::Update ->
                // ProcessActiveRaceCars -> UpdateActiveRaceCars -> HandleWheels ->
                // TrailSystem::AddTrailSegment. Nothing called it before this change: the
                // module was a 1-byte ODR stub in BrnGameModule.hpp.
                //
                // FLAG PC arguments: the input/replay/sound-pre-update legs of the console
                // cascade have no per-frame buffer on this build, so they go in null and
                // DoUpdate_Effects skips each absent source. The suspend flag is the console's
                // "returning to the front end / loading" gate, which has no producer here yet;
                // FALSE is the console's value while a race is running, and it is what keeps
                // the effects system live rather than suspended.
                if (lbRunFullModuleCascade)
                    DoUpdate_Effects(mpUpdateInputBufferStack,
                                 mpUpdateOutputBufferStack,
                                 /*input   out*/ 0,
                                 mGameStateModule.GetOutputBuffer(),
                                 mpWorldUpdateOutputBuffer,
                                 mpDirectorOutputBuffer,
                                 /*replays out*/ 0,
                                 /*sound   out*/ 0,
                                 mpEffectsOutputBuffer,
                                 /*lbSuspendEffects*/ false,
                                 ConstructUpdateSetFromFsm());

                // ARTIST DoUpdate's sound leg follows the final camera publication
                // and effects update. Complete the capture begun before world update.
                if (lbRunFullModuleCascade)
                    FinishInGameSoundFramePC();

                // ---- ADOPT THE SERIALISERS THE EFFECTS LEG JUST REGISTERED ----------------
                // ReplayModule::StoreSerialisers @0x8264B600 is what hands every registered
                // BaseSerialiser its stream and STATIC buffers out of the replay module's linear
                // region. On the console it runs from ReplayModule::Update_PostSim @0x8265F618;
                // that leg is not reconstructed, so it runs here.
                //
                // ⚠ AFTER DoUpdate_Effects, NOT BEFORE -- MEASURED (run 9). The first version ran
                // it just above and adopted NOTHING across a whole 35-second run: the effects
                // OUTPUT buffer's replay request interface is rebuilt every frame, so before the
                // effects leg its eleven slots are all null. EffectsModule::Update @0x8229EC28
                // registers mEffectsSerialiser at its very first statement, so straight after the
                // leg is the one point in the frame where the interface is populated. (Run 9 also
                // proves it is not merely stale-by-a-frame: nothing was ever adopted, on any
                // frame, which only a per-frame clear explains.)
                //
                // ⚠ AND UNDER THE READ LOCK, through the CONST accessor. The first version used
                // the write-lock accessor @0x8227E280 with no lock at all: 3,895 "Not locked for
                // writing" assertions in one run. This leg only READS the eleven slots, so the
                // const overload @0x823BAD40 is the right one -- the same read/write pairing
                // mistake this file's own DoUpdate_Effects made against the game-action queue,
                // one commit earlier.
                //
                // Idempotent by construction (only slots whose pointer changed are touched), so
                // running it every frame costs one null compare per slot.
                // DELETE-WHEN ReplayModule::Update_PostSim lands: the call moves there.
                if (lbRunFullModuleCascade && mpEffectsOutputBuffer != 0)
                {
                    mpEffectsOutputBuffer->LockForRead();
                    const BrnEffects::EffectsIO::OutputBuffer* lpcEffectsOut = mpEffectsOutputBuffer;
                    mReplayModule.StoreSerialisers(*lpcEffectsOut->GetReplayRequestInterface());
                    mpEffectsOutputBuffer->UnlockForRead();
                }

                // ---- THE GAME-STATE POST-WORLD LEG -------------------------------------------
                // Console DoUpdate order: ... DoUpdate_Effects, DoUpdate_Sound,
                // DoUpdate_ReplaysPostSim, **DoUpdate_GameStatePostWorld**, DoUpdate_NetworkPostSim.
                // This position matters for two of its inputs: the director camera it reads the
                // picture-paradise flag from is the one this step's DoUpdate_Director published, and
                // the GUI out-queue BridgeGuiToGameState walks holds this step's GUI records.
                //
                // The full cascade runs when this sub-step has its network output: InGame and
                // scripted-load stage 8. Keep the PostWorld producer paired with the PreWorld
                // consumer above so stage 8 refreshes the active-car snapshot and drains the GUI
                // carry queue on the next sub-step, as ARTIST does. The same update-set captured
                // before NetworkPreSim remains valid even if the flow state advances later here.
                if (lbRunFullModuleCascade)
                {
                    DoUpdate_GameStatePostWorld(mpUpdateInputBufferStack,
                                                mpUpdateOutputBufferStack,
                                                &mPcInputOutputBuffer,
                                                mpWorldUpdateOutputBuffer,
                                                mpGuiOutputBuffer,
                                                /*replays post-sim out*/ 0,
                                                mpDirectorOutputBuffer,
                                                lFullModuleUpdateSet);
                }

                // ⚠️ FLAG PC quality-of-life: LATCH THIS TICK'S CAMERA.
                // Last thing in the sub-step, after the director's final pass has published
                // into mpDirectorOutputBuffer and before that buffer is torn down. Renders
                // that fall between ticks blend the last two latches; see the banner on
                // LatchDispatchCamera.
                // THE NETWORK POST-SIMULATION LEG. Console DoUpdate order: ... DoUpdate_Effects,
                // DoUpdate_Sound, DoUpdate_ReplaysPostSim, DoUpdate_GameStatePostWorld, then this,
                // then UpdateTimers (right below, as on the console). The GUI output buffer
                // carries this sub-step's just-produced GUI batch, shared with Sound and
                // PostWorld before the per-step output lifetime ends.
                if (mpNetworkOutputBuffer != 0)
                {
                    DoUpdate_NetworkPostSim(mpUpdateInputBufferStack, mpUpdateOutputBufferStack,
                                            mGameStateModule.GetOutputBuffer(),
                                            mpWorldUpdateOutputBuffer,
                                            mpGuiOutputBuffer,
                                            ConstructUpdateSetFromFsm());
                }

                // ---- the TIMER tick (X360 BrnGameModule::UpdateTimers @0x823BCFD0) ------------
                // ⭐⭐ MOVED HERE 2026-09-25 (FX-DIRECTOR2) -- the console's position. DoUpdate
                // @0x823F0AF8 calls it at 0x823F1CFC, the last module leg of the step, straight after
                // DoUpdate_NetworkPostSim (0x823F1C44). It folds in this step's game-state requests
                // and the director request MainDirector::Update published in THIS step's
                // DoUpdate_Director (SetTimestepMultiplier 0x82275148), applies them
                // (TimerRequestInterface::ApplyToTimers @0x828D7468) and ticks both timers --
                // Timer::Update @0x828D7320 makes the scale target current at once (0x828D7340, no
                // ramp). The NEXT sub-step's BridgeTimers snapshots the result, so a request made in
                // step N is integrated by the world in step N+1.
                // ⛔ WHAT THE OLD POSITION COST (boot audit F-P3-13 had flagged it, 2026-08-17, and
                // deferred the move): it ran mid-step, between the world leg and the director, so a
                // director request was drained one step late and integrated one step after that.
                // On the h225 s80 crash cell (fxd2on3) the hard stop's 0.000125 reached the world on
                // the crash's FOURTH frame (f778) instead of its third (f777) -- the frame that takes
                // the car from 197 to 102 mph ran at 0.016667 -- and every ImpactSlomoController
                // burst started a frame late the same way. Game-state requests were not affected.
                // It runs BEFORE the game-action retire below, which clears the game-state output's
                // request slot this drains.
                if (lbRunFullModuleCascade)
                    UpdateTimers();

                // THE GAME-ACTION RETIRE (FLAG PC lifecycle, see the note above DoUpdate_Director's
                // GUI block). On the console the game-state output buffer is re-Constructed every
                // frame, so an action lives for the whole DoUpdate and every leg that reads the
                // queue sees it; the last of them is the network post-simulation leg just above.
                // Retiring earlier (it sat right after the director leg) hid every game action
                // from the effects and network legs: the network never saw the start-of-game
                // reset-player-car action, so the free-burn car id stayed 0 in every lobby.
                {
                    BrnGameState::GameStateModuleIO::OutputBuffer* lpGameStateOutput =
                        mGameStateModule.GetOutputBuffer();
                    if (lpGameStateOutput != 0)
                    {
                        lpGameStateOutput->LockForWrite();
                        lpGameStateOutput->GetGameActionQueue()->Clear();
                        // FLAG PC-platform leaf: the persistent PC output must retire the
                        // trigger inputs after their world consumer. The console reconstructs
                        // all three queues each step in OutputBuffer::Construct82382940.
                        lpGameStateOutput->GetTriggerManagementInputInterface()->GetAddTriggerEventQueue().Clear();
                        lpGameStateOutput->GetTriggerManagementInputInterface()->GetRemoveTriggerEventQueue().Clear();
                        lpGameStateOutput->GetTriggerQueryInputInterface()->Clear();
                        // ⭐ [FLAG PC lifecycle, 2026-08-28 crash-slomo transport wave] THE TIMER
                        // REQUEST SLOT RETIRES WITH THE ACTION QUEUE, and for exactly the reason
                        // spelt out above: on the console this whole OutputBuffer is re-Constructed
                        // by the module scheduler every frame, so a posted TimerRequests entry is
                        // ONE-SHOT; on PC the module owns one persistent buffer. UpdateTimers() has
                        // already drained it this sub-step. Without this retire, the first
                        // DriveThruManager::SetPlayerCarDriver would latch KU_FLAG_MULTIPLIER here
                        // for the rest of the session: its 0.52631581f presentation timestep would
                        // be re-Appended every sub-step (tripping SetTimestepMultiplier's
                        // "Attempt to change slowmo multiple times" assert on the producer side and
                        // Append's "only 1 slowmo request" on the consumer side), and the sim would
                        // never come back to real time when the drive-thru hands control back.
                        lpGameStateOutput->GetTimerRequestInterface()->Clear();
                        // ⭐ [FLAG PC lifecycle, FX-GS2 2026-09-23, G10-D11] THE GAME-STATE -> GUI
                        // INTERFACE RETIRES TOO, for the same reason. The console rebuilds this
                        // OutputBuffer every frame, and OutputBuffer::Construct runs
                        // GameStateToGuiInterface::Construct (this + 17488), so each of its eight
                        // EventQueues starts every frame empty. Here the buffer is persistent and the
                        // queues are AddEvent-only (asserting, then writing past the end on overflow):
                        // AddFinishedRaceEvent's 4-slot queue already overran on a session's fifth
                        // finish, and CheckForTailingRivals' 7-slot on-tail queue would overrun in a
                        // few seconds of racing. The console's own Construct is the retire: queues
                        // empty, miPlayerRaceCarIndex back to -1. Their one consumer,
                        // TranslateGuiInterfaceToGuiEvents, has already run in the GUI leg above
                        // (G10-D11 part 2), so each record is posted in the sub-step that produced
                        // it -- or dropped with the buffer while frame-stepping, as on the console.
                        // FLAG PC-platform leaf: retire the persistent output after all
                        // frame consumers, matching the next OutputBuffer::Construct
                        // (82382940). Raw GUI responses and both validity flags are
                        // one-shot; the bridge copies them without clearing its source.
                        lpGameStateOutput->GetGuiEventQueue()->Clear();
                        lpGameStateOutput->SetSetUpAllEventStartsInterfaceIsValid(false);
                        lpGameStateOutput->SetSpecificGameModeEventInterfaceIsValid(false);
                        lpGameStateOutput->GetGameStateToGuiInterface()->Construct();
                        // FLAG PC-platform leaf: retire this queue after its final frame consumer.
                        // ARTIST reconstructs the whole OutputBuffer each sub-step, starting this queue empty.
                        lpGameStateOutput->GetTakedownEventOutputQueue()->Clear();
                        lpGameStateOutput->UnlockForWrite();
                    }
                }

                // ARTIST823F2010..2028: consume actual bind/unbind replies at the
                // last input-output use. HandleInputBindResult alone advances3->4.
                if (lbRunFullModuleCascade)
                {
                    mPcInputOutputBuffer.LockForRead();
                    BridgeInputToGame(&mPcInputOutputBuffer);
                    mPcInputOutputBuffer.UnlockForRead();
                }

                // Every current-frame GUI consumer has finished. This also drops a
                // skipped/partial batch at the same boundary as the native IO teardown.
                if (mGuiModule.IsPrepared())
                    mGuiModule.GetGuiOutQueue()->Clear();

                if (lbRunFullModuleCascade)
                    LatchDispatchCamera();
                PerfMonCpu::StopMonitor(mCpuMonitors.miUT_EachUpdate);

                if (liStep != miNumSimFramesRequired - 1)
                {
                    PerfMonCpu::StartMonitor(mCpuMonitors.miUT_GameState);
                    DestroyStaticIOBuffers();
                    PerfMonCpu::StopMonitor(mCpuMonitors.miUT_GameState);
                }

                ++liStep;
            }
            while (liStep < miNumSimFramesRequired);
        }
        // The resource callback is requested per simulation step above and
        // consumed once after the dispatch join. Zero-step frames request none.
        PerfMonCpu::StopMonitor(mCpuMonitors.miUT_TotalUpdate);
        sbSimUpdateComplete = 1;

        // FLAG: ARTIST 0x823CB498 brackets the per-frame Render with the monitor at
        // mCpuMonitors+0x4C (=miUT_RenderAll), not +0x50 (miUT_FrustumTesting). Fixed.
        PerfMonCpu::StartMonitor(mCpuMonitors.miUT_RenderAll);
        {
            BrnGameMainFlowController::EMainGameFlowState leState = mMainFlowStateMachine.GetCurrentState();
            if (leState != BrnGameMainFlowController::E_MGS_INVALID)
            {
                MainGameFlowState* lpState = mMainFlowStateMachine.GetState(leState);
                lpState->Render();
            }
        }

        // ⚠️ FLAG PC quality-of-life: ONLY IF THIS FRAME ACTUALLY RAN A SUB-STEP.
        //
        // These six are the LAST sub-step's set -- the loop above creates them per step and
        // destroys them between steps, deliberately leaving the final set alive so the flow
        // state's Render (just above) can read them. That reasoning assumes at least one
        // sub-step ran, which was guaranteed while mi8FrameRateMinSteps was the console's 1.
        //
        // It no longer is. On a frame that runs no sub-step nothing was created, and these
        // pointers are the nulls the PREVIOUS frame's teardown left. IOBufferStack::
        // DestroyIOBuffer asserts on a null and then dereferences it anyway (it mirrors the
        // console, which does exactly that) -- six asserts and a fault. Guarded, not
        // null-checked one by one, so the pairing with the create side stays obvious.
        if (miNumSimFramesRequired > 0)
        {
            if (mpNetworkOutputBuffer != 0)
                mpUpdateOutputBufferStack->DestroyIOBuffer<BrnNetwork::BrnNetworkModuleIO::OutputBuffer>(&mpNetworkOutputBuffer);
            mpUpdateOutputBufferStack->DestroyIOBuffer<BrnEffects::EffectsIO::OutputBuffer>(&mpEffectsOutputBuffer);
            mpUpdateOutputBufferStack->DestroyIOBuffer<BrnWorldIO::UpdateOutputBuffer>(&mpWorldUpdateOutputBuffer);
            mpUpdateOutputBufferStack->DestroyIOBuffer<BrnDirector::DirectorIO::OutputBuffer>(&mpDirectorOutputBuffer);
            mpUpdateOutputBufferStack->DestroyIOBuffer<CgsGui::ModelIO::OutputBuffer>(&mpGuiModelOutputBuffer);
            mpUpdateOutputBufferStack->DestroyIOBuffer<CgsGui::CgsGuiModuleIO::OutputBuffer>(&mpGuiOutputBuffer);
            mpUpdateInputBufferStack->DestroyIOBuffer<CgsGui::ViewIO::InputBuffer>(&mpGuiViewInputBuffer);
            mpUpdateInputBufferStack->DestroyIOBuffer<CgsGui::CgsGuiModuleIO::InputBuffer>(&mpGuiInputBuffer);
        }

        PerfMonCpu::StopMonitor(mCpuMonitors.miUT_RenderAll);
        return false;
    }

    // FLAG PC-platform scheduling: the in-game state drives the world from
    // GameMain's sub-step. Preserve ARTIST DoUpdate's pre-world sound capture
    // (823F1300), but consume the frame after director/GUI/effects (823F19E8).
    // A freshly constructed director output has an identity camera until then.
    BrnSound::Module::Io::RootPreUpdateOutputBuffer* BrnGameModule::BeginInGameSoundFramePC()
    {
        BrnGameModule* lpGameModule = this;
        CgsModule::IOBufferStack* lpOutputStack = lpGameModule->GetUpdateOutputBufferStack();
        BrnSound::Module::Io::RootOutputBuffer*& lpSoundRootOutput = mpInGameSoundRootOutputPC;
        BrnSound::Module::Io::RootPreUpdateOutputBuffer*& lpSoundPreUpdateOutput = mpInGameSoundPreUpdateOutputPC;
        lpOutputStack->CreateIOBuffer<BrnSound::Module::Io::RootOutputBuffer>(
            &lpSoundRootOutput, "Sound");
        lpOutputStack->CreateIOBuffer<BrnSound::Module::Io::RootPreUpdateOutputBuffer>(
            &lpSoundPreUpdateOutput, "SoundRootPreUpdateOutput");

        if (lpSoundPreUpdateOutput != 0 && lpGameModule->GetGuiInputBuffer() != 0)
        {
            lpGameModule->DoPreUpdate_Sound(lpOutputStack, lpSoundPreUpdateOutput,
                                            lpGameModule->GetGuiInputBuffer());
        }

        return lpSoundPreUpdateOutput;
    }

    void BrnGameModule::FinishInGameSoundFramePC()
    {
        BrnGameModule* lpGameModule = this;
        auto* lpOutputStack = GetUpdateOutputBufferStack();
        auto*& lpSoundRootOutput = mpInGameSoundRootOutputPC;
        auto*& lpSoundPreUpdateOutput = mpInGameSoundPreUpdateOutputPC;
        // The post-world sound leg (console @0x823F19E8): the full DoUpdate_Sound with the PC's
        // live sources. Replay pre-sim + effects outputs are null until those modules are driven
        // per-frame (FLAG'd inside the leg); the update set is the same FSM derivation the world
        // drive uses.
        if (lpSoundRootOutput != 0)
        {
            const BrnUpdateSet lUpdateSet = lpGameModule->ConstructUpdateSetFromFsm();
            lpGameModule->DoUpdate_Sound(
                lpGameModule->GetUpdateInputBufferStack(),
                lpOutputStack,
                lpGameModule->GetGameStateModule().GetOutputBuffer(),
                lpGameModule->GetWorldUpdateOutputBuffer(),
                lpGameModule->GetDirectorOutputBuffer(),
                0,   // replays pre-sim output: module not driven per-frame on PC yet
                lpSoundRootOutput,
                lpGameModule->GetGuiOutputBuffer(),
                0,   // effects output: module unmounted (lock-only participant on console)
                lUpdateSet);

            // The caller-side sound->resource forwards (console DoUpdate tail @0x823F1F08-34;
            // the leg itself does NOT forward): the root output's AttribSys <2048> queue +
            // <4096> request interface into the GameData input, under the standard
            // W(gameDataIn)+R(rootOut) bracket -- the same pair the loading spine forwards.
            BrnResource::GameDataIO::InputBuffer* lpGameDataInput =
                BrnGameMainFlowController::GetScriptedLoadGameDataInput();
            if (lpGameDataInput != 0)
            {
                lpGameDataInput->LockForWrite();
                lpSoundRootOutput->LockForRead();
                {
                    const BrnSound::Module::Io::RootOutputBuffer* lpSoundRootOutputRead = lpSoundRootOutput;
                    lpGameDataInput->GetAttribSysRequestInterface()->mRequestQueue.Append(
                        lpSoundRootOutputRead->GetAttribSysRequestInterface()->mRequestQueue);
                    lpGameDataInput->GetRequestInterface()->mRequestQueue.Append(
                        lpSoundRootOutputRead->GetResourceRequestInterface()->mRequestQueue);
                }
                lpSoundRootOutput->UnlockForRead();
                lpGameDataInput->UnlockForWrite();
            }
        }

        // Teardown in reverse creation order (console @0x823F20E0 preUpdateOut ... @0x823F21B4 rootOut).
        if (lpSoundPreUpdateOutput != 0)
            lpOutputStack->DestroyIOBuffer<BrnSound::Module::Io::RootPreUpdateOutputBuffer>(
                &lpSoundPreUpdateOutput);
        if (lpSoundRootOutput != 0)
            lpOutputStack->DestroyIOBuffer<BrnSound::Module::Io::RootOutputBuffer>(
                &lpSoundRootOutput);

    }

    // @ BrnGameModule.cpp:2497 - allocate this sub-step's static GUI/director IO buffers from
    // the update input/output buffer stacks.
    // ARTIST823DCD78. The scheduler continues to use its existing host
    // route; this recovered native caller has no selected invocation yet.
    void BrnGameModule::DoUpdate_GuiPreWorld(
        CgsModule::IOBufferStack* lpInputBufferStack,
        CgsModule::IOBufferStack* lpOutputBufferStack,
        CgsGui::CgsGuiModuleIO::OutputBuffer* lpGuiOutput,
        CgsGui::ModelIO::OutputBuffer* lpModelOutput,
        BrnResource::GameDataIO::InputBuffer* lpGameDataInput)
    {
        CgsDev::PerfMonCpu::StartMonitor(mCpuMonitors.miUT_GUI);
        if (!mbDiskError)
            mGuiModule.PreWorldUpdate(lpInputBufferStack, lpOutputBufferStack,
                lpGuiOutput, lpModelOutput);
        CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_GUI);

        const CgsGui::ModelIO::OutputBuffer* lpModelRead = lpModelOutput;
        const CgsGui::CgsGuiModuleIO::OutputBuffer* lpGuiRead = lpGuiOutput;
        CgsModule::LockBuffersForIO(lpGameDataInput, lpModelRead, lpGuiRead);
        lpGameDataInput->GetRequestInterface()->mRequestQueue.Append(
            *lpGuiRead->GetGuiResourceRequestQueue());
        CgsModule::UnlockBuffersForIO(lpGameDataInput, lpModelRead, lpGuiRead);
    }

    void BrnGameModule::CreateStaticIOBuffers()
    {
        // CreateIOBuffer<T> runs each buffer's own Construct right after the stack alloc, the
        // same as the X360 instantiations (e.g. CgsGuiModuleIO::InputBuffer @0x823AC898 ->
        // InputBuffer::Construct @0x82857378, DirectorIO::OutputBuffer @0x823ACBF8). The hand
        // Construct calls that used to follow each line here are gone -- they would now run
        // twice, and DirectorIO::OutputBuffer::Construct re-clears a freshly built buffer.
        mpUpdateInputBufferStack->CreateIOBuffer<CgsGui::CgsGuiModuleIO::InputBuffer>(&mpGuiInputBuffer, "Gui");
        mpUpdateInputBufferStack->CreateIOBuffer<CgsGui::ViewIO::InputBuffer>(&mpGuiViewInputBuffer, "GuiView");
        mpUpdateOutputBufferStack->CreateIOBuffer<CgsGui::CgsGuiModuleIO::OutputBuffer>(&mpGuiOutputBuffer, "Gui");
        mpUpdateOutputBufferStack->CreateIOBuffer<CgsGui::ModelIO::OutputBuffer>(&mpGuiModelOutputBuffer, "GuiModel");
        mpUpdateOutputBufferStack->CreateIOBuffer<BrnDirector::DirectorIO::OutputBuffer>(&mpDirectorOutputBuffer, "Director");

        // ⭐ THIS SUB-STEP'S WORLD UPDATE OUTPUT BUFFER (see the header note on
        // GetWorldUpdateOutputBuffer). The console's DoUpdate owns it for the whole sub-step
        // and threads it through every leg; DoUpdate is a PC leaf, so it lives here with the
        // other per-sub-step buffers. The world leg (DriveWorldUpdateFrame) drives the world
        // INTO it and DoUpdate_Director's BridgeWorldToDirector reads it back out.
        mpUpdateOutputBufferStack->CreateIOBuffer<BrnWorldIO::UpdateOutputBuffer>(
            &mpWorldUpdateOutputBuffer, "World");

        // THIS SUB-STEP'S EFFECTS OUTPUT BUFFER (see the header note on the member). The
        // console's DoUpdate @0x823F0AF8 creates it near the top and destroys it at the very
        // bottom; DoUpdate is a PC leaf here, so it shares the other buffers' lifetime.
        mpUpdateOutputBufferStack->CreateIOBuffer<BrnEffects::EffectsIO::OutputBuffer>(
            &mpEffectsOutputBuffer, "Effects");

        // THIS SUB-STEP'S NETWORK OUTPUT BUFFER (see the header note on the member). The
        // console's DoUpdate creates it at its top and destroys it at its bottom, and DoUpdate
        // runs from exactly two places: MainGameFlowStateInGame::Update, and
        // LoadingScriptedState::Update once the shared load stage reads 8 (below 8 that Update
        // runs its partial spine instead, which carves its own network buffers). The initial
        // loading screen never updates the network module; it loads it. So the buffer, and
        // with it every network leg of this sub-step, exists only in those states. Created
        // last so it is destroyed first.
        const BrnGameMainFlowController::EMainGameFlowState leState = mMainFlowStateMachine.GetCurrentState();
        const bool lbLoadingScriptedState = (leState >= BrnGameMainFlowController::E_MGS_CHECK_DISK_SPACE)
                                         && (leState <= BrnGameMainFlowController::E_MGS_COMPLETE_LOADING);
        if ((leState == BrnGameMainFlowController::E_MGS_IN_GAME)
            || (lbLoadingScriptedState && gBrnScriptedLoadStage == 8))
        {
            mpUpdateOutputBufferStack->CreateIOBuffer<BrnNetwork::BrnNetworkModuleIO::OutputBuffer>(
                &mpNetworkOutputBuffer, "Network");
        }
    }

    // @ BrnGameModule.cpp:2515 - free this sub-step's static GUI/director IO buffers (reverse
    // order of CreateStaticIOBuffers).
    void BrnGameModule::DestroyStaticIOBuffers()
    {
        if (mpNetworkOutputBuffer != 0)
            mpUpdateOutputBufferStack->DestroyIOBuffer<BrnNetwork::BrnNetworkModuleIO::OutputBuffer>(&mpNetworkOutputBuffer);
        mpUpdateOutputBufferStack->DestroyIOBuffer<BrnEffects::EffectsIO::OutputBuffer>(&mpEffectsOutputBuffer);
        mpUpdateOutputBufferStack->DestroyIOBuffer<BrnWorldIO::UpdateOutputBuffer>(&mpWorldUpdateOutputBuffer);
        mpUpdateOutputBufferStack->DestroyIOBuffer<BrnDirector::DirectorIO::OutputBuffer>(&mpDirectorOutputBuffer);
        mpUpdateOutputBufferStack->DestroyIOBuffer<CgsGui::ModelIO::OutputBuffer>(&mpGuiModelOutputBuffer);
        mpUpdateOutputBufferStack->DestroyIOBuffer<CgsGui::CgsGuiModuleIO::OutputBuffer>(&mpGuiOutputBuffer);
        mpUpdateInputBufferStack->DestroyIOBuffer<CgsGui::ViewIO::InputBuffer>(&mpGuiViewInputBuffer);
        mpUpdateInputBufferStack->DestroyIOBuffer<CgsGui::CgsGuiModuleIO::InputBuffer>(&mpGuiInputBuffer);
    }

    // =========================================================================================
    // ⭐ [FX-RUMBLE3 2026-09-24, crash-parity G10-D4] DoUpdate_InputPreWorld -- X360 0x823C5650
    // (DWARF BrnGameModule.h:550; BrnGameModuleUpdateFunctions.cpp:45, locals
    // `IOHelper<PreWorldInputBuffer> lpInputModulePreWorldInputBuffer`, `uint32_t liStartPressedPort`).
    // The first leg of every update step, and the ONLY place the game's rumble requests reach the
    // pads: until it existed RumbleManager's four queues were filled every frame and never drained.
    //   0x823C5670  StartMonitor(gm+0x996F28 == mCpuMonitors+0x10, miUT_GameState)
    //   0x823C5680  IOHelper: CreateIOBuffer<CgsInput::InputIO::PreWorldInputBuffer>(inStack, "InputPreWorld")
    //               (0x823AEE18: Alloc 920 + PreWorldInputBuffer::Construct), asserting
    //               "mpStack->CreateIOBuffer( &mpBuffer, lpcName )" (CgsModuleIOHelper.h:52)
    //   0x823C56C8  StartMonitor(gm+0x996F9C == mCpuMonitors+0x84, miUT_GameState_Bridge)
    //   0x823C56D8  LockForWrite ; GameStateModule::BridgeRumbleToInput(gm+0x669400, buffer,
    //               gm+0x9A0B0C == &mTimerStatusInterface) ; UnlockForWrite ; StopMonitor
    //   0x823C5720  mInputModule (gm+0x6E9630) vtable+0x44 == InputModule::PreWorldUpdate(inStack,
    //               outStack, buffer, lpInputModuleOutput, *(gm+0x9A0622) == 0 -- !mbDiskError)
    //   0x823C5738..0x823C57F8  if (miInputModuleState == 1): select the invite user or first
    //               START-pressed pad, then set miInputModuleState = 2
    //   0x823C5808  QueryRequestDoStepFrame(lpInputModuleOutput)                   -- caller unactivated
    //   0x823C57F8  StopMonitor(miUT_GameState) ; the IOHelper's DestroyIOBuffer (0x823AEEE8) at scope end
    // =========================================================================================
    u32 BrnGameModule::DoUpdate_InputPreWorld(CgsModule::IOBufferStack* lpInputBufferStack,
                                              CgsModule::IOBufferStack* lpOutputBufferStack,
                                              CgsInput::InputIO::OutputBuffer* lpInputModuleOutput)
    {
        CgsDev::PerfMonCpu::StartMonitor(mCpuMonitors.miUT_GameState);
        CgsModule::IOHelper<CgsInput::InputIO::PreWorldInputBuffer> lpInputModulePreWorldInputBuffer(
            lpInputBufferStack, "InputPreWorld");

        CgsDev::PerfMonCpu::StartMonitor(mCpuMonitors.miUT_GameState_Bridge);
        lpInputModulePreWorldInputBuffer->LockForWrite();
        mGameStateModule.BridgeRumbleToInput(lpInputModulePreWorldInputBuffer, &mTimerStatusInterface);
        lpInputModulePreWorldInputBuffer->UnlockForWrite();
        CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_GameState_Bridge);

        mInputModule.PreWorldUpdate(lpInputBufferStack, lpOutputBufferStack,
                                    lpInputModulePreWorldInputBuffer, lpInputModuleOutput, !mbDiskError);

        // The selection path keeps the original no-user sentinel until state 1 finds a user.
        u32 liStartPressedPort = CgsInput::KU_NUMBER_OF_PADS;
        if (miInputModuleState == 1)
        {
            lpInputModuleOutput->LockForRead();
            if (mHardware.HasGameBeenRebootedDueToInvite())
            {
                BrnHW::System360HW* lpLaunchData = GetSoftRebootData();
                if (lpLaunchData == 0)
                {
                    CgsDev::Assert::BeginAssert();
                    CgsDev::Assert::FireAssert("lpLaunchData",
                        "d:\\p4\\b5_main\\burnout\\main\\code\\gamesource\\unity\\../Game/BrnGameModuleUpdateFunctions.cpp", 71);
                    CgsDev::Assert::EndAssert();
                }
                liStartPressedPort = lpLaunchData->mdwUserIndex;
                miInputModuleState = 2;
            }
            else
            {
                for (s32 liPort = 0; liPort < CgsInput::KU_NUMBER_OF_PADS; ++liPort)
                {
                    const CgsInput::InputIO::PadOutputInformation* lpPadInfo =
                        lpInputModuleOutput->GetPadInfo(liPort);
                    if (((lpPadInfo->maActionInfo[E_GAMEINPUTACTIONS_START].muStatus >> 1) & 1) != 0)
                    {
                        liStartPressedPort = static_cast<u32>(liPort);
                        miInputModuleState = 2;
                        break;
                    }
                }
            }
            lpInputModuleOutput->UnlockForRead();
        }
        // This remains an idle/rebind transition: construction starts at state 4; an unbind
        // completion returns to 0, and BridgeGuiToGame event 90 can arm state 1 again.
        // Original 0x823C5808: query only after the input module has published its pad output.
        QueryRequestDoStepFrame(lpInputModuleOutput);
        CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_GameState);
        return liStartPressedPort;
    }

    // ARTIST 0x823BCF40; one-time initial console mapping, all four pads (port -1).
    void BrnGameModule::PrepareInitialInputMapping(
        CgsInput::InputIO::PostWorldInputBuffer* lpPostWorldInput)
    {
        CGS_ASSERT(lpPostWorldInput != 0, "lpInputBuffer");
        lpPostWorldInput->LockForWrite();
        lpPostWorldInput->PostMappingRequest(KA_CONSOLE_DEFAULT_GAME_INPUT_MAPPING, -1);
        CGS_ASSERT(lpPostWorldInput != 0, "lpInputBuffer");
        lpPostWorldInput->UnlockForWrite();
    }

    // ARTIST 0x823BD390; bind player 0 to the port selected by the pre-world input leg.
    void BrnGameModule::BindInputToPort(
        s32 liPort,
        CgsInput::InputIO::PostWorldInputBuffer* lpPostWorldInput)
    {
        CGS_ASSERT(lpPostWorldInput != 0, "lpInputBuffer");
        lpPostWorldInput->LockForWrite();
        lpPostWorldInput->PostBindRequest(0, liPort);
        CGS_ASSERT(lpPostWorldInput != 0, "lpInputBuffer");
        lpPostWorldInput->UnlockForWrite();
    }

    // ARTIST 0x823C59E8. Both stacks are passed by the original caller; only the input stack
    // owns this helper. The GameState output is read-locked and the World output read-locked
    // around their respective bridges, in console order.
    void BrnGameModule::DoUpdate_InputPostWorld(
        CgsModule::IOBufferStack* lpInputBufferStack,
        CgsModule::IOBufferStack* /*lpOutputBufferStack*/,
        const BrnGameState::GameStateModuleIO::OutputBuffer* lpGameStateOutput,
        const BrnWorldIO::UpdateOutputBuffer* lpWorldOutput,
        u32 liStartPressedPort)
    {
        CgsDev::PerfMonCpu::StartMonitor(mCpuMonitors.miUT_GameState);
        CgsModule::IOHelper<CgsInput::InputIO::PostWorldInputBuffer> lpPostWorldInput(
            lpInputBufferStack, "InputPostWorld");
        CgsInput::InputIO::PostWorldInputBuffer* lpPostWorldInputBuffer = lpPostWorldInput;

        if (!sbInitialInputMappingPosted)
        {
            PrepareInitialInputMapping(lpPostWorldInputBuffer);
            sbInitialInputMappingPosted = true;
        }

        if (miInputModuleState == 2)
        {
            BindInputToPort(static_cast<s32>(liStartPressedPort), lpPostWorldInputBuffer);
            miInputModuleState = 3;
        }
        else if (miInputModuleState == 5)
        {
            lpPostWorldInputBuffer->LockForWrite();
            lpPostWorldInputBuffer->PostUnbindRequest(0);
            lpPostWorldInputBuffer->UnlockForWrite();
            miInputModuleState = 6;
        }

        CgsDev::PerfMonCpu::StartMonitor(mCpuMonitors.miUT_GameState_Bridge);
        CgsModule::LockBuffersForIO(lpPostWorldInputBuffer, lpGameStateOutput);
        BridgeGameStateToController(lpPostWorldInputBuffer, lpGameStateOutput);
        CgsModule::UnlockBuffersForIO(lpPostWorldInputBuffer, lpGameStateOutput);

        CgsModule::LockBuffersForIO(lpPostWorldInputBuffer, lpWorldOutput);
        const BrnWorldIO::UpdateOutputBuffer::VehicleManagerOutputInterface*
            lpVehicleManagerOutput = lpWorldOutput->GetVehicleManagerOutputInterface();
        lpPostWorldInputBuffer->SetWheelFFSpring(lpVehicleManagerOutput->GetPlayerWheelFFSpring());
        CgsModule::UnlockBuffersForIO(lpPostWorldInputBuffer, lpWorldOutput);
        CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_GameState_Bridge);

        mInputModule.PostWorldUpdate(lpInputBufferStack, lpPostWorldInputBuffer);
        CgsDev::PerfMonCpu::StopMonitor(mCpuMonitors.miUT_GameState);
    }

    // ARTIST 0x823BD248. The caller owns the input-module output buffer's read lock.
    void BrnGameModule::BridgeInputToGame(
        const CgsInput::InputIO::OutputBuffer* lpInputModuleOutput)
    {
        if (lpInputModuleOutput->GetBindResultQueue()->GetLength() != 0 &&
            miInputModuleState != 3)
        {
            CGS_ASSERT(false,
                "lpInputModuleOutput->GetBindResultQueue()->GetLength() == 0 || "
                "meInputBindState == E_INPUTBINDSTATE_BIND_REQUESTED");
        }
        if (lpInputModuleOutput->GetUnbindResultQueue()->GetLength() != 0 &&
            miInputModuleState != 6)
        {
            CGS_ASSERT(false,
                "lpInputModuleOutput->GetUnbindResultQueue()->GetLength() == 0 || "
                "meInputBindState == E_INPUTBINDSTATE_UNBIND_REQUESTED");
        }

        if (miInputModuleState == 3)
        {
            const CgsInput::InputIO::OutputBuffer::BindResultQueue* lpBindResults =
                lpInputModuleOutput->GetBindResultQueue();
            const s32 liNumResults = lpBindResults->GetLength();
            for (s32 i = 0; i < liNumResults; ++i)
                HandleInputBindResult(lpBindResults->GetEvent(i));
        }
        else if (miInputModuleState == 6)
        {
            const CgsInput::InputIO::OutputBuffer::UnBindResultQueue* lpUnbindResults =
                lpInputModuleOutput->GetUnbindResultQueue();
            const s32 liNumResults = lpUnbindResults->GetLength();
            for (s32 i = 0; i < liNumResults; ++i)
                HandleInputUnbindResult(lpUnbindResults->GetEvent(i));
        }
    }

    // ARTIST 0x823A8C38. Only player 0 changes the game's active-controller state.
    void BrnGameModule::HandleInputBindResult(const CgsInput::InputIO::BindResult& lrResult)
    {
        if (lrResult.miPlayer != 0)
            return;

        CGS_ASSERT(miInputModuleState == 3,
                   "meInputBindState == E_INPUTBINDSTATE_BIND_REQUESTED");
        CGS_ASSERT(lrResult.meResultCode == CgsInput::E_BINDRESULTOK,
                   "CgsInput::E_BINDRESULTOK == lResult.GetResultCode()");

        miPlayer0ControllerPort = lrResult.miPort;
        if ((CgsDev::Message::gxMessageFilterFlags & 1) != 0)
            *CgsDev::Log::gpDebugPrint << "Active controller is port: "
                                       << lrResult.miPort << "\n";

        miSecondaryControllerPort = (miPlayer0ControllerPort == 0) ? 1 : 0;
        mDebugManager.SetGamePad(
            mInputModule.mControllers.GetDebugGamePad(miSecondaryControllerPort));
        miInputModuleState = 4;
    }

    // ARTIST 0x823A8D50. Only player 0 changes the game's active-controller state.
    void BrnGameModule::HandleInputUnbindResult(const CgsInput::InputIO::UnBindResult& lrResult)
    {
        if (lrResult.miPlayer != 0)
            return;

        CGS_ASSERT(miInputModuleState == 6,
                   "meInputBindState == E_INPUTBINDSTATE_UNBIND_REQUESTED");
        CGS_ASSERT(lrResult.meResultCode == CgsInput::E_UNBINDRESULTOK,
                   "CgsInput::E_UNBINDRESULTOK == lResult.GetResultCode()");

        miPlayer0ControllerPort = CgsInput::KU_NUMBER_OF_PADS;
        if ((CgsDev::Message::gxMessageFilterFlags & 1) != 0)
            *CgsDev::Log::gpDebugPrint << "Active controller invalidated\n";
        mDebugManager.SetGamePad(0);
        miInputModuleState = 0;
    }

    // X360 0x823C5580; BrnGameModule.cpp:4013 (DecFIGS).
    void BrnGameModule::QueryRequestDoStepFrame(
        const CgsInput::InputIO::OutputBuffer* lpInputOutputBuffer)
    {
        if (_gbHACKIsOnline)
            return;

        lpInputOutputBuffer->LockForRead();
        s32 liControllerPort = 0;
        const CgsInput::InputIO::PadOutputInformation* lpPadInfo =
            GetPadInfoForPlayer0(lpInputOutputBuffer, &liControllerPort);
        if (lpPadInfo != 0 &&
            (lpPadInfo->maActionInfo[21].muStatus & 2u) != 0 &&
            (lpPadInfo->maActionInfo[57].muStatus & 1u) != 0 &&
            (lpPadInfo->maActionInfo[56].muStatus & 1u) != 0)
        {
            if (mbSteppingFrames)
                mbRequestDoPlayFrame = true;
            else
                mbRequestDoStepFrame = true;
        }
        lpInputOutputBuffer->UnlockForRead();
    }

    // @ BrnGameModule.cpp:4048 - apply a pending step/play-frame request: a step request
    // starts single-stepping and runs one step; a play request resumes from stepping.
    void BrnGameModule::UpdateRequestDoStepFrame()
    {
        if (mbRequestDoStepFrame)
        {
            mbSteppingFrames = true;
            mbDoStep = true;
            mbRequestDoStepFrame = false;
        }
        else if (mbRequestDoPlayFrame)
        {
            if (mbSteppingFrames)
                mbStopStepping = true;
            mbRequestDoPlayFrame = false;
        }
    }

    // @ 0x823C54D8 [P1 sim-pause] -- the pause spine's consumer end: drain the game-action
    // queue under the output buffer's read lock; action 86 (KI_ACTION_PAUSE_STRICT) raises
    // mbSimPaused and STOPS the sim timer, action 87 (KI_ACTION_UNPAUSE) clears it and
    // restarts the timer. Console stores, verbatim (p1_dump.txt):
    //     case 86: *(gm+0x9A0621) = 1; *(gm+0x9A0B08) = 0;   // mbSimPaused / simTimer.mbRunning
    //     case 87: *(gm+0x9A0621) = 0; *(gm+0x9A0B08) = 1;
    // (0x9A0B08 == the sim Timer @0x9A0AF4 +0x18 mbRunning -- the byte Construct's step 9
    // seeds to 1; see the step-9 note above.) Both stores by name here. The stopped sim
    // timer is what freezes the world: every sim sub-step's timestep derives from it, and
    // ConstructUpdateSetFromFsm additionally raises update-set bit 0 off mbSimPaused.
    void BrnGameModule::CheckGameActions(
        BrnGameState::GameStateModuleIO::OutputBuffer* lpGameStateOutput)
    {
        lpGameStateOutput->LockForRead();
        const BrnGameState::GameStateModuleIO::GameActionQueue* lpActionQueue =
            static_cast<const BrnGameState::GameStateModuleIO::OutputBuffer*>(lpGameStateOutput)
                ->GetGameActionQueue();

        const CgsModule::Event* lpEvent = 0;
        s32 liSize = 0;
        s32 liAction = lpActionQueue->GetFirstEvent(&lpEvent, &liSize);
        while (lpEvent != 0)
        {
            if (liAction == 86)
            {
                mbSimPaused = true;
                mSimTimer.SetRunning(false);
                // [DIAG] NOT IN THE X360 BINARY -- the pause spine's consumer rung.
                if (CgsDev::Log::gpDebugPrint != 0)
                    *CgsDev::Log::gpDebugPrint << "[sim-pause] action 86 -> PAUSED (sim timer stopped)\n";
            }
            else if (liAction == 87)
            {
                mbSimPaused = false;
                mSimTimer.SetRunning(true);
                // [DIAG] NOT IN THE X360 BINARY -- the resume rung.
                if (CgsDev::Log::gpDebugPrint != 0)
                    *CgsDev::Log::gpDebugPrint << "[sim-pause] action 87 -> RESUMED (sim timer running)\n";
            }
            const CgsModule::Event* lpCurrent = lpEvent;
            liAction = lpActionQueue->GetNextEvent(lpCurrent, &lpEvent, &liSize);
        }
        lpGameStateOutput->UnlockForRead();
    }

    // @ BrnGameModule.cpp:3542 - build this frame's simulation update-set bitmask from the
    // active flow-state machine + game flags.
    BrnUpdateSet BrnGameModule::ConstructUpdateSetFromFsm()
    {
        u32 luUpdateSet = 0x80;
        if (mMainFlowStateMachine.IsInGameState())
            luUpdateSet = 0x88;
        if (mMainFlowStateMachine.IsSaveLoadState())
            luUpdateSet = (luUpdateSet & 0xFF3F) | 0x40;
        if (mMainFlowStateMachine.IsVideoState())
            luUpdateSet |= 0x20;
        if (mbSimPaused || mMainFlowStateMachine.IsSaveLoadState())
            luUpdateSet |= 0x1;
        if (mbStalled)
            luUpdateSet |= 0x400;
        if (mbDiskError)
            luUpdateSet |= 0x200;
        return (BrnUpdateSet)luUpdateSet;
    }

    // ARTIST 0x823CBBB0. Search a GUI-model output event queue for the requested type.
    bool BrnGameModule::IsEventInGuiQueue(
        s32 liEventTypeToFind,
        const CgsGui::ModelIO::OutputBuffer::GuiEventQueue* lpEventQueue)
    {
        CGS_ASSERT(lpEventQueue != 0, "lpEventQueue != NULL");

        const CgsModule::Event* lpEvent = 0;
        s32 liEventSize = 0;
        s32 liEventType = lpEventQueue->GetFirstEvent(&lpEvent, &liEventSize);
        if (lpEvent == 0)
            return false;

        while (liEventType != liEventTypeToFind)
        {
            liEventType = lpEventQueue->GetNextEvent(lpEvent, &lpEvent, &liEventSize);
            if (lpEvent == 0)
                return false;
        }
        return true;
    }

    // ARTIST 0x823CBC48 is unnamed; DecFIGS declares this GuiEventQueueSmall overload.
    bool BrnGameModule::IsEventInGuiQueue(
        s32 liEventTypeToFind,
        const CgsGui::GuiEventQueueSmall* lpEventQueue)
    {
        CGS_ASSERT(lpEventQueue != 0, "lpEventQueue != NULL");

        const CgsModule::Event* lpEvent = 0;
        s32 liEventSize = 0;
        s32 liEventType = lpEventQueue->GetFirstEvent(&lpEvent, &liEventSize);
        if (lpEvent == 0)
            return false;

        while (liEventType != liEventTypeToFind)
        {
            liEventType = lpEventQueue->GetNextEvent(lpEvent, &lpEvent, &liEventSize);
            if (lpEvent == 0)
                return false;
        }
        return true;
    }

    // ARTIST 0x823DCB40. Keep this late, output-derived update set distinct from
    // ConstructUpdateSetFromFsm(), which is the set captured before the module legs.
    BrnUpdateSet BrnGameModule::ConstructUpdateSet(
        const BrnGameState::GameStateModuleIO::OutputBuffer* lpGameStateModuleOutputBuffer,
        const BrnNetwork::BrnNetworkModuleIO::OutputBuffer* lpNetworkModuleOutputBuffer,
        const CgsInput::InputIO::OutputBuffer* lpInputModuleOutputBuffer,
        const CgsGui::ModelIO::OutputBuffer* lpGuiModuleModelOutputBuffer,
        const BrnReplays::ReplayIO::OutputBuffer_PreSim* lpReplayOutputBuffer)
    {
        CGS_ASSERT(lpGameStateModuleOutputBuffer != 0,
                   "lpGameStateModuleOutputBuffer != NULL");
        CGS_ASSERT(lpInputModuleOutputBuffer != 0,
                   "lpInputModuleOutputBuffer != NULL");
        CGS_ASSERT(lpGuiModuleModelOutputBuffer != 0,
                   "lpGuiModuleModelOutputBuffer != NULL");

        BrnUpdateSet leUpdateSet = ConstructUpdateSetFromFsm();

        // ARTIST locks the game-state output here without reading from it.
        lpGameStateModuleOutputBuffer->LockForRead();
        lpGameStateModuleOutputBuffer->UnlockForRead();

        // Replay status bit 0 selects replay playback and the paired update bits 0x101.
        lpReplayOutputBuffer->LockForRead();
        if ((lpReplayOutputBuffer->GetStatusInterface()->mxStatusFlags & 1u) != 0)
            leUpdateSet |= 0x101;
        lpReplayOutputBuffer->UnlockForRead();

        // A pending pad-disconnect event contributes update bit 0x4. The typed queue
        // accessor returns the BaseEventQueue whose GetLength is the asm's +8 word.
        lpInputModuleOutputBuffer->LockForRead();
        if (lpInputModuleOutputBuffer->GetPadDisconnectedQueue()->GetLength() != 0)
            leUpdateSet |= 0x4;
        lpInputModuleOutputBuffer->UnlockForRead();

        CGS_ASSERT(lpNetworkModuleOutputBuffer != 0,
                   "lpNetworkModuleOutputBuffer != NULL");
        lpNetworkModuleOutputBuffer->LockForRead();
        if (IsEventInGuiQueue(44, lpNetworkModuleOutputBuffer->GetGuiEventQueue()))
            leUpdateSet |= 0x2;
        if (lpNetworkModuleOutputBuffer->IsInInvite())
            leUpdateSet |= 0x10;
        lpNetworkModuleOutputBuffer->UnlockForRead();

        lpGuiModuleModelOutputBuffer->LockForRead();
        if (IsEventInGuiQueue(66, lpGuiModuleModelOutputBuffer->GetGuiOutEvents()))
            leUpdateSet |= 0x40;
        if (IsEventInGuiQueue(69, lpGuiModuleModelOutputBuffer->GetGuiOutEvents()))
            leUpdateSet |= 0x20;
        if (mbDiskError)
            leUpdateSet |= 0x200;
        if (mbStreamingStalled)
            leUpdateSet |= 0x800;
        lpGuiModuleModelOutputBuffer->UnlockForRead();

        return leUpdateSet;
    }

    // @ BrnGameModule.cpp:1146 - the update-thread stage machine: drives GamePrepare (one-time
    // setup) -> GameMain (per-frame update, repeating) -> GameRelease (teardown). meGameUpdateStage
    // is PREPARE(0)/MAIN(1)/RELEASE(2). Returns true to keep the thread alive.
    // ARTIST 0x823C5480: the public frame entry brackets ThreadLayout::Update.
    // Massive's console hardware callback has no native PC service.
    void BrnGameModule::Update()
    {
        CgsDev::PerfMonCpu::StartProfiling();
        {
            renderengine::FrameProfile::Scope lDisplayProfile(renderengine::FrameProfile::UPDATE, renderengine::FrameProfile::UPDATE_DISPLAY);
            mRenderModule.PrepareDisplayPC();
        }
        const bool lbParallel = mbAllowFrameOverlapPC
            && meGameUpdateStage == E_GAMEUPDATESTAGE_MAIN
            && mMainFlowStateMachine.IsInGameState();
        if (lbParallel != mbActiveFrameOverlapPC)
        {
            mThreadLayout.EndPC(false);
            mThreadLayout.SetParallelEnabledPC(lbParallel);
            mThreadLayout.Begin(this, mCpuMonitors.miUT_Resource,
                mCpuMonitors.miUT_ThreadSync, mCpuMonitors.miUT_WaitOnDispatch);
            mbActiveFrameOverlapPC = lbParallel;
        }
        mThreadLayout.Update();
        CgsDev::PerfMonCpu::StopProfiling();
    }

    void BrnGameModule::BeginFramesPC(bool lbAllowParallel)
    {
        mbAllowFrameOverlapPC = lbAllowParallel;
        mbActiveFrameOverlapPC = false;
        mThreadLayout.SetParallelEnabledPC(false);
        mThreadLayout.Begin(this, mCpuMonitors.miUT_Resource,
            mCpuMonitors.miUT_ThreadSync, mCpuMonitors.miUT_WaitOnDispatch);
        mbFrameLayoutInitializedPC = true;
    }

    void BrnGameModule::EndFramesPC()
    {
        mThreadLayout.SynchronizeDispatchPC();
        mRenderModule.EndMeshFramesPC();
        mThreadLayout.EndPC();
        mbFrameLayoutInitializedPC = false;
    }

    void BrnGameModule::SynchronizeDispatchPC()
    {
        if (mbFrameLayoutInitializedPC)
            mThreadLayout.SynchronizeDispatchPC();
    }

    bool BrnGameModule::UpdateThread()
    {
        renderengine::FrameProfile::CycleScope lUpdateProfile(renderengine::FrameProfile::UPDATE, renderengine::FrameProfile::UPDATE_SIMULATION);
        struct UpdateScopePC
        {
            bool& mrInside;
            explicit UpdateScopePC(bool& lrInside) : mrInside(lrInside) { mrInside = true; }
            ~UpdateScopePC() { mrInside = false; }
        } lUpdateScope(mbInsideUpdatePC);
        CgsDev::Assert::PollFrameProbePC(0);
        switch (meGameUpdateStage)
        {
        case E_GAMEUPDATESTAGE_PREPARE:
            if (!GamePrepare())
                break;
            meGameUpdateStage = E_GAMEUPDATESTAGE_MAIN;
            GameMain();
            break;

        case E_GAMEUPDATESTAGE_MAIN:
            meGameUpdateStage = E_GAMEUPDATESTAGE_MAIN;
            GameMain();
            break;

        case E_GAMEUPDATESTAGE_RELEASE:
            meGameUpdateStage = E_GAMEUPDATESTAGE_RELEASE;
            if (GameRelease())
                meGameUpdateStage = E_GAMEUPDATESTAGE_PREPARE;
            break;

        default:
            CGS_ASSERT(false, "Invalid update stage\n");
            break;
        }
        // FLAG PC-platform leaf: the completed write GDL may be expanded while
        // the render worker consumes the previous bank. The joined publication
        // revalidates resources before making this result visible.
        mRenderModule.PrepareMeshFrameForWritePC();
        return true;
    }

    // @ BrnGameModule.cpp:3872 - debug helper: fill liNumBytes at lpDest with the repeating
    // 32-bit pattern luValue (head/tail handled byte-wise). Used by DebugMemoryInit to stamp
    // freed module memory with a marker value.
    void BrnGameModule::DebugSetMemoryToInt(void* lpDest, s32 liNumBytes, u32 luValue)
    {
        u8*       lpByte = static_cast<u8*>(lpDest);
        const u8* lpPattern = reinterpret_cast<const u8*>(&luValue);
        for (s32 i = 0; i < liNumBytes; ++i)
            lpByte[i] = lpPattern[i & 3];
    }

    // @ BrnGameModule.cpp:1515 - after the GPU vsync wait completes, ask the frame-rate
    // manager how many simulation steps this render frame must run (driving GameMain's
    // catch-up loop count).
    void BrnGameModule::OnCompletionOfVsyncWait()
    {
        renderengine::FrameProfile::Scope lFramePhaseProfile(renderengine::FrameProfile::UPDATE, renderengine::FrameProfile::UPDATE_TIMING);
        miNumSimFramesRequired = mFrameRateManager.UpdatePostRenderWait(
            mi8ActualFrameRateMinStepsThisFrame, mi8ActualFrameRateMaxStepsThisFrame);

        // ⚠️ FLAG PC quality-of-life: publish this frame's blend factor + real frame length
        // to the render legs. This is the ONE producer -- everything that interpolates reads
        // CgsSystem::FrameInterpolation, never the manager, so a render leg deep in the world
        // module does not have to reach the game module to find out how far between two
        // simulation ticks the frame it is drawing sits.
        CgsSystem::FrameInterpolation::SetEnabled(mFrameRateManager.IsDecoupledFromRenderRate());
        CgsSystem::FrameInterpolation::SetAlpha(mFrameRateManager.GetInterpolationAlpha());
        CgsSystem::FrameInterpolation::SetFrameSeconds(mFrameRateManager.GetLastFrameSeconds());
    }

    // @ BrnGameModule.cpp:1565 - render the on-screen assert overlay via the renderer module.
    void BrnGameModule::RenderAssert(const AssertData* lpAssertData)
    {
        mRenderModule.RenderAssert(lpAssertData);
    }

    // @ BrnGameModule.cpp:3981 - debug-menu "step frame" callback: begin single-stepping and
    // request one step. The void* context is the game-module instance.
    void BrnGameModule::StepFrameCB(void* lpContext)
    {
        BrnGameModule* lpThis = static_cast<BrnGameModule*>(lpContext);
        lpThis->mbSteppingFrames = true;
        lpThis->mbDoStep = true;
    }

    // @ BrnGameModule.cpp:3996 - debug-menu "play frame" callback: while single-stepping,
    // request a resume.
    void BrnGameModule::PlayFrameCB(void* lpContext)
    {
        BrnGameModule* lpThis = static_cast<BrnGameModule*>(lpContext);
        if (lpThis->mbSteppingFrames)
            lpThis->mbStopStepping = true;
    }

    // @ X360 0x823A8B38 - the disk-error worker thread body. Raises the system dirty-disc
    // error UI for the given user and never returns (the console holds on the error UI).
    // Tail-calls straight into the XDK entry point.
    void BrnGameModule::DiskErrorThreadProc(unsigned long dwUserIndex)
    {
        XShowDirtyDiscErrorUI(dwUserIndex);
    }

    // @ X360 0x823C0268 - return the embedded hardware object (the launch/soft-reboot data
    // block the platform fills at boot). The X360 forms this + 0x9A11C0, which is &mHardware.
    BrnHW::System360HW* BrnGameModule::GetSoftRebootData()
    {
        return &mHardware;
    }

    // @ X360 0x823C0288 - forward to the hardware object's invite-reboot query (the X360
    // hands it &mHardware as the System360HW `this` and tail-calls).
    int BrnGameModule::HasGameBeenRebootedDueToInvite()
    {
        return mHardware.HasGameBeenRebootedDueToInvite();
    }

    // @ X360 0x823C0278 - the soft-reboot flag. Reads a single byte at game-module + 0x9A1254,
    // which is mHardware + 0x94 (the launch-data flag byte BrnHW::System360HW::mPad94).
    int BrnGameModule::HasGameBeenSoftRebooted()
    {
        return mHardware.mPad94;
    }

    // @ X360 0x823A9030 - the game module's GameTalk "StopRenderMetrics" receiver. Walks
    // every key of the incoming message and, on the "StopRenderMetrics" key, clears the
    // render-metrics-requested flag. Same receiver shape as
    // BrnDirector::Camera::BehaviourRenderMetrics::GameTalkMessageReceiver: the context
    // module is delivered by pointer-to-pointer (lppModule).
    void BrnGameModule::RenderMetricsMessageHandler(EA::GameTalk::GameTalkMessage* lpMessage,
                                                    BrnGameModule** lppModule)
    {
        BrnGameModule* lpModule = *lppModule;
        for (s32 liIndex = 0; liIndex < lpMessage->GetNumKeys(); ++liIndex)
        {
            const char* lpcKey = lpMessage->GetKey(liIndex);
            if (_stricmp(lpcKey, "StopRenderMetrics") == 0)
                lpModule->miRenderMetricsRequested = 0;
        }
    }
}
