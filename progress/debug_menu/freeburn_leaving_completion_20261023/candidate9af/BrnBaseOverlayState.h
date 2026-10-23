#pragma once

#include "types.hpp"
#include "BrnCommonTypes.h"                                               // CgsID
#include "GameShared/GameClasses/Gui/Model/State/CgsGuiState.h"           // CgsGui::State (base)
#include "GameShared/GameClasses/Gui/Model/Resources/CgsGuiPopupResource.h" // PopupIcons (mapcIconStateNames indexing)
#include "GameSource/Gui/BrnGuiEventTypeDefs.h"                            // GuiOverlayCompleteEvent / GuiOverlayFullInfoResponse
#include "GameSource/Gui/Flow/Overlay/Components/BrnOverlayComponent.h"    // OverlayComponent (by value)
#include "GameSource/Gui/Flow/Shared/FlaptComponents/BrnGuiFlaptIconComponent.h" // FlaptIconComponent (by value)
#include "GameSource/Gui/Flow/Shared/FlaptComponents/BrnGuiFlaptHelpItem.h"      // FlaptHelpItem (by value x2)
#include "GameSource/Gui/Flapt/BrnFlaptTextFieldRef.h"                     // BrnFlapt::TextFieldRef (by value x2)

// ============================================================================
// GameSource/Gui/Flow/Overlay/States/BrnBaseOverlayState.h
//
// BrnGui::BaseOverlayState -- the shared base of every popup-overlay GUI flow
// state (the Wait / Ok / OkCancel families x CrashNav / InGame / Online): it owns
// the full-screen transition component ("Overlays_mc"), the popup icon, the two
// help items and the title/message text fields, waits for the overlays director's
// full-info response (event 187), dresses the popup from it, and reports how it
// was left (event 189). Reconstructed from BURNOUT_X360_ARTIST.XEX; member names/
// types/enums and the method set from the DecFIGS DWARF (BrnBaseOverlayState.h),
// gated on the X360 ledger.
//
// LAYOUT (X360 offsets, documented; all access is BY NAME):
//   +0x00  CgsGui::State base (0x38)
//   +0x38  mOverlayComponent      (OverlayComponent, 0x18)
//   +0x50  mIconComponent         (FlaptIconComponent, 0x14; vptr @ +0x50)
//   +0x64  mHelpItem1Component    (FlaptHelpItem, 0x48)
//   +0xAC  mHelpItem2Component    (FlaptHelpItem, 0x48)
//   +0xF4  mTitleTextField        (TextFieldRef, 0x0C)
//   +0x100 mMessageTextField      (TextFieldRef, 0x0C)
//   +0x10C mpcFlashFileId         (const char*)
//   +0x110 mCurrentOverlayId      (CgsID)
//   +0x118 meLeaveMethod          (GuiOverlayCompleteEvent::LeaveMethod)
//   +0x11C meInternalState        (OverlayInternalState)
//   +0x120 mpGuiCache             (GuiCache*)
//   +0x124 mauExpectedComponentIds[8] (u32)
//   +0x144 muNumExpectedComponents    (u32)
//   sizeof 0x148
//
// VTABLE (new slots after CgsGui::State's, X360-attested): Prepare @+0x24 /
// UpdateRunning @+0x28 / SetupOverlay @+0x2C / FillInPopupType @+0x30 (OnEnter
// @0x824B1E60 dispatches +0x30 then +0x24; UpdateWFInfo @0x824B25D0 dispatches
// +0x2C with the full-info response) -- matching the DWARF declaration order.
// ============================================================================

namespace BrnGui
{
    class GuiCache;

    struct BaseOverlayState : public CgsGui::State
    {
        // DWARF BrnBaseOverlayState.h:63 -- the popup lifecycle.
        enum OverlayInternalState
        {
            E_OVERLAYINTERNALSTATE_START        = 0,
            E_OVERLAYINTERNALSTATE_WFINIT       = 1,
            E_OVERLAYINTERNALSTATE_SETUPOVERLAY = 2,
            E_OVERLAYINTERNALSTATE_WFTRANSIN    = 3,
            E_OVERLAYINTERNALSTATE_RUNNING      = 4,
            E_OVERLAYINTERNALSTATE_WFTRANSOUT   = 5,
            E_OVERLAYINTERNALSTATE_DONE         = 6,
            E_OVERLAYINTERNALSTATE_COUNT        = 7,
        };

        // DWARF h:38/h:39 -- the component roles the popups use.
        typedef FlaptIconComponent OverlayIconComponent;
        typedef FlaptHelpItem      OverlayHelpItem;

        // DWARF h:157.
        static const u32 KU_MAX_INIT_COMPONENTS_NUM = 8;

        // ---- CgsGui::State overrides (this TU) ----
        // @0x824B1E60 (DWARF cpp:80) -- reset the popup bookkeeping, register for the
        // observed events, construct the shared components, then FillInPopupType() and
        // Prepare().
        virtual void OnEnter();

        // @0x824B2DC8 (DWARF cpp:326) -- post the GuiOverlayCompleteEvent (id 189,
        // 32 bytes on channel 40), unregister (priority event 187 + the observed set),
        // and reset the components.
        virtual void OnLeave();

