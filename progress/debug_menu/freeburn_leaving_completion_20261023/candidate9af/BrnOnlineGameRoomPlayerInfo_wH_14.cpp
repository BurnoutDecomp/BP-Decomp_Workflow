// ===================================================================================
// BrnGui::OnlineGameRoomPlayerInfo -- wave-H partfile 14: the three network-lifecycle
// in-queue handlers that report a game the local player is being removed from, a
// failed launch, and a refreshed stats record for the highlighted player.
//   b5-decomp/src/GameSource/Gui/Flow/Screen/States/BrnOnlineGameRoomPlayerInfo_wH_14.cpp
//
//   HandleLeftGameEvent     @0x82498358  (cpp:2392)
//   HandleLaunchedEvent     @0x82498A10  (cpp:2599)
//   HandlePlayerStatsEvent  @0x82484BA0  (cpp:2636)
//
// Reconstructed store-for-store from BURNOUT_X360_ARTIST.XEX (pseudocode arbitrated by
// the raw asm, scratchpad/waveB/...BrnOnlineGameRoomPlayerInfo.cpp.asm.txt). The first
// two have VERBATIM copy-paste twins in the car-select screen -- their X360 assert
// strings still name OnlineGameRoomPlayerInfo:: -- already reconstructed as
// CarSelectMain::HandleLeftGameEvent / ::HandleLaunchedEvent in
// BrnCarSelectMain_wG_02.cpp; the wire records and the assert treatment below follow
// that committed precedent, adapted to THIS screen's members (the kicked-popup and
// launch-failed tables are class statics here, our left-game path additionally sets
// mbKicked and sends "GO_BACK" rather than "DISCONNECT").
//
// The owning header (BrnOnlineGameRoomPlayerInfo.h) carries the X360 member offsets
// every access below resolves through BY NAME:
//   this+28    -> mpStateInterface (CgsGui::State)   this+87516 -> mpGuiCache
//   this+34400 -> mMessageText (the tab title)       this+87504 -> meSubState
//   this+38984 -> mPlayerNameComponent               this+87535 -> mbKicked
//   this+39149 -> mPlayerNameComponent.miHighlightedIndex (SelectableGroup +0xA5, s8)
//   this+75684 -> mPlayerStatsDisplay.meState (GuiNetworkPlayerStats +0x11E4)
//   this+84312 -> mRouteInfoDisplay.meState   (GuiNetworkRouteInfo   +0x21A8)
// and on the cache side:
//   cache+0xB650 -> maLobbyPlayerInfo[i].mPlayerID (row stride 56 == the committed
//                   pointer-free sizeof(LobbyPlayerStatusData), so the console stride
//                   IS the host stride; the row is still reached by NAMED array index)
//   cache+0xA9DF -> mbOnlineRanked
//
// OUT-QUEUE RECORDS. The X360 reaches the overlay wires two ways -- by inlining
// CgsGui::StateInterface::OutputGuiEvent<T> (the construct-then-memcpy pairs at
// 0x82498AE0 / 0x82498584) and by calling the out-of-line instantiation
// (HandleLeftGameEvent's lobby-deleted overlay at 0x82498444) -- but both emit the
// identical { sizeof(payload), <event id>, 16, <pad>, payload } record on channel 40.
// The committed CgsGui::StateInterface::OutputGuiEvent template queues the bare
// payload under channel == GetEventType() instead, which is NOT what the X360
// instantiation does, so every site below posts the wire record directly (identical to
// BrnCarSelectMain_wG_02.cpp / BrnOnlineGameRoomPlayerInfo_wH_08.cpp).
//
// X360 LITERALS. The console's baked AddEvent sizes (0x130 / 0x18) and payload-size
// words (0x120 / 8) are written as host sizeof() expressions; every payload involved is
// pointer-free, so the static_asserts below pin the host records back onto the console
// sizes rather than letting a widened layout drift silently onto the wire.
// ===================================================================================

