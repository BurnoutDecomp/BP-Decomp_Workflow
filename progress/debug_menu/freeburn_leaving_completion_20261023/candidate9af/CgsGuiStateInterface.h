#pragma once

#include "types.hpp"
#include <cstddef>
#include "GameShared/GameClasses/Gui/CgsGuiEvent.h"
#include "GameShared/GameClasses/Gui/CgsGuiShared.h"
#include "GameShared/GameClasses/Gui/Model/Resources/CgsGuiResourceModuleIO.h"

namespace rw { struct IResourceAllocator; }
namespace CgsLanguage { class LanguageManager; }

// CgsGui::StateInterface - the channel a GUI state uses to reach the rest of the
// game: it owns the large output event queue the state writes to, plus the access
// pointers / allocator the state needs. Recovered from the X360 spine; layout,
// method set and the emitted event records are from the DecFIGS DWARF
// (CgsGuiStateInterface.h).
namespace CgsGui
{
    class EventObserver;

    // Events the interface emits onto its output queue. The numeric template id is
    // the GuiEvent<N> type; the queue "channel" id (passed to AddEvent) selects the
    // output wrapper: 40 = GuiEventOut, 41 = GuiOutViewState, 42 = internal,
    // 39 = resource request.
    struct GuiEventPlayAptMovie : public GuiEvent<18>
    {
        const char* mpacMovieName;
        s32         miLevelNum;
        GuiEventPlayAptMovie() : GuiEvent<18>(8, 12) {}
    };

    // Empty payload tags boxed by GuiEventWrapper<...,40>.  On X360 sizeof(T)
    // is 1, producing the exact 16-byte {1,type,12,payload/pad} wire record in
    // PlayLoadingScreen / StopLoadingScreen.
    struct GuiEventPlayAptLoadingMovie : public CgsModule::Event
    {
        s32 GetEventType() const { return 19; }
    };

    struct GuiEventStopAptLoadingMovie : public CgsModule::Event
    {
        s32 GetEventType() const { return 20; }
    };

    // The view's clear-screen (black backdrop) control record (DecFIGS
    // CgsGuiEventTypeDefs.h:130; X360-attested by the ViewModule case-25 consumer
    // @0x8285FCE8 and the boot states' posts: BootLegal::OnEnter ACTIVE alpha 1.0,
    // BootLegal::OnLeave / BootProfile::OnEnter INACTIVE -- the prompt renders over
    // the save/load loading-screen background, not over black).
    struct GuiEventClearScreenSet : public GuiEvent<25>
    {
        enum EClearScreen
        {
            E_CLEAR_SCREEN_ACTIVE   = 0,
            E_CLEAR_SCREEN_INACTIVE = 1,
            E_CLEAR_SCREEN_MAX      = 2,
        };

        EClearScreen meClearScreen;
        f32          mfAlpha;

        GuiEventClearScreenSet() : GuiEvent<25>(8, 12) {}
    };

    struct GuiEventRequestResource : public CgsModule::Event
    {
        ResourceRequestTypes      meType;
        ResourceRequestLoadUnload meLoadUnload;
        const char*               mpacFileName;
        s32                       miUserData;
    };

    // The "play a music stream on the menu" GUI event. X360-attested by the
    // OutputGuiEvent<GuiEventPlayMusicOnMenuStream> instantiation @0x82476C00: record
    // { muHeader0 = 8, muEventType = 23, muHeader2 = 12 } + { the sound-name hash,
    // two flag bytes }, channel 40, 20 bytes. (BrnGui::Credits posts it with
    // CgsSound::Playback::Name::MakeHash("Credits") and both flags clear.)
    struct GuiEventPlayMusicOnMenuStream : public GuiEvent<23>
    {
        u32  muStreamNameHash;   // +0x0C  (CgsSound::Playback::Name::MakeHash result)
        bool mbFlagA;            // +0x10  (roles not recovered; Credits passes false/false)
        bool mbFlagB;            // +0x11

        explicit GuiEventPlayMusicOnMenuStream(u32 luStreamNameHash,
                                               bool lbFlagA = false, bool lbFlagB = false)
            : GuiEvent<23>(8, 12)
            , muStreamNameHash(luStreamNameHash), mbFlagA(lbFlagA), mbFlagB(lbFlagB) {}
    };

