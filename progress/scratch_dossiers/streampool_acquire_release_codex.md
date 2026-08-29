# StreamPool::AcquireStream / ReleaseStream — complete ARTIST decode

Date: 2026-08-29

Scope: exactly rw::audio::core::StreamPool::AcquireStream at 0x82B6BAB0 and
rw::audio::core::StreamPool::ReleaseStream at 0x82B6BC48. This report does not
re-decode GetInstance. Where the already-established GetInstance evidence is needed
to confirm mGuid or mListNode, only its proving instruction is cited.

Primary evidence:

- .ida-exports/BURNOUT_X360_ARTIST.XEX/0x82B6BAB0.json
- .ida-exports/BURNOUT_X360_ARTIST.XEX/0x82B6BC48.json
- The assembly fields are present, so no missing-dossier/raw-code fallback was needed.
- Raw ARTIST data bytes were checked for the two loaded constants:
  0x8214B270 = 7F EF FF FF FF FF FF FF = DBL_MAX, and
  0x8214AED0 = 42 C8 00 00 = 100.0f.

Naming/type corroboration:

- IDA Files/ProStreet08Milestone.pdb, an Oct-2007 X360 rwaudiocore PDB, gives the
  exact shared-vendor layouts and names quoted below.
- IDA Files/ProStreet08Milestone.map gives
  ?AcquireStream@StreamPool@core@audio@rw@@QAAPAXMP6AXPAX@Z0@Z and
  ?ReleaseStream@StreamPool@core@audio@rw@@QAAXPAX@Z.
- The Feb-2007 vendor header streampool.h independently gives the same public
  signatures, StreamDesc names/types, and the inlined AllocateStream helper.
- DecFIGS has the same two mangled functions at 0xE2E738 and 0xE2E234. It is used
  only as a declaration/name corroboration; ARTIST assembly below decides behavior.

## Result

The exact logical declarations are:

    using StreamHandle = void *;
    using StreamLostCallback = void (*)(void *pContext);

    StreamHandle AcquireStream(float priority,
                               StreamLostCallback pStreamLostCallback,
                               void *pStreamLostContext);
    void ReleaseStream(StreamHandle streamHandle);

AcquireStream performs three scans when necessary:

1. Reuse pass: find the first allocated entry whose stored context is non-null and
   equals pStreamLostContext; increment its refCount and return it
   (0x82B6BAE4–0x82B6BB00, 0x82B6BB74–0x82B6BB80).
2. Free pass: find the first entry with allocated == 0 and initialize it
   (0x82B6BB20–0x82B6BB3C, 0x82B6BB84–0x82B6BBB0).
3. Replacement pass: reached only after the free pass found no free entry. Select
   the entry with the lowest priority; break equal-priority ties by the lowest
   timeStamp (0x82B6BB40–0x82B6BBDC). Replacement is permitted only when that
   selected priority is ordered-less-than both the incoming priority and 100.0f
   (0x82B6BBDC–0x82B6BBF0). It calls the old entry's callback with its old context
   and then initializes the same entry for the new client
   (0x82B6BBF4–0x82B6BC34).

ReleaseStream decrements the handle's signed-short refCount. Exactly when the
post-decrement value is zero it calls pRwCoreStream->Kill() and clears allocated;
otherwise it does nothing further (0x82B6BC5C–0x82B6BC80). It does not read this.

## Exact ABI / register contract

### AcquireStream

Logical return type is void * / StreamHandle, not int. Successful paths leave the
StreamDesc address in r3 (for example the array pointer loaded at 0x82B6BAE0 and
returned through 0x82B6BB80, or the explicit mr r3,r31 at 0x82B6BC1C); failure puts
zero in r3 at 0x82B6BC38.

ARTIST X360 entry contract:

| Value | Register | Proof |
|---|---:|---|
| this | r3 | copied to r30 at 0x82B6BAC0 |
| float priority | f1 | copied to f31 at 0x82B6BAC4, later stored with stfs at 0x82B6BB8C / 0x82B6BC0C |
| callback pointer | r5 | copied to r28 at 0x82B6BAC8 |
| context pointer | r6 | copied to r29 at 0x82B6BACC |
| return StreamHandle | r3 | success/failure sites above |

The float consumes ABI argument slot 2 while travelling in f1, so r4 is not a
trailing integer parameter and is never read by this function. The callback and
context consequently arrive in r5 and r6. Hex-Rays' five-argument prototype and
double priority are false.