        // @0x824B2B38 (DWARF cpp:192) -- the popup state-machine pump. Ledger-wise it
        // was DWARF-misattributed to a header grab-bag TU (CgsStrStream.h) and marked
        // reviewed there with no committed body; recovered HERE at its real home (the
        // established grab-bag-landing pattern).
        virtual void Update();

        // ---- new virtuals (X360 vtable order; see header banner) ----
        // @0x824B1F80 (DWARF cpp:119) -- bind "Overlays_mc" out of the flapt file and
        // reset the components.
        virtual void Prepare();

        // DWARF h:98 -- the RUNNING-phase hook (X360 vtbl +0x28; Update @0x824B2C8C
        // dispatches it). Every popup family overrides it and the X360 has no base
        // symbol, so it is pure here.
        virtual bool UpdateRunning() = 0;

        // @0x824B1690 (DWARF cpp:458) -- dress the popup from the director's full-info
        // response: title/message localised text (with up to
        // GuiOverlayFullInfoResponse::MKI_MAX_PARAMS_IN_MESSAGE formatted parameters)
        // and the icon state.
        virtual void SetupOverlay(const GuiOverlayFullInfoResponse* lpResponse);

        // DWARF h:110 declares GetResourcesToLoad on this class too; the base carries
        // no X360 body (each concrete popup state overrides it), so it is not
        // redeclared here -- CgsGui::State's is inherited.

        // @0x824B2670 (DWARF cpp:510) -- drain (and discard) the state's in-queue.
        // Like Update, its ledger row was DWARF-misattributed (CgsVariableEventQueue.h)
        // and marked reviewed with no committed body; recovered HERE at its real home.
        void UpdatePermanent();

    protected:
        // DWARF h:136 -- fill in the popup's expected components / flash file id
        // (X360 vtbl +0x30; OnEnter dispatches it). Every popup family overrides it
        // and the X360 has no base symbol, so it is pure here.
        virtual void FillInPopupType() = 0;

        // DWARF cpp:659 -- drop every bound component handle. The X360 has no
        // standalone symbol for it (always inlined -- the 12 zero stores in OnEnter /
        // Prepare / OnLeave); recovered here as the shared helper those three call.
        void ResetOverlayComponents();

    private:
        // @0x824B2490 (DWARF cpp:351) -- drain the state's in-queue for the GuiCache
        // pointer event (id 64) and latch it.
        void GetCache();

        // @0x824B18B8 (DWARF cpp:595) -- once the transition movie is on the named
        // frame, find + bind the icon/help-item/title/message children.
        void SetupOverlayComponents(const char* lpcTransition);

        // @0x824B25D0 (DWARF cpp:423) -- poll the in-queue for the overlays director's
        // full-info response (event 187); on arrival latch the overlay id and
        // SetupOverlay(). True once received.
        bool UpdateWFInfo();

        // DWARF cpp:140 -- true (once) when the overlay component's transition-complete
        // flag has been raised. No standalone X360 symbol (always inlined -- the
        // flag-test/clear pairs inside Update @0x824B2C3C and @0x824B2CC8); recovered
        // here from those instances.
        bool UpdateWFTransComplete();

    protected:
        OverlayComponent      mOverlayComponent;     // +0x38 (DWARF h:118)
        OverlayIconComponent  mIconComponent;        // +0x50 (DWARF h:119)
        OverlayHelpItem       mHelpItem1Component;   // +0x64 (DWARF h:120)
        OverlayHelpItem       mHelpItem2Component;   // +0xAC (DWARF h:121)
        BrnFlapt::TextFieldRef mTitleTextField;      // +0xF4 (DWARF h:126)
        BrnFlapt::TextFieldRef mMessageTextField;    // +0x100 (DWARF h:127)
        const char*           mpcFlashFileId;        // +0x10C (DWARF h:130)
        CgsID                 mCurrentOverlayId;     // +0x110 (DWARF h:132)
        GuiOverlayCompleteEvent::LeaveMethod meLeaveMethod; // +0x118 (DWARF h:133)

    private:
        OverlayInternalState  meInternalState;       // +0x11C (DWARF h:140)
        GuiCache*             mpGuiCache;             // +0x120 (DWARF h:141)
        u32                   mauExpectedComponentIds[KU_MAX_INIT_COMPONENTS_NUM]; // +0x124 (DWARF h:158)
        u32                   muNumExpectedComponents; // +0x144 (DWARF h:159)

        // ---- statics (DWARF cpp:26-51; values read from the decrypted XEX rodata,
        //      .rodata @0x82063CC4 onward) ----
        static const s32  maiEventToObserve[5];       // { 21, 6, 64, 187, 188 }
        static const s32  miNumEventsObserved;        // == 5
        static const s32  maiEventTypeOverridden[1];  // { 6 }
        static const s32  miNumOverriddenEvents;      // == 1
        static const char macOverlayComponentName[12];   // "Overlays_mc"
        static const char macTitleTextFieldName[25];     // "Overlays_mc_Title_txt_mc"
        static const char macMessageTextFieldName[24];   // "Overlays_mc_Main_txt_mc"
        static const char macIconComponentName[21];      // "Overlays_mc_Icons_mc"
        static const char* const mapcIconStateNames[CgsGui::E_POPUPICONS_COUNT]; // { "invisible", "warning" }
        static const char macHelpItem1ComponentName[22]; // "Overlays_mc_helpItem0"
        static const char macHelpItem2ComponentName[22]; // "Overlays_mc_helpItem1"
    };
}
