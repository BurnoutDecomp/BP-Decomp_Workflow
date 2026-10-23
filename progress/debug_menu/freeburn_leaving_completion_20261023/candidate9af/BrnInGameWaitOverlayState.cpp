#include "GameSource/Gui/Flow/Overlay/States/BrnInGameWaitOverlayState.h"

// Reconstructed from BURNOUT_X360_ARTIST.XEX @ 0x824B1DF0
// (BrnGui::InGameWaitOverlayState::FillInPopupType): a single store of the
// class's flash-file-id literal into mpcFlashFileId (X360 this+0x10C).

namespace BrnGui
{
    const char InGameWaitOverlayState::KPC_IN_GAME_FRAME_LABEL[7] = "InGame";

    // @ 0x824B1DF0
    void InGameWaitOverlayState::FillInPopupType()
    {
        mpcFlashFileId = KPC_IN_GAME_FRAME_LABEL;
    }
}
