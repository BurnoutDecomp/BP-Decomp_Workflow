#ifndef BRN_GUI_MODULE_H
#define BRN_GUI_MODULE_H

#include "GameShared/GameClasses/Gui/CgsGuiModule.h" // actual shared base and Model owner (CP15/16)
#include "GameShared/GameClasses/Gui/CgsImageFileInfo.h" // GUI358 autosave image record
#include "GameShared/GameClasses/Gui/View/CgsGuiViewModuleIO.h"  // CgsGui::ViewIO Input/OutputBuffer (the per-frame bridge pair)
#include "GameSource/Gui/BrnGuiMovieManager.h"                          // BrnGui::MovieManager (embedded)
#include "GameSource/Replays/Serialisers/BrnReplayGuiModuleSerialiser.h"
#include "GameShared/GameClasses/Gui/CgsGuiShared.h"
#include "GameShared/GameClasses/Module/CgsBaseEventReceiverQueue.h"
#include "GameSource/Gui/BrnGuiColourCalibrationScreen.h"               // BrnGui::ColourCalibrationScreen (embedded; DWARF BrnGuiModule.h:506)
#include "GameSource/Gui/PFX/BrnGuiEffectsArbitrator.h"
#include "SharedClasses/BrnSharedConstants.h"                 // BrnUpdateSet (the frame update set)                  // BrnGui::EffectsArbitrator (embedded; X360 gm+1546880)
#include "GameSource/Gui/BrnGuiViewModule.h"                             // BrnGui::ViewModule (embedded)
#include "GameShared/GameClasses/Gui/CgsGuiModuleIO.h"                  // CgsGui::CgsGuiModuleIO::InputBuffer (the inbound GUI event buffer)
#include "GameShared/GameClasses/Gui/Model/CgsModelModuleIO.h"          // CgsGui::ModelIO Input/OutputBuffer (the FSM controller's IO pair)
#include "GameShared/GameClasses/Gui/Model/Resources/CgsGuiResourceModule.h" // CgsGui::GuiResourceModule (+ IO buffers) -- the REAL FSM/resource loader
#include "GameShared/GameClasses/Module/CgsVariableEventQueue.h"        // CgsModule::VariableEventQueue
#include "GameShared/GameClasses/System/Resource/CgsResourcePool.h"     // CgsResource::Pool (holds the loaded FSM bundle)
#include "GameShared/GameClasses/Memory/CgsHeapMalloc.h"               // CgsMemory::HeapMalloc (the FSM Lua VM heap)
#include "GameShared/GameClasses/Memory/CgsLinearMalloc.h"             // CgsMemory::LinearMalloc (the HUD state pool)
#include "GameSource/Gui/BrnGuiFsmController.h"                         // BrnGui::GuiFsmController (the flow FSM controller)
#include "GameSource/Gui/Flow/HUD/BrnHudFlow.h"                         // BrnGui::BrnHudFlow (the 14-state HUD flow)
#include "GameSource/Gui/Flow/Overlay/BrnOverlayFlow.h"                 // BrnGui::BrnOverlayFlow (the 15-popup-state overlay flow)
#include "GameSource/Gui/Flow/Screen/BrnScreenFlow.h"                   // BrnGui::BrnScreenFlow (the 61-state front-end SCREEN flow)
#include "GameSource/Gui/BrnGuiKeyboard.h"
#include "GameSource/Gui/BrnGuiKeyboardHost.h"
#include "GameSource/Gui/BrnGuiProfileHost.h"
#include "GameSource/Gui/BrnGuiDebugComponent.h"
#include "GameSource/Gui/BrnGuiHudMessagesDebugComponent.h"
#include "GameSource/Gui/BrnGuiSatNavDebugComponent.h"
#include "GameSource/Gui/BrnGuiGuiCacheDebugComponent.h"
#include "GameSource/Gui/BrnGuiProfile.h"                               // BrnGui::ProfileManager (module-owned; REAL)
#include "GameShared/GameClasses/Gui/CgsGuideIntegration.h"             // CgsGui::SystemUserProfile (module-owned; X360 +949152)
#include "GameSource/Gui/BrnGuiCache.h"                                 // BrnGui::GuiCache (the flow states' cache)
#include "GameSource/Gui/SatNav/BrnMapIconManager.h"   // [H3b] BrnGui::MapIconManager (by-value member)
#include "GameSource/Gui/SatNav/BrnGuiTracker.h"       // BrnGui::GuiTracker (module-owned; X360 +1131872)
#include "GameSource/Gui/BrnGuiFreeburnChallengeManager.h" // BrnGui::FreeburnChallengeManager (module-owned; X360 +309584)
#include "GameSource/Gui/BrnGuiBurnoutSkillsManager.h"         // BrnGui::BurnoutSkillsManager (module-owned; GuiCache::mpSkillsManager)
#include "GameSource/Gui/BrnGuiHudMessageDirector.h"                    // BrnGui::HudMessageDirector (module-owned; X360 +639264)
#include "GameSource/Gui/BrnGuiHudMessageAnalyzer.h"                    // BrnGui::HudMessageAnalyzer (module-owned; X360 +660992)
#include "GameSource/Gui/BrnGuiOverlaysDirector.h"                      // BrnGui::GuiOverlaysDirector (module-owned; console +0xA1B10)
#include "GameSource/Gui/BrnGuiWorldDataController.h"                   // BrnGui::WorldDataController (module-owned; X360 +307836)
#include "GameSource/Gui/BrnGuiAlwaysAvailableComponentsManager.h"     // module-owned permanent FLApt components
#include "GameSource/Gui/BrnCustomRendererManager.h"                    // BrnGui::CustomRendererManager (module-owned; X360 +311952)

