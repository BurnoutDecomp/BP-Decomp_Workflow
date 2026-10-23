#include "GameSource/Gui/Flow/Overlay/Components/BrnOverlayComponent.h"

#include "GameShared/GameClasses/Core/CgsAssert.h"   // CGS_ASSERT

// Reconstructed store-for-store from BURNOUT_X360_ARTIST.XEX.
//
//   TransitionCompleteCallback @0x8241C198 -- the apt "transition complete" timeline
//   callback. The apt system hands the OverlayComponent back as the user-data pointer;
//   the callback asserts it is non-null, then raises the component's transition-complete
//   flag. The X360 inlines SetTransitionComplete to a direct `stb 1, 0x14`; we restore the
//   named setter call. The second callback argument (a u16 timeline/frame tag) is unused
//   by this handler (the X360 never touches r4).
//
//   RunOverlay(flash id, frame label) @0x824B1498 (ledger TU class:BrnGui::OverlayComponent)
//   -- assert the flash id (h:115), play the overlay movie on it, rebind
//   mTransitionMovieClipRef to the "singleOverlay_mc" child on the resulting frame
//   (FindChildMovieClipOnFrame @0x8246C8B0 -- the on-frame variant, NOT the recursive
//   search), then play the phase label on that child. Called by
//   BrnGui::BaseOverlayState::Update with "waiting"/"transin"/"transout".

namespace BrnGui
{

// @ 0x8241C120 -- bind the state channel (the base Construct inline, with its
// h:113 "lpStateInterface" tripwire + mAptRef invalidate), then clear the
// transition clip handle and the transition-complete flag (the X360 zeroes
// this+0x0C/+0x10/+0x14 after the base's stores). The name/parent args are
// unused by the body (DWARF shape Construct(name, iface, parent)).
void OverlayComponent::Construct(const char* /*lacName*/,
                                 CgsGui::StateInterface* lpStateInterface,
                                 const char* /*lpcParentName*/)
{
    BrnFlaptComponent::Construct(lpStateInterface);

    mTransitionMovieClipRef.SetInvalid();
    mbTransitionComplete = false;
}

// @ 0x82427BF0 -- bind the named overlay clip through the base Prepare with NO
// parent prefix (the X360 body carries the base inline const-propped with a null
// parent: the h:133 "lacName != NULL" tripwire, the bare-name FindComponent, the
// mpMovieClipInst assert and the timeline reset -- no composite-key path), then
// install the transition-complete timeline callback on the bound clip and clear
// the transition clip handle + flag.
void OverlayComponent::Prepare(const char* lacName, const BrnFlapt::FileRef& lFile,
                               const char* /*lacParentName*/)
{
    BrnFlaptComponent::Prepare(lacName, lFile, 0);

    mAptRef.SetFrameTriggerCallback(reinterpret_cast<void*>(&TransitionCompleteCallback), this);

    mTransitionMovieClipRef.SetInvalid();
    mbTransitionComplete = false;
}

// @ 0x8241C198
void OverlayComponent::TransitionCompleteCallback(void* lpUserData, u16 /*luArg*/)
{
    CGS_ASSERT(NULL != lpUserData, "NULL != lpUserData");

    OverlayComponent* lpThis = static_cast<OverlayComponent*>(lpUserData);
    lpThis->SetTransitionComplete(true);
}

// @ 0x824B1498
void OverlayComponent::RunOverlay(const char* lpcOverlayFlashId, const char* lpcFrameLabel)
{
    // Non-gating tripwire (h:115): the popup family must have filled in its flash id.
    CGS_ASSERT(NULL != lpcOverlayFlashId, "NULL != lpcOverlayFlashId");

    mAptRef.GotoAndPlayLabel(lpcOverlayFlashId);

    // The frame the label landed on carries the popup's single-overlay child; adopt it
    // as the transition clip and run the phase label on it.
    BrnFlapt::MovieClipRef lSingleOverlayClip;
    mTransitionMovieClipRef =
        *mAptRef.FindChildMovieClipOnFrame(&lSingleOverlayClip, "singleOverlay_mc");
    mTransitionMovieClipRef.GotoAndPlayLabel(lpcFrameLabel);
}

} // namespace BrnGui
