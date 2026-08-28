# SOUND legs of LoadingScriptedState::Update @0x823F22D8 — implementation-grade spec

Decoded 2026-08-28 from `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x823F22D8.json` (631 instrs,
`assembly` authoritative), cross-checked against the C1/C2 notes in
`progress/audio_faithfulness/AUDIT_2026-08-25.md` (all confirmed; extensions marked NEW).
All addresses are X360 ARTIST. `gm` = the BrnGameModule singleton, reloaded per use from
`off_830102D0`. Register constants held across the function:

| reg | value | meaning (PC name) |
|-----|-------|-------------------|
| r16 | hi16 of `dword_82FAE4B0` | `meLoadingStage` static (PC `gBrnScriptedLoadStage`) |
| r30 | hi16 of `off_830102D0` | gm pointer slot |
| r29 | 0x996F00 | gm slot: update-INPUT `IOBufferStack*` (`GetUpdateInputBufferStack()`) |
| r31 | 0x996F04 | gm slot: update-OUTPUT `IOBufferStack*` (`GetUpdateOutputBufferStack()`) |
| r25 | `*(gm+0x996F10)` (lwzx @0x823F2358) | PERSISTENT `GameDataIO::InputBuffer*` (PC `s_GameDataInput`) |
| r20 | `*(gm+0x996F14)` (lwzx @0x823F235C) | PERSISTENT `GameDataIO::OutputBuffer*` (PC `s_GameDataOutput`) |
| r24 | ret of ConstructUpdateSetFromFsm | live `BrnUpdateSet` (u16 semantics) |

Early-out @0x823F22F4-0x823F2304: `if (meLoadingStage == 8)` tail-call
`BrnGameModule::DoUpdate(gm)` and return — the full spine (whose sound leg is
`DoUpdate_Sound` @0x823DCEC0, see appendix B) takes over.

---

## 1. Sound IO buffer creation (inside the 16-buffer batch 0x823F238C–0x823F24FC)

`CgsModule::IOBufferStack::CreateIOBuffer<T>(T** out, const char* name)` — carve + Construct
off the given stack. The sound trio (creation positions 3–5 of 16):

| addr | template type | carved from | name string | stack slot | reg later |
|------|---------------|-------------|-------------|-----------|-----------|
| 0x823F23CC | `BrnSound::Module::Io::RootInputBuffer` | `*(gm+0x996F00)` update-**INPUT** stack | `"Sound"` | var_B8 | **r15** (loaded @0x823F2518, live to teardown) |
| 0x823F23E0 | `BrnSound::Module::Io::RootOutputBuffer` | `*(gm+0x996F04)` update-**OUTPUT** stack | `"Sound"` | var_BC | **r28** (loaded @0x823F2A88) |
| 0x823F23F8 | `BrnSound::Module::Io::RootPreUpdateOutputBuffer` | `*(gm+0x996F04)` update-**OUTPUT** stack | `"SoundRootPreUpdateOutput"` | var_C0 | **r22** (loaded @0x823F2704; r22 is REPURPOSED as the 0x9A0AD4 offset constant from 0x823F28F0 on) |

Raw asm for the RootInputBuffer create (shows the stack selection):

```
0x823F23B4  ori   r29, r11, 0x6F00      # r29 = 0x996F00
0x823F23BC  addi  r26, r11, aSound@l    # "Sound"
0x823F23C0  lwz   r11, off_830102D0@l(r30)
0x823F23C8  lwzx  r3, r11, r29          # this = *(gm+0x996F00)  <- INPUT stack
0x823F23CC  bl    CreateIOBuffer<RootInputBuffer>(&var_B8, "Sound")
0x823F23D0  lwz   r11, off_830102D0@l(r30)
0x823F23DC  lwzx  r3, r11, r31          # this = *(gm+0x996F04)  <- OUTPUT stack
0x823F23E0  bl    CreateIOBuffer<RootOutputBuffer>(&var_BC, "Sound")
```

