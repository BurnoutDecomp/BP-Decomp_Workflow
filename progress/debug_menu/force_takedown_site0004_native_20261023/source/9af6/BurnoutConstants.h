#pragma once

// Game-wide constants/enums. Recovered from the DecFIGS DWARF (BurnoutConstants.h).
#include "types.hpp"
#include "GameShared/GameClasses/Core/CgsAssert.h"   // CGS_ASSERT (range-guarded operator++)

// Slot index of an active race car (the local player + rivals), or INVALID.
enum EActiveRaceCarIndex : s32
{
    E_ACTIVE_RACE_CAR_INDEX_INVALID = -1,
    E_ACTIVE_RACE_CAR_INDEX_0       = 0,
    E_ACTIVE_RACE_CAR_INDEX_1       = 1,
    E_ACTIVE_RACE_CAR_INDEX_2       = 2,
    E_ACTIVE_RACE_CAR_INDEX_3       = 3,
    E_ACTIVE_RACE_CAR_INDEX_4       = 4,
    E_ACTIVE_RACE_CAR_INDEX_5       = 5,
    E_ACTIVE_RACE_CAR_INDEX_6       = 6,
    E_ACTIVE_RACE_CAR_INDEX_7       = 7,
    E_ACTIVE_RACE_CAR_INDEX_COUNT   = 8
};

// Global slot index of a race car across all modes (the player + up to 34 rivals/traffic
// racers tracked by the global output interface), or INVALID. DWARF BurnoutConstants.h:43
// (enumerators 0..34, COUNT = 35). Grows out the prior EGlobalRaceCarIndex_Stub placeholder.
enum EGlobalRaceCarIndex : s32
{
    E_GLOBAL_RACE_CAR_INDEX_INVALID = -1,
    E_GLOBAL_RACE_CAR_INDEX_0       = 0,
    E_GLOBAL_RACE_CAR_INDEX_1       = 1,
    E_GLOBAL_RACE_CAR_INDEX_2       = 2,
    E_GLOBAL_RACE_CAR_INDEX_3       = 3,
    E_GLOBAL_RACE_CAR_INDEX_4       = 4,
    E_GLOBAL_RACE_CAR_INDEX_5       = 5,
    E_GLOBAL_RACE_CAR_INDEX_6       = 6,
    E_GLOBAL_RACE_CAR_INDEX_7       = 7,
    E_GLOBAL_RACE_CAR_INDEX_8       = 8,
    E_GLOBAL_RACE_CAR_INDEX_9       = 9,
    E_GLOBAL_RACE_CAR_INDEX_10      = 10,
    E_GLOBAL_RACE_CAR_INDEX_11      = 11,
    E_GLOBAL_RACE_CAR_INDEX_12      = 12,
    E_GLOBAL_RACE_CAR_INDEX_13      = 13,
    E_GLOBAL_RACE_CAR_INDEX_14      = 14,
    E_GLOBAL_RACE_CAR_INDEX_15      = 15,
    E_GLOBAL_RACE_CAR_INDEX_16      = 16,
    E_GLOBAL_RACE_CAR_INDEX_17      = 17,
    E_GLOBAL_RACE_CAR_INDEX_18      = 18,
    E_GLOBAL_RACE_CAR_INDEX_19      = 19,
    E_GLOBAL_RACE_CAR_INDEX_20      = 20,
    E_GLOBAL_RACE_CAR_INDEX_21      = 21,
    E_GLOBAL_RACE_CAR_INDEX_22      = 22,
    E_GLOBAL_RACE_CAR_INDEX_23      = 23,
    E_GLOBAL_RACE_CAR_INDEX_24      = 24,
    E_GLOBAL_RACE_CAR_INDEX_25      = 25,
    E_GLOBAL_RACE_CAR_INDEX_26      = 26,
    E_GLOBAL_RACE_CAR_INDEX_27      = 27,
    E_GLOBAL_RACE_CAR_INDEX_28      = 28,
    E_GLOBAL_RACE_CAR_INDEX_29      = 29,
    E_GLOBAL_RACE_CAR_INDEX_30      = 30,
    E_GLOBAL_RACE_CAR_INDEX_31      = 31,
    E_GLOBAL_RACE_CAR_INDEX_32      = 32,
    E_GLOBAL_RACE_CAR_INDEX_33      = 33,
    E_GLOBAL_RACE_CAR_INDEX_34      = 34,
    E_GLOBAL_RACE_CAR_INDEX_COUNT   = 35
};

