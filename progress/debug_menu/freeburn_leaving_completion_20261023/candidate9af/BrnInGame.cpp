#include "GameSource/Gui/Flow/Screen/States/BrnInGame.h"
#include <cstdlib>
#include <cstring>   // std::strcmp (the BRN_LOSE_DIAG witness)
#include "GameShared/GameClasses/Development/Log/CgsLog.h"

#include "GameShared/GameClasses/Gui/Model/State/CgsGuiStateInterface.h"  // StateInterface / GuiEventNetworkSuspension / GuiEventPlayAptMovie
#include "GameShared/GameClasses/Module/CgsVariableEventQueue.h"          // the state in-queue
#include "GameShared/GameClasses/Core/CgsAssert.h"                        // CGS_ASSERT
#include "GameShared/GameClasses/Core/CgsID.h"                            // CgsID / CgsIDCompress
#include "GameSource/Gui/BrnGuiCache.h"                                   // BrnGui::GuiCache
#include "GameSource/Gui/SatNav/BrnGuiTracker.h"                           // GuiTracker::ClearTracker
#include "GameSource/Gui/BrnGuiEventTypeDefs.h"                           // GuiOverlayRequest / GuiOverlayCompleteEvent / GuiEventActivateCrashNav
// BrnGuiDemangledEventTypes.h -- the canonical home of BrnGui::GuiEventNetworkPlayerImage
// (id 258) -- is not included here; the 258 wire record is built locally below, the same
// standing accommodation BrnLicenseComponent.cpp and BrnPhotoBoothComponent.cpp already make
// for this exact event.
#include "GameSource/Gui/Flow/Screen/States/Shared/BrnScreenShared.h"     // GetSplashScreenIDForGameMode (+ GsmIO::EGameModeType)
#include "GameSource/GameState/Progression/BrnProfile.h"                  // BrnProgression::Profile::GetIsNewProfile (the intro gate)
#include "GameSource/Input/GameInputActions.h"                       // EGameInputActions (the controller action vocabulary)

// BrnGui::InGame -- reconstructed from BURNOUT_X360_ARTIST.XEX (addresses in the
// header). The SCREEN flow's in-game root state: it owns the pause / main-map /
// event-map / driver-details entry points, the online main-menu handshakes
// (privileges -> "CNOnlStrtQn" question -> SelectOnlineMenuOption -> "TO_*" state
// events), the trophy-unlock / completion countdowns, and the EA-TRAX next-track
// debounce. The registered-event table (30 ids @0x82066680) and every .data constant
// below were read from the image; the class shape is the DecFIGS DWARF (BrnIngame.h).
//
// GUI-CACHE BOUNDARY (FLAG'd below): the state reads/writes a set of GuiCache members
// past the committed layout tail (the online bools @+0x4B4C.., the pause gates, the
// current-landmark s16 @+0x5284, the tracker pointer @+0x4054). Where the committed
// GuiCache exposes a named accessor it is called; each remaining touch is a FLAG'd
// boundary helper documenting the X360 member (DWARF name where recovered) so the real
// accessor can replace it when the GuiCache TU grows -- same discipline as
// BrnBootProfile.cpp's boundaries.
namespace BrnGui
{
    // DWARF BrnInGame.cpp:85/86 -- namespace-scope float globals (they live in .data on
    // the console builds). Values read from the X360 image: both 3.5 seconds.
    f32 KF_TIME_UNTIL_TROPHY_CAR_UNLOCK_SEQUENCE = 3.5f;   // @ 0x82F272D8
    f32 KF_TIME_UNTIL_COMPLETION_SEQUENCE        = 3.5f;   // @ 0x82F272DC

    namespace
    {
        // [FLAG PC witness] BRN_LOSE_DIAG -- NOT IN THE CONSOLE. The screen-flow half of the
        // event-end watchdog (issue #32): which state event took the flow out of InGame, and
        // whether GUI 291's "TO_OFF_POST"/"TO_ST_POST" survived to the end of the update that
        // posted it. Opt-in, first 60 lines.
        bool LoseDiagLine()
        {
            static const bool sbEnabled = (std::getenv("BRN_LOSE_DIAG") != 0);
            static s32        siLines   = 0;
            return sbEnabled && CgsDev::Log::gpDebugPrint != 0 && (siLines++ < 60);
        }

        // ---- observed-event ids (roles from the Update dispatch / assert strings; the
        //      full 30-entry registered table is the static below) ----------------------
        const s32 KI_EVENT_CONTROLLER          = 6;    // controller action (sub-id @+4)
        const s32 KI_EVENT_PAD_DISCONNECTED    = 9;    // per-frame pad-disconnect tick
        const s32 KI_EVENT_GUI_CACHE           = 64;   // per-frame cache event (GuiCache* payload)
        const s32 KI_EVENT_OVERLAY_COMPLETE    = 189;  // GuiOverlayCompleteEvent payload
        const s32 KI_EVENT_NETWORK_SPLASH      = 269;  // GuiEventNetworkSplashEvent payload
        const s32 KI_EVENT_PERFORM_MENU_OPTION = 284;  // GuiEventPerformOnlineMainMenuOption payload

        // ---- controller action sub-ids (payload word +4 of the action event). Named from
        //      the DWARF vocabulary now that it has a home in the tree
        //      (GameSource/Input/GameInputActions.h); the trailing comment on each line is
        //      what THIS state does with it. ⚠️ 46 used to be called KI_ACTION_PAUSE_MAIN_MAP
        //      here -- a local invention. The ROLE was right (Back opens the map) but the id
        //      is E_GAMEINPUTACTIONS_GUI_BACK, and that misnomer is part of why the PC
        //      binding table went years without a Back button. -------------------------
        const s32 KI_ACTION_GUI_START         = E_GAMEINPUTACTIONS_GUI_START;         // 45 -> driver details
        const s32 KI_ACTION_GUI_BACK          = E_GAMEINPUTACTIONS_GUI_BACK;          // 46 -> main map
        const s32 KI_ACTION_GUI_LSHOULDER     = E_GAMEINPUTACTIONS_GUI_LSHOULDER;     // 54 -> suppress a pending next-track
        const s32 KI_ACTION_GUI_RSHOULDER     = E_GAMEINPUTACTIONS_GUI_RSHOULDER;     // 55 -> arm the next-EA-track debounce
        const s32 KI_ACTION_GUI_EVENT_DETAILS = E_GAMEINPUTACTIONS_GUI_EVENT_DETAILS; // 58 -> open the event map

        const f32 KF_EA_TRAX_DEBOUNCE = 0.3f;   // flt_82066050 (.rodata, 0x3E99999A)

        // The "no current event start location" LandmarkIndex sentinel the per-frame
        // event-map gate compares against. word_82F27394 (.data s16 == -1, the
        // BrnInGame.cpp statics block); its source name is not in the recovered DWARF
        // slice.
        const s16 KI_NO_EVENT_START_LANDMARK = -1;

        // GuiCache::meLastDisconnectedError value that selects the "CNLobbyDiscD"
        // overlay variant (any other non-zero error shows "CNLobbyDisc"). The
        // CgsNetwork::EServerInterfaceError enumerator name is not recovered.
        const s32 KI_SERVER_ERROR_LOBBY_DISCONNECT_D = 19;

        const s32 KI_CHANNEL_GUI_OUT      = 40;  // GuiEventOut
        const s32 KI_CHANNEL_VIEW_STATE   = 41;  // GuiOutViewState
        const s32 KI_CHANNEL_GUI_INTERNAL = 42;  // internal/HUD-component channel

        // DWARF GuiEventNetworkSplashEvent::ESplashState (BrnGuiEventTypeDefs.h:5462);
        // local until that header's TU grows the event type.
        const u32 KU_SPLASH_STATE_SHOW     = 0;
        const u32 KU_SPLASH_STATE_STOP     = 1;
        const u32 KU_SPLASH_STATE_FINISHED = 2;

