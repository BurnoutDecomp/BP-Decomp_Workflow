#include "GameSource/Gui/Flow/Overlay/States/BrnInGameOnlineWaitOverlayState.h"

// Reconstructed from BURNOUT_X360_ARTIST.XEX @ 0x824B1E20
// (BrnGui::InGameOnlineWaitOverlayState::FillInPopupType): a single store of the
// class's flash-file-id literal into mpcFlashFileId (X360 this+0x10C).

namespace BrnGui
{
    const char InGameOnlineWaitOverlayState::KPC_IN_GAME_FRAME_LABEL[13] = "InGameOnline";

    // @ 0x824B1E20
    void InGameOnlineWaitOverlayState::FillInPopupType()
    {
        mpcFlashFileId = KPC_IN_GAME_FRAME_LABEL;
    }
}