// BrnGui::GuiModule -- the GUI module (a dispatched CgsModule, like BrnRendererModule). The X360 module
// (Construct 0x82518028 / Prepare 0x82518D68 / Update 0x82527A58 / Render 0x825146B8) builds the entire
// GUI subsystem (model + view + the HUD/Screen flows) and EMBEDS the MovieManager (X360 +301600), driving
// it each frame via UpdateAndRenderMovieManager (0x82511240).
//
// THE BOOT/MENU FLOW IS THE REAL CONTROLLER CHAIN (2026-07-10): the module owns the real
// BrnGui::GuiFsmController + BrnHudFlow (the 14-state pool BF_PRELOAD..PRE_FLY_BY in ONE
// CgsGui::StateMachine), sequenced exactly as the X360 GuiModule::Update does --
//   * GuiEventRunFsm posts (event 144, from the game module's BridgeGameToGui) ->
//     GuiFsmController::RunFsm;
//   * the controller's load machine posts GuiEventLoadRequest records into the ModelIO
//     input buffer; the FSM LuaCode bundle loads land as GuiEventLoadNotification (14)
//     records on the ModelIO output buffer; PrepareLua enters the script's state;
//   * the flow's states register their observed events (records 34/35 on the state
//     interface output queue); the module fans matching inbound GUI events into the
//     flow's in-queue (the EventInterpreterModule observer-subscription dispatch);
//   * each boot state posts command 70 (channel 40) at phase end; the game module's
//     BridgeGuiToGame consumes it and the game main flow requests the next FSM stage.
// The [PC IO] leaf that remains module-side is the synchronous FSM-bundle load standing
// in for the GuiResourceModule module dispatch (ServiceFsmBundleRequests).
namespace EA { namespace GameTalk { class GameTalkMessage; } }

namespace BrnGui
{
    class GuiModule : public CgsGui::GuiModule
    {
    public:
        // [gateui r4] X360 `BrnGui::GuiModule::Construct` @0x82518028 is NOT the module
        // virtual -- it is a direct, argument-taking call the OWNER makes
        // (BrnGameModule::Construct), and the pure-virtual `Construct()` slot stays
        // `CgsModule::ModuleSingleBuffered::Construct`, exactly as `CgsGui::GuiModule::
        // Construct` @0x82856FA8 (which likewise takes `lpViewModule`) chains into it.
        // Round 4 restores the console's first argument: `a2` == the owner's
        // `&mGameDataModule.mHudMessageController` (X360 gm+0x65A1D0), asserted
        // "lpHudMessageController" BrnGuiModule.cpp:229 and then stored into the cache at
        // line 368 (`*(gm + 1021872) = a2`, the inlined GuiCache::SetHudMessageController
        // with assert "lpController" BrnGuiCache.h:2405). Without it
        // GuiCache::mpHudMessageController had ZERO writers and every HUD message died at
        // HudMessageDirector::FilterAndSendOffMessage's `mpController` assert.
        //
        // `lbHighDef` is the console's LAST argument (a6): the video-mode HD bool the renderer
        // handed the game module. GuiModule::Construct stores it into the cache
        // (`*(gm + 1024649) = a6` == GuiCache +0x4B49, the byte every HD/SD layout choice in
        // the GUI reads), picks the sat-nav view rect with it (@0x82518A2C) and constructs
        // the GUI resource module with it (the GuiApt\ vs GuiAptSD\ bundle path). Until
        // 2026-09-07 it was not passed and the byte was never written -- issue #11.
        //
        // The console's third argument is `lpPopupController` (the owner's
        // &mGameDataModule.mPopupController, asserted non-null), stored into the
        // cache through the inlined GuiCache::SetPopupController right after the director
        // store; GuiModule::Update hands it on to GuiOverlaysDirector::SetController. The
        // aspect-ratio argument is not reconstructed (it is sourced inside the body).
        void Construct(const BrnResource::HudMessageController* lpHudMessageController,
                       const BrnResource::PopupController* lpPopupController,
                       bool lbHighDef);

        // DecFIGS BrnGuiModule.h:660; ARTIST823AAC3C inlines the false store
        // at CompleteLoading::OnLeave, matching the constructor/validator byte.
        void SetMovieBootMode(bool lbBootMovieMode) { mbBootMovieMode = lbBootMovieMode; }

        // DecFIGS names, with ARTIST82518D68's actual stage order. ARTIST
        // moved the world-data stage after WF resources.
        enum GuiPrepareStage
        {
            E_PREPARE_START = 0,
            E_PREPARE_MEMORY = 1,
            E_PREPARE_PARENT = 2,
            E_PREPARE_HUD = 3,
            E_PREPARE_SCREEN = 4,
            E_PREPARE_OVERLAY = 5,
            E_PREPARE_FSM_CONTROLLER = 6,
            E_PREPARE_CUSTOMRENDERER_PREPARE = 7,
            E_PREPARE_MOVIE_MANAGER = 8,
            E_PREPARE_COLOUR_CALIBRATION_SCREEN = 9,
            E_PREPARE_GUI_DEBUG_COMPONENT = 10,
            E_PREPARE_PROFILE = 11,
            E_PREPARE_SYSTEM_NOTIFICATIONS = 12,
            E_PREPARE_WF_RESOURCES = 13,
            E_PREPARE_WORLD_DATA_CONTROLLER = 14,
            E_PREPARE_DONE = 15,
        };
        enum GuiReleaseStage
        {
            E_RELEASE_START = 0,
            E_RELEASE_MEMORY = 1,
            E_RELEASE_PARENT = 2,
            E_RELEASE_HUD = 3,
            E_RELEASE_SCREEN = 4,
            E_RELEASE_OVERLAY = 5,
            E_RELEASE_FSM_CONTROLLER = 6,
            E_RELEASE_CUSTOMRENDERER_DESTRUCT = 7,
            E_RELEASE_CUSTOMRENDERER_RELEASE = 8,
            E_RELEASE_MOVIE_MANAGER = 9,
            E_RELEASE_COLOUR_CALIBRATION_SCREEN = 10,
            E_RELEASE_WORLD_DATA_CONTROLLER = 11,
            E_RELEASE_GUI_DEBUG_COMPONENT = 12,
            E_RELEASE_PROFILE = 13,
            E_RELEASE_SYSTEM_NOTIFICATIONS = 14,
            E_RELEASE_DONE = 15,
        };

        bool Prepare() override;
        // ARTIST825194B8; original native vtable+0x5C. The selected host
        // keeps PrepareWorldData2 until the outer phase is migrated as a whole.
        virtual bool Prepare2(BrnResource::GameDataIO::InputBuffer* lpGameDataInput);
        bool Release() override;
        void Destruct() override;
        void Update() override;

        // ARTIST 0x8251A3D0; native owner of GUI pre-world validation, profile-upgrade requests,
        // movie-data acquire publication, and the shared GUI model's PreWorld update.
        void PreWorldUpdate(CgsModule::IOBufferStack* lpInputBufferStack,
                            CgsModule::IOBufferStack* lpOutputBufferStack,
                            CgsGui::CgsGuiModuleIO::OutputBuffer* lpGuiOutput,
                            CgsGui::ModelIO::OutputBuffer* lpModelOutputBuffer) override;