    // The "suspend / resume network processing" GUI event. X360-attested by the
    // OutputGuiEvent<CgsGui::GuiEventNetworkSuspension> instantiation @0x82493A88: the
    // queued record is { muHeader0 = 4 (payload bytes), muEventType = 45, muHeader2 = 12
    // (payload offset) } + one payload word, channel 40, 16 bytes.
    // The payload word is the suspension type: the network state manager suspends on 0 and
    // calls SuspensionManager::Resume on 1, so a true constructor argument means RESUME.
    // (BrnGui::PauseScreen posts 0 when leaving the pause menu.)
    struct GuiEventNetworkSuspension : public GuiEvent<45>
    {
        enum ESuspensionType
        {
            E_SUSPENSION_TYPE_SUSPEND = 0,
            E_SUSPENSION_TYPE_RESUME  = 1,
            E_SUSPENSION_TYPE_COUNT   = 2,
        };

        ESuspensionType meSuspensionType;   // +0x0C payload word

        explicit GuiEventNetworkSuspension(bool lbResume)
            : GuiEvent<45>(4, 12),
              meSuspensionType(lbResume ? E_SUSPENSION_TYPE_RESUME : E_SUSPENSION_TYPE_SUSPEND) {}
    };

    // ARTIST8285B8A0/B900/B960/B9C0 and ProcessOutEvents8285E1D0.
    // These are flat queue payloads; GuiEvent<N>'s host wrapper is not copied.
    struct GuiEventRegisterForEvents : public CgsModule::Event
    {
        s32 miEventType;
        EventObserver* lpEventObserver;
    };
    struct GuiEventUnRegisterForEvents : public GuiEventRegisterForEvents {};
    struct GuiEventPriorityRegisterForEvents : public CgsModule::Event
    {
        s32 miEventType;
        s32 miEventTypeOverridden[KI_MAX_EVENTS_PER_OBSERVER];
        u32 muOverrideCount;
        EventObserver* lpEventObserver;
    };
    struct GuiEventPriorityUnRegisterForEvents : public GuiEventRegisterForEvents {};
    struct GuiEventPriorityStopBlocking : public CgsModule::Event
    {
        EventObserver* lpEventObserver;
    };

    static_assert(offsetof(GuiEventRegisterForEvents, lpEventObserver) ==
        (sizeof(void*) == 8 ? 8 : 4), "Registration retains the complete observer pointer");
    static_assert(offsetof(GuiEventPriorityRegisterForEvents, muOverrideCount) == 0x964,
        "ARTIST600-element priority list followed by count");
    static_assert(offsetof(GuiEventPriorityRegisterForEvents, lpEventObserver) == 0x968,
        "Priority observer follows the count");
    static_assert(sizeof(GuiEventPriorityRegisterForEvents) ==
        (sizeof(void*) == 8 ? 2416 : 2412), "Priority registration widens the observer pointer");

    struct StateInterface
    {
        CgsGui::EventObserver* mpObserver;

    private:
        GuiAccessPointers*               mpAccessPointers;
        rw::IResourceAllocator*          mpAllocator;
        GuiStackEventQueue::GuiEventQueueLarge mOutEventQueue;

    public:
        void Construct();
        void Prepare(rw::IResourceAllocator* lpAllocator, GuiAccessPointers* lpAccessPointers);

        void RegisterForEvents(const s32* lpiEventIds, s32 liCount);
        void UnRegisterForEvents(const s32* lpiEventIds, s32 liCount);
        void PriorityRegisterForEvent(s32 liPriority, const s32* lpiEventIds, u32 luCount);
        void PriorityUnRegisterForEvent(s32 liPriority);
        void StopPriorityEventBlocking();

        void RequestResource(const char* lpacFileName, ResourceRequestTypes leType,
                             s32 liUserData, ResourceRequestLoadUnload leLoadUnload);
        void UnloadResource(const char* lpacFileName, ResourceRequestTypes leType, s32 liUserData);

        GuiStackEventQueue::GuiEventQueueLarge* GetOutputEventQueue();
        void SetEventObserver(CgsGui::EventObserver* lpObserver);