#include "GameSource/Gui/Flow/Screen/States/BrnOnlineGameRoomPlayerInfo.h"

#include "GameShared/GameClasses/Core/CgsAssert.h"                        // CGS_ASSERT
#include "GameShared/GameClasses/Gui/CgsGuiEvent.h"                       // CgsGui::GuiEvent<N>
#include "GameShared/GameClasses/Gui/Model/State/CgsGuiStateInterface.h"  // StateInterface out-queue
#include "GameShared/GameClasses/Module/CgsVariableEventQueue.h"          // CgsModule::Event / AddEvent
#include "GameSource/Gui/BrnGuiCache.h"                                   // BrnGui::GuiCache / GuiFlow
#include "GameSource/Gui/BrnGuiEventTypeDefs.h"                           // BrnGui::GuiOverlayRequest
#include "GameSource/Network/Managers/BrnNetworkPlayerStats.h"            // BrnNetwork::NetworkPlayerStats
#include "GameSource/Network/SharedIO/BrnNetworkModuleInGamePlayerStatusInterface.h"      // InGamePlayerStatusData
#include "GameSource/Network/SharedIO/BrnNetworkModuleOnlineLobbyPlayerStatusInterface.h" // LobbyPlayerStatusData
#include "GameShared/GameClasses/System/PC/BrnNetHarnessPC.h"             // [netui] witness lines (LAN / harness only)

// The canonical homes for the three in-queue payload shapes below are
// GameSource/Gui/BrnGuiDemangledEventTypes.h, but that header and BrnGuiEventTypeDefs.h
// are MUTUALLY EXCLUSIVE by construction (both define GuiAudioTriggerEvent and three
// more types with different layouts) and the owning header pulls BrnGuiCache.h ->
// BrnGuiEventTypeDefs.h in. So the payloads are modelled here as file-local views --
// the same idiom the committed BrnInGame.cpp / BrnCarSelectMain_wG_02.cpp use, and the
// queue hands out HEADER-STRIPPED payloads, so the views start at the first field.

namespace BrnGui
{
    namespace
    {
        const s32 KI_CHANNEL_GUI_OUT = 40;   // GuiEventOut -- the AddEvent channel every site uses

        // ---- in-queue payload views ------------------------------------------------

        // Event 273 ("left game"): the reason word, then -- for the kicked reason -- the
        // kick sub-reason that indexes KAPC_KICKED_POPUP. The X360 bounds-checks the kick
        // reason SIGNED (blt on 0 then blt on 5); Hex-Rays renders it as `> 4u`.
        struct GuiEventLeftGamePayload : public CgsModule::Event
        {
            s32 miReason;        // +0x00
            s32 miKickReason;    // +0x04
        };

        // Event 58 ("launched"): one word read both as the failure test and as the
        // KPC_LAUNCH_FAILED_STRINGIDS index.
        struct GuiEventLaunchedPayload : public CgsModule::Event
        {
            s32 miResult;        // +0x00  (0 == launched OK)
        };

        // Event 320 ("player stats"): a whole cached stats record followed by the player
        // it belongs to and the stat value to display. The X360 reads +0x84 / +0x88,
        // which is exactly this member order past the 132-byte pointer-free record.
        struct GuiEventPlayerStatsPayload : public CgsModule::Event
        {
            BrnNetwork::NetworkPlayerStats mStats;      // +0x00  (132 bytes)
            s32                            miPlayerId;  // +0x84
            s32                            miValue;     // +0x88
        };

        // ---- out-queue wire records ------------------------------------------------

        // The OutputGuiEvent<BrnGui::GuiOverlayRequest> record: { 288, 184, 16, <pad>,
        // the 288-byte request }, channel 40, 304 bytes.
        struct GuiOverlayRequestWire : public CgsGui::GuiEvent<184>
        {
            u32               muPad0C;    // +0x0C (the payload is 16-aligned past the header)
            GuiOverlayRequest mRequest;   // +0x10