        typedef CgsModule::VariableEventQueue<18432, 16> StateInputQueue;

        // ---- in-queue payload views (the queue delivers the header-stripped payload;
        //      same idiom as BrnGuiOverlaysDirector.cpp's notification views) -----------
        struct GuiEventCache : public CgsModule::Event
        {
            GuiCache* mpGuiCache;
        };

        struct GuiEventProfilePointer : public CgsModule::Event   // event 350 payload
        {
            BrnProgression::Profile* mpProfile;
        };

        // The GuiOverlayCompleteEvent payload (id @+0, leave method @+8 -- the X360
        // HandleOverlayComplete `ld 0(r30)` / `lwz 8(r30)` loads).
        struct GuiOverlayCompletePayload : public CgsModule::Event
        {
            CgsID mOverlayId;
            s32   miLeaveMethod;   // GuiOverlayCompleteEvent::LeaveMethod
        };

        // The GuiEventPerformOnlineMainMenuOption payload (the option word leads).
        struct GuiEventMainMenuOptionPayload : public CgsModule::Event
        {
            EMainMenuOptions meMainMenuOption;
        };

        // ---- out-queue wire records --------------------------------------------------
        // 16-byte GuiEvent<N> command { 1, N, 12 } (the shared channel-command record;
        // same shape as BrnBootProfile.cpp's).
        template <s32 N>
        struct GuiCommandEvent16 : public CgsGui::GuiEvent<N>
        {
            u8 mu8Flag;
            u8 maPad[3];
            GuiCommandEvent16(u8 lu8Flag = 0) : CgsGui::GuiEvent<N>(1, 12), mu8Flag(lu8Flag)
            { maPad[0] = maPad[1] = maPad[2] = 0; }
        };

        template <s32 N>
        void PostCommand16(CgsGui::StateInterface* lpInterface, s32 liChannel, u8 lu8Flag = 0)
        {
            GuiCommandEvent16<N> lEvent(lu8Flag);
            lpInterface->GetOutputEventQueue()->AddEvent(
                reinterpret_cast<const CgsModule::Event*>(&lEvent), liChannel, 16);
        }

        // ⛔ `GuiViewStateEvent20` DELETED 2026-09-06 (hud lane). It was the OnEnter
        // "view reset" modelled as a 20-byte { 8, 258, 12, w0, w1 } record with the payload
        // written as TWO X360 32-BIT WORDS -- `GuiViewStateEvent20 lViewReset(0u,
        // 0xFFFFFFFFu)`. The payload is not two opaque words: id 258 is
        // BrnGui::GuiEventNetworkPlayerImage { NetworkTexture* mpTexture; s32
        // miTextureIndex; }, and the console is posting the CLEAR record { null, -1 } --
        // NetworkPlayerImageRenderer::RecvEvent case 258 then takes its
        // `mbRenderTexture == false` arm and arms the 3-frame texture-clear countdown.
        // Read store-for-store from InGame::OnEnter @0x824D0498 (0x824D0518..0x824D0554):
        //     stw r28(0),  var_70        ; payload word 0 = 0            (the pointer)
        //     li  r11,-1 ; stw r11, var_70+4  ; payload word 1 = -1      (the index)
        //     ld  r11, var_70            ; take those 8 bytes as one 64-bit value
        //     li  r30,8  ; stw r30, var_70    ; header0 = sizeof(T) == 8 on X360
        //     stw r29(12), var_68        ; header2 = 12 (payload offset)
        //     li  r11,0x102; stw r11, var_70+4 ; header1 = 258
        //     li  r5,0x29 ; li r6,0x14   ; channel 41, record 20 bytes
        //     bl  VariableEventQueue<65536,16>::AddEvent
        // The 8 in header0 is `sizeof(GuiEventNetworkPlayerImage)` on a 4-BYTE-POINTER
        // console -- exactly the X360 size that rule 2 forbids reproducing on the x64 host,
        // where the same object is 16 bytes. Nothing consumed the record while the
        // channel-41 bridge filtered it away, so the wrong width was invisible; with the
        // console's routing restored (BrnGuiModule.cpp case 41 + the ViewModule tail
        // forward) the renderer read `miTextureIndex` off the end of an 8-byte payload,
        // asserted BrnNetworkPlayerImageRenderer.cpp:355/:481 and then AV'd in CopyTexture
        // (run scratch\bugtest\runs\hud_visibility\20260906_111310).
        // It is replaced by the typed wire record below, whose header words are computed from
        // the HOST offsetof/sizeof -- byte-identical in shape to the GuiEventWrapper<T,41>
        // the console's own OutputViewState<GuiEventNetworkPlayerImage> @0x82436CF0 builds,
        // and to the record BrnLicenseComponent.cpp / BrnPhotoBoothComponent.cpp already post
        // for this same event.

        // The channel-41 wire record for BrnGui::GuiEventNetworkPlayerImage (id 258):
        // { sizeof(payload), 258, offsetof(payload) } + { NetworkTexture*, s32 index }.
        // Local for the include reason stated at the top of this file, NOT because the type
        // lacks a home. The two payload members mirror that home field for field.
        struct GuiEventNetworkPlayerImageWire : public CgsGui::GuiEvent<258>
        {
            const CgsNetwork::NetworkTexture* mpTexture;        // payload +0x00
            s32                               miTextureIndex;   // payload +0x08 x64 (+0x04 console)

            GuiEventNetworkPlayerImageWire(const CgsNetwork::NetworkTexture* lpTexture,
                                           s32 liTextureIndex)
                : CgsGui::GuiEvent<258>(), mpTexture(lpTexture), miTextureIndex(liTextureIndex)
            {
                const size_t luOffset = offsetof(GuiEventNetworkPlayerImageWire, mpTexture);
                muHeader0 = static_cast<u32>(sizeof(*this) - luOffset);   // X360 8
                muHeader2 = static_cast<u32>(luOffset);                   // X360 12
            }
        };

        // The OutputGuiEvent<BrnGui::GuiOverlayRequest> wire record (@0x82436BE0):
        // { 288, 184, 16, <pad>, the 288-byte request }, channel 40, 304 bytes.
        struct GuiOverlayRequestWire : public CgsGui::GuiEvent<184>
        {
            u32               muPad0C;    // +0x0C (payload is 16-aligned past the header)
            GuiOverlayRequest mRequest;   // +0x10
            GuiOverlayRequestWire()
                : CgsGui::GuiEvent<184>(static_cast<u32>(sizeof(GuiOverlayRequest)), 16)
                , muPad0C(0) {}
        };

        void PostOverlayRequest(CgsGui::StateInterface* lpInterface, const char* lpcOverlayId)
        {
            GuiOverlayRequestWire lWire;
            lWire.mRequest.Construct(lpcOverlayId);
            lpInterface->GetOutputEventQueue()->AddEvent(
                reinterpret_cast<const CgsModule::Event*>(&lWire), KI_CHANNEL_GUI_OUT,
                static_cast<s32>(sizeof(GuiOverlayRequestWire)));
        }

        // The OutputGuiEvent<BrnGui::GuiOverlayWaitFinishRequest> wire record
        // (@0x82476E98): { 8, 188, 16, <pad>, CgsID }, channel 40, 24 bytes.
        struct GuiOverlayWaitFinishWire : public CgsGui::GuiEvent<188>
        {
            u32                         muPad0C;    // +0x0C (8-aligned payload)
            GuiOverlayWaitFinishRequest mRequest;   // +0x10 (the compressed overlay id)
            GuiOverlayWaitFinishWire() : CgsGui::GuiEvent<188>(8, 16), muPad0C(0) {}
        };

        void PostOverlayWaitFinishRequest(CgsGui::StateInterface* lpInterface,
                                          const char* lpcOverlayId)
        {
            GuiOverlayWaitFinishWire lWire;
            lWire.mRequest.Construct(lpcOverlayId);
            lpInterface->GetOutputEventQueue()->AddEvent(
                reinterpret_cast<const CgsModule::Event*>(&lWire), KI_CHANNEL_GUI_OUT,
                static_cast<s32>(sizeof(GuiOverlayWaitFinishWire)));
        }

