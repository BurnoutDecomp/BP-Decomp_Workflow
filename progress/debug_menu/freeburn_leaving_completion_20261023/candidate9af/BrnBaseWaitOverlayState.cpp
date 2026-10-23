#include "GameSource/Gui/Flow/Overlay/States/BrnBaseWaitOverlayState.h"

#include "GameShared/GameClasses/Module/CgsVariableEventQueue.h"   // the 18432 in-queue view

// BrnGui::BaseWaitOverlayState -- reconstructed from BURNOUT_X360_ARTIST.XEX.
//
// Bodied here (2 ledger functions, DWARF primary file
// GameSource/Gui/Flow/Overlay/States/BrnBaseWaitOverlayState.cpp):
//   BaseWaitOverlayState::SetupOverlay  @0x824B1B50
//   BaseWaitOverlayState::UpdateRunning @0x824B26D0

namespace BrnGui
{
namespace
{
    typedef CgsModule::VariableEventQueue<18432, 16> OverlayStateInQueue;

    // The game's "this wait popup may finish now" request (the id the overlays
    // director forwards; see BrnGuiOverlaysDirector).
    const s32 KI_EVENT_OVERLAY_WAIT_FINISH = 188;
}

// @ 0x824B1B50
void BaseWaitOverlayState::SetupOverlay(const GuiOverlayFullInfoResponse* lpResponse)
{
    BaseOverlayState::SetupOverlay(lpResponse);

    // A wait popup offers no actions: blank text, both glyphs invisible (the X360
    // passes the empty string @0x820046A7 and button 15 twice, remap on).
    mHelpItem1Component.SetItem("", FlaptButtonIconComponent::E_PADBUTTON_INVISIBLE,
                                FlaptButtonIconComponent::E_PADBUTTON_INVISIBLE, true);
    mHelpItem2Component.SetItem("", FlaptButtonIconComponent::E_PADBUTTON_INVISIBLE,
                                FlaptButtonIconComponent::E_PADBUTTON_INVISIBLE, true);
}

// @ 0x824B26D0
bool BaseWaitOverlayState::UpdateRunning()
{
    OverlayStateInQueue* lpInQueue = reinterpret_cast<OverlayStateInQueue*>(mpInGuiEventQueue);

    const CgsModule::Event* lpEvent = NULL;
    s32 liSize = 0;
    s32 liEventId = lpInQueue->GetFirstEvent(&lpEvent, &liSize);
    while (lpEvent != NULL)
    {
        // The wait-finish request's leading qword is the overlay id (asm: cmpld of
        // the payload +0x00 against mCurrentOverlayId @+0x110 -- the Hex-Rays +4 is
        // a decompiler artifact).
        if (liEventId == KI_EVENT_OVERLAY_WAIT_FINISH &&
            *reinterpret_cast<const CgsID*>(lpEvent) == mCurrentOverlayId)
        {
            meLeaveMethod = GuiOverlayCompleteEvent::E_LEAVEMETHOD_NONE;
            return true;
        }

        liEventId = lpInQueue->GetNextEvent(lpEvent, &lpEvent, &liSize);
    }

    return false;
}
}
