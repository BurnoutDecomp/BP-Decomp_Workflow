#include "GameSource/Gui/Flow/Overlay/States/BrnBaseOverlayState.h"

#include <cstring>   // std::strlen / std::strncpy (the inlined StrCpy)

#include "GameShared/GameClasses/Core/CgsAssert.h"                        // CGS_ASSERT
#include "GameShared/GameClasses/Gui/CgsGuiShared.h"                      // GuiAccessPointers::GetFlaptManager
#include "GameShared/GameClasses/Gui/Model/State/CgsGuiStateInterface.h"  // CgsGui::StateInterface
#include "GameShared/GameClasses/Module/CgsVariableEventQueue.h"          // VariableEventQueue<18432,16> (the in-queue view)
#include "GameSource/Gui/BrnGuiEventTypeDefs.h"                           // GuiOverlayShowingNotification (event 190)
#include "GameSource/Gui/Flapt/BrnFlaptFileRef.h"                         // BrnFlapt::FileRef (by value)
#include "GameSource/Gui/Flapt/BrnFlaptManager.h"                         // BrnFlapt::FlaptManager::GetFile

// BrnGui::BaseOverlayState -- reconstructed from BURNOUT_X360_ARTIST.XEX.
//
// Bodied here (7 ledger functions, DWARF primary file
// GameSource/Gui/Flow/Overlay/States/BrnBaseOverlayState.cpp):
//   BaseOverlayState::OnEnter                @0x824B1E60
//   BaseOverlayState::Prepare                @0x824B1F80
//   BaseOverlayState::SetupOverlay           @0x824B1690
//   BaseOverlayState::SetupOverlayComponents @0x824B18B8
//   BaseOverlayState::GetCache               @0x824B2490
//   BaseOverlayState::UpdateWFInfo           @0x824B25D0
//   BaseOverlayState::OnLeave                @0x824B2DC8
// plus, recovered at their real home:
//   BaseOverlayState::Update                 @0x824B2B38  (ledger-drift: DWARF-
//   BaseOverlayState::UpdatePermanent        @0x824B2670   misattributed to header
//     grab-bag TUs -- CgsStrStream.h / CgsVariableEventQueue.h -- and marked reviewed
//     there with no committed bodies; landed here, the grab-bag-landing pattern)
//   ResetOverlayComponents (DWARF cpp:659) and UpdateWFTransComplete (DWARF cpp:140):
//     no standalone X360 symbols -- recovered from their inlined instances (the 12
//     zero stores @0x824B1F0C/@0x824B2020/@0x824B2E50; the transition-flag test/clear
//     pairs inside Update @0x824B2C3C/@0x824B2CC8).
//
// The statics' values are read from the decrypted XEX .rodata: the observed-event
// table @0x82063CC4 {21, 6, 64, 187, 188}, the counts + override table
// @0x82063CD8 {5, 6, 1}, the component-name strings @0x82063CE4.., the icon-state
// pointer pair @0x82063D6C -> {"invisible" @0x8204B4F8, "warning" @0x820638DC}, and
// KE_POPUP_PARAM_LOOKUP @0x82063D74 {0, 0, 9}.

namespace BrnGui
{
namespace
{
    // The state IN-queue is an 18KB variable event queue (the X360
    // VariableEventQueue<18432,16> instantiation drained by GetCache/UpdateWFInfo --
    // the same idiom as BrnBootLegal / BrnCredits).
    typedef CgsModule::VariableEventQueue<18432, 16> OverlayStateInQueue;