        // The OutputGuiEvent<BrnGui::GuiEventNetworkSplashEvent> wire record
        // (@0x82493880): { 4, 269, 12, state }, channel 40, 16 bytes.
        struct GuiNetworkSplashWire16 : public CgsGui::GuiEvent<269>
        {
            u32 muSplashState;   // +0x0C (ESplashState)
            explicit GuiNetworkSplashWire16(u32 luSplashState)
                : CgsGui::GuiEvent<269>(4, 12), muSplashState(luSplashState) {}
        };

        // ---- GuiCache boundary (X360 members past the committed layout tail; the
        //      committed accessors are used where they exist: GetGameMode /
        //      GetInEventColouringGate / GetTimeStep / AreAllAptComponentsInitialised).
        //      Each helper names the X360 member + offset so the GuiCache TU can absorb
        //      it as a real accessor. ---------------------------------------------------

        // ARTIST SelectOnlineMenuOption 0x824D0C9C: restore the return-to-EasyDrive latch.
        // The existing cache accessor has the earlier consumer name OnlineStartPending.
        void CacheSetEnteredOnlineViaEasyDrive(GuiCache* lpCache) { lpCache->SetOnlineStartPending(true); }

        // The five PauseAllowed @0x824B8DF8 gate bytes, read off the cache BY NAME
        // (issue #29 wave, 2026-09-15). These used to be five `return false` leaves, which
        // is why the START button opened Driver Details during an event intro: the console's
        // `lbz cache+0xA015` (the pre-race fly-by) and `+0xA014` (event prepared, not yet
        // started) both said "no pausing" and neither was read here.
        //   +0x4B57  DWARF h:1675 mbIsInJunkyard        +0x4B59  h:1677 mbMugshotActive
        //   +0x13B90 DWARF h:1895 mbIsLoadingScreenVisible
        //   +0xA014  mbEventPreparedForModeStart (name inferred; GuiCache::RecEvent 93 sets,
        //            237/322 clear)                     +0xA015  h:569 mbIsPreRaceFlyByActive
        bool CacheIsInJunkyard(const GuiCache* lpCache)    { return lpCache->IsInJunkyard(); }
        bool CacheIsMugshotActive(const GuiCache* lpCache) { return lpCache->IsMugshotActive(); }

        // FLAG PC-platform leaf: GuiCache::mCurrentLandmarkIndex (DWARF h:1709; X360
        // s16 +0x5284) has no committed accessor; PC returns the "no event start"
        // sentinel so the event map stays gated until the cache member lands.
        s16 CacheGetCurrentLandmarkIndex(const GuiCache* /*lpCache*/)
        { return KI_NO_EVENT_START_LANDMARK; }

        // +0xA014 / +0xA015 -- see the block above CacheIsInJunkyard. PauseGame @0x824DF05C
        // re-reads +0xA014 on the online arm (set == suppress the "ON_PAUSE" state event).
        bool CacheFarPauseGateA(const GuiCache* lpCache) { return lpCache->IsEventPreparedForModeStart(); }
        bool CacheFarPauseGateB(const GuiCache* lpCache) { return lpCache->IsPreRaceFlyByActive(); }

        // +0x13B90 == DWARF mbIsLoadingScreenVisible: it suppresses both HandleControllerInput
        // and PauseAllowed while the loading screen is up (see the block above CacheIsInJunkyard).
        bool CacheIsInputSuppressed(const GuiCache* lpCache) { return lpCache->IsLoadingScreenVisible(); }

        // The X360 Update reads the profile gate byte at +118033 (= 0x1CD11) each frame
        // and, when it is set, fires "TO_INTRO" + command 476 -- the first-boot entry to
        // the intro (welcome text / photo booth / licence / fly-by) sequence. That byte is
        // BrnProgression::Profile::mbIsNewProfile (BrnProfile.h:476, Construct seeds true;
        // BrnGui::Intro::OnLeave @0x824D1640 clears it), reached here through the
        // DWARF-attested accessor. Named for the X360 semantic, which is "this profile has
        // never played", not "wants a title reset".
        bool ProfileIsNew(const BrnProgression::Profile* lpProfile)
        {
            return lpProfile->GetIsNewProfile();
        }
    }

    // @ 0x82066680 (.rdata, read from the image): the 30 observed event ids, in table
    // order. Update also carries a defensive case for id 3 (ignored) that is NOT in the
    // registered set.
    const s32 InGame::maiEventToObserve[30] =
    {
        2,                              // per-frame tick (ignored)
        KI_EVENT_CONTROLLER,            // 6
        KI_EVENT_PAD_DISCONNECTED,      // 9
        50,                             // invite join go-ahead -> ENTER_GAME
        44,                             // network in-game failed -> "OnLostConn"
        KI_EVENT_GUI_CACHE,             // 64
        228,                            // open-main-map request
        229,                            // car-select request -> "TO_CSELECT"
        134,                            // loading-screen handshake -> command 135
        136,                            // world reload request -> "START_LOAD"
        322,                            // entering-online state -> "TO_GAME_ROOM"
        93,                             // game-mode update -> "ENTER_GAME" (lobby/showtime)
        320,                            // online event finished -> "TO_ST_POST"/"TO_ON_POST"
        291,                            // offline event finished -> "TO_ST_POST"/"TO_OFF_POST"
        288,                            // return to title -> "TO_INTRO"
        81,                             // car select/unlock -> "TO_CUNLOCK"/"TO_CSELECT"
        75,                             // car unlock -> "TO_CUNLOCK"
        KI_EVENT_NETWORK_SPLASH,        // 269
        KI_EVENT_OVERLAY_COMPLETE,      // 189
        133,                            // invite failed -> "GMInvSmGame"
        271,                            // accept -> "ACCEPT"
        516,                            // UI-visible (system guide) update
        511,                            // video request -> "TO_VIDEO"
        132,                            // invite complete -> network suspension release
        350,                            // profile pointer
        KI_EVENT_PERFORM_MENU_OPTION,   // 284
        373,                            // rival event finished -> "TO_RVL_POST"
        375,                            // arm the trophy-car-unlock countdown
        285,                            // instant-freeburn search fail
        309,                            // arm the completion-sequence countdown
    };
    const s32 InGame::miNumEventsObserved = 30;   // @ 0x820666F8

    // @ 0x82F272A4 (.data, read from the image): option -> screen-flow state-event
    // string (DWARF BrnInGame.cpp:66).
    const char* const InGame::KAPC_MAIN_MENU_STATE_ACTIONS_TEXT[13] =
    {
        "TO_FBURN_QK",    // E_MAIN_MENU_OPTIONS_FREEBURN_PLAY_NOW
        "TO_FBURN_CU",    // E_MAIN_MENU_OPTIONS_FREEBURN_CUSTOM_MATCH
        "TO_FBURN_CR",    // E_MAIN_MENU_OPTIONS_FREEBURN_CREATE
        "TO_IMG_GAL",     // E_MAIN_MENU_OPTIONS_IMAGE_GALLERY
        "TO_VIW_CHL",     // E_MAIN_MENU_OPTIONS_VIEW_CHALLENGES
        "TO_UNRANK_QK",   // E_MAIN_MENU_OPTIONS_UNRANKED_PLAY_NOW
        "TO_UNRANK_CU",   // E_MAIN_MENU_OPTIONS_UNRANKED_CUSTOM_MATCH
        "TO_UNRANK_CR",   // E_MAIN_MENU_OPTIONS_UNRANKED_CREATE
        "TO_RANKED_QK",   // E_MAIN_MENU_OPTIONS_RANKED_PLAY_NOW
        "TO_RANKED_CU",   // E_MAIN_MENU_OPTIONS_RANKED_CUSTOM_MATCH
        "TO_RANKED_CR",   // E_MAIN_MENU_OPTIONS_RANKED_CREATE
        "TO_SCOREB",      // E_MAIN_MENU_OPTIONS_SCOREBOARDS
        "TO_NEWS",        // E_MAIN_MENU_OPTIONS_NEWS
    };