The first object access is the unguarded lbz from this+0x28 at 0x82B6BAD4. There is
no null-this guard.

### ReleaseStream

Logical return type is void, as fixed by the mangled symbol and vendor declaration.
The decompiler's int return is false. ARTIST receives this in r3 and streamHandle
in r4; 0x82B6BC58 copies r4 to r31, while no instruction reads the incoming r3.
If Kill is called, its incidental result remains in r3, but ReleaseStream has no
language-level return value (call at 0x82B6BC74, epilogue at 0x82B6BC80–0x82B6BC90).

The handle is dereferenced without a null or ownership check at 0x82B6BC5C.

## Corrected typed layout

The provisional Hungarian names in the input dossier are offsets-correct but are
not the real rwaudiocore vendor names. The X360 ProStreet PDB and Feb vendor header
agree on the following names.

### StreamPool (X360 console layout)

| Offset | Correct vendor member | Type | ARTIST attestation |
|---:|---|---|---|
| +0x00 | mpSystem | System * | read at 0x82B6BBA4 and 0x82B6BC28; its +0x08 double is copied into StreamDesc::timeStamp at 0x82B6BBA8–0x82B6BBAC and 0x82B6BC2C–0x82B6BC30 |
| +0x04 | mpStreamDesc | StreamDesc * | read at 0x82B6BAE0, 0x82B6BB20, and 0x82B6BB58 |
| +0x24 | mGuid | Guid / unsigned int | established GetInstance load at 0x82B6BA84 |
| +0x28 | mNumStreams | unsigned char | lbz at 0x82B6BAD4; the resulting count controls all scans at 0x82B6BADC, 0x82B6BB0C, 0x82B6BB18, 0x82B6BB38, 0x82B6BB4C, and 0x82B6BBD0 |
| +0x2C | mListNode | ListDNode | established GetInstance owner recovery subtracts 0x2C at 0x82B6BA78 |

Corrections to the provisional names are therefore:

- mpEntries -> mpStreamDesc
- muGuid -> mGuid
- mu8EntryCount -> mNumStreams
- mListLink -> mListNode

The requested bodies do not access the pool bytes from +0x08 through +0x23. The PDB
names vendor members there, but their behavior is unattested by these functions and
is not inferred here.

### StreamDesc (X360 console layout, sizeof 0x20)

| Offset | Correct vendor member | Type | ARTIST attestation |
|---:|---|---|---|
| +0x00 | timeStamp | double | read for victim selection at 0x82B6BB68 and 0x82B6BBBC; written from mpSystem's +0x08 double at 0x82B6BBAC and 0x82B6BC30 |
| +0x08 | priority | float | read at 0x82B6BB5C; written with stfs at 0x82B6BB8C and 0x82B6BC0C |
| +0x0C | pStreamLostCallback | void (*)(void *) | written at 0x82B6BB90 and 0x82B6BC14; loaded for indirect call at 0x82B6BBF8 |
| +0x10 | pStreamLostContext | void * | tested/matched at 0x82B6BAF0–0x82B6BB00; written at 0x82B6BB98 and 0x82B6BC18; loaded into callback argument r3 at 0x82B6BBF4 |
| +0x14 | pRwCoreStream | rw::core::filesys::Stream * | loaded as Kill's this at 0x82B6BC70; call at 0x82B6BC74 |
| +0x18 | refCount | signed short | lhz/add/sth increment sequences at 0x82B6BB74–0x82B6BB7C, 0x82B6BB84–0x82B6BBA0, and 0x82B6BC04–0x82B6BC24; ReleaseStream's extsh. at 0x82B6BC64 explicitly sign-extends the decremented 16-bit value before testing it |
| +0x1A | allocated | unsigned char | read at 0x82B6BAE4 and 0x82B6BB24; set to 1 at 0x82B6BB9C and 0x82B6BC20; cleared at 0x82B6BC7C |
| +0x1B | pad | char | vendor PDB/header name only; no requested ARTIST instruction accesses it |
| +0x1C..+0x1F | tail padding | — | implied by the next-record increments; no semantic access |

Corrections to the provisional entry names are:

- mfPriority -> priority
- mpfnStreamLost -> pStreamLostCallback
- mpStream -> pRwCoreStream
- miRefCount -> refCount
- mbAllocated -> allocated

