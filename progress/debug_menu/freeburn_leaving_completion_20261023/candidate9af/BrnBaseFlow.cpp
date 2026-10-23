#include "GameSource/Gui/Flow/BrnBaseFlow.h"

#include "GameShared/GameClasses/Core/CgsAssert.h"                       // CGS_ASSERT
#include "GameShared/GameClasses/Gui/Model/State/CgsGuiState.h"         // CgsGui::State (PreWorldUpdate)
#include "GameSource/Gui/BrnGuiCache.h"                                 // GuiCache (UpdateStreaming's unload/ensure pair)
#include "GameShared/GameClasses/Fsm/Resources/CgsLuaCodeResource.h"    // CgsResource::LuaCodeResource (PrepareLua)
#include "GameShared/GameClasses/Memory/CgsHeapMalloc.h"               // CgsMemory::HeapMalloc (PrepareLua)
#include "GameShared/GameClasses/Development/Log/CgsLog.h"             // gpDebugPrint / gxMessageFilterFlags (PrintSingleSize)

// BrnGui::BrnBaseFlow::SetInEventQueue, reconstructed from BURNOUT_X360_ARTIST.XEX
// @ 0x827E28A8 (semantic parity, not byte match).
//
// X360 body:
//   cmplwi lpInEventQueue, 0 / bne ...          ; assert lpInEventQueue != NULL (BrnBaseFlow.h:162)
//   addis  r3, this, 1 ; addi r3, r3, 0x20      ; r3 = &mStateMachine (this + 0x10020)
//   bl     CgsGui::StateMachine::SetInEventQueue ; forward (this->mStateMachine, lpInEventQueue)
// A thin forwarder: validate the incoming GUI input-event queue (non-gating assert tripwire),
// then hand it to the flow's owned state machine. Under CGS_ASSERT the original's d:\p4-baked
// file/line is dropped per policy; the plain condition string ("lpInEventQueue") is forwarded.
//
// The +0x10020 reach is the EventObserver base size; member-by-name access (mStateMachine) through
// the real base reproduces it. Caller's StateMachine::SetInEventQueue is the GameShared out-of-line
// member already declared in CgsGuiStateMachine.h.

namespace BrnGui
{
    // BrnBaseFlow.h -- accumulate the size first (whatever the filter), then print the line.
    void BrnBaseFlow::PrintSingleSize(const char* lpcName, s32 liSize, s32* lpiTotal)
    {
        *lpiTotal += liSize;
        if (CgsDev::Message::gxMessageFilterFlags & 1)
        {
            *CgsDev::Log::gpDebugPrint << (lpcName ? lpcName : "<NULLSTRING>") << " : " << liSize
                                       << " : " << *lpiTotal << "\n";
        }
    }

    void BrnBaseFlow::SetInEventQueue(InputBuffer::GuiEventQueue* lpInEventQueue)
    {
        CGS_ASSERT(lpInEventQueue != 0, "lpInEventQueue");
        mStateMachine.SetInEventQueue(lpInEventQueue);
    }

    // @ 0x824F1BC0 -- bring the EventObserver base up, construct the embedded state machine, then
    // stash the GUI cache and reset the streaming/release bookkeeping.
    void BrnBaseFlow::Construct(GuiCache* lpGuiCache)
    {
        EventObserver::Construct();
        mStateMachine.Construct();      // ScriptedFsm::Construct: mpCurrentState=0, mLuaState.Construct(), seq=0
        // @0x824F1C04 -- the X360 seeds the state machine's sequence number to 1 here, so the
        // FIRST Update sees seq(1) != muFsmSequenceNumber(0) and kicks streaming once.
        // ScriptedFsm::Construct leaves it 0; restore the seed (boot audit F-P8b-10). Harmless
        // while the mode word is OFF -- UpdateStreaming returns immediately -- but it is the
        // console's initial condition and it matters the moment the SCREEN flow is armed.
        mStateMachine.SetSequenceNumber(1);
        mpGuiCache          = lpGuiCache;
        mReleaseStage       = E_RELEASESTAGE_DONE;
        muFsmSequenceNumber = 0;
        meStreamingMode     = E_STREAMING_OFF;
    }