    // @ 0x824B8D98 -- base construct, then zero the sequence timers + the disconnect
    // counter (OnEnter re-seeds the rest of the members).
    void InGame::Construct(CgsID lId, CgsFsm::ScriptedFsm* lpFsm)
    {
        CgsGui::State::Construct(lId, lpFsm);
        mfTimeUntilTrophyCarUnlockSeq = 0.0f;
        miNumberOfIgnoredDisconnects  = 0;
        mfTimeUntilCompletionSeq      = 0.0f;
    }

    // @ 0x824D0498 -- register the 30-event table, reset the per-visit members, bring
    // the HUD components up, reset the view state, activate the CrashNav flow, post the
    // in-game entry commands and register the wait-finish handshake for every overlay
    // that must fully hide before the flow moves on.
    void InGame::OnEnter()
    {
        mpStateInterface->RegisterForEvents(maiEventToObserve, miNumEventsObserved);

        mfTimeUntilNextEATrack          = 0.0f;
        mfTimeToDisableNextEATrack      = 0.0f;
        mbIsInEventStartLocation        = false;
        mbIsGuideVisible                = false;
        meSelectedOnlineMainMenuOption  = E_MAIN_MENU_OPTIONS_COUNT;
        mpGuiCache                      = 0;
        mpProfile                       = 0;

        // { 1, 148, 12, flag=1 } on the internal channel -- HUD components up (the
        // flag=0 twin is ShutDownHudComponents).
        PostCommand16<148>(mpStateInterface, KI_CHANNEL_GUI_INTERNAL, 1);

        // The view-channel player-image CLEAR: GuiEventNetworkPlayerImage { null, -1 } on
        // channel 41, i.e. "no picture for any slot" -- NetworkPlayerImageRenderer::RecvEvent
        // @0x82449CA0 case 258 sees mpTexture == 0 AND miTextureIndex == -1, so
        // mbRenderTexture is false and it arms the 3-frame clear countdown. The console
        // builds the record inline at 0x824D0518..0x824D0554 (see the note where the old
        // two-word helper stood); OutputViewState<T> builds the identical wrapper at host
        // width, which is the whole point of using it here.
        GuiEventNetworkPlayerImageWire lViewReset(0, -1);
        mpStateInterface->GetOutputEventQueue()->AddEvent(
            reinterpret_cast<const CgsModule::Event*>(&lViewReset), KI_CHANNEL_VIEW_STATE,
            static_cast<s32>(sizeof(lViewReset)));

        // { 8, 191, 12, 1, 0 } -- activate the CrashNav (front-end map) flow.
        GuiEventActivateCrashNav lActivateCrashNav(true);
        mpStateInterface->GetOutputEventQueue()->AddEvent(
            reinterpret_cast<const CgsModule::Event*>(&lActivateCrashNav), KI_CHANNEL_GUI_OUT,
            static_cast<s32>(sizeof(GuiEventActivateCrashNav)));

        PostCommand16<261>(mpStateInterface, KI_CHANNEL_GUI_OUT);
        PostCommand16<145>(mpStateInterface, KI_CHANNEL_GUI_OUT);
        PostCommand16<65>(mpStateInterface, KI_CHANNEL_GUI_OUT, 1);

        // The wait-finish registrations: each overlay that must finish hiding before
        // its flow transition proceeds (X360 posts the 24-byte 188 record per name).
        PostOverlayWaitFinishRequest(mpStateInterface, "CNOnlLvgGame");
        PostOverlayWaitFinishRequest(mpStateInterface, "CNOnlLvGmQn");
        PostOverlayWaitFinishRequest(mpStateInterface, "CNOnlLvChaQn");
        PostOverlayWaitFinishRequest(mpStateInterface, "GMOnlLvGmQn");
        PostOverlayWaitFinishRequest(mpStateInterface, "CNOnlEntGame");
        PostOverlayWaitFinishRequest(mpStateInterface, "CNOnlLchGame");
        PostOverlayWaitFinishRequest(mpStateInterface, "CNOnlLchGmH");
        PostOverlayWaitFinishRequest(mpStateInterface, "OnHReturnOn");
        PostOverlayWaitFinishRequest(mpStateInterface, "OnCReturnOn");
        PostOverlayWaitFinishRequest(mpStateInterface, "OnHEnterOn");
        PostOverlayWaitFinishRequest(mpStateInterface, "OnCEnterOn");

        if (LoseDiagLine())
            *CgsDev::Log::gpDebugPrint << "[lose-diag] InGame entered [FLAG PC witness]\n";
    }

    // @ 0x824B8DE0
    void InGame::OnLeave()
    {
        mpStateInterface->UnRegisterForEvents(maiEventToObserve, miNumEventsObserved);

        if (LoseDiagLine())
        {
            *CgsDev::Log::gpDebugPrint << "[lose-diag] InGame left via \"" << GetPendingEventName()
                                       << "\" (gameMode "
                                       << (mpGuiCache != 0 ? mpGuiCache->GetGameMode() : -2)
                                       << ") [FLAG PC witness]\n";
        }
    }

    // @ the ICF fold 0x825011B0 (== BrnGui::Video::GetResourcesToLoad): only the count
    // is zeroed; the tuple out-pointer is deliberately left untouched.
    void InGame::GetResourcesToLoad(const CgsGui::sResourceTuple** /*lppResourceTuples*/,
                                    u32* lpuNumberOfResources) const
    {
        *lpuNumberOfResources = 0;
    }

    // @ 0x824E0468 -- gate on the cache + the input-suppression byte, then dispatch the
    // action sub-id. The X360 in-game action ids are kept verbatim (none of them is the
    // menu accept action, so the PC dual-accept mapping does not apply here).
    void InGame::HandleControllerInput(const CgsModule::Event* lpEvent)
    {
        if (mpGuiCache == 0 || CacheIsInputSuppressed(mpGuiCache))
            return;

        const s32 liAction = *reinterpret_cast<const s32*>(
            reinterpret_cast<const u8*>(lpEvent) + 4);
        switch (liAction)
        {
        case KI_ACTION_GUI_START:
            PauseGame(true, true);
            break;

        case KI_ACTION_GUI_BACK:
            PauseGame(true, false);
            break;

        case KI_ACTION_GUI_LSHOULDER:
            mfTimeToDisableNextEATrack = KF_EA_TRAX_DEBOUNCE;
            break;

        case KI_ACTION_GUI_RSHOULDER:
            if (mfTimeUntilNextEATrack <= 0.0f)
                mfTimeUntilNextEATrack = KF_EA_TRAX_DEBOUNCE;
            break;

        case KI_ACTION_GUI_EVENT_DETAILS:
            OpenEventMap();
            break;

        default:
            break;
        }
    }

