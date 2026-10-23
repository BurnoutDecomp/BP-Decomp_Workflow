#ifndef BRN_OVERLAY_COMPONENT_H
#define BRN_OVERLAY_COMPONENT_H

#include "types.hpp"
#include "GameSource/Gui/Flow/Shared/FlaptComponents/BrnGuiFlaptComponent.h"  // BrnGui::BrnFlaptComponent (base)
#include "GameSource/Gui/Flapt/BrnFlaptMovieClipRef.h"                        // BrnFlapt::MovieClipRef (embedded)
#include "GameShared/GameClasses/Core/CgsAssert.h"                            // CGS_ASSERT (RunOverlay)

// ============================================================================
// GameSource/Gui/Flow/Overlay/Components/BrnOverlayComponent.h
//
// BrnGui::OverlayComponent -- an apt-driven full-screen overlay (transition wipe)
// component. It owns one transition movie-clip ref and a "transition complete" flag
// that an apt timeline callback raises when the wipe finishes. Derives from
// BrnGui::BrnFlaptComponent. Reconstructed from BURNOUT_X360_ARTIST.XEX; member
// names/types pinned from the DecFIGS DWARF (BrnOverlayComponent.h), gated on the
// X360 ledger.
//
// LAYOUT (base proven non-polymorphic @ +0x00 / size 0x0C by the FlaptComponent
// siblings; the mbTransitionComplete store is proven by TransitionCompleteCallback
// @0x8241C198 -> `stb 1, 0x14(r31)`):
//   +0x00  BrnFlaptComponent base (mpStateInterface @ +0x00, mAptRef @ +0x04)  -- 0x0C
//   +0x0C  mTransitionMovieClipRef  (BrnFlapt::MovieClipRef, 8 bytes)
//   +0x14  mbTransitionComplete     (bool)
//   sizeof 0x18
//
// SetTransitionComplete/GetTransitionComplete have no standalone X360 symbol (always
// inlined), so they are defined inline here. The other members (Construct/Prepare/
// RunOverlay/GetTransitionMovieClipRef) land with their own TUs; declare them additively
// as those land. All member access is BY NAME.
// ============================================================================

namespace BrnGui
{
    class OverlayComponent : public BrnFlaptComponent
    {
    public:
        // The apt transition clip's "complete" timeline callback raises this flag; the
        // overlay's owner polls it to know the wipe has finished.
        bool GetTransitionComplete() const            { return mbTransitionComplete; }
        void SetTransitionComplete(bool lbComplete)   { mbTransitionComplete = lbComplete; }

        // ADDITIVE GROW (BrnGui::InvisibleOverlayState::OnEnter @0x824B1568, which drives
        // all three): Construct / Prepare are the component's own ledger functions
        // (declaration-only; shapes per the FlaptComponent-family convention and the
        // caller's ABI -- Construct(name, iface, parent=0); Prepare(name, file, parent=0)).
        void Construct(const char* lacName, CgsGui::StateInterface* lpStateInterface,
                       const char* lpcParentName);
        void Prepare(const char* lacName, const BrnFlapt::FileRef& lFile,
                     const char* lacParentName);

        // GetTransitionMovieClipRef -- the transition clip handle. ADDITIVE GROW
        // (BrnGui::BaseOverlayState::SetupOverlayComponents @0x824B18B8, which inlines
        // it: the searched ref is this+0x44 == &mTransitionMovieClipRef, and the assert
        // text names the DWARF accessor's result "lpTransitionMovieClipRef").
        BrnFlapt::MovieClipRef* GetTransitionMovieClipRef() { return &mTransitionMovieClipRef; }

        // RunOverlay (BrnOverlayComponent.h:141, header-inline on the X360 -- the
        // InvisibleOverlayState::OnEnter asm carries its body: the flash-id assert then
        // the string-keyed GotoAndPlayLabel @0x8246F3E8 on the component's clip): jump
        // the overlay movie to the named flash label and play it.
        void RunOverlay(const char* lpcOverlayFlashId)
        {
            CGS_ASSERT(NULL != lpcOverlayFlashId, "NULL != lpcOverlayFlashId");
            mAptRef.GotoAndPlayLabel(lpcOverlayFlashId);
        }

        // RunOverlay(flash id, frame label) @ 0x824B1690's caller family -- the
        // out-of-line overload @0x824B1498 (assert @h:115): play the overlay movie on
        // the popup family's flash label, rebind the transition clip to the
        // "singleOverlay_mc" child present on that frame, and play the phase label
        // ("waiting"/"transin"/"transout") on it. Bodied in BrnOverlayComponent.cpp.
        void RunOverlay(const char* lpcOverlayFlashId, const char* lpcFrameLabel);

    private:
        // TransitionCompleteCallback @0x8241C198 -- the apt timeline callback the overlay
        // registers on its transition clip. The X360 passes the OverlayComponent in r3 as
        // the explicit user-data pointer (not as `this`), so this is a STATIC member.
        static void TransitionCompleteCallback(void* lpUserData, u16 luArg);

        BrnFlapt::MovieClipRef mTransitionMovieClipRef;   // +0x0C
        bool                   mbTransitionComplete;       // +0x14
    };
}

#endif // BRN_OVERLAY_COMPONENT_H