The input's signed-short correction is confirmed. The two previously omitted
semantic fields are timeStamp at +0x00 and pStreamLostContext at +0x10.

## AcquireStream: complete instruction-level decode

### Prologue and argument capture

    0x82B6BAB0  mflr r12
        Save LR in r12 for the shared GPR-save helper.
    0x82B6BAB4  bl __savegprlr_28
        Save nonvolatile GPRs r28–r31 and LR.
    0x82B6BAB8  stfd f31,var_30(r1)
        Save nonvolatile f31.
    0x82B6BABC  stwu r1,back_chain(r1)
        Allocate the local frame.
    0x82B6BAC0  mr r30,r3
        r30 = this.
    0x82B6BAC4  fmr f31,f1
        f31 = incoming float priority. The later stfs proves float, not double.
    0x82B6BAC8  mr r28,r5
        r28 = incoming pStreamLostCallback.
    0x82B6BACC  mr r29,r6
        r29 = incoming pStreamLostContext.
    0x82B6BAD0  li r10,0
        First-pass index = 0.
    0x82B6BAD4  lbz r11,0x28(r30)
        r11 = this->mNumStreams. This is the first, unguarded this dereference.
    0x82B6BAD8  cmpwi r11,0
        Test whether the unsigned-byte count is zero.
    0x82B6BADC  ble 0x82B6BB14
        If count <= 0, skip the reuse pass. Because count came from lbz, this is
        effectively the zero-count case.

### Pass 1: reuse an allocated entry for the same non-null context

    0x82B6BAE0  lwz r3,4(r30)
        r3 = this->mpStreamDesc, the first entry and eventual handle return.
    0x82B6BAE4  lbz r9,0x1A(r3)
        Read entry->allocated.
    0x82B6BAE8  cmplwi r9,0
        Test allocated.
    0x82B6BAEC  beq 0x82B6BB04
        Unallocated entry cannot match; advance.
    0x82B6BAF0  lwz r9,0x10(r3)
        r9 = entry->pStreamLostContext.
    0x82B6BAF4  cmplwi r9,0
        Require the stored context itself to be non-null.
    0x82B6BAF8  beq 0x82B6BB04
        A null stored context never participates in reuse, even if the incoming
        context is also null.
    0x82B6BAFC  cmplw cr6,r9,r29
        Compare stored context with incoming pStreamLostContext.
    0x82B6BB00  beq cr6,0x82B6BB74
        On equality, branch to the refCount increment/return path.
    0x82B6BB04  addi r10,r10,1
        Increment first-pass index.
    0x82B6BB08  addi r3,r3,0x20
        Advance by the X360 StreamDesc size. Host C++ must use mpStreamDesc[index],
        never this literal.
    0x82B6BB0C  cmpw cr6,r10,r11
        Compare index against mNumStreams.
    0x82B6BB10  blt cr6,0x82B6BAE4
        Continue while index < count.

The match path is placed later in the instruction stream:

    0x82B6BB74  lhz r11,0x18(r3)
        Load the matching entry's 16-bit refCount bits.
    0x82B6BB78  addi r11,r11,1
        Increment.
    0x82B6BB7C  sth r11,0x18(r3)
        Store the low 16 bits back to refCount.
    0x82B6BB80  b 0x82B6BC3C
        Return the already-current r3 handle. No priority, callback, context,
        timestamp, stream pointer, or allocated field is changed.

### Pass 2: select the first unallocated entry

    0x82B6BB14  li r10,0
        Second-pass index = 0.
    0x82B6BB18  cmpwi cr6,r11,0
        Re-test mNumStreams.
    0x82B6BB1C  ble cr6,0x82B6BB40
        Zero count skips the free scan.
    0x82B6BB20  lwz r3,4(r30)
        Restart from this->mpStreamDesc[0].
    0x82B6BB24  lbz r9,0x1A(r3)
        Read entry->allocated.
    0x82B6BB28  cmplwi r9,0
        Test it.
    0x82B6BB2C  beq 0x82B6BB84
        The first allocated == 0 entry is selected for initialization.
    0x82B6BB30  addi r10,r10,1
        Increment second-pass index.
    0x82B6BB34  addi r3,r3,0x20
        Advance by the X360 StreamDesc size. This is the second raw-stride site.
    0x82B6BB38  cmpw cr6,r10,r11
        Compare index with count.
    0x82B6BB3C  blt cr6,0x82B6BB24
        Continue while index < count.

