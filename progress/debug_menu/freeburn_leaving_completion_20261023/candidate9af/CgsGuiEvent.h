#pragma once

#include "types.hpp"
#include "GameShared/GameClasses/Module/CgsVariableEventQueue.h"

// GUI event vocabulary recovered from the DecFIGS DWARF (CgsGuiEvent.h):
//   - GuiEvent<N>          : the base of every concrete GUI event; N is the
//                            compile-time event-type id.
//   - GuiEventQueueBase<N,A>: a VariableEventQueue specialised for GUI events.
//   - GuiStackEventQueue    : owns one large GUI queue (the StateInterface output).
namespace CgsGui
{
    // Queue capacities (bytes) and the record alignment, from the X360 build.
    const s32 KI_INPUT_QUEUE_SIZE_KB  = 32768;
    const s32 KI_LARGE_QUEUE_SIZE_KB  = 65536;
    const s32 KI_MEDIUM_QUEUE_SIZE_KB = 16384;
    const s32 KI_SMALL_QUEUE_SIZE_KB  = 4096;
    const s32 KI_TINY_QUEUE_SIZE_KB   = 256;
    const s32 KI_QUEUE_ALIGNMENT      = 16;

    // Observer-fanout caps (DecFIGS CgsGuiEvent.h:41-42). The GUI event router holds at
    // most KI_MAX_OBSERVERS observer slots and queues at most KI_MAX_EVENTS_PER_OBSERVER
    // events per observer per frame. Declared additively alongside the queue-size set.
    const s32 KI_MAX_OBSERVERS           = 4;
    const s32 KI_MAX_EVENTS_PER_OBSERVER = 600; // ARTIST8284EA60/EAC8, not DecFIGS576

    // Base of every GUI event. The X360 emitters fill a small fixed header before
    // pushing the record onto a queue: muHeader0 / muHeader2 are queue bookkeeping
    // words (their precise meaning is not recovered from the leak), and muEventType
    // carries the GuiEvent<N> template id. EventTypeId is the compile-time id.
    template <s32 EventTypeId>
    struct GuiEvent : public CgsModule::Event
    {
        u32 muHeader0;
        u32 muEventType;
        u32 muHeader2;

        explicit GuiEvent(u32 luHeader0 = 0, u32 luHeader2 = 0)
            : muHeader0(luHeader0)
            , muEventType(static_cast<u32>(EventTypeId))
            , muHeader2(luHeader2)
        {
        }

        s32 GetEventType() const { return EventTypeId; }
    };

    // ARTIST AddGuiEvent<GuiEvent<91>> posts one unwritten byte (0x823D2660: AddEvent id 91,
    // size 1), so this tag is the empty event representation rather than the generic 12-byte
    // header above. The local object remains uninitialized, matching the original payload.
    template <>
    struct GuiEvent<91> : public CgsModule::Event
    {
        s32 GetEventType() const { return 91; }
    };
    static_assert(sizeof(GuiEvent<91>) == 1, "ARTIST GUI tag 91 is one byte");

    // ARTIST's Payback bridge uses these one-byte tag instantiations, not the generic
    // 12-byte header record: AddGuiEvent helpers 0x823D7570/0x823D7628/0x823D2FB8 pin
    // ids 178/180/183 at size 1. Keep their empty byte representation unwritten.
    template <>
    struct GuiEvent<178> : public CgsModule::Event
    {
        s32 GetEventType() const { return 178; }
    };
    template <>
    struct GuiEvent<180> : public CgsModule::Event
    {
        s32 GetEventType() const { return 180; }
    };
    template <>
    struct GuiEvent<183> : public CgsModule::Event
    {
        s32 GetEventType() const { return 183; }
    };
    static_assert(sizeof(GuiEvent<178>) == 1 && sizeof(GuiEvent<180>) == 1 &&
                  sizeof(GuiEvent<183>) == 1, "ARTIST Payback tag records are one byte");

    // ARTIST823D8540 posts tag523 with size1 (823D85DC/E0). Action293
    // stores no payload byte; retain the original empty event representation.
    template <>
    struct GuiEvent<523> : public CgsModule::Event
    {
        s32 GetEventType() const { return 523; }
    };
    static_assert(sizeof(GuiEvent<523>) == 1, "ARTIST GUI tag523 is one byte");

