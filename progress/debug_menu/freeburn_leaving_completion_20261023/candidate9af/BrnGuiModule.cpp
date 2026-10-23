#include "GameSource/Gui/BrnGuiPerfmons.h"
#include "GameSource/Gui/BrnGuiModule.h"
#include "GameShared/GameClasses/Core/CgsAssert.h"
#include "GameShared/GameClasses/System/Resource/CgsResourceIOEvents.h" // original movie acquire request
#include "GameSource/Gui/BrnGuiDemangledEventTypes.h" // collision-world event 493
#include "GameSource/Resource/SharedIO/BrnGameDataEvents.h" // collision-world swap requests/replies
#include "GameSource/Resource/BrnResourceAllocator.h" // console-memory markers
#include "SDKs/EA/GameTalk/GameTalk.h"
#include "SharedClasses/Gui/SatNav/BrnMapUtils.h"   // [H3b] MapTransform (the sat-nav view-rect install)

#include <cstdio>                                                         // std::snprintf (log formatting)
#include <windows.h>                                                      // [gate] GetEnvironmentVariableA (BRN_FLAPT_AFTER_DISPATCH)
#include <chrono>   // the PC frame clock for the view time-step event (FLAG: wall clock)
#include <cstring>  // std::strcmp (ARTIST GUI-audio action-name table)

#include "GameShared/GameClasses/Core/CgsID.h"                            // CgsIDCompress
#include "GameShared/GameClasses/Development/Log/CgsLog.h"                // CgsDev::Log
#include "GameShared/GameClasses/Development/MessageSystem/CgsMessage.h" // CgsDev::Message::gxMessageFilterFlags
#include "GameShared/GameClasses/System/Resource/CgsResourceBundleLoader.h"// CgsResource::BundleLoader ([PC IO] FSM loads)
#include "GameShared/GameClasses/System/Resource/CgsResourceTypeRegistry.h"// CgsResource::ResolveResourceType
#include "GameShared/GameClasses/System/Resource/CgsResourceTypeIds.h"    // E_RESOURCETYPE_LUACODE / E_MEMTYPE_*
#include "GameShared/GameClasses/Fsm/Resources/CgsLuaCodeResource.h"      // CgsResource::LuaCodeResource
#include "GameShared/GameClasses/Gui/CgsGuiEvent.h"                       // CgsGui::GuiEvent<N> (channel command records)
#include "GameShared/GameClasses/Gui/Model/State/CgsGuiStateInterface.h"  // CgsGui::GuiEventPlayAptMovie (channel-41 payload)
#include "GameShared/GameClasses/Gui/Model/CgsEventInterpreterModule.h"   // priority removal/blocking event ids
#include "GameShared/GameClasses/Gui/Model/Resources/CgsGuiResourceModuleIO.h" // CgsGui::GuiEventLoadNotification / GuiEventLoadRequest
#include "GameSource/Gui/BrnGuiEventTypeDefs.h"                          // BrnGui::GuiAudioTriggerEvent
#include "GameSource/GameState/Progression/BrnProfile.h"                   // BrnProgression::Profile::Construct (the PC progression block seed)
#include "GameSource/Gui/BrnGuiAlwaysAvailableComponentsManager.h"        // AlwaysAvailableComponentsManager + free accessor (bodied below)
#include "GameShared/GameClasses/Gui/CgsGuiShared.h"                      // CgsGui::GuiAccessPointers (flow interface wiring)
#include "GameShared/GameClasses/Gui/View/AptInterface/CgsAptAux.h"       // CgsGui::AptAuxPointer (the AptAux singleton)
#include "GameShared/GameClasses/Gui/View/AptInterface/CgsAptCommunicator.h" // CgsGui::AptCommunicator (the per-frame trigger publish)
#include "GameShared/GameClasses/Sound/Playback/CgsCommon.h"              // CgsSound::Playback::Name::MakeHash (event-155 keys)
#include "GameShared/GameClasses/Memory/CgsLinearMalloc.h"                // FLApt live-instance allocator
#include "GameShared/GameClasses/Development/CgsStrStream.h"
#include "rw/rwcore_general_alloc.h"                                   // actual public allocator derivation
#include "GameSource/Resource/BrnGameDataModuleIO.h"                      // BrnResource::GameDataIO::Input/OutputBuffer (the colour-calibration screen's IO)
#include "GameSource/Resource/SharedIO/BrnGameDataAllocatorList.h"        // AllocatorList::GetRWLinearResourceAllocator (mGuiConfig.mpTextureAllocator)
#include "GameSource/GameFlowController/TopLevel/BrnGameMainFlowStates.h" // GetScriptedLoadGameData{Input,Output} (the PC stand-in for the scheduler's GameData IO pair)
#include "GameSource/Network/Managers/BrnNetworkLiveRevengeManager.h"      // BrnNetwork::LiveRevengeProfile (the PC live-revenge block)

// Existing PC platform providers in System/PC/CgsXboxLivePC.cpp.
extern "C" void* XNotifyCreateListener(unsigned long long luAreas);
extern "C" int XNotifyGetNext(void* lhListener, unsigned long luFilter,
    unsigned long* lpuId, unsigned long* lpuParam);

// DecFIGS types GuiModule::Construct's alternate-text palette as const RGBA*.
// ARTIST's eight packed words at 0x82F27F84 are the complete table.
struct RGBA
{
    u32 mPacked;
};

// ============================================================================
// BrnGui::GuiModule -- the GUI module. X360 GuiModule::Construct (0x82518028) builds the
// whole GUI subsystem; Update (0x82527A58) dispatches the inbound GUI events, drives the
// GuiFsmController + the flows, the MovieManager and the view chain. This PC module
// reconstructs that spine with the REAL controller chain:
//
//   BridgeGameToGui (game side) posts GuiEventRunFsm (event 144)
//     -> DispatchInboundGuiEvents -> GuiFsmController::RunFsm
//     -> the controller's load machine posts a GuiEventLoadRequest into the ModelIO input
//     -> ServiceFsmBundleRequests ([PC IO] GuiResourceModule stand-in) loads
//        FSM/<NAME>.BUNDLE and posts the GuiEventLoadNotification (14) back
//     -> GuiFsmController::Update -> BrnBaseFlow::PrepareLua -> the script SetState()s the
//        matching CgsGui::State in BrnHudFlow's 14-state pool
//   The states run under mHudFlow.Update(); everything they post drains through
//   DrainFlowOutputQueue (subscriptions 34/35, movie 508/509, view-state 41, GUI-out 40,
//   music 155 / triggers 201); each boot state posts command 70 at phase end, which the
//   game module's BridgeGuiToGame consumes to advance the game main flow.
// ============================================================================

// The loading-screen visual signal (BrnRendererModule::Render shows the loading screen
// while it's set). Driven by the REAL protocol now: the states post the loading-screen
// commands 19/20 on the GUI-out channel and the game module's BridgeGuiToGame writes the
// dispatch write buffer's command (BrnDispatchThreadInputBuffer.h).
extern bool gBrnInitialLoadingComplete;    // set by the game-flow when the load stages finish
extern bool gBrnGuiDrivesLoadingScreen;    // we set this while the HUD flow FSM is live
// The in-game flow-state latch (BrnGameMainFlowInGameState.cpp) -- gates the PC
// ignition-event stand-in in the per-frame view drive below.
namespace BrnGameMainFlowController { extern bool gBrnInGameStateActive; }
extern bool gbLogGuiAudioTriggers; // X360 byte_82FB5098; defined by CgsAptCommunicator.cpp.

namespace
{
    // ARTIST file-global Tool.GUI request owners at82FB5060/5088/5089.
    // The native image starts these bytes at zero. Construct clears only the
    // start flag; native Update consumes start before stop. Names are host projections.
    char gacGuiToolHookName[32] = {};
    bool gbGuiToolStartHookRequested = false;
    bool gbGuiToolStopHookRequested = false;

    // Host extraction of the callback's duplicated assert/copy block. Keep
    // assertion continuation and strncpy's original fixed32 behavior.
    void CopyGuiToolHookName(const char* lpcContent, s32 liOriginalLine)
    {
        if (!lpcContent)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert("lpcContent != NULL",
                "..\\..\\..\\GameSource\\Gui/BrnGuiModule.cpp", liOriginalLine);
            CgsDev::Assert::EndAssert();
        }
        if (std::strlen(lpcContent) >= 32)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::MessageBufferPC lMessage;
            CgsDev::StrStream lStream(lMessage.GetBuffer(), lMessage.GetSize());
            lStream << "String too long: " << (lpcContent ? lpcContent : "<NULLSTRING>");
            CgsDev::Assert::FireAssert(lMessage.GetBuffer(),
                "..\\..\\..\\GameShared\\GameClasses\\Core/CgsStringUtils.h", 55);
            CgsDev::Assert::EndAssert();
        }
        std::strncpy(gacGuiToolHookName, lpcContent, 32);
    }

    // [FLAG PC witness] BRN_HUD_VIS gate for the `[hud-vis] cmd` lines in the channel-42
    // drain (lane `hud`, bug-test wave 2026-09-06). NOT IN THE X360 BINARY.
    // DELETE-WHEN tools\tests\cases\hud_visibility.ps1 is retired.
    bool HudVisWitnessEnabled()
    {
        static s32 siState = -1;
        if (siState < 0)
        {
            char lacValue[8] = { 0 };
            const DWORD luLen = ::GetEnvironmentVariableA("BRN_HUD_VIS", lacValue,
                                                          sizeof(lacValue));
            siState = (luLen > 0 && lacValue[0] != '0') ? 1 : 0;
        }
        return siState != 0;
    }

    // [FLAG PC witness] BRN_FREEROAM_DIAG: one `[freeroam-gui] routed <id> -> <consumer>` line
    // per free-roam GUI event the inbound dispatch hands to the cache or the tracker, first 8
    // per id (165 repeats every frame the car sits in a landmark area).
    void FreeRoamRouteWitness(s32 liId, const char* lpcConsumer)
    {
        static const bool sbDiag = (getenv("BRN_FREEROAM_DIAG") != 0);
        if (!sbDiag || CgsDev::Log::gpDebugPrint == 0)
            return;

        static const s32 KAI_WITNESSED_IDS[] = { 64, 79, 165, 201, 211, 232, 233 };
        const s32 KI_NUM_WITNESSED_IDS =
            static_cast<s32>(sizeof(KAI_WITNESSED_IDS) / sizeof(KAI_WITNESSED_IDS[0]));
        static s32 saiLinesLeft[sizeof(KAI_WITNESSED_IDS) / sizeof(KAI_WITNESSED_IDS[0])] =
            { 8, 8, 8, 8, 8, 8, 8 };

        for (s32 liSlot = 0; liSlot < KI_NUM_WITNESSED_IDS; ++liSlot)
        {
            if (KAI_WITNESSED_IDS[liSlot] == liId)
            {
                if (saiLinesLeft[liSlot] > 0)
                {
                    --saiLinesLeft[liSlot];
                    *CgsDev::Log::gpDebugPrint
                        << "[freeroam-gui] routed " << liId << " -> " << lpcConsumer << "\n";
                }
                return;
            }
        }
    }

    // Backing for the per-flow FSM bundle pools (3 mem types each; the boot FSM scripts
    // are tiny single-state bundles ~1.5 KB -- BRNSCREENFSM is the largest at ~68 KB --
    // and each pool reserves 64 KB for its own management structures). One backing per
    // flow slot: each flow's ScriptedFsm holds its LuaCode resource while live.
    const u32 KU_FSM_POOL_BYTES = 256u * 1024u;
    u8 s_fsmPoolBacking[BrnGui::E_GUIFLOW_COUNT][CgsResource::E_MEMTYPE_NUMTYPES][KU_FSM_POOL_BYTES];
    u8 s_fsmLuaHeapBuffer[512u * 1024u];

    // Backing for the HUD flow's 14-state pool (BrnHudFlow::Prepare carves the state
    // objects out of this linear region; BootLegal is the largest at a few KB).
    u8 s_hudStatePoolBacking[512u * 1024u];

    // Backing for the overlay flow's 15-popup-state pool (X360 sizes 0x40/0x50/13x0x148;
    // sized generously for the x64 member inflation).
    u8 s_overlayStatePoolBacking[256u * 1024u];

    // Backing for the SCREEN flow's 61-state pool (X360 total ~638 KB with 4-byte
    // pointers; the big real states -- ON_GAME_ROOM 86 KB, ON_CUST_MAT 57 KB -- widen
    // on x64, so the region carries 2x headroom).
    u8 s_screenStatePoolBacking[2u * 1024u * 1024u];

    // The view's FLApt timeline tree is one linear allocation, reset when the GUI
    // module is rebuilt. ARTIST receives the GUI module's LinearAllocator here;
    // the PC owner supplies an equivalent dedicated region.
    alignas(16) u8 s_flaptLinearBacking[16u * 1024u * 1024u];
    CgsMemory::LinearMalloc s_flaptLinear;

    // Backing for the profile manager's allocators (FLAG PC stand-in: the console hands
    // the 0x26 game-data heap + a module linear; the PC module owns dedicated regions).
    // The heap carves the 3x9608 mugshot circular buffer + the SLS callback block; the
    // LINEAR carves the save/load system's mugshot image buffer
    // (miExtraFilesSizeBytes 9600 * mugshotsPerType 20 * types 5 == 960000 bytes) + the
    // content-info file buffer -- so it must clear ~1 MB (the 64 KB it had returned null
    // from SaveLoadSystem::Prepare's Malloc and tripped the mpMugshotBufferData assert).
    u8 s_profileHeapBacking[192u * 1024u];
    u8 s_profileLinearBacking[2u * 1024u * 1024u];

    // FLAG PC-platform leaf: the live-revenge profile block the console's NETWORK module
    // installs on the ProfileManager via GUI event 351 (SetLiveRevengeProfile). That
    // subsystem is not wired on PC, so mpLiveRevengeProfile stays null and
    // ProfileManager::Bootup->ReadProfileData faults (memcpy from mpLiveRevengeProfile).
    // This stand-in is a Clear()ed profile -- the current version and an empty relationship
    // table, what the console's network module installs before any save loads -- installed in
    // Prepare below. Its size is the real segment width (BrnGuiProfile.h: live-revenge is
    // memcpy'd 30016 B), asserted below.
    //
    // ⛔⛔ [one-profile wave 2026-08-28] s_pcProgressionProfileBacking (sizeof(Profile)) and
    // s_pcProgressionManifestBacking (4096 "ExpectedManifest") ARE DELETED, not moved. They
    // were a SECOND BrnProgression::Profile: the save deserialised into them while every
    // gameplay reader used GameStateModule::mProgressionManager::mProfile. The console's own
    // installer -- GuiModule::Update's case-350 arm consuming GameStateModule::PreWorldUpdate's
    // action-193 record -- now runs (see the arm and Prepare below), so both pointers are the
    // live game-state objects and neither stand-in has anything to stand in for.
    // ⛔ DO NOT RE-ADD either one to "guard" a null: the console's ProfileManager::Construct
    // zeroes both members too, and nothing dereferences them before BF_PROFILE -- which runs
    // hundreds of log lines after the first sub-step's event-350 post.
    BrnNetwork::LiveRevengeProfile s_pcLiveRevengeProfile;
    static_assert(sizeof(BrnNetwork::LiveRevengeProfile) == 30016,
                  "the live-revenge block is the 30016-byte segment the profile manager copies");

    // The subscription record the states post through StateInterface::RegisterForEvents
    // (X360 wire records 34/35: { s32 miEventType; EventObserver* } -- only the leading
    // event-type word matters to the dispatch table; the pointer is the posting observer).
    struct RegisterEventRecord
    {
        s32 miEventType;
    };

    // StateInterface::PriorityRegisterForEvent's ARTIST wire prefix. The observer
    // pointer follows at +0x968 on PPC; GuiModule already knows the posting flow, so
    // the native pointer is deliberately not part of this parser.
    struct PriorityRegisterRecordPrefix
    {
        s32 miEventType;
        s32 maiEventTypeOverridden[600];
        u32 muOverrideCount;
    };

    // The event-64 record: the module posts the GuiCache pointer each frame (the X360
    // AddEvent(&cachePtr, 64, ptr-size) in GuiModule::Update -- the states' "cache" feed).
    struct GuiEventCache : public CgsModule::Event
    {
        BrnGui::GuiCache* mpGuiCache;
    };
}

// ============================================================================
// THE APT BRING-UP (transplanted from the retired BrnGuiAptRuntime.cpp): the
// GuiModule owns the Apt bring-up driver; render callbacks use the frame owner's buffers, as the
// console GuiModule::Prepare owns the view/apt prepare chain. Every FLAG below
// is carried over unchanged; the remaining stand-in is the [PC IO] language
// string-table load (its console replacement, the CgsLanguage::Sku pump, is
// reconstructed and awaits wiring -- see the retirement plan).
// ============================================================================

#include <cstdio>    // std::snprintf (probe logging)
#include <cstring>   // std::strncpy
#include <chrono>    // steady_clock (the faithful timeline pacing's elapsed-ms source)

#include "GameShared/GameClasses/Development/Log/CgsLog.h"   // CgsDev::Log::WriteToLog

// ---- the Apt text render-data hooks (dynamic-text draw/release) --------------
#include "GameShared/GameClasses/Gui/View/AptInterface/CgsAptCallbackRender.h"   // AptCallbackRender::DrawString / DeallocateString + AptMaskRenderOperation

// ---- the Apt host adaptor + render handler (the render bridge) --------------
#include "GameShared/GameClasses/Gui/View/AptInterface/CgsAptAux.h"          // CgsGui::AptAux / AptAuxPointer
#include "GameShared/GameClasses/Gui/View/AptInterface/CgsAptRenderHandler.h"// CgsGui::AptImRendererSet / AptIm2dRenderBuffer
#include "GameShared/GameClasses/Gui/View/CgsGuiViewModule.h"                // CgsGui::ViewModule (real Apt/text owner)
#include "GameShared/GameClasses/Gui/CgsGuiModuleIO.h"                       // CgsGuiModuleIO::ImRendererSet
#include "GameShared/GameClasses/Module/CgsModuleUtils.h"
#include "GameShared/GameClasses/Development/PerfMon/Cpu/CgsPerfMonCpu.h"
#include "GameSource/Gui/BrnGuiPerfmons.h"

// ---- the Apt engine leaves that ARE bodied (the bring-up drives these) ------
#include "SDKs/EATech/Apt/DogmaAllocator.h"                   // DOGMA_PoolManager
#include "SDKs/EATech/Apt/AptValueGCPoolManager.h"            // AptValueGC_PoolManager
#include "SDKs/EATech/include/Apt/AptDefine.h"                // gpGCPoolManager / gpNonGCPoolManager
#include "SDKs/EATech/include/Apt/AptActionInterpreter.h"     // AptActionInterpreter + AptInitParmsT
#include "SDKs/EATech/include/Apt/AptTarget.h"                // AptTarget + gpAptTarget singletons
#include "SDKs/EATech/include/Apt/AptString/EAString.h"       // EAStringC (loader file name)
#include "SDKs/EATech/include/Apt/AptLoader.h"                // AptLoader / GetTarget / AptFilePtr

// ---- the original 2D command-buffer types used by the Apt render callbacks ----
#include "GameShared/GameClasses/Graphics/ImmediateMode/ImRenderBuffer/CgsImRenderBufferTemplate.h" // ImRenderBuffer<V> (AptAux render-set only)
#include "GameShared/GameClasses/Graphics/ImmediateMode/CgsIm2d.h"  // CgsGraphics::Im2d (the PROVEN immediate render path)
#include "pc/gcm/renderengine/texture.h"                      // renderengine::Texture (mesh texture binding -> mpD3DTexture)
#include "rw/rwcore_structs.h"                                // rw::ResourceAllocatorRegistry::GetDefaultAllocator

// ---- the synchronous bundle load + the Apt-data resource -> geometry path ----
#include "GameShared/GameClasses/System/Resource/CgsResourcePool.h"         // CgsResource::Pool / Entry
#include "GameShared/GameClasses/System/Resource/CgsResourceBundleLoader.h" // CgsResource::BundleLoader
#include "GameShared/GameClasses/System/Resource/CgsResourceTypeRegistry.h" // CgsResource::ResolveResourceType
#include "GameShared/GameClasses/System/Resource/CgsResourceTypeRegistration.h" // RegisterAllResourceTypes
#include "GameShared/GameClasses/System/Resource/CgsSmallResourcePS3.h"     // E_MEMTYPE_* / E_MEMTYPE_NUMTYPES
#include "GameShared/GameClasses/Gui/View/AptInterface/CgsAptDataHeader.h"  // CgsGui::AptDataHeader (relocated movie header)
#include "GameShared/GameClasses/Gui/View/AptInterface/CgsAptCommunicator.h" // AptCommunicator (the framework-bootstrap ordering gate)
#include "GameShared/GameClasses/Gui/Model/Resources/CgsGuiGeometryObjects.h" // CgsResource::GuiGeometryObject / File
#include "GameShared/GameClasses/Gui/Model/Resources/CgsGuiResourceModuleIO.h"  // CgsGui::GuiEventLoadNotification (the load-notification records)

// ---- STEP 1 FAITHFUL INSTANTIATION (gated; the direct-geometry render stays the fallback) ----
#include "SDKs/EATech/include/Apt/AptCharacterAnimation.h"    // AptCharacterAnimation::Fixup (FixupTranscode/InPlace)
#include "SDKs/EATech/include/Apt/AptConstFile.h"             // AptConstFile (pointer-size dispatch)
#include "SDKs/EATech/include/Apt/AptFile.h"                  // AptFile (synthesised loaded-file handle for instantiation)
#include "SDKs/EATech/include/Apt/AptCharacterHelper.h"       // AptGetAnimationAtLevel (the root level-0 CIH)
#include "SDKs/EATech/include/Apt/AptCharacterAnimationInst.h"// MakeCharacterAnimationInst (loaded movie -> live inst)
#include "SDKs/EATech/include/Apt/AptCIH.h"                   // AptCIH (the root display-object node)
#include "SDKs/EATech/include/Apt/AptMovie.h"                 // AptMovie::doFrameControls / resolve (timeline driver)
#include "SDKs/EATech/include/Apt/AptCharacterSpriteInstBase.h" // mDisplayList (the root CIH's child display list)
#include "SDKs/EATech/include/Apt/AptCharacterTextInst.h"     // SetTextValue/ClearStateFlags (the apt_labeltxt bridge)
#include "SDKs/EATech/include/Apt/AptAnimationTarget.h"       // AptAnimationTarget::GetRootDisplayList (the director's root list)
#include "SDKs/EATech/include/Apt/AptDisplayList.h"           // AptDisplayList::AsState
#include "SDKs/EATech/include/Apt/AptDisplayListState.h"      // AptDisplayListState::mpFirst (the placed-node chain)
#include "SDKs/EATech/include/Apt/AptCharacterInst.h"         // AptCurrentRenderTreeManager / gnCurrUpdateTick (StopMovie's removal op)
#include "SDKs/EATech/include/Apt/AptRenderTreeManager.h"     // AptRenderTreeManager::Update_ItemRemoved (StopMovie's park)

// ---- the Apt TEXT system (fonts + glyph batcher + localisation) --------------
// The PC stand-in for CgsGui::ViewModule's owned text sub-objects (GetFontCollection() /
// GetTextRenderer() / GetLanguageManager()): the bring-up constructs + loads them itself and
// hands them to AptAux::Construct so the Apt dynamic-text path lays out + draws visible glyphs.
#include "GameShared/GameClasses/Gui/View/CgsGuiFontCollection.h"   // CgsGui::FontCollection (typeface set)
#include "GameShared/GameClasses/Graphics/Font/CgsFontRenderer.h"   // CgsGraphics::TextRenderer (glyph batcher)
#include "GameShared/GameClasses/Fonts/CgsFont.h"                   // CgsResource::Font (loaded typeface)
#include "GameShared/GameClasses/System/Resource/CgsResourceTypeIds.h" // E_RESOURCETYPE_FONT
#include "GameShared/GameClasses/Language/CgsLanguageManager.h"     // CgsLanguage::LanguageManager
#include "GameShared/GameClasses/Memory/CgsHeapMalloc.h"            // CgsMemory::HeapMalloc (language allocator)
#include "pc/gcm/renderengine/device.h"                             // renderengine::gDevice (font atlas gate)

#include <cstdlib>   // malloc (font pool backing, language file block)



// ---- the Apt allocator-pool globals (X360 off_8324D808 aliases) -------------
// Declared extern in the Apt TUs (AptGlobals.cpp defines them, null). Re-declared
// here (legal redundant declarations) so this TU can WIRE them off our pools -- the
// X360 AptInit that wires them is un-reconstructed, so the bring-up does its job.
// (gpNonGCPoolManager / gpGCPoolManager come from AptDefine.h, already included.)
extern DOGMA_PoolManager* gpAptOperandStackPool;   // off_8324D808 (operand-stack arrays)
extern DOGMA_PoolManager* gpAptPseudoDataPool;     // off_8324D808
extern DOGMA_PoolManager* gpAptRenderManagerPool;  // off_8324D808
extern DOGMA_PoolManager* gpAptSharedPtrPool;      // off_8324D808
extern DOGMA_PoolManager* gpAptSingleListPool;     // off_8324D808
// gpAptValueGCPool extern RETIRED (2026-08-11): off_8324D834's three homes were
// unified onto AptDefine.h's gpGCPoolManager; this never-referenced alias
// declaration pointed at the deleted void* view.

// The interpreter VM singleton (X360 &dword_8324E760) -- defined in AptGlobals.cpp.
extern AptActionInterpreter gAptActionInterpreter;

// The faithful per-frame dynamic-text refresh pass (AptCIHBehaviour.cpp): install
// AptCIH::ProcessTextInst as the generalised-process callback + walk the root subtree,
// so every dynamic-text node re-resolves its bound text + (re)lays it out through
// EnsureStringAllocated. The console runs this inside AptUpdate (sub_82B0D608).
struct AptCIH;
void AptRunGeneralisedTextProcess(AptCIH* pRoot);

// The Apt input-recorder/replay gate (X360 byte_82F733F7; defined in AptGlobals.cpp, default 0).
// When SHUT (0) a freshly-placed clip's play-head does NOT auto-advance (deterministic replay);
// when OPEN (1) fresh clips step + run doFrameControls, placing their nested content. Normal play
// runs with the gate OPEN -- the console opens it outside replay recording. The bring-up opens it
// so the imported sprite CONTAINERS recurse + place their nested shapes/images. // FLAG: set to the
// normal-play value (the replay-recorder subsystem that would toggle it is out of this slice).
extern unsigned char gbAptRecorderGate;   // byte_82F733F7

namespace
{
    using namespace BrnGui;

    // ---- run-state flags --------------------------------------------------------
    bool s_bAllocatorReady   = false;   // DOGMA + AptValueGC pools constructed + wired
    bool s_bInterpreterReady = false;   // AptActionInterpreter::initialize done
    bool s_bAuxReady         = false;   // AptAux::Construct done (gAptFuncs render slots live)
    bool s_bTargetReady      = false;   // an AptTarget context exists (FLAG: see below)
    bool s_bRuntimeReady     = false;   // the whole bring-up succeeded
    bool s_bBringUpAttempted = false;   // ran the (idempotent) bring-up at least once

    CgsGui::ViewModule* s_pViewModule = nullptr;
    CgsMemory::LinearMalloc* s_pFlaptLinear = nullptr;   // the FLApt instance allocator (GuiModule-owned)

    // Apt render callbacks retain the view's canonical renderer set. Each
    // dispatch publishes the original main-renderer buffers into that set.

    // ---- the pending load-notification queue (the GuiResourceModule OUTPUT-BUFFER stand-in) ----
    // Every bundle the host's [PC IO] leaf loads queues one GuiEventLoadNotification per carried
    // resource here; GuiModule's frame bridge drains them into the view input buffer as view
    // events (14), and the REAL CgsGui::ViewModule::ProcessIncomingLoadNotification @0x8285BD30
    // performs the registration (AddAptData / LoadStringTable / AddFont) -- exactly the console
    // notification flow, with only the bundle IO itself host-side. FIFO ring; the records point
    // at RESIDENT pool entries, so a queued handle stays valid until drained.
    const u32 KU_MAX_PENDING_LOAD_NOTIFICATIONS = 96u;   // PERSISTENTAPT alone carries 61 AptData resources
    CgsGui::GuiEventLoadNotification s_aPendingLoadNotifications[KU_MAX_PENDING_LOAD_NOTIFICATIONS];
    u32 s_uPendingLoadNotificationWrite = 0;
    u32 s_uPendingLoadNotificationRead  = 0;
    u32 s_uNextLoadRequestId            = 0;

    // The language allocator and staged resources remain in this loader bridge for now;
    // the objects they prepare are owned by CgsGui::ViewModule.
    CgsMemory::HeapMalloc        s_AptLanguageAllocator; // backs the manager's element allocs
    CgsResource::Pool            s_AptLanguagePool;      // the resident LANGUAGE bundle pool
    // The AptAux data-handler allocator (AptAlloc/AptFree service the engine's
    // pfnMemFree + the data-handler loads through it). Host heap for the faithful
    // AptAux::Prepare drive (step 5). Host-sized: 256K OOM'd composing
    // Title_Screen02 + B5HelperComponents once the audited real allocation paths
    // went live (AptAlloc 16384-byte failure, boot-measured 2026-08-10); 8M holds
    // the full title-flow set with headroom.
    unsigned char                s_aAptDataHeap[8 * 1024 * 1024];
    CgsMemory::HeapMalloc        s_AptDataAllocator;
    bool s_bTextSystemReady = false;                     // fonts + strings loaded (one-shot)

    // The language allocator's backing heap: ~4.7K hash elements (24B each) + heap overhead.
    const u32 KU_LANGUAGE_HEAP_BYTES = 512u * 1024u;
    u8 s_aLanguageHeap[KU_LANGUAGE_HEAP_BYTES];


    // The language string-table bundle. FLAG: langid selection is host-static (0002 ==
    // langid 8, the clean English table -- verified offline: TITLES_PRESS_START ->
    // "Press START"); the console picks the bundle from the SKU/dash language.
    const char* const KC_APT_LANGUAGE_BUNDLE = "LANGUAGE/0002.bundle";

    // (The PER-MOVIE SLOTS -- framework/flow/persist/aux AptMovieSlot machinery, the
    // BF_LEGAL park latch and the per-slot tick pacing -- are RETIRED, slice 2 of the
    // runtime retirement: every movie mounts through the ENGINE chain now. BootPreload
    // plays "main" @ level 0 over channel-41 exactly like the console; AptLoadAnimation
    // -> AptLinker::Load / AptLinker::Update own the load + mount + unload, and the
    // PERSISTENTAPT component library stays a registered-data import library (the
    // GuiResourceModule's up-front bank), not a mounted movie.)

    // PHASE 2: the per-slot movie pool backings + the host bundle-IO leaf (AptLoadMovieSlot)
    // are RETIRED -- every movie slot's bundle now loads through the real GuiResourceModule's
    // [PC] servicer (CgsGuiResourceModulePC.cpp owns the streamed-apt bank), so the host no
    // longer carves its own resident movie pools here.

    // The Apt-data resource type id (X360 0x1E == 30; CgsResource::AptDataHeaderType::GetTypeID).

    // ====================================================================================
    // FAITHFUL LOAD-PATH STATE.
    //
    // The load flow is the console notification chain with only the bundle IO host-side:
    //   AptLoadMovieSlot ([PC IO] BundleLoader) -> queued GuiEventLoadNotification(s) ->
    //   GuiModule's bridge drains them as view events (14) -> the REAL ViewModule::
    //   ProcessIncomingLoadNotification @0x8285BD30 -> AptDataHandler::AddAptData; then
    //   the play-movie event drives DriveFaithfulLoad: FindAptData -> AptLoader::Load ->
    //   AptCallbackFile::LoadAnimation -> AptCompleteAnimationAsyncLoad -> CompleteLoad
    //   -> Resolve -> Fixup -> AptGetAnimationAtLevel -> MakeCharacterAnimationInst.
    // The movie root locates inside CompleteLoad (const chunk movieOffset @+0x18, the
    // XB1-attested native-8 formula); the resolve64 bounds derive inside LoadAnimation
    // from the header's size slot. The old byte-pattern root locator, the
    // gAptLoadAnimRootOverride / span pokes, and the direct AddAptData host calls are
    // RETIRED (2026-07-09, the step-5 load-ownership move).
    //
    // DEFENSIVE: the whole path is heavily guarded; ANY failure leaves the slot's
    // mbInstantiated false and the game up.
    // ====================================================================================

    // (The faithful-load state -- char-anim def base, AptFile handle, root CIH,
    //  attempted/instantiated flags -- moved into AptMovieSlot above: each of the two
    //  movies owns its own copy, keyed off the slot the load path is driven with.)
    // STAGED VM EXECUTION (2026-07-01): the deferred-action DRAIN (AptAnimationTarget::
    // RunActions after each tick). The full chain is wired + verified live -- with this
    // false the queue fills faithfully (289 enqueues to frame 100, boot green); with it
    // true the first real bytecode EXECUTES (45 ops traced: pushes, Stop, a taken
    // BranchIfTrue) but the run dies at frame ~2 in the byte-push family: a sub-clip
    // stream indexes the movie string DICTIONARY (interp mpRegisters) before any
    // DefineDictionary (0x88) stream has installed it. On the console the ordering
    // guarantee comes from the clip-event queue chain (AptCIH_queueClipEvents -- still
    // the deferred link-cluster stub) + init-action sequencing. Flip to true once that
    // cluster is homed. // (RESOLVED 2026-07-01 -- see below; the switch is retired.)
    //
    // STATUS 2026-07-01 (FINAL): the drain is PERMANENTLY ON. The frame-3 crash was a
    // straddled (never-relocated) tag-1 stream slot from a deep-nested movie (the
    // converter 4-byte-straddle family) dereferenced into a wild runStream PC -- now
    // guarded at both the enqueue (queueFrameActions) and the drain (RunActions). With
    // the CONVERTER-FIXED bundles (branch offsets corrected, 2026-07-01) the full VM
    // runs steady-state: 1243 tick+drain frames, 0 asserts, the executed stop()s hold
    // the clips faithfully.
    bool   s_bDisableRunActions    = false;

    // ---- the faithful timeline PACING (console AptUpdate/sub_82B0D608) ------------------
    // The console accumulates the ELAPSED MILLISECONDS into the root anim inst (charInst+36)
    // and ticks the display list once per movie msPerFrame (character+44 -- TITLE_SCREEN02
    // authors 33ms == 30fps), catch-up looping while the accumulator holds a full frame;
    // RunActions runs per TICK and the generalised text/mask process per UPDATE. Without
    // this the movie ticked once per RENDER frame (~170fps) and every transition played
    // ~5.7x too fast (a blink instead of an animation). The pacing state (msPerFrame,
    // accumulator, last-update clock, tick counter) is PER SLOT (AptMovieSlot above):
    // each movie ticks on its OWN authored clock, exactly as the console paces each
    // level's root anim inst separately.

