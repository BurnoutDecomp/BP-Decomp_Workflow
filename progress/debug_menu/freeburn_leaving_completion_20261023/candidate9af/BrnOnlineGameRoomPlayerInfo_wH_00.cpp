// BrnGui::OnlineGameRoomPlayerInfo -- wave-H group 00: Update @0x824B0770 and
// UpdateSoundSettings @0x8249AD00.
//
// This group was reconstructed complete but parked out-of-tree by its implementer
// because it needed three shared-header declarations that implementers are not
// permitted to touch (MenuToggle::Update, and CrashNavOptionsData friendship for the
// two volume members). The conductor added those declarations; this is that
// reconstruction, unchanged apart from this banner.
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineGameRoomPlayerInfo.h"

#include "GameShared/GameClasses/Core/CgsAssert.h"                        // CGS_ASSERT
#include "GameShared/GameClasses/Gui/CgsGuiEvent.h"                       // CgsGui::GuiEvent<N>
#include "GameShared/GameClasses/Gui/CgsGuiShared.h"                      // CgsGui::GuiAccessPointers
#include "GameShared/GameClasses/Gui/Model/State/CgsGuiStateInterface.h"  // StateInterface out-queue
#include "GameShared/GameClasses/Module/CgsVariableEventQueue.h"          // CgsModule::Event / the in-queue
#include "GameSource/Gui/BrnGuiCache.h"                                   // BrnGui::GuiCache (delta / camera / disconnect)
#include "GameSource/Gui/BrnGuiEventTypeDefs.h"                           // BrnGui::GuiEventActivateCrashNav (id 191)
#include "GameSource/Gui/SatNav/BrnMapIconManager.h"                      // BrnGui::MapIconManager::IconSizeMode

namespace BrnGui
{
    namespace
    {
        // ---- the state in-queue (CgsGui::State::mpInGuiEventQueue's real instantiation) ---
        typedef CgsModule::VariableEventQueue<18432, 16> StateInputQueue;

        // ---- AddEvent channels (the out-queue selector word) ---------------------------
        const s32 KI_CHANNEL_GUI_OUT      = 40;   // OutputGuiEvent
        const s32 KI_CHANNEL_GUI_INTERNAL = 42;   // OutputInternalState

        // ---- observed wire ids (the class's maiEventToObserve[33] set) ------------------
        // Named where the role is attested by the handler this arm calls or by the assert
        // string the arm fires; FLAG marks the ones whose producer-side name is not in the
        // recovered DWARF slice and which are named for what THIS screen does with them.
        const s32 KI_EVENT_CONTROLLER_PRESSED   = 6;
        const s32 KI_EVENT_CONTROLLER_RELEASED  = 7;
        const s32 KI_EVENT_NETWORK_DISCONNECTED = 44;
        const s32 KI_EVENT_IN_GAME              = 50;   // assert string "lpInGameEvent"
        const s32 KI_EVENT_LEAVING_GAME         = 53;
        const s32 KI_EVENT_ASK_TO_LAUNCH        = 55;
        const s32 KI_EVENT_ONLINE_LAUNCHING     = 57;
        const s32 KI_EVENT_ONLINE_LAUNCHED      = 58;
        const s32 KI_EVENT_GUI_CACHE            = 64;
        const s32 KI_EVENT_CAR_SELECT_START     = 81;
        const s32 KI_EVENT_RETURN_TO_HUD        = 85;   // FLAG: named for this arm's action
        const s32 KI_EVENT_INVITE_FAILED        = 133;
        const s32 KI_EVENT_INVITE_COMPLETE      = 134;  // FLAG: named for this arm's action (posts id 135)
        const s32 KI_EVENT_OVERLAY_COMPLETE     = 189;
        const s32 KI_EVENT_TO_CAR_SELECT        = 229;  // FLAG: named for this arm's action
        const s32 KI_EVENT_PLAYER_LOBBY_LIST    = 244;
        const s32 KI_EVENT_PLAYER_STATS         = 248;
        const s32 KI_EVENT_GAME_PARAMS_CHANGED  = 257;
        const s32 KI_EVENT_SPLASH_SCREEN        = 269;
        const s32 KI_EVENT_NETWORK_LEFT_GAME    = 273;
        const s32 KI_EVENT_LEAVING_GAME_FAILED  = 275;
        const s32 KI_EVENT_PERFORM_PAUSE_OPTION = 283;  // GuiEventPerformOnlinePauseOption
        const s32 KI_EVENT_UI_VISIBLE           = 516;  // assert string "lpUiVisibleEvent != NULL"
        const s32 KI_EVENT_EVERY_PLAYER_STATUS  = 581;

