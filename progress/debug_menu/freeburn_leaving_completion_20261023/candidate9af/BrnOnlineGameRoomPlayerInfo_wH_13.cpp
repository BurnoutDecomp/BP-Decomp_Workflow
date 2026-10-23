// ===================================================================================
// BrnGui::OnlineGameRoomPlayerInfo -- wave-H partfile 13: the overlay plumbing.
//   b5-decomp/src/GameSource/Gui/Flow/Screen/States/BrnOnlineGameRoomPlayerInfo_wH_13.cpp
//
//   HandleAskToLaunchEvent @0x82498698  cpp:2527 (assert cpp:2542)
//   HandleInviteFailed     @0x82498BA0  cpp:2721 (assert cpp:2735)
//   HandleOverlayComplete  @0x824A56A0  cpp:2884 (assert cpp:2899)
//
// Reconstructed store-for-store from BURNOUT_X360_ARTIST.XEX (pseudocode arbitrated by
// the raw asm: scratchpad/waveB/...BrnOnlineGameRoomPlayerInfo.cpp.asm.txt). The class
// shape, the member map and the rodata tables live in the wave-H keystone scaffold
// BrnOnlineGameRoomPlayerInfo.{h,cpp}; the sibling bodies land in the other
// BrnOnlineGameRoomPlayerInfo_wH_XX.cpp partfiles.
//
// These three are the screen's overlay conversation: it asks a question (the launch
// confirmation), it reports a failed invite, and it answers whatever question the
// overlay director says the player just closed.
//
// X360 offsets appear only in comments; every access below resolves by NAME (the host
// layout widens pointers and component vptrs, so no console offset or stride is
// reproduced in code). The members these bodies touch, with their console offsets:
//   this+28    -> mpStateInterface (CgsGui::State)      this+87464 -> mOverlayCompleteEvent
//   this+55584 -> mSettingToggle                        this+87516 -> mpGuiCache
//   this+87534 -> mbNeedToClearSplashScreen             this+87536 -> mbShownFromPause
// and on the cache side cache+0xB878 -> the embedded options profile
// (GuiCache::GetOptionsDataProfile, inlined by the X360 as `cache + 0xB878`).
//
// PAYLOAD VIEWS. The in-queue hands a state the HEADER-STRIPPED payload, so the DWARF's
// typed event-pointer signatures would mislead every field offset by 12; these bodies
// take `const CgsModule::Event*` and cast to a payload view, the same idiom the
// committed BrnInGame.cpp and the sibling wave-H partfiles use. The overlay-complete
// payload already has a home -- OnlineGameRoomPlayerInfo::OverlayCompleteData in the
// class header (it is also the type of the stored mOverlayCompleteEvent member and the
// parameter type of ClearSplashScreenOverlay) -- so it is reused rather than re-forked.
//
// OUT-QUEUE RECORDS. Where the X360 calls CgsGui::StateInterface::OutputGuiEvent<T> the
// callee stack-builds a { payload size, event id, payload offset, payload } record and
// posts it on channel 40; the two instantiations these bodies reach were dumped from the
// image to pin the record exactly:
//   OutputGuiEvent<BrnGui::GuiOverlayRequest>    @0x82436BE0 -> { 288, 184, 16, request },
//                                                   channel 40, 304 bytes
//   OutputGuiEvent<BrnGui::GuiAudioTriggerEvent> @0x82436890 -> { 100, 457, 12, payload },
//                                                   channel 40, 112 bytes
// The committed CgsGuiStateInterface.h OutputGuiEvent template posts the bare payload
// under channel == GetEventType() instead, which is NOT that record, so each site below
// builds the attested record and posts it through GetOutputEventQueue()->AddEvent() --
// the accommodation BrnCarSelectMain_wG_02.cpp and BrnOnlineGameRoomPlayerInfo_wH_08.cpp
// already make. Every size word is a HOST sizeof expression, never the console's baked
// 0x120 / 0x130 / 0x64 / 0x70 immediates.
//
// HEADER CLASH. BrnGuiEventTypeDefs.h (pulled in by the class header via BrnGuiCache.h,
// and needed here for GuiOverlayRequest / GuiAudioTriggerEvent) hard-collides with
// BrnGuiDemangledEventTypes.h, so the ids that are homed only in the demangled header
// (457, 463, 474, 52) are carried as file-local wire views -- as in BrnInGame.cpp and
// the sibling partfiles 07/08/09.
// ===================================================================================

