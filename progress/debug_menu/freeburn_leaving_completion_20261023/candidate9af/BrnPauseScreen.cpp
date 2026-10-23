#include "GameSource/Gui/Flow/Screen/States/BrnPauseScreen.h"

#include "GameShared/GameClasses/Gui/Model/State/CgsGuiStateInterface.h"  // StateInterface / GuiEventNetworkSuspension / PlayAptMovie
#include "GameShared/GameClasses/Gui/CgsGuiEvent.h"                       // CgsGui::GuiEvent<N>
#include "GameShared/GameClasses/Module/CgsVariableEventQueue.h"          // the state in-queue
#include "GameShared/GameClasses/Core/CgsAssert.h"                        // CGS_ASSERT
#include "GameShared/GameClasses/Development/CgsStrStream.h"              // CgsDev::StrStreamBase (unexpected-event log)
#include "GameShared/GameClasses/Development/Log/CgsLog.h"                // CgsDev::Log::gpDebugPrint / Message::gxMessageFilterFlags
#include "GameSource/Gui/BrnGuiCache.h"                                   // BrnGui::GuiCache (resource pins + apt-component watch)
#include "GameSource/Gui/BrnGuiEventTypeDefs.h"                           // BrnGui::GuiEventActivateCrashNav / GuiFlow
#include "GameSource/Input/GameInputActions.h"                       // EGameInputActions (the controller action vocabulary)

// BrnGui::PauseScreen -- reconstructed from BURNOUT_X360_ARTIST.XEX:
//   OnEnter               @0x824CFCE0
//   OnLeave               @0x824CFDF0
//   Update                @0x824DA0C0
//   HandleControllerInput @0x824CFE78  (this TU's 1 ledger function)
//   GetResourcesToLoad    = the ICF fold @0x825011B0 (== BrnGui::Video::
//                           GetResourcesToLoad; the PauseScreen vtable slot @0x82074298)
//   (the ctor is the vtable-establishing default, inlined into BrnScreenFlow::Prepare
//    @0x82523E50 -- no standalone X360 export; the PC implicit default matches.)
//
// The SCREEN flow's in-game pause state ("PAUSED"), entered off InGame's pause path.
// OnEnter shuts the HUD components down, parks the CrashNav (front-end map) flow and
// registers the leaving-game overlay wait-finish handshake; Update then walks the
// LOADING -> INITIALISING -> PROMPT ladder off the per-frame cache event: pin the
// BRNGENERALPAUSE apt (resource 153) + the shared B5MenuItem flapt (36), play the
// "BrnGeneralPause" movie on level 3, wait for the menu row's apt component, bring the
// one-option menu up. HandleControllerInput backs the prompt out into the game
// (GO_BACK) or hands off to the colour-calibration screen (TO_COLOUR).
//
// HandleControllerInput X360 asm walk: gate on meSubState == E_SUBSTATE_PROMPT
// (this+0x38 == 2), then switch on the controller-action sub-id (payload word +4 of
// the action event; jump table base 38, 13 cases):
//   38            -> SendStateEvent("TO_COLOUR")   (the colour-calibration screen hand-off)
//   45 / 49 / 50  -> the "resume game" path: assert the highlighted pause option is the
//                    single valid one (lbz this+0xE5 == mPauseOptions.miHighlightedIndex;
//                    the pause menu has exactly one option -- KAPC_PAUSE_OPTION_STRING_IDS
//                    is a 1-entry table -- so a non-zero index is "Invalid pause option
//                    selected", cpp:277), then:
//                      OutputGuiEvent<GuiEventActivateCrashNav>({ 1, 0 })   (@0x82493938)
//                      OutputGuiEvent<GuiEventNetworkSuspension>({ 0 })     (@0x82493A88)
//                      AddEvent(out-queue, GuiEvent<533>{ 1, 533, 12 }, channel 40, 16)
//                      SendStateEvent("GO_BACK")
//   anything else -> ignored.

namespace BrnGui
{
namespace
{
    // ---- observed-event ids (the 2-entry registered table below) ----------------------
    const s32 KI_EVENT_CONTROLLER = 6;    // controller action (sub-id @+4)
    const s32 KI_EVENT_GUI_CACHE  = 64;   // per-frame cache event (GuiCache* payload)

    const s32 KI_CHANNEL_GUI_OUT      = 40;  // GuiEventOut
    const s32 KI_CHANNEL_GUI_INTERNAL = 42;  // internal/HUD-component channel