            GuiOverlayRequestWire()
                : CgsGui::GuiEvent<184>(static_cast<u32>(sizeof(GuiOverlayRequest)), 16)
                , muPad0C(0)
            {
            }
        };

        // The OutputGuiEvent<BrnGui::GuiOverlayWaitFinishRequest> record:
        // { 8, 188, 16, <pad>, the compressed overlay id }, channel 40, 24 bytes.
        struct GuiOverlayWaitFinishWire : public CgsGui::GuiEvent<188>
        {
            u32                         muPad0C;    // +0x0C (the payload is 8-aligned)
            GuiOverlayWaitFinishRequest mRequest;   // +0x10

            GuiOverlayWaitFinishWire()
                : CgsGui::GuiEvent<188>(static_cast<u32>(sizeof(GuiOverlayWaitFinishRequest)), 16)
                , muPad0C(0)
            {
            }
        };

        // Record-size pins: both payloads are pointer-free, so the X360's AddEvent size
        // immediates must survive unchanged on the x64 host.
        static_assert(sizeof(GuiOverlayRequestWire) == 304, "overlay request record is 304 bytes");
        static_assert(sizeof(GuiOverlayWaitFinishWire) == 24, "overlay wait-finish record is 24 bytes");

        // ---- overlay / state-event vocabularies (the asm's rodata literals) --------
        const char KAC_OVERLAY_LOBBY_DELETED[]   = "CNLobbyDlted";   // lobby went away under us
        const char KAC_OVERLAY_LEAVE_GAME_QN[]   = "CNOnlLvGmQn";    // "leave the game?" question
        const char KAC_OVERLAY_LEAVE_CHAL_QN[]   = "CNOnlLvChaQn";   // "leave the challenge?" question
        const char KAC_OVERLAY_LAUNCH_FAILED[]   = "CNOnlLchFail";
        const char KAC_STATE_EVENT_GO_BACK[]     = "GO_BACK";

        // The reason words this handler acts on. FLAG: the producer-side enum name is not
        // in the recovered DWARF slice; the roles come from the overlay ids they raise.
        const s32 KI_LEFT_GAME_REASON_KICKED         = 2;
        const s32 KI_LEFT_GAME_REASON_LOBBY_DELETED  = 3;

        // The X360's own kick-reason bound (the `>= 5` half of the signed assert range);
        // it is exactly the element count of OnlineGameRoomPlayerInfo::KAPC_KICKED_POPUP.
        const s32 KI_KICK_REASON_COUNT = 5;

        // The launch-failed message parameter slot AddMessageParam is called with.
        const u32 KU_LAUNCH_FAILED_MESSAGE_PARAM = 2;
    }