#include "GameSource/Gui/Flow/Screen/States/BrnOnlineGameRoomPlayerInfo.h"

#include "GameShared/GameClasses/Core/CgsAssert.h"                        // CGS_ASSERT
#include "GameShared/GameClasses/Core/CgsID.h"                            // CgsID / CgsIDCompress
#include "GameShared/GameClasses/Gui/CgsGuiEvent.h"                       // CgsGui::GuiEvent<N>
#include "GameShared/GameClasses/Gui/Model/State/CgsGuiStateInterface.h"  // StateInterface out-queue
#include "GameShared/GameClasses/Module/CgsVariableEventQueue.h"          // CgsModule::Event / AddEvent
#include "GameSource/Gui/BrnGuiCache.h"                                   // GuiCache::GetOptionsDataProfile
#include "GameSource/Gui/BrnGuiOptionsDataProfile.h"                      // OptionsDataProfile volume getters
#include "GameSource/Gui/BrnGuiEventTypeDefs.h"                           // GuiOverlayRequest / GuiAudioTriggerEvent
#include "GameShared/GameClasses/System/PC/BrnNetHarnessPC.h"             // [netui] witness lines (LAN / harness only)

namespace BrnGui
{
    namespace
    {
        // ---- AddEvent channels (the out-queue selector word) ------------------------
        const s32 KI_CHANNEL_GUI_OUT = 40;   // OutputGuiEvent

        // ---- overlay ids these bodies name (X360 rodata literals) --------------------
        const char KAC_OVERLAY_LAUNCH_QUESTION[]  = "CNLobbyLchQn";  // "start the match?"
        const char KAC_OVERLAY_CANCEL_CONFIRM[]   = "CNCnclCnfrm";   // "discard the settings edit?"
        const char KAC_OVERLAY_LEAVE_GAME_QN[]    = "CNOnlLvGmQn";   // "leave the game?"
        const char KAC_OVERLAY_LEAVE_CHALLENGE_QN[] = "CNOnlLvChaQn"; // "leave the challenge?"
        const char KAC_OVERLAY_HOST_LEAVE_QN[]    = "OnHostLvQn";    // "leave, as the host?"
        const char KAC_OVERLAY_LEAVING_GAME[]     = "CNOnlLvgGame";  // the "leaving..." splash
        const char KAC_OVERLAY_INVITE_SAME_GAME[] = "CNInvSmGame";   // invite target already here
        const char KAC_OVERLAY_INVITE_SAME_MACHINE[] = "CNInvSmMach";// invite target on this box
        const char KAC_OVERLAY_INVITE_HOST[]      = "CNInvHost";     // invite refused by the host

        // The overlay-complete leave method this screen acts on. FLAG: the producer-side
        // enum (GuiOverlayCompleteEvent::LeaveMethod, named by the DWARF but without
        // recovered enumerators) is not in the recovered slice; the value below is the
        // X360's own `cmpwi 1` compare, named for the role it plays at both sites.
        const s32 KI_LEAVE_METHOD_CONFIRMED = 1;

        // The audio label + action the settings cancel plays on its way out.
        const s32  KI_AUDIO_ACTION_MENU_CUE = 7;   // X360 `li r4, 7`
        const char KAC_SOUND_LABEL_GO_BACK[] = "GO_BACK";

        // The invite-failure reasons. FLAG: the producer-side enum name is not in the
        // recovered DWARF slice; the roles come from the overlay each reason raises.
        const s32 KI_INVITE_FAILED_SAME_MACHINE = 0;
        const s32 KI_INVITE_FAILED_SAME_GAME    = 1;
        const s32 KI_INVITE_FAILED_HOST         = 2;

        // ---- in-queue payload view ---------------------------------------------------
        // The invite-failed payload: one word, the reason (`lwz r11, 0(r30)`).
        struct GuiEventInviteFailedPayload : public CgsModule::Event
        {
            s32 miReason;   // +0x00
        };

        // ---- out-queue wire records ---------------------------------------------------

        // The record OutputGuiEvent<BrnGui::GuiOverlayRequest> @0x82436BE0 builds:
        // { 288, 184, 16, <pad>, the 288-byte request }, channel 40, 304 bytes. The
        // payload is 8-aligned on the console, so its offset word is 16 rather than 12.
        struct GuiOverlayRequestWire : public CgsGui::GuiEvent<184>
        {
            u32               muPad0C;    // +0x0C (payload is 16-aligned past the header)
            GuiOverlayRequest mRequest;   // +0x10

