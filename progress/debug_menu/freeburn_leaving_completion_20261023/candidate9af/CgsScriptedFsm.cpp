#include "GameShared/GameClasses/Fsm/CgsScriptedFsm.h"

#include "GameShared/GameClasses/Fsm/Resources/CgsLuaCodeResource.h"  // CgsResource::LuaCodeResource
#include "GameShared/GameClasses/Fsm/CgsEvent.h"                       // CgsFsm::Event
#include "GameShared/GameClasses/Fsm/CgsVariable.h"                    // CgsFsm::Variable
#include "GameShared/GameClasses/Memory/CgsHeapMalloc.h"              // CgsMemory::HeapMalloc
#include "GameShared/GameClasses/Core/CgsID.h"                        // CgsIDCompress / CgsIDUnCompress
#include "GameShared/GameClasses/Core/CgsStringUtils.h"               // CgsCore::SPrintf
#include "GameShared/GameClasses/Core/CgsAssert.h"                    // CGS_ASSERT (flagged assert substitute)
#include "GameShared/GameClasses/Development/Log/CgsLog.h"            // [DIAG] BRN_SCREEN_DIAG witness
#include <cstdio>                                                      // std::sscanf
#include <cstdlib>                                                    // [DIAG] getenv

// ===========================================================================
//  CgsFsm::ScriptedFsm -- reconstructed from BURNOUT_X360_ARTIST.XEX. The transition
//  logic lives in the FSM's Lua script (run through mLuaState); this C++ drives it:
//  Prepare brings the script up and enters the start state; SetState looks a state up by
//  id in the concrete FSM's table (GetState/GetStateCount) and swaps it (OnLeave/OnEnter);
//  SendEvent (next pass) marshals an event's variables into Lua then NextState->SetState.
//  The X360 gpcMessageBuffer assert machinery is replaced by CGS_ASSERT per the project rule.
// ===========================================================================