        // FLAG PC-platform leaf: borrow this caller's already write/read-locked
        // GameData pair. This is the selected GUI port's ownership boundary,
        // not the complete original native GuiModule::Update signature.
        void Update(BrnResource::GameDataIO::InputBuffer* lpGameDataInput,
                    const BrnResource::GameDataIO::OutputBuffer* lpGameDataOutput);

        // The frame's simulation update set. X360 GuiModule::Update @0x82527A58 receives it as
        // its second argument from the module scheduler (`a2`) and reads ONE bit of it: bit 8
        // (0x08, set while the main flow FSM is in an in-game state -- see
        // BrnGameModule::ConstructUpdateSetFromFsm) is stored at +0xFA294 (== the cache's
        // 'gameplay HUD ready' byte) and handed to EffectsArbitrator::EventUpdate, whose
        // UpdateHooks tail runs only while it is set. The PC scheduler ticks Update() with no
        // arguments, so BrnGameModule::GameMain latches the set here first. (Until 2026-09-17
        // both readers were fed a stand-in, GuiCache::IsGameplayHudActive, which the console
        // DROPS across every crash bar -- so once the crash-bar event reached the cache the
        // screen-filter hooks stopped advancing during a crash and only ran for the frames
        // between the HUD's return and the hook's stop.)
        void SetFrameUpdateSet(BrnUpdateSet luUpdateSet) { muFrameUpdateSet = luUpdateSet; }

        // ⭐ 2026-08-16 (boot audit F-P1-1). Prepare no longer runs from BrnGameModule::Construct;
        // it runs from loading stage 2, with the loading screen already up, exactly as the
        // console's LoadingScriptedState::LoadGUIModule @0x823EF310 pumps it (vtable+0x58 per
        // frame). This latch is what everything that used to be able to assume "the GUI module
        // was prepared before the frame loop started" now tests -- above all the game module's
        // per-frame Update() drive, which on the console does not exist until the module
        // scheduler has the module prepared.
        bool IsPrepared() const { return mbPrepared; }

        // ARTIST 0x825146B8: forward the supplied complete renderer set, render
        // the view, update/record movies, then post renderer effect-frame events.
        virtual void Render(CgsGui::ViewIO::InputBuffer* lpViewInput,
                    CgsGui::CgsGuiModuleIO::InputBuffer* lpInput,
                    RendererIO::OutputBuffer* lpRenderOutput);
        CgsGui::ViewIO::InputBuffer* GetViewInputBuffer() { return &mViewInputBuffer; }
        // FLAG PC-platform leaf: keep the completed input after its sub-step IO
        // stack is reclaimed. The owner runs BridgeRendererToGui on the selected
        // input every dispatch, so all five current renderer pointers are refreshed.
        void CaptureRenderInputPC(const CgsGui::CgsGuiModuleIO::InputBuffer* lpInput);
        CgsGui::CgsGuiModuleIO::InputBuffer* GetCompletedRenderInputPC();

        // ⭐⭐ THE GUI END-OF-FRAME NOTIFY. X360 BrnGui::GuiModule::EndOfFrame @0x824F1008 is
        // three instructions -- `addis r3,r3,5 ; addi r3,r3,-0x3D70 ; b CustomRendererManager::
        // EndOfFrame` -- a tail call into mCustomRendererManager (+311952), which is itself a
        // tail call into NetworkPlayerImageRenderer::SwapBuffers (+112192). Its ONLY console
        // caller is BrnGameModule::OnEndOfUpdateFrame @0x823DBBA0, between the dispatch-buffer
        // swap and BrnRendererModule::EndOfFrame.
        //
        // It was DECLARED NOWHERE, DEFINED NOWHERE and CALLED BY NOTHING in this tree until
        // 2026-09-07 -- the sibling of the ParticleModule::EndOfFrame hole fixed in c227a165,
        // and named by the same stale "[gated] the metrics/particle/GUI end-of-frame notifies
        // land with their subsystems" comment. See the body for what its absence cost.
        void EndOfFrame();                                                    // 0x824F1008

        // @ 0x82511240 -- MovieManager::Update + the movie frame draw (the movie pass).
        void UpdateAndRenderMovieManager(CgsGui::ViewIO::InputBuffer* lpViewInput);
        // BridgeFromViewToOutput @0x8285DE10 -- after the view module's Update, append its
        // own out-event queue (33 GuiEventLoadingScreenState lives there) onto the module out.
        void BridgeFromViewToOutput();

        static void FlaptSoundTriggerCallback(void* lpUserData,
                                              const char* lpcComponentName,
                                              const char* lpcSwfName,
                                              const char* lpcActionName,
                                              const char* lpcLabel);

        // DecFIGS BrnGuiModule.h:667; ARTIST owns this bundle by value.
        CgsGui::GuiAccessPointers* GetGuiAccessPointers() { return &mGuiAccessPointers; }
        MovieManager* GetMovieManager() { return &mMovieManager; }
        ViewModule* GetViewModule() { return &mViewModule; }
        AlwaysAvailableComponentsManager* GetAlwaysAvailableComponentsManager()
        {
            return &mAlwaysAvailableComponentsManager;
        }

        // (RequestAptMovieLoad RETIRED, slice 2 of the runtime retirement: the engine's
        // AptLoader owns movie data acquisition -- registered-data first, bundle-IO
        // fallback -- through the real AptLoaderStartAsyncLoad platform hook.)

        // Hand this sub-step's GUI module INPUT buffer (filled by BrnGameModule's
        // BridgeControllerToGui + BridgeGameToGui) to the update drive; Update dispatches
        // its inbound events (144 -> RunFsm, 14/16/481 -> the model notifications,
        // 504/508/513 -> the MovieManager) and fans the rest into the HUD flow's in-queue
        // per the observer subscriptions. FLAG (bridge stand-in): on the console the
        // buffer arrives through the module scheduler's IO set.
        void SetGuiEventInputBuffer(CgsGui::CgsGuiModuleIO::InputBuffer* lpBuffer)
        {
            mpGuiEventInputBuffer = lpBuffer;
        }

        // The module's GUI OUT event queue for this frame (the flow states' channel-40
        // command records and the module's own out events). BrnGameModule::BridgeGuiToGame
        // drains it after the module update -- the PC stand-in for the console GUI module
        // OUTPUT buffer's out-event queue the bridge reads. Cleared by the bridge.
        CgsModule::VariableEventQueue<18432, 16>* GetGuiOutQueue() { return &mGuiOutQueue; }