    // @ 0x824F1C38 -- EventObserver::Prepare (stash access pointers + allocator into the
    // StateInterface) then point the owned state machine at that StateInterface.
    bool BrnBaseFlow::Prepare(CgsGui::GuiAccessPointers* lpAccessPointers,
                              rw::IResourceAllocator* lpAllocator)
    {
        EventObserver::Prepare(lpAccessPointers, lpAllocator);
        mStateMachine.SetStateInterface(&mStateInterface);
        return true;
    }

    // @ 0x824F1C78 -- compile + enter the FSM's Lua script. The two asserts are the X360's
    // (BrnBaseFlow.cpp:86/87); on a successful ScriptedFsm::Prepare the release stage is armed at
    // START so a later Release() walks the full teardown.
    bool BrnBaseFlow::PrepareLua(CgsResource::LuaCodeResource* lpLuaCodeResource,
                                 CgsMemory::HeapMalloc* lpHeapMalloc, CgsID lInitialStateId)
    {
        CGS_ASSERT(lpLuaCodeResource != 0, "Invalid lua code resource sent to BrnBaseFlow::Prepare");
        CGS_ASSERT(lpHeapMalloc != 0,      "Invalid Heap allocator sent to BrnBaseFlow::Prepare");

        if (mStateMachine.Prepare(lpLuaCodeResource, lpHeapMalloc, lInitialStateId))
        {
            mReleaseStage = E_RELEASESTAGE_START;
            return true;
        }
        return false;
    }

    // @ 0x824F1DC0 -- staged teardown. The X360 falls through START->LEAVESTATE->RELEASESTATEMACHINE
    // (releasing the FSM there), each step advancing mReleaseStage so a re-entered Release() resumes
    // where it left off; DONE just succeeds.
    bool BrnBaseFlow::Release()
    {
        switch (mReleaseStage)
        {
            case E_RELEASESTAGE_START:
                mReleaseStage = E_RELEASESTAGE_START;
                // fall through
            case E_RELEASESTAGE_LEAVESTATE:
                mReleaseStage = E_RELEASESTAGE_LEAVESTATE;
                // fall through
            case E_RELEASESTAGE_RELEASESTATEMACHINE:
                mReleaseStage = E_RELEASESTAGE_RELEASESTATEMACHINE;
                if (!mStateMachine.Release())
                    return false;
                // fall through
            case E_RELEASESTAGE_DONE:
                mReleaseStage = E_RELEASESTAGE_DONE;
                return true;
            default:
                return false;
        }
    }

    // @ 0x82507FD8 -- pump the FSM, and when the script's state sequence advances, refresh the
    // next-state resource streaming.
    void BrnBaseFlow::Update()
    {
        mStateMachine.CgsFsm::Fsm::Update();   // base FSM tick: current state PreUpdate/Update/PostUpdate
        if (mStateMachine.IsLuaResourceValid())
        {
            const u32 luSequence = mStateMachine.GetSequenceNumber();
            if (luSequence != muFsmSequenceNumber)
            {
                muFsmSequenceNumber = luSequence;
                UpdateStreaming(mStateMachine.GetCurrentStateIndex(), meStreamingMode);
            }
        }
    }

    // @ 0x82514DB8 -- forward PreWorldUpdate to the current state.
    void BrnBaseFlow::PreWorldUpdate()
    {
        CgsGui::State* lpCurrentState = mStateMachine.GetCurrentState();
        if (lpCurrentState != 0)
        {
            lpCurrentState->PreWorldUpdate();
            // FLAG: the X360 then raises GUI notification events 66 (save-load state) / 69 (video
            // state) onto the EventObserver's output queue when the current state's
            // mbIsSaveLoadState / mbIsVideoState flags are set. That output-queue plumbing
            // (CgsModule::VariableEventQueue::AddEvent) is not reconstructed yet, so the raise is
            // deferred. The boot video states drive PlayVideo directly through the StateInterface,
            // so this does not gate the boot path. Restore once the output-queue API lands:
            //   if (lpCurrentState->IsSaveLoadState()) <raise event 66>;
            //   if (lpCurrentState->IsVideoState())    <raise event 69>;
        }
    }