namespace CgsFsm
{

ScriptedFsm::ScriptedFsm() { Construct(); }

void ScriptedFsm::Construct()
{
    mpCurrentState   = nullptr;
    mLuaState.Construct();
    muSequenceNumber = 0;
}

void ScriptedFsm::Destruct()
{
    if (mLuaState.IsLuaResourceValid())
        Release();
}

// @ 0x82836668
bool ScriptedFsm::Prepare(CgsResource::LuaCodeResource* lpLuaCodeResource,
                          CgsMemory::HeapMalloc* lpHeapMalloc, CgsID lInitialStateId)
{
    mLuaState.Prepare(lpLuaCodeResource, lpHeapMalloc);
    mpCurrentState = nullptr;
    // No explicit start state -> ask the script which state it starts in; otherwise force it.
    if (lInitialStateId == 0)
        SetState(mLuaState.GetCurrentState());
    else
        SetState(lInitialStateId);
    return true;
}

// @ 0x828366D0
bool ScriptedFsm::Release()
{
    if (mpCurrentState != nullptr)
        mpCurrentState->OnLeave();
    mpCurrentState = nullptr;
    CGS_ASSERT(mLuaState.IsLuaResourceValid(), "mLuaState.IsLuaResourceValid()");
    mLuaState.Release();
    return true;
}

// @ 0x82835E90 -- find the state with this id in the table and make it current.
void ScriptedFsm::SetState(CgsID lStateId)
{
    ++muSequenceNumber;

    ScriptedState* lpTarget = nullptr;
    const s32 liCount = GetStateCount();
    for (s32 li = 0; li < liCount; ++li)
    {
        ScriptedState* lpState = GetState(li);
        if (lpState != nullptr && lpState->GetId() == lStateId)
        {
            lpTarget = lpState;
            break;
        }
    }

    if (lpTarget == nullptr)
    {
        char lacId[KI_CGSID_STRING_LEN];
        CgsIDUnCompress(lStateId, lacId);
        // [DIAG] NOT IN THE X360 BINARY (BRN_SCREEN_DIAG=1). This arm is the
        // "the script asked for a state nobody registered" case -- the FSM wants to
        // open a menu that does not exist in the state pool. Named, because the
        // assert text alone does not say WHICH.
        if (getenv("BRN_SCREEN_DIAG") != 0 && CgsDev::Log::gpDebugPrint != 0)
            *CgsDev::Log::gpDebugPrint << "[screen] MISSING STATE '" << lacId
                                       << "' -- the FSM asked for it, the pool has no such state\n";
        CGS_ASSERT(false, "Could not find state with id");   // X360 appends the id (lacId)
        return;
    }

    if (lpTarget == mpCurrentState)
        return;                                              // already current

    // [DIAG] NOT IN THE X360 BINARY (BRN_SCREEN_DIAG=1). The single choke point every
    // scripted screen transition passes through, so ONE witness names every menu the
    // game actually opens, in order. Used to prove menu coverage against the console's
    // own FSM rather than inferring it from which files exist.
    if (getenv("BRN_SCREEN_DIAG") != 0 && CgsDev::Log::gpDebugPrint != 0)
    {
        char lacFrom[KI_CGSID_STRING_LEN];
        char lacTo[KI_CGSID_STRING_LEN];
        lacFrom[0] = '\0';
        // mpCurrentState is declared as the CgsFsm::State base, but within this class it
        // is only ever assigned nullptr or lpTarget (a ScriptedState*), so the id is
        // always there to read. Diag-only path.
        if (mpCurrentState != nullptr)
            CgsIDUnCompress(static_cast<const ScriptedState*>(mpCurrentState)->GetId(), lacFrom);
        CgsIDUnCompress(lStateId, lacTo);
        *CgsDev::Log::gpDebugPrint << "[screen] ENTER '" << lacTo << "' (from '"
                                   << (mpCurrentState != nullptr ? lacFrom : "-") << "') seq "
                                   << static_cast<s32>(muSequenceNumber) << "\n";
    }

    if (mpCurrentState != nullptr)
        mpCurrentState->OnLeave();
    mpCurrentState = lpTarget;
    lpTarget->OnEnter();
}

// @ 0x828368A8 -- Lua indices name authored graph nodes, not C++ state-table slots.
const ScriptedState* ScriptedFsm::GetStateByIndex(s32 liStateIndex)
{
    CGS_ASSERT(mLuaState.IsLuaResourceValid(), "mLuaState.IsLuaResourceValid()");

    char lacStateIndex[128];
    CgsCore::SPrintf(lacStateIndex, 128, "%d", liStateIndex);
    const CgsID lStateIndexId = CgsIDCompress(lacStateIndex);
    char lacStateName[128];
    mLuaState.GetString("GetStateName", lStateIndexId, lacStateName, 128);
    const CgsID lStateId = CgsIDCompress(lacStateName);

    const s32 liNumStates = GetStateCount();
    for (s32 liState = 0; liState < liNumStates; ++liState)
    {
        const ScriptedState* lpState = GetState(liState);
        if (lpState->GetId() == lStateId)
            return lpState;
    }
    return nullptr;
}

// @ 0x82836BA8 -- the script's numeric index for the current state.
s32 ScriptedFsm::GetCurrentStateIndex()
{
    CGS_ASSERT(mLuaState.IsLuaResourceValid(), "mLuaState.IsLuaResourceValid()");
    return mLuaState.GetInt("GetCurrentStateIndex", CgsIDCompress("0"));
}

// Base state-table accessors. The concrete FSM (CgsGui::StateMachine) overrides these to
// index into its fixed state array; the base has no table.
ScriptedState* ScriptedFsm::GetState(s32 /*liIndex*/) { return nullptr; }
s32            ScriptedFsm::GetStateCount()           { return 0; }

// @ 0x82836790 -- push the event's variables into the Lua state via "SetEventVariable",
// then run the scripted transition: NextState(event.id) -> the script's new current state.
void ScriptedFsm::SendEvent(const Event* lpEvent)
{
    CGS_ASSERT(lpEvent != nullptr, "lpEvent != NULL");
    CGS_ASSERT(mLuaState.IsLuaResourceValid(), "mLuaState.IsLuaResourceValid()");

    const s32 liCount = lpEvent->GetVariableCount();
    for (s32 li = 0; li < liCount; ++li)
    {
        const Variable* lpVariable = lpEvent->GetVariable(li);
        if (lpVariable != nullptr)
            lpVariable->ToLua(&mLuaState, "SetEventVariable");
    }

    mLuaState.NextState(lpEvent->GetId());
    SetState(mLuaState.GetCurrentState());
}

// @ 0x82836998 -- retrieve the authored next-state list for a Lua FSM state.
void ScriptedFsm::GetNextStates(s32 liStateIndex,
                                s32* lpaiNextStates,
                                s32* lpiNumNextStates)
{
    if (!mLuaState.IsLuaResourceValid())
    {
        CgsDev::Assert::BeginAssert();
        CgsDev::Assert::FireAssert("mLuaState.IsLuaResourceValid()",
            "..\\..\\..\\GameShared\\GameClasses\\FSM/CgsScriptedFsm.cpp", 263);
        CgsDev::Assert::EndAssert();
    }

    char lacStateIndex[128];
    CgsCore::SPrintf(lacStateIndex, 128, "%d", liStateIndex);
    const CgsID lStateIndexId = CgsIDCompress(lacStateIndex);
    char lacNextStateIndices[128];
    mLuaState.GetString("GetNextStates", lStateIndexId, lacNextStateIndices, 128);

    s32 liOverflowScratch; // ARTIST sp+var_140 receives conversion 33, outside the 32-slot output.
    const s32 liParsedCount = std::sscanf(lacNextStateIndices,
        "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d",
        &lpaiNextStates[0],
        &lpaiNextStates[1],
        &lpaiNextStates[2],
        &lpaiNextStates[3],
        &lpaiNextStates[4],
        &lpaiNextStates[5],
        &lpaiNextStates[6],
        &lpaiNextStates[7],
        &lpaiNextStates[8],
        &lpaiNextStates[9],
        &lpaiNextStates[10],
        &lpaiNextStates[11],
        &lpaiNextStates[12],
        &lpaiNextStates[13],
        &lpaiNextStates[14],
        &lpaiNextStates[15],
        &lpaiNextStates[16],
        &lpaiNextStates[17],
        &lpaiNextStates[18],
        &lpaiNextStates[19],
        &lpaiNextStates[20],
        &lpaiNextStates[21],
        &lpaiNextStates[22],
        &lpaiNextStates[23],
        &lpaiNextStates[24],
        &lpaiNextStates[25],
        &lpaiNextStates[26],
        &lpaiNextStates[27],
        &lpaiNextStates[28],
        &lpaiNextStates[29],
        &lpaiNextStates[30],
        &lpaiNextStates[31],
        &liOverflowScratch);
    *lpiNumNextStates = liParsedCount;

    if (liParsedCount > 32)
    {
        CgsDev::Assert::BeginAssert();
        CgsDev::Assert::FireAssert("Too many state transitions in FSM\n",
            "..\\..\\..\\GameShared\\GameClasses\\FSM/CgsScriptedFsm.cpp", 296);
        CgsDev::Assert::EndAssert();
    }
}

} // namespace CgsFsm
