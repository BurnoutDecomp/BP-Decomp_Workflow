# BrnGameModule::DoUpdate_Sound @0x823DCEC0 — implementation-grade decode

Decoded 2026-08-28 from `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x823DCEC0.json` (121 instrs,
`assembly` authoritative). Extends `progress/scratch_dossiers/spine_sound_leg_0x823F22D8.md`
appendix B (all of its claims confirmed below). This is the IN-GAME sound leg of the full
per-frame spine `BrnGameModule::DoUpdate` @0x823F0AF8 — its ONLY caller (single bl,
@0x823F19E8). `gm` = the BrnGameModule singleton (`this`). Frame 0xE0, `__savegprlr_17`.

Companion decode of `BridgeSoundToTraining` @0x823C63C0 in §8 (verified against the PC body).

---

## 1. Signature

IDA's 32-arg prototype is an artifact of assuming the PPC32-SysV arg base (caller sp+8).
The caller's store pattern proves the Xenon convention: stack params live in **8-byte slots
starting at caller sp+0x54** (32-bit values in the slot's first word, u16 via `sth` at
slot+2, u8 via `stb` at slot+3 — DoUpdate's other legs corroborate: Director leg `sth`
@+0x5E = slot2+2, Effects leg `sth`@+0x6E = slot4+2 / `stb`@+0x67 = slot3+3, GUI leg fills
slots 1,5,6,8,9(+2),10). Slots sp+0x58/0x60 are never written anywhere in DoUpdate. So the
real signature is **this + 11 parameters**:

```cpp
void BrnGame::BrnGameModule::DoUpdate_Sound(                       // this = r3 = gm
    CgsModule::IOBufferStack*                  lpInputBufferStack,   // r4  ("stackA", update-INPUT)
    CgsModule::IOBufferStack*                  lpOutputBufferStack,  // r5  ("stackB", update-OUTPUT)
    BrnGameState::GameStateModuleIO::OutputBuffer* lpGameStateOutput,// r6
    BrnWorldIO::UpdateOutputBuffer*            lpWorldOutput,        // r7
    BrnDirector::DirectorIO::OutputBuffer*     lpDirectorOutput,     // r8
    BrnReplays::ReplayIO::OutputBuffer_PreSim* lpReplaysPreSimOutput,// r9
    BrnSound::Module::Io::RootOutputBuffer*    lpSoundOutput,        // r10 (rootOut)
    CgsGui::CgsGuiModuleIO::OutputBuffer*      lpGuiOutput,          // stack slot 9  (sp+0x54, callee arg_54 -> r22)
    BrnEffects::EffectsIO::OutputBuffer*       lpEffectsOutput,      // stack slot 10 (sp+0x5C, callee arg_5C -> r21)
    BrnUpdateSet                               leUpdateSet);         // stack slot 11 u16 (sp+0x64, callee lhz arg_66 -> r20)
```