    // @ 0x824FFD48 -- next-state resource streaming.
    // @ 0x824FFD48 -- the per-state APT streaming pass, store-for-store.
    //
    // ⭐ RECONSTRUCTED 2026-08-16 (boot audit F-P8b-9); was a `(void)` no-op.
    //
    // A NOTE ON WHEN THIS RUNS, because it is easy to get wrong: the mode word is
    // E_STREAMING_OFF for the HUD flow on the console too -- BrnBaseFlow::Construct is its
    // only writer there -- so every boot state's resources are loaded by DIRECT
    // GuiCache::EnsureResources calls inside the states' own Updates, NOT through here.
    // The SCREEN flow is the one that arms it: GuiModule::Prepare's stage 4 stores 1 into
    // ScreenFlow's mode word and GuiModule::Update refreshes it per frame, which is what
    // makes each screen transition unload the previous screen's type-4 APTs and ensure the
    // new one's. That arming is a separate finding (F-P8b-17) and is NOT invented here --
    // this function stays dormant until its writer lands, exactly as on the console.
    void BrnBaseFlow::UpdateStreaming(s32 liStateIndex, EStreamingMode meStreamingMode)
    {
        // 1. @0x824FFD60 -- mode 0 returns before ANY work.
        if (meStreamingMode == E_STREAMING_OFF)
            return;
        if (mpGuiCache == 0)
            return;

        // 2. @0x824FFD78 -- drop every per-state APT (type 4) the previous state held.
        mpGuiCache->UnloadAllResources(CgsGui::E_GUI_RESOURCETYPE_APT);

        // 3. @0x824FFD98 -- the indexed state must BE the current state.
        const CgsGui::State* lpState = mStateMachine.GetStateByIndex(liStateIndex);
        CGS_ASSERT(lpState == mStateMachine.GetCurrentState(),
                   "GetStateMachine().GetCurrentState()==lpState");   // BrnBaseFlow.cpp:334
        if (lpState == 0)
            return;

        // 4. @0x824FFDF8 -- vtable+0x20 GetResourcesToLoad, then ensure that set.
        const CgsGui::sResourceTuple* lpResources = 0;
        u32 luCount = 0;
        const_cast<CgsGui::State*>(lpState)->GetResourcesToLoad(&lpResources, &luCount);
        mpGuiCache->EnsureResourcesAreLoaded(lpResources, luCount);

        // 5. @0x824FFE14 -- E_STREAMING_PRELOAD additionally prefetches each next state.
        if (meStreamingMode == E_STREAMING_PRELOAD)
        {
            s32 laiNextStateIndices[280]; // X360 stack buffer: 0x460 bytes (1120).
            s32 liNextStateCount = 0;
            mStateMachine.GetNextStates(liStateIndex, laiNextStateIndices, &liNextStateCount);

            for (s32 liNextState = 0; liNextState < liNextStateCount; ++liNextState)
            {
                const s32 liNextStateIndex = laiNextStateIndices[liNextState];
                const CgsGui::State* lpNextState = mStateMachine.GetStateByIndex(liNextStateIndex);
                if (lpNextState != 0)
                {
                    const CgsGui::sResourceTuple* lpNextResources = 0;
                    u32 luNextResourceCount = 0;
                    lpNextState->GetResourcesToLoad(&lpNextResources, &luNextResourceCount);
                    mpGuiCache->EnsureResourcesAreLoaded(lpNextResources, luNextResourceCount);
                }
                else if ((CgsDev::Message::gxMessageFilterFlags & 1) != 0)
                {
                    *CgsDev::Log::gpDebugPrint
                        << "        (Warning: next state index=" << liNextStateIndex
                        << " is present in FSM but state object does not exist)\n";
                }
            }
        }
    }
}
