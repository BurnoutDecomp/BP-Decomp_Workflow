# Phase E — complete the RWAC plug-in registry and light the splice voices

**Status as of 2026-08-29: COMPLETE.** All **25 of 25** registry records are live,
including registration **21** (`SndPlayer1`, `off_82F901C4` 'SnP1') and registration
**24** (`SndPlayer1_CgsStreamMod`, `off_82F2E124` 'JStr'). The SpliceManager now stages
all **64 mono + 24 stereo** voices and prepares both real free stacks.

Completion gates:

- faithfulness lint: PASS, no new findings across every changed file;
- PC executable: 1,996 TUs, link OK, zero warnings and zero errors;
- connected-device 120-second `-skipvideos -nosecure` smoke: XAudio2 opened at 48 kHz, the
  engine's first valid mixed frame reached the device, and the run had zero hard asserts,
  exceptions, RWAC allocation failures, mono/stereo/null voice failures, mastering-voice
  failures, and failure callbacks;
- the historical 436-line total is no longer an exact whole-program baseline: the final
  unattended run emitted 315 lines and stopped at the legal-screen loop, while an earlier
  interacted run continued into the attract/world path and emitted unrelated graphics,
  bundle, and trigger diagnostics. The Phase-E audio markers retain the expected shape
  (one first-valid-frame line and no audio failure markers).
- fresh-eyes review findings were closed against ARTIST `PhysicalDeviceThread` assembly and
  DecFIGS declarations: physical `Open` now returns status 0 independently of its out-handle;
  directory/read/close callbacks preserve the virtual return, returned handle, and out-count;
  close callbacks clear the compound handle; `Handle::DeviceHandle` is opaque `void*` end to end.

This file is the working plan. It supersedes the phase-E section of the session plan for
anything they disagree on, because several of that plan's premises turned out to be wrong —
see **§2 What changed**.

---

## 1. Where each item stands

| Item | State | Blocking on |
|---|---|---|
| **E1** five plug-in callbacks (regs 6/9/14/15/18) | ✅ DONE (earlier session) | — |
| **E2** `SndPlayer1` home | ✅ DONE | — |
| &nbsp;&nbsp;• type + layout + `ComputeLayout` | ✅ | |
| &nbsp;&nbsp;• `GetSize`, `CreateInstance`, `PreProcess`, `WaitForStartTime`, `Declick`, `AdvanceCurrentRequest`, `GetFeedSlot`, `GetPpuTicksEvent` | ✅ | |
| &nbsp;&nbsp;• `Process` @0x82BA0568 | ✅ **NEW** (`45d0c2f4`) | |
| &nbsp;&nbsp;• `Event`/`EventEvent`, `~SndPlayer1`/`ReleaseEvent`, `RwacTimerClient` + ~15 helpers | ✅ | |
| &nbsp;&nbsp;• **registration 21** | ✅ | |
| **E3** SubMix / GainFader / LowPassButterworth (regs 5/11/22) | ✅ DONE (earlier session) | — |
| **E4** game descriptors | ✅ DONE | — |
| &nbsp;&nbsp;• `GinsuPlayer` reg 23, `GainArray` reg 25 | ✅ DONE | |
| &nbsp;&nbsp;• `SndPlayer1_CgsStreamMod` **reg 24** | ✅ | |
| **E5** splice-voice staging (64 mono + 24 stereo) | ✅ DONE | — |
| &nbsp;&nbsp;• `CreateMonoVoice` / `CreateStereoVoice` bodies | ✅ (`65abfff5`) | |
| &nbsp;&nbsp;• the constructor's staging loops + the two `VoicePool::Prepare`s | ✅ | |
| **Support** `rw::audio::core::StreamPool` home | ✅ **NEW** (`a452edb5`) | — |
| **Support** `DecoderRegistry::DecoderFactory` @0x82B6C778 | ✅ DONE | — |

### Commits this session (b5-decomp `dev`)