The free-entry initialization path is:

    0x82B6BB84  lhz r11,0x18(r3)
        Load selected entry->refCount. It is incremented, not assigned 1.
    0x82B6BB88  li r10,1
        Value for allocated = true.
    0x82B6BB8C  stfs f31,8(r3)
        entry->priority = incoming priority.
    0x82B6BB90  stw r28,0xC(r3)
        entry->pStreamLostCallback = incoming callback.
    0x82B6BB94  addi r11,r11,1
        Compute refCount + 1.
    0x82B6BB98  stw r29,0x10(r3)
        entry->pStreamLostContext = incoming context.
    0x82B6BB9C  stb r10,0x1A(r3)
        entry->allocated = true.
    0x82B6BBA0  sth r11,0x18(r3)
        Store incremented refCount.
    0x82B6BBA4  lwz r11,0(r30)
        r11 = this->mpSystem.
    0x82B6BBA8  lfd f0,8(r11)
        Load mpSystem's current-time double; the vendor inline helper names this
        expression mpSystem->GetTime().
    0x82B6BBAC  stfd f0,0(r3)
        entry->timeStamp = current time.
    0x82B6BBB0  b 0x82B6BC3C
        Return r3, the initialized entry.

### Pass 3: priority/timeStamp replacement candidate

This block is reached only after pass 2 exhausted all entries, so all entries are
allocated. That is why the replacement scan itself has no allocated test
(control reaches 0x82B6BB40 from 0x82B6BB3C only after every 0x82B6BB24 test was
nonzero; zero count also reaches it directly).

    0x82B6BB40  lis r10,dbl_8214B270@ha
        Form the address of the double seed.
    0x82B6BB44  fmr f0,f31
        selectedPriority = incoming priority.
    0x82B6BB48  li r31,0
        pSelected = null.
    0x82B6BB4C  cmpwi cr6,r11,0
        Test mNumStreams before the replacement scan.
    0x82B6BB50  lfd f12,dbl_8214B270@l(r10)
        selectedTimeStamp = DBL_MAX. Raw ARTIST bytes at 0x8214B270 are
        7F EF FF FF FF FF FF FF.
    0x82B6BB54  ble cr6,0x82B6BBDC
        Zero count skips the loop and goes to the final eligibility checks.
    0x82B6BB58  lwz r10,4(r30)
        r10 = this->mpStreamDesc.
    0x82B6BB5C  lfs f13,8(r10)
        f13 = entry->priority.
    0x82B6BB60  fcmpu cr6,f13,f0
        Unordered compare entry priority against selectedPriority.
    0x82B6BB64  bge cr6,0x82B6BBB4
        Branch whenever the ordered predicate entry->priority < selectedPriority
        is false. For NaN/unordered, the update-at-0x82B6BB68 path is NOT taken.
        Faithful C++ is the strict ordered predicate, not operator >=.
    0x82B6BB68  lfd f12,0(r10)
        Strictly lower priority: selectedTimeStamp = entry->timeStamp.
    0x82B6BB6C  fmr f0,f13
        selectedPriority = entry->priority.
    0x82B6BB70  b 0x82B6BBCC
        Skip equal-priority tie handling and record this entry.

Equal-priority tie handling:

    0x82B6BBB4  fcmpu cr6,f13,f0
        Recompare entry priority with selectedPriority.
    0x82B6BBB8  bne cr6,0x82B6BBD0
        If not ordered-equal, skip the entry. Unordered/NaN is also not equal and
        therefore skips it.
    0x82B6BBBC  lfd f13,0(r10)
        Equal priority: load entry->timeStamp.
    0x82B6BBC0  fcmpu cr6,f13,f12
        Compare entry timeStamp with selectedTimeStamp.
    0x82B6BBC4  bge cr6,0x82B6BBD0
        Skip whenever the strict ordered predicate
        entry->timeStamp < selectedTimeStamp is false. Unordered skips.
    0x82B6BBC8  fmr f12,f13
        selectedTimeStamp = the strictly lower timestamp.
    0x82B6BBCC  mr r31,r10
        pSelected = current entry. This is shared by the lower-priority path and
        the equal-priority/lower-timestamp path.
    0x82B6BBD0  addic. r11,r11,-1
        Decrement remaining entry count and set CR0.
    0x82B6BBD4  addi r10,r10,0x20
        Advance by the X360 StreamDesc size. This is the third and last raw 0x20
        stride site in AcquireStream.
    0x82B6BBD8  bne 0x82B6BB5C
        Continue until all entries have been examined.