Sizes (attested elsewhere): `RootOutputBuffer` = 6224 (0x1850, C1 closure);
`RootPreUpdateOutputBuffer` = 824 (C1 carve); `RootInputBuffer` >= 0xEEE0 (C3b abutment) —
use the PC class sizes. NOTE the full 16-buffer batch is NOT strictly in=INPUT/out=OUTPUT:
"Input" OutputBuffer and "NetworkPreSim" PreSimulationInputBuffer both come off the OUTPUT
stack (r31). Stack membership per buffer, in creation order:
Input-out B, GameState-out B, SoundRootIn **A**, SoundRootOut **B**, SoundRootPreUpdateOut
**B**, World-in A, World-out B, GUI-in A, GUI-out B, GUIView-in A, GUIModel-out B,
GameStatePreWorld A, GameStatePostWorld A, GameState-out#2 B, NetworkPreSim B, Network-out B
(A = +0x996F00, B = +0x996F04).

Immediately after the batch: 0x823F2504 `LockForWrite(r25)` (persistent GameData in),
0x823F250C `LockForRead(r20)` (persistent GameData out) — held across the WHOLE spine,
released @0x823F2BC0/0x823F2BC8 (see §9).

## 2. Loading-stage machine — sound-relevant entries (0x823F2510–0x823F26CC)

Gated: skip whole machine if park flag `byte_82FAE28E` != 0 (@0x823F2520-28).
Switch on `meLoadingStage`, cases 0..8, fall-through on success:

* **cases 0/1** @0x823F2574: `meLoadingStage := 1`, `LoadSoundModuleAgain(this, r4=r25 gameDataIn, r5=r20 gameDataOut)` @0x823F2588 (fn 0x823E7700).
* case 2 LoadEffectsModule, case 3 LoadGameState2, case 4 gui-module vcall
  `(*vtbl(gm+0x6EAA20))+0x5C)(gm+0x6EAA20, r25)`, case 5 LoadWorldModule — not sound.
* **case 6** @0x823F2644 — NEW (not in the C1/C2 notes): posts the sound "world load done"
  game event, then jumps the stage straight to 8:

```
0x823F2644  li    r11, 6
0x823F2648  mr    r3, r15                                  # sound RootInputBuffer
0x823F264C  stw   r11, dword_82FAE4B0@l(r16)               # meLoadingStage = 6
0x823F2650  bl    CgsModule::IOBuffer::LockForWrite        # (r15)
0x823F2654  mr    r3, r15
0x823F2658  bl    RootInputBuffer::GetGameEventQueue       # 0x823B8668 -> r15+0x3084
0x823F265C  li    r6, 1                                    # size = 1
0x823F2660  li    r5, 0x129                                # event id = 0x129 (297)
0x823F2664  addi  r4, r1, 0x160+var_F0                     # payload ptr (1 byte, NEVER written!)
0x823F2668  bl    VariableEventQueue<13312,16>::AddEvent   # 0x8233FAE8
0x823F266C  mr    r3, r15
0x823F2670  bl    CgsModule::IOBuffer::UnlockForWrite
0x823F2674  li    r11, 8
0x823F2678  stw   r11, dword_82FAE4B0@l(r16)               # meLoadingStage = 8 (skips case 7)
```

  AddEvent signature `(this=queue, const void* data, u32 id, u32 size)` (same arg pattern as
  the id-0x8F GUI post @0x823F2984-94). The 1-byte payload `var_F0` is an UNINITIALIZED
  stack byte — faithful PC body passes an uninitialized local u8 (the id alone is the
  signal). `RootInputBuffer::GetGameEventQueue` @0x823B8668: asserts byte0 bit 0x08
  (write-locked, `extrwi 1,28`, "Not locked for writing", Sound/Module h line 0x185),
  returns `this+0x3084` = the `VariableEventQueue<13312,16>` game-event queue.
* case 7 (LoadWorldCollision) is NOT reached by fall-through from 6 (6 branches to the
  common exit after setting stage 8).

## 3. Pre-world drives (positions)

* 0x823F26D8 `r24 = BrnGameModule::ConstructUpdateSetFromFsm(gm)` @0x823BD420.
* 0x823F26F4 `r17 = DoUpdate_InputPreWorld(gm, r4=*(gm+0x996F00), r5=*(gm+0x996F04), r6=inputOut var_B0)`.
* **0x823F2714 `DoPreUpdate_Sound(gm, r4=*(gm+0x996F04), r5=r22 preUpdateOut, r6=r27 guiIn)`** — see §4.
  Sits AFTER InputPreWorld, BEFORE network/gamestate/world. NO locks held by the caller.