| Commit | What |
|---|---|
| `bcf8a6d7` | Retract the false "`rw::core::filesys::Stream` is not homed" claim (3 sites) |
| `be48b46f` | The seek-table base is a **pointer** in two records; x64 was truncating it |
| `45d0c2f4` | `SndPlayer1::Process` bodied; record why the pool path is dead |
| `a452edb5` | `rw::audio::core::StreamPool` homed — an empty registry is the faithful port |
| `849afb4d` | Complete `SndPlayer1`/`JStr`, decoder descriptors/factory, and registrations 21/24 |
| `65abfff5` | Stage all 64 mono + 24 stereo splice voices and prepare both free stacks |
| `1850e5b3` | Close the streamed-filesystem ABI, native-width boot fixes, and audio diagnostics |

Parent repo: `d541099f` (five decode dossiers), `be4585f2` (build mount + AcquireStream decode).

---

## 2. What changed — three premises of the original plan were wrong

### 2.1 `rw::core::filesys::Stream` was never missing

The deferral notes claimed SndPlayer1's streaming half needed **two** un-homed surfaces. Only
one was real. `rw::core::filesys::Stream` has been homed all along at
`b5-decomp/src/SDKs/EATech/rwcore/filesys/stream.h`, carrying `QueueFile`, `GetChunk`,
`ReleaseChunk`, `GetRequestState`, `GetState`, the `Chunk` record and the `ChunkParseCallback`
typedef — the exact shapes every console call site uses. The banked decode said so plainly; the
banner written over it did not. That false half roughly doubled the apparent remaining work.

### 2.2 ⭐ `StreamPool`'s registry is NEVER POPULATED — the stream path is dead code

This is the finding that collapsed the rest of the phase.

`StreamPool::GetInstance` @0x82B6BA68 walks an intrusive list off the global at
**`0x83271C7C`**. **No instruction in the entire image ever writes that global.** Verified three
independent ways:

1. Every instruction word with displacement `0x1C7C` — five hits, and only one is real
   (GetInstance's own `lwz` @0x82B6BA6C). The others resolve to `0x820A1C7C` (rodata, via
   `addis r11,r0,0x820A`), to a running pointer in r29, or are data words that merely decode
   like instructions. **There is no `stw` to it anywhere.**
2. The literal `0x83271C7C` appears **zero** times as a data word, so no pointer table hands its
   address to a generic list helper.
3. `0x83271C7C` maps to file offset `0x1274C7C`, past the end of the `0x105B000`-byte image —
   it is **`.bss`**, zero at load. The walk exits down `li r3,0` every time.

Consistently, ARTIST contains no `StreamPool` constructor, no `CreateInstance` and no boot-time
pool creation, even though the Feb-2007 vendor header declares one.

`AcquireStream` @0x82B6BAB0 then dereferences its `this` with **no null guard**
(`lbz r11,0x28(r30)` @0x82B6BAD4), and `SndPlayer1::PlayHandler` passes the pool straight in
while testing only the **result** (@0x82BA431C).

**Therefore SndPlayer1's stream-open path would fault on retail hardware.** It is compiled-in
dead code. The guard is `RequestExternal::playType` (@0x82BA42E4):

```
lbz    r11, 0x49(r31)     ; playType
cmplwi cr6, r11, 1
beq    cr6, streamopen    ; 1 = streamed  -> open
cmplwi cr6, r11, 2
bne    cr6, commit        ; 2 = hybrid    -> open ;  0 = resident -> skip
```

Retail works, so retail only ever hands a `'SnP1'` voice **resident** requests. Real stream
music goes through the `'JStr'` fork and the module's `IStreamProvider` (`off_82FFBA0C`), which
an independent decode confirmed never touches this pool.

**Consequence for the port:** the pool home is **faithful, not defensive**. An empty registry
whose lookup fails is *exact* — it fails for the console's own reason. `GetInstance` is written
as the real list walk over a genuinely empty, writer-less list, **not** as `return 0`.
⚠️ **Do not add a null-pool guard the console lacks.** That would hide a real content divergence
behind silently different behaviour.

### 2.3 The E5 staging spec in the old banner was wrong on three points

Corrected from the assembly (`splice_staging_decoderfactory_codex.md`):

* The stage config's first field is **not** a `const f32*`. It is the generic create-context
  pointer (`VoiceStageConfig::mpContext`, the console `PlugInConfig`'s `void*`
  constructor-parameter slot). Stage 0 points it at a stack `SndPlayer1::ConstructorParams`
  holding one float — the depth of that voice's request ring.
