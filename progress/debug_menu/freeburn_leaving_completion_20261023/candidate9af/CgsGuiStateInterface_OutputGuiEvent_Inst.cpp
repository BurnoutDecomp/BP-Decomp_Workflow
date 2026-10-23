// ============================================================================
// b5-decomp/src/GameShared/GameClasses/Gui/Model/State/CgsGuiStateInterface_OutputGuiEvent_Inst.cpp
//
// The 66 X360-attested explicit instantiations of
// CgsGui::StateInterface::OutputGuiEvent<T> (the channel-40 output GUI event publisher).
// The single shared body lives in CgsGuiStateInterface.h; each instantiation compiles to the
// identical stack-build-a-GuiEventWrapper<T,40> + VariableEventQueue<65536,16>::AddEvent(
// &wrapper, 40, sizeof(wrapper)) sequence, differing only in the per-T sizeof / GetEventType()
// constants that fall out of T. Reuses the homed GUI-event payload types (their homes are
// #included below); newly-homed output-family payloads carry (id,size) read from the same asm.
// ============================================================================

#include "GameShared/GameClasses/Gui/Model/State/CgsGuiStateInterface.h"
#include "GameShared/GameClasses/Gui/View/AptInterface/CgsAptCommunicator.h"
#include "GameSource/Gui/BrnGuiDemangledEventTypes.h"
#include "GameSource/Gui/Events/BrnGuiEventAudioTrax.h"   // GuiEventAudioTraxUpdate (moved out of the demangled header)
#include "GameSource/Gui/BrnGuiEventTypeDefs.h"
#include "GameSource/Gui/BrnGuiVideoEvents.h"
#include "GameSource/Gui/Events/BrnGuiEventNetworkCreateGame.h"
#include "GameSource/Gui/Events/BrnGuiEventNetworkGameParams.h"