            GuiOverlayRequestWire()
                : CgsGui::GuiEvent<184>(static_cast<u32>(sizeof(GuiOverlayRequest)), 16)
                , muPad0C(0)
            {
            }
        };

        // The record OutputGuiEvent<BrnGui::GuiAudioTriggerEvent> @0x82436890 builds:
        // { 100, 457, 12, the 100-byte payload }, channel 40, 112 bytes. The committed PC
        // GuiAudioTriggerEvent already carries that 12-byte queue header in front of its
        // 100-byte payload, so the event object IS the record -- but its GuiEvent<201>
        // base seeds the size word 0 and the id 201, while the X360 wire words are the
        // payload size and id 457. This view restores them without forking the payload
        // type. (Cross-TU finding: 201 is GuiEventHideDriveThru's id; 457 is the id both
        // this instantiation and BrnGuiDemangledEventTypes.h attest for the audio
        // trigger. Same view as BrnOnlineGameRoomPlayerInfo_wH_08.cpp's.)
        const u32 KU_WIRE_ID_AUDIO_TRIGGER = 457;

        struct GuiAudioTriggerWire : public GuiAudioTriggerEvent
        {
            GuiAudioTriggerWire()
            {
                muHeader0 = static_cast<u32>(sizeof(GuiAudioTriggerEvent) -
                                             sizeof(CgsGui::GuiEvent<201>));
                muEventType = KU_WIRE_ID_AUDIO_TRIGGER;
            }
        };

        // Id 463 == BrnGui::GuiEventAudioSettings: { 8, 463, 12, the two volume words },
        // channel 40, 20 bytes. Field order is the X360 store order -- GetMusicVolume
        // lands in the first payload word, GetSFXVolume in the second.
        typedef CgsGui::GuiEvent<463> AudioSettingsHeader;
        struct GuiEventAudioSettingsWire : public AudioSettingsHeader
        {
            s32 miMusicVolume;   // +0x0C
            s32 miSFXVolume;     // +0x10

            GuiEventAudioSettingsWire(s32 liMusicVolume, s32 liSFXVolume)
                : AudioSettingsHeader(static_cast<u32>(2 * sizeof(s32)),
                                      static_cast<u32>(sizeof(AudioSettingsHeader)))
                , miMusicVolume(liMusicVolume)
                , miSFXVolume(liSFXVolume)
            {
            }
        };

        // Id 474 == BrnGui::GuiEventVoipSettings: { 4, 474, 12, the voip volume word },
        // channel 40, 16 bytes.
        typedef CgsGui::GuiEvent<474> VoipSettingsHeader;
        struct GuiEventVoipSettingsWire : public VoipSettingsHeader
        {
            s32 miVoipVolume;    // +0x0C

            explicit GuiEventVoipSettingsWire(s32 liVoipVolume)
                : VoipSettingsHeader(static_cast<u32>(sizeof(s32)),
                                     static_cast<u32>(sizeof(VoipSettingsHeader)))
                , miVoipVolume(liVoipVolume)
            {
            }
        };

        // Id 52 -- the "leave the online game" request: { 1, 52, 12, <one payload byte> },
        // channel 40, 16 bytes. FLAG: the producer-side type name is not in the recovered
        // DWARF slice and the id is absent from BrnGuiDemangledEventTypes.h; the role is
        // pinned by the consumer, BrnNetwork::StateManager::ProcessGuiEvents @0x82577F20
        // case 52, which starts the leave-game matchmaking process and answers with
        // CgsGui::GuiEvent<53>. The payload is a single byte that the X360 producer never
        // writes and the consumer never reads (the X360 emits only the three header
        // stores), so it is left unwritten here too.
        typedef CgsGui::GuiEvent<52> LeaveOnlineGameHeader;
        struct GuiEventLeaveOnlineGameWire : public LeaveOnlineGameHeader
        {
            u8 maPayload[1];   // +0x0C -- never written by the X360 (see above)

            GuiEventLeaveOnlineGameWire()
                : LeaveOnlineGameHeader(static_cast<u32>(sizeof(maPayload)),
                                        static_cast<u32>(sizeof(LeaveOnlineGameHeader)))
            {
            }
        };