* **Neither pool count is zeroed before staging.** Both voice-building loops finish first
  (mono @0x826C3294–0x826C32AC, stereo @0x826C32C4–0x826C32DC); the mono count is zeroed
  immediately before the mono `Prepare` (@0x826C32E4, call @0x826C32F0), and the stereo count
  only after that, immediately before the stereo `Prepare` (@0x826C32FC, call @0x826C3304).
* The retail counts **64 mono / 24 stereo** are hard-coded in
  `CgsSound::Playback::SplicerFactory::SplicerFactory` (`r5=0x40` @0x826DB0B4, `r6=0x18`
  @0x826DB0B0) — they do **not** come from `SplicerFactorySpec`.

Also confirmed: `flt_82001C98` == `1.0f` and `flt_82001D9C` == `2.0f`, re-read from rodata at
file `0x4C98` / `0x4D9C`.

---

## 3. Remaining work — `SndPlayer1` (E2), the critical path

### 3.1 The bodies still to land

Spec: `progress/scratch_dossiers/sndplayer1_streaming_verify_codex.md` §2 (implementation-ready
faithful C++ for every one). Fuller decode: `sndplayer1_bodies_decode.md`.

| Function | Address | Notes |
|---|---|---|
| `Event` / EventEvent (vt[1]) | 0x82BA5C48 | six events: PLAY(0) / STOP(1) / ISREQUESTDONE(2) / GETREQUESTBUFFERED(3) / MODIFYSTARTTIME(4) / PLAY1(5); other ids are no-ops. Exporter gap — hand-disassembled. |
| `~SndPlayer1` / ReleaseEvent (vt[0]) | 0x82BA4178 | `StreamLostCallback(this)` first and unconditionally; `RemoveTimer` only when `mbTimerAdded == 1`; `System::Free(mpRequestHandle)`. Clears no fields. |
| `RwacTimerClient` | 0x82BA6980 | the per-frame pump |
| `PlayHandler` | 0x82BA41D8 | |
| `StopHandler` | 0x82BA44E0 | |
| `ModifyStartTimeHandler` | 0x82BA03D0 | |
| `StartRequest` | 0x82BA6438 | |
| `SubmitChunk` | 0x82BA4570 | |
| `StreamNextChunk` | 0x82BA6080 | |
| `HandleLoopStart` | 0x82BA6160 | |
| `HandleSampleEnd` | 0x82BA6248 | |
| `SetSeekData` | 0x82B9C068 | |
| `StreamLostCallback` | 0x82BA4100 | |
| `FeedCleanup` | 0x82BA0268 | |
| `RequestCleanup` | 0x82BA4080 | |
| `RemoveRequest` | 0x82BA0460 | |
| `ChunkParsed` | 0x82BA3FF8 | the `rw::core::filesys` chunk-parse callback handed to `QueueFile`. IDA's truncated name reads like a string; it is a function. |
| `` `vector deleting destructor' `` | 0x82B9EAF8 | vt[3]; compiler-generated on host |

Supporting thunk: **`0x82BC09B0` is not a function** — it is a five-instruction argument-shuffling
thunk into `Stream::QueueFile` @0x82BC04A0 (`mr r8,r7; mr r7,r6; mr r6,r5; li r5,0; b …`) that
injects a **null pre-open handle** in the third slot. Calling `QueueFile` with the caller's
arguments unshifted is wrong.

### 3.2 Required type fixes (from the verification)

1. `RequestExternal::streamHandle` → `StreamPool::StreamHandle`.
2. `RequestExternal::pRwCoreStream` → `rw::core::filesys::Stream *`.
3. The two `SndPlayer1FeedDesc` pointers → `rw::core::filesys::Chunk *` / `Stream *`.
4. `Decoder` +0x20 wants a named `u32 muInstanceSize` (or an accessor).

⚠️ `StreamPool::StreamDesc` is **private**. The spec's `external.streamHandle->mfPriority = …`
must become `SetStreamPriority(handle, …)`; use `GetRwCoreStream(handle)` for the stream.

### 3.3 Already fixed this session (do not re-derive)

`DecoderRequest::muReserved04` → `const u8 *mpSeekData`, and `RequestExternal::mSeekBlockA`
→ `u8 *pSeekData`. The full chain, verified instruction by instruction:

```
SeekTableParser::mpSeekData          (u8*; PDB types it void*)
  -> SetSeekData   lwz r11,0x50(r1) / stw r11,0x38(r31)   @0x82B9C0E0  -> RequestExternal +0x38
  -> SubmitChunk   lwz r8,0x38(r29)                       @0x82BA464C  -> Feed argument 5
  -> Decoder::Feed stw r8,4(r30)                          @0x82B67964  -> DecoderRequest +0x04