Return: void (IDA's `_DWORD*` is the DestroyIOBuffer/EndAssert r3 falling out of the epilog).
Callee-saved aliases: r31=this, r25=stackA, r19=stackB, r29=gsOut, r28=worldOut,
r27=directorOut, r26=replaysPreSimOut, r18=rootOut, r22=guiOut, r21=effectsOut,
r20=updateSet, r30=self-carved RootInputBuffer.

**Appendix B confirmations**: `lhz arg_66` IS the updateSet (passed by value as the 11th
param, a u16 in a stack slot); the two IOBufferStacks come in as r4/r5; every "buffer"
after that is a single concrete IO buffer, not a stack.

## 2. Perfmon brackets

* @0x823DCEF0/0x823DCEF8 `PerfMonCpu::StartMonitor(*(s32*)(gm+0x996F34))` — **miUT_Sound**
  (r24 = gm+0x996F34, handle loaded by value).
* @0x823DCF04/0x823DCF08 `StartMonitor(*(s32*)(gm+0x996FB4))` — **miUT_SoundUpdate** (r23).
* Stops in reverse: @0x823DD058/5C miUT_SoundUpdate, @0x823DD060/64 miUT_Sound.
* Bracket covers the RootInputBuffer create + all bridges + RootSoundModule::Update, but
  **NOT the DestroyIOBuffer** (destroy is after both Stops). Same pair as DoPreUpdate_Sound
  (spine report §10).

## 3. RootInputBuffer self-carve (CgsModuleIOHelper on-stack helper)

The function carves its own RootInputBuffer per call through the 2-word
`CgsModuleIOHelper.h` helper object at var_90/var_8C (var_90 = mpStack, var_8C = mpBuffer):

* @0x823DCF10 `stw r25, var_90` — helper.mpStack = **stackA (r4 arg, the update-INPUT
  stack `*(gm+0x996F00)` — same stack the loading spine carves its "Sound" input from)**.
* @0x823DCF20 `CreateIOBuffer<BrnSound::Module::Io::RootInputBuffer>(this=stackA,
  &var_8C, "Sound")` → **0x823AD380** (the exact same template instantiation the loading
  spine calls @0x823F23CC).
* On false @0x823DCF38-50: assert `"mpStack->CreateIOBuffer( &mpBuffer, lpcName )"`,
  file `"..\..\..\GameShared\GameClasses\Module/CgsModuleIOHelper.h"`, line **52** (0x34).
* @0x823DCF5C `r30 = var_8C` — the carved buffer, live to the end.
* Destroyed @0x823DD070 `DestroyIOBuffer<RootInputBuffer>(r3=var_90 stackA, r4=&var_8C)`
  → 0x823C7918; on false @0x823DD080-98 assert `"mpStack->DestroyIOBuffer( &mpBuffer )"`,
  same header, line **57** (0x39).

## 4. Lock brackets + bridge/install sequence (exact console order)

Two overlapping (NOT nested) lock brackets wrap the whole bridge cluster; **both are fully
released BEFORE RootSoundModule::Update** (Update takes its own locks internally, as on the
loading spine).

**Bracket A — the 6-buffer helper pair** (`sub_823B7620` / `sub_823B7760`, CgsModuleUtils.h
lines 403-408 / 428-433, asserts `lpInputBuffer` + `lpOutputBuffer0..4` non-null):

* @0x823DCF74 `sub_823B7620(r3=rootIn, r4=directorOut, r5=worldOut, r6=gsOut,
  r7=guiOut(r22, stack param 9), r8=replaysPreSimOut)` — performs, in order:
  `LockForWrite(rootIn); LockForRead(directorOut); LockForRead(worldOut);
  LockForRead(gsOut); LockForRead(guiOut); LockForRead(replaysPreSimOut)`.
* @0x823DD004 `sub_823B7760(same six)` — exact reverse:
  `UnlockForRead(replaysPreSimOut); UnlockForRead(guiOut); UnlockForRead(gsOut);
  UnlockForRead(worldOut); UnlockForRead(directorOut); UnlockForWrite(rootIn)`.

**Bracket B — the effects buffer, locked alone and never read**:

* @0x823DCF78/80 `r21 = arg_5C (lpEffectsOutput); LockForRead(effectsOut)` — AFTER the
  helper's locks.
* @0x823DD008/0C `UnlockForRead(effectsOut)` — AFTER the helper's unlocks (so the brackets
  interleave A-open, B-open, A-close, B-close).
* **No bridge or install consumes effectsOut** — it is a lock-only participant (presumably
  a planned/retired effects→sound bridge). A faithful body must keep the lock pair.