Thus the exact ordering key is lowest priority, then lowest timeStamp. The
selected-priority seed being the incoming priority means entries above it never
become candidates. Equal-priority entries can temporarily become candidates via
the DBL_MAX tie seed, but the final strict-priority eligibility test rejects
replacement at equal priority.

### Replacement eligibility, callback, and reinitialization

    0x82B6BBDC  fcmpu cr6,f0,f31
        Compare selectedPriority with incoming priority.
    0x82B6BBE0  bge cr6,0x82B6BC38
        Fail unless selectedPriority is ordered-less-than incoming priority.
        Unordered fails. Faithful host spelling is
        !(selectedPriority < priority), never selectedPriority >= priority.
    0x82B6BBE4  lis r11,flt_8214AED0@ha
        Form address of the float threshold.
    0x82B6BBE8  lfs f13,flt_8214AED0@l(r11)
        f13 = 100.0f. Raw ARTIST bytes at 0x8214AED0 are 42 C8 00 00.
    0x82B6BBEC  fcmpu cr6,f0,f13
        Compare selectedPriority with 100.0f.
    0x82B6BBF0  bge cr6,0x82B6BC38
        Fail unless selectedPriority is ordered-less-than 100.0f. Unordered fails;
        faithful spelling is !(selectedPriority < 100.0f).
    0x82B6BBF4  lwz r3,0x10(r31)
        Callback argument r3 = selected->pStreamLostContext.
    0x82B6BBF8  lwz r11,0xC(r31)
        r11 = selected->pStreamLostCallback.
    0x82B6BBFC  mtctr r11
        Put the callback target in CTR.
    0x82B6BC00  bctrl
        Call pStreamLostCallback(pStreamLostContext). There is no callback-null
        check and no pSelected-null check.
    0x82B6BC04  lhz r11,0x18(r31)
        Load the selected entry's refCount after the callback returns. This
        ordering permits the callback to have changed refCount synchronously.
    0x82B6BC08  li r10,1
        Value for allocated = true.
    0x82B6BC0C  stfs f31,8(r31)
        selected->priority = incoming priority.
    0x82B6BC10  addi r11,r11,1
        Compute the post-callback refCount + 1.
    0x82B6BC14  stw r28,0xC(r31)
        selected->pStreamLostCallback = incoming callback.
    0x82B6BC18  stw r29,0x10(r31)
        selected->pStreamLostContext = incoming context.
    0x82B6BC1C  mr r3,r31
        Return value = selected entry.
    0x82B6BC20  stb r10,0x1A(r31)
        selected->allocated = true.
    0x82B6BC24  sth r11,0x18(r31)
        Store incremented refCount.
    0x82B6BC28  lwz r11,0(r30)
        r11 = this->mpSystem.
    0x82B6BC2C  lfd f0,8(r11)
        Load mpSystem->GetTime()'s inlined double value.
    0x82B6BC30  stfd f0,0(r31)
        selected->timeStamp = current time.
    0x82B6BC34  b 0x82B6BC3C
        Go to the common epilogue.
    0x82B6BC38  li r3,0
        Failure result = null.

### Epilogue

    0x82B6BC3C  addi r1,r1,0x80
        Pop the local frame.
    0x82B6BC40  lfd f31,var_30(r1)
        Restore f31.
    0x82B6BC44  b __restgprlr_28
        Restore r28–r31/LR and return.