    // ---- HandleLeftGameEvent @ 0x82498358 (cpp:2392) --------------------------------
    // In-queue event 273. Raise the reason-specific overlay(s), hand the flow the
    // "GO_BACK" state event, and drop the expected-apt-component list if the screen is
    // still part-way through one of its loads.
    void OnlineGameRoomPlayerInfo::HandleLeftGameEvent(const CgsModule::Event* lpLeftGameEvent)
    {
        // The X360 fires BOTH asserts back-to-back on the null path: the bare expression
        // text (cpp:2408) then the streamed message (cpp:2409).
        CGS_ASSERT(lpLeftGameEvent != 0, "lpLeftGameEvent");                                  // cpp:2408
        CGS_ASSERT(lpLeftGameEvent != 0,
                   "Invalid event sent to OnlineGameRoomPlayerInfo::HandleLeftGameEvent");    // cpp:2409

        const GuiEventLeftGamePayload* lpPayload =
            reinterpret_cast<const GuiEventLeftGamePayload*>(lpLeftGameEvent);

        // Two independent tests in the asm (the reason word is re-read at 0x82498448),
        // not an if/else chain.
        if (lpPayload->miReason == KI_LEFT_GAME_REASON_LOBBY_DELETED && !mbKicked)
        {
            GuiOverlayRequestWire lWire;
            lWire.mRequest.Construct(KAC_OVERLAY_LOBBY_DELETED);

            mpStateInterface->GetOutputEventQueue()->AddEvent(
                reinterpret_cast<const CgsModule::Event*>(&lWire), KI_CHANNEL_GUI_OUT,
                static_cast<s32>(sizeof(lWire)));
        }

        if (lpPayload->miReason == KI_LEFT_GAME_REASON_KICKED)
        {
            // Tear down both outstanding "are you sure you want to leave" questions
            // before the kick overlay goes up.
            {
                GuiOverlayWaitFinishWire lWaitGame;
                lWaitGame.mRequest.Construct(KAC_OVERLAY_LEAVE_GAME_QN);

                mpStateInterface->GetOutputEventQueue()->AddEvent(
                    reinterpret_cast<const CgsModule::Event*>(&lWaitGame), KI_CHANNEL_GUI_OUT,
                    static_cast<s32>(sizeof(lWaitGame)));
            }
            {
                GuiOverlayWaitFinishWire lWaitChallenge;
                lWaitChallenge.mRequest.Construct(KAC_OVERLAY_LEAVE_CHAL_QN);

                mpStateInterface->GetOutputEventQueue()->AddEvent(
                    reinterpret_cast<const CgsModule::Event*>(&lWaitChallenge), KI_CHANNEL_GUI_OUT,
                    static_cast<s32>(sizeof(lWaitChallenge)));
            }

            // cpp:2433 -- SIGNED bound check (asm: blt on 0, then blt on 5). The X360
            // streams "Invalid kick reason of " << miKickReason << "\n" into the assert
            // buffer; collapsed to the static text per project policy.
            CGS_ASSERT(lpPayload->miKickReason >= 0 && lpPayload->miKickReason < KI_KICK_REASON_COUNT,
                       "Invalid kick reason of ");

            GuiOverlayRequestWire lWire;
            lWire.mRequest.Construct(KAPC_KICKED_POPUP[lpPayload->miKickReason]);

            mpStateInterface->GetOutputEventQueue()->AddEvent(
                reinterpret_cast<const CgsModule::Event*>(&lWire), KI_CHANNEL_GUI_OUT,
                static_cast<s32>(sizeof(lWire)));

            mbKicked = true;
        }

        BrnNetHarnessPC::WitnessTag("netui", "game-room", "left game (GUI 273) reason=%d -> GO_BACK",
                                    lpPayload->miReason);
        SendStateEvent(KAC_STATE_EVENT_GO_BACK);

        if (mpGuiCache != 0 &&
            (meSubState == E_SUBSTATE_LOADING_SCREEN ||
             meSubState == E_SUBSTATE_LOADING_COMPONENTS ||
             meSubState == E_SUBSTATE_LOADING_PAUSE_SCREEN ||
             meSubState == E_SUBSTATE_LOADING_PAUSE_COMPONENTS))
        {
            mpGuiCache->ClearExpectedAptComponentList(E_GUIFLOW_SCREEN);
        }
    }