**The bridges/installs, all between the locks, ALL UNCONDITIONAL** (the only branches in
the whole function are the two assert checks; updateSet is consumed as *data*, never as a
gate — the loading spine's `meLoadingStage > 5` gates have no counterpart here):

1. @0x823DCF84 `r20 = lhz arg_66` — updateSet materialized.
2. **@0x823DCF98 `BridgeWorldToSound(gm, r4=rootIn, r5=worldOut, r6=updateSet)` →
   0x823CD580** (C3b: r6 feeds the bit-0x100 replay-source select). World output buffer =
   the r7 argument — a per-frame "World" `BrnWorldIO::UpdateOutputBuffer` carved by the
   caller (see §6), NOT a gm member.
3. **@0x823DCFA0 `r3 = DirectorIO::OutputBuffer::GetCameraOutput(directorOut)` →
   0x823B3308**: asserts read-locked (byte0 bit 0x10, `extrwi 1,27`, "Not locked for
   reading", `..\..\..\GameSource\Director/Direct...` line **931**/0x3A3), returns
   **directorOut+0x180** (the camera-output block). The director output buffer is the r8
   argument = **persistent gm member `*(gm+0x9A0BDC)`** (caller loads it there — the slot
   right after the gui-out member).
   @0x823DCFAC `RootInputBuffer::SetCameraInput(rootIn, cam)` → **0x823C9140**: asserts
   WRITE-locked (bit 0x08, `extrwi 1,28`, "Not locked for writing",
   `..\..\..\GameSource\Sound/Module/Br...` line **366**/0x16E), then
   `BrnDirector::Camera::Camera::operator=(rootIn+0x2F20, cam)` — the camera is copied by
   value into **rootIn+0x2F20**.
4. **@0x823DCFBC `BridgeGameStateToSound(gm, r4=rootIn, r5=gsOut)` → 0x823CDE50** — its
   only call site in the binary (spine report §6 confirmed the loading spine never calls
   it). Game-state output buffer = the r6 argument — per-frame "GameState"
   `GameStateModuleIO::OutputBuffer` carved by the caller (§6), not a gm member.
5. **@0x823DCFD4 `BridgeGuiToSound(gm, r4=rootIn, r5=*(gm+0x9A0BD8))` → 0x823C0A58** —
   appendix B CONFIRMED: gui out is reloaded from **member gm+0x9A0BD8** (lis/ori 0x9A0BD8
   + `lwzx` @0x823DCFC0-D0). It is the SAME pointer as stack param 9 (the caller passes
   `*(gm+0x9A0BD8)` there — the body locks the param but re-reads the member for the
   bridge arg; both are one buffer). No separate accessor call — a raw member load.
6. **@0x823DCFDC `r3 = ReplayIO::OutputBuffer_PreSim::GetStatusInterface(replaysPreSimOut)`
   → 0x823BB080** (IDA truncates to `GetStatu`): asserts read-locked ("Not locked for
   reading", `d:\p4\b5_main\burnout\main\code\g...` line **103**/0x67), returns
   **replaysPreSimOut+0x4**. Source buffer = the r9 argument — per-frame "ReplaysPreSim"
   `OutputBuffer_PreSim` carved by the caller (§6).
   @0x823DCFE8 `RootInputBuffer::SetReplayStatusInterface(rootIn, si)` → **0x823B7EC0**:
   asserts write-locked (same Sound/Module header, line **163**/0xA3), then
   `BrnReplays::ReplayIO::StatusInterface::operator=(rootIn+0x4, si)` — copied by value
   into **rootIn+0x4**.

Order is exactly appendix B's: **WorldToSound → SetCameraInput → GameStateToSound →
GuiToSound → SetReplayStatusInterface** (vs the loading spine's GuiToSound-then-
WorldToSound, which also lacks both installs and the gamestate bridge).

## 5. RootSoundModule::Update @0x823DD054 → 0x826FB238

Called with NO locks held. Argument derivation (0x823DD010-50):

| PC arg | reg | derivation |
|--------|-----|------------|
| this | r3 | gm+0x8A7D00 (mSoundModule) |
| f32 gameDt | f1 | GAME timer gm+0x9A0AD4: `[+0x10] mDelta * [+0xC] mScale` (lfs @0x823DD040/44, fmuls @0x823DD050) |
| f32 simDt | f2 | SIM timer gm+0x9A0AF0: `[+0x10] * [+0xC]` (lfs @0x823DD02C/34, fmuls @0x823DD03C) |
| IOBufferStack* | r6 | r25 = **stackA arg (r4)** — update-INPUT stack |
| IOBufferStack* | r7 | r19 = **stackB arg (r5)** — update-OUTPUT stack |
| RootInputBuffer* | r8 | r30 — the self-carved "Sound" buffer (§3) |
| RootOutputBuffer* | r9 | r18 = **rootOut arg (r10)** — the caller's per-frame "Sound" RootOutputBuffer |
| BrnUpdateSet | r10 | r20 = **updateSet stack param 11** (`lhz arg_66`) |

Identical timer products, timers, `this`, and stack order as the loading spine's call
@0x823F2AC8 — cross-confirmed. (Note this leg does NOT run `Timer::Update` itself; the
game timer is updated earlier in DoUpdate's frame, as on the loading spine.)

## 6. After Update / teardown — NO resource forward here

After Update the function only does: StopMonitor x2 (reverse order, §2) then the
DestroyIOBuffer of the self-carved rootIn (§3). **The sound→resource forward (rootOut
2048-queue drain + RequestInterface merge) is the CALLER's job**: DoUpdate keeps rootOut
(r27 = var_B4) live after the call and

* passes it as r8 into `DoUpdate_ReplaysPostSim` (mr @0x823F1A90, bl @0x823F1AB4), and
* drains it in its tail resource cluster (`mr r3,r27` @0x823F1F08 / @0x823F1F24 feeding
  `GameDataIO::InputBuffer` appends incl. `AppendRequestInterface<4096>` @0x823F1F34,
  right after `BridgeGuiToResource` @0x823F1E88) — detail decode belongs to the DoUpdate
  agent.

DoUpdate also owns the rootOut lifecycle: created @0x823F0C98 ("Sound",
`RootOutputBuffer`, off `*(gm+0x996F04)`, slot var_B4), destroyed @0x823F21B4. No
freed-buffer handling exists inside DoUpdate_Sound.

## 7. Caller context — the one bl @0x823F19E8 in DoUpdate @0x823F0AF8

Long-lived caller registers: r25=gm, r14=gm+0x996F04 (&output-stack slot),
r16=gm+0x996F00 (&input-stack slot, via var_118), r28=gm+0x9A0BDC (addis/addi
@0x823F1610/161C), r23=updateSet=`ConstructUpdateSet(gm,...)` result @0x823F13CC
(perfmon-bracketed; refines the frame-top `ConstructUpdateSetFromFsm` @0x823F0B28),
r15=var_114=&gm->guiOut slot (r11=gm+0x9A0BD8 stored @0x823F1248). All verified live —
no redefinition between their defs and the call.

```
0x823F19B0  lwz  r15, var_114(r1)   # &gm(+0x9A0BD8) gui-out member slot
0x823F19B4  mr   r7,  r26           # worldOut   = var_AC  ("World" BrnWorldIO::UpdateOutputBuffer, created @0x823F0C20 off *(gm+0x996F04))
0x823F19B8  lwz  r27, var_B4(r1)    # rootOut    = "Sound" RootOutputBuffer (created @0x823F0C98 off *(gm+0x996F04))
0x823F19BC  mr   r3,  r25           # this = gm
0x823F19C0  lwz  r9,  var_E4(r1)    # replaysPreSimOut = "ReplaysPreSim" OutputBuffer_PreSim (created @0x823F0CD4 off output stack)
0x823F19C4  mr   r10, r27           # rootOut
0x823F19C8  lwz  r8,  0(r28)        # directorOut = *(gm+0x9A0BDC)   PERSISTENT member
0x823F19CC  lwz  r5,  0(r14)        # stackB = *(gm+0x996F04) update-OUTPUT stack
0x823F19D0  lwz  r11, 0(r15)        # guiOut = *(gm+0x9A0BD8)        PERSISTENT member
0x823F19D4  lwz  r6,  var_EC(r1)    # gsOut = "GameState" GameStateModuleIO::OutputBuffer (created @0x823F0BE4 off output stack)
0x823F19D8  lwz  r4,  0(r16)        # stackA = *(gm+0x996F00) update-INPUT stack
0x823F19DC  sth  r23, sp+0x66       # param 11: updateSet u16 (slot sp+0x64)
0x823F19E0  stw  r29, sp+0x5C       # param 10: effectsOut = var_C4 ("Effects" EffectsIO::OutputBuffer, created @0x823F0D4C off output stack; r29 loaded @0x823F16E4)
0x823F19E4  stw  r11, sp+0x54       # param 9:  guiOut
0x823F19E8  bl   BrnGameModule::DoUpdate_Sound
```

The call sits between `DoUpdate_Effects` (@0x823F1910) and `DoUpdate_ReplaysPostSim`
(@0x823F1AB4), separated only by the per-leg `BrnResource::GetAvailableMemory` leak-check
blocks; no conditional skips it. Member cluster note: gm+0x9A0BD0 / +0x9A0BD4 / +0x9A0BD8
/ +0x9A0BDC are a run of persistent buffer-pointer members (the first two feed
DoUpdate_GuiPreWorld/GUI; +0x9A0BD8 = gui out, +0x9A0BDC = director out).

## 8. BridgeSoundToTraining @0x823C63C0 — full decode + PC verdict

54 instrs, `__savegprlr_27`, frame 0x90. Only caller: `DoPreUpdate_Sound` @0x823EE4D8.
Signature: `BridgeSoundToTraining(this=gm r3, RootPreUpdateOutputBuffer* lpSoundOutputBuffer r4)`.

1. @0x823C63D4 `r3 = 0x823B8BB8(lpSoundOutputBuffer)` — `RootPreUpdateOutputBuffer::
   GetPreUpdateOutput()` (asserts read-locked, returns this+0x8; the same address the
   spine report labeled GetGuiEventQueue — identical folded accessor, see
   BrnRootSoundModuleIo.h:117-121 note).
2. @0x823C63D8 `r31 = r3 + 0x2A0` — the **AudioEffectsMessageQueue**
   (`VariableEventQueue<128,16>` at buffer+0x2A8 = PreUpdateOutput block +0x2A0).
3. @0x823C63E8 `r27 = GetFirstEvent(r3=queue, r4=&var_40 lpEvent, r5=&var_3C liEventSize)`
   → 0x8227BFB0. (Internals: asserts constructed; count @queue+0x88, first-record offset
   @+0x8C; record layout: id word @rec+1, size word @rec+5, data @rec+0x11; empty →
   *lpEvent=0, *size=0, returns -1.) Return value = the event id; var_40 = event pointer.
4. @0x823C63F4/F8 if lpEvent == 0, exit.
5. Loop @0x823C6404-30: `cmpwi r27, 2`; if equal @0x823C6410
   `TrainingManager::OnVoiceoverFinished(gm + 0x674B30)` → 0x82359020 — **the manager is
   an EMBEDDED object at gm+0x674B30 (= 6769456): `add r3, r29, r28`, no pointer load**.
   Then @0x823C6424 `GetNextEvent(queue, r4=lpEvent, r5=&var_40, r6=&var_3C)` →
   0x82285E58; reload lpEvent; loop while non-null.
   **Quirk: r27 is assigned ONCE (from GetFirstEvent) — GetNextEvent's returned id is
   discarded, so the id==2 test re-tests the FIRST event's id every iteration.**

**Verdict on the PC body (`b5-decomp/src/GameSource/Game/GameBridgeSoundToX.cpp:39-54`):
FAITHFUL — no new divergence.**

* Queue derivation `GetPreUpdateOutput().GetAudioEffectsMessageQueue()` is byte-equivalent
  (GetPreUpdateOutput = this+0x8 with the read-lock assert, mAudioEffectsMessageQueue @
  block+0x2A0 — both attested in BrnRootSoundModuleIo.h:87/:129/:355 and matching the asm's
  call + `addi 0x2A0`).
* `GetFirstEvent(&lpEvent, &liEventSize)` returning the type, `while (lpEvent)`, the id-2
  constant (`cmpwi` @0x823C6404), and the GetNextEvent arg order all match.
* The first-event-id quirk is reproduced exactly and documented (file comment lines 33-38)
  — correctly NOT "fixed".
* The single mechanical divergence — PC derefs a `mpTrainingManager` POINTER member at
  +6769456 where the console has the manager EMBEDDED there — is a pre-existing, declared
  stand-in (FLAG comment at `BrnGameModule.hpp:986-989`: "real layout embeds it @
  +6769456"). Behavior-identical provided the pointer targets the real manager; nothing to
  change now, resolve when the real layout lands.
* Console "returns" GetNextEvent's last r3; PC `void` — IDA artifact, fine.

## 9. Consolidated ordered call list

```
StartMonitor(*(gm+0x996F34)  miUT_Sound)                          0x823DCEF8
StartMonitor(*(gm+0x996FB4)  miUT_SoundUpdate)                    0x823DCF08
CreateIOBuffer<RootInputBuffer>(stackA, &helper.mpBuffer, "Sound") 0x823DCF20  [+assert h:52]
sub_823B7620: Write(rootIn); Read(directorOut, worldOut, gsOut, guiOut, replaysPreSimOut) 0x823DCF74
LockForRead(effectsOut)                                           0x823DCF80
BridgeWorldToSound(gm, rootIn, worldOut, updateSet)               0x823DCF98
SetCameraInput(rootIn, GetCameraOutput(directorOut)=+0x180) -> rootIn+0x2F20  0x823DCFA0/AC
BridgeGameStateToSound(gm, rootIn, gsOut)                         0x823DCFBC
BridgeGuiToSound(gm, rootIn, *(gm+0x9A0BD8))                      0x823DCFD4
SetReplayStatusInterface(rootIn, GetStatusInterface(replaysPreSimOut)=+0x4) -> rootIn+0x4  0x823DCFDC/E8
sub_823B7760: UnlockRead(replaysPreSim, gui, gs, world, director); UnlockWrite(rootIn) 0x823DD004
UnlockForRead(effectsOut)                                         0x823DD00C
RootSoundModule::Update(gm+0x8A7D00, gameTimer(+0x9A0AD4).dt*scale,
    simTimer(+0x9A0AF0).dt*scale, stackA, stackB, rootIn, rootOut, updateSet)  0x823DD054
StopMonitor(miUT_SoundUpdate); StopMonitor(miUT_Sound)            0x823DD05C/64
DestroyIOBuffer<RootInputBuffer>(stackA, &helper.mpBuffer)        0x823DD070  [+assert h:57]
(no resource forward, no gates, no other calls)
```