        // ---- car-select-start payload types (the id-81 payload word) --------------------
        // FLAG: named for the two branches this arm takes; the producer-side enum is not in
        // the recovered slice. Anything else fires the "Invalid car select type" assert.
        const s32 KI_CAR_SELECT_TYPE_FROM_LOBBY   = 1;
        const s32 KI_CAR_SELECT_TYPE_ONLINE_EVENT = 2;

        // The zero the two EA-trax timers are compared against (X360 flt_82001CC0).
        const f32 KF_ZERO_TIME = 0.0f;

        // ---- in-queue payload views -----------------------------------------------------
        // The in-queue hands the state the HEADER-STRIPPED payload, so each view starts at
        // the producer's first payload field (BrnInGame.cpp / wave-H 05 precedent).

        // Id 44: the server-interface error the disconnect popup shows (`lwz 0(r27)`).
        struct NetworkDisconnectedPayload : public CgsModule::Event
        {
            s32 meError;   // +0x00
        };

        // Id 50: read as a BYTE (`lbz 0(r27)`) -- the "entering a game" flag.
        struct InGameEventPayload : public CgsModule::Event
        {
            bool mbInGame;   // +0x00
        };

        // Id 81: the car-select type word (`lwz 0(r27)`).
        struct CarSelectStartPayload : public CgsModule::Event
        {
            s32 meCarSelectType;   // +0x00
        };

        // Id 283: the pause option to perform (`lwz 0(r27)`).
        struct PerformPauseOptionPayload : public CgsModule::Event
        {
            s32 mePauseOption;   // +0x00
        };

        // Id 516: the "UI visible" word (`lwz 0(r27)`); 0 == the UI just went away, which
        // is what pushes the free-burning screen into the pause menu.
        struct UiVisiblePayload : public CgsModule::Event
        {
            s32 miUiVisible;   // +0x00
        };

        // ---- out-queue wire records ------------------------------------------------------
        // Each is a CgsGui::GuiEvent<N> header { payload size, event id, payload offset }
        // followed by the payload, published through
        // mpStateInterface->GetOutputEventQueue()->AddEvent(record, channel, sizeof(record)).

        // The bare one-byte-payload command record { 1, N, 12, <payload byte> }, X360 record
        // size 16. The X360 stack-builds ONLY the three header words for all three ids this
        // file posts (135, 461, 533) -- the payload byte keeps whatever the reused stack slot
        // held -- so the constructor leaves it alone rather than inventing a stored value.
        template <s32 TI_EVENT_ID>
        struct GuiCommandWire16 : public CgsGui::GuiEvent<TI_EVENT_ID>
        {
            u8 mu8Payload;   // +0x0C (not written by the X360)

            GuiCommandWire16()
                : CgsGui::GuiEvent<TI_EVENT_ID>(
                      static_cast<u32>(sizeof(u8)),
                      static_cast<u32>(sizeof(CgsGui::GuiEvent<TI_EVENT_ID>)))
            {
            }
        };

        // Id 148 == BrnGui::GuiEventShowHideHud (payload size 1). The car-select-start arm
        // publishes it on the INTERNAL channel with the flag clear (the X360's
        // OutputInternalState<GuiEventShowHideHud> @0x82493C98, record size 16).
        typedef CgsGui::GuiEvent<148> ShowHideHudHeader;
        struct GuiEventShowHideHudWire : public ShowHideHudHeader
        {
            bool mbShowHud;   // +0x0C

            explicit GuiEventShowHideHudWire(bool lbShowHud)
                : ShowHideHudHeader(static_cast<u32>(sizeof(bool)),
                                    static_cast<u32>(sizeof(ShowHideHudHeader)))
                , mbShowHud(lbShowHud)
            {
            }
        };