        // X360 GuiModule::Render(renderOut) -> EffectsArbitrator::GenerateEffectFrameEvents
        // @0x82503060 (on PC BrnGameModule calls it under the renderer output read lock).
        void GenerateEffectFrameEvents(RendererIO::OutputBuffer* lpRenderOutput)
        {
            mEffectsArbitrator.GenerateEffectFrameEvents(lpRenderOutput);
        }
        // [FLAG PC bring-up] the frame-pointer form BrnGameModule::DoDispatch drives.
        void GenerateEffectFrameEvents(BrnEffectsFrame* lpFrame1, BrnEffectsFrame* lpFrame2)
        {
            mEffectsArbitrator.GenerateEffectFrameEvents(lpFrame1, lpFrame2);
        }

        // The module's profile manager (X360 module+681696). Exposed so the game module's
        // per-sub-step GUI bridge can read back the progression pair the console's
        // GameState module publishes as game action 193 -- see the FLAG in
        // BrnGameModule.cpp. The X360 reaches the embedded manager by offset from inside
        // GuiModule::Update itself, so no accessor is emitted there.
        ProfileManager&       GetProfileManager()       { return mProfileHost.GetProfileManager(); }
        const ProfileManager& GetProfileManager() const { return mProfileHost.mProfileManager; }

        // X360 GuiModule::Prepare @0x82518D68 STAGE 14: `if (!WorldDataController::Prepare(
        // guiModule + 307836, gameDataInputBuffer)) return 0;`. The controller is a GuiModule
        // member (Construct binds it into the cache) and its acquire machine talks to the
        // GAME DATA request queue, so it can only be pumped where that buffer pair is live.
        // FLAG PC drive point: the console's module scheduler hands GuiModule::Prepare the
        // GameData input/output pair; on PC the only place that pair exists and is pumped is
        // BrnGameModule::ResourceUpdateThread (the single-threaded stand-in for the console's
        // resource thread), which calls this immediately before GameDataModule::Update -- the
        // same "stage the request, then pump" order the console's Prepare has. Returns the
        // machine's own done flag.
        bool PrepareWorldData(BrnResource::GameDataIO::InputBuffer* lpGameDataInput);

        // ⭐ [event-starts wave 2026-08-27] X360 GuiModule::Prepare2 @0x825194B8's
        // WorldDataController leg -- WorldDataController::Prepare2 @0x82516CB8, the only writer of
        // mpProgressionData / mpStreetData. Same FLAG'd PC drive point as PrepareWorldData above.
        // ⛔ MUTUALLY EXCLUSIVE WITH PrepareWorldData: both machines drain the SAME receiver
        // queue. The body's banner spells out what overlapping them corrupts.
        bool PrepareWorldData2(BrnResource::GameDataIO::InputBuffer* lpGameDataInput);

        // True once PrepareWorldData has reported done (or has parked on a request no PC
        // producer answers -- see the banner in BrnGuiWorldDataController.cpp). The driver
        // reads it only for its one-shot diagnostic.
        const WorldDataController& GetWorldDataController() const { return mWorldDataController; }

        // The sat-nav tracker (mGuiTracker). BrnGameModule::BridgeWorldRouteInformationToGui hands
        // it the route replies.
        GuiTracker* GetGuiTracker() { return &mGuiTracker; }

        // Is the SCREEN flow's live state currently subscribed to liEventId? The observer
        // table is the module's own record of the type-34/35 registration records each state
        // posts from OnEnter (RegisterForEvents), so this is the exact "a state is listening
        // for this event right now" signal -- and it goes false again when that state leaves.
        // Read by the game module's GameState->GUI car-select stand-in, which must not publish
        // into a queue nobody is draining. FLAG PC bring-up: on the console the producers are
        // driven by the game-state side, which never needs to ask.
        bool IsScreenFlowObserving(s32 liEventId) const
        {
            return liEventId >= 0 && liEventId < KI_MAX_OBSERVED_EVENT_ID
                && mabObservedEventIds[E_GUIFLOW_SCREEN][liEventId];
        }

    private:
        // The GUI debug components read the cache inline off their module pointer.
        friend struct SatNavDebugComponent;
        friend struct GuiDebugComponent;
        friend struct GuiCacheDebugComponent; // actual cache status reader

        // ARTIST824F10D8; the real static callback registered by native
        // Prepare. Its recovered body remains unregistered in the host flow.
        static void GameTalkMsgHandler(EA::GameTalk::GameTalkMessage* lpMessage);

        // Extracted ARTIST82519218..54; called only by the future typed Prepare stage10.
        // Keep current no-arg host Prepare selected until the complete native chain is ready.
        void PrepareNativeDebugComponents();

        // Extracted ARTIST8251A4D4..8251A538; dormant until the typed PreWorld chain is selected.
        void PublishNativeMovieResourceRequest(CgsGui::CgsGuiModuleIO::OutputBuffer* lpGuiOutput);
        void UpdateCollisionWorldValidation(CgsGui::CgsGuiModuleIO::OutputBuffer* lpGuiOutput);
        void UpdateCarPoolValidation(CgsGui::CgsGuiModuleIO::OutputBuffer* lpGuiOutput);

        // Extracted native blocks: Prepare82519360..C4,
        // Update82529CA8..DD0 and Release824F917C..B0. These remain
        // uncalled by the selected host lifecycle until native composition.
        void PrepareNativeSystemNotifications();
        void UpdateNativeSystemNotifications(CgsGui::ModelIO::InputBuffer* lpInputBuffer);
        void ReleaseNativeSystemNotifications();

        // Dispatch this sub-step's inbound GUI events (the real GuiModule::Update event
        // switch @0x82527A58: 144 -> RunFsm, 481 -> HandleHudStateLoadComplete + forward,
        // 14/16 -> the model-out notification queue, 358 -> profile image autosave,
        // 493 -> collision-world completion, 504/508/513 -> MovieManager, 512 -> traffic-pool state),
        // and fan every event the flow subscribed to
        // (records 34/35) into the HUD flow's in-queue
        // -- the EventInterpreterModule observer dispatch.
        // Returns the last dispatched record. A non-null cursor consumes only the
        // appended suffix; the frame owner initializes the image-save flag once.
        const CgsModule::Event* DispatchInboundGuiEvents(
            bool& rbHasSaveImageEvent, CgsGui::ImageFileInfo& lrSaveImageInfo,
            const CgsModule::Event* lpAfterEvent = 0);
        void AutosaveProfile(const CgsGui::ImageFileInfo* lpImageFileInfo);