    // (The import content-load registry + AptLoaderStartAsyncLoad -- the PC body
    // of the console's async .apt stream -- are RE-HOMED to the marked PC leaf TU
    // GameShared/GameClasses/Gui/PC/CgsAptStreamLoaderPC.cpp.)

    // NOTE: the Apt allocator/interpreter/target bring-up (the invented Steps 1/2/5 that
    // used to live here -- a local AptAllocatorInitialize + WireAllocatorGlobals + the
    // interpreter init + AptCreateTargetInstance) is RETIRED: it is now the faithful
    // CgsGui::AptAux::InitializeApt @0x82848E50 (CgsAptAux.cpp), which chains the homed
    // AptAllocatorInitialize/AptUpdateInitialize/AptRenderInitialize/AptCreateTargetInstance/
    // AptChangeTargetInstance (SDKs/EATech/Apt/AptInit.cpp). PrepareRuntime() below drives
    // it after AptAux::Construct has bound the canonical view renderer set.
}


namespace BrnGui
{
    // Forward declarations (definitions are `static` later in this BrnGui namespace; called
    // from PlayMovie / Update which appear before their definitions). Must be in BrnGui (not
    // the anon namespace) so the in-namespace calls bind to the static definitions.
    // (The old x64 byte-pattern root locator is RETIRED (2026-07-09):
    // AptLoader::CompleteLoad's faithful native-8 root location -- the const chunk's
    // movieOffset @const+0x18, the XB1-attested formula -- covers every bundle, so the
    // locator and its gAptLoadAnimRootOverride poke are gone. The DumpResourceBytes hex
    // probes went with them.)
    // (STEP 4 nested-content dirty propagation retired 2026-07-04 -- the AptCIH ctor births
    // fresh sprite/animation children dirty, so no host propagation pass is needed. See the
    // per-frame tick in UpdateRuntime.)


    // (AptLoadOneGuiFont RETIRED, slice 4a: the locale fonts load through the REAL
    // cache/module chain -- GuiModule::Prepare stage 13's font table {17,16},{18,16},
    // {19,16} -> GuiCache -> GuiResourceModule font bank -> type-16 notifications ->
    // ViewModule::AddFont. QueueLoadNotification below still carries the language
    // string-table record until the language request path is recovered.)

    // Queue one load notification for a loaded pool entry (see the ring's note above).
    // liRequestType carries the X360 ARTIST request-type numeric the view module's dispatch
    // switches on (12 = the localised-text bundle -- the one remaining host-queued record).
    static void QueueLoadNotification(CgsResource::Entry* lpEntry, s32 liRequestType)
    {
        if (s_uPendingLoadNotificationWrite - s_uPendingLoadNotificationRead
                >= KU_MAX_PENDING_LOAD_NOTIFICATIONS)
        {
            CgsDev::Log::WriteToLog("[AptRT] notify: pending load-notification ring FULL -- "
                                    "record dropped (FLAG).\n");
            return;
        }
        CgsGui::GuiEventLoadNotification& lrEvent = s_aPendingLoadNotifications[
            s_uPendingLoadNotificationWrite % KU_MAX_PENDING_LOAD_NOTIFICATIONS];
        lrEvent.mResourceHandle.mpResourceMemory =
            &lpEntry->mResource.m_baseResources[CgsResource::E_MEMTYPE_MAINMEMORY];
        lrEvent.mResourceHandle.mpSourceEntry = lpEntry;
        lrEvent.meRequestType   = static_cast<CgsGui::ResourceRequestTypes>(liRequestType);
        lrEvent.muLoadRequestId = ++s_uNextLoadRequestId;
        ++s_uPendingLoadNotificationWrite;
    }

    // -------------------------------------------------------------------------
    // AptLoadLanguageBundle -- load the staged LANGUAGE string-table bundle through the
    // REAL resource chain: BundleLoader -> the Language (0x27) resource -> the registered
    // LanguageResourceType::FixUp relocation -> a queued load notification (request
    // type 12), which the real ViewModule::ProcessIncomingLoadNotification routes to
    // LanguageManager::LoadStringTable @0x828664B8. Only the synchronous bundle IO is
    // host-side ([PC IO] -- the X360 streams it via the GUI resource module). The pool
    // stays resident (the manager stores the relocated string POINTERS).
    // -------------------------------------------------------------------------
    static bool AptLoadLanguageBundle(const char* lpcBundlePath, CgsResource::Pool* lpPool)
    {
        const u32 KU_LANG_POOL_BYTES = 4u * 1024u * 1024u;
        void* lpMainMem = malloc(KU_LANG_POOL_BYTES);
        if (lpMainMem == 0)
            return false;

        CgsResource::Pool::InitOptions lOptions;
        lOptions.miId    = 6;
        lOptions.mpcName = "AptLanguage";
        for (u32 lt = 0; lt < CgsResource::E_MEMTYPE_NUMTYPES; ++lt)
        {
            lOptions.maHeapInfo[lt].muMaxNodes       = 64u;
            lOptions.maHeapInfo[lt].muHeapMemorySize = KU_LANG_POOL_BYTES - 64u * 1024u;
            lOptions.maHeapInfo[lt].muHeapAlignment  = 16u;
            lOptions.mResource.m_baseResources[lt]   = lpMainMem;
            lOptions.mDescriptor.m_baseResourceDescriptors[lt].m_size      = KU_LANG_POOL_BYTES;
            lOptions.mDescriptor.m_baseResourceDescriptors[lt].m_alignment = 16u;
        }
        lOptions.muMaxResources         = 16u;
        lOptions.muMaxImports           = 16u;
        lOptions.miRefCountThreshold    = 0;
        lOptions.miNumDependencies      = 0;
        lOptions.miBankId               = 0;
        lOptions.mbAllowDefragmentation = false;
        lpPool->InitPool(&lOptions);

        CgsResource::BundleLoader lLoader;
        const s32 liLoaded = lLoader.LoadBundle(lpcBundlePath, lpPool, CgsResource::ResolveResourceType);
        char lac[224];
        if (liLoaded <= 0)
        {
            std::snprintf(lac, sizeof(lac), "[AptRT] text: language bundle '%s' FAILED to load.\n",
                          lpcBundlePath);
            CgsDev::Log::WriteToLog(lac);
            return false;
        }

        s32 liIndex = -1;
        CgsResource::Entry* lpEntry = lpPool->FindFirstResourceOfType(0x27u, &liIndex);
        if (lpEntry == 0 ||
            lpEntry->mResource.m_baseResources[CgsResource::E_MEMTYPE_MAINMEMORY] == 0)
        {
            std::snprintf(lac, sizeof(lac),
                "[AptRT] text: '%s' has no Language (0x27) resource.\n", lpcBundlePath);
            CgsDev::Log::WriteToLog(lac);
            return false;
        }

        QueueLoadNotification(lpEntry, 12);
        std::snprintf(lac, sizeof(lac),
            "[AptRT] text: language '%s' loaded -- string-table notification queued.\n",
            lpcBundlePath);
        CgsDev::Log::WriteToLog(lac);
        return true;
    }

    // -------------------------------------------------------------------------
    // AptBringUpTextSystem -- one-shot: load the 3 typefaces + the language string table
    // and arm the text system the AptAux render handler hands to the Apt string path.
    // Gated on the D3D device (the font atlas FixUp creates D3D textures); retried by the
    // (idempotent) bring-up until the device exists.
    // FLAG stand-in for the un-homed CgsGui::ViewModule::Prepare text/font bring-up (Phase 4c retires
    // this; NOT a permanent PC leaf).
    // -------------------------------------------------------------------------
    static void AptBringUpTextSystem()
    {
        if (s_bTextSystemReady)
            return;
        if (renderengine::gDevice == 0)
        {
            CgsDev::Log::WriteToLog("[AptRT] text: device not up yet -- font/language load deferred.\n");
            return;
        }

        CgsResource::RegisterAllResourceTypes();   // idempotent (Font 0x21 + raster handlers)


        // The language MANAGER is prepared by the real staged ViewModule::Prepare
        // (slice 6: its LANGUAGE stage runs mLanguageManager.Prepare; formatting
        // strings derive at LoadStringTable). Only the string-table bundle IO +
        // its queued type-12 notification remain host-side.
        const bool lbStrings = AptLoadLanguageBundle(KC_APT_LANGUAGE_BUNDLE, &s_AptLanguagePool);

        s_bTextSystemReady = lbStrings;   // fonts ride the module chain now (slice 4a)
        char lac[160];
        std::snprintf(lac, sizeof(lac), "[AptRT] text: system %s (fonts=%d strings=%s).\n",
                      s_bTextSystemReady ? "READY" : "INCOMPLETE", 0, lbStrings ? "ok" : "MISSING");
        CgsDev::Log::WriteToLog(lac);
    }

    // -------------------------------------------------------------------------
    // PrepareRuntime -- the once-only host bring-up (idempotent). Mirrors the
    // X360 CgsGui::AptAux::InitializeApt @0x82848E50 + AptAllocatorInitialize
    // @0x82ADD118, but only the pieces whose engine bodies exist; every step that
    // crosses an un-homed engine routine is // FLAG'd and skipped defensively.
    // -------------------------------------------------------------------------
    bool PrepareAptRuntime()
    {
        if (s_pViewModule == nullptr)
            return false;
        if (s_bRuntimeReady)
            return true;
        // Idempotent: each step is guarded by its own *Ready flag, so re-entry only runs
        // the preparation steps that have not yet succeeded. Log "begin" only on the
        // first attempt to avoid per-frame spam.
        if (!s_bBringUpAttempted)
            CgsDev::Log::WriteToLog("[AptRT] bring-up: begin.\n");
        s_bBringUpAttempted = true;

        // ---- STEP 4: AptAux::Construct (the host callback table + render handler) -
        // Build the ImRendererSet (3D buffers arrive from the frame renderer) and
        // hand it to AptAux::Construct, which seeds the render handler + installs the
        // gAptFuncs render-callback family (the engine's render dispatch reaches our
        // AptRenderHandler::Render through it).
        if (!s_bAuxReady)
        {
            // ViewModule::Construct already gave AptAux the address of its own
            // renderer set. Its original null slots remain until Render publishes
            // the owner-supplied buffers; runtime preparation needs no private buffer.
            // Bring the TEXT system up first (fonts + language + glyph batcher) so the
            // handler's text-layout inputs are live from the start. One-shot; device-gated.
            AptBringUpTextSystem();

            CgsGui::AptAux* lpAptAux = s_pViewModule->GetAptAux();
            s_bAuxReady = (CgsGui::AptAuxPointer::mpAptAuxInst == lpAptAux);

            char lac[200];
            std::snprintf(lac, sizeof(lac),
                "[AptRT] step4 aux: Construct done. singleton=%p renderer-set=%p\n",
                (void*)CgsGui::AptAuxPointer::mpAptAuxInst,
                (void*)s_pViewModule->GetImRendererSet());
            CgsDev::Log::WriteToLog(lac);
        }

        // ---- STEP 5: the FAITHFUL Apt runtime bring-up (AptAux::InitializeApt) ----
        // This retires the invented Steps 1/2/5 (allocator wiring, interpreter init,
        // target create) with the single faithful CgsGui::AptAux::InitializeApt @0x82848E50,
        // homed in CgsAptAux.cpp. It runs, in the console's exact order:
        //   AptAllocatorInitialize(0x10000,0x4000,0x10000,0x4000)  (the pools + wiring)
        //   AptUpdateInitialize(v8, 0)                             (config + AS interpreter)
        //   AptRenderInitialize(updated)                           (clip stack + render pool)
        //   AptCreateTargetInstance(v7) + AptChangeTargetInstance  (the live director context)
        // (the ext-object phase is FLAG'd inside InitializeApt -- it needs the deferred
        //  AptValueInitialize singletons). Matches the X360 lifecycle: AptAux::Construct
        //  (above, at "ctor" time) then AptAux::Prepare -> InitializeApt.
        //
        // Requires AptAux::Construct to have published the singleton (step 4). Idempotent:
        // once a live GetTarget() exists the runtime is already up (do not re-run).
        if (!s_bAllocatorReady)
        {
            if (!s_bAuxReady)
            {
                CgsDev::Log::WriteToLog("[AptRT] step5 InitializeApt: DEFERRED -- AptAux::Construct not done "
                                        "(view construction not complete).\n");
            }
            else if (GetTarget() != nullptr)
            {
                // Already initialised (a prior pass / another caller). Mark up.
                s_bAllocatorReady   = true;
                s_bInterpreterReady = true;
                s_bTargetReady      = true;
                CgsDev::Log::WriteToLog("[AptRT] step5 InitializeApt: already up (GetTarget() live).\n");
            }
            else
            {
                CgsDev::Log::WriteToLog("[AptRT] step5 InitializeApt: calling AptAux::InitializeApt "
                                        "(alloc + update + render + target) ...\n");
                // Drive the faithful AptAux::Prepare state machine (@0x828503E0): the
                // data-handler prepare (giving AptAlloc/AptFree a real heap), then
                // InitializeApt, then the miState0=3 seed AptAux::Update asserts on.
                // Driven through the REAL staged CgsGui::ViewModule::Prepare
                // (retirement slice 6; the mbIsNewModule store makes the base
                // stage fall through, matching the console new-module contract).
                s_AptDataAllocator.Construct(s_aAptDataHeap,
                                             static_cast<s32>(sizeof(s_aAptDataHeap)));
                s_AptLanguageAllocator.Construct(s_aLanguageHeap,
                                                 static_cast<s32>(KU_LANGUAGE_HEAP_BYTES));
                while (!s_pViewModule->Prepare(&s_AptDataAllocator, nullptr,
                                               &s_AptLanguageAllocator, s_pFlaptLinear))
                {
                }

                // Reflect the faithful init into the facade's step flags (for the channel-41
                // readiness gate + the log). InitializeApt wires the pools + interpreter and
                // publishes the target into GetTarget().
                s_bAllocatorReady   = (gpAptOperandStackPool != nullptr);
                s_bInterpreterReady = s_bAllocatorReady;
                AptTarget* lpNow    = GetTarget();
                s_bTargetReady      = (lpNow != nullptr);
                char lac[220];
                std::snprintf(lac, sizeof(lac),
                    "[AptRT] step5 InitializeApt: done. pools=%s GetTarget()=%p%s\n",
                    s_bAllocatorReady ? "wired" : "NULL(FLAG)", (void*)lpNow,
                    s_bTargetReady
                        ? " (director+loader+linker live)"
                        : " (target null -- FLAG; see the InitializeApt/AptTarget path)");
                CgsDev::Log::WriteToLog(lac);
            }
        }

        // The runtime is "ready" (for channel-41 routing) once the allocator and
        // AptAux host are up through the original view preparation. The
        // target being live lets PlayMovie + the per-frame tick reach a real GetTarget().
        s_bRuntimeReady = s_bAllocatorReady && s_bAuxReady;
        CgsDev::Log::WriteToLog(s_bRuntimeReady
            ? (s_bTargetReady
                ? "[AptRT] bring-up: READY (InitializeApt: alloc+interp+render+TARGET up; GetTarget() live).\n"
                : "[AptRT] bring-up: READY (InitializeApt: alloc+interp+render up; target FLAG'd).\n")
            : "[AptRT] bring-up: INCOMPLETE -- see step probes above.\n");
        return s_bRuntimeReady;
    }

    // (EnsureFrameworkMovie / PlayRuntimeMovie / DriveFaithfulLoad RETIRED, slice 2:
    // the engine linker mounts every movie -- see the slice note at the top. The
    // registered-data/bundle-IO completion (LoadImportBundle) lives on as the
    // body of the real AptLoaderStartAsyncLoad platform hook.)


    // PropagateDirtyToChildren (STEP 4 dirty-propagation stand-in) was RETIRED 2026-07-04: the real
    // mechanism is the AptCIH ctor (@0x82B00638) dirtying a freshly-created sprite/animation node
    // (SetDirtyState(true,true), AptCIH.cpp), so the root tick's own child-list recursion composes the
    // whole subtree per frame. The batch-dirty walk that used to live here is no longer needed.

    // -------------------------------------------------------------------------
    // RETIRED (2026-07-01): the invented direct-geometry render (RenderLoadedGeometryDirect +
    // ResolveMeshTexture) is GONE -- the movie renders through the real display-list ->
    // render-tree -> AptRenderHandler::Render -> ImRenderBuffer -> D3D9 path.
    // RETIRED (2026-07-09): the host render DRIVE (RenderRuntime's per-slot AptRender walk +
    // its s_bMovieStopped layer gating) moved to the real chain -- GuiModule::Render ->
    // CgsGui::ViewModule::Render @0x82858810 -> RenderInternal @0x82858AF8 -> AptAux::Render
    // @0x82848FB8 -> AptRenderTarget @0x82AF4ED0 (every layer, the engine's consumed-tick
    // bank). The main renderer publishes and consumes the original Im2d bank.
    // -------------------------------------------------------------------------

    // RETIRED (2026-07-09, step 6): the component view-state/key-value bridge, the
    // title help-item defaults, and their clip-walk helpers are GONE -- the REAL
    // component framework drives the menu (onLoad -> BuildName -> RegisterComponent
    // -> AddNewAptComponent; per-frame AptAux::UpdateComponents -> AptCommunicator::
    // UpdateAllComponents -> the movie AS UpdateAll -> GetComponentData).

    // Pop one queued load notification (the language string-table record). The
    // module bridge drains this ahead of the view Update. False when empty.
    bool PopPendingAptLoadNotification(CgsGui::GuiEventLoadNotification* lpOut)
    {
        if (s_uPendingLoadNotificationRead == s_uPendingLoadNotificationWrite)
            return false;
        *lpOut = s_aPendingLoadNotifications[
            s_uPendingLoadNotificationRead % KU_MAX_PENDING_LOAD_NOTIFICATIONS];
        ++s_uPendingLoadNotificationRead;
        return true;
    }

    bool AptFlowMovieLive()
    {
        // FLOW semantics: BootLegal drives this query off its channel-41 movie at
        // display level 1. Engine-native since the AptLoadAnimation retirement: the
        // linker mounts the flow movie's anim inst onto the level-1 node -- live ==
        // that node exists with a bound character inst (SetCharacterInst ran).
        AptCIH* lpNode = AptFindAnimationAtLevel(1);
        return lpNode != nullptr && lpNode->GetCharacterInst() != nullptr;
    }

    // True once the movie has COMPOSED: the root clip's first paced tick has run its
    // frame-0 place commands, so the child display list is populated (the PLACE-named
    // clips the view-state bridge targets exist). The console's equivalent gate is the
    // GuiCache apt-component handshake (AreAllAptComponentsInitialised): a component
    // reports initialised only once its clip is placed.
    bool AptFlowMovieComposed()
    {
        // FLOW semantics (BootLegal's compose gate): composed == the mounted level-1
        // movie's first paced tick ran its frame-0 place commands (child display list
        // non-empty). Engine-native read of the same node IsRuntimeMovieLive probes.
        AptCIH* lpRoot = AptFindAnimationAtLevel(1);
        if (lpRoot == nullptr)
            return false;
        AptCharacterInst* lpCI = lpRoot->GetCharacterInst();
        if (lpCI == nullptr || (lpCI->GetTypeTag() != 5 && lpCI->GetTypeTag() != 9))
            return false;
        AptDisplayListState* lpState =
            static_cast<AptCharacterSpriteInstBase*>(lpCI)->mDisplayList.AsState();
        return lpState != nullptr && lpState->mpFirst != nullptr;
    }
}


namespace BrnGui
{
    GuiModule*      gpActiveGuiModule      = 0;

    // The exact eight packed colours passed to ViewModule::Construct by ARTIST
    // (0x82F27F84, count 8).
    const RGBA KA_ALTERNATE_TEXT_COLOURS[8] =
    {
        { 0xFF000000u },
        { 0xFF00CCFFu },
        { 0xFFFFFFFFu },
        { 0xFF2864B7u },
        { 0xFFA68C4Au },
        { 0xFF0F0F9Cu },
        { 0xFF6B8A57u },
        { 0xFF33B6E6u },
    };

    // X360 GuiModule::Construct (0x82518028) builds the whole GUI subsystem. This slice
    // constructs the view module, the movie manager, and the real flow-controller chain
    // (cache + HUD flow + FSM controller).
    void GuiModule::Construct(const BrnResource::HudMessageController* lpHudMessageController,
                              const BrnResource::PopupController* lpPopupController,
                              bool lbHighDef)
    {
        // ARTIST 0x82518054: register GUI profiling handles before any view updates.
        // The registry is static; the initializer does not use its receiver.
        GuiPerfmons().Initialise();

        // X360 GuiModule::Construct @0x82518028, pseudocode lines 327-332 -- the console's
        // own argument assert, fired before anything is built.
        CGS_ASSERT(lpHudMessageController != 0, "lpHudMessageController");   // BrnGuiModule.cpp:229
        CGS_ASSERT(lpPopupController != 0, "lpPopupController");

        // Route through the real BrnGui::ViewModule::Construct @0x824F13B8 with the X360
        // caller's recovered args: the view flapt count (7), a 16:9 aspect, and the real
        // alternate-text-colours table + count 8 (see the static above). The
        // X360 passes a null debug name here; the descriptive "BrnGuiView" is a harmless
        // non-null label the base accepts.
        mViewModule.Construct(this, "BrnGuiView", 7, 1280.0f / 720.0f,
                              KA_ALTERNATE_TEXT_COLOURS, 8);
        // ARTIST825184E4: construct the actual shared Model and stored-event
        // owner. Native preparation/update selection remains with its caller.
        CgsGui::GuiModule::Construct(&mViewModule, lbHighDef);
        mViewModule.GetFlaptManager()->SetSoundTriggerHandler(
            &GuiModule::FlaptSoundTriggerCallback, this);
        // X360 GuiModule::Construct @0x82518B18: EffectsArbitrator::Construct just ahead of
        // MovieManager::Construct + ColourCalibrationScreen::Construct.
        muFrameUpdateSet = 0;
        mEffectsArbitrator.Construct();
        mMovieManager.Construct();
        // ARTIST82518B88 initializes the actual boot-movie owner byte.
        mbBootMovieMode = true;
        // ARTIST82518858: distinct from primary Prepare and release stages.
        mePrepareStage = E_PREPARE_START;
        muPrepare2State = 0;
        meReleaseStage = E_RELEASE_DONE;
        // X360 GuiModule::Construct @0x82518B18-24: MovieManager::Construct is immediately
        // followed by ColourCalibrationScreen::Construct (gm+301600 then gm+306752), with
        // EffectsArbitrator::Construct just ahead of the pair.
        mColourCalibrationScreen.Construct();
        // ARTIST82518028: these values seed the collision-world and car-pool validators.
        meCollisionWorldStateValidationState = E_COLLISIONWORLDSTATEVALIDATIONSTATE_IDLE;
        mbCollisionWorldInvalid = false;
        meCarPoolStateValidationState = E_CARPOOLSTATEVALIDATIONSTATE_IDLE;
        mbCollisionWorldInvalidateForNetworking = false;
        mbCollisionWorldValidateForNetworking = false;

        // ---- [profile-save] THE AUTOSAVE LATCH'S OWN INITIALISERS -------------------------
        // X360 GuiModule::Construct @0x82518028, the run that immediately follows
        // ColourCalibrationScreen::Construct (pseudocode lines 413..421):
        //     *(gm + 1628216..1628220) = 0;      // the four sibling bytes (not landed here)
        //     *(gm + 1628224)          = 0.0;    // mfLastProfileAutosaveTime
        //     *(gm + 1628228)          = 0;      // mbProfileAutosavePending
        // ⛔ These two were MISSING from the pair's landing commit, which left the tail's
        // `if (mbProfileAutosavePending)` reading an indeterminate byte on the first Update.
        mfLastProfileAutosaveTime = 0.0f;
        mbProfileAutosavePending  = false;
        // The console keeps the FORCE flag in a per-Update stack byte it zeroes at the top of
        // Update (@0x82527A58, `v142 = 0` before the event walk). This build carries it as a
        // member (the walk and the tail are two functions), so it gets the same defined start
        // here; the tail clears it again at the end of every Update.
        mbForceProfileAutosave    = false;

        mAlwaysAvailableComponentsManager.Construct();

        // X360 GuiModule::GuiModule @0x827E5B28 constructs the custom-renderer manager as a
        // by-value member; GuiModule::Construct @0x82518028 then drives its Construct.
        // ⭐ This is the object the Apt custom-control render callback reaches through
        // AptRenderHandler::mpCustomRendererManager -- until this leg NOTHING in the PC
        // build instantiated it, so `_type='PlayerImage'` on the licence card (and every
        // other custom control) had nowhere to resolve to.
        // ARTIST82518BB0..BD0: bind this receiver's own backing with 1024/16, then Clear.
        mEventReceiverQueue.Construct();
        // ARTIST82518BD4..C0C: the collision validator has its own 1024/16 receiver.
        mCollisonPoolValidationReceiverQueue.Construct();
        // ARTIST82518BF0..C0C: the real receiver owns its backing storage.
        mGDMReceiverQueue.Construct();
        gbGuiToolStartHookRequested = false; // ARTIST82518C38..82518C44
        mhSysListenerHandle = 0; // ARTIST82518C48, before serialiser Construct
        mGuiModuleSerialiser.Construct(); // ARTIST82518C4C, before manager Construct
        mCustomRendererManager.Construct();

        // ⭐ X360 GuiModule::Construct's LAST TWO ACTIONS, @0x82518D2C-54:
        //     addis r30, r31, 5 ; addi r30, r30, -0x3D70   ; r30 = gm + 311952 (the manager)
        //     mr r3, r30 ; lwz r11,0(r30) ; lwz r11,0(r11) ; mtctr r11 ; bctrl   ; its Construct
        //     addis r4, r31, 5 ; mr r3, r30 ; addi r4, r4, -0x6E80
        //     bl BrnGui__CustomRendererManager__SetFlaptRenderer
        // The argument is gm + 327680 - 28352 - 64... i.e. +299392, which is
        // mViewModule (gm+132224) + mFlaptManager (view +0x28CC0 == +167104) + mRenderer
        // (+0x40): 132224 + 167104 + 64 == 299392 exactly. (The sibling constant at
        // @0x82518C6C, gm+299328, is the FlaptManager itself -- the `this` the
        // SetSoundTriggerHandler call above uses.)
        // ⛔ THIS CALL WAS MISSING, and the setter it drives was writing the wrong field
        // (see BrnCustomRenderer.cpp), so NetworkPlayerImageRenderer::mpFlaptRenderer had
        // ZERO writers in this build. It is read by SwapBuffers, which the newly-wired
        // GuiModule::EndOfFrame runs every frame -- without this line that is a
        // "mpFlaptRenderer" assert per frame, not a fix.
        mCustomRendererManager.SetFlaptRenderer(&mViewModule.GetFlaptManager()->mRenderer);

        mpGuiEventInputBuffer = 0;
        mbRenderInputCompletedPC = false;
        mCompletedRenderInputPC.Construct();
        mpOutputBuffer = 0;
        mGuiConfig.mpTextureAllocator = 0;   // retained selected PC initialization
        mGuiConfig.mpRendererAllocator = 0;  // retained selected PC initialization
        mbCustomRenderersPrepared = false;   // [licence-icon] the manager staged-prepare latch

        // The flow-controller chain (the X360 Construct's flow set): the cache Construct
        // (the watcher reset @0x82505860 -> 0x824FD978), then the profile manager (X360
        // GuiModule::Construct @0x82518028 hands it the cache, the sign-in watcher, and
        // the view module's language manager), then the flows against the cache; the
        // controller starts UNLOADED on every flow slot.
        // ⭐⭐ THE SAT-NAV TRACKER, Constructed BEFORE the cache exactly as the console does.
        // X360 GuiModule::Construct @0x82518028 emits the tracker's inlined Construct at
        // @0x82518874..@0x825188C8 (off r29 == gm+1131872) and only then calls
        // GuiCache::Construct @0x82518948 with `mr r4, r29`. Order matters here for the same
        // reason it does on the console: the cache's own "Invalid tracker pointer" assert
        // (BrnGuiCache.cpp:1226) fires on a pointer that is handed over before its object is
        // initialised, and every reader downstream (GetGuiTracker) gets the live one.
        mGuiTracker.Construct();

        // X360 @0x8251893C..@0x82518948, verbatim:
        //     mr r5, r26   ; the module's CgsGui::SystemUserProfile @gm+949152
        //     mr r4, r29   ; the module's GuiTracker              @gm+1131872
        //     mr r3, r27   ; the GuiCache                         @gm+1005376
        //     bl BrnGui::GuiCache::Construct
        // ⭐ This is the WRITER of GuiCache::mpGuiTracker (+0x4054) the tree never had.
        mGuiCache.Construct(&mGuiTracker, &mSystemUserProfile);

        // X360 GuiModule::Construct @0x82518028, the two lines that follow GuiCache::Construct
        // and MapIconManager::Construct: Construct the module's own WorldDataController (the
        // seven inlined stores at gm+307836..+309028 + the receiver-queue Clear) and bind it
        // into the cache (`*(gm + 1021860) = gm + 307836`, guarded by the "lpController"
        // assert at BrnGuiCache.h:2310). This is the pointer every GUI component that resolves
        // a car / landmark / event through GuiCache::GetWorldDataController reaches.
        mWorldDataController.Construct();
        mGuiCache.SetWorldDataController(&mWorldDataController);

        // [H3b] X360 GuiModule::Construct: MapIconManager::Construct(gm+1088304, cache)
        // right after the cache/world-data wiring, then the cache binding + the sat-nav
        // view-rect pick + the mask matrix build (the @0x82518A2C..@0x82518A64 run).
        mMapIconManager.Construct(&mGuiCache);
        mGuiCache.SetMapIconManager(&mMapIconManager);
        // ⭐ THE HIGH-DEFINITION BYTE (issue #11). X360 @0x82518A24: `*(gm + 1024649) = a6`
        // -- 1024649 - 1005376 == 19273 == GuiCache +0x4B49, the byte BootLegal::Update,
        // MainMapComponent::Construct, CrashNavMapMain, CrashNavDriverDetails and
        // RoadSignIconManager all read to choose between their HD and SD constants. This
        // store is the byte's ONLY writer in the image; without it the cache said SD.
        mGuiCache.SetIsHighDefinition(lbHighDef);
        {
            // [FLAG PC witness] once, unconditional -- tools/tests/cases/hd_ui_flag.ps1 reads it.
            char lacLine[160];
            std::snprintf(lacLine, sizeof(lacLine),
                          "[GuiModule] high-definition=%d (GuiCache +0x4B49; display %dx%d)\n",
                          lbHighDef ? 1 : 0,
                          static_cast<int>(renderengine::gDisplayWidth),
                          static_cast<int>(renderengine::gDisplayHeight));
            CgsDev::Log::WriteToLog(lacLine);
        }
        // @0x82518A2C..A64: the sat-nav view rect pick, `a6 ? unk_82FB30A0 : unk_82FB3130`
        // stored to the live rect @0x82FB36A0.
        MapTransform::SetSatNavRect(lbHighDef ? MapTransform::GetSatNavViewRectHD()
                                              : MapTransform::GetSatNavViewRectSD());
        SetMaskAspectCorrectionMatrix(&mGuiCache);

        // ⭐ [stuntrace] THE FREEBURN-CHALLENGE MANAGER HAND-OFF -- the missing writer of
        // GuiCache::mpChallengeManager. X360 GuiModule::Construct @0x82518028, the two lines
        // that follow the mask-matrix build and the BurnoutSkillsManager pair, verbatim:
        //     BrnGui::FreeburnChallengeManager::Construct(gm + 309584, gm + 1005376);
        //     if (gm == -309584) { ... FireAssert("lpChallengeManager",
        //                          "..\\..\\..\\GameSource\\Gui/BrnGuiCache.h", 2374); ... }
        //     *(gm + 1021868) = gm + 309584;          // == GuiCache +0x406C
        // (1021868 - 1005376 == 16492 == 0x406C, the member BrnGuiCache.h:1105 pins.) The
        // setter carries the console's own assert, so nothing is restated here.
        //
        // This is the GUI-OBJECT half of the freeburn-challenge chain and is SEPARATE from the
        // challenge-LIST data half (GameDataModule streams OnlineChallenges.bndl and
        // WorldDataController publishes the list GuiCache::GetFreeburnChallengeList returns).
        // The list landed first; this pointer had no producer at all, which is what made
        // RaceMainHudState::UpdateRunning's case-6 arm (BrnRaceMainHudState_wS3.cpp:261, an
        // UNCONDITIONAL GetFreeburnChallengeManager per controller-input event) fire
        // "mpChallengeManager" once per input frame for the whole of a live stunt race.
        //
        // The console's BurnoutSkillsManager pair sits between the mask matrix and this one:
        // the module's skills manager is constructed against the cache and bound as
        // GuiCache::mpSkillsManager (the "lpSkillsManager" assert is the setter's).
        mBurnoutSkillsManager.Construct(&mGuiCache);
        mGuiCache.SetSkillsManager(&mBurnoutSkillsManager);
        mFreeburnChallengeManager.Construct(&mGuiCache);
        mGuiCache.SetChallengeManager(&mFreeburnChallengeManager);

        // X360 GuiModule::Construct wires the shared state-access bundle here, before
        // any flow is allowed to run: ViewModule::GetAptAux/GetLanguageManager,
        // ViewModule::GetFlaptManager, and this GuiCache are the four live owners.
        // AptAux itself is installed during Prepare below because the PC runtime host
        // constructs that singleton there; the other three owners already exist.
        mGuiAccessPointers.Construct();
        mGuiAccessPointers.mpLanguageManager = mViewModule.GetLanguageManager();
        mGuiAccessPointers.SetFlaptManager(mViewModule.GetFlaptManager());
        mGuiAccessPointers.SetGuiCache(&mGuiCache);
        // ARTIST82518CE8/D24: publish the actual contained receiver and serialiser.
        // The serialiser's static buffer is allocated by the replay owner later.
        mGuiAccessPointers.SetGDMReceiverQueue(&mGDMReceiverQueue);
        mGuiAccessPointers.SetSerialiser(&mGuiModuleSerialiser);

        // ARTIST82518798/A0/A8: the profile watcher owns these three initial stores.
        mSystemUserProfile.Construct();
        mProfileHost.GetProfileManager().Construct(mGuiCache, mSystemUserProfile,
                                  mViewModule.GetLanguageManager());
        // ARTIST825187CC/D0/D4: real contained keyboard and listener host.
        mGuiKeyboard.Construct();
        mKeyboardHost.Construct();
        mScreenFlow.Construct(&mGuiCache);
        mHudFlow.Construct(&mGuiCache);
        mOverlayFlow.Construct(&mGuiCache);
        // ARTIST82518570/580/590/5A0: the four real observer owners, event0.
        mGuiModel.AddGuiEventObserver(&mHudFlow, 0);
        mGuiModel.AddGuiEventObserver(&mScreenFlow, 0);
        mGuiModel.AddGuiEventObserver(&mOverlayFlow, 0);
        mGuiModel.AddGuiEventObserver(&mAlwaysAvailableComponentsManager, 0);
        mFsmController.Construct();

        // ARTIST82518720 and the inlined overlay Construct: both directors receive the real contained
        // Model. Their original publishers are restored together (CP16).
        mHudMessageDirector.Construct(&mGuiModel, &mGuiCache);
        mHudMessageAnalyzer.Construct(&mHudMessageDirector);
        mOverlaysDirector.Construct(&mGuiModel);

        // ARTIST825187D8..82518818: actual debug subobjects, after their real director owner.
        // Their C++ constructors installed only vtables/queue flags; this is their data phase.
        mDebugComponent.Construct(this);
        mHudMessageDebugComponent.Construct(&mHudMessageDirector);
        mSatNavDebugComponent.Construct(this);
        mGuiCacheDebugComponent.Construct(this);

        // ⭐ [gateui r4] THE CONTROLLER HAND-OFF -- the missing writer of
        // GuiCache::mpHudMessageController. X360 GuiModule::Construct @0x82518028
        // pseudocode lines 362-368, IMMEDIATELY before the director store:
        //     if ( !a2 ) { BeginAssert; FireAssert("lpController",
        //                  "..\\..\\..\\GameSource\\Gui/BrnGuiCache.h", 2405); EndAssert; }
        //     *(a1 + 1021872) = a2;                     // == GuiCache +0x4070, mpHudMessageController
        //     if ( a1 == -639264 ) { ... "lpDirector", BrnGuiCache.h, 2433 ... }
        //     *(a1 + 1021876) = a1 + 639264;            // == GuiCache +0x4074, mpHudMessageDirector
        // (1021872 - 1005376 == 16496 == 0x4070 and 1021876 - 1005376 == 16500 == 0x4074,
        // the two members BrnGuiCache.h:917/918 pin -- so the console's order really is
        // controller THEN director.) The setter carries the console's assert already, so the
        // CGS_ASSERT below is the ARGUMENT one (BrnGuiModule.cpp:229) re-stated at the point
        // of use rather than a second copy of BrnGuiCache.h:2405.
        CGS_ASSERT(lpHudMessageController != 0,
                   "lpHudMessageController (GuiCache::mpHudMessageController would stay null "
                   "and every HUD message would die at FilterAndSendOffMessage's mpController "
                   "assert)");
        mGuiCache.SetHudMessageController(lpHudMessageController);

        mGuiCache.SetHudMessageDirector(&mHudMessageDirector);
        // The popup controller: the console's third argument, stored right after the
        // director (GuiCache +0x4078).
        mGuiCache.SetPopupController(lpPopupController);

        // The REAL GUI resource-loading module + its persistent IO pair (replaces the
        // host FSM-bundle stand-in). Construct the IO buffers (their embedded queues come
        // up here) and the module. The HD flag is the console's own argument (the same a6
        // the cache byte above took): it picks GuiApt\ vs GuiAptSD\, FLAPTHUD vs FLAPTHUDSD
        // and Fonts\ vs FontsSD\ (the FSM bundle path itself is HD-independent). Construct
        // seeds the module counters/stages + marks it a new-module type (its base Prepare
        // then skips the old-module IO-structure lock path -- no assert).
        mResourceInputBuffer.Construct();
        mResourceOutputBuffer.Construct();
        mGuiResourceModule.Construct(lbHighDef);

        for (s32 lf = 0; lf < KI_NUM_EVENT_OBSERVERS; ++lf)
        {
            for (s32 li = 0; li < KI_MAX_OBSERVED_EVENT_ID; ++li)
                mabObservedEventIds[lf][li] = false;
            mabPriorityBlocking[lf] = false;
            for (s32 lc = 0; lc < KI_MAX_PRIORITY_CLAIMS_PER_FLOW; ++lc)
            {
                PriorityClaim& lrClaim = maPriorityClaims[lf][lc];
                lrClaim.mbActive   = false;
                lrClaim.miEventType = -1;
                for (s32 li = 0; li < KI_MAX_OBSERVED_EVENT_ID; ++li)
                    lrClaim.mabOverriddenEventIds[li] = false;
            }
        }
        // ⭐ THE EVENT-64 CACHE HAND-OFF -- the console's own tail of GuiModule::Construct,
        // two lines before its GuiAccessPointers block:
        //     v102[0] = a1 + 1005376;                              // the GuiCache
        //     BrnGui::GuiTracker::RecEvent(a1 + 1131872, v102, 64, 4);
        // (The 4 is the X360's 32-bit pointer size; RecEvent never reads the size argument,
        // so the host passes sizeof the record it actually built.) The arm latches
        // mpGuiCache and seeds mPlayersTrackerInfo from the cache's world-camera lane
        // (GuiCache +0x4AE0), which is the tracker's own view of where the player is.
        // ⚠️ The console re-posts 64 on every cache update; this build posts it once, at
        // construction -- so the tracker's player record does not follow the camera yet.
        // Named as the known gap (see the RecEvent banner in BrnGuiTracker.h), not papered
        // over: the 232 publish path that draws the route line does not depend on it.
        {
            GuiEventCachePointer lCachePointerEvent;
            lCachePointerEvent.mpCachePointer = &mGuiCache;
            mGuiTracker.RecEvent(
                reinterpret_cast<const CgsModule::Event*>(&lCachePointerEvent), 64,
                static_cast<s32>(sizeof(lCachePointerEvent)));
        }

        mbResourcesReadyFed = false;
        mbPrepared          = false;
    }