        // Id 188 -- the overlay wait-finish handshake the X360 publishes through
        // OutputGuiEvent<BrnGui::GuiOverlayWaitFinishRequest> @0x82476E98: the 8-byte
        // compressed overlay id sits at the 8-aligned payload slot, X360 record size 24,
        // channel 40 (the BrnPauseScreen.cpp / BrnInGame.cpp wire twin).
        typedef CgsGui::GuiEvent<188> OverlayWaitFinishHeader;
        struct GuiOverlayWaitFinishWire : public OverlayWaitFinishHeader
        {
            u32                         muPad0C;    // +0x0C (payload alignment pad)
            GuiOverlayWaitFinishRequest mRequest;   // +0x10 (the compressed overlay id)

            GuiOverlayWaitFinishWire()
                : OverlayWaitFinishHeader(
                      static_cast<u32>(sizeof(GuiOverlayWaitFinishRequest)),
                      static_cast<u32>(sizeof(OverlayWaitFinishHeader) + sizeof(u32)))
                , muPad0C(0)
            {
            }
        };

        // Id 463 -- the sound-volume settings record { 8, 463, 12, music, sfx }, X360
        // record size 20, channel 40. FLAG: the producer-side type name is not in the
        // recovered slice; the two payload words are the options model's music / SFX
        // volume members, in that order.
        typedef CgsGui::GuiEvent<463> SoundVolumesHeader;
        struct GuiEventSoundVolumesWire : public SoundVolumesHeader
        {
            s32 meMusicVolume;   // +0x0C
            s32 meSFXVolume;     // +0x10

            GuiEventSoundVolumesWire(CrashNavOptionsData::EOptionsSoundVolumes leMusicVolume,
                                     CrashNavOptionsData::EOptionsSoundVolumes leSFXVolume)
                : SoundVolumesHeader(static_cast<u32>(2 * sizeof(s32)),
                                     static_cast<u32>(sizeof(SoundVolumesHeader)))
                , meMusicVolume(static_cast<s32>(leMusicVolume))
                , meSFXVolume(static_cast<s32>(leSFXVolume))
            {
            }
        };

        // Post the id-188 record for one overlay name -- the X360 does exactly this four
        // times across the TU (Construct the request onto the wire record, then publish).
        void PostOverlayWaitFinish(CgsGui::StateInterface* lpStateInterface,
                                   const char* lpacOverlayName)
        {
            GuiOverlayWaitFinishWire lWaitFinish;
            lWaitFinish.mRequest.Construct(lpacOverlayName);
            lpStateInterface->GetOutputEventQueue()->AddEvent(
                reinterpret_cast<const CgsModule::Event*>(&lWaitFinish), KI_CHANNEL_GUI_OUT,
                static_cast<s32>(sizeof(lWaitFinish)));   // X360 record size 24
        }
    }