    // Original PFX tags carry one unwritten byte: ARTIST8250D828/2C
    // posts497, and823CEFA4/A8 posts500. The queue owns their type/size.
    template <>
    struct GuiEvent<497> : public CgsModule::Event
    {
        s32 GetEventType() const { return 497; }
    };
    template <>
    struct GuiEvent<500> : public CgsModule::Event
    {
        s32 GetEventType() const { return 500; }
    };
    static_assert(sizeof(GuiEvent<497>) == 1 && sizeof(GuiEvent<500>) == 1,
                  "PFX tags497 and500 are one-byte empty events");

    // ARTIST GuiDebug callbacks post these original tags as one unwritten byte.
    // Their record type/size belongs to the queue; no generic event prefix is stored.
    template <>
    struct GuiEvent<226> : public CgsModule::Event
    {
        s32 GetEventType() const { return 226; }
    };
    static_assert(sizeof(GuiEvent<226>) == 1, "ARTIST GuiDebug tag226 is one byte");
    template <>
    struct GuiEvent<227> : public CgsModule::Event
    {
        s32 GetEventType() const { return 227; }
    };
    static_assert(sizeof(GuiEvent<227>) == 1, "ARTIST GuiDebug tag227 is one byte");
    template <>
    struct GuiEvent<228> : public CgsModule::Event
    {
        s32 GetEventType() const { return 228; }
    };
    static_assert(sizeof(GuiEvent<228>) == 1, "ARTIST GuiDebug tag228 is one byte");
    template <>
    struct GuiEvent<229> : public CgsModule::Event
    {
        s32 GetEventType() const { return 229; }
    };
    static_assert(sizeof(GuiEvent<229>) == 1, "ARTIST GuiDebug tag229 is one byte");
    template <>
    struct GuiEvent<230> : public CgsModule::Event
    {
        s32 GetEventType() const { return 230; }
    };
    static_assert(sizeof(GuiEvent<230>) == 1, "ARTIST GuiDebug tag230 is one byte");
    template <>
    struct GuiEvent<288> : public CgsModule::Event
    {
        s32 GetEventType() const { return 288; }
    };
    static_assert(sizeof(GuiEvent<288>) == 1, "ARTIST GuiDebug tag288 is one byte");
    template <>
    struct GuiEvent<511> : public CgsModule::Event
    {
        s32 GetEventType() const { return 511; }
    };
    static_assert(sizeof(GuiEvent<511>) == 1, "ARTIST GuiDebug tag511 is one byte");

    // GuiEventWrapper<T, leEventType> (DecFIGS CgsGuiEvent.h:77). The stack record the GUI
    // output path (CgsGui::StateInterface::OutputGuiEvent<T> and its sibling OutputViewState /
    // OutputInternalState channels) builds and hands to VariableEventQueue::AddEvent. It boxes an
    // arbitrary payload T, recording the payload's byte size (miOutEventSize), its own
    // GetEventType() (miOutEventType) and where it sits relative to the record (miOutEventOffset).
    //
    // LAYOUT -- from the X360 ARTIST asm (rung 1, authoritative). Every OutputGuiEvent<T> body
    // (e.g. @0x824367D8 OutputGuiEvent<GuiAudioEvent>) stack-builds
    //     +0x00  miOutEventSize   (s32) = sizeof(T)
    //     +0x04  miOutEventType   (s32) = T::GetEventType()
    //     +0x08  miOutEventOffset (s32) = offsetof(this, mOutEvent)
    //     +0x0C  T  mOutEvent            (aligned to alignof(T): +0x0C for align<=4, +0x10 for align 8)
    // then calls AddEvent(&record, /*channel*/ leEventType, /*size*/ sizeof(record)). There is NO
    // GuiEvent<leEventType> base in front of miOutEventSize: the asm's offset word is 12 for an
    // align<=4 payload and 16 for an align-8 payload (GuiAudioEvent @0x824367D8), which is exactly
    // offsetof(mOutEvent) for this 3-word header -- a GuiEvent<N> base (12 bytes) would force
    // offset 24. AddEvent writes its own CBufferEntry{id,size} queue header from the channel arg;
    // it does not prepend a GuiEvent header. The leEventType template arg is the AddEvent channel
    // (40 = OutputGuiEvent, 41 = OutputViewState, 42 = OutputInternalState) and names the record
    // type; it is not a stored field. Wrapper instances seen in the DWARF include
    // GuiEventWrapper<CgsGui::GuiEventPlayAptMovie,41>, GuiEventWrapper<BrnGui::GuiChallengeSelectedEvent,40>,
    // GuiEventWrapper<BrnGui::GuiAudioEvent,40>, GuiEventWrapper<CgsGui::GuiEvent<155>,40>, etc.
    template <class T, s32 leEventType>
    class GuiEventWrapper
    {
    public:
        s32 miOutEventSize;    // +0x00  sizeof(T)
        s32 miOutEventType;    // +0x04  T::GetEventType()
        s32 miOutEventOffset;  // +0x08  offsetof(mOutEvent)
        T   mOutEvent;         // +0x0C  payload (aligned to alignof(T))