        // Push a GUI event onto the state's output queue, keyed by its GuiEvent<N> type id. The X360
        // boot states (e.g. BrnGui::BootVideos) emit BrnGui::GuiEventPlayVideo/StopVideo through this; the
        // template is generic so it can carry a higher-layer (GameSource) event type without this GameShared
        // header depending on it -- it is only instantiated where TEvent is complete. The queued event is
        // then routed to the registered observers (the MovieManager for the video events).
        //
        // FLAG known divergence -- DO NOT "harmonize" OutputViewState/OutputInternalState below
        // to match this body; harmonize this body to THEM when the payload types are re-shaped.
        // The X360 OutputGuiEvent<T> bodies also stack-build a GuiEventWrapper<T,40> and pass the
        // constant channel 40, exactly like the two templates below: @0x824367D8
        // (<GuiAudioEvent>) writes {24,456,16} + a 24-byte copy -> AddEvent(&rec, 40, 40), and
        // @0x82476C00 (<GuiEventPlayMusicOnMenuStream>) writes {8,23,12} + 8 -> AddEvent(&rec,
        // 40, 20). This body instead passes the event directly with lrEvent.GetEventType() as the
        // channel. It is kept as-is deliberately, because the payload-type population is SPLIT
        // between two encodings (BrnGuiDemangledEventTypes.h alone: 94 GuiEvent<N>-derived vs 152
        // raw). The GuiEvent<N>-derived ones -- this header's GuiEventPlayMusicOnMenuStream(8,12) /
        // GuiEventNetworkSuspension(4,12) / GuiEventPlayAptMovie(8,12) included -- set
        // muHeader0/muHeader2 to the wrapper's own size/offset words, i.e. they bake the wrapper
        // header INTO the type, so direct-pass reproduces the right record bytes for them and
        // switching to the wrapper would emit a DOUBLE header. The raw ones (`u8 maData[N]` +
        // GetEventType(), no GuiEvent base) need the wrapper and get no header at all here.
        // Resolving the split means re-shaping the payload types across several headers this TU
        // does not own, so the direct pass stays. Consumers that need the exact X360 wire record
        // build it themselves and post it through GetOutputEventQueue()->AddEvent() -- that is the
        // standing accommodation (BrnCarSelectMain_wG_02.cpp, BrnOnlineGameRoomPlayerInfo_wH_08/13/14.cpp).
        //
        // The reinterpret_cast is what lets the RAW half instantiate at all: AddEvent takes a
        // `const CgsModule::Event*`, and a raw payload type has no CgsModule::Event base, so plain
        // `&lrEvent` does not convert (C2664). It is the same cast the two sibling bodies below
        // already spell. For the 94 GuiEvent<N>-derived types it is a NO-OP: CgsModule::Event is an
        // empty, non-polymorphic base at offset 0, so the cast yields exactly the address the
        // implicit derived-to-base conversion would. No queued byte changes, and the FLAGged
        // divergence above is untouched.
        //
        // WHY THE CAST STAYS (conductor, measured): without it the COMMITTED, already-reviewed
        // BrnChallengeSelector.cpp does not compile at all -- its Hide() posts a raw payload type
        // and fails C2664 right here. That is a pre-existing break on dev, not something wave L
        // introduced. A wave-L review advised against landing the cast; that advice predates this
        // measurement and should not be acted on to revert it. The cast changes NO queued byte for
        // the 94 GuiEvent<N>-derived types (CgsModule::Event is an empty, non-polymorphic base at
        // offset 0), and it does NOT resolve the raw-vs-wrapped wire divergence FLAGged above --
        // that divergence is unchanged and still owned here.
        // GATE STATE (measured 2026-08-04 with the cast in place; the older note here claimed the
        // raw types still C2664 -- they no longer do). Raw-type consumers compile again:
        // BrnChallengeSelector.cpp and BrnChallengeSelector_wL_01.cpp (GuiChallengeSelectedEvent)
        // and BrnPaybackComponent.cpp (GuiEventPaybackBeginAward) all gate pass.
        // CgsGuiStateInterface_OutputGuiEvent_Inst.cpp still fails, but ONLY on C3190/C2945 from its
        // `template int` spelling; a copy of it with `template int` -> `template void` gates PASS on
        // all 66 instantiations. `void` is the correct spelling (the X360 mangled names are `QAAX`).
        template <typename TEvent>
        void OutputGuiEvent(TEvent& lrEvent)
        {
            mOutEventQueue.AddEvent(reinterpret_cast<const CgsModule::Event*>(&lrEvent),
                                    lrEvent.GetEventType(), static_cast<s32>(sizeof(TEvent)));
        }