        // Drain one flow's StateInterface output queue -- the per-frame dispatch point
        // for everything its states post: subscription records (34/35, keyed into that
        // flow's observed-id table), movie play/stop (508/509), the channel-40 command
        // records (-> mGuiOutQueue for the game bridge), the channel-41 view-state
        // records (-> the view input queue), and the menu-music / audio-trigger events
        // (155/201, the PC sound leaves).
        void DrainFlowOutputQueue(s32 liFlow);

        // ARTIST 0x82507800; reads the base GUI module output queue after its Update.
        // The selected PC path has no caller for this OutputBuffer-based entry yet.
        void HandleEventsPostBaseModuleUpdate(CgsGui::CgsGuiModuleIO::OutputBuffer* lpOutput);

        // @0x824F0D30 -- refresh the two live player-name entries in the language
        // database ("PLAYER_NAME_STRING_ID" / "PLAYER_NAME_STRING_ID_Q"). The X360 asks
        // XUserGetName for the signed-in gamertag; when that FAILS it falls back to the
        // database's own "DEFAULTPLAYERNAME" / "DEFAULTPLAYERNAMEQUOTED" entries ("You" /
        // '"You"'). Triggered by GUI event 507 in GuiModule::Update's dispatch (the
        // record BrnGui::BootProfile::OnLeave posts when the profile boot completes).
        // (The console passes the view-state queue as a second argument; the body never
        // reads it, so it is dropped here.)
        void UpdatePlayerName();

        // Selected PC GUI port: preserve the original calibration call with the
        // GameData locks owned by the frame caller.
        void UpdateCalibrationScreen(BrnResource::GameDataIO::InputBuffer* lpGameDataInput,
                                     const BrnResource::GameDataIO::OutputBuffer* lpGameDataOutput);

        // The GUI resource-loading dispatch: hand the flow controller's FSM-bundle load
        // requests (GuiEventLoadRequest, queue type 39, out of mModelInputBuffer) to the
        // REAL CgsGui::GuiResourceModule, run it (its acquire machine + the [PC] platform
        // servicer that loads FSM\<NAME>.BUNDLE), and bridge its GuiEventLoadNotification
        // (14) records back into the ModelIO output buffer the controller reads. Replaces
        // the host stand-in ServiceFsmBundleRequests below (Phase 1 of retiring that path).
        void DispatchGuiResourceModule();

        // [PC IO] the ORIGINAL host FSM-bundle stand-in: drained the ModelIO input
        // buffer's load requests, loaded "FSM/<NAME>.BUNDLE" synchronously, and posted
        // the GuiEventLoadNotification (14) itself. SUPERSEDED by DispatchGuiResourceModule
        // (the real module now owns this); retained unused this phase (/OPT:REF strips it).
        void ServiceFsmBundleRequests();

        // Post one event into each live flow's in-queue if that flow subscribed to it
        // (the observer-subscription filter, per flow).
        void RouteEventToFlow(const CgsModule::Event* lpEvent, s32 liId, s32 liSize);

        enum ECollisionWorldStateValidationState
        {
            E_COLLISIONWORLDSTATEVALIDATIONSTATE_IDLE = 0,
            E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALIDATING_FOR_BOOT = 1,
            E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALID_FOR_BOOT = 2,
            E_COLLISIONWORLDSTATEVALIDATIONSTATE_VALIDATING_FOR_BOOT = 3,
            E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALIDATING_FOR_SAVELOAD = 4,
            E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALID_FOR_SAVELOAD = 5,
            E_COLLISIONWORLDSTATEVALIDATIONSTATE_VALIDATING_FOR_SAVELOAD = 6,
            E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALIDATING_FOR_MOVIE = 7,
            E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALID_FOR_MOVIE = 8,
            E_COLLISIONWORLDSTATEVALIDATIONSTATE_VALIDATING_FOR_MOVIE = 9,
            E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALIDATING_FOR_NETWORKING = 10,
            E_COLLISIONWORLDSTATEVALIDATIONSTATE_INVALID_FOR_NETWORKING = 11,
            E_COLLISIONWORLDSTATEVALIDATIONSTATE_VALIDATING_FOR_NETWORKING = 12,
            E_COLLISIONWORLDSTATEVALIDATIONSTATE_COUNT = 13,
        };
        enum ECarPoolValidationState
        {
            E_CARPOOLSTATEVALIDATIONSTATE_IDLE = 0,
            E_CARPOOLSTATEVALIDATIONSTATE_WAITING_FOR_POOL_TO_EMPTY = 1,
            E_CARPOOLSTATEVALIDATIONSTATE_INVALIDATING_FOR_MOVIE = 2,
            E_CARPOOLSTATEVALIDATIONSTATE_INVALID_FOR_MOVIE = 3,
            E_CARPOOLSTATEVALIDATIONSTATE_VALIDATING_FOR_MOVIE = 4,
            E_CARPOOLSTATEVALIDATIONSTATE_WAITING_FOR_POOL_TO_FILL = 5,
            E_CARPOOLSTATEVALIDATIONSTATE_COUNT = 6,
        };

        // ARTIST82518B88; DecFIGS BrnGuiModule.h:417. The flow's
        // CompleteLoading::OnLeave owns the later false transition.
        bool mbBootMovieMode;
        ECollisionWorldStateValidationState meCollisionWorldStateValidationState;
        bool mbCollisionWorldInvalid;
        ECarPoolValidationState meCarPoolStateValidationState;

        // DecFIGS h:513/514; ARTIST82518850/68. These are the derived
        // lifecycle owners, separate from the shared GuiModule's own stages.
        GuiPrepareStage mePrepareStage;
        // ARTIST-only second-prepare word (Construct82518858). DecFIGS lacks
        // this addition; the host member name is a projection of that owner.
        u32 muPrepare2State;
        GuiReleaseStage meReleaseStage;

        // This sub-step's GUI module INPUT buffer (set by BrnGameModule each sub-step; the
        // buffer itself lives on the update IO stack and is re-created per sub-step).
        CgsGui::CgsGuiModuleIO::InputBuffer* mpGuiEventInputBuffer;