// DWARF BurnoutConstants.h:84 -- post-increment used to walk the global race-car slots.
// [stuntrace waveB fix round, 2026-08-26] THE RANGE GUARD WAS MISSING HERE while its
// EActiveRaceCarIndex twin below carried it, even though this operator's own comment already cited
// DWARF :84 for it. The X360 emits it: ModeManager::ResetNextLandmarks @0x82328460 loads the string
// "leEnumIndex <= E_GLOBAL_RACE_CAR_INDEX_COUNT" (`addi r25, r11, aLeenumindexEGl@l` @0x823284A4)
// and fires it with `li r5, 0x54` == BurnoutConstants.h:84 @0x82328550 -- the exact DWARF line this
// comment names. ModeManager::CheckForOutOfRangeCarsReachingFinish, RCEntityGlobalRaceCarOutput
// Interface::GetGlobalRaceCarIndex and ~15 RaceCarEntityModule / AIModule loops emit the same one.
// Non-fatal, same shape as the active twin: the old value is still returned on a failed guard.
inline EGlobalRaceCarIndex operator++(EGlobalRaceCarIndex &leIndex, int)
{
    const EGlobalRaceCarIndex lePrev = leIndex;
    leIndex = static_cast<EGlobalRaceCarIndex>(static_cast<s32>(leIndex) + 1);
    CGS_ASSERT( leIndex <= E_GLOBAL_RACE_CAR_INDEX_COUNT,
                "leEnumIndex <= E_GLOBAL_RACE_CAR_INDEX_COUNT" );
    return lePrev;
}

// Post-increment over the active-race-car slots. X360 @0x821F1DB8 (DWARF
// BurnoutConstants.h:39): saves the old value, increments, then range-guards the new
// value with the project CGS_ASSERT (X360 fires when the incremented index exceeds
// E_ACTIVE_RACE_CAR_INDEX_COUNT, i.e. > 8). The guard is non-fatal -- the X360 returns
// the saved old value even on a failed guard. The assert is included here (rather than
// only at the .cpp anchor) so the macro is expanded exactly once where the operator is
// defined; CgsAssert.h is pulled in below for the macro.
inline EActiveRaceCarIndex operator++(EActiveRaceCarIndex &leEnumIndex, int)
{
    const EActiveRaceCarIndex leOldEnumIndex = leEnumIndex;
    leEnumIndex = static_cast<EActiveRaceCarIndex>(static_cast<s32>(leEnumIndex) + 1);
    CGS_ASSERT( leEnumIndex <= E_ACTIVE_RACE_CAR_INDEX_COUNT,
                "leEnumIndex <= E_ACTIVE_RACE_CAR_INDEX_COUNT" );
    return leOldEnumIndex;
}

namespace BrnGameState
{
    // DWARF BurnoutConstants.h:91 -- lifecycle of a freeburn challenge. COUNT (7)
    // doubles as the "no status / uninitialised" sentinel that network messages
    // construct the field with (e.g. BrnNetwork::FreeburnChallengeMessage).
    enum EChallengeStatus
    {
        E_CHALLENGE_STATUS_ONGOING                      = 0,
        E_CHALLENGE_STATUS_SUCCESS                      = 1,
        E_CHALLENGE_STATUS_ABORTED                      = 2,
        E_CHALLENGE_STATUS_ABORTED_DUE_TO_PLAYER_LEAVE  = 3,
        E_CHALLENGE_STATUS_ABORTED_BEFORE_STARTING      = 4,
        E_CHALLENGE_STATUS_RESET_IF_NEEDED              = 5,
        E_CHALLENGE_STATUS_FAILURE                      = 6,
        E_CHALLENGE_STATUS_COUNT                        = 7,
    };
} // namespace BrnGameState
