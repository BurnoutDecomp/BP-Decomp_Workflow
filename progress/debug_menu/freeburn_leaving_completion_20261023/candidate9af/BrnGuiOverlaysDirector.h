#pragma once

#include "types.hpp"
#include "GameShared/GameClasses/Core/CgsID.h"        // CgsID / CgsIDCompress
#include "GameShared/GameClasses/Core/CgsAssert.h"     // CGS_ASSERT (the inlined SetController)
#include "GameShared/GameClasses/Gui/CgsGuiModuleIO.h" // CgsGui::CgsGuiModuleIO::InputBuffer (+ the 18432 queue type)
#include "GameShared/GameClasses/Gui/Model/CgsModelModuleIO.h" // CgsGui::ModelIO::InputBuffer (BridgeOutEvents)
#include "GameSource/Gui/BrnGuiEventTypeDefs.h"        // the overlay payload records: GuiOverlayRequest,
                                                       // GuiOverlayFullInfoResponse and the 188/189/190
                                                       // handshake trio this class exchanges

namespace CgsGui { class ModelModule; }
namespace BrnResource { struct PopupController; }

// BrnGui::GuiOverlaysDirector - routes overlay show/hide traffic between the game and
// the overlay GUI flow: it queues one pending overlay (current + one buffered), resolves
// each request against the popup table, answers full-info requests, tracks the
// wait-to-finish handshake, and manages the entering-online splash timing.
// Member names, order and method set from the type information.
namespace BrnGui
{
    class GuiCache;
    struct GuiEventNetworkShowFreeBurnIntro;   // BrnGuiDemangledEventTypes.h (id 279)

    struct GuiOverlaysDirector
    {
        // Inlined by the console into GuiModule::Construct.
        void Construct(CgsGui::ModelModule* lpModelModule);

        // Drain the GUI module input queue and dispatch the overlay traffic.
        void Update(CgsGui::CgsGuiModuleIO::InputBuffer* lpGuiInputBuffer);

        // Hand this frame's director output (185/187/188) to the model input buffer.
        void BridgeOutEvents(CgsGui::ModelIO::InputBuffer* lpGuiModelInput);

        // Inlined by the console into GuiModule::Update: store, then the non-gating
        // "mpController" assert (BrnGuiOverlaysDirector.h:125).
        void SetController(const BrnResource::PopupController* lpController)
        {
            mpController = lpController;
            CGS_ASSERT(mpController != NULL, "mpController");
        }

    private:
        void HandleOverlayRequest(const GuiOverlayRequest* lpEvent);

        // Inlined into Update's id-186 arm: publish the current overlay description (187).
        void HandleOverlayFullInfoRequest()
        {
            mOutputQueue.AddEvent(reinterpret_cast<const CgsModule::Event*>(&mCurrentOverlay),
                                  187, static_cast<s32>(sizeof(GuiOverlayFullInfoResponse)));
        }

        void HandleWaitFinishRequest(const GuiOverlayWaitFinishRequest* lpEvent);

        // Inlined into Update's id-190 arm: the overlay is on screen, so bounce a stored
        // wait-finish for it downstream now.
        void HandleOverlayShowingNotification(const GuiOverlayShowingNotification* lpNotification)
        {
            if (mbIsWaitRequestValid && lpNotification->mOverlayId == mWaitEndRequestId)
            {
                GuiOverlayWaitFinishRequest lWaitEvent;
                lWaitEvent.mOverlayId = mWaitEndRequestId;
                mOutputQueue.AddEvent(reinterpret_cast<const CgsModule::Event*>(&lWaitEvent),
                                      lWaitEvent.GetEventType(),
                                      static_cast<s32>(sizeof(lWaitEvent)));
            }
        }

        void SetUpOverlayInfo(GuiOverlayFullInfoResponse* lpOverlay, const GuiOverlayRequest* lpEvent);

        // Inlined into HandleOverlayRequest and Update's id-189 arm: mark an overlay as
        // showing and post the internal request (id 185) whose one word is the popup style
        // the overlay flow's invisible state switches on.
        void StartCurrentOverlay()
        {
            const u32 luStyle = static_cast<u32>(mCurrentOverlay.meStyle);
            mbInOverlay = true;
            mOutputQueue.AddEvent(reinterpret_cast<const CgsModule::Event*>(&luStyle), 185,
                                  static_cast<s32>(sizeof(luStyle)));
        }

        void HandleShowFreeBurnIntroRequest(const GuiEventNetworkShowFreeBurnIntro* lpNotification);

        // ---- members (console offsets) ----
        const BrnResource::PopupController*      mpController;                    // +0x00
        CgsGui::CgsGuiModuleIO::InputBuffer*     mpGuiInputBuffer;                // +0x04
        CgsGui::ModelModule*                     mpModelModule;                   // +0x08
        GuiOverlayFullInfoResponse               mCurrentOverlay;                 // +0x10
        GuiOverlayFullInfoResponse               mBufferedOverlay;                // +0x1D0
        CgsModule::VariableEventQueue<18432, 16> mOutputQueue;                    // +0x390
        GuiCache*                                mpGuiCache;                      // +0x4BA0
        bool                                     mbInOverlay;                     // +0x4BA4
        CgsID                                    mWaitEndRequestId;               // +0x4BA8
        bool                                     mbIsWaitRequestValid;            // +0x4BB0
        s32                                      miFramesToShowEnteringOnline;    // +0x4BB4
    };
}