        // Record-size pins. Every one of these payloads is pointer-free, so the X360's
        // AddEvent size immediate must survive unchanged on the x64 host; if a host layout
        // ever drifts, this is where it is caught rather than on the wire.
        static_assert(sizeof(GuiOverlayRequestWire) == 304, "overlay request record is 304 bytes");
        static_assert(sizeof(GuiAudioTriggerWire) == 112, "audio trigger record is 112 bytes");
        static_assert(sizeof(GuiEventAudioSettingsWire) == 20, "audio settings record is 20 bytes");
        static_assert(sizeof(GuiEventVoipSettingsWire) == 16, "voip settings record is 16 bytes");
        static_assert(sizeof(GuiEventLeaveOnlineGameWire) == 16, "leave-game record is 16 bytes");
    }

    // ---- HandleAskToLaunchEvent @ 0x82498698 --------------------------------------
    // The host asked everyone to confirm the launch: put the launch question up.
    void OnlineGameRoomPlayerInfo::HandleAskToLaunchEvent(const CgsModule::Event* lpAskToLaunchEvent)
    {
        // cpp:2542. The X360 streams this text into the assert buffer before firing.
        CGS_ASSERT(lpAskToLaunchEvent != 0,
                   "Invalid event sent to OnlineGameRoomPlayerInfo::HandleAskToLaunchEvent");

        // The X360 constructs the request in a scratch stack slot and memcpy's it into the
        // record (the inlined OutputGuiEvent<GuiOverlayRequest> copy); constructed in
        // place here.
        GuiOverlayRequestWire lWire;
        lWire.mRequest.Construct(KAC_OVERLAY_LAUNCH_QUESTION);

        mpStateInterface->GetOutputEventQueue()->AddEvent(
            reinterpret_cast<const CgsModule::Event*>(&lWire), KI_CHANNEL_GUI_OUT,
            static_cast<s32>(sizeof(lWire)));
    }

    // ---- HandleInviteFailed @ 0x82498BA0 -------------------------------------------
    // An outgoing invite bounced: raise the overlay that explains why. The three reasons
    // the screen answers each name their own overlay; any other reason is ignored.
    void OnlineGameRoomPlayerInfo::HandleInviteFailed(const CgsModule::Event* lpInviteFailedEvent)
    {
        CGS_ASSERT(lpInviteFailedEvent != 0, "lpInviteFailedEvent");   // cpp:2735

        const s32 liReason =
            reinterpret_cast<const GuiEventInviteFailedPayload*>(lpInviteFailedEvent)->miReason;

        // The X360 splits this into two shapes: the same-game arm has the
        // OutputGuiEvent<GuiOverlayRequest> body inlined (construct + memcpy + AddEvent),
        // the other two call the out-of-line instantiation. Both produce the identical
        // record, so both are posted the same way here.
        const char* lpcOverlayId = 0;

        if (liReason == KI_INVITE_FAILED_SAME_GAME)
        {
            lpcOverlayId = KAC_OVERLAY_INVITE_SAME_GAME;
        }
        else if (liReason == KI_INVITE_FAILED_SAME_MACHINE)
        {
            lpcOverlayId = KAC_OVERLAY_INVITE_SAME_MACHINE;
        }
        else if (liReason == KI_INVITE_FAILED_HOST)
        {
            lpcOverlayId = KAC_OVERLAY_INVITE_HOST;
        }
        else
        {
            return;
        }

        GuiOverlayRequestWire lWire;
        lWire.mRequest.Construct(lpcOverlayId);

        mpStateInterface->GetOutputEventQueue()->AddEvent(
            reinterpret_cast<const CgsModule::Event*>(&lWire), KI_CHANNEL_GUI_OUT,
            static_cast<s32>(sizeof(lWire)));
    }