namespace CgsGui
{
    template int StateInterface::OutputGuiEvent<BrnGui::GuiAudioEvent>(BrnGui::GuiAudioEvent&);  // 0x824367D8
    template int StateInterface::OutputGuiEvent<BrnGui::GuiAudioTriggerEvent>(BrnGui::GuiAudioTriggerEvent&);  // 0x82436890
    template int StateInterface::OutputGuiEvent<BrnGui::GuiAutosaveRequestEvent>(BrnGui::GuiAutosaveRequestEvent&);  // 0x824937E0
    template int StateInterface::OutputGuiEvent<BrnGui::GuiChallengeSelectedEvent>(BrnGui::GuiChallengeSelectedEvent&);  // 0x82436778
    template int StateInterface::OutputGuiEvent<BrnGui::GuiChangeCarEvent>(BrnGui::GuiChangeCarEvent&);  // 0x82493B98
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEvent100PerCentComplete>(BrnGui::GuiEvent100PerCentComplete&);  // 0x824C31C8
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventActivateCarSelect>(BrnGui::GuiEventActivateCarSelect&);  // 0x82493B48
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventActivateCrashNav>(BrnGui::GuiEventActivateCrashNav&);  // 0x82493938
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventAudioGenericSequence>(BrnGui::GuiEventAudioGenericSequence&);  // 0x824C2DA8
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventAudioSettings>(BrnGui::GuiEventAudioSettings&);  // 0x82493728
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventAudioTraxLastPlayedIndexes>(BrnGui::GuiEventAudioTraxLastPlayedIndexes&);  // 0x824C3110
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventAudioTraxPreview>(BrnGui::GuiEventAudioTraxPreview&);  // 0x824C3050
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventAudioTraxUpdate>(BrnGui::GuiEventAudioTraxUpdate&);  // 0x824C30A0
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventAudioVoiceOver>(BrnGui::GuiEventAudioVoiceOver&);  // 0x824C3178
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventChallengedEventDataRequest>(BrnGui::GuiEventChallengedEventDataRequest&);  // 0x824C2F50
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventControllerSettings>(BrnGui::GuiEventControllerSettings&);  // 0x82493778
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventCustomeEventCreate>(BrnGui::GuiEventCustomeEventCreate&);  // 0x824C2FF0
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventNetworkConnect>(BrnGui::GuiEventNetworkConnect&);  // 0x824C2E98
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventNetworkCreateGame>(BrnGui::GuiEventNetworkCreateGame&);  // 0x82493ED8
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventNetworkCustomMatchJoin>(BrnGui::GuiEventNetworkCustomMatchJoin&);  // 0x82493C48
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventNetworkCustomMatchSearch>(BrnGui::GuiEventNetworkCustomMatchSearch&);  // 0x82493BE8
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventNetworkGameParams>(BrnGui::GuiEventNetworkGameParams&);  // 0x82436AD0
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventNetworkNewsAndTOS>(BrnGui::GuiEventNetworkNewsAndTOS&);  // 0x82493E38
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventNetworkOutputPlayerTexture>(BrnGui::GuiEventNetworkOutputPlayerTexture&);  // 0x82436D40
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventNetworkQuickMatch>(BrnGui::GuiEventNetworkQuickMatch&);  // 0x82494158
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventNetworkSelectedPlayerOption>(BrnGui::GuiEventNetworkSelectedPlayerOption&);  // 0x82436CA0
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventNetworkSplashEvent>(BrnGui::GuiEventNetworkSplashEvent&);  // 0x82493880
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventOnlineInviteEvent>(BrnGui::GuiEventOnlineInviteEvent&);  // 0x824369C0
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventOnlineShowProfile>(BrnGui::GuiEventOnlineShowProfile&);  // 0x82436B30
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventPlayVideo>(BrnGui::GuiEventPlayVideo&);  // 0x82476C68
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventPostEventFreeCarSequenceStart>(BrnGui::GuiEventPostEventFreeCarSequenceStart&);  // 0x824C2DF8
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventPostEventRankUpSequenceStart>(BrnGui::GuiEventPostEventRankUpSequenceStart&);  // 0x824C2E48
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventRequestCompressedCamPic>(BrnGui::GuiEventRequestCompressedCamPic&);  // 0x82436D90
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventRequestSpecificPreSetRaces>(BrnGui::GuiEventRequestSpecificPreSetRaces&);  // 0x82493E88
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventRequestTraining>(BrnGui::GuiEventRequestTraining&);  // 0x82436840
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventRoadRuleDataRequest>(BrnGui::GuiEventRoadRuleDataRequest&);  // 0x82476EE8
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventRoadRuleFail>(BrnGui::GuiEventRoadRuleFail&);  // 0x82436950
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventRoadRuleModeRequest>(BrnGui::GuiEventRoadRuleModeRequest&);  // 0x82436B90
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventRunFsm>(BrnGui::GuiEventRunFsm&);  // 0x824938D0
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventScoreboardRequestEvScoreTarget>(BrnGui::GuiEventScoreboardRequestEvScoreTarget&);  // 0x82493F88
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventScoreboardRequestGamercardEvent>(BrnGui::GuiEventScoreboardRequestGamercardEvent&);  // 0x82493D38
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventScoreboardRequestIndexEvent>(BrnGui::GuiEventScoreboardRequestIndexEvent&);  // 0x82493FF8
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventScoreboardRequestTableEvent>(BrnGui::GuiEventScoreboardRequestTableEvent&);  // 0x82494098
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventScoreboardRequestVariationEvent>(BrnGui::GuiEventScoreboardRequestVariationEvent&);  // 0x82494048
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventSetPlayer0ControllerPort>(BrnGui::GuiEventSetPlayer0ControllerPort&);  // 0x82476D88
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventShowHideHud>(BrnGui::GuiEventShowHideHud&);  // 0x82493988
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventStopVideo>(BrnGui::GuiEventStopVideo&);  // 0x82476CF8
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventTickerClearMessages>(BrnGui::GuiEventTickerClearMessages&);  // 0x82436DF0
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventTickerCustomMessage>(BrnGui::GuiEventTickerCustomMessage&);  // 0x82436C40
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventTrophyCarUnlock>(BrnGui::GuiEventTrophyCarUnlock&);  // 0x82476F38
    template int StateInterface::OutputGuiEvent<BrnGui::GuiEventVoipSettings>(BrnGui::GuiEventVoipSettings&);  // 0x82493CE8
    template int StateInterface::OutputGuiEvent<BrnGui::GuiImageGalleryRequestCollectedDataEvent>(BrnGui::GuiImageGalleryRequestCollectedDataEvent&);  // 0x824939D8
    template int StateInterface::OutputGuiEvent<BrnGui::GuiImageGalleryRequestEvent>(BrnGui::GuiImageGalleryRequestEvent&);  // 0x82493AD8
    template int StateInterface::OutputGuiEvent<BrnGui::GuiMuteDac>(BrnGui::GuiMuteDac&);  // 0x82476BB0
    template int StateInterface::OutputGuiEvent<BrnGui::GuiNetworkCustomRouteCreated>(BrnGui::GuiNetworkCustomRouteCreated&);  // 0x82493F38
    template int StateInterface::OutputGuiEvent<BrnGui::GuiOverlayRequest>(BrnGui::GuiOverlayRequest&);  // 0x82436BE0
    template int StateInterface::OutputGuiEvent<BrnGui::GuiOverlayShowingNotification>(BrnGui::GuiOverlayShowingNotification&);  // 0x824B2938
    template int StateInterface::OutputGuiEvent<BrnGui::GuiOverlayWaitFinishRequest>(BrnGui::GuiOverlayWaitFinishRequest&);  // 0x82476E98
    template int StateInterface::OutputGuiEvent<BrnGui::GuiReplayDeleteReelEvent>(BrnGui::GuiReplayDeleteReelEvent&);  // 0x824C3268
    template int StateInterface::OutputGuiEvent<BrnGui::GuiReplaySetModeEvent>(BrnGui::GuiReplaySetModeEvent&);  // 0x824C3218
    template int StateInterface::OutputGuiEvent<BrnGui::GuiRequestCarControlChangeEvent>(BrnGui::GuiRequestCarControlChangeEvent&);  // 0x82493830
    template int StateInterface::OutputGuiEvent<BrnGui::GuiSaveLoadImageExportRequested>(BrnGui::GuiSaveLoadImageExportRequested&);  // 0x82493A28
    template int StateInterface::OutputGuiEvent<BrnGui::GuiTelemetryEvent>(BrnGui::GuiTelemetryEvent&);  // 0x824940E8
    template int StateInterface::OutputGuiEvent<CgsGui::GuiEventNetworkSuspension>(CgsGui::GuiEventNetworkSuspension&);  // 0x82493A88
    template int StateInterface::OutputGuiEvent<CgsGui::GuiEventPlayMusicOnMenuStream>(CgsGui::GuiEventPlayMusicOnMenuStream&);  // 0x82476C00
    template int StateInterface::OutputGuiEvent<CgsGui::GuiEventSoundTrigger>(CgsGui::GuiEventSoundTrigger&);  // 0x824368F0
}