    // @ 0x824D08C0 -- DWARF param: const GuiEventNetworkSplashEvent* (the payload's
    // ESplashState word leads).
    void InGame::HandleSplashScreenRequests(const CgsModule::Event* lpNetworkSplashEvent)
    {
        CGS_ASSERT(lpNetworkSplashEvent != 0, "lpNetworkSplashEvent");   // cpp:851

        const u32 luSplashState = *reinterpret_cast<const u32*>(lpNetworkSplashEvent);
        if (luSplashState == KU_SPLASH_STATE_SHOW)
        {
            CGS_ASSERT(mpGuiCache != 0, "mpGuiCache");                   // cpp:862
            const s32 liGameModeType = mpGuiCache->GetGameMode();
            // X360 bounds: > -1 (E_MODE_NONE) and < 18 (its E_MODE_COUNT -- one mode
            // more than the committed DecFIGS enum's 17; named form kept).
            CGS_ASSERT(liGameModeType > BrnGameState::GameStateModuleIO::E_MODE_NONE,
                       "leGameModeType > GsmIO::E_MODE_NONE");           // cpp:864
            CGS_ASSERT(liGameModeType < BrnGameState::GameStateModuleIO::E_MODE_COUNT + 1,
                       "leGameModeType < GsmIO::E_MODE_COUNT");          // cpp:865

            const char* lpcSplashScreenID = GetSplashScreenIDForGameMode(
                static_cast<BrnGameState::GameStateModuleIO::EGameModeType>(liGameModeType));
            CGS_ASSERT(lpcSplashScreenID != 0, "lpcSplashScreenID != NULL");   // cpp:870
            PostOverlayRequest(mpStateInterface, lpcSplashScreenID);
        }
        else if (luSplashState == KU_SPLASH_STATE_STOP)
        {
            const s32 liGameModeType = mpGuiCache->GetGameMode();
            if (liGameModeType == BrnGameState::GameStateModuleIO::E_MODE_ONLINE_FREE_BURN_LOBBY ||
                liGameModeType == BrnGameState::GameStateModuleIO::E_MODE_ONLINE_SHOWTIME)
            {
                PostOverlayWaitFinishRequest(mpStateInterface, "OnSplshFreeB");
            }
        }
    }

    // @ 0x824DA350 -- DWARF param: const GuiEventPerformOnlineMainMenuOption*. Privilege
    // check first; a join option picked while offline-but-in-a-mode raises the
    // "CNOnlStrtQn" (leave the current game?) question and parks the option for the
    // overlay-complete handshake.
    void InGame::HandlePerformOnlineMainMenuOption(const CgsModule::Event* lpEvent)
    {
        const EMainMenuOptions leOption =
            reinterpret_cast<const GuiEventMainMenuOptionPayload*>(lpEvent)->meMainMenuOption;
        if (std::getenv("BRN_EASYDRIVE_TRACE") && CgsDev::Log::gpDebugPrint)
            *CgsDev::Log::gpDebugPrint << "[easydrive-command] main option " << static_cast<s32>(leOption) << "\n";


        if (!CheckPrivileges(leOption))
        {
            PostOverlayRequest(mpStateInterface, "CNOnlPrivErr");
            return;
        }

        CGS_ASSERT(mpGuiCache != 0, "mpGuiCache");   // cpp:919

        // The non-join options (gallery / challenges / scoreboards / news) go straight
        // through.
        const bool lbJoinOption =
            leOption <= E_MAIN_MENU_OPTIONS_FREEBURN_CREATE ||
            (leOption >= E_MAIN_MENU_OPTIONS_UNRANKED_PLAY_NOW &&
             leOption <= E_MAIN_MENU_OPTIONS_RANKED_CREATE);
        if (!lbJoinOption)
        {
            SelectOnlineMenuOption(leOption);
            return;
        }

        if (!mpGuiCache->IsOnline() &&
            mpGuiCache->GetGameMode() != BrnGameState::GameStateModuleIO::E_MODE_NONE)
        {
            PostOverlayRequest(mpStateInterface, "CNOnlStrtQn");
            meSelectedOnlineMainMenuOption = leOption;
        }
        else
        {
            SelectOnlineMenuOption(leOption);
        }
    }

    // @ 0x824D0A38 -- the instant-freeburn search failed: raise the "GMSrchFail"
    // overlay (its OK completion retries as a freeburn CREATE -- see
    // HandleOverlayComplete).
    void InGame::HandleInstantFreeburnSearchFail()
    {
        PostOverlayRequest(mpStateInterface, "GMSrchFail");
    }

    // @ 0x824DA4C8 -- DWARF param: const GuiOverlayCompleteEvent* (payload: id @+0,
    // leave method @+8).
    void InGame::HandleOverlayComplete(const CgsModule::Event* lpOverlayCompleteEvent)
    {
        CGS_ASSERT(lpOverlayCompleteEvent != 0, "lpOverlayCompleteEvent");   // cpp:982
        CGS_ASSERT(mpGuiCache != 0, "mpGuiCache");                           // cpp:984

        const GuiOverlayCompletePayload* lpComplete =
            reinterpret_cast<const GuiOverlayCompletePayload*>(lpOverlayCompleteEvent);

        if (lpComplete->mOverlayId == CgsIDCompress("CNOnlStrtQn") &&
            lpComplete->miLeaveMethod == GuiOverlayCompleteEvent::E_LEAVEMETHOD_OK)
        {
            // The "leave the current game?" question was accepted: run the parked option.
            SelectOnlineMenuOption(meSelectedOnlineMainMenuOption);
        }
        else if (lpComplete->mOverlayId == CgsIDCompress("GMSrchFail") &&
                 lpComplete->miLeaveMethod == GuiOverlayCompleteEvent::E_LEAVEMETHOD_OK)
        {
            // Search-fail acknowledged: retry as "create your own freeburn".
            GuiEventMainMenuOptionPayload lRetry;
            lRetry.meMainMenuOption = E_MAIN_MENU_OPTIONS_FREEBURN_CREATE;
            HandlePerformOnlineMainMenuOption(
                reinterpret_cast<const CgsModule::Event*>(&lRetry));
        }
        else
        {
            const s32 liGameModeType = mpGuiCache->GetGameMode();
            if ((liGameModeType == BrnGameState::GameStateModuleIO::E_MODE_ONLINE_FREE_BURN_LOBBY ||
                 liGameModeType == BrnGameState::GameStateModuleIO::E_MODE_ONLINE_SHOWTIME) &&
                lpComplete->mOverlayId == CgsIDCompress("OnSplshFreeB"))
            {
                GuiNetworkSplashWire16 lFinished(KU_SPLASH_STATE_FINISHED);
                mpStateInterface->GetOutputEventQueue()->AddEvent(
                    reinterpret_cast<const CgsModule::Event*>(&lFinished), KI_CHANNEL_GUI_OUT, 16);
            }
        }
    }

    // @ 0x824DEFE8 -- online pauses go to the online pause screen; offline "pauses" open
    // the driver details or the main map. (The X360 never reads the first parameter --
    // it is kept for the DWARF signature.)
    void InGame::PauseGame(bool /*lbUserInstigated*/, bool lbOpenDriverDetails)
    {
        CGS_ASSERT(mpGuiCache != 0, "mpGuiCache");   // cpp:1038

        if (!PauseAllowed())
            return;

        if (mpGuiCache->IsOnline())
        {
            if (!CacheFarPauseGateA(mpGuiCache))
                SendStateEvent("ON_PAUSE");
        }
        else if (lbOpenDriverDetails)
        {
            OpenDriverDetails();
        }
        else
        {
            OpenMainMap();
        }
    }

    // @ 0x824B8DF8 -- pausing is blocked by the far pause gates, the mugshot capture and
    // the junkyard, and requires every GUI flow layer's apt components initialised.
    bool InGame::PauseAllowed()
    {
        CGS_ASSERT(mpGuiCache != 0, "mpGuiCache");   // cpp:1096

        if (CacheFarPauseGateA(mpGuiCache) || CacheIsMugshotActive(mpGuiCache) ||
            CacheIsInputSuppressed(mpGuiCache) || CacheFarPauseGateB(mpGuiCache) ||
            CacheIsInJunkyard(mpGuiCache))
        {
            return false;
        }

        // Walk the three flow layers (the X360 drives the GuiFlow post-increment helper
        // @0x824B2E98 over SCREEN/HUD/OVERLAY).
        GuiFlow leFlow = E_GUIFLOW_FIRST;
        while (mpGuiCache->AreAllAptComponentsInitialised(leFlow))
        {
            leFlow = static_cast<GuiFlow>(leFlow + 1);
            if (leFlow >= E_GUIFLOW_COUNT)
                return true;
        }
        return false;
    }