        // ARTIST's callback publishes GuiAudioTriggerEvent through GuiModule's current
        // output buffer. The PC scheduler exposes that channel as mGuiOutQueue, so retain
        // the same explicit producer pointer instead of bypassing the event route.
        CgsModule::VariableEventQueue<18432, 16>* mpOutputBuffer;

        // ARTIST82518BB0..BD0: this derived receiver owns its inline 1024-byte backing.
        // Separate owners handle collision validation and GameData replies.
        CgsGui::GuiAccessPointers::GuiEventReceiverQueue mEventReceiverQueue;
        CgsGui::GuiAccessPointers::GuiEventReceiverQueue mCollisonPoolValidationReceiverQueue;

        ViewModule mViewModule;       // DecFIGS BrnGuiModule.h:441 (owns Apt/text/render state)

        // X360 +311952 -- the GUI CUSTOM-RENDERER SET manager. GuiModule::GuiModule
        // @0x827E5B28 constructs it by value and GuiModule::Prepare @0x82518D68 stage 7
        // does, in this order:
        //     v27 = (*(*(v3 + 311952) + 4))(v3 + 311952, rwGeneralRes, rwLinearRes);
        //     CgsGui::ViewModule::SetCustomRendererManager(v3 + 132224, v3 + 311952, 10,
        //                                                  v3 + 1629284);
        //     if (!v27) return 0;
        // -- i.e. Prepare the manager, install it into the view module (which mirrors it
        // into AptRenderHandler::mpCustomRendererManager, the pointer the Apt custom-control
        // callback reads), and only then gate on the prepare result.
        CustomRendererManager mCustomRendererManager;   // X360 +311952
        // ARTIST-only handle at gm+0x18DC60. The original Release
        // assertion names this member; the PC provider returns a kernel HANDLE.
        void* mhSysListenerHandle;
        BrnReplays::GuiModuleSerialiser mGuiModuleSerialiser; // ARTIST gm+1629284

        // The view-module IO pair the per-frame bridge fills (the input buffer carries the
        // view-state events -- frame time step 26, the play-movie events 18, the load
        // notifications 14 -- into CgsGui::ViewModule::Update). FLAG (bridge stand-in):
        // the console fills these through the module scheduler's IO stacks.
        CgsGui::ViewIO::InputBuffer  mViewInputBuffer;
        CgsGui::ViewIO::OutputBuffer mViewOutputBuffer;
        CgsGui::CgsGuiModuleIO::InputBuffer mCompletedRenderInputPC;
        bool mbRenderInputCompletedPC = false;
        s64 miLastViewFrameMs;        // PC frame clock for the time-step event (FLAG: wall clock)
        MovieManager mMovieManager;   // X360 +301600 (drives the boot/attract videos)

        // X360 +306752 -- the full-screen colour/brightness calibration test card. DWARF
        // BrnGuiModule.h:506 places it between mMovieManager (h:504) and
        // mWorldDataController (h:509), which is exactly the order GuiModule::Construct
        // @0x82518B18-24 constructs them in (`MovieManager::Construct(gm+301600)` then
        // `ColourCalibrationScreen::Construct(gm+306752)`). Reached BY NAME here -- the
        // guest displacement is a note, not a layout instruction.
        ColourCalibrationScreen mColourCalibrationScreen;   // X360 +306752

        // DecFIGS BrnGuiModule.h:516; ARTIST82518EF4..82519024 fills all
        // seven pool ids and seven allocator rows. The two selected PC
        // consumers use these same rows rather than separate projections.
        CgsGui::GuiModuleConfig mGuiConfig;

        // Host extraction of native Prepare's inline stage-1 block. This
        // helper stays dormant until the whole typed Prepare chain is ready.
        void PopulateNativeGuiConfig(
            const BrnResource::GameDataIO::OutputBuffer* lpGameDataOutput);

        // Host extraction of ARTIST825193C8..82519444. Unselected; native
        // Prepare must wait here before its world-data stage.
        bool EnsureNativeGuiResources();

        // [licence-icon] the manager's staged-prepare latch. The console pumps the manager's
        // Prepare through GuiModule::Prepare's stage re-entry (`if (!v27) goto fail` + the module
        // scheduler re-calls Prepare until every stage passes); this build's Prepare runs once,
        // so Update owns the pump (see the seat note at the call).
        bool mbCustomRenderersPrepared;
        BrnUpdateSet muFrameUpdateSet;        // the scheduler's `a2` (see SetFrameUpdateSet)
        // Apt runtime preparation lives in this module; the renderer owns the
        // immediate command buffers supplied to the original Render entry.
        // X360 gm+1546880 -- THE SCREEN-FILTER SYSTEM (BrnGuiEffectsArbitrator.h): the post-FX
        // hook blender the director's crash / wreck / stunt requests reach through GUI events
        // 495..500. Construct'd right before MovieManager::Construct (GuiModule::Construct
        // @0x82518B18); Update runs its ResourceUpdate + EventUpdate, the render drive its
        // GenerateEffectFrameEvents.
        EffectsArbitrator mEffectsArbitrator;
        AlwaysAvailableComponentsManager mAlwaysAvailableComponentsManager;

        // ---- the real flow-controller chain (X360 GuiModule members) --------------------
        // X360 +307836 -- the GUI-side world/progression/vehicle data front-end. Construct
        // Constructs it and binds it into the cache (SetWorldDataController); Prepare stage 14
        // runs its acquire machine. It MUST outlive every flow state that resolves a car.
        WorldDataController mWorldDataController;   // X360 +307836
        CgsGui::GuiAccessPointers mGuiAccessPointers; // ARTIST gm+1005332
        CgsGui::GuiAccessPointers::GuiEventReceiverQueue mGDMReceiverQueue; // gm+1628232
        GuiCache          mGuiCache;        // X360 +1005376 (the flow states' cache; event-64 payload)
        // [H3b] the shared map-icon manager (X360 +1088304; ctor from GuiModule::GuiModule
        // @0x827E5D7C, Construct + GuiCache::SetMapIconManager from GuiModule::Construct).
        MapIconManager    mMapIconManager;