## ReleaseStream: complete instruction-level decode

    0x82B6BC48  mflr r12
        Save LR in r12.
    0x82B6BC4C  stw r12,var_8(r1)
        Save LR to the caller frame.
    0x82B6BC50  std r31,var_10(r1)
        Save nonvolatile r31.
    0x82B6BC54  stwu r1,back_chain(r1)
        Allocate the local frame.
    0x82B6BC58  mr r31,r4
        r31 = streamHandle, logically StreamDesc *. Incoming this in r3 is unused.
    0x82B6BC5C  lhz r11,0x18(r31)
        Load the handle's 16-bit refCount bits. This is an unguarded handle
        dereference.
    0x82B6BC60  addi r11,r11,-1
        Decrement the promoted value.
    0x82B6BC64  extsh. r11,r11
        Sign-extend the low 16 bits and set CR0. This attests signed short.
    0x82B6BC68  sth r11,0x18(r31)
        Store the decremented low 16 bits back to refCount.
    0x82B6BC6C  bne 0x82B6BC80
        If the signed-short post-decrement value is nonzero, skip Kill and leave
        allocated unchanged.
    0x82B6BC70  lwz r3,0x14(r31)
        r3 = handle->pRwCoreStream.
    0x82B6BC74  bl rw::core::filesys::Stream::Kill
        Call pRwCoreStream->Kill(). There is no stream-pointer null check.
    0x82B6BC78  li r11,0
        Prepare false.
    0x82B6BC7C  stb r11,0x1A(r31)
        handle->allocated = false.
    0x82B6BC80  addi r1,r1,0x60
        Pop the frame.
    0x82B6BC84  lwz r12,var_8(r1)
        Restore saved LR value.
    0x82B6BC88  mtlr r12
        Restore LR.
    0x82B6BC8C  ld r31,var_10(r1)
        Restore r31.
    0x82B6BC90  blr
        Return void.

No field other than refCount is changed on the nonzero path. On the zero path,
refCount is stored as zero before Kill, then allocated is cleared after Kill
(0x82B6BC68, 0x82B6BC74, 0x82B6BC7C). The callback, context, priority, timestamp,
and stream pointer are not cleared. Decrementing an already-zero refCount wraps the
stored short to -1/0xFFFF and takes the nonzero path; there is no underflow guard
(0x82B6BC5C–0x82B6BC6C).

## Faithful typed C++

This spelling assumes the PDB/vendor StreamDesc and StreamPool members above. It
uses array indexing, so it remains correct when x64 pointer widening changes
sizeof(StreamDesc). AllocateStream is the real inline vendor helper corroborated by
the ARTIST stores at 0x82B6BB84–0x82B6BBAC and 0x82B6BC04–0x82B6BC30.

    StreamPool::StreamHandle StreamPool::AcquireStream(
        float priority,
        StreamLostCallback pStreamLostCallback,
        void *pStreamLostContext)
    {
        for (int i = 0; i < mNumStreams; ++i)
        {
            StreamDesc &stream = mpStreamDesc[i];
            if (stream.allocated &&
                stream.pStreamLostContext != nullptr &&
                stream.pStreamLostContext == pStreamLostContext)
            {
                ++stream.refCount;
                return &stream;
            }
        }

        for (int i = 0; i < mNumStreams; ++i)
        {
            StreamDesc &stream = mpStreamDesc[i];
            if (!stream.allocated)
                return AllocateStream(
                    &stream, priority, pStreamLostCallback, pStreamLostContext);
        }

        float selectedPriority = priority;
        double selectedTimeStamp = DBL_MAX;
        StreamDesc *pSelected = nullptr;

        for (int i = 0; i < mNumStreams; ++i)
        {
            StreamDesc &stream = mpStreamDesc[i];
            if (stream.priority < selectedPriority)
            {
                selectedPriority = stream.priority;
                selectedTimeStamp = stream.timeStamp;
                pSelected = &stream;
            }
            else if (stream.priority == selectedPriority &&
                     stream.timeStamp < selectedTimeStamp)
            {
                selectedTimeStamp = stream.timeStamp;
                pSelected = &stream;
            }
        }

        // Keep these as negated ordered comparisons. Replacing either with >=
        // changes fcmpu unordered/NaN behavior.
        if (!(selectedPriority < priority) ||
            !(selectedPriority < 100.0f))
        {
            return nullptr;
        }

        // Deliberately no null guard: ARTIST calls through the selected entry.
        pSelected->pStreamLostCallback(pSelected->pStreamLostContext);
        return AllocateStream(
            pSelected, priority, pStreamLostCallback, pStreamLostContext);
    }

    void StreamPool::ReleaseStream(StreamHandle streamHandle)
    {
        StreamDesc *pStreamDesc = static_cast<StreamDesc *>(streamHandle);
        if (--pStreamDesc->refCount == 0)
        {
            pStreamDesc->pRwCoreStream->Kill();
            pStreamDesc->allocated = false;
        }
    }