    // ---- HandleLaunchedEvent @ 0x82498A10 (cpp:2599) --------------------------------
    // In-queue event 58. On a non-zero launch result, raise the "CNOnlLchFail" overlay
    // carrying the result's ONLINE_LAUNCHED_FAILED_* string id as message param 2, then
    // put the tab title back to whichever page the screen is actually showing.
    void OnlineGameRoomPlayerInfo::HandleLaunchedEvent(const CgsModule::Event* lpLaunchedEvent)
    {
        // cpp:2611 -- the X360 streams this text into the assert buffer.
        CGS_ASSERT(lpLaunchedEvent != 0,
                   "Invalid event sent to OnlineGameRoomPlayerInfo::HandleLaunchedEvent");

        const GuiEventLaunchedPayload* lpPayload =
            reinterpret_cast<const GuiEventLaunchedPayload*>(lpLaunchedEvent);

        if (lpPayload->miResult != 0)
        {
            // The X360 builds the request in a scratch stack slot and memcpy's the 288
            // bytes into the record (the inlined OutputGuiEvent<GuiOverlayRequest> copy);
            // constructed in place here.
            GuiOverlayRequestWire lWire;
            lWire.mRequest.Construct(KAC_OVERLAY_LAUNCH_FAILED);
            lWire.mRequest.AddMessageParam(KU_LAUNCH_FAILED_MESSAGE_PARAM,
                                           KPC_LAUNCH_FAILED_STRINGIDS[lpPayload->miResult]);

            mpStateInterface->GetOutputEventQueue()->AddEvent(
                reinterpret_cast<const CgsModule::Event*>(&lWire), KI_CHANNEL_GUI_OUT,
                static_cast<s32>(sizeof(lWire)));

            // Tab title. The X360 tests the two panels' visibility state words directly
            // (mPlayerStatsDisplay.meState @+0x11E4 and mRouteInfoDisplay.meState
            // @+0x21A8, both compared against E_STATE_VISIBLE == 0); the stats panel's
            // state member is private, so its test goes through the DWARF-attested
            // IsVisible() accessor the compiler inlined here.
            if (mPlayerStatsDisplay.IsVisible())
            {
                mMessageText.SetText(KAC_PLAYER_INFO_STRING_ID);
            }
            else if (mRouteInfoDisplay.meState == GuiNetworkRouteInfo::E_STATE_VISIBLE)
            {
                mMessageText.SetText(KAC_EVENT_INFO_STRING_ID);
            }
            else
            {
                mMessageText.SetText(KAC_EVENT_MAP_STRING_ID);
            }
        }
    }

    // ---- HandlePlayerStatsEvent @ 0x82484BA0 (cpp:2636) -----------------------------
    // In-queue event 320. A refreshed stats record arrived; push it into the stats panel
    // only while it still belongs to the player the list is highlighting.
    void OnlineGameRoomPlayerInfo::HandlePlayerStatsEvent(const CgsModule::Event* lpPlayerStatsEvent)
    {
        // cpp:2648 -- streamed into the assert buffer by the X360.
        CGS_ASSERT(lpPlayerStatsEvent != 0,
                   "Invalid event sent to OnlineGameRoomPlayerInfo::HandlePlayerStatsEvent");

        const GuiEventPlayerStatsPayload* lpPayload =
            reinterpret_cast<const GuiEventPlayerStatsPayload*>(lpPlayerStatsEvent);

        if (mpGuiCache != 0 &&
            lpPayload->miPlayerId ==
                reinterpret_cast<const BrnNetwork::BrnNetworkModuleIO::LobbyPlayerStatusData*>(
                    mpGuiCache->maLobbyPlayerInfo[mPlayerNameComponent.miHighlightedIndex])->mPlayerID)
        {
            const s32 liHighlightedIndex = mPlayerNameComponent.miHighlightedIndex;

            const BrnNetwork::BrnNetworkModuleIO::InGamePlayerStatusData* lpPlayerInfo =
                mpGuiCache->GetOnlinePlayerInfo(liHighlightedIndex);

            // Name from the in-game record (+256), the event's value and its stats block,
            // the highlighted row as the player image index, and the world-rank column
            // gated on the cached game params' "ranked" flag.
            mPlayerStatsDisplay.SetInfo(lpPlayerInfo->mPlayerName.macName,
                                        lpPayload->miValue,
                                        &lpPayload->mStats,
                                        liHighlightedIndex,
                                        mpGuiCache->mbOnlineRanked,
                                        mpGuiCache);
        }
    }
}
