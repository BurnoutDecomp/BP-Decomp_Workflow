#include "GameSource/GameState/TakedownManager/BrnTakedownManager.h"

namespace BrnGameState
{
// X360 0x82355CE8. Reset one active race car's takedown bookkeeping to "no takedown pending":
// clear the 8 per-rival revenge flags, clear the waiting/chain/multiple state, and seed the timers
// (mfTimeSinceLastTakenDown = FLT_MAX, mfTimeSinceVictimCrashed = 0, mfTimeSinceLastTakedown = -1
// "never"). The X360 build clears the revenge flags in a bounds-checked enum loop (the inlined
// EActiveRaceCarIndex operator++); restored here as a plain 8-iteration loop over the fixed array.
// The trailing `return result` on this void function is a register artifact and is dropped.
void TakedownManager::RaceCarData::Clear()
{
    for (s32 li = 0; li < 8; ++li)
    {
        mabRevengeRelationships[li] = false;
    }

    mbWaitingOnTakedown      = false;
    miTakedownChainLength    = 0;
    miMultipleTakedownLength = 0;

    mfTimeSinceLastTakenDown = 3.4028235e38f;   // FLT_MAX
    mfTimeSinceVictimCrashed = 0.0f;
    mfTimeSinceLastTakedown  = -1.0f;
}
}