    // Overlay wire event ids on the state in-queue (X360; see the header banner for
    // the PS3 id divergence): 64 = the GuiCache pointer broadcast, 187 = the overlays
    // director's full-info response, 189 = the complete event OnLeave posts.
    const s32 KI_EVENT_GUI_CACHE          = 64;
    const s32 KI_EVENT_OVERLAY_FULL_INFO  = 187;
}

// DWARF cpp:57 -- PopupParamTypes -> CgsLanguage::LanguageManager::ParameterFormatType
// (raw integers per the TextFieldRef house style): UNUSED -> 0, STRING -> 0,
// STRING_ID -> 9. XEX .rodata @0x82063D74.
const s32 KE_POPUP_PARAM_LOOKUP[CgsGui::E_POPUPPARAMTYPES_COUNT] = { 0, 0, 9 };

// ---- statics (DWARF cpp:26-51; XEX .rodata @0x82063CC4..0x82063D6C) ----
const s32  BaseOverlayState::maiEventToObserve[5]      = { 21, 6, 64, 187, 188 };
const s32  BaseOverlayState::miNumEventsObserved       = 5;
const s32  BaseOverlayState::maiEventTypeOverridden[1] = { 6 };
const s32  BaseOverlayState::miNumOverriddenEvents     = 1;
const char BaseOverlayState::macOverlayComponentName[12]   = "Overlays_mc";
const char BaseOverlayState::macTitleTextFieldName[25]     = "Overlays_mc_Title_txt_mc";
const char BaseOverlayState::macMessageTextFieldName[24]   = "Overlays_mc_Main_txt_mc";
const char BaseOverlayState::macIconComponentName[21]      = "Overlays_mc_Icons_mc";
const char* const BaseOverlayState::mapcIconStateNames[CgsGui::E_POPUPICONS_COUNT] =
    { "invisible", "warning" };
const char BaseOverlayState::macHelpItem1ComponentName[22] = "Overlays_mc_helpItem0";
const char BaseOverlayState::macHelpItem2ComponentName[22] = "Overlays_mc_helpItem1";

// DWARF cpp:659 -- no standalone X360 symbol (always inlined; recovered from the 12
// zero stores in OnEnter/Prepare/OnLeave): drop every bound component handle. Each
// SetInvalid is itself inline (the icon's and help items' mAptRef pairs, then the
// two 3-word text-field handles -- 12 words in all, matching the asm exactly).
void BaseOverlayState::ResetOverlayComponents()
{
    mIconComponent.SetInvalid();
    mHelpItem1Component.SetInvalid();
    mHelpItem2Component.SetInvalid();
    mTitleTextField.SetInvalid();
    mMessageTextField.SetInvalid();
}

// @ 0x824B1E60
void BaseOverlayState::OnEnter()
{
    meLeaveMethod   = GuiOverlayCompleteEvent::E_LEAVEMETHOD_NONE;
    meInternalState = E_OVERLAYINTERNALSTATE_START;
    mpGuiCache      = NULL;

    mpStateInterface->RegisterForEvents(maiEventToObserve, miNumEventsObserved);

    mOverlayComponent.Construct(macOverlayComponentName, mpStateInterface, NULL);
    // The icon takes the icon-state name table as its third Construct argument (the
    // X360 passes @0x82063D6C in r6; the virtual Construct body only stores the
    // state interface).
    mIconComponent.Construct(macIconComponentName, mpStateInterface, mapcIconStateNames);
    mHelpItem1Component.Construct(macHelpItem1ComponentName, mpStateInterface, NULL);
    mHelpItem2Component.Construct(macHelpItem2ComponentName, mpStateInterface, NULL);

    ResetOverlayComponents();

    // Virtual dispatches, in the X360 order: the concrete popup family fills in its
    // type (vtbl +0x30), then the flash file is bound (vtbl +0x24).
    FillInPopupType();
    Prepare();
}

// @ 0x824B1F80
void BaseOverlayState::Prepare()
{
    // Both accessors carry the X360's inlined NULL asserts
    // ("mpAccessPointers != NULL", CgsGuiStateInterface.h:344 /
    //  "NULL != mpFlaptManager", CgsGuiShared.h:194).
    CgsGui::GuiAccessPointers* lpAccessPointers = mpStateInterface->GetAccessPointers();
    BrnFlapt::FlaptManager*    lpFlaptManager   = lpAccessPointers->GetFlaptManager();

    BrnFlapt::FileRef lFile;
    lpFlaptManager->GetFile(&lFile, 0);

    mOverlayComponent.Prepare(macOverlayComponentName, lFile, NULL);

    ResetOverlayComponents();
}

// @ 0x824B2DC8
void BaseOverlayState::OnLeave()
{
    // Report how the popup was left: {header 16/189/16} + {mCurrentOverlayId,
    // meLeaveMethod} -- 32 bytes on channel 40 of the state's output queue.
    GuiOverlayCompleteEvent lCompleteEvent;
    lCompleteEvent.Construct(mCurrentOverlayId, meLeaveMethod);
    mpStateInterface->GetOutputEventQueue()->AddEvent(
        reinterpret_cast<const CgsModule::Event*>(&lCompleteEvent), 40,
        static_cast<s32>(sizeof(GuiOverlayCompleteEvent)));

    // Release the priority claim on the full-info event and the observed set.
    mpStateInterface->PriorityUnRegisterForEvent(KI_EVENT_OVERLAY_FULL_INFO);
    mpStateInterface->UnRegisterForEvents(maiEventToObserve, miNumEventsObserved);

    ResetOverlayComponents();
}

// DWARF cpp:140 -- recovered from the two inlined instances in Update
// (@0x824B2C3C / @0x824B2CC8): consume the transition-complete flag.
bool BaseOverlayState::UpdateWFTransComplete()
{
    if (mOverlayComponent.GetTransitionComplete())
    {
        mOverlayComponent.SetTransitionComplete(false);
        return true;
    }
    return false;
}

// @ 0x824B2B38 -- the popup state-machine pump: one switch whose cases FALL THROUGH
// so a popup can advance several phases in a single frame (the X360 jump table's
// case bodies chain exactly this way; each case re-stores its own tag first).
void BaseOverlayState::Update()
{
    switch (meInternalState)
    {
    case E_OVERLAYINTERNALSTATE_START:
        meInternalState = E_OVERLAYINTERNALSTATE_START;
        GetCache();
        mOverlayComponent.RunOverlay(mpcFlashFileId, "waiting");
        SetupOverlayComponents("waiting");
        // Claim the overridden events (the controller-action id 6) under the
        // full-info key while the popup is up (released by OnLeave).
        mpStateInterface->PriorityRegisterForEvent(KI_EVENT_OVERLAY_FULL_INFO,
                                                   maiEventTypeOverridden,
                                                   miNumOverriddenEvents);
        // fall through
    case E_OVERLAYINTERNALSTATE_WFINIT:
    {
        meInternalState = E_OVERLAYINTERNALSTATE_WFINIT;
        // Ask the overlays director for the full overlay description (header-only
        // record {1, 186, 12}, 16 bytes on channel 40).
        GuiOverlayFullInfoRequest lRequest;
        mpStateInterface->GetOutputEventQueue()->AddEvent(
            reinterpret_cast<const CgsModule::Event*>(&lRequest), 40,
            static_cast<s32>(sizeof(GuiOverlayFullInfoRequest)));
    }
        // fall through
    case E_OVERLAYINTERNALSTATE_SETUPOVERLAY:
        meInternalState = E_OVERLAYINTERNALSTATE_SETUPOVERLAY;
        if (!UpdateWFInfo())
            break;
        mOverlayComponent.RunOverlay(mpcFlashFileId, "transin");
        // fall through
    case E_OVERLAYINTERNALSTATE_WFTRANSIN:
        meInternalState = E_OVERLAYINTERNALSTATE_WFTRANSIN;
        if (!UpdateWFTransComplete())
            break;
        {
            // Tell the director the popup is on screen (the 8-byte id record; the
            // OutputGuiEvent<GuiOverlayShowingNotification> instantiation @0x824B2C78).
            GuiOverlayShowingNotification lShowing;
            lShowing.mOverlayId = mCurrentOverlayId;
            mpStateInterface->OutputGuiEvent(lShowing);
        }
        // fall through
    case E_OVERLAYINTERNALSTATE_RUNNING:
        meInternalState = E_OVERLAYINTERNALSTATE_RUNNING;
        if (UpdateRunning())   // virtual (vtbl +0x28)
        {
            mOverlayComponent.RunOverlay(mpcFlashFileId, "transout");
            meInternalState = E_OVERLAYINTERNALSTATE_WFTRANSOUT;
        }
        break;

    case E_OVERLAYINTERNALSTATE_WFTRANSOUT:
        meInternalState = E_OVERLAYINTERNALSTATE_WFTRANSOUT;
        if (!UpdateWFTransComplete())
            break;
        SendStateEvent("DONE");
        // fall through
    case E_OVERLAYINTERNALSTATE_DONE:
        meInternalState = E_OVERLAYINTERNALSTATE_DONE;
        break;

    default:
        // cpp:305 -- the X360 streams "Invalid State : " + meInternalState + " !";
        // folded static per convention.
        CGS_ASSERT(false, "Invalid State : ");
        break;
    }

    UpdatePermanent();
    reinterpret_cast<OverlayStateInQueue*>(mpInGuiEventQueue)->Clear();
}

// @ 0x824B2670 -- walk (and discard) whatever is left on the state's in-queue.
void BaseOverlayState::UpdatePermanent()
{
    OverlayStateInQueue* lpInQueue = reinterpret_cast<OverlayStateInQueue*>(mpInGuiEventQueue);

    const CgsModule::Event* lpEvent = NULL;
    s32 liSize = 0;
    lpInQueue->GetFirstEvent(&lpEvent, &liSize);
    while (lpEvent != NULL)
        lpInQueue->GetNextEvent(lpEvent, &lpEvent, &liSize);
}

// @ 0x824B2490
void BaseOverlayState::GetCache()
{
    // Non-gating tripwire: the cache must not already be latched (cpp:353).
    CGS_ASSERT(mpGuiCache == NULL, "mpGuiCache == NULL");

    OverlayStateInQueue* lpInQueue = reinterpret_cast<OverlayStateInQueue*>(mpInGuiEventQueue);

    const CgsModule::Event* lpEvent = NULL;
    s32 liSize = 0;
    s32 liEventId = lpInQueue->GetFirstEvent(&lpEvent, &liSize);
    while (lpEvent != NULL)
    {
        if (liEventId == KI_EVENT_GUI_CACHE)
        {
            // The payload's leading word is the GuiCache pointer. The X360 streams
            // the message ("Invalid gui cached", cpp:367) and stores regardless
            // (non-gating), exactly as here.
            GuiCache* lpCache = *reinterpret_cast<GuiCache* const*>(lpEvent);
            CGS_ASSERT(lpCache != NULL, "Invalid gui cached");
            mpGuiCache = lpCache;
        }

        liEventId = lpInQueue->GetNextEvent(lpEvent, &lpEvent, &liSize);
    }

    // Non-gating tripwire: a cache must have arrived (cpp:374).
    CGS_ASSERT(mpGuiCache != NULL, "mpGuiCache");
}

// @ 0x824B25D0
bool BaseOverlayState::UpdateWFInfo()
{
    OverlayStateInQueue* lpInQueue = reinterpret_cast<OverlayStateInQueue*>(mpInGuiEventQueue);

    const CgsModule::Event* lpEvent = NULL;
    s32 liSize = 0;
    s32 liEventId = lpInQueue->GetFirstEvent(&lpEvent, &liSize);
    while (lpEvent != NULL)
    {
        if (liEventId == KI_EVENT_OVERLAY_FULL_INFO)
        {
            const GuiOverlayFullInfoResponse* lpResponse =
                reinterpret_cast<const GuiOverlayFullInfoResponse*>(lpEvent);

            mCurrentOverlayId = lpResponse->mNameId;
            SetupOverlay(lpResponse);   // virtual (vtbl +0x2C)
            return true;
        }

        liEventId = lpInQueue->GetNextEvent(lpEvent, &lpEvent, &liSize);
    }

    return false;
}

// @ 0x824B1690
void BaseOverlayState::SetupOverlay(const GuiOverlayFullInfoResponse* lpResponse)
{
    mTitleTextField.SetLocalisedText(lpResponse->macTitleId, 9);

    if (lpResponse->miMessageParamsUsed != 0)
    {
        // Build the positional-parameter arrays: each parameter string is copied into
        // a 64-byte stack slot (the inlined StrCpy: debug-assert the source fits,
        // CgsStringUtils.h:55, then a 64-char strncpy), and its format type is looked
        // up from the param-type table.
        char lacParamStrings[GuiOverlayFullInfoResponse::MKI_MAX_PARAMS_IN_MESSAGE]
                            [CgsGui::GuiPopupParameter::KI_MAX_PARAM_STRING_LENGTH];
        const char* lapcParams[GuiOverlayFullInfoResponse::MKI_MAX_PARAMS_IN_MESSAGE];
        s32         laeParamFormatTypes[GuiOverlayFullInfoResponse::MKI_MAX_PARAMS_IN_MESSAGE];

        for (s32 liParam = 0; liParam < lpResponse->miMessageParamsUsed; ++liParam)
        {
            const CgsGui::GuiPopupParameter& lrParam = lpResponse->maMessageParams[liParam];

            CGS_ASSERT(std::strlen(lrParam.macParameter) <
                           CgsGui::GuiPopupParameter::KI_MAX_PARAM_STRING_LENGTH,
                       "String too long: ");
            std::strncpy(lacParamStrings[liParam], lrParam.macParameter,
                         CgsGui::GuiPopupParameter::KI_MAX_PARAM_STRING_LENGTH);

            lapcParams[liParam]          = lacParamStrings[liParam];
            laeParamFormatTypes[liParam] = KE_POPUP_PARAM_LOOKUP[lrParam.meParamType];
        }

        mMessageTextField.SetLocalisedText(lpResponse->macMessageId, 9,
                                           lpResponse->miMessageParamsUsed,
                                           lapcParams, laeParamFormatTypes);
    }
    else
    {
        mMessageTextField.SetLocalisedText(lpResponse->macMessageId, 9);
    }

    // Non-gating range tripwires (cpp:490/491), then the indexed icon state.
    CGS_ASSERT(lpResponse->meIcon >= CgsGui::E_POPUPICONS_INVISIBLE,
               "lpResponse->meIcon >= CgsGui::E_POPUPICONS_INVISIBLE");
    CGS_ASSERT(lpResponse->meIcon <= CgsGui::E_POPUPICONS_WARNING,
               "lpResponse->meIcon <= CgsGui::E_POPUPICONS_WARNING");
    mIconComponent.SetState(mapcIconStateNames[lpResponse->meIcon]);
}

// @ 0x824B18B8
void BaseOverlayState::SetupOverlayComponents(const char* lpcTransition)
{
    if (lpcTransition == NULL)
    {
        // Gating on the X360 (the assert arm returns immediately; cpp:597).
        CGS_ASSERT(NULL != lpcTransition, "NULL != lpcTransition");
        return;
    }

    BrnFlapt::MovieClipRef* lpTransitionMovieClipRef =
        mOverlayComponent.GetTransitionMovieClipRef();

    // Non-gating tripwires (cpp:607/608; the first is the compiler-folded
    // &member != NULL check the X360 still emits).
    CGS_ASSERT(NULL != lpTransitionMovieClipRef, "NULL != lpTransitionMovieClipRef");
    CGS_ASSERT(true == lpTransitionMovieClipRef->IsValid(),
               "true == lpTransitionMovieClipRef->IsValid( )");

    // Locate the popup's children under the transition clip. The finds are asserted
    // but NON-gating (the X360 proceeds with the -- then unwritten -- refs on a miss),
    // so the out-refs are deliberately left uninitialised, exactly as the X360 stack
    // slots are.
    BrnFlapt::MovieClipRef lHelpItem0;
    BrnFlapt::MovieClipRef lHelpItem1;
    BrnFlapt::MovieClipRef lIcon;

    bool lbFound = lpTransitionMovieClipRef->TryFindChildComponentRecursively("helpItem0", &lHelpItem0);
    CGS_ASSERT(true == lbFound,
               "true == lpTransitionMovieClipRef->TryFindChildComponentRecursively( \"helpItem0\", &lHelpItem0 )");

    lbFound = lpTransitionMovieClipRef->TryFindChildComponentRecursively("helpItem1", &lHelpItem1);
    CGS_ASSERT(true == lbFound,
               "true == lpTransitionMovieClipRef->TryFindChildComponentRecursively( \"helpItem1\", &lHelpItem1 )");

    lbFound = lpTransitionMovieClipRef->TryFindChildComponentRecursively("Icons_mc", &lIcon);
    CGS_ASSERT(true == lbFound,
               "true == lpTransitionMovieClipRef->TryFindChildComponentRecursively( \"Icons_mc\", &lIcon )");

    mIconComponent.Prepare(&lIcon);              // virtual (vtbl +0x04)
    mHelpItem1Component.Prepare(&lHelpItem0);
    mHelpItem2Component.Prepare(&lHelpItem1);

    // Bind the title/message text fields: find the named "_mc" wrapper, hide it, and
    // pull the actual text field off its parent.
    BrnFlapt::MovieClipRef lTextMovieClip;
    if (lpTransitionMovieClipRef->TryFindChildComponentRecursively("Title_txt_mc", &lTextMovieClip))
    {
        lTextMovieClip.SetVisible(false);
        BrnFlapt::MovieClipRef lParentMovieClip;
        lTextMovieClip.GetParent(&lParentMovieClip);

        BrnFlapt::TextFieldRef lTextField;
        mTitleTextField = *lParentMovieClip.FindChildTextField(&lTextField, "Title_txt");
    }
    else
    {
        mTitleTextField.SetInvalid();
    }

    if (lpTransitionMovieClipRef->TryFindChildComponentRecursively("Main_txt_mc", &lTextMovieClip))
    {
        lTextMovieClip.SetVisible(false);
        BrnFlapt::MovieClipRef lParentMovieClip;
        lTextMovieClip.GetParent(&lParentMovieClip);

        BrnFlapt::TextFieldRef lTextField;
        mMessageTextField = *lParentMovieClip.FindChildTextField(&lTextField, "Main_txt");
    }
    else
    {
        mMessageTextField.SetInvalid();
    }
}
}