For completeness, the vendor inline helper whose operations are visible in ARTIST
is semantically:

    StreamPool::StreamDesc *StreamPool::AllocateStream(
        StreamDesc *pStreamDesc,
        float priority,
        StreamLostCallback pStreamLostCallback,
        void *pStreamLostContext)
    {
        pStreamDesc->allocated = true;
        ++pStreamDesc->refCount;
        pStreamDesc->priority = priority;
        pStreamDesc->pStreamLostCallback = pStreamLostCallback;
        pStreamDesc->pStreamLostContext = pStreamLostContext;
        pStreamDesc->timeStamp = mpSystem->GetTime();
        return pStreamDesc;
    }

The helper's source statement order need not match the compiler's reordered stores;
all member values and the important callback-before-refCount-reload ordering are
fixed by the ARTIST instructions cited above.

## Explicit hazard audit

### 1. Float ABI slot

Confirmed: priority is float in f1, callback is r5, and context is r6
(0x82B6BAC4–0x82B6BACC). There is no r4 parameter. The stfs instructions at
0x82B6BB8C and 0x82B6BC0C exclude a double source-level priority.

### 2. Raw console offsets/strides do not survive x64

All 0x20 entry-stride instructions in AcquireStream are:

- 0x82B6BB08 — first/reuse pass
- 0x82B6BB34 — second/free pass
- 0x82B6BBD4 — replacement pass

ReleaseStream has no stride instruction because it receives a handle directly.
Typed PC code must use mpStreamDesc[i], never byte addition by 0x20. StreamDesc
contains two data pointers and one function pointer, so its X360 0x20 layout is not
the x64 layout.

Neither requested body uses the pool's 0x2C list-node offset. The already-established
GetInstance owner conversion is the relevant ARTIST site at 0x82B6BA78. Typed PC
code must use mListNode/container ownership, never subtract 0x2C; widened members
before mListNode move it on x64.

### 3. fcmpu / NaN polarity

All replacement comparisons are expressed above using strict ordered < or ==:

- Candidate priority update: 0x82B6BB60–0x82B6BB68.
- Equal-priority test: 0x82B6BBB4–0x82B6BBBC.
- Timestamp tie-break update: 0x82B6BBC0–0x82B6BBC8.
- Incoming-priority eligibility: 0x82B6BBDC–0x82B6BBE0.
- 100.0f eligibility: 0x82B6BBEC–0x82B6BBF0.

For the four bge instructions, unordered makes the strict ordered update/success
path not taken. The C++ therefore uses !(x < y) for rejection and never substitutes
x >= y.

### 4. Variable-length tail placement on x64

There is no object-size/tail-placement literal in either requested ARTIST body:
both reach entries solely through typed member mpStreamDesc at pool +0x04
(0x82B6BAE0, 0x82B6BB20, 0x82B6BB58).

The known console creator formula exists only in corroborating DecFIGS, not in an
ARTIST creation path: 0xE2E52C computes this+0x3B, 0xE2E538 rounds it down to an
8-byte boundary (therefore align-up of console sizeof(StreamPool) 0x34), and
0xE2E548 stores the resulting tail pointer into mpStreamDesc. Porting +0x3B or the
resulting +0x38 tail start to x64 would place the tail inside the widened host
object. A future PC creator must use typed/separate storage or an alignment
calculation from host sizeof(StreamPool) and alignof(StreamDesc). This report does
not invent an ARTIST creator, which the established dossier shows is absent.

## Explicit unknowns / non-claims

- Why the literal replacement ceiling is 100.0f is not named by ARTIST. This report
  preserves the value and predicate only (loads/tests at 0x82B6BBE4–0x82B6BBF0).
- The requested bodies do not attest behavior for StreamPool bytes +0x08..+0x23.
- StreamDesc::pad and the final four console padding bytes have no semantics in
  either body.
- No validation, locking, ownership check, callback-null check, stream-null check,
  refCount overflow check, or refCount underflow check is present. None is added.
- No creation/registration behavior is inferred. GetInstance and the empty ARTIST
  registry remain exactly as established in the prerequisite dossier.
- No assumption is made about what a stream-lost callback does. ARTIST only attests
  that it is called synchronously before refCount is reloaded for the replacement
  allocation (0x82B6BBF4–0x82B6BC04).