        // The two sibling output channels of OutputGuiEvent: 41 == "view state", 42 ==
        // "internal state" (the channel legend is in CgsGuiEvent.h's GuiEventWrapper
        // comment). Both return **void**: the X360 mangled names are
        //   ??$OutputViewState@V<T>@BrnGui@@@StateInterface@CgsGui@@QAAXAAV<T>@BrnGui@@@Z
        // and the same with OutputInternalState -- `QAAX` == public / non-const / __cdecl /
        // **X = void return**. Checked on all 12 attested instantiations -- view state
        // 0x824C2FA0 / 0x82436CF0 / 0x824C2EE8 / 0x82493D98 / 0x82476B60 / 0x82476DD8 /
        // 0x82465E50, internal state 0x82436A30 / 0x82436A80 / 0x82493DE8 / 0x82493C98 /
        // 0x82476E38 -- every one of them spells `QAAX`. Hex-Rays renders them `int`
        // only because it propagates the tail-called AddEvent's bool return.
        //
        // BODY (X360 ARTIST, rung 1). These two stack-build a GuiEventWrapper<TEvent, channel>
        // and queue *that* -- which is what the X360 OutputGuiEvent bodies do as well; only the
        // in-tree OutputGuiEvent body above still direct-passes (see its FLAG). Measured on
        // OutputViewState<GuiEventShowHideSatNav> @0x82476DD8 -- the record written is
        //     +0 = 12 (sizeof(T))   +4 = 213 (GetEventType())   +8 = 12 (payload offset)
        //     +12..+23 = a 3-word copy of the caller's object, loaded from 0/4/8(r4)
        // then AddEvent(&record, /*channel*/41, /*size*/24). The payload words come from
        // offsets 0/4/8 of the passed event -- confirmed at the emitter, PreRaceFlyByState::
        // Update @0x824DC804..0x824DC820, which fills its local at +0/+4/+8 -- so the
        // wrapper's three header words are NOT part of TEvent. The channel is a compile-time
        // constant (`li r5,0x29` / `li r5,0x2A`), not the event's type id.
        // This shape reproduces every attested record exactly, including the align-8 cases:
        //   <GuiEventFilterEventIcons>     {4,557,12}  + 4  -> 16   @0x824C2FA0
        //   <GuiEventShowHideBoostBar>     {1,214,12}  + 1  -> 16   @0x82476B60
        //   <GuiEventShowHideHud>          {1,148,12}  + 1  -> 16   @0x82493C98
        //   <GuiEventShowHideSatNav>       {12,213,12} + 12 -> 24   @0x82476DD8 / 0x82476E38
        //   <GuiEventSetHoveredEventIcon>  {24,559,16} + 24 -> 40   @0x824C2EE8 (alignas(8))
        // Bodies live here (not in a .cpp) because the X360 emits one out-of-line copy per
        // T; the explicit instantiations are in the sibling CgsGuiStateInterface_Output*_Inst.cpp.
        template <typename TEvent>
        void OutputViewState(TEvent& lrEvent)
        {
            GuiEventWrapper<TEvent, 41> lWrapper(lrEvent);
            mOutEventQueue.AddEvent(reinterpret_cast<const CgsModule::Event*>(&lWrapper),
                                    41, static_cast<s32>(sizeof(lWrapper)));
        }

        template <typename TEvent>
        void OutputInternalState(TEvent& lrEvent)
        {
            GuiEventWrapper<TEvent, 42> lWrapper(lrEvent);
            mOutEventQueue.AddEvent(reinterpret_cast<const CgsModule::Event*>(&lWrapper),
                                    42, static_cast<s32>(sizeof(lWrapper)));
        }

        void PlayAptMovie(const char* lpacMovieName, s32 liLevelNum);
        void PlayVideo(const char* lpacVideoName);
        void PlayLoadingScreen();
        void StopLoadingScreen();
        void Clear();

        rw::IResourceAllocator*       GetAllocator();
        GuiAccessPointers*            GetAccessPointers();
        CgsLanguage::LanguageManager* GetLanguageManager();
        bool                          IsUsingMetricUnits();
    };

    // ARTIST OutputGuiEvent<GuiEventNetworkSuspension> 0x82493A88 sends
    // {4,45,12,type} on channel 40. This legacy event type already contains that
    // wrapper, so queue it once, on the wrapper channel. The GUI router then
    // delivers the single payload word to event-45 consumers.
    template <>
    inline void StateInterface::OutputGuiEvent<GuiEventNetworkSuspension>(GuiEventNetworkSuspension& lrEvent)
    {
        mOutEventQueue.AddEvent(&lrEvent, 40, static_cast<s32>(sizeof(lrEvent)));
    }
}