* 0x823F273C `BrnNetworkModule::ProcessBeforeSimulation(gm+0x8C3600, stackA, stackB, netPreSimIn var_E8, netOut r26=var_EC, r8=r24)`.
* 0x823F2758 BridgeNetworkToGui, 0x823F2788 BridgeGuiToGameState (each wrapped in the
  lock-pair helpers `sub_823B6FE0`/`sub_823B7060`, see §4).
* 0x823F27BC `GameStateModule::PreWorldUpdate(gm+0x669500, stackA, stackB, gsPreWorldIn var_DC, gsOut r23=var_E4, r8=r24)`.
* 0x823F27D8 BridgeGameStateToGui.

## 4. DoPreUpdate_Sound @0x823EE4D8 — FULL body (42 instrs)

Signature: `DoPreUpdate_Sound(BrnGameModule* this, CgsModule::IOBufferStack* lpStack,
BrnSound::Module::Io::RootPreUpdateOutputBuffer* lpPreUpdateOut,
CgsGui::CgsGuiModuleIO::InputBuffer* lpGuiIn)`. The spine passes the update-OUTPUT stack
(`*(gm+0x996F04)`) as `lpStack`; it is only forwarded into `RootSoundModule::PreUpdate`.

Exact console order:

1. @0x823EE500 `PerfMonCpu::StartMonitor(*(s32*)(this+0x996F34))` — **`mCpuMonitors.miUT_Sound`**
   (BrnCpuMonitors embedded at gm+0x996F18; miUT_Sound = +0x1C). Handle is an s32 loaded
   BY VALUE (`lwz r3, 0(r28)`).
2. @0x823EE510 `PerfMonCpu::StartMonitor(*(s32*)(this+0x996FB4))` — **`miUT_SoundUpdate`** (+0x9C).
3. @0x823EE524 `RootSoundModule::PreUpdate(this=gm+0x8A7D00 /*mSoundModule*/, r4=lpStack, r5=lpPreUpdateOut)` → **0x826EB928** (already bodied, C1).
4. @0x823EE530 `sub_823B6FE0(lpGuiIn, lpPreUpdateOut)` — lock-pair helper: asserts non-null
   ("lpInputBuffer" line 0x103 / "lpOutputBuffer0" line 0x104), then
   `LockForWrite(lpGuiIn); LockForRead(lpPreUpdateOut)`.
