#pragma once

#include "GameSource/Gui/Flow/Overlay/States/BrnBaseOverlayState.h"

// BrnGui::BaseWaitOverlayState - the "wait..." popup family base: no accept/cancel
// buttons (both help items are blanked), and the popup only leaves when the game
// posts the matching wait-finish request (event 188). DWARF home
// BrnBaseWaitOverlayState.h (adds no members; SetupOverlay/UpdateRunning overrides).
// FillInPopupType stays with the concrete CrashNav/InGame/Online states.
namespace BrnGui
{
    struct BaseWaitOverlayState : public BaseOverlayState
    {
        // @0x824B1B50 (this TU) -- base dressing, then blank both help items.
        virtual void SetupOverlay(const GuiOverlayFullInfoResponse* lpResponse);

        // @0x824B26D0 (this TU) -- leave only on the matching wait-finish request.
        virtual bool UpdateRunning();
    };
}
