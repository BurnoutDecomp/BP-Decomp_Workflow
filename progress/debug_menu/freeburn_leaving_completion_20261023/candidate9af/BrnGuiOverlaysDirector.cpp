#include "GameShared/GameClasses/Gui/Model/CgsModelModule.h"
#include "GameSource/Gui/BrnGuiOverlaysDirector.h"

#include <cstring>   // std::memcpy (the buffered -> current overlay promote)
#include <cstdlib>   // std::getenv ([FLAG PC witness] BRN_OVERLAY_DIAG)

#include "GameShared/GameClasses/Core/CgsAssert.h"                     // CGS_ASSERT
#include "GameShared/GameClasses/Development/Log/CgsLog.h"             // CgsDev::Log::gpDebugPrint / Message::gxMessageFilterFlags
#include "GameShared/GameClasses/Development/CgsStrStream.h"           // CgsDev::StrStreamBase (operator<<)
#include "GameSource/Gui/BrnGuiEventTypeDefs.h"                        // BrnGui::GuiOverlayRequest
#include "GameSource/Gui/BrnGuiDemangledEventTypes.h"                  // BrnGui::GuiEventNetworkShowFreeBurnIntro (279)
#include "GameSource/Gui/BrnGuiCache.h"                                // GuiCache::GetNumActivePlayers / GetOnlinePlayerInfo
#include "GameSource/Network/SharedIO/BrnNetworkModuleInGamePlayerStatusInterface.h" // InGamePlayerStatusData
#include "SharedClasses/DataLists/BrnPopupController.h"                // BrnResource::PopupController::GetPopup

// BrnGui::GuiOverlaysDirector.
//
// Event ids on the module input queue (the Update dispatch):
//   64  the GuiCache-ready event (payload = GuiCache*)
//   184 an overlay request (GuiOverlayRequest)         -> HandleOverlayRequest
//   186 a full-info request                            -> HandleOverlayFullInfoRequest (187)
//   188 a wait-finish request                          -> HandleWaitFinishRequest
//   189 overlay complete (the overlay state left)      -> promote the buffered overlay
//   190 overlay showing notification                   -> HandleOverlayShowingNotification
//   279 show-freeburn-intro request                    -> HandleShowFreeBurnIntroRequest
//   322 stop mode                                      -> drop a buffered online-transition overlay
// and on the output queue: 185 = start an overlay (the popup style word), 187 = full info,
// 188 = wait finished.

namespace BrnGui
{
namespace
{
    // How long the entering-online splash stays up (frames).
    const s32 KI_FRAMES_TO_SHOW_ENTERING_FREEBURN = 120;

    // The four entering/returning-online overlay names the director special-cases, in the
    // order the console compares and waves them.
    const char* const KPC_ONLINE_OVERLAYS[4] =
    {
        "OnHReturnOn", "OnCReturnOn", "OnHEnterOn", "OnCEnterOn"
    };

    // True when the id names one of the four online transition overlays (the console emits
    // the four CgsIDCompress compares inline at each site).
    bool IsOnlineTransitionOverlay(CgsID lOverlayId)
    {
        return lOverlayId == CgsIDCompress(KPC_ONLINE_OVERLAYS[0]) ||
               lOverlayId == CgsIDCompress(KPC_ONLINE_OVERLAYS[1]) ||
               lOverlayId == CgsIDCompress(KPC_ONLINE_OVERLAYS[2]) ||
               lOverlayId == CgsIDCompress(KPC_ONLINE_OVERLAYS[3]);
    }

    // [FLAG PC witness] NOT CONSOLE CODE. `[overlay] <what> <name> ...`, opt-in behind
    // BRN_OVERLAY_DIAG=1, first 64 lines per run: the director's request / start / complete
    // traffic, so an offline or online overlay can be told apart in a log.
    void OverlayWitness(const char* lpcWhat, CgsID lOverlayId, s32 liValue)
    {
        static s32 siEnabled = -1;
        static s32 siLines   = 0;
        if (siEnabled < 0)
        {
            const char* lpcEnv = std::getenv("BRN_OVERLAY_DIAG");
            siEnabled = (lpcEnv != NULL && lpcEnv[0] != '\0' && lpcEnv[0] != '0') ? 1 : 0;
        }
        if (siEnabled == 0 || siLines >= 64 || CgsDev::Log::gpDebugPrint == NULL)
            return;
        ++siLines;
        char lacName[16];
        CgsIDConvertToString(lOverlayId, lacName);
        lacName[12] = 0;
        *CgsDev::Log::gpDebugPrint << "[overlay] " << lpcWhat << " " << lacName << " " << liValue << "\n";
    }