    // ---- HandleOverlayComplete @ 0x824A56A0 ----------------------------------------
    // The overlay director closed an overlay: act on whichever question it was.
    //   "CNCnclCnfrm"  -- the settings edit was discarded: restore the profile's volumes,
    //                     tear the toggle group down and go back where we came from.
    //   "CNLobbyLchQn" -- the launch question: forwarded to HandleLaunchQuestion.
    //   the three leave questions -- confirmed: raise the "leaving" splash and ask the
    //                     network layer to leave the game.
    //   anything else  -- a splash screen closing: clear it now if the cache is up,
    //                     otherwise remember it and clear it on the next Update.
    void OnlineGameRoomPlayerInfo::HandleOverlayComplete(const CgsModule::Event* lpEvent)
    {
        CGS_ASSERT(lpEvent != 0, "lpOverlayCompleteEvent");   // cpp:2899

        // The stored member and ClearSplashScreenOverlay's parameter are both this shape
        // (id qword at +0, leave method at +8) -- see the class header.
        const OverlayCompleteData* lpOverlayCompleteEvent =
            reinterpret_cast<const OverlayCompleteData*>(lpEvent);

        if (lpOverlayCompleteEvent->mOverlayId == CgsIDCompress(KAC_OVERLAY_CANCEL_CONFIRM))
        {
            if (lpOverlayCompleteEvent->miLeaveMethod == KI_LEAVE_METHOD_CONFIRMED)
            {
                // The X360 reads both volumes into one stack qword, plays the back-out
                // cue, publishes the audio settings, then reads the voip volume into the
                // next record and publishes that.
                const s32 liMusicVolume = mpGuiCache->GetOptionsDataProfile()->GetMusicVolume();
                const s32 liSFXVolume   = mpGuiCache->GetOptionsDataProfile()->GetSFXVolume();

                GuiAudioTriggerWire lAudio;
                lAudio.Construct(KI_AUDIO_ACTION_MENU_CUE, "", KAC_SOUND_LABEL_GO_BACK, "");
                mpStateInterface->GetOutputEventQueue()->AddEvent(
                    reinterpret_cast<const CgsModule::Event*>(&lAudio), KI_CHANNEL_GUI_OUT,
                    static_cast<s32>(sizeof(lAudio)));

                GuiEventAudioSettingsWire lAudioSettings(liMusicVolume, liSFXVolume);
                mpStateInterface->GetOutputEventQueue()->AddEvent(
                    reinterpret_cast<const CgsModule::Event*>(&lAudioSettings), KI_CHANNEL_GUI_OUT,
                    static_cast<s32>(sizeof(lAudioSettings)));

                GuiEventVoipSettingsWire lVoipSettings(
                    mpGuiCache->GetOptionsDataProfile()->GetVoipVolume());
                mpStateInterface->GetOutputEventQueue()->AddEvent(
                    reinterpret_cast<const CgsModule::Event*>(&lVoipSettings), KI_CHANNEL_GUI_OUT,
                    static_cast<s32>(sizeof(lVoipSettings)));

                mSettingToggle.Unloaded();
                mSettingToggle.Clear();   // group vtable slot 6

                if (mbShownFromPause)
                {
                    UnloadSettingsResources();
                    HideHUDAndEnterMenus();
                    ShowPauseScreen();
                }
                else
                {
                    UnloadSettingsResources();
                    HideSettingsPage();
                }
            }
        }
        else if (lpOverlayCompleteEvent->mOverlayId == CgsIDCompress(KAC_OVERLAY_LAUNCH_QUESTION))
        {
            HandleLaunchQuestion(lpOverlayCompleteEvent->miLeaveMethod);
        }
        else if (lpOverlayCompleteEvent->mOverlayId == CgsIDCompress(KAC_OVERLAY_LEAVE_GAME_QN) ||
                 lpOverlayCompleteEvent->mOverlayId == CgsIDCompress(KAC_OVERLAY_LEAVE_CHALLENGE_QN) ||
                 lpOverlayCompleteEvent->mOverlayId == CgsIDCompress(KAC_OVERLAY_HOST_LEAVE_QN))
        {
            if (lpOverlayCompleteEvent->miLeaveMethod == KI_LEAVE_METHOD_CONFIRMED)
            {
                GuiOverlayRequestWire lWire;
                lWire.mRequest.Construct(KAC_OVERLAY_LEAVING_GAME);
                mpStateInterface->GetOutputEventQueue()->AddEvent(
                    reinterpret_cast<const CgsModule::Event*>(&lWire), KI_CHANNEL_GUI_OUT,
                    static_cast<s32>(sizeof(lWire)));

                GuiEventLeaveOnlineGameWire lLeaveGame;
                mpStateInterface->GetOutputEventQueue()->AddEvent(
                    reinterpret_cast<const CgsModule::Event*>(&lLeaveGame), KI_CHANNEL_GUI_OUT,
                    static_cast<s32>(sizeof(lLeaveGame)));

                BrnNetHarnessPC::WitnessTag("netui", "leave", "post 52 method=%d",
                                            lpOverlayCompleteEvent->miLeaveMethod);
            }
        }
        else if (mpGuiCache != 0)
        {
            ClearSplashScreenOverlay(lpOverlayCompleteEvent);
        }
        else
        {
            // No cache yet -- stash the whole 16-byte record and let Update clear it.
            mOverlayCompleteEvent = *lpOverlayCompleteEvent;
            mbNeedToClearSplashScreen = true;
        }
    }
}
