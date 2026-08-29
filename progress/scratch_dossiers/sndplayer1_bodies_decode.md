# `rw::audio::core::SndPlayer1` -- full body decode (phase E, 2026-08-28)
Produced by a 4-way decode fan-out plus 2 adversarial verifiers over the ARTIST image.
Every one of the 27 functions came back DECODED; none is blocked.

Ground truth is the `assembly` field of `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x<ADDR>.json`,
with exporter gaps (`EventEvent` @0x82BA5C48, `PlugIn::Initialize<SndPlayer1>` @0x82B9D368,
`DecoderRegistry::DecoderFactory` @0x82B6C778) hand-decoded from the decrypted XEX at
`file_off = 0x3000 + vaddr - 0x82000000`, big-endian.

> **Read the verification section FIRST.** It carries the host-porting hazard list, which is
> the highest-value part of this document: the natural transliteration of this class is wrong
> in at least a dozen specific, enumerated places.

---

# Part 1 -- verification and host-porting hazards

## Verifier 1 -- verdict: DISCREPANCIES

### GetSize behaviour opens: "Twelve instructions, leaf, no branches taken on the common path."

**Actual:** GetSize is SEVENTEEN instructions (0x82BA0220..0x82BA0260 inclusive), which is also exactly how many lines the decode's own register-by-register table lists. Self-inconsistent count.

**Evidence:** (0x82BA0260 - 0x82BA0220)/4 + 1 = 17. Raw words verified from IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex at file_off 0xBA3220: 81630000 280B0000 4182001C 3941FFF0 C00B0000 FC00065E 7C0057AE 8161FFF0 48000008 39600001 89230008 1D4B0030 552B103E 396B01DF 556B0038 7C6B5214 4E800020 = 17 words, terminated by blr.

### GetSize hazards #1 / sketch header comment: "0x1D8 is the fixed-header extent. It contains 30 32-bit pointers".

**Actual:** The decode's own enumeration on the very next lines sums to 52 pointers, not 30. Its downstream numbers are consistent with 52, not 30 -- so "30" is the wrong figure, and the only figure a reader would carry away.

**Evidence:** Enumeration in the decode: vptr(1) + PlugIn mpSystem/mpVoice/mpAttribute/mpPlugInDescRunTime(4) + TimerHandle's four(4) + mpRequestExternal(1) + "the 20 feed records' pChunkInfo + pRwCoreStream (40 pointers on their own)"(40) + mpLoadedDecoder(1) + mpRequestHandle(1) = 52. 52 x 4 bytes of widening = 208, which is what makes the decode's own two derived figures correct: hazard 1's "under-allocates the object by ~200 bytes" and the sketch's "pushes uDeclick from 0x1D8 to ~0x2A0" (0x1D8 + 208 = 0x2A8). Both require 52; neither is reachable from 30. Feed-record pointer pair independently confirmed: FeedCleanup @0x82BA0308 `lwz r9, 0(r31)` (pChunkInfo, passed as r4 to Stream::ReleaseChunk) and @0x82BA0334 `lwz r3, 4(r31)` (pRwCoreStream, the ReleaseChunk this), stride 0x10 from `rotlwi r11,r11,4` @0x82BA0290; vendor references/Feb-2007/.../rwaudiocore/2.11.00/include/rw/audio/core/plugins/sndplayer1.h SndPlayer1FeedDesc = {ChunkInfo *pChunkInfo; Stream *pRwCoreStream; int chunkSamplesPlayed; u8 decoderRequestHandle; u8 feedState; u8 requestIndex;}.

### GetSize hazards #1: "BOTH literals in this formula are pointer-bearing console extents and NEITHER survives: 0x1D8 ... and 0x30 ..." -- i.e. the decode asserts there are exactly two console literals in this cluster needing a host sizeof(), and CreateInstance's `behaviour` records `mulli r9, r29, 0x50` / `addi r4, r9, 4` as the private-Alloc size expression with no host-expression note anywhere.

**Actual:** 0x50 is a THIRD pointer-bearing console extent, and unlike 0x1D8/0x30 it is consumed by CreateInstance's own System::Alloc call, so a transliterated `0x50*n + 4` under-allocates the RequestExternal array on x64 exactly the way hazard 1 warns about for the other two. The house rule ("NEVER transliterate a console size/offset that contains a 32-bit pointer -- say what the host expression must be instead") is therefore unmet for the one allocation this function actually performs. The `+4` head is also a console-implicit alignment assumption: on x64 the RequestExternal array must start at an alignof(RequestExternal)-correct offset past the f32 counter, not at a hard-coded 4.

**Evidence:** 0x82BA6CEC `1D3D0050` = mulli r9, r29, 0x50; 0x82BA6D0C `38890004` = addi r4, r9, 4; 0x82BA6D14 bl System::Alloc; 0x82BA6D24 `39630004` = addi r11, r3, 4; 0x82BA6D30 `917F0058` = stw r11, 0x58(r31). The 0x50-stride record holds at least four 32-bit pointers, proven in PlayHandler with r31 = mpRequestExternal + 0x50*i (stride confirmed by FeedCleanup @0x82BA031C `mulli r11, r7, 0x50` + `lwz r10, 0x58(r30)`): 0x82BA4304 `stw r3, 0x20(r31)` = StreamPool*, 0x82BA4320 `stw r3, 0x24(r31)` = AcquireStream handle*, 0x82BA4330 `stw r11, 0x28(r31)` = Stream*, 0x82BA4388 `stw r3, 0x1C(r31)` = the char* from System::Alloc("SndPlayer1 StreamLoopFileName").

### CreateInstance behaviour, PHASE 3: "and the alloc arguments: r3 = self->mpSystem (`lwz r3,4(r31)`), r5 = the name string, r6 = 0x10 (align), r7 = 0 (allocator override)."

**Actual:** r5 is NOT the "SndPlayer" string the decode loads into r28 two instructions earlier and later names explicitly as AddTimer's r7. It is a distinct rodata literal reached by a NEGATIVE displacement off r28. Leaving it as "the name string" in the same paragraph that establishes r28 = "SndPlayer" invites the host port to pass the wrong debug-allocation name; under the no-invention rule the actual literal had to be stated or marked BLOCKED.

**Evidence:** r28 is built at 0x82BA6CC0 `3D408217` (lis r10,0x8217) + 0x82BA6CCC `3B8A45CC` (addi r28,r10,0x45CC) => r28 = 0x821745CC, string at file_off 0x1775CC = "SndPlayer". The alloc name is 0x82BA6CFC `38BCFFCC` = addi r5, r28, -0x34 => 0x82174598, string at file_off 0x177598 = "SndPlayer1 RequestHandle and RequestExternal array". IDA's own operand comment on that line reads "SndPlayer1 RequestHandle and RequestExt"..., i.e. the dossier already showed it was a different string.

### CreateInstance behaviour, PHASE 8: "mbTimerAdded (+0x1D0) is therefore the exact byte ReleaseEvent tests (`cmplwi r11,1` @0x82BA4190)".

**Actual:** 0x82BA4190 is the `lbz`, not the `cmplwi`. The compare is one instruction later at 0x82BA4194. The substantive claim (ReleaseEvent gates System::RemoveTimer on +0x1D0 == 1) is correct; only the cited address is off by one instruction.

**Evidence:** Raw words at file_off 0xBA7190: 0x82BA4190 `897F01D0` = lbz r11, 0x1D0(r31); 0x82BA4194 `2B0B0001` = cmplwi cr6, r11, 1; 0x82BA4198 `409A0010` = bne cr6, +0x10; 0x82BA419C `389F0040` = addi r4, r31, 0x40; 0x82BA41A0 `807F0004` = lwz r3, 4(r31); 0x82BA41A4 = bl RemoveTimer.

### CreateInstance behaviour items [10]/[11] annotate +0x38 and +0x30 as "= 0.0 (f64!)" and the decode carries no hazard about the attribute slot type; the task requires the sketch be written by-name against the committed b5-decomp engine types.

**Actual:** The f64 reading is CORRECT (I tried hard to refute it and could not -- see evidence), but the decode omits the blocking consequence: the committed b5-decomp/vendor/renderware/include/rw/audio/core/PlugIn.h declares `struct Attribute_t { f32 mfValue; u32 muPad; }`, which has no f64 member, so stores [10] and [11] cannot be written by name against the target type as the decode leaves it. The vendor type is `union Attribute_t { double f64; float f32; }`. The decode also never flags the endianness consequence: on big-endian PPC the f64 write puts the double's HIGH word at +0x30, so PlugIn::GetAttribute's f32 view reads a different word than it will on little-endian x64 -- a real console/host divergence for attribute slots 1 and 2 that a faithful port has to decide about.

**Evidence:** Attribute base proven at self+0x28: PlugIn::Initialize<SndPlayer1> raw @0x82B9D3A8 `7D7FF214` = add r11,r31,r30 (r30 = the 0x28 from `38800028` @0x82BA6CB4), 0x82B9D3AC `917F000C` = stw r11, 0xC(r31). Generic accessor is f32 at stride 8: PlugIn::GetAttribute @0x82B6A8C8 `lwz r11,0xC(r3) ; slwi r10,r4,3 ; lfsx f0,r10,r11 ; stfs f0,0(r5)`. But SndPlayer1 genuinely writes doubles into slots 1/2: RwacTimerClient @0x82BA6A20..0x82BA6A4C `lfs f0,0x1A4(r31) ; lwa r11,0x1AC ; lwa r9,0x1A8 ; fcfid f13 ; fcfid f12 ; fdiv f13,f13,f0 ; stfd f13,0x38(r31) ; fdiv f0,f12,f0 ; stfd f0,0x30(r31)` -- non-zero doubles, while slot 0 in the same function is `stfs f13,0x28(r31)` @0x82BA69F4. Vendor plugin.h line 2122 confirms `union Attribute_t { double f64; float f32; };` and sndplayer1.h line 355 `Attribute_t mAttribute[ATTRIBUTE_MAX]`. Committed PlugIn.h Attribute_t (f32 mfValue; u32 muPad) cannot express either store.

### Verifier notes

METHOD: read both dossiers' `assembly` fields, then re-decoded every word of both functions from IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex (file_off = 0x3000 + vaddr - 0x82000000, big-endian) and hand-verified the rlwinm/rotlwi masks bit-field by bit-field. All five cross-referenced sites (Voice::CreateInstance, PlugIn::CreateInstance, PlugIn::Initialize<SndPlayer1>, ReleaseEvent, Process) were re-read from raw bytes or their own dossiers.

WHAT SURVIVED REFUTATION (all confirmed, do not re-litigate):

GetSize @0x82BA0220 -- byte-exact. `lwz r11,0(r3)` / cmplwi / beq; fctidz+stfiwx truncate-toward-zero, low 32 bits; default n=1; `lbz r9,8(r3)`; `mulli r10,r11,0x30`; `rotlwi r11,r9,2` (0x552B103E = rlwinm r11,r9,2,0,31 -- no wrap for a byte); `addi r11,r11,0x1DF`; `clrrwi r11,r11,3` (0x556B0038 = rlwinm r11,r11,0,0,28, mask 0xFFFFFFF8); `add r3,r11,r10`; blr. Formula align_up(0x1D8 + 4*c, 8) + 0x30*n CONFIRMED. No fcmpu anywhere, so hazard 5's "no branch polarity to preserve" is right; fctidz(NaN) = 0x8000000000000000 -> stfiwx keeps low word 0, and a negative float yields a huge unsigned n, both as stated.

CreateInstance @0x82BA6C80 -- all 27 numbered init stores verified in the asm's exact order, offsets and widths, including the stfs/stfd split, the f13 reload of 48000.0f at 0x82BA6D98 landing between the 0.0-double stores and the two 48000.0f stores, and `stfs f0,0(r9)` with r9 re-loaded from +0x1B0 at 0x82BA6D60. Phase 5 request loop (guarded by `cmplwi cr6,r29,0 ; beq`, re-loads lhz 0x1C4 each pass, `stb r30,0x2A(r10)`, stride 0x30) confirmed. Phase 7 feed loop (`addi r11,r31,0x5C`, `li r10,0x14`, stb +0xD, stw +0x00, stride 0x10, 0x5C+20*0x10 = 0x19C) confirmed. Phase 8 AddTimer arg vector confirmed including r5 = 0x82BA6980 (`38AA6980` off `lis r10,0x82BA`), and the return polarity (`clrlwi. r11,r3,24 ; beq -> li r3,1 ; stb 1,0x1D0`) is exactly as decoded: AddTimer returning zero is success.

Rodata re-read and confirmed: flt_82001CC0 = 0.0f (00000000), dbl_82001CA8 = 0.0 (0000000000000000), flt_820AA808 = 48000.0f (473B8000, reached via `lis r11,0x820B` + `lfs f13,-0x57F8(r11)`).

Dispatch sites confirmed: Voice::CreateInstance 0x82B6EC98 `lwz r11,4(r31)` / 0x82B6EC9C `mr r3,r31` / 0x82B6ECA0 `lwz r11,4(r11)` / 0x82B6ECA8 bctrl; 12-byte config stride (`3BFF000C` @0x82B6ECB8); the 16-alignment of each stage carve (`397C000F` + `556B0036` = rlwinm r11,r11,0,0,27 = mask 0xFFFFFFF0, then `add r28,r3,r11`); `li r7,0x10` @0x82B6ECC8. PlugIn::CreateInstance 0x82B6A85C/0x60 copies config+8 into +0x21 BEFORE the bctrl, 0x82B6A864 `lwz r4,0(r6)`, 0x82B6A868 `lwz r11,8(r5)`, 0x82B6A874 `clrlwi. r11,r3,24` + bne-to-success, and the failure path really is vt[0](self) then vt[3](self,0) then null. PlugIn::Initialize<SndPlayer1> @0x82B9D368 does all three things claimed: `stw r11,0(r31)` with the 0x8217F344 vtable, `bl` TimerHandle ctor on r3 = self+0x40, `add r11,r31,r30 ; stw r11,0xC(r31)` = mpAttribute at self+0x28.

The decode BEATS the prior scratch dossier on +0x1CF. progress/scratch_dossiers/sndplayer1_decode_codex.md calls it "ARTIST-only/unknown byte ... no semantic reader was found"; it is in fact a feed-slot cleanup cursor, exactly as the decode under test names it. SndPlayer1::FeedCleanup reads it at 0x82BA0278, 0x82BA028C (`rotlwi r11,r11,4` -> +0x5C = the feed record), and advances/wraps it at 0x82BA034C..0x82BA0364 (`addi +1 ; clrlwi ; cmplwi 0x14 ; -> 0 ; stb r11,0x1CF`), chasing +0x1CE. Caveat: the decode says "NOT an unknown byte; see hazards", but hazards 1-7 contain no entry for +0x1CF -- the pointer dangles even though the claim is true.

Every +0x1C6..+0x1CE name in the decode matches the vendor member ORDER in references/Feb-2007/.../rwaudiocore/2.11.00/include/rw/audio/core/plugins/sndplayer1.h one-for-one (mMaxChannels, mNextFreeRequest, mNextRequestToFree, mCurrentRequest, mMaxRequests, mDcOffsetsGathered, mNumDeclickSamples, mNextFeedSlotToFill, mNextFeedSlotToFree). The vendor list ENDS there -- +0x1CF and +0x1D0 are ARTIST-build additions, so the decode's names for those two are reconstructions, both behaviourally grounded (FeedCleanup / ReleaseEvent). Note one real ARTIST divergence the decode gets right without calling out that it is a divergence: the vendor header declares `float mRequestHandle` as an EMBEDDED float at that slot, whereas ARTIST stores the allocation base pointer there (`stw r3,0x1B0`) and writes the counter through it (`lwz r9,0x1B0 ; stfs f0,0(r9)`).

Hazard 3 (two different sources for the channel byte), hazard 4 (mMaxRequests takes only n&0xFF; PlayHandler wraps +0x1C7 against +0x1CA at 0x82BA44A4/0x82BA44A8/0x82BA44C4, StopHandler loops on +0x1CA at 0x82BA44F8/0x82BA452C), hazard 7 (streammod fork = 0x20 / 0x88 / 0x0C-no-pointers / 0x188 vs vendor 0x30 / 0x50 / 0x10-two-pointers / 0x1D8) and the config literals {&1.0f,'SnP1',1} / {&2.0f,'SnP1',2} (b5-decomp/src/GameShared/GameClasses/Sound/Playback/Splicer/SpliceManager.cpp:83-84) all check out.

TWO SUB-DISCREPANCY NITS not worth a row:
(a) The decode transcribes IDA's `addi r10, r1, back_chain` / `lwz r11, back_chain(r1)` literally, which reads as displacement 0. The real encodings are 0x3941FFF0 and 0x8161FFF0 = r1 - 0x10, i.e. the frameless leaf's red-zone scratch below SP, not the back-chain word. Hazard 6's interpretation ("a frameless leaf's scratch word, not a member store; the host uses an ordinary local") is correct regardless.
(b) The sketch asserts `alignof(SndPlayer1) >= alignof(RequestInternal)` under a comment reading "the carve is 16-aligned", while hazard 2 says the required assert is `alignof(SndPlayer1) <= 16`. These are different conditions and neither alone captures the console invariant; the port wants both.

## Verifier 2 -- verdict: DISCREPANCIES

### (Q1) GetSize reads the stage's channel count from config byte +8, so the host can write `*((const u8*)apConfig + 8)`.

**Actual:** +8 is an OFFSET PAST TWO 32-BIT POINTERS inside VoiceStageConfig {void* mpContext; PlugInDescRunTime* mpDesc; u32 mFlagAndField8}. On x64 mFlagAndField8 sits at +16 and the console's +8 lands INSIDE the widened mpDesc. Host expression MUST be `apConfig->mFlagAndField8 & 0xFF`. This is the exact mis-read the memory index records as the phase-D 'mixer scribble crash'. Related asymmetry that also invites a wrong port: GetSize's r3 is the VoiceStageConfig* itself (it derefs +0 to reach the f32 ctor-param array), but SndPlayer1::CreateInstance's r4 is ALREADY config->mpContext (the f32*) -- PlugIn::CreateInstance @0x82B6A864 does `lwz r4, 0(r6)` before the bctrl. The two entry points do NOT take the same type.

**Evidence:** GetSize 0x82BA0248 `lbz r9, 8(r3)`; 0x82BA0220 `lwz r11, 0(r3)` + 0x82BA0230 `lfs f0, 0(r11)`. PlugIn::CreateInstance 0x82B6A85C `lbz r11, 8(r6)` / 0x82B6A860 `stb r11, 0x21(r31)` / 0x82B6A864 `lwz r4, 0(r6)`. Voice.h VoiceStageConfig.

### (Q1) The SndPlayer1 fixed extent is 0x1D8 (literal 0x1DF = 0x1D8+7 in both GetSize and CreateInstance), so the host can keep 0x1DF/0x1D8.

**Actual:** 0x1D8 spans roughly 49 32-bit pointer slots and cannot be transliterated: vptr +0x00, System* +0x04, Voice* +0x08, Attribute_t* +0x0C, PlugInDescRunTime* +0x10, the embedded TimerHandle's node/callback/context/name at +0x40/+0x44/+0x48/+0x4C, RequestExternal* +0x58, TWENTY feed descriptors at +0x5C carrying two pointers each, Decoder* +0x19C, and the handle-array f32* +0x1B0. Host expression: `align_up(sizeof(SndPlayer1), 8)` from ONE shared layout helper used by both GetSize and CreateInstance. Precondition the console constant hides: CreateInstance computes align8(this + 0x1D8) while GetSize computes align8(0x1D8) with no `this`; the two agree only because Voice::CreateInstance places stages 16-aligned. Host Voice.cpp does keep 16-aligned placement (Voice.cpp:74,124), so the precondition holds -- but it must be asserted, and the request-array alignment must track alignof(RequestInternal) (8, from its leading f64), not a hardcoded 8.

**Evidence:** GetSize 0x82BA0254 `addi r11, r11, 0x1DF` + 0x82BA0258 `clrrwi r11, r11, 3`; CreateInstance 0x82BA6CC8 `addi r11, r31, 0x1DF` + 0x82BA6CD4 `clrrwi r11, r11, 3`. Pointer slots: 0x82BA6D30 `stw r11, 0x58`, 0x82BA6DD8 `stw r30, 0(r11)` (feed +0x00), 0x82BA6D1C `stw r3, 0x1B0`, 0x82BA0824 `stw r11, 0x19C`, 0x82BA6E00 `addi r4, r31, 0x40` (TimerHandle).

### (Q1) The RequestInternal stride 0x30 is a plain 48-byte POD record and survives x64 (it is even 48 bytes wide on the host by coincidence).

**Actual:** RequestInternal +0x08 IS A Decoder* -- Process loads it straight into mpCurrentDecoder and passes it as r3 to Decoder::Decode; StartRequest stores the DecoderFactory result there; SubmitChunk passes it as r3 to Decoder::Feed. So every `0x30` here is a console sizeof containing a 32-bit pointer and must become `sizeof(RequestInternal)`. The host layout happening to land on 48 again (f64 +0, Decoder* +8, then the scalar tail) is a COINCIDENCE that must not be relied on -- and it breaks the moment a second pointer is typed into the record. Five sites: GetSize's `mulli r10, r11, 0x30`, CreateInstance's `mulli r9, r29, 0x50`-adjacent request loop `addi r11, r11, 0x30`, and Process's four `mulli r11, r11, 0x30`.

**Evidence:** Process 0x82BA0818 `lwz r11, 8(r30)` -> 0x82BA0824 `stw r11, 0x19C(r31)` -> 0x82BA08EC `lwz r3, 0x19C(r31)` + 0x82BA08F4 `bl Decoder::Decode`. StartRequest 0x82BA64B4 `stw r3, 8(r28)` after DecoderFactory. SubmitChunk 0x82BA4620/0x82BA4654 `lwz r3, 8(r11)` -> `bl Decoder::Feed`. Strides: 0x82BA024C, 0x82BA6D48, 0x82BA05A8, 0x82BA0628, 0x82BA08A8, 0x82BA09E0.

### (Q1/Q3) The 16-byte feed-descriptor ring at this+0x5C is scalar bookkeeping, so the `rotlwi rX, i, 4` index scalings and the `v12 += 16` init walk transliterate directly.

**Actual:** THE FEED DESCRIPTOR CARRIES TWO 32-BIT POINTERS: +0x00 is a stream ChunkInfo* and +0x04 is an rw::core::filesys::Stream* -- FeedCleanup loads both and passes them as r4/r3 to Stream::ReleaseChunk, and SubmitChunk copies RequestExternal+0x28 (the Stream) into +0x04. Host sizeof is 24 (void*, Stream*, s32, u8 handle, u8 state, u8 reqIndex, pad), NOT 16. Every `i*16` must become `i * sizeof(SndPlayer1FeedDesc)` and the +0x5C base must become the named array member. Three distinct spellings all mean the same scaling and all break: `rotlwi r11, r11, 4` (Process x5: 0x82BA0688, 0x82BA06D0, 0x82BA06E8, 0x82BA081C, 0x82BA0958), `clrlslwi r10, r10, 24, 4` (Process 0x82BA0A98 -- the pseudocode renders this as `(16*v51) & 0xFF0`, which is nonsense at stride 24), and CreateInstance's `addi r11, r11, 0x10` init walk, which at stride 16 would cover only 320 of the host array's 480 bytes and land every store at the wrong member. This stride is NOT listed among the hazards in progress/scratch_dossiers/sndplayer1_decode_codex.md section 1.

**Evidence:** FeedCleanup 0x82BA0308 `lwz r9, 0(r31)` (feed base r31 = this+0x5C+16i) -> 0x82BA0340 `lwz r4, 0(r31)` and 0x82BA0334 `lwz r3, 4(r31)` -> 0x82BA0344 `bl rw::core::filesys::Stream::ReleaseChunk`; 0x82BA0324 `lwz r9, 4(r9)` reads ChunkInfo+0x04. SubmitChunk 0x82BA4604 `lwz r10, 0x28(r29)` -> 0x82BA460C `stw r10, 4(r30)`. CreateInstance loop 0x82BA6DA4..0x82BA6DE0.

### (Q1) CreateInstance's private allocation is `0x50*n + 4` with the array based at `alloc + 4`.

**Actual:** Both halves are wrong on x64. (a) 0x50 is the RequestExternal stride and that record is pointer-dense -- +0x08 sample/payload pointer, +0x1C loop filename, +0x20 StreamPool, +0x24 stream handle, +0x28 Stream (SubmitChunk reads +0x28 and hands it to Stream::ReleaseChunk as a Stream*) -- so it must be `sizeof(RequestExternal) * n`. (b) The `+4` head slot (the f32 request-handle counter that CreateInstance zeroes through +0x1B0) leaves the array at 4-mod-16, which on x64 MISALIGNS RequestExternal's leading f64 (+0x00 stream file offset) and its 8-byte pointers. The host must either pad the header to alignof(RequestExternal) or use two allocations; `System::Alloc(..., 16, 0)` only aligns the block, not the +4 sub-base.

**Evidence:** CreateInstance 0x82BA6CEC `mulli r9, r29, 0x50` + 0x82BA6D0C `addi r4, r9, 4` + 0x82BA6D14 `bl System::Alloc` + 0x82BA6D24 `addi r11, r3, 4` / 0x82BA6D30 `stw r11, 0x58(r31)`; 0x82BA6D88 `stfs f0, 0(r9)` (f0 = flt_82001CC0 = 0.0f, rodata-verified). Stride consumers: SubmitChunk 0x82BA4584, FeedCleanup 0x82BA031C, StartRequest 0x82BA6460 -- all `mulli rX, i, 0x50` off `lwz 0x58`.

### (Q1) Process's `mulli r10, r9, 0x14` indexes the decoder's request ring at a 20-byte stride, and Decoder.h states the record is pointer-free so 'the 20-byte stride still survives x64'.

**Actual:** THE COMMITTED HEADER COMMENT IS STALE AND SELF-CONTRADICTING, and Process's 0x14 must become sizeof(DecoderRequest) = 24. DecoderRequest's own member list in the same header declares `const void *mpFedData` at +0x00 (Decoder::Feed `stw r4, 0`; SubmitChunk passes a computed payload pointer as that argument), so it is an 8-byte member on x64 and the record grows to 24. Decoder.cpp:44-66 already documents the revision and pins `sizeof(DecoderRequest)`, but Decoder.h:57-58 ('every field is a 32-bit word (no pointers) so the stride survives the x64 widening'), Decoder.h:62-63 ('every field remains a 32-bit-safe scalar, so the 20-byte stride still survives x64') and Decoder.h:153 ('this + muRequestQueueOffset + 0x14 * mucRequestDecodeIndex') still assert the opposite -- a reader porting Process from the header alone will hardcode 20. TRAP: the literal 0x14 appears twice in the same call chain with OPPOSITE host fates -- StartRequest's `li r6, 0x14` is the ring MODULUS (20 slots, stays 20, lands at Decoder+0x32) while DecoderFactory's `mulli r21, r26, 0x14` and Process's `mulli 0x14` are the STRIDE (becomes 24). DecoderFactory also adds a trailing `addi r29, r11, 0x14` that is sizeof(DecoderBuffer) -- a third 0x14 that likewise widens to 24 because DecoderBuffer::mpData is a pointer.

**Evidence:** Process 0x82BA0830 `mulli r10, r9, 0x14` and 0x82BA0AB4 `mulli r8, r9, 0x14`, both added to `lwz r8, 0x24(r11)` (muRequestQueueOffset) + the decoder base, then reading +0x0C (miEndSample) / +0x08 (miStartSample) / decoder +0x31 (mucRequestDecodeIndex) / decoder +0x1C (miCurrentSampleOffset). DecoderFactory @0x82B6C778 raw-decoded from the XEX (exporter gap): 0x82B6C78C `mr r26, r6`, 0x82B6C7B0 `mulli r21, r26, 0x14`, 0x82B6C7E4 `addi r29, r11, 0x14`, 0x82B6C894 `stb r26, 0x32(r31)`, ring init walk 0x82B6C93C..0x82B6C948 `addi r11, r11, 0x14`. StartRequest 0x82BA64A0 `li r6, 0x14`.

### (Q1/Q2) Process's stack-allocator carve size comes from RequestInternal+0x28, a plain u16 byte count that can be read and used as-is.

**Actual:** THAT NUMBER IS AN ENTIRE CONSOLE DECODER-INSTANCE SIZE -- the single most pointer-dense constant in the function, and it reaches Process through a NARROW FIELD THAT CAN OVERFLOW ON THE HOST. DecoderFactory computes it as `align8(codecGetSize) + numRequests*sizeof(DecoderRequest) [+ align16 + sizeof(DecoderBuffer)]` and stores the 32-bit total at Decoder+0x20; StartRequest then does `lwz r11, 0x20(r3)` / `sth r11, 0x28(r28)` -- a silent 32->16 truncation. On x64 that total grows by at least the Decoder header's five widened pointers, 20*(24-20)=80 bytes of ring, and 4 bytes of DecoderBuffer, plus each codec's own widening. If any host codec's total crosses 65536 the u16 wraps and Process carves a fraction of what the decoder needs, moving StackAllocator::mpTop too little and letting the next scratch consumer overlap it. The host must (a) keep the narrow field but ASSERT the producer's value fits, or widen it at the producer with a matching consumer change, and (b) never treat 0x28 as a decoder-independent constant. BLOCKED on quantifying the actual host overflow risk: DecoderRegistry::DecoderFactory @0x82B6C778 is an exporter gap and is not bodied on the host yet (Decoder.cpp:56-60 says so), so no host codec total exists to measure.

**Evidence:** Process 0x82BA07F0 `lhz r11, 0x28(r30)` / 0x82BA07F4 `addi r9, r11, 0x7F` / 0x82BA07FC `clrrwi r9, r9, 7`, and again 0x82BA0A20..0x82BA0A2C. StartRequest 0x82BA64BC `lwz r11, 0x20(r3)` / 0x82BA64C8 `sth r11, 0x28(r28)`. DecoderFactory raw decode: 0x82BA6C7C4..0x82B6C7E4 size accumulation, 0x82B6C87C `stw r29, 0x20(r31)`.

### (Q2) CreateInstance computes its two relative offsets as `(this + 479) & 0xFFF8` and `(end + 7) & 0xFFF8` (per the IDA pseudocode), so the host can copy those masks.

**Actual:** The 0xFFF8 is a 16-BIT TRUNCATION ARTIFACT, not an alignment mask, and the pseudocode additionally gets the FIRST one wrong. The asm's first align is `clrrwi r11, r11, 3` -- a full 32-bit `& ~7` -- and only the SECOND is `rlwinm r10, r10, 0, 16, 28` (`& 0x0000FFF8`), applied to an ABSOLUTE 32-bit address whose top 16 bits are then discarded. It is correct on console only because the result is immediately `subf`'d against `this` and stored via `sth`, so the low 16 bits survive intact. Applying `& 0xFFF8` to a 64-bit host `this` before subtracting yields garbage. Host expression: compute `align_up(base + 4*channels, alignof(RequestInternal))` at full width, subtract `(uintptr_t)this`, then narrow on the u16 store. Overflow check for Q2 on these two fields: host fixed extent is ~0x1D8 + ~49 widened pointers ~= 0x2A0, plus 4*channels -- both offsets stay far under 65535, so the u16 width itself is SAFE and must be preserved (widening it would move +0x1C6..+0x1D0).

**Evidence:** CreateInstance 0x82BA6CC8/0x82BA6CD4 (`addi r11, r31, 0x1DF` / `clrrwi r11, r11, 3`), 0x82BA6CE4 `subf r11, r31, r11`, 0x82BA6CF4 `sth r11, 0x1C2(r31)`; 0x82BA6CE8 `addi r10, r10, 7`, 0x82BA6CF8 `rlwinm r10, r10, 0,16,28`, 0x82BA6D00 `subf r10, r31, r10`, 0x82BA6D10 `sth r10, 0x1C4(r31)`. Pseudocode line: `v5 = (a1 + 479) & 0xFFF8;` -- contradicted by the clrrwi.

### (Q2) The request count n is stored at +0x1CA and used consistently.

**Actual:** It is stored NARROW while three other consumers use it WIDE. `stb r29, 0x1CA` keeps only the low byte, but the same 32-bit r29 sizes the allocation (`mulli r9, r29, 0x50`), drives the record init loop (`addic. r29, r29, -1`), and GetSize's `mulli r10, r11, 0x30` sizes the instance from the full value. At n = 256 the object and allocation are sized for 256 requests while mMaxRequests reads 0 -- the ring modulus in AdvanceCurrentRequest / StopHandler / ModifyStartTimeHandler collapses. This is a CONSOLE-side truncation that the host must reproduce, not repair: do NOT widen +0x1CA (it is packed against +0x1C9/+0x1CB and the wrap arithmetic `if (++i == mMaxRequests) i = 0` depends on the byte), and do NOT clamp n. Unreachable with the shipped splice configs ({&1.0f,'SnP1',1} and {&2.0f,'SnP1',2}); an assert at the store is the correct host addition.

**Evidence:** CreateInstance 0x82BA6CEC `mulli r9, r29, 0x50`, 0x82BA6D28 `stb r29, 0x1CA(r31)`, 0x82BA6D40 `addic. r29, r29, -1`; GetSize 0x82BA024C `mulli r10, r11, 0x30`. Modulus readers: StopHandler 0x82BA44F8/0x82BA452C `lbz r11, 0x1CA`, ModifyStartTimeHandler 0x82BA03D8.

### (Q1/Q2) The float->int conversion of the ctor parameter is `(int)*a2`, identically in GetSize and CreateInstance.

**Actual:** The console pair is `fctidz` + `stfiwx`: a SATURATING 64-bit truncate whose LOW 32 BITS are then stored. PowerPC fctidz yields 0x8000000000000000 for NaN (low word 0 -> n = 0) and 0x7FFFFFFFFFFFFFFF for large positives (low word 0xFFFFFFFF -> n = -1). x64 `cvttss2si` gives 0x80000000 for both (n = INT_MIN, then `mulli 0x50` overflows the allocation size). Faithful host expression: saturate to s64, then take the low 32 bits -- and it must be ONE shared helper, because GetSize and CreateInstance MUST agree on n or the request array overruns the GetSize allocation. There is no range/NaN/sign validation on either path.

**Evidence:** GetSize 0x82BA0230..0x82BA023C `lfs f0, 0(r11)` / `fctidz f0, f0` / `stfiwx f0, 0, r10` / `lwz r11, back_chain(r1)`; CreateInstance 0x82BA6C9C..0x82BA6CA8, identical sequence into r29.

### (Q3) Each of GetSize / CreateInstance / Process contains deferred-command records whose stride or handler-return must be converted to a host sizeof.

**Actual:** NONE OF THE THREE TOUCHES THE DEFERRED RING -- no reference to System::mpDeferredRingBase (+0x20) or muDeferredRingCursor (+0x10B8), and none of them is a ring handler. Applying the house ring rule here would be the error: Process's `li r3, 1` / `li r3, 0` is the PlugIn stage BUFFER STATUS (1 = the src slot holds a valid frame; Mixer::ProcessInputPlugIns consumes it), and its Declick path is a plain r3 passthrough of Declick's status; CreateInstance's `li r3, 1` / `li r3, 0` is the descriptor create SUCCESS BOOL that PlugIn::CreateInstance tests with `clrlwi. r11, r3, 24` before running vt[0]+vt[3]; GetSize returns a byte size. Converting any of these to a host sizeof would break the mixer. The ring rule's real scope in this class is the SIBLING handlers, all of which do need it: ModifyStartTimeHandler `li r3, 0x18` (console {handler,self,f64,f32,pad} -> host 32), StopHandler `li r3, 8` (console {handler,self} -> host 16), and PlayHandler, which does not use a literal at all -- it ECHOES a u16 size stored inside the record (`lhz r3, 0x2C(r29)`), so on the host the PRODUCER (EventEvent's PlayCommand builder) must write the host record size into that field, and that field is another narrow store of a computed size.

**Evidence:** Full assembly scan of 0x82BA0220 / 0x82BA6C80 / 0x82BA0568: no +0x20 or +0x10B8 System access. Process returns: 0x82BA0594 `bl Declick` + 0x82BA0598 `b loc_82BA0C10` (r3 passthrough), 0x82BA0B50 `li r3, 0`, 0x82BA0C0C `li r3, 1`. CreateInstance returns 0x82BA6E14 `li r3, 0` / 0x82BA6E20 `li r3, 1`; tested at PlugIn::CreateInstance 0x82B6A874. Handlers: 0x82BA0454 `li r3, 0x18`, 0x82BA454C `li r3, 8`, 0x82BA44D0 `lhz r3, 0x2C(r29)`.

### (Q4) The stack-allocator scratch carve leaks on some exit path of Process.

**Actual:** IT DOES NOT -- I traced every exit and found no leak, so this is reported as a correction to the suspicion plus the pairing hazard that a host rewrite would introduce. The carve happens at exactly two sites (0x82BA07EC and 0x82BA0A1C), both of which do `saved = alloc->mpTop; alloc->mpTop = saved - align128(req->muScratchBytes)`. Every exit that can be reached AFTER a carve funnels through the restore block at 0x82BA0AFC. The three exits that bypass 0x82BA0AFC all occur strictly BEFORE the first carve: the Declick tail (0x82BA0594), the format-handshake publish (0x82BA0BD0 -> 0x82BA0C0C, reached from 0x82BA0670/0x82BA0680), and the future-start zero-fill publish (0x82BA07E4 -> 0x82BA0C0C, reached from 0x82BA0738 when the fill count is non-zero -- the carve at 0x82BA07EC is on the OTHER side of that branch). The WaitForStartTime-unavailable exit (0x82BA0728) also precedes the carve. THE REAL HAZARD: the restore is not paired to a carve flag -- it is gated on `mpCurrentDecoder != 0` (r21, the new top, is only a secondary non-zero test), so the invariant 'carved => mpCurrentDecoder non-null' is load-bearing and undocumented. Any host edit that clears mpCurrentDecoder early, or adds an early return between 0x82BA07EC and 0x82BA0AFC, leaks the carve permanently -- and the mid-function restore-then-re-carve at 0x82BA09B4/0x82BA0A1C reuses the SAME saved-top slot, so a stale carve flag would double-restore. Host form: model {u8* mpSavedTop; bool mbCarved} as one pair, clear mbCarved inside every restore, and keep mpTop typed as u8* (StackAllocator::mpTop is a pointer; r21/r22 must not be ints).

**Evidence:** Carves: 0x82BA07EC..0x82BA0810 and 0x82BA0A1C..0x82BA0A40 (`lwz r10, 4(r31)` -> `lwz r11, 0(r10)` = System::mpObjectTable -> `lwz r10, 0xC(r11)` = StackAllocator::mpTop, `mr r22, r10` / `mr r21, r9` / `stw r9, 0xC(r11)`). Restores: 0x82BA09B4..0x82BA09CC (guarded on `lwz r11, 0x19C(r31)` non-zero) and 0x82BA0AFC..0x82BA0B1C (guarded on 0x19C non-zero AND `cmplwi cr6, r21, 0`). Bypassing exits: 0x82BA0598, 0x82BA072C, 0x82BA07E4, 0x82BA0C08 fallthrough. Mixer.h StackAllocator::mpTop is `u8*` at +0x0C.

### (prior dossier, section 4 'Future start' row) A nearer future start 'zero-fills that many frames in the dst descriptor'.

**Actual:** The fill count is CAPPED at mSamplesRequested (+0x1C0) before use -- `if (count >= mSamplesRequested) count = mSamplesRequested`, an UNSIGNED compare, and the clamped value is what is both memset and published to Mixer::mNumSamples. Omitting the cap lets a far-future start zero more than the frame quantum and publish a sample count larger than the buffer. (Independently re-verified here; this is the review's known error (b) in that dossier, restated with the compare's signedness so the host does not turn it into a signed min.) The same unsigned-vs-signed distinction runs the other way three instructions later on the decode path, where the min against +0x1C0 is a SIGNED `cmpw`.

**Evidence:** Process 0x82BA073C `lhz r11, 0x1C0(r31)` / 0x82BA0740 `cmplw cr6, r26, r11` / 0x82BA0744 `blt cr6, loc_82BA074C` / 0x82BA0748 `mr r26, r11`; the clamped r26 then drives 0x82BA0754 `slwi r25, r26, 2` (XMemSet byte count) and 0x82BA07BC `stwx r26, r24, r9` (mixer +0x30020). Decode-path counterpart: 0x82BA0880..0x82BA0894 uses `cmpw` (signed).

### Verifier notes

Scope: independently decoded GetSize @0x82BA0220, CreateInstance @0x82BA6C80, Process @0x82BA0568 from the `assembly` fields only, and corroborated the record layouts they index into against GetFeedSlot @0x82BA0380, FeedCleanup @0x82BA0268, SubmitChunk @0x82BA4570, StartRequest @0x82BA6438, StopHandler @0x82BA44E0, ModifyStartTimeHandler @0x82BA03D0, PlugIn::CreateInstance @0x82B6A818, and a hand decode of the exporter-gap DecoderRegistry::DecoderFactory @0x82B6C778 (file 0x00B6F778). Rodata verified: flt_82001CC0 = 0.0f, dbl_82001CA8 = 0.0, flt_820AA808 = 48000.0f.

ANSWERS IN BRIEF.
(1) Pointer-bearing console sizes/offsets, none transliterable: 0x1D8/0x1DF (fixed extent), 0x30 (RequestInternal, Decoder* at +0x08), 0x10 and base 0x5C (feed descriptor, TWO pointers at +0x00/+0x04), 0x50 and the `+4` sub-base (RequestExternal, five pointers), 0x14 in Process (DecoderRequest, mpFedData at +0x00), the VoiceStageConfig `+8` byte read, and the carve amount itself (RequestInternal+0x28 <- Decoder+0x20 = a whole decoder-instance size). The Mixer offsets 0x30000/0x3000C/0x30010/0x30018/0x30020/0x30024/0x3002C match Mixer.h field-for-field, but 0x3000C/0x30010 are the SampleBuffer* ping-pong pair -- the swap at 0x82BA08F8..0x82BA0910 must be `std::swap(mixer.mpSrcBuffer, mixer.mpDstBuffer)` by name, never a raw word swap.
(2) Narrow stores of computed values: +0x1C2 and +0x1C4 (u16 relative offsets) are SAFE -- host values land near 0x2A0, decades under 65535, and both fields must keep their u16 width. +0x1C0 (u16 sample count, capped at 256 by the caller) safe. +0x1C6 (u8 channels, <= SampleBuffer's 64-slot capacity) safe. THE TWO THAT CAN OVERFLOW: +0x1CA (u8 request count, truncating a 32-bit n that three other consumers use wide -- console-side, preserve it) and RequestInternal+0x28 (u16 truncating a 32-bit decoder-instance size that GROWS on x64 -- the only field where host widening creates an overflow the console did not have).
(3) Zero deferred-command records in the three functions; the house ring rule must NOT be applied to any of their returns. The rule's real targets are the siblings (0x18 -> 32, 8 -> 16, and PlayHandler's in-record u16 size that the producer must fill with the host sizeof).
(4) No leak. Every carve is restored; the three exits that bypass the restore block all precede the first carve. The defect is structural, not a live leak: the carve is paired to `mpCurrentDecoder != 0` rather than to a carve flag.

NaN/unordered polarity: my three functions contain only `fcmpu` + `bne` (0x82BA066C, format change) and `fcmpu` + `beq` (0x82BA0708, start-time == 0.0). Both transliterate naturally in C++ -- `!=` is true and `==` is false for unordered, matching the taken/not-taken paths -- so no negated predicate is required here. The house rule DOES bite one address away: ModifyStartTimeHandler 0x82BA0444 `fcmpu cr6, f0, f13` + 0x82BA0448 `ble cr6, skip` takes the STORE path on NaN, so the faithful host form is `if (!(startTime <= systemTime)) store;`, not `if (startTime > systemTime) store;`. Flagging it because a port of that handler will land in the same TU.

Adjacent finding worth acting on: Decoder.h lines 57-58, 62-63 and 153 still assert DecoderRequest is pointer-free with a surviving 20-byte stride, contradicting the same header's own `const void *mpFedData` member and the correction already written into Decoder.cpp:44-66. That comment is the most likely source of a wrong Process port and should be corrected when the SndPlayer1 TU lands (no file was edited -- this task was read-only).

Not verified / out of scope: RequestInternal +0x1C/+0x20/+0x24 are read as plain s32 by Process and no pointer use appears, so I take them as scalars but did not attest their producers; feed descriptor +0x0F is never touched by any body I read; and the host magnitude of the Decoder+0x20 total is BLOCKED because DecoderFactory is not bodied on the host yet.

---

# Part 2 -- the decoded bodies

## Cluster: rw::audio::core::SndPlayer1 — host layout + construction (GetSize @0x82BA0220, CreateInstance @0x82BA6C80, PlugIn::Initialize&lt;SndPlayer1&gt; @0x82B9D368)

### `rw::audio::core::SndPlayer1::GetSize` @ `0x82BA0220`  [DECODED]

**Signature**

```cpp
// Vendor SDK spelling (Feb-2007 rwaudiocore 2.11.00 rw/audio/core/plugins/sndplayer1.h:284):
//   private: static unsigned int SndPlayer1::GetSize(PlugInConfig *pPlugInConfig);
// Our committed spelling of that record is VoiceStageConfig (Voice.h), so in this TU:
static u32 GetSize(const VoiceStageConfig *apConfig);

// DISPATCH SITE (authoritative): Voice::CreateInstance @0x82B6EC98..0x82B6ECA8
//   r31 = the config ENTRY (12-byte stride, `addi r31,r31,0xC` per stage)
//   lwz r11,4(r31)   -> config->mpDesc      (PlugInDescRunTime*)
//   mr  r3,r31       -> r3 = &config[i]     <-- the WHOLE entry, not its context word
//   lwz r11,4(r11)   -> desc->pGetSize
//   bctrl
// i.e. the slot is cast to  u32 (*)(const VoiceStageConfig *)  exactly as
// PlugInDescRunTime::pGetSize is documented in PlugIn.h.
```

**Behaviour**

Twelve instructions, leaf, no branches taken on the common path. Register-by-register:

0x82BA0220 `lwz r11, 0(r3)`      -- r11 = apConfig->mpContext (VoiceStageConfig +0x00). The
                                    splice literals put a `SndPlayer1::ConstructorParams *`
                                    here (vendor: `struct ConstructorParams { float maxRequests; }`).
0x82BA0224 `cmplwi r11, 0`
0x82BA0228 `beq  loc_82BA0244`   -- null context => the default.
0x82BA022C `addi r10, r1, back_chain`
0x82BA0230 `lfs  f0, 0(r11)`     -- f0 = ctorParams->maxRequests (the FIRST float only).
0x82BA0234 `fctidz f0, f0`       -- convert-to-int64, ROUND TOWARD ZERO.
0x82BA0238 `stfiwx f0, 0, r10`   -- store the LOW 32 bits of that int64 to the scratch word.
0x82BA023C `lwz  r11, back_chain(r1)`  -- r11 = n (the truncated request count).
0x82BA0240 `b    loc_82BA0248`
0x82BA0244 `li   r11, 1`         -- n = 1 when there are no constructor params.
0x82BA0248 `lbz  r9, 8(r3)`      -- c = apConfig->mFlagAndField8 low byte (the stage's
                                    channel/init byte; PlugIn::CreateInstance copies the SAME
                                    byte into PlugIn::mOutputChannels @0x82B6A85C..0x82B6A860).
0x82BA024C `mulli r10, r11, 0x30`-- r10 = 0x30 * n           (RequestInternal extent * count)
0x82BA0250 `rotlwi r11, r9, 2`   -- r11 = 4 * c              (c <= 255, so no wrap: this is a shift)
0x82BA0254 `addi  r11, r11, 0x1DF`
0x82BA0258 `clrrwi r11, r11, 3`  -- r11 = (4c + 0x1D8 + 7) & ~7 == align_up(0x1D8 + 4c, 8)
0x82BA025C `add   r3, r11, r10`
0x82BA0260 `blr`                 -- return align_up(0x1D8 + 4*c, 8) + 0x30*n

So the console formula is exactly
    declickOffset = 0x1D8
    requestOffset = align_up(0x1D8 + 4*channels, 8)
    size          = requestOffset + 0x30*maxRequests
and it is COUPLED to CreateInstance, which recomputes the same two offsets from `this`
(`addi r11,r31,0x1DF ; clrrwi r11,r11,3 ; subf r11,r31,r11`) and stores them into the two
16-bit fields mDeclickBufferOffset (+0x1C2) / mRequestInternalOffset (+0x1C4). The two agree
only because Voice::CreateInstance places every stage on a 16-byte boundary
(`addi r11,r28,0xF ; clrrwi r11,r11,4 ; add r28,r3,r11` @0x82B6ECAC..0x82B6ECBC) inside a
block that System::New2<Voice> allocates with align 16 (`li r7,0x10` @0x82B6ECC8).

Why 0x1D8: the console fixed header runs +0x00..+0x1D0 inclusive (mbTimerAdded is the last
byte CreateInstance writes), i.e. extent 0x1D1, padded up to the class's 8-byte alignment
(the f64 attribute slots at +0x30/+0x38 and RequestInternal's leading `double startTime`)
=> 0x1D8. It is therefore `align_up(sizeof(SndPlayer1), 8)` written as a literal.

There is NO validation anywhere: no NaN check, no sign check, no range clamp. GetSize sizes
the object from the full 32-bit `n`, while CreateInstance stores only its LOW BYTE into
mMaxRequests (+0x1CA). The two committed splice configs pass &1.0f and &2.0f, which are safe.

**Constants**

No rodata is referenced by GetSize itself -- every operand is an immediate
(0x30, 0x1DF, the clrrwi/rlwinm masks) or comes from the config record.

Mask decode (needed to trust the formula):
  `clrrwi r11,r11,3`        == rlwinm r11,r11,0,0,28  -> mask bits 0..28 (BE) = 0xFFFFFFF8 (align down 8)
  `rlwinm r10,r10,0,16,28`  (CreateInstance's twin) -> mask bits 16..28 (BE) = 0x0000FFF8
                               i.e. align-down-8 AND truncate-to-16-bits in one op, because
                               the result is immediately `sth`-ed into mRequestInternalOffset.
  `rotlwi r9,r10,2`         == r10 << 2 for a byte-sized r10 (no wrap possible).

Related rodata verified for the sibling functions in this cluster (file_off = 0x3000 + vaddr - 0x82000000,
big-endian, read from IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex):
  flt_82001CC0  @0x82001CC0  file_off 0x00004CC0  `00 00 00 00`               -> 0.0f
  dbl_82001CA8  @0x82001CA8  file_off 0x00004CA8  `00 00 00 00 00 00 00 00`   -> 0.0
  flt_820AA808  @0x820AA808  file_off 0x000AD808  `47 3B 80 00`               -> 48000.0f

**Host hazards**

1. X64 LAYOUT TRAP (the whole point of this function): BOTH literals are console extents
   containing 32-bit pointers. 0x1D8 = the pointer-dense fixed header (30 pointers listed in
   the sketch); 0x30 = sizeof(RequestInternal), whose +0x08 is `Decoder *pDecoder`. Returning
   the console formula on x64 under-allocates the object by ~200 bytes and puts the declick
   array and the request ring INSIDE the fixed header. Host expression: sizeof(SndPlayer1)
   and sizeof(RequestInternal), through the single ComputeLayout helper.

2. COUPLING TRAP: GetSize derives the declick offset as the CONSTANT 0x1D8 while
   CreateInstance derives it from the live `this` (`align_up(this + 0x1D8, 8) - this`). They
   agree only because Voice::CreateInstance 16-aligns every stage carve. On the host the
   helper must be address-independent (sizeof-based) and must assert
   alignof(SndPlayer1) <= 16, or an under-aligned carve silently shifts the request ring out
   of the allocation.

3. GetSize's channel byte comes from the CONFIG (`lbz 8(r3)`), CreateInstance's from the
   already-populated PlugIn::mOutputChannels (`lbz 0x21(r31)`). PlugIn::CreateInstance copies
   config+8 into mOutputChannels *before* dispatching pCreateInstance (@0x82B6A85C..0x82B6A860),
   so they are the same byte -- but the host must not "tidy" either site into reading the
   other source, or a future config change desynchronises size from layout.

4. NO VALIDATION, and an asymmetric truncation: the object is sized from the full 32-bit `n`
   but mMaxRequests (+0x1CA) receives only `n & 0xFF` (CreateInstance `stb r29,0x1CA`). A
   config of 256.0f allocates 256 records and then sets mMaxRequests = 0, which makes
   PlayHandler's ring wrap (`+0x1C7` vs `+0x1CA`) and StopHandler's loop degenerate. Faithful
   = reproduce it; do NOT add a clamp. The committed configs are {&1.0f,'SnP1',1} and
   {&2.0f,'SnP1',2} (the matching numbers are coincidence: the float is maxRequests, the
   config byte is channels).

5. NaN/negative: `fctidz` on a NaN yields the PowerPC "invalid" result (0x8000000000000000),
   whose low word `stfiwx` keeps is 0 -- so a NaN config would size the object with zero
   requests. A negative float yields a huge unsigned n. There is no fcmpu in this body at all,
   so there is no branch polarity to preserve here; do not invent a guard.

6. Console leaf-frame artifact: `addi r10, r1, back_chain` + `stfiwx` writes the 4-byte
   scratch through r1 with no stack frame established (GetSize has no `stwu`). It is a
   frameless leaf's scratch word, not a member store; the host uses an ordinary local.

7. Do NOT copy any number from progress/scratch_dossiers/streammod_gainarray_decode_codex.md.
   SndPlayer1_CgsStreamMod is a 2.11-era FORK: its RequestInternal stride is 0x20, its
   RequestExternal 0x88, its feed record 0x0C with NO pointers, and its fixed extent 0x188.
   The vendor SndPlayer1 decoded here is 0x30 / 0x50 / 0x10 (two pointers) / 0x1D8. Only the
   SHAPE (computed layout + two stored 16-bit offsets + separate external-request allocation)
   is shared.

**Implementation sketch**

```cpp
// =====================================================================================
// The ONE host layout helper. Both GetSize and CreateInstance go through it; nothing else
// may recompute an offset. (Vendor header proof that the two 16-bit fields are the real
// runtime mechanism: rwaudiocore 2.11.00 sndplayer1.h declares
//   RequestInternal *GetRequestInternal(unsigned index)
//     { return &reinterpret_cast<RequestInternal*>((uintptr_t)this + mRequestInternalOffset)[index]; }
//   float *GetDeclickBuffer()
//     { return reinterpret_cast<float*>((uintptr_t)this + mDeclickBufferOffset); }
// -- offset-relative, so the accessors are width-agnostic once the STORED offsets are host
// values. Only the two literals that PRODUCE those offsets have to change.)
// =====================================================================================
struct SndPlayer1Layout
{
    u16 muDeclickBufferOffset;   // -> mDeclickBufferOffset  (+0x1C2); console 0x1D8
    u16 muRequestInternalOffset; // -> mRequestInternalOffset(+0x1C4); console align_up(0x1D8+4c,8)
    u32 muTotalSize;             // GetSize's return;        console requestOffset + 0x30*n
};

static inline u32 SnP1AlignUp(u32 auValue, u32 auAlign)
{
    return (auValue + (auAlign - 1u)) & ~(auAlign - 1u);
}

// X64 LAYOUT TRAP -- the two console literals in this formula are BOTH pointer-bearing
// console extents and NEITHER survives:
//   0x1D8 is the fixed-header extent. It contains 30 32-bit pointers: the vptr, PlugIn's
//         mpSystem / mpVoice / mpAttribute / mpPlugInDescRunTime, TimerHandle's four
//         (mpItemHandleNode / mpCallback / mpContext / mpName), mpRequestExternal, the 20
//         feed records' pChunkInfo + pRwCoreStream (40 pointers on their own), mpLoadedDecoder
//         and mpRequestHandle.
//   0x30  is sizeof(RequestInternal) on the console and contains Decoder *pDecoder at +0x08.
// Host expressions: sizeof(SndPlayer1) and sizeof(SndPlayer1::RequestInternal).
SndPlayer1Layout SndPlayer1::ComputeLayout(u8 au8Channels, u32 auMaxRequests)
{
    // console: `addi r11,this,0x1DF ; clrrwi r11,r11,3 ; subf r11,this,r11`
    // == align_up(sizeof-of-the-fixed-header, 8). The host object's own trailing padding
    // to alignof(SndPlayer1) is already inside sizeof(), so the align_up is a no-op that we
    // keep for shape (and because it documents the console's 8).
    const u32 uDeclick =
        SnP1AlignUp(static_cast<u32>(sizeof(SndPlayer1)),
                    static_cast<u32>(alignof(SndPlayer1)));

    // console: `rotlwi r10,c,2 ; add ; addi +7 ; rlwinm 0,16,28` == align_up(+4c, 8).
    // The console 8 IS alignof(RequestInternal) (its leading `double startTime`); on the
    // host it stays alignof(RequestInternal) for exactly the same reason.
    const u32 uRequest =
        SnP1AlignUp(uDeclick + static_cast<u32>(sizeof(f32)) * au8Channels,
                    static_cast<u32>(alignof(RequestInternal)));

    SndPlayer1Layout layout;
    layout.muDeclickBufferOffset   = static_cast<u16>(uDeclick);
    layout.muRequestInternalOffset = static_cast<u16>(uRequest);
    layout.muTotalSize =
        uRequest + static_cast<u32>(sizeof(RequestInternal)) * auMaxRequests;

    // The two offsets are stored in 16-bit fields (mDeclickBufferOffset /
    // mRequestInternalOffset) and the Voice's total carve is likewise bookkept in 32 bits;
    // the host widening pushes uDeclick from 0x1D8 to ~0x2A0, still far inside u16, but the
    // truncation above must be guarded rather than assumed.
    RW_ASSERT(uRequest <= 0xFFFFu);
    RW_ASSERT(alignof(SndPlayer1) >= alignof(RequestInternal)); // the carve is 16-aligned
    return layout;
}

// -------------------------------------------------------------------------------------
// SndPlayer1::GetSize @0x82BA0220 -- the descriptor's pGetSize hook (the stage-carve stride).
//
// COMPUTED, not a constant: this is the one rwaudio plug-in whose instance size depends on
// its stage config, so the RawPuller2/Send/SinePlayer/Dac "return host sizeof" convention is
// NOT enough here -- the two variable tails (the per-channel declick array and the
// RequestInternal[] ring) live inside the SAME allocation.
// -------------------------------------------------------------------------------------
u32 SndPlayer1::GetSize(const VoiceStageConfig *apConfig)
{
    // lwz r11,0(r3) / cmplwi / beq -> li r11,1
    // fctidz + stfiwx + lwz: truncate TOWARD ZERO to int64 then keep the low 32 bits.
    // Faithful: no NaN, sign or range check exists in the body (see hazards).
    u32 uMaxRequests = 1u;
    if (apConfig->mpContext != 0)
    {
        const ConstructorParams *pParams =
            static_cast<const ConstructorParams *>(apConfig->mpContext);
        uMaxRequests = static_cast<u32>(static_cast<s64>(pParams->maxRequests));
    }

    // lbz r9,8(r3) -- the same byte PlugIn::CreateInstance copies into mOutputChannels.
    const u8 u8Channels = static_cast<u8>(apConfig->mFlagAndField8);

    return ComputeLayout(u8Channels, uMaxRequests).muTotalSize;
}
```

### `rw::audio::core::SndPlayer1::CreateInstance` @ `0x82BA6C80`  [DECODED]

**Signature**

```cpp
// Vendor SDK spelling (rwaudiocore 2.11.00 sndplayer1.h:285):
//   private: static bool SndPlayer1::CreateInstance(PlugIn *pPlugIn, void *pConstructorParams);
// Host TU (typed, cast at the descriptor slot exactly where the console's generic dispatch
// casts -- the PlugInDescRunTime::pCreateInstance convention documented in PlugIn.h):
static int CreateInstance(SndPlayer1 *self, ConstructorParams *apConstructorParams);

// DISPATCH SITE (authoritative): PlugIn::CreateInstance @0x82B6A864..0x82B6A870
//   lwz r4, 0(r6)   -> r4 = apConfig->mpContext   (the ConstructorParams*, may be NULL)
//   lwz r11,8(r5)   -> desc->pCreateInstance
//   bctrl           -> int (*)(PlugIn *self, void *pConstructorParams)
//   clrlwi. r11,r3,24 ; bne success   -- only the LOW BYTE of the return is tested,
//                                        non-zero == success.
// On failure the generic caller runs vt[0](self) then vt[3](self, 0) and returns null
// (already modelled in the committed PlugIn.cpp as `self->~PlugIn(); self->Destroy(0);`).
```

**Behaviour**

r31 = self, r29 = the request count, r30 = the shared zero, r28 = "SndPlayer".
Every store below was read row-by-row off the assembly; the ORDER is the asm's order.

PHASE 1 -- decode the constructor parameter (0x82BA6C8C..0x82BA6CB4)
  `mr r31,r3`; `cmplwi cr6,r4,0`; if r4 == 0 -> `li r29,1`, else
  `lfs f0,0(r4)` / `fctidz` / `stfiwx` / `lwz r29` -- identical truncation to GetSize's.
  r29 = n = trunc_toward_zero(apConstructorParams->maxRequests), low 32 bits.

PHASE 2 -- construct (0x82BA6CB4..0x82BA6CBC)
  `li r4,0x28` ; `mr r3,r31` ; `bl PlugIn::Initialize<SndPlayer1>`
  -- installs the SnP1 vtable, runs TimerHandle's ctor on self+0x40, and bases the attribute
     table at self+0x28. See the third function in this cluster.

PHASE 3 -- compute + publish the layout (0x82BA6CC0..0x82BA6D10)
  `lbz  r9, 0x21(r31)`            c  = PlugIn::mOutputChannels (set by the generic caller)
  `addi r11, r31, 0x1DF`
  `clrrwi r11, r11, 3`            r11 = align_up(this + 0x1D8, 8)
  `rotlwi r10, r9, 2`             r10 = 4*c
  `li   r30, 0`                   the shared zero register for the whole body
  `add  r10, r10, r11`
  `subf r11, r31, r11`            r11 = declickOffset (0x1D8 for a 16-aligned instance)
  `addi r10, r10, 7`
  `mulli r9, r29, 0x50`           the EXTERNAL-request allocation size, 0x50 * n
  `stb  r30, 0x1D0(r31)`          [1] mbTimerAdded = 0  (BEFORE the fallible work)
  `sth  r11, 0x1C2(r31)`          [2] mDeclickBufferOffset  = declickOffset
  `rlwinm r10,r10,0,16,28`        align-down-8 AND truncate-to-u16 in one op
  `subf r10, r31, r10`
  `addi r4, r9, 4`                alloc size = 0x50*n + 4
  `sth  r10, 0x1C4(r31)`          [3] mRequestInternalOffset = align_up(declick+4c, 8)
  and the alloc arguments: r3 = self->mpSystem (`lwz r3,4(r31)`), r5 = the name string,
  r6 = 0x10 (align), r7 = 0 (allocator override).

PHASE 4 -- the external-request allocation (0x82BA6D14..0x82BA6D34)
  `bl System::Alloc` ; `stw r3, 0x1B0(r31)`   [4] mpRequestHandle = the allocation BASE
  `beq -> 0x82BA6E14` : allocation failed => `li r3,0` and RETURN 0 (nothing is undone; the
                        generic caller's vt[0]/vt[3] path does the teardown, and ReleaseEvent
                        @0x82BA41A8 null-checks +0x1B0 before freeing).
  `addi r11, r3, 4`   ; `stb r29, 0x1CA(r31)` [5] mMaxRequests = (u8)n   <-- LOW BYTE ONLY
                      ; `stw r11, 0x58(r31)`  [6] mpRequestExternal = base + 4

PHASE 5 -- request-ring state (0x82BA6D38..0x82BA6D54), skipped entirely when n == 0
  for (i = 0; i < n; ++i)
      *(u8 *)(this + mRequestInternalOffset + 0x30*i + 0x2A) = 0;   [7] state = REQUESTSTATE_FREE
  The loop re-loads `lhz 0x1C4(r31)` every iteration and destroys r29.
  NOTHING ELSE in RequestInternal is initialised -- not startTime, not pDecoder.

PHASE 6 -- the flat field seeding (0x82BA6D58..0x82BA6DCC), asm order preserved
  [8]  `stb r10,0x1C6`   mMaxChannels = PlugIn::mOutputChannels (re-loaded from +0x21)
  [9]  `stfs f0,0x28`    mAttribute[0] (ATTRIBUTE_GETCURRENTREQUEST) = 0.0f   (flt_82001CC0)
  [10] `stfd f13,0x38`   mAttribute[2] (ATTRIBUTE_GETSAMPLELENGTH)   = 0.0    (dbl_82001CA8, f64!)
  [11] `stfd f13,0x30`   mAttribute[1] (ATTRIBUTE_GETSAMPLEPOSITION) = 0.0    (f64!)
  [12] `stfs f0,0(r9)`   *(f32 *)mpRequestHandle = 0.0f   (the running handle counter that
                          EventEvent increments and wraps at MAX_REQUEST_HANDLE_VALUE)
  [13] `stb r30,0x1C9`   mCurrentRequest        = 0
  [14] `stfs f0,0x1B4`   mLastRequestHandleProcessed = 0.0f
  [15] `stb r30,0x1C8`   mNextRequestToFree     = 0
  [16] `stb r30,0x1C7`   mNextFreeRequest       = 0
  [17] `stfs f0,0x1B8`   mLastRequestHandleSuccessfullyProcessed = 0.0f
  [18] `stfs f0,0x1A0`   mCurrentRequestHandle  = 0.0f
  [19] `stw r30,0x1A8`   mCurrentRequestSamplesPlayed = 0
  [20] `stfs f13,0x1A4`  mCurrentRequestSampleRate = 48000.0f  (flt_820AA808)
  [21] `stw r30,0x1AC`   mCurrentRequestNumSamples = 0
  [22] `stfs f13,0x1BC`  mPreviousSampleRate    = 48000.0f
  [23] `stb r30,0x1CC`   mNumDeclickSamples     = 0
  [24] `stb r30,0x1CB`   mDcOffsetsGathered     = 0
  [25] `stb r30,0x1CD`   mNextFeedSlotToFill    = 0
  [26] `stb r30,0x1CE`   mNextFeedSlotToFree    = 0
  [27] `stb r30,0x1CF`   mNextFeedSlotToCleanup = 0   <-- NOT an unknown byte; see hazards

PHASE 7 -- the feed ring (0x82BA6DA4, 0x82BA6DD0..0x82BA6DE0)
  r11 = this + 0x5C ; r10 = 0x14 (20)
  do { `stb r30, 0xD(r11)`  feed[i].feedState  = FEEDSTATE_FREE
       `stw r30, 0(r11)`    feed[i].pChunkInfo = NULL
       r11 += 0x10 ; } while (--r10);
  This proves the record stride (0x10) and the count (20 == the vendor header's
  MAX_DECODERFEEDS) independently of any other body, and 0x5C + 20*0x10 == 0x19C lands
  exactly on mpLoadedDecoder. feed[i].pRwCoreStream / chunkSamplesPlayed /
  decoderRequestHandle / requestIndex are NOT initialised.

PHASE 8 -- timer registration (0x82BA6DE4..0x82BA6E24)
  `lwz r11,4(r31)`  the System
  r3 = r11 + 0x60   -> &System::mTimerManager
  r4 = r31 + 0x40   -> &self->mTimerClient
  r5 = &SndPlayer1::RwacTimerClient (0x82BA6980)
  r6 = r31          -> context = self
  r7 = "SndPlayer"
  r8 = 1            -> collectionIndex
  r9 = 1            -> visibility
  `bl TimerManager::AddTimer` ; `clrlwi. r11,r3,24`
    non-zero (failure) -> `li r3,0` ; return 0     (the allocation is NOT freed here --
                                                    ReleaseEvent frees it on the teardown path)
    zero     (success) -> `li r3,1` ; `stb 1,0x1D0(r31)` ; return 1
  mbTimerAdded (+0x1D0) is therefore the exact byte ReleaseEvent tests (`cmplwi r11,1`
  @0x82BA4190) before calling System::RemoveTimer.

NEVER TOUCHED BY CreateInstance: mpLoadedDecoder (+0x19C) -- Process zeroes it on entry
(`stw r15,0x19C(r31)` @0x82BA05AC); mSamplesRequested (+0x1C0) -- PreProcess overwrites the
halfword every frame; the declick f32[] tail; every RequestInternal field except `state`;
and the ENTIRE RequestExternal[] array (PlayHandler seeds a record when it claims it).

**Constants**

Every rodata operand, recomputed with file_off = 0x3000 + vaddr - 0x82000000 and read
big-endian out of IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex:

| symbol / site | vaddr | file_off | raw BE bytes | decoded |
|---|---|---|---|---|
| flt_82001CC0 (f0; 0x82BA6D64) | 0x82001CC0 | 0x00004CC0 | `00 00 00 00` | 0.0f |
| dbl_82001CA8 (f13; 0x82BA6D78) | 0x82001CA8 | 0x00004CA8 | `00 00 00 00 00 00 00 00` | 0.0 |
| flt_820AA808 (f13; 0x82BA6D98) | 0x820AA808 | 0x000AD808 | `47 3B 80 00` | 48000.0f |
| aSndplayer_0 (r28; 0x82BA6CC0/0x82BA6CCC) | 0x821745CC | 0x001775CC | `53 6E 64 50 6C 61 79 65 72 00` | "SndPlayer" |
| alloc name (r5; 0x82BA6CFC, = r28 + (0x8217457C+0x1C - 0x821745CC)) | 0x82174598 | 0x00177598 | `53 6E 64 50 6C 61 79 65 72 31 20 52 65 71 75 65 73 74 48 61 6E 64 6C 65 ...` | "SndPlayer1 RequestHandle and RequestExternal array" |
| SndPlayer1 vtable (installed by Initialize) | 0x8217F344 | 0x00182344 | `82 BA 41 78 82 BA 5C 48 82 BD D2 D0 82 B9 EA F8` | [0]=0x82BA4178 ReleaseEvent, [1]=0x82BA5C48 EventEvent, [2]=0x82BDD2D0 GetPpuTicksEvent, [3]=0x82B9EAF8 `vector deleting destructor' |
| next table (proves SnP1's ends at 4) | 0x8217F354 | 0x00182354 | `82 B9 D0 A8 82 BA 0F 80 82 B9 68 40 82 B9 EB 58` | VuMeter's table -- slot [1] is VuMeter::EventEvent @0x82BA0F80 (dossier-named), installed by the ADJACENT PlugIn::Initialize<VuMeter> @0x82B9D3EC |
| RwacTimerClient (r5 of AddTimer) | 0x82BA6980 | -- | -- | `static void RwacTimerClient(void *pContext, float timeToNextCall)` (vendor sig, sndplayer1.h:131) |

Adjacent, for the decoder LUT the report already tabulated (rodata block just before the
alloc-name string): 0x82174578 file_off 0x00177578 =
`58 61 73 30 45 4C 33 30 50 36 42 30 45 58 6D 30 58 61 73 31 45 4C 33 31 4C 33 32 50 4C 33 32 53`
-> 'Xas0','EL30','P6B0','EXm0','Xas1','EL31','L32P','L32S' -- eight guids, then the alloc name
at 0x82174598 with NO terminator gap, which is why StartRequest's unbounded `lwzx` past
index 7 reads string bytes.

Immediates worth naming rather than transliterating: 0x28 (attribute base offset -> host
offsetof), 0x1DF/0x30/0x50/0x10/0x14 (layout literals -> host sizeofs / MAX_DECODERFEEDS),
0x60 (System -> TimerManager, already a named member), 0x40 (this -> mTimerClient,
already a named member).

**Host hazards**

1. THE `base + 4` ALIGNMENT TRAP (the deliverable's named risk). The console allocates
   `0x50*n + 4` and sets mpRequestExternal = base + 4, so RequestExternal[i].streamFileOffset
   -- a `double` -- lands at 4 mod 8 for every even i. PowerPC fixes up misaligned lfd/stfd in
   hardware, so the console never notices. On x64 the host RequestExternal is 8-aligned, so
   `base + 4` is not merely slow, it is arithmetically wrong (it would offset every field by
   4). DO: keep ONE allocation (ReleaseEvent @0x82BA41A8..0x82BA41BC frees exactly the pointer
   at mpRequestHandle, and it is the only free), but carve it through a typed header struct
   whose array member is naturally aligned -- `RW_OFFSETOF(RequestBlock, maRequests) +
   sizeof(RequestExternal)*n`, align 16 -- with the f32 counter still at offset 0 so
   mpRequestHandle == the block base and the free stays valid. DO NOT write `+ 4`, and do not
   split it into two allocations (that would change what ReleaseEvent frees).

2. RECORD-STRIDE / EXTENT TRAPS, all four: 0x1D8 (fixed header, 30 pointers), 0x30
   (RequestInternal, one Decoder*), 0x50 (RequestExternal, SEVEN pointers), 0x10 (feed record,
   TWO pointers). None survives x64. Every one must become a host sizeof, and every array walk
   must go through GetRequestInternal()/mFeedDesc[]/mpRequestExternal[] rather than
   `base + stride*i`.

3. NARROWED-POINTER STORES inside the ctor loops: `stw r30, 0(r11)` clears feed[i].pChunkInfo
   with a 32-bit store, and `stw r3, 0x1B0` / `stw r11, 0x58` store pointers as words. On the
   host these are 8-byte members; write them by name (`= 0`, `= pBlock`, `= pBlock->maRequests`),
   never as word stores or memset spans.

4. mAttribute IS NOT THREE f32 SLOTS. CreateInstance writes slot 0 with `stfs` and slots 1/2
   with `stfd` (and RwacTimerClient @0x82BA69EC..0x82BA6A4C does the same), so slots 1 and 2
   hold f64 values spanning the whole 8-byte Attribute_t. A host that seeds them as three f32s
   leaves the low halves dirty and makes PlugIn::GetAttribute(1) return the high word of a
   double -- which is what the console does too, so preserve it: keep Attribute_t[3] for the
   indexed API and reach the two f64 slots through typed accessors.

5. THE `0x28` ARGUMENT TO Initialize IS A CONSOLE OFFSET. On x64 five pointers precede
   mAttribute[0], so the host attribute base is ~0x38. Pass the live delta (or offsetof); a
   literal 0x28 lands mpAttribute inside mpPlugInDescRunTime.

6. THE PRIOR REPORT'S +0x1CF ROW IS WRONG. progress/scratch_dossiers/sndplayer1_decode_codex.md
   calls +0x1CF an "ARTIST-only/unknown byte ... no semantic reader was found". It has a
   reader: FeedCleanup @0x82BA0268 loads it at 0x82BA0278/0x82BA028C/0x82BA034C and stores it
   at 0x82BA0364, walking it (mod 20) up to mNextFeedSlotToFree (+0x1CE) and releasing each
   FEEDSTATE_DECODECOMPLETED chunk. The ring is THREE cursors, not two:
     +0x1CD mNextFeedSlotToFill    -- GetFeedSlot @0x82BA0384 allocates and advances it
     +0x1CE mNextFeedSlotToFree    -- Process @0x82BA0A70 consumes and advances it
     +0x1CF mNextFeedSlotToCleanup -- FeedCleanup releases up to +0x1CE  [3.03 addition]
   The Feb-2007 vendor header (2.11.00) ends at mNextFeedSlotToFree, confirming +0x1CF and
   +0x1D0 are the 3.03 additions -- and that ProStreet's PDB, which names the timer flag at
   +0x1CF, is a DIFFERENT build. Keep ARTIST's extra byte.
   Related latent asymmetry, faithful, do not "fix": StopHandler @0x82BA4540..0x82BA4560 resets
   +0x1CD and +0x1CE but NOT +0x1CF.

7. FAILURE PATHS LEAK, FAITHFULLY. On alloc failure the body returns 0 with mpRequestHandle
   already stored (null, so ReleaseEvent's null check absorbs it). On AddTimer failure it
   returns 0 with the allocation LIVE and mbTimerAdded == 0; the generic caller then runs
   vt[0] (ReleaseEvent), which frees it and skips RemoveTimer. Do not add an unwind here --
   the teardown is genuinely the vtable's job, and adding a free would double-free.

8. mpLoadedDecoder (+0x19C) is deliberately left UNINITIALISED by CreateInstance -- the feed
   loop stops at +0x19B and nothing else writes it. Process zeroes it as its first act
   (`stw r15,0x19C(r31)` @0x82BA05AC) before any read. Faithful is to leave it; if house policy
   forbids an uninitialised pointer member, zero it with an explicitly marked PC-hygiene
   comment rather than silently.

9. n == 0 is representable (a config float in (-1, 1)): the request-state loop is skipped by
   `cmplwi cr6,r29,0 ; beq`, the allocation is still made (4 bytes), and mMaxRequests becomes 0.
   Reproduce the guard; do not turn it into a do/while.

10. NO fcmpu APPEARS IN THIS BODY, so there is no unordered/NaN branch polarity to preserve
    here. (The `fctidz` NaN behaviour noted under GetSize applies identically -- a NaN
    maxRequests yields n == 0.) Do not import a comparison from the Process/Declick paths.

11. This is NOT the deferred-ring surface: neither GetSize nor CreateInstance enqueues or
    handles a command, so no ring-cursor advance is involved. (For the neighbours that are:
    StopHandler @0x82BA454C returns the console literal 8 and PlayHandler @0x82BA44D0 returns
    the record's OWN stored 16-bit size field (`lhz r3,0x2C(r29)`) because PlayCommand is
    variable-length -- both must become host sizes, and the variable one must be recomputed by
    the producer with host sizeof + the path bytes.)

**Implementation sketch**

```cpp
// -------------------------------------------------------------------------------------
// SndPlayer1::CreateInstance @0x82BA6C80 -- the descriptor's pCreateInstance body.
//
// The generic PlugIn::CreateInstance @0x82B6A818 has ALREADY written the base fields
// (mpVoice / mpPlugInDescRunTime / mpSystem / mLatencyInSamples / mDecaySamples /
// mCpuTicks / mInputChannels / mOutputChannels) into `self` before this runs, and it
// hands us the config's context word as `apConstructorParams`. Returns 1 on success.
// -------------------------------------------------------------------------------------
int SndPlayer1::CreateInstance(SndPlayer1 *self, ConstructorParams *apConstructorParams)
{
    // ---- [phase 1] 0x82BA6C8C..0x82BA6CB4 -- the same truncation GetSize performs.
    u32 uMaxRequests = 1u;
    if (apConstructorParams != 0)
        uMaxRequests = static_cast<u32>(static_cast<s64>(apConstructorParams->maxRequests));

    // ---- [phase 2] 0x82BA6CBC -- `li r4,0x28 ; bl PlugIn::Initialize<SndPlayer1>`.
    // X64 TRAP: 0x28 is the CONSOLE byte offset of mAttribute[0]. The host offset is the
    // live delta to the member, because five pointers precede it.
    PlugIn::Initialize<SndPlayer1>(
        self,
        static_cast<u32>(reinterpret_cast<char *>(&self->mAttribute[0]) -
                         reinterpret_cast<char *>(self)));

    // ---- [phase 3] 0x82BA6CC0..0x82BA6D10 -- ONE layout helper, shared with GetSize.
    // Console: the offsets are derived from `this` (align_up(this+0x1D8,8) - this) and are
    // 0x1D8 / align_up(0x1D8+4c,8) only because the stage carve is 16-aligned. The host
    // form is address-independent.
    const SndPlayer1Layout layout =
        ComputeLayout(self->mOutputChannels, uMaxRequests);

    self->mbTimerAdded            = 0;                              // stb  0,   0x1D0
    self->mDeclickBufferOffset    = layout.muDeclickBufferOffset;   // sth  r11, 0x1C2
    self->mRequestInternalOffset  = layout.muRequestInternalOffset; // sth  r10, 0x1C4

    // ---- [phase 4] 0x82BA6D14..0x82BA6D34 -- the external-request block.
    // X64 TRAP (the console's `0x50*n + 4`, and the `base + 4` placement):
    //   * 0x50 is sizeof(RequestExternal) on the console and holds SEVEN 32-bit pointers
    //     (pSampleData, pStreamLoopFileName, pStreamPool, streamHandle, pRwCoreStream,
    //     pNextChunk, pLoopStartChunk) -> use sizeof(RequestExternal).
    //   * `+4` puts an array whose first member is a `double streamFileOffset` at only
    //     4-byte alignment (PowerPC absorbs the misaligned lfd/stfd in hardware; on x64 it
    //     is a latent misalignment and, with an 8-byte-aligned host RequestExternal, it is
    //     simply wrong arithmetic). Do NOT transliterate the 4: carve the counter through a
    //     typed, correctly-padded header so the array starts on alignof(RequestExternal),
    //     while keeping ONE allocation (ReleaseEvent @0x82BA41A8 frees exactly the pointer
    //     stored at mpRequestHandle, so the counter must stay at offset 0 of the block).
    struct RequestBlock
    {
        f32 mRequestHandleCounter;                      // console: base + 0x00
        // implicit pad to alignof(RequestExternal) -- console: none (the misaligned `+4`)
        RequestExternal maRequests[1];                  // console: base + 0x04
    };
    const u32 uBlockSize =
        static_cast<u32>(RW_OFFSETOF(RequestBlock, maRequests)) +
        static_cast<u32>(sizeof(RequestExternal)) * uMaxRequests;

    RequestBlock *pBlock = static_cast<RequestBlock *>(
        System::Alloc(self->mpSystemUseGetSystemAccessor, uBlockSize,
                      "SndPlayer1 RequestHandle and RequestExternal array",
                      /*align*/ 16, /*allocatorOverride*/ 0));

    self->mpRequestHandle = reinterpret_cast<f32 *>(pBlock); // stw r3, 0x1B0 (the BASE)
    if (pBlock == 0)
        return 0;                                            // beq -> li r3,0 ; return

    self->mMaxRequests     = static_cast<u8>(uMaxRequests);  // stb r29, 0x1CA -- LOW BYTE
    self->mpRequestExternal = pBlock->maRequests;            // stw r3+4, 0x58

    // ---- [phase 5] 0x82BA6D38..0x82BA6D54 -- only the state byte, only for i < n.
    for (u32 i = 0; i < uMaxRequests; ++i)
        self->GetRequestInternal(i)->state = REQUESTSTATE_FREE;

    // ---- [phase 6] 0x82BA6D58..0x82BA6DCC -- flat seeding, in the asm's store order.
    self->mMaxChannels    = self->mOutputChannels;   // stb  r10, 0x1C6
    self->mAttribute[0].mfValue = KF_ZERO;           // stfs f0,  0x28   (f32 slot)
    self->SetSampleLengthAttribute(0.0);             // stfd f13, 0x38   (f64 across slot 2)
    self->SetSamplePositionAttribute(0.0);           // stfd f13, 0x30   (f64 across slot 1)
    *self->mpRequestHandle = KF_ZERO;                // stfs f0,  0(r9)
    self->mCurrentRequest  = 0;                      // stb  r30, 0x1C9
    self->mLastRequestHandleProcessed = KF_ZERO;     // stfs f0,  0x1B4
    self->mNextRequestToFree = 0;                    // stb  r30, 0x1C8
    self->mNextFreeRequest   = 0;                    // stb  r30, 0x1C7
    self->mLastRequestHandleSuccessfullyProcessed = KF_ZERO; // stfs f0, 0x1B8
    self->mCurrentRequestHandle       = KF_ZERO;     // stfs f0,  0x1A0
    self->mCurrentRequestSamplesPlayed = 0;          // stw  r30, 0x1A8
    self->mCurrentRequestSampleRate   = KF_INTERNAL_RATE; // stfs f13, 0x1A4 (48000.0f)
    self->mCurrentRequestNumSamples   = 0;           // stw  r30, 0x1AC
    self->mPreviousSampleRate         = KF_INTERNAL_RATE; // stfs f13, 0x1BC
    self->mNumDeclickSamples     = 0;                // stb  r30, 0x1CC
    self->mDcOffsetsGathered     = 0;                // stb  r30, 0x1CB
    self->mNextFeedSlotToFill    = 0;                // stb  r30, 0x1CD
    self->mNextFeedSlotToFree    = 0;                // stb  r30, 0x1CE
    self->mNextFeedSlotToCleanup = 0;                // stb  r30, 0x1CF

    // ---- [phase 7] 0x82BA6DD0..0x82BA6DE0 -- 20 feed records, stride 0x10 on the console.
    // The console `stw r30,0(r11)` is a 32-bit store over pChunkInfo; on the host that
    // member is 8 bytes, so it must be a by-name null assignment, never a 4-byte clear.
    for (u32 i = 0; i < KU_MAX_DECODERFEEDS; ++i)   // MAX_DECODERFEEDS == 20 (vendor header)
    {
        self->mFeedDesc[i].feedState  = FEEDSTATE_FREE; // stb r30, 0xD(r11)
        self->mFeedDesc[i].pChunkInfo = 0;              // stw r30, 0(r11)
    }

    // ---- [phase 8] 0x82BA6DE4..0x82BA6E24 -- register the per-frame timer.
    // AddTimer returns 0 on success (only its low byte is tested).
    if (TimerManager::AddTimer(&self->mpSystemUseGetSystemAccessor->mTimerManager, // r3 = system + 0x60
                               &self->mTimerClient,                                // r4 = this + 0x40
                               &SndPlayer1::RwacTimerClient,                       // r5
                               self,                                              // r6 context
                               "SndPlayer",                                        // r7 name
                               /*collectionIndex*/ 1,                              // r8
                               /*visibility*/ 1) != 0)                             // r9
        return 0;                                    // li r3,0 (no unwind here -- faithful)

    self->mbTimerAdded = 1;                          // stb 1, 0x1D0
    return 1;
}

// =====================================================================================
// THE HOST STRUCT SHAPES this body and its siblings require. Names are the VENDOR names
// (Feb-2007 rwaudiocore 2.11.00 rw/audio/core/plugins/sndplayer1.h -- the same class,
// one minor version older); the ARTIST build (3.03-era) ADDS the fields marked [3.03].
// Console offsets in comments; the host declares natural widths and every body reads BY NAME.
// =====================================================================================
class SndPlayer1 : public PlugIn
{
public:
    struct ConstructorParams { f32 maxRequests; };            // vendor, verbatim

    enum Attribute { ATTRIBUTE_GETCURRENTREQUEST = 0, ATTRIBUTE_GETSAMPLEPOSITION = 1,
                     ATTRIBUTE_GETSAMPLELENGTH = 2, ATTRIBUTE_MAX = 3 };
    enum RequestState { REQUESTSTATE_FREE = 0, REQUESTSTATE_QUEUED = 1,
                        REQUESTSTATE_FEEDING = 2, REQUESTSTATE_FEEDCOMPLETE = 3,
                        REQUESTSTATE_COMPLETE = 4 };
    enum FeedState { FEEDSTATE_FREE = 0, FEEDSTATE_FED = 1, FEEDSTATE_DECODECOMPLETED = 2 };
    enum { KU_MAX_DECODERFEEDS = 20 };                        // vendor MAX_DECODERFEEDS
    enum { KI_MAX_REQUEST_HANDLE_VALUE = 1 << (24 - 2) };     // vendor; == 4194304

    // ---- RequestInternal: console stride 0x30. WIDENS (pDecoder). ------------------
    struct RequestInternal
    {
        f64 startTime;                 // +0x00  PlayHandler stfd; Process lfd; cleared on reach
        Decoder *pDecoder;             // +0x08  *** WIDENS *** StartRequest stores the factory result
        f32 requestHandle;             // +0x0C  Process copies it into mCurrentRequestHandle
        f32 sampleRate;                // +0x10  UnpackHeader (18-bit field, fcfid'd)
        s32 numSamples;                // +0x14  UnpackHeader (29-bit field)
        s32 loopStart;                 // +0x18  UnpackHeader; -1 == no loop
        s32 numSamplesToSkipPlayer;    // +0x1C  [3.03] SetSeekData clears; Process's skip budget
        s32 numSamplesToSkipDecoder;   // +0x20  [3.03] SetSeekData; seeds feed.chunkSamplesPlayed
                                       //        and Decoder::Feed's startSample
        s32 numSamplesToSkipStream;    // +0x24  [3.03] SetSeekData; seeds RequestExternal.numSamplesFed
        u16 decoderInstanceSize;       // +0x28  StartRequest copies Decoder+0x20; Process carves
                                       //        align_up(this,128) off the System stack allocator
        u8  state;                     // +0x2A  RequestState -- the ONLY field CreateInstance writes
        u8  numChannels;               // +0x2B  UnpackHeader's 6-bit field + 1
    };                                 // console 0x30; host: use sizeof(), never 0x30

    // ---- RequestExternal: console stride 0x50. SEVEN pointers -> DOES NOT SURVIVE. --
    struct RequestExternal
    {
        f64 streamFileOffset;                    // +0x00  PlayHandler stfd (command +0x10)
                                                 //  *** the console puts THIS at base+4 ***
        char *pSampleData;                       // +0x08  *** WIDENS *** UnpackHeader: past the packed header
        s32 loopStartStreamOffset;               // +0x0C  UnpackHeader (32-bit); read via `lwa` (signed)
        s32 gigaSamplesInRam;                    // +0x10  UnpackHeader when playType == 2
        s32 numSamplesFed;                       // +0x14  PlayHandler clears; SubmitChunk adds the chunk's
                                                 //        leading BE u32; SetSeekData seeds from RI+0x24
        s32 numBytesFed;                         // +0x18  StreamNextChunk adds chunk->size;
                                                 //        FeedCleanup subtracts it back
        char *pStreamLoopFileName;               // +0x1C  *** WIDENS *** System::Alloc'd copy
        StreamPool *pStreamPool;                 // +0x20  *** WIDENS *** StreamPool::GetInstance
        StreamPool::StreamHandle streamHandle;   // +0x24  *** WIDENS *** AcquireStream's result
        rw::core::filesys::Stream *pRwCoreStream;// +0x28  *** WIDENS *** == *(streamHandle + 0x14)
        rw::core::filesys::Stream::RequestId streamerRequestId; // +0x2C  (32-bit id, no widen)
        char *pNextChunk;                        // +0x30  *** WIDENS *** SubmitChunk's return
        char *pLoopStartChunk;                   // +0x34  *** WIDENS *** saved pNextChunk / pSampleData
        s32 mSeekBlockA;                         // +0x38  [3.03] SeekTableParser out; -> Decoder::Feed r8
        s32 mSeekBlockB;                         // +0x3C  [3.03] SeekTableParser out (UNNAMED-consumer)
        s32 mSeekStreamOffset;                   // +0x40  [3.03] added to trunc(streamFileOffset)
        s32 mSeekBlockD;                         // +0x44  [3.03] -> Decoder::Feed r9
        u8  codec;                               // +0x48  UnpackHeader 4-bit; indexes sDecoderGuidLut
        u8  playType;                            // +0x49  UnpackHeader 2-bit (1/2 == streamed)
        u8  feedSlotLatest;                      // +0x4A  StreamNextChunk / HandleLoopStart
        u8  expelMode;                           // +0x4B  PlayHandler (command +0x2E)
        u8  mNoSeekTable;                        // +0x4C  [3.03] SetSeekData sets 1 when parsing failed
    };                                 // console 0x50; host: use sizeof(), never 0x50

    // ---- SndPlayer1FeedDesc: console stride 0x10, count 20. TWO pointers -> widens. -
    // NOTE: this is NOT the SndPlayer1_CgsStreamMod feed record (that fork's is 0x0C with
    // no pointers). Stride and count proven independently by CreateInstance's own loop
    // (`addi r11,r11,0x10`, `li r10,0x14`, base this+0x5C, ending exactly at +0x19C) and by
    // the `rotlwi ...,4` / `cmplwi ...,0x14` shape in GetFeedSlot / FeedCleanup / Process.
    struct SndPlayer1FeedDesc
    {
        rw::core::filesys::Stream::ChunkInfo *pChunkInfo; // +0x00 *** WIDENS *** ctor nulls it
        rw::core::filesys::Stream *pRwCoreStream;         // +0x04 *** WIDENS *** SubmitChunk = RE.pRwCoreStream
        s32 chunkSamplesPlayed;                           // +0x08 SubmitChunk seeds; Process accumulates
        Decoder::RequestHandle decoderRequestHandle;      // +0x0C u8 -- Decoder::Feed's return
        u8  feedState;                                    // +0x0D FeedState -- ctor clears it
        u8  requestIndex;                                 // +0x0E SubmitChunk stores the owning request
        u8  mPad0F;                                       // +0x0F (no writer found)
    };                                 // console 0x10; host: use sizeof(), never 0x10

    static u32 GetSize(const VoiceStageConfig *apConfig);        // @0x82BA0220
    static int CreateInstance(SndPlayer1 *self, ConstructorParams *p); // @0x82BA6C80
    static SndPlayer1Layout ComputeLayout(u8 au8Channels, u32 auMaxRequests); // host-only

    // vt[0] == ReleaseEvent @0x82BA4178 -- the committed PlugIn base models slot 0 as the
    // destructor and slot 3 as Destroy(int), and PlugIn::CreateInstance's failure path calls
    // exactly those two, so the overrides keep that mapping.
    virtual ~SndPlayer1();                        // vt[0] 0x82BA4178 ReleaseEvent
    virtual int  Event(int aiEventId, void *apParam); // vt[1] 0x82BA5C48 EventEvent
    virtual int  VFunc2();                        // vt[2] 0x82BDD2D0 GetPpuTicksEvent (returns mTimerClient.mCpuTicks)
    virtual void Destroy(int aFlags);             // vt[3] 0x82B9EAF8 `vector deleting destructor'

    // ---- the two variable tails: NOT members. Reached through the stored 16-bit offsets,
    // exactly as the vendor header does -- this is the mechanism that makes the widening
    // invisible to every consumer body.
    RequestInternal *GetRequestInternal(u32 auIndex)
    {
        RequestInternal *pArray = reinterpret_cast<RequestInternal *>(
            reinterpret_cast<char *>(this) + mRequestInternalOffset);
        return &pArray[auIndex];
    }
    f32 *GetDeclickBuffer()
    {
        return reinterpret_cast<f32 *>(
            reinterpret_cast<char *>(this) + mDeclickBufferOffset);
    }

    // ---- layout (console offsets in comments; x64 widths, by-name access) -------------
    // +0x28 -- the three PlugIn attribute slots. THE SLOTS ARE NOT UNIFORM: slot 0 is
    // written/read as f32 (`stfs 0x28`), slots 1 and 2 as f64 spanning the whole 8-byte slot
    // (`stfd 0x30` / `stfd 0x38`, RwacTimerClient @0x82BA6A04..0x82BA6A4C). Declared as the
    // vendor's Attribute_t[3] so GetAttribute/SetAttribute still index by 8, with typed
    // accessors for the two f64 slots.
    Attribute_t mAttribute[ATTRIBUTE_MAX];        // +0x28..+0x3F
    TimerHandle mTimerClient;                     // +0x40  (vendor name: TimerClient)
    RequestExternal *mpRequestExternal;           // +0x58  *** WIDENS *** == block base + 4
    SndPlayer1FeedDesc mFeedDesc[KU_MAX_DECODERFEEDS]; // +0x5C..+0x19B
    Decoder *mpLoadedDecoder;                     // +0x19C *** WIDENS *** (vendor types it uintptr_t)
    f32 mCurrentRequestHandle;                    // +0x1A0
    f32 mCurrentRequestSampleRate;                // +0x1A4
    s32 mCurrentRequestSamplesPlayed;             // +0x1A8
    s32 mCurrentRequestNumSamples;                // +0x1AC
    f32 *mpRequestHandle;                         // +0x1B0 *** WIDENS *** the allocation BASE;
                                                  //   [3.03] the 2.11 header has an inline
                                                  //   `float mRequestHandle` here -- do NOT
                                                  //   use the older shape, ARTIST dereferences
                                                  //   and System::Free's this pointer.
    f32 mLastRequestHandleProcessed;              // +0x1B4
    f32 mLastRequestHandleSuccessfullyProcessed;  // +0x1B8
    f32 mPreviousSampleRate;                      // +0x1BC
    u16 mSamplesRequested;                        // +0x1C0 (PreProcess `sth`; NOT ctor-initialised)
    u16 mDeclickBufferOffset;                     // +0x1C2 <- layout.muDeclickBufferOffset
    u16 mRequestInternalOffset;                   // +0x1C4 <- layout.muRequestInternalOffset
    u8  mMaxChannels;                             // +0x1C6
    u8  mNextFreeRequest;                         // +0x1C7
    u8  mNextRequestToFree;                       // +0x1C8
    u8  mCurrentRequest;                          // +0x1C9
    u8  mMaxRequests;                             // +0x1CA (low byte of n)
    u8  mDcOffsetsGathered;                       // +0x1CB
    u8  mNumDeclickSamples;                       // +0x1CC
    u8  mNextFeedSlotToFill;                      // +0x1CD GetFeedSlot's allocation cursor
    u8  mNextFeedSlotToFree;                      // +0x1CE Process's consume cursor
    u8  mNextFeedSlotToCleanup;                   // +0x1CF [3.03] FeedCleanup's release cursor
    u8  mbTimerAdded;                             // +0x1D0 ReleaseEvent's `== 1` gate
    // +0x1D1..+0x1D7 console tail pad; the host's is whatever alignof(SndPlayer1) requires.
    // Then, OUTSIDE the class: f32 declick[mMaxChannels] @mDeclickBufferOffset, and
    // RequestInternal[mMaxRequests] @mRequestInternalOffset.
};
```

### `rw::audio::core::PlugIn::Initialize<rw::audio::core::SndPlayer1>` @ `0x82B9D368`  [DECODED]

**Signature**

```cpp
// Demangled from the call-site symbol at 0x82BA6CBC:
//   ??$Initialize@VSndPlayer1@core@audio@rw@@@PlugIn@core@audio@rw@@KAXPAVSndPlayer1@123@I@Z
//   K = protected static, A = __cdecl, X = void, PAVSndPlayer1 = SndPlayer1*, I = unsigned int
protected:
    template <class T>
    static void PlugIn::Initialize(T *apPlugIn, unsigned int auAttributeOffset);

// NOTE: PlugIn::Initialize does NOT yet exist in the committed
// b5-decomp/vendor/renderware/include/rw/audio/core/PlugIn.h -- this cluster ADDS it.
// The plug-ins already homed (Delay, Gain, Iir2*, ReverbModel1) each inline its effect
// locally with a `FLAGGED: the real Initialize<T> body lives in the PlugIn TU` comment
// (see Delay.cpp's CreateInstance header); homing the template retires those notes.
```

**Behaviour**

NO DOSSIER. Hand-decoded from raw XEX file offset 0x00BA0368
(file_off = 0x3000 + 0x82B9D368 - 0x82000000), big-endian PowerPC, 24 words:

0x82B9D368  7D8802A6  mflr   r12
0x82B9D36C  9181FFF8  stw    r12, -8(r1)
0x82B9D370  FBC1FFE8  std    r30, -0x18(r1)
0x82B9D374  FBE1FFF0  std    r31, -0x10(r1)
0x82B9D378  9421FF90  stwu   r1, -0x70(r1)
0x82B9D37C  7C7F1B78  mr     r31, r3          ; r31 = apPlugIn (the SndPlayer1)
0x82B9D380  7C9E2378  mr     r30, r4          ; r30 = auAttributeOffset (0x28 from the caller)
0x82B9D384  2B1F0000  cmplwi cr6, r31, 0
0x82B9D388  419A0018  beq    cr6, 0x82B9D3A0  ; null object -> skip construction
0x82B9D38C  3D608218  lis    r11, 0x8218
0x82B9D390  387F0040  addi   r3, r31, 0x40    ; r3 = &apPlugIn->mTimerClient
0x82B9D394  396BF344  addi   r11, r11, -0x0CBC ; r11 = 0x8217F344  (the SndPlayer1 vtable)
0x82B9D398  917F0000  stw    r11, 0(r31)      ; *** the vptr install ***
0x82B9D39C  4BFCEB0D  bl     0x82B6BEA8       ; TimerHandle::TimerHandle(&mTimerClient)
                                              ;   (LI = 0x3FCEB0C, sign-extended -0x314F4,
                                              ;    0x82B9D39C - 0x314F4 = 0x82B6BEA8 -- the
                                              ;    committed TimerHandle::TimerHandle_ctor)
0x82B9D3A0  2B1E0000  cmplwi cr6, r30, 0
0x82B9D3A4  419A000C  beq    cr6, 0x82B9D3B0  ; offset 0 -> leave mpAttribute alone
0x82B9D3A8  7D7FF214  add    r11, r31, r30
0x82B9D3AC  917F000C  stw    r11, 0x0C(r31)   ; *** mpAttribute = (char*)this + offset ***
0x82B9D3B0  38210070  addi   r1, r1, 0x70
0x82B9D3B4  8181FFF8  lwz    r12, -8(r1)
0x82B9D3B8  7D8803A6  mtlr   r12
0x82B9D3BC  EBC1FFE8  ld     r30, -0x18(r1)
0x82B9D3C0  EBE1FFF0  ld     r31, -0x10(r1)
0x82B9D3C4  4E800020  blr                     ; void (r3 holds the leftover &mTimerClient)

Shape: the leading `if (apPlugIn)` guarding a vtable store + an embedded-subobject ctor is
the MSVC placement-new null guard, so the source is `new (apPlugIn) T;` -- the T ctor being
inlined here as {vptr install, TimerHandle ctor}. The attribute store is a SEPARATE statement
outside that guard.

CROSS-CHECK that this is the SndPlayer1 instantiation and not a neighbour's: the immediately
following 24-word body at 0x82B9D3C8 is byte-identical except `addi r3,r31,0x24` (a different
embedded-timer offset) and `addi r11,r11,-0x0CAC` -> vtable 0x8217F354. Reading
0x8217F344..0x8217F363 out of the XEX shows two 4-slot tables, and the second one's slot [1]
is 0x82BA0F80 == the dossier-named rw::audio::core::VuMeter::EventEvent. So 0x8217F344 is
SndPlayer1's, it is exactly four slots, and the neighbour is PlugIn::Initialize<VuMeter>.

Also proven by this body: mTimerClient sits at +0x40 in SndPlayer1 (matching the vendor
header's member order Attribute_t mAttribute[3] @+0x28 then TimerClient mTimerClient), and the
attribute base handed in by SndPlayer1::CreateInstance is +0x28 == &mAttribute[0]. Since the
TimerHandle ctor seeds mpName = "Unknown" and mStage = 3, and TimerManager::AddTimer later
overwrites mpName = "SndPlayer" and mStage = 1 (@0x82B6EBEC/0x82B6EBF0), the two-phase name
/stage sequence the instance-layout table records is real.

**Constants**

| item | vaddr | file_off | raw BE bytes | decoded |
|---|---|---|---|---|
| the body itself (exporter gap) | 0x82B9D368..0x82B9D3C4 | 0x00BA0368..0x00BA03C4 | `7D8802A6 9181FFF8 FBC1FFE8 FBE1FFF0 9421FF90 7C7F1B78 7C9E2378 2B1F0000 419A0018 3D608218 387F0040 396BF344 917F0000 4BFCEB0D 2B1E0000 419A000C 7D7FF214 917F000C 38210070 8181FFF8 7D8803A6 EBC1FFE8 EBE1FFF0 4E800020` | 24 instructions, decoded above |
| the installed vtable | 0x8217F344 | 0x00182344 | `82 BA 41 78 82 BA 5C 48 82 BD D2 D0 82 B9 EA F8` | [0] ReleaseEvent 0x82BA4178, [1] EventEvent 0x82BA5C48, [2] GetPpuTicksEvent 0x82BDD2D0, [3] `vector deleting destructor' 0x82B9EAF8 |
| the NEXT table (bounds proof) | 0x8217F354 | 0x00182354 | `82 B9 D0 A8 82 BA 0F 80 82 B9 68 40 82 B9 EB 58` | VuMeter's 4 slots; [1] = VuMeter::EventEvent @0x82BA0F80 (IDA-named), installed by PlugIn::Initialize<VuMeter> @0x82B9D3EC |
| branch target decode | -- | -- | `4BFCEB0D` | b-form: LI = 0x03FCEB0C, sign-extended = -0x314F4; 0x82B9D39C - 0x314F4 = 0x82B6BEA8 = TimerHandle::TimerHandle (committed @ TimerHandle.cpp) |
| vtable address materialisation | -- | -- | `3D608218` + `396BF344` | lis 0x8218 then addi -0x0CBC (0xF344 sign-extends) => 0x8217F344 |

Strings this body reaches indirectly: TimerHandle::TimerHandle_ctor seeds mpName = "Unknown"
(already a committed constant in TimerHandle.cpp); TimerManager::AddTimer later replaces it
with aSndplayer_0 @0x821745CC, file_off 0x001775CC, `53 6E 64 50 6C 61 79 65 72 00` = "SndPlayer".

**Host hazards**

1. THE ATTRIBUTE OFFSET ARGUMENT IS A CONSOLE OFFSET AND MUST NOT BE TRANSLITERATED. The
   caller passes 0x28; on x64 five pointers (vptr, mpSystem, mpVoice, mpAttribute,
   mpPlugInDescRunTime) plus two f32s, a u32 and two u8s precede mAttribute[0], so the host
   value is the live `(char*)&self->mAttribute[0] - (char*)self`. A literal 0x28 aims
   mpAttribute at mpPlugInDescRunTime and every GetAttribute/SetAttribute then reads/writes
   the descriptor pointer.

2. TimerHandle IS NOT DEFAULT-CONSTRUCTED BY placement new. The committed TimerHandle.h
   declares a POD with a static TimerHandle_ctor and no user constructor, so `new (self) T`
   leaves mTimerClient untouched -- yet the console explicitly calls the ctor here. T's host
   constructor must call TimerHandle::TimerHandle_ctor(&mTimerClient) (the Delay_ctor
   precedent in plugins/Delay.cpp). Skipping it leaves mpItemHandleNode/mpName/mStage
   garbage, and TimerManager::AddTimer only overwrites mpCallback/mpContext/mpName/mCpuTicks/
   mStage/mTimerVisibility -- mpItemHandleNode is set by Collection::AddItem, so the miss is
   silent until teardown.

3. T'S HOST CONSTRUCTOR MUST NOT INITIALISE ANY PlugIn BASE FIELD. The generic
   PlugIn::CreateInstance @0x82B6A828..0x82B6A860 has already written mpVoice,
   mpPlugInDescRunTime, mpSystem, mLatencyInSamples, mDecaySamples, mCpuTicks, mInputChannels
   and mOutputChannels BEFORE dispatching pCreateInstance -- and SndPlayer1::CreateInstance
   reads mOutputChannels back out (`lbz 0x21`) immediately after Initialize returns. A member
   initialiser or a `= {}` in the host ctor would zero the channel count and collapse the
   computed layout to declickOffset == requestOffset.

4. THE VTABLE SLOT ORDER IS [Release, Event, GetPpuTicks, deletingDtor], NOT the C++ default.
   PlugIn::CreateInstance's failure path calls vt[0](self) then vt[3](self, 0) -- i.e. Release
   then destroy-without-free. The committed PlugIn.h already models that as
   `virtual ~PlugIn()` (slot 0) / `Event` (1) / `VFunc2` (2) / `Destroy(int)` (3), and
   PlugIn.cpp's failure path is written as `self->~PlugIn(); self->Destroy(0);`. SndPlayer1
   must override in exactly that declaration order so ReleaseEvent lands in slot 0 and the
   deleting destructor in slot 3; declaring the destructor anywhere else silently reorders the
   host vtable and turns the failure path into a double-destroy.

5. THE FUNCTION IS void. The console leaves &mTimerClient in r3 as address-materialisation
   residue; IDA/pseudocode would render a return value. The mangled name says X (void) and the
   caller ignores r3 -- do not invent a return.

6. THE NULL GUARD COVERS ONLY THE CONSTRUCTION, NOT THE ATTRIBUTE STORE. Faithful order is:
   `if (self) construct;` then, separately, `if (offset) store;`. Do not merge them into one
   `if (self && offset)` -- that changes the observable behaviour for a null object and, more
   importantly, misrepresents where the compiler's placement-new guard actually is.

7. NO fcmpu, no float compare, no record size and no ring interaction in this body -- there is
   no NaN branch polarity and no cursor advance to preserve. Everything load-bearing is the
   two offsets (0x40 -> mTimerClient, 0x0C -> mpAttribute) and the vtable word, all of which
   become by-name access on the host.

**Implementation sketch**

```cpp
// -------------------------------------------------------------------------------------
// PlugIn::Initialize<T> -- the shared "construct the leaf plug-in over the stage carve and
// base its attribute table" helper. X360 instantiations: <SndPlayer1> @0x82B9D368 (raw XEX
// recovery, file 0x00BA0368) and <VuMeter> @0x82B9D3C8; both are the SAME body modulo the
// inlined T ctor, so one template reproduces them.
//
// It runs AFTER the generic PlugIn::CreateInstance @0x82B6A818 has already written every
// base field, so T's construction must not touch them: on the console the inlined ctor
// stores only the vtable word and constructs the embedded sub-objects. The host equivalent
// is placement-new of a T whose default constructor has NO member initialisers for the base
// fields -- PlugIn's implicit default ctor writes the vptr and nothing else, which is
// exactly the console's `stw r11, 0(r31)`.
// -------------------------------------------------------------------------------------
template <class T>
void PlugIn::Initialize(T *apPlugIn, unsigned int auAttributeOffset)
{
    // cmplwi cr6,r31,0 ; beq -- the placement-new null guard the compiler emitted.
    if (apPlugIn != 0)
    {
        // stw <T's vtable>, 0(r31)  + bl TimerHandle::TimerHandle(this+0x40)
        // The host placement-new IS the vptr store; T's ctor performs the embedded
        // sub-object construction the console inlined here (for SndPlayer1 that is the one
        // TimerHandle ctor -- see SndPlayer1_ctor below, the Delay_ctor precedent).
        new (apPlugIn) T;
    }

    // cmplwi cr6,r30,0 ; beq ; add r11,r31,r30 ; stw r11,0x0C(r31)
    // Deliberately OUTSIDE the null guard, faithful to the asm (a null object with a
    // non-zero offset faults on the console too -- no call site does that).
    if (auAttributeOffset != 0)
        apPlugIn->mpAttribute = reinterpret_cast<PlugIn::Attribute_t *>(
            reinterpret_cast<char *>(apPlugIn) + auAttributeOffset);
}

// The inlined T ctor for this instantiation, spelled out the way Delay.cpp spells Delay_ctor
// (TimerHandle has no user-declared constructor in the committed TimerHandle.h, so placement
// new does NOT construct it -- the explicit call is required, and it is what the console
// emits):
SndPlayer1::SndPlayer1()
{
    // stw 0x8217F344, 0(r31) -- the host vptr install, done by the compiler.
    // bl 0x82B6BEA8 with r3 = this + 0x40:
    TimerHandle::TimerHandle_ctor(&mTimerClient);
    // Nothing else. In particular: no base-field initialisers (PlugIn::CreateInstance has
    // already filled them and this ctor runs after), and none of the SndPlayer1 tail fields
    // -- SndPlayer1::CreateInstance seeds those explicitly, in its own order.
}

// Call site, from SndPlayer1::CreateInstance (console `li r4,0x28 ; bl ...`):
//   PlugIn::Initialize<SndPlayer1>(
//       self,
//       (u32)((char *)&self->mAttribute[0] - (char *)self));   // NOT the literal 0x28
```

### Cluster notes

GROUND-TRUTH SOURCES USED (all re-verified in this session, nothing inherited):
* .ida-exports/BURNOUT_X360_ARTIST.XEX/0x82BA0220.json and 0x82BA6C80.json -- `assembly` field, read instruction by instruction.
* IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex, file_off = 0x3000 + vaddr - 0x82000000, big-endian, via [IO.File]::ReadAllBytes -- for the exporter-gap body at 0x82B9D368 (file 0x00BA0368), the vtable at 0x8217F344 (file 0x00182344), the neighbouring VuMeter table at 0x8217F354, the three float/double constants, and the two strings at 0x82174598 / 0x821745CC.
* Corroborating dossiers read in full for the struct shapes: Process @0x82BA0568, FeedCleanup @0x82BA0268, GetFeedSlot @0x82BA0380, PlayHandler @0x82BA41D8, StopHandler @0x82BA44E0, SubmitChunk @0x82BA4570, UnpackHeader @0x82B9BF08, SetSeekData @0x82B9C068, StreamNextChunk @0x82BA6080, HandleLoopStart @0x82BA6160, HandleSampleEnd @0x82BA6248, ReleaseEvent @0x82BA4178, RwacTimerClient @0x82BA6980, PlugIn::CreateInstance @0x82B6A818, Voice::CreateInstance @0x82B6EC50.

⭐ THE BIG FIND THIS SESSION -- A REAL VENDOR HEADER EXISTS FOR THIS EXACT CLASS, and neither prior report cites it:
  references/Feb-2007/BrnEntityModuleUnity/SDKs/Packages/rwaudiocore/2.11.00/include/rw/audio/core/plugins/sndplayer1.h
It is `class SndPlayer1 : public PlugIn` with the FULL private member list, and it maps onto the ARTIST offsets slot-for-slot from mAttribute[3] @+0x28 through mNextFeedSlotToFree @+0x1CE. Every name in my sketches is that header's name, not a reconstruction. It also supplies, verbatim: ConstructorParams{float maxRequests}, the Attribute/EventId/ExpelMode/RequestState/FeedState enums, MAX_DECODERFEEDS = 20, MAX_REQUEST_HANDLE_VALUE = 1<<22 (== 4194304, the wrap constant the other report found in rodata), the RequestInternal / RequestExternal / SndPlayer1FeedDesc struct definitions, and -- crucially for this cluster -- the two offset-relative accessors GetRequestInternal(index) and GetDeclickBuffer() written against mRequestInternalOffset / mDeclickBufferOffset. That is independent confirmation that the computed-layout + two-stored-16-bit-offsets design is the real vendor mechanism and that a host port only has to change the two literals that PRODUCE those offsets.
The DecFIGS PS3 dump references/DecFIGS/dwarfdump/SDKs/EATech/include/rw/audio/core/plugins/sndplayer1.h is the 3.03-era counterpart but only emits the nested structs (ConstructorParams, PlayParams, IsRequestDoneParams, FileInfo, DecoderIndexToGuidDesc) and `GUID = 1399738417` (== 0x536E5031 == 'SnP1'); its line numbers are ~2-22 higher than 2.11's, which is how I bracket the 3.03 additions.

ARTIST (3.03) vs the 2.11 header -- the exact deltas, all asm-proven:
  * RequestInternal grew 0x20 -> 0x30: three s32 skip counters inserted at +0x1C/+0x20/+0x24 (SetSeekData @0x82B9C0C4..0x82B9C128 writes +0x20/+0x24 and clears +0x1C; Process reads +0x1C as the skip budget and +0x20+0x24 as the initial samples-played), pushing decoderInstanceSize/state/numChannels to +0x28/+0x2A/+0x2B.
  * RequestExternal grew to 0x50: pNextChunk/pLoopStartChunk moved from the tail up to +0x30/+0x34 (HandleLoopStart @0x82BA61D8/0x82BA6208, HandleSampleEnd @0x82BA62A8/0x82BA62E0), and a seek block +0x38/+0x3C/+0x40/+0x44 plus a flag byte +0x4C was appended (SetSeekData; PlayHandler reads +0x40; SubmitChunk feeds +0x38/+0x44 to Decoder::Feed).
  * `float mRequestHandle` @+0x1B0 became `float *mpRequestHandle` -- the base of the single System::Alloc'd {counter, RequestExternal[n]} block. This is the change that creates the base+4 alignment problem.
  * Two bytes appended: mNextFeedSlotToCleanup @+0x1CF and mbTimerAdded @+0x1D0.

CORRECTIONS TO progress/scratch_dossiers/sndplayer1_decode_codex.md (beyond the three the prompt already flagged):
  (a) Its +0x1CF row -- "ARTIST-only/unknown byte ... no semantic reader was found" -- is wrong. FeedCleanup @0x82BA0268 both reads and advances it as the chunk-release cursor. The feed ring has THREE cursors: fill (+0x1CD, GetFeedSlot), consume (+0x1CE, Process), release (+0x1CF, FeedCleanup). Its +0x1CE label "next feed slot to free" is the vendor name but reads as a reclaim cursor; it is the DECODE-consume cursor.
  (b) Its RequestExternal rows +0x24 / +0x28 are swapped in effect: +0x24 is the StreamPool::StreamHandle from AcquireStream and +0x28 is the rw::core::filesys::Stream* (= *(handle+0x14)) that Stream::GetChunk / GetRequestState are actually called on (StreamNextChunk @0x82BA60D0/0x82BA60F4).
  (c) Its section-2 note "the eight decoder GUID words visible before the adjacent string" -- confirmed exactly, and the alloc-name string it abuts is at 0x82174598 (I recomputed the CreateInstance operand arithmetic to land there).
  (d) Its claim that the SnP1 vtable is four slots is CORRECT and I re-verified it the harder way: 0x8217F344..0x8217F353 are SnP1's four, and 0x8217F354's slot [1] is the IDA-named VuMeter::EventEvent @0x82BA0F80, installed by the adjacent PlugIn::Initialize<VuMeter> @0x82B9D3EC.

DIVERGENCE DISCIPLINE vs progress/scratch_dossiers/streammod_gainarray_decode_codex.md: I copied NO offset from it. I used it only to (i) confirm that the game-side SndPlayer1_CgsStreamMod is a 2.11-era FORK (its RequestInternal stride 0x20 IS the 2.11 vendor layout, which is why the vendor 3.03 class is 0x30) and (ii) borrow the SHAPE of the argument that computed layouts must be sizeof-derived. Concrete divergences to never cross: StreamMod = RequestInternal 0x20 / RequestExternal 0x88 / FeedDesc 0x0C with NO pointers / fixed extent 0x188 / feed offsets +0x04,+0x08,+0x09 / cursors at +0x185,+0x186. Vendor SndPlayer1 = 0x30 / 0x50 / 0x10 with TWO pointers / 0x1D8 / feed offsets +0x08,+0x0C,+0x0D,+0x0E / cursors at +0x1CD,+0x1CE,+0x1CF.

WHAT THIS CLUSTER LEAVES OPEN FOR THE NEXT ONE (not blocked, just out of scope):
  * RequestExternal +0x38 / +0x3C / +0x44 have writers (SetSeekData) and consumers (Decoder::Feed args r8/r9) but no attested SEMANTIC name; I typed them s32 with UNNAMED-consumer comments rather than invent names. +0x30/+0x34 ARE named (pNextChunk/pLoopStartChunk) by asm behaviour + the 2.11 header, so those are safe.
  * SndPlayer1FeedDesc +0x0F has no writer at all in any body I read; declared as pad.
  * PlugIn::Initialize<T> is being ADDED to PlugIn.h by this cluster. Once it lands, the four "FLAGGED: the real Initialize<T> body lives in the PlugIn TU" notes in plugins/Delay.cpp, Gain.cpp, Iir2*.cpp and ReverbModel1.cpp can be retired in a follow-up -- their locally-inlined equivalents are the same body.
  * PlugIn.h's Attribute_t (f32 + u32 pad) is fine for the indexed API but does not express that SnP1's slots 1 and 2 are f64; I recommended typed accessors rather than changing the shared base type, since Dac and the filters index it as f32.

## Cluster: rw::audio::core::SndPlayer1 -- THE DATA PATH (Process / PreProcess / WaitForStartTime / Declick / AdvanceCurrentRequest), X360 BURNOUT_X360_ARTIST.XEX

### `rw::audio::core::SndPlayer1::PreProcess` @ `0x82B9C2D8`  [DECODED]

**Signature**

```cpp
// Installed in PlugInDescRunTime::pPreProcess; Mixer::ProcessInputPlugIns casts the slot to
//   int (*)(PlugIn*, Mixer*, int, int)   (Mixer.cpp:235, bctrl @0x82B6A124)
// DWARF (twin class, GameShared/.../internal/sndplayer1.h:386):
//   int PreProcess(rw::audio::core::PlugIn *, Mixer *, bool, int)
static int rw::audio::core::SndPlayer1::PreProcess(rw::audio::core::PlugIn *apPlugIn,
                                                  rw::audio::core::Mixer * /*apContext*/,
                                                  bool /*abAlreadyProcessedThisFrame*/,
                                                  int aiRequestedCount);
```

**Behaviour**

Four instructions, no branches, no memory reads.

  0x82B9C2D8  mr   r11, r3      ; r11 = self (the PlugIn* first argument)
  0x82B9C2DC  li   r3, 0        ; return value = 0
  0x82B9C2E0  sth  r6, 0x1C0(r11) ; mSamplesRequested = (u16)aiRequestedCount
  0x82B9C2E4  blr

Register-to-argument mapping (Xenon PPC, `this`-style static self in r3): r3 = PlugIn* self, r4 = Mixer* (never read), r5 = the bool alreadyProcessedThisFrame (never read), r6 = the requested sample count. The store is a HALFWORD (`sth`), so only the low 16 bits of the caller's int survive; the caller (Mixer::ProcessInputPlugIns) starts the cascade at `MIXER_FRAME_SIZE - produced` and clamps every returned count to 256 afterwards, so on the voice path the value is always in [0,256] and the truncation is lossless. Faithfully reproduce the truncation anyway -- it is the only width narrowing in the function.

The return value 0 is the count cascaded DOWN to the next-lower stage in the pre-process walk. SndPlayer1 is a SOURCE stage (PlugInDescRunTime::mu8PlugInType <= 3 marks the source-stage boundary, Voice::CreateInstance @0x82B6EDC8), i.e. it is always stage index 0 in the splice voices, so there is no lower stage that consumes the 0. Process is the sole consumer of the stowed count: it reads mSamplesRequested at four places (0x82BA073C future-start cap, 0x82BA0880 decode-count clamp, 0x82BA0B44 status derivation, and Declick's 0x82B9C1D8 publish cap).

No other field is touched. There is NO discontinuity handling, NO context read, NO validation.

**Constants**

None. PreProcess reads no rodata and materialises no literal other than the immediate 0 (`li r3, 0`) and the instance offset 0x1C0 (mSamplesRequested).

For completeness, the one offset used:
  +0x1C0  u16 mSamplesRequested   (DWARF name from the twin class's member list,
                                   GameShared/.../internal/sndplayer1.h:492)

**Host hazards**

* NARROWED VALUE, not a narrowed pointer: `sth` truncates the int to 16 bits. mSamplesRequested must stay a u16 member on the host and the store must keep the explicit static_cast<u16> so the behaviour is identical if a caller ever exceeds 65535. Do NOT "fix" it to an int.
* The +0x1C0 literal is a CONSOLE offset inside an object whose earlier members (vptr, System*, Voice*, Attribute_t*, PlugInDescRunTime*, mpRequestExternal, 20 feed records each holding TWO 32-bit pointers, mpLoadedDecoder, mpRequestHandle) all widen on x64. The host must reach the field BY NAME; there is no valid host constant here.
* r4/r5 are attested unused -- do not invent a discontinuity/reset behaviour for them. Several sibling players DO use r5; this one does not (it is never read before `blr`).
* This is NOT a deferred-command handler, so the return is NOT a ring-cursor advance: 0 here is the pre-process CASCADE COUNT handed to the next lower stage. Do not apply the host-sizeof rule to it.
* The IDA prototype `(int a1, int a2, int a3, __int16 a4)` types a4 as __int16 because of the `sth`; the ARGUMENT is a full int (Mixer.cpp passes `liCount`). Type the parameter int and cast at the store.

**Implementation sketch**

```cpp
// -------------------------------------------------------------------------------------
// SndPlayer1::PreProcess @0x82B9C2D8 -- stow the frame's requested sample count and
// cascade 0 to the next-lower stage (there is none: SnP1 is the source stage).
// FOUR instructions; r4 (Mixer) and r5 (alreadyProcessedThisFrame) are decode-attested
// UNUSED -- the parameters are named but not read, exactly as on the console.
// -------------------------------------------------------------------------------------
int SndPlayer1::PreProcess(PlugIn *apPlugIn, AudioProcessContext * /*apContext -- r4, unused*/,
                           bool /*abAlreadyProcessedThisFrame -- r5, unused*/,
                           int aiRequestedCount)
{
    SndPlayer1 *self = static_cast<SndPlayer1 *>(apPlugIn);

    // sth r6, 0x1C0(r11) -- a HALFWORD store. The caller clamps its cascade to
    // MIXER_FRAME_SIZE (256), so the narrowing is lossless on the voice path, but it IS
    // the console behaviour and mSamplesRequested is a u16 member for exactly this reason.
    self->mSamplesRequested = static_cast<u16>(aiRequestedCount);

    return 0;   // li r3, 0
}
```

### `rw::audio::core::SndPlayer1::WaitForStartTime` @ `0x82B9C148`  [DECODED]

**Signature**

```cpp
// DWARF (twin class, GameShared/.../internal/sndplayer1.h:444):
//   bool WaitForStartTime(Mixer *, double, unsigned int *)
// Non-static member. Xenon register map at the ONLY call site (Process @0x82BA071C):
//   r3 = this            (loaded but NEVER read by the body)
//   r4 = Mixer *apContext                       -> argument 1
//   f1 = f64 adStartTime (the r5 GPR slot is SKIPPED -- the float-slot-skip rule)
//   r6 = u32 *apuSamples                        -> argument 3
bool rw::audio::core::SndPlayer1::WaitForStartTime(rw::audio::core::Mixer *apContext,
                                                   f64 adStartTime,
                                                   u32 *apuSamples);
```

**Behaviour**

Instruction walk (assembly field of 0x82B9C148.json), r4 = context, f1 = start time, r6 = out.

  0x82B9C148  lis  r11, 3                 ; 0x30000
  0x82B9C14C  lfdx f0, r4, r11            ; f0 = apContext->mdStreamTime      (+0x30000, f64)
  0x82B9C150  lis  r11, dbl_82001CA8@ha
  0x82B9C154  fsub f0, f1, f0             ; f0 = adStartTime - mdStreamTime   (delta, seconds)
  0x82B9C158  lfd  f13, dbl_82001CA8@l(r11) ; f13 = 0.0 (verified from the XEX, below)
  0x82B9C15C  fcmpu cr6, f0, f13
  0x82B9C160  ble  cr6, loc_82B9C1B0      ; ORDERED (delta <= 0.0) -> "start already reached"

OUTCOME 1 -- start reached (delta <= 0.0, ordered):
  0x82B9C1B0  li   r11, 0
  0x82B9C1B4  stw  r11, 0(r6)             ; *apuSamples = 0
  0x82B9C1B8  li   r3, 1                  ; return true

Else (delta > 0.0, OR delta is NaN -- `ble` is NOT taken on unordered):
  0x82B9C164  lis  r11, 3
  0x82B9C168  ori  r11, r11, 0x18         ; 0x30018
  0x82B9C16C  lwzx r11, r4, r11           ; r11 = apContext->mpFormat  (MixerExecuteParams*)
  0x82B9C170  lfs  f13, 0xC(r11)          ; f13 = mpFormat->mfSampleRate (+0x0C, f32)
  0x82B9C174  lis  r11, flt_820ADBFC@ha
  0x82B9C178  fmul f0, f13, f0            ; f0 = sampleRate * delta   (frames until start)
  0x82B9C17C  lfs  f13, flt_820ADBFC@l(r11) ; f13 = 256.0f
  0x82B9C180  frsp f0, f0                 ; ROUND TO SINGLE -- the compare is at f32 precision
  0x82B9C184  fcmpu cr6, f0, f13
  0x82B9C188  blt  cr6, loc_82B9C194      ; ORDERED (frames < 256.0f) -> outcome 3

OUTCOME 2 -- too far in the future (frames >= 256.0f, OR frames is NaN):
  0x82B9C18C  li   r3, 0                  ; return false
  0x82B9C190  blr                         ; *apuSamples is NOT written -- left untouched

OUTCOME 3 -- near future (0 < frames < 256):
  0x82B9C194  lis  r11, 3
  0x82B9C198  ori  r11, r11, 0x28         ; 0x30028
  0x82B9C19C  lfsx f13, r4, r11           ; f13 = apContext->mfResampleGain (f32)
  0x82B9C1A0  fmuls f0, f13, f0           ; f0 = mfResampleGain * frames
  0x82B9C1A4  fctidz f0, f0               ; ROUND TOWARD ZERO to a 64-bit integer
  0x82B9C1A8  stfiwx f0, 0, r6            ; *apuSamples = the LOW 32 BITS of that integer
  0x82B9C1AC  b    loc_82B9C1B8
  0x82B9C1B8  li   r3, 1                  ; return true

Semantics: mdStreamTime is the frame-start stream clock (seconds); mpFormat->mfSampleRate is the OUTPUT rate (48000.0f as Dac::Mix stores it), so `frames` is the number of OUTPUT frames until the request starts. The 256 gate is exactly MIXER_FRAME_SIZE: a start more than one full mix frame away is simply declined and the caller reports buffer-unavailable. Inside one frame, the count handed back is rescaled by mfResampleGain (the per-voice pitch/resample ratio Mixer::Execute seeds to 1.0f and the upstream resampler updates), converting the OUTPUT frame delay into the number of SOURCE samples of silence Process must emit ahead of the first real sample.

The body never reads `this`. r3 is dead on entry (Process loads it purely because the console models this as a member call).

**Constants**

dbl_82001CA8   va 0x82001CA8   file_off = 0x3000 + 0x82001CA8 - 0x82000000 = 0x4CA8
               raw BE: 00 00 00 00 00 00 00 00      decoded: (f64) 0.0
               role: the ordered `delta <= 0.0` threshold at 0x82B9C15C.
               (The SAME symbol is Process's start-time-armed sentinel at 0x82BA0704 and
                the value Process stores back into RequestInternal::startTime at 0x82BA07E8.)

flt_820ADBFC   va 0x820ADBFC   file_off = 0x3000 + 0x820ADBFC - 0x82000000 = 0xB0BFC
               raw BE: 43 80 00 00                  decoded: (f32) 256.0f
               role: the one-mix-frame horizon at 0x82B9C184. Numerically identical to
               rw::audio::core::MIXER_FRAME_SIZE (base.h:308, DWARF value 256) and to
               Mixer::KU_FRAME_SIZE, but it is a genuine f32 rodata word, not an immediate.

No other rodata. The 0x30000 / 0x30018 / 0x30028 words are `lis`+`ori` immediates for the
Mixer header offsets (mdStreamTime / mpFormat / mfResampleGain), reached by name on the host.

**Host hazards**

* NaN/UNORDERED POLARITY -- the load-bearing hazard here. Both branches are `fcmpu` + a conditional that is NOT taken on unordered:
    - (delta, 0.0) + `ble`: a NaN start time falls into the FUTURE branch.
    - (frames, 256.0f) + `blt`: a NaN then DECLINES (returns false).
  So a NaN start time makes the voice report buffer-unavailable forever, not decode. The sketch spells the second test `if (!(lfFrames < 256.0f)) return false;` precisely so NaN reaches the return; rewriting it as `if (lfFrames >= 256.0f) return false;` INVERTS the NaN case (NaN >= x is false -> it would fall through and decode garbage). Keep both predicates ordered and un-negated-in-sense.
* `frsp` at 0x82B9C180 is REAL: the 256 comparison happens at f32 precision. Omitting the static_cast<f32> silently changes the boundary behaviour.
* `fctidz` + `stfiwx` is truncate-toward-zero into a 64-BIT integer, then store the LOW 32 BITS. It is NOT a saturating conversion and NOT a 32-bit `fctiwz`. On x64 a bare `static_cast<u32>(float)` is UB for out-of-range inputs; go through s64 as the sketch does.
* On outcome 2 the out parameter is NOT written. The caller (Process @0x82BA0730) never reads it on that path, but a host implementation that helpfully zeroes it would diverge if the contract is ever reused. Leave it untouched.
* `this` (r3) is unused. Do not "use" it (e.g. to read mSamplesRequested) -- the mSamplesRequested CAP lives in the CALLER, at Process 0x82BA073C..0x82BA0748, not here. The architecture report progress/scratch_dossiers/sndplayer1_decode_codex.md section 4 omits that cap entirely; it is the caller's, and this function must not grow it.
* mpFormat (+0x30018) is a POINTER on the console; +0x0C into MixerExecuteParams is mfSampleRate. On x64 MixerExecuteParams' members shift (mpVoiceListNodes widens), so mfSampleRate is NOT at +0x0C any more -- by-name access only.
* Argument-slot trap: the double occupies the r5 GPR slot while riding in f1, which is why the out pointer lands in r6 and NOT r5. A host signature that reorders the parameters (e.g. `(f64, Mixer*, u32*)`) still compiles but no longer matches the console's call shape; keep (Mixer*, f64, u32*) as the DWARF declares it.

**Implementation sketch**

```cpp
// -------------------------------------------------------------------------------------
// SndPlayer1::WaitForStartTime @0x82B9C148 -- how much silence, if any, must precede a
// request whose scheduled start time has not been reached yet.
//
// THREE outcomes:
//   (1) start reached   -> *apuSamples = 0, returns true  (caller decodes this frame)
//   (2) >= one whole mix frame away (or a NaN start time)
//                       -> returns false, *apuSamples UNTOUCHED (caller declines)
//   (3) inside this mix frame
//                       -> *apuSamples = trunc(mfResampleGain * frames), returns true
//
// `this` is decode-attested UNUSED (r3 is never read); it stays a member only because
// that is the console's call shape.
//
// NaN POLARITY (both compares are `fcmpu` + a conditional branch, so an unordered result
// takes the NOT-TAKEN path):
//   `ble cr6` on (delta, 0.0)     -- NaN falls THROUGH into the future branch.
//                                    The faithful C++ predicate is the ORDERED one:
//                                    `if (ldDelta <= 0.0)` -- false for NaN. Correct.
//   `blt cr6` on (frames, 256.0f) -- NaN does NOT take the branch, i.e. NaN declines.
//                                    The faithful C++ predicate is `if (lfFrames < 256.0f)`
//                                    -- false for NaN, so control reaches `return false`.
// Writing either test with a negated form (`!(a > b)`, `>=` + swap) would flip the NaN
// behaviour and make a NaN start time DECODE instead of DECLINE. Do not restructure them.
// -------------------------------------------------------------------------------------
bool SndPlayer1::WaitForStartTime(AudioProcessContext *apContext, f64 adStartTime,
                                  u32 *apuSamples)
{
    // fsub f0, f1, f0 -- both operands are f64; the subtraction stays double precision.
    const f64 ldDelta = adStartTime - apContext->mdStreamTime;      // lfdx +0x30000

    if (ldDelta <= 0.0)                     // fcmpu + ble  (dbl_82001CA8 == 0.0)
    {
        *apuSamples = 0;                    // stw r11, 0(r6)
        return true;                        // li r3, 1
    }

    // frsp -- the product is ROUNDED TO SINGLE before the 256 compare. Keeping the whole
    // expression in double on the host would compare a slightly different value at the
    // boundary, so the narrowing is reproduced explicitly.
    const f32 lfFrames = static_cast<f32>(apContext->mpFormat->mfSampleRate * ldDelta);

    if (!(lfFrames < 256.0f))               // blt NOT taken  (flt_820ADBFC == 256.0f)
        return false;                       // li r3, 0 -- *apuSamples deliberately UNWRITTEN

    // fmuls then fctidz then stfiwx: multiply at single precision, truncate toward zero to
    // a 64-bit integer, store only the LOW 32 BITS. The intermediate is 64-bit on the
    // console, so an out-of-range product wraps rather than saturating; the s64 cast
    // reproduces that. (In range this is just a truncating conversion.)
    *apuSamples = static_cast<u32>(
        static_cast<s64>(apContext->mfResampleGain * lfFrames));    // lfsx +0x30028

    return true;                            // li r3, 1
}
```

### `rw::audio::core::SndPlayer1::Declick` @ `0x82B9C1C0`  [DECODED]

**Signature**

```cpp
// DWARF (twin class, GameShared/.../internal/sndplayer1.h:443):
//   rw::audio::core::BufferStatus Declick(Mixer *)
// Non-static member. Register map at the ONLY call site (Process @0x82BA0594, a plain
// `bl` with r3/r4 still holding Process's own two incoming arguments):
//   r3 = this (SndPlayer1*), r4 = Mixer *apContext
rw::audio::core::BufferStatus rw::audio::core::SndPlayer1::Declick(rw::audio::core::Mixer *apContext);
```

**Behaviour**

Full instruction walk (assembly field of 0x82B9C1C0.json). r3 = this, r4 = context.

PROLOGUE / SETUP (0x82B9C1C0..0x82B9C1F0)
  std r30/r31                              ; two nonvolatiles saved (no LR save -- leaf)
  addis r30, r4, 3 ; addi r30, r30, 0x10   ; r30 = &apContext->mpDstBuffer   (+0x30010)
  lhz  r11, 0x1C2(r3)                      ; r11 = mDeclickBufferOffset
  lbz  r10, 0x1CC(r3)                      ; r10 = mNumDeclickSamples   (the REMAINING count)
  lhz  r9,  0x1C0(r3)                      ; r9  = mSamplesRequested
  add  r7,  r11, r3                        ; r7  = GetDeclickBuffer()  (f32* per channel)
  cmplw cr6, r10, r9                       ; UNSIGNED compare remaining vs requested
  lwz  r11, 0(r30)                         ; r11 = apContext->mpDstBuffer  (loaded BEFORE the swap)
  bge  cr6, +8                             ; remaining >= requested -> keep r9
  mr   r9, r10                             ; else r9 = remaining
                                           ; => r9 = luCount = min(remaining, requested)

RAMP (0x82B9C1F0..0x82B9C268), skipped entirely when mOutputChannels == 0
  lbz  r8, 0x21(r3)                        ; r8 = mOutputChannels  (PlugIn base +0x21)
  cmplwi r8, 0 ; beq loc_82B9C26C
  extsw r5, r10                            ; the divisor is the FULL remaining count,
                                           ;   NOT the capped luCount
  lhz  r31, 0xE(r11)                       ; r31 = dst->muStride
  lwz  r8,  4(r11)                         ; r8  = dst->mpSamples   (channel-0 base)
  lbz  r6,  0x21(r3)                       ; r6  = channel loop counter (re-read)
  rotlwi r31, r31, 2                       ; r31 = muStride * 4  -> BYTE stride per channel
  std/lfd/fcfid/frsp                       ; f13 = (f32)(s64)remaining
  lfs  f0, flt_82001C98                    ; 1.0f
  fdivs f12, f0, f13                       ; f12 = lfStep = 1.0f / remaining

  loc_82B9C22C:                            ; per channel
    lfs  f0, 0(r7)                         ; f0 = lfValue = declick[ch]  (the saved last sample)
    cmplwi cr6, r9, 0
    fmuls f13, f0, f12                     ; f13 = lfDelta = lfValue * lfStep
                                           ;   COMPUTED ONCE from the ORIGINAL value
    beq  cr6, loc_82B9C25C                 ; luCount == 0 -> emit nothing, do NOT store back
    mr   r5, r8 ; mr r11, r9
    loc_82B9C244:
      fsubs f0, f0, f13                    ; lfValue -= lfDelta
      stfs  f0, 0(r5)                      ; channelBase[i] = lfValue
      addic. r11, r11, -1 ; addi r5, r5, 4
      bne   loc_82B9C244
    stfs f0, 0(r7)                         ; declick[ch] = the running value (RESUME point)
  loc_82B9C25C:
    addic. r6, r6, -1
    add  r8, r31, r8                       ; channelBase += muStride*4 BYTES
    addi r7, r7, 4                         ; ++declick
    bne  loc_82B9C22C

ACCOUNT + PUBLISH + SWAP (0x82B9C26C..0x82B9C2D4)
  addis r11, r4, 3 ; addi r11, r11, 0xC    ; r11 = &apContext->mpSrcBuffer   (+0x3000C)
  subf  r10, r9, r10                       ; *** r10 = remaining - luCount ***
  stb   r10, 0x1CC(r3)                     ; mNumDeclickSamples = remaining - PUBLISHED COUNT
  lwz   r5, 0(r11)                         ; old src
  lwz   r10, 0(r30)                        ; old dst
  stw   r5, 0(r30)                         ; mpDstBuffer = old src
  stw   r10, 0(r11)                        ; mpSrcBuffer = old dst   (the ping-pong)
  lbz   r11, 0x21(r3) ; stbx r11, r4, 0x3002C   ; mbChannelCount = mOutputChannels
  lfs   f0, 0x1BC(r3) ; stfsx f0, r4, 0x30024   ; mfSampleRate  = mPreviousSampleRate
  stwx  r9, r4, 0x30020                    ; mNumSamples    = luCount
  lbz   r11, 0x1CC(r3)
  cmplwi r11, 0
  bne   +8
  stb   r11, 0x1CB(r3)                     ; remaining hit 0 -> mDcOffsetsGathered = 0
  li    r3, 1                              ; BUFFERSTATUS_AVAILABLE, unconditionally
  ld    r30/r31 ; blr

CONFIRMED, AGAINST THE ARCHITECTURE REPORT: the update at 0x82B9C270 is `subf r10, r9, r10`, i.e. r10 = r10 - r9 = mNumDeclickSamples MINUS THE PUBLISHED COUNT. It is NOT a unit decrement. progress/scratch_dossiers/sndplayer1_decode_codex.md section 4 ("decrements +0x1CC") is WRONG and must not be inherited. Because luCount = min(remaining, requested), the subtraction can never underflow the byte, and the sequence remaining -> remaining-count -> ... terminates in ceil(remaining/requested) calls.

WHEN IT REACHES ZERO (0x82B9C2B8..0x82B9C2C4): the byte at +0x1CB, mDcOffsetsGathered, is cleared. That byte is the SECOND half of Process's declick-dispatch guard (Process @0x82BA057C tests +0x1CC != 0 AND +0x1CB != 0), so clearing it disarms the declick path for good until the next successful decode re-arms it (Process @0x82BA0BC0 `stb 1, 0x1CB`). Nothing else is reset -- mNumDeclickSamples is already 0 by then and the declick float array keeps its (now ~0.0f) values.

RAMP GEOMETRY: lfDelta is computed ONCE per channel per call, from the value standing in the declick slot, using 1/remaining-at-entry. Within a call that is a straight linear ramp of slope value/remaining. ACROSS calls it is still ONE straight line: after publishing `count` samples the slot holds value*(1 - count/remaining) and the remaining count is remaining-count, so the next call's step is (value*(remaining-count)/remaining) / (remaining-count) = value/remaining -- the identical slope. The ramp therefore lands exactly on 0.0f as the last of `remaining` samples is emitted.

EDGE CASES
  * luCount == 0 (mSamplesRequested == 0): every channel computes lfDelta, writes nothing, and does NOT store back. mNumDeclickSamples is unchanged (remaining - 0), mNumSamples publishes 0, the buffers still swap, and it still returns 1.
  * mOutputChannels == 0: the whole ramp block is jumped over; the publish/swap/account tail still runs.
  * Division by zero is impossible via Process (the +0x1CC != 0 guard), but this function does not check it itself -- 1.0f/0.0f would be +inf. Reproduce without adding a guard.
  * The samples BEYOND luCount in the destination buffer are NOT cleared; only luCount samples are written and only luCount are published.

**Constants**

flt_82001C98   va 0x82001C98   file_off = 0x3000 + 0x82001C98 - 0x82000000 = 0x4C98
               raw BE: 3F 80 00 00                  decoded: (f32) 1.0f
               role: the numerator of the ramp step at 0x82B9C228 (`fdivs f12, f0, f13`).

No other rodata is referenced. Everything else is an immediate or an instance/context offset:
  +0x21   u8  mOutputChannels        (PlugIn base; the ramp's channel bound)
  +0x1BC  f32 mPreviousSampleRate    (published as Mixer::mfSampleRate)
  +0x1C0  u16 mSamplesRequested      (the publish cap)
  +0x1C2  u16 mDeclickBufferOffset   (GetDeclickBuffer())
  +0x1CB  u8  mDcOffsetsGathered     (cleared when the ramp runs out)
  +0x1CC  u8  mNumDeclickSamples     (the remaining ramp length; SUBTRACTED from)
  Mixer +0x3000C/+0x30010/+0x30020/+0x30024/+0x3002C, SampleBuffer +0x04/+0x0E.

(For cross-reference: Process's declick DISPATCH guard and the arming store use the same
two bytes; the 0.0 sentinel dbl_82001CA8 and the 256.0f horizon flt_820ADBFC belong to
WaitForStartTime/Process, not to Declick.)

**Host hazards**

* THE SUBTRACTION, NOT A DECREMENT (the inherited error). `subf r10, r9, r10` at 0x82B9C270 with r9 = the published count. A `--mNumDeclickSamples` transliteration would stretch a 64-sample declick over 64 mix frames instead of one, and would leave mDcOffsetsGathered armed for ~16000 extra frames -- an audible, self-sustaining tail. Write the subtraction.
* CHANNEL-BOUND MISMATCH (a live console hazard, reproduce but flag): the ramp loop is bounded by mOutputChannels (+0x21), which the FORMAT HANDSHAKE in Process MUTATES to the incoming request's channel count (Process @0x82BA0C08 `stb r11, 0x21`). The declick float array, however, was sized at CreateInstance from the ORIGINAL output-channel count. Process's own capture loop is clamped by mMaxChannels (+0x1C6, never mutated); Declick is NOT. A format change to more channels than the instance was created with therefore walks the ramp past the declick array and into the RequestInternal table. Faithful reproduction means keeping the mOutputChannels bound; add an assert, not a clamp, and say so in the comment.
* muStride is a SAMPLE stride, not a byte stride. The console's `rotlwi r31, r31, 2` exists only because it advances a raw byte pointer. On the host, index `mpSamples[muStride * ch + i]`. Re-deriving a byte stride by hand is the classic way to double-scale this loop.
* `extsw r5, r10` sign-extends the ramp length before `fcfid`: the divisor conversion goes through a SIGNED 64-bit value. mNumDeclickSamples is a byte so it is always 0..255 and the sign is moot, but keep the s32 cast so the conversion is the same one the console performs (an unsigned->float conversion is a different instruction).
* No division guard. 1.0f/0.0f is +inf here; only Process's dispatch guard prevents it. Do NOT add an early-out for luRemaining == 0 -- that would change which byte stores happen (the swap/publish tail runs unconditionally on the console).
* luCount == 0 must still fall through the channel loop (computing lfDelta and skipping the store-back) and must still perform the swap, the three context publishes and the return of 1. An early `if (luCount == 0) return ...` diverges: the console still ping-pongs the buffers on that path.
* The declick slot is stored back ONLY when luCount != 0. Hoisting the store-back out of the `if` writes the unchanged value -- harmless today, but it is not what the asm does and it hides the count==0 case.
* mpDstBuffer is captured BEFORE the swap and is what the ramp writes into; the SAME descriptor is what the swap then publishes as mpSrcBuffer. Reading mpDstBuffer after the swap (as a re-ordered sketch might) writes to the wrong region.
* The IDA pseudocode models r4/r5 as one `__int64 a2` and writes `HIDWORD(a2) + 196624`. That is an artefact: r4 alone is the Mixer, and 196624 == 0x30010. Ignore the pseudocode's 64-bit framing entirely.
* Return type: the console `li r3, 1` is rw::audio::core::BUFFERSTATUS_AVAILABLE (base.h:319, DWARF). Process forwards this return unchanged as its own (`bl Declick ; b <epilogue>`), so it must stay 1.

**Implementation sketch**

```cpp
// -------------------------------------------------------------------------------------
// SndPlayer1::Declick @0x82B9C1C0 -- ramp the last emitted sample of every output channel
// down to silence over mNumDeclickSamples samples, a slice per mix frame, then publish and
// ping-pong. Armed by Process (mDcOffsetsGathered) when a request stopped mid-waveform.
//
// ALWAYS returns BUFFERSTATUS_AVAILABLE.
//
// *** THE COUNT UPDATE IS A SUBTRACTION, NOT A DECREMENT ***
//   subf r10, r9, r10 ; stb r10, 0x1CC(r3)
// mNumDeclickSamples -= the count just PUBLISHED. (The architecture report's section 4
// claim that it "decrements" is wrong.) When it reaches zero, mDcOffsetsGathered is
// cleared, which disarms Process's declick dispatch until the next successful decode.
// -------------------------------------------------------------------------------------
BufferStatus SndPlayer1::Declick(AudioProcessContext *apContext)
{
    SampleBuffer *lpDst = apContext->mpDstBuffer;          // lwz +0x30010, BEFORE the swap
    f32 *lpDeclick = GetDeclickBuffer();                   // (u8*)this + mDeclickBufferOffset

    const u32 luRemaining = mNumDeclickSamples;            // lbz +0x1CC (the FULL remaining)

    // cmplw + bge -- an UNSIGNED min of the remaining ramp against this frame's request.
    u32 luCount = mSamplesRequested;                       // lhz +0x1C0
    if (luRemaining < luCount)
        luCount = luRemaining;

    // The channel bound is mOutputChannels (PlugIn base +0x21), NOT mMaxChannels.
    if (mOutputChannels != 0)
    {
        // fcfid/frsp then fdivs: the reciprocal is taken over the FULL remaining count,
        // never over luCount. That is what keeps the ramp one straight line across the
        // several frames it takes to run out.
        const f32 lfStep = 1.0f / static_cast<f32>(static_cast<s32>(luRemaining));

        for (u32 luChannel = 0; luChannel < mOutputChannels; ++luChannel)
        {
            f32 lfValue = lpDeclick[luChannel];            // lfs 0(r7)
            const f32 lfDelta = lfValue * lfStep;          // fmuls -- ONCE, before the loop

            if (luCount != 0)                              // beq skips the inner loop AND
            {                                              //   the store-back below
                // muStride is the PER-CHANNEL SAMPLE stride; the console's `rotlwi ,2`
                // turns it into a byte stride only because it walks a raw pointer. On the
                // host, index the f32 array -- never multiply a host stride by 4 yourself.
                f32 *lpChannel = lpDst->mpSamples + lpDst->muStride * luChannel;
                for (u32 luSample = 0; luSample < luCount; ++luSample)
                {
                    lfValue -= lfDelta;                    // fsubs
                    lpChannel[luSample] = lfValue;         // stfs
                }
                lpDeclick[luChannel] = lfValue;            // stfs 0(r7) -- resume point
            }
        }
    }

    // *** THE SUBTRACTION *** -- subf r10, r9, r10 ; stb r10, 0x1CC(r3)
    mNumDeclickSamples = static_cast<u8>(luRemaining - luCount);

    // The ping-pong, done AFTER the ramp (Process's decode path does the same swap).
    SampleBuffer *lpOldSrc = apContext->mpSrcBuffer;       // lwz +0x3000C
    apContext->mpDstBuffer = lpOldSrc;
    apContext->mpSrcBuffer = lpDst;                        // the ramped buffer is now src

    apContext->mbChannelCount = mOutputChannels;           // stbx +0x3002C
    apContext->mfSampleRate   = mPreviousSampleRate;       // stfsx +0x30024 (lfs +0x1BC)
    apContext->mNumSamples    = luCount;                   // stwx  +0x30020

    // Ramp exhausted -> disarm Process's declick dispatch.
    if (mNumDeclickSamples == 0)
        mDcOffsetsGathered = 0;                            // stb +0x1CB

    return BUFFERSTATUS_AVAILABLE;                         // li r3, 1 -- every path
}
```

### `rw::audio::core::SndPlayer1::AdvanceCurrentRequest` @ `0x82B9C2E8`  [DECODED]

**Signature**

```cpp
// DWARF (twin class, GameShared/.../internal/sndplayer1.h -> sndplayer1shared.cpp:14):
//   void AdvanceCurrentRequest()
// Non-static member; r3 = this. The console leaves `this` in r3 on return (a dead
// passthrough IDA types as `int`), and both call sites (Process @0x82BA061C and
// @0x82BA09D4) discard it.
void rw::audio::core::SndPlayer1::AdvanceCurrentRequest();
```

**Behaviour**

Full instruction walk (assembly field of 0x82B9C2E8.json).

RING ADVANCE (0x82B9C2E8..0x82B9C30C)
  lbz  r11, 0x1C9(r3)      ; r11 = mCurrentRequest
  lbz  r10, 0x1CA(r3)      ; r10 = mMaxRequests
  addi r11, r11, 1
  clrlwi r11, r11, 24      ; (u8)(mCurrentRequest + 1)   -- wraps at 256 as a byte first
  mr   r9, r11
  cmplw cr6, r9, r10
  stb  r11, 0x1C9(r3)      ; STORE the incremented value FIRST, unconditionally
  li   r10, 0
  bne  cr6, +8
  stb  r10, 0x1C9(r3)      ; then overwrite with 0 when it equalled mMaxRequests

Note the two-store shape: the incremented byte is committed and only then replaced by 0.
The wrap test is `== mMaxRequests`, not `>=`, so a corrupt cursor already past the max
would never wrap. Faithful behaviour is `if (++cursor == mMaxRequests) cursor = 0;` with
the byte truncation applied to the increment.

RE-POINT + UNCONDITIONAL CLEARS (0x82B9C310..0x82B9C32C)
  lbz  r9,  0x1C9(r3)      ; RE-READ the (possibly wrapped) cursor
  lhz  r11, 0x1C4(r3)      ; mRequestInternalOffset
  mulli r9, r9, 0x30       ; * console sizeof(RequestInternal)
  stw  r10, 0x1A8(r3)      ; mCurrentRequestSamplesPlayed = 0
  add  r11, r11, r9
  stw  r10, 0x1AC(r3)      ; mCurrentRequestNumSamples    = 0
  add  r11, r11, r3        ; r11 = GetRequestInternal(mCurrentRequest)

Both clears happen BEFORE the validity test and are therefore unconditional.
mCurrentRequestHandle (+0x1A0) and mCurrentRequestSampleRate (+0x1A4) are NOT cleared --
on the invalid path they keep their STALE values. That asymmetry is deliberate: Process's
zero-length-request loop relies on numSamples going to 0, and the ISREQUESTDONE event path
reads the handle.

VALIDITY TEST -- the inlined IsRequestActive (0x82B9C32C..0x82B9C34C)
  lbz  r9, 0x2A(r11)       ; r9 = req->state
  cmpwi cr6, r9, 4 ; beq loc_82B9C344      ; state == E_COMPLETE(4)  -> invalid
  cmpwi cr6, r9, 0 ; li r9, 1 ; bne +8     ; state != E_FREE(0)      -> valid (r9 = 1)
  loc_82B9C344: mr r9, r10                 ; fallthrough (state == 0) -> invalid (r9 = 0)
  clrlwi. r9, r9, 24
  beqlr                                    ; invalid -> RETURN with the clears standing

  => valid  <=>  (state != E_FREE) && (state != E_COMPLETE)
  The intermediate states E_QUEUED(1), E_FEEDING(2), E_FEEDCOMPLETE(3) are all "active".

CACHE REFRESH (0x82B9C350..0x82B9C36C), valid requests only
  stw  r10, 0x1A8(r3)      ; mCurrentRequestSamplesPlayed = 0  (redundant second store,
                           ;   present in the binary; harmless, reproduce or note)
  lfs  f0, 0xC(r11)  ; stfs f0, 0x1A0(r3)   ; mCurrentRequestHandle     = req->requestHandle
  lfs  f0, 0x10(r11) ; stfs f0, 0x1A4(r3)   ; mCurrentRequestSampleRate = req->sampleRate
  lwz  r11, 0x14(r11); stw  r11, 0x1AC(r3)  ; mCurrentRequestNumSamples = req->numSamples
  blr

The two f32 fields are moved with lfs/stfs -- a float-register copy, not a word copy. It
matters only for signalling-NaN payloads; a f32 assignment on the host is equivalent.

CALLER CONTEXT: Process calls this in exactly two places -- (1) 0x82BA061C, after marking
a ZERO-LENGTH request E_COMPLETE, inside the scan loop that keeps advancing until it finds
a request with numSamples != 0 or runs out; (2) 0x82BA09D4, after a request played to its
end with no loop point. Both recompute the request pointer from mCurrentRequest afterwards
rather than trusting anything this function returns.

**Constants**

No rodata. Every value is an immediate or an instance offset:
  0x30    console sizeof(RequestInternal)  -- MUST NOT be transliterated (see hazards)
  4       E_COMPLETE   (DWARF RequestState, GameShared/.../internal/sndplayer1.h)
  0       E_FREE
  +0x1A0  f32 mCurrentRequestHandle
  +0x1A4  f32 mCurrentRequestSampleRate
  +0x1A8  s32 mCurrentRequestSamplesPlayed
  +0x1AC  s32 mCurrentRequestNumSamples
  +0x1C4  u16 mRequestInternalOffset
  +0x1C9  u8  mCurrentRequest
  +0x1CA  u8  mMaxRequests
  RequestInternal +0x0C requestHandle / +0x10 sampleRate / +0x14 numSamples / +0x2A state

**Host hazards**

* RECORD STRIDE (the x64 trap): `mulli r9, r9, 0x30` is the CONSOLE sizeof(RequestInternal). That record holds `Decoder *pDecoder` at +0x08 and a leading `f64 startTime`, so on x64 it becomes 0x38 (0x30 + 4 bytes of pointer growth + 4 of tail alignment). The host expression is `GetRequestInternal(index)` over a typed `RequestInternal*`; never `(u8*)this + offset + 0x30*index`. The same applies to mRequestInternalOffset itself -- it must be produced by the one host ComputeLayout(config) helper that GetSize and CreateInstance also use, and asserted to fit its u16 field.
* The wrap test is EQUALITY (`bne cr6`). If mCurrentRequest ever exceeds mMaxRequests it never wraps and the next GetRequestInternal indexes out of the allocation. Reproduce `==`; do not "harden" it to `>=`.
* The increment is truncated to a byte BEFORE the comparison (`clrlwi r11, r11, 24`). With mMaxRequests == 0 (never produced by the committed create path, which defaults the constructor param to 1) the cursor would run 1..255 and wrap at 256. Keep the static_cast<u8> on the increment so that degenerate case behaves identically.
* mCurrentRequestHandle / mCurrentRequestSampleRate are NOT cleared on the invalid path. Zeroing them "for tidiness" changes the ISREQUESTDONE event answer (EventEvent compares the queried handle against mCurrentRequestHandle) and changes what Process republishes. Leave them stale.
* The duplicate `mCurrentRequestSamplesPlayed = 0` on the valid path is real (0x82B9C31C then 0x82B9C350). Keep it with a comment rather than deleting it -- deleting it is a silent divergence from the store sequence even though the value is identical.
* The two f32 refreshes are lfs/stfs (float-register copies). Assigning f32-to-f32 on the host is equivalent; do NOT convert them to u32 word copies or to double.
* The console returns `this` in r3 (IDA types the function `int`); both call sites discard it. Declare the host function `void`, as the DWARF does. Do not invent a bool "found an active request" return -- Process re-tests the state itself at 0x82BA0634 and 0x82BA09EC.
* `state` is a u8 holding rw::audio::core::SndPlayer1::RequestState (FREE=0, QUEUED=1, FEEDING=2, FEEDCOMPLETE=3, COMPLETE=4, from the twin's DWARF). The `cmpwi` comparisons are on the zero-extended byte; keep the member u8 and compare against the enum, not against an int-typed field.

**Implementation sketch**

```cpp
// -------------------------------------------------------------------------------------
// SndPlayer1::AdvanceCurrentRequest @0x82B9C2E8 -- step the request ring cursor and
// refresh the four cached "current request" fields from the new slot.
//
// The two COUNT caches are cleared unconditionally; the handle and sample rate are
// refreshed ONLY for an active slot and are deliberately left STALE otherwise.
// -------------------------------------------------------------------------------------
void SndPlayer1::AdvanceCurrentRequest()
{
    // addi + clrlwi: the increment is truncated to a byte BEFORE the wrap test, and the
    // test is `== mMaxRequests`, never `>=`.
    mCurrentRequest = static_cast<u8>(mCurrentRequest + 1);   // stb, unconditional
    if (mCurrentRequest == mMaxRequests)
        mCurrentRequest = 0;                                  // stb again

    // *** HOST EXPRESSION ***: the console `mulli r9, r9, 0x30` is the CONSOLE
    // sizeof(RequestInternal), and RequestInternal contains a 32-bit Decoder* (+0x08) and
    // a leading f64, so 0x30 does NOT survive x64 (host sizeof is 0x38 with the natural
    // f64 alignment). Index the typed array; mRequestInternalOffset must itself come from
    // the single host ComputeLayout() helper, never from the console literal 0x1D8/0x30.
    RequestInternal *lpRequest = GetRequestInternal(mCurrentRequest);

    // Both clears precede the validity test -- unconditional.
    mCurrentRequestSamplesPlayed = 0;    // stw +0x1A8
    mCurrentRequestNumSamples    = 0;    // stw +0x1AC

    // The inlined IsRequestActive: FREE and COMPLETE are dead; QUEUED / FEEDING /
    // FEEDCOMPLETE are all live.
    if (lpRequest->state == E_FREE || lpRequest->state == E_COMPLETE)
        return;                          // beqlr -- mCurrentRequestHandle and
                                         //   mCurrentRequestSampleRate stay STALE

    mCurrentRequestSamplesPlayed = 0;    // the binary stores it a second time; kept so the
                                         //   store sequence matches instruction-for-instruction
    mCurrentRequestHandle     = lpRequest->requestHandle;  // lfs/stfs +0x0C -> +0x1A0
    mCurrentRequestSampleRate = lpRequest->sampleRate;     // lfs/stfs +0x10 -> +0x1A4
    mCurrentRequestNumSamples = lpRequest->numSamples;     // lwz/stw  +0x14 -> +0x1AC
}
```

### `rw::audio::core::SndPlayer1::Process` @ `0x82BA0568`  [DECODED]

**Signature**

```cpp
// Installed in PlugInDescRunTime::pProcess; Mixer::ProcessInputPlugIns / Mixer::Execute
// cast the slot to  int (*)(PlugIn*, Mixer*, int)  (Mixer.cpp:61, bctrl @0x82B6A1F4).
// DWARF (twin class, GameShared/.../internal/sndplayer1.h:387):
//   rw::audio::core::BufferStatus Process(rw::audio::core::PlugIn *, Mixer *, bool)
// Register map: r3 = PlugIn* self (-> r31), r4 = Mixer* (-> r24), r5 = the bool
// (decode-attested UNUSED -- overwritten with 0 at 0x82BA05C4 before any read).
static rw::audio::core::BufferStatus rw::audio::core::SndPlayer1::Process(
        rw::audio::core::PlugIn *apPlugIn,
        rw::audio::core::Mixer *apContext,
        bool /*abAlreadyProcessedThisFrame*/);
```

**Behaviour**

428 instructions. Register contract established at 0x82BA0574: r31 = self, r24 = apContext. Nonvolatile locals: r15 = the constant 0; r16/r17/r18/r19 = the Mixer offsets 0x30020/0x3000C/0x3002C/0x30024; r20 = luSkipped; r21 = the carved scratch top (doubles as the "a carve is outstanding" flag); r22 = the SAVED scratch top; r23 = the constant 4 (E_COMPLETE); r25 = luAvailable; r26 = the decode request count; r28 = the skip countdown; r30 = the current RequestInternal*; r5 = luProduced (proven to survive every call on its live paths -- see hazards). Stack: one i32 at r1+0x50 (0xF0+var_A0), the WaitForStartTime out parameter.

=== 1. DECLICK DISPATCH (0x82BA057C..0x82BA0598) ===
  lbz r11, 0x1CC(r31) ; beq loc_82BA059C      ; mNumDeclickSamples == 0 -> normal path
  lbz r11, 0x1CB(r31) ; beq loc_82BA059C      ; mDcOffsetsGathered  == 0 -> normal path
  bl  Declick                                  ; r3/r4 still hold self/context untouched
  b   loc_82BA0C10                             ; forward r3 -- Declick's 1 -- as the return
BOTH bytes must be non-zero. This is the ONLY exit that bypasses the epilogue at
loc_82BA0AFC, and legitimately so: nothing has been carved yet. The return value is
Declick's own BUFFERSTATUS_AVAILABLE, not the `li r3, 1` at 0x82BA0C0C.

=== 2. ENTRY STATE (0x82BA059C..0x82BA05C4) ===
  mpLoadedDecoder = 0                          ; stw r15, 0x19C  -- EVERY Process entry
  r30 = GetRequestInternal(mCurrentRequest)    ; lbz+0x1C9, lhz+0x1C4, mulli 0x30
  luSkipped = 0 ; carveNew = 0 ; carveSaved = 0 ; luProduced = 0

=== 3. REQUEST / ZERO-LENGTH SCAN (0x82BA05C8..0x82BA0660) ===
  IsRequestActive(req) := (state != 4) && (state != 0)
  if (!active) -> loc_82BA0AFC (epilogue)
  r23 = 4
  loop:
    lwz r11, 0x14(r30)                         ; req->numSamples
    if (numSamples != 0) break                 ; a real request -- go to the handshake
    stb r23, 0x2A(r30)                         ; req->state = E_COMPLETE
    AdvanceCurrentRequest()
    r30 = GetRequestInternal(mCurrentRequest)  ; recomputed, not carried
    if (!IsRequestActive(req)) -> loc_82BA0AFC
  Zero-length requests are RETIRED, not played: marked COMPLETE and stepped over, as many
  as sit consecutively in the ring. Termination is guaranteed because the ring is finite
  and every retired slot becomes COMPLETE, which the validity test rejects on the next lap.

=== 4. FORMAT HANDSHAKE (0x82BA0664..0x82BA0680 -> 0x82BA0BD0) ===
  lfs f0, 0x10(r30) ; lfs f13, 0x1BC(r31) ; fcmpu ; bne cr6, loc_82BA0BD0
     -> req->sampleRate != mPreviousSampleRate  (bne is TAKEN on unordered, so a NaN rate
        also takes the handshake -- exactly what `a != b` gives in C++)
  lbz r11, 0x21(r31) ; lbz r10, 0x2B(r30) ; cmplw ; bne cr6, loc_82BA0BD0
     -> req->numChannels != mOutputChannels
  loc_82BA0BD0 (the handshake body):
    mNumSamples    = 0                         ; stwx r15, r24, 0x30020
    mbChannelCount = req->numChannels          ; stbx    +0x3002C
    mfSampleRate   = req->sampleRate           ; stfsx   +0x30024
    mPreviousSampleRate = req->sampleRate      ; stfs    +0x1BC
    mOutputChannels     = req->numChannels     ; stb     +0x21
    -> loc_82BA0C0C: return 1
  It publishes an EMPTY frame carrying the NEW format, adopts that format, and returns
  AVAILABLE. It does NOT swap the buffers, does NOT touch the declick state, and does NOT
  reach the epilogue -- correct, because the carve is still ahead of it at 0x82BA07EC.
  The next frame re-enters and the comparisons now match.

=== 5. FEED-SLOT SCAN (0x82BA0684..0x82BA06F8) ===
  if (mFeedDesc[mNextFeedSlotToFree].feedState == 0) {
      luFill = mNextFeedSlotToFill;            ; read ONCE, outside the loop (0x82BA069C)
      while (mNextFeedSlotToFree != luFill) {
          u8 next = mNextFeedSlotToFree + 1; if (next == 20) next = 0;   ; MAX_DECODERFEEDS
          mNextFeedSlotToFree = next;          ; stb 0x1CE -- committed each lap
          if (mFeedDesc[next].feedState != 0) break;
      }
  }
  if (mFeedDesc[mNextFeedSlotToFree].feedState != 1) -> loc_82BA0AFC (epilogue)
  Feed states: 0 = empty, 1 = ready to decode, 2 = consumed / awaiting FeedCleanup. The
  scan skips over empties, advancing the consume cursor, and stops at the fill cursor. A
  slot in state 2 also blocks (only state 1 proceeds).

=== 6. START TIME (0x82BA06FC..0x82BA07E8) ===
  lfd f1, 0(r30) ; lfd f12, dbl_82001CA8(=0.0) ; fcmpu ; beq cr6, loc_82BA07EC
     -> startTime == 0.0 exactly means "already armed"; skip straight to the carve.
        (NaN takes the not-equal path into WaitForStartTime, which then declines.)
  WaitForStartTime(self, context, req->startTime, &luFrames)     ; r6 = r1+0x50
  OUTCOME A -- returns 0 (>= 256 output frames away, or NaN):
     mCurrentRequestSamplesPlayed = 0 ; -> loc_82BA0AFC (epilogue -> returns 0)
  OUTCOME B -- returns 1 with luFrames == 0 (start reached):
     stfd f12, 0(r30)                          ; req->startTime = 0.0 -- ARM IT
     fall into the carve at loc_82BA07EC
  OUTCOME C -- returns 1 with luFrames != 0 (near future): emit that many silent samples
     *** THE CAP THE ARCHITECTURE REPORT OMITS *** (0x82BA073C..0x82BA0748):
         lhz r11, 0x1C0(r31) ; cmplw cr6, r26, r11 ; blt cr6, +8 ; mr r26, r11
         -> luFrames = min(luFrames, mSamplesRequested)   [UNSIGNED]
     r28 = &context->mpDstBuffer ; r27 = *r28 ; r25 = luFrames*4 (bytes)
     for (ch = 0; ch < req->numChannels; ++ch)             ; the bound is RE-READ each lap
         XMemSet(dst->mpSamples + dst->muStride*ch, 0, luFrames*4)
     mNumSamples = luFrames                    ; stwx +0x30020
     swap mpSrcBuffer <-> mpDstBuffer          ; the zero-filled buffer becomes src
     mbChannelCount = req->numChannels ; mfSampleRate = req->sampleRate
     mCurrentRequestSamplesPlayed = 0
     -> loc_82BA0C0C: return 1
     This exit also bypasses the epilogue (nothing carved yet) and does NOT capture declick
     samples or set mDcOffsetsGathered -- silence needs no declick.

=== 7. SCRATCH CARVE (0x82BA07EC..0x82BA0810) ===
  lwz  r10, 4(r31)                  ; self->mpSystemUseGetSystemAccessor
  lhz  r11, 0x28(r30)               ; req->decoderInstanceSize (u16)
  addi r9, r11, 0x7F ; clrrwi r9, r9, 7          ; align_up(size, 128)
  lwz  r11, 0(r10)                  ; System::mpObjectTable -> StackAllocator*
  lwz  r10, 0xC(r11)                ; StackAllocator::mpTop
  subf r9, r9, r10                  ; newTop = mpTop - alignedSize  (downward stack)
  r22 = r10 (saved) ; r21 = r9 (new top / carve flag)
  stw  r9, 0xC(r11)                 ; mpTop = newTop
  The reservation IS the codec's working scratch: the region [newTop, savedTop) is what
  the decode callback consumes off the shared audio stack allocator (the same slot [3]
  AiffWriter @0x82B95CC8 and Delay::CreateInstance @0x82BA2790 read). Note there is NO
  null check on req->pDecoder before this first carve; the check exists only on the second
  carve at 0x82BA0A44.

=== 8. DECODER LOAD + FEED AVAILABILITY (0x82BA0814..0x82BA0870) ===
  mpLoadedDecoder = req->pDecoder            ; stw 0x19C
  luAvailable = <inlined Decoder::GetSamplesRemaining(mFeedDesc[free].decoderRequestHandle)>
    handle = mFeedDesc[mNextFeedSlotToFree].decoderRequestHandle    ; lbz +0x68 (feed +0x0C)
    rq     = decoder + decoder->muRequestQueueOffset + 0x14*handle  ; lwz +0x24, mulli 0x14
    if (rq->miEndSample == 0)                       luAvailable = 0
    else if (handle == decoder->mucRequestDecodeIndex)   ; lbz +0x31
                                                   luAvailable = rq->miEndSample
                                                                 - decoder->miCurrentSampleOffset
    else                                           luAvailable = rq->miEndSample
                                                                 - rq->miStartSample
  This is instruction-for-instruction rw::audio::core::Decoder::GetSamplesRemaining
  @0x826914D0 (the twin class calls it out of line; ARTIST's ordinary SndPlayer1 has it
  inlined). Express it as that call on the host.

=== 9. SKIP + DECODE COUNTS (0x82BA0870..0x82BA08B8) ===
  r28 = req->samplesToSkip (+0x1C)
  if (luAvailable < r28) r28 = luAvailable                 ; SIGNED cmpw
  r26 = min(mSamplesRequested, luAvailable - r28)          ; SIGNED cmpw
  r30 = GetRequestInternal(mCurrentRequest)  ; re-materialised, identical value
  r29 = &context->mpDstBuffer ; r27 = *r29   ; the SAME descriptor feeds BOTH loops

=== 10. SKIP LOOP, CAPPED AT 256 PER CALL (0x82BA08BC..0x82BA08E4) ===
  while (r28 != 0) {                                        ; `bne`, not `bgt`
      s32 chunk = (r28 < 256) ? r28 : 256;                  ; SIGNED cmpwi 0x100
      r28 -= chunk;
      luSkipped += Decoder::Decode(mpLoadedDecoder, dst, chunk);
  }
  Every lap decodes INTO THE SAME dst buffer starting at sample 0 (Decoder::Decode's output
  index is its own running count, 0x82B67B94), so each lap overwrites the previous one and
  the final main Decode overwrites them all. THAT is the discard mechanism -- there is no
  scratch buffer for skipped audio. luSkipped accumulates the ACTUAL returns, which can be
  less than requested if the decoder runs dry; the loop still terminates because r28 is
  driven by the requested chunk, not by the return.

=== 11. MAIN DECODE + PUBLISH/SWAP (0x82BA08E8..0x82BA0920) ===
  luProduced = Decoder::Decode(mpLoadedDecoder, dst, r26)   ; called even when r26 == 0
  lpOldSrc = context->mpSrcBuffer
  context->mpSrcBuffer = dst        ; the FILLED descriptor becomes src
  context->mNumSamples = luProduced
  context->mpDstBuffer = lpOldSrc   ; ping-pong
  context->mbChannelCount = req->numChannels ; context->mfSampleRate = req->sampleRate
  BUFFER CONTRACT: the decoder is handed the descriptor sitting in mpDstBuffer BEFORE the
  swap; on return that descriptor is mpSrcBuffer. The console passes the Mixer's
  SampleBuffer* straight into Decoder::Decode(DecoderBuffer*) -- a deliberate type pun
  (Decode reads only +0x04 mpSamples/mpData and +0x0E muStride).

=== 12. ACCOUNTING (0x82BA0924..0x82BA0988) ===
  mCurrentRequestHandle = req->requestHandle                ; lfs/stfs +0x0C -> +0x1A0
  if (mCurrentRequestSamplesPlayed == 0)                    ; first output for this request
      mCurrentRequestSamplesPlayed = req->seekStreamSampleOffset (+0x24)
                                   + req->seekDecoderSampleOffset (+0x20)
  luRemainingInFeed = (luAvailable - luProduced) - luSkipped ; r7, computed here for step 14
  mCurrentRequestSamplesPlayed += luProduced + luSkipped
  mCurrentRequestSampleRate = req->sampleRate ; mCurrentRequestNumSamples = req->numSamples
  mFeedDesc[mNextFeedSlotToFree].chunkSamplesPlayed += luProduced + luSkipped   ; +0x64

=== 13. LOOP / END (0x82BA098C..0x82BA0A4C) ===
  if (mCurrentRequestSamplesPlayed != req->numSamples) -> step 14   ; EXACT equality
  if (req->loopStart >= 0) { mCurrentRequestSamplesPlayed = req->loopStart; -> step 14 }
  ELSE -- the sample ended and there is no loop point:
     req->state = E_COMPLETE (r23)
     if (mpLoadedDecoder != 0) {                            ; RESTORE THE CARVE NOW
         mpLoadedDecoder = 0
         GetStack()->mpTop = carveSaved                     ; stw r22, 0xC(r11)
     }
     AdvanceCurrentRequest()
     next = GetRequestInternal(mCurrentRequest)             ; r8, NOT written back to r30
     if (IsRequestActive(next) && next->pDecoder != 0) {    ; NULL CHECK present here
         carveSaved = GetStack()->mpTop
         carveNew   = carveSaved - align_up(next->decoderInstanceSize, 128)
         GetStack()->mpTop = carveNew
         mpLoadedDecoder = next->pDecoder
     }
     -> step 14
  r30 is deliberately NOT updated to the new request; no later path reads it.

=== 14. FEED ROLLOVER (loc_82BA0AF4 / loc_82BA0A50, 0x82BA0AF4 + 0x82BA0A50..0x82BA0AF0) ===
  while (luRemainingInFeed == 0) {
      feed = &mFeedDesc[mNextFeedSlotToFree];
      if (feed->feedState != 1) -> epilogue;                ; nothing consumable
      feed->feedState = 2;                                  ; consumed; FeedCleanup releases it
      u8 next = mNextFeedSlotToFree + 1; if (next == 20) next = 0;
      Decoder *dec = mpLoadedDecoder;                       ; lwz 0x19C BEFORE the stb
      mNextFeedSlotToFree = next;
      if (dec == 0) break;
      if (mFeedDesc[next].feedState != 1) break;
      luRemainingInFeed = <inlined GetSamplesRemaining(dec, mFeedDesc[next].decoderRequestHandle)>;
      ; a second empty record (miEndSample == 0) yields 0 and the loop consumes it too
  }

=== 15. EPILOGUE / SCRATCH RESTORE (loc_82BA0AFC, 0x82BA0AFC..0x82BA0B1C) ===
  if (mpLoadedDecoder != 0) {
      mpLoadedDecoder = 0;
      if (carveNew != 0) GetStack()->mpTop = carveSaved;
  }
  The two conditions together are the invariant "a carve is outstanding": carveNew is only
  set alongside a decoder load, and the loop-end path at step 13 already restored + cleared
  in tandem, so the outer mpLoadedDecoder test correctly suppresses a double restore.
  RESTORE COVERAGE, path by path: declick (no carve), invalid request (no carve), format
  handshake (no carve -- the carve is downstream of it), feed-not-ready (no carve),
  far-future start (no carve), near-future zero-fill (no carve); every path that DOES carve
  -- normal decode, loop, end-of-sample, feed rollover -- routes through this epilogue.
  Verified exhaustively against the branch graph.

=== 16. STATUS DERIVATION + LAST-SAMPLE CAPTURE (0x82BA0B20..0x82BA0BCC) ===
  context->mbChannelCount = mOutputChannels        ; ALWAYS -- overwrites step 11's value
  context->mfSampleRate   = mPreviousSampleRate    ; ALWAYS -- likewise
     (identical values whenever the handshake let us through, but they are also stored on
      the no-request / no-feed / far-future paths where req is stale or absent.)
  if (luProduced == 0) {
      if (luSkipped != 0)         { context->mNumSamples = 0; return 1; }
      if (mSamplesRequested == 0) { context->mNumSamples = 0; return 1; }
      return 0;                   ; *** mNumSamples is NOT republished on this path ***
  }
  ; luProduced != 0 -- capture the declick anchors
  u32 n = min(context->mbChannelCount, mMaxChannels);   ; re-reads the byte just stored
  SampleBuffer *src = context->mpSrcBuffer;             ; the JUST-SWAPPED filled buffer
  f32 *declick = GetDeclickBuffer();
  for (ch = 0; ch < n; ++ch)
      declick[ch] = src->mpSamples[src->muStride*ch + luProduced - 1];   ; lfs -4(r8)
  mDcOffsetsGathered = 1;                               ; ARM the declick path
  return 1;

RETURN SUMMARY
  BUFFERSTATUS_AVAILABLE (1): declick dispatch (Declick's own 1); format handshake;
    near-future zero-fill; luProduced != 0; luProduced == 0 with luSkipped != 0;
    luProduced == 0 with mSamplesRequested == 0.
  BUFFERSTATUS_UNAVAILABLE (0): luProduced == 0 AND luSkipped == 0 AND
    mSamplesRequested != 0 -- which is how "no active request", "all requests zero-length",
    "no ready feed slot", "start time more than a frame away" and "the decoder produced
    nothing" all report. On that path mNumSamples keeps its previous value and the caller
    (Mixer::HandleBufferStatusUnavailable) must ignore it; mbChannelCount and mfSampleRate
    ARE still overwritten.

**Constants**

dbl_82001CA8   va 0x82001CA8   file_off = 0x3000 + 0x82001CA8 - 0x82000000 = 0x4CA8
               raw BE: 00 00 00 00 00 00 00 00      decoded: (f64) 0.0
               TWO roles in Process: the `startTime == 0.0` armed sentinel at 0x82BA0708,
               and the value stored back into RequestInternal::startTime at 0x82BA07E8
               (`stfd f12` -- f12 still holds the same load).

Process references NO other rodata word. flt_820ADBFC (256.0f) and flt_82001C98 (1.0f)
belong to its callees WaitForStartTime and Declick respectively (recomputed offsets and
raw bytes are in those two entries). Everything else Process uses is an immediate:

  0x100 / 256   the per-Decode-call skip chunk cap (0x82BA08BC). Numerically equal to
                rw::audio::core::MIXER_FRAME_SIZE (base.h:308, DWARF 256) and
                Mixer::KU_FRAME_SIZE, but here it is a bare `cmpwi cr6, r28, 0x100`.
  0x14 / 20     KU_MAX_DECODERFEEDS -- the feed-ring modulus (0x82BA06BC, 0x82BA0A7C).
                DWARF: `const unsigned char MAX_DECODERFEEDS = 20`
                (SDKs/EATech/include/rw/audio/core/plugins/sndplayer1.h:169) -- this class's
                OWN dump, not the twin's.
  0x7F + clrrwi 7   align_up(decoderInstanceSize, 128) for the scratch carve.
  4             E_COMPLETE   (r23; DWARF RequestState)
  0             E_FREE
  1 / 2         feed states "ready" / "consumed"
  0x30          CONSOLE sizeof(RequestInternal)      -- must NOT be transliterated
  0x10 (rotlwi 4) CONSOLE sizeof(SndPlayer1FeedDesc) -- must NOT be transliterated
  0x14          Decoder request-ring stride (pointer-free; survives, but reach it through
                Decoder::RequestQueue()/GetSamplesRemaining)
  Mixer offsets 0x30000 / 0x3000C / 0x30010 / 0x30018 / 0x30020 / 0x30024 / 0x30028 /
                0x3002C (r16..r19 hold four of them as loop-invariant immediates).
  Instance offsets used: +0x04 mpSystemUseGetSystemAccessor, +0x21 mOutputChannels,
                +0x19C mpLoadedDecoder, +0x1A0/+0x1A4/+0x1A8/+0x1AC the current-request
                cache, +0x1BC mPreviousSampleRate, +0x1C0 mSamplesRequested,
                +0x1C2 mDeclickBufferOffset, +0x1C4 mRequestInternalOffset,
                +0x1C6 mMaxChannels, +0x1C9 mCurrentRequest, +0x1CA mMaxRequests,
                +0x1CB mDcOffsetsGathered, +0x1CC mNumDeclickSamples,
                +0x1CD mNextFeedSlotToFill, +0x1CE mNextFeedSlotToFree,
                feed +0x08 chunkSamplesPlayed / +0x0C decoderRequestHandle / +0x0D feedState.

**Host hazards**

* RECORD STRIDES -- the two X360 literals that contain 32-bit pointers and MUST NOT be transliterated:
    - `mulli r11, r11, 0x30` (four sites) is the CONSOLE sizeof(RequestInternal); that record has `Decoder *pDecoder` at +0x08 and a leading f64, so the host size is 0x38. Host expression: `GetRequestInternal(index)` over a typed array, with mRequestInternalOffset produced by the single host ComputeLayout(config) helper.
    - `rotlwi r11, r11, 4` (six sites) is the CONSOLE sizeof(SndPlayer1FeedDesc) == 0x10; that record holds TWO 32-bit pointers (pChunkInfo at +0x00, the filesys Stream at +0x04 -- both attested by FeedCleanup @0x82BA0308..0x82BA0348, which passes them to rw::core::filesys::Stream::ReleaseChunk), so the host size is 24. Host expression: `mFeedDesc[slot]`.
  The `mulli ,0x14` on the Decoder request ring is the one stride that IS pointer-free and survives -- but express it as Decoder::GetSamplesRemaining()/RequestQueue() anyway.
* NARROWED POINTERS: `StackAllocator::mpTop` is a real pointer. The console's `lwz`/`subf`/`stw` at 0x82BA0800..0x82BA0810 and 0x82BA0A30..0x82BA0A40 must become `u8 *lpCarveSaved` / `u8 *lpCarveNew`, never u32 words. Likewise mpLoadedDecoder (the twin's DWARF types it `uintptr_t`; on the host make it `Decoder *`) and SampleBuffer::mpSamples.
* `System::mpObjectTable` is declared `void*` in the committed PlugIn.h but IS a `StackAllocator*` (Mixer.h defines the type and documents the aliasing). Cast at the use site or retype the member; do NOT index it as `((u32*)mpObjectTable)[3]`. The sketch hoists the lookup to function scope because the epilogue's restore needs it while the console re-loads it at every use -- behaviour-neutral, but note the hoist so a reviewer does not read it as invention.
* SAMPLEBUFFER / DECODERBUFFER TYPE PUN: the console hands `Mixer::mpDstBuffer` (a SampleBuffer*) straight to Decoder::Decode, which reads it as a DecoderBuffer (+0x04 base, +0x0E stride). On x64 the two layouts still happen to agree (SampleBuffer{System*,f32*,u32,u16,u16} vs DecoderBuffer{u32,f32*,u32,u16,u16} both put the pointer at +8 and the stride at +22), so the reinterpret_cast works -- but it is coincidence, not design. Either keep the cast with a static_assert on offsetof for both structs, or give Decode a SampleBuffer overload. Never silently rely on it.
* NaN / UNORDERED POLARITY, three sites:
    - 0x82BA0670 `fcmpu` + `bne` on (req->sampleRate, mPreviousSampleRate): `bne` is TAKEN on unordered, so a NaN rate takes the FORMAT HANDSHAKE. `a != b` in C++ is exactly this. Do not rewrite as `!(a == b)` with the branches swapped.
    - 0x82BA070C `fcmpu` + `beq` on (req->startTime, 0.0): `beq` is NOT taken on unordered, so a NaN start time goes to WaitForStartTime (which then declines). `a != 0.0` gives this. Do not write it inverted.
    - WaitForStartTime's own two compares -- see that function's hazards.
* SIGNED vs UNSIGNED comparisons are mixed and load-bearing:
    - `cmplw` (UNSIGNED): the zero-fill cap against mSamplesRequested (0x82BA0740), the declick channel min (0x82BA0B6C), the feed-cursor equality tests.
    - `cmpw`  (SIGNED): the skip clamp against liAvailable (0x82BA0874), the decode-count clamp (0x82BA0888), the 256 chunk cap (0x82BA08BC), the played-vs-numSamples equality (0x82BA0994), the loopStart sign test (0x82BA09A0).
  liAvailable can legitimately be 0; a negative would only come from corrupt decoder state. Keeping the signedness exact is what makes the corrupt case behave identically.
* THE SKIP LOOP TERMINATES ON `!= 0`, NOT `> 0` (0x82BA08E0 `bne`). With a negative liToSkip the first lap takes the whole value as its chunk (liToSkip < 256) and drives it to 0 in one pass, which still terminates. Rewriting the loop as `while (liToSkip > 0)` changes that path.
* THE MAIN DECODE IS CALLED EVEN WITH COUNT 0 (0x82BA08E8). Guarding it with `if (liToDecode)` skips the publish/swap that follows unconditionally in the asm. Do not add the guard.
* THE PUBLISH IS OVERWRITTEN: step 11 stores req->numChannels / req->sampleRate into the context, and step 16 immediately overwrites both with mOutputChannels / mPreviousSampleRate on every epilogue path. Identical values past the handshake -- but a "simplification" that removes either store diverges on the no-request / far-future / no-feed paths, where step 16 fires with no valid request at all.
* STATUS 0 LEAVES mNumSamples STALE (0x82BA0B50 returns without a `stwx` to +0x30020). Callers must ignore it; do not helpfully zero it.
* r5 (liProduced) LIVENESS: r5 is a VOLATILE GPR yet the compiler keeps liProduced in it across `bl WaitForStartTime` and `bl AdvanceCurrentRequest`. Both callees provably never write r5 (verified against their full assembly), so the compiler exploited interprocedural knowledge. The same applies to f12 holding 0.0 across the WaitForStartTime call before `stfd f12, 0(r30)` at 0x82BA07E8. Neither is a bug and neither survives into C++ -- an ordinary local reproduces both -- but do NOT "fix" the store at 0x82BA07E8 into something other than 0.0 on the theory that f12 was clobbered: dbl_82001CA8 is provably 0.0 and WaitForStartTime touches only f0/f13.
* NO NULL CHECK ON pDecoder AT THE FIRST CARVE (0x82BA07EC..0x82BA0828 dereferences it immediately). The second carve at 0x82BA0A44 DOES check. Reproduce the asymmetry; add an assert on the first if you must, not a branch.
* DECLICK CHANNEL-BOUND ASYMMETRY: the capture loop here is clamped by mMaxChannels (+0x1C6, fixed at create time) while Declick's ramp is bounded by mOutputChannels (+0x21), which THIS function mutates in the format handshake. A request with more channels than the instance was created for therefore makes Declick walk past the declick array. Faithful; flag it in the header comment.
* mNumDeclickSamples IS NEVER SET BY Process. Process only ARMS mDcOffsetsGathered = 1; the producer of mNumDeclickSamples is outside this cluster (the stop/expel path). Do not invent a store for it.
* THE FEED CURSOR IS COMMITTED EVERY LAP of the scan (`stb r11, 0x1CE` inside the loop at 0x82BA06C8, and again at 0x82BA0A8C). If a later step bails, the cursor stays where the scan left it. That is the console's behaviour; do not buffer the cursor in a local and write it once.
* `mMaxChannels` (+0x1C6) vs `mOutputChannels` (+0x21) vs `req->numChannels` (+0x2B) are three DIFFERENT bytes used in three different places. Mixing them up silently truncates or overruns the capture loop.
* THE THIRD FEED CURSOR: FeedCleanup @0x82BA0268 uses a byte at +0x1CF that trails mNextFeedSlotToFree; the twin's DWARF member list names only Fill and Free, so +0x1CF has NO DWARF name. Process never touches it, so it is out of this cluster -- but the earlier architecture report calls +0x1CF an "ARTIST-only/unknown byte with no semantic reader", which is now WRONG: FeedCleanup reads and advances it as the chunk-release cursor (0x82BA0278, 0x82BA034C..0x82BA0364). Name it descriptively (e.g. mNextFeedSlotToCleanUp) and mark the NAME, not the semantics, as reconstructed.
* RequestInternal +0x1C/+0x20/+0x24 NAMES ARE RECONSTRUCTED (the twin has no such fields). Semantics are attested by the sole writer, SndPlayer1::SetSeekData @0x82B9C068: +0x20 and +0x24 take SeekTableParser::Parse results [2] and [1] (and [1] is also copied into RequestExternal::numSamplesFed), while +0x1C is stored 0 on BOTH of SetSeekData's branches. PlayHandler @0x82BA42E0 calls SetSeekData for every request, so on ARTIST samplesToSkip is always 0 and the skip loop is dead in practice -- reproduce it anyway, and do not rename these three from a guess about a seek feature this build never exercises.
* Return type is rw::audio::core::BufferStatus (base.h:319: UNAVAILABLE=0, AVAILABLE=1), not a bare int; the Mixer dispatch typedef narrows it to int at the call site, which is where the cast belongs.
* r5 (abAlreadyProcessedThisFrame) is attested unused (overwritten at 0x82BA05C4 before any read). Do not invent discontinuity handling for it.

**Implementation sketch**

```cpp
// -------------------------------------------------------------------------------------
// SndPlayer1::Process @0x82BA0568 -- the source stage: turn decoder feeds into one
// published Mixer source frame.
//
// r5 (abAlreadyProcessedThisFrame) is decode-attested UNUSED -- overwritten with 0 at
// 0x82BA05C4 before any read.
//
// The mSamplesRequested CAP on the future-start zero-fill (step 6c below) is NOT in
// progress/scratch_dossiers/sndplayer1_decode_codex.md section 4; it is at
// 0x82BA073C..0x82BA0748 and it is what keeps the zero fill inside the requested chunk.
// -------------------------------------------------------------------------------------
BufferStatus SndPlayer1::Process(PlugIn *apPlugIn, AudioProcessContext *apContext,
                                 bool /*abAlreadyProcessedThisFrame -- r5, unused*/)
{
    SndPlayer1 *self = static_cast<SndPlayer1 *>(apPlugIn);

    // --- 1. declick dispatch: BOTH bytes must be armed -------------------------------
    if (self->mNumDeclickSamples != 0 && self->mDcOffsetsGathered != 0)
        return self->Declick(apContext);        // bl + b <epilogue>: its 1 IS our return

    // --- 2. entry state ---------------------------------------------------------------
    self->mpLoadedDecoder = 0;                  // stw r15, 0x19C -- every entry
    RequestInternal *lpRequest = self->GetRequestInternal(self->mCurrentRequest);

    // Hoisted to function scope: the epilogue's restore needs it. The console re-loads it
    // from mpSystemUseGetSystemAccessor at every use, so hoisting is behaviour-neutral.
    // HOST: mpObjectTable is declared void* in PlugIn.h but IS a StackAllocator* (Mixer.h).
    StackAllocator *lpStack =
        static_cast<StackAllocator *>(self->mpSystemUseGetSystemAccessor->mpObjectTable);

    s32   liSkipped   = 0;      // r20
    s32   liProduced  = 0;      // r5  (see the hazard note on r5 liveness)
    u8   *lpCarveNew  = 0;      // r21 -- non-null == a scratch carve is outstanding
    u8   *lpCarveSaved = 0;     // r22 -- mpTop is a REAL POINTER, never a u32 word
    s32   liRemainingInFeed = 0;// r7

    // The console's inlined IsRequestActive, four sites.
    #define SNDP1_ACTIVE(rq) ((rq)->state != E_COMPLETE && (rq)->state != E_FREE)

    if (SNDP1_ACTIVE(lpRequest))
    {
        // --- 3. retire zero-length requests -------------------------------------------
        while (lpRequest->numSamples == 0)
        {
            lpRequest->state = E_COMPLETE;                      // stb r23(=4), 0x2A
            self->AdvanceCurrentRequest();
            lpRequest = self->GetRequestInternal(self->mCurrentRequest);
            if (!SNDP1_ACTIVE(lpRequest))
                goto epilogue;
        }

        // --- 4. format handshake ------------------------------------------------------
        // `bne` is TAKEN on unordered, so a NaN rate takes the handshake -- which is
        // exactly what `!=` yields in C++. Do NOT rewrite as !(a == b) with a swap.
        if (lpRequest->sampleRate != self->mPreviousSampleRate ||
            lpRequest->numChannels != self->mOutputChannels)
        {
            apContext->mNumSamples    = 0;                      // publish an EMPTY frame...
            apContext->mbChannelCount = lpRequest->numChannels;  // ...carrying the NEW format
            apContext->mfSampleRate   = lpRequest->sampleRate;
            self->mPreviousSampleRate = lpRequest->sampleRate;   // adopt it
            self->mOutputChannels     = lpRequest->numChannels;
            return BUFFERSTATUS_AVAILABLE;   // no swap, no carve, no epilogue -- correct
        }

        // --- 5. feed-slot scan: skip empties, stop at the fill cursor ------------------
        if (self->mFeedDesc[self->mNextFeedSlotToFree].feedState == 0)
        {
            const u8 lucFill = self->mNextFeedSlotToFill;        // read ONCE (0x82BA069C)
            while (self->mNextFeedSlotToFree != lucFill)
            {
                u8 lucNext = static_cast<u8>(self->mNextFeedSlotToFree + 1);
                if (lucNext == KU_MAX_DECODERFEEDS) lucNext = 0; // DWARF MAX_DECODERFEEDS
                self->mNextFeedSlotToFree = lucNext;             // committed each lap
                if (self->mFeedDesc[lucNext].feedState != 0) break;
            }
        }
        if (self->mFeedDesc[self->mNextFeedSlotToFree].feedState != 1)
            goto epilogue;                  // 0 (empty) or 2 (consumed) both block

        // --- 6. start time ------------------------------------------------------------
        // dbl_82001CA8 == 0.0: an exactly-zero start time means "already armed".
        // (A NaN start time is != 0.0, so it goes to WaitForStartTime, which declines.)
        if (lpRequest->startTime != 0.0)
        {
            u32 luFrames = 0;
            if (!self->WaitForStartTime(apContext, lpRequest->startTime, &luFrames))
            {
                self->mCurrentRequestSamplesPlayed = 0;
                goto epilogue;              // >= one mix frame away (or NaN) -> status 0
            }
            if (luFrames != 0)
            {
                // *** THE CAP THE ARCHITECTURE REPORT OMITS (0x82BA073C..0x82BA0748) ***
                if (luFrames >= self->mSamplesRequested)     // cmplw + blt: UNSIGNED
                    luFrames = self->mSamplesRequested;

                SampleBuffer *lpDst = apContext->mpDstBuffer;
                // The channel bound is RE-READ from the request every lap (0x82BA078C).
                for (u32 luCh = 0; luCh < lpRequest->numChannels; ++luCh)
                {
                    std::memset(lpDst->mpSamples + lpDst->muStride * luCh, 0,
                                luFrames * sizeof(f32));       // XMemSet, luFrames*4 bytes
                }
                apContext->mNumSamples = luFrames;
                SampleBuffer *lpOldSrc = apContext->mpSrcBuffer;
                apContext->mpSrcBuffer = lpDst;                // the swap
                apContext->mpDstBuffer = lpOldSrc;
                apContext->mbChannelCount = lpRequest->numChannels;
                apContext->mfSampleRate   = lpRequest->sampleRate;
                self->mCurrentRequestSamplesPlayed = 0;
                return BUFFERSTATUS_AVAILABLE;   // no carve -> no epilogue; no declick capture
            }
            lpRequest->startTime = 0.0;      // stfd f12 -- ARM the request (f12 still 0.0)
        }

        // --- 7. carve the codec scratch off the shared audio stack --------------------
        // mpTop is a REAL POINTER; the 128 alignment is pointer-free and survives verbatim.
        {
            const u32 luScratch = (lpRequest->decoderInstanceSize + 0x7Fu) & ~0x7Fu;
            lpCarveSaved = lpStack->mpTop;
            lpCarveNew   = lpCarveSaved - luScratch;      // downward-growing stack
            lpStack->mpTop = lpCarveNew;
        }

        // --- 8. load the decoder + this feed record's availability --------------------
        // NOTE: no null check on pDecoder here -- faithful (the second carve, step 13,
        // DOES check). The feedState==1 gate implies StartRequest already ran.
        self->mpLoadedDecoder = lpRequest->pDecoder;      // stw 0x19C
        Decoder *lpDecoder = self->mpLoadedDecoder;

        // Instruction-for-instruction Decoder::GetSamplesRemaining @0x826914D0, inlined on
        // the console. Its 0x14 request stride is pointer-free and survives x64, but reach
        // it through the typed ring, not by hand.
        s32 liAvailable = lpDecoder->GetSamplesRemaining(
                self->mFeedDesc[self->mNextFeedSlotToFree].decoderRequestHandle);

        // --- 9. skip / decode counts (both compares are SIGNED) -----------------------
        s32 liToSkip = lpRequest->samplesToSkip;         // +0x1C; SetSeekData always 0
        if (liAvailable < liToSkip) liToSkip = liAvailable;
        s32 liToDecode = self->mSamplesRequested;
        if (liToDecode >= liAvailable - liToSkip) liToDecode = liAvailable - liToSkip;

        lpRequest = self->GetRequestInternal(self->mCurrentRequest); // re-materialised
        SampleBuffer *lpDst = apContext->mpDstBuffer;    // the SAME descriptor for both loops

        // --- 10. skip loop, 256 samples per Decode call -------------------------------
        // Every lap writes from sample 0 of lpDst and is overwritten by the next lap and
        // finally by the main decode -- THAT is how the skipped audio is discarded.
        while (liToSkip != 0)                            // `bne`, not `> 0`
        {
            const s32 liChunk = (liToSkip < 256) ? liToSkip : 256;   // signed cmpwi 0x100
            liToSkip -= liChunk;
            liSkipped += lpDecoder->Decode(
                reinterpret_cast<DecoderBuffer *>(lpDst), liChunk);   // the console pun
        }

        // --- 11. the main decode + publish/swap ---------------------------------------
        // Called even when liToDecode == 0.
        liProduced = lpDecoder->Decode(reinterpret_cast<DecoderBuffer *>(lpDst), liToDecode);
        {
            SampleBuffer *lpOldSrc = apContext->mpSrcBuffer;
            apContext->mpSrcBuffer = lpDst;              // the FILLED buffer becomes src
            apContext->mNumSamples = liProduced;
            apContext->mpDstBuffer = lpOldSrc;
            apContext->mbChannelCount = lpRequest->numChannels;
            apContext->mfSampleRate   = lpRequest->sampleRate;
        }

        // --- 12. accounting -----------------------------------------------------------
        self->mCurrentRequestHandle = lpRequest->requestHandle;
        if (self->mCurrentRequestSamplesPlayed == 0)     // first output for this request
        {
            self->mCurrentRequestSamplesPlayed =
                lpRequest->seekStreamSampleOffset + lpRequest->seekDecoderSampleOffset;
        }
        liRemainingInFeed = (liAvailable - liProduced) - liSkipped;
        self->mCurrentRequestSamplesPlayed += liProduced + liSkipped;
        self->mCurrentRequestSampleRate = lpRequest->sampleRate;
        self->mCurrentRequestNumSamples = lpRequest->numSamples;
        self->mFeedDesc[self->mNextFeedSlotToFree].chunkSamplesPlayed +=
            liProduced + liSkipped;

        // --- 13. loop point / end of sample -------------------------------------------
        if (self->mCurrentRequestSamplesPlayed == lpRequest->numSamples)   // EXACT equality
        {
            if (lpRequest->loopStart >= 0)
            {
                self->mCurrentRequestSamplesPlayed = lpRequest->loopStart;
            }
            else
            {
                lpRequest->state = E_COMPLETE;
                if (self->mpLoadedDecoder != 0)
                {
                    self->mpLoadedDecoder = 0;
                    lpStack->mpTop = lpCarveSaved;      // restore NOW, mid-body
                }
                self->AdvanceCurrentRequest();
                RequestInternal *lpNext =
                    self->GetRequestInternal(self->mCurrentRequest);
                // lpRequest is deliberately NOT re-pointed; nothing below reads it.
                if (SNDP1_ACTIVE(lpNext) && lpNext->pDecoder != 0)   // null check HERE only
                {
                    const u32 luScratch =
                        (lpNext->decoderInstanceSize + 0x7Fu) & ~0x7Fu;
                    lpCarveSaved = lpStack->mpTop;
                    lpCarveNew   = lpCarveSaved - luScratch;
                    lpStack->mpTop = lpCarveNew;
                    self->mpLoadedDecoder = lpNext->pDecoder;
                }
            }
        }

        // --- 14. feed rollover: retire exhausted feed records --------------------------
        while (liRemainingInFeed == 0)
        {
            SndPlayer1FeedDesc *lpFeed = &self->mFeedDesc[self->mNextFeedSlotToFree];
            if (lpFeed->feedState != 1)
                break;                                   // -> epilogue
            lpFeed->feedState = 2;                       // consumed; FeedCleanup frees it

            u8 lucNext = static_cast<u8>(self->mNextFeedSlotToFree + 1);
            if (lucNext == KU_MAX_DECODERFEEDS) lucNext = 0;
            Decoder *lpDec = self->mpLoadedDecoder;      // read BEFORE the cursor store
            self->mNextFeedSlotToFree = lucNext;
            if (lpDec == 0) break;
            if (self->mFeedDesc[lucNext].feedState != 1) break;
            liRemainingInFeed = lpDec->GetSamplesRemaining(
                    self->mFeedDesc[lucNext].decoderRequestHandle);
        }
    }

epilogue:
    // --- 15. restore the carve (the ONLY restore point for every carving path) --------
    if (self->mpLoadedDecoder != 0)
    {
        self->mpLoadedDecoder = 0;
        if (lpCarveNew != 0)
            lpStack->mpTop = lpCarveSaved;
    }

    // --- 16. status derivation -------------------------------------------------------
    // These two are published on EVERY epilogue path, overwriting step 11's values with
    // the plug-in's own (identical past the handshake, but also set when there is no
    // request at all).
    apContext->mbChannelCount = self->mOutputChannels;
    apContext->mfSampleRate   = self->mPreviousSampleRate;

    if (liProduced == 0)
    {
        if (liSkipped == 0 && self->mSamplesRequested != 0)
            return BUFFERSTATUS_UNAVAILABLE;  // mNumSamples deliberately NOT republished
        apContext->mNumSamples = 0;           // skip-only work, or a zero-sample request
        return BUFFERSTATUS_AVAILABLE;
    }

    // Capture the last emitted sample of each channel as the declick anchor, from the
    // JUST-SWAPPED src slot (the buffer the decoder filled).
    {
        u32 luChannels = apContext->mbChannelCount;      // re-read, == mOutputChannels
        if (luChannels >= self->mMaxChannels)            // cmplw + blt: UNSIGNED min
            luChannels = self->mMaxChannels;
        SampleBuffer *lpSrc = apContext->mpSrcBuffer;
        f32 *lpDeclick = self->GetDeclickBuffer();
        for (u32 luCh = 0; luCh < luChannels; ++luCh)
        {
            lpDeclick[luCh] =
                lpSrc->mpSamples[lpSrc->muStride * luCh + liProduced - 1];  // lfs -4(r8)
        }
    }
    self->mDcOffsetsGathered = 1;             // arm the declick path for the next stop
    return BUFFERSTATUS_AVAILABLE;

    #undef SNDP1_ACTIVE
}
```

### Cluster notes

GROUND TRUTH USED
* Dossiers (the `assembly` field only; pseudocode consulted for hints and repeatedly rejected): 0x82BA0568 (Process, 428 instructions), 0x82B9C2D8 (PreProcess), 0x82B9C148 (WaitForStartTime), 0x82B9C1C0 (Declick), 0x82B9C2E8 (AdvanceCurrentRequest). Callee/context dossiers read in full to ground the decode: 0x82B67A50 Decoder::Decode, 0x826914D0 Decoder::GetSamplesRemaining, 0x82B679D8 Decoder::AdvanceDecodeState, 0x82BA0380 GetFeedSlot, 0x82BA0268 FeedCleanup, 0x82B9C068 SetSeekData, 0x82BA41D8 PlayHandler (skip-counter writer search). Repo types read: Mixer.h, PlugIn.h, Decoder.h, Voice.h, SubMix.h/.cpp, SinePlayer.h, Dac.cpp, Mixer.cpp (the two dispatch typedefs).
* Rodata re-read byte-for-byte from IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex, big-endian, file_off = 0x3000 + vaddr - 0x82000000: dbl_82001CA8 @0x4CA8 = 00 00 00 00 00 00 00 00 = 0.0; flt_82001C98 @0x4C98 = 3F 80 00 00 = 1.0f; flt_820ADBFC @0xB0BFC = 43 80 00 00 = 256.0f. All three were previously only asserted, never quoted.

NEW GROUND TRUTH THIS PASS -- the twin class's FULL DWARF member list and method signatures
references/DecFIGS/dwarfdump/GameShared/GameClasses/Sound/Playback/Plugins/Streaming/internal/sndplayer1.h dumps rw::audio::core::SndPlayer1_CgsStreamMod complete, naming every member and every method of the shape this class shares. That closes several things the prior reports left as reconstruction:
* Signatures, verbatim: `int PreProcess(PlugIn*, Mixer*, bool, int)` (:386), `BufferStatus Process(PlugIn*, Mixer*, bool)` (:387), `BufferStatus Declick(Mixer*)` (:443), `bool WaitForStartTime(Mixer*, double, unsigned int*)` (:444), `void AdvanceCurrentRequest()`, plus the helpers this cluster inlines: `bool IsRequestActive(unsigned char)`, `RequestInternal *GetRequestInternal(unsigned int)`, `float *GetDeclickBuffer()`. WaitForStartTime's DWARF parameter order independently confirms the r5-GPR-slot-skip register decode (Mixer* in r4, the double in f1, the out pointer in r6).
* Member names for the ordinary class's offsets: +0x19C mpLoadedDecoder, +0x1A0..+0x1AC the mCurrentRequest{Handle,SampleRate,SamplesPlayed,NumSamples} cache, +0x1BC mPreviousSampleRate, +0x1C0 mSamplesRequested, +0x1C2 mDeclickBufferOffset, +0x1C4 mRequestInternalOffset, +0x1C6 mMaxChannels, +0x1C9 mCurrentRequest, +0x1CA mMaxRequests, +0x1CB mDcOffsetsGathered, +0x1CC mNumDeclickSamples, +0x1CD mNextFeedSlotToFill, +0x1CE mNextFeedSlotToFree, +0x1D0 mTimerAdded.
* `enum BufferStatus { BUFFERSTATUS_UNAVAILABLE = 0, BUFFERSTATUS_AVAILABLE = 1 }` and `MIXER_FRAME_SIZE = 256` from references/DecFIGS/dwarfdump/SDKs/EATech/include/rw/audio/core/base.h:319/:308. `MAX_DECODERFEEDS = 20` and `ConstructorParams { float maxRequests; }` come from the ORDINARY class's own DWARF (SDKs/EATech/include/rw/audio/core/plugins/sndplayer1.h:169/:51), so the feed-ring modulus 20 and the constructor-param interpretation are directly attested for this class, not carried across from the twin.

THE THREE INHERITED ERRORS -- adjudicated
(a) CONFIRMED WRONG. Declick 0x82B9C270 is `subf r10, r9, r10` -> mNumDeclickSamples -= the PUBLISHED count (r9 = min(remaining, mSamplesRequested)), not a unit decrement. The sketch and the behaviour walk carry the subtraction; the hazard entry states what a decrement would sound like. When the byte reaches 0, 0x82B9C2C4 clears mDcOffsetsGathered (+0x1CB), which disarms Process's declick dispatch until the next successful decode re-arms it at 0x82BA0BC0.
(b) CONFIRMED. The future-start zero-fill count IS capped at mSamplesRequested, at 0x82BA073C..0x82BA0748 (`lhz +0x1C0; cmplw; blt; mr`), an UNSIGNED min. It lives in Process, not in WaitForStartTime -- so WaitForStartTime must NOT grow the cap and must keep ignoring `this`.
(c) NOT RE-VERIFIED. The handle-counter wrap value lives in EventEvent @0x82BA5C48, which is outside this cluster and has no dossier. I neither repeat nor contradict the claim anywhere above.

FURTHER CORRECTIONS TO THE ARCHITECTURE REPORT (progress/scratch_dossiers/sndplayer1_decode_codex.md)
* Section 4 "Future start": a near-future start zero-fills min(frames, mSamplesRequested) frames, not "that many" -- see (b).
* Section 4 "No active request/feed": the final-return-0 condition is right, but it omits that mbChannelCount and mfSampleRate ARE still published on that path (0x82BA0B2C / 0x82BA0B34). Only mNumSamples is withheld.
* Section 4 "Decode": Process skips min(available, RequestInternal+0x1C), and it never writes +0x1C back. That counter's sole writer, SetSeekData @0x82B9C068, stores 0 on both branches, so on ARTIST the skip loop is dead in practice. Reproduce it anyway.
* Section 2's row for +0x1CF ("no semantic reader was found in the decoded paths") is superseded: FeedCleanup @0x82BA0268 reads and advances it as the chunk-release cursor trailing mNextFeedSlotToFree. Process never touches it.
* Section 2's row "+0x1C/+0x20/+0x24 player/decoder/stream skip counters" is now grounded: SetSeekData writes SeekTableParser::Parse results [2]->+0x20 and [1]->+0x24 (the latter also into RequestExternal::numSamplesFed), and Process seeds mCurrentRequestSamplesPlayed with their sum on the first output frame. The NAMES remain reconstructed (the twin has no such fields).

SHAPES BORROWED FROM THE STREAMMOD REPORT (progress/scratch_dossiers/streammod_gainarray_decode_codex.md), with the divergence stated each time
* The RequestState enum spelling (FREE=0, QUEUED=1, FEEDING=2, FEEDCOMPLETE=3, COMPLETE=4) and the field NAMES startTime / pDecoder / requestHandle / sampleRate / numSamples / loopStart / decoderInstanceSize / state / numChannels. SHAPE ONLY -- every offset differs: the ordinary RequestInternal is console stride 0x30 with decoderInstanceSize at +0x28, state +0x2A, numChannels +0x2B and three extra skip words at +0x1C/+0x20/+0x24, versus the twin's stride 0x20 with +0x1C/+0x1E and no skip counters.
* SndPlayer1FeedDesc field names (chunkSamplesPlayed / decoderRequestHandle / feedState / requestIndex). SHAPE ONLY -- the ordinary record is console stride 0x10 and begins with TWO pointers (pChunkInfo +0x00 and the rw::core::filesys::Stream +0x04, both attested by FeedCleanup's Stream::ReleaseChunk call at 0x82BA0344), pushing chunkSamplesPlayed to +0x08, the handle to +0x0C, feedState to +0x0D and requestIndex to +0x0E. The twin's record is stride 0x0C, pointer-free, with those fields at +0x00/+0x04/+0x08/+0x09/+0x0A. NO offset was copied across.
* The observation that the twin's Process CALLS Decoder::GetSamplesRemaining out of line is what let me identify the ordinary Process's 0x82BA0828..0x82BA086C block as the SAME function inlined -- verified instruction-for-instruction against 0x826914D0.

VERIFICATION OF THE SCRATCH-RESTORE CLAIM
Every Process exit was walked against the branch graph. Carve sites: 0x82BA07EC (first) and 0x82BA0A1C (re-carve after a request ends). Restore sites: 0x82BA09C0..0x82BA09CC (mid-body, end-of-sample path) and 0x82BA0B14..0x82BA0B1C (epilogue). Exits that bypass the epilogue are 0x82BA0598 (declick), 0x82BA07E4 (near-future zero fill) and the 0x82BA0BD0 -> 0x82BA0C0C format handshake -- all three are strictly UPSTREAM of the first carve, so no leak. The epilogue's guard is `mpLoadedDecoder != 0` AND `carveNew != 0`; the mid-body restore clears mpLoadedDecoder in the same breath, which is exactly what stops a double restore when the re-carve does not happen.

NOTHING IN THIS CLUSTER IS BLOCKED. All five functions are DECODED end to end. The only reconstructed items are three field NAMES (RequestInternal +0x1C/+0x20/+0x24) and one out-of-cluster field NAME (+0x1CF), each with its attesting writer cited and each marked as reconstructed rather than asserted. One deliberate deviation in the Process sketch is flagged rather than hidden: the StackAllocator lookup is hoisted to function scope because the epilogue's restore needs it, whereas the console re-loads it from mpSystemUseGetSystemAccessor at each of its three uses -- behaviour-neutral, noted in the hazards.

## Cluster: rw::audio::core::SndPlayer1 — the event surface (vtable) and its deferred-command handlers

### `rw::audio::core::SndPlayer1::EventEvent  (host: SndPlayer1::Event, vt[1])` @ `0x82BA5C48 (file 0x00BA8C48 .. 0x00BA907C; body ends at 0x82BA607C `blr`)`  [DECODED]

**Signature**

```cpp
virtual int Event(int aiEventId, void *apParam);   // console: int __fastcall EventEvent(SndPlayer1 *r3, int r4, void *r5)
// Dispatch site: the static pass-through PlugIn::Event @0x82B6A8F8 tail-vcalls vt[1] with r4/r5 untouched (same contract Dac::Event already models). Slot proof: vtable off_8217F344 (file 0x00182344) = {82BA4178 ReleaseEvent, 82BA5C48 EventEvent, 82BDD2D0 GetPpuTicksEvent, 82B9EAF8 vector-deleting-dtor}, re-dumped this pass; words 4/5 (82B9D0A8, 82BA0F80) are the adjacent VuMeter table at 0x8217F354.
```

**Behaviour**

NO DOSSIER EXISTS. Hand-decoded from the decrypted XEX (capstone PPC32-BE over file 0x00BA8C48; every branch target and every `lis/addi` pair re-derived from raw big-endian words, several spot-verified byte-for-byte).

PROLOGUE (0x82BA5C48..0x82BA5C6C): frame 0xB0; r9 = this, r31 = apParam, r8 = this->mpSystemUseGetSystemAccessor (`lwz r8, 4(r9)`). r30/r31 saved. Dispatch is a linear compare chain, NOT a jump table: r4==0 -> 0x82BA5ED4 (PLAY legacy-expand); r4==5 -> 0x82BA5F28 (PLAY1); r4==1 -> STOP; r4==2 -> ISREQUESTDONE; r4==3 -> GETREQUESTBUFFERED; r4==4 -> MODIFYSTARTTIME; ANY OTHER id falls straight to the epilogue with no side effect at all.

EVENT 1 STOP (0x82BA5C80..0x82BA5CA4). Pure enqueue, 8 console bytes: r11 = mpSystem->muDeferredRingCursor (+0x10B8); r10 = mpSystem->mpDeferredRingBase (+0x20) + r11; cursor += 8 and is stored back BEFORE the payload stores; then *(u32*)(rec+0x00) = 0x82BA44E0 (&StopHandler, from `lis r7,0x82BA` + `addi r7,r7,0x44E0`), *(u32*)(rec+0x04) = this. No parameter block is read.

EVENT 2 ISREQUESTDONE (0x82BA5CA8..0x82BA5D08). Param block: +0x00 f32 queried handle (IN), +0x04 f32 result (OUT, 0.0f/1.0f). Registers: f0 = param->handle, f13 = this->mpAttribute[0].mfValue (`lfs 0x28(r9)` — RwacTimerClient @0x82BA69EC/0x82BA69F4 fills that slot from mfCurrentRequestHandle +0x1A0, so it IS a handle), f12 = 0.0f preloaded from flt_82001CC0. EXACT TRUTH CONDITION, branch by branch:
  0x82BA5CC4 `blt` -> if (handle <  attr0) result = 1.0f  [jump to the 1.0f load at 0x82BA5CFC]
  0x82BA5CCC `beq` -> if (handle == attr0) go to the attr2 test
  0x82BA5CD8 `bgt` -> if (handle >  mfLastRequestProcessed +0x1B4) result = 0.0f (store f12, still 0.0f)
  0x82BA5CE4 `ble` -> if (handle <= mfLastRequestSuccessfullyProcessed +0x1B8) result = 0.0f
  else -> attr2 test
  0x82BA5CF8 `bne` -> if (*(f64*)(this+0x38) /*attribute 2, sample length*/ != 0.0 [dbl_82001CA8]) result = 0.0f; else result = 1.0f.
So: done = (handle < attr0) || ( (handle == attr0 || (!(handle > lastProcessed) && !(handle <= lastSuccessful))) && attr2 == 0.0 ). One store `stfs f12, 4(r31)` on every path. NOTE the attribute-2 read is an `lfd` of the FULL 8-byte slot, not the f32 half.

EVENT 3 GETREQUESTBUFFERED (0x82BA5D0C..0x82BA5E90). Param block: +0x00 f32 queried handle (IN), +0x04 f32 buffered amount (OUT), +0x08 f32 complete flag (OUT).
  GUARD (0x82BA5D14..0x82BA5D20): if (mu8MaxRequests /*+0x1CA*/ == 0) return with the parameter block COMPLETELY UNTOUCHED — no store to +0x04 or +0x08 at all. (The prior architecture report's "no-match output remains 0/false" is wrong twice: nothing is pre-zeroed, and the non-matching laps DO store.)
  SCAN: r6 = index i (0-based), r10 = i*0x30 (RequestInternal stride), r8 = i*0x50 (RequestExternal stride), f13 = queried handle, f0 = 0.0f held live in a register for the whole loop. Each lap recomputes lpReq = this + muRequestArrayOffset(u16 +0x1C4) + r10 and re-reads mu8MaxRequests from +0x1CA at the bottom (`lbz 0x1CA(r9)` @0x82BA5DA4).
    match test 1: `lfs f12, 0x0C(r7)` (RequestInternal.mfHandle) `fcmpu`/`bne` -> non-match falls to the STORE-ZEROS tail.
    match test 2: state byte +0x2A — the canonical 3-way idiom (== 4 -> 0; != 0 -> 1; == 0 -> 0), i.e. skip when FREE(0) or COMPLETE(4).
    then lpExt = mpRequestExternal(+0x58) + r8; switch on lpExt->mu8PlayType (+0x49): 1 or 2 -> STREAMED; 0 -> RESIDENT; anything else -> falls through into the STORE-ZEROS tail and keeps scanning.
  STORE-ZEROS tail (0x82BA5D98): param+0x04 = 0.0f; ++i; param+0x08 = 0.0f; i*=strides advance; loop while i < mu8MaxRequests. So after a full no-match scan the caller sees 0.0/0.0 written mMaxRequests times.
  RESIDENT (0x82BA5DBC): param+0x04 = 0.0f; param+0x08 = 1.0f (flt_82001C98); return.
  STREAMED (0x82BA5DD0..0x82BA5E90): param+0x08 = 0.0f; param+0x04 = (f32)(f64)(s32)lpExt->muBytesFed (`lwa 0x18(r30)` — SIGN-EXTENDING load, then fcfid/frsp). lpStream = lpExt->mpStream (+0x28); if it is null jump straight to COMPLETE. Otherwise pick ONE of two byte-count accessors:
      if (lpReq->miLoopStart /*+0x18, `lwz`+`cmpwi`, blt*/ >= 0  AND  (f32)(f64)(u32)i == this->mpAttribute[0].mfValue)  -> r3 = call 0x82BBD940(lpStream)
      else -> r3 = call 0x82BBD948(lpStream, lpExt->muStreamerRequestId /*+0x2C*/)
    (*** CONSOLE QUIRK, VERIFIED IN THE RAW BYTES: 0x82BA5E04 is `78 CB 00 20` = clrldi r11,r6,32 — r6 is the LOOP INDEX, initialised at 0x82BA5D18 and bumped only in the store-zeros tail — and 0x82BA5E08 is `C0 09 00 28` = lfs f0,0x28(r9), attribute 0, a HANDLE. The code really does compare a request INDEX, converted to float, against a monotonically-increasing handle. It is almost certainly a source bug for mu8CurrentRequestIndex (+0x1C9), but it is what ships and it must be reproduced. ***)
    Then param+0x04 = (f32)(f64)result + param+0x04 (`fadds`, so single-precision).
    COMPLETION: if (Stream::GetRequestState(lpStream, lpExt->muStreamerRequestId) /*0x82BBD9D0*/ == 3) -> COMPLETE; else if (Stream::GetState(lpStream) /*0x82BBD990*/ == 2) -> COMPLETE; else return leaving param+0x08 == 0.0f.
    COMPLETE (0x82BA5E84): param+0x08 = 1.0f; return.
  Callee identification (hand-decoded, no dossier for the second): 0x82BBD940 = `lwz r3,0x0C(r3); blr` — Stream's own accumulated-bytes word. 0x82BBD948 = per-request bytes: impl = stream->+0x04; idx = requestId & 0xFF; if (idx >= impl->+0x3C) return 0; rec = impl->+0x38 + idx*0x140; if (rec->+0x00 != requestId) return 0; if (rec->+0x04 == 0) return 0; return rec->+0x138. 0x82BBD990 = GetState: `return *(u32*)(*(u32*)(stream+4) + 0x70)`.

EVENT 4 MODIFYSTARTTIME (0x82BA5E94..0x82BA5ED0). Param block: +0x00 f64 new start time, +0x08 f32 request handle. Enqueue of 0x18 console bytes: rec = ringBase + cursor; cursor += 0x18 stored back first; rec+0x00 = 0x82BA03D0 (&ModifyStartTimeHandler); rec+0x04 = this; `lfd`/`stfd` param+0x00 -> rec+0x08; `lfs`/`stfs` param+0x08 -> rec+0x10. rec+0x14..0x17 is tail padding, never written. The handler's own reads (`lwz 4(r3)`, `lfd 8(r3)`, `lfs 0x10(r3)`) confirm the layout exactly.

EVENT 0 PLAY, legacy expand (0x82BA5ED4..0x82BA5F24). Builds a 0x30-byte "expanded" block on the stack at sp+0x60 (the fctidz scratch at sp+0x50 does not overlap) and then falls into the shared tail with r10 = sp+0x60. Field-by-field, exp <- legacy:
    exp+0x00 f64 startTime        <- legacy+0x00 f64
    exp+0x08 f64 streamFileOffset <- legacy+0x08 f64
    exp+0x10 f64 seekTime         <- 0.0 (dbl_82001CA8)  [SUPPLIED, not copied]
    exp+0x18 ptr  path            <- legacy+0x10
    exp+0x1C ptr  sample header   <- legacy+0x14
    exp+0x20 ptr  seek table      <- 0 (`li r11,0`)      [SUPPLIED]
    exp+0x24 u32  streamPoolGuid  <- legacy+0x18
    exp+0x28 f32  expel mode      <- legacy+0x1C
    exp+0x2C f32  handle          <- legacy+0x20   (DEAD: unconditionally overwritten at 0x82BA5F70)
  So the legacy block is 0x24 = 36 bytes wide, NOT the 40 the prior report claims, and legacy+0x20 is its OUT handle slot.

EVENT 5 PLAY1 (0x82BA5F28): `mr r10, r31` only — the caller's block IS the expanded block; the shared tail writes the handle back in place at +0x2C.

SHARED PLAY TAIL (0x82BA5F2C..0x82BA6064).
  (a) Handle counter (0x82BA5F2C..0x82BA5F60): p = this->mpRequestHandleCounter (+0x1B0); f0 = 1.0f (flt_82001C98); *p = *p + 1.0f (`fadds`); reload *p; `fcmpu` against flt_820B56EC = 4194304.0f; `ble` skips; on the not-taken path `stfs f0, 0(r11)` — and f0 STILL HOLDS THE 1.0f LOADED AT 0x82BA5F38, never reloaded. *** THE WRAP VALUE IS 1.0f. The architecture report's "wraps to zero" is WRONG; the adversarial review is RIGHT. Settled from the bytes. *** Also note the wrap is `> 4194304.0f` strictly (ble skips at exactly 4194304.0f).
  (b) Publish (0x82BA5F64..0x82BA5F78): handle = *counter; store to exp+0x2C; and, only when aiEventId == 0, ALSO store to legacy param+0x20.
  (c) Record size (0x82BA5F7C..0x82BA5FC4): nameBytes = exp->path ? strlen(path)+1 : 1 (the strlen is an open-coded `lbz/addi/cmplwi/bne` loop, then `subf`, `addi -1`, `addi +1`); size = (nameBytes + 0x3B) & ~3 == align_up(0x38 + nameBytes, 4). The 0x38 is the CONSOLE fixed head. Minimum 0x3C.
  (d) Enqueue (0x82BA5FB8..0x82BA6034): rec = ringBase + cursor; cursor += size, stored back first. Then rec+0x04 = this; rec+0x00 = 0x82BA41D8 (&PlayHandler); rec+0x30 = *this->mpRequestHandleCounter (RE-READ from memory, not the register); rec+0x08 = exp+0x00 (f64 start time); rec+0x10 = exp+0x08 (f64 stream file offset); rec+0x18 = exp+0x10 (f64 seek time); rec+0x24 = exp+0x1C (sample-header ptr); rec+0x28 = exp+0x20 (seek-table ptr); rec+0x20 = exp+0x24 (stream-pool GUID — NOTE the two pointer fields and the GUID are stored OUT OF ORDER relative to the source block); rec+0x2C = (u16)size (`sth`); rec+0x2E = low byte of (s64)trunc(exp+0x28 f32) — `fctidz` to sp+0x50 then `lbz sp+0x57`, i.e. the LOW byte of the big-endian doubleword = the expel mode.
  (e) Path tail (0x82BA6038..0x82BA6064): cr6 still carries `cmplwi r11, 1` from 0x82BA5FC8 (nothing between them touches CR). If nameBytes == 1 (path null OR empty string) write a single `stb 0, 0x38(rec)`. Otherwise copy byte-by-byte from exp->path into rec+0x38 with a store-then-test loop, so the terminating NUL IS copied.

EPILOGUE (0x82BA6068..0x82BA607C): restores and `blr` with NO `li r3, ...` anywhere. r3 is whatever survived: `this` on the ISREQUESTDONE path, a stream-call result on GETREQUESTBUFFERED, junk elsewhere. The return is a dead passthrough that every caller discards — exactly the situation Dac::Event already documents, so the host returns 0.

**Constants**

flt_82001C98  vaddr 0x82001C98  file_off 0x00004C98  raw BE `3F 80 00 00`  = 1.0f   (the ISREQUESTDONE/RESIDENT/COMPLETE true value, the handle increment, AND the wrap target)
dbl_82001CA8  vaddr 0x82001CA8  file_off 0x00004CA8  raw BE `00 00 00 00 00 00 00 00` = 0.0 (f64)  (attribute-2 comparand; the supplied legacy seek time)
flt_82001CC0  vaddr 0x82001CC0  file_off 0x00004CC0  raw BE `00 00 00 00`  = 0.0f  (the false value / loop zero held live in f0)
flt_820B56EC  vaddr 0x820B56EC  file_off 0x000B86EC  raw BE `4A 80 00 00`  = 4194304.0f  (2^22, the handle-counter wrap threshold; strict `>`)
Handler addresses formed by lis/addi (r7 base 0x82BA0000 from `lis r7,-0x7d46`):
  0x82BA0000 + 0x44E0 = 0x82BA44E0  SndPlayer1::StopHandler
  0x82BA0000 + 0x03D0 = 0x82BA03D0  SndPlayer1::ModifyStartTimeHandler
  0x82BA0000 + 0x41D8 = 0x82BA41D8  SndPlayer1::PlayHandler
vtable off_8217F344  file_off 0x00182344  raw BE `82BA4178 82BA5C48 82BDD2D0 82B9EAF8` (re-dumped; the following words 82B9D0A8/82BA0F80 are the VuMeter table at 0x8217F354).

**Host hazards**

1. NO DOSSIER. Everything above is a hand decode of the decrypted XEX; three loads were re-verified against the raw big-endian words (0x82BA5E04 `78 CB 00 20`, 0x82BA5E08 `C0 09 00 28`, the two `bl` displacements 0x82BA5E24/0x82BA5E3C resolving to 0x82BBD940/0x82BBD948).
2. RING-RECORD STRIDES. Console 8 (Stop), 0x18 (ModifyStartTime) and `(nameBytes+0x3B)&~3` (Play) all count 32-bit function pointers and 32-bit `this`. On x64 the producer advance MUST be the host sizeof / host-computed size, and it must equal what the handler returns. The PlayCommand additionally carries two 32-bit payload pointers (mpHeader, mpSeekTable) that widen.
3. PLAYCOMMAND ALIGNMENT. The console rounds the record to 4. On the host the record leads with three f64s, so rounding to 4 would misalign the next record in the ring: round to alignof(SndPlayer1PlayCommand).
4. muRecordSize IS A u16 ON THE WIRE (`sth 0x2C`). The widened record still fits, but assert it — a silent truncation desynchronises the ring replay.
5. NaN / UNORDERED POLARITY, five sites: `blt` @0x82BA5CC4 (as written), `beq` @0x82BA5CCC (as written), `bgt` @0x82BA5CD8 and `ble` @0x82BA5CE4 (both jump to FALSE, so keep-going is the NEGATED ordered predicate), `bne` @0x82BA5CF8 (NaN attribute-2 yields FALSE), and `ble` @0x82BA5F58 (unordered counter WRAPS — write `!(x <= 4194304.0f)`).
6. HANDLE-COUNTER WRAP = 1.0f. Settled against the architecture report's claim of 0.0f; the register f0 is never reloaded between 0x82BA5F38 and the wrap store at 0x82BA5F60. A 0.0f wrap would make the first post-wrap handle collide with the CreateInstance-initialised 0.0f in every request slot.
7. INDEX-vs-HANDLE FLOAT COMPARE in GETREQUESTBUFFERED. A shipped console bug. Reproduce it; do not substitute mu8CurrentRequestIndex.
8. mu8MaxRequests == 0 leaves the GETREQUESTBUFFERED param block completely unwritten (uninitialised-read hazard for the caller). Also, a full no-match scan writes 0.0/0.0 mMaxRequests times rather than once.
9. `lwa 0x18(r30)` is a SIGN-EXTENDING 32-bit load of the byte counter; a naive u32 read diverges once it exceeds 2 GiB (and the value is then run through fcfid as SIGNED).
10. LEGACY BLOCK IS 36 BYTES (0x24), not the 40 the prior architecture report states; +0x20 is the OUT handle, and the copy of it into exp+0x2C is dead.
11. Request-array indexing: RequestInternal stride 0x30 and RequestExternal stride 0x50 are console strides over records containing 32-bit pointers (Decoder*, sample/stream/pool pointers). Both must be host-layout indexing (GetRequest(i) / mpRequestExternal[i]), never `(char*)this + muRequestArrayOffset + 0x30*i`.
12. Attribute 0 is read as an f32 at +0x28 but attributes 1/2 are FULL 8-byte doubles at +0x30/+0x38 — an `Attribute_t[3]` (f32+u32 pairs) is layout-compatible only if the host attribute view keeps the 8-byte stride and lets the f64 members alias the slots (24 bytes either way; the f64 raises alignment from 4 to 8 without moving anything).
13. EventEvent's r3 is an uninitialised passthrough; returning 0 (the Dac::Event precedent) is safe only because every call site discards it.

**Implementation sketch**

```cpp
// ---------------- parameter blocks (all caller-supplied, all read/written in place)
struct SndPlayer1IsRequestDoneParams   // event 2
{
    f32 mfHandle;   // +0x00 (in)
    f32 mfIsDone;   // +0x04 (out: 0.0f / 1.0f)
};
struct SndPlayer1BufferedParams        // event 3
{
    f32 mfHandle;    // +0x00 (in)
    f32 mfBuffered;  // +0x04 (out: bytes)
    f32 mfComplete;  // +0x08 (out: 0.0f / 1.0f)
};
struct SndPlayer1ModifyStartTimeParams // event 4
{
    f64 mdStartTime; // +0x00 (in)
    f32 mfHandle;    // +0x08 (in)
};
struct SndPlayer1PlayLegacyParams      // event 0 -- 0x24 CONSOLE bytes (NOT 40)
{
    f64 mdStartTime;        // +0x00
    f64 mdStreamFileOffset; // +0x08
    const char *mpcPath;    // +0x10  (POINTER -- widens)
    const void *mpHeader;   // +0x14  (POINTER -- widens)
    u32 muStreamPoolGuid;   // +0x18
    f32 mfExpelMode;        // +0x1C
    f32 mfHandle;           // +0x20  (out)
};
struct SndPlayer1PlayParams            // event 5 == the expanded form -- 0x30 CONSOLE bytes
{
    f64 mdStartTime;        // +0x00
    f64 mdStreamFileOffset; // +0x08
    f64 mdSeekTime;         // +0x10
    const char *mpcPath;    // +0x18  (POINTER -- widens)
    const void *mpHeader;   // +0x1C  (POINTER -- widens)
    const void *mpSeekTable;// +0x20  (POINTER -- widens)
    u32 muStreamPoolGuid;   // +0x24
    f32 mfExpelMode;        // +0x28
    f32 mfHandle;           // +0x2C  (out)
};

// ---------------- deferred-command records. RING CONTRACT: the producer's cursor
// advance and the handler's return are the SAME value, and on the host that value is
// the HOST sizeof -- NEVER the console 8 / 0x18 / (nameBytes+0x3B)&~3, all of which
// count 32-bit function/object/string pointers.
struct SndPlayer1StopCommand           // console 8
{
    int (*mpHandler)(void *);  // +0x00 -> &SndPlayer1::StopHandler
    SndPlayer1 *mpPlayer;      // +0x04
};
struct SndPlayer1ModifyStartTimeCommand // console 0x18 (+0x14..0x17 pad, never written)
{
    int (*mpHandler)(void *);  // +0x00 -> &SndPlayer1::ModifyStartTimeHandler
    SndPlayer1 *mpPlayer;      // +0x04
    f64 mdStartTime;           // +0x08
    f32 mfHandle;              // +0x10
};
struct SndPlayer1PlayCommand            // VARIABLE SIZE; console head 0x38 + path
{
    int (*mpHandler)(void *);  // +0x00 -> &SndPlayer1::PlayHandler
    SndPlayer1 *mpPlayer;      // +0x04
    f64 mdStartTime;           // +0x08
    f64 mdStreamFileOffset;    // +0x10
    f64 mdSeekTime;            // +0x18
    u32 muStreamPoolGuid;      // +0x20
    const void *mpHeader;      // +0x24  (POINTER -- widens)
    const void *mpSeekTable;   // +0x28  (POINTER -- widens)
    u16 muRecordSize;          // +0x2C  <- the ring advance PlayHandler hands back
    u8  mu8ExpelMode;          // +0x2E
    f32 mfHandle;              // +0x30
    char macPath[1];           // +0x38  NUL-terminated, variable length
};

// vt[1] == EventEvent @0x82BA5C48 (hand-decoded from the raw XEX -- no dossier).
int SndPlayer1::Event(int aiEventId, void *apParam)
{
    System *lpSystem = mpSystemUseGetSystemAccessor;      // lwz r8, 4(r9)

    SndPlayer1PlayParams  lExpanded;   // console: the 0x30-byte block at sp+0x60
    SndPlayer1PlayParams *lpPlay;      // console r10

    switch (aiEventId)
    {
    // ------------------------------------------------------------------ 1 STOP
    case 1:
    {
        SndPlayer1StopCommand *lpCmd = reinterpret_cast<SndPlayer1StopCommand *>(
            lpSystem->mpDeferredRingBase + lpSystem->muDeferredRingCursor);
        lpSystem->muDeferredRingCursor +=
            static_cast<u32>(sizeof(SndPlayer1StopCommand));   // console addi r11,r11,8
        lpCmd->mpHandler = &SndPlayer1::StopHandler;
        lpCmd->mpPlayer  = this;
        return 0;
    }

    // --------------------------------------------------------- 2 ISREQUESTDONE
    case 2:
    {
        SndPlayer1IsRequestDoneParams *lpQ =
            static_cast<SndPlayer1IsRequestDoneParams *>(apParam);
        const f32 lfHandle  = lpQ->mfHandle;
        const f32 lfCurrent = mAttributes.mfCurrentRequestHandle;   // attribute 0
        f32 lfDone = 0.0f;                                          // flt_82001CC0

        if (lfHandle < lfCurrent)               // blt: unordered -> NOT taken; ordered as written
        {
            lfDone = 1.0f;                      // flt_82001C98
        }
        else
        {
            // Both inner guards JUMP TO FALSE, so an unordered compare CONTINUES --
            // write the negated ordered predicate, never "<=" / ">" flipped.
            const bool lbInWindow =
                (lfHandle == lfCurrent)                                     // beq
                || (!(lfHandle >  mfLastRequestProcessed)                   // bgt -> false
                 && !(lfHandle <= mfLastRequestSuccessfullyProcessed));     // ble -> false
            // bne -> false, and NaN counts as "not equal", so NaN yields false here.
            if (lbInWindow && mAttributes.mdSampleLength == 0.0)            // lfd +0x38 vs dbl_82001CA8
                lfDone = 1.0f;
        }
        lpQ->mfIsDone = lfDone;
        return 0;
    }

    // --------------------------------------------------- 3 GETREQUESTBUFFERED
    case 3:
    {
        SndPlayer1BufferedParams *lpQ = static_cast<SndPlayer1BufferedParams *>(apParam);
        if (mu8MaxRequests == 0)
            return 0;                 // FAITHFUL: the param block is left UNTOUCHED

        const f32 lfHandle = lpQ->mfHandle;
        for (u32 luIndex = 0; luIndex < mu8MaxRequests; ++luIndex)  // +0x1CA re-read each lap
        {
            RequestInternal *lpReq = GetRequest(luIndex);   // host-layout helper, never base+0x30*i
            if (lpReq->mfHandle == lfHandle)                // bne -> next (NaN -> next)
            {
                const u8 lu8State = lpReq->mu8State;
                if (lu8State != 0 && lu8State != 4)         // skip FREE / COMPLETE
                {
                    RequestExternal *lpExt = &mpRequestExternal[luIndex];
                    const u8 lu8PlayType = lpExt->mu8PlayType;

                    if (lu8PlayType == 0)                   // resident
                    {
                        lpQ->mfBuffered = 0.0f;
                        lpQ->mfComplete = 1.0f;
                        return 0;
                    }
                    if (lu8PlayType == 1 || lu8PlayType == 2)   // streamed
                    {
                        lpQ->mfComplete = 0.0f;
                        // lwa: the byte counter is loaded SIGN-EXTENDED.
                        lpQ->mfBuffered = static_cast<f32>(
                            static_cast<f64>(static_cast<s32>(lpExt->muBytesFed)));

                        Stream *lpStream = lpExt->mpStream;
                        if (lpStream)
                        {
                            s32 liBytes;
                            // *** CONSOLE QUIRK, PRESERVED VERBATIM ***
                            // The loop INDEX is float-compared against attribute 0,
                            // which RwacTimerClient @0x82BA69F4 fills from
                            // mfCurrentRequestHandle (+0x1A0) -- a HANDLE, not an index.
                            // Raw bytes: 78 CB 00 20 (clrldi r11,r6,32), C0 09 00 28
                            // (lfs f0,0x28(r9)). Do NOT "fix" this to mu8CurrentRequestIndex.
                            if (lpReq->miLoopStart >= 0
                                && static_cast<f32>(static_cast<f64>(luIndex))
                                       == mAttributes.mfCurrentRequestHandle)
                                liBytes = Stream::GetBytesBuffered(lpStream);         // 0x82BBD940
                            else
                                liBytes = Stream::GetRequestBytesBuffered(            // 0x82BBD948
                                              lpStream, lpExt->muStreamerRequestId);

                            lpQ->mfBuffered = static_cast<f32>(static_cast<f64>(liBytes))
                                            + lpQ->mfBuffered;                        // fadds

                            if (Stream::GetRequestState(lpStream,
                                    lpExt->muStreamerRequestId) != 3                  // 0x82BBD9D0
                                && Stream::GetState(lpStream) != 2)                   // 0x82BBD990
                                return 0;      // mfComplete stays 0.0f
                        }
                        lpQ->mfComplete = 1.0f;
                        return 0;
                    }
                    // any other play type falls through to the zeroing tail
                }
            }
            lpQ->mfBuffered = 0.0f;   // written on EVERY non-matching lap
            lpQ->mfComplete = 0.0f;
        }
        return 0;
    }

    // -------------------------------------------------------- 4 MODIFYSTARTTIME
    case 4:
    {
        const SndPlayer1ModifyStartTimeParams *lpP =
            static_cast<const SndPlayer1ModifyStartTimeParams *>(apParam);
        SndPlayer1ModifyStartTimeCommand *lpCmd =
            reinterpret_cast<SndPlayer1ModifyStartTimeCommand *>(
                lpSystem->mpDeferredRingBase + lpSystem->muDeferredRingCursor);
        lpSystem->muDeferredRingCursor +=
            static_cast<u32>(sizeof(SndPlayer1ModifyStartTimeCommand)); // console addi 0x18
        lpCmd->mpHandler   = &SndPlayer1::ModifyStartTimeHandler;
        lpCmd->mpPlayer    = this;
        lpCmd->mdStartTime = lpP->mdStartTime;
        lpCmd->mfHandle    = lpP->mfHandle;
        return 0;
    }

    // ------------------------------------------------- 0 PLAY (legacy expand)
    case 0:
    {
        const SndPlayer1PlayLegacyParams *lpL =
            static_cast<const SndPlayer1PlayLegacyParams *>(apParam);
        lExpanded.mdStartTime        = lpL->mdStartTime;        // exp+0x00 <- +0x00
        lExpanded.mdStreamFileOffset = lpL->mdStreamFileOffset; // exp+0x08 <- +0x08
        lExpanded.mdSeekTime         = 0.0;                     // exp+0x10 <- dbl_82001CA8
        lExpanded.mpcPath            = lpL->mpcPath;            // exp+0x18 <- +0x10
        lExpanded.mpHeader           = lpL->mpHeader;           // exp+0x1C <- +0x14
        lExpanded.mpSeekTable        = 0;                       // exp+0x20 <- li 0
        lExpanded.muStreamPoolGuid   = lpL->muStreamPoolGuid;   // exp+0x24 <- +0x18
        lExpanded.mfExpelMode        = lpL->mfExpelMode;        // exp+0x28 <- +0x1C
        lExpanded.mfHandle           = lpL->mfHandle;           // exp+0x2C <- +0x20 (dead copy)
        lpPlay = &lExpanded;
        break;
    }
    // ----------------------------------------------------------------- 5 PLAY1
    case 5:
        lpPlay = static_cast<SndPlayer1PlayParams *>(apParam);  // mr r10, r31
        break;

    default:
        return 0;   // every other id is a no-op
    }

    // ------------------------------------------------- shared PLAY / PLAY1 tail
    // Handle counter. *** THE WRAP TARGET IS 1.0f, NOT 0.0f *** -- the wrap store at
    // 0x82BA5F60 re-uses f0, which still holds the 1.0f increment loaded at 0x82BA5F38.
    *mpRequestHandleCounter = *mpRequestHandleCounter + 1.0f;      // fadds, flt_82001C98
    // fcmpu + ble: unordered falls THROUGH to the wrap, so negate the ordered predicate.
    if (!(*mpRequestHandleCounter <= 4194304.0f))                  // flt_820B56EC
        *mpRequestHandleCounter = 1.0f;

    const f32 lfHandle = *mpRequestHandleCounter;
    lpPlay->mfHandle = lfHandle;                                   // stfs 0x2C(r10)
    if (aiEventId == 0)
        static_cast<SndPlayer1PlayLegacyParams *>(apParam)->mfHandle = lfHandle; // +0x20

    // Variable record size. Console: (nameBytes + 0x3B) & ~3, i.e.
    // align_up(0x38 + nameBytes, 4) with 0x38 = the CONSOLE head (four 32-bit pointers).
    // HOST: use the host head offset and align to alignof(SndPlayer1PlayCommand) (8), so
    // the NEXT record's f64 fields stay aligned. NEVER transliterate 0x3B / ~3.
    u32 luNameBytes = 1;                                    // console default when path is null
    if (lpPlay->mpcPath)
        luNameBytes = static_cast<u32>(std::strlen(lpPlay->mpcPath)) + 1;
    const size_t lkAlign = alignof(SndPlayer1PlayCommand);
    const u32 luRecordSize = static_cast<u32>(
        (offsetof(SndPlayer1PlayCommand, macPath) + luNameBytes + (lkAlign - 1))
        & ~(lkAlign - 1));
    // muRecordSize is a u16 on the wire; assert the widened record still fits.
    RWAUDIO_ASSERT(luRecordSize <= 0xFFFFu);

    SndPlayer1PlayCommand *lpCmd = reinterpret_cast<SndPlayer1PlayCommand *>(
        lpSystem->mpDeferredRingBase + lpSystem->muDeferredRingCursor);
    lpSystem->muDeferredRingCursor += luRecordSize;

    lpCmd->mpPlayer           = this;
    lpCmd->mpHandler          = &SndPlayer1::PlayHandler;
    lpCmd->mfHandle           = *mpRequestHandleCounter;   // console RE-READS memory here
    lpCmd->mdStartTime        = lpPlay->mdStartTime;
    lpCmd->mdStreamFileOffset = lpPlay->mdStreamFileOffset;
    lpCmd->mdSeekTime         = lpPlay->mdSeekTime;
    lpCmd->mpHeader           = lpPlay->mpHeader;          // exp+0x1C -> cmd+0x24
    lpCmd->mpSeekTable        = lpPlay->mpSeekTable;       // exp+0x20 -> cmd+0x28
    lpCmd->muStreamPoolGuid   = lpPlay->muStreamPoolGuid;  // exp+0x24 -> cmd+0x20
    lpCmd->muRecordSize       = static_cast<u16>(luRecordSize);
    // fctidz to a doubleword, then the LOW byte of the big-endian store: a truncating
    // f32 -> s64 -> u8 conversion with no range check (console has none either).
    lpCmd->mu8ExpelMode = static_cast<u8>(static_cast<s64>(lpPlay->mfExpelMode));

    if (luNameBytes == 1)          // path null OR empty string -- same console branch
    {
        lpCmd->macPath[0] = '\0';
    }
    else
    {
        const char *lpcSrc = lpPlay->mpcPath;   // store-then-test: the NUL IS copied
        char *lpcDst = lpCmd->macPath;
        for (;;)
        {
            const char lcByte = *lpcSrc++;
            *lpcDst++ = lcByte;
            if (lcByte == '\0')
                break;
        }
    }
    // The console's r3 is an uninitialised passthrough every caller discards (the same
    // situation Dac::Event documents), so return 0.
    return 0;
}
```

### `rw::audio::core::SndPlayer1::PlayHandler` @ `0x82BA41D8`  [DECODED]

**Signature**

```cpp
static int PlayHandler(void *apCommand);   // console: int __fastcall PlayHandler(SndPlayer1PlayCommand *r3)
// Deferred-ring handler: System::ExecuteCommands calls it with the record's own address and advances the byte cursor by the RETURN.
```

**Behaviour**

r29 = cmd; r30 = cmd->mpPlayer (+0x04); r27 = self->mpSystemUseGetSystemAccessor.

RESERVE (0x82BA41EC..0x82BA4214). self->mfLastRequestProcessed (+0x1B4) = cmd->mfHandle (+0x30) — this store happens BEFORE the slot is even tested, so a rejected Play still bumps it. i = self->mu8NextFreeRequest (+0x1C7); lpReq = self + muRequestArrayOffset(+0x1C4) + 0x30*i. If lpReq->mu8State (+0x2A) != 0 (slot not FREE) jump straight to the return — no other state is touched.

SEED (0x82BA4218..0x82BA4274). lpExt = self->mpRequestExternal(+0x58) + 0x50*i. lpReq->mfHandle(+0x0C) = cmd->mfHandle; lpReq->mpDecoder(+0x08) = 0; lpReq->mdStartTime(+0x00) = cmd->mdStartTime(+0x08); lpExt->mdStreamFileOffset(+0x00) = cmd->mdStreamFileOffset(+0x10); lpExt->mu8ExpelMode(+0x4B) = cmd->mu8ExpelMode(+0x2E); lpReq->mu8State = 1 (QUEUED); lpExt->+0x14, +0x18, +0x24, +0x2C, +0x1C all cleared (samples fed, bytes fed, stream handle, streamer request id, loop file name). Then UnpackHeader(self, self->mu8NextFreeRequest /*RE-READ from +0x1C7*/, cmd->mpHeader /*+0x24*/).

SEEK-SAMPLE COMPUTE (0x82BA4278..0x82BA42D0). skip = (s32)trunc(lpReq->mfSampleRate(+0x10) * cmd->mdSeekTime(+0x18)) via fmul/fctiwz/stfiwx. If skip <= 0 -> skip = 0 and the two clamps are SKIPPED (the `mr r6,r26; cmpwi; beq` pair is an unconditional bypass). Otherwise: if (lpExt->mu8PlayType(+0x49) == 2) skip = 0; if (lpReq->miLoopStart(+0x18) >= 0) skip = 0. Then if (lpReq->miNumSamples(+0x14) <= skip) -> FAIL.

FAIL (0x82BA4390..0x82BA4398), reached from four places (short sound, AcquireStream null, Alloc null): lpReq->miNumSamples = 0; lpReq->mu8State = 0 (back to FREE); fall to the return. NOTE mu8NextFreeRequest is NOT advanced and mfLastRequestSuccessfullyProcessed is NOT updated on this path.

SetSeekData(self, self->mu8NextFreeRequest, cmd->mpSeekTable(+0x28), skip)  @0x82B9C068.

PLAY-TYPE GATE (0x82BA42E4..0x82BA42F4). If lpExt->mu8PlayType is neither 1 nor 2, jump directly to COMMIT — resident sounds do no streaming work.

STREAM OPEN (0x82BA42F8..0x82BA4324). lpExt->mpStreamPool(+0x20) = StreamPool::GetInstance(cmd->muStreamPoolGuid /*+0x20*/) @0x82B6BA68. Then AcquireStream(pool, /*f1*/ self->mpVoice->mfPriority /*Voice+0x38*/, /*r5*/ &SndPlayer1::StreamLostCallback, /*r6*/ self) @0x82B6BAB0 -> lpExt->mpStreamHandle(+0x24); null -> FAIL. lpExt->mpStream(+0x28) = handle->+0x14.

LOOP-FILENAME DUP (0x82BA4334..0x82BA43A4). Only when lpReq->miLoopStart >= 0: open-coded strlen over cmd->macPath (cmd+0x38), n = len+1; lpExt->mpcLoopFileName(+0x1C) = System::Alloc(self->mpSystem, n, "SndPlayer1 StreamLoopFileName" /*0x821745D8*/, 16, 0); null -> FAIL; XMemCpy(dst, cmd->macPath, n).

FIRST QUEUE (0x82BA43A8..0x82BA440C). gate = true; if (playType == 2 && miLoopStart >= 0 && lpExt->miResidentSamples(+0x10) > miLoopStart) gate = false. When gate: offset = (s64)trunc(lpExt->mdStreamFileOffset) + lpExt->muSeekByteOffset(+0x40); lpExt->muStreamerRequestId(+0x2C) = Stream::QueueFile(lpExt->mpStream, cmd->macPath, /*flags*/0, offset, &SndPlayer1ChunkParsed /*0x82BA3FF8*/, self). (0x82BC09B0 is a five-argument shuffle thunk that inserts a 0 in the third slot and tail-branches to rw::core::filesys::Stream::QueueFile.)

LOOP PREFETCH (0x82BA4410..0x82BA449C). Only when miLoopStart >= 0. gate2 = true; if (playType == 2 && lpExt->miResidentSamples(+0x10) >= lpReq->miNumSamples(+0x14)) gate2 = false. When gate2, run the SAME QueueFile TWICE (r27 = 2 countdown), each time with offset = (s64)trunc((f64)(s32)lpExt->miLoopStreamOffset(+0x0C) /*lwa, sign-extended*/ + lpExt->mdStreamFileOffset); the first non-zero result is latched into muStreamerRequestId only if it is still 0.

COMMIT (0x82BA44A0..0x82BA44CC). lpReq->mu8State = 1 (re-store, redundant on the fall-through path but reached from the resident shortcut too); n = self->mu8NextFreeRequest + 1 truncated to u8; if (n == self->mu8MaxRequests(+0x1CA)) n = 0; self->mu8NextFreeRequest = n; self->mfLastRequestSuccessfullyProcessed(+0x1B8) = cmd->mfHandle.

RETURN (0x82BA44D0): `lhz r3, 0x2C(r29)` = cmd->muRecordSize — THE RING-CURSOR ADVANCE, taken from the record itself because the record is variable-size. Every exit path (including both failure paths) returns it.

**Constants**

aSndplayer1Stre  vaddr 0x821745D8  file_off 0x001775D8  raw BE `53 6E 64 50 6C 61 79 65 72 31 20 53 74 72 65 61 6D 4C 6F 6F 70 46 69 6C 65 4E 61 6D 65 00` = "SndPlayer1 StreamLoopFileName" (recomputed from the lis/addi pair at 0x82BA4364/0x82BA436C; the next string in rodata is "EXPELMOD...").
SndPlayer1ChunkParsed callback vaddr 0x82BA3FF8 (recomputed from BOTH lis/addi pairs, 0x82BA43E0/0x82BA43EC and 0x82BA4454/0x82BA4460 — same target; the bytes there `7C 6B 1B 78 2B 04 00 08 40 98 00 0C 38 60 00 00 4E 80 00 20` are a real function prologue, not data).
Immediates: alloc alignment 16, allocator override 0, System::Alloc flag path as usual; QueueFile flags word 0 injected by the thunk at 0x82BC09B0 (`mr r8,r7; mr r7,r6; mr r6,r5; li r5,0; b Stream::QueueFile`).
No float literals are loaded from rodata by this function.

**Host hazards**

1. THE RETURN IS THE RING-CURSOR ADVANCE and it is READ OUT OF THE RECORD (`lhz +0x2C`), not an immediate — so it is automatically the host size as long as Event() stamps the host-computed size. This is the one handler in the cluster whose return is data-driven; do NOT replace it with sizeof(), because the record is variable-length.
2. `muRecordSize` is u16; assert on the producer side.
3. RECORD STRIDES: 0x30 (RequestInternal, holds Decoder*) and 0x50 (RequestExternal, holds five pointers) are console strides. All indexing must go through host-layout helpers.
4. cmd->macPath is read via `addi r25, r29, 0x38` — the console fixed-head size. On the host that is `lpCmd->macPath`, and the offset differs.
5. Voice priority arrives in f1: `lwz r11, 8(r30)` (PlugIn::mpVoice) then `lfs f1, 0x38(r11)` (Voice::mfPriority). Getting the argument register wrong here silently passes garbage as a stream priority.
6. `lwa 0x0C(r31)` (miLoopStreamOffset) is SIGN-EXTENDED before fcfid; a u32 read diverges on negative/large values.
7. The seek-sample conversion (`fctiwz`) and the loop offsets (`fctidz`) are TRUNCATING with no range or NaN check — a NaN seek time yields an implementation-defined integer on the host where PPC yields 0x80000000. Clamp only if the parent decides to; the console does not.
8. `mfLastRequestProcessed` is written before the FREE-slot test, so a dropped Play still moves it — this feeds the ISREQUESTDONE window in Event(), so the ordering is observable and must be preserved.
9. The loop chunk is queued TWICE (r27 = 2), and the streamer-request-id latch only takes the first non-zero. Easy to collapse to one call by accident.
10. On every FAIL path mu8NextFreeRequest is NOT advanced but mfLastRequestProcessed already was — the asymmetry is real.
11. 0x82BC09B0 is a THUNK, not the destination: it injects a zero third argument. Calling Stream::QueueFile with the caller's five arguments unshifted is wrong.

**Implementation sketch**

```cpp
// @0x82BA41D8 -- deferred handler for the variable-size PlayCommand.
// RETURN = THE RING-CURSOR ADVANCE. Console `lhz r3, 0x2C(r29)`: the size the producer
// stamped into the record, which on the host is the HOST-computed size (see Event()).
int SndPlayer1::PlayHandler(void *apCommand)
{
    SndPlayer1PlayCommand *lpCmd = static_cast<SndPlayer1PlayCommand *>(apCommand);
    SndPlayer1 *lpSelf = lpCmd->mpPlayer;
    System *lpSystem = lpSelf->mpSystemUseGetSystemAccessor;

    // Bumped BEFORE the slot test -- a rejected Play still advances it. Faithful.
    lpSelf->mfLastRequestProcessed = lpCmd->mfHandle;

    const u8 lu8Index = lpSelf->mu8NextFreeRequest;
    RequestInternal *lpReq = lpSelf->GetRequest(lu8Index);   // host-layout helper
    if (lpReq->mu8State != 0)                                // not FREE -> drop the command
        return static_cast<int>(lpCmd->muRecordSize);

    RequestExternal *lpExt = &lpSelf->mpRequestExternal[lu8Index];

    lpReq->mfHandle    = lpCmd->mfHandle;
    lpReq->mpDecoder   = 0;
    lpReq->mdStartTime = lpCmd->mdStartTime;
    lpExt->mdStreamFileOffset = lpCmd->mdStreamFileOffset;
    lpExt->mu8ExpelMode       = lpCmd->mu8ExpelMode;
    lpReq->mu8State           = 1;                  // QUEUED
    lpExt->muSamplesFed       = 0;
    lpExt->muBytesFed         = 0;
    lpExt->mpStreamHandle     = 0;
    lpExt->muStreamerRequestId= 0;
    lpExt->mpcLoopFileName    = 0;

    UnpackHeader(lpSelf, lpSelf->mu8NextFreeRequest, lpCmd->mpHeader);  // re-reads +0x1C7

    // fmul + fctiwz: truncating f32*f64 -> s32, no range check (console has none).
    s32 liSkipSamples = static_cast<s32>(lpReq->mfSampleRate * lpCmd->mdSeekTime);
    if (liSkipSamples > 0)
    {
        if (lpExt->mu8PlayType == 2)   liSkipSamples = 0;
        if (lpReq->miLoopStart >= 0)   liSkipSamples = 0;
    }
    else
    {
        liSkipSamples = 0;
    }

    if (lpReq->miNumSamples <= liSkipSamples)
        goto fail;

    SetSeekData(lpSelf, lpSelf->mu8NextFreeRequest, lpCmd->mpSeekTable, liSkipSamples);

    if (lpExt->mu8PlayType == 1 || lpExt->mu8PlayType == 2)
    {
        lpExt->mpStreamPool = StreamPool::GetInstance(lpCmd->muStreamPoolGuid);
        lpExt->mpStreamHandle = StreamPool::AcquireStream(
            lpExt->mpStreamPool,
            lpSelf->mpVoice->mfPriority,                 // f1 <- Voice +0x38
            &SndPlayer1::StreamLostCallback,
            lpSelf);
        if (!lpExt->mpStreamHandle)
            goto fail;
        lpExt->mpStream = lpExt->mpStreamHandle->mpStream;   // handle +0x14

        if (lpReq->miLoopStart >= 0)
        {
            const u32 luBytes =
                static_cast<u32>(std::strlen(lpCmd->macPath)) + 1;
            lpExt->mpcLoopFileName = static_cast<char *>(System::Alloc(
                lpSystem, luBytes, "SndPlayer1 StreamLoopFileName", 16, 0));
            if (!lpExt->mpcLoopFileName)
                goto fail;
            std::memcpy(lpExt->mpcLoopFileName, lpCmd->macPath, luBytes);
        }

        bool lbQueueHead = true;
        if (lpExt->mu8PlayType == 2 && lpReq->miLoopStart >= 0
            && lpExt->miResidentSamples > lpReq->miLoopStart)
            lbQueueHead = false;
        if (lbQueueHead)
        {
            // fctidz on the f64 offset, then + the seek byte offset SetSeekData produced.
            const s64 lkOffset =
                static_cast<s64>(lpExt->mdStreamFileOffset) + lpExt->muSeekByteOffset;
            lpExt->muStreamerRequestId = rw::core::filesys::Stream::QueueFile(
                lpExt->mpStream, lpCmd->macPath, /*flags*/ 0, lkOffset,
                &SndPlayer1::ChunkParsed, lpSelf);       // thunk 0x82BC09B0 -> QueueFile
        }

        if (lpReq->miLoopStart >= 0)
        {
            bool lbQueueLoop = true;
            if (lpExt->mu8PlayType == 2
                && lpExt->miResidentSamples >= lpReq->miNumSamples)
                lbQueueLoop = false;
            if (lbQueueLoop)
            {
                for (int liLap = 2; liLap != 0; --liLap)   // the loop chunk is queued TWICE
                {
                    // lwa: miLoopStreamOffset is loaded sign-extended, then fcfid'd.
                    const s64 lkOffset = static_cast<s64>(
                        static_cast<f64>(static_cast<s64>(lpExt->miLoopStreamOffset))
                        + lpExt->mdStreamFileOffset);
                    const u32 luId = rw::core::filesys::Stream::QueueFile(
                        lpExt->mpStream, lpCmd->macPath, /*flags*/ 0, lkOffset,
                        &SndPlayer1::ChunkParsed, lpSelf);
                    if (lpExt->muStreamerRequestId == 0)
                        lpExt->muStreamerRequestId = luId;
                }
            }
        }
    }

    // ---- COMMIT
    lpReq->mu8State = 1;                                     // QUEUED (re-store, faithful)
    {
        u8 lu8Next = static_cast<u8>(lpSelf->mu8NextFreeRequest + 1);
        if (lu8Next == lpSelf->mu8MaxRequests)
            lu8Next = 0;
        lpSelf->mu8NextFreeRequest = lu8Next;
    }
    lpSelf->mfLastRequestSuccessfullyProcessed = lpCmd->mfHandle;
    return static_cast<int>(lpCmd->muRecordSize);

fail:
    lpReq->miNumSamples = 0;
    lpReq->mu8State = 0;                                     // back to FREE
    return static_cast<int>(lpCmd->muRecordSize);            // RING-CURSOR ADVANCE
}
```

### `rw::audio::core::SndPlayer1::StopHandler` @ `0x82BA44E0`  [DECODED]

**Signature**

```cpp
static int StopHandler(void *apCommand);   // console: int __fastcall StopHandler(SndPlayer1StopCommand *r3)
```

**Behaviour**

self = cmd->mpPlayer (`lwz r31, 4(r3)`). r28 = 0 held live as the zero source; r29 = index; r30 = index*0x30.

TEARDOWN LOOP (0x82BA44F8..0x82BA453C). Guarded by `if (self->mu8MaxRequests /*+0x1CA*/ != 0)`. Each lap recomputes lpReq = self + muRequestArrayOffset(+0x1C4) + r30 and tests lpReq->mu8State(+0x2A): if NON-ZERO, call RemoveRequest(self, index) @0x82BA0460. Note the test is `!= 0`, i.e. COMPLETE(4) requests ARE torn down here (unlike the FREE/COMPLETE skip idiom used everywhere else in this class). mu8MaxRequests is RE-READ from memory at the bottom of every lap (0x82BA452C) — RemoveRequest could in principle change it, and the faithful transliteration must re-read.

RemoveRequest itself (context, @0x82BA0460): Decoder::Release on lpReq->mpDecoder then null it; walk all 20 feed slots (base self+0x5C, stride 0x10) and for every slot whose mu8RequestIndex(+0x0E) == index, clear mu8State(+0x0D), subtract chunk->+0x04 from lpExt->muBytesFed(+0x18), Stream::ReleaseChunk when a stream handle exists, and null the chunk pointer; then StreamPool::ReleaseStream under System::Lock/Unlock; System::Free the loop file name; lpReq->mu8State = 0; and if lpExt->mu8ExpelMode(+0x4B) == 1, Voice::ExpelAfterDecay(self->mpVoice).

RESET BLOCK (0x82BA4540..0x82BA4564), all unconditional:
  +0x1C9 mu8CurrentRequestIndex     = 0
  +0x1C7 mu8NextFreeRequest         = 0
  +0x1C8 mu8NextRequestToFree       = 0
  +0x1A8 muCurrentRequestSamplesPlayed = 0   (stw, 32-bit)
  +0x1AC muCurrentRequestSampleCount   = 0   (stw, 32-bit)
  +0x1CD mu8NextFeedSlotToFill      = 0
  +0x1CE mu8NextFeedSlotToFree      = 0
  +0x1CC mu8DeclickSamplesRemaining = 16     (`li r11, 0x10`)  <-- ARMS a 16-sample declick ramp
Deliberately NOT reset: mu8DeclickOffsetsGathered (+0x1CB), the handle counter behind mpRequestHandleCounter (+0x1B0), mfLastRequestProcessed/mfLastRequestSuccessfullyProcessed (+0x1B4/+0x1B8), mfCurrentRequestHandle (+0x1A0), mfPreviousSampleRate (+0x1BC), the attribute slots.

RETURN (0x82BA454C): `li r3, 8` — THE RING-CURSOR ADVANCE, the console sizeof(SndPlayer1StopCommand).

**Constants**

No rodata constants. The only immediates are 0x10 (=16, the declick sample count stored to +0x1CC), 0x30 (the console RequestInternal stride, used only as the loop's byte step) and the return value 8 (the console record size).

**Host hazards**

1. THE RETURN IS THE RING-CURSOR ADVANCE. Console `li r3, 8` is the CONSOLE sizeof — the record holds a 32-bit function pointer and a 32-bit `this`. On x64 return sizeof(SndPlayer1StopCommand) (16), and Event()'s STOP advance must be the same expression.
2. The 0x30 stride is a console record stride (RequestInternal contains a Decoder*): index by host layout.
3. The state test is `!= 0`, NOT the FREE/COMPLETE 3-way idiom. Copying the idiom in from ModifyStartTimeHandler / Event-3 would leak completed requests' decoders, streams and loop-filename allocations.
4. mu8MaxRequests is re-read every lap; hoisting it into a local changes behaviour if RemoveRequest ever mutates it.
5. muCurrentRequestSamplesPlayed / muCurrentRequestSampleCount are 32-bit (`stw`) while everything around them at +0x1C7..+0x1CE is a byte (`stb`) — a wholesale memset over the tail would be wrong.
6. +0x1CB (declick offsets gathered) is deliberately left alone while +0x1CC is set to 16. Per the adversarial review, Process's declick path SUBTRACTS THE PUBLISHED COUNT from +0x1CC rather than decrementing by one — do not re-derive the pairing from the prior architecture report's section 4.
7. RemoveRequest's feed walk uses feed stride 0x10, state at feed+0x0D and owning-request index at feed+0x0E; SubmitChunk @0x82BA465C writes the decoder request handle with `stb r3, 0x0C(r30)` — a BYTE at feed+0x0C, not the 32-bit word the prior architecture report's section 2 implies.

**Implementation sketch**

```cpp
// @0x82BA44E0 -- the deferred STOP: tear every live request down and re-arm declick.
// RETURN = THE RING-CURSOR ADVANCE (console `li r3, 8` == the CONSOLE record size).
int SndPlayer1::StopHandler(void *apCommand)
{
    SndPlayer1StopCommand *lpCmd = static_cast<SndPlayer1StopCommand *>(apCommand);
    SndPlayer1 *lpSelf = lpCmd->mpPlayer;

    // The bound is RE-READ from mu8MaxRequests on every lap (lbz 0x1CA inside the loop).
    for (u32 luIndex = 0; luIndex < lpSelf->mu8MaxRequests; ++luIndex)
    {
        // NOTE: plain != 0, so COMPLETE(4) requests are torn down here too -- this is
        // NOT the FREE/COMPLETE skip idiom the rest of the class uses.
        if (lpSelf->GetRequest(luIndex)->mu8State != 0)
            RemoveRequest(lpSelf, static_cast<u8>(luIndex));
    }

    lpSelf->mu8CurrentRequestIndex        = 0;
    lpSelf->mu8NextFreeRequest            = 0;
    lpSelf->mu8NextRequestToFree          = 0;
    lpSelf->muCurrentRequestSamplesPlayed = 0;
    lpSelf->muCurrentRequestSampleCount   = 0;
    lpSelf->mu8NextFeedSlotToFill         = 0;
    lpSelf->mu8NextFeedSlotToFree         = 0;
    lpSelf->mu8DeclickSamplesRemaining    = 16;   // li r11, 0x10 -- arm the declick ramp

    return static_cast<int>(sizeof(SndPlayer1StopCommand));   // console li r3, 8
}
```

### `rw::audio::core::SndPlayer1::ModifyStartTimeHandler` @ `0x82BA03D0`  [DECODED]

**Signature**

```cpp
static int ModifyStartTimeHandler(void *apCommand);   // console: int __fastcall ModifyStartTimeHandler(SndPlayer1ModifyStartTimeCommand *r3)
```

**Behaviour**

Leaf function, no stack frame, 35 instructions.

r10 = cmd->mpPlayer (`lwz r10, 4(r3)`); r8 = index = 0; r7 = self->mu8MaxRequests (+0x1CA). If it is zero the whole body is skipped.
r11 is set ONCE to self + muRequestArrayOffset(u16 +0x1C4) + 0x2A — i.e. a walking pointer parked on RequestInternal[0].mu8State — and thereafter only advanced by 0x30. Every field access is a NEGATIVE displacement off that cursor: -0x1E is +0x0C (mfHandle), -0x2A is +0x00 (mdStartTime), 0 is +0x2A (mu8State).
f0 = cmd->mfHandle (`lfs f0, 0x10(r3)`).

SCAN (0x82BA03F4..0x82BA0430): per lap, `lfs f13, -0x1E(r11)`; `fcmpu`; `bne` -> next lap. On a handle match, run the 3-way state idiom (state == 4 -> 0; state != 0 -> 1; state == 0 -> 0) and break out on non-zero, i.e. accept anything that is neither FREE(0) nor COMPLETE(4). Otherwise ++index, r11 += 0x30, continue while index < mu8MaxRequests. Falling off the end goes straight to the return.

APPLY (0x82BA0438..0x82BA0450): r10 = self->mpSystemUseGetSystemAccessor (`lwz r10, 4(r10)` — note r10 still held `self`, so this is self->mpSystem). f0 = lpReq->mdStartTime (`lfd -0x2A(r11)`); f13 = mpSystem->mfSystemTime (`lfd 8(r10)` — System +0x08, PDB mSystemTime, confirmed against the committed PlugIn.h). `fcmpu cr6, f0, f13`; `ble cr6` -> SKIP the write. So the store happens only when the request's CURRENT start time is strictly in the future relative to the System clock: an already-started (or already-due) request is never retimed. Then lpReq->mdStartTime = cmd->mdStartTime (`lfd 8(r3)` / `stfd -0x2A(r11)`).

RETURN (0x82BA0454): `li r3, 0x18` — THE RING-CURSOR ADVANCE, the console sizeof(SndPlayer1ModifyStartTimeCommand) = 24. Returned on every path, including the mu8MaxRequests == 0 and no-match paths.

**Constants**

No rodata constants and no float literals. Immediates only: 0x2A (the state-byte bias baked into the walking cursor), 0x30 (console RequestInternal stride), 4 and 0 (the COMPLETE/FREE state comparands), and the return 0x18 (console record size).

**Host hazards**

1. THE RETURN IS THE RING-CURSOR ADVANCE. Console `li r3, 0x18` counts a 32-bit function pointer plus a 32-bit `this` plus f64+f32+pad. On x64 return sizeof(SndPlayer1ModifyStartTimeCommand) (32 with 8-byte pointers), and Event()'s MODIFYSTARTTIME advance must use the identical expression.
2. NaN POLARITY: `fcmpu` + `ble` at 0x82BA0448 jumps AWAY from the store, so an unordered compare PERFORMS the store. The host predicate must be `!(current <= systemTime)`, never `current > systemTime`.
3. The handle match is `fcmpu`/`bne`: a NaN handle matches nothing (correct as written with `!=`).
4. The walking cursor with negative displacements (-0x1E, -0x2A) is a compiler artifact over the CONSOLE 0x30 stride and the console field offsets. Do not transliterate the biases; index the host record by name.
5. `lwz r10, 4(r10)` reuses r10 (which held `self`) to fetch mpSystem — easy to misread as cmd+4 twice. The clock is System::mfSystemTime (+0x08), NOT Mixer::mdStreamTime (+0x30000); the two are different time bases even though Process's WaitForStartTime compares against the Mixer's.
6. mu8MaxRequests is loaded once here (unlike StopHandler, which re-reads it) — keep that difference.
7. The scan stops at the FIRST accepted match; duplicate handles (possible after a counter wrap to 1.0f) retime only the earliest slot.

**Implementation sketch**

```cpp
// @0x82BA03D0 -- retime a still-pending request.
// RETURN = THE RING-CURSOR ADVANCE (console `li r3, 0x18` == the CONSOLE record size).
int SndPlayer1::ModifyStartTimeHandler(void *apCommand)
{
    const SndPlayer1ModifyStartTimeCommand *lpCmd =
        static_cast<const SndPlayer1ModifyStartTimeCommand *>(apCommand);
    SndPlayer1 *lpSelf = lpCmd->mpPlayer;

    if (lpSelf->mu8MaxRequests != 0)
    {
        const f32 lfHandle = lpCmd->mfHandle;
        for (u32 luIndex = 0; luIndex < lpSelf->mu8MaxRequests; ++luIndex)
        {
            RequestInternal *lpReq = lpSelf->GetRequest(luIndex);   // host-layout helper
            if (lpReq->mfHandle != lfHandle)                        // bne -> next (NaN -> next)
                continue;
            const u8 lu8State = lpReq->mu8State;
            if (lu8State == 0 || lu8State == 4)                     // FREE / COMPLETE
                continue;

            // fcmpu + ble SKIPS the write, so an unordered compare WRITES.
            // Negated ordered predicate -- never spell this "start > systemTime".
            if (!(lpReq->mdStartTime
                  <= lpSelf->mpSystemUseGetSystemAccessor->mfSystemTime))   // System +0x08
            {
                lpReq->mdStartTime = lpCmd->mdStartTime;
            }
            break;   // the console leaves the loop on the first accepted match
        }
    }
    return static_cast<int>(sizeof(SndPlayer1ModifyStartTimeCommand));  // console li r3, 0x18
}
```

### `rw::audio::core::SndPlayer1::ReleaseEvent  (host: ~SndPlayer1, vt[0])` @ `0x82BA4178`  [DECODED]

**Signature**

```cpp
virtual ~SndPlayer1();   // console: int __fastcall ReleaseEvent(SndPlayer1 *r3)
// vt[0] of off_8217F344. House precedent: Dac.h/Dac.cpp map ReleaseEvent @0x82B9DAE0 onto ~Dac().
```

**Behaviour**

r31 = this.
1. StreamLostCallback(this) @0x82BA4100 — called with r3 = this and no other argument, unconditionally and FIRST, before any teardown. (Contextually it is the same routine the StreamPool hands back on stream loss; it walks the requests and RemoveRequest's them.)
2. `lbz r11, 0x1D0(r31)`; `cmplwi cr6, r11, 1`; `bne` -> skip. So the timer is removed ONLY when mbTimerAdded is EXACTLY 1 (not merely non-zero — this is the byte CreateInstance sets to 1 only after TimerManager::AddTimer returned zero). Then System::RemoveTimer(this->mpSystemUseGetSystemAccessor, this + 0x40) @0x82B6EB80 — the +0x40 operand is the embedded TimerHandle member (TimerHandle.h layout confirms: node/callback/context/name/ticks/stage/visibility).
3. `lwz r4, 0x1B0(r31)`; if non-null, System::Free(this->mpSystemUseGetSystemAccessor, mpRequestHandleCounter, 0) @0x82B6BE48. That single allocation is the console `0x50*n + 4` block: the f32 handle counter followed at byte +4 by the n RequestExternal records. The pointer is NOT nulled afterwards.
Return: r3 is whatever the last call left — StreamLostCallback's, RemoveTimer's, or System::Free's result. A dead passthrough.
NOT done here: the RequestInternal array and the declick array are inside the GetSize allocation the Voice owns, so they are not freed; mbTimerAdded is not cleared.

**Constants**

No rodata constants and no float literals. The only immediates are 0x1D0 (the mbTimerAdded byte), the comparand 1, 0x40 (the embedded TimerHandle offset), 0x1B0 (mpRequestHandleCounter) and the System::Free allocator-override argument 0.

**Host hazards**

1. `this + 0x40` is the embedded TimerHandle member and MUST be `&mTimerHandle` on the host — the console offset is meaningless once PlugIn's four pointer members widen.
2. mpRequestHandleCounter points at the console `0x50*n + 4` block: an f32 followed at byte +4 by n RequestExternal records. RequestExternal contains five 32-bit pointers and leads with an f64, so the +4 packing does NOT survive pointer widening; the free path must simply mirror whatever the host CreateInstance allocated.
3. The timer test is `== 1`, not truthiness. A `if (mbTimerAdded)` transliteration would call RemoveTimer on a handle that was never registered.
4. The return is a dead passthrough of three different callees' results; do not invent a status code for it.
5. Slot ordering caveat for the parent: the raw table is {ReleaseEvent, EventEvent, GetPpuTicksEvent, deleting-dtor}, i.e. the destructor sits in slot 3, whereas the committed PlugIn.h declares `virtual ~PlugIn()` FIRST (slot 0). The host compiler builds its own table and nothing reads the console layout, so this is a documentation discrepancy rather than a defect — but the ~SndPlayer1/Event/VFunc2 declaration order must match PlugIn.h's, not the console table's.

**Implementation sketch**

```cpp
// vt[0] == ReleaseEvent @0x82BA4178 -- plug-in teardown (the console's r3 is a dead
// passthrough of whichever call ran last; modelled void, per the ~Dac() precedent).
SndPlayer1::~SndPlayer1()
{
    StreamLostCallback(this);            // unconditional, and FIRST

    // EXACTLY == 1, not merely non-zero: CreateInstance @0x82BA6E0C..0x82BA6E24 sets this
    // byte to 1 only after TimerManager::AddTimer returned zero.
    if (mbTimerAdded == 1)
        System::RemoveTimer(mpSystemUseGetSystemAccessor, &mTimerHandle);   // console this+0x40

    // The ONE private allocation: the f32 handle counter with the RequestExternal array
    // behind it. The console packed it as `0x50*n + 4`; that literal must NOT survive to
    // x64 -- RequestExternal holds five pointers AND leads with an f64, so `base + 4`
    // would place it at 4-byte alignment. Whatever CreateInstance allocates on the host
    // (a typed/aligned storage header, or two allocations), this frees the SAME base.
    if (mpRequestHandleCounter)
        System::Free(mpSystemUseGetSystemAccessor, mpRequestHandleCounter, 0);
    // (the console does not null the pointer afterwards)
}
```

### `rw::audio::core::SndPlayer1::GetPpuTicksEvent  (vt[2])` @ `0x82BDD2D0`  [DECODED]

**Signature**

```cpp
virtual int VFunc2();   // PlugIn.h's vt[2] slot; console: int __fastcall GetPpuTicksEvent(SndPlayer1 *r3)
// Suggested host spelling: `virtual int GetPpuTicks();` overriding PlugIn's vt[2].
```

**Behaviour**

Two instructions: `lwz r3, 0x50(r3)` / `blr`.
The object's TimerHandle is embedded at +0x40 and TimerHandle::mCpuTicks sits at +0x10 within it (committed TimerHandle.h, PDB-reconciled). 0x40 + 0x10 = 0x50, so this returns mTimerHandle.mCpuTicks — the CPU ticks TimerManager accumulates for this plug-in's registered timer — NOT PlugIn::mCpuTicks at +0x1C.
No side effects, no null check, no scaling.

**Constants**

None. The single immediate is the displacement 0x50.

**Host hazards**

1. 0x50 is a CONSOLE composite offset (PlugIn header + attribute slots + TimerHandle base, all of which shift once PlugIn's four pointer members widen). It must be written as `mTimerHandle.mCpuTicks`; a literal `*(u32*)((char*)this + 0x50)` lands in the middle of the widened TimerHandle on x64.
2. Do not confuse this with PlugIn::mCpuTicks (+0x1C, the generic per-stage cost) — they are different counters written by different code (TimerManager vs. the stage pipeline).
3. The console returns a raw u32 in a signed r3; keep the u32 field type and cast at the boundary.

**Implementation sketch**

```cpp
// vt[2] == GetPpuTicksEvent @0x82BDD2D0 -- `lwz r3, 0x50(r3); blr`.
// +0x50 == the embedded TimerHandle (+0x40) + TimerHandle::mCpuTicks (+0x10):
// the TIMER's accumulated ticks, NOT PlugIn::mCpuTicks (+0x1C).
int SndPlayer1::VFunc2()   // house spelling: GetPpuTicks()
{
    return static_cast<int>(mTimerHandle.mCpuTicks);
}
```

### `rw::audio::core::SndPlayer1::`vector deleting destructor'  (vt[3])` @ `0x82B9EAF8`  [DECODED]

**Signature**

```cpp
// MSVC-synthesised: void *__fastcall `vector deleting destructor'(SndPlayer1 *r3, unsigned int flags, const char *r5)
// NOT hand-written on the host: the compiler emits this from `virtual ~SndPlayer1()`.
```

**Behaviour**

r31 = this; r30 = flags (r4).
1. `addi r3, r31, 0x40` then `bl STUB` @0x82AD5078 — the TimerHandle sub-object destructor, COMDAT-folded to an empty stub in this build. r4/r5 ride through untouched.
2. `stw` off_820AA810 into *(u32*)this — the shared base-PlugIn-vtable sentinel (the project already exports it as `gpBasePlugInVTableSentinel`, defined in PlugIn.cpp:145). Note this installs the BASE sentinel, not a SndPlayer1 table: after this store the object is no longer a SndPlayer1.
3. `clrlwi. r10, r30, 31` / `beq`: if (flags & 1) `operator delete(this)` @0x82C08FB0.
4. `mr r3, r31` — returns `this` unconditionally, even after the delete.
CRITICALLY: this thunk does NOT call SndPlayer1::ReleaseEvent @0x82BA4178. The real teardown (StreamLostCallback, RemoveTimer, System::Free) lives entirely in the vt[0] entry and is invoked separately by the engine. On the host, where ReleaseEvent IS ~SndPlayer1(), the compiler-generated deleting destructor necessarily folds both — that is a structural divergence to record, not to code around.

**Constants**

off_820AA810 -- the shared base-PlugIn-vtable sentinel; already committed as `extern void* const gpBasePlugInVTableSentinel` (PlugIn.h) / `= &sBasePlugInVTableSlot` (PlugIn.cpp:145). No numeric literals beyond the +0x40 TimerHandle displacement and the `& 1` delete flag.

**Host hazards**

1. DO NOT AUTHOR THIS FUNCTION. It is compiler-synthesised; hand-writing it produces a second, conflicting deleting-destructor symbol.
2. `this + 0x40` is the embedded TimerHandle member — a console composite offset over the un-widened PlugIn header.
3. The `flags & 1` bit is the MSVC deleting-destructor convention; the third argument r5 is only forwarded to the sub-object destructor and is otherwise unused.
4. It returns `this` even on the delete path — a dangling pointer by construction. Every caller discards it.
5. TEARDOWN-DOUBLING RISK: the console splits `release` (vt[0]) from `destroy` (vt[3]); the host, following the Dac precedent, fuses them into ~SndPlayer1(). A stray `delete pPlugIn` on the host therefore does what the console's vt[3] never did.
6. The STUB at 0x82AD5078 being empty is an ICF artifact of THIS build; do not conclude TimerHandle has no destructor semantics in general.

**Implementation sketch**

```cpp
// vt[3] @0x82B9EAF8 -- the MSVC `vector deleting destructor' thunk. DO NOT HAND-WRITE IT:
// declaring `virtual ~SndPlayer1();` (the vt[0] ReleaseEvent body) makes the host compiler
// emit the equivalent. For the record, the console body is:
//
//     TimerHandle::~TimerHandle(&this->mTimerHandle);   // COMDAT-folded to STUB @0x82AD5078
//     *(void **)this = gpBasePlugInVTableSentinel;      // off_820AA810 (PlugIn.cpp:145)
//     if (flags & 1)
//         operator delete(this);
//     return this;                                      // returned even after the delete
//
// Two things the host CANNOT reproduce literally and must not try to:
//  * `this + 0x40` is the embedded TimerHandle -- by name, &mTimerHandle.
//  * the vptr overwrite is the compiler's own base-class-vptr reinstall during
//    destruction; the explicit `stw` has no host equivalent (PlugIn.h already retired
//    the explicit mpVTable member -- the hidden vptr IS the +0x00 word).
//
// The one BEHAVIOURAL note for the parent: on the console this thunk performs NO plug-in
// teardown at all -- StreamLostCallback / System::RemoveTimer / System::Free live only in
// vt[0] (ReleaseEvent). On the host, mapping ReleaseEvent onto ~SndPlayer1() means a
// `delete` DOES run that teardown. Only ever destroy a SndPlayer1 through the engine's
// vt[0] release path, never with a bare `delete`, or the teardown runs twice.
```

### Cluster notes

TWO CORRECTIONS SETTLED FROM THE BYTES, AS ASKED:

(1) THE HANDLE-COUNTER WRAP IS 1.0f, NOT 0.0f. The adversarial review is right and progress/scratch_dossiers/sndplayer1_decode_codex.md section 5 is wrong. Proof chain, all in the shared PLAY tail:
  0x82BA5F30  lis   r7, 0x8200
  0x82BA5F38  lfs   f0, 0x1C98(r7)     <- f0 = 1.0f  (flt_82001C98, file 0x4C98 = 3F 80 00 00)
  0x82BA5F3C  fadds f13, f13, f0       <- the increment
  0x82BA5F50  lfs   f13, 0x56EC(r11)   <- 4194304.0f (flt_820B56EC, file 0xB86EC = 4A 80 00 00)
  0x82BA5F54  fcmpu cr6, f12, f13
  0x82BA5F58  ble   cr6, 0x82BA5F64    <- skip
  0x82BA5F60  stfs  f0, 0(r11)         <- f0 STILL HOLDS 1.0f; never reloaded
Nothing between 0x82BA5F38 and 0x82BA5F60 writes f0. A 0.0f wrap would also be semantically wrong: CreateInstance seeds every RequestInternal handle and both watermark floats to 0.0f, so the first post-wrap handle would collide.

(2) The prior report's ISREQUESTDONE and GETREQUESTBUFFERED summaries needed repair beyond the three errors I was warned about:
  * "No-match output remains 0/false" is wrong twice. When mu8MaxRequests == 0 the parameter block is left COMPLETELY UNWRITTEN (guard at 0x82BA5D14..0x82BA5D20 returns before any store). And a non-matching lap actively stores 0.0f to param+0x04 and param+0x08, once per lap.
  * The legacy PLAY block is 0x24 (36) bytes, not 40. Reads stop at +0x20, which is its OUT handle slot.
  * Feed record +0x0C is a BYTE (`stb r3, 0x0C(r30)` in SubmitChunk @0x82BA465C), not the 32-bit word section 2 implies; it sits immediately before state (+0x0D) and owning-request-index (+0x0E).

ONE SHIPPED CONSOLE BUG, PRESERVED VERBATIM. In EventEvent event 3, the streamed branch compares the LOOP INDEX, converted to float, against attribute 0 — which RwacTimerClient @0x82BA69EC/0x82BA69F4 fills from mfCurrentRequestHandle (+0x1A0), a monotonically increasing handle. Raw bytes re-read to rule out a capstone artifact: 0x82BA5E04 = 78 CB 00 20 (clrldi r11,r6,32; r6 is the index, initialised at 0x82BA5D18 and bumped only in the zeroing tail), 0x82BA5E08 = C0 09 00 28 (lfs f0,0x28(r9)). It looks like a source slip for mu8CurrentRequestIndex (+0x1C9); the practical effect is that the whole-stream byte accessor 0x82BBD940 is essentially never selected and the per-request accessor 0x82BBD948 always is. Reproduce it; do not silently repair it.

CALLEES IDENTIFIED THIS PASS (two had no dossier):
  0x82BBD940  Stream::GetBytesBuffered        -- `lwz r3, 0x0C(r3); blr`
  0x82BBD948  Stream::GetRequestBytesBuffered -- hand-decoded: impl = stream->+0x04; idx = requestId & 0xFF; if (idx >= impl->+0x3C) return 0; rec = impl->+0x38 + idx*0x140; if (rec->+0x00 != requestId || rec->+0x04 == 0) return 0; return rec->+0x138.
  0x82BBD990  Stream::GetState                -- `return *(u32*)(*(u32*)(stream+4) + 0x70)`
  0x82BC09B0  a five-argument SHUFFLE THUNK, not a function: `mr r8,r7; mr r7,r6; mr r6,r5; li r5,0; b rw::core::filesys::Stream::QueueFile` — it injects a zero flags word into the third slot. Calling QueueFile with the caller's arguments unshifted is wrong.
  0x82BA3FF8  SndPlayer1::ChunkParsed (the QueueFile chunk callback; address recomputed from BOTH lis/addi pairs in PlayHandler and verified to be a real prologue)
  0x821745D8  "SndPlayer1 StreamLoopFileName"

RING-CONTRACT SUMMARY (every return flagged as the cursor advance):
  StopHandler              -> console 8       -> host sizeof(SndPlayer1StopCommand)
  ModifyStartTimeHandler   -> console 0x18    -> host sizeof(SndPlayer1ModifyStartTimeCommand)
  PlayHandler              -> `lhz cmd+0x2C`  -> DATA-DRIVEN: the u16 the producer stamped. This is the only one that is not an immediate, because the record is variable-length. Its host size must be align_up(offsetof(SndPlayer1PlayCommand, macPath) + nameBytes, alignof(SndPlayer1PlayCommand)); the console's `(nameBytes + 0x3B) & ~3` counts four 32-bit pointers and rounds to 4, which would misalign the next record's three leading f64s on x64. Assert the result fits the u16 wire field.
  ReleaseEvent / GetPpuTicksEvent / the deleting destructor are not ring handlers; ReleaseEvent's return is a dead three-way passthrough.

NOTHING WAS BLOCKED. All seven functions decoded. Two provisional namings I inherited rather than proved: RequestExternal +0x18 as "bytes fed" (section 2 of the prior report; consistent with its use here as the streamed buffered-byte base and with RemoveRequest subtracting a chunk length from it) and RequestExternal +0x40 as the seek byte offset (attested here only by PlayHandler's use of it as an addend to the f64 file offset, immediately after SetSeekData ran). Neither affects any control flow above.

METHOD NOTE: EventEvent has no dossier. I disassembled 0x82BA5C48..0x82BA607C with capstone (CS_ARCH_PPC, MODE_32|BIG_ENDIAN) over the decrypted XEX at file 0x00BA8C48, then hand-verified the load-bearing words against raw big-endian bytes: the clrldi/lfs pair behind the index-vs-handle quirk, both `bl` displacements into 0x82BBD940/0x82BBD948, the four rodata float/double literals, and the vtable at file 0x00182344. Every lis/addi pair was resolved arithmetically rather than trusted from a symbol name.

## Cluster: rw::audio::core::SndPlayer1 -- the streaming + decoder chain (12 functions)

### `rw::audio::core::SndPlayer1::StartRequest` @ `0x82BA6438`  [DECODED]

**Signature**

```cpp
static u8 StartRequest(SndPlayer1 *apSelf, u32 auRequestIndex);  // r3=self, r4=index (callers pass a zero-extended byte); r3 out is tested with clrlwi. r3,24 -> u8 0/1
```

**Behaviour**

Entry (0x82BA6438..0x82BA646C): r31=self, r27=index. Computes req = self + self->mRequestArrayOffset(lhz +0x1C4) + 0x30*index (r28) and ext = self->mpRequestExternal(lwz +0x58) + 0x50*index (r30). Latches r26 = self->mpSystem (lwz +0x04).

1. System::Lock(self->mpSystem) @0x82BA6470.
2. reg = System::GetDecoderRegistry(self->mpSystem) @0x82BA6478 -- note the System pointer is RELOADED from +0x04, not reused from r26.
3. Codec map, 0x82BA647C..0x82BA6494: r11 = lbz ext+0x48 (codec index); rotlwi r11,r11,2 (== *4, the byte can never reach the rotate-wrap range); r10 = &dword_82174578; r4 = lwzx r11,r10 -- i.e. kDecoderGuids[codec]. THERE IS NO BOUNDS CHECK. handle = DecoderRegistry::GetDecoderHandle(reg, guid) (returns null on no-match, @0x82B67C80).
4. DecoderFactory argument derivation, 0x82BA6498..0x82BA64AC, in register order:
     r3 = reg (the registry, `this`)
     r4 = handle (GetDecoderHandle's DecoderDesc*)
     r5 = lbz req+0x2B  == RequestInternal::mucChannels (UnpackHeader's 6-bit field + 1)
     r6 = li 0x14 == 20, an immediate. It is the SAME modulus as the SndPlayer1 feed ring (GetFeedSlot / Process / FeedCleanup all wrap at 0x14) and it becomes the decoder's request-ring size (Decoder::mucRequestCount), which is what makes SubmitChunk's returned Feed slot index a valid handle for FeedCleanup's GetSamplesRemaining probe.
     r7 = lwz self+0x04 == self->mpSystem, RELOADED again.
   decoder = DecoderRegistry::DecoderFactory(reg, handle, channels, 20, system) @0x82B6C778.
5. req->mpDecoder = decoder (stw 8(r28)) is stored BEFORE the null test. If decoder == 0 -> loc_82BA653C: System::Unlock, return 0.
6. 0x82BA64BC..0x82BA64C8: req->muDecoderScratchSize = (u16)decoder->[+0x20] -- a `lwz r11,0x20(r3)` followed by `sth r11,0x28(r28)`, i.e. the low halfword of the decoder's scratch/instance size word is kept. (Decoder +0x20 is inside Decoder.h's `mPad20[4]` opaque gap; Process later carves align_up(that,128) off the System stack allocator.)
7. Seek-active flag, 0x82BA64CC..0x82BA64F4:
     flag = (req->miStreamSkip (+0x24) != 0) || (req->miDecoderSkip (+0x20) != 0) || (ext->miPlayerSkip (+0x3C) != 0)
   evaluated as a short-circuit chain of `cmpwi/bne` into `li r10,1` / `li r10,0`; r7 = clrlwi(r10,24).
8. Play-type dispatch on lbz ext+0x49 (0x82BA64F0..0x82BA6508):
     playType == 0 (RAM) or == 2 (gigastream) -> the RESIDENT path (loc_82BA654C).
     otherwise (1 == stream, 3) -> the STREAMED path.
9. STREAMED path 0x82BA6508..0x82BA653C: ok = StreamNextChunk(self, index, ext->mucIsNewFeedChunk (lbz +0x4C), flag). If (u8)ok != 0 -> loc_82BA6580: System::Unlock; return 1. If it failed: reload decoder = req->mpDecoder; if non-null call Decoder::Release(decoder) @0x82691528 and store req->mpDecoder = 0; then Unlock; return 0.
10. RESIDENT path loc_82BA654C..0x82BA657C: GetFeedSlot(self, &slot) is called and ITS RETURN IS IGNORED (r3 is dropped); slot is read back with `lwz` from the 4-byte stack out-slot. Then
      ext->mucLatestFeedSlot = (u8)slot                      (stb 0x4A(r30))
      chunk = ext->mpSampleData (lwz 8(r30)) + ext->miChunkOffset (lwz 0x40(r30))
      ext->mpNextChunk = SubmitChunk(self, chunk, index, ext->mucIsNewFeedChunk, flag)   (stw 0x30(r30))
    Note r7 still carries `flag` across the GetFeedSlot call (GetFeedSlot clobbers only r3/r4/r9/r10/r11), so SubmitChunk's 5th argument on this path is the seek flag.
11. loc_82BA6580: System::Unlock(system); return 1.

RETURN CONTRACT: 1 = the request is now feeding (the caller, RwacTimerClient, then promotes state QUEUED->FEEDING); 0 = give up this tick, the request stays QUEUED and the timer retries next tick.

**Constants**

dword_82174578 -- the 8-entry decoder-GUID table. vaddr 0x82174578 -> file_off = 0x3000 + 0x82174578 - 0x82000000 = 0x00177578. Raw big-endian bytes read from IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex:
  [0] 58 61 73 30 = 0x58617330 'Xas0'
  [1] 45 4C 33 30 = 0x454C3330 'EL30'
  [2] 50 36 42 30 = 0x50364230 'P6B0'
  [3] 45 58 6D 30 = 0x45586D30 'EXm0'
  [4] 58 61 73 31 = 0x58617331 'Xas1'
  [5] 45 4C 33 31 = 0x454C3331 'EL31'
  [6] 4C 33 32 50 = 0x4C333250 'L32P'
  [7] 4C 33 32 53 = 0x4C333253 'L32S'
The table is EXACTLY 8 words: the very next words at 0x82174598 are 53 6E 64 50 / 6C 61 79 65 ('SndP','laye'), the head of the C string "SndPlayer1 RequestHandle and RequestExternal array\0" (file 0x00177598). This CONFIRMS the prior report's table and its "index 8 is already string data" claim.
Immediate: r6 = 0x14 = 20 (DecoderFactory arg4).

**Host hazards**

* NO BOUNDS CHECK on the codec index (0x82BA647C..0x82BA6494 is lbz / rotlwi / lwzx with no compare). UnpackHeader reads the codec as a FOUR-BIT field, so 0..15 are reachable from a malformed asset while the table holds only 8 entries; indices 8..15 read the adjacent "SndPlayer1 RequestHandle and RequestExternal array" literal as GUIDs. GetDecoderHandle then walks its list, matches nothing and returns null; what DecoderFactory does with a null handle is UNVERIFIED (0x82B6C778 is an exporter gap with no dossier), so the only guaranteed guard is StartRequest's own null test on the RESULT. Reproduce the missing check faithfully; do not add one silently.
* CONSOLE RECORD STRIDES: `mulli r10,r27,0x30` (RequestInternal) and `mulli r11,r27,0x50` (RequestExternal) both index records that contain 32-bit pointers -- RequestInternal::mpDecoder, and RequestExternal's mpSampleData / mpLoopFileName / mpStreamPool / mpStreamPoolEntry / mpStream / mpNextChunk / mpLoopChunk / mpSeekData. Neither literal is a valid x64 stride; the host must index typed arrays (`sizeof(SndPlayer1RequestInternal)` / `sizeof(SndPlayer1RequestExternal)`). Likewise `lhz +0x1C4` is a 16-bit RELATIVE offset the host must recompute from its own layout.
* `rotlwi r11,r11,2` is a multiply-by-4 only because the codec byte is < 2^30; do not port it as a rotate.
* The System pointer is loaded THREE times (r26 at entry for Lock/Unlock, then fresh `lwz 4(r31)` for GetDecoderRegistry and again for DecoderFactory's r7). Harmless, but reproduce the accessor rather than caching -- PlugIn.h routes it through GetSystem().
* GetFeedSlot's return is ignored on the resident path. That is safe only because the sole caller, RwacTimerClient, checks `feed[mucNextFeedSlotToFill].mucState == 0` immediately before (0x82BA6AF4). If any new caller is added the stack out-slot is read uninitialised. Faithful port keeps the ignore.
* `req->mpDecoder` is stored before the null check, so a failed create leaves 0 in the field -- relied on by the caller's retry.
* All compares here are integer (`cmpwi`/`cmplwi`) -- no fcmpu, so no NaN-polarity inversion applies to this function.
* DecoderRegistry::DecoderFactory is NOT declared in the committed DecoderRegistry.h. The host needs it added with the call-site-derived signature `static Decoder *DecoderFactory(DecoderRegistry *apSelf, DecoderDesc *apHandle, u8 aucChannels, u32 auNumRequests, System *apSystem);` -- flagged as call-site-derived, since 0x82B6C778 has no dossier.

**Implementation sketch**

```cpp
// ---- file-scope, from rodata dword_82174578 (see `constants`) ----
// The registered decoder GUIDs, indexed by the asset header's 4-bit codec field.
static const u32 kDecoderGuids[8] = {
    0x58617330u, // 0 'Xas0'
    0x454C3330u, // 1 'EL30'
    0x50364230u, // 2 'P6B0'
    0x45586D30u, // 3 'EXm0'   <- the one RwacTimerClient special-cases
    0x58617331u, // 4 'Xas1'
    0x454C3331u, // 5 'EL31'
    0x4C333250u, // 6 'L32P'
    0x4C333253u, // 7 'L32S'
};
// The decoder's request-ring size handed to DecoderFactory. Same value as kMaxFeeds.
static const u32 kDecoderNumRequests = 20;

u8 SndPlayer1::StartRequest(SndPlayer1 *apSelf, u32 auRequestIndex)
{
    // HOST STRIDE RULE: the console's 0x30 / 0x50 multiplies embed 32-bit pointers
    // (RequestInternal::mpDecoder; RequestExternal's seven pointers), so index the
    // host arrays -- never reproduce the immediates.
    SndPlayer1RequestInternal &lReq = apSelf->Req(auRequestIndex);
    SndPlayer1RequestExternal &lExt = apSelf->Ext(auRequestIndex);
    System *lpSystem = apSelf->GetSystem();

    System::Lock(lpSystem);

    DecoderRegistry *lpReg = System::GetDecoderRegistry(apSelf->GetSystem());

    // NO BOUNDS CHECK on the codec index -- faithful (see `hazards`).
    DecoderDesc *lpHandle =
        DecoderRegistry::GetDecoderHandle(lpReg, (int)kDecoderGuids[lExt.mucCodec]);

    // (handle, numChannels, 20, System) exactly as the call site derives them.
    lReq.mpDecoder = DecoderRegistry::DecoderFactory(
        lpReg, lpHandle, lReq.mucChannels, kDecoderNumRequests, apSelf->GetSystem());

    if (lReq.mpDecoder == 0)
    {
        System::Unlock(lpSystem);
        return 0;
    }

    // Low halfword of the decoder's scratch-instance size word (X360 Decoder +0x20).
    lReq.muDecoderScratchSize = (u16)lReq.mpDecoder->GetScratchInstanceSize();

    const u8 lucSeekActive =
        (lReq.miStreamSkip != 0 || lReq.miDecoderSkip != 0 || lExt.miPlayerSkip != 0) ? 1u : 0u;

    if (lExt.mucPlayType != 0 && lExt.mucPlayType != 2)
    {
        // stream / gigastream-tail: pull the next chunk out of the filesys Stream.
        if (StreamNextChunk(apSelf, auRequestIndex, lExt.mucIsNewFeedChunk, lucSeekActive) == 0)
        {
            if (lReq.mpDecoder != 0)
            {
                Decoder::Release(lReq.mpDecoder);
                lReq.mpDecoder = 0;
            }
            System::Unlock(lpSystem);
            return 0;
        }
    }
    else
    {
        // RAM / gigastream head: the whole block is already resident.
        u32 luSlot = 0;
        GetFeedSlot(apSelf, &luSlot);       // return DELIBERATELY ignored -- faithful
        lExt.mucLatestFeedSlot = (u8)luSlot;
        // Asset-byte arithmetic (NOT a host struct offset): payload base + seek chunk offset.
        lExt.mpNextChunk = SubmitChunk(apSelf,
                                       lExt.mpSampleData + lExt.miChunkOffset,
                                       auRequestIndex,
                                       lExt.mucIsNewFeedChunk,
                                       lucSeekActive);
    }

    System::Unlock(lpSystem);
    return 1;
}
```

### `rw::audio::core::SndPlayer1::SubmitChunk` @ `0x82BA4570`  [DECODED]

**Signature**

```cpp
static const u8 *SubmitChunk(SndPlayer1 *apSelf, const u8 *apBlock, u32 auRequestIndex, u8 aucIsNewFeedChunk, u8 aucSeekActive);  // r3,r4,r5,r6,r7; returns apBlock + blockBytes (r3 = r10 + r31)
```

**Behaviour**

r31 = apBlock (r4), r29 = ext = self->mpRequestExternal + 0x50*index.

A. ASSET BLOCK HEADER (0x82BA458C..0x82BA4610). The compiler emits an unaligned 32-bit load as four lbz/stb pairs into two 4-byte stack slots:
     var_38 = apBlock[0..3]  -> blockBytes  (read back with `lwz` at 0x82BA4664)
     var_40 = apBlock[4..7]  -> numSamples  (read back with `lwz` at 0x82BA4614 into r28)
   and the payload handed to the decoder is `apBlock + 8` (`addi r4, r31, 8` at 0x82BA459C, held in r4 all the way to the Feed call). So the on-disk block is { u32 blockBytes; u32 numSamples; payload[] }.

B. FEED-SLOT FILL (0x82BA45D0..0x82BA460C). slot = lbz ext+0x4A (the slot StartRequest / StreamNextChunk / HandleLoopStart / HandleSampleEnd just published); r30 = self + 0x5C + 16*slot (rotlwi r10,r10,4 then `addi r30, r10, 0x5C`). Stores, in emitted order:
     feed->mucRequestIndex (+0x0E) = (u8)auRequestIndex        (stb r5)
     feed->mucState        (+0x0D) = 1  == SUBMITTED           (stb r9, r9=1)
     feed->miDecoderSkip   (+0x08) = 0                          (stw r8, r8=0)
     feed->mpStream        (+0x04) = ext->mpStream (lwz 0x28(r29))
   feed->mpChunkInfo (+0x00) is NOT touched here -- StreamNextChunk writes it before calling; the resident paths leave whatever was there (see hazards).

C. FEED-CALL SPLIT on aucSeekActive. CR0 is set at 0x82BA45C8 by `clrlwi. r10, r7, 24` and consumed at 0x82BA461C.
   r6 (Decoder::Feed's ucContinue) is computed identically on both arms as
       cntlzw(t) then extrwi 1 bit at position 26   ==  (aucIsNewFeedChunk == 0) ? 1 : 0
   i.e. ucContinue = !aucIsNewFeedChunk -- "this is NOT a fresh feed chunk, keep decoding the current stream".

   aucSeekActive == 0 (0x82BA4620..0x82BA4634):
       Feed(req->mpDecoder, apBlock+8, numSamples, ucContinue, iStartSample=0, uArg4=0, ucFlag11=0)
   aucSeekActive != 0 (0x82BA4638..0x82BA4654):
       feed->miDecoderSkip (+0x08) = req->miDecoderSkip (lwz 0x20(r11))   -- overwrites the 0 above
       Feed(req->mpDecoder, apBlock+8, numSamples,
            ucContinue,
            iStartSample = req->miDecoderSkip   (lwz 0x20(r11) -> r7),
            uArg4        = ext->mpSeekData      (lwz 0x38(r29) -> r8),   <-- A POINTER
            ucFlag11     = ext->miSeekDataVersion (lwz 0x44(r29) -> r9))

D. TAIL (0x82BA465C..0x82BA4670):
     feed->mucDecoderRequestHandle (+0x0C) = (u8)Feed's return  (stb r3)
     ext->miSamplesFed (+0x14) += numSamples
     return apBlock + blockBytes                                (add r3, r10, r31)

The return is the pointer to the NEXT block, which every caller stores into ext->mpNextChunk (+0x30).

**Constants**

None of its own. The two immediates are `li r9,1` (the SUBMITTED feed state) and `li r8,0`. The `extrwi r6, cntlzw(x), 1, 26` idiom is a compiled `(x == 0)`, not a table.

**Host hazards**

* ⚠️ DECODER.H CORRECTION -- POINTER IN A u32 SLOT. Decoder.h currently declares `u32 uReserved04` / `DecoderRequest::muReserved04` and states "every committed call site passes 0" and "every field is a 32-bit word (no pointers) so the 20-byte stride survives the x64 widening". SubmitChunk's seek arm FALSIFIES both: it passes ext->mpSeekData (0x82BA464C `lwz r9,0x44` / 0x82BA464C..0x82BA4650; the r8 source is `lwz r8, 0x38(r29)`), and SetSeekData proves +0x38 is SeekTableParser::mpSeekData, a real `u8*`. Decoder::Feed stores r8 to DecoderRequest+0x04 (raw-verified at 0x82B67964 `stw r8,4(r30)`). So DecoderRequest carries a POINTER, its 20-byte console stride does NOT survive x64, and every ring index (Decoder::Feed, GetSamplesRemaining, GetCurrentRequestDesc, EaXmaDec::DecodeEvent) must use sizeof(DecoderRequest). Likewise `mucFlag11` is not always 0 -- it is (u8)ext->miSeekDataVersion here.
* CONSOLE FEED STRIDE: `rotlwi r10, r10, 4` + `addi r30, r10, 0x5C` is feed[slot] at a hard 16-byte stride from self+0x5C. The record holds TWO pointers (mpChunkInfo, mpStream), so 16 is not the host size and 0x5C is not the host base -- index a typed array.
* The block header is read as ASSET bytes (four lbz reassembled into one native lwz). On the big-endian console that is a big-endian u32; on x64 the same asset bytes are still big-endian unless the pipeline byte-swaps SNR/SNS payloads. This cluster cannot settle which -- the host `ReadAssetU32` helper must match whatever the sample-asset pipeline produces. Flagged, not assumed.
* feed->mpChunkInfo (+0x00) is NOT written here. Only StreamNextChunk sets it (before calling); the three RESIDENT submit sites (StartRequest, HandleLoopStart, HandleSampleEnd) leave the previous occupant's value in place. FeedCleanup then releases whatever pointer is there when the slot reaches state 2 -- correct only because CreateInstance nulls every mpChunkInfo and FeedCleanup nulls it again after release. Do not "tidy" this by clearing it in SubmitChunk; the null-after-release invariant is what makes it safe.
* r7 (aucSeekActive) is tested at 0x82BA45C8 but CR0 is consumed 84 bytes later at 0x82BA461C -- do not reorder the header reads past the branch when hand-porting; the C++ above preserves the observable order.
* No floating-point compares -- no NaN polarity concerns.

**Implementation sketch**

```cpp
// The on-disk sample-block header. ASSET LAYOUT, not a host ABI struct -- the +8
// payload offset and the blockBytes advance stay literal.
struct SndPlayer1BlockHeader
{
    u32 muBlockBytes;  // apBlock[0..3]
    u32 muNumSamples;  // apBlock[4..7]
    // payload follows at apBlock + 8
};

const u8 *SndPlayer1::SubmitChunk(SndPlayer1 *apSelf, const u8 *apBlock,
                                  u32 auRequestIndex, u8 aucIsNewFeedChunk,
                                  u8 aucSeekActive)
{
    SndPlayer1RequestInternal &lReq = apSelf->Req(auRequestIndex);
    SndPlayer1RequestExternal &lExt = apSelf->Ext(auRequestIndex);

    // The console reassembles both words byte-by-byte (unaligned load), then reads them
    // back with a single native lwz -- i.e. plain ASSET byte order, not a swap.
    const u32 luBlockBytes = ReadAssetU32(apBlock + 0);
    const u32 luNumSamples = ReadAssetU32(apBlock + 4);
    const void *lpPayload  = apBlock + 8;

    SndPlayer1FeedDesc &lFeed = apSelf->Feed(lExt.mucLatestFeedSlot);
    lFeed.mucRequestIndex = (u8)auRequestIndex;
    lFeed.mucState        = 1;                 // SUBMITTED
    lFeed.miDecoderSkip   = 0;
    lFeed.mpStream        = lExt.mpStream;

    // ucContinue == !isNewFeedChunk (the cntlzw/extrwi pair is exactly this predicate).
    const u8 lucContinue = (aucIsNewFeedChunk == 0) ? 1u : 0u;

    u8 lucHandle;
    if (aucSeekActive == 0)
    {
        lucHandle = Decoder::Feed(lReq.mpDecoder, lpPayload, (s32)luNumSamples,
                                  lucContinue, /*iStartSample*/ 0,
                                  /*apSeekData*/ 0, /*ucSeekVersion*/ 0);
    }
    else
    {
        lFeed.miDecoderSkip = lReq.miDecoderSkip;
        lucHandle = Decoder::Feed(lReq.mpDecoder, lpPayload, (s32)luNumSamples,
                                  lucContinue, lReq.miDecoderSkip,
                                  lExt.mpSeekData,               // POINTER -- must widen
                                  (u8)lExt.miSeekDataVersion);
    }

    lFeed.mucDecoderRequestHandle = lucHandle;
    lExt.miSamplesFed += (s32)luNumSamples;

    return apBlock + luBlockBytes;   // the next block
}
```

### `rw::audio::core::SndPlayer1::StreamNextChunk` @ `0x82BA6080`  [DECODED]

**Signature**

```cpp
static u8 StreamNextChunk(SndPlayer1 *apSelf, u32 auRequestIndex, u8 aucIsNewFeedChunk, u8 aucSeekActive);  // r3,r4,r5,r6; result tested with clrlwi. r3,24
```

**Behaviour**

r31=self, r29=index, r27=aucIsNewFeedChunk, r26=aucSeekActive; r28 = req, r30 = ext (same 0x30 / 0x50 derivations as StartRequest).

A. STREAM-REQUEST LIVENESS GATE (0x82BA60B8..0x82BA60EC). Only when req->mucState == 1 (QUEUED):
     if (ext->muStreamRequestId (lwz +0x2C) != 0)
         if (Stream::GetRequestState(ext->mpStream (lwz +0x28), requestId) == 0)   // the request record is gone
             req->miNumSamples (stw 0x14(r28)) = 0;                                 // raw-verified: 917C0014
             return 0;
   Stream::GetRequestState @0x82BBD9D0 returns Request::miState (rec +0x04) and 0 when the slot index is out of range or rec->miId no longer matches -- so 0 means "the streamer no longer knows this request" (open failed / slot recycled), NOT "still pending". Zeroing miNumSamples turns the request into a zero-length request, which is Process's retire-and-advance case. This is the stream-failure retirement path, not a bug.
   Any other request state, a zero request id, or a live request falls through to B.

B. PULL A CHUNK (0x82BA60F4..0x82BA6100). chunk = Stream::GetChunk(ext->mpStream) @0x82BBD878 (returns &ChunkNode::mChunk, or null when the engine has nothing buffered). If null -> return 0.

C. RESERVE A FEED SLOT (0x82BA6104..0x82BA6124). ok = GetFeedSlot(self, &slotOut). NOTE THE ORDER: the buffered-byte accounting happens BEFORE the failure test --
     ext->miBytesBuffered (+0x18) += chunk->muSize (lwz 4(r8))
   and only then `if ((u8)ok == 0) return 0;`. So a failed slot reservation still charges the chunk's bytes and leaks the chunk (it is neither released nor remembered).

D. SUBMIT (0x82BA6128..0x82BA6154):
     slot = (u32)slotOut
     ext->mucLatestFeedSlot (+0x4A) = (u8)slot
     feed[slot].mpChunkInfo = chunk        (slwi r10,r11,4 ; add r10,r10,r31 ; stw r8,0x5C(r10))
     SubmitChunk(self, chunk->mpData (lwz 8(r8)), index, aucIsNewFeedChunk, aucSeekActive)
     -- SubmitChunk's RETURN IS DISCARDED here (unlike every other call site, which stores it into ext->mpNextChunk). Streamed play does not walk a resident block list.
     return 1

**Constants**

None. No rodata reference; the only immediates are the 0/1 returns.

**Host hazards**

* THE +0x14 ZEROING IS NOT A TYPO. `stw r11, 0x14(r28)` with r11 = 0 was raw-verified from the XEX: file_off 0x3000 + 0x82BA60E4 - 0x82000000 = 0x00BA90E4, word 91 7C 00 14 = stw r11, 0x14(r28), r28 = RequestInternal. UnpackHeader independently proves RequestInternal +0x14 is the 29-bit sample count (`stw r3, 0x14(r31)` @0x82B9BFCC). Do not "fix" it.
* GetRequestState's POLARITY: 0 == gone/failed, non-zero == live. The naive reading ("0 means idle so wait") is backwards; the body at 0x82BBD9D0 returns rec->miState and only falls to `li r3,0` on out-of-range / id-mismatch.
* CHUNK LEAK on GetFeedSlot failure: the chunk is fetched from the Stream and neither released (Stream::ReleaseChunk) nor stored in a feed slot, yet its bytes are charged to miBytesBuffered. Faithful port keeps this; the only reason it is not fatal in practice is that RwacTimerClient pre-checks feed availability before every StreamNextChunk it drives.
* CONSOLE STRIDES: 0x30 (RequestInternal), 0x50 (RequestExternal), `slwi r10,r11,4` + `stw r8,0x5C(r10)` (feed[slot].mpChunkInfo). All three records contain 32-bit pointers -- index typed host arrays.
* `rw::core::filesys::Stream` IS homed (b5-decomp/src/SDKs/EATech/rwcore/filesys/stream.h): GetRequestState(u32) and GetChunk() exist with the exact shapes used here, and `Chunk` names muSize (+0x04) / mpData (+0x08). No invented API is needed for this function.
* Integer compares only; no NaN polarity.

**Implementation sketch**

```cpp
u8 SndPlayer1::StreamNextChunk(SndPlayer1 *apSelf, u32 auRequestIndex,
                               u8 aucIsNewFeedChunk, u8 aucSeekActive)
{
    SndPlayer1RequestInternal &lReq = apSelf->Req(auRequestIndex);
    SndPlayer1RequestExternal &lExt = apSelf->Ext(auRequestIndex);

    // While still QUEUED: if the streamer has forgotten our file request, retire the
    // request by making it zero-length (Process's retire-and-advance case).
    if (lReq.mucState == 1 /*QUEUED*/ && lExt.muStreamRequestId != 0)
    {
        if (lExt.mpStream->GetRequestState(lExt.muStreamRequestId) == 0)
        {
            lReq.miNumSamples = 0;
            return 0;
        }
    }

    rw::core::filesys::Chunk *lpChunk = lExt.mpStream->GetChunk();
    if (lpChunk == 0)
        return 0;

    u32 luSlot = 0;
    const u8 lucGotSlot = GetFeedSlot(apSelf, &luSlot);

    // FAITHFUL ORDER: the byte charge happens before the slot test.
    lExt.miBytesBuffered += (s32)lpChunk->muSize;
    if (lucGotSlot == 0)
        return 0;                       // chunk is leaked here -- console behaviour

    lExt.mucLatestFeedSlot = (u8)luSlot;
    apSelf->Feed(luSlot).mpChunkInfo = lpChunk;

    // return discarded: streamed play has no resident next-block pointer.
    (void)SubmitChunk(apSelf, lpChunk->mpData, auRequestIndex,
                      aucIsNewFeedChunk, aucSeekActive);
    return 1;
}
```

### `rw::audio::core::SndPlayer1::HandleLoopStart` @ `0x82BA6160`  [DECODED]

**Signature**

```cpp
static u8 HandleLoopStart(SndPlayer1 *apSelf, u32 auRequestIndex);  // r3,r4 only -- IDA's 7-arg prototype is register noise; r5..r9 are never read
```

**Behaviour**

r8 = self (a copy kept because r3 is reused for calls), r30 = index, r31 = ext, and r10 = self + self->mRequestArrayOffset (the REQUEST ARRAY BASE, with the 0x30*index added only on the branch that needs it, 0x82BA61C0).

Called by RwacTimerClient when ext->miSamplesFed == req->miLoopStart, i.e. the feeder has reached the loop point and must start re-feeding from the loop start.

Dispatch on ext->mucPlayType (lbz +0x49) at 0x82BA6190:
  playType == 0 (RAM) -> RESIDENT SUBMIT (loc_82BA61D8).
  playType == 1 (stream) -> 0x82BA61A4: ok = StreamNextChunk(self, index, /*isNewFeedChunk*/1, /*seekActive*/0). If (u8)ok != 0 return 1 else return 0.
  otherwise (2 gigastream, 3) -> loc_82BA61C0: req = base + 0x30*index;
        if (req->miLoopStart (lwz +0x18) >= ext->miResidentSamples (lwz +0x10))   // signed cmpw + bge
            -> loc_82BA6210: ok = StreamNextChunk(self, index, 1, 0); return ok ? 1 : 0
        else fall through to RESIDENT SUBMIT.

RESIDENT SUBMIT (loc_82BA61D8..0x82BA620C):
     ext->mpLoopChunk (+0x34) = ext->mpNextChunk (+0x30)      (lwz r11,0x30 ; stw r11,0x34)
     GetFeedSlot(self, &slot)      -- RETURN IGNORED
     ext->mucLatestFeedSlot = (u8)slot
     ext->mpNextChunk = SubmitChunk(self, ext->mpNextChunk (re-loaded, lwz 0x30(r31)), index,
                                    /*isNewFeedChunk*/ 1, /*seekActive*/ 0)
     return 1
   Both SubmitChunk immediates are hard-coded here (`li r6,1`, `li r7,0`): a loop restart is always a NEW feed chunk and never carries seek state.

RETURN: 1 = handled (the timer loops back and re-examines the SAME request); 0 = the stream could not supply a chunk this tick (the timer returns).

**Constants**

None. Immediates only: li r5,1 / li r6,0 (StreamNextChunk's isNewFeedChunk/seekActive) and li r6,1 / li r7,0 (SubmitChunk's).

**Host hazards**

* `cmpw cr6, r11, r9` + `bge cr6` at 0x82BA61D0/0x82BA61D4 is an INTEGER signed compare, not fcmpu -- write `>=` directly. No NaN inversion applies. (miLoopStart is a full 32-bit value read from the asset when the loop flag is set, so it can look negative; the compare is signed, faithfully.)
* GetFeedSlot's return is ignored (0x82BA61E4 -> the very next instruction reads the out-slot). Safe only because RwacTimerClient re-tests `feed[mucNextFeedSlotToFill].mucState == 0` at 0x82BA6B9C immediately before dispatching here. Keep the ignore AND keep the caller's guard.
* ext->mpNextChunk is read TWICE (0x82BA61D8 for the mpLoopChunk copy, 0x82BA61F4 for the SubmitChunk argument) with GetFeedSlot in between; GetFeedSlot cannot touch it, so a single host read is equivalent -- but the two-read order is what the asm shows.
* The 0x30 / 0x50 record strides and the `lhz +0x1C4` relative base are console pointer-bearing arithmetic; index typed host arrays.
* IDA's `BOOL __fastcall(a1..a7)` prototype is wrong -- only r3/r4 are read. Do not carry the phantom parameters into the host signature.

**Implementation sketch**

```cpp
u8 SndPlayer1::HandleLoopStart(SndPlayer1 *apSelf, u32 auRequestIndex)
{
    SndPlayer1RequestExternal &lExt = apSelf->Ext(auRequestIndex);

    bool lbResident;
    if (lExt.mucPlayType == 0)
    {
        lbResident = true;                       // RAM
    }
    else if (lExt.mucPlayType == 1)
    {
        // stream: just pull the next chunk, flagged as a new feed chunk.
        return StreamNextChunk(apSelf, auRequestIndex, /*isNewFeedChunk*/ 1,
                               /*seekActive*/ 0) != 0 ? 1u : 0u;
    }
    else
    {
        // gigastream: the loop point is resident only if it is inside the RAM head.
        // SIGNED compare (cmpw), matching the asm.
        const SndPlayer1RequestInternal &lReq = apSelf->Req(auRequestIndex);
        if (lReq.miLoopStart >= lExt.miResidentSamples)
            return StreamNextChunk(apSelf, auRequestIndex, 1, 0) != 0 ? 1u : 0u;
        lbResident = true;
    }

    if (lbResident)
    {
        lExt.mpLoopChunk = lExt.mpNextChunk;
        u32 luSlot = 0;
        GetFeedSlot(apSelf, &luSlot);            // return ignored -- faithful
        lExt.mucLatestFeedSlot = (u8)luSlot;
        lExt.mpNextChunk = SubmitChunk(apSelf, lExt.mpNextChunk, auRequestIndex,
                                       /*isNewFeedChunk*/ 1, /*seekActive*/ 0);
    }
    return 1;
}
```

### `rw::audio::core::SndPlayer1::HandleSampleEnd` @ `0x82BA6248`  [DECODED]

**Signature**

```cpp
static u8 HandleSampleEnd(SndPlayer1 *apSelf, u32 auRequestIndex, u8 *apbFinished);  // r3,r4,r5; *apbFinished is written on EVERY path
```

**Behaviour**

r30=self, r28=index, r29=req, r31=ext. Called by RwacTimerClient when ext->miSamplesFed == req->miNumSamples -- the feeder has fed the whole sample.

0. NO-LOOP EXIT (0x82BA6278..0x82BA6280, 0x82BA6424): if (req->miLoopStart < 0) { *apbFinished = 1; return 1; }  (`cmpwi cr6, r11, 0` + `blt` -- signed integer). Otherwise *apbFinished = 0 (0x82BA6284..0x82BA6288) and the loop is serviced below.

1. playType == 0, RAM (0x82BA6298..0x82BA62E4):
     if (req->miLoopStart == 0) ext->mpLoopChunk (+0x34) = ext->mpSampleData (+0x08)   // rewind to the payload head
     GetFeedSlot(self, &slot)                      -- RETURN IGNORED
     ext->mucLatestFeedSlot = (u8)slot
     ext->miSamplesFed (+0x14) = req->miLoopStart (+0x18)
     ext->mpNextChunk (+0x30) = SubmitChunk(self, ext->mpLoopChunk, index, /*isNewFeedChunk*/1, /*seekActive*/0)
     return 1

2. playType == 1, STREAM (0x82BA62F0..0x82BA6354):
     Re-queues the file at the loop offset:
       offset64 = (s64)( (f64)(s64)ext->miLoopStreamOffset (lwa +0x0C)  +  ext->mdStreamFileOffset (lfd +0x00) )
                  built with fcfid (int64->double), fadd, fctidz (double->int64 truncate toward zero)
       sub_82BC09B0(ext->mpStream (+0x28), ext->mpLoopFileName (+0x1C), offset64,
                    &SndPlayer1ChunkParse (0x82BA3FF8), self)
     ext->miSamplesFed = req->miLoopStart
     ok = StreamNextChunk(self, index, /*isNewFeedChunk*/1, /*seekActive*/0)
     if ((u8)ok != 0) return 1 else return 0

3. otherwise (2 gigastream, 3) (0x82BA6358..0x82BA6420):
     ext->miSamplesFed = req->miLoopStart
     if (req->miLoopStart < ext->miResidentSamples (+0x10))          // signed cmpw + bge to skip
         if (req->miLoopStart == 0) ext->mpLoopChunk = ext->mpSampleData
         GetFeedSlot(self, &slot)  -- RETURN IGNORED; ext->mucLatestFeedSlot = (u8)slot
         ext->mpNextChunk = SubmitChunk(self, ext->mpLoopChunk, index, 1, 0)
     // 0x82BA63B4: does the sample also have a streamed tail?
     if (ext->miResidentSamples >= req->miNumSamples (+0x14)) return 1;      // fully resident, done
     // streamed tail: re-queue it, same offset math as case 2
     sub_82BC09B0(ext->mpStream, ext->mpLoopFileName, offset64, &SndPlayer1ChunkParse, self)
     if (req->miLoopStart < ext->miResidentSamples) return 1;               // the RAM head already covers the loop
     // else fall into case 2's tail (b loc_82BA6334):
     ext->miSamplesFed = req->miLoopStart; ok = StreamNextChunk(self, index, 1, 0);
     return ok ? 1 : 0

sub_82BC09B0 (0x82BC09B0) is a 5-instruction argument-shuffling THUNK into rw::core::filesys::Stream::QueueFile @0x82BC04A0:
     r8 = r7 (context)   r7 = r6 (parse callback)   r6 = r5 (offset64)   r5 = 0 (preOpenHandle)   b QueueFile
 so the effective call is Stream::QueueFile(stream, path, /*preOpenHandle*/0, offset64, &SndPlayer1ChunkParse, self). QueueFile's r6 is stored with `std` into Request+0x120, a genuine 64-bit slot (stream.h names it mu64Size). Its RETURN (the new request id) IS DISCARDED here -- ext->muStreamRequestId (+0x2C) is NOT refreshed by HandleSampleEnd, unlike PlayHandler which stores it at 0x82BA440C.

**Constants**

rw::audio::core::SndPlayer1::SndPlayer1ChunkPa... -- the chunk-parse CALLBACK, not a string. Recovered from the lis/addi pair: 0x82BA62F8 = 3D 60 82 BA (lis r11, 0x82BA), 0x82BA6308 = 38 CB 3F F8 (addi r6, r11, 0x3FF8) -> 0x82BA3FF8 (file_off 0x00BA6FF8). The identical pair is re-emitted at 0x82BA63DC / 0x82BA63EC and again in PlayHandler at 0x82BA4454 / 0x82BA4460. A byte scan of the whole XEX finds NO "SndPlayer1 Chunk..." string, and 0x82BA3FF8 disassembles as code -- the IDA name is a truncated FUNCTION name.

The callee, decoded from raw XEX at 0x82BA3FF8 (file 0x00BA6FF8), register contract r3 = buffer, r4 = available bytes, r9 = u32* out-consumed (r5..r8 unread; IDA's 7-arg prototype matches rw::core::filesys::ChunkParseCallback, whose 7th parameter is lpuConsumed):
    if (avail < 8) return 0;
    raw = big-endian u32 at buf[0..3]        (four lbz reassembled through the caller's back-chain slot as scratch -- no frame)
    last = raw >> 31;  size = raw & 0x7FFFFFFF;
    if (size > avail) return 0;
    *out = size;
    if (last != 1) return 1;
    write `size` back over buf[0..3] (flag cleared, four stb); return 2;
This is what makes SubmitChunk's header read work: the parser has already stripped the top bit, so blockBytes is the clean length.

No rodata floats or tables are referenced by HandleSampleEnd itself.

**Host hazards**

* ⚠️ THE STREAM REQUEST ID IS NOT REFRESHED. Stream::QueueFile returns the new request id (`lwz r3, 0(r31)` at 0x82BC0588) and PlayHandler stores it into ext->muStreamRequestId; HandleSampleEnd discards it on BOTH re-queue sites. StreamNextChunk's liveness gate then keeps probing the OLD id. Faithful -- reproduce the discard.
* GetFeedSlot's return is ignored at both submit sites (0x82BA62B4, 0x82BA638C). Same caller-guard dependency as HandleLoopStart.
* All the branch compares here are INTEGER: `cmpwi/blt` on miLoopStart (0x82BA6280), `cmpw/bge` on loopStart-vs-residentSamples (0x82BA636C, 0x82BA641C), `cmpw/blt` on residentSamples-vs-numSamples (0x82BA63C4). There is NO fcmpu in this body, so the NaN-polarity rule does not apply -- write the ordered predicates directly. The only FP work is the fcfid/fadd/fctidz offset computation, which is a conversion chain, not a branch.
* `lwa r10, 0xC(r31)` is a SIGN-EXTENDING 32->64 load of miLoopStreamOffset before fcfid; the host must write `(f64)(s64)ext.miLoopStreamOffset`, not `(f64)(u32)`.
* `fctidz` truncates toward zero into a 64-bit integer. On x64 that is a plain `(s64)` cast of the double (C++ truncation semantics match); do NOT use llround/floor.
* CONSOLE STRIDES 0x30 / 0x50 as elsewhere.
* stream.h names Stream::QueueFile's third parameter `lu64Size`, but every SndPlayer1 call site (here and PlayHandler @0x82BA4404, which passes `ext->miChunkOffset + (s64)ext->mdStreamFileOffset`) supplies a FILE BYTE OFFSET. Flagged as a naming conflict in the already-homed filesys header; it does not change this function's decode.
* SndPlayer1ChunkParse writes four bytes through r1 (`stb r10, back_chain(r1)`) -- it uses the CALLER's back-chain word as scratch with no frame of its own. A host port must use a real local; the console trick is not reproducible and not observable.

**Implementation sketch**

```cpp
u8 SndPlayer1::HandleSampleEnd(SndPlayer1 *apSelf, u32 auRequestIndex, u8 *apbFinished)
{
    SndPlayer1RequestInternal &lReq = apSelf->Req(auRequestIndex);
    SndPlayer1RequestExternal &lExt = apSelf->Ext(auRequestIndex);

    if (lReq.miLoopStart < 0)          // signed cmpwi/blt -- no loop, the sample is over
    {
        *apbFinished = 1;
        return 1;
    }
    *apbFinished = 0;

    if (lExt.mucPlayType == 0)                                  // ---- RAM ----
    {
        if (lReq.miLoopStart == 0)
            lExt.mpLoopChunk = lExt.mpSampleData;
        u32 luSlot = 0;
        GetFeedSlot(apSelf, &luSlot);                           // return ignored
        lExt.mucLatestFeedSlot = (u8)luSlot;
        lExt.miSamplesFed = lReq.miLoopStart;
        lExt.mpNextChunk = SubmitChunk(apSelf, lExt.mpLoopChunk, auRequestIndex, 1, 0);
        return 1;
    }

    if (lExt.mucPlayType == 1)                                  // ---- STREAM ----
    {
        RequeueLoopStream(apSelf, lExt);
        lExt.miSamplesFed = lReq.miLoopStart;
        return StreamNextChunk(apSelf, auRequestIndex, 1, 0) != 0 ? 1u : 0u;
    }

    // ---- GIGASTREAM (playType 2, and the unused 3) ----
    lExt.miSamplesFed = lReq.miLoopStart;
    if (lReq.miLoopStart < lExt.miResidentSamples)              // loop point is in the RAM head
    {
        if (lReq.miLoopStart == 0)
            lExt.mpLoopChunk = lExt.mpSampleData;
        u32 luSlot = 0;
        GetFeedSlot(apSelf, &luSlot);                           // return ignored
        lExt.mucLatestFeedSlot = (u8)luSlot;
        lExt.mpNextChunk = SubmitChunk(apSelf, lExt.mpLoopChunk, auRequestIndex, 1, 0);
    }
    if (lExt.miResidentSamples >= lReq.miNumSamples)
        return 1;                                               // no streamed tail at all

    RequeueLoopStream(apSelf, lExt);
    if (lReq.miLoopStart < lExt.miResidentSamples)
        return 1;

    lExt.miSamplesFed = lReq.miLoopStart;
    return StreamNextChunk(apSelf, auRequestIndex, 1, 0) != 0 ? 1u : 0u;
}

// The shared re-queue step (emitted twice, at 0x82BA62F0 and 0x82BA63D4).
// The offset really is (f64 base + s32 loop offset) truncated to s64: fcfid/fadd/fctidz.
void SndPlayer1::RequeueLoopStream(SndPlayer1 *apSelf, SndPlayer1RequestExternal &arExt)
{
    const s64 lOffset = (s64)((f64)(s64)arExt.miLoopStreamOffset + arExt.mdStreamFileOffset);
    // sub_82BC09B0 is a thunk: preOpenHandle is hard-wired to 0 and the return discarded.
    (void)arExt.mpStream->QueueFile(arExt.mpLoopFileName, /*preOpenHandle*/ 0,
                                    (u64)lOffset, &SndPlayer1::SndPlayer1ChunkParse,
                                    apSelf);
}
```

### `rw::audio::core::SndPlayer1::UnpackHeader` @ `0x82B9BF08`  [DECODED]

**Signature**

```cpp
static void UnpackHeader(SndPlayer1 *apSelf, u32 auRequestIndex, const u8 *apHeader);  // r3,r4,r5. IDA types it `int` but the returned r3 is a dead GetBits residue -- no caller reads it
```

**Behaviour**

r31 = req (self + mRequestArrayOffset + 0x30*index), r30 = ext (mpRequestExternal + 0x50*index), r28 = apHeader, r27 = 0.

A BitGetter is constructed ON THE STACK at r1+0x50 (`0xA0+var_50`) as { mpBitBuffer = apHeader; mBitPosition = 0 } (0x82B9BF34..0x82B9BF38) and every field is pulled MSB-first through BitGetter::GetBits @0x82680460.

EXACT BIT WIDTHS AND DESTINATIONS, in emission order:
   1.  4 bits  -> DISCARDED (version)                                     0x82B9BF3C/0x82B9BF4C
   2.  4 bits  -> ext->mucCodec           (+0x48, stb)                    0x82B9BF50..0x82B9BF68
   3.  6 bits  -> req->mucChannels        (+0x2B, stb) = value + 1        0x82B9BF60..0x82B9BF7C
   4. 18 bits  -> req->mfSampleRate       (+0x10, stfs)                   0x82B9BF74..0x82B9BFA0
                  conversion: clrldi r11,r3,32 (zero-extend to 64) ; std ; lfd ; fcfid ; frsp ; stfs
                  i.e. mfSampleRate = (f32)(f64)(u64)(u32)rateBits -- UNSIGNED.
   5.  2 bits  -> ext->mucPlayType        (+0x49, stb)   0=RAM 1=stream 2=gigastream (3 unused)
   6.  1 bit   -> loopFlag (r29, register only)
   7. 29 bits  -> req->miNumSamples       (+0x14, stw)                    0x82B9BFC0..0x82B9BFCC
   (fixed part = 4+4+6+18+2+1+29 = 64 bits exactly)
   8.  if (loopFlag & 0xFF) : 32 bits -> req->miLoopStart (+0x18, stw)
       else                 : req->miLoopStart = -1                       0x82B9BFD0..0x82B9BFF0
   9.  if (ext->mucPlayType == 2) : 32 bits -> ext->miResidentSamples (+0x10, stw)   0x82B9BFF4..0x82B9C00C
  10.  if (loopFlag != 0):
            playType == 1                                   -> read 32 bits -> ext->miLoopStreamOffset (+0x0C)
            playType == 2 && req->miLoopStart >= ext->miResidentSamples  (signed cmpw + bge)
                                                            -> read 32 bits -> ext->miLoopStreamOffset
            otherwise (playType 0 or 3, or a loop point inside the gigastream RAM head)
                                                            -> ext->miLoopStreamOffset = 0 (r27)
       if (loopFlag == 0): ext->miLoopStreamOffset is LEFT UNTOUCHED.       0x82B9C010..0x82B9C04C
  11.  ext->mpSampleData (+0x08) = apHeader + (mBitPosition >> 3)          0x82B9C050..0x82B9C05C
       `lwz r11, var_4C(r1)` reads the BitGetter's cursor back off the stack; `srwi r11,r11,3` is the bits->bytes divide.

Since the fixed part is 64 bits and every optional field is 32, the cursor is always byte-aligned at step 11 and the >>3 truncation is exact.

**Constants**

No rodata. Widths are all immediates: li r4,4 / 4 / 6 / 0x12(18) / 2 / 1 / 0x1D(29) / 0x20(32). The stack BitGetter lives at r1+0x50 (data) and r1+0x54 (cursor) -- an 8-byte object matching the committed BitGetter.h exactly (mpBitBuffer +0x00, mBitPosition +0x04).

**Host hazards**

* THE CODEC FIELD IS FOUR BITS (0..15) but StartRequest's GUID table has only EIGHT entries and no bounds check. The two facts must be documented together -- this function is where the out-of-range value can enter.
* Step 10's `cmpw cr6, r11, r10` + `bge` is a SIGNED INTEGER compare of miLoopStart against miResidentSamples. miLoopStart at that point came from a raw 32-bit GetBits, so an asset with bit31 set makes it negative and the branch flips. Faithful; no NaN rule applies (there is no fcmpu anywhere in this body).
* The sample-rate conversion is `clrldi r11,r3,32` -> UNSIGNED widen -> fcfid -> frsp. Writing `(f32)(s32)bits` would differ for 18-bit values (it cannot here, since 18 bits max 262143), but the host must still use the unsigned form so the code reads as the asm does.
* `srwi r11, r11, 3` truncates -- exact only because the header is always a whole number of bytes (64 + 32k bits). If a future asset version adds a non-multiple-of-8 field the payload pointer silently rounds down.
* ext->mpSampleData is a POINTER assembled from `apHeader + byteCount` -- it widens on x64; the RequestExternal 0x50 stride does not survive.
* IDA's `int` return is a dead register: r3 last holds a GetBits result (or is stale when no optional field was read). PlayHandler ignores it. Model as void.
* GetBits(32) on a 32-bit-wide accumulator: BitGetter::GetBits is documented to shift fragments into the low end; a 32-bit request is the maximum the accumulator holds and is exercised on four paths here. No overflow guard exists.

**Implementation sketch**

```cpp
void SndPlayer1::UnpackHeader(SndPlayer1 *apSelf, u32 auRequestIndex, const u8 *apHeader)
{
    SndPlayer1RequestInternal &lReq = apSelf->Req(auRequestIndex);
    SndPlayer1RequestExternal &lExt = apSelf->Ext(auRequestIndex);

    BitGetter lBits;
    lBits.mpBitBuffer  = apHeader;
    lBits.mBitPosition = 0;

    (void)BitGetter::GetBits(&lBits, 4);                       // version -- discarded
    lExt.mucCodec    = (u8)BitGetter::GetBits(&lBits, 4);
    lReq.mucChannels = (u8)(BitGetter::GetBits(&lBits, 6) + 1);
    // UNSIGNED int -> f64 -> f32 (clrldi/fcfid/frsp), not a signed conversion.
    lReq.mfSampleRate = (f32)(f64)(u64)BitGetter::GetBits(&lBits, 18);
    lExt.mucPlayType = (u8)BitGetter::GetBits(&lBits, 2);
    const u32 luLoopFlag = BitGetter::GetBits(&lBits, 1);
    lReq.miNumSamples = (s32)BitGetter::GetBits(&lBits, 29);

    if ((u8)luLoopFlag != 0)
        lReq.miLoopStart = (s32)BitGetter::GetBits(&lBits, 32);
    else
        lReq.miLoopStart = -1;

    if (lExt.mucPlayType == 2)
        lExt.miResidentSamples = (s32)BitGetter::GetBits(&lBits, 32);

    if (luLoopFlag != 0)
    {
        const bool lbNeedLoopOffset =
            (lExt.mucPlayType == 1) ||
            (lExt.mucPlayType == 2 && lReq.miLoopStart >= lExt.miResidentSamples); // SIGNED
        if (lbNeedLoopOffset)
            lExt.miLoopStreamOffset = (s32)BitGetter::GetBits(&lBits, 32);
        else
            lExt.miLoopStreamOffset = 0;
    }
    // luLoopFlag == 0: miLoopStreamOffset is deliberately left as-is.

    // Payload starts at the first byte past the packed header.
    lExt.mpSampleData = const_cast<u8 *>(apHeader) + (lBits.mBitPosition >> 3);
}
```

### `rw::audio::core::SndPlayer1::SetSeekData` @ `0x82B9C068`  [DECODED]

**Signature**

```cpp
static void SetSeekData(SndPlayer1 *apSelf, u32 auRequestIndex, const u8 *apSeekTable, s32 aiTargetSample);  // r3,r4,r5,r6
```

**Behaviour**

r30 = req, r31 = ext (usual 0x30 / 0x50 derivations). r4 is re-purposed at 0x82B9C088 (`mr r4, r5`) so the seek-table pointer becomes SeekTableParser::Parse's arg2.

GUARD (0x82B9C0A0..0x82B9C0AC): `cmpwi cr6, r6, 0 ; ble` and `cmplwi cr6, r4, 0 ; beq`, i.e. the parse arm runs only when aiTargetSample > 0 (SIGNED) AND apSeekTable != 0. Otherwise the RESET arm runs.

PARSE ARM (0x82B9C0B0..0x82B9C104). A 32-byte SeekTableParser lives on the stack at r1+0x50 (`0x90+var_40`); SeekTableParser::Parse(&parser, apSeekTable, aiTargetSample) @0x82B6FBD8. Its return is IGNORED. The committed SeekTableParser.h layout names every slot the copy-out touches:
     req->miDecoderSkip     (+0x20) = parser.mDecoderSkip      (var_38 == parser+0x08)
     req->miStreamSkip      (+0x24) = parser.mStreamSkip       (var_3C == parser+0x04)
     ext->miPlayerSkip      (+0x3C) = parser.mPlayerSkip       (var_34 == parser+0x0C)
     ext->miChunkOffset     (+0x40) = parser.mChunkOffset      (var_30 == parser+0x10)
     ext->mpSeekData        (+0x38) = parser.mpSeekData        (var_40 == parser+0x00)   <-- A POINTER
     ext->miSeekDataVersion (+0x44) = parser.mSeekDataVersion  (var_2C == parser+0x14)
     ext->mucIsNewFeedChunk (+0x4C) = (u8)parser.mIsNewFeedChunk (var_24 == parser+0x1C, lbz/stb)
     req->miPlayerSkip      (+0x1C) = 0
     ext->miSamplesFed      (+0x14) = req->miStreamSkip   (re-read from +0x24 at 0x82B9C0F8)

RESET ARM (0x82B9C108..0x82B9C128), when there is no usable seek:
     req->miDecoderSkip     = 0
     ext->miPlayerSkip      = 0
     ext->miChunkOffset     = 0
     ext->mpSeekData        = 0
     ext->mucIsNewFeedChunk = 1
     req->miPlayerSkip      = 0
     req->miStreamSkip      = 0
   NOTE the asymmetry: ext->miSeekDataVersion (+0x44) and ext->miSamplesFed (+0x14) are NOT written on this arm.

The three skip counters this writes are exactly the trio StartRequest ORs into its seek-active flag, and req->miDecoderSkip is what SubmitChunk hands Decoder::Feed as iStartSample.

**Constants**

None. The only immediates are 0 and the `li r10,1` that becomes mucIsNewFeedChunk on the reset arm. The stack SeekTableParser is 32 bytes at r1+0x50; the field mapping was cross-checked against the committed SeekTableParser.h (mpSeekData +0x00, mStreamSkip +0x04, mDecoderSkip +0x08, mPlayerSkip +0x0C, mChunkOffset +0x10, mSeekDataVersion +0x14, mLatency +0x18, mIsNewFeedChunk +0x1C) and every displacement lines up.

**Host hazards**

* ⚠️ ext->mpSeekData (+0x38) IS A POINTER (SeekTableParser::mpSeekData, typed u8* in the committed header). It is the value SubmitChunk feeds to Decoder::Feed's r8 and therefore lands in DecoderRequest+0x04. It widens on x64 in BOTH structs, so neither RequestExternal's 0x50 stride nor DecoderRequest's 0x14 stride is portable.
* ⚠️ ext->miPlayerSkip (+0x3C) IS WRITE-ONLY-ISH: a whole-surface scan of every SndPlayer1 dossier for `0x3C(r` finds exactly three sites -- the two stores here and StartRequest's single read at 0x82BA64DC (the seek-flag OR). Meanwhile req->miPlayerSkip (+0x1C) -- the one Process actually consumes at 0x82BA0870 -- is only ever written to ZERO here and by nothing else in the class. So the parser's mPlayerSkip never reaches the player. Reported as observed; do NOT "connect" the two on the host without new evidence.
* The reset arm leaves miSeekDataVersion and miSamplesFed stale. Since SubmitChunk only reads miSeekDataVersion under the seek-active flag (which the reset arm forces to false via the three zeroed counters), the staleness is inert -- but only by that coupling.
* SeekTableParser::Parse's boolean result is discarded, so a table that failed to resolve still leaves whatever Parse's own reset wrote (Parse zeroes +0x00/+0x04/+0x08/+0x10/+0x14 on failure but NOT +0x0C mPlayerSkip or +0x1C mIsNewFeedChunk -- both of which this function copies out).
* PlayHandler's call site (0x82BA42D4..0x82BA42E0) proves the fourth argument is a TARGET SAMPLE, not a byte size: r6 comes from the play command's seek time and is compared against req->miNumSamples immediately before (`lwz r11,0x14(r28) ; cmpw ; ble`). IDA's `a4` name gives no hint.
* Integer compares only -- no NaN polarity.

**Implementation sketch**

```cpp
void SndPlayer1::SetSeekData(SndPlayer1 *apSelf, u32 auRequestIndex,
                             const u8 *apSeekTable, s32 aiTargetSample)
{
    SndPlayer1RequestInternal &lReq = apSelf->Req(auRequestIndex);
    SndPlayer1RequestExternal &lExt = apSelf->Ext(auRequestIndex);

    if (aiTargetSample > 0 && apSeekTable != 0)          // SIGNED > 0 (cmpwi/ble)
    {
        SeekTableParser lParser;
        (void)lParser.Parse(const_cast<u8 *>(apSeekTable), aiTargetSample); // result ignored

        lReq.miDecoderSkip     = lParser.mDecoderSkip;
        lReq.miStreamSkip      = lParser.mStreamSkip;
        lExt.miPlayerSkip      = lParser.mPlayerSkip;
        lExt.miChunkOffset     = lParser.mChunkOffset;
        lExt.mpSeekData        = lParser.mpSeekData;      // POINTER -- must widen
        lExt.miSeekDataVersion = lParser.mSeekDataVersion;
        lExt.mucIsNewFeedChunk = lParser.mIsNewFeedChunk;
        lReq.miPlayerSkip      = 0;
        lExt.miSamplesFed      = lReq.miStreamSkip;
    }
    else
    {
        lReq.miDecoderSkip     = 0;
        lExt.miPlayerSkip      = 0;
        lExt.miChunkOffset     = 0;
        lExt.mpSeekData        = 0;
        lExt.mucIsNewFeedChunk = 1;
        lReq.miPlayerSkip      = 0;
        lReq.miStreamSkip      = 0;
        // miSeekDataVersion and miSamplesFed deliberately untouched -- faithful.
    }
}
```

### `rw::audio::core::SndPlayer1::StreamLostCallback` @ `0x82BA4100`  [DECODED]

**Signature**

```cpp
static void StreamLostCallback(SndPlayer1 *apSelf);  // r3 = the SndPlayer1, delivered as the StreamPool entry's context; IDA's `int result` return is r3 falling through unchanged
```

**Behaviour**

r31 = self, r28 = 0 (the shared zero), r29 = request index, r30 = 0x30*index (the byte stride, advanced in lock-step).

  if (self->mucMaxRequests (lbz +0x1CA) == 0) skip the loop entirely.
  for (i = 0; i < mucMaxRequests; ++i) {
      state = *(u8*)(self + self->mRequestArrayOffset + 0x30*i + 0x2A);
      if (state != 0 /*not FREE*/) RemoveRequest(self, i);        // @0x82BA0460
  }
  self->mucCurrentRequestIndex (+0x1C9) = 0;
  self->mucNextFreeRequest     (+0x1C7) = 0;
  self->mucNextRequestToFree   (+0x1C8) = 0;

Note the loop recomputes the request base as `self->mRequestArrayOffset + r30` each iteration (0x82BA4128..0x82BA4130) -- the +0x1C4 halfword is re-read every lap.

TWO ROLES, both attested:
  1. The StreamPool loss notification. PlayHandler installs it at 0x82BA4300..0x82BA4318: `lis/addi r5, &StreamLostCallback ; mr r6, self ; bl StreamPool::AcquireStream`, and AcquireStream stores its r5 into the pool entry's +0x0C slot (0x82B6BB90 `stw r28, 0xC(r3)`). So the pool calls it as fn(context) when the stream it lent out is taken away.
  2. ReleaseEvent's teardown step (0x82BA4178 calls it before removing the timer and freeing the +0x1B0 allocation).

It does NOT touch the three feed cursors (+0x1CD/+0x1CE/+0x1CF) or the declick state -- only StopHandler does that (0x82BA455C..0x82BA4564).

**Constants**

None. Immediates only (li r28,0; addi r30,r30,0x30; addi r29,r29,1).

**Host hazards**

* CONSOLE STRIDE 0x30 and the +0x1C4 relative base: RequestInternal contains Decoder* mpDecoder, so neither survives x64. The host loop must index a typed array.
* The loop bound is re-loaded from +0x1CA on EVERY iteration (0x82BA414C), so a RemoveRequest that changed mucMaxRequests would be observed. It does not, but keep the read inside the loop if you want literal fidelity; a hoisted `mucMaxRequests` is behaviourally identical here.
* r3 is never written after entry, so the console "returns" self. No caller reads it -- model as void, and do not let IDA's `int result` prototype leak into the host signature.
* THE INSTALLED CALLBACK'S REAL SIGNATURE is StreamPool's, and rw::audio::core::StreamPool is NOT homed anywhere in this repo (no StreamPool.h; grep over b5-decomp finds no such type). What is attested from the call site + AcquireStream @0x82B6BAB0: AcquireStream(r3 = StreamPool*, f1 = f32 priority, r5 = the lost-callback function pointer, r6 = the callback context) and the pool ENTRY it returns has a 32-byte stride with { +0x08 f32 priority, +0x0C the callback, +0x14 rw::core::filesys::Stream*, +0x18 u16 refcount, +0x1A u8 inUse }. The host needs a StreamPool home carrying at least that entry shape and a `typedef void (*StreamLostFn)(void *apContext);` -- do NOT invent a wider API.
* No floating point at all in this body.

**Implementation sketch**

```cpp
void SndPlayer1::StreamLostCallback(SndPlayer1 *apSelf)
{
    // Every non-FREE request is torn down; the pool has taken the stream away.
    for (u32 i = 0; i < apSelf->mucMaxRequests; ++i)
    {
        if (apSelf->Req(i).mucState != 0 /*FREE*/)
            RemoveRequest(apSelf, i);
    }

    apSelf->mucCurrentRequestIndex = 0;
    apSelf->mucNextFreeRequest     = 0;
    apSelf->mucNextRequestToFree   = 0;
    // The three feed cursors and the declick state are deliberately NOT reset here.
}
```

### `rw::audio::core::SndPlayer1::RwacTimerClient` @ `0x82BA6980`  [DECODED]

**Signature**

```cpp
static void RwacTimerClient(void *apContext, f32 afUnusedTickArg);  // registered as TimerHandle::mpCallback (`void (*)(void*, f32)`); AddTimer @0x82B6EBE4/0x82B6EBE8 stores this function at instance+0x44 and `self` at instance+0x48. The body reads only r3
```

**Behaviour**

r31 = self (from apContext). r10 holds self->mRequestArrayOffset (lhz +0x1C4) for the WHOLE body -- loaded once at 0x82BA69B8 and never reloaded; r27 is the walking request index; r30 the current RequestInternal*; r29 = (u8)r27 latched per lap; r28 the matching RequestExternal*.

0. VOICE GATE (0x82BA6998..0x82BA69A4). `lwz r11, 8(r31)` = PlugIn::mpVoice; `lbz r11, 0x47(r11)` = Voice::mucState. If it equals 2 (EXPELLED) the function returns IMMEDIATELY -- before FeedCleanup, before RequestCleanup, before any attribute publish.

1. HOUSEKEEPING (0x82BA69A8..0x82BA69B0): FeedCleanup(self) then RequestCleanup(self).

2. ATTRIBUTE PUBLISH (0x82BA69B4..0x82BA6A4C). idx = self->mucCurrentRequestIndex (+0x1C9); req = self + reqOffset + 0x30*idx.
   available = (req->mucState != 0 && req->mucState != 4).
   attribute 0 (ATTRIBUTE_GETCURRENTREQUEST, f32 at self+0x28) = self->mfCurrentRequestHandle (lfs +0x1A0) -- published UNCONDITIONALLY, before the availability branch.
   if (!available):
       attribute 2 (GETSAMPLELENGTH,   f64 at self+0x38) = 0.0   (dbl_82001CA8)
       attribute 1 (GETSAMPLEPOSITION, f64 at self+0x30) = 0.0
       RETURN.
   else:
       rate = self->mfCurrentRequestSampleRate (lfs +0x1A4)
       attribute 2 = (f64)(s64)(s32)self->miCurrentRequestSampleCount  (lwa +0x1AC) / rate
       attribute 1 = (f64)(s64)(s32)self->miCurrentRequestSamplesPlayed(lwa +0x1A8) / rate

3. FIND A REQUEST WITH SAMPLES (0x82BA6A50..0x82BA6ABC). If req->miNumSamples (+0x14) == 0, advance idx (wrap at mucMaxRequests, +0x1CA) and repeat:
       if the next request is not `available` -> RETURN;
       if it has miNumSamples == 0 -> keep advancing.
   Note this scan can wrap forever only if some request is available with a non-zero count -- the not-available exit terminates it.

4. MAIN SERVICE LOOP (loc_82BA6AD0), with f30 = dbl_820B6460 (0.005333333333333333 == 256/48000) and f31 = dbl_82001CA8 (0.0) held live:
   a. if (req->mucState is 0 or 4) RETURN.
   b. if (feed[self->mucNextFeedSlotToFill (+0x1CD)].mucState (+0x69+16*slot) != 0) RETURN.   -- no free feed slot this tick
   c. r29 = (u8)idx; ext = mpRequestExternal + 0x50*r29.
   d. PRIORITY REPUBLISH (0x82BA6B1C..0x82BA6B30): if (ext->mpStreamPoolEntry (lwz +0x24) != 0)
          *(f32*)(entry + 8) = self->mpVoice->mfPriority (lfs Voice+0x38)
      i.e. the pool entry's priority slot is refreshed from the owning Voice every tick.
   e. QUEUED -> FEEDING (0x82BA6B34..0x82BA6B8C):
          if (req->mucState == 1 /*QUEUED*/) {
              if (StartRequest(self, r29) == 0) RETURN;          // stays QUEUED, retry next tick
              req->mucState = 2;                                 // FEEDING  (stb r11=2, 0x2A(r30))
              if (ext->mucCodec == 3 /* 'EXm0' */
                  && req->mdStartTime == 0.0                     // fcmpu f0,f31 + bne -> skip
                  && r29 == self->mucCurrentRequestIndex)
                  req->mdStartTime = self->mpSystem->mfSystemTime (lfd System+0x08) + 0.005333333333333333;
          }
      This is the ONLY QUEUED->FEEDING transition in the class.
   f. FEEDING SERVICE (0x82BA6B90..0x82BA6C38):
          if (req->mucState != 2) goto ADVANCE (loc_82BA6C3C).
          if (feed[mucNextFeedSlotToFill].mucState != 0) goto ADVANCE.   -- re-checked
          if (ext->miSamplesFed (+0x14) == req->miLoopStart (+0x18))
              ok = HandleLoopStart(self, r29);  ok ? goto (a) with the SAME request : RETURN;
          else if (ext->miSamplesFed == req->miNumSamples (+0x14))
              ok = HandleSampleEnd(self, r29, &finished);
              if (!ok) RETURN;
              if (!finished) goto (a) with the SAME request;
              req->mucState = 3;                                 // stream complete, awaiting Process
              idx = (r29 + 1) % mucMaxRequests; goto NEXT;
          else
              ok = StreamNextChunk(self, r29, /*isNewFeedChunk*/0, /*seekActive*/0);
              ok ? goto (a) with the SAME request : RETURN;
   g. ADVANCE (loc_82BA6C3C): idx = (r29 + 1) % mucMaxRequests.
   h. NEXT (loc_82BA6C5C): if (idx == self->mucCurrentRequestIndex) RETURN;   // wrapped to the head
      req = self + reqOffset + 0x30*idx; goto (a).

The modulo is written as `n = (x+1) & 0xFF; if (n == mucMaxRequests) n = 0;` at all three sites (0x82BA6A68, 0x82BA6C08, 0x82BA6C3C).

**Constants**

dbl_82001CA8 -- vaddr 0x82001CA8, file_off = 0x3000 + 0x82001CA8 - 0x82000000 = 0x00004CA8. Raw big-endian bytes: 00 00 00 00 00 00 00 00 = 0.0 (f64). Used both as the "no request" attribute value and as the fcmpu comparand for `mdStartTime == 0.0`. (It is the same shared 0.0 literal System::CreateInstance seeds mfSystemTime from.)

dbl_820B6460 -- vaddr 0x820B6460, file_off = 0x3000 + 0x820B6460 - 0x82000000 = 0x000B9460. Raw big-endian bytes: 3F 75 D8 67 C3 EC E2 A5 = 0.005333333333333333 (f64). That is exactly 256 / 48000 -- one 256-frame mixer chunk at 48 kHz, i.e. the start time is pushed one mix block into the future. Name it kOneMixChunkSeconds.

Codec immediate 3 == kDecoderGuids[3] == 'EXm0' (0x45586D30, file 0x00177584).
Other immediates: voice state 2 (EXPELLED), request states 0/1/2/3/4, feed-ring modulus is implicit via mucMaxRequests (+0x1CA), feed record stride via `rotlwi ...,4` and base +0x69.

**Host hazards**

* ⚠️ ATTRIBUTE WIDTH TRAP (the sharpest x64 issue in this cluster). PlugIn::mpAttribute points at self+0x28 and PlugIn::GetAttribute @0x82B6A8C8 is `lwz r11,0xC(r3) ; slwi r10,r4,3 ; lfsx f0,r10,r11` -- an 8-BYTE STRIDE read with a 4-BYTE `lfs`. The timer writes attribute 0 with `stfs` (a genuine f32) but attributes 1 and 2 with `stfd` (full f64 covering +0x30..+0x37 and +0x38..+0x3F). On the BIG-ENDIAN console a subsequent GetAttribute of index 1 or 2 returns the double's HIGH word reinterpreted as f32; on little-endian x64 the identical code returns the LOW word. A literal port therefore SILENTLY CHANGES what GETSAMPLEPOSITION / GETSAMPLELENGTH report. The rodata doc string at 0x82174b58 ("If the GETSAMPLELENGTH attribute is not set to 0.0...") shows game code does read them through the f32 path, so this is observable. No other accessor exists in the image (a name scan finds only GetAttribute / SetAttribute / SetAttributeHandler). BLOCKED pending a decision by whoever homes the class: either model slots 1/2 as a f64 union and give the reader the double, or reproduce the console's high-word aliasing. Do not silently pick one.
* `lwa` (0x82BA6A1C, 0x82BA6A24) sign-extends 32->64 before fcfid: write `(f64)(s64)value`, never `(f64)(u32)`.
* NO ZERO GUARD on mfCurrentRequestSampleRate before the two fdiv's. CreateInstance seeds 48000.0f, but a corrupted request yields inf/NaN straight into the published attributes.
* NaN POLARITY: the only fcmpu is 0x82BA6B6C (`fcmpu cr6, f0, f31` + `bne cr6, skip`). Unordered clears EQ, so NaN takes the NOT-taken/skip path -- identical to C++ `mdStartTime == 0.0`. Write it as `==`; do NOT negate. Every other compare in the body is integer (cmpwi/cmplwi/cmplw/cmpw).
* mRequestArrayOffset is loaded ONCE into r10 at 0x82BA69B8 and reused at 0x82BA6A88 and 0x82BA6C6C. On the host this is a computed relative offset containing pointer-bearing strides -- use the typed accessor each time; the caching is a register allocation detail, not semantics.
* CONSOLE STRIDES: 0x30 (RequestInternal), 0x50 (RequestExternal), `rotlwi ...,4` + `lbz 0x69(...)` (feed[slot].mucState). All three records carry pointers.
* The EXPELLED-voice early-out at 0x82BA69A4 skips FeedCleanup, so an expelled voice's buffered chunks are never released by the timer -- ReleaseEvent's StreamLostCallback path is what tears them down. Faithful.
* The feed-availability check appears TWICE per lap (0x82BA6AF4 and 0x82BA6B9C) with StartRequest in between -- StartRequest may consume the slot, hence the re-check. Do not fold them.
* `*(f32*)(ext->mpStreamPoolEntry + 8)` writes into an UNHOMED StreamPool entry. Register contract: the pointer comes from StreamPool::AcquireStream's return (entry stride 0x20; +0x08 is the f32 priority AcquireStream itself seeds at 0x82B6BB8C). The host needs a StreamPool entry type with a named mfPriority; do not reach through a raw byte offset.
* This function is NOT a deferred-command-ring handler -- none of the twelve in this cluster is -- so the "return the host sizeof of the record" rule does not apply anywhere here. (SndPlayer1's ring handlers are PlayHandler @0x82BA41D8, StopHandler @0x82BA44E0 and ModifyStartTimeHandler @0x82BA03D0, all outside this slice.)

**Implementation sketch**

```cpp
void SndPlayer1::RwacTimerClient(void *apContext, f32 /*afUnusedTickArg*/)
{
    SndPlayer1 *lpSelf = static_cast<SndPlayer1 *>(apContext);

    // 2 == Voice expelled: do nothing at all (not even feed cleanup).
    if (lpSelf->GetVoice()->mucState == 2)
        return;

    FeedCleanup(lpSelf);
    RequestCleanup(lpSelf);

    u32 luIndex = lpSelf->mucCurrentRequestIndex;
    SndPlayer1RequestInternal *lpReq = &lpSelf->Req(luIndex);

    // --- attribute publish -------------------------------------------------------
    // ATTRIBUTE_GETCURRENTREQUEST -- always, even with nothing playing.
    lpSelf->SetAttrCurrentRequest(lpSelf->mfCurrentRequestHandle);

    if (lpReq->mucState == 0 || lpReq->mucState == 4)
    {
        lpSelf->SetAttrSampleLength(0.0);      // dbl_82001CA8
        lpSelf->SetAttrSamplePosition(0.0);
        return;
    }
    {
        const f32 lfRate = lpSelf->mfCurrentRequestSampleRate;   // no zero guard -- faithful
        lpSelf->SetAttrSampleLength((f64)(s64)lpSelf->miCurrentRequestSampleCount  / lfRate);
        lpSelf->SetAttrSamplePosition((f64)(s64)lpSelf->miCurrentRequestSamplesPlayed / lfRate);
    }

    // --- skip requests that carry no samples -------------------------------------
    while (lpReq->miNumSamples == 0)
    {
        luIndex = (luIndex + 1u) % lpSelf->mucMaxRequests;
        lpReq   = &lpSelf->Req(luIndex);
        if (lpReq->mucState == 0 || lpReq->mucState == 4)
            return;
    }

    // --- service loop -------------------------------------------------------------
    for (;;)
    {
        if (lpReq->mucState == 0 || lpReq->mucState == 4)
            return;
        if (lpSelf->Feed(lpSelf->mucNextFeedSlotToFill).mucState != 0)
            return;                                     // no free feed slot

        const u32 luIdx = (u8)luIndex;
        SndPlayer1RequestExternal &lExt = lpSelf->Ext(luIdx);

        if (lExt.mpStreamPoolEntry != 0)
            lExt.mpStreamPoolEntry->mfPriority = lpSelf->GetVoice()->mfPriority;

        if (lpReq->mucState == 1 /*QUEUED*/)
        {
            if (StartRequest(lpSelf, luIdx) == 0)
                return;
            lpReq->mucState = 2;                        // FEEDING

            // codec 3 == 'EXm0'. fcmpu + bne: NaN takes the NOT-taken (skip) path, which
            // is exactly what `== 0.0` does in C++ -- no negation needed here.
            if (lExt.mucCodec == 3 &&
                lpReq->mdStartTime == 0.0 &&
                luIdx == lpSelf->mucCurrentRequestIndex)
            {
                lpReq->mdStartTime = lpSelf->GetSystem()->mfSystemTime + kOneMixChunkSeconds;
            }
        }

        bool lbAdvance = true;
        if (lpReq->mucState == 2 /*FEEDING*/ &&
            lpSelf->Feed(lpSelf->mucNextFeedSlotToFill).mucState == 0)
        {
            if (lExt.miSamplesFed == lpReq->miLoopStart)
            {
                if (HandleLoopStart(lpSelf, luIdx) == 0) return;
                continue;                               // same request again
            }
            if (lExt.miSamplesFed == lpReq->miNumSamples)
            {
                u8 lucFinished = 0;
                if (HandleSampleEnd(lpSelf, luIdx, &lucFinished) == 0) return;
                if (lucFinished == 0) continue;         // same request again
                lpReq->mucState = 3;                    // stream complete
            }
            else
            {
                if (StreamNextChunk(lpSelf, luIdx, 0, 0) == 0) return;
                continue;                               // same request again
            }
        }
        (void)lbAdvance;

        luIndex = (luIdx + 1u) % lpSelf->mucMaxRequests;
        if (luIndex == lpSelf->mucCurrentRequestIndex)
            return;                                     // wrapped back to the head
        lpReq = &lpSelf->Req(luIndex);
    }
}
```

### `rw::audio::core::SndPlayer1::FeedCleanup` @ `0x82BA0268`  [DECODED]

**Signature**

```cpp
static void FeedCleanup(SndPlayer1 *apSelf);  // r3 only; IDA's `int result` is r3 unchanged
```

**Behaviour**

r30 = self, r29 = 0, r31 = the current feed record.

The walk is a do/while over the RELEASE cursor, bounded by the CONSUME cursor:
   if (self->mucFeedReleaseCursor (lbz +0x1CF) == self->mucFeedConsumeCursor (lbz +0x1CE)) return;
   do {
       slot = self->mucFeedReleaseCursor;
       feed = self + 0x5C + 16*slot;                       // rotlwi r11,r11,4 ; addi r31,r11,0x5C
       if (feed->mucState (+0x0D) == 2 /*CONSUMED*/) {
           reqIdx = feed->mucRequestIndex (+0x0E)
           handle = feed->mucDecoderRequestHandle (+0x0C)
           dec    = Req(reqIdx)->mpDecoder (+0x08)
           // --- an INLINED Decoder::GetSamplesRemaining(dec, handle) ---
           rec = dec + dec->muRequestQueueOffset (lwz +0x24) + 0x14*handle
           total = rec->miEndSample (lwz +0x0C)
           if (total != 0) {
               cursor = (handle == dec->mucRequestDecodeIndex (lbz +0x31))
                          ? dec->miCurrentSampleOffset (lwz +0x1C)
                          : rec->miStartSample (lwz +0x08);
               if (total - cursor != 0) goto advance;      // the decoder still owes samples
           }
           // --- release ---
           chunk = feed->mpChunkInfo (lwz +0x00)
           feed->mucState = 0 /*FREE*/                     // stored BEFORE the null test
           if (chunk != 0) {
               ext = self->mpRequestExternal + 0x50*reqIdx
               ext->miBytesBuffered (+0x18) -= chunk->muSize (lwz +0x04)
               if (feed->mpStream (+0x04) != 0)
                   rw::core::filesys::Stream::ReleaseChunk(feed->mpStream, chunk)   // @0x82BC09C8
               feed->mpChunkInfo = 0
           }
       }
   advance:
       n = (self->mucFeedReleaseCursor + 1) & 0xFF;
       if (n == 0x14) n = 0;                               // 20 feed slots
       self->mucFeedReleaseCursor = n;
   } while (n != self->mucFeedConsumeCursor);

The inlined probe is byte-for-byte the body of Decoder::GetSamplesRemaining @0x826914D0 (which returns 0 for an empty slot, so the whole test collapses to `GetSamplesRemaining(dec, handle) == 0`).

**Constants**

None in rodata. Immediates: the feed-ring modulus 0x14 == 20 (0x82BA0358), the decoder request-record stride 0x14 == 20 (`mulli r10, r9, 0x14` @0x82BA02C4), feed state 2 (CONSUMED) and 0 (FREE).

**Host hazards**

* ⚠️ CORRECTION TO THE PRIOR REPORT (section 2). It lists `+0x1CE` as "next feed slot to free" and `+0x1CF` as "ARTIST-only/unknown byte; no semantic reader was found". FeedCleanup IS that reader: +0x1CF is the feed RELEASE cursor (read and written at 0x82BA0278/0x82BA028C/0x82BA034C/0x82BA0364) and +0x1CE is its bound. A whole-class scan confirms the three-cursor pipeline: +0x1CD is the WRITE cursor (GetFeedSlot only), +0x1CE the CONSUME cursor (Process only -- it flips feed state 1->2 at 0x82BA0A6C and advances the cursor at 0x82BA0A8C with the same wrap-at-20), +0x1CF the RELEASE cursor (FeedCleanup only). Rename accordingly.
* ASYMMETRIC RESET: StopHandler zeroes +0x1CD and +0x1CE (0x82BA455C/0x82BA4560) but NOT +0x1CF; only CreateInstance zeroes it (0x82BA6DCC). That is deliberate -- after a stop, FeedCleanup walks the release cursor forward (wrapping) until it reaches the freshly-zeroed consume cursor, draining every outstanding slot. Do not "fix" the asymmetry.
* ⚠️ CONSOLE DECODER-RING STRIDE: `mulli r10, r9, 0x14` indexes DecoderRequest at 20 bytes. Per the SubmitChunk finding, DecoderRequest::muReserved04 actually carries a POINTER (the seek-data blob), so 20 is NOT the host size. The sketch calls Decoder::GetSamplesRemaining by name specifically so this literal never reaches the host.
* feed->mucState is set to 0 BEFORE the chunk null test, so a state-2 slot with a null chunk is still freed. Preserve the order.
* CONSOLE FEED STRIDE: `rotlwi r11,r11,4` + `addi r31,r11,0x5C`. The record holds two pointers (mpChunkInfo, mpStream) -- index a typed array.
* miBytesBuffered is charged in StreamNextChunk (chunk->muSize, added even when the slot reservation then fails) and discharged here -- the failure path in StreamNextChunk therefore leaks both the chunk and its byte charge permanently. Documented at StreamNextChunk; noted here because this is the only discharge site.
* No floating point; no NaN polarity.
* Requires no unhomed API: rw::core::filesys::Stream::ReleaseChunk(Chunk*) and Chunk::muSize are both in the committed stream.h.

**Implementation sketch**

```cpp
void SndPlayer1::FeedCleanup(SndPlayer1 *apSelf)
{
    if (apSelf->mucFeedReleaseCursor == apSelf->mucFeedConsumeCursor)
        return;

    do
    {
        SndPlayer1FeedDesc &lFeed = apSelf->Feed(apSelf->mucFeedReleaseCursor);

        if (lFeed.mucState == 2 /*CONSUMED*/)
        {
            Decoder *lpDec = apSelf->Req(lFeed.mucRequestIndex).mpDecoder;

            // The console inlines GetSamplesRemaining here; call it by name so the
            // DecoderRequest ring is indexed with the HOST sizeof, never the 0x14 literal.
            if (Decoder::GetSamplesRemaining(lpDec, lFeed.mucDecoderRequestHandle) == 0)
            {
                rw::core::filesys::Chunk *lpChunk = lFeed.mpChunkInfo;
                lFeed.mucState = 0;                       // FREE (before the null test)
                if (lpChunk != 0)
                {
                    apSelf->Ext(lFeed.mucRequestIndex).miBytesBuffered -= (s32)lpChunk->muSize;
                    if (lFeed.mpStream != 0)
                        lFeed.mpStream->ReleaseChunk(lpChunk);
                    lFeed.mpChunkInfo = 0;
                }
            }
        }

        u32 luNext = (u32)((apSelf->mucFeedReleaseCursor + 1) & 0xFF);
        if (luNext == kMaxFeeds) luNext = 0;              // kMaxFeeds == 20
        apSelf->mucFeedReleaseCursor = (u8)luNext;
    }
    while (apSelf->mucFeedReleaseCursor != apSelf->mucFeedConsumeCursor);
}
```

### `rw::audio::core::SndPlayer1::GetFeedSlot` @ `0x82BA0380`  [DECODED]

**Signature**

```cpp
static u8 GetFeedSlot(SndPlayer1 *apSelf, u32 *apuOutSlot);  // r3, r4. Returns 1 on success / 0 when the slot is busy; *apuOutSlot is written ONLY on success, and with a full 32-bit stw
```

**Behaviour**

Leaf, no frame, 19 instructions.

    r11 = self
    slot = self->mucNextFeedSlotToFill (lbz +0x1CD)
    if (*(u8*)(self + 0x69 + 16*slot) != 0)          // feed[slot].mucState, via rotlwi r9,r10,4
        return 0;                                     // (loc_82BA03C4: li r3,0 ; blr)
    *apuOutSlot = slot;                               // stw r10, 0(r4)  -- FULL 32-BIT STORE
    n = (self->mucNextFeedSlotToFill + 1) & 0xFF;     // re-read from +0x1CD, not reused
    if (n == 0x14) n = 0;                             // 20 slots
    self->mucNextFeedSlotToFill = (u8)n;
    return 1;

The slot is handed out WITHOUT marking it busy -- the caller's SubmitChunk is what sets feed[slot].mucState = 1. Between GetFeedSlot returning and SubmitChunk running, the ring's write cursor has already advanced past a still-FREE slot; every caller closes that window by calling SubmitChunk immediately (StartRequest, StreamNextChunk, HandleLoopStart, HandleSampleEnd all do).

**Constants**

None in rodata. Immediates: 0x14 == 20 (the feed-ring modulus), the feed record stride 16 (`rotlwi r9, r10, 4`) and the feed array base displacement 0x69 (== self+0x5C for feed[0] plus the record's +0x0D state field).

**Host hazards**

* THE OUT-PARAMETER IS 32 BITS, not a byte: `stw r10, 0(r4)`. Every caller reserves a 4-byte stack slot and reads it back with `lwz`, then narrows to a byte only when storing into ext->mucLatestFeedSlot. Declaring the host parameter `u8*` would corrupt three bytes of the caller's frame. Keep `u32*`.
* THE RETURN IS IGNORED at three of the four call sites (StartRequest's resident arm, HandleLoopStart, HandleSampleEnd). Only StreamNextChunk tests it -- and even there it tests AFTER charging chunk bytes. The safety net is RwacTimerClient's own `feed[mucNextFeedSlotToFill].mucState == 0` pre-checks. Reproduce the ignores; do not add defensive tests.
* THE SLOT IS NOT MARKED BUSY HERE. The write cursor advances past a FREE slot, so a second GetFeedSlot before the matching SubmitChunk would hand out a different (also free) slot and the first would never be claimed. No console path does that.
* CONSOLE FEED STRIDE 16 and base +0x5C/+0x69: the record contains mpChunkInfo and mpStream (both pointers), so neither literal survives x64 -- index a typed array.
* `rotlwi r9, r10, 4` is a multiply-by-16 only because the slot byte is < 2^28; do not port it as a rotate.
* No floating point.

**Implementation sketch**

```cpp
static const u32 kMaxFeeds = 20;   // the 0x14 wrap shared by GetFeedSlot / Process / FeedCleanup

u8 SndPlayer1::GetFeedSlot(SndPlayer1 *apSelf, u32 *apuOutSlot)
{
    const u32 luSlot = apSelf->mucNextFeedSlotToFill;
    if (apSelf->Feed(luSlot).mucState != 0)
        return 0;                        // slot still busy -- caller must back off

    *apuOutSlot = luSlot;                // 32-bit out-parameter, faithful to the stw

    u32 luNext = (apSelf->mucNextFeedSlotToFill + 1u) & 0xFFu;
    if (luNext == kMaxFeeds) luNext = 0;
    apSelf->mucNextFeedSlotToFill = (u8)luNext;
    return 1;
}
```

### `rw::audio::core::SndPlayer1::RequestCleanup` @ `0x82BA4080`  [DECODED]

**Signature**

```cpp
static void RequestCleanup(SndPlayer1 *apSelf);  // r3 only; IDA's `int result` is r3 unchanged
```

**Behaviour**

r31 = self. The body is a test-first while loop (the entry `b loc_82BA40C8` jumps straight to the condition):

    while ( Req(self->mucNextRequestToFree (+0x1C8))->mucState (+0x2A) == 4 /*COMPLETE*/ )
    {
        RemoveRequest(self, self->mucNextRequestToFree);        // @0x82BA0460
        n = (self->mucNextRequestToFree + 1) & 0xFF;            // re-read from +0x1C8
        if (n == self->mucMaxRequests (lbz +0x1CA)) n = 0;
        self->mucNextRequestToFree = (u8)n;
    }

The condition recomputes the record address from scratch every lap: `lbz r11,0x1C8 ; lhz r10,0x1C4 ; mulli r11,r11,0x30 ; add ; add ; lbz r11,0x2A`.

State 4 is the "Process has finished with this request, retire it" marker; RemoveRequest is what returns the record to FREE (0) and calls Voice::ExpelAfterDecay when the expel mode says so. RequestCleanup is called from exactly one place: RwacTimerClient, immediately after FeedCleanup.

**Constants**

None. Immediates: request state 4 (COMPLETE) and the `& 0xFF` / compare-against-mucMaxRequests wrap idiom shared with RwacTimerClient and PlayHandler.

**Host hazards**

* CONSOLE STRIDE 0x30 and the +0x1C4 relative base -- RequestInternal carries Decoder* mpDecoder, so index a typed host array.
* THE WRAP MODULUS IS mucMaxRequests (+0x1CA), the low byte of the constructor-parameter float, NOT a constant. If mucMaxRequests were 0 the `n == 0` test never fires and the cursor runs 0..255 through out-of-bounds records -- CreateInstance defaults it to 1 when no constructor param is supplied, so it is never 0 in practice. Reproduce as written.
* The loop has no iteration cap: it terminates only when a request is not in state 4. RemoveRequest must clear the state (it does, via the FREE store) or this spins forever -- do not "harden" it.
* Both cursors are re-read from memory each lap rather than cached; a host port may cache, but the request record address must be recomputed through the typed accessor.
* r3 is never rewritten, so the console "returns" self; no caller reads it. Model void.
* No floating point, no NaN polarity.

**Implementation sketch**

```cpp
void SndPlayer1::RequestCleanup(SndPlayer1 *apSelf)
{
    while (apSelf->Req(apSelf->mucNextRequestToFree).mucState == 4 /*COMPLETE*/)
    {
        RemoveRequest(apSelf, apSelf->mucNextRequestToFree);

        u32 luNext = (u32)((apSelf->mucNextRequestToFree + 1) & 0xFF);
        if (luNext == apSelf->mucMaxRequests) luNext = 0;
        apSelf->mucNextRequestToFree = (u8)luNext;
    }
}
```

### Cluster notes

GROUND TRUTH USED. All twelve dossiers exist under .ida-exports/BURNOUT_X360_ARTIST.XEX/ and the `assembly` field was the sole basis; pseudocode was not used (its argument lists are wrong for at least HandleLoopStart, StreamLostCallback, RequestCleanup and FeedCleanup). Raw XEX (file_off = 0x3000 + vaddr - 0x82000000, big-endian) was used for: the 8-entry codec table at 0x00177578; dbl_82001CA8 at 0x00004CA8; dbl_820B6460 at 0x000B9460; the lis/addi pair that resolves the SndPlayer1ChunkPa... symbol to 0x82BA3FF8 (file 0x00BA6FF8) and that function's full body; Decoder::Feed @0x82B67920 (an exporter gap -- hand-disassembled to confirm the r4..r9 -> DecoderRequest field mapping); and spot-verification of 17 individual instruction words across StartRequest / StreamNextChunk / SubmitChunk / FeedCleanup / GetFeedSlot / RwacTimerClient (all matched the exporter exactly).

FOUR CORRECTIONS / ADDITIONS TO progress/scratch_dossiers/sndplayer1_decode_codex.md (beyond the three the review already found, which I did not inherit):
1. Section 2 (instance layout) mislabels the feed cursors. The real triple is +0x1CD = feed WRITE cursor (GetFeedSlot only), +0x1CE = feed CONSUME cursor (Process only: it flips feed state 1->2 at 0x82BA0A6C then advances at 0x82BA0A8C), +0x1CF = feed RELEASE cursor (FeedCleanup only, 0x82BA0278/0x82BA028C/0x82BA034C/0x82BA0364). Section 2 calls +0x1CE "next feed slot to free" and declares +0x1CF unknown with "no semantic reader was found" -- FeedCleanup is that reader.
2. Section 6 step 5 says SubmitChunk "calls Decoder::Feed and records the returned decoder request handle in feed +0x0C". True, but it omits the SEEK arm: when StartRequest's seek flag is set, SubmitChunk passes iStartSample = RequestInternal::miDecoderSkip, arg5 = RequestExternal::mpSeekData (A POINTER) and arg6 = (u8)RequestExternal::miSeekDataVersion. This directly falsifies two claims in the committed b5-decomp/vendor/renderware/include/rw/audio/core/Decoder.h: that DecoderRequest is pointer-free (so its 20-byte stride survives x64) and that "every committed call site passes 0" for muReserved04/mucFlag11. DecoderRequest must gain `const void *mpSeekData` and every ring index (Feed, GetSamplesRemaining, GetCurrentRequestDesc, EaXmaDec::DecodeEvent) must switch to sizeof(DecoderRequest).
3. Section 8's callee table lists 0x82BA3FF8 nowhere and IDA's truncated name "SndPlayer1ChunkPa" reads like a string. It is a FUNCTION -- the rw::core::filesys chunk-parse callback SndPlayer1 hands to Stream::QueueFile. Its body is decoded in this report (HandleSampleEnd's `constants`). A full byte scan of the XEX finds no "SndPlayer1 Chunk..." literal, confirming it.
4. Section 8 lists 0x82BC09B0 as "unnamed stream request helper". It is a 5-instruction argument-shuffling thunk into rw::core::filesys::Stream::QueueFile @0x82BC04A0 with lpPreOpenHandle hard-wired to 0.

WHAT IS ALREADY HOMED AND MUST BE USED BY NAME (no invention needed): rw::core::filesys::Stream / Chunk / Request / StreamState (b5-decomp/src/SDKs/EATech/rwcore/filesys/stream.h -- GetChunk, GetRequestState, ReleaseChunk, QueueFile and the ChunkParseCallback typedef all match the call sites exactly); rw::audio::core::Decoder / DecoderRequest / DecoderRegistry / BitGetter / SeekTableParser / Voice / TimerHandle / System / PlugIn.

WHAT IS NOT HOMED -- register contracts, not invented APIs:
* DecoderRegistry::DecoderFactory @0x82B6C778 (exporter gap, no dossier). Call site contract: r3 = DecoderRegistry*, r4 = DecoderDesc* handle from GetDecoderHandle, r5 = u8 channel count, r6 = u32 20, r7 = System*; returns Decoder* or null. Add to DecoderRegistry.h flagged as call-site-derived.
* Decoder +0x20, read by StartRequest as the scratch-instance size (falls inside Decoder.h's opaque mPad20[4]). Needs a named u32 member plus an accessor; Process carves align_up(value,128) off the System stack allocator with it.
* rw::audio::core::StreamPool -- NOT present anywhere in the repo. Attested from PlayHandler + AcquireStream @0x82B6BAB0: StreamPool::GetInstance(u32 guid); StreamPool::AcquireStream(pool, f32 priority /*f1*/, StreamLostFn, void *context) returning a 32-byte-stride ENTRY with { +0x08 f32 priority (RwacTimerClient republishes it every tick from Voice::mfPriority), +0x0C the lost-callback, +0x14 rw::core::filesys::Stream*, +0x18 u16 refcount, +0x1A u8 inUse }. RequestExternal +0x20 is the pool, +0x24 the entry, +0x28 the Stream.

TWO OPEN ITEMS THE HOST MUST DECIDE (both flagged BLOCKED-in-place inside the per-function hazards rather than guessed):
A. The attribute width trap. RwacTimerClient stores attributes 1 and 2 with `stfd` (f64) into an 8-byte-stride slot array that PlugIn::GetAttribute @0x82B6A8C8 reads with `lfs` (f32). On BE that returns the double's high word; on x64 LE the same code returns the low word, silently changing GETSAMPLEPOSITION / GETSAMPLELENGTH. The rodata doc at 0x82174b58 proves game code reads them through that f32 path. Attribute names are rodata-confirmed: 0 = ATTRIBUTE_GETCURRENTREQUEST (0x82174b2c), 1 = ATTRIBUTE_GETSAMPLEPOSITION (0x8217921c), 2 = ATTRIBUTE_GETSAMPLELENGTH (0x82178fcc).
B. Asset byte order. SubmitChunk's block header (blockBytes, numSamples) and the SndPlayer1ChunkParse size word are read as native (big-endian) 32-bit values off the asset. Whether the x64 host must byte-swap depends on the SNR/SNS pipeline, which this cluster cannot settle -- routed through a `ReadAssetU32` helper in the sketch rather than assumed.

ONE MORE OBSERVED ODDITY, reported not repaired: SeekTableParser::mPlayerSkip is copied to RequestExternal +0x3C, read only by StartRequest's seek-flag OR, and never reaches RequestInternal +0x1C -- the field Process actually consumes as the player skip, which SetSeekData explicitly zeroes. A whole-class dossier scan for `0x3C(r` finds exactly three sites (two SetSeekData stores, one StartRequest read). Either a console bug or a step in a not-yet-decoded path; do not wire them together.

NONE of the twelve functions is a deferred-command-ring handler, so the "handler return == host sizeof of the record" rule has no application in this cluster. SndPlayer1's ring handlers are PlayHandler @0x82BA41D8, StopHandler @0x82BA44E0 and ModifyStartTimeHandler @0x82BA03D0, all outside this slice.

STATE ENUMS grounded across the cluster -- RequestInternal::mucState: 0 FREE, 1 QUEUED (PlayHandler), 2 FEEDING (RwacTimerClient after StartRequest succeeds -- the only transition), 3 STREAM-COMPLETE (HandleSampleEnd reported finished), 4 COMPLETE/retire (Process; consumed by RequestCleanup). SndPlayer1FeedDesc::mucState: 0 FREE, 1 SUBMITTED (SubmitChunk), 2 CONSUMED (Process), back to 0 (FeedCleanup). Play type (RequestExternal +0x49, the 2-bit header field): 0 RAM, 1 stream, 2 gigastream, 3 unused -- the "stream or gigastream" naming is confirmed verbatim by the rodata doc strings at 0x82175620 and 0x821763f0.
