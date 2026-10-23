#include "GameShared/GameClasses/Gui/Model/State/CgsGuiStateMachine.h"

#include "GameShared/GameClasses/Core/CgsAssert.h"   // CGS_ASSERT

// CgsGui::StateMachine, reconstructed from BURNOUT_X360_ARTIST.XEX. This home bodies
// the X360-emitted StateMachine functions split across the GUI state-machine TUs:
//
//   SetStateInterface() @ 0x824ECAC0 (CgsGuiStateMachine.h -- wires the shared interface)
//   GetState(i)  @ 0x827DDDB0  (CgsGuiStateMachine.h -- the ScriptedFsm virtual override)
//   SetStates()  @ 0x82848700  (CgsGuiStateMachine.cpp -- installs the state table)
//
// The X360 asserts forward through CGS_ASSERT (Begin/Fire/EndAssert); the original
// streamed the count/max into the message via CgsDev::StrStream -- under CGS_ASSERT the
// failure path forwards the plain condition string, and the X360-baked d:\p4 file paths /
// line numbers (148/149, 47/49/55) are dropped per project policy.

namespace CgsGui
{
    // The base ScriptedFsm() ctor (delegated to implicitly) runs ScriptedFsm::Construct (mpCurrentState=0,
    // mLuaState.Construct, sequence=0); the StateMachine adds an empty table + no interface yet. SetStates/
    // SetStateInterface populate them. (No standalone X360 export -- the ctor is inlined at the embedding
    // sites, e.g. inside BrnBaseFlow.)
    StateMachine::StateMachine()
    {
        miNumStates      = 0;
        mpStateInterface = 0;
    }

    // X360 0x824ECAC0. Validate the incoming interface pointer, then store it to
    // mpStateInterface (the `stw r28, 0x218(r27)` tail store, this+0x218). SetStates later
    // wires every owned state to this interface, so it must be non-null first.
    void StateMachine::SetStateInterface(StateInterface* lpStateInterface)
    {
        CGS_ASSERT(lpStateInterface != 0,
                   "Invalid state interface in StateMachine::SetStateInterface");
        mpStateInterface = lpStateInterface;
    }

    // X360 0x827DDDB0. Bounds-check the index against miNumStates (this+0x14), then assert
    // the slot is populated, and return mapGuiStates[liIndex] (this+0x18). Covariant return
    // (CgsGui::State* refines CgsFsm::ScriptedState*).
    State* StateMachine::GetState(s32 liIndex)
    {
        CGS_ASSERT(liIndex >= 0 && liIndex < miNumStates,
                   "Invalid index range in StateMachine::GetState");
        CGS_ASSERT(mapGuiStates[liIndex] != 0,
                   "Attempting to get invalid state in StateMachine::GetState");
        return mapGuiStates[liIndex];
    }

    // X360 0x82848700. Validate the requested count and the wired-up interface, clamp the
    // count to the table capacity, then copy each source State* into mapGuiStates and wire
    // it to mpStateInterface. The final store sets miNumStates (this+0x14).
    void StateMachine::SetStates(State** lpapStates, s32 liNumStates)
    {
        CGS_ASSERT(liNumStates <= KI_MAX_NUM_STATES,
                   "Attempting to add to many states in StateMachine::SetStates");
        CGS_ASSERT(mpStateInterface != 0,
                   "You must set a valid state interface before calling StateMachine::SetStates");

        if (liNumStates > KI_MAX_NUM_STATES)
            liNumStates = KI_MAX_NUM_STATES;

        for (s32 li = 0; li < liNumStates; ++li)
        {
            CGS_ASSERT(lpapStates[li] != 0, "Invalid State pointer in StateMachine::SetStates");
            mapGuiStates[li] = lpapStates[li];
            mapGuiStates[li]->SetStateInterface(mpStateInterface);
        }

        miNumStates = liNumStates;
    }

    // ScriptedFsm virtual override -- the table size SetState/SendEvent scan against. Inlined in
    // the X360 (no standalone export); the count lives at this+0x14 (the SetStates final store).
    s32 StateMachine::GetStateCount()
    {
        return miNumStates;
    }

    // The active state. ScriptedFsm::SetState stores the resolved CgsGui::State into the Fsm base
    // mpCurrentState (covariant: every entry in mapGuiStates is a CgsGui::State), so the current
    // state is that pointer narrowed back to CgsGui::State. Inlined in the X360 (no export).
    State* StateMachine::GetCurrentState()
    {
        return static_cast<State*>(mpCurrentState);
    }

    // CgsGuiStateMachine.h:161 -- narrow the ScriptedFsm lookup to the GUI state type.
    // ARTIST 0x828368A8 resolves Lua GetStateName(index) before scanning object IDs.
    const State* StateMachine::GetStateByIndex(s32 liIndex)
    {
        return static_cast<const State*>(CgsFsm::ScriptedFsm::GetStateByIndex(liIndex));
    }

    // Hand the GUI input-event queue down to every owned state (the mirror of SetStates wiring
    // the StateInterface): BrnBaseFlow::SetInEventQueue @0x827E28A8 forwards here. Reconstructed
    // (inlined in the X360, no standalone export) from the SetStates per-state forwarding pattern.
    void StateMachine::SetInEventQueue(InputBuffer::GuiEventQueue* lpInGuiEventQueue)
    {
        for (s32 li = 0; li < miNumStates; ++li)
        {
            if (mapGuiStates[li] != 0)
                mapGuiStates[li]->SetInEventQueue(lpInGuiEventQueue);
        }
    }
}