```

`EaXmaDec_wG_04` was **already dereferencing** it, laundering a `u32` back through
`static_cast<usize>`, so a real 64-bit pointer was being truncated. `sizeof(DecoderRequest)` is
now **32**, not 20 or 24.

`SetSeekData`'s remaining field mapping (all from its store block @0x82B9C068):
`+0x3C mPlayerSkip`, `+0x40 mChunkOffset`, `+0x44 mSeekDataVersion`, `+0x4C mIsNewFeedChunk`
(renamed from `mNoSeekTable`; `SubmitChunk` passes `continue = !mIsNewFeedChunk`). The parser's
`mStreamSkip`/`mDecoderSkip` go to the **RequestInternal** (+0x24 / +0x20) instead.
⚠️ Its reset path is **asymmetric** — it leaves `mSeekDataVersion` and `numSamplesFed` stale
(@0x82B9C108–0x82B9C128). Console behaviour; do not "tidy" it.

---

## 4. Remaining work — E5, the splice-voice staging

**Hard precondition: registration 21 must be live first.** `Voice::CreateInstance` dereferences
the descriptor a handle resolves to on its first sizing pass (`lwz` config+0x04 @0x82B6EC98, then
the GetSize hook at descriptor+0x04 @0x82B6ECA0, called @0x82B6ECA8). A null handle therefore
**faults** — it does not return null. Staging against an unregistered `'SnP1'` crashes.

Of the four tags the staging needs, three are already live: `'Rsp0'` (reg 18), `'Pn21'` (reg 14),
`'Sen0'` (reg 20). Only `'SnP1'` is missing. *(The old banner claiming `Rsp0`/`Pn21` were also
unregistered is stale.)*

### The chains (confirmed instruction by instruction)

```
mono   (4 stages, @0x826A3318):  {&ConstructorParams{1.0f}, 'SnP1', 1}
                                 {0,                        'Rsp0', 1}
                                 {0,                        'Pn21', 6}
                                 {0,                        'Sen0', 6}
stereo (3 stages, @0x826A33EC):  {&ConstructorParams{2.0f}, 'SnP1', 2}
                                 {0,                        'Rsp0', 2}
                                 {0,                        'Sen0', 2}      <- no panner stage
