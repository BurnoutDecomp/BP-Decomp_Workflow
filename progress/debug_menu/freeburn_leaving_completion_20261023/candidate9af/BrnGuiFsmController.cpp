// BrnGuiFsmController.cpp
// Reconstructed from BURNOUT_X360_ARTIST.XEX.

#include "GameSource/Gui/BrnGuiFsmController.h"

#include "GameShared/GameClasses/Core/CgsAssert.h"
#include "GameShared/GameClasses/Core/CgsID.h"
#include "GameShared/GameClasses/Development/CgsStrStream.h"
#include "GameShared/GameClasses/Gui/Model/CgsModelModuleIO.h"
#include "GameShared/GameClasses/Fsm/Resources/CgsLuaCodeResource.h"
#include "GameSource/Gui/Flow/BrnBaseFlow.h"

namespace BrnGui
{
namespace
{
    const char* const KAC_BLANK_FSM_ID = " ";

    bool IsValidFlow(s32 liFlow)
    {
        return liFlow >= E_GUIFLOW_FIRST && liFlow < E_GUIFLOW_COUNT;
    }

    u32 FlowLoadRequestId(s32 liFlow)
    {
        switch (liFlow)
        {
            case E_GUIFLOW_SCREEN:  return 13;
            case E_GUIFLOW_HUD:     return 14;
            case E_GUIFLOW_OVERLAY: return 15;
            default:
            {
                char lacMessageBuffer[CgsDev::Assert::KI_MESSAGEBUFFERSIZE];
                CgsDev::StrStream lStrStream(lacMessageBuffer, CgsDev::Assert::KI_MESSAGEBUFFERSIZE);
                lStrStream << "Invalid GuiFlow (" << liFlow << ") in GuiFsmController::TriggerLoad";
                CgsDev::Assert::BeginAssert();
                CgsDev::Assert::FireAssert(lStrStream.GetBuffer(), __FILE__, __LINE__);
                CgsDev::Assert::EndAssert();
                return 0;
            }
        }
    }