        // Box the payload: copy it in and capture its size / type / record-relative offset. The
        // X360 body copies the event bytes into the record then writes the three header words; this
        // copy-constructs mOutEvent (so payloads without a default constructor still work -- the asm
        // never default-constructs the payload) and fills the header. miOutEventOffset is the
        // "offsetof via a 1-based dummy" idiom the X360 build emits for the offset word.
        explicit GuiEventWrapper(T& lrEvent)
            : miOutEventSize(static_cast<s32>(sizeof(T)))
            , miOutEventType(lrEvent.GetEventType())
            , miOutEventOffset(static_cast<s32>(reinterpret_cast<size_t>(
                  reinterpret_cast<char*>(&(reinterpret_cast<GuiEventWrapper*>(1)->mOutEvent)) - 1)))
            , mOutEvent(lrEvent)
        {
        }

        // The AddEvent channel this record is queued under (leEventType); names the record type.
        s32 GetChannel() const { return leEventType; }

        // The boxed payload lives miOutEventOffset bytes past the record's own address.
        const CgsModule::Event* GetRawEvent() const
        {
            return reinterpret_cast<const CgsModule::Event*>(
                reinterpret_cast<const unsigned char*>(this) + miOutEventOffset);
        }
    };

    template <s32 BUFSIZE, s32 ALIGN>
    class GuiEventQueueBase : public CgsModule::VariableEventQueue<BUFSIZE, ALIGN>
    {
    public:
        void Construct();
        bool Prepare();
        bool Release();
        void Destruct();
        void Clear();
        s32  GetLength() const;
        void AddGuiEvent(const CgsModule::Event* lpEvent, s32 liType, s32 liSize);
        s32  GetFirstEvent(const CgsModule::Event** lppEvent, s32* lpiSize) const;
        s32  GetNextEvent(const CgsModule::Event* lpEvent, const CgsModule::Event** lppNextEvent, s32* lpiSize) const;
    };

    // Named GUI event-queue sizes (bytes), from the X360 queue-size constants.
    typedef GuiEventQueueBase<65536, 16> GuiEventQueueLarge;
    typedef GuiEventQueueBase<16384, 16> GuiEventQueueMedium;
    typedef GuiEventQueueBase<4096, 16>  GuiEventQueueSmall;
    typedef GuiEventQueueBase<256, 16>   GuiEventQueueTiny;

    // DecFIGS CgsGuiEvent.h:189 -- the unqualified "GuiEventQueue" name aliases the medium
    // (16384) queue (matching the GuiEventQueueLarge/Small naming, this is the default).
    typedef GuiEventQueueBase<16384, 16> GuiEventQueue;

    // The original GuiStackEventQueue derives from CgsModule::IOBuffer; the in-scope
    // GUI-state code only uses the nested GuiEventQueueLarge typedef, so the IOBuffer
    // base is intentionally omitted here to avoid a transitive module-IO cascade.
    struct GuiStackEventQueue
    {
        typedef CgsGui::GuiEventQueueLarge GuiEventQueueLarge;

        GuiEventQueueLarge mGuiEventQueue;
    };
}

// Complete the existing GUI-state queue spelling. The Interpreter owns these
// actual queue objects, and EventObserver/BrnBaseFlow pass them by this type.
// ARTIST uses the18432-byte specialization; this wrapper adds no fields.
namespace InputBuffer
{
    class GuiEventQueue : public CgsModule::VariableEventQueue<18432, 16> {};
}