    // ARTIST82518E9C..82519024, extracted from the original inline memory
    // stage. No selected host caller invokes this helper yet.
    void GuiModule::PopulateNativeGuiConfig(
        const BrnResource::GameDataIO::OutputBuffer* lpGameDataOutput)
    {
        if (!lpGameDataOutput->GetAllocatorList())
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::MessageBufferPC lMessage;
            CgsDev::StrStream lStream(lMessage.GetBuffer(), lMessage.GetSize());
            lStream << "Invalid allocator list passed into BrnGui::GuiModule::Prepare";
            CgsDev::Assert::FireAssert(lMessage.GetBuffer(),
                "..\\..\\..\\GameSource\\Gui/BrnGuiModule.cpp", 367);
            CgsDev::Assert::EndAssert();
        }
        mGuiConfig.miAptPersistentBunldePoolId = 8;
        mGuiConfig.miAptStreamedbundlePoolId = 9;
        mGuiConfig.miFontBundlePoolId = 0;
        mGuiConfig.miGlobalTexturePoolId = 10;
        mGuiConfig.miFSMBunldePoolId = 11;
        mGuiConfig.miLanguageBundlePoolId = 11;
        mGuiConfig.miTexturesBundlePoolId = 12;
        mGuiConfig.mpAptAllocator = lpGameDataOutput->GetAllocatorList()->GetHeapAllocator(32);
        mGuiConfig.mpFSMAllocator = lpGameDataOutput->GetAllocatorList()->GetHeapAllocator(38);
        mGuiConfig.mpRendererAllocator =
            lpGameDataOutput->GetAllocatorList()->GetRWGeneralResourceAllocator(31);
        mGuiConfig.mpLanguageAllocator = lpGameDataOutput->GetAllocatorList()->GetHeapAllocator(38);
        mGuiConfig.mpGuiStateAllocator = lpGameDataOutput->GetAllocatorList()->GetLinearAllocator(44);
        mGuiConfig.mpTextureAllocator =
            lpGameDataOutput->GetAllocatorList()->GetRWLinearResourceAllocator(42);
        mGuiConfig.mpFlaptAllocator = lpGameDataOutput->GetAllocatorList()->GetLinearAllocator(66);
        mGuiConfig.mpGuiStateAllocator->SetAlignment(16);
        mGuiConfig.mpFlaptAllocator->SetAlignment(16);
    }

    // ARTIST825193C8..82519444. Counts and tuple words are recovered
    // directly from the three original tables; enum ordinals are target values.
    // This extracted block has no selected host caller.
    bool GuiModule::EnsureNativeGuiResources()
    {
        static const CgsGui::sResourceTuple maEuropeanFontResourcesToLoad[3] =
        {
            { 17u, static_cast<CgsGui::ResourceRequestTypes>(16) },
            { 18u, static_cast<CgsGui::ResourceRequestTypes>(16) },
            { 19u, static_cast<CgsGui::ResourceRequestTypes>(16) },
        };
        static const CgsGui::sResourceTuple maJapaneseFontResourcesToLoad[2] =
        {
            { 20u, static_cast<CgsGui::ResourceRequestTypes>(16) },
            { 21u, static_cast<CgsGui::ResourceRequestTypes>(16) },
        };
        static const CgsGui::sResourceTuple maBasicResourcesToLoad[2] =
        {
            { 125u, static_cast<CgsGui::ResourceRequestTypes>(7) },
            { 196u, static_cast<CgsGui::ResourceRequestTypes>(10) },
        };
        const CgsGui::sResourceTuple* lpFonts;
        u32 luFontCount;
        if (mGuiCache.GetLanguage() == CgsLanguage::E_LANGUAGE_JAPANESE)
        {
            lpFonts = maJapaneseFontResourcesToLoad;
            luFontCount = 2;
        }
        else
        {
            lpFonts = maEuropeanFontResourcesToLoad;
            luFontCount = 3;
        }
        if (!mGuiCache.EnsureResourcesAreLoaded(lpFonts, luFontCount))
            return false;
        return mGuiCache.EnsureResourcesAreLoaded(maBasicResourcesToLoad, 2);
    }

    // ARTIST824F10D8. GameTalk's actual MessageHandler contract is void.
    // Registration belongs to native Prepare and remains unselected here.
    void GuiModule::GameTalkMsgHandler(EA::GameTalk::GameTalkMessage* lpMessage)
    {
        const char* lpcKey = lpMessage->GetKey(0);
        if (_strnicmp(lpcKey, "StartHook", 9) == 0)
        {
            CopyGuiToolHookName(lpMessage->GetKeyContent("StartHook"), 3554);
            gbGuiToolStartHookRequested = true;
        }
        else if (_strnicmp(lpcKey, "StopHook", 8) == 0)
        {
            CopyGuiToolHookName(lpMessage->GetKeyContent("StopHook"), 3564);
            gbGuiToolStopHookRequested = true;
        }
        else if (_strnicmp(lpcKey, "StopMenuHook", 12) == 0)
        {
            std::strncpy(gacGuiToolHookName, "", 32);
            gbGuiToolStopHookRequested = true;
        }
    }

    bool GuiModule::Prepare()
    {
        // ---- X360 GuiModule::Prepare @0x82518D68, STAGE 1 (the mGuiConfig fill) -----------
        // The console's stage 1 reads seven pool ids and seven allocators out of the GameData
        // OUTPUT buffer's AllocatorList. The selected PC path keeps its existing two rows:
        //     *(gm + 311932) = AllocatorList::GetRWLinearResourceAllocator(list, 42)
        // (0x82518DE0's `ori r21, r11, 0xC27C`), the allocator ColourCalibrationScreen::Update
        // carves its texture-state resource from. Bank 42 is "Network Image Allocator" and is
        // a real RW-LINEAR bank on this build (BrnMemoryMapData.h:109), created by
        // GameDataModule::CreateAllocators.
        // FLAG PC drive point: the console's module scheduler hands GuiModule::Prepare the
        // GameData IO pair; on PC the pair is the one the whole scripted load already uses.
        // The ordering that makes this safe is proven, not assumed: BrnGameModule::GamePrepare
        // runs `mGameDataModule.Prepare(0,0)` to completion (returning false until done) and
        // the loading flow -- which is what calls GuiModule::Prepare -- only runs once
        // GamePrepare has returned done, so CreateAllocators has already registered bank 42.
        // Read once here, exactly as the console reads it once in Prepare.
        // NO LOCK PAIR OF ITS OWN (step-11 verifier catch): the only caller,
        // InitialLoadingScreen's stage-2 leg in BrnGameMainFlowStates.cpp (:691 LockForRead ..
        // :1073 Prepare() .. :789 UnlockForRead), already holds this buffer's read lock, and
        // CgsModule::IOBuffer's lock is a single status BIT (CgsIOBuffer.h:26/:42), not a count --
        // an inner Unlock would clear the caller's lock and its own UnlockForRead would then assert
        // "Not locked for read". GetAllocatorList's read assert is satisfied by the caller's bracket.
        mGuiConfig.mpTextureAllocator = 0;
        mGuiConfig.mpRendererAllocator = 0;
        {
            BrnResource::GameDataIO::OutputBuffer* lpGameDataOutput =
                BrnGameMainFlowController::GetScriptedLoadGameDataOutput();
            if (lpGameDataOutput != 0)
            {
                // (IsBufferLockedForReading is protected; GetAllocatorList's own read assert
                // is the check.)
                const BrnResource::GameDataIO::AllocatorList* lpAllocators =
                    lpGameDataOutput->GetAllocatorList();
                if (lpAllocators != 0)
                {
                    mGuiConfig.mpTextureAllocator = lpAllocators->GetRWLinearResourceAllocator(42);
                    mGuiConfig.mpRendererAllocator =
                        lpAllocators->GetRWGeneralResourceAllocator(31);
                }
            }
        }

        // Load VIDEOS\VIDEOLIST.BUNDLE synchronously (English; see MovieManager::Prepare) and
        // publish the manager so the renderer draws the active movie each frame (interim render
        // bridge; the X360 renders it through the GUI's own ViewIO ImRenderers).
        mMovieManager.Prepare(0);
        PrepareNativeDebugComponents();
        gpActiveMovieManager = &mMovieManager;
        gpActiveGuiModule = this;

        // The FSM Lua VM heap (the controller's allocator) + the HUD state pool.
        mFsmLuaHeap.Construct(s_fsmLuaHeapBuffer, static_cast<s32>(sizeof(s_fsmLuaHeapBuffer)));
        mHudStatePool.Construct();
        mHudStatePool.Create(s_hudStatePoolBacking, sizeof(s_hudStatePoolBacking));

        // The FLApt linear allocator must exist BEFORE the view-module prepare: the
        // staged BrnGui::ViewModule::Prepare's FLAPT stage seeds every
        // FlaptFileInstance from it (a null here leaves null instance allocators --
        // the state machine one-shots at DONE and never re-seeds).
        s_flaptLinear.Construct();
        s_flaptLinear.Create(s_flaptLinearBacking, sizeof(s_flaptLinearBacking));
        s_flaptLinear.SetAlignment(16);

        // Stand up the GUI-owned Apt runtime host (allocator + interpreter + AptAux host
        // callback table) BEFORE the flow prepares, so the flow
        // states' access pointers can reach the AptAux singleton. Idempotent + defensive.
        // The host drives the REAL staged (virtual) ViewModule::Prepare, whose FLAPT
        // stage prepares the FlaptManager with this linear -- the console prepare shape
        // (the separate FlaptManager::Prepare call is retired with it).
        s_pViewModule  = &mViewModule;
        s_pFlaptLinear = &s_flaptLinear;
        PrepareAptRuntime();

        // Complete the shared access bundle with the AptAux singleton created by the
        // PC runtime host above.  Construct already installed the language, Flapt, and
        // GuiCache owners exactly as the X360 GuiModule::Construct does.
        mGuiAccessPointers.mpAptAux = CgsGui::AptAuxPointer::mpAptAuxInst;

        // ---- X360 GuiModule::Prepare @0x82518D68, STAGE 7 -------------------------------
        //   v27 = (*(*(v3+311952) + 4))(v3+311952, rwGeneralResource, rwLinearResource);
        //   CgsGui::ViewModule::SetCustomRendererManager(v3+132224, v3+311952, 10, v3+1629284);
        //   if (!v27) goto fail;
        // Order matters and is reproduced: the manager is Prepared FIRST, installed SECOND,
        // and the prepare result is only gated on afterwards -- so the view module gets the
        // manager pointer even on a not-yet-finished staged prepare.
        //
        // ⚠️ It MUST be installed after PrepareAptRuntime() above, because
        // ViewModule::SetCustomRendererManager mirrors the pointer into
        // mAptAux.mRenderHandler and AptAux::Construct clears that same slot to 0.
        //
        // ⭐ [licence-icon] 2026-08-24: the allocator FLAG that stood here is PAID -- the call
        // now passes the console's own pair (stage 1 above fills both mGuiConfig rows: slot 31
        // general -> mGuiConfig.mpRendererAllocator, slot 42 linear -> mGuiConfig.mpTextureAllocator; the X360 stage-7
        // call is `Prepare(*(gm+311924), *(gm+311932))` @0x82518D68). One call advances the
        // staged prepare as far as it can this frame; the console re-enters Prepare until every
        // stage passes, so Update owns the PC pump (see the [licence-icon] block there).
        const bool lbCustomRenderersPrepared =
            mCustomRendererManager.Prepare(mGuiConfig.mpRendererAllocator, mGuiConfig.mpTextureAllocator);
        mbCustomRenderersPrepared = lbCustomRenderersPrepared;
        mViewModule.SetCustomRendererManager(&mCustomRendererManager, 10,
                                             &mGuiModuleSerialiser);
        (void)lbCustomRenderersPrepared;   // the console's `if (!v27) return 0;` -- see FLAG
        {
            char lacProbe[192];
            std::snprintf(lacProbe, sizeof(lacProbe),
                          "[custrend] manager installed: prepared=%d numComponents=%d "
                          "slot0(PlayerImage) id=%016llX renderable=%d\n",
                          lbCustomRenderersPrepared ? 1 : 0,
                          mCustomRendererManager.GetNumComponents(),
                          static_cast<unsigned long long>(
                              mCustomRendererManager.GetComponentID(BrnGui::E_NETWORK_PLAYER_IMAGE)),
                          mCustomRendererManager.GetComponentRenderable(
                              BrnGui::E_NETWORK_PLAYER_IMAGE) ? 1 : 0);
            CgsDev::Log::WriteToLog(lacProbe);
        }

        // The REAL flow bring-up: base prepare (access pointers into the StateInterface)
        // + the 14-state pool carve, then the flow's single in-queue. (allocator: the
        // flagged NULL died 2026-08-29 -- MapManager dereferences it now; see the
        // lpFlowAllocator stand-in below.) FLAG (ProfileManager): un-reconstructed; BF_PROFILE's
        // manager-gated calls are boundary no-ops (see BrnBootProfile.cpp).
        // The profile manager's Prepare precedes the flows': it attaches the sign-in
        // listener, prepares the embedded save/load system, and carves the mugshot
        // circular buffer (X360 hands the 0x26 game-data heap + a module linear; the
        // PC module owns dedicated backing regions -- see the FLAG at the statics).
        // ARTIST82519264..82519300: retain call order and assertion continuation.
        if (!mSystemUserProfile.Prepare())
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert("mSystemUserProfile.Prepare()",
                "..\\..\\..\\GameSource\\Gui/BrnGuiModule.cpp", 519);
            CgsDev::Assert::EndAssert();
        }
        if (!mGuiKeyboard.Prepare(&mSystemUserProfile))
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert("mGuiKeyboard.Prepare(&mSystemUserProfile )",
                "..\\..\\..\\GameSource\\Gui/BrnGuiModule.cpp", 523);
            CgsDev::Assert::EndAssert();
        }
        if (!mKeyboardHost.Prepare(&mGuiKeyboard))
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert("mKeyboardHost.Prepare(&mGuiKeyboard)",
                "..\\..\\..\\GameSource\\Gui/BrnGuiModule.cpp", 525);
            CgsDev::Assert::EndAssert();
        }
        mProfileHeap.Construct(s_profileHeapBacking, static_cast<s32>(sizeof(s_profileHeapBacking)));
        mProfileLinear.Construct();
        mProfileLinear.Create(s_profileLinearBacking, sizeof(s_profileLinearBacking));
        mProfileHost.GetProfileManager().Prepare(&mProfileHeap, &mProfileLinear);

        // Install the PC-boundary blank LIVE-REVENGE block (see the static above): the
        // console's network module does this via SetLiveRevengeProfile (GUI event 351);
        // without it Bootup->ReadProfileData faults on the null pointer. Clear() makes it a
        // fresh, unsaved profile of the current version, so the saves written from it pass
        // the live-revenge validation (older PC saves carrying version 0 fail it and reset).
        //
        // ⛔⛔ [one-profile wave 2026-08-28] THE PROGRESSION PAIR IS NO LONGER INSTALLED HERE,
        // and this was the whole defect. There is exactly ONE BrnProgression::Profile on the
        // console -- GameStateModule::mProgressionManager::mProfile, embedded at GSM+48288 --
        // and GameStateModule::PreWorldUpdate posts its address as game action 193 every
        // pre-world update; ProfileManager::SetProgressionProfile @0x824ECC98 has exactly one
        // xref in the whole image and it is GuiModule::Update's case-350 arm consuming that
        // record. We had no case-350 arm, so the manager could never be told the live address
        // and this Prepare installed a module static instead. The result was measurable and
        // permanent: Profile::Deserialise wrote the SAVE into the static while every gameplay
        // reader (ProgressionManager::AreRoadRulesAvailable, the medal/event/car tables, the
        // TrainingManager flags) read mProgressionManager.mProfile -- which was Construct()ed
        // and never loaded into, so it answered mbIsNewProfile = 1 on every boot, for ever.
        // The case-350 arm now does the console's install and the static is gone.
        s_pcLiveRevengeProfile.Clear();
        mProfileHost.GetProfileManager().SetLiveRevengeProfile(&s_pcLiveRevengeProfile);

        // X360 GuiModule::Prepare @0x82518D68 STAGE 3, line 104: `*(gm + 660992) = gm +
        // 1005332`, i.e. the analyzer adopts the shared GuiAccessPointers block (the same
        // block the three flows are prepared against, one line below). The console inlines
        // the store; the DWARF names the method (BrnGuiHudMessageAnalyzer.h:75) and it is
        // bodied as the de-inlined form in BrnGuiHudMessageAnalyzer.cpp. Without it
        // mpAccessPointers is never written and TriggerChallengeEndedMessage /
        // HandleStuntPerformed dereference it (mpAccessPointers->mpLanguageManager).
        mHudMessageAnalyzer.SetAccessPointers(&mGuiAccessPointers);

        // FLAG PC stand-in (main-menu wave, 2026-08-29): the console threads a specific
        // rw resource allocator from the (still-parked) GUI resource slice through
        // EventObserver::Prepare; its identity is not recovered. The flows' allocator was
        // a flagged NULL until CrashNavMap landed the first real dereferencer
        // (MapManager::RecvEvent carves a TextureState resource for the low-res map
        // backdrop) -- the park's own "becomes load-bearing when" fired as a boot
        // GetAllocator assert + null-deref AV. The PC stand-in is the RW DEFAULT
        // allocator, the exact allocator the committed apt texture-state cache leaf
        // already uses for the SAME TextureState carve (CgsAptRenderHandler.cpp:333).
        // DELETE-WHEN the GUI resource slice lands the console's real allocator.
        rw::IResourceAllocator* lpFlowAllocator =
            rw::ResourceAllocatorRegistry::GetDefaultAllocator();

        mHudFlow.Prepare(&mGuiAccessPointers, lpFlowAllocator, &mHudStatePool,
                         &mProfileHost.GetProfileManager());
        mHudInQueue.Construct();
        mHudFlow.SetInEventQueue(&mHudInQueue);

        // The overlay flow: the 15-popup-state pool + its own in-queue (the X360 module
        // prepares all three flows here).
        mOverlayStatePool.Construct();
        mOverlayStatePool.Create(s_overlayStatePoolBacking, sizeof(s_overlayStatePoolBacking));
        mOverlayFlow.Prepare(&mGuiAccessPointers, lpFlowAllocator, &mOverlayStatePool);
        mOverlayInQueue.Construct();
        mOverlayFlow.SetInEventQueue(&mOverlayInQueue);

        // The SCREEN flow: the 61-state front-end pool + its own in-queue. The X360
        // Prepare threads the module's ProfileManager through BY REFERENCE (the CN_PROFILE
        // state's Construct consumes it; the manager is a shell until reconstructed).
        mScreenStatePool.Construct();
        mScreenStatePool.Create(s_screenStatePoolBacking, sizeof(s_screenStatePoolBacking));
        if (mScreenFlow.Prepare(&mGuiAccessPointers, lpFlowAllocator, &mScreenStatePool,
                                mProfileHost.GetProfileManager()))
        {
            // ARTIST true-return path at 0x825190E8 seeds the SCREEN flow to CURRENT.
            mScreenFlow.SetStreamingMode(BrnBaseFlow::E_STREAMING_CURRENT);
        }
        mScreenInQueue.Construct();
        mScreenFlow.SetInEventQueue(&mScreenInQueue);

        // The always-available components manager (save-icon spinner, EATrax/achievement/
        // showtime overlays): give it its own in-queue and latch it. The manager's Prepare
        // state machine + per-frame Update pump run from GuiModule::Update (matching the
        // console's GuiModule::Update @0x82527A58, which calls the manager's Prepare each
        // frame). PrepareFlapt (binding SaveIcon_mc etc.) is driven by the flapt-load
        // notification in ViewModule::ProcessIncomingLoadNotification.
        mAlwaysAvailInQueue.Construct();
        mAlwaysAvailableComponentsManager.SetInEventQueue(&mAlwaysAvailInQueue);

        // The controller: store the model-module pointer + the FSM allocator, then
        // register the three flow slots.
        mFsmController.Prepare(
            &mGuiModel, &mFsmLuaHeap);
        mFsmController.AddFlow(E_GUIFLOW_SCREEN, &mScreenFlow);
        mFsmController.AddFlow(E_GUIFLOW_HUD, &mHudFlow);
        mFsmController.AddFlow(E_GUIFLOW_OVERLAY, &mOverlayFlow);

        // The ModelIO pair the controller exchanges with the loader: construct the
        // IOBuffer bases (the eStatusConstructed guard the lock methods assert on) and
        // the queues this module uses (the input event/request queues + the output
        // notifications).
        mModelInputBuffer.Construct();
        mModelOutputBuffer.Construct();
        mModelInputBuffer.LockForWrite();
        mModelInputBuffer.GetEventQueueNonConst()->Construct();
        mModelInputBuffer.GetLoadRequests()->Construct();
        mModelInputBuffer.UnlockForWrite();
        mModelOutputBuffer.LockForWrite();
        mModelOutputBuffer.GetLoadNotificationsNonConst()->Construct();
        mModelOutputBuffer.UnlockForWrite();

        // Prepare the GUI resource module with seven bank/pool ids (member order:
        // aptPersistent, aptStreamed, font, FSM, language, textures, globalTexture). On
        // the console these are the resource system's real bank handles the module routes
        // each request type to; on PC they are opaque routing tags -- the module only
        // COMPARES them, and the [PC] platform servicer materialises just the FSM bank
        // (id 4) while completing the other banks' requests without IO. They must be
        // DISTINCT so the FSM bank is uniquely identified against the START-stage
        // PERSISTENTAPT (bank 1) / GUITEXTURES.BIN (bank 6) loads.
        mGuiResourceModule.Prepare(/*aptPersistent*/ 1, /*aptStreamed*/ 2, /*font*/ 3,
                                   /*FSM*/ 4, /*language*/ 5, /*textures*/ 6,
                                   /*globalTexture*/ 7);

        mGuiOutQueue.Construct();
        mpOutputBuffer = &mGuiOutQueue;
        mOverlayLoopBackQueue.Construct();
        mOverlayLoopBackQueue.Clear();

        // The view-module IO pair the per-frame bridge fills.
        mViewInputBuffer.Construct();
        mViewInputBuffer.LockForWrite();
        mViewInputBuffer.GetViewStateQueue()
            .CgsModule::VariableEventQueue<65536, 16>::Construct();
        mViewInputBuffer.UnlockForWrite();
        mViewOutputBuffer.Construct();
        miLastViewFrameMs = -1;

        // GuiModule::Prepare stage 13 FIRST blocks on the locale's font table -- the
        // ARTIST western-SKU set is exactly {17,16}, {18,16}, {19,16}
        // (WesternB5Header_70 / WesternB5Body_35 / WesternB5DotMat_35 as
        // E_FONT_RESOURCETYPE_FONTDATA). Drive it through the SAME cache/module pump
        // the second table below uses: the module's container path loads each
        // "Language\Fonts\<name>.font" bundle into the font bank and the notification
        // sweep emits the type-16 records; the view registers each font
        // (ProcessIncomingLoadNotification case 16 -> AddFont) BEFORE the second
        // table is allowed to instantiate FLAPTHUD's text fields -- the original
        // fonts-before-FLApt ordering, by the console's own mechanism.
        // FLAG PC-platform leaf: language IO completed before font requests.
        // Merge its queued notification first so LoadStringTable establishes the
        // default font before the original custom-renderer font callbacks run.
        mViewInputBuffer.LockForWrite();
        {
            CgsGui::GuiEventLoadNotification lNotification;
            while (PopPendingAptLoadNotification(&lNotification))
            {
                mViewInputBuffer.GetViewStateQueue()
                    .CgsModule::VariableEventQueue<65536, 16>::AddEvent(
                        reinterpret_cast<const CgsModule::Event*>(&lNotification), 14,
                        static_cast<s32>(sizeof(lNotification)));
            }
        }
        mViewInputBuffer.UnlockForWrite();

        {
            const CgsGui::sResourceTuple kaFontResources[3] =
            {
                { 17u, static_cast<CgsGui::ResourceRequestTypes>(16) },
                { 18u, static_cast<CgsGui::ResourceRequestTypes>(16) },
                { 19u, static_cast<CgsGui::ResourceRequestTypes>(16) },
            };

            bool lbFontsReady = mGuiCache.EnsureResourcesAreLoaded(kaFontResources, 3);
            for (u32 luPass = 0; luPass < 64u && !lbFontsReady; ++luPass)
            {
                mModelInputBuffer.LockForWrite();
                mGuiCache.Update(&mModelInputBuffer);
                mModelInputBuffer.UnlockForWrite();

                DispatchGuiResourceModule();

                mModelOutputBuffer.LockForRead();
                {
                    const CgsGui::ModelIO::OutputBuffer::GuiNotificationQueue* lpNotifications =
                        mModelOutputBuffer.GetLoadNotifications();
                    const CgsModule::Event* lpNotification = 0;
                    s32 liNotificationSize = 0;
                    s32 liNotificationId =
                        lpNotifications->GetFirstEvent(&lpNotification, &liNotificationSize);
                    while (liNotificationId >= 0 && lpNotification != 0)
                    {
                        if (liNotificationId == 14 || liNotificationId == 16)
                        {
                            mGuiCache.RecEvent(lpNotification, liNotificationId);
                            // Bridge the font notification to the view (event 14) so
                            // ProcessIncomingLoadNotification collects it (AddFont).
                            if (liNotificationId == 14)
                            {
                                mViewInputBuffer.LockForWrite();
                                mViewInputBuffer.GetViewStateQueue()
                                    .CgsModule::VariableEventQueue<65536, 16>::AddEvent(
                                        lpNotification, 14, liNotificationSize);
                                mViewInputBuffer.UnlockForWrite();
                            }
                        }

                        const CgsModule::Event* lpNext = 0;
                        liNotificationId = lpNotifications->GetNextEvent(
                            lpNotification, &lpNext, &liNotificationSize);
                        lpNotification = lpNext;
                    }
                }
                mModelOutputBuffer.UnlockForRead();

                mModelOutputBuffer.LockForWrite();
                mModelOutputBuffer.GetLoadNotificationsNonConst()->Clear();
                mModelOutputBuffer.UnlockForWrite();

                lbFontsReady = mGuiCache.EnsureResourcesAreLoaded(kaFontResources, 3);
            }
            CGS_ASSERT(lbFontsReady, "GUI locale fonts failed to load");
        }

        mViewModule.Update(0, 0, &mViewInputBuffer, &mViewOutputBuffer);
        BridgeFromViewToOutput();
        mViewInputBuffer.LockForWrite();
        mViewInputBuffer.GetViewStateQueue()
            .CgsModule::VariableEventQueue<65536, 16>::Clear();
        mViewInputBuffer.UnlockForWrite();

        // The second ARTIST stage-13 table is this exact resource pair:
        // resource 125 "main" (persistent Apt, type 7) and resource 196
        // "FLAPTHUD" (persistent FLApt, type 10). The PC resource transport is
        // synchronous, so advance the same cache/module state machines here until
        // both completion notifications have arrived, then let the view consume them
        // before any flow state can enter InvisibleOverlayState.
        const CgsGui::sResourceTuple kaStartupResources[2] =
        {
            { 125u, static_cast<CgsGui::ResourceRequestTypes>(7) },
            { 196u, static_cast<CgsGui::ResourceRequestTypes>(10) },
        };

        bool lbStartupResourcesReady =
            mGuiCache.EnsureResourcesAreLoaded(kaStartupResources, 2);
        for (u32 luPass = 0; luPass < 64u && !lbStartupResourcesReady; ++luPass)
        {
            mModelInputBuffer.LockForWrite();
            mGuiCache.Update(&mModelInputBuffer);
            mModelInputBuffer.UnlockForWrite();

            DispatchGuiResourceModule();

            mModelOutputBuffer.LockForRead();
            {
                const CgsGui::ModelIO::OutputBuffer::GuiNotificationQueue* lpNotifications =
                    mModelOutputBuffer.GetLoadNotifications();
                const CgsModule::Event* lpNotification = 0;
                s32 liNotificationSize = 0;
                s32 liNotificationId =
                    lpNotifications->GetFirstEvent(&lpNotification, &liNotificationSize);
                while (liNotificationId >= 0 && lpNotification != 0)
                {
                    if (liNotificationId == 14 || liNotificationId == 16)
                        mGuiCache.RecEvent(lpNotification, liNotificationId);

                    const CgsModule::Event* lpNext = 0;
                    liNotificationId = lpNotifications->GetNextEvent(
                        lpNotification, &lpNext, &liNotificationSize);
                    lpNotification = lpNext;
                }
            }
            mModelOutputBuffer.UnlockForRead();

            mModelOutputBuffer.LockForWrite();
            mModelOutputBuffer.GetLoadNotificationsNonConst()->Clear();
            mModelOutputBuffer.UnlockForWrite();

            lbStartupResourcesReady =
                mGuiCache.EnsureResourcesAreLoaded(kaStartupResources, 2);
        }
        CGS_ASSERT(lbStartupResourcesReady,
                   "GUI startup resources main/FLAPTHUD failed to load");

        // Both type-7 and type-10 completion records were bridged in load order.
        // Processing the queue registers main with Apt and FLAPTHUD with FlaptManager.
        mViewModule.Update(0, 0, &mViewInputBuffer, &mViewOutputBuffer);
        BridgeFromViewToOutput();
        mViewInputBuffer.LockForWrite();
        mViewInputBuffer.GetViewStateQueue()
            .CgsModule::VariableEventQueue<65536, 16>::Clear();
        mViewInputBuffer.UnlockForWrite();

        // The HUD flow FSM chain is live: the GUI owns the loading-screen visual through
        // the real 19/20 command protocol (BridgeGuiToGame consumes them).
        gBrnGuiDrivesLoadingScreen = true;

        CgsDev::Log::WriteToLog(
            "[GuiModule] flow controller live (HUD flow registered; awaiting GuiEventRunFsm).\n");
        mbPrepared = true;
        return true;
    }

    // ARTIST825194B8: the enclosing second-prepare owner. Keep the unsigned
    // stage tests and original wait/continuation behavior; no readiness surrogate.
    bool GuiModule::Prepare2(BrnResource::GameDataIO::InputBuffer* lpGameDataInput)
    {
        if (muPrepare2State < 2)
        {
            muPrepare2State = 1;
            if (!mWorldDataController.Prepare2(lpGameDataInput))
                return false;
        }
        else if (muPrepare2State >= 3)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert("Invalid prepare state", "..\\..\\..\\GameSource\\Gui/BrnGuiModule.cpp", 658);
            CgsDev::Assert::EndAssert();
            return false;
        }
        muPrepare2State = 2;
        return true;
    }

    // X360 GuiModule::Prepare @0x82518D68 STAGE 14, split out to its own entry point because the
    // PC has no module scheduler to hand GuiModule::Prepare the GameData IO pair. See the FLAG on
    // the declaration; the machine itself is the console's, unaltered.
    bool GuiModule::PrepareWorldData(BrnResource::GameDataIO::InputBuffer* lpGameDataInput)
    {
        if (lpGameDataInput == 0)
            return false;
        return mWorldDataController.Prepare(lpGameDataInput);
    }

    // ⭐ [event-starts wave 2026-08-27] X360 GuiModule::Prepare2 @0x825194B8's WorldDataController
    // leg, split out for exactly the same reason as PrepareWorldData above (the PC has no module
    // scheduler to hand GuiModule::Prepare2 the GameData IO pair). The machine itself is the
    // console's, unaltered -- see WorldDataController::Prepare2.
    //
    // ⛔ THE CALLER MUST NOT PUMP THIS AND PrepareWorldData IN THE SAME PHASE. Both machines drain
    // the SAME mReceiverQueue and neither checks what the one queued reply belongs to, so
    // overlapping them makes each eat the other's answer -- and on this build that is not
    // hypothetical: Prepare parks forever at stage 9 waiting on a GetFreeburnChallengeList reply
    // that no PC producer sends, so a Prepare2 reply arriving while Prepare is still pumped would
    // be consumed as the challenge list AND falsely advance meState to WFPLAYERCARCOLOURS.
    // BrnGameModule's driver enforces the exclusion; see the ⛔ at its call site.
    bool GuiModule::PrepareWorldData2(BrnResource::GameDataIO::InputBuffer* lpGameDataInput)
    {
        if (lpGameDataInput == 0)
            return false;
        return mWorldDataController.Prepare2(lpGameDataInput);
    }

    // Original stage12 has no failure return after this assertion.
    // Selecting the full typed Prepare will own the stage transition/call.
    void GuiModule::PrepareNativeSystemNotifications()
    {
        mhSysListenerHandle = XNotifyCreateListener(1);
        if (!mhSysListenerHandle)
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::MessageBufferPC lMessage;
            CgsDev::StrStream lStream(lMessage.GetBuffer(), lMessage.GetSize());
            lStream << "Failed to create an X360 system listener";
            CgsDev::Assert::FireAssert(lMessage.GetBuffer(),
                "..\\..\\..\\GameSource\\Gui/BrnGuiModule.cpp", 557);
            CgsDev::Assert::EndAssert();
        }
    }

    // ARTIST82529CA8..82529DD0: dequeue at most one notification,
    // then publish the actual four-byte event516 to the fresh Model input.
    void GuiModule::UpdateNativeSystemNotifications(
        CgsGui::ModelIO::InputBuffer* lpInputBuffer)
    {
        unsigned long luNotificationId;
        unsigned long luNotificationParam;
        if (mhSysListenerHandle &&
            XNotifyGetNext(mhSysListenerHandle, 9, &luNotificationId, &luNotificationParam))
        {
            if (luNotificationId == 0x02000002)
            {
                CgsDev::Assert::BeginAssert();
                CgsDev::Assert::MessageBufferPC lMessage;
                CgsDev::StrStream lStream(lMessage.GetBuffer(), lMessage.GetSize());
                lStream << "Invite notification processed by GuiModule. This could break cross game invites\n";
                CgsDev::Assert::FireAssert(lMessage.GetBuffer(),
                    "..\\..\\..\\GameSource\\Gui/BrnGuiModule.cpp", 2918);
                CgsDev::Assert::EndAssert();
            }
            const u32 luUiVisible = luNotificationParam != 1;
            if (!lpInputBuffer)
            {
                CgsDev::Assert::BeginAssert();
                CgsDev::Assert::FireAssert("lpInputBuffer",
                    "..\\..\\..\\GameShared\\GameClasses\\Module/CgsModuleUtils.h", 238);
                CgsDev::Assert::EndAssert();
            }
            lpInputBuffer->LockForWrite();
            lpInputBuffer->GetEventQueueNonConst()->AddEvent(
                reinterpret_cast<const CgsModule::Event*>(&luUiVisible), 516, sizeof(luUiVisible));
            if (!lpInputBuffer)
            {
                CgsDev::Assert::BeginAssert();
                CgsDev::Assert::FireAssert("lpInputBuffer",
                    "..\\..\\..\\GameShared\\GameClasses\\Module/CgsModuleUtils.h", 248);
                CgsDev::Assert::EndAssert();
            }
            lpInputBuffer->UnlockForWrite();
        }
    }

    // Original Release closes before its stage switch, including failed close.
    // The assertion continues and clears the original member in either case.
    void GuiModule::ReleaseNativeSystemNotifications()
    {
        if (mhSysListenerHandle)
        {
            if (!CloseHandle(mhSysListenerHandle))
            {
                CgsDev::Assert::BeginAssert();
                CgsDev::Assert::FireAssert("CloseHandle( mhSysListenerHandle )",
                    "..\\..\\..\\GameSource\\Gui/BrnGuiModule.cpp", 681);
                CgsDev::Assert::EndAssert();
            }
            mhSysListenerHandle = 0;
        }
    }

    bool GuiModule::Release()
    {
        mbRenderInputCompletedPC = false;
        mScreenFlow.Release();       // staged: current state OnLeave + ScriptedFsm release
        mHudFlow.Release();
        mOverlayFlow.Release();
        // Leave retry-sensitive GUI owners intact until the movie pool releases successfully.
        if (!mMovieManager.Release())
            return false;
        mProfileHost.GetProfileManager().Release();   // detach the sign-in listener + release the SLS
        // ARTIST824F92A4..824F930C: profile, keyboard, then keyboard listener host.
        if (!mSystemUserProfile.Release())
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert("mSystemUserProfile.Release()",
                "..\\..\\..\\GameSource\\Gui/BrnGuiModule.cpp", 710);
            CgsDev::Assert::EndAssert();
        }
        mGuiKeyboard.Release();
        if (!mKeyboardHost.Release())
        {
            CgsDev::Assert::BeginAssert();
            CgsDev::Assert::FireAssert("mKeyboardHost.Release()",
                "..\\..\\..\\GameSource\\Gui/BrnGuiModule.cpp", 712);
            CgsDev::Assert::EndAssert();
        }
        mFsmLuaHeap.Destruct();
        if (gpActiveGuiModule == this)
            gpActiveGuiModule = 0;
        gpActiveMovieManager = 0;
        return true;
    }

    // Extracted ARTIST8251A4D4..8251A538. Only the future typed PreWorld phase calls this block.
    void GuiModule::PublishNativeMovieResourceRequest(CgsGui::CgsGuiModuleIO::OutputBuffer* lpGuiOutput)
    {
        const CgsResource::ID lResourceId = mMovieManager.PendingVideoDataResourceRequest();
        if (lResourceId.GetHash() == 0)
            return;

        CgsResource::Events::AcquireResourceRequest lRequest;
        lRequest.mpUser = mMovieManager.GetRecieverQueue();
        lRequest.miEventId = MovieManager::KI_VIDEO_DATA_RESOURCE_EVENT_ID;
        lRequest.miPoolId = 11;
        lRequest.mResourceId = lResourceId;
        lpGuiOutput->LockForWrite();
        lpGuiOutput->GetGuiResourceRequestQueue()->AddEvent(&lRequest, 4);
        lpGuiOutput->UnlockForWrite();
    }

    // ARTIST8251A3D0; original call order and locks are retained. The active PC GameMain
    // still does not select this virtual phase; that remains a separate frame-wiring increment.
    void GuiModule::PreWorldUpdate(CgsModule::IOBufferStack* lpInputBufferStack,
                                   CgsModule::IOBufferStack* lpOutputBufferStack,
                                   CgsGui::CgsGuiModuleIO::OutputBuffer* lpGuiOutput,
                                   CgsGui::ModelIO::OutputBuffer* lpModelOutputBuffer)
    {
        CgsDev::PerfMonCpu::StartMonitor(GuiPerfmons::miGuiModulePreWorldUpdate);
        CGS_ASSERT(lpGuiOutput != 0, "lpGuiOutput != NULL");
        CGS_ASSERT(lpModelOutputBuffer != 0, "lpModelOutputBuffer != NULL");
        CGS_ASSERT(lpInputBufferStack != 0, "lpInputBufferStack != NULL");
        CGS_ASSERT(lpOutputBufferStack != 0, "lpOutputBufferStack != NULL");

        lpGuiOutput->LockForWrite();
        UpdateCollisionWorldValidation(lpGuiOutput);
        UpdateCarPoolValidation(lpGuiOutput);
        mProfileHost.GetProfileManager().LoadProfileUpgradeData(lpGuiOutput, &mEventReceiverQueue);
        lpGuiOutput->UnlockForWrite();

        PublishNativeMovieResourceRequest(lpGuiOutput);
        CgsGui::GuiModule::PreWorldUpdate(lpInputBufferStack, lpOutputBufferStack,
                                          lpGuiOutput, lpModelOutputBuffer);
        CgsDev::PerfMonCpu::StopMonitor(GuiPerfmons::miGuiModulePreWorldUpdate);
    }

    // ARTIST82519578. Pending* calls consume their flags/state even when an
    // assertion is disabled, so keep every call outside its assertion expression.
    void GuiModule::UpdateCollisionWorldValidation(CgsGui::CgsGuiModuleIO::OutputBuffer* lpOutput)
    {
        const auto ConsumeNetworkingInvalidate = [this]() {
            const bool lbPending = mbCollisionWorldInvalidateForNetworking;
            mbCollisionWorldInvalidateForNetworking = false;
            return lbPending;
        };
        const auto ConsumeNetworkingValidate = [this]() {
            const bool lbPending = mbCollisionWorldValidateForNetworking;
            mbCollisionWorldValidateForNetworking = false;
            return lbPending;
        };
        const auto NoNetworkingInvalidate = [&]() {
            const bool lbPending = ConsumeNetworkingInvalidate();
            CGS_ASSERT(!lbPending, "!PendingCollisionWorldInvalidateForNetworking()");
        };
        const auto NoMovieInvalidate = [this]() {
            const bool lbPending = mMovieManager.PendingCollisionWorldInvalidate();
            CGS_ASSERT(!lbPending, "!mMovieManager.PendingCollisionWorldInvalidate()");
        };
        const auto NoProfileInvalidate = [this]() {
            const bool lbPending = mProfileHost.GetProfileManager().PendingCollisionWorldInvalidate();
            CGS_ASSERT(!lbPending, "!mProfileHost.GetProfileManager().PendingCollisionWorldInvalidate()");
        };
        const auto SwapOut = [this, lpOutput]() {
            BrnResource::GameDataIO::SwapOutCollisionWorldRequest lRequest;
            lRequest.miEventId = 0;
            lRequest.mpReceiverQueue = &mCollisonPoolValidationReceiverQueue;
            lpOutput->GetGuiResourceRequestQueue()->AddEvent(&lRequest, 67);
        };
        const auto SwapIn = [this, lpOutput]() {
            BrnResource::GameDataIO::SwapInCollisionWorldRequest lRequest;
            lRequest.miEventId = 0;
            lRequest.mpReceiverQueue = &mCollisonPoolValidationReceiverQueue;
            lpOutput->GetGuiResourceRequestQueue()->AddEvent(&lRequest, 68);
        };
        const auto AskWorld = [lpOutput](GuiEventRequestCollisionWorldEvent::EEventType leType) {
            GuiEventRequestCollisionWorldEvent lRequest;
            lRequest.meEventType = leType;
            lpOutput->AddGuiOutEvent(lRequest);
        };
        const auto ReadResponse = [this](s32 liExpectedType) {
            const CgsModule::Event* lpEvent = 0;
            s32 liSize = 0;
            const s32 liType = mCollisonPoolValidationReceiverQueue.GetFirstEvent(&lpEvent, &liSize);
            CGS_ASSERT(mCollisonPoolValidationReceiverQueue.GetLength() == 1,
                "mCollisonPoolValidationReceiverQueue.GetLength() == 1");
            if (liExpectedType == 67)
                CGS_ASSERT(liType == 67, "liEventId == BrnResource::GameDataIO::EVENT_SWAP_OUT_COLLISION_WORLD");
            else
                CGS_ASSERT(liType == 68, "liEventId == BrnResource::GameDataIO::EVENT_SWAP_IN_COLLISION_WORLD");
            return lpEvent;
        };

        switch (meCollisionWorldStateValidationState)
        {
        case E_COLLISIONWORLDSTATEVALIDATIONSTATE_IDLE:
        {
            const bool lbMovie = mMovieManager.PendingCollisionWorldInvalidate();
            const bool lbNetworking = ConsumeNetworkingInvalidate();
            if (mbBootMovieMode)
            {
                const bool lbProfile = mProfileHost.GetProfileManager().PendingCollisionWorldInvalidate();
                if (lbMovie || lbProfile)
                {
                    BrnResource::PrintConsoleMemory(0);
                    mCollisonPoolValidationReceiverQueue.Clear();
                    SwapOut();
                    meCollisionWorldStateValidationState = lbMovie
                        ? E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALIDATING_FOR_BOOT
                        : E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALIDATING_FOR_SAVELOAD;
                }
            }
            else if (lbMovie || lbNetworking)
            {
                CGS_ASSERT(!mbCollisionWorldInvalid, "!mbCollisionWorldInvalid");
                CGS_ASSERT((lbMovie && !lbNetworking) || (!lbMovie && lbNetworking),
                    "( lbMoviePendingInvalidate && !lbNetworkingPendingInvalidate) || (!lbMoviePendingInvalidate && lbNetworkingPendingInvalidate)");
                AskWorld(GuiEventRequestCollisionWorldEvent::E_COLLISON_WORLD_INVALIDATE);
                meCollisionWorldStateValidationState = lbMovie
                    ? E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALIDATING_FOR_MOVIE
                    : E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALIDATING_FOR_NETWORKING;
            }
            break;
        }
        case E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALIDATING_FOR_BOOT:
            NoNetworkingInvalidate();
            if (mCollisonPoolValidationReceiverQueue.GetLength() > 0)
            {
                const auto* lpResponse = static_cast<const BrnResource::GameDataIO::SwapOutCollisionWorldResponse*>(ReadResponse(67));
                mMovieManager.FreeCollisionPoolMemory(lpResponse);
                BrnResource::PrintConsoleMemory(0);
                mbCollisionWorldInvalid = true;
                mMovieManager.SetCollisionWorldValid(false);
                meCollisionWorldStateValidationState = E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALID_FOR_BOOT;
            }
            break;
        case E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALID_FOR_BOOT:
            NoNetworkingInvalidate();
            CGS_ASSERT(mbCollisionWorldInvalid, "mbCollisionWorldInvalid");
            if (mMovieManager.PendingCollisionWorldValidate())
            {
                SwapIn();
                mCollisonPoolValidationReceiverQueue.Clear();
                meCollisionWorldStateValidationState = E_COLLISIONWORLDSTATEVALIDATIONSTATE_VALIDATING_FOR_BOOT;
            }
            break;
        case E_COLLISIONWORLDSTATEVALIDATIONSTATE_VALIDATING_FOR_BOOT:
            NoNetworkingInvalidate();
            if (mCollisonPoolValidationReceiverQueue.GetLength() > 0)
            {
                ReadResponse(68);
                BrnResource::PrintConsoleMemory(0);
                BrnResource::PrintConsoleMemory(0);
                mbCollisionWorldInvalid = false;
                mMovieManager.SetCollisionWorldValid(true);
                meCollisionWorldStateValidationState = E_COLLISIONWORLDSTATEVALIDATIONSTATE_IDLE;
            }
            break;
        case E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALIDATING_FOR_SAVELOAD:
            NoMovieInvalidate();
            NoNetworkingInvalidate();
            if (mCollisonPoolValidationReceiverQueue.GetLength() > 0)
            {
                ReadResponse(67);
                BrnResource::PrintConsoleMemory(0);
                mbCollisionWorldInvalid = true;
                mProfileHost.GetProfileManager().SetCollisionWorldValid(false);
                meCollisionWorldStateValidationState = E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALID_FOR_SAVELOAD;
            }
            break;
        case E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALID_FOR_SAVELOAD:
            NoMovieInvalidate();
            NoNetworkingInvalidate();
            CGS_ASSERT(mbCollisionWorldInvalid, "mbCollisionWorldInvalid");
            if (mProfileHost.GetProfileManager().PendingCollisionWorldValidate())
            {
                SwapIn();
                mCollisonPoolValidationReceiverQueue.Clear();
                meCollisionWorldStateValidationState = E_COLLISIONWORLDSTATEVALIDATIONSTATE_VALIDATING_FOR_SAVELOAD;
            }
            break;
        case E_COLLISIONWORLDSTATEVALIDATIONSTATE_VALIDATING_FOR_SAVELOAD:
            NoMovieInvalidate();
            NoNetworkingInvalidate();
            if (mCollisonPoolValidationReceiverQueue.GetLength() > 0)
            {
                ReadResponse(68);
                BrnResource::PrintConsoleMemory(0);
                mbCollisionWorldInvalid = false;
                mProfileHost.GetProfileManager().SetCollisionWorldValid(true);
                meCollisionWorldStateValidationState = E_COLLISIONWORLDSTATEVALIDATIONSTATE_IDLE;
            }
            break;
        case E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALIDATING_FOR_MOVIE:
            NoProfileInvalidate();
            NoNetworkingInvalidate();
            if (mbCollisionWorldInvalid)
            {
                mMovieManager.SetCollisionWorldValid(false);
                meCollisionWorldStateValidationState = E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALID_FOR_MOVIE;
            }
            break;
        case E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALID_FOR_MOVIE:
            NoProfileInvalidate();
            NoNetworkingInvalidate();
            CGS_ASSERT(mbCollisionWorldInvalid, "mbCollisionWorldInvalid");
            if (mMovieManager.PendingCollisionWorldValidate())
            {
                AskWorld(GuiEventRequestCollisionWorldEvent::E_COLLISON_WORLD_VALIDATE);
                meCollisionWorldStateValidationState = E_COLLISIONWORLDSTATEVALIDATIONSTATE_VALIDATING_FOR_MOVIE;
            }
            break;
        case E_COLLISIONWORLDSTATEVALIDATIONSTATE_VALIDATING_FOR_MOVIE:
            NoProfileInvalidate();
            NoNetworkingInvalidate();
            if (!mbCollisionWorldInvalid)
            {
                mMovieManager.SetCollisionWorldValid(true);
                meCollisionWorldStateValidationState = E_COLLISIONWORLDSTATEVALIDATIONSTATE_IDLE;
            }
            break;
        case E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALIDATING_FOR_NETWORKING:
            NoProfileInvalidate();
            NoMovieInvalidate();
            if (mbCollisionWorldInvalid)
                meCollisionWorldStateValidationState = E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALID_FOR_NETWORKING;
            break;
        case E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALID_FOR_NETWORKING:
            NoProfileInvalidate();
            NoMovieInvalidate();
            if (ConsumeNetworkingValidate())
            {
                AskWorld(GuiEventRequestCollisionWorldEvent::E_COLLISON_WORLD_VALIDATE);
                meCollisionWorldStateValidationState = E_COLLISIONWORLDSTATEVALIDATIONSTATE_VALIDATING_FOR_NETWORKING;
            }
            break;
        case E_COLLISIONWORLDSTATEVALIDATIONSTATE_VALIDATING_FOR_NETWORKING:
            NoProfileInvalidate();
            NoMovieInvalidate();
            if (!mbCollisionWorldInvalid)
                meCollisionWorldStateValidationState = E_COLLISIONWORLDSTATEVALIDATIONSTATE_IDLE;
            break;
        default:
            CGS_ASSERT(false, "Unhandled state");
            break;
        }
    }

    // ARTIST82514228. Pool15 is positively attested here. Invalidate IN_USE
    // retries at WAITING_FOR_POOL_TO_EMPTY; it never fabricates completion.
    void GuiModule::UpdateCarPoolValidation(CgsGui::CgsGuiModuleIO::OutputBuffer* lpOutput)
    {
        switch (meCarPoolStateValidationState)
        {
        case E_CARPOOLSTATEVALIDATIONSTATE_IDLE:
            if (mMovieManager.PendingCarPoolInvalidate())
            {
                if (mbBootMovieMode)
                    mbTrafficPoolEmptied = true;
                else
                {
                    const bool lbEmpty = true;
                    lpOutput->GetGameActionQueue()->AddEvent(
                        reinterpret_cast<const CgsModule::Event*>(&lbEmpty), 13, sizeof(lbEmpty));
                    mbTrafficPoolEmptied = false;
                }
                meCarPoolStateValidationState = E_CARPOOLSTATEVALIDATIONSTATE_WAITING_FOR_POOL_TO_EMPTY;
            }
            break;
        case E_CARPOOLSTATEVALIDATIONSTATE_WAITING_FOR_POOL_TO_EMPTY:
            if (mbTrafficPoolEmptied)
            {
                CgsResource::Events::InvalidatePoolRequest lRequest;
                lRequest.mpUser = &mEventReceiverQueue;
                lRequest.miEventId = BrnResource::E_POOL_TRAFFIC;
                lRequest.miPoolId = BrnResource::E_POOL_TRAFFIC;
                lpOutput->GetGuiResourceRequestQueue()->AddEvent(&lRequest, 7);
                meCarPoolStateValidationState = E_CARPOOLSTATEVALIDATIONSTATE_INVALIDATING_FOR_MOVIE;
            }
            break;
        case E_CARPOOLSTATEVALIDATIONSTATE_INVALIDATING_FOR_MOVIE:
            if (mEventReceiverQueue.GetLength() > 0)
            {
                CGS_ASSERT(mEventReceiverQueue.GetLength() == 1, "mEventReceiverQueue.GetLength() == 1");
                const CgsModule::Event* lpEvent = 0;
                s32 liSize = 0;
                const s32 liEventId = mEventReceiverQueue.GetFirstEvent(&lpEvent, &liSize);
                CGS_ASSERT(liEventId == 7, "liEventId == CgsResource::ResourceIO::EVENT_INVALIDATEPOOL");
                const auto* lpResponse = reinterpret_cast<const CgsResource::Events::InvalidatePoolResponse*>(lpEvent);
                CGS_ASSERT(lpResponse->miEventId == BrnResource::E_POOL_TRAFFIC,
                    "lpInvalidatePoolResponse->GetEventId() == BrnResource::E_POOL_TRAFFIC");
                mEventReceiverQueue.Clear(); // Original Clear preserves payload storage.
                if (lpResponse->GetResult() != CgsResource::Events::InvalidatePoolResponse::E_RESULT_SUCCESS)
                    meCarPoolStateValidationState = E_CARPOOLSTATEVALIDATIONSTATE_WAITING_FOR_POOL_TO_EMPTY;
                else
                {
                    mMovieManager.SetCarPoolValid(false, lpResponse->GetResource(), lpResponse->GetDescriptor());
                    meCarPoolStateValidationState = E_CARPOOLSTATEVALIDATIONSTATE_INVALID_FOR_MOVIE;
                }
            }
            break;
        case E_CARPOOLSTATEVALIDATIONSTATE_INVALID_FOR_MOVIE:
            if (mMovieManager.PendingCarPoolValidate())
            {
                CgsResource::Events::ValidatePoolRequest lRequest;
                lRequest.mpUser = &mEventReceiverQueue;
                lRequest.miEventId = BrnResource::E_POOL_TRAFFIC;
                lRequest.miPoolId = BrnResource::E_POOL_TRAFFIC;
                lpOutput->GetGuiResourceRequestQueue()->AddEvent(&lRequest, 8);
                meCarPoolStateValidationState = E_CARPOOLSTATEVALIDATIONSTATE_VALIDATING_FOR_MOVIE;
            }
            break;
        case E_CARPOOLSTATEVALIDATIONSTATE_VALIDATING_FOR_MOVIE:
            if (mEventReceiverQueue.GetLength() <= 0)
                break;
            {
                CGS_ASSERT(mEventReceiverQueue.GetLength() == 1, "mEventReceiverQueue.GetLength() == 1");
                const CgsModule::Event* lpEvent = 0;
                s32 liSize = 0;
                const s32 liEventId = mEventReceiverQueue.GetFirstEvent(&lpEvent, &liSize);
                CGS_ASSERT(liEventId == 8, "liEventId == CgsResource::ResourceIO::EVENT_VALIDATEPOOL");
                const auto* lpResponse = reinterpret_cast<const CgsResource::Events::ValidatePoolResponse*>(lpEvent);
                CGS_ASSERT(lpResponse->miEventId == BrnResource::E_POOL_TRAFFIC,
                    "lpValidatePoolResponse->GetEventId() == BrnResource::E_POOL_TRAFFIC");
                mEventReceiverQueue.Clear();
                if (mbBootMovieMode)
                    mbTrafficPoolEmptied = false;
                else
                {
                    const bool lbEmpty = false;
                    lpOutput->GetGameActionQueue()->AddEvent(
                        reinterpret_cast<const CgsModule::Event*>(&lbEmpty), 13, sizeof(lbEmpty));
                    CGS_ASSERT(mbTrafficPoolEmptied, "mbTrafficPoolEmptied");
                }
                meCarPoolStateValidationState = E_CARPOOLSTATEVALIDATIONSTATE_WAITING_FOR_POOL_TO_FILL;
            }
            [[fallthrough]];
        case E_CARPOOLSTATEVALIDATIONSTATE_WAITING_FOR_POOL_TO_FILL:
            if (!mbTrafficPoolEmptied)
            {
                CgsResource::SmallResource lResource;
                CgsResource::Entry::ResourceDescriptor lDescriptor;
                for (s32 liType = 0; liType < 3; ++liType)
                {
                    lResource.m_baseResources[liType] = 0;
                    lDescriptor.m_baseResourceDescriptors[liType].m_size = 0;
                    lDescriptor.m_baseResourceDescriptors[liType].m_alignment = 1;
                }
                mMovieManager.SetCarPoolValid(true, lResource, lDescriptor);
                meCarPoolStateValidationState = E_CARPOOLSTATEVALIDATIONSTATE_IDLE;
            }
            break;
        default:
            CGS_ASSERT(false, "Unhandled state");
            break;
        }
    }

    // ARTIST GuiModule::Prepare stage 10 (0x82519218..0x82519254): register the four
    // native debug components and clear the event receiver queue at the original stage.
    void GuiModule::PrepareNativeDebugComponents()
    {
        mDebugComponent.Register();
        mHudMessageDebugComponent.Register();
        mSatNavDebugComponent.Register();
        mGuiCacheDebugComponent.Register();
        mEventReceiverQueue.Clear();
    }