    void AssertInvalidFlowLoadState(s32 liFlow)
    {
        char lacMessageBuffer[CgsDev::Assert::KI_MESSAGEBUFFERSIZE];
        CgsDev::StrStream lStrStream(lacMessageBuffer, CgsDev::Assert::KI_MESSAGEBUFFERSIZE);
        lStrStream << "Invalid case in FsmController Update for Fsm(" << liFlow << ")";
        CgsDev::Assert::BeginAssert();
        CgsDev::Assert::FireAssert(lStrStream.GetBuffer(), __FILE__, __LINE__);
        CgsDev::Assert::EndAssert();
    }
}

// @ 0x824F1940
void GuiFsmController::Construct()
{
    mpGuiModelModule = 0;
    mpFSMAllocator = 0;
    mePrepareStage = E_PREPARESTAGE_START;

    for (u32 luFlow = 0; luFlow < KU_NUM_FLOWS; ++luFlow)
    {
        mapFlows[luFlow] = 0;
        maeFlowLoadState[luFlow] = E_FLOWLOADSTAGE_UNLOADED;
        maHashToLoad[luFlow] = 0;
        maacNameToLoad[luFlow][0] = 0;
        mInitialStateId[luFlow] = 0;
        mapLoadNotification[luFlow] = 0;
        mapUnloadNotification[luFlow] = 0;
        mbFsmTransitionPending[luFlow] = false;
        mbModeManagerWaitingForResponse[luFlow] = false;

        mFsmToChangeTo[luFlow] = GuiEventRunFsm();
        mCurrentFsm[luFlow] = mFsmToChangeTo[luFlow];
        macNameToUnload[luFlow][0] = 0;
    }

    mDummyUnloadNotification.meRequestType = CgsGui::E_GUI_RESOURCETYPE_START;
    mDummyUnloadNotification.muLoadRequestId = 0;
    mDummyUnloadNotification.muFileNameHash = 0;
}

// @ 0x824F1BE8
bool GuiFsmController::Prepare(CgsGui::ModelModule* lpGuiModelModule,
                               CgsMemory::HeapMalloc* lpFSMAllocator)
{
    if (mePrepareStage < E_PREPARESTAGE_START)
        return true;

    if (mePrepareStage <= E_PREPARESTAGE_SETPOINTERS)
    {
        mpGuiModelModule = lpGuiModelModule;
        mpFSMAllocator = lpFSMAllocator;
        mePrepareStage = E_PREPARESTAGE_SETPOINTERS;
        mePrepareStage = E_PREPARESTAGE_DONE;
        return true;
    }

    if (mePrepareStage == E_PREPARESTAGE_DONE)
        mePrepareStage = E_PREPARESTAGE_DONE;

    return true;
}

// @ 0x827E54A8
void GuiFsmController::AddFlow(GuiFlow leFlow, BrnBaseFlow* lpFlow)
{
    const s32 liFlow = static_cast<s32>(leFlow);
    if (!IsValidFlow(liFlow))
    {
        char lacMessageBuffer[CgsDev::Assert::KI_MESSAGEBUFFERSIZE];
        CgsDev::StrStream lStrStream(lacMessageBuffer, CgsDev::Assert::KI_MESSAGEBUFFERSIZE);
        lStrStream << "Invalid GuiFlow (" << liFlow << ") in GuiFsmController::AddFlow";
        CgsDev::Assert::BeginAssert();
        CgsDev::Assert::FireAssert(lStrStream.GetBuffer(), __FILE__, __LINE__);
        CgsDev::Assert::EndAssert();
        return;
    }

    if (mapFlows[leFlow] != 0)
    {
        char lacMessageBuffer[CgsDev::Assert::KI_MESSAGEBUFFERSIZE];
        CgsDev::StrStream lStrStream(lacMessageBuffer, CgsDev::Assert::KI_MESSAGEBUFFERSIZE);
        lStrStream << "Error, cant set a flow that is already set";
        CgsDev::Assert::BeginAssert();
        CgsDev::Assert::FireAssert(lStrStream.GetBuffer(), __FILE__, __LINE__);
        CgsDev::Assert::EndAssert();
    }

    mapFlows[leFlow] = lpFlow;
}

// @ 0x824F9918
void GuiFsmController::RunFsm(const GuiEventRunFsm* lpEvent)
{
    const s32 liFlow = static_cast<s32>(lpEvent->meFlowToUse);
    if (!IsValidFlow(liFlow))
    {
        char lacMessageBuffer[CgsDev::Assert::KI_MESSAGEBUFFERSIZE];
        CgsDev::StrStream lStrStream(lacMessageBuffer, CgsDev::Assert::KI_MESSAGEBUFFERSIZE);
        lStrStream << "Invalid FlowToUse in the event";
        CgsDev::Assert::BeginAssert();
        CgsDev::Assert::FireAssert(lStrStream.GetBuffer(), __FILE__, __LINE__);
        CgsDev::Assert::EndAssert();
    }

    const GuiFlow leFlow = static_cast<GuiFlow>(liFlow);
    mbFsmTransitionPending[leFlow] = true;
    mbModeManagerWaitingForResponse[leFlow] = true;
    mFsmToChangeTo[leFlow] = *lpEvent;

    if (maeFlowLoadState[leFlow] == E_FLOWLOADSTAGE_UNLOADED)
    {
        RunQueuedFsm(leFlow);
    }
    else if (maeFlowLoadState[leFlow] == E_FLOWLOADSTAGE_RUNNING)
    {
        maeFlowLoadState[leFlow] = E_FLOWLOADSTAGE_FSMSHUTDOWN;
    }
}

// @ 0x824F1A00
void GuiFsmController::RunQueuedFsm(GuiFlow leFlowToUse)
{
    maHashToLoad[leFlowToUse] = mFsmToChangeTo[leFlowToUse].mFsmId;
    CgsIDConvertToString(mFsmToChangeTo[leFlowToUse].mFsmId, maacNameToLoad[leFlowToUse]);
    mInitialStateId[leFlowToUse] = mFsmToChangeTo[leFlowToUse].mInitialStateId;

    for (s32 liIndex = 0; liIndex < KI_FSM_NAME_LENGTH; ++liIndex)
    {
        if (maacNameToLoad[leFlowToUse][liIndex] == ' ')
        {
            maacNameToLoad[leFlowToUse][liIndex] = 0;
            break;
        }
    }

    maeFlowLoadState[leFlowToUse] = E_FLOWLOADSTAGE_TRIGGERLOAD;
    mbFsmTransitionPending[leFlowToUse] = false;

    mCurrentFsm[leFlowToUse] = mFsmToChangeTo[leFlowToUse];
    mFsmToChangeTo[leFlowToUse].mFsmId = CgsIDCompress(KAC_BLANK_FSM_ID);
    mFsmToChangeTo[leFlowToUse].mInitialStateId = CgsIDCompress(KAC_BLANK_FSM_ID);
    mFsmToChangeTo[leFlowToUse].meFsmToRun = E_GUI_HUD_NUMSFSMS;
    mFsmToChangeTo[leFlowToUse].meFlowToUse = E_GUIFLOW_COUNT;
}

// @ 0x825148C8
void GuiFsmController::Update(CgsGui::ModelIO::InputBuffer* lpModelInputBuffer,
                              const CgsGui::ModelIO::OutputBuffer* lpModelOutputBuffer)
{
    CGS_ASSERT(mpGuiModelModule != 0, "The Model Module isn't valid yet. Call Construct() first");

    const CgsGui::ModelIO::OutputBuffer::GuiNotificationQueue* lpLoadNotifications =
        lpModelOutputBuffer->GetLoadNotifications();
    CGS_ASSERT(lpLoadNotifications != 0, "Invalid queue in BrnGuiFsmController::Update");

    const CgsModule::Event* lpEvent = 0;
    s32 liEventSize = 0;
    s32 liEventType = lpLoadNotifications->GetFirstEvent(&lpEvent, &liEventSize);
    while (lpEvent != 0)
    {
        if (liEventType == 14)
        {
            const CgsGui::GuiEventLoadNotification* lpLoadNotification =
                static_cast<const CgsGui::GuiEventLoadNotification*>(lpEvent);
            switch (lpLoadNotification->muLoadRequestId)
            {
                case 13: mapLoadNotification[E_GUIFLOW_SCREEN]  = lpLoadNotification; break;
                case 14: mapLoadNotification[E_GUIFLOW_HUD]     = lpLoadNotification; break;
                case 15: mapLoadNotification[E_GUIFLOW_OVERLAY] = lpLoadNotification; break;
            }
        }
        else if (liEventType == 16)
        {
            const CgsGui::GuiEventUnloadNotification* lpUnloadNotification =
                static_cast<const CgsGui::GuiEventUnloadNotification*>(lpEvent);
            switch (lpUnloadNotification->muLoadRequestId)
            {
                case 13: mapUnloadNotification[E_GUIFLOW_SCREEN]  = lpUnloadNotification; break;
                case 14: mapUnloadNotification[E_GUIFLOW_HUD]     = lpUnloadNotification; break;
                case 15: mapUnloadNotification[E_GUIFLOW_OVERLAY] = lpUnloadNotification; break;
            }
        }

        liEventType = lpLoadNotifications->GetNextEvent(lpEvent, &lpEvent, &liEventSize);
    }

    for (s32 liFlow = E_GUIFLOW_FIRST; liFlow < E_GUIFLOW_COUNT; ++liFlow)
    {
        if (mapFlows[liFlow] == 0)
            continue;

        switch (maeFlowLoadState[liFlow])
        {
            case E_FLOWLOADSTAGE_TRIGGERLOAD:
            {
                mapLoadNotification[liFlow] = 0;

                CgsGui::GuiEventLoadRequest lLoadRequest;
                lLoadRequest.Construct(CgsGui::E_GUI_RESOURCETYPE_PFX_BUNDLE,
                                       CgsGui::E_GUI_RESOURCEREQUEST_LOAD,
                                       maacNameToLoad[liFlow],
                                       FlowLoadRequestId(liFlow));
                lpModelInputBuffer->AddResourceRequests(lLoadRequest);
                maeFlowLoadState[liFlow] = E_FLOWLOADSTAGE_WFLOAD;
                // fall through
            }

            case E_FLOWLOADSTAGE_WFLOAD:
            {
                const CgsGui::GuiEventLoadNotification* lpLoadNotification = mapLoadNotification[liFlow];
                if (lpLoadNotification != 0)
                {
                    if (mbFsmTransitionPending[liFlow])
                    {
                        mapUnloadNotification[liFlow] = &mDummyUnloadNotification;
                        maeFlowLoadState[liFlow] = E_FLOWLOADSTAGE_WFUNLOAD;
                        mapLoadNotification[liFlow] = 0;
                    }
                    else
                    {
                        CgsResource::SafeResourceHandle<CgsResource::LuaCodeResource> lLuaCodeHandle;
                        lLuaCodeHandle.mpResourceMemory = lpLoadNotification->mResourceHandle.mpResourceMemory;
                        lLuaCodeHandle.mpSourceEntry = lpLoadNotification->mResourceHandle.mpSourceEntry;

                        mapFlows[liFlow]->PrepareLua(lLuaCodeHandle.Get(),
                                                     mpFSMAllocator,
                                                     mInitialStateId[liFlow]);
                        mapLoadNotification[liFlow] = 0;
                        maeFlowLoadState[liFlow] = E_FLOWLOADSTAGE_RUNNING;
                        mInitialStateId[liFlow] = 0;
                    }
                }
                break;
            }

            case E_FLOWLOADSTAGE_RUNNING:
            case E_FLOWLOADSTAGE_UNLOADED:
                break;

            case E_FLOWLOADSTAGE_FSMSHUTDOWN:
                if (mapFlows[liFlow]->Release())
                {
                    maeFlowLoadState[liFlow] = E_FLOWLOADSTAGE_TRIGGERUNLOAD;
                    // fall through
                }
                else
                {
                    break;
                }

            case E_FLOWLOADSTAGE_TRIGGERUNLOAD:
                mapUnloadNotification[liFlow] = 0;
                mapUnloadNotification[liFlow] = &mDummyUnloadNotification;
                maeFlowLoadState[liFlow] = E_FLOWLOADSTAGE_WFUNLOAD;
                // fall through

            case E_FLOWLOADSTAGE_WFUNLOAD:
                if (mapUnloadNotification[liFlow] != 0)
                {
                    if (mbFsmTransitionPending[liFlow])
                        RunQueuedFsm(static_cast<GuiFlow>(liFlow));
                    mapUnloadNotification[liFlow] = 0;
                    maeFlowLoadState[liFlow] = E_FLOWLOADSTAGE_TRIGGERLOAD;
                }
                break;

            default:
                AssertInvalidFlowLoadState(liFlow);
                break;
        }
    }
}

// @ 0x824F1B08
bool GuiFsmController::HandleHudStateLoadComplete()
{
    bool lbTransitionPending = false;
    bool lbModeManagerWaitingForResponse = false;

    for (u32 luFlow = 0; luFlow < KU_NUM_FLOWS; ++luFlow)
    {
        if (mbFsmTransitionPending[luFlow])
        {
            lbTransitionPending = true;
            maeFlowLoadState[luFlow] = E_FLOWLOADSTAGE_FSMSHUTDOWN;
        }
        else if (mbModeManagerWaitingForResponse[luFlow])
        {
            lbModeManagerWaitingForResponse = true;
            mbModeManagerWaitingForResponse[luFlow] = false;
        }
    }

    return !lbTransitionPending && lbModeManagerWaitingForResponse;
}

// @ 0x824ECCF8
bool GuiFsmController::IsTransitionPending(u32 luFlowId) const
{
    if (luFlowId >= KU_NUM_FLOWS)
    {
        char lacMessageBuffer[CgsDev::Assert::KI_MESSAGEBUFFERSIZE];
        CgsDev::StrStream lStrStream(lacMessageBuffer, CgsDev::Assert::KI_MESSAGEBUFFERSIZE);
        lStrStream << "Invalid Flow Id passed";
        CgsDev::Assert::BeginAssert();
        CgsDev::Assert::FireAssert(lStrStream.GetBuffer(), __FILE__, __LINE__);
        CgsDev::Assert::EndAssert();
    }

    if (mapFlows[luFlowId] == 0)
    {
        char lacMessageBuffer[CgsDev::Assert::KI_MESSAGEBUFFERSIZE];
        CgsDev::StrStream lStrStream(lacMessageBuffer, CgsDev::Assert::KI_MESSAGEBUFFERSIZE);
        lStrStream << "Error, flow not set";
        CgsDev::Assert::BeginAssert();
        CgsDev::Assert::FireAssert(lStrStream.GetBuffer(), __FILE__, __LINE__);
        CgsDev::Assert::EndAssert();
    }

    return mbFsmTransitionPending[luFlowId];
}

} // namespace BrnGui
