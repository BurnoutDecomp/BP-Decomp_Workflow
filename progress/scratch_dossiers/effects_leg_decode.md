# Effects leg decode — DoUpdate_Effects / BridgeRendererToEffects / EffectsModule::Update

Ground truth: the `assembly` fields of `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x<ADDR>.json`.
Vtable slot resolution read straight from the decrypted XEX rodata
(`IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex`, file_off = 0x3000 + vaddr − 0x82000000,
big-endian). Names are the dossiers' own `name` fields; truncated exports are resolved against the
PC tree's already-attested address annotations where those exist (each such resolution is marked).
Companion walk: `progress/scratch_dossiers/doupdate_spine_codex.md` (scheduler order, section 4:
`0x823F1910 -> DoUpdate_Effects @0x823DD0A8 -> M(effects)`).

---

## 1. `BrnGame::BrnGameModule::DoUpdate_Effects @ 0x823DD0A8` — full decode

Frame 0xE0, saves r17–r31 (`__savegprlr_17`). Single caller: `DoUpdate @0x823F0AF8`
(bl @0x823F1910).

### 1.1 Signature (register + stack args, caller-verified — see section 4)

| ABI slot | Captured in | Value |
|---|---|---|
| r3 | r30 | `this` (BrnGameModule*) |
| r4 | r24 | update **INPUT** IOBufferStack (`*(this+0x996F00)`) |
| r5 | r19 | update **OUTPUT** IOBufferStack (`*(this+0x996F04)`) |
| r6 | r26 | `CgsInput::InputIO::OutputBuffer*` (pad/input module output) |
| r7 | r29 | `BrnGameState::GameStateModuleIO::OutputBuffer*` |
| r8 | r28 | `BrnWorldIO::UpdateOutputBuffer*` |
| r9 | r25 | `BrnDirector::DirectorIO::OutputBuffer*` |
| r10 | r27 | `BrnReplays::ReplayIO::OutputBuffer_PreSim*` |
| caller sp+0x54 (`arg_54`) | r23 | `BrnSound::Module::Io::RootPreUpdateOutputBuffer*` |
| caller sp+0x5C (`arg_5C`) | (loaded late) | `BrnEffects::EffectsIO::OutputBuffer*` |
| caller sp+0x64 slot, byte @+0x67 (`arg_67`) | (lbz) | `bool` resources-live (`*GetLive(resourceOutput)`) |
| caller sp+0x6C slot, halfword @+0x6E (`arg_6E`) | r21 | `u16` update set (BrnUpdateSet) |

PC-shaped signature (mirrors the committed `DoUpdate_Sound` declaration style in
`b5-decomp/src/GameSource/Game/BrnGameModule.hpp`):

```cpp
void DoUpdate_Effects(CgsModule::IOBufferStack*                        lpInputBufferStack,      // r4
                      CgsModule::IOBufferStack*                        lpOutputBufferStack,     // r5
                      const CgsInput::InputIO::OutputBuffer*           lpInputOutputBuffer,     // r6
                      BrnGameState::GameStateModuleIO::OutputBuffer*   lpGameStateOutputBuffer, // r7
                      BrnWorldIO::UpdateOutputBuffer*                  lpWorldOutputBuffer,     // r8
                      BrnDirector::DirectorIO::OutputBuffer*           lpDirectorOutputBuffer,  // r9
                      BrnReplays::ReplayIO::OutputBuffer_PreSim*       lpReplaysPreSimOutputBuffer, // r10
                      BrnSound::Module::Io::RootPreUpdateOutputBuffer* lpSoundPreUpdateOutputBuffer, // sp+0x54
                      BrnEffects::EffectsIO::OutputBuffer*             lpEffectsOutputBuffer,   // sp+0x5C
                      bool                                             lbResourcesLive,         // sp+0x64/+0x67
                      BrnUpdateSet                                     leUpdateSet);            // sp+0x6C/+0x6E
```

### 1.2 PerfMon

