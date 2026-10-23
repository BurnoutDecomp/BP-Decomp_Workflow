#pragma once

#include "BrnCommonTypes.h"
#include "GameSource/BurnoutConstants.h"            // ::EActiveRaceCarIndex (the one and only)
#include "GameSource/GameState/BrnTakedownType.h"   // BrnGameState::ETakedownType (canonical)

namespace BrnGameState
{
    // Recovered from BrnTakedownManagerTypes.h (DecFIGS DWARF). CgsID is a 64-bit
    // hash, so the struct is 8-byte aligned and the owning queue's inline buffer
    // lands at +16.
    typedef u64 CgsID;

    // Slot index of an active race car. There is exactly ONE such enum, at global scope
    // (BurnoutConstants.h); TakedownEvent's two index members are that type. The alias exists
    // so `BrnGameState::EActiveRaceCarIndex` keeps naming it for the code that spells it that
    // way -- it must never become a second enum, which would re-mangle every unqualified use in
    // headers included after this one.
    typedef ::EActiveRaceCarIndex EActiveRaceCarIndex;

    struct TakedownEvent
    {
        EActiveRaceCarIndex meAggressorIndex;
        EActiveRaceCarIndex meVictimIndex;
        CgsID               mAggressorCarID;
        CgsID               mVictimCarID;
        ETakedownType       meType;
        s32                 miMultipleTakedownCount;
        s32                 miTakedownChainCount;
        bool                mbMarkedManTakeDown;
        bool                mbRemote;
        bool                mbSettledScore;
    };
}
