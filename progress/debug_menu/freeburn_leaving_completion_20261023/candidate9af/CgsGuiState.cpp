#include "GameShared/GameClasses/Gui/Model/State/CgsGuiState.h"   // CgsGui::State (+ ScriptedState base, StateInterface fwd, sResourceTuple fwd)

#include "GameShared/GameClasses/Core/CgsAssert.h"       // CGS_ASSERT
#include "GameShared/GameClasses/Core/CgsStringUtils.h"  // CgsCore::SPrintf
#include "GameShared/GameClasses/Fsm/CgsEvent.h"         // CgsFsm::Event
#include "GameShared/GameClasses/Fsm/CgsScriptedFsm.h"   // CgsFsm::ScriptedFsm::IsLuaResourceValid (mpFsm's concrete type)
#include "GameShared/GameClasses/Gui/CgsGuiEvent.h"       // CgsGui::GuiEvent<1>
#include "GameShared/GameClasses/Gui/Model/State/CgsGuiStateInterface.h" // output queue

#include <cstring>   // strlen

// CgsGui::State base bodies. The X360 keeps these out-of-line in CgsGuiState.cpp; the GUI virtuals are
// no-op defaults (derived states override OnEnter/OnLeave/Update/GetResourcesToLoad) and the setters just
// store the channel/queue. Reconstructed minimally to close the link for the boot HUD-flow states.
//
// SetStateInterface @ 0x82846838 is the X360-emitted out-of-line setter for this class (its own ledger
// TU): assert the incoming interface is non-null, then store it to mpStateInterface (this+0x1C, the
// `stw r28, 0x1C(r27)` tail store). The original streamed the d:\p4-baked file/line via CgsDev::Assert;
// under CGS_ASSERT the failure path forwards the plain condition string (file/line dropped per policy).

namespace CgsGui
{
    namespace
    {
        // DecFIGS CgsGuiEventTypes.h: GuiEventStateChange derives GuiEvent<1> and
        // carries the pending state's fixed 16-byte event name. ARTIST PostUpdate
        // builds its header as {16, 1, 12} and queues the 28-byte record on channel 40.
        struct GuiEventStateChange : public GuiEvent<1>
        {
            char macStateChangeEvent[16];

            GuiEventStateChange() : GuiEvent<1>(16, 12)
            {
                macStateChangeEvent[0] = 0;
            }
        };

        static_assert(sizeof(GuiEventStateChange) == 28,
                      "GuiEventStateChange must match the ARTIST 28-byte wire record");
    }

    State::State()
        : mpInGuiEventQueue(0)
        , mpStateInterface(0)
        , mbStateChangePending(false)
        , mbIsSaveLoadState(false)
        , mbIsVideoState(false)
    {
        macEvent[0] = 0;
    }

    void State::Construct(CgsID liId, CgsFsm::ScriptedFsm* lpFsm)
    {
        CgsFsm::ScriptedState::Construct(liId, lpFsm);   // ARTIST 0x82848508: bl CgsFsm::ScriptedState::Construct (sets mId/mpFsm)
        mpInGuiEventQueue = 0;       // ARTIST 0x82848508: stw 0,0x18
        mpStateInterface = 0;        // stw 0,0x1C
        mbIsSaveLoadState = false;   // stb 0,0x31  (FLAG: was missing -- ARTIST zeroes both bools here)
        mbIsVideoState = false;      // stb 0,0x32
        mbStateChangePending = false;// stb 0,0x20
    }

    void State::PreWorldUpdate() {}

    // X360 0x828486A0. Assert the pending-change flag was cleared by the last PostUpdate,
    // then unconditionally clear it (stb 0, 0x20(r31) runs regardless of the branch taken).
    void State::PreUpdate()
    {
        CGS_ASSERT(!mbStateChangePending, "mbStateChangePending == false");
        mbStateChangePending = false;
    }

    // ARTIST 0x8285BA00. A pending state event is published to the GUI output
    // channel, delivered to the owning scripted FSM, then cleared. PreUpdate's
    // assertion is the next-frame tripwire that this hand-off happened.
    void State::PostUpdate()
    {
        if (mbStateChangePending)
        {
            CGS_ASSERT(strlen(macEvent) < sizeof(macEvent),
                       "Event too long for message. Increase buffer");

            GuiEventStateChange lStateChangeEvent;
            CgsCore::SPrintf(lStateChangeEvent.macStateChangeEvent,
                             sizeof(lStateChangeEvent.macStateChangeEvent), macEvent);
            lStateChangeEvent.macStateChangeEvent[
                sizeof(lStateChangeEvent.macStateChangeEvent) - 1] = 0;
            mpStateInterface->GetOutputEventQueue()->AddEvent(
                &lStateChangeEvent, 40, static_cast<s32>(sizeof(lStateChangeEvent)));

            CgsFsm::Event lEvent;
            lEvent.Construct(CgsIDCompress(macEvent));
            mpFsm->SendEvent(&lEvent);
            mbStateChangePending = false;
        }
    }

    void State::GetResourcesToLoad(const sResourceTuple** lppResourceTuples, u32* lpuNumberOfResources) const
    {
        *lppResourceTuples = 0;
        *lpuNumberOfResources = 0;
    }

    // X360 0x82846838. Validate the interface pointer, then store it (this+0x1C).
    void State::SetStateInterface(StateInterface* lpStateInterface)
    {
        CGS_ASSERT(lpStateInterface != 0,
                   "Invalid state interface sent to State::SetStateInterface");
        mpStateInterface = lpStateInterface;
    }

    void State::SetInEventQueue(InputBuffer::GuiEventQueue* lpInGuiEventQueue)
    {
        mpInGuiEventQueue = lpInGuiEventQueue;
    }

    // X360 0x82848550. Assert the event string is non-null; only when the owning ScriptedFsm's
    // Lua resource is valid does it copy the event name into macEvent (via SPrintf, asserting if
    // the source string is too long) and raise mbStateChangePending -- a null/rejected event never
    // sets the pending flag.
    void State::SendStateEvent(const char* lpacEvent)
    {
        CGS_ASSERT(lpacEvent != 0, "Invalid event sent to State::SendStateEvent");

        if (mpFsm->IsLuaResourceValid())
        {
            CGS_ASSERT(strlen(lpacEvent) < sizeof(macEvent),
                       "Event too long for message. Increase buffer");

            CgsCore::SPrintf(macEvent, sizeof(macEvent), lpacEvent);
            macEvent[sizeof(macEvent) - 1] = 0;
            mbStateChangePending = true;
        }
    }
}