        // ⭐ X360 +1131872 -- THE SAT-NAV TRACKER, and the object GuiCache::mpGuiTracker
        // points at. GuiModule::Construct @0x82518028 owns it exactly the way it owns
        // mWorldDataController / mMapIconManager / mFreeburnChallengeManager above: a plain
        // by-value member, inline-Constructed (the eleven stores off r29 == gm+1131872 at
        // @0x82518874..@0x825188C8), handed to GuiCache::Construct as its FIRST argument
        // (`mr r4, r29` @0x82518940), and finally given the cache back through the tail
        // publish `GuiTracker::RecEvent(gm+1131872, {gm+1005376}, 64, 4)`.
        //
        // Until this member existed, GuiCache::mpGuiTracker had ZERO writers in the whole
        // tree: the three sat-nav publishers in BrnGuiCache_wJ_01.cpp built their
        // GuiEventSetTracker record, found GetGuiTracker() null, logged the one-shot
        // "[guicache-tracker] ... mpGuiTracker is not bound" and dropped it -- so the
        // sat-nav route line could never come up. (Same failure shape as the
        // mpChallengeManager gap noted below.)
        GuiTracker        mGuiTracker;      // X360 +1131872

        // ⭐ [stuntrace] X360 +309584 -- THE GUI-SIDE FREEBURN-CHALLENGE TRACKER, and the
        // object GuiCache::mpChallengeManager points at. GuiModule::Construct @0x82518028
        // constructs it against the cache and binds it in (SetChallengeManager, the console's
        // `*(gm + 1021868) = gm + 309584`); GuiModule::Update @0x82527A58 ticks it once per
        // frame. It is the ONE owner in the image -- the manager is a plain by-value member of
        // this module, exactly like mWorldDataController/mMapIconManager above.
        //
        // Until this member existed, GuiCache::mpChallengeManager had ZERO writers and every
        // in-event HUD frame that touched a freeburn-challenge arm of RaceMainHudState fired
        // the "mpChallengeManager" assert (BrnGuiCache.h:2390) and then read off a null
        // pointer -- the user-blocking dialog on starting a stunt race.
        // The Burnout Skillz page tracker GuiCache::mpSkillsManager points at (the lobby
        // position table and the bar values read it); constructed, bound and ticked beside the
        // challenge manager.
        BurnoutSkillsManager     mBurnoutSkillsManager;
        FreeburnChallengeManager mFreeburnChallengeManager;   // X360 +309584
        BrnScreenFlow     mScreenFlow;      // X360 mScreenFlow (SCREEN = E_GUIFLOW_SCREEN, the front-end)
        BrnHudFlow        mHudFlow;         // X360 +638904-adjacent flow set (HUD = E_GUIFLOW_HUD)
        BrnOverlayFlow    mOverlayFlow;     // X360 mOverlayFlow (OVERLAY = E_GUIFLOW_OVERLAY)
        GuiFsmController  mFsmController;   // X360 +638904 (the flow FSM controller)

        // ---- the HUD-message pair (gateui wave, round 2) --------------------------------
        // X360 GuiModule::Construct @0x82518028 lines 277-278 constructs them back to back
        // and in this order:
        //     HudMessageDirector::Construct(gm + 639264, gm + 552 /*ModelModule*/, gm + 1005376 /*GuiCache*/);
        //     HudMessageAnalyzer ::Construct(gm + 660992, gm + 639264 /*the director*/);
        // then line 376 publishes the director into the cache
        // (`*(gm + 1021876) = gm + 639264` == GuiCache::SetHudMessageDirector), and
        // Prepare @0x82518D68 stage 3 line 104 gives the analyzer the shared access-pointer
        // block (`*(gm + 660992) = gm + 1005332`).
        //
        // ⭐ THIS PAIR IS THE GUI END OF THE gateui CHAIN. Until it landed, the whole
        // HudMessageAnalyzer fan-out (25 partfiles) and the director's send path were
        // unreachable code: HudMessageAnalyzer::Update had no caller anywhere in the
        // program, so `[UI-gate] hud stunt-info ...` could never print no matter what the
        // GameState/bridge lanes did (round-1 verify WRONG-2).
        HudMessageDirector mHudMessageDirector;  // X360 +639264
        HudMessageAnalyzer mHudMessageAnalyzer;  // X360 +660992
        GuiOverlaysDirector mOverlaysDirector;   // console +0xA1B10 (662288)

        KeyboardHost mKeyboardHost; // ARTIST gm+681672
        ProfileHost mProfileHost; // ARTIST gm+A66D0; actual contained manager is host+10.
        // ---- [profile-save 2026-08-27] the module's AUTOSAVE latch + throttle ------------
        // X360 GuiModule::Update tail @0x825295CC..0x825296A4:
        //   r30 = module + 0x18D844 (1628228) -- the autosave-PENDING byte, raised by the
        //     event walk's case 356 (GuiAutosaveRequestEvent), case 358 and case 43, cleared
        //     by the tail once the Autosave has been started;
        //   module + 0x18D840 (1628224) -- the f32 GuiCache::GetTime() stamp of the last
        //     autosave, the throttle's base (`lfsx f13,r26,r31` / `fadds f0,f13,flt_82004C6C`
        //     with flt_82004C6C == 60.0f).
        // GuiModule::AutosaveProfile @0x8251A568 and GuiDebugComponent::AutosaveProfile
        // @0x825238E0 write the same pair after their own Autosave calls.
        // ARTIST Construct clears the networking request latches; input Update events and the
        // car-pool validator own the traffic-pool latch transitions.
        bool mbCollisionWorldInvalidateForNetworking;
        bool mbCollisionWorldValidateForNetworking;
        bool mbTrafficPoolEmptied;
        bool mbProfileAutosavePending;      // X360 +1628228
        f32  mfLastProfileAutosaveTime;     // X360 +1628224
        // The per-frame FORCE flag the console keeps in a stack byte across its single
        // Update (`v142`): case 356 ORs the request's own payload byte into it and case 505
        // (game paused) sets it outright, so a forced request bypasses the 60-second
        // throttle. This build splits the console's one Update into DispatchInboundGuiEvents
        // + Update, so the byte has to survive between them -- it is written by the event
        // walk and consumed (and cleared) by the tail in the same frame.
        bool mbForceProfileAutosave;        // X360 Update stack byte var_430 (v142)
        BrnGuiKeyboard mGuiKeyboard; // ARTIST gm+1545808
        CgsGui::SystemUserProfile mSystemUserProfile; // X360 +949152 (sign-in watcher the manager listens to)
        // Four actual by-value GUI debug owners (ARTIST827E5D38..6C), native relative order.
        // Existing host field order is retained; host offsets follow these complete types.
        GuiDebugComponent mDebugComponent;
        GuiHudMessagesDebugComponent mHudMessageDebugComponent;
        SatNavDebugComponent mSatNavDebugComponent;
        GuiCacheDebugComponent mGuiCacheDebugComponent;
        CgsMemory::HeapMalloc  mFsmLuaHeap;    // the FSM Lua VM heap (the controller's allocator)
        CgsMemory::HeapMalloc   mProfileHeap;   // the manager's heap (mugshot buffer + SLS callbacks)
        CgsMemory::LinearMalloc mProfileLinear; // the manager's linear (SLS Prepare)
        CgsMemory::LinearMalloc mHudStatePool; // the 14-state pool allocator (HudFlow::Prepare)
        CgsMemory::LinearMalloc mOverlayStatePool; // the 15-popup-state pool allocator (OverlayFlow::Prepare)
        CgsMemory::LinearMalloc mScreenStatePool;  // the 61-state pool allocator (ScreenFlow::Prepare)

