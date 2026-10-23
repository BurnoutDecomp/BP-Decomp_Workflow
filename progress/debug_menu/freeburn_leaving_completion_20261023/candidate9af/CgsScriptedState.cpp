#include "GameShared/GameClasses/FSM/CgsScriptedState.h"  // CgsFsm::ScriptedState (committed layout)
#include "GameShared/GameClasses/FSM/CgsScriptedFsm.h"     // CgsFsm::ScriptedFsm (complete arg type)

// Reconstructed from BURNOUT_X360_ARTIST.XEX @ 0x82835FF0
//   (CgsFsm::ScriptedState::Construct)
//
// FLAG (silent-bug fix): the previous reconstruction misread the X360 Hex-Rays
// 64-bit `a1` ABI artifact and stored `this` (a self/back-reference) at +8 and a
// 32-bit argument at +0x10. That was wrong on BOTH counts.
//
// The mangled DecFIGS name is the ground truth for the signature:
//   _ZN6CgsFsm13ScriptedState9ConstructEyPNS_11ScriptedFsmE
//     == CgsFsm::ScriptedState::Construct(unsigned long long, CgsFsm::ScriptedFsm*)
// i.e. Construct(CgsID lId, ScriptedFsm* lpFsm)  (CgsID == u64).
//
// ARTIST asm (0x82835FF0), authoritative:
//     std  r4, 8(r3)      ; *(this + 8)    = lId      <- 8-byte store of arg1 (the CgsID)
//     stw  r5, 0x10(r3)   ; *(this + 0x10) = lpFsm    <- 4-byte store of arg2 (the ptr)
//     blr
// DecFIGS asm (0xB526DC) confirms the same two stores (source order reversed):
//     stw  lpFsm, 0x10(this)
//     std  lId,   8(this)
//
// So: arg1 (the CgsID) -> mId (+0x08, 8 bytes); arg2 (the ScriptedFsm*) -> mpFsm
// (+0x10, 4 bytes on the 32-bit ABI). No self-reference is ever stored. With the
// committed CgsScriptedState layout (State vptr @ +0, CgsID mId @ +0x08,
// ScriptedFsm* mpFsm @ +0x10) the offsets land exactly on the asm stores.

namespace CgsFsm
{
    void ScriptedState::Construct(CgsID liId, ScriptedFsm* lpFsm)
    {
        mId   = liId;   // std  r4, 8(this)
        mpFsm = lpFsm;  // stw  r5, 0x10(this)
    }
}
