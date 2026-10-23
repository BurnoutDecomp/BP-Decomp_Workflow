#include "GameShared/GameClasses/FSM/CgsFsm.h"   // CgsFsm::Fsm + CgsFsm::State

// CgsFsm::Fsm::Update @ 0x82835CE0
// Per-frame drive of the current state. When a state is set, runs the three-call
// spine in vtable order: PreUpdate (State vtable +12), Update (+8), PostUpdate (+16);
// no-op when there is no current state. Behaviour-faithful to the X360 pseudocode,
// which reads mpCurrentState and dispatches the three State virtuals through its
// vtable. Reuses the committed CgsFsm::State (CgsState.h) by name.
//
// FLAG: mpCurrentState is RE-READ from the member before EACH of the three calls.
// ARTIST asm (0x82835CE0) reloads `lwz r3, 0(r31)` before every dispatch, and the
// DecFIGS asm (0xB52500) does the same (calls 2/3 do `lwz r11, 0(this)`). The
// original source therefore writes `mpCurrentState->...` each time, NOT a cached
// local -- a state transition triggered inside PreUpdate/Update must affect the
// subsequent calls. Caching in a local (the previous reconstruction) was a silent
// behavioural bug.

namespace CgsFsm
{
    void Fsm::Construct()
    {
        mpCurrentState = 0;
    }

    // Swap the active state, running the leaving state's OnLeave and the entering state's
    // OnEnter (the standard FSM transition; CgsFsm::ScriptedFsm uses its own id-based SetState).
    // The X360 inlines these tiny base methods; reconstructed from the FSM semantics.
    void Fsm::SetState(State* lpState)
    {
        if (lpState == mpCurrentState)
            return;
        if (mpCurrentState)
            mpCurrentState->OnLeave();
        mpCurrentState = lpState;
        if (lpState)
            lpState->OnEnter();
    }

    bool Fsm::Release()
    {
        if (mpCurrentState)
            mpCurrentState->OnLeave();
        mpCurrentState = 0;
        return true;
    }

    void Fsm::Update()
    {
        if (mpCurrentState)
        {
            mpCurrentState->PreUpdate();
            mpCurrentState->Update();
            mpCurrentState->PostUpdate();
        }
    }

    void Fsm::Render()
    {
        if (mpCurrentState)
            mpCurrentState->Render();
    }
}