    // ---- Controller action sub-ids (payload word +4 of the action event). Named from the
    //      DWARF vocabulary (GameSource/Input/GameInputActions.h). ⚠️ ALL THREE OF THE
    //      RESUME IDS USED TO BE MISNAMED HERE, each one shifted onto its neighbour's
    //      meaning: 45 was called "BACK", 49 "STOP" and 50 "START". 45 is GUI_START, 49 is
    //      GUI_SELECT and 50 is GUI_CANCEL. Nothing about the switch changes -- all three
    //      resume -- but the names are no longer evidence for the wrong PC binding. ------
    const s32 KI_ACTION_GUI_DPAD_DOWN = E_GAMEINPUTACTIONS_GUI_DPAD_DOWN; // 38 -> colour-calibration hand-off
    const s32 KI_ACTION_GUI_START     = E_GAMEINPUTACTIONS_GUI_START;     // 45 -> leave the pause menu (resume)
    const s32 KI_ACTION_GUI_SELECT    = E_GAMEINPUTACTIONS_GUI_SELECT;    // 49 -> leave the pause menu (resume)
    const s32 KI_ACTION_GUI_CANCEL    = E_GAMEINPUTACTIONS_GUI_CANCEL;    // 50 -> leave the pause menu (resume)

    typedef CgsModule::VariableEventQueue<18432, 16> StateInputQueue;

    // The event-64 payload view (the queue delivers the header-stripped payload; the
    // member name is the X360 assert's: "lpCacheEvent->mpCachePointer").
    struct GuiEventCache : public CgsModule::Event
    {
        GuiCache* mpCachePointer;
    };

    // The GuiEvent<533> command the pause screen posts on its out-queue when the pause
    // menu closes back into the game (the sibling of the GuiEvent<532> record
    // BrnPausedHudState posts on enter). The X360 fills { muHeader0 = 1, muEventType = 533,
    // muHeader2 = 12 } and pushes a 16-byte record on channel 40; the trailing word is
    // left uninitialised.
    struct GuiEventPauseScreenClosed : public CgsGui::GuiEvent<533>
    {
        u32 muReserved;   // +0x0C (X360 leaves this gap word uninitialised; record size 16)

        GuiEventPauseScreenClosed() : CgsGui::GuiEvent<533>(1, 12) {}
    };

    // The { 1, 148, 12, flag } HUD-components command record (BrnInGame.cpp's
    // GuiCommandEvent16<148> twin: flag 1 = bring the HUD components up, 0 = shut them
    // down; the X360 zeroes only the flag byte, the pad is modelled zeroed).
    struct GuiEventHudComponentsCommand : public CgsGui::GuiEvent<148>
    {
        u8 mu8Enable;    // +0x0C
        u8 maPad[3];

        explicit GuiEventHudComponentsCommand(u8 lu8Enable)
            : CgsGui::GuiEvent<148>(1, 12), mu8Enable(lu8Enable)
        {
            maPad[0] = maPad[1] = maPad[2] = 0;
        }
    };

    // The OutputGuiEvent<BrnGui::GuiOverlayWaitFinishRequest> wire record (@0x82476E98):
    // { 8, 188, 16, <pad>, CgsID }, channel 40, 24 bytes (BrnInGame.cpp's wire twin).
    struct GuiOverlayWaitFinishWire : public CgsGui::GuiEvent<188>
    {
        u32                         muPad0C;    // +0x0C (8-aligned payload)
        GuiOverlayWaitFinishRequest mRequest;   // +0x10 (the compressed overlay id)