    // @ 0x824DA610 -- shut the HUD components down (the {1,148,12,0} internal command)
    // and hand the flow to the main map.
    void InGame::OpenMainMap()
    {
        PostCommand16<148>(mpStateInterface, KI_CHANNEL_GUI_INTERNAL, 0);
        SendStateEvent("MAP_MAIN");
    }

    // @ 0x824DA680 -- as OpenMainMap, but only when standing at an event start location.
    void InGame::OpenEventMap()
    {
        if (!mbIsInEventStartLocation)
            return;
        PostCommand16<148>(mpStateInterface, KI_CHANNEL_GUI_INTERNAL, 0);
        SendStateEvent("MAP_EVENT");
    }

    // @ 0x824DA700 -- as OpenMainMap, into the driver-details screen.
    void InGame::OpenDriverDetails()
    {
        PostCommand16<148>(mpStateInterface, KI_CHANNEL_GUI_INTERNAL, 0);
        SendStateEvent("TO_D_DETAIL");
    }

    // @ 0x824D0AB0 -- the {1,148,12,0} internal command (flag=0 == shut down).
    void InGame::ShutDownHudComponents()
    {
        PostCommand16<148>(mpStateInterface, KI_CHANNEL_GUI_INTERNAL, 0);
    }

    // @ 0x824B8EF8 -- the non-network options (gallery / challenges / scoreboards /
    // news) are always allowed; the join options need the multiplayer privilege.
    bool InGame::CheckPrivileges(EMainMenuOptions leMainMenuOption)
    {
        CGS_ASSERT(mpGuiCache != 0, "mpGuiCache");   // cpp:1253

        const bool lbMultiplayerAllowed = mpGuiCache->IsMultiplayerAllowed();
        switch (leMainMenuOption)
        {
        case E_MAIN_MENU_OPTIONS_FREEBURN_PLAY_NOW:
        case E_MAIN_MENU_OPTIONS_FREEBURN_CUSTOM_MATCH:
        case E_MAIN_MENU_OPTIONS_FREEBURN_CREATE:
        case E_MAIN_MENU_OPTIONS_UNRANKED_PLAY_NOW:
        case E_MAIN_MENU_OPTIONS_UNRANKED_CUSTOM_MATCH:
        case E_MAIN_MENU_OPTIONS_UNRANKED_CREATE:
        case E_MAIN_MENU_OPTIONS_RANKED_PLAY_NOW:
        case E_MAIN_MENU_OPTIONS_RANKED_CUSTOM_MATCH:
        case E_MAIN_MENU_OPTIONS_RANKED_CREATE:
            return lbMultiplayerAllowed;

        case E_MAIN_MENU_OPTIONS_IMAGE_GALLERY:
        case E_MAIN_MENU_OPTIONS_VIEW_CHALLENGES:
        case E_MAIN_MENU_OPTIONS_SCOREBOARDS:
        case E_MAIN_MENU_OPTIONS_NEWS:
            return true;

        default:
            CGS_ASSERT(false, "Invalid menu option");   // cpp:1289
            return false;
        }
    }

    // @ 0x824D0B08 -- fire the option's screen-flow state event, record the ranked /
    // freeburn join intent on the cache for the join options (plus command 268), and
    // mark the easy-drive entry.
    void InGame::SelectOnlineMenuOption(EMainMenuOptions leMainMenuOption)
    {
        // The X360 streams "Invalid Cache pointer selecting an online menu(<option>)"
        // into the assert buffer; the plain condition string is kept per policy.
        CGS_ASSERT(mpGuiCache != 0, "Invalid Cache pointer selecting an online menu");   // cpp:1308

        SendStateEvent(KAPC_MAIN_MENU_STATE_ACTIONS_TEXT[leMainMenuOption]);

        bool lbJoinRequest = true;
        switch (leMainMenuOption)
        {
        case E_MAIN_MENU_OPTIONS_FREEBURN_PLAY_NOW:
        case E_MAIN_MENU_OPTIONS_FREEBURN_CUSTOM_MATCH:
        case E_MAIN_MENU_OPTIONS_FREEBURN_CREATE:
            mpGuiCache->SetDoJoinOnlineRankedGame(false);
            mpGuiCache->SetDoJoinOnlineFreeburnGame(true);
            break;

        case E_MAIN_MENU_OPTIONS_UNRANKED_PLAY_NOW:
        case E_MAIN_MENU_OPTIONS_UNRANKED_CUSTOM_MATCH:
        case E_MAIN_MENU_OPTIONS_UNRANKED_CREATE:
            mpGuiCache->SetDoJoinOnlineRankedGame(false);
            mpGuiCache->SetDoJoinOnlineFreeburnGame(false);
            break;

        case E_MAIN_MENU_OPTIONS_RANKED_PLAY_NOW:
        case E_MAIN_MENU_OPTIONS_RANKED_CUSTOM_MATCH:
        case E_MAIN_MENU_OPTIONS_RANKED_CREATE:
            mpGuiCache->SetDoJoinOnlineRankedGame(true);
            mpGuiCache->SetDoJoinOnlineFreeburnGame(false);
            break;

        default:   // gallery / challenges / scoreboards / news: no join bookkeeping
            lbJoinRequest = false;
            break;
        }

        if (lbJoinRequest)
        {
            mpGuiCache->SetResetOnlineGameOptions(true);
            PostCommand16<268>(mpStateInterface, KI_CHANNEL_GUI_OUT);
        }

        CacheSetEnteredOnlineViaEasyDrive(mpGuiCache);
    }