```

The trailing number is the stage's **output** channel count, and `Voice::CreateInstance` threads
it: input starts at 0 and each stage's output byte becomes the next stage's input
(@0x82B6ED5C, @0x82B6EDFC–0x82B6EE14, @0x82B6EE4C). Mono walks 0→1, 1→1, 1→6, 6→6; stereo
0→2, 2→2, 2→2.

`VoicePluginPair` is `{Voice* mpVoice; PlugIn** mppPlugIn;}` — console `sizeof` **8**, host **16**.
⚠️ The console loops advance the pair by the literal 8 (@0x826C32A4, @0x826C32D4); the host must
index a typed array. `mppPlugIn` points at stage 0 of the voice's **inline** plug-in pointer
array (written inside `Voice::CreateInstance` @0x82B6EE64), not at a separate allocation.

### Constructor order (corrected)

1. mono loop ×`auMonoVoiceCount` → `CreateMonoVoice(&monoPairs[i])`
2. stereo loop ×`auStereoVoiceCount` → `CreateStereoVoice(&stereoPairs[i])`
3. `mMonoVoicePool.muPooledVoiceCount = 0;` then `mMonoVoicePool.Prepare(monoPairs, count)`
4. `mStereoVoicePool.muPooledVoiceCount = 0;` then `mStereoVoicePool.Prepare(stereoPairs, count)`

`VoicePool::Prepare` @0x8268AC40 is already bodied; it stores count and `count-1`
(@0x8268AD34, @0x8268AD40). The current parked state (`miPooledVoiceStackFreeIndex = -1`,
counts discarded) **must disappear** when the staging lands.

**Boot proof for E5:** 88 real voices in the pools and zero failure callbacks
("failed to create mono voice" / "Failed to create stereo voice" — note the shipped capital F
on the stereo string).

---

## 5. Remaining work — registration 24 (`SndPlayer1_CgsStreamMod`)

Decode report: `progress/scratch_dossiers/streammod_streaming_decode_codex.md`.

**Blocker verdict (established):** this fork has **no `StreamPool` dependency**. It opens through
`off_82FFBA0C` / `IStreamProvider` (@0x826A447C–0x826A4498 and @0x826A465C–0x826A4674) and then
reaches `StreamDeviceDiskRead::Read`/`Seek` directly. Remaining gaps named by the decode:
the `ReadStream` forwarding bodies and `DecoderRegistry::DecoderFactory`.

Console addresses: `GetSize` @0x826A4210, `CreateInstance` @0x826EA508, `PreProcess` @0x8268CD10,
`Process` @0x826A46B0.

⚠️ **The twins are genuinely different types.** Nothing may be copied between them without
re-attestation:

| | `'SnP1'` | `'JStr'` |
|---|---|---|
| feed record | console 0x10, **two pointers** | console 0x0C, **pointer-free** |
| `mu8NumEvents` | **6** | **5** |
| stream transport | `StreamPool` (dead) | `IStreamProvider` (live) |

The five-vs-six event count is from the recovered descriptor records
(`snp1_jstr_descriptor_records.md`) and is an independent check on whichever of the parent's six
events the fork's decode finds missing.

---

## 6. `DecoderRegistry::DecoderFactory` @0x82B6C778

An exporter gap (no dossier — hand-disassembled at file `0x00B6F778`). Decoded in
`splice_staging_decoderfactory_codex.md`; **not yet bodied**.

⚠️ It allocates the decoder's inline request ring with the console literal
`mulli r21, r26, 0x14`. The host record is now **32 bytes**, so that literal is wrong by twelve
bytes per slot. **The host must size the ring with `sizeof(DecoderRequest)`.**

⚠️ It dereferences its descriptor argument unconditionally (`r30=r4` @0x82B6C784, then
`lwz r11,0(r30)` @0x82B6C798) — a null descriptor faults before any result exists.
`StartRequest`'s later result-null test does **not** protect against this.

---

## 7. Hazard catalogue — every one of these has already cost this project real bugs

1. **A console size literal that places a variable-length tail.** On x64 the object is larger, so
   the tail lands *inside* it. **Hit six times this wave** (Resample, GinsuPlayer, SubMix, the
   stream mod, SndPlayer1, StreamPool). The fix is always **one shared host `ComputeLayout`
   helper used by BOTH the size query and the placement**, so they cannot disagree.
2. **Record strides.** `mulli 0x30` (RequestInternal), `mulli 0x50` (RequestExternal),
   `rotlwi rN,rM,4` / `clrlslwi rN,rM,24,4` (FeedDesc 0x10), `mulli 0x14` (DecoderRequest),
   `0x20` (StreamDesc), `8` (VoicePluginPair), `0x2C` (StreamPool list-link). **Every one of
   these records holds pointers, so none is a valid x64 stride.** Index typed arrays; recover
   container owners with `offsetof`.
3. **`lbz rN, 8(config)` must become a named member.** On x64 the raw +8 lands inside the widened
   `mpDesc`. This exact mis-read produced the phase-D mixer-scribble crash.
4. **NaN polarity.** `fcmpu` + `bge`/`ble`/`blt`: the unordered case takes the **not-taken** path.
   Write the negated ordered predicate `!(x < y)`, never `x >= y`.
5. **`fctidz`/`fctiwz` + `stfiwx` are not C++ casts.** They are saturating truncates whose low
   bits are stored: NaN → 0 or the `INT64_MIN` pattern, huge → `0xFFFFFFFF`/`INT64_MAX`, where an
   x64 cast gives `INT_MIN` for both. `fctiwz` yields PPC's integer-indefinite `0x80000000`.
   Use explicit conversion helpers.
6. **Hex-Rays invents trailing parameters** when a callee's float arguments occupy ABI slots
   2..4 (integers then land in r7..r9). Already produced two wrong signatures here.
7. **Deferred-command records.** The producer's cursor advance and the handler's **return** must
   both be the host `sizeof`, never the console literal. The variable-length Play record stamps
   its own `u16` size and its handler returns that stamped value.
8. **`& 0xFFF8` in pseudocode** is a 16-bit truncation artifact, not an alignment mask.
9. **Never register a placeholder descriptor.** `RegisterPlugInRunTime` writes the link field
   ~40 bytes into the record (`mpNext` at +0x24), so a short record scribbles past its end —
   measured global corruption. A descriptor goes live only when *every* slot it publishes points
   at a real bodied function.

---

## 8. Verification protocol (every batch)

1. Per-TU gate from the repo root, via PowerShell:
   `& .\tools\_gate_one.bat "<abs path>.cpp"` — passes when `%TEMP%\gate_<name>.obj` exists.
   **Delete the obj first** so the check is real.
2. `py tools/work/faithfulness_lint.py --files <changed files>` — must report
   `NEW findings (not in baseline): none`.
3. `.\build.cmd exe` — expect ~1991 TUs, link ok, **zero** warnings.
4. Boot smoke: `Burnout_PC.exe -skipvideos`, ~90 s. Healthy baseline is **436 log lines**, the
   single known `[UI-gate] PARK: HudMessageDirector::Construct` line, zero exceptions, and
   `[Audio] engine fill: first VALID mixed frame reached the device`.
5. Commit per slice with `git commit -F <file>`; push `b5-decomp` `dev`. The parent pointer is
   bumped by a reconcile bot — push parent `main` only for `progress/` and build-mount changes.

### Environment traps that will waste your time

* **The process is named `Burnout_PC`, not `BrnGame`.** The log is `BrnGame.log`, which is what
  makes this easy to get wrong. `Stop-Process -Name BrnGame` matches nothing, exits 0, and the
  usual stop-check then *confirms a lie*; the next link dies `LNK1104`. Stop by `-Id` from
  `Start-Process -PassThru`, or by `-Name Burnout_PC`.
* **A disconnected RDP session invalidates every boot.** `query session` showing the user's
  session as `Disc` means D3D9 **and** XAudio2 are gone. The log shows
  `[device] Start: … NO DEVICE this run` and then `[Audio] CreateMasteringVoice failed --
  running muted` every frame (≈1825 lines instead of 436). **The engine-fill line can never
  appear**, so the run is worthless as an audio regression signal. Triage any audio boot by
  grepping `CreateMasteringVoice failed` first.
* **Other sessions land submodule commits ahead of their parent build mounts.** This produced
  three unrelated `LNK2019` breaks in one session (`ArbStateCrashing`,
  `PhysicalTrafficManager`, `TrafficEntityModule`). If the link fails on a symbol you did not
  touch, run `git pull --rebase --autostash origin main` in the parent before investigating.

---

## 9. Deliberate non-goals for phase E

* **`rw::core::filesys` stays unmounted.** `stream.cpp` was mounted and backed out: it links only
  one symbol StreamPool wants (`Stream::Kill`) and immediately exposes
  `Stream::startnextrequest`, which its own header records as owned by a not-yet-homed TU.
  `rw::core::filesys` is also a documented PC simplification here — the PC's real async I/O is
  the DeviceManager engine. Mounting it is a **phase-F stream-content decision**, not a link fix.
  The one affected call carries a `DELETE-WHEN` at its site in `StreamPool.cpp`.
* Phases **F** (sound content loading) and **G** (retiring the PC stand-in leaves:
  `MenuMusicPC`, `CgsGuiSoundPC`, `SpeechAudioPC`, the movie-audio leaf) are out of scope here.

---

## 10. Definition of done

1. `CgsGenericRwacFactory.cpp` shows **25 live `CGS_RWAC_REGISTER` calls**, none commented.
2. The SpliceManager constructor stages **64 mono + 24 stereo** voices and both pools report
   their real counts with free stacks seeded at `count - 1`.
3. A `-skipvideos` boot on a **connected** session reaches the engine-fill indicator with the
   historical baseline marker shape (the total line count now varies with UI progression), zero
   new hard asserts, and zero voice-creation failure callbacks.
4. No FLAG in the phase-E surface without a stated reason and a `DELETE-WHEN`.