ONE monitor, no nesting (unlike sound's 0x996F34/0x996FB4 pair):
- `0x823DD0D8/E0`: `CgsDev::PerfMonCpu::StartMonitor(*(this + 0x996F38))`
- `0x823DD25C/60`: `StopMonitor(*(this + 0x996F38))`
Everything in the body — carve, bridges, module Update, all of it — is inside this bracket;
only the input-buffer destroy follows the stop. The caller's `M(effects)` memory-audit block
(`0x823F1914` onward) runs after return.

### 1.3 Buffer carve (the effects update-INPUT buffer)

The leg self-carves its input buffer off the **input** stack — DoUpdate does NOT create it.
Inlined `CgsModule::IOHelper<BrnEffects::EffectsIO::InputBuffer>` ctor pattern
(assert file `"..\..\..\GameShared\GameClasses\Mo..."` = CgsModuleIOHelper.h, lines 0x34/0x39):

- `0x823DD0E4-F8`: `CreateIOBuffer<EffectsIO::InputBuffer> @0x823AF9C8`
  (r3 = input stack (incoming r4), r4 = &local `mpBuffer` (fp var_8C), r5 = `"Effects"`).
  Helper body: `IOBufferStack::Alloc(0x1850? no — 0xE4A0, "Effects")` — **alloc size 0xE4A0**
  (`0x823AFA60-70`), then `BrnEffects::EffectsIO::InputBuffer::Construct` on success
  (`0x823AFA80`). 0xE4A0 matches the PC header's `maImage[0xE4A0]` exactly.
- `0x823DD0FC-128`: on failure, assert triple
  (`"mpStack->CreateIOBuffer( &mpBuffer, lpc"...`, line 0x34 = 52).
- `0x823DD134`: r31 = the created `InputBuffer*`.

### 1.4 Lock bracket

`sub_823B78A0` / `sub_823B7A10` are a dedicated 7-buffer lock/unlock pair (BrnGameModule.cpp-local
statics; assert names `lpInputBuffer`, `lpOutputBuffer0..5`, file `aDP4B5MainBurno_139`,
lock lines 0x1C6–0x1CC = 454–460, unlock lines 0x1E2–0x1E8 = 482–488; each first null-asserts
all seven pointers).

Call @`0x823DD150` — `sub_823B78A0(in=r31, out0=director(r25), out1=pad(r26), out2=world(r28),
out3=gamestate(r29), out4=replayPreSim(r27), out5=soundPreUpdate(r23))`:
- `LockForWrite(effects input)`, then `LockForRead` in order:
  **director → pad → world → game-state → replay-pre-sim → sound-pre-update**.

Call @`0x823DD230` — `sub_823B7A10(same seven, same order)`:
- `UnlockForRead` in exact reverse (**soundPre → replayPre → gamestate → world → pad → director**),
  then `UnlockForWrite(effects input)`.

Everything between the two helpers (all staging below) runs under the locks. The virtual
`EffectsModule::Update` call happens AFTER the unlock — the module locks its own in/out
buffers internally (see section 3).

### 1.5 Ordered body (every call, with args)

Inside the lock bracket, in console order:

1. `0x823DD154-160` — `EffectsIO::InputBuffer::SetTimerStatusInterface @0x823BA548`
   `(in, this + 0x9A0B0C)` — the game module's own 48-byte TimerStatusInterface member
   (the same struct BridgeTimers snapshots; 0x30-byte copy per the setter).
2. `0x823DD164-174` — `BrnDirector::DirectorIO::OutputBuffer::GetCameraOutput @0x823B3308`
   `(directorOut)` → `EffectsIO::InputBuffer::SetCameraInput @0x823C9770 (in, camera)`.
3. `0x823DD178-1A0` — `CgsInput::InputIO::OutputBuffer::GetPadInfo @0x823B1230 (padOut, 0)`;
   test `(*(u32*)(padInfo + 0x34) >> 1) & 1`; if set →
   `BrnEffects::EffectsModule::RestartEffects @0x822793E0 (this + 0x878700)`.
   (Debug pad-combo restart; **the EffectsModule instance is embedded in BrnGameModule at
   +0x878700** — same offset DoDispatch uses.)
4. `0x823DD1A4-1B8` — r21 = updateSet (arg_6E);
   `BrnGame::BrnGameModule::BridgeEntityToEffects @0x823CDF00
   (this, r4=worldOut(r28), r5=in(r31), r6=updateSet(r21))`. Full decode in section 1.7.
5. `0x823DD1BC-1D4` — game-action forward:
   `GameStateModuleIO::OutputBuffer::GetGameActionQueue @0x823B96F0 (gameStateOut)`
   (read-lock accessor; returns `gameStateOut + 4`; identity proven by its caller set —
   BridgeGameStateToSound/-Director/-World/-Network, CheckGameActions,
   TranslateGameActionsToGuiEvents — and the PC `mpOutputBuffer->GetGameActionQueue()`)
   → `EffectsIO::InputBuffer::GetGameActionQueue (W) @0x823BA708` (returns `in + 0xA690`,
   write-lock assert) →
   `CgsModule::VariableEventQueue<13312,16>::Append<13312,16> @0x823C7440 (dest, src)`.
6. `0x823DD1D8-1E8` — `ReplayIO::OutputBuffer_PreSim::GetStatusInterface @0x823BB080
   (replayPreSimOut)` (returns `+4`) →
   `EffectsIO::InputBuffer::SetReplayStatusInterface @0x823BA7B0 (in, ·)`.
7. `0x823DD1EC-200` — `BrnSound::Module::Io::RootPreUpdateOutputBuffer::GetPreUpdateOutput
   @0x823B8BB8 (soundPreUpdateOut)` (truncated export `...::Ge`; identity attested in PC
   `BrnRootSoundModuleIo.h:396/470`) →
   `EffectsIO::InputBuffer::SetAudioEffectsMessageQueue @0x823BA9E0 (in, result + 0x2A0)`
   (144-byte copy into `in + 0xE404`). The audio-effects message queue lives at
   PreUpdateOutput+0x2A0.
8. `0x823DD204-228` — `lbz` the incoming resources-live byte (arg_67), `stbx` it RAW into
   `in + 0xE494` (no setter, no per-store lock assert — it is inside the write lock).
   0xE494 = 0xE404 + 0x90, i.e. the word right after the audio message queue; this member is
   currently UNNAMED in the PC InputBuffer header (its 0xE4A0 image covers it).
9. `0x823DD230` — unlock helper (section 1.4).

### 1.6 Module dispatch + teardown

- `0x823DD234-258` — virtual call:
  `r3 = this + 0x878700` (EffectsModule), `r4 = input stack (r24)`, `r5 = output stack (r19)`,
  `r6 = in (r31)`, `r7 = effects OUTPUT buffer (arg_5C)`, `r8 = updateSet (r21)`;
  `lwz r11,0(r3); lwz r11,0x44(r11); mtctr; bctrl` — **vtable slot +0x44**.
  Rodata-verified (section 3): slot +0x44 of the EffectsModule vtable `off_820D0D48`
  = **`BrnEffects::EffectsModule::Update @0x8229EC28`**.
- `0x823DD25C-260` — `StopMonitor(*(this + 0x996F38))`.
- `0x823DD264-294` — `DestroyIOBuffer<EffectsIO::InputBuffer> @0x823AFAA0`
  (r3 = the input stack saved at var_90, r4 = &mpBuffer); on failure assert
  `"mpStack->DestroyIOBuffer( &mpBuffer )"`, line 0x39 = 57 (IOHelper dtor pattern).
- `0x823DD298-29C` — epilogue.

### 1.7 `BridgeEntityToEffects @0x823CDF00` (101 instrs — the entity→effects staging)

`(this[unused], r4 = BrnWorldIO::UpdateOutputBuffer* (r22), r5 = EffectsIO::InputBuffer* (r23),
r6 = u16 updateSet (r31))`. Seven installs, in order (world getters are read-lock, input setters
write-lock — both already held by the caller's bracket):

1. `UpdateOutputBuffer::GetContactSpy[Interface] @0x823B5D68` → `InputBuffer::SetContactSpyInterface @0x823BA658` (1-word copy → `in+0x7B90`).
2. `GetDe[formationOutputInterface] @0x823B6350` → `SetDeformationInterface @0x823C9820` (→ `in+0x7BA0`).
3. `[GetPropVFXLocatorQueue] @0x823B6740` (truncated `BrnWorldIO::U`; PC h:712 pins the identity) → `SetPropVFXLocatorQueue @0x823C98D0` (clear count + Append → `in+0xE0D0`).
4. `updateSet & 0x100` (rlwinm bit 23) ? `sub_823B5CC0` = `GetReplayActiveRaceCarOutputInterface` (PC h:547, `+40336`) : `sub_823B5C18` = `GetActiveRaceCarOutputInterface` (PC h:544, `+29856`) → `SetActiveRaceCarInterface @0x823BA490` (XMemCpy 0x28F0 → `in+0x1140`).
5. Inline loop: copy 8 records × 0x24 bytes from `iface + 0x210` into `in + 0x4`
   (9-word `mtctr` copy per record; range asserts `leActiveRaceCarIndex >= / < E_ACTIVE_RACE_CAR...`,
   `GameSource\World/EntityMod...` lines 0x485/0x486, plus `leEnumIndex <=` BurnoutConstants:0x27).
6. `GetVehicleOut[putInterface] @0x823B58D0` → `SetVehiclePhysicalStateQueue @0x823C96B8 (in, iface + 0x2620)` (clear count + Append → `in+0x3A30`).
7. `GetEffectsEnviron[mentInterface] @0x823B64A0` → `SetEffectsEnvironmentInterface @0x823BA868` (16-byte copy → `in+0xDAA0`).
8. `sub_823B6938` (read-lock; returns `worldOut + 0x34C30` — the update-output triangle-cache
   interface; NOT yet declared on the PC `UpdateOutputBuffer`) →
   `SetTriangleCacheInterface @0x823BA928` (1-word copy → `in+0xE400`).

---

## 2. `BrnGame::BrnGameModule::BridgeRendererToEffects @ 0x823C1168` — full decode

**Caller: `DoDispatch @0x823DC458` ONLY** (whole xrefs_to list) — this bridge is on the
**dispatch leg**, not the update leg, and it fills the **`EffectsIO::DispatchInputBuffer`**,
not the update InputBuffer. Frame 0x80, saves r28–r31.

Signature: `(r3 = this [never read], r4 = EffectsIO::DispatchInputBuffer* (r29),
r5 = RendererIO::OutputBuffer* (r28))`.

The "four calls" (four install groups):

| # | Source accessor | Returns | Destination install |
|---|---|---|---|
| 1 | `RendererIO::OutputBuffer::GetDispatchFrame @0x823B35A8` (read-lock assert; `lwz r3,4(out)` → **out+0x4**) | `CgsGraphics::DispatchFrame*` | **RAW store** `stw r11, 0x10(dispatchIn)` — `mpDispatchFrame` @ +0x10, inlined (no setter symbol, no store-side lock assert) |
| 2 | `GetBaseEffectsFrame @0x823B3B90` (read-lock; **out+0x24**) | `BrnEffectsFrame*` | `DispatchInputBuffer::SetBaseEffectsFrame @0x823BADE8` (write-lock; → dispatchIn+0x4) |
| 3 | loop slot = 0,1: `GetFXEventsEffectsFrame @0x823B3D10 (out, slot)` (slot<2 assert `"Invalid slot for Fx Layer"` + read-lock; **out + (0xE+slot)*4** = +0x38/+0x3C) | `BrnEffectsFrame*` ×2 | `SetFXEventsEffectsFrame @0x823BAE90 (in, slot, ·)` (slot assert + write-lock; → dispatchIn + (2+slot)*4 = +0x8/+0xC) |
| 4 | global `dword_83011AF4` (block `unk_83011A78`) | `renderengine::Texture*` (env map) | `SetEnvironmentMap @0x823BAA98` (write-lock; → dispatchIn+0x1B0) |

`dword_83011AF4` is seeded by `BrnRendererModule::Construct @0x8240A778` at `0x8240BE80-BE9C`:
`CgsRenderTarget::GetTexture(*(renderer + 0x244), 0)` — the env-map render target's texture
(renderer pool slot 3 per the in-tree PARKED note), cached in the global render-state block
alongside the depth texture (`dword_83011ABC`).

**Lock expectations** — the bridge takes NO locks itself; DoDispatch pre-holds both:

```
0x823DC658  BrnRendererModule::Update(this+0x4400, ...)         ; renderer publishes its output
0x823DC664  LockForWrite(effects dispatch input)     ; r30 = *(fp var_A4)
0x823DC670  LockForWrite(world dispatch input)       ; r26 = *(fp var_84)
0x823DC678  LockForWrite(r22 = *(this+0x996F10))     ; (game dispatch-side buffer)
0x823DC680  LockForRead (renderer output)            ; r28 = *(fp var_9C)
0x823DC690  LockForWrite(*(this+0x9A0BCC))           ; (gui input buffer)
0x823DC6A0  BridgeRendererToWorld  @0x823CDD20 (this, worldDispatchIn, rendererOut)
0x823DC6B0  BridgeRendererToGui    @0x823CD6B0 (this, *(this+0x9A0BCC), rendererOut)
0x823DC6C0  BridgeRendererToEffects@0x823C1168 (this, effectsDispatchIn, rendererOut)   <-- HERE
0x823DC6C8  GetIm2dDebugRenderBuffer(rendererOut) -> stw into r22+0x10024
0x823DC6E0  UnlockForWrite(effects dispatch input)   ; then the other unlocks
```

The DispatchInputBuffer itself is carved earlier in DoDispatch (`0x823DC560-570`):
`IOHelper<EffectsIO::DispatchInputBuffer>::IOHelper @0x823C19C0
(&fp var_A8, *(this+0x996F00) input stack, "EffectsDispatch")` — buffer pointer lands in
fp var_A4; destroyed at `0x823DC910` (`DestroyIOBuffer<DispatchInputBuffer> @0x823AED40`).

Downstream of the bridge, still in DoDispatch (the dispatch-input consumers, for context):
- `0x823DC718-740`: `sub_823B6FE0`(W dispatchIn + R director output) →
  `DirectorIO::OutputBuffer::GetCameraOutput(*(this+0x9A0BDC))` →
  `DispatchInputBuffer::SetCameraInput @0x823C9988` → `sub_823B7060` (unlock pair).
- `0x823DC858`: `BridgeWorldToEffects_Dispatch @0x823C11F8` (world dispatch output →
  the key-light/irradiance/white-level members, under its own R/W bracket).
- `0x823DC884`: `BrnEffects::EffectsModule::GenerateDispatchLists @0x82296668` reads the
  buffer under `LockForRead` — the sole consumer (forwards the env map into the particle
  dispatch input, per the in-tree PARKED note).

---

## 3. `BrnEffects::EffectsModule::Update @ 0x8229EC28` — vtable resolution + top shape

### 3.1 Vtable (rodata, decrypted XEX @ file_off 0xD3D48)

The ctor `EffectsModule::EffectsModule @0x827E35E0` stores the base module vtable
`off_820CE500` first (16 slots, +0x00..+0x3C — the string at +0x40 proves the base list ends
there), then overwrites `*(this+0)` with **`off_820D0D48`** — the EffectsModule vtable:

| Slot | Target | Identity |
|---|---|---|
| +0x00 | 0x8228FE98 | `EffectsModule::Construct` |
| +0x08 | 0x8227FCA8 | `EffectsModule::Release` |
| +0x0C | 0x8227FD78 | `EffectsModule::Destruct` |
| +0x40 | 0x8229E690 | `EffectsModule::Prepare` |
| **+0x44** | **0x8229EC28** | **`EffectsModule::Update`** ← DoUpdate_Effects's bctrl |
| +0x48 | 0x8227FE10 | `EffectsModule::PreRenderUpdate` (DoDispatch's early bctrl @0x823DC49C, arg = DispatchThreadInputBuffer `*(this+0x9A11B0)`) |
| +0x4C | 0x8227FE88 | `EffectsModule::DispatchThreadUpdate` |

(Slots +0x10..+0x3C are the shared base defaults, 0x8286Exxx/0x827DCxxx.)

### 3.2 Update signature (as called / as used)

Called with `(this, r4=inputStack, r5=outputStack, r6=EffectsIO::InputBuffer*,
r7=EffectsIO::OutputBuffer*, r8=updateSet)`. The body captures ONLY `r20=r6` (input buffer) and
`r16=r7` (output buffer); **incoming r4, r5 and r8 are never read** (first r4/r5/r8 ops are all
writes; nothing is spilled in the prologue) — IDA's proto accordingly shows 5 params.

### 3.3 Top shape (first ~40 instrs + ordered call list; NOT a full decode)

630 instructions. Entry:
1. `lbzx this+0x2C340` — module-disabled byte → plain return.
2. `lbz this+0x2C351` — skip-one-frame latch → clear it + return.
3. `LockForWrite(out)`; `OutputBuffer::GetReplayRequestInterface (W) @0x8227E280` →
   `BrnReplays::ReplayIO::RequestInterface::RegisterSerialiser @0x821F34A0 (·, this+0x2F550)`
   (the module-embedded EffectsSerialiser).
4. `LockForRead(in)`.
5. if `lbz this+0x234`: `LoadNativeParticleParams @0x82290510`, clear the flag.
6. `switch (dword_82FAD294)` — 5 cases (the replays global mode): the suspend/resume paths
   unlock + return early, calling `ParticleModule::SuspendPlayingEffects @0x8227A2B8` /
   `ResumePlayingEffects @0x8228A320`; case 0 reads `in+0xE494` (the resources-live byte the
   game leg stored) and mirrors module state bytes at `this+0x23BB0/0x23BB1/0x23BB4`.
7. Resources branch: `Attrib::Gen::surfacelist::Num_Surfaces`, `Attrib::Instance::
   GetAttributePointer`/`DefaultDataArea`/`RefSpec::GetCollection`, `surface`/`visualfxsurface`
   ctors, `BrnParticle::Native::TrailSystem::UpdateTrailType @0x8228C248` (per-surface trail
   refresh), `Instance::~Instance` ×2.
8. Main body, ordered sub-updates (bl order):
   `EffectsSerialiser::GetStaticLayout` → `InputBuffer::GetCameraInput @0x8227D940` →
   `GetTimerStatusInterface @0x8227D9E8` (time step / abs time / multiplier products — the
   three floats the PC PARKED comment documents) → `ParticleModule::ResetSparkFrameData
   @0x8227EAC8` → `EffectsSerialiser::Read @0x82650508` / `StaticLayout::Clear` →
   `HandleShowtimeTrafficBounce @0x82292808` → `InputBuffer::GetGameActionQueue (R)
   @0x8227DBE0` → `HandleGameActions @0x82296FD8` → `JunkyardVfxStart @0x82291AE8` /
   `JunkyardVfxStop @0x82292028` → `GetActiveRaceCarInterface @0x8227D7F0` →
   `GetAudioEffectsMessageQueue @0x8227DDD8` → `GetDeformationInterface @0x8227DB38` →
   `ProcessActiveRaceCars @0x8229EB30` → `GetContactSpyInterface @0x8227DA90` →
   `ProcessCarContactQueues @0x8229B7F8` → `HandleGlassSmashEventsForAllCars @0x82297420` →
   `GetPlayerRaceCarState @0x822803C0` → `GetPropVFXLocatorQueue @0x8227DC88` →
   `PropCollisions::UpdateLocatorVfx @0x822993A0` →
   `RCEntityActiveRaceCarOutputInterface::IsPlayerCarActive/GetPlay.../...` →
   `HandlePlayerTriangleCache @0x82296EA0` → `HandleQADebugTests @0x82291700` →
   `Camera::CameraState::HasChanged @0x8227D380` → `BoostStateMachine::SetWorldIndex
   @0x82280578` → one `bctrl @0x8229F51C` (the embedded ParticleModule's Update virtual,
   vtable+68 — per the in-tree PARKED comment, args = timestep/abs-time/multiplier) →
   tail `UnlockForRead(in)` / `UnlockForWrite(out)` → `EffectsSerialiser::Write @0x82650600`
   when recording.

---

## 4. Caller context — `DoUpdate @0x823F0AF8`, the ONE bl @0x823F1910

Setup (`0x823F18DC-190C`); DoUpdate frame is 0x1C0, so `var_X` = frame offset `0x1C0−X`;
outgoing stack args land at DoUpdate's own sp+0x54.. (var_16C=+0x54, var_164=+0x5C,
var_15A+1=+0x67, var_154+2=+0x6E):

| Arg | Instruction | Where the value was made |
|---|---|---|
| r3 = this | `mr r3, r25` | r25 = this since `0x823F0B04` |
| r4 = input stack | `lwz r4, 0(r16)`; r16 = `*(var_118)` (reloaded `0x823F1824`) | var_118 = spill of `this+0x996F00` holder (`stw r23 @0x823F0B48`) |
| r5 = output stack | `lwz r5, 0(r14)` | r14 = `this+0x996F04` (`0x823F0B8C/94`) |
| r6 = pad output | `lwz r6, var_DC` | created `0x823F0B50` `CreateIOBuffer<OutputBuffer@InputIO@CgsInput>` → var_DC |
| r7 = game-state output | `lwz r7, var_EC` | created `0x823F0BE4` `CreateIOBuffer<OutputBuffer@GameStateModuleIO>` → var_EC |
| r8 = world update output | `mr r8, r26`; r26 = `*(var_AC)` (`0x823F1488`) | created `0x823F0C20` `CreateIOBuffer<UpdateOutputBuffer@BrnWorldIO>` → var_AC |
| r9 = director output | `lwz r9, 0(r28)`; r28 = `this+0x9A0BDC` (`0x823F1610/1C`) | **persistent member** — the frame's director OutputBuffer (DoUpdate creates only the director INPUT, var_D4 @0x823F0C5C) |
| r10 = replay pre-sim output | `lwz r10, var_E4` | created `0x823F0CD4` `CreateIOBuffer<OutputBuffer_PreSim@ReplayIO>` → var_E4 |
| sp+0x54 = sound pre-update output | `stw r15, var_16C`; r15 = `*(var_CC)` (`0x823F12E8`) | created `0x823F0D88` `"SoundRootPreUpdateOutput"` → var_CC |
| sp+0x5C = **effects output** | `stw r29, var_164`; r29 = `*(var_C4)` (`0x823F16E4`) | created `0x823F0D4C` `CreateIOBuffer<OutputBuffer@EffectsIO> @0x823AE778` (`"Effects"`, on `*(this+0x996F04)` output stack; helper Allocs **0x1850** + `OutputBuffer::Construct`) → var_C4; destroyed `0x823F2124` `DestroyIOBuffer @0x823AE848` |
| sp+0x67 = resources-live byte | `lbz r11, var_120; stb r11, var_15A+1` | var_120 written once `@0x823F0E1C`: under `LockForRead`, `BrnResource::GameDataIO::OutputBuffer::GetLive @0x823B1638` on the resource output (r27), `lbz` its first byte (perfmon `*(this+0x996F60)` bracket, `0x823F0DFC-0E28`) |
| sp+0x6E = update set | `sth r23, var_154+2` | r23 = `ConstructUpdateSet @0x823DCB40` result (`mr r23,r3 @0x823F13D0`) — same halfword later stored for the sound leg `@0x823F19DC` |

**The effects INPUT / dispatch-input buffer story**: DoUpdate creates NO effects input buffer of
any kind. The update-leg `EffectsIO::InputBuffer` ("Effects", 0xE4A0) is self-carved inside
DoUpdate_Effects from the input stack and destroyed there (section 1.3/1.6). The
`EffectsIO::DispatchInputBuffer` ("EffectsDispatch") is a different object on a different leg:
carved in `DoDispatch @0x823DC560-570` from the same input stack via
`IOHelper<DispatchInputBuffer> @0x823C19C0`, filled by BridgeRendererToEffects + the camera
staging + BridgeWorldToEffects_Dispatch, read by `EffectsModule::GenerateDispatchLists`, and
destroyed at the end of DoDispatch (`0x823DC910`).

---

## 5. PC tree cross-check + mount worklist

### 5.1 Per-function / per-type status

| Console item | PC home | Status |
|---|---|---|
| `EffectsIO::InputBuffer` type + 19 accessors | `SharedIO/BrnEffectsModuleIO_InputBuffer.h` + `_Accessors.cpp` | **exists-faithful**. Every offset re-verified against this decode (GameActionQueue W @+0xA690 = 0x823BA708 ✓, audio queue @+0xE404/0x90 ✓, image 0xE4A0 = the console alloc size ✓). Gaps: (a) **no `Construct()`** (the create helper @0x823AF9C8 calls `InputBuffer::Construct` after Alloc); (b) **no named member/setter for the resources-live byte @+0xE494** (console writes it raw; `Update` reads it raw). |
| `EffectsIO::OutputBuffer` type + 7 accessors | `SharedIO/BrnEffectsModuleIO_OutputBuffer.{h,cpp}` | **exists-faithful** (offsets 0x4/0x1014/0x1824 ✓). Gaps: **no `Construct()`** (create helper @0x823AE778 Allocs 0x1850 then calls it); trailing `ReplayRequestInterface` is a 4-byte placeholder — console total is 0x1850, so its real span is ~0x2C. |
| `EffectsIO::DispatchInputBuffer` + accessors | `SharedIO/BrnEffectsModuleIO_DispatchInputBuffer.{h,cpp}` + `_IOHelper.cpp` | **exists-faithful**, including `Construct @0x82288120` and all four bridge setters. Gap: `mpDispatchFrame` is private with **no Set/GetDispatchFrame declared** — the console bridge writes +0x10 raw (inlined), so the PC bridge needs a setter (or friend) added per the header's GROW note. |
| `EffectsModule` class | `Effects/EffectsModule.h` + `.cpp` (223 lines) | **exists-partial**: ctor @0x827E35E0, `GetNextAcquireResourceResponse` @0x8227F098, `HandleConvoySlipStream` @0x822926C8 only. `Update @0x8229EC28`, `Prepare @0x8229E690`, `PreRenderUpdate @0x8227FE10`, `DispatchThreadUpdate @0x8227FE88`, `RestartEffects @0x822793E0`, `GenerateDispatchLists @0x82296668` and the ~30 Handle*/Process* bodies are **absent**; none of the four virtuals is even declared on the header. |
| ⚠ ODR seam | `Game/BrnGameModule.hpp:138` | `namespace BrnEffects { class EffectsModule : public CgsModule::ModuleSingleBuffered {}; }` — an EMPTY placeholder backing `mEffectsModule` (hpp:800, h:363). **Conflicts with the real class** in `Effects/EffectsModule.h`; the mount must drop the placeholder and include the real header (and the real object is ~0x2F550 bytes). |
| `DoUpdate_Effects @0x823DD0A8` | — | **absent** (hpp:201/269 mention it in comments only; the sibling `DoUpdate_Sound` declaration is the pattern to follow). |
| `BridgeEntityToEffects @0x823CDF00` | — | **absent** (only the InputBuffer.h banner names it). |
| `BridgeRendererToEffects @0x823C1168` | — | **absent**; `BrnGameModule.cpp` ~2340–2382 is the PARKED banner: only the env-map tail is documented, deliberately unwired ("the missing item is not a value, it is TWO TRANSLATION UNITS"), DELETE-WHEN EffectsModule.cpp + DispatchInputBuffer.cpp are on the build list and GenerateDispatchLists drives the particle dispatch input — then "reconstruct BridgeRendererToEffects in full (it is four calls)" and retire ParticleModuleBringUp's five BLOCKED fields. This decode (section 2) is that full body. |
| Lock helpers `sub_823B78A0`/`sub_823B7A10` | — | **absent** (BrnGameModule.cpp statics; the sound leg's analogues `sub_823B7620/sub_823B7760` are likewise console-only, PC folded them into the leg body per the hpp comment — either idiom works, the seven-buffer W+6R order is the load-bearing fact). |
| Build list | `tools/build/build_game_exe.bat` | only `Effects\Particles\ParticleModuleBringUp.cpp` (line 454, with its own DELETE note) and `Effects\Curves.cpp` (line 492) from GameSource\Effects are on it. None of the SharedIO TUs, EffectsModule.cpp, or the bridges. |

Source-side accessors the leg consumes — all **exist-faithful on PC**:
- `GameStateModuleIO::OutputBuffer::GetGameActionQueue` (= sub_823B96F0) — `BrnGameStateModule.cpp` uses it.
- `DirectorIO::OutputBuffer::GetCameraOutput @0x823B3308` — already used by the bring-up staging.
- `CgsInput::InputIO::OutputBuffer::GetPadInfo @0x823B1230` — `System/Input/` (embed-checked).
- `ReplayIO::OutputBuffer_PreSim::GetStatusInterface @0x823BB080` — `BrnReplayModuleIO.{h,cpp}`.
- `RootPreUpdateOutputBuffer::GetPreUpdateOutput @0x823B8BB8` — `BrnRootSoundModuleIo.h:396/470`, `.cpp:100`. (The +0x2A0 audio-effects-queue offset must be expressed off the PreUpdateOutput type.)
- `RendererIO::OutputBuffer::GetDispatchFrame/GetBaseEffectsFrame/GetFXEventsEffectsFrame` — `Graphics/BrnRendererModuleIO.h:121/129/131` (same X360 addresses annotated).
- WorldIO `UpdateOutputBuffer` getters: `GetContactSpyInterface` (h:607), `GetDeformationOutputInterface` (h:640), `GetPropVFXLocatorQueue` (h:669), `GetActiveRaceCarOutputInterface` (h:603) / `GetReplayActiveRaceCarOutputInterface` (h:604), `GetVehicleOutputInterface` (h:585), `GetEffectsEnvironmentInterface` (h:647) — all present. **Missing: the triangle-cache getter (sub_823B6938, returns worldOut+0x34C30)** — not declared on the PC UpdateOutputBuffer (only the Append side + the SceneManager-level getters exist).
- `VariableEventQueue<13312,16>::Append<13312,16>` — template instantiated on PC (`BrnReplayModuleIO.cpp:117`; typedefs in WorldEntityModuleIO/ReplayModuleIO).

### 5.2 Link-closure worklist for the mount (referenced symbols with no home)

Update leg (DoUpdate_Effects proper):
1. `BrnGameModule::DoUpdate_Effects` — new body in BrnGameModule.cpp (this report §1 is the spec).
2. `EffectsIO::InputBuffer::Construct` — new (create-helper dependency; zero/init per its own X360 body @ the address the create helper bl's — decode when writing it).
3. `EffectsIO::OutputBuffer::Construct` — new (same, for the caller-side "Effects" output create; also needed by `LoadingScriptedState::LoadEffectsModule @0x823E7820`, which creates a static effects OutputBuffer and forwards its resource/vault interfaces — currently `[deferred]` at `BrnGameMainFlowStates.cpp:771`).
4. `IOHelper<EffectsIO::InputBuffer>` instantiation (mirror `_DispatchInputBuffer_IOHelper.cpp`); ditto `CreateIOBuffer/DestroyIOBuffer<EffectsIO::InputBuffer/OutputBuffer>` template availability at the DoUpdate/DoUpdate_Effects sites.
5. The 7-buffer lock/unlock pair (statics beside the leg, or inline — order per §1.4).
6. `BrnGameModule::BridgeEntityToEffects` — new (§1.7); needs `UpdateOutputBuffer::GetTriangleCacheInterface` (worldOut+0x34C30) added to `BrnWorldModuleIO.h` (GROW, do not fork).
7. InputBuffer additions: named resources-live member @+0xE494 (setter or friend-store), and a typed handle for the PreUpdateOutput+0x2A0 audio-effects message queue hand-off.
8. `EffectsModule` class merge: delete the BrnGameModule.hpp:138 placeholder, include the real header, declare the four virtuals (`Prepare/Update/PreRenderUpdate/DispatchThreadUpdate` — slots +0x40..+0x4C; mind the PC tree's deliberate +1 vtable shift from the added virtual dtor, CgsModule.h banner) and `RestartEffects`.
9. `EffectsModule::Update @0x8229EC28` itself + its callee tree (§3.3) — the big rock: ~30 module methods, the real ParticleModule (retiring `ParticleModuleBringUp.cpp`, build line 454), `BrnReplays::EffectsSerialiser` (Read/Write/GetStaticLayout), `BoostStateMachine::SetWorldIndex`, `PropCollisions::UpdateLocatorVfx`, `TrailSystem::UpdateTrailType`, the Attrib surface/visualfxsurface walk, `RCEntityActiveRaceCarOutputInterface` accessors.
10. `EffectsModule::RestartEffects @0x822793E0` (pad-combo path; small).
11. Build list: add EffectsModule.cpp + the three SharedIO TUs (+ new bridge TUs) to `tools/build/build_game_exe.bat`.

Dispatch leg (BridgeRendererToEffects proper — per the PARKED DELETE-WHEN):
12. `BrnGameModule::BridgeRendererToEffects` — new (§2); needs `DispatchInputBuffer::SetDispatchFrame` (or friend access to mpDispatchFrame).
13. A live `EffectsIO::DispatchInputBuffer` instance on the dispatch path (console: IOHelper carve in DoDispatch; PC: DoDispatch is still bring-up staging, so the buffer + W/R lock bracket must be introduced wherever the PC dispatch seam lands).
14. The env-map source: PC equivalent of `dword_83011AF4` = the env-map render-target texture the reflections wave already builds (renderer pool slot 3) — expose it where the bridge can reach it (the console global block is renderer-Construct-seeded).
15. Consumers to make it non-fabrication (the PARKED note's own bar): `EffectsModule::GenerateDispatchLists @0x82296668` + `BridgeWorldToEffects_Dispatch @0x823C11F8` (key-light/white-level fill) + `DispatchThreadUpdate @0x8227FE88` / `PreRenderUpdate @0x8227FE10`; then retire the five BLOCKED ParticleRenderData fields and the `PCBringUpProduceParticleRenderData` stand-in (BrnGameModule.cpp DELETE-WHEN block).

Already home, no work: all EffectsIO accessor bodies listed in §5.1, the six source-module
output-buffer accessors, `VEQ<13312,16>::Append`, `PerfMonCpu` pair, the assert triple,
`GameDataIO::OutputBuffer::GetLive`, `ConstructUpdateSet`.