    // Post one 8-byte wait-finish record (188) for the named overlay.
    void PostWaitFinish(CgsModule::VariableEventQueue<18432, 16>& lrQueue, const char* lpcOverlayName)
    {
        GuiOverlayWaitFinishRequest lOverlayFinishRequest;
        lOverlayFinishRequest.Construct(lpcOverlayName);
        lrQueue.AddEvent(reinterpret_cast<const CgsModule::Event*>(&lOverlayFinishRequest),
                         lOverlayFinishRequest.GetEventType(),
                         static_cast<s32>(sizeof(lOverlayFinishRequest)));
    }
}

// Inlined by the console into GuiModule::Construct. The GuiCache pointer is not set here:
// it arrives with the first event 64.
void GuiOverlaysDirector::Construct(CgsGui::ModelModule* lpModelModule)
{
    mpController     = NULL;
    mpGuiInputBuffer = NULL;
    mpModelModule    = lpModelModule;

    mbInOverlay                  = false;
    mbIsWaitRequestValid         = false;
    mWaitEndRequestId            = 0;
    miFramesToShowEnteringOnline = -1;

    mOutputQueue.Construct();
    mOutputQueue.Clear();

    mCurrentOverlay.mNameId  = 0;
    mBufferedOverlay.mNameId = 0;
}

void GuiOverlaysDirector::HandleOverlayRequest(const GuiOverlayRequest* lpEvent)
{
    CGS_ASSERT(mpController != NULL, "mpController");

    if (mbInOverlay)
    {
        // Already showing one: park the request in the buffered slot (warning when that
        // overwrites an as-yet-unshown queued overlay; category bit 0 of the message filter
        // gates the debug print).
        if (mBufferedOverlay.mNameId != 0)
        {
            char lacOverlayName[16];
            CgsIDConvertToString(lpEvent->GetOverlayId(), lacOverlayName);
            lacOverlayName[12] = 0;

            if ((CgsDev::Message::gxMessageFilterFlags & 1) != 0)
            {
                *CgsDev::Log::gpDebugPrint
                    << "WARNING - OVERWRITING A QUEUED OVERLAY!\n    Adding overlay named "
                    << lacOverlayName
                    << " over queued overlay "
                    << mBufferedOverlay.macName
                    << "\n\n";
            }
        }
        SetUpOverlayInfo(&mBufferedOverlay, lpEvent);
        OverlayWitness("buffered", mBufferedOverlay.mNameId, static_cast<s32>(mBufferedOverlay.meStyle));
    }
    else
    {
        SetUpOverlayInfo(&mCurrentOverlay, lpEvent);
        StartCurrentOverlay();
        OverlayWitness("start", mCurrentOverlay.mNameId, static_cast<s32>(mCurrentOverlay.meStyle));
    }
}

void GuiOverlaysDirector::HandleWaitFinishRequest(const GuiOverlayWaitFinishRequest* lpEvent)
{
    if (!mbInOverlay)
        return;

    // Cancel a matching buffered overlay outright.
    if (mBufferedOverlay.mNameId == lpEvent->mOverlayId)
        mBufferedOverlay.mNameId = 0;

    if (mCurrentOverlay.mNameId == lpEvent->mOverlayId)
    {
        if (mbIsWaitRequestValid)
        {
            // The console streams both printable ids into the message; folded static.
            CGS_ASSERT(lpEvent->mOverlayId == mWaitEndRequestId,
                       "Received a finish wait request when one is already stored");
        }
        else
        {
            mbIsWaitRequestValid = true;
            mWaitEndRequestId    = lpEvent->mOverlayId;
        }
    }
}

// Fill an overlay description from a request, then stamp the popup record over it. The
// message and button params are copied through the request's accessors straight into the
// response's GuiPopupParameter slots ({id word, 64-byte text} -- the accessors' output
// shape).
void GuiOverlaysDirector::SetUpOverlayInfo(GuiOverlayFullInfoResponse* lpOverlay,
                                           const GuiOverlayRequest* lpEvent)
{
    static_assert(sizeof(GuiOverlayRequest::ParamOut) == sizeof(CgsGui::GuiPopupParameter),
                  "a request param copies into a GuiPopupParameter slot");

    lpOverlay->mNameId            = lpEvent->GetOverlayId();
    lpOverlay->mbButon1ParamUsed  = lpEvent->mbButton1Used != 0;
    lpOverlay->mbButon2ParamUsed  = lpEvent->mbButton2Used != 0;
    lpOverlay->miMessageParamsUsed = lpEvent->GetMessageParamCount();

    for (s32 liIter = 0; liIter < lpOverlay->miMessageParamsUsed; ++liIter)
    {
        lpEvent->GetMessageParam(
            reinterpret_cast<GuiOverlayRequest::ParamOut*>(&lpOverlay->maMessageParams[liIter]),
            liIter);
    }

    if (lpOverlay->mbButon1ParamUsed)
        lpEvent->GetButton1Param(reinterpret_cast<GuiOverlayRequest::ParamOut*>(&lpOverlay->mButton1Param));

    if (lpOverlay->mbButon2ParamUsed)
        lpEvent->GetButton2Param(reinterpret_cast<GuiOverlayRequest::ParamOut*>(&lpOverlay->mButton2Param));

    mpController->GetPopup(lpOverlay);
}

// GUI event 279, posted when an online free-burn mode's intro stops. With mbShow set it
// raises the enter/return overlay, worded from the host's point of view; without it, it
// waves the current overlay and the four online transition overlays through their
// wait-finish.
void GuiOverlaysDirector::HandleShowFreeBurnIntroRequest(const GuiEventNetworkShowFreeBurnIntro* lpNotification)
{
    typedef BrnNetwork::BrnNetworkModuleIO::InGamePlayerStatusData InGamePlayerStatusData;

    CGS_ASSERT(mpGuiCache != NULL, "mpGuiCache");

    if (lpNotification->mbShow)
    {
        const s32 liOnlinePlayerCount = mpGuiCache->GetNumActivePlayers();
        const InGamePlayerStatusData* lpFirstNonHostPlayerInfo = NULL;
        const InGamePlayerStatusData* lpHostPlayerInfo         = NULL;

        for (s32 liOnlinePlayerIndex = 0; liOnlinePlayerIndex < liOnlinePlayerCount; ++liOnlinePlayerIndex)
        {
            const InGamePlayerStatusData* lpPlayerInfo = mpGuiCache->GetOnlinePlayerInfo(liOnlinePlayerIndex);
            CGS_ASSERT(lpPlayerInfo != NULL, "lpPlayerInfo");

            if (lpPlayerInfo->mbIsHost)
                lpHostPlayerInfo = lpPlayerInfo;
            else if (lpFirstNonHostPlayerInfo == NULL)
                lpFirstNonHostPlayerInfo = lpPlayerInfo;

            if (lpHostPlayerInfo != NULL && lpFirstNonHostPlayerInfo != NULL)
                break;
        }

        CGS_ASSERT(lpHostPlayerInfo != NULL, "lpHostPlayerInfo");

        GuiOverlayRequest lEnterGameOverlayRequest;
        if (lpNotification->mbFinishedOnlineEvent)
        {
            if (lpHostPlayerInfo->mbIsLocalPlayer)
            {
                lEnterGameOverlayRequest.Construct("OnHReturnOn");
            }
            else
            {
                lEnterGameOverlayRequest.Construct("OnCReturnOn");
                lEnterGameOverlayRequest.AddMessageParam(1, lpHostPlayerInfo->mPlayerName.GetPlayerName());
            }
        }
        else if (lpHostPlayerInfo == NULL ||
                 (lpHostPlayerInfo->mbIsLocalPlayer && liOnlinePlayerCount == 1))
        {
            lEnterGameOverlayRequest.Construct("OnHEnterOn");
        }
        else if (lpHostPlayerInfo->mbIsLocalPlayer && liOnlinePlayerCount > 1)
        {
            // The local host with company: named after the first non-host player.
            CGS_ASSERT(lpFirstNonHostPlayerInfo != NULL, "lpFirstNonHostPlayerInfo");
            lEnterGameOverlayRequest.Construct("OnCEnterOn");
            lEnterGameOverlayRequest.AddMessageParam(1, lpFirstNonHostPlayerInfo->mPlayerName.GetPlayerName());
        }
        else
        {
            lEnterGameOverlayRequest.Construct("OnCEnterOn");
            lEnterGameOverlayRequest.AddMessageParam(1, lpHostPlayerInfo->mPlayerName.GetPlayerName());
        }
        HandleOverlayRequest(&lEnterGameOverlayRequest);
    }
    else if (mbInOverlay)
    {
        GuiOverlayWaitFinishRequest lOverlayFinishRequest;
        lOverlayFinishRequest.mOverlayId = mCurrentOverlay.mNameId;
        mOutputQueue.AddEvent(reinterpret_cast<const CgsModule::Event*>(&lOverlayFinishRequest),
                              lOverlayFinishRequest.GetEventType(),
                              static_cast<s32>(sizeof(lOverlayFinishRequest)));

        for (s32 li = 0; li < 4; ++li)
            PostWaitFinish(mOutputQueue, KPC_ONLINE_OVERLAYS[li]);
    }
}

void GuiOverlaysDirector::Update(CgsGui::CgsGuiModuleIO::InputBuffer* lpGuiInputBuffer)
{
    // The whole update is gated on a bound controller.
    if (mpController == NULL)
        return;

    CGS_ASSERT(lpGuiInputBuffer != NULL,
               "Input buffer is not valid. Is it definately locked for reading?");
    mpGuiInputBuffer = lpGuiInputBuffer;

    CgsGui::CgsGuiModuleIO::InputBuffer::GuiEventInputQueue* lpEventQueue =
        lpGuiInputBuffer->GetGuiEvents();
    CGS_ASSERT(lpEventQueue != NULL, "lpEventQueue != NULL");

    const CgsModule::Event* lpEvent = NULL;
    s32 liEventSize = 0;
    s32 liEventType = lpEventQueue->GetFirstEvent(&lpEvent, &liEventSize);
    while (lpEvent != NULL)
    {
        switch (liEventType)
        {
        case 64:   // the GuiCache is ready (payload = GuiCache*)
            CGS_ASSERT(lpEvent != NULL, "lpCacheEvent");
            mpGuiCache = *reinterpret_cast<GuiCache* const*>(lpEvent);
            break;

        case 184:
            HandleOverlayRequest(reinterpret_cast<const GuiOverlayRequest*>(lpEvent));
            break;

        case 186:
            HandleOverlayFullInfoRequest();
            break;

        case 188:
            HandleWaitFinishRequest(reinterpret_cast<const GuiOverlayWaitFinishRequest*>(lpEvent));
            break;

        case 189:  // the overlay state left: the record leads with the overlay id
        {
            const GuiOverlayHiddenNotification* lpCompleteEvent =
                reinterpret_cast<const GuiOverlayHiddenNotification*>(lpEvent);
            OverlayWitness("complete", lpCompleteEvent->mOverlayId,
                           lpCompleteEvent->mOverlayId == mCurrentOverlay.mNameId ? 1 : 0);
            if (lpCompleteEvent->mOverlayId == mCurrentOverlay.mNameId)
            {
                mbInOverlay          = false;
                mbIsWaitRequestValid = false;

                if (mBufferedOverlay.mNameId != 0)
                {
                    // Promote the buffered overlay; an online transition overlay also arms
                    // the entering-online splash countdown.
                    if (IsOnlineTransitionOverlay(mBufferedOverlay.mNameId))
                        miFramesToShowEnteringOnline = KI_FRAMES_TO_SHOW_ENTERING_FREEBURN;

                    std::memcpy(&mCurrentOverlay, &mBufferedOverlay,
                                sizeof(GuiOverlayFullInfoResponse));
                    mBufferedOverlay.mNameId = 0;
                    StartCurrentOverlay();
                }
            }
            break;
        }

        case 190:
            HandleOverlayShowingNotification(
                reinterpret_cast<const GuiOverlayShowingNotification*>(lpEvent));
            break;

        case 279:
            HandleShowFreeBurnIntroRequest(
                reinterpret_cast<const GuiEventNetworkShowFreeBurnIntro*>(lpEvent));
            break;

        case 322:  // a mode stopped: drop a buffered online-transition overlay
            if (mBufferedOverlay.mNameId != 0 &&
                IsOnlineTransitionOverlay(mBufferedOverlay.mNameId))
            {
                mBufferedOverlay.mNameId = 0;
            }
            break;

        default:
            break;
        }

        liEventType = lpEventQueue->GetNextEvent(lpEvent, &lpEvent, &liEventSize);
    }

    // The entering-online splash countdown: on expiry, wave all four online transition
    // overlays through their wait-finish.
    if (miFramesToShowEnteringOnline >= 0)
    {
        if (--miFramesToShowEnteringOnline < 0)
        {
            miFramesToShowEnteringOnline = -1;
            for (s32 li = 0; li < 4; ++li)
                PostWaitFinish(mOutputQueue, KPC_ONLINE_OVERLAYS[li]);
        }
    }

    mpGuiInputBuffer = NULL;
}

// ARTIST825011C0: publish through the real bound Model, then clear.
void GuiOverlaysDirector::BridgeOutEvents(CgsGui::ModelIO::InputBuffer* lpGuiModelInput)
{
    if (mOutputQueue.GetLength() == 0)
        return;

    CGS_ASSERT(lpGuiModelInput != NULL, "lpGuiModelInput");

    CGS_ASSERT(mpModelModule != NULL, "mpModelModule");

    lpGuiModelInput->LockForWrite();
    mpModelModule->AddGuiEvents(&mOutputQueue, lpGuiModelInput);
    lpGuiModelInput->UnlockForWrite();

    mOutputQueue.Clear();
}
}