        GuiOverlayWaitFinishWire() : CgsGui::GuiEvent<188>(8, 16), muPad0C(0) {}
    };
}

// ---- statics (the DWARF cpp:26-51 block; values read from the decrypted XEX) ----------

// @ 0x82066660 (.rdata): the 2 observed event ids, in table order.
const s32 PauseScreen::maiEventToObserve[2] =
{
    KI_EVENT_CONTROLLER,   // 6
    KI_EVENT_GUI_CACHE,    // 64
};
const s32 PauseScreen::miNumEventsObserved = 2;   // @ 0x82066668

// @ 0x82F2728C (.data) / count @ 0x82F2729C: the pause movie's apt bundle (id 153 ==
// "BrnGeneralPause" in the GUI resource-name table @0x82F278E0) + the shared menu-item
// widget flapt (id 36 == "B5MenuItem"). Update pins these through the GuiCache; the
// GetResourcesToLoad virtual deliberately reports none (the X360 fold below).
const CgsGui::sResourceTuple PauseScreen::maResourcesToLoad[2] =
{
    { 153, CgsGui::E_GUI_RESOURCETYPE_APT },
    {  36, CgsGui::E_GUI_RESOURCETYPE_FLAPT_HD_BUNDLE },
};
const u32 PauseScreen::muNumResourcesToLoad = 2;   // @ 0x82F2729C

// @ 0x8206666C (.rdata): the menu component's base name (rows are "<base>_<i>").
const char PauseScreen::KAC_OPTION_CPT_NAME_BASE[7] = "Option";

// @ 0x82F272A0 (.data): the single pause option's localisation key.
const char* PauseScreen::KAPC_PAUSE_OPTION_STRING_IDS[1] =
{
    "$ONLINE_PAUSE_OPTION_CONTINUE",   // -> the string @0x8205CB90
};

// @ 0x824CFCE0 -- register the 2-event table, reset the substate ladder, shut the HUD
// components down, park the CrashNav flow behind the menu, register the leaving-game
// overlay wait-finish handshake and build the one-row pause-options menu.
void PauseScreen::OnEnter()
{
    mpStateInterface->RegisterForEvents(maiEventToObserve, miNumEventsObserved);
    meSubState = E_SUBSTATE_LOADING;

    // { 1, 148, 12, flag=0 } on the internal channel -- HUD components down (the flag=1
    // twin is InGame::OnEnter's bring-up).
    GuiEventHudComponentsCommand lHudDown(0);
    mpStateInterface->GetOutputEventQueue()->AddEvent(
        reinterpret_cast<const CgsModule::Event*>(&lHudDown), KI_CHANNEL_GUI_INTERNAL, 16);

    // { 8, 191, 12, 0, 0 } -- deactivate the CrashNav (front-end map) flow while the
    // pause menu owns the screen (HandleControllerInput re-activates it on resume).
    GuiEventActivateCrashNav lDeactivateCrashNav(false);
    mpStateInterface->GetOutputEventQueue()->AddEvent(
        reinterpret_cast<const CgsModule::Event*>(&lDeactivateCrashNav), KI_CHANNEL_GUI_OUT,
        static_cast<s32>(sizeof(GuiEventActivateCrashNav)));

    // The 24-byte 188 record: hold the flow until the leaving-game overlay fully hides.
    GuiOverlayWaitFinishWire lWaitFinish;
    lWaitFinish.mRequest.Construct("CNOnlLvgGame");
    mpStateInterface->GetOutputEventQueue()->AddEvent(
        reinterpret_cast<const CgsModule::Event*>(&lWaitFinish), KI_CHANNEL_GUI_OUT,
        static_cast<s32>(sizeof(GuiOverlayWaitFinishWire)));

    mPauseOptions.Construct(KAC_OPTION_CPT_NAME_BASE, mpStateInterface, 1, 0, -1);
}

// @ 0x824CFDF0 -- drop the pause movie (the X360 inlines StateInterface::PlayAptMovie's
// { 8, 18, 12, "", 3 } channel-41 record) and unregister the event table.
void PauseScreen::OnLeave()
{
    mpStateInterface->PlayAptMovie("", 3);
    mpStateInterface->UnRegisterForEvents(maiEventToObserve, miNumEventsObserved);
}

// @ 0x824DA0C0 -- drain the in-queue: controller actions to HandleControllerInput, the
// per-frame cache event through the LOADING -> INITIALISING -> PROMPT ladder, anything
// else to the filtered debug log. Then clear the queue and tick the menu component (the
// X360 dispatches component vtable slot 5 == SelectableGroup::Update).
void PauseScreen::Update()
{
    StateInputQueue* lpInQueue = reinterpret_cast<StateInputQueue*>(mpInGuiEventQueue);
    const CgsModule::Event* lpEvent = 0;
    s32 liSize = 0;

    for (s32 liEventId = lpInQueue->GetFirstEvent(&lpEvent, &liSize);
         lpEvent != 0;
         liEventId = lpInQueue->GetNextEvent(lpEvent, &lpEvent, &liSize))
    {
        if (liEventId == KI_EVENT_CONTROLLER)
        {
            HandleControllerInput(lpEvent);
        }
        else if (liEventId == KI_EVENT_GUI_CACHE)
        {
            const GuiEventCache* lpCacheEvent = reinterpret_cast<const GuiEventCache*>(lpEvent);
            CGS_ASSERT(lpCacheEvent->mpCachePointer != 0, "lpCacheEvent->mpCachePointer");   // cpp:132
            GuiCache* lpCache = lpCacheEvent->mpCachePointer;

            switch (meSubState)
            {
            case E_SUBSTATE_LOADING:
                // Pin the pause apt + the menu-item flapt; once resident, watch the menu
                // row's apt component, start the pause movie and move the ladder on.
                if (lpCache->EnsureResourcesAreLoaded(maResourcesToLoad, muNumResourcesToLoad))
                {
                    lpCache->ClearExpectedAptComponentList(E_GUIFLOW_SCREEN);
                    lpCache->AppendExpectedAptComponent(E_GUIFLOW_SCREEN, "Option_0");
                    // The X360 reads the movie name out of the GUI resource-name table
                    // (off_82F27B44 == entry 153, "BrnGeneralPause"); reconstructed as the
                    // literal that entry holds (the BrnPreloadOverlayState idiom).
                    mpStateInterface->PlayAptMovie("BrnGeneralPause", 3);
                    meSubState = E_SUBSTATE_INITIALISING;
                }
                break;

            case E_SUBSTATE_INITIALISING:
                // Wait for the menu row's apt component, then bring the one-option menu
                // up ("continue") and open the prompt.
                if (lpCache->AreAllAptComponentsInitialised(E_GUIFLOW_SCREEN))
                {
                    mPauseOptions.SetupMenu(1, false);
                    mPauseOptions.SetText(0, KAPC_PAUSE_OPTION_STRING_IDS[0]);
                    meSubState = E_SUBSTATE_PROMPT;
                }
                break;

            case E_SUBSTATE_PROMPT:
                break;

            default:
                CGS_ASSERT(false, "Invalid internal state in BrnPauseScreen::Update()");   // cpp:177
                break;
            }
        }
        else if (CgsDev::Message::gxMessageFilterFlags & 1)
        {
            // The X360 streams the diagnostic through the debug print (cpp:187).
            *CgsDev::Log::gpDebugPrint
                << "Unexpected event received : " << liEventId
                << " in "
                << "..\\..\\..\\GameSource\\Gui/Flow/Screen/States/BrnPauseScreen.cpp"
                << " at line " << 187 << "\n";
        }
    }

    lpInQueue->Clear();
    mPauseOptions.Update();
}

// @ the ICF fold 0x825011B0 (== BrnGui::Video::GetResourcesToLoad; the PauseScreen
// vtable slot @0x82074298): only the count is zeroed; the tuple out-pointer is
// deliberately left untouched. The real pause tuples (maResourcesToLoad above) go
// through GuiCache::EnsureResourcesAreLoaded in Update instead.
void PauseScreen::GetResourcesToLoad(const CgsGui::sResourceTuple** /*lppResourceTuples*/,
                                     u32* lpuNumberOfResources) const
{
    *lpuNumberOfResources = 0;
}

// @ 0x824CFE78
void PauseScreen::HandleControllerInput(const CgsModule::Event* lpEvent)
{
    if (meSubState != E_SUBSTATE_PROMPT)
        return;

    // The action sub-id rides in the event's +4 payload word (same idiom as the boot
    // states -- see BrnBootLegal.cpp's in-queue drain).
    const s32 liAction =
        *reinterpret_cast<const s32*>(reinterpret_cast<const u8*>(lpEvent) + 4);

    switch (liAction)
    {
    case KI_ACTION_GUI_DPAD_DOWN:
        SendStateEvent("TO_COLOUR");
        break;

    case KI_ACTION_GUI_START:
    case KI_ACTION_GUI_SELECT:
    case KI_ACTION_GUI_CANCEL:
    {
        // The pause menu carries exactly one option (KAPC_PAUSE_OPTION_STRING_IDS), so any
        // non-zero highlighted index is invalid (X360 cpp:277) -- fire the assert and do
        // NOT run the resume path (the X360 returns straight out of the assert branch).
        if (mPauseOptions.miHighlightedIndex == 0)
        {
            // Wake the CrashNav (front-end map) flow, lift the network suspension, post
            // the pause-closed command record, and back out of this screen.
            GuiEventActivateCrashNav lActivateCrashNav(true);
            mpStateInterface->OutputGuiEvent(lActivateCrashNav);

            CgsGui::GuiEventNetworkSuspension lNetworkSuspension(false);
            mpStateInterface->OutputGuiEvent(lNetworkSuspension);

            GuiEventPauseScreenClosed lPauseClosed;
            mpStateInterface->GetOutputEventQueue()->AddEvent(
                reinterpret_cast<const CgsModule::Event*>(&lPauseClosed), KI_CHANNEL_GUI_OUT, 16);

            SendStateEvent("GO_BACK");
        }
        else
        {
            CGS_ASSERT(false, "Invalid pause option selected");
        }
        break;
    }

    default:
        break;
    }
}
}