    // ================================================================================
    //  Update  @ 0x824B0770  (cpp:464)
    // ================================================================================
    void OnlineGameRoomPlayerInfo::Update()
    {
        StateInputQueue* lpInQueue = reinterpret_cast<StateInputQueue*>(mpInGuiEventQueue);
        const CgsModule::Event* lpEvent = 0;
        s32 liSize = 0;

        for (s32 liEventId = lpInQueue->GetFirstEvent(&lpEvent, &liSize);
             lpEvent != 0;
             liEventId = lpInQueue->GetNextEvent(lpEvent, &lpEvent, &liSize))
        {
            switch (liEventId)
            {
                case KI_EVENT_CONTROLLER_PRESSED:
                    HandleControllerInputPressed(lpEvent);
                    break;

                case KI_EVENT_CONTROLLER_RELEASED:
                    HandleControllerInputReleased(lpEvent);
                    break;

                // Registered in maiEventToObserve but consumed with no action here.
                case 8:
                case 14:
                case 16:
                case 21:
                case 199:
                case 202:
                case 213:
                case 320:
                case 334:
                case 344:
                case 406:
                    break;

                case KI_EVENT_NETWORK_DISCONNECTED:
                    // While an invite is being performed the disconnect is expected, so the
                    // error word is NOT latched -- the screen just backs out. Note the X360
                    // re-walks GetAccessPointers()->GetGuiCache() for the store rather than
                    // reusing the pointer it just tested.
                    if (mpStateInterface->GetAccessPointers()->GetGuiCache()->mbPerformingInvite)
                    {
                        SendStateEvent("GO_BACK");
                    }
                    else
                    {
                        GuiCache* lpGuiCache = mpStateInterface->GetAccessPointers()->GetGuiCache();
                        if (lpEvent != 0)
                        {
                            lpGuiCache->meLastDisconnectedError =
                                reinterpret_cast<const NetworkDisconnectedPayload*>(lpEvent)->meError;
                        }
                        else
                        {
                            lpGuiCache->meLastDisconnectedError = 0;
                        }
                        SendStateEvent("GO_BACK");
                    }
                    break;

                case KI_EVENT_IN_GAME:
                {
                    CGS_ASSERT(lpEvent != 0, "lpInGameEvent");   // cpp:608 (non-fatal)
                    // Entering the game: hold the flow until the "enter game" overlay has
                    // finished showing.
                    if (reinterpret_cast<const InGameEventPayload*>(lpEvent)->mbInGame)
                    {
                        PostOverlayWaitFinish(mpStateInterface, "CNOnlEntGame");
                    }
                    break;
                }

                case KI_EVENT_LEAVING_GAME:
                    mMessageText.SetText(KAC_LEAVING_GAME_STRING_ID);
                    meSubState = E_SUBSTATE_LEAVING;
                    break;

                case KI_EVENT_ASK_TO_LAUNCH:
                    HandleAskToLaunchEvent(lpEvent);
                    break;

                case KI_EVENT_ONLINE_LAUNCHING:
                    HandleLaunchingEvent(lpEvent);
                    break;

                case KI_EVENT_ONLINE_LAUNCHED:
                    HandleLaunchedEvent(lpEvent);
                    break;

                case KI_EVENT_GUI_CACHE:
                    HandleGuiCacheEvent(lpEvent);
                    CheckForCompletedLoads();
                    break;

                case KI_EVENT_CAR_SELECT_START:
                {
                    // The HUD goes down first whichever way the car select is reached.
                    GuiEventShowHideHudWire lHideHud(false);
                    mpStateInterface->GetOutputEventQueue()->AddEvent(
                        reinterpret_cast<const CgsModule::Event*>(&lHideHud),
                        KI_CHANNEL_GUI_INTERNAL,
                        static_cast<s32>(sizeof(lHideHud)));   // X360 record size 16

                    const s32 leCarSelectType =
                        reinterpret_cast<const CarSelectStartPayload*>(lpEvent)->meCarSelectType;
                    if (leCarSelectType == KI_CAR_SELECT_TYPE_FROM_LOBBY)
                    {
                        // Only leave for the car select if the player was actually out in the
                        // world (or already on the way out).
                        if (meSubState == E_SUBSTATE_FREE_BURNING ||
                            meSubState == E_SUBSTATE_LEAVING)
                        {
                            SendStateEvent("TO_CSELECT");
                            PostOverlayWaitFinish(mpStateInterface, "CNOnlLvgGame");
                        }
                    }
                    else if (leCarSelectType == KI_CAR_SELECT_TYPE_ONLINE_EVENT)
                    {
                        SendStateEvent("TO_ON_CARSEL");

                        // Hand the front-end map (CrashNav) flow back the screen.
                        GuiEventActivateCrashNav lActivateCrashNav(true);
                        mpStateInterface->GetOutputEventQueue()->AddEvent(
                            reinterpret_cast<const CgsModule::Event*>(&lActivateCrashNav),
                            KI_CHANNEL_GUI_OUT,
                            static_cast<s32>(sizeof(lActivateCrashNav)));   // X360 record size 20

                        GuiCommandWire16<533> lScreenFlowCommand;
                        mpStateInterface->GetOutputEventQueue()->AddEvent(
                            reinterpret_cast<const CgsModule::Event*>(&lScreenFlowCommand),
                            KI_CHANNEL_GUI_OUT,
                            static_cast<s32>(sizeof(lScreenFlowCommand)));  // X360 record size 16
                    }
                    else
                    {
                        // cpp:701 -- streamed as "Invalid car select type : " << type << "\n";
                        // lowered to the static text per project policy. Non-fatal: the X360
                        // falls straight through into the plain car-select transition.
                        CGS_ASSERT(false, "Invalid car select type : ");
                        SendStateEvent("TO_CSELECT");
                    }
                    break;
                }

                case KI_EVENT_RETURN_TO_HUD:
                    UnloadPauseResources();
                    HideMenusAndReturnToHUD();
                    break;

                case KI_EVENT_INVITE_FAILED:
                    HandleInviteFailed(lpEvent);
                    break;

                case KI_EVENT_INVITE_COMPLETE:
                {
                    GuiCommandWire16<135> lCommand;
                    mpStateInterface->GetOutputEventQueue()->AddEvent(
                        reinterpret_cast<const CgsModule::Event*>(&lCommand), KI_CHANNEL_GUI_OUT,
                        static_cast<s32>(sizeof(lCommand)));   // X360 record size 16
                    break;
                }

                case KI_EVENT_OVERLAY_COMPLETE:
                    HandleOverlayComplete(lpEvent);
                    break;

                case KI_EVENT_TO_CAR_SELECT:
                    SendStateEvent("TO_CSELECT");
                    break;

                case KI_EVENT_PLAYER_LOBBY_LIST:
                    HandlePlayerLobbyListEvent(lpEvent);
                    break;

                case KI_EVENT_PLAYER_STATS:
                    HandlePlayerStatsEvent(lpEvent);
                    break;

                case KI_EVENT_GAME_PARAMS_CHANGED:
                    HandleGameParamsChangedEvent(lpEvent);
                    break;

                case KI_EVENT_SPLASH_SCREEN:
                    HandleSplashScreenRequests(lpEvent);
                    break;

                case KI_EVENT_NETWORK_LEFT_GAME:
                    HandleLeftGameEvent(lpEvent);
                    break;

                case KI_EVENT_LEAVING_GAME_FAILED:
                    HandleLeavingGameFailedEvent(lpEvent);
                    break;

                case KI_EVENT_PERFORM_PAUSE_OPTION:
                    // Only actionable while the player is driving with the menus down.
                    if (meSubState == E_SUBSTATE_FREE_BURNING)
                    {
                        PerformPauseOption(
                            reinterpret_cast<const PerformPauseOptionPayload*>(lpEvent)->mePauseOption);
                        mbShownFromPause = false;
                    }
                    break;

                case KI_EVENT_UI_VISIBLE:
                    if (meSubState == E_SUBSTATE_FREE_BURNING)
                    {
                        CGS_ASSERT(lpEvent != 0, "lpUiVisibleEvent != NULL");   // cpp:519 (non-fatal)
                        if (reinterpret_cast<const UiVisiblePayload*>(lpEvent)->miUiVisible == 0)
                        {
                            HideHUDAndEnterMenus();
                            ShowPauseScreen();
                        }
                    }
                    break;

                case KI_EVENT_EVERY_PLAYER_STATUS:
                    mChallengeListComponent.HandleEveryPlayerCompletionStatus(
                        reinterpret_cast<const BrnGameState::GameStateModuleIO::FburnChallengeEveryPlayerStatusData*>(
                            lpEvent));
                    break;

                default:
                    // cpp:748 -- streamed as "Unexpected event received : " << liEventId <<
                    // " in " << <file> << " at line " << 748 << "\n"; lowered to the static
                    // text per project policy. Non-fatal.
                    CGS_ASSERT(false, "Unexpected event received : ");
                    break;
            }
        }

        // ---- the EA-trax debounce pair (armed by the free-burn controller handler) ------
        // While the "disable next track" hold is running the skip timer is pinned at zero;
        // otherwise the skip timer runs down and fires the id-461 command as it expires.
        // Both run on the cache's frame delta (GuiCache's leading word).
        if (mfTimeToDisableNextEATrack > KF_ZERO_TIME)
        {
            mfTimeToDisableNextEATrack -= mpGuiCache->mfTimeStep;
            mfTimeUntilNextEATrack = KF_ZERO_TIME;
        }
        else if (mfTimeUntilNextEATrack > KF_ZERO_TIME)
        {
            mfTimeUntilNextEATrack -= mpGuiCache->mfTimeStep;
            // `bgt` skips the post, so an unordered compare posts too.
            if (!(mfTimeUntilNextEATrack > KF_ZERO_TIME))
            {
                GuiCommandWire16<461> lNextTrackCommand;
                mpStateInterface->GetOutputEventQueue()->AddEvent(
                    reinterpret_cast<const CgsModule::Event*>(&lNextTrackCommand),
                    KI_CHANNEL_GUI_OUT,
                    static_cast<s32>(sizeof(lNextTrackCommand)));   // X360 record size 16
            }
        }

        // ---- the menu pass: skipped entirely while the player is out driving ------------
        if (meSubState != E_SUBSTATE_FREE_BURNING)
        {
            mRouteInfoDisplay.Update(mpInGuiEventQueue);
            mPlayerNameComponent.Update();
            mOptionComponent.Update();
            mPauseComponent.Update();
            mPlayerStatsDisplay.Update();
            mSettingToggle.Update();
            mViewEventOptions.Update();

            switch (meSubState)
            {
                case E_SUBSTATE_MAP:
                {
                    CrashNavMap::Update();

                    // The one-shot cursor snap: the first map update after the page comes up
                    // centres the map on the local player and grows the icons.
                    if (mbFirstMapUpdate && mpGuiCache != 0 && mbIsScreenLoaded)
                    {
                        const Vector4* lpPlayerInfo = &mpGuiCache->mv4WorldCameraPosition;
                        CGS_ASSERT(lpPlayerInfo != 0, "lpPlayerInfo");   // cpp:813 (non-fatal)

                        // The X360 permutes the world position into the 2-D map point with
                        // unk_82CDA450 == 00010203 18191A1B 00010203 00010203, i.e. the
                        // (X,Y,Z,W) world vector becomes (X,Z,X,X).
                        Vector2 lv2MapLocation;
                        lv2MapLocation.x = lpPlayerInfo->x;
                        lv2MapLocation.y = lpPlayerInfo->z;
                        lv2MapLocation.z = lpPlayerInfo->x;
                        lv2MapLocation.w = lpPlayerInfo->x;
                        mMainMapComponent.SnapToLocation(lv2MapLocation);

                        if (CrashNavMap::PlaceCursorOnPlayer())
                        {
                            mpIconManager->meIconSizeMode = MapIconManager::E_ICONSIZE_LARGE;
                            mbFirstMapUpdate = false;
                        }
                    }
                    break;
                }

                case E_SUBSTATE_CHALLENGES:
                    mChallengeToggle.Update();
                    mChallengeListComponent.Update();
                    break;

                case E_SUBSTATE_CONTROLLER_DISABLE_DELAY:
                    // Swallow input for KI_CONTROLLER_DISABLE_DELAY_FRAME_COUNT frames after
                    // the menus came down, then hand the player back to free burning.
                    --miDelayFrameCount;
                    if (miDelayFrameCount < 0)
                    {
                        meSubState = E_SUBSTATE_FREE_BURNING;
                    }
                    break;

                case E_SUBSTATE_SETTINGS:
                    // The accept prompt only appears once a setting has actually moved.
                    if (mbSettingsChanged)
                    {
                        mHelpItemAccept.SetItem("$CAPS_BUTTON_ACCEPT",
                                                ButtonIconComponent::E_PADBUTTON_SELECT,
                                                ButtonIconComponent::E_PADBUTTON_INVISIBLE);
                    }
                    else
                    {
                        // The empty-string rodata sentinel (&unk_820046A7).
                        mHelpItemAccept.SetItem("",
                                                ButtonIconComponent::E_PADBUTTON_INVISIBLE,
                                                ButtonIconComponent::E_PADBUTTON_INVISIBLE);
                    }
                    break;

                default:
                    break;
            }
        }

        // Every X360 arm tails into this same Clear (the duplicated epilogues).
        lpInQueue->Clear();
    }

    // ================================================================================
    //  UpdateSoundSettings  @ 0x8249AD00  (cpp:4590)
    //
    //  Publish the two sound-volume settings the options model currently holds. Called
    //  by HandleSettingChanged when a volume toggle moves.
    // ================================================================================
    void OnlineGameRoomPlayerInfo::UpdateSoundSettings()
    {
        CGS_ASSERT(mpStateInterface != 0, "mpStateInterface");   // cpp:4636 (non-fatal)

        // { 8, 463, 12, music, sfx } on channel 40, X360 record size 20. The X360 copies
        // the two adjacent option words out as one doubleword; they are the two volume
        // members in order.
        GuiEventSoundVolumesWire lSoundVolumes(mCrashNavOptionsData.meMusicVolume,
                                               mCrashNavOptionsData.meSFXVolume);
        mpStateInterface->GetOutputEventQueue()->AddEvent(
            reinterpret_cast<const CgsModule::Event*>(&lSoundVolumes), KI_CHANNEL_GUI_OUT,
            static_cast<s32>(sizeof(lSoundVolumes)));
    }
}
