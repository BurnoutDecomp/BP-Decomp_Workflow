#pragma once

// Takedown classification (BrnGameState::ETakedownType). Canonical home for the enum; recovered
// in full from the DecFIGS DWARF (BrnTakedownManagerTypes.h:41). Other takedown headers include
// this rather than redefining it (it was previously duplicated minimally here and in
// BrnTakedownManagerTypes.h - a same-namespace latent ODR, now deduped).
#include "types.hpp"

namespace BrnGameState
{
    enum ETakedownType : s32
    {
        E_TAKEDOWN_NONE          = -1,
        E_TAKEDOWN_STANDARD      = 0,
        E_TAKEDOWN_GRINDING      = 1,
        E_TAKEDOWN_T_BONE        = 2,
        E_TAKEDOWN_VERTICAL      = 3,
        E_TAKEDOWN_TRAFFIC_CHECK = 4,
        E_TAKEDOWN_HEAD_ON       = 5,
        E_TAKEDOWN_UNKNOWN0      = 6,
        E_TAKEDOWN_UNKNOWN1      = 7,
        E_TAKEDOWN_DOUBLE        = 8,
        E_TAKEDOWN_REVENGE       = 9,
        E_TAKEDOWN_INTO_CAR      = 10,
        E_TAKEDOWN_INTO_VAN      = 11,
        E_TAKEDOWN_INTO_BUS      = 12,
        E_TAKEDOWN_COUNT         = 13,
    };
}