void GuiModule::Destruct()
    {
        mbRenderInputCompletedPC = false;
        mMovieManager.Destruct();
        // ARTIST825076D0..825077A4: four actual derived teardown owners, original order.
        mDebugComponent.Destruct();
        mHudMessageDebugComponent.Destruct();
        mSatNavDebugComponent.Destruct();
        mGuiCacheDebugComponent.Destruct();
        // X360 GuiModule::Destruct @0x82507690: ColourCalibrationScreen::Destruct is the LAST
        // sub-object destruct, immediately before the base CgsGui::GuiModule::Destruct.
        // ARTIST825077D0/D4: retain the original host/profile pointer teardown.
        mKeyboardHost.Destruct();
        mGuiKeyboard.Destruct();
        mColourCalibrationScreen.Destruct();
        // ARTIST825077F4: the shared queue/base lifecycle follows the final
        // game subobject. Existing Movie/APT lifetime owners above are retained.
        CgsGui::GuiModule::Destruct();
    }

    // Post one event into each subscribing observer's in-queue (the EventInterpreterModule
    // observer-subscription filter the console applies in ProcessInEvents before handing
    // an observer its per-frame queue). The observer slots are the three flows plus the
    // always-available components manager.
    void GuiModule::RouteEventToFlow(const CgsModule::Event* lpEvent, s32 liId, s32 liSize)
    {
        if (liId < 0 || liId >= KI_MAX_OBSERVED_EVENT_ID)
            return;
        if ((liId == 284 || liId == 94) && CgsDev::Log::gpDebugPrint && std::getenv("BRN_EASYDRIVE_TRACE"))
            *CgsDev::Log::gpDebugPrint << "[easydrive-route] id " << liId << " screen "
                << (mabObservedEventIds[0][liId] ? 1 : 0) << " hud " << (mabObservedEventIds[1][liId] ? 1 : 0) << "\n";


        // IsPriorityEvent + IsEventBlocked from ARTIST's EventInterpreterModule.
        // The first registered priority key owns the event; a blocking owner removes
        // its override events from every other observer until it unregisters.
        s32 liPriorityOwner = -1;
        s32 liBlockingOwner = -1;
        for (s32 lf = 0; lf < KI_NUM_EVENT_OBSERVERS; ++lf)
        {
            for (s32 lc = 0; lc < KI_MAX_PRIORITY_CLAIMS_PER_FLOW; ++lc)
            {
                const PriorityClaim& lrClaim = maPriorityClaims[lf][lc];
                if (!lrClaim.mbActive)
                    continue;
                if (liPriorityOwner < 0 && lrClaim.miEventType == liId)
                    liPriorityOwner = lf;
                if (liBlockingOwner < 0 && mabPriorityBlocking[lf] &&
                    lrClaim.mabOverriddenEventIds[liId])
                {
                    liBlockingOwner = lf;
                }
            }
        }

        CgsModule::VariableEventQueue<18432, 16>* lapQueues[KI_NUM_EVENT_OBSERVERS] =
            { &mScreenInQueue, &mHudInQueue, &mOverlayInQueue, &mAlwaysAvailInQueue };
        for (s32 lf = 0; lf < KI_NUM_EVENT_OBSERVERS; ++lf)
        {
            if (!mabObservedEventIds[lf][liId])
                continue;

            if (liPriorityOwner >= 0)
            {
                if (lf == liPriorityOwner || liBlockingOwner < 0)
                {
                    lapQueues[lf]->AddEvent(lpEvent, liId, liSize);
                    if (lf == liPriorityOwner)
                        mabPriorityBlocking[lf] = true;
                }
                else if (mabObservedEventIds[lf][CgsGui::E_GUI_PRIORITY_REMOVAL])
                {
                    const s32 liRemovedEventId = liId;
                    lapQueues[lf]->AddEvent(
                        reinterpret_cast<const CgsModule::Event*>(&liRemovedEventId),
                        CgsGui::E_GUI_PRIORITY_REMOVAL, static_cast<s32>(sizeof(liRemovedEventId)));
                }
                continue;
            }

            if (liBlockingOwner >= 0)
            {
                if (lf == liBlockingOwner)
                {
                    const s32 liBlockingEventId = liId;
                    lapQueues[lf]->AddEvent(
                        reinterpret_cast<const CgsModule::Event*>(&liBlockingEventId),
                        CgsGui::E_GUI_PRIORITY_BLOCKING, static_cast<s32>(sizeof(liBlockingEventId)));
                    lapQueues[lf]->AddEvent(lpEvent, liId, liSize);
                }
                else if (mabObservedEventIds[lf][CgsGui::E_GUI_PRIORITY_REMOVAL])
                {
                    const s32 liRemovedEventId = liId;
                    lapQueues[lf]->AddEvent(
                        reinterpret_cast<const CgsModule::Event*>(&liRemovedEventId),
                        CgsGui::E_GUI_PRIORITY_REMOVAL, static_cast<s32>(sizeof(liRemovedEventId)));
                }
                continue;
            }

            lapQueues[lf]->AddEvent(lpEvent, liId, liSize);
        }
    }

    // ARTIST @0x825112B0 converts the FLApt action string to a
    // GuiAudioTriggerEvent and publishes it through the module output buffer.
    void GuiModule::FlaptSoundTriggerCallback(void* lpUserData,
                                              const char* lpcComponentName,
                                              const char* lpcSwfName,
                                              const char* lpcActionName,
                                              const char* lpcLabel)
    {
        CGS_ASSERT(lpUserData != 0, "lpUserData");
        CGS_ASSERT(lpcComponentName != 0, "lpcComponentName");
        CGS_ASSERT(lpcSwfName != 0, "lpcSwfName");
        CGS_ASSERT(lpcActionName != 0, "lpcActionName");
        CGS_ASSERT(lpcLabel != 0, "lpcLabel");

        GuiModule* lpThis = static_cast<GuiModule*>(lpUserData);
        CGS_ASSERT(lpThis->mpOutputBuffer != 0, "mpOutputBuffer");

        // off_82F277A8..off_82F277E0: the fourteen authored presentation actions.
        static const char* const KAPC_ACTION_NAMES[14] = {
            "ON_ENTER", "ON_LEAVE", "ON_FOCUS", "ON_LOSE_FOCUS",
            "ON_ACCEPT", "ON_CANCEL", "ON_TICK", "ON_CHANGE",
            "ON_UP", "ON_DOWN", "ON_LEFT", "ON_LEFT_SWEEP",
            "ON_RIGHT", "ON_RIGHT_SWEEP"
        };

        s32 liAction = 14;
        for (s32 li = 0; li < 14; ++li)
        {
            if (std::strcmp(lpcActionName, KAPC_ACTION_NAMES[li]) == 0)
            {
                liAction = li;
                break;
            }
        }

        GuiAudioTriggerEvent lAudioEvent;
        lAudioEvent.Construct(liAction, lpcComponentName, lpcLabel, lpcSwfName);
        // ARTIST sub_824FB9A8 emits this diagnostic after Construct for any action >= 14.
        if (liAction >= 14 && ::gbLogGuiAudioTriggers &&
            (CgsDev::Message::gxMessageFilterFlags & 1) != 0)
        {
            const char* lpcLogComponent = lpcComponentName != 0 ? lpcComponentName : "<NULLSTRING>";
            const char* lpcLogAction = lpcActionName != 0 ? lpcActionName : "<NULLSTRING>";
            const char* lpcLogLabel = lpcLabel != 0 ? lpcLabel : "<NULLSTRING>";
            const char* lpcLogMovie = lpcSwfName != 0 ? lpcSwfName : "<NULLSTRING>";
            *CgsDev::Log::gpDebugPrint
                << "\nGUI AUDIO TRIGGERS: "
                << "Received invalid sound action. Component: " << lpcLogComponent
                << " Action: " << lpcLogAction
                << " Label: " << lpcLogLabel
                << " Movie: " << lpcLogMovie
                << "\n";
        }
        lpThis->mpOutputBuffer->AddEvent(
            reinterpret_cast<const CgsModule::Event*>(&lAudioEvent),
            lAudioEvent.GetEventType(), static_cast<s32>(sizeof(lAudioEvent)));
    }

    namespace
    {
        // The four player-name string ids UpdatePlayerName reads/writes. The read side
        // ("DEFAULTPLAYERNAME"/"DEFAULTPLAYERNAMEQUOTED", X360 off_82F278B4/off_82F278B8)
        // are language-DATABASE keys whose entries ship in the LANGUAGE bundles ("You" /
        // '"You"'); the write side (off_82F278AC/off_82F278B0) are the LIVE ids every
        // GUI consumer resolves (GuiCache::GetPlayerName returns the first verbatim).
        const char* const KAPC_UPN_PLAYER_NAME_ID        = "PLAYER_NAME_STRING_ID";      // @0x8206E7DC
        const char* const KAPC_UPN_PLAYER_NAME_QUOTED_ID = "PLAYER_NAME_STRING_ID_Q";    // @0x8206E7C4
        const char* const KAPC_UPN_DEFAULT_NAME_ID       = "DEFAULTPLAYERNAME";          // off_82F278B4
        const char* const KAPC_UPN_DEFAULT_QUOTED_ID     = "DEFAULTPLAYERNAMEQUOTED";    // off_82F278B8
    }

    // @ 0x824F0D30 -- publish the live player name into the language database (see the
    // header note). Runs when GuiModule::Update sees event 507 -- the command record
    // BootProfile::OnLeave posts as the profile boot completes -- so every subsequent
    // "PLAYER_NAME_STRING_ID" lookup (the licence card's playerName field, the HUD
    // message analyzer's name substitution) resolves to a real name instead of the id.
    //
    // [PC] XUserGetName has no host equivalent and no user is ever signed in, so this
    // always takes the console's XUserGetName-FAILED branch: copy the database's own
    // DEFAULT entries ("You" / '"You"') under the live ids -- byte-identical to an X360
    // with no profile signed in. The signed-in branch (gamertag + the "''%s''" quoted
    // form) needs the platform user account and stays X360-only.
    void GuiModule::UpdatePlayerName()
    {
        CgsLanguage::LanguageManager* lpLanguageManager = mViewModule.GetLanguageManager();
        if (lpLanguageManager == 0)
            return;   // [PC] Prepare not finished yet; the console cannot reach 507 this early.

        const u8* lpcDefaultName = lpLanguageManager->FindString(KAPC_UPN_DEFAULT_NAME_ID);
        CGS_ASSERT(lpcDefaultName != 0,
                   "Couldn't find default player name in string database.");             // cpp:1216
        if (lpcDefaultName == 0)
            return;   // [PC] the console strncpy's from NULL here; entries ship in every LANGUAGE bundle
        CGS_ASSERT(std::strlen(reinterpret_cast<const char*>(lpcDefaultName)) < 0x1B,
                   "String too long: ");                                                  // CgsStringUtils.h:55
        char lacName[32];
        std::strncpy(lacName, reinterpret_cast<const char*>(lpcDefaultName), 27);
        lacName[27] = 0;
        lpLanguageManager->AddString(KAPC_UPN_PLAYER_NAME_ID,
                                     reinterpret_cast<const u8*>(lacName));

        const u8* lpcDefaultQuoted = lpLanguageManager->FindString(KAPC_UPN_DEFAULT_QUOTED_ID);
        CGS_ASSERT(lpcDefaultQuoted != 0,
                   "Couldn't find default player name quoted in string database.");      // cpp:1222
        if (lpcDefaultQuoted == 0)
            return;   // [PC] see above
        CGS_ASSERT(std::strlen(reinterpret_cast<const char*>(lpcDefaultQuoted)) < 0x1F,
                   "String too long: ");                                                  // CgsStringUtils.h:55
        char lacQuoted[32];
        std::strncpy(lacQuoted, reinterpret_cast<const char*>(lpcDefaultQuoted), 31);
        lacQuoted[31] = 0;   // the console's explicit v35 = 0 store
        lpLanguageManager->AddString(KAPC_UPN_PLAYER_NAME_QUOTED_ID,
                                     reinterpret_cast<const u8*>(lacQuoted));
    }

    // X360 0x8251A568: preserve an image file when autosave is disabled, otherwise autosave
    // it as a one-record ImageFileInfo request. The current PC Update keeps its documented
    // sign-in-gate deviation, but retains the original autosave-enabled and image-copy branches.
    void GuiModule::AutosaveProfile(const CgsGui::ImageFileInfo* lpImageFileInfo)
    {
        if (lpImageFileInfo != 0 && !mProfileHost.GetProfileManager().AutosaveIsEnabled())
        {
            mProfileHost.GetProfileManager().CopyImageToBuffer(lpImageFileInfo);
        }

        if (mProfileHost.GetProfileManager().AutosaveIsEnabled())
        {
            mProfileHost.GetProfileManager().Autosave(&mProfileHost,
                                     lpImageFileInfo != 0 ? 1 : 0, lpImageFileInfo);
            mbProfileAutosavePending  = false;
            mfLastProfileAutosaveTime = mGuiCache.GetTime();
        }
    }

    // The real GuiModule::Update event dispatch (X360 0x82527A58's switch): consume the
    // module-level events, forward the load notifications, and fan the rest to the flow.
    const CgsModule::Event* GuiModule::DispatchInboundGuiEvents(
        bool& rbHasSaveImageEvent, CgsGui::ImageFileInfo& lrSaveImageInfo,
        const CgsModule::Event* lpAfterEvent)
    {
        if (mpGuiEventInputBuffer == 0)
            return lpAfterEvent;

        mpGuiEventInputBuffer->LockForRead();
        const CgsModule::VariableEventQueue<32768, 16>* lpInQueue =
            static_cast<const CgsGui::CgsGuiModuleIO::InputBuffer*>(mpGuiEventInputBuffer)->GetGuiEvents();

        const CgsModule::Event* lpEvent = 0;
        s32 liSize = 0;
        const CgsModule::Event* lpLastDispatchedEvent = lpAfterEvent;
        s32 liId = lpAfterEvent != 0
            ? lpInQueue->GetNextEvent(lpAfterEvent, &lpEvent, &liSize)
            : lpInQueue->GetFirstEvent(&lpEvent, &liSize);
        while (liId >= 0 && lpEvent != 0)
        {
            switch (liId)
            {
                case 141:   // ARTIST82528ACC..AE0: reply with this module's actual keyboard.
                {
                    // FLAG PC-platform leaf: the existing no-argument GUI pump publishes
                    // through mGuiOutQueue and its subscription-filtered observer loop-back.
                    GuiEventKeyboardResponse lResponse;
                    lResponse.lpKeyboard = &mGuiKeyboard;
                    if (mGuiOutQueue.AddEvent(reinterpret_cast<const CgsModule::Event*>(&lResponse),
                                             lResponse.GetEventType(), static_cast<s32>(sizeof(lResponse))))
                        RouteEventToFlow(reinterpret_cast<const CgsModule::Event*>(&lResponse),
                                         lResponse.GetEventType(), static_cast<s32>(sizeof(lResponse)));
                    break;
                }

                case 143:   // ARTIST 82528AE8..AF8: user-index word, then sign-in refresh.
                    mSystemUserProfile.SetUserIndex(*reinterpret_cast<const u32*>(lpEvent));
                    mSystemUserProfile.UpdateUserSigninState();
                    break;

                case 144:   // GuiEventRunFsm -- the flow-change request (BridgeGameToGui)
                    mFsmController.RunFsm(reinterpret_cast<const GuiEventRunFsm*>(lpEvent));
                    break;

                case 481:   // HUD-state load complete: notify the controller + forward
                    mFsmController.HandleHudStateLoadComplete();
                    // fall through -- the record also lands on the notification queue
                case 14:    // load notification    -> the ModelIO output notification queue
                case 16:    // unload notification  -> (the controller's Update consumes them)
                {
                    mModelOutputBuffer.LockForWrite();
                    mModelOutputBuffer.GetLoadNotificationsNonConst()->AddEvent(lpEvent, liId, liSize);
                    mModelOutputBuffer.UnlockForWrite();
                    break;
                }

                case 221:  // ARTIST 82528B28: the same bar size also gates HUD messages.
                    mHudMessageDirector.SetBlackBarSize(*reinterpret_cast<const f32*>(lpEvent));
                    break;

                case 26:    // GuiEventTimeInfo -- the per-frame { delta, now } pair
                    // The cache LEADS with this pair and every GUI-side timer reads it
                    // straight off mpGuiCache+0 (see GuiCache::RecTimeInfo's note). Without
                    // this latch mfTimeStep stays 0 and every GUI dwell/tick in the game is
                    // frozen -- which is exactly what parked BrnGui::Intro in WELCOMETEXT.
                    mGuiCache.RecTimeInfo(
                        reinterpret_cast<const CgsGui::GuiEventTimeInfo*>(lpEvent));
                    break;

                case 504:   // localized audio ready
                case 508:   // play video
                case 513:   // (movie family)
                    mMovieManager.RecvEvent(lpEvent, liId);
                    break;

                case 493:   // World collision invalidate/validate completion
                {
                    const auto* lpCollisionWorldEvent =
                        reinterpret_cast<const GuiEventRequestCollisionWorldEvent*>(lpEvent);
                    if (lpCollisionWorldEvent->meEventType ==
                        GuiEventRequestCollisionWorldEvent::E_COLLISON_WORLD_INVALIDATED)
                        mbCollisionWorldInvalid = true;
                    else if (lpCollisionWorldEvent->meEventType ==
                             GuiEventRequestCollisionWorldEvent::E_COLLISON_WORLD_VALIDATED)
                        mbCollisionWorldInvalid = false;
                    break;
                }

                case 512:   // Traffic-pool emptied/refilled latch
                {
                    const bool lbTrafficPoolEmpty =
                        reinterpret_cast<const GuiEventTrafficPoolEmptied*>(lpEvent)->mbTrafficPoolEmpty;
                    if (lbTrafficPoolEmpty)
                    {
                        CGS_ASSERT(!mbTrafficPoolEmptied, "!mbTrafficPoolEmptied");
                        mbTrafficPoolEmptied = true;
                    }
                    else
                    {
                        CGS_ASSERT(mbTrafficPoolEmptied, "mbTrafficPoolEmptied");
                        mbTrafficPoolEmptied = false;
                    }
                    break;
                }

                case 350:   // GuiEventProgressionProfileData -- the live-profile handoff
                    // ⭐⭐⭐ [one-profile wave 2026-08-28] THE MISSING HALF OF CASE 350, and
                    // the reason this build owned TWO BrnProgression::Profile objects where the
                    // console owns one. X360 BrnGui::GuiModule::Update @0x82527A58:
                    //     case 350:
                    //       BrnGui::ProfileManager::SetProgressionProfile(a1 + 681696, *v61, v61[1]);
                    // i.e. the event's two payload words ARE the manager's mpProgressionProfile /
                    // mpProgressionData, and this is the ONLY writer of either on the console
                    // (SetProgressionProfile @0x824ECC98 has exactly one xref, and it is this).
                    // We routed 350 to the GuiCache only, so the manager never learned the live
                    // profile's address and BrnGuiModule::Prepare installed a module-static
                    // stand-in instead -- a SECOND Profile that Deserialise wrote into and no
                    // gameplay code ever read. The static and its install are deleted with this
                    // arm; the console's own chain is now the only installer.
                    {
                        const BrnGui::GuiEventProgressionProfileData* lpProfileData =
                            reinterpret_cast<const BrnGui::GuiEventProgressionProfileData*>(lpEvent);
                        mProfileHost.GetProfileManager().SetProgressionProfile(lpProfileData->mpProfile,
                                                              lpProfileData->mpProgressionData);
                    }
                    // fall through -- the record also feeds GuiCache::mpProfile (case 350 below)
                case 27:    // Actual Sku notification -> the cache enum owner.
                case 29:    // Actual language notification -> the cache enum owner.
                case 501:   // Original PFX enumeration -> actual cache owner.
                case 330:   // GuiEventSetRoadRuleScoreMode -- the road-rule panel mode word
                case 335:   // GuiEventRoadRuleBegin -- the rule's score type marked active
                case 336:   // GuiEventRoadRuleEnd   -- the rule's score type marked inactive
                case 169:   // GuiEventChangeDistrict -- the district-marker source words
                case 147:   // [H3b] GuiEventUpdateHud -- the player {speed,rpm,gear} words
                case 199:   // [H3b] GuiEventUpdateSatNav -- the icon array (player position arm)
                case 204:   // [H3b] the sat-nav event-filter pair (the ch40 mirror)
                case 207:   // [H3b] GuiRaceCarInfoEvent -- the mRaceCarInfo SoA feed
                case 208:   // Traffic score targets for AboveCarRenderer.
                case 210:   // Visible overhead-sign score targets.
                case 376:   // [H3b] GuiPlayerRaceCarIdEvent -- the player index pair (case-199 gate)
                case 377:   // GuiPlayerCrashingStateChangeEvent -- the crash-bar state latch + the
                            // gameplay-HUD-active drop (RecEvent @0x8250F58C; was misfiled as 132)
                case 379:   // [reveal gate] GuiPlayerEngineEvent -- the ignition latch (+0x4B20)
                case 238:   // Race positions, finished flags and per-slot validity.
                case 380:   // Player entered or left a shortcut.
                case 492:   // [E1] GuiEventCurrentStatus  -- distance driven + player-team table
                case 424:   // [E1] GuiEventScoreUpdate    -- THE EVENT TIMER (mfEventTime/mfTargetTime)
                case 428:   // [E1] GuiAttackScoreUpdate   -- THE STUNT SCORE (current/target/combo/multiplier)
                case 434:   // [showtime] GuiCrashScoreUpdate -- THE SHOWTIME SCORE (cars crashed + distance)
                case 426:   // [road-rage] GuiRoadRageScoreUpdate -- THE TAKEDOWN COUNT (current/target)
                case 194:   // Specific preset races; the cache adopts the per-mode table.
                case 203:   // [event-starts] GuiEventUpdateEventStarts -- THE EVENT-START TABLE
                case 93:    // [A9] GuiEventPrepareForModeStart -- THE MODE-TYPE SEED (meGameModeType)
                case 159:   // Pre-race messages and the in-event map colouring gate.
                case 162:   // Clear the pre-race message count.
                case 170:   // Landmark race list and its navigation tracker.
                case 289:   // [results] GuiEventOfflinePostEvent -- THE OFFLINE RESULT RECORD
                case 318:   // Online post-event record, adopted by the existing cache arm.
                case 292:   // [results] post-event teardown (clears the record + suppress byte)
                case 307:   // Medal totals and wins remaining on the licence.
                case 304:   // [results] raises the presentation-suppressed byte
                case 237:   // [event-start 2026-09-10] GuiGameModeStarted -- drops mbEventPreparedForModeStart
                case 321:   // [event-end 2026-09-10] GuiEventFinishedModeResults -- GuiCache's shared LABEL_232 tail
                case 322:   // [event-end 2026-09-10] GuiEventStopMode -- game mode back to NONE, tracker cleared
                case 556:   // [event-state 2026-09-10] GuiEventEventStateResponse -- the DISCOVERED-event array
                case 373:   // [FX-FLOW 2026-09-24, G13-X5] GuiShutdownEvent -- mShutdownCarID (RecEvent 0x8250FFA8)
                case 374:   // [FX-FLOW 2026-09-24, G13-X5] GuiShutdownFinishedEvent -- mbCarUnlockPending (0x8250FFC4)
                case 44:    // [net] GuiEventNetworkDisconnected -- the local player marked disconnected
                case 58:    // [net] the game launched -- disconnected / eliminated tables cleared
                case 108:   // [net] GuiEventOnlineTimeout -- the online timeout pending byte
                case 239:   // [net] GuiEventRaceDistanceRemaining -- the eliminated bytes
                case 240:   // [net] GuiEventRaceDistanceToCheckpoint -- the checkpoint distance
                case 243:   // [net] GuiEventNetworkPlayerList -- the pre-game roster
                case 244:   // [net] GuiEventNetworkLobbyPlayerList -- the lobby roster
                case 245:   // [net] GuiEventNetworkPlayerStatus -- the in-game roster + host byte
                case 257:   // [net] GuiEventNetworkGameParams -- the params mirror (online game mode)
                case 273:   // [net] GuiEventNetworkLeftGame -- the params security reset
                case 320:   // [net] online showtime completed
                case 79:    // GuiEnteredJunkyard -- the in-junkyard byte
                case 201:   // GuiEventHideDriveThru -- a closed drive-thru's map row hidden
                case 375:   // GuiEventTrophyCarUnlock -- the award screen's unlock type and car
                case 415:   // GuiChangeCarEvent -- current and original car ids for event icons
                    FreeRoamRouteWitness(liId, "cache");
                    // [H1 wave 2026-08-25] On the console EVERY module-input event reaches
                    // GuiCache::RecEvent (its ~180-case switch consumes what it wants);
                    // this build's pump routes selectively, so the two cache-consumed ids
                    // this wave landed handlers for are forwarded here explicitly. 350 is
                    // what fills GuiCache::mpProfile (the odometer asserts it per frame);
                    // 169 is what fills the district-marker words. ⚠️ Do NOT blanket-route
                    // the whole stream: 14/16 are already re-consumed off the notification
                    // queue below and would double-deliver.
                    // [E1 event-status wave 2026-08-26] 492/424/428 join the list on the same
                    // terms: BridgeGameStateToGui's stunt slice posts them and GuiCache::RecEvent
                    // now has the matching three arms. None of the three is re-consumed off the
                    // notification queue, so forwarding them here delivers exactly once.
                    // ⭐⭐ [results-screen wave 2026-08-29] 289/292/304 join on identical terms,
                    // and they were THE last link in the offline results chain. Measured: with
                    // GuiCache::RecEvent's case-289 arm landed but this forward missing, the
                    // bridge posted the 192-byte record (its action-37 arm builds and pushes it
                    // unconditionally on the offline path), the cache never saw it, and
                    // InstantResultsState copied 192 ZERO bytes -- so its own reconstructed
                    // SetupComponents printed the console's "Unhandled game mode! (0)" and the
                    // screen stayed blank. A selective pump means a landed producer AND a landed
                    // consumer still add up to nothing until the id is on this list; that is
                    // three separate places to check, and the log looked identical at each.
                    // None of the three is re-consumed off the notification queue.
                    // [showtime score wave 2026-08-29] 434 joins on IDENTICAL terms and completes
                    // that set for modes 2/16: its only producer is the same bridge's showtime arm
                    // (@0x823EEE18), GuiCache::RecEvent's case-434 arm is its only consumer, and
                    // nothing else in the pump touches it. It is the SOLE writer of
                    // miShowTimeCarsCrashed / miShowTimeComboMultiplier /
                    // mfShowTimeDistanceTravelled -- the three words
                    // EventInfoComponent::UpdateCrash renders.
                    // ⚠️ THE ID IS 434 (AddGuiEvent<GuiCrashScoreUpdate> @0x823D10D0 `li r5, 0x1B2`),
                    // NOT the DecFIGS DWARF's 429. Forwarding 429 here would forward an id nothing
                    // posts, and RecEvent has no arm for it either.
                    // [A9 mode-type arm 2026-08-27] 93 joins on exactly the same terms and it is
                    // the one that makes the other three mean anything: BrnGame::
                    // TranslateEventFlowGameActionToGuiEvent's case-23 arm posts it (mounted +
                    // called), GuiCache::RecEvent's case-93 arm above is its only consumer, and
                    // it is the SOLE writer of meGameModeType -- the switch variable case 424
                    // and case 428 assert against and EventInfoComponent::Update switches on.
                    // ⭐ SELECTIVE, NOT BLANKET (the gateui-campaign house rule): 93 is not
                    // observed by any flow (RouteEventToFlow drops it) and is not re-consumed
                    // off the notification queue, so this forward delivers it exactly once.
                    // [event-starts wave 2026-08-27] 203 joins on identical terms: its only
                    // producer is BridgeGameStateToGui's event-start arm (landed as
                    // GameBridgeGameStateToX_EventStartsGuiEvents.cpp), GuiCache::RecEvent's
                    // case-203 arm is its only consumer, and nothing else in the pump touches
                    // it -- so this forward delivers it exactly once. It is the SOLE writer of
                    // GuiCache::maEventStarts, the table GetProfileEventDisplayInfo walks.
                    mGuiCache.RecEvent(lpEvent, liId);
                    break;

                case 343:   // GuiEventRoadRuleChangeMode -- the active road rule
                    // The console's module switch hands the new rule to the skills manager and,
                    // like every event, then gives the record to GuiCache::RecEvent, which keeps
                    // it for GetActiveRoadRule (the ticker's road-rules mode reads that).
                    mBurnoutSkillsManager.SetRoadRuleMode(
                        reinterpret_cast<const GuiEventRoadRuleChangeMode*>(lpEvent)->meScoreType);
                    mGuiCache.RecEvent(lpEvent, liId);
                    break;

                // The free-burn challenge tracker's event arms, in the console's case order.
                // Only the online free-burn lobby produces these records (the action->GUI
                // translator's 153/154/155/157 arms and the network bridge's 583).
                case 544:
                    mFreeburnChallengeManager.SelectNext();
                    break;
                case 574:
                    mFreeburnChallengeManager.StartChallenge(
                        reinterpret_cast<const GuiChallengeStartEvent*>(lpEvent));
                    break;
                case 576:
                    mFreeburnChallengeManager.TriggerChallenge(
                        reinterpret_cast<const GuiChallengeTriggerResponse*>(lpEvent));
                    break;
                case 577:
                    mFreeburnChallengeManager.HandleNewData(
                        reinterpret_cast<const GuiChallengeUpdateEvent*>(lpEvent));
                    break;
                case 578:
                    mFreeburnChallengeManager.StartResults();
                    break;
                case 579:
                    mFreeburnChallengeManager.FinishChallenge();
                    break;
                case 581:
                    mFreeburnChallengeManager.HandleCompletionStatus(
                        reinterpret_cast<const GuiEventFburnChallengeEveryPlayerStatus*>(lpEvent));
                    break;
                case 583:
                    mFreeburnChallengeManager.StartNotActiveChallenge(
                        reinterpret_cast<const GuiChallengeNotActiveStartEvent*>(lpEvent));
                    break;
                case 584:
                    mFreeburnChallengeManager.EndNotActiveChallenge();
                    break;

                case 358:
                    // X360 copies the four image-save words into a frame-local record, raises
                    // the force/pending latches, then lets Update call AutosaveProfile. The host
                    // record is 24 bytes because the buffer pointer widened; the unwritten
                    // trailing word remains byte-for-byte residue.
                    std::memcpy(&lrSaveImageInfo, lpEvent, sizeof(lrSaveImageInfo));
                    rbHasSaveImageEvent = true;
                    mbForceProfileAutosave = true;
                    mbProfileAutosavePending = true;
                    break;

                case 359:   // Image-file records loaded by ProfileManager (ARTIST GuiModule::Update case 359)
                    mProfileHost.GetProfileManager().LoadImageFiles(
                        &mProfileHost,
                        reinterpret_cast<const CgsGui::ImageFileInfo*>(lpEvent));
                    break;

                case 356:   // [profile-save] GuiAutosaveRequestEvent -- THE AUTOSAVE LATCH
                {
                    // ⭐⭐ X360 GuiModule::Update's event walk @0x82529054 (jumptable
                    // 0x82528C5C case 0 == GUI id 356), instruction for instruction:
                    //     lbz  r11, 0(r30)          ; the request's one payload byte
                    //     lbz  r10, var_430(r1)     ; v142, the per-Update FORCE byte
                    //     or   r11, r11, r10
                    //     stb  r11, var_430(r1)     ; v142 |= payload
                    //     li   r11, 1
                    //     stbx r11, r26, r15        ; *(module + 0x18D844) = 1  (pending)
                    //
                    // ⛔⛔ THIS ARM IS THE ONE LINK THE AUTOSAVE COMMIT DID NOT LAND. Its
                    // message claims "case 356 raises the pending byte", but the diff only
                    // added the CONSUMER (Update's tail) -- `mbProfileAutosavePending` had a
                    // reader and a clearer and NO WRITER, so the latch could never rise and
                    // ProfileManager::Autosave was unreachable. Measured 2026-08-27: a full
                    // junkyard->car-select->driving run logged
                    // `[profile-save] action 55 -> gui 356 (flag 0)` and then never wrote
                    // Memcard\Profile.sav, because the byte on the other side of this arm
                    // stayed down. The 1-byte record is the AutosaveRequestWire356 both
                    // GameBridgeGameStateToX_{Stunt,EventFlow}GuiEvents.cpp post.
                    //
                    // ⚠️ The producers in this build post a payload of ZERO (CarSelectManager's
                    // exit post, BrnCarSelectManager.cpp:1185), so the force byte stays clear
                    // and the tail's 60-second throttle is what actually times the save --
                    // exactly as on the console. Only the paused-game arm (case 505) and the
                    // mugshot arm (case 358) force it.
                    mbForceProfileAutosave =
                        mbForceProfileAutosave || (*reinterpret_cast<const u8*>(lpEvent) != 0);
                    mbProfileAutosavePending = true;
                    break;
                }

                default:
                    // The other module-level consumers (profile/skills/overlays/keyboard/
                    // language...) are subsystem follow-ons; their events pass through to
                    // the flow filter below.
                    break;
            }

            // The console's per-event tail, after GuiCache::RecEvent: the set-tracker, landmark
            // reached, route-information, cache-pointer and regenerate-route ids go to the
            // tracker (GuiCache ignores all five).
            if (liId == 232 || liId == 165 || liId == 211 || liId == 64 || liId == 233)
            {
                FreeRoamRouteWitness(liId, "tracker");
                mGuiTracker.RecEvent(lpEvent, liId, liSize);
            }

            // ⭐ [tut-ticker] THE CUSTOM-RENDERER MANAGER FEED (2026-08-24). On the console
            // every module-input GUI event reaches BrnGui::CustomRendererManager::RecvEvent
            // through the view hop (BridgeFromInputToView -> ViewModule::
            // ProcessIncomingViewEvents' per-event hook @0x8285FCE8 tail). This build feeds
            // the view queue selectively, so the manager forward sits HERE, on the full
            // module-input stream -- exactly-once for everything that transits this queue
            // (537 the tutorial ticker, 64 the GuiCache bind, 258/571 the player image...).
            // The seat deviation is flagged at the console hook in CgsGuiViewModule.cpp.
            mCustomRendererManager.RecvEvent(lpEvent, liId);

            // The observer-subscription fan-out (EventInterpreterModule::ProcessInEvents).
            RouteEventToFlow(lpEvent, liId, liSize);

            lpLastDispatchedEvent = lpEvent;
            const CgsModule::Event* lpNext = 0;
            liId = lpInQueue->GetNextEvent(lpEvent, &lpNext, &liSize);
            lpEvent = lpNext;
        }
        mpGuiEventInputBuffer->UnlockForRead();
        return lpLastDispatchedEvent;
    }

    // The REAL GuiResourceModule dispatch (replaces ServiceFsmBundleRequests). Runs the
    // reconstructed CgsGui::GuiResourceModule each frame against its own persistent IO
    // pair, and bridges the two queue ends to the flow controller's ModelIO buffers --
    // the same 39-in / 14-out contract the host stand-in served, now through the module:
    //   1. feed this frame's controller load requests (GuiEventLoadRequest, id 39) into
    //      the module input, then clear the controller queue (consumed);
    //   2. run the module -- it drains the requests into its bundle-load queue, advances
    //      the acquire state machine, and at its Update tail runs the [PC] platform
    //      servicer that loads FSM\<NAME>.BUNDLE synchronously; completed loads post
    //      GuiEventLoadNotification (14) into the module output;
    //   3. clear the module input's now-consumed request queue (the persistent PC buffer
    //      is not recreated per frame as the console's transient one is);
    //   4. bridge the module's load notifications into the ModelIO output notification
    //      queue the controller reads (what the host stand-in posted on completion);
    //   5. clear the module output's bridged notifications.
    // The module's acquire machine takes several frames per bundle (acquire-miss -> load
    // -> re-acquire -> notify); the controller's WFLOAD stage polls for the notification,
    // so the completion arriving 1+ frames after the request is safe. On the console the
    // module runs under the model scheduler between the controller's request-post and
    // notification-read; here it runs in that same slot, before the controller Update.
    void GuiModule::DispatchGuiResourceModule()
    {
        // 1. Feed the controller's requests (posted into mModelInputBuffer by the previous
        //    frame's GuiFsmController::Update) into the module input, then clear them.
        mModelInputBuffer.LockForWrite();
        mResourceInputBuffer.LockForWrite();
        CgsGui::GuiEventQueueSmall* lpControllerRequests = mModelInputBuffer.GetLoadRequests();
        mGuiResourceModule.AddResourceRequests(lpControllerRequests, &mResourceInputBuffer);
        lpControllerRequests->Clear();
        mResourceInputBuffer.UnlockForWrite();
        mModelInputBuffer.UnlockForWrite();

        // 2. Run the module for this frame (it locks its own IO pair internally; hold no
        //    lock here). The Update tail's ServicePlatformRequests loads the bundle files.
        mGuiResourceModule.Update(&mResourceInputBuffer, &mResourceOutputBuffer);

        // 3. Drop this frame's now-consumed input requests (ProcessIncomingLoadRequests
        //    reads but does not clear them; the persistent PC buffer must not re-queue).
        mResourceInputBuffer.LockForWrite();
        mResourceInputBuffer.GetLoadRequestsNonConst()->Clear();
        mResourceInputBuffer.UnlockForWrite();

        // 4. Bridge every notification to ModelIO, where both the FSM controller and
        //    GuiCache observe it. Apt movie load notifications (request types 4..7) also
        //    go to the VIEW input buffer as
        //      view event 14, where the REAL CgsGui::ViewModule::ProcessIncomingLoadNotification
        //      @0x8285BD30 registers each header (AddAptData). Phase 2 routes the movie-slot
        //      bundle IO through the module, so these replace the AptRuntimeHost's
        //      PopPendingLoadNotification ring for the flow movie.
        //    The dual delivery is the ARTIST contract: the cache owns resource state while
        //    ViewModule owns Apt registration.
        mResourceOutputBuffer.LockForRead();
        mModelOutputBuffer.LockForWrite();
        mViewInputBuffer.LockForWrite();
        {
            const CgsGui::GuiResourceModuleIO::InputBuffer::GuiEventQueue* lpNotifications =
                mGuiResourceModule.GetLoadedNotifications(&mResourceOutputBuffer);
            const CgsModule::Event* lpEvent = 0;
            s32 liSize = 0;
            s32 liId = lpNotifications->GetFirstEvent(&lpEvent, &liSize);
            while (liId >= 0 && lpEvent != 0)
            {
                bool lbAptMovie   = false;
                bool lbAptUnload  = false;
                if (liId == 14)
                {
                    const s32 liReqType = static_cast<s32>(
                        reinterpret_cast<const CgsGui::GuiEventLoadNotification*>(lpEvent)->meRequestType);
                    lbAptMovie = (liReqType >= 4 && liReqType <= 7) || liReqType == 10;
                }
                else if (liId == 15)
                {
                    // ⭐⭐ [driver-details pause wave 2026-08-28] THE MISSING OTHER HALF of the
                    // line above, and the reason a released apt movie was never un-registered.
                    // GuiResourceModule::UnloadBundle posts a type-15 unload-REQUEST notification
                    // (OutputBuffer::AddUnloadRequestNotification @0x8285AC08, `li r5,0xF`), whose
                    // console consumer is ViewModule::ProcessIncomingUnloadRequestNotification
                    // @0x828586E8 -> AptDataHandler::RemoveAptData. This bridge forwarded ONLY the
                    // type-14 loads to the view, so the removal end of the pair could never run --
                    // AddAptData is idempotent by name, so every reload of a released movie handed
                    // the Apt linker the STALE header. Same apt request-type gate as the load side
                    // (the view's own arm re-tests 4..7, which is the console's gate).
                    const s32 liReqType = static_cast<s32>(
                        reinterpret_cast<const CgsGui::GuiEventUnloadRequestNotification*>(
                            lpEvent)->meRequestType);
                    lbAptUnload = (liReqType >= 4 && liReqType <= 7);
                }
                mModelOutputBuffer.GetLoadNotificationsNonConst()->AddEvent(
                    lpEvent, liId, liSize);
                // Dynamic components observe completion directly (ARTIST
                // LargeCarComponent 0x8241B7A8/0x8241B868). These local module
                // notifications bypass DispatchInboundGuiEvents, so fan them
                // out here as well as delivering them to the cache/controller.
                // The PC loader also emits id-zero Apt registrations for every
                // bundled clip (CgsGuiResourceModulePC.cpp); those are view data,
                // not completions for a component's named resource request.
                if ((liId == 14 && (!lbAptMovie
                         || reinterpret_cast<const CgsGui::GuiEventLoadNotification*>(
                                lpEvent)->muLoadRequestId != 0))
                    || liId == 16)
                    RouteEventToFlow(lpEvent, liId, liSize);
                if (lbAptMovie)
                    mViewInputBuffer.GetViewStateQueue()
                        .CgsModule::VariableEventQueue<65536, 16>::AddEvent(lpEvent, 14, liSize);
                else if (lbAptUnload)
                    mViewInputBuffer.GetViewStateQueue()
                        .CgsModule::VariableEventQueue<65536, 16>::AddEvent(lpEvent, 15, liSize);
                const CgsModule::Event* lpNext = 0;
                liId = lpNotifications->GetNextEvent(lpEvent, &lpNext, &liSize);
                lpEvent = lpNext;
            }
        }
        mViewInputBuffer.UnlockForWrite();
        mModelOutputBuffer.UnlockForWrite();
        mResourceOutputBuffer.UnlockForRead();

        // 5. The notifications are bridged; clear the module output queue for next frame.
        mResourceOutputBuffer.LockForWrite();
        mResourceOutputBuffer.GetLoadNotificationsNonConst()->Clear();
        mResourceOutputBuffer.UnlockForWrite();
    }

    // (RequestAptMovieLoad RETIRED, slice 2: no more host movie-slot requests --
    // the engine's AptLoader owns movie data acquisition.)

    // (RequestAptMovieLoadThroughModule RETIRED, slice 2: the engine's AptLoader
    // requests movie data itself -- registered-data first, bundle-IO fallback --
    // through the real AptLoaderStartAsyncLoad platform hook.)

    // [PC IO] the ORIGINAL host FSM-bundle stand-in: serviced the controller's FSM-bundle
    // load requests synchronously and posted the load notification it waits for. SUPERSEDED
    // by DispatchGuiResourceModule (the real CgsGui::GuiResourceModule now owns this path);
    // retained unused this phase -- /OPT:REF strips the unreferenced body from the exe.
    // (On the console the request queue reaches CgsGui::GuiResourceModule through the
    // module scheduler; ProcessIncomingLoadRequests + LoadBundle then post the
    // notification -- those bodies are reconstructed, but the module dispatch that runs
    // them was not, so the IO leaf lived here.)
    void GuiModule::ServiceFsmBundleRequests()
    {
        mModelInputBuffer.LockForWrite();
        CgsGui::GuiEventQueueSmall* lpRequests = mModelInputBuffer.GetLoadRequests();

        const CgsModule::Event* lpEvent = 0;
        s32 liSize = 0;
        s32 liId = lpRequests->GetFirstEvent(&lpEvent, &liSize);
        bool lbAnyServed = false;
        while (liId >= 0 && lpEvent != 0)
        {
            if (liId == 39)   // GuiEventLoadRequest
            {
                const CgsGui::GuiEventLoadRequest* lpRequest =
                    reinterpret_cast<const CgsGui::GuiEventLoadRequest*>(lpEvent);
                if (lpRequest->meLoadUnload == CgsGui::E_GUI_RESOURCEREQUEST_LOAD &&
                    lpRequest->mpacFileToLoad != 0)
                {
                    lbAnyServed = true;

                    // The controller's request ids map onto the flow slots (13/14/15 =
                    // SCREEN/HUD/OVERLAY); each flow owns a resident pool so a load for
                    // one flow never drops another flow's live LuaCode.
                    s32 liFlow = E_GUIFLOW_HUD;
                    switch (lpRequest->muLoadRequestId)
                    {
                        case 13u: liFlow = E_GUIFLOW_SCREEN;  break;
                        case 14u: liFlow = E_GUIFLOW_HUD;     break;
                        case 15u: liFlow = E_GUIFLOW_OVERLAY; break;
                        default:  break;
                    }

                    // Re-init that flow's pool for the fresh bundle (the previous FSM's
                    // LuaCode was released by the flow's staged Release before this load).
                    CgsResource::Pool::InitOptions lOptions;
                    lOptions.miId    = 2;
                    lOptions.mpcName = "GuiFsm";
                    for (u32 lt = 0; lt < CgsResource::E_MEMTYPE_NUMTYPES; ++lt)
                    {
                        lOptions.maHeapInfo[lt].muMaxNodes       = 64u;
                        lOptions.maHeapInfo[lt].muHeapMemorySize = KU_FSM_POOL_BYTES - 64u * 1024u;
                        lOptions.maHeapInfo[lt].muHeapAlignment  = 16u;
                        lOptions.mResource.m_baseResources[lt]   = s_fsmPoolBacking[liFlow][lt];
                        lOptions.mDescriptor.m_baseResourceDescriptors[lt].m_size      = KU_FSM_POOL_BYTES;
                        lOptions.mDescriptor.m_baseResourceDescriptors[lt].m_alignment = 16u;
                    }
                    lOptions.muMaxResources         = 64u;
                    lOptions.muMaxImports           = 64u;
                    lOptions.miRefCountThreshold    = 0;
                    lOptions.miNumDependencies      = 0;
                    lOptions.miBankId               = 0;
                    lOptions.mbAllowDefragmentation = false;
                    mFsmBundlePool[liFlow].InitPool(&lOptions);

                    char lacBundlePath[160];
                    std::snprintf(lacBundlePath, sizeof(lacBundlePath), "FSM/%s.BUNDLE",
                                  lpRequest->mpacFileToLoad);

                    CgsResource::BundleLoader lLoader;
                    const s32 liLoaded = lLoader.LoadBundle(lacBundlePath, &mFsmBundlePool[liFlow],
                                                            CgsResource::ResolveResourceType);
                    s32 liIndex = -1;
                    CgsResource::Entry* lpEntry = (liLoaded > 0)
                        ? mFsmBundlePool[liFlow].FindFirstResourceOfType(
                              CgsResource::E_RESOURCETYPE_LUACODE, &liIndex)
                        : 0;

                    char lac[200];
                    std::snprintf(lac, sizeof(lac),
                        "[GuiModule] FSM bundle '%s' -> %s (request id %u).\n",
                        lacBundlePath, lpEntry != 0 ? "loaded" : "MISSING",
                        lpRequest->muLoadRequestId);
                    CgsDev::Log::WriteToLog(lac);

                    if (lpEntry != 0)
                    {
                        // The notification the controller's WFLOAD stage waits for (the
                        // GuiResourceModule's AddLoadNotification record, queue type 14).
                        CgsGui::GuiEventLoadNotification lNotification;
                        lNotification.mResourceHandle.mpResourceMemory =
                            &lpEntry->mResource.m_baseResources[CgsResource::E_MEMTYPE_MAINMEMORY];
                        lNotification.mResourceHandle.mpSourceEntry = lpEntry;
                        lNotification.meRequestType   = lpRequest->meRequestType;
                        lNotification.muLoadRequestId = lpRequest->muLoadRequestId;

                        mModelOutputBuffer.LockForWrite();
                        mModelOutputBuffer.GetLoadNotificationsNonConst()->AddEvent(
                            reinterpret_cast<const CgsModule::Event*>(&lNotification), 14,
                            static_cast<s32>(sizeof(lNotification)));
                        mModelOutputBuffer.UnlockForWrite();
                    }
                }
                // Unload requests never reach this queue on the reconstructed controller
                // (its WFUNLOAD stage completes against the dummy notification).
            }
            const CgsModule::Event* lpNext = 0;
            liId = lpRequests->GetNextEvent(lpEvent, &lpNext, &liSize);
            lpEvent = lpNext;
        }
        if (lbAnyServed || liId < 0)
            lpRequests->Clear();
        mModelInputBuffer.UnlockForWrite();
    }

    // ARTIST82507800; the native caller invokes this immediately after
    // CgsGui::GuiModule::Update, while the same module OutputBuffer is still live.
    void GuiModule::HandleEventsPostBaseModuleUpdate(
        CgsGui::CgsGuiModuleIO::OutputBuffer* lpOutput)
    {
        lpOutput->LockForRead();

        const CgsModule::Event* lpEvent = 0;
        s32 liEventSize = 0;
        s32 liEventType = lpOutput->GetOutEventQueue()->GetFirstEvent(&lpEvent, &liEventSize);
        while (lpEvent != 0)
        {
            switch (liEventType)
            {
            case 493:
            {
                const GuiEventRequestCollisionWorldEvent* lpRequest =
                    reinterpret_cast<const GuiEventRequestCollisionWorldEvent*>(lpEvent);
                switch (lpRequest->meEventType)
                {
                case GuiEventRequestCollisionWorldEvent::E_COLLISON_WORLD_INVALIDATE:
                    if (meCollisionWorldStateValidationState !=
                        E_COLLISIONWORLDSTATEVALIDATIONSTATE_IDLE)
                    {
                        CgsDev::Assert::BeginAssert();
                        CgsDev::Assert::FireAssert(
                            "meCollisionWorldStateValidationState == E_COLLISIONWORLDSTATEVALIDATIONSTATE_IDLE",
                            "..\\..\\..\\GameSource\\Gui/BrnGuiModule.cpp", 1729);
                        CgsDev::Assert::EndAssert();
                    }
                    // ARTIST stbx to GuiModule +0x18D83B.
                    mbCollisionWorldInvalidateForNetworking = true;
                    break;

                case GuiEventRequestCollisionWorldEvent::E_COLLISON_WORLD_VALIDATE:
                    if (meCollisionWorldStateValidationState !=
                        E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALID_FOR_NETWORKING)
                    {
                        CgsDev::Assert::BeginAssert();
                        CgsDev::Assert::FireAssert(
                            "meCollisionWorldStateValidationState == E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALID_FOR_NETWORKING",
                            "..\\..\\..\\GameSource\\Gui/BrnGuiModule.cpp", 1737);
                        CgsDev::Assert::EndAssert();
                    }
                    // ARTIST stbx to GuiModule +0x18D83C.
                    mbCollisionWorldValidateForNetworking = true;
                    break;

                default:
                    CgsDev::Assert::BeginAssert();
                    CgsDev::Assert::FireAssert(
                        "Invalid collsion world request output event type",
                        "..\\..\\..\\GameSource\\Gui/BrnGuiModule.cpp", 1745);
                    CgsDev::Assert::EndAssert();
                    break;
                }
                break;
            }

            case 508:
            case 509:
                mMovieManager.RecvEvent(lpEvent, liEventType);
                break;

            case 514:
            case 515:
                mColourCalibrationScreen.RecvEvent(lpEvent, liEventType);
                break;

            default:
                break;
            }

            liEventType = lpOutput->GetOutEventQueue()->GetNextEvent(
                lpEvent, &lpEvent, &liEventSize);
        }

        lpOutput->UnlockForRead();
    }

    // Drain one observer's StateInterface output queue -- the per-frame dispatch point for
    // everything its states post (the ModelModule bridge + EventInterpreter
    // ProcessOutEvents roles). The 34/35 subscription records key into THAT observer's
    // observed-id table. The fourth slot is the always-available components manager,
    // whose Prepare posts its real 19-id registration through the same records.
    void GuiModule::DrainFlowOutputQueue(s32 liFlow)
    {
        CgsGui::GuiStackEventQueue::GuiEventQueueLarge* lpOutQueue = 0;
        switch (liFlow)
        {
            case E_GUIFLOW_SCREEN:  lpOutQueue = mScreenFlow.GetOutputEventQueue();  break;
            case E_GUIFLOW_HUD:     lpOutQueue = mHudFlow.GetOutputEventQueue();     break;
            case E_GUIFLOW_OVERLAY: lpOutQueue = mOverlayFlow.GetOutputEventQueue(); break;
            case E_GUIOBSERVER_ALWAYSAVAILABLE:
                lpOutQueue = mAlwaysAvailableComponentsManager.GetOutputEventQueue();
                break;
            default:                break;
        }
        if (lpOutQueue == 0)
            return;

        CgsModule::VariableEventQueue<65536, 16>* lpOutBase = lpOutQueue;
        const CgsModule::Event* lpEvent = 0;
        s32 liSize = 0;
        s32 liId = lpOutBase->GetFirstEvent(&lpEvent, &liSize);
        while (liId >= 0 && lpEvent != 0)
        {
            switch (liId)
            {
                case 34:   // RegisterForEvents (the observer-subscription record)
                case 35:   // UnRegisterForEvents
                {
                    const s32 liType =
                        reinterpret_cast<const RegisterEventRecord*>(lpEvent)->miEventType;
                    if (liType >= 0 && liType < KI_MAX_OBSERVED_EVENT_ID)
                        mabObservedEventIds[liFlow][liType] = (liId == 34);
                    break;
                }
                case 36:   // PriorityRegisterForEvent
                {
                    if (liSize < static_cast<s32>(sizeof(PriorityRegisterRecordPrefix)))
                        break;
                    const PriorityRegisterRecordPrefix* lpRecord =
                        reinterpret_cast<const PriorityRegisterRecordPrefix*>(lpEvent);

                    PriorityClaim* lpClaim = 0;
                    for (s32 lc = 0; lc < KI_MAX_PRIORITY_CLAIMS_PER_FLOW; ++lc)
                    {
                        PriorityClaim& lrCandidate = maPriorityClaims[liFlow][lc];
                        if (lrCandidate.mbActive &&
                            lrCandidate.miEventType == lpRecord->miEventType)
                        {
                            lpClaim = &lrCandidate;
                            break;
                        }
                        if (lpClaim == 0 && !lrCandidate.mbActive)
                            lpClaim = &lrCandidate;
                    }
                    if (lpClaim == 0)
                        break;

                    lpClaim->mbActive    = true;
                    lpClaim->miEventType = lpRecord->miEventType;
                    for (s32 li = 0; li < KI_MAX_OBSERVED_EVENT_ID; ++li)
                        lpClaim->mabOverriddenEventIds[li] = false;
                    const u32 luCount = (lpRecord->muOverrideCount < 600u)
                        ? lpRecord->muOverrideCount : 600u;
                    for (u32 lu = 0; lu < luCount; ++lu)
                    {
                        const s32 liOverridden = lpRecord->maiEventTypeOverridden[lu];
                        if (liOverridden >= 0 && liOverridden < KI_MAX_OBSERVED_EVENT_ID)
                            lpClaim->mabOverriddenEventIds[liOverridden] = true;
                    }
                    break;
                }
                case 37:   // PriorityUnRegisterForEvent
                {
                    const s32 liPriority =
                        reinterpret_cast<const RegisterEventRecord*>(lpEvent)->miEventType;
                    for (s32 lc = 0; lc < KI_MAX_PRIORITY_CLAIMS_PER_FLOW; ++lc)
                    {
                        PriorityClaim& lrClaim = maPriorityClaims[liFlow][lc];
                        if (lrClaim.mbActive && lrClaim.miEventType == liPriority)
                        {
                            lrClaim.mbActive = false;
                            lrClaim.miEventType = -1;
                            break;
                        }
                    }
                    break;
                }
                case 38:   // StopPriorityEventBlocking
                    mabPriorityBlocking[liFlow] = false;
                    break;

                case 39:   // StateInterface::RequestResource (dynamic car artwork, etc.)
                    // ARTIST EventInterpreterModule::ProcessOutEvents 0x8285E1D0
                    // forwards these records to its resource-output queue. Feed the
                    // same native request to the resource module alongside cached loads.
                    mModelInputBuffer.LockForWrite();
                    mModelInputBuffer.GetLoadRequests()->AddEvent(lpEvent, liId, liSize);
                    mModelInputBuffer.UnlockForWrite();
                    break;

                case KI_GUIEVENT_PLAY_VIDEO:   // 508
                case KI_GUIEVENT_STOP_VIDEO:   // 509
                    mMovieManager.GetReceiverQueue()->AddEvent(lpEvent, liId, liSize);
                    break;

                case 514:   // colour-calibration screen SHOW
                case 515:   // colour-calibration screen HIDE
                    // X360 GuiModule::HandleEventsPostBaseModuleUpdate @0x82507800 -- the
                    // function that runs immediately after the base module update
                    // (@0x8252A330) and walks the module OUT-event queue, dispatching
                    // 493 -> the collision-world latches, 508/509 -> MovieManager::RecvEvent
                    // and 514/515 -> ColourCalibrationScreen::RecvEvent
                    // (`bl 0x824471D0` @0x825079A8, with r5 still holding the event id).
                    // THIS DRAIN IS THE PC STAND-IN FOR THAT FUNCTION -- it already carries
                    // its 508/509 arm -- so the calibration arm belongs here, at the same
                    // point in the frame (after the flows have ticked and posted).
                    // This is the RE-KEYED form: the console's base module rewraps each
                    // channel-40 GuiEventOut record by its inner event type before the
                    // out-queue is walked, so HandleEventsPostBaseModuleUpdate sees 514/515
                    // directly. The PC queue does not re-key, so the CHANNEL-40 form is
                    // handled in `case 40` below; both are the same console wire.
                    mColourCalibrationScreen.RecvEvent(lpEvent, liId);
                    // The console does NOT consume it: BridgeGuiToDirector @0x823CBF70 walks
                    // the SAME out-event queue afterwards and turns 514/515 into
                    // SetGotColourCalibration{Shown,Hidden}Event. Forward it on.
                    mGuiOutQueue.AddEvent(lpEvent, liId, liSize);
                    break;

                case 40:   // channel 40: GuiEventOut command records -> the game bridge
                {
                    // Command 507 = "refresh the player name" (the {1, 507, 12} record
                    // BootProfile::OnLeave posts as the profile boot completes). On the
                    // console it round-trips through the game/network side and comes back
                    // as GUI in-event 507, whose Update arm (0x82527A58 case 507) calls
                    // UpdatePlayerName. [FLAG PC-platform seam] the network module that
                    // reflects it does not exist on PC, so the record is answered at the
                    // drain -- the same call at the same point in the frame, one hop
                    // earlier. DELETE-WHEN the network sign-in manager lands and posts
                    // in-event 507; then this becomes a plain forward and case 507 moves
                    // to DispatchInboundGuiEvents.
                    if (liSize >= 8 &&
                        reinterpret_cast<const u32*>(lpEvent)[1] == 507u)
                    {
                        UpdatePlayerName();
                        break;   // consumed, exactly as the console's Update arm consumes it
                    }

                    // Commands 514 / 515 -- the colour-calibration screen show/hide requests.
                    // BrnGui::CrashNavColourCalibrate::ShowCalibrationCard @0x824CE7A8 posts
                    // them on CHANNEL 40 as { muHeader0 = 1, muEventType = 514/515,
                    // muHeader2 = 12 } 16-byte records (`li r5,0x28` = channel 40,
                    // `li r6,0x10` = 16, `li r11,0x202`/`0x203`), NOT as type-keyed events.
                    // On the console the base module's out-event rewrap turns them into
                    // plain 514/515 before HandleEventsPostBaseModuleUpdate @0x82507800 sees
                    // them; the PC queue keeps them on their channel, so the arm is applied
                    // here too. NOT consumed -- BridgeGuiToDirector decodes the same record
                    // out of mGuiOutQueue (BrnGameModule.cpp `case 514:` / `case 515:`), so
                    // it must still be forwarded below.
                    if (liSize >= 8)
                    {
                        const u32 luCalibrationCommand =
                            reinterpret_cast<const u32*>(lpEvent)[1];
                        if (luCalibrationCommand == 514u || luCalibrationCommand == 515u)
                        {
                            const CgsModule::Event* lpCalibrationPayload = lpEvent;
                            if (liSize >= 12)
                            {
                                const u32 luOffset = reinterpret_cast<const u32*>(lpEvent)[2];
                                if (luOffset >= 12u && static_cast<s32>(luOffset) < liSize)
                                {
                                    lpCalibrationPayload =
                                        reinterpret_cast<const CgsModule::Event*>(
                                            reinterpret_cast<const u8*>(lpEvent) + luOffset);
                                }
                            }
                            mColourCalibrationScreen.RecvEvent(
                                lpCalibrationPayload, static_cast<s32>(luCalibrationCommand));
                        }
                    }

                    // ⭐⭐ INNER ID 144 -- GuiEventRunFsm posted BY A FLOW STATE. This is the
                    // seat the offline results screen's exit needed and did not have.
                    //
                    // The console's chain: InstantResultsState::TriggerExitResults @0x824D58A8
                    // ends with OutputGuiEvent<GuiEventRunFsm> @0x824938D0, which stack-builds
                    // {sizeof=0x18, type=0x90, offset=0x10} + the 24-byte record and AddEvents
                    // it on CHANNEL 40. EventInterpreterModule::ProcessOutEvents' case '('
                    // then UNWRAPS it -- @0x8285E568 `lwz r11,8(r22)` (offset) / `lwz r6,0(r22)`
                    // (payload size) / `lwz r5,4(r22)` (inner type) -> AddEvent into the module's
                    // out-event buffer -- and the module bus fans that channel back around as
                    // in-events, where GuiModule::Update's case 144 hands it to
                    // GuiFsmController::RunFsm. (That loop-back is the same one the profile
                    // manager's out-queue pump below already models, and it is how the
                    // autosave-icon flag reaches the always-available manager.)
                    //
                    // This build routes channel 40 to the game bridge only, so without this arm
                    // a state-posted RunFsm is a SILENT DROP: BridgeGuiToGameState has no
                    // case 144 either (its X360 switch does not carry one -- checked), so the
                    // record simply evaporates and the results screen ADVANCEs into nothing.
                    // Answered at the drain, one hop earlier than the console's bus round-trip
                    // -- the identical accommodation the 507 arm above already makes, and for
                    // the identical reason. NOT consumed: the record is still forwarded below,
                    // exactly as the console still puts it on the out buffer.
                    // DELETE-WHEN the out-buffer -> in-events bus loop-back is modelled
                    // generically; then this becomes a plain forward.
                    if (liSize >= 12)
                    {
                        const u32* lpuRecord = reinterpret_cast<const u32*>(lpEvent);
                        const u32  luInnerType   = lpuRecord[1];
                        const u32  luInnerOffset = lpuRecord[2];
                        if (luInnerType == 144u && luInnerOffset >= 12u &&
                            static_cast<s32>(luInnerOffset) + static_cast<s32>(sizeof(GuiEventRunFsm))
                                <= liSize)
                        {
                            mFsmController.RunFsm(
                                reinterpret_cast<const GuiEventRunFsm*>(
                                    reinterpret_cast<const u8*>(lpEvent) + luInnerOffset));
                        }
                    }

                    // EventInterpreterModule::ProcessOutEvents @0x8285E568 unwraps a
                    // channel-40 GuiEventWrapper before it publishes the GuiModule output:
                    // word 0 is the raw payload size, word 1 is the event type, and word 2
                    // is the payload offset.  Every game-module bridge consumes that
                    // canonical, type-keyed queue; leaving the wrapper keyed as 40 makes
                    // BridgeGuiToSound miss events such as voice-over request 466.
                    const u32* const lpuWrapper = reinterpret_cast<const u32*>(lpEvent);
                    const u32 luPayloadSize   = lpuWrapper[0];
                    const u32 luEventType     = lpuWrapper[1];
                    const u32 luPayloadOffset = lpuWrapper[2];
                    const CgsModule::Event* const lpRawEvent =
                        reinterpret_cast<const CgsModule::Event*>(
                            reinterpret_cast<const u8*>(lpEvent) + luPayloadOffset);
                    mGuiOutQueue.AddEvent(
                        lpRawEvent, static_cast<s32>(luEventType),
                        static_cast<s32>(luPayloadSize));

                    if (luEventType == 141u)
                    {
                        // FLAG PC-platform leaf: this existing channel-40 drain has no
                        // module-inbound bus round-trip. Execute the original141 reply
                        // here, as for144/507 above; the subscribed state reads142 next tick.
                        GuiEventKeyboardResponse lResponse;
                        lResponse.lpKeyboard = &mGuiKeyboard;
                        if (mGuiOutQueue.AddEvent(reinterpret_cast<const CgsModule::Event*>(&lResponse),
                                                 lResponse.GetEventType(), static_cast<s32>(sizeof(lResponse))))
                            RouteEventToFlow(reinterpret_cast<const CgsModule::Event*>(&lResponse),
                                             lResponse.GetEventType(), static_cast<s32>(sizeof(lResponse)));
                    }

                    // ProcessOutEvents also returns the unwrapped event to the interpreter's
                    // observer fan-out.  This is why a state that posts voice-over event 466
                    // observes 466 as "started" on the following GUI update, while sound later
                    // posts the distinct completion event 467 through its pre-update output.
                    // ARTIST GuiModule::Update 0x828602C8 appends the output events
                    // to mLoadNotifications for the next input/view pass. The PC
                    // pump already delivers these to observers here; include the
                    // renderer observer too, as DispatchInboundGuiEvents does.
                    // Without it, screen-posted ticker messages never reach the view.
                    mCustomRendererManager.RecvEvent(lpRawEvent, static_cast<s32>(luEventType));
                    // The results teardown also belongs to the cache observer. Flow
                    // output does not pass through DispatchInboundGuiEvents on PC.
                    if (luEventType == 292u)
                        mGuiCache.RecEvent(lpRawEvent, static_cast<s32>(luEventType));
                    RouteEventToFlow(
                        lpRawEvent, static_cast<s32>(luEventType),
                        static_cast<s32>(luPayloadSize));
                    break;
                }

                case 41:   // channel 41: GuiOutViewState records -> the view input queue
                {
                    const CgsGui::GuiEventPlayAptMovie* lpPlay =
                        reinterpret_cast<const CgsGui::GuiEventPlayAptMovie*>(lpEvent);
                    // [FLAG PC witness] `[hud-vis] ch41` -- lane `hud`, bug-test wave
                    // 2026-09-04. NOT IN THE X360 BINARY. The console's channel-41 arm
                    // (EventInterpreterModule::ProcessOutEvents @0x8285E1D0 case ')' ,
                    // @0x8285E5xx) forwards EVERY record's payload to the view queue --
                    // `AddEvent(viewQueue, record + record[2], record[1], record[0])`,
                    // no id filter at all. This build filters; a record whose type is not
                    // in the list below never reaches the view module and therefore never
                    // reaches CustomRendererManager::RecvEvent, so its HUD element never
                    // changes state. This line names each record and whether it survived.
                    // Bounded: first two of each type. Opt-in behind BRN_HUD_VIS=1.
                    // DELETE-WHEN tools\tests\cases\hud_visibility.ps1 is retired.
                    if (HudVisWitnessEnabled() && CgsDev::Log::gpDebugPrint != 0)
                    {
                        static s32 saiSeen[64]  = { 0 };
                        static u32 sauType[64]  = { 0 };
                        static s32 siSeenCount  = 0;
                        const u32 luType = lpPlay->muEventType;
                        s32 liIndex = -1;
                        for (s32 lk = 0; lk < siSeenCount; ++lk)
                            if (sauType[lk] == luType) { liIndex = lk; break; }
                        if (liIndex < 0 && siSeenCount < 64)
                        {
                            liIndex = siSeenCount++;
                            sauType[liIndex] = luType;
                            saiSeen[liIndex] = 0;
                        }
                        if (liIndex >= 0 && saiSeen[liIndex] < 2)
                        {
                            ++saiSeen[liIndex];
                            // Mirrors the dispatch below exactly: 18 and 25 have their own
                            // body-rebuild arms, everything else rides the generalized
                            // forward, which needs a sane payload offset.
                            const u32 luOffset =
                                reinterpret_cast<const u32*>(lpEvent)[2];
                            const bool lbBridged =
                                (luType == 18u || luType == 25u) ||
                                (luOffset >= 12u &&
                                 static_cast<s32>(luOffset) <= liSize);
                            *CgsDev::Log::gpDebugPrint
                                << "[hud-vis] ch41 type=" << static_cast<s32>(luType)
                                << " size=" << liSize
                                << (lbBridged ? " bridged=1\n" : " bridged=0 DROPPED\n");
                        }
                    }
                    if (lpPlay->muEventType == 18)   // PlayAptMovie {name, level}
                    {
                        PrepareAptRuntime();   // idempotent

                        struct { const char* mpacMovieName; s32 miLevelNum; } lBody =
                            { lpPlay->mpacMovieName, lpPlay->miLevelNum };
                        mViewInputBuffer.GetViewStateQueue()
                            .CgsModule::VariableEventQueue<65536, 16>::AddEvent(
                                reinterpret_cast<const CgsModule::Event*>(&lBody), 18,
                                static_cast<s32>(sizeof(lBody)));
                    }
                    else if (lpPlay->muEventType == 25)   // GuiEventClearScreenSet {mode, alpha}
                    {
                        // The view's black-backdrop control: BootLegal enables it (alpha
                        // 1.0) under the title, BootLegal::OnLeave / BootProfile::OnEnter
                        // disable it so the save/load prompt composes over the
                        // loading-screen background (ViewModule case 25 @0x8285FCE8).
                        const CgsGui::GuiEventClearScreenSet* lpClear =
                            reinterpret_cast<const CgsGui::GuiEventClearScreenSet*>(lpEvent);
                        struct { s32 miMode; f32 mfAlpha; } lBody =
                            { lpClear->meClearScreen, lpClear->mfAlpha };
                        mViewInputBuffer.GetViewStateQueue()
                            .CgsModule::VariableEventQueue<65536, 16>::AddEvent(
                                reinterpret_cast<const CgsModule::Event*>(&lBody), 25,
                                static_cast<s32>(sizeof(lBody)));
                    }
                    // ⭐ [boost-bar + H3b reconcile 2026-08-25] the custom-renderer record
                    // family -- 213 (SatNav/MainMap show/hide, {s32 mode, f32 fade, u8
                    // enable}), 214/215 (the BoostBar/AboveCar enables), 204 (the sat-nav
                    // event-starts display command) and 212 (the per-frame RenderSatNav
                    // payload) -- bridged BODY-ONLY into the view-state queue, exactly as
                    // the case-18/25 bridges above strip theirs. ONE delivery path: the
                    // view module's custom-renderer manager forward
                    // (ViewModule::ProcessIncomingViewEvents cases 204/212/213/214/215 ->
                    // CustomRendererManager::RecvEvent), the console's loop-tail seat. The
                    // console routes the WHOLE channel onto the view queue; this build
                    // still bridges selectively, one record type at a time, as each
                    // consumer lands. The header size comes from the record's own head[2]
                    // ({payloadSize, type, headerSize}) rather than a hardcoded 12: the
                    // alignas(16) 212 record carries a 16-byte head, its siblings 12.
                    // ⭐ [map-world 2026-08-29] 223 (GuiEventRenderMainMap, the per-frame
                    // MAIN-MAP payload) joins the family -- the next record type whose
                    // consumers landed. MainMapRenderer (manager slot 2) and
                    // CrashNavIconRenderer (slot 3) both latch it in RecvEvent; without this
                    // bridge the whole map screen drew nothing and CrashNavIconRenderer's
                    // `mRenderMainMapEvent.mfZoomLevel != 0.0f` assert fired once per frame
                    // on a record that had never been delivered.
                    // ⭐⭐ [hud F4 2026-09-06] THE WHITELIST IS GONE -- THE CONSOLE HAS NO ID
                    // FILTER ON THIS CHANNEL. The list that stood here (204/212/213/214/215/223)
                    // was a bring-up stand-in that grew one record type at a time as each
                    // consumer landed, and it excluded every other record type. The console's
                    // arm is EventInterpreterModule::ProcessOutEvents @0x8285E1D0, case ')'
                    // (== 41), five instructions at @0x8285E64C:
                    //     lwz r11, 8(r22)   ; headerOffset = record[2]
                    //     mr  r3, r23       ; the view-state queue
                    //     lwz r6, 0(r22)    ; payload size = record[0]
                    //     add r4, r11, r22  ; payload = record + headerOffset (BYTES)
                    //     lwz r5, 4(r22)    ; inner event type = record[1]
                    //     bl  VariableEventQueue<65536,16>::AddEvent
                    // -- byte for byte the sibling of case '(' (40) and case '*' (42), and it
                    // runs for EVERY record on the channel. Two asserts guard it (":944" the
                    // queue, ":948" "Invalid raw event in EventInterpreterModule::
                    // ProcessOutEvents" on the payload pointer); both are kept below.
                    //
                    // WHAT THE FILTER COST, MEASURED (run scratch\bugtest\runs\hud_visibility\
                    // 20260906_104450, the `[hud-vis] ch41 ... bridged=0 DROPPED` witness):
                    //   type 258 GuiEventNetworkPlayerImage  x2 -- LicenseComponent::
                    //     SendPlayerPictureEvent / PhotoBoothComponent's texture posts; slot 0
                    //     NetworkPlayerImageRenderer never received a picture, so the licence
                    //     card kept its silhouette.
                    //   type 559 GuiEventSetHoveredEventIcon x2 -- posted while the MAIN MAP is
                    //     open; slot 3 CrashNavIconRenderer's mHoveredEventIcon never updated,
                    //     so the hovered event icon never changed state on the map.
                    // Both are HUD elements whose visibility is decided by a record this build
                    // threw away between the producer and the only consumer.
                    //
                    // [FLAG PC size] the console passes record[0] as the payload size; this
                    // build passes the RESIDUAL (liSize - headerOffset) instead, exactly as the
                    // old arm did. Reason: records in this tree are a mix -- StateInterface::
                    // OutputViewState builds its wrapper with the x64 sizeof(T), while the
                    // hand-rolled GuiEvent<N>(size, 12) helpers still carry the X360-era size
                    // literal in record[0] (e.g. PostCommand16<214> writes 1 for a 4-byte
                    // aligned payload). The residual is >= record[0] in every case and every
                    // consumer reads a typed prefix, so it is the safe superset; switch to
                    // record[0] when the hand-rolled helpers carry host sizes.
                    // DELETE-WHEN those helpers are host-sized.
                    else
                    {
                        const u32 luPayloadOffset =
                            reinterpret_cast<const u32*>(lpEvent)[2];
                        // ":948" -- the console asserts the payload pointer, then posts.
                        CGS_ASSERT(luPayloadOffset >= 12u,
                                   "Invalid raw event in EventInterpreterModule::ProcessOutEvents");
                        if (luPayloadOffset >= 12u &&
                            static_cast<s32>(luPayloadOffset) <= liSize)
                        {
                            const u8* lpu8Body =
                                reinterpret_cast<const u8*>(lpEvent) + luPayloadOffset;
                            mViewInputBuffer.GetViewStateQueue()
                                .CgsModule::VariableEventQueue<65536, 16>::AddEvent(
                                    reinterpret_cast<const CgsModule::Event*>(lpu8Body),
                                    static_cast<s32>(lpPlay->muEventType),
                                    liSize - static_cast<s32>(luPayloadOffset));
                        }
                    }
                    break;
                }

                case 155:  // menu-music request (0 = stop)
                    // The model channel is 155, while the typed sound event carried
                    // by it is GuiEventPlayMusicOnMenuStream (23). Publish the typed
                    // id so BridgeGuiToSound reaches MusicEffect::Notify.
                    CGS_ASSERT(mpOutputBuffer != 0, "mpOutputBuffer");
                    mpOutputBuffer->AddEvent(lpEvent, 23, liSize);
                    break;

                case 201:  // GUI audio trigger -> the module output event channel
                    CGS_ASSERT(mpOutputBuffer != 0, "mpOutputBuffer");
                    mpOutputBuffer->AddEvent(lpEvent, liId, liSize);
                    break;

                case 42:
                {
                    // ⭐⭐ CHANNEL 42 IS *NOT* A DEAD-END, AND THE [FLAG] THAT STOOD HERE
                    // ("consumers are module-internal follow-ons") THREW THE WHOLE CHANNEL
                    // AWAY. It is the console's OutputInternalState<T> channel -- the twin
                    // of channel 40's OutputGuiEvent<T>, differing only in the AddEvent
                    // selector (`li r5,0x2A` vs `li r5,0x28`; compare
                    // StateInterface::OutputInternalState<GuiEventShowHideHud> @0x82493C98
                    // with OutputGuiEvent<GuiEventShowHideHud> @0x82493988 -- byte for byte
                    // the same 16-byte {1,148,12,flag} record).
                    //
                    // The console consumes it in EventInterpreterModule::ProcessOutEvents
                    // @0x8285E1D0, case '*' (== 42) @0x8285E6C8:
                    //     lwz  r11, 8(r22)      ; headerOffset  (record[2] == 12)
                    //     addi r3, r18, 0x15C0  ; the module's OWN internal in-queue
                    //     lwz  r6, 0(r22)       ; payload size  (record[0])
                    //     add  r4, r11, r22     ; payload = record + headerOffset (BYTES)
                    //     lwz  r5, 4(r22)       ; event type    (record[1])
                    //     bl   VariableEventQueue<18432,16>::AddEvent
                    // i.e. it UNWRAPS the record and re-posts the inner event -- exactly as
                    // the sibling cases '(' (40) and ')' (41) unwrap theirs -- into a queue
                    // that EventInterpreterModule::Update @0x8285F670 splices into the
                    // inbound stream at the top of the NEXT frame:
                    //     EventQueue->Append(this + 0x15C0); (this + 0x15C0)->Clear();
                    //     ProcessInEvents(this, EventQueue);
                    // so an internal-state event is fanned to every registered observer
                    // one frame later, like any other GUI event.
                    //
                    // WHAT THE DROP COST, MEASURED: the in-game HUD stayed drawn ON TOP of
                    // the pause screen. InGame::OpenDriverDetails @0x824DA700 (and
                    // OpenMainMap / OpenEventMap / ShutDownHudComponents) post exactly this
                    // record -- GuiEventShowHideHud{0} -- and it is what
                    // FBurnMainHudState::UpdatePermenant's case 148 turns into
                    // SendStateEvent("PAUSE"), and what PausedHudState::Update's case 148
                    // (payload byte non-zero, from InGame::OnEnter's flag=1 twin) turns
                    // back into "UNPAUSE". Producers, consumers and the HUD flow's PAUSED
                    // slot were all already here; only this hop was missing.
                    //
                    // RouteEventToFlow is this build's ProcessInEvents fan-out, and this
                    // drain runs AFTER the flows have ticked and after the per-frame
                    // in-queue Clear -- so posting here lands the event for the next
                    // frame's flow Update, which is the console's one-frame defer exactly.
                    const u32 luHeaderSize = reinterpret_cast<const u32*>(lpEvent)[2];
                    const s32 liInnerId    =
                        static_cast<s32>(reinterpret_cast<const u32*>(lpEvent)[1]);
                    const s32 liPayload    =
                        static_cast<s32>(reinterpret_cast<const u32*>(lpEvent)[0]);
                    // :958 "Invalid raw event in EventInterpreterModule::ProcessOutEvents"
                    CGS_ASSERT(luHeaderSize >= 12u,
                               "Invalid raw event in EventInterpreterModule::ProcessOutEvents");
                    if (luHeaderSize >= 12u &&
                        static_cast<s32>(luHeaderSize) + liPayload <= liSize)
                    {
                        const u8* lpu8Body =
                            reinterpret_cast<const u8*>(lpEvent) + luHeaderSize;
                        // [FLAG PC witness] `[hud-vis] cmd` -- lane `hud`, bug-test wave
                        // 2026-09-06. NOT IN THE X360 BINARY. The HUD show/hide COMMAND
                        // (GuiEventShowHideHud, id 148) as it leaves the internal-state
                        // channel: InGame::OnEnter posts flag=1, OpenMainMap /
                        // OpenEventMap / OpenDriverDetails / ShutDownHudComponents post
                        // flag=0. This is the pause boundary in the log, and it is
                        // bounded (a handful per run). Opt-in behind BRN_HUD_VIS=1.
                        // DELETE-WHEN tools\tests\cases\hud_visibility.ps1 is retired.
                        if (liInnerId == 148 && liPayload >= 1 && HudVisWitnessEnabled() &&
                            CgsDev::Log::gpDebugPrint != 0)
                        {
                            *CgsDev::Log::gpDebugPrint
                                << "[hud-vis] cmd 148 flag="
                                << static_cast<s32>(lpu8Body[0]) << " ch=42\n";
                        }
                        RouteEventToFlow(
                            reinterpret_cast<const CgsModule::Event*>(lpu8Body),
                            liInnerId, liPayload);
                    }
                    break;
                }

                default:
                    // Resource requests (39) and the other state outputs are follow-ons.
                    break;
            }

            const CgsModule::Event* lpNext = 0;
            liId = lpOutBase->GetNextEvent(lpEvent, &lpNext, &liSize);
            lpEvent = lpNext;
        }
        lpOutBase->Clear();
    }

    // Selected no-argument PC entry for the GUI port. Original GuiModule::Update
    // (0x82527A58) receives its IO set from its frame caller.
    void GuiModule::Update()
    {
        // FLAG PC-platform leaf: the no-argument host entry owns its scripted
        // GameData pair. Loading callers already own the pair and use the typed
        // overload below. The original native Update receives its IO set from
        // its caller; this boundary does not recover that complete signature.
        BrnResource::GameDataIO::InputBuffer* lpGameDataInput =
            BrnGameMainFlowController::GetScriptedLoadGameDataInput();
        const BrnResource::GameDataIO::OutputBuffer* lpGameDataOutput =
            BrnGameMainFlowController::GetScriptedLoadGameDataOutput();
        lpGameDataInput->LockForWrite();
        lpGameDataOutput->LockForRead();
        Update(lpGameDataInput, lpGameDataOutput);
        lpGameDataOutput->UnlockForRead();
        lpGameDataInput->UnlockForWrite();
    }

    // The original call at ARTIST 82529AE4..82529B04 borrows the caller's
    // GameData pair. Keep its selected-port call together without an inner lock.
    void GuiModule::UpdateCalibrationScreen(
        BrnResource::GameDataIO::InputBuffer* lpGameDataInput,
        const BrnResource::GameDataIO::OutputBuffer* lpGameDataOutput)
    {
        if (lpGameDataInput != 0)
        {
            mColourCalibrationScreen.Update(lpGameDataInput, lpGameDataOutput,
                                            &mGuiOutQueue, mGuiConfig.mpTextureAllocator);
        }
    }

    // FLAG PC-platform leaf: selected GUI port with an explicitly borrowed
    // GameData pair, already locked by this frame's owner.
    void GuiModule::Update(BrnResource::GameDataIO::InputBuffer* lpGameDataInput,
                           const BrnResource::GameDataIO::OutputBuffer* lpGameDataOutput)
    {
        // ---- 1. inbound GUI events (144 -> RunFsm; 14/16/481 -> notifications;
        //          504/508/513 -> MovieManager; subscription fan-out to the flow) -------
        bool lbHasSaveImageEvent = false;
        CgsGui::ImageFileInfo lSaveImageInfo;
        const CgsModule::Event* lpLastInboundEvent =
            DispatchInboundGuiEvents(lbHasSaveImageEvent, lSaveImageInfo);

        // ---- 2. the per-frame cache event (64): the real Update posts the GuiCache
        //          pointer into the event queue each frame; the states read it as their
        //          "cache ready" feed (BootPreload/BootVideos/BootProfile all key on it).
        {
            // The per-frame "gameplay HUD data ready" trio the gameplay HUD components gate on
            // (BoostBarRenderer::Update @0x82451CA4 reads cache+0x4B54/0x4B56/0x4B58 as one
            // gate). The console publishes +0x4B54 from the frame's update set
            // (`(lUpdateSet & 8) != 0`, PS3 GuiModule::Update); the other two bytes' producers
            // are unrecovered. [FLAG PC stand-in] the update set is not threaded into this
            // PC-shaped Update and the two producers are unknown, so all three follow the
            // gameplay-HUD flag the cache already maintains -- the same "in gameplay" condition
            // the update-set bit models. DELETE-WHEN the two producers are recovered.
            // 2026-09-17: the update set IS threaded now (SetFrameUpdateSet); the first byte
            // follows the console's `(a2 & 8) != 0` (@0x82527A58 -> +0xFA294). The other two
            // ride along as before.
            mGuiCache.SetGameplayHudReady((muFrameUpdateSet & 8) != 0);
            GuiEventCache lCacheEvent;
            lCacheEvent.mpGuiCache = &mGuiCache;
            // ⭐ [licence-icon] the CUSTOM-RENDERER manager is the event's other console
            // consumer (its RecvEvent case 64 fans the GuiCache to every component --
            // NetworkPlayerImageRenderer latches mpGuiCache off it, the pointer its staged
            // Prepare's resource wait needs). The queue record below is excluded from
            // suffix dispatch; this direct handoff remains its sole manager delivery.
            mCustomRendererManager.RecvEvent(
                reinterpret_cast<const CgsModule::Event*>(&lCacheEvent), 64);

            // FLAG PC-platform leaf: ARTIST82529848 publishes cache64 before
            // GuiDebugComponent::Update reads it (82529C04). Publish the same
            // native record here so its read pass refreshes the PFX enumeration.
            // Original callbacks flush before base/model dispatch; this PC pump
            // dispatches/cache-updates earlier, so flush before those consumers.
            if (mpGuiEventInputBuffer != 0)
            {
                mpGuiEventInputBuffer->LockForWrite();
                CgsGui::CgsGuiModuleIO::InputBuffer::GuiEventInputQueue* lpGuiEvents =
                    mpGuiEventInputBuffer->GetGuiEvents();
                if (lpGuiEvents->AddEvent(reinterpret_cast<const CgsModule::Event*>(&lCacheEvent),
                                          64, static_cast<s32>(sizeof(lCacheEvent))))
                {
                    s32 liCacheEventSize = 0;
                    if (lpLastInboundEvent != 0)
                        lpGuiEvents->GetNextEvent(lpLastInboundEvent, &lpLastInboundEvent, &liCacheEventSize);
                    else
                        lpGuiEvents->GetFirstEvent(&lpLastInboundEvent, &liCacheEventSize);
                }
                mpGuiEventInputBuffer->UnlockForWrite();

                mDebugComponent.Update(mpGuiEventInputBuffer);
                mSatNavDebugComponent.Update(mpGuiEventInputBuffer);
                mGuiCacheDebugComponent.Update(mpGuiEventInputBuffer);
                // ARTIST 0x82529C40..44 copies the debug-selected mode each frame.
                mScreenFlow.SetStreamingMode(mDebugComponent.GetScreenFlowStreamingMode());
                // Fixed queue storage retains the cursor across Append. Skip
                // all prior input and cache64; retain initial image-save state.
                DispatchInboundGuiEvents(lbHasSaveImageEvent, lSaveImageInfo, lpLastInboundEvent);
            }

            // ⭐ [licence-icon] THE PREPARE PUMP (PC seat of the console's staged-Prepare
            // re-entry -- see the mbCustomRenderersPrepared note in the header). Advances the
            // manager's staged prepare each frame until the PlayerImage component reaches
            // E_PREPARESTAGE_DONE (its GuiCache wait needs the cache bind above first, which
            // is why the pump sits after it). One-shot log on completion.
            if (!mbCustomRenderersPrepared)
            {
                mbCustomRenderersPrepared =
                    mCustomRendererManager.Prepare(mGuiConfig.mpRendererAllocator, mGuiConfig.mpTextureAllocator);
                if (mbCustomRenderersPrepared)
                {
                    CgsDev::Log::WriteToLog("[custrend] manager prepare DONE (pump)\n");

                    // ⭐ [licence-icon] THE OFFLINE DEFAULT-IMAGE ARM (PC stand-in, FLAG).
                    // ASM-RECOVERED ANSWER to "what selects the default photo when none
                    // exists": the console has exactly ONE writer of the renderer's
                    // mbUseDefaultTexture -- GUI event 571, posted ONLY by
                    // TranslateNetworkEventsToGuiEvents @0x823E0900 case 73 (the network
                    // module's "no mugshot for this player" report; even an offline console
                    // boot runs that module). There is NO non-571 default path in the image.
                    // This build has no network module, so the report's one observable --
                    // one 571 into the manager once the component is prepared -- is
                    // synthesized here, at the same exactly-once seat as the prepare latch.
                    // A real transmitted image (event 258 with a texture) still clears the
                    // flag, exactly as on console. DELETE-WHEN the network module +
                    // TranslateNetworkEventsToGuiEvents land.
                    const u8 lacUseDefault[4] = { 0, 0, 0, 0 };   // CgsGui::GuiEvent<571>: payload unread
                    mCustomRendererManager.RecvEvent(
                        reinterpret_cast<const CgsModule::Event*>(lacUseDefault), 571);
                    CgsDev::Log::WriteToLog(
                        "[licence-icon] default player image armed (571 stand-in)\n");
                }
            }
        }

        // ---- 2b. boot-resources-ready feedback (event 567; bring-up FLAG) -------------
        // The console GUI cache posts 567 when the title's expected apt components have
        // initialised, which arms BootLegal's press-start path. The cache watcher isn't
        // reconstructed; post it once when the apt movie is live.
        if (!mbResourcesReadyFed && AptFlowMovieLive())
        {
            CgsModule::Event lReady;
            RouteEventToFlow(&lReady, 567, static_cast<s32>(sizeof(lReady)));
            mbResourcesReadyFed = true;
            CgsDev::Log::WriteToLog("[GuiModule] apt movie live -> fed resources-ready (567).\n");
        }

        // ---- 3. the FSM-bundle load service (the REAL GuiResourceModule) then the
        //          controller update ---------------------------------------------------
        DispatchGuiResourceModule();
        mModelInputBuffer.LockForWrite();
        mModelOutputBuffer.LockForRead();

        // ARTIST GuiCache::RecEvent consumes load/unload completion before the cache
        // update publishes its next double-buffered request batch.
        {
            const CgsGui::ModelIO::OutputBuffer::GuiNotificationQueue* lpNotifications =
                mModelOutputBuffer.GetLoadNotifications();
            const CgsModule::Event* lpNotification = 0;
            s32 liNotificationSize = 0;
            s32 liNotificationId =
                lpNotifications->GetFirstEvent(&lpNotification, &liNotificationSize);
            while (liNotificationId >= 0 && lpNotification != 0)
            {
                if (liNotificationId == 14 || liNotificationId == 16)
                {
                    mGuiCache.RecEvent(lpNotification, liNotificationId);

                    // ⭐ [map-world 2026-08-29] THE CUSTOM-RENDERER MANAGER IS THE OTHER
                    // CONSOLE CONSUMER OF THESE COMPLETIONS. On the X360 every view-side
                    // event reaches CustomRendererManager::RecvEvent through the view hop,
                    // and MainMapRenderer::RecvEvent @0x82449E98's case-14 arm is the ONLY
                    // way that component ever gets its two mask textures (203
                    // MainMapBackgroundMask / 202 PreRaceBackgroundMask) -- it has no
                    // resource-loading Prepare stage at all.
                    //
                    // MEASURED: the resource module publishes these completions on the MODEL
                    // OUTPUT notification queue read right here. They do NOT transit the
                    // module INPUT queue (the DispatchInboundGuiEvents tail forward) and they
                    // do NOT transit the view queue (the ViewModule case-14 forward) -- with
                    // both of those seats live, MainMapRenderer saw notifications for ids
                    // 17/18/19/1/196/125/33..131 and NEVER 202 or 203, so its guard held the
                    // whole map screen blank. This is the third and last PC seat of the one
                    // console hop; the three streams are disjoint, so nothing is delivered
                    // twice. Retire all three when BridgeFromInputToView gets its console
                    // caller (see the FLAG at the hook in CgsGuiViewModule.cpp).
                    mCustomRendererManager.RecvEvent(lpNotification, liNotificationId);
                }

                const CgsModule::Event* lpNext = 0;
                liNotificationId = lpNotifications->GetNextEvent(
                    lpNotification, &lpNext, &liNotificationSize);
                lpNotification = lpNext;
            }
        }
        mGuiCache.Update(&mModelInputBuffer);
        mFsmController.Update(&mModelInputBuffer, &mModelOutputBuffer);
        mModelOutputBuffer.UnlockForRead();
        mModelInputBuffer.UnlockForWrite();

        // X360 GuiModule::Update: EffectsArbitrator::ResourceUpdate(modelIn, modelOut)
        // @0x825177E8 -- the hook bundle (request 228) and colour-cube (229..) load
        // notifications, consumed before the tail clears the queue; a fresh bundle posts the
        // cube requests onto the model input.
        mModelInputBuffer.LockForWrite();
        mModelOutputBuffer.LockForRead();
        mEffectsArbitrator.ResourceUpdate(&mModelInputBuffer, &mModelOutputBuffer);
        mModelOutputBuffer.UnlockForRead();
        mModelInputBuffer.UnlockForWrite();

        // The real Update clears the notification queue at its tail (the per-frame IO
        // buffer lifecycle); the controller has consumed this frame's records.
        mModelOutputBuffer.LockForWrite();
        mModelOutputBuffer.GetLoadNotificationsNonConst()->Clear();
        mModelOutputBuffer.UnlockForWrite();

        // ---- 3b. the profile manager pump (X360 GuiModule::Update: the SLS Update at
        //          module+685896, the collision-world validate/invalidate swap
        //          @0x82519578, and the manager out-queue drained into the GUI out
        //          channel). The world-side pool free/restore around the swap is the
        //          un-reconstructed world collision pool -- FLAG'd absent (no world on
        //          the PC boot path); the manager's own state machine is driven fully. --
        // ARTIST8252A088/A094: system notifications and keyboard completion precede SLS.
        mSystemUserProfile.Update();
        mGuiKeyboard.Update();
        mProfileHost.GetProfileManager().Update();
        if (mProfileHost.GetProfileManager().PendingCollisionWorldInvalidate())
        {
            // FLAG PC-platform leaf: the console frees the world collision pool here.
            mProfileHost.GetProfileManager().SetCollisionWorldValid(false);
        }
        if (mProfileHost.GetProfileManager().PendingCollisionWorldValidate())
        {
            // FLAG PC-platform leaf: the console restores the world collision pool here.
            mProfileHost.GetProfileManager().SetCollisionWorldValid(true);
        }
        {
            CgsGui::GuiEventQueueSmall& lrProfileOut = mProfileHost.GetProfileManager().GetOutEventQueue();
            const CgsModule::Event* lpEvent = 0;
            s32 liSize = 0;
            s32 liId = lrProfileOut.GetFirstEvent(&lpEvent, &liSize);
            while (liId >= 0 && lpEvent != 0)
            {
                mGuiOutQueue.AddEvent(lpEvent, liId, liSize);
                // The console publishes these on the module bus (AddGuiOutEvents onto the
                // out buffer's gui-events channel), where they come back around as in
                // events and reach every registered observer through the interpreter's
                // subscription filter (that is how the autosave-icon flag, id 355, reaches
                // the always-available manager). Model the loop with the same filter.
                RouteEventToFlow(lpEvent, liId, liSize);
                const CgsModule::Event* lpNext = 0;
                liId = lrProfileOut.GetNextEvent(lpEvent, &lpNext, &liSize);
                lpEvent = lpNext;
            }
            lrProfileOut.Clear();
        }

        // ---- 3b'. THE PROFILE AUTOSAVE TAIL --------------------------------------------
        // ⭐⭐ [profile-save 2026-08-27] X360 GuiModule::Update @0x825295CC..0x825296A4,
        // store for store (r26 == the module, r30 == module+0x18D844, r31 == 0x18D840):
        //     if (*(module + 1628228) == 1) {                     // the autosave-pending latch
        //         r11 = 1;
        //         if (*(module + 1024648) != 0) r11 = 0;          // the cache's suppress byte
        //         else if (!(GuiCache::GetTime() > *(module + 1628224) + 60.0f)) r11 = 0;
        //         if ((v142 | r11) == 1) {                        // v142 == the FORCE flag
        //             if (v143 == 1) GuiModule::AutosaveProfile(v186);   // with an image record
        //             else if (*(module + 949156) == 1 && *(module + 686280)) {
        //                 ProfileManager::Autosave(&mProfileHost.GetProfileManager(), &host, 0, 0);
        //                 *(module + 1628228) = 0;
        //                 *(module + 1628224) = GuiCache::GetTime();
        //             }
        //         }
        //     }
        // flt_82004C6C == 60.0f. GUI358 now reaches AutosaveProfile with the complete
        // host-native ImageFileInfo record; absent that event, this block saves the profile
        // without image files.
        //
        // The two gates, and what each is on PC:
        //  * module+1024648 == GuiCache+19272 -- GuiCache::Construct @0x82505860 zeroes it
        //    (`*(a1 + 19272) = 0;`) and its ONLY writer is a GuiCache::RecEvent @0x8250DDF0 arm
        //    for an event id this build does not route, so it is 0 for the whole run: no
        //    suppression. Reproduced as the console's initial value rather than as a fake read.
        //  * module+686280 == mProfileHost.GetProfileManager().mSaveLoadSystem's autosave-enabled word, which is
        //    exactly ProfileManager::AutosaveIsEnabled() (the committed accessor over the same
        //    word) -- tested below.
        //  * module+949156 == mSystemUserProfile.miState (1 == E_USERSIGNINSTATE_SIGNEDIN).
        //    ⚠️ FLAG PC bring-up DEVIATION, deliberate and named: that state machine is driven
        //    by Xbox XNotify sign-in notifications (SystemUserProfile::Update ->
        //    UpdateUserSigninState -> XUserGetSigninState), none of which fires on PC, so
        //    miState stays 0 for the entire run and gating on it would make the console's own
        //    autosave permanently unreachable here. The rest of this build already answers the
        //    same "is a user signed in" question the other way (BrnGuiProfile.cpp's
        //    SaveLoadSystem_GetSignedInUserIndex PC leaf reports slot 0, and BF_PROFILE drives
        //    ProfileManager::Bootup through the same gate unguarded), so the gate is dropped
        //    HERE for the same reason and in the same place -- not silently widened.
        //    DELETE-WHEN a PC sign-in path drives mSystemUserProfile.miState.
        if (mbProfileAutosavePending)
        {
            // flt_82004C6C == 60.0f (the throttle window, X360 `fadds f0,f13,f0`).
            const f32 KF_AUTOSAVE_THROTTLE_SECONDS = 60.0f;
            const f32 lfNow = mGuiCache.GetTime();
            const bool lbThrottleElapsed = lfNow > (mfLastProfileAutosaveTime + KF_AUTOSAVE_THROTTLE_SECONDS);

            if (mbForceProfileAutosave || lbThrottleElapsed)
            {
                if (lbHasSaveImageEvent)
                {
                    AutosaveProfile(&lSaveImageInfo);
                }
                else if (mProfileHost.GetProfileManager().AutosaveIsEnabled())
                {
                    // The console's 4-arg call with count 0 / records NULL: save the profile
                    // image with no image files attached. The handler is the ProfileHost the
                    // module embeds; this build drives the manager directly, so it is the
                    // manager's own task-result handler that the boot states already use.
                    mProfileHost.GetProfileManager().Autosave(&mProfileHost, 0, 0);
                    mbProfileAutosavePending  = false;
                    mfLastProfileAutosaveTime = mGuiCache.GetTime();

                    if (CgsDev::Log::gpDebugPrint != 0)
                    {
                        *CgsDev::Log::gpDebugPrint
                            << "[profile-save] autosave requested (t=" << lfNow << ")\n";
                    }
                }
            }
        }
        // ⭐⭐ [drive-thru wave 2026-08-27] THE `else` ARM: THE 300-SECOND PERIODIC AUTOSAVE.
        // The block above is only the CONSUMER of the latch; this is the second PRODUCER, and it
        // was missing entirely -- so until now the game only ever autosaved on the event-driven
        // path (the id-356 GuiAutosaveRequestEvent arm at :1974). X360 @0x825296AC..0x82529700,
        // store for store (r26 == the module, r30 == module+0x18D844 == the pending latch):
        //     ori   r11, r11, 0x979C   ; 0xF979C == 1021852 == mGuiCache + 0x405C
        //     lwzx  r11, r26, r11      ; GuiCache::mpProfile
        //     cmpwi r11, 0 / beq       ; null-guarded
        //     ori   r10, r10, 0xA615   ; 42517
        //     lbzx  r11, r11, r10      ; Profile+42517, a BYTE
        //     cmplwi r11, 1 / bne      ; == 1 exactly, not "non-zero"
        //     bl    GuiCache::GetTime  ; module+0xF5740 == 1005376 == mGuiCache
        //     lfsx  f13, r26, 0x18D840 ; mfLastProfileAutosaveTime
        //     lfs   f0, flt_8201A258   ; 300.0f
        //     fadds f0, f13, f0 / fcmpu f1, f0 / ble
        //     li    r11, 1 / stb r11, 0(r30)   ; mbProfileAutosavePending = true
        // It ARMS the latch only; mbForceProfileAutosave is untouched, so the actual save
        // happens on the NEXT Update through the arm above -- whose own 60 s throttle is
        // trivially satisfied once 300 s have passed. That is why the two windows differ.
        //
        // ⚠️ THE GATE IS THE GOLD-CARS FLAG, AND THAT IS NOT A TYPO. Profile+42517 is the
        // 100%-completion flag (see the ⭐⭐ note on the pair in BrnProfile.h: the two flags were
        // named in DWARF declaration order and were swapped; CheckForSpecialCarUnlocks
        // @0x82396058 prints +42517 as "mProfile.AreGoldCarsUnlocked() : " and sets it from
        // ComputeCompletionPercentage() >= 100.0f). So the console's periodic autosave only runs
        // for a completed profile. Reproduced as-is -- it is a fixed byte compare against 1, not
        // an inference -- and flagged rather than "corrected" into a nicer-looking gate.
        // Consequence worth knowing when testing: on a fresh profile this arm never fires, and
        // the event-driven path above remains the only autosave. That matches the measured
        // behaviour (a fresh boot writes its container from the id-356 arm, not from here).
        else
        {
            const BrnProgression::Profile* lpCacheProfile = mGuiCache.GetProfile();
            if (lpCacheProfile != 0 && lpCacheProfile->GetGoldCarsUnlocked())
            {
                const f32 KF_AUTOSAVE_PERIOD_SECONDS = 300.0f;   // flt_8201A258
                if (mGuiCache.GetTime() > (mfLastProfileAutosaveTime + KF_AUTOSAVE_PERIOD_SECONDS))
                {
                    mbProfileAutosavePending = true;
                }
            }
        }
        mbForceProfileAutosave = false;   // the console's per-Update stack byte

        // Pump the always-available components manager (the top-left save-icon spinner + the
        // in-game EATrax/achievement/showtime overlays). The console GuiModule::Update
        // (@0x82527A58) advances its Prepare state machine each frame, and the interpreter's
        // UpdateObservers runs its Update against the queue the subscription filter filled
        // (RouteEventToFlow above delivers the ids its Prepare registered -- 64, 355, ...).
        // 0x8252A278. Prepare's BOOL RETURN IS A GATE, not a status byte to drop: the
        // console skips the whole overlay tick below until the prepare state machine reaches
        // DONE (`clrlwi r11, r3, 0x18 ; cmplwi 0 ; beq 0x8252A2CC`).
        const bool lbAlwaysAvailReady =
            mAlwaysAvailableComponentsManager.Prepare(&mGuiAccessPointers);
        mAlwaysAvailableComponentsManager.Update();
        if (lbAlwaysAvailReady)
        {
            // 0x8252A288..0x8252A2CC -- the EATrax chyron / achievement popup timeout tick.
            // Runs AFTER the queue pump above so a notification raised this frame is ticked
            // with this frame's clock; the console reaches the manager's own Update from
            // UpdateObservers instead, so Prepare -> overlays stays adjacent either way.
            mAlwaysAvailableComponentsManager.UpdateTimedComponents();
        }
        mAlwaysAvailInQueue.Clear();

        // ---- 3b'. the overlays director's controller (console: inlined
        //          GuiOverlaysDirector::SetController, just before the calibration screen).
        //          The cache word is tested for null first; the setter then stores it and
        //          asserts it.
        if (mGuiCache.GetPopupController() != 0)
            mOverlaysDirector.SetController(mGuiCache.GetPopupController());

        // ---- 3c. the colour-calibration screen (X360 GuiModule::Update @0x82529B04) -----
        // The console ticks it here after the profile/overlay pumps and before
        // the flow update. The selected PC port uses this caller's borrowed
        // GameData pair and mGuiOutQueue as its GUI output boundary.
        // [FLAG PC bring-up TEST HOOK -- OFF BY DEFAULT] BRN_POSTFX_CALIB_SCREEN_TEST=<n>: 300
        // updates before the n-th GuiModule::Update ensure the CN_COLOUR state's two APT resources
        // are loaded (the same GuiCache::EnsureResourcesAreLoaded call BrnBaseFlow::UpdateStreaming
        // makes on state entry, over the same {143 APT, 34 APT} list CrashNavColourCalibrate::
        // maResourcesToLoad carries -- 143 = BRNCRASHNAVCOLOURCALIBRATE, the bundle that holds the
        // calibration card raster the screen acquires from pool 9), on the n-th feed the screen a
        // 514 (show), and 600 updates later a 515 (hide). Stands in for the flow entering CN_COLOUR
        // + CrashNavColourCalibrate::SetupComponents / OnLeave, all reconstructed but UNREACHABLE on
        // this build (the FSM's only inbound edge to CN_COLOUR is "TO_COLOUR", posted by
        // CrashNavSettings, which has no TU). Exercises the whole chain: APT load -> screen acquire
        // -> 546 -> BridgeGuiToGame -> dispatch buffer -> the composite's calibration ramp override.
        // Without the resource load the acquire returns the null handle and the screen's own
        // "!= NULLResourceHandle" assert (cpp:147) fires -- measured. DELETE-WHEN CrashNavSettings lands.
        {
            static s32  siTestShowAt = -2;   // -2 = not read yet, -1 = knob absent
            static u32  suUpdates    = 0u;
            if (siTestShowAt == -2)
            {
                const char* lpcEnv = std::getenv("BRN_POSTFX_CALIB_SCREEN_TEST");
                siTestShowAt = (lpcEnv != 0 && lpcEnv[0] != '\0') ? std::atoi(lpcEnv) : -1;
                if (siTestShowAt >= 0)
                    CgsDev::Log::WriteToLog("[calib-screen] TEST HOOK armed: load APT at N-300, show at update N, hide at N+600\n");
            }
            ++suUpdates;
            if (siTestShowAt >= 300)
            {
                CgsModule::Event lEvent;
                if (suUpdates == static_cast<u32>(siTestShowAt) - 300u)
                {
                    static const CgsGui::sResourceTuple kaCalibrateResources[] =
                        { { 143u, CgsGui::E_GUI_RESOURCETYPE_APT }, { 34u, CgsGui::E_GUI_RESOURCETYPE_APT } };
                    mGuiCache.EnsureResourcesAreLoaded(kaCalibrateResources, 2u);
                    CgsDev::Log::WriteToLog("[calib-screen] TEST HOOK: CN_COLOUR APT resources {143,34} requested\n");
                }
                else if (suUpdates == static_cast<u32>(siTestShowAt))
                    mColourCalibrationScreen.RecvEvent(&lEvent, 514);
                else if (suUpdates == static_cast<u32>(siTestShowAt) + 600u)
                    mColourCalibrationScreen.RecvEvent(&lEvent, 515);
            }
        }
        UpdateCalibrationScreen(lpGameDataInput, lpGameDataOutput);
        // The console's next call after ColourCalibrationScreen::Update, unconditional: the
        // sat-nav tracker's route request (GUI out 494).
        mGuiTracker.Update(&mGuiOutQueue);

        // ---- 3c'. THE SCREEN-FILTER ARBITRATOR (X360 GuiModule::Update @0x82527A58) --------
        // EffectsArbitrator::EventUpdate @0x825125C0: the 495..500 hook events this frame's
        // bridge posted (start / stop / background / enumeration request -> the 501 reply on
        // the out queue), then UpdateHooks. The GuiCache hand-over is the console's event-64
        // case; this build posts 64 outside the module queue, so the cache is handed over by
        // name. The update set is the scheduler's own (SetFrameUpdateSet), as on the console.
        mEffectsArbitrator.SetGuiCache(&mGuiCache);
        if (mpGuiEventInputBuffer != 0)
        {
            const BrnUpdateSet leUpdateSet = muFrameUpdateSet;
            mpGuiEventInputBuffer->LockForRead();
            mEffectsArbitrator.EventUpdate(leUpdateSet, mpGuiEventInputBuffer, &mGuiOutQueue);
            mpGuiEventInputBuffer->UnlockForRead();
        }

        // ---- 3d. THE HUD-MESSAGE PUMP (gateui wave, round 2) --------------------------
        // X360 GuiModule::Update @0x82527A58, reproduced in the console's own order:
        //
        //   910  v153 = gm + 1005376;
        //   911  VariableEventQueue<32768,16>::AddEvent(v156, &v153, 64, 4);
        //          -- v156 == sub_8284F238(a5) == CgsGuiModuleIO::InputBuffer::GetGuiEvents(),
        //             i.e. the console PUSHES the GuiCache pointer (event 64) back into the
        //             very queue the analyzer is about to drain. That record is how
        //             HudMessageAnalyzer::mpGuiCache gets set: Construct @0x82509060 leaves
        //             it NULL and Update's case 64 latches it (_wB_12). Without this push
        //             the analyzer's first `mpGuiCache->...` is a null deref.
        //   912-929 the mpHudMessageController assert (BrnGuiCache.h:2418) + SetController.
        //   1015 LockForWrite(a8)                        -- the VIEW input buffer
        //   1022 v114 = ViewIO::InputBuffer::GetViewStateQueue(a8)
        //   1024 HudMessageAnalyzer::Update(gm + 660992, v115, v114)
        //   1031 UnlockForWrite(a8)
        //   1035 HudMessageDirector::Update(gm + 639264, v150)   -- v150 == the ModelIO
        //          input buffer, the same one GuiCache::Update is handed at line 1048.
        //
        // The console runs the analyzer between ColourCalibrationScreen::Update (1007) and
        // GuiOverlaysDirector::Update (1032), both inside the GUI input buffer's write lock;
        // the director follows the analyzer below, in the same lock.
        if (mpGuiEventInputBuffer != 0)
        {
            mpGuiEventInputBuffer->LockForWrite();
            {
                CgsGui::CgsGuiModuleIO::InputBuffer::GuiEventInputQueue* lpGuiEvents =
                    mpGuiEventInputBuffer->GetGuiEvents();

                // The native cache64 record is already in this queue, published
                // before the debug read/flush pass at the PC dispatch boundary.

                // console lines 911-928, and the SHAPE below is the CONSOLE'S OWN, not a
                // PC gate: it fires a NON-GATING `mpHudMessageController` assert
                // (BrnGuiCache.h:2418) and then wraps the SetController call in
                // `if ( *(a1 + 1021872) )` -- i.e. it too declines to publish a null
                // controller.
                //
                // ⭐ [gateui r4] THE ROUND-3 PARK IS RETIRED. Its DELETE-WHEN ("a
                // HudMessageController producer lands") is met twice over:
                // GameDataModule::PrepareHudMessages fills mHudMessageController, and
                // GuiModule::Construct now receives it as the console's `a2` and stores it
                // through GuiCache::SetHudMessageController. So this gate is expected to be
                // TRUE from the first frame and the assert below is a tripwire, not a
                // standing gap report.
                //
                // The assert fires ONCE rather than per frame: a per-pump assert storm is
                // what the 440-assert perf incident was, and the console reaches this line
                // once per frame too.
                if (!mGuiCache.HasHudMessageController())
                {
                    static bool sbNoControllerAssertFired = false;
                    if (!sbNoControllerAssertFired)
                    {
                        sbNoControllerAssertFired = true;
                        CgsDev::Assert::BeginAssert();
                        CgsDev::Assert::FireAssert(
                            "mpHudMessageController",
                            "..\\..\\..\\GameSource\\Gui/BrnGuiCache.h", 2418);
                        CgsDev::Assert::EndAssert();
                    }
                }
                else
                {
                    // ARTIST82529894..825298A8 lazily binds the debug component too.
                    if (!mHudMessageDebugComponent.ControllerIsValid())
                        mHudMessageDebugComponent.SetController(mGuiCache.GetHudMessageController());
                    mHudMessageDirector.SetController(mGuiCache.GetHudMessageController());
                }

                // console lines 1015-1031: the analyzer runs with the VIEW input buffer
                // write-locked across it (it appends view-state records through
                // mpViewOutputQueue).
                mViewInputBuffer.LockForWrite();
                mHudMessageAnalyzer.Update(lpGuiEvents, &mViewInputBuffer.GetViewStateQueue());
                mViewInputBuffer.UnlockForWrite();

                // [FLAG PC seam] the previous frame's flow-posted overlay traffic. On the
                // console it rode the GUI out-event loop-back into this queue at the top of
                // the update; here it joins the queue only now, after every other reader of
                // it has run, so the director is the one consumer that sees it (the flows got
                // the same records at the drain). See mOverlayLoopBackQueue.
                lpGuiEvents->Append(mOverlayLoopBackQueue);
                mOverlayLoopBackQueue.Clear();

                // console line 1032: the overlays director drains the queue.
                mOverlaysDirector.Update(mpGuiEventInputBuffer);
            }
            mpGuiEventInputBuffer->UnlockForWrite();
        }

        // console line 1035. The director drains its own published messages (event 154)
        // into the model module's input GUI-event queue.
        mHudMessageDirector.Update(&mModelInputBuffer);

        // The overlays director hands its 185/187/188 records to the model input buffer
        // (console: after the debug components, before GuiCache::Update). The walk below
        // fans them out to the overlay flow's states.
        mOverlaysDirector.BridgeOutEvents(&mModelInputBuffer);

        // FLAG PC bring-up (dispatch seam, NOT a behaviour change): on the console the
        // records the director just appended are consumed by the embedded
        // CgsGui::ModelModule's own update -- the EventInterpreterModule fans them out to
        // every registered observer, which is how event 154 reaches
        // BrnFBurnMainHudState::RecvEvent. This build models that fan-out with
        // RouteEventToFlow (see DispatchInboundGuiEvents), so the same walk is run here
        // over the model input buffer's queue. It is ALSO what keeps that queue bounded:
        // nothing else drains or clears it, and a GuiHudMessage is ~840 bytes against a
        // 32768-byte queue -- roughly 39 messages to an overflow assert.
        // DELETE-WHEN CgsGui::ModelModule is reconstructed and owns this dispatch.
        {
            mModelInputBuffer.LockForRead();
            const CgsGui::ModelIO::InputBuffer::GuiEventInputQueue* lpModelEvents =
                static_cast<const CgsGui::ModelIO::InputBuffer&>(mModelInputBuffer).GetEventQueue();
            const CgsModule::Event* lpEvent = 0;
            s32 liSize = 0;
            s32 liId = lpModelEvents->GetFirstEvent(&lpEvent, &liSize);
            while (liId >= 0 && lpEvent != 0)
            {
                RouteEventToFlow(lpEvent, liId, liSize);
                const CgsModule::Event* lpNext = 0;
                liId = lpModelEvents->GetNextEvent(lpEvent, &lpNext, &liSize);
                lpEvent = lpNext;
            }
            mModelInputBuffer.UnlockForRead();

            mModelInputBuffer.LockForWrite();
            mModelInputBuffer.GetEventQueueNonConst()->Clear();
            mModelInputBuffer.UnlockForWrite();
        }

        // ⭐ [stuntrace] the freeburn-challenge tracker's per-frame tick. X360
        // GuiModule::Update @0x82527A58 runs it in exactly this seat -- the two manager ticks
        // immediately before the base module update that drives the flows:
        //     BrnGui::BurnoutSkillsManager::Update(gm + 309032);
        //     BrnGui::FreeburnChallengeManager::Update(gm + 309584);
        //     CgsGui::GuiModule::Update(gm, ...);      // == the flow ticks below
        // The body is the AUTO_ROTATE page timer and is entirely behind
        // `meInternalState != E_INTERNAL_STATE_OFF`, so on an offline event it costs one
        // compare per frame. The skills-manager tick above it rotates the Burnout Skillz page
        // only in game mode 15.
        // The manager's event arms (544/574/576..579/581/583/584) are in
        // DispatchInboundGuiEvents; only free-burn challenge records reach them.
        mBurnoutSkillsManager.Update();
        mFreeburnChallengeManager.Update();

        // FLAG PC-platform leaf: this port fans the current frame's model/input
        // events out directly. ARTIST 82529848 appends cache 64 after the existing
        // GUI input; base Update 828602C8 then bridges that stream to the model.
        // Publish it here, after current inbound events (including profile 350),
        // before observer updates. A post-update handoff leaves stale 64 ahead of
        // the next frame's profile and violates Intro's SetProfilePointer contract.
        {
            GuiEventCache lCacheEvent;
            lCacheEvent.mpGuiCache = &mGuiCache;
            RouteEventToFlow(reinterpret_cast<const CgsModule::Event*>(&lCacheEvent), 64,
                             static_cast<s32>(sizeof(lCacheEvent)));
        }

        // ---- 4. the flow ticks (each current state's PreUpdate/Update/PostUpdate) -----
        // ARTIST82518570/80 registers HUD before Screen; UpdateObservers keeps
        // that order. The outgoing HUD hides its minimap before the new map
        // screen takes ownership and makes the shared icon bank visible.
        mHudFlow.Update();
        mScreenFlow.Update();
        mOverlayFlow.Update();
        // ...then RESET each observer's per-frame queue, exactly as the always-available
        // manager's queue is reset above. The console's EventInterpreterModule fills an
        // observer's in-queue from the subscription filter, runs UpdateObservers, and the
        // queue starts the next frame empty -- an observer sees an event once.
        //
        // These three were never cleared, so every routed event stayed in the queue and was
        // re-delivered on every subsequent frame, growing without bound until the 18 KB
        // VariableEventQueue overflowed (a boot reached "Event Type 64 has 223 entries" and
        // then asserted "Queue overflow. Write Pos=18431"). Past the overflow the walk reads
        // whatever is at the tail, which is how BrnGui::Intro started tripping its
        // unhandled-event assert on ids 0 and 256 -- ids nothing ever posts. It stayed
        // invisible while only a handful of events were routed per frame; the INTRO path
        // routes a profile record every sub-step and hit the wall in seconds.
        mScreenInQueue.Clear();
        mHudInQueue.Clear();
        mOverlayInQueue.Clear();

        // ---- 5. drain the flow's output (subscriptions / movie / view / game / audio) --
        mViewInputBuffer.LockForWrite();
        {
            // Drain the pending LOAD NOTIFICATIONS into the view queue FIRST (event 14 --
            // the GuiResourceModule output-buffer stand-in): the real ViewModule::
            // ProcessIncomingLoadNotification @0x8285BD30 performs every registration
            // (AddAptData / LoadStringTable / AddFont) when the queue dispatches, BEFORE
            // any play-movie event (18) posted below consumes the registered data --
            // the console's notification-before-play ordering.
            CgsGui::GuiEventLoadNotification lNotification;
            while (PopPendingAptLoadNotification(&lNotification))
            {
                mViewInputBuffer.GetViewStateQueue()
                    .CgsModule::VariableEventQueue<65536, 16>::AddEvent(
                        reinterpret_cast<const CgsModule::Event*>(&lNotification), 14,
                        static_cast<s32>(sizeof(lNotification)));
            }

            DrainFlowOutputQueue(E_GUIFLOW_SCREEN);
            DrainFlowOutputQueue(E_GUIFLOW_HUD);
            DrainFlowOutputQueue(E_GUIFLOW_OVERLAY);
            // The always-available manager is the fourth registered observer: its
            // StateInterface out-queue carries the type-34 registration records its
            // Prepare posts (the real 19-id table) plus anything its components emit.
            DrainFlowOutputQueue(E_GUIOBSERVER_ALWAYSAVAILABLE);
        }
        mViewInputBuffer.UnlockForWrite();

        // ---- 6. the MovieManager pump (receiver -> RecvEvent -> Update -> 510 back) ---
        {
            CgsModule::BaseEventReceiverQueue* lpRecv = mMovieManager.GetReceiverQueue();
            const CgsModule::Event* lpEvent = 0;
            s32 liSize = 0;
            s32 liId = lpRecv->GetFirstEvent(&lpEvent, &liSize);
            while (liId >= 0 && lpEvent != 0)
            {
                mMovieManager.RecvEvent(lpEvent, liId);
                const CgsModule::Event* lpNext = 0;
                liId = lpRecv->GetNextEvent(lpEvent, &lpNext, &liSize);
                lpEvent = lpNext;
            }
            lpRecv->Clear();
        }
        // (MovieManager::Update advances from the render pass now -- the console's
        // UpdateAndRenderMovieManager @0x82511240 -- so the two arms below read the state
        // that pass left.)
        //
        // X360 GuiModule::Update @0x82527A58, the two MovieManager arms it drives by hand,
        // in the console's order (`*(gm + 301604)` == the manager's meState, `gm + 304976`
        // == its playing VideoDefinition, dword_830082A8 == K_NULL_NAME == MakeHash("") == 0):
        //     if (state == 12 /*REPORTING_FINISHED*/) { def = playing; state = 13 /*IDLE*/;
        //         AddGuiOutEvent<GuiEventPlayMusicOnMenuStream>({K_NULL_NAME, 0, 0});  // stop the video's stream
        //         modelInput.GetEventQueue().AddEvent(&def, 510, 48); }              // "video finished"
        //     if (state == 5 /*REQUESTING_AUDIO*/)     { def = playing; state = 6 /*WAITING_FOR_AUDIO*/;
        //         AddGuiOutEvent<GuiEventPlayMusicOnMenuStream>({def.mSoundStreamName, 0,
        //                                                        def.mbDisableCustomSoundtracks}); }
        // The movie's sound is the sound module's MENU stream: MusicEffect resolves the
        // name (GetStreamFromVideoName), queues it on slot 12 and answers GuiOut 504, which
        // case 504 above hands to MovieManager::RecvEvent (6 -> 7 PLAYING). The typed
        // menu-stream event goes out on the module output buffer under its own id 23,
        // exactly as the flow-originated channel-155 records are re-posted below.
        if (mMovieManager.GetState() == MovieManager::E_MOVIEMANAGERSTATE_REPORTING_FINISHED)
        {
            const MovieManager::VideoDefinition lFinished = mMovieManager.GetPlayingMovieDefinition();
            mMovieManager.SetState(MovieManager::E_MOVIEMANAGERSTATE_IDLE);
            CgsGui::GuiEventPlayMusicOnMenuStream lStopStream(0u, false, false);
            mpOutputBuffer->AddEvent(reinterpret_cast<const CgsModule::Event*>(&lStopStream),
                                     23, static_cast<s32>(sizeof(lStopStream)));
            RouteEventToFlow(reinterpret_cast<const CgsModule::Event*>(&lFinished), 510,
                             static_cast<s32>(sizeof(lFinished)));
            CgsDev::Log::WriteToLog("[GuiModule] video finished -> menu stream cleared, fed 510 to the flow.\n");
        }
        if (mMovieManager.GetState() == MovieManager::E_MOVIEMANAGERSTATE_REQUESTING_AUDIO)
        {
            const MovieManager::VideoDefinition lPlaying = mMovieManager.GetPlayingMovieDefinition();
            mMovieManager.SetState(MovieManager::E_MOVIEMANAGERSTATE_WAITING_FOR_AUDIO);
            CgsGui::GuiEventPlayMusicOnMenuStream lVideoStream(
                lPlaying.mSoundStreamName, false, lPlaying.mbDisableCustomSoundtracks);
            mpOutputBuffer->AddEvent(reinterpret_cast<const CgsModule::Event*>(&lVideoStream),
                                     23, static_cast<s32>(sizeof(lVideoStream)));
            char lac[160];
            std::snprintf(lac, sizeof(lac),
                          "[GuiModule] video audio requested: menu stream 0x%08X (disableCustom=%d) -> WAITING_FOR_AUDIO\n",
                          static_cast<unsigned>(lPlaying.mSoundStreamName),
                          lPlaying.mbDisableCustomSoundtracks ? 1 : 0);
            CgsDev::Log::WriteToLog(lac);
        }

        // ---- 7. the view frame (the real per-frame owner) -----------------------------
        // Post the frame time step (view event 26) onto the view-state queue and run
        // CgsGui::ViewModule::Update -- which dispatches the view events (incl. the
        // bridged play-movie 18 + notifications 14), advances the view clock, and ticks
        // AptAux::Update (the component flush + the engine AptUpdateTarget frame pacer).
        // FLAG (PC time source): the console's step rides the module scheduler's clock;
        // the wall clock is the host stand-in.
        {
            const s64 liNowMs = static_cast<s64>(
                std::chrono::duration_cast<std::chrono::milliseconds>(
                    std::chrono::steady_clock::now().time_since_epoch()).count());
            f32 lfStepSeconds = 0.0f;
            if (miLastViewFrameMs >= 0)
                lfStepSeconds = static_cast<f32>(liNowMs - miLastViewFrameMs) * 0.001f;
            miLastViewFrameMs = liNowMs;

            // FLAG PC-platform leaf: the console scheduler supplies a bounded simulation
            // step, whereas this host stand-in measures wall time across synchronous file
            // and movie loads. Cap it to one 60 Hz simulation tick so the faithful Flapt
            // updater never receives an impossible multi-frame delta (which ARTIST asserts)
            // and Apt does not attempt wall-clock catch-up after a blocking host operation.
            const f32 kfMaxHostViewStep = 1.0f / 60.0f;
            if (lfStepSeconds > kfMaxHostViewStep)
                lfStepSeconds = kfMaxHostViewStep;

            mViewInputBuffer.LockForWrite();
            if (lfStepSeconds > 0.0f)
            {
                mViewInputBuffer.GetViewStateQueue()
                    .CgsModule::VariableEventQueue<65536, 16>::AddEvent(
                        reinterpret_cast<const CgsModule::Event*>(&lfStepSeconds), 26,
                        static_cast<s32>(sizeof(lfStepSeconds)));
            }
            mViewInputBuffer.UnlockForWrite();

            mViewModule.Update(0, 0, &mViewInputBuffer, &mViewOutputBuffer);
            BridgeFromViewToOutput();

            // ⭐ [boost-bar gate 2026-08-25] THE PER-FRAME COMPONENT PUMP. The console
            // drives CustomRendererManager::Update @0x82450908 once per frame from the
            // view chain (the call is virtual, so the exact console seat is not name-
            // recoverable; this PC seat follows the manager's Prepare-pump precedent
            // above). It must run AFTER the view dispatch just above (so this frame's
            // RecvEvent payloads -- the 206 boost info, 212 sat-nav render, 213/214
            // show-hides -- are already latched) and BEFORE GuiModule::Render (so
            // BoostBarRenderer::Update's visibility machine processes the allowed-to-
            // boost edge before RenderComponent's state-consistency asserts read it).
            // Without this call NO custom-render component ever ticked: the boost bar's
            // interpolators never re-keyed toward the live boost amount and its fade
            // machine froze at the Construct-seeded FULL -- the user-reported "asserts
            // when there is no boost" ("Visibility is full but we are not allowed to
            // boost", :1080) and "bar doesn't update with the correct values".
            // ARTIST BridgeFromViewToOutput 0x8285DE50..64 copies the custom
            // renderer's +12 event queue into GUI output; the next update feeds it
            // back to cache/flow observers. Preserve that feedback before Update
            // clears the queue, including the ticker's visibility edge (538).
            {
                const auto* lpFeedback = mCustomRendererManager.GetOutputEventQueue();
                const CgsModule::Event* lpEvent = nullptr;
                s32 liSize = 0;
                s32 liType = lpFeedback->GetFirstEvent(&lpEvent, &liSize);
                while (lpEvent)
                {
                    mGuiCache.RecEvent(lpEvent, liType);
                    RouteEventToFlow(lpEvent, liType, liSize);
                    const CgsModule::Event* lpNext = nullptr;
                    liType = lpFeedback->GetNextEvent(lpEvent, &lpNext, &liSize);
                    lpEvent = lpNext;
                }
            }
            mCustomRendererManager.Update();

            // [PC diagnostic] log the flow-movie mount state on CHANGE only (live /
            // composed flips) -- the mount/unmount/remount observability line.
            //
            // ⚠️⚠️ THIS USED TO REPORT LEVEL 1 ONLY, AND THAT IS A DIAGNOSTIC THAT LIES BY
            // OMISSION. Measured 2026-08-29 (results-screen wave): the offline results state
            // plays its movie at LEVEL 3, the bundle loaded, the runtime logged
            // "[AptRT] import-load: 'Results'" -- and then the log said nothing at all,
            // because the only mount instrument in the build was hard-wired to level 1. The
            // silence read exactly like "the movie never mounted" when it was in fact
            // "nothing was watching". Every level a state can address (0..8, the bound
            // ViewModule::ProcessIncomingAptEvent asserts) is now reported.
            {
                static s32 s_aiPrevLevelState[9] = { -1, -1, -1, -1, -1, -1, -1, -1, -1 };
                for (s32 liLevel = 0; liLevel < 9; ++liLevel)
                {
                    AptCIH* lpNode = AptFindAnimationAtLevel(liLevel);
                    s32 liState = 0;
                    if (lpNode != 0 && lpNode->GetCharacterInst() != 0)
                    {
                        liState |= 1;
                        AptCharacterInst* lpCI = lpNode->GetCharacterInst();
                        if (lpCI->GetTypeTag() == 5 || lpCI->GetTypeTag() == 9)
                        {
                            AptDisplayListState* lpState =
                                static_cast<AptCharacterSpriteInstBase*>(lpCI)->mDisplayList.AsState();
                            if (lpState != 0 && lpState->mpFirst != 0)
                                liState |= 2;
                        }
                    }
                    if (liState != s_aiPrevLevelState[liLevel])
                    {
                        char lacState[96];
                        std::snprintf(lacState, sizeof(lacState),
                                      "[AptRT] level-%d state -> live=%d composed=%d\n",
                                      liLevel, liState & 1, (liState >> 1) & 1);
                        CgsDev::Log::WriteToLog(lacState);
                        s_aiPrevLevelState[liLevel] = liState;
                    }
                }
            }
            {

                // [hud reveal gate 2026-08-25] DELETED: the "world-load stand-in" that fed a
                // fabricated engine-on 379 the frame the in-game HUD movie composed. It had
                // no console counterpart at all -- GuiModule::Update @0x828602C8 posts no GUI
                // event of its own -- and it was the direct cause of the user-reported "the
                // HUD is always visible, even in the Junkyard": it fired the ignition latch
                // ~3800 log lines before the player's engine actually started, so the HUD's
                // master "EventHud_Animator" ran 'transin' during car select.
                // The REAL producer is the console's own edge latch inside
                // BrnGameModule::BridgeWorldVehicleDataToGui @0x823E5930..0x823E59AC, landed
                // this wave in GameBridgeWorldToGui.cpp -- it reads the world's published
                // EActiveRaceCarEngineState and posts 379 only on a genuine off/on flip.
                // ⛔ DO NOT RE-ADD a stand-in here: with the world side live, a second
                // producer would double-post and re-open exactly this bug.
            }

            // The view consumed this frame's bridged events; reset the queue for the
            // next frame's bridge fill.
            mViewInputBuffer.LockForWrite();
            mViewInputBuffer.GetViewStateQueue()
                .CgsModule::VariableEventQueue<65536, 16>::Clear();
            mViewInputBuffer.UnlockForWrite();

            // The console GuiModule::Update @0x828602C8 tail: publish this frame's
            // AptCommunicator trigger records (SendAptEvent 21 apt triggers /
            // SendAptSoundEvent 22 sound triggers) into the view OUTPUT buffer's GUI
            // event queue, then clear the communicator queue.
            mViewOutputBuffer.LockForWrite();
            CgsGui::AptCommunicator::FlushTriggerEventsTo(mViewOutputBuffer.GetGuiEventQueue());
            mViewOutputBuffer.UnlockForWrite();
            // Deliver this frame's SOUND triggers (event 22 -- the AS SendAptSoundEvent
            // records: type[32] action[32] label[32] + layer) through the sound-logic
            // message route as typed GuiAudioTriggerEvent records.
            mViewOutputBuffer.LockForRead();
            {
                const CgsModule::VariableEventQueue<18432, 16>* lpTrigQueue =
                    static_cast<const CgsGui::ViewIO::OutputBuffer&>(mViewOutputBuffer).GetGuiEventQueue();
                const CgsModule::Event* lpTrig = 0;
                s32 liTrigSize = 0;
                s32 liTrigId = lpTrigQueue->GetFirstEvent(&lpTrig, &liTrigSize);
                while (liTrigId >= 0 && lpTrig != 0)
                {
                    if (liTrigId == 21)
                    {
                        // ARTIST GuiCache::RecEvent case 21 marks expected Apt
                        // components on ONLOAD, then the EventInterpreter fans the
                        // same trigger to any flow state observing event 21.
                        mGuiCache.RecEvent(lpTrig, liTrigId);
                        RouteEventToFlow(lpTrig, liTrigId, liTrigSize);
                    }
                    else if (liTrigId == 22 && liTrigSize >= 100)
                    {
                        // Convert Apt's {type[32], action[32], label[32], layer}
                        // record into the real GuiAudioTriggerEvent consumed by the
                        // presentation effect. The action table is the ARTIST
                        // OnEnter..OnRightSweep enum, with Apt underscores ignored.
                        const char* lpacT = reinterpret_cast<const char*>(lpTrig);
                        static const char* const KAPC_ACTIONS[14] = {
                            "OnEnter", "OnExit", "OnFocus", "OnLoseFocus", "OnAccept", "OnCancel",
                            "OnTick", "OnChange", "OnUp", "OnDown", "OnLeft", "OnLeftSweep",
                            "OnRight", "OnRightSweep"
                        };
                        s32 liAction = -1;
                        for (s32 liCandidate = 0; liCandidate < 14 && liAction < 0; ++liCandidate)
                        {
                            const char* lpSource = lpacT + 32;
                            const char* lpTarget = KAPC_ACTIONS[liCandidate];
                            bool lbSame = true;
                            while (lbSame && (*lpSource || *lpTarget))
                            {
                                if (*lpSource == '_') { ++lpSource; continue; }
                                const char lcSource = (*lpSource >= 'A' && *lpSource <= 'Z')
                                    ? static_cast<char>(*lpSource + 32) : *lpSource;
                                const char lcTarget = (*lpTarget >= 'A' && *lpTarget <= 'Z')
                                    ? static_cast<char>(*lpTarget + 32) : *lpTarget;
                                if (lcSource != lcTarget) { lbSame = false; break; }
                                ++lpSource;
                                ++lpTarget;
                            }
                            if (lbSame)
                                liAction = liCandidate;
                        }
                        if (liAction >= 0)
                        {
                            BrnGui::GuiAudioTriggerEvent lAudio;
                            lAudio.Construct(liAction, lpacT, lpacT + 64, "");
                            CGS_ASSERT(mpOutputBuffer != 0, "mpOutputBuffer");
                            mpOutputBuffer->AddEvent(
                                reinterpret_cast<const CgsModule::Event*>(&lAudio),
                                201, static_cast<s32>(sizeof(lAudio)));
                        }
                    }
                    const CgsModule::Event* lpTrigNext = 0;
                    liTrigId = lpTrigQueue->GetNextEvent(lpTrig, &lpTrigNext, &liTrigSize);
                    lpTrig = lpTrigNext;
                }
            }
            mViewOutputBuffer.UnlockForRead();
            // [PC] the downstream consumer (BridgeFromViewToOutput -> the module output
            // -> the sound-logic/flow observers) is un-homed, and the console's view
            // output buffer is re-created per frame off the IO stack; reset the queue
            // here as that per-frame recreate's stand-in so it cannot overflow either.
            mViewOutputBuffer.LockForWrite();
            mViewOutputBuffer.GetGuiEventQueue()
                ->CgsModule::VariableEventQueue<18432, 16>::Clear();
            mViewOutputBuffer.UnlockForWrite();
        }

        // [FLAG PC seam] keep this frame's overlay traffic from the module out-queue for the
        // director's next update (see mOverlayLoopBackQueue): the ids its dispatch handles.
        {
            const CgsModule::Event* lpEvent = 0;
            s32 liSize = 0;
            s32 liId = mGuiOutQueue.GetFirstEvent(&lpEvent, &liSize);
            while (liId >= 0 && lpEvent != 0)
            {
                switch (liId)
                {
                    case 184: case 186: case 188: case 189: case 190: case 279: case 322:
                        mOverlayLoopBackQueue.AddEvent(lpEvent, liId, liSize);
                        break;
                    default:
                        break;
                }
                const CgsModule::Event* lpNext = 0;
                liId = mGuiOutQueue.GetNextEvent(lpEvent, &lpNext, &liSize);
                lpEvent = lpNext;
            }
        }
    }

    // ⭐⭐⭐ THE GUI END-OF-FRAME NOTIFY, restored 2026-09-07. X360 @0x824F1008, verbatim:
    //     addis r3, r3, 5 ; addi r3, r3, -0x3D70 ; b BrnGui__CustomRendererManager__EndOfFrame
    // -- +327680-15728 == +311952 == mCustomRendererManager, tail-called. That in turn is
    //     addis r3, r3, 2 ; addi r3, r3, -0x49C0 ; b BrnGui__NetworkPlayerImageRenderer__SwapBuffers
    // -- +131072-18880 == +112192 == the embedded NetworkPlayerImageRenderer. So the whole
    // notify is one thing: SWAP THE PLAYER-IMAGE TRIPLE BUFFER.
    //
    // ⛔ IT WAS DECLARED NOWHERE, DEFINED NOWHERE AND CALLED BY NOTHING -- which links in
    // total silence. Both bodies below it were already correct and had NEVER EXECUTED. This
    // is the exact sibling of ParticleModule::EndOfFrame (c227a165, issue #17), named by the
    // same stale banner line in BrnGameModule::OnEndOfUpdateFrame.
    //
    // ⭐ WHAT ITS ABSENCE COSTS, from the console's own arithmetic (no eyeballing):
    //   NetworkPlayerImageRenderer::Construct @0x82445A50 seeds `*(this+736) = 1` and
    //   `*(this+740) = 2` -- miCurrentRenderTexture = 1, miCurrentCopyToTexture = 2 -- and
    //   SwapBuffers @0x82445E58 is the ONLY writer of either word in the whole image (both
    //   `(x+1) % 3`, via the 0x55555556 magic-multiply pair at 0x82445E9C/0x82445EA4).
    //   RecvEvent @0x82449CA0 case 258 copies an arriving picture into slot `v4[185]` ==
    //   miCurrentCopyToTexture and flags `maabRender*Texture[idx][thatSlot]`; GetRenderOutput
    //   @0x82445CC0 reads slot `miCurrentRenderTexture` and consults the flags at THAT slot.
    //   With the cursors frozen at 1 and 2, every picture is written to slot 2 and every read
    //   asks slot 1, whose flags no code path can ever set. ⇒ A RECEIVED PLAYER PICTURE CAN
    //   NEVER BE DISPLAYED. The two type-258 producers are single-player:
    //   LicenseComponent::SendPlayerPictureEvent and PhotoBoothComponent (see the bridge note
    //   in DispatchInboundGuiEvents) -- the licence card and the photo booth.
    //   Secondary: SwapBuffers is also the only per-frame writer of the Flapt special texture
    //   ("CustomComponentTexture.tif", FlaptFile::SetSpecialTexture @0x8246D750) and of
    //   FlaptRenderer::miSpecialTextureShaderProgram, so both stayed at whatever
    //   NetworkPlayerImageRenderer::Prepare @0x82451560 left on the frame it ran.
    //
    // ⚠️ NOT a fix for GitHub #9 (minimap blips) or #11 (in-game event UI): this chain is
    // three tail calls long and touches nothing but the player-image buffer set. Measured,
    // not assumed -- see the wave report.
    void GuiModule::EndOfFrame()
    {
        mCustomRendererManager.EndOfFrame();
    }

    // ARTIST 0x825146B8 plus its CgsGui::GuiModule::Render core @0x8285AF38.
    // That core is inlined here while the canonical base/model class hierarchy
    // remains unrecovered; this preserves its operations without a proxy base.
    // The scheduler supplies the real view/module inputs and renderer output.
    // Preparation gates the entire original pass; no renderer pointer is selected here.
    // Perfmon aliases: dword_82F2767C = miGuiModuleRender, dword_82F330B8 = miGuiRender.
    void GuiModule::Render(CgsGui::ViewIO::InputBuffer* lpViewInput,
                           CgsGui::CgsGuiModuleIO::InputBuffer* lpInput,
                           RendererIO::OutputBuffer* lpRenderOutput)
    {
        CgsDev::PerfMonCpu::StartMonitor(GuiPerfmons::miGuiModuleRender);
        CGS_ASSERT(lpInput != nullptr, "lpInput");
        CGS_ASSERT(lpRenderOutput != nullptr, "lpRenderOutput");
        if (mbPrepared && mDebugComponent.IsGuiRenderingEnabled())
        {
            CgsDev::PerfMonCpu::StartMonitor(GuiPerfmons::miGuiRender);
            // 0x823B6FE0/7060 carry these non-gating checks around the bridge.
            CGS_ASSERT(lpViewInput != nullptr, "lpInputBuffer");
            CGS_ASSERT(lpInput != nullptr, "lpOutputBuffer0");
            CgsModule::LockBuffersForIO(lpViewInput, lpInput);
            lpViewInput->SetImRenderers(lpInput->GetImRenderers());
            CGS_ASSERT(lpViewInput != nullptr, "lpInputBuffer");
            CGS_ASSERT(lpInput != nullptr, "lpOutputBuffer0");
            CgsModule::UnlockBuffersForIO(lpViewInput, lpInput);
            mViewModule.Render(lpViewInput);
            CgsDev::PerfMonCpu::StopMonitor(GuiPerfmons::miGuiRender);

            UpdateAndRenderMovieManager(lpViewInput);
            mEffectsArbitrator.GenerateEffectFrameEvents(lpRenderOutput);
        }
        CgsDev::PerfMonCpu::StopMonitor(GuiPerfmons::miGuiModuleRender);
    }

    // FLAG PC-platform leaf: retain the completed camera/input across a present
    // with no new simulation step. The next dispatch refreshes its renderer set
    // through the original bridge before Render consumes it.
    void GuiModule::CaptureRenderInputPC(const CgsGui::CgsGuiModuleIO::InputBuffer* lpInput)
    {
        CGS_ASSERT(lpInput != nullptr, "lpInput");
        CgsModule::LockBuffersForIO(&mCompletedRenderInputPC, lpInput);
        const CgsGui::ImRendererSet& lrRenderers = lpInput->GetImRenderers();
        CgsGraphics::Camera lCamera = lrRenderers.mCamera;
        mCompletedRenderInputPC.SetCamera(lCamera);
        mCompletedRenderInputPC.SetImRenderers(lrRenderers);
        CgsModule::UnlockBuffersForIO(&mCompletedRenderInputPC, lpInput);
        mbRenderInputCompletedPC = true;
    }

    CgsGui::CgsGuiModuleIO::InputBuffer* GuiModule::GetCompletedRenderInputPC()
    {
        return mbRenderInputCompletedPC ? &mCompletedRenderInputPC : nullptr;
    }

    // BridgeFromViewToOutput @0x8285DE10 -- an export hole, read with tools/re/ppcdis.py:
    //     Append<18432,16>(this + 111644, ViewIO::OutputBuffer::GetGuiEventQueue(viewOut));
    //     OutputBuffer::AddGuiOutEvents(moduleOut, *(view + 57352) + 12);
    //     OutputBuffer::AddGuiOutEvents(moduleOut, view + 56768);   // ViewModule::mOutputEventQueue
    // (called from CgsGui::GuiModule::Update @0x82860548, right after the view Update).
    // The first two carry the view OUTPUT buffer's queue -- the Apt trigger records 21/22
    // that Update above already drains by hand. The third had NO PC seat: the view module's
    // OWN out queue, where ProcessIncomingAptEvent @0x8285EAE8 posts 33
    // GuiEventLoadingScreenState {visible} for PlayAptLoadingMovie 19 / StopAptLoadingMovie
    // 20. The sound logic module drains the module out queue (BridgeGuiToSound @0x823C0A58)
    // and turns 33 into bit 1 of its dispatch flags word -- half of MusicEffect::
    // UpdateParams' stream-pause gate -- so on PC that gate could never hold while the
    // loading screen was up, and HUDEffect::Notify's loading-screen test never tripped.
    void GuiModule::BridgeFromViewToOutput()
    {
        CGS_ASSERT(mpOutputBuffer != 0, "mpOutputBuffer");
        mpOutputBuffer->Append(mViewModule.GetOutputEventQueue());
    }

    // @ 0x82511240 -- pump the movie manager (the movie pass of the GUI render).
    // ARTIST 0x82511240: movie update precedes the view-input read bracket.
    // MoviePlayer::Render records into the same supplied Im2d command buffer.
    void GuiModule::UpdateAndRenderMovieManager(CgsGui::ViewIO::InputBuffer* lpViewInput)
    {
        mMovieManager.Update();
        lpViewInput->LockForRead();
        mMovieManager.Render(lpViewInput->GetImRenderers().mpIm2dRenderBuffer);
        lpViewInput->UnlockForRead();
    }

}

// ---- GetAlwaysAvailableComponentsManager (free accessor) ----------------------------
// Header-declared in BrnGuiAlwaysAvailableComponentsManager.h; homed here because this TU
// owns the GuiModule layout.
namespace BrnGui
{
    AlwaysAvailableComponentsManager* GetAlwaysAvailableComponentsManager(GuiModule* lpGuiModule)
    {
        return lpGuiModule->GetAlwaysAvailableComponentsManager();
    }

}