    // @ 0x824E0ED0 -- two-pass in-queue drain (cache latch, then the 30-event dispatch),
    // then the per-frame tails: the trophy-unlock / completion countdowns, the
    // event-start-location gate, the EA-TRAX debounce, the profile title-reset gate and
    // the guide-forced pause.
    void InGame::Update()
    {
        StateInputQueue* lpInQueue = reinterpret_cast<StateInputQueue*>(mpInGuiEventQueue);
        const CgsModule::Event* lpEvent = 0;
        s32 liSize = 0;

        // ---- pass 1: latch the GuiCache pointer (only while unset) and surface a
        //      pending lobby-disconnect overlay off the freshly-arrived cache ----------
        if (mpGuiCache == 0)
        {
            for (s32 liEventId = lpInQueue->GetFirstEvent(&lpEvent, &liSize);
                 lpEvent != 0;
                 liEventId = lpInQueue->GetNextEvent(lpEvent, &lpEvent, &liSize))
            {
                if (liEventId != KI_EVENT_GUI_CACHE)
                    continue;

                const GuiEventCache* lpCacheEvent =
                    reinterpret_cast<const GuiEventCache*>(lpEvent);
                // The X360 streams "Invalid gui cached" into the assert buffer (cpp:239).
                CGS_ASSERT(lpCacheEvent->mpGuiCache != 0, "Invalid gui cached");
                mpGuiCache = lpCacheEvent->mpGuiCache;

                const s32 liDisconnectError = mpGuiCache->GetDoDisconnectPopupError();   // lwz +0x4B40
                if (liDisconnectError != 0)
                {
                    PostOverlayRequest(mpStateInterface,
                                       liDisconnectError == KI_SERVER_ERROR_LOBBY_DISCONNECT_D
                                           ? "CNLobbyDiscD" : "CNLobbyDisc");
                    mpGuiCache->SetDoDisconnectPopup(0);                                 // stw 0, +0x4B40
                }
            }
        }

        CGS_ASSERT(mpGuiCache != 0, "mpGuiCache");   // cpp:275

        const char* lpacPostEventStateEvent = 0;   // [FLAG PC witness] BRN_LOSE_DIAG only

        // ---- pass 2: the full dispatch ---------------------------------------------
        for (s32 liEventId = lpInQueue->GetFirstEvent(&lpEvent, &liSize);
             lpEvent != 0;
             liEventId = lpInQueue->GetNextEvent(lpEvent, &lpEvent, &liSize))
        {
            switch (liEventId)
            {
            case 2:
            case 3:                      // defensive (id 3 is not in the registered set)
            case KI_EVENT_GUI_CACHE:     // consumed by pass 1
                break;

            case KI_EVENT_CONTROLLER:
                if (!mpGuiCache->IsPreparingForInvite() &&
                    !mpGuiCache->IsPerformInviteReceived())
                {
                    HandleControllerInput(lpEvent);
                }
                break;

            case KI_EVENT_PAD_DISCONNECTED:
                if (!mpGuiCache->IsOnline() && PauseAllowed())
                {
                    ++miNumberOfIgnoredDisconnects;
                    if (miNumberOfIgnoredDisconnects > KI_NUMBER_OF_DISCONNECTS_TO_IGNORE)
                    {
                        PauseGame(false, false);
                        miNumberOfIgnoredDisconnects = 0;
                    }
                }
                break;

            case 44:   // network in-game failed (the DWARF HandleInGameFailedEvent body,
                       // inlined here by the X360 build)
                CGS_ASSERT(mpGuiCache != 0, "mpGuiCache");   // cpp:568
                if (mpGuiCache->IsOnline())
                    PostOverlayRequest(mpStateInterface, "OnLostConn");
                break;

            case 50:   // invite join go-ahead
                if (mpGuiCache->IsPerformInviteReceived())
                {
                    mpGuiCache->ClearExpectedAptComponentList(E_GUIFLOW_SCREEN);
                    SendStateEvent("ENTER_GAME");
                }
                break;

            case 75:
                ShutDownHudComponents();
                SendStateEvent("TO_CUNLOCK");
                break;

            case 81:   // car select/unlock request (payload word: 1 == go)
                if (*reinterpret_cast<const s32*>(lpEvent) != 1)
                    break;
                CGS_ASSERT(mpGuiCache != 0, "mpGuiCache");   // cpp:378
                // GuiCache::mbIsInEvent (the committed accessor named it from its
                // road-rule consumer).
                if (mpGuiCache->GetInEventColouringGate())
                    break;
                ShutDownHudComponents();
                SendStateEvent(mpGuiCache->IsJunkyardCarUnlockPending() ? "TO_CUNLOCK"
                                                                   : "TO_CSELECT");
                break;

            case 93:   // game-mode update (the mode word rides @+12)
            {
                const s32 liGameModeType =
                    *reinterpret_cast<const s32*>(reinterpret_cast<const u8*>(lpEvent) + 12);
                if ((liGameModeType == BrnGameState::GameStateModuleIO::E_MODE_ONLINE_FREE_BURN_LOBBY ||
                     liGameModeType == BrnGameState::GameStateModuleIO::E_MODE_ONLINE_SHOWTIME) &&
                    !mpGuiCache->IsStartingGameDueToPlayerJoin())
                {
                    SendStateEvent("ENTER_GAME");
                }
                break;
            }

            case 132:  // invite complete (payload word 0 == lift the network suspension)
                CGS_ASSERT(lpEvent != 0, "lpInviteCompleteEvent");   // cpp:587
                if (*reinterpret_cast<const u32*>(lpEvent) == 0)
                {
                    CgsGui::GuiEventNetworkSuspension lSuspension(false);
                    mpStateInterface->OutputGuiEvent(lSuspension);
                }
                break;

            case 133:  // invite failed (payload word 1 == the target game is smaller)
                CGS_ASSERT(lpEvent != 0, "lpInviteFailedEvent");     // cpp:534
                if (*reinterpret_cast<const u32*>(lpEvent) == 1)
                    PostOverlayRequest(mpStateInterface, "GMInvSmGame");
                break;

            case 134:  // loading-screen handshake -> command 135
                PostCommand16<135>(mpStateInterface, KI_CHANNEL_GUI_OUT);
                break;

            case 136:
                SendStateEvent("START_LOAD");
                break;

            case KI_EVENT_OVERLAY_COMPLETE:
                HandleOverlayComplete(lpEvent);
                break;

            case 228:  // open-main-map request (state event first on the X360, then the
                       // HUD shutdown command -- kept in that order)
                SendStateEvent("MAP_MAIN");
                PostCommand16<148>(mpStateInterface, KI_CHANNEL_GUI_INTERNAL, 0);
                break;

            case 229:
                SendStateEvent("TO_CSELECT");
                break;

            case KI_EVENT_NETWORK_SPLASH:
                HandleSplashScreenRequests(lpEvent);
                break;

            case 271:
                SendStateEvent("ACCEPT");
                break;

            case KI_EVENT_PERFORM_MENU_OPTION:
                HandlePerformOnlineMainMenuOption(lpEvent);
                break;

            case 285:
                HandleInstantFreeburnSearchFail();
                break;

            case 288:  // back to the title flow
                ShutDownHudComponents();
                SendStateEvent("TO_INTRO");
                break;

            case 291:  // offline event finished
            {
                CGS_ASSERT(mpGuiCache != 0, "mpGuiCache");                        // cpp:461
                CGS_ASSERT(mpGuiCache->GetGuiTracker() != 0, "mpGuiCache->GetGuiTracker()");   // cpp:462
                mpGuiCache->GetGuiTracker()->ClearTracker();
                const s32 liGameModeType = mpGuiCache->GetGameMode();
                const bool lbShowtime =
                    liGameModeType == BrnGameState::GameStateModuleIO::E_MODE_OFFLINE_SHOWTIME ||
                    liGameModeType == BrnGameState::GameStateModuleIO::E_MODE_ONLINE_SHOWTIME;
                SendStateEvent(lbShowtime ? "TO_ST_POST" : "TO_OFF_POST");
                lpacPostEventStateEvent = lbShowtime ? "TO_ST_POST" : "TO_OFF_POST";

                // [FLAG PC harness] BRN_LOSE_PAUSE_WITH_291=map|driver -- NOT A CONSOLE PATH.
                // Replays a player's Back (map) or Start (driver details) press that reaches
                // this state in the same update as GUI 291, through the console's own
                // PauseGame. One-shot. OFF unless the env var is set.
                {
                    static const char* const spcPauseWith291 = std::getenv("BRN_LOSE_PAUSE_WITH_291");
                    static bool              sbFired         = false;
                    if (spcPauseWith291 != 0 && !sbFired)
                    {
                        sbFired = true;
                        const bool lbDriverDetails = std::strcmp(spcPauseWith291, "driver") == 0;
                        if (CgsDev::Log::gpDebugPrint != 0)
                        {
                            *CgsDev::Log::gpDebugPrint
                                << "[lose-diag] HARNESS PAUSE WITH GUI 291 ("
                                << (lbDriverDetails ? "driver" : "map")
                                << ") -> InGame::PauseGame [FLAG PC harness]\n";
                        }
                        PauseGame(true, lbDriverDetails);
                    }
                }
                break;
            }

            case 309:  // arm the completion-sequence countdown (payload bytes {1, 0})
                if (reinterpret_cast<const u8*>(lpEvent)[0] == 1 &&
                    reinterpret_cast<const u8*>(lpEvent)[1] == 0)
                {
                    mfTimeUntilCompletionSeq = KF_TIME_UNTIL_COMPLETION_SEQUENCE;
                }
                break;

            case 320:  // online event finished
            {
                CGS_ASSERT(mpGuiCache != 0, "mpGuiCache");                        // cpp:443
                CGS_ASSERT(mpGuiCache->GetGuiTracker() != 0, "mpGuiCache->GetGuiTracker()");   // cpp:444
                mpGuiCache->GetGuiTracker()->ClearTracker();
                const s32 liGameModeType = mpGuiCache->GetGameMode();
                const bool lbShowtime =
                    liGameModeType == BrnGameState::GameStateModuleIO::E_MODE_OFFLINE_SHOWTIME ||
                    liGameModeType == BrnGameState::GameStateModuleIO::E_MODE_ONLINE_SHOWTIME;
                SendStateEvent(lbShowtime ? "TO_ST_POST" : "TO_ON_POST");
                break;
            }

            case 322:  // entering-online state (payload byte @+9 == proceed)
                // The X360 streams the message through StrStream (cpp:418); plain form kept.
                CGS_ASSERT(mpGuiCache != 0, "INVALID MPGUICACHE IN INGAME::UPDATE");
                if (mpGuiCache->IsOnline() &&
                    reinterpret_cast<const u8*>(lpEvent)[9] != 0)
                {
                    SendStateEvent("TO_GAME_ROOM");
                }
                break;

            case 350:  // the profile object arrives by pointer
                mpProfile = reinterpret_cast<const GuiEventProfilePointer*>(lpEvent)->mpProfile;
                break;

            case 373:  // rival event finished
                ShutDownHudComponents();
                mpGuiCache->GetGuiTracker()->ClearTracker();
                SendStateEvent("TO_RVL_POST");
                break;

            case 375:  // arm the trophy-car-unlock countdown
                mfTimeUntilTrophyCarUnlockSeq = KF_TIME_UNTIL_TROPHY_CAR_UNLOCK_SEQUENCE;
                break;

            case 511:
                SendStateEvent("TO_VIDEO");
                break;

            case 516:  // UI-visible update: the guide is up while the UI is NOT visible
                CGS_ASSERT(lpEvent != 0, "lpUiVisibleEvent != NULL");   // cpp:315
                mbIsGuideVisible = (*reinterpret_cast<const u32*>(lpEvent) == 0);
                break;

            default:
                CGS_ASSERT(false, "Unexpected event in InGame::Update");   // cpp:624
                break;
            }
        }

        // ---- the sequence countdowns (trophy unlock outranks completion; both only
        //      tick outside a game mode and reset when one starts) --------------------
        if (mfTimeUntilTrophyCarUnlockSeq > 0.0f)
        {
            if (mpGuiCache->GetGameMode() == BrnGameState::GameStateModuleIO::E_MODE_NONE)
            {
                mfTimeUntilTrophyCarUnlockSeq -= mpGuiCache->GetTimeStep();
                if (mfTimeUntilTrophyCarUnlockSeq <= 0.0f)
                {
                    ShutDownHudComponents();
                    mpGuiCache->GetGuiTracker()->ClearTracker();
                    SendStateEvent("TO_TRPHY_UNL");
                }
            }
            else
            {
                mfTimeUntilTrophyCarUnlockSeq = 0.0f;
            }
        }
        else if (mfTimeUntilCompletionSeq > 0.0f)
        {
            if (mpGuiCache->GetGameMode() == BrnGameState::GameStateModuleIO::E_MODE_NONE)
            {
                mfTimeUntilCompletionSeq -= mpGuiCache->GetTimeStep();
                if (mfTimeUntilCompletionSeq <= 0.0f)
                {
                    ShutDownHudComponents();
                    mpGuiCache->GetGuiTracker()->ClearTracker();
                    SendStateEvent("TO_COMPLETED");
                }
            }
            else
            {
                mfTimeUntilCompletionSeq = 0.0f;
            }
        }

        // ---- the event-map gate: standing at an event start location? ---------------
        mbIsInEventStartLocation =
            (CacheGetCurrentLandmarkIndex(mpGuiCache) != KI_NO_EVENT_START_LANDMARK);

        // ---- the EA-TRAX next-track debounce ----------------------------------------
        if (mfTimeToDisableNextEATrack > 0.0f)
        {
            mfTimeUntilNextEATrack      = 0.0f;
            mfTimeToDisableNextEATrack -= mpGuiCache->GetTimeStep();
        }
        else if (mfTimeUntilNextEATrack > 0.0f)
        {
            mfTimeUntilNextEATrack -= mpGuiCache->GetTimeStep();
            if (mfTimeUntilNextEATrack <= 0.0f)
                PostCommand16<461>(mpStateInterface, KI_CHANNEL_GUI_OUT);
        }

        // ---- the first-boot intro gate (X360 Update tail: `lwz mpProfile` ->
        //      `lbz +118033` -> SendStateEvent("TO_INTRO") + command 476) ---------------
        if (mpProfile != 0 && ProfileIsNew(mpProfile))
        {
            SendStateEvent("TO_INTRO");
            PostCommand16<476>(mpStateInterface, KI_CHANNEL_GUI_OUT);
        }

        // ---- the system guide forces the pause path ----------------------------------
        if (mbIsGuideVisible)
            PauseGame(false, false);

        // ---- FLAG PC fix (issue #32), NOT IN THE CONSOLE: re-open a results screen that never
        //      opened. GUI 291 is one-shot and only InGame observes it. If a pause request
        //      (Back -> map, Start -> driver details) takes the screen flow out of InGame in the
        //      update 291 arrives, or in the few updates between the finish and 291, the map /
        //      driver-details state drops it, the results screen never opens, so no GUI 292 and
        //      no game event 26 ever leave the GUI: the mode sits in RESULTS forever with the AI
        //      driving the player's car (ShowModeResults' action 7). The console has the same
        //      hole for a press landing before 291 (its pause gate does not look at the mode
        //      state either). Recovery: while InGame is up, an offline (non-showtime) mode is
        //      still running and the cache still holds that mode's un-dismissed results record
        //      (GUI 289 sets it, the results screen's own GUI 292 clears it), send the transition
        //      291 would have sent. The 60-update hold keeps clear of the normal exit, where
        //      InGame comes back a frame or two before 292 has cleared the record.
        {
            static s32 siPendingResultsUpdates = 0;
            const s32  liGameModeType          = mpGuiCache->GetGameMode();
            const GuiEventOfflinePostEvent::OfflinePostEventData& lrResults =
                mpGuiCache->GetOfflinePostEventData();
            const bool lbResultsPending =
                lpacPostEventStateEvent == 0 && !mpGuiCache->IsOnline() &&
                liGameModeType > BrnGameState::GameStateModuleIO::E_MODE_NONE &&
                liGameModeType < BrnGameState::GameStateModuleIO::E_MODE_OFFLINE_COUNT &&
                liGameModeType != BrnGameState::GameStateModuleIO::E_MODE_OFFLINE_SHOWTIME &&
                lrResults.miPlayerFinishPosition > 0 &&
                lrResults.meFinishedGameModeType == liGameModeType;
            siPendingResultsUpdates = lbResultsPending ? siPendingResultsUpdates + 1 : 0;
            if (siPendingResultsUpdates == 60)
            {
                siPendingResultsUpdates = 0;
                ShutDownHudComponents();   // 291's HUD pause was spent while the flow was away
                mpGuiCache->GetGuiTracker()->ClearTracker();
                SendStateEvent("TO_OFF_POST");
                if (LoseDiagLine())
                {
                    *CgsDev::Log::gpDebugPrint
                        << "[lose-diag] RECOVERED: mode " << liGameModeType
                        << " results record pending (finish position "
                        << static_cast<s32>(lrResults.miPlayerFinishPosition)
                        << ") with InGame up and no results screen -> \"TO_OFF_POST\" [FLAG PC fix]\n";
                }
            }
        }

        // [FLAG PC witness] BRN_LOSE_DIAG: State::SendStateEvent keeps only the LAST event of
        // an update, so a later pause/map/driver-details request in the same update replaces
        // the post-event transition and the results screen never opens.
        if (lpacPostEventStateEvent != 0 && LoseDiagLine())
        {
            const bool lbKept = std::strcmp(GetPendingEventName(), lpacPostEventStateEvent) == 0;
            *CgsDev::Log::gpDebugPrint
                << (lbKept ? "[lose-diag] InGame GUI 291 -> \"" : "[lose-diag] DROPPED GUI 291: \"")
                << lpacPostEventStateEvent
                << (lbKept ? "\" pending" : "\" replaced in the same update by \"")
                << (lbKept ? "" : GetPendingEventName())
                << (lbKept ? "" : "\"") << " [FLAG PC witness]\n";
        }

        lpInQueue->Clear();
    }
}