        // The ModelIO pair the controller exchanges with the (module-dispatch) resource
        // loader: requests out through the input buffer, notifications back on the output
        // buffer. On the console these are per-frame stack buffers ("GUIModel"); the PC
        // module owns a persistent pair and clears the queues per frame as the real
        // Update does (Clear @ the update tail).
        CgsGui::ModelIO::InputBuffer  mModelInputBuffer;
        CgsGui::ModelIO::OutputBuffer mModelOutputBuffer;

        // The REAL GUI resource-loading module + its own per-frame IO pair. Wired in to
        // REPLACE the host FSM-bundle stand-in: the controller's GuiEventLoadRequest queue
        // (out of mModelInputBuffer) is handed to the module, which loads FSM\<NAME>.BUNDLE
        // through its acquire machine + the [PC] platform servicer and posts the
        // GuiEventLoadNotification (14) back -- DispatchGuiResourceModule bridges those into
        // mModelOutputBuffer for the controller. The console recreates the module IO
        // buffers each frame; the PC pair is persistent and cleared per frame.
        CgsGui::GuiResourceModule                 mGuiResourceModule;
        CgsGui::GuiResourceModuleIO::InputBuffer  mResourceInputBuffer;
        CgsGui::GuiResourceModuleIO::OutputBuffer mResourceOutputBuffer;

        // The per-flow in-queues (every observed event is fanned into the subscribing
        // flow's queue) + the module GUI-OUT queue the game bridge drains.
        ::InputBuffer::GuiEventQueue mScreenInQueue;
        ::InputBuffer::GuiEventQueue mHudInQueue;
        ::InputBuffer::GuiEventQueue mOverlayInQueue;
        CgsModule::VariableEventQueue<18432, 16> mGuiOutQueue;
        // [FLAG PC seam] the console's GUI out-event loop-back (CgsGui::GuiModule +111644):
        // CgsGui::GuiModule::Update appends the frame's out-events there and the next
        // BrnGui::GuiModule::Update appends them into the GUI input queue, where the overlays
        // director reads the flows' 184/186/188/189/190. This build fans flow output to the
        // flows at the drain instead (RouteEventToFlow), so only the director's ids are kept
        // here and handed to it. DELETE-WHEN the input-queue loop-back is modelled whole.
        CgsModule::VariableEventQueue<18432, 16> mOverlayLoopBackQueue;
        // The always-available components manager's in-queue: the subscription filter
        // (RouteEventToObserver) delivers the events the manager registered for (its real
        // 19-id table: save-icon 355, connect 64, showtime, ...) into it, then the module
        // pumps AlwaysAvailableComponentsManager::Update against it each frame -- the same
        // observer contract the console's EventInterpreterModule drives (deliver via
        // SetInEventQueue's queue, pump via UpdateObservers).
        ::InputBuffer::GuiEventQueue mAlwaysAvailInQueue;

        // The registered event OBSERVERS (the console EventInterpreterModule's observer
        // list): the three flows plus the always-available components manager -- the AAC
        // registers through its own StateInterface exactly like a flow state (its Prepare
        // posts the real 19-id table, ARTIST dword_8206F760, as type-34 records).
        static const s32 E_GUIOBSERVER_ALWAYSAVAILABLE = E_GUIFLOW_COUNT;
        static const s32 KI_NUM_EVENT_OBSERVERS        = E_GUIFLOW_COUNT + 1;

        // The observer-subscription tables (records 34/35 from each observer's state
        // interface output queue). One flag set per observer slot.
        static const s32 KI_MAX_OBSERVED_EVENT_ID = 1024;
        bool mabObservedEventIds[KI_NUM_EVENT_OBSERVERS][KI_MAX_OBSERVED_EVENT_ID];

        // EventInterpreterModule priority state. ARTIST permits ten priority keys
        // per observer; each key owns an override-event mask. A priority owner starts
        // blocking its override set after receiving its priority event and stops when
        // the state unregisters or posts the explicit stop-blocking record.
        static const s32 KI_MAX_PRIORITY_CLAIMS_PER_FLOW = 10;
        struct PriorityClaim
        {
            bool mbActive;
            s32  miEventType;
            bool mabOverriddenEventIds[KI_MAX_OBSERVED_EVENT_ID];
        };
        PriorityClaim maPriorityClaims[KI_NUM_EVENT_OBSERVERS][KI_MAX_PRIORITY_CLAIMS_PER_FLOW];
        bool          mabPriorityBlocking[KI_NUM_EVENT_OBSERVERS];

        // One resident pool per flow slot for the loaded FSM LuaCode bundle (request ids
        // 13/14/15 = SCREEN/HUD/OVERLAY; each flow's ScriptedFsm holds its LuaCode
        // resource while live, so the pools must not alias across flows).
        CgsResource::Pool mFsmBundlePool[E_GUIFLOW_COUNT];
        bool              mbResourcesReadyFed;   // fed BF_LEGAL its resources-ready (567) yet
        // The Prepare latch behind IsPrepared() (see the accessor's note). The console has no
        // such member because its stage word IS the latch -- CgsGui::GuiModule::Prepare
        // @0x82518D68 is a 16-stage resumable ladder whose gated stages return 0 until the
        // stage word reaches DONE (boot audit F-P8a-1). This build's Prepare is still the
        // one-shot synchronous collapse of that ladder, so a bool is the whole of the state;
        // it becomes the stage word when the ladder itself is adopted.
        bool              mbPrepared;
    };

    // Renderer bridge, matching gpActiveMovieManager: GuiModule publishes itself while
    // prepared; the game dispatcher drives the original supplied-IO GUI render chain.
    extern GuiModule* gpActiveGuiModule;

}

#endif