5. @0x823EE538 `q256 = RootPreUpdateOutputBuffer::GetGuiEventQueue(lpPreUpdateOut)` →
   **0x823B8BB8**: asserts read-locked (byte0 bit 0x10, `extrwi 1,27`, h line 0x24E),
   returns `this+0x8` = the `VariableEventQueue<256,16>` GuiOut (C1's 824-byte carve).
6. @0x823EE544 `q32k = CgsGui::CgsGuiModuleIO::InputBuffer::GetEventQueue(lpGuiIn)` →
   **0x8284F238**: asserts write-locked, returns `this+0x4` = `VariableEventQueue<32768,16>`.
7. @0x823EE54C `q32k->Append<256,16>(*q256)` → **0x823DAF20**.
8. @0x823EE558 **`BridgeSoundToTraining(this, lpPreUpdateOut)` → 0x823C63C0** — NEW, was not
   in the checklist or the C1/C2 notes.
9. @0x823EE564 `sub_823B7060(lpGuiIn, lpPreUpdateOut)` — unlock pair:
   `UnlockForRead(lpPreUpdateOut); UnlockForWrite(lpGuiIn)`.
10. @0x823EE56C StopMonitor(miUT_SoundUpdate); @0x823EE574 StopMonitor(miUT_Sound) — reverse order.

## 5. BridgeSoundToWorld — PRE-world, inside `if (meLoadingStage > 5)` (0x823F27F0–0x823F288C)

Gate @0x823F27F0-F4: `cmpwi meLoadingStage, 5; ble -> skip whole world block`.
(r19 = worldOut var_C8 is loaded @0x823F27EC BEFORE the gate and stays live.)

1. @0x823F27FC `LockForRead(r22 preUpdateOut)`.
2. @0x823F2808 `LockForWrite(r18 worldIn var_C4)`.
3. **@0x823F2818 `BridgeSoundToWorld(gm, r4=worldIn, r5=preUpdateOut)` → 0x823CDC98** (C3a: one append).
4. @0x823F2820 `UnlockForWrite(worldIn)`; @0x823F2828 `UnlockForRead(preUpdateOut)`.
5. THEN the world update, additionally gated on updateSet bits:
   `if (!(r24 & 0x20) && !(r24 & 0x40))` (`clrlwi r11,r24,16` + `rlwinm 0,26,26` /
   `rlwinm 0,25,25` @0x823F282C-44):
   * @0x823F2858 `LinearMalloc::FreeAll(*(gm+0x9A0630))` (world scratch allocator).
   * @0x823F288C world-module virtual `(*(vtbl(gm+0x10E80))+0x4C)(gm+0x10E80, r4=r24
     updateSet, r5=stackA, r6=stackB, r7=worldIn r18, r8=worldOut r19, r9=*(gm+0x9A0630))`
     — THE world update.

**BridgeSoundToWorld therefore runs whenever stage > 5, even on frames where bits 0x20/0x40
suppress the world vcall itself.**

## 6. Post-world sound bridges (after the GUI module vcall @0x823F2A0C)

Between the world block and these: DoUpdate_GuiPreWorld (only if `r24 & 0x20`, with an
Unlock/relock bracket on r25), DoUpdate_InputPostWorld @0x823F28E8,
**`CgsSystem::Timer::Update(gm+0x9A0AD4)` @0x823F28FC** (the GAME timer — the f1 source,
§7), the GuiEventTimeInfo post, gui-out clears, the id-0x8F input-state event,
BridgeGameToGui, BridgeControllerToGui, then the GUI module virtual
`(*(vtbl(gm+0x6EAA20))+0x60)(...)` @0x823F2A0C.

**BridgeGuiToSound — unconditional:**
1. @0x823F2A14 `LockForRead(r26 guiOut var_D0)`.
2. @0x823F2A1C `LockForWrite(r15 soundRootIn)`.
3. **@0x823F2A2C `BridgeGuiToSound(gm, r4=soundRootIn, r5=guiOut)` → 0x823C0A58**.
4. @0x823F2A34 `UnlockForWrite(r15)`; @0x823F2A3C `UnlockForRead(r26)`.

**BridgeWorldToSound — gated `if (meLoadingStage > 5)`** (@0x823F2A40-48):
1. @0x823F2A50 `LockForRead(r19 worldOut)`.
2. @0x823F2A58 `LockForWrite(r15 soundRootIn)`.
3. **@0x823F2A6C `BridgeWorldToSound(gm, r4=soundRootIn, r5=worldOut, r6=r24 updateSet)` → 0x823CD580** (C3b: the bit-0x100 replay-source select consumes r6).
4. @0x823F2A74 `UnlockForWrite(r15)`; @0x823F2A7C `UnlockForRead(r19)`.

**`BridgeGameStateToSound` @0x823CDE50 is NOT CALLED in this function.** Confirmed by full
bl-scan and by its xrefs_to: its ONLY caller is `BrnGameModule::DoUpdate_Sound` @0x823DCEC0
(the full-game spine leg, appendix B). The loading spine has no gamestate→sound bridge.

## 7. RootSoundModule::Update @0x823F2AC8 — unconditional, called with NO external locks held

Raw asm (the whole argument setup):

```
0x823F2A80  lwz   r11, off_830102D0@l(r30)   # gm
0x823F2A84  mr    r10, r24                   # arg7  BrnUpdateSet (live FSM value, not a literal)
0x823F2A88  lwz   r28, 0x160+var_BC(r1)      # sound RootOutputBuffer*
0x823F2A8C  mr    r8, r15                    # arg5  RootInputBuffer*
0x823F2A90  addis r5, r11, 0x9A
0x823F2A94  add   r4, r11, r22               # r4 = gm+0x9A0AD4  (r22 == 0x9A0AD4 since 0x823F28F0)
0x823F2A98  addi  r5, r5, 0xAF0              # r5 = gm+0x9A0AF0
0x823F2A9C  addis r3, r11, 0x8A
0x823F2AA0  lwzx  r7, r11, r31               # arg4  *(gm+0x996F04) update-OUTPUT stack
0x823F2AA4  mr    r9, r28                    # arg6  RootOutputBuffer*
0x823F2AA8  lwzx  r6, r11, r29               # arg3  *(gm+0x996F00) update-INPUT stack
0x823F2AAC  addi  r3, r3, 0x7D00             # this = gm+0x8A7D00 (mSoundModule)
0x823F2AB0  lfs   f12, 0x10(r4)              # gameTimer.mDelta      (gm+0x9A0AE4)
0x823F2AB4  lfs   f0,  0x10(r5)              # simTimer.mDelta       (gm+0x9A0B00)
0x823F2AB8  lfs   f13, 0xC(r5)               # simTimer.mScale       (gm+0x9A0AFC)
0x823F2ABC  fmuls f2, f0, f13                # arg2 f2 = simDelta * simScale
0x823F2AC0  lfs   f0,  0xC(r4)               # gameTimer.mScale      (gm+0x9A0AE0)
0x823F2AC4  fmuls f1, f12, f0                # arg1 f1 = gameDelta * gameScale
0x823F2AC8  bl    BrnSound::Module::RootSoundModule::Update   # 0x826FB238
```

PC signature `Update(f32, f32, IOBufferStack*, IOBufferStack*, RootInputBuffer*,
RootOutputBuffer*, BrnUpdateSet)` maps as:

| PC arg | console reg | derivation |
|--------|-------------|------------|
| f32 #1 | f1 | **GAME timer** `gm+0x9A0AD4`: `[+0x10] * [+0xC]` = last-delta x scale. This timer was `Timer::Update`d THIS frame @0x823F28FC. |
| f32 #2 | f2 | **SIM timer** `gm+0x9A0AF0` (adjacent; sizeof(Timer)=0x1C): same `[+0x10] * [+0xC]` product. Not updated in this function. |
| IOBufferStack* #1 | r6 | `*(gm+0x996F00)` update-INPUT stack |
| IOBufferStack* #2 | r7 | `*(gm+0x996F04)` update-OUTPUT stack |
| RootInputBuffer* | r8 | r15 (the "Sound" buffer from §1) |
| RootOutputBuffer* | r9 | r28 = var_BC (the "Sound" output buffer) |
| BrnUpdateSet | r10 | r24 = ConstructUpdateSetFromFsm result — **member/FSM-derived, no literal** |

Timer field semantics (from `CgsSystem::Timer::Update` @0x828D7320): +0x00 u32 frame count,
+0x04 s32 whole elapsed secs, +0x08 f32 frac elapsed, **+0x0C f32 scale**, **+0x10 f32
delta** (copied from +0x14 raw dt each Update), +0x14 f32 raw dt, +0x18 u8 enabled. So both
f32 args are *scaled delta seconds*. `DoUpdate_Sound` @0x823DCEC0 (full spine) computes the
IDENTICAL products from the SAME two gm timers — cross-confirmation. The recon
(`BrnGameModule.cpp:3229-31`) already names gm+0x9A0AD4 = THE GAME TIMER and gm+0x9A0AF0 =
the sim timer.

NOTE: neither RootIn (r15) nor RootOut (r28) is locked by the caller around Update —
RootSoundModule::Update takes its own locks internally (C2's "console lock set").

## 8. Sound→resource forward, AFTER Update (0x823F2ACC–0x823F2B74)

Read-lock cluster: @0x823F2AD0 guiModelOut r23, @0x823F2AD8 guiOut r26, @0x823F2AE0
worldOut r19, **@0x823F2AE8 soundRootOut r28**. Then:

1. @0x823F2AFC `BridgeGuiToResource(gm, r4=r25 gameDataIn, r5=guiModelOut, r6=guiOut)`.
2. @0x823F2B18 `BridgeWorldToResource(gm, r4=r25, r5=worldOut)` — gated `meLoadingStage > 5` (@0x823F2B00-08).
3. @0x823F2B24 `BridgeGuiToGame(gm, r4=guiOut)`.
4. **@0x823F2B2C `q2048 = RootOutputBuffer::GetResourceEventQueue(r28)` → 0x823B8B10**:
   asserts read-locked (h line 0x22C), returns `this+0x1014` = `VariableEventQueue<2048,16>`.
5. **@0x823F2B38 `q32k = GameDataIO::InputBuffer::GetEventQueue(r25)` → 0x823B1830**:
   asserts write-locked (Resource/BrnGam h line 0xE2), returns `this+0x8014` =
   `VariableEventQueue<32768,16>` (`addis r3,r28,1; addi r3,r3,-0x7FEC` = +0x8014).
6. **@0x823F2B40 `q32k->Append<2048,16>(*q2048)` → 0x823CE908** — the sound resource-event
   queue drained into the GameData input event queue.
7. **@0x823F2B48 `ri = RootOutputBuffer::GetRequestInterface(r28)` → 0x823B8A68**: asserts
   read-locked (h line 0x224), returns `this+0x4` = `RequestInterface<4096>`.
8. **@0x823F2B54 `r25->AppendRequestInterface<4096>(ri)` → 0x823C76B8** — the sound resource
   REQUEST interface merged in. (Two forwards total: event queue + request interface.)

Unlock reads in reverse @0x823F2B5C-74: soundRootOut, worldOut, guiOut, guiModelOut.
The soundRootOut read-lock brackets the whole resource cluster even though only steps 4-8
touch it.

## 9. Tail + teardown

* @0x823F2B88 BridgeInputToGame (inputOut r21 read-locked around it).
* @0x823F2BB8 `RenderGUI(this, guiIn, guiOut, guiModelOut, guiViewIn r17, 0)` — only if `meLoadingStage != 8`.
* @0x823F2BC0 `UnlockForWrite(r25 gameDataIn)`; @0x823F2BC8 `UnlockForRead(r20 gameDataOut)` — the spine-wide persistent-pair bracket closes.
* DestroyIOBuffer batch 0x823F2BCC–0x823F2CC8 in EXACT REVERSE creation order, each passing
  the same stack the buffer was carved from. The sound trio:
  * @0x823F2C88 `DestroyIOBuffer<RootPreUpdateOutputBuffer>(*(gm+0x996F04), &var_C0)`
  * @0x823F2C98 `DestroyIOBuffer<RootOutputBuffer>(*(gm+0x996F04), &var_BC)`
  * @0x823F2CA8 `DestroyIOBuffer<RootInputBuffer>(*(gm+0x996F00), &var_B8)`

## 10. PerfMon brackets — summary

* **LoadingScriptedState::Update itself contains ZERO PerfMonCpu calls.** The bridges,
  RootSoundModule::Update, and the resource forward are all UNBRACKETED on the loading spine
  (unlike the full spine, where DoUpdate_Sound wraps the equivalents).
* The only sound-leg monitors fire inside `DoPreUpdate_Sound`:
  `StartMonitor(gm.mCpuMonitors.miUT_Sound)` (s32 @ gm+0x996F34 = BrnCpuMonitors@gm+0x996F18
  + 0x1C) then `StartMonitor(miUT_SoundUpdate)` (gm+0x996FB4 = +0x9C); Stops in reverse.
  Handles are s32 VALUES passed to StartMonitor/StopMonitor (@0x821F1198/0x821F1308).

## 11. Other sound-related calls (checklist extensions)

1. **`LoadSoundModuleAgain` @0x823E7700** — stage-0/1 arm of the load machine, args
   `(this, gameDataIn r25, gameDataOut r20)`.
2. **Stage-6 game-event post id 0x129 (297)**, 1 uninitialized payload byte, into the
   RootInputBuffer 13312 game-event queue at +0x3084 (§2) — the "sound, world load done" signal.
3. **`BridgeSoundToTraining` @0x823C63C0** inside DoPreUpdate_Sound (§4 step 8), args
   `(gm, preUpdateOut)` — needs its own decode before C4 wires it (or an honest stub).

Lock-bit encoding used by all the queue accessors: IOBuffer byte0 bit 0x08 = write-locked
(`extrwi 1,28`), bit 0x10 = read-locked (`extrwi 1,27`).

---

## Appendix A — consolidated ordered call list (sound entries starred)

```
  meLoadingStage==8 ? tail BrnGameModule::DoUpdate(gm) : fall through
  16x CreateIOBuffer (incl. * RootIn@0x823F23CC / * RootOut@0x823F23E0 / * PreUpdateOut@0x823F23F8)
  LockForWrite(gameDataIn +0x996F10) / LockForRead(gameDataOut +0x996F14)
  stage machine (park-flag gated):
*   0/1: LoadSoundModuleAgain(this, in, out)
    2..5: effects / gamestate2 / gui-vcall+0x5C / world module loads
*   6: RootIn.GetGameEventQueue(+0x3084).AddEvent(id 0x129, 1 byte); stage:=8
  r24 = ConstructUpdateSetFromFsm(gm)
  r17 = DoUpdate_InputPreWorld(gm, stackA, stackB, inputOut)
* DoPreUpdate_Sound(gm, stackB, preUpdateOut, guiIn)                       0x823F2714
*   { miUT_Sound + miUT_SoundUpdate brackets; RootSoundModule::PreUpdate(gm+0x8A7D00,
*     stackB, preUpdateOut); guiIn.q32k.Append<256,16>(preUpdateOut+0x8);
*     BridgeSoundToTraining(gm, preUpdateOut) }
  NetworkModule::ProcessBeforeSimulation(gm+0x8C3600, ...)
  BridgeNetworkToGui / BridgeGuiToGameState / GameStateModule::PreWorldUpdate / BridgeGameStateToGui
  if (meLoadingStage > 5):
*   Read(preUpdateOut)+Write(worldIn); BridgeSoundToWorld(gm, worldIn, preUpdateOut) 0x823F2818; unlocks
    if (!(r24 & 0x60)): FreeAll(gm+0x9A0630); worldModule vcall+0x4C(updateSet, stackA,
      stackB, worldIn, worldOut, allocator)                                0x823F288C
  if (r24 & 0x20): DoUpdate_GuiPreWorld (gameDataIn unlock/relock bracket)
  DoUpdate_InputPostWorld(gm, stackA, stackB, gsOut#1, worldOut, r17)
  Timer::Update(gm+0x9A0AD4)                                               0x823F28FC
  GuiEventTimeInfo post; gui-out clears; id-0x8F event; BridgeGameToGui; BridgeControllerToGui
  guiModule vcall+0x60(gm+0x6EAA20, updateSet, stackA, stackB, guiIn, guiOut, guiModelOut,
    guiViewIn, [gameDataOut, gameDataIn, false])                           0x823F2A0C
* Read(guiOut)+Write(rootIn); BridgeGuiToSound(gm, rootIn, guiOut)         0x823F2A2C; unlocks
* if (meLoadingStage > 5):
*   Read(worldOut)+Write(rootIn); BridgeWorldToSound(gm, rootIn, worldOut, r24) 0x823F2A6C; unlocks
* RootSoundModule::Update(gm+0x8A7D00, gameTimer.dt*scale, simTimer.dt*scale,
*   stackA, stackB, rootIn, rootOut, r24)                                  0x823F2AC8
  Read(guiModelOut, guiOut, worldOut, * rootOut)
  BridgeGuiToResource; [stage>5] BridgeWorldToResource; BridgeGuiToGame
* gameDataIn.q32k(+0x8014).Append<2048,16>(rootOut+0x1014)                 0x823F2B40
* gameDataIn.AppendRequestInterface<4096>(rootOut+0x4)                     0x823F2B54
  unlock reads; BridgeInputToGame; [stage!=8] RenderGUI(..., 0)
  UnlockForWrite(gameDataIn); UnlockForRead(gameDataOut)
  16x DestroyIOBuffer, reverse order (sound trio @0x823F2C88/0x823F2C98/0x823F2CA8)
  (NO BridgeGameStateToSound anywhere in this function)
```

## Appendix B — divergence note: the full spine's DoUpdate_Sound @0x823DCEC0 (121 instrs)

For when C4+ reaches `BrnGameModule::DoUpdate`. Same miUT_Sound/miUT_SoundUpdate bracket
pair, same f1/f2 timer products (gameTimer +0x9A0AD4 / simTimer +0x9A0AF0), same
gm+0x8A7D00 `this` — but it:
* carves the RootInputBuffer ITSELF per call ("Sound", off its r4 stack arg, with
  mpStack->CreateIOBuffer/DestroyIOBuffer asserts) and destroys it at the end;
* orders the bridges **WorldToSound → SetCameraInput (from
  `DirectorIO::OutputBuffer::GetCameraOutput`) → BridgeGameStateToSound @0x823DCFBC →
  BridgeGuiToSound (gui out = member `*(gm+0x9A0BD8)`) → SetReplayStatusInterface (from
  `ReplayIO::OutputBuffer_PreSim::GetStatu...`)** — a DIFFERENT order from the loading
  spine's GuiToSound-then-WorldToSound, plus two RootInputBuffer installs the loading spine
  never does;
* passes updateSet as a stack halfword (`lhz arg_66`) into BridgeWorldToSound and into
  RootSoundModule::Update's r10.
Do not conflate the two legs when wiring C4.
