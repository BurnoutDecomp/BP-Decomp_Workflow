# X360 `DoUpdate` sound/gameplay spine decode

Ground truth used throughout: the `assembly` fields of the per-function dossiers under `.ida-exports/BURNOUT_X360_ARTIST.XEX/`. Function names below are copied from each addressed function's own `name` field. Where an exported name is visibly truncated, it is left truncated and called out rather than completed by inference. Pseudocode was not used as evidence for any conclusion in this report.

## 1. Caller list

`rg -l --fixed-strings 826FB238 .ida-exports\BURNOUT_X360_ARTIST.XEX` returned 37 dossiers. `rg -l --fixed-strings 826EB928 ...` returned 14. Most hits are the targets' own dossiers or reverse-reference metadata in dossiers for functions called by the targets. Checking the caller dossiers' `xrefs_from` arrays and their `bl` instructions leaves these genuine direct call sites:

| Target | Caller dossier | Caller `name` field | Direct call instruction | Disposition |
|---|---:|---|---:|---|
| `0x826FB238`, `BrnSound::Module::RootSoundModule::Update` | `0x823DCEC0` | `BrnGame::BrnGameModule::DoUpdate_Sound` | `0x823DD054` | Gameplay sound-update wrapper; decoded below and traced upward to the in-game pump. |
| `0x826FB238`, `BrnSound::Module::RootSoundModule::Update` | `0x823F22D8` | `LoadingScriptedState::Update` | `0x823F2AC8` | Already decoded elsewhere; listed as requested and skipped here. |
| `0x826EB928`, `BrnSound::Module::RootSoundModule::PreUpdate` | `0x823EE4D8` | `BrnGame::BrnGameModule::DoPreUpdate_Sound` | `0x823EE524` | Gameplay sound-preupdate wrapper; decoded below and traced upward to the in-game pump. |

There are no other genuine direct call sites in the literal-hit sets. The two gameplay wrappers both identify `0x823F0AF8`, whose own dossier name is `BrnGame::BrnGameModule::DoUpdate`, as their caller (`xrefs_to`). This is the actual in-game per-frame pump.

## 2. In-game pump decode

### Pump identity and high-level position

The in-game pump is `BrnGame::BrnGameModule::DoUpdate @ 0x823F0AF8`. Its direct scheduler order around sound is:

`DoUpdate_InputPreWorld @ 0x823C5650` -> `DoUpdate_NetworkPreSim @ 0x823C5858` -> `DoUpdate_GameStatePreWorld @ 0x823EE0E8` -> `DoUpdate_ReplaysPreSim @ 0x823DD2A0` -> `DoUpdate_GuiPreWorld @ 0x823DCD78` -> `DoPreUpdate_Sound @ 0x823EE4D8` -> `ConstructUpdateSet @ 0x823DCB40` -> `DoUpdate_World @ 0x823E8BD0` -> `DoUpdate_InputPostWorld @ 0x823C59E8` -> `DoUpdate_Director @ 0x823E8DE0` -> `DoUpdate_GUI @ 0x823F0758` -> `DoUpdate_DirectorPostGUI @ 0x823DCE38` -> `DoUpdate_Effects @ 0x823DD0A8` -> `DoUpdate_Sound @ 0x823DCEC0` -> `DoUpdate_ReplaysPostSim @ 0x823DD408` -> `DoUpdate_GameStatePostWorld @ 0x823E92A8` -> `DoUpdate_NetworkPostSim @ 0x823EE580`.

Thus sound has two distinct legs: a preupdate before the world, and the full update after the world, director, GUI, and effects.

### Sound IO-buffer acquisition, in console instruction order

1. The parent pump first acquires the persistent-per-pump sound **root output** buffer:
   - `0x823F0C84-0x823F0C94`: `r3` is loaded from the output-stack holder at `this + 0x996F04`; `r4` is the address of the local buffer slot; `r5` is the literal `"Sound"`.
   - `0x823F0C98`: call `0x823AD458`, whose own name field is the truncated `??$CreateIOBuffer@VRootOutputBuffer@Io@Module@BrnSound@@@IOBufferStack@CgsModule@@QAA_NPAPAVRootOutputBuffer@Io@Module@`.
   - In that helper's own assembly, `0x823AD4F0-0x823AD4FC` calls `CgsModule::IOBufferStack::Alloc @ 0x8286EDE8` with size `0x1850` and the supplied name; if non-null, `0x823AD50C` calls `BrnSound::Module::Io::RootOutputBuffer::Construct @ 0x826AF448`.
   - `0x823F0C9C-0x823F0CBC` conditionally runs the standard assert triple if creation failed.

2. After the replay pre/post and effects output buffers, the parent acquires the sound **root preupdate output** buffer:
   - `0x823F0D74-0x823F0D84`: the same output stack is put in `r3`; `r4` addresses the local buffer slot; `r5` is the literal `"SoundRootPreUpdateOutput"`.
   - `0x823F0D88`: call `0x823AD528`, own name field (truncated) `??$CreateIOBuffer@VRootPreUpdateOutputBuffer@Io@Module@BrnSound@@@IOBufferStack@CgsModule@@QAA_NPAPAVRootPreUpdateOutpu`.
   - In that helper, `0x823AD5C0-0x823AD5CC` calls `CgsModule::IOBufferStack::Alloc @ 0x8286EDE8` with size `0x338`; `0x823AD5DC` conditionally calls `BrnSound::Module::Io::RootPreUpdateOutputBuffer::Construct @ 0x826C8348`.
   - `0x823F0D8C-0x823F0DAC` conditionally asserts on failure.

3. The full post-world sound wrapper acquires a temporary sound **root input** buffer:
   - In `BrnGame::BrnGameModule::DoUpdate_Sound @ 0x823DCEC0`, `0x823DCF0C-0x823DCF1C` puts the wrapper's incoming `r4` stack in `r3`, a local pointer slot in `r4`, and literal `"Sound"` in `r5`.
   - `0x823DCF20`: call `0x823AD380`, own name field (truncated) `??$CreateIOBuffer@VRootInputBuffer@Io@Module@BrnSound@@@IOBufferStack@CgsModule@@QAA_NPAPAVRootInputBuffer@Io@Module@Br`.
   - In that helper, `0x823AD418-0x823AD428` calls `CgsModule::IOBufferStack::Alloc @ 0x8286EDE8` with size `0x13740`; `0x823AD438` conditionally calls `BrnSound::Module::Io::RootInputBuffer::Construct @ 0x826C81D8`.
   - The wrapper destroys this temporary input after the sound monitor stops, at `0x823DD070`, through `0x823C7918` (own exported name truncated to `??$DestroyIOBuffer@VRootInputBuffer@Io@Module@BrnSound@@@IOBufferStack@CgsModule@@QAA_NPAPAVRootInputBuffer@Io@Module@B`).

No `GetBuffer` call is present in these three acquisition paths. The observed helper implementation is `IOBufferStack::Alloc` followed by the type's `Construct`; this is stated explicitly because the assembly does not support substituting a guessed `GetBuffer` path.

### Preupdate and relationship to the world update

- Parent `0x823F12E4-0x823F1300`: `r3 = this`, `r4 = *[this + 0x996F04]` (the output stack), `r5 =` the `SoundRootPreUpdateOutput` buffer, and `r6 = *[this + 0x9A0BCC]`; call `BrnGame::BrnGameModule::DoPreUpdate_Sound @ 0x823EE4D8` at `0x823F1300`.
- Wrapper `0x823EE514-0x823EE524`: `r3 = this + 0x8A7D00`, `r4 =` incoming output stack, `r5 =` incoming root-preupdate output; call `BrnSound::Module::RootSoundModule::PreUpdate @ 0x826EB928` at `0x823EE524`.
- The wrapper then performs its preupdate-output forwarding/training leg at `0x823EE528-0x823EE564`, including exported `sub_823B6FE0 @ 0x823B6FE0`, accessor `BrnSound::Module::Io::RootPreUpdateOutputBuffer::Ge @ 0x823B8BB8` (name is truncated in its own dossier), queue append `0x823DAF20`, `BrnGame::BrnGameModule::BridgeSoundToTraining @ 0x823C63C0`, and `sub_823B7060 @ 0x823B7060`.
- Only after this does the parent call `BrnGame::BrnGameModule::ConstructUpdateSet @ 0x823DCB40` (`0x823F13CC`), then `BrnGame::BrnGameModule::DoUpdate_World @ 0x823E8BD0` (`0x823F14B4`).

Inside `DoUpdate_World`, the world-input bridge order is controller (`0x823E8C9C`), network (`0x823E8CAC`), game state (`0x823E8CBC`), GUI (`0x823E8CCC`), replay status (`0x823E8CD4`/`0x823E8CE0`), then sound. `0x823E8CE4-0x823E8CF0` passes `r3 = this`, `r4 =` world update input, and `r5 =` the preupdate sound output, then calls `BrnGame::BrnGameModule::BridgeSoundToWorld @ 0x823CDC98` at `0x823E8CF0`. This happens before the actual world update: the normal path calls the world-module virtual at `0x823E8D64`; the update-set `0x20` path instead calls `WorldModule::UpdateForBootUpVideo @ 0x827CFDE0` at `0x823E8D6C`.

After the world returns, the parent executes input-post-world, director, GUI, director-post-GUI, and effects before calling `DoUpdate_Sound` at `0x823F19E8`.

### Post-world bridges and `RootSoundModule::Update`

Within `DoUpdate_Sound`, the relevant console order is:

1. `0x823DCF20`: create the root sound input described above; `0x823DCF74`: `sub_823B7620 @ 0x823B7620` initializes/collects inputs.
2. `0x823DCF80`: `CgsModule::IOBuffer::LockForRead @ 0x82204C88` on the incoming buffer held in stack argument `+0x5C`.
3. `0x823DCF88-0x823DCF98`: call `BrnGame::BrnGameModule::BridgeWorldToSound @ 0x823CD580` with `r3 = this`, `r4 =` root sound input, `r5 =` world output, and `r6 =` the zero-extended update-set halfword.
4. `0x823DCFA0`: `BrnDirector::DirectorIO::OutputBuffer::GetCameraOutput @ 0x823B3308`; `0x823DCFAC`: `BrnSound::Module::Io::RootInputBuffer::SetCameraInput @ 0x823C9140`.
5. `0x823DCFB0-0x823DCFBC`: `BrnGame::BrnGameModule::BridgeGameStateToSound @ 0x823CDE50` with the root input and game-state output.
6. `0x823DCFC0-0x823DCFD4`: load `r5 = *(this + 0x9A0BD8)` and call `BrnGame::BrnGameModule::BridgeGuiToSound @ 0x823C0A58` with `r3 = this`, `r4 =` root input.
7. `0x823DCFDC`: `BrnReplays::ReplayIO::OutputBuffer_PreSim::GetStatu @ 0x823BB080`; `0x823DCFE8`: `BrnSound::Module::Io::RootInputBuffer::SetReplayStatusInterface @ 0x823B7EC0`.
8. `0x823DD004`: `sub_823B7760 @ 0x823B7760`; `0x823DD00C`: unlock the read buffer through `CgsModule::IOBuffer::UnlockForRead @ 0x82204D50`.
9. `0x823DD010-0x823DD054`: form all final update arguments and call `BrnSound::Module::RootSoundModule::Update @ 0x826FB238`.

The four requested bridges therefore sit in exact gameplay order as:

`BridgeSoundToWorld @ 0x823CDC98` **inside the pre-world/world-input leg** -> actual world update -> `BridgeWorldToSound @ 0x823CD580` -> `BridgeGameStateToSound @ 0x823CDE50` -> `BridgeGuiToSound @ 0x823C0A58` **inside the post-world sound-input leg** -> `RootSoundModule::Update @ 0x826FB238`.

The update call's exact register arguments, all established at `0x823DD010-0x823DD054`, are:

| ABI location | Assembly-derived value |
|---|---|
| `r3` | `this + 0x8A7D00` (`addis ...,0x8A`; `addi ...,0x7D00`). |
| `f1` | f32 product `*(float *)(this + 0x9A0AE4) * *(float *)(this + 0x9A0AE0)`, from two `lfs` and `fmuls f1` at `0x823DD040-0x823DD050`. |
| `f2` | f32 product `*(float *)(this + 0x9A0B00) * *(float *)(this + 0x9A0AFC)`, from two `lfs` and `fmuls f2` at `0x823DD02C-0x823DD03C`. |
| `r6` | The wrapper's incoming `r4` (`r25`): input IO-buffer stack. (`r4`/`r5` argument slots are consumed by the two floating arguments under this PPC ABI.) |
| `r7` | The wrapper's incoming `r5` (`r19`): output IO-buffer stack. |
| `r8` | The temporary root sound input buffer (`r30`). |
| `r9` | The wrapper's incoming `r10` (`r18`): the parent pump's `"Sound"` root output buffer. |
| `r10` | `r20`, loaded with `lhz` at `0x823DCF84`: the zero-extended low 16 bits of the value returned by `ConstructUpdateSet @ 0x823DCB40`. In the parent it is retained in `r23`, stored with `sth` at `0x823F19DC`, and received as the wrapper stack halfword at `+0x66`. This is the final integer update-set argument. |

### Sound-to-resource forwarding after update

After `DoUpdate_Sound` returns, and after replay/game-state/network post-simulation plus timer/framerate work, the parent builds the resource input. The sound leg is at `0x823F1F08-0x823F1F34`:

1. `0x823F1F0C`: call `BrnSound::Module::Io::RootOutp @ 0x823B8B10` on the root sound output. The own-dossier name is truncated exactly as shown.
2. `0x823F1F18`: call `BrnResource::GameDataIO::InputBuffe @ 0x823B1830` on the resource input (also a truncated own-dossier name).
3. `0x823F1F20`: forward the first result into the second with `??$Append@$0IAA@$0BA@@?$VariableEventQueue@$0IAAA@$0BA@@CgsModule@@QAA_NABV?$VariableEventQueue@$0IAA@$0BA@@1@@Z @ 0x823CE908`; the assembly comment identifies the instantiated operation as `VariableEventQueue<32768,16>::Append<2048,16>`.
4. `0x823F1F28`: call `BrnSound::Module::Io::RootOutputBuffer::G @ 0x823B8A68` (own name truncated).
5. `0x823F1F34`: pass that result to `??$AppendRequestInterface@$0BAAA@@InputBuffer@GameDataIO@BrnResource@@QAAXPBV?$RequestInterface@$0BAAA@@12@@Z @ 0x823C76B8`; the assembly comment identifies this as `GameDataIO::InputBuffer::AppendRequestInterface<4096>`.

So there are two post-update sound-to-resource forwards: a `2048`-byte event-queue interface append and a `4096` request-interface append.

### PerfMon brackets

- Parent setup/output-buffer acquisition: `StartMonitor @ 0x821F1198` at `0x823F0B1C` using `*(this + 0x996F30)`; the sound output and sound preupdate output buffers are created inside this bracket; `StopMonitor @ 0x821F1308` at `0x823F0DEC`.
- `DoPreUpdate_Sound`: outer start at `0x823EE500` using `*(this + 0x996F34)`, inner sound start at `0x823EE510` using `*(this + 0x996FB4)`, then stops in reverse order at `0x823EE56C` and `0x823EE574`.
- `DoUpdate_World`: start at `0x823E8C08` using `*(this + 0x996F54)`; all input bridges including `BridgeSoundToWorld` are inside; stop at `0x823E8D1C`. The actual normal/boot-video world update follows this stop.
- `DoUpdate_Sound`: outer start at `0x823DCEF8` using `*(this + 0x996F34)`, inner sound start at `0x823DCF08` using `*(this + 0x996FB4)`, then stops in reverse order at `0x823DD05C` and `0x823DD064`. Root-input creation, all post-world bridges, and `RootSoundModule::Update` are inside these nested brackets; root-input destruction follows the stops.
- Resource-forwarding tail: the parent starts `*(this + 0x996F28)` at `0x823F1CEC` and stops it at `0x823F203C`. The sound-to-resource queue/request forwards at `0x823F1F0C-0x823F1F34` are inside this bracket.

## 3. `DoUpdate_World` module walk

### Caller hunt and caller identity

`rg -l --fixed-strings 823E8BD0 .ida-exports\BURNOUT_X360_ARTIST.XEX` returned 24 dossiers. Inspecting which hit contains the target in `xrefs_from` and a real `bl` leaves exactly one caller:

- Caller dossier: `0x823F0AF8`
- Caller own `name`: `BrnGame::BrnGameModule::DoUpdate`
- Call instruction: `0x823F14B4  bl BrnGame__BrnGameModule__DoUpdate_World`
- Callee own `name`: `BrnGame::BrnGameModule::DoUpdate_World @ 0x823E8BD0`.

The final bullet above deliberately restates both own-dossier names; there are no additional callers.

### How the full call stream is represented

`BrnGame::BrnGameModule::DoUpdate` contains 432 direct `bl` instructions and no `bctrl`. Most of the count is an unrolled conditional memory-audit sequence after every scheduler phase. To keep every call explicit without hiding the scheduler under hundreds of repeated names, the exact two conditional sub-sequences are defined once and every occurrence/call site is enumerated below.

**Assert sequence `A`**, executed only when the immediately preceding create/destroy/check fails:

1. `CgsDev::Assert::BeginAssert @ 0x82817548`
2. `CgsDev::Assert::FireAssert @ 0x82820810`
3. `CgsDev::Assert::EndAssert @ 0x82817558`

**Memory-audit sequence `M`**, in exact order:

1. Unconditional `BrnResource::GetAvailableMemory @ 0x82661A38`.
2. If the available-memory value changed and logging is enabled: `CgsDev::StrStreamBase::operator<< @ 0x821F01A8` -> `sub_821F0E50 @ 0x821F0E50` -> `CgsDev::StrStreamBase::operator<< @ 0x821F01A8` -> the same `operator<<` -> the same `operator<<` -> `sub_821F0EC8 @ 0x821F0EC8` -> `operator<< @ 0x821F01A8` -> `sub_821F0EC8 @ 0x821F0EC8` -> `operator<< @ 0x821F01A8`.
3. If the global failure byte is enabled after a memory change: assert sequence `A`.

The following table gives all 22 `M` instances. In each row, `check` is step 1; the nine comma-separated `log` addresses map positionally to the nine calls in step 2; the final three addresses map to `A`. This is also their chronological order.

| After phase | `check` call site | Nine conditional `log` call sites | Conditional `A` call sites |
|---|---:|---|---|
| reusable allocator `FreeAll` | `0x823F0E6C` | `0x823F0ED8, 0x823F0EE0, 0x823F0EE8, 0x823F0EF0, 0x823F0EF8, 0x823F0F00, 0x823F0F08, 0x823F0F10, 0x823F0F18` | `0x823F0F2C, 0x823F0F3C, 0x823F0F40` |
| input pre-world | `0x823F0F60` | `0x823F0F88, 0x823F0F90, 0x823F0F98, 0x823F0FA0, 0x823F0FA8, 0x823F0FB0, 0x823F0FB8, 0x823F0FC0, 0x823F0FC8` | `0x823F0FDC, 0x823F0FEC, 0x823F0FF0` |
| network pre-sim | `0x823F1014` | `0x823F103C, 0x823F1044, 0x823F104C, 0x823F1054, 0x823F105C, 0x823F1064, 0x823F106C, 0x823F1074, 0x823F107C` | `0x823F1090, 0x823F10A0, 0x823F10A4` |
| game state pre-world | `0x823F10D0` | `0x823F10F8, 0x823F1100, 0x823F1108, 0x823F1110, 0x823F1118, 0x823F1120, 0x823F1128, 0x823F1130, 0x823F1138` | `0x823F114C, 0x823F115C, 0x823F1160` |
| replays pre-sim | `0x823F1184` | `0x823F11AC, 0x823F11B4, 0x823F11BC, 0x823F11C4, 0x823F11CC, 0x823F11D4, 0x823F11DC, 0x823F11E4, 0x823F11EC` | `0x823F1200, 0x823F1210, 0x823F1214` |
| GUI pre-world | `0x823F1250` | `0x823F1278, 0x823F1280, 0x823F1288, 0x823F1290, 0x823F1298, 0x823F12A0, 0x823F12A8, 0x823F12B0, 0x823F12B8` | `0x823F12CC, 0x823F12DC, 0x823F12E0` |
| sound preupdate | `0x823F1304` | `0x823F1330, 0x823F1338, 0x823F1340, 0x823F1348, 0x823F1350, 0x823F1358, 0x823F1360, 0x823F1368, 0x823F1370` | `0x823F1388, 0x823F1398, 0x823F139C` |
| construct update set | `0x823F13DC` | `0x823F1408, 0x823F1410, 0x823F1418, 0x823F1420, 0x823F1428, 0x823F1430, 0x823F1438, 0x823F1440, 0x823F1448` | `0x823F1460, 0x823F1470, 0x823F1474` |
| world | `0x823F14B8` | `0x823F14E4, 0x823F14EC, 0x823F14F4, 0x823F14FC, 0x823F1504, 0x823F150C, 0x823F1514, 0x823F151C, 0x823F1524` | `0x823F153C, 0x823F154C, 0x823F1550` |
| input post-world | `0x823F1570` | `0x823F159C, 0x823F15A4, 0x823F15AC, 0x823F15B4, 0x823F15BC, 0x823F15C4, 0x823F15CC, 0x823F15D4, 0x823F15DC` | `0x823F15F4, 0x823F1604, 0x823F1608` |
| director | `0x823F1644` | `0x823F1670, 0x823F1678, 0x823F1680, 0x823F1688, 0x823F1690, 0x823F1698, 0x823F16A0, 0x823F16A8, 0x823F16B0` | `0x823F16C8, 0x823F16D8, 0x823F16DC` |
| GUI | `0x823F1780` | `0x823F17AC, 0x823F17B4, 0x823F17BC, 0x823F17C4, 0x823F17CC, 0x823F17D4, 0x823F17DC, 0x823F17E4, 0x823F17EC` | `0x823F1804, 0x823F1814, 0x823F1818` |
| director post-GUI | `0x823F1840` | `0x823F186C, 0x823F1874, 0x823F187C, 0x823F1884, 0x823F188C, 0x823F1894, 0x823F189C, 0x823F18A4, 0x823F18AC` | `0x823F18C4, 0x823F18D4, 0x823F18D8` |
| effects | `0x823F1914` | `0x823F1940, 0x823F1948, 0x823F1950, 0x823F1958, 0x823F1960, 0x823F1968, 0x823F1970, 0x823F1978, 0x823F1980` | `0x823F1998, 0x823F19A8, 0x823F19AC` |
| sound update | `0x823F19EC` | `0x823F1A18, 0x823F1A20, 0x823F1A28, 0x823F1A30, 0x823F1A38, 0x823F1A40, 0x823F1A48, 0x823F1A50, 0x823F1A58` | `0x823F1A70, 0x823F1A80, 0x823F1A84` |
| replays post-sim | `0x823F1AB8` | `0x823F1AE4, 0x823F1AEC, 0x823F1AF4, 0x823F1AFC, 0x823F1B04, 0x823F1B0C, 0x823F1B14, 0x823F1B1C, 0x823F1B24` | `0x823F1B3C, 0x823F1B4C, 0x823F1B50` |
| game state post-world | `0x823F1B7C` | `0x823F1BA8, 0x823F1BB0, 0x823F1BB8, 0x823F1BC0, 0x823F1BC8, 0x823F1BD0, 0x823F1BD8, 0x823F1BE0, 0x823F1BE8` | `0x823F1C00, 0x823F1C14, 0x823F1C18` |
| network post-sim | `0x823F1C48` | `0x823F1C74, 0x823F1C7C, 0x823F1C84, 0x823F1C8C, 0x823F1C94, 0x823F1C9C, 0x823F1CA4, 0x823F1CAC, 0x823F1CB4` | `0x823F1CCC, 0x823F1CDC, 0x823F1CE0` |
| timers | `0x823F1D00` | `0x823F1D2C, 0x823F1D34, 0x823F1D3C, 0x823F1D44, 0x823F1D4C, 0x823F1D54, 0x823F1D5C, 0x823F1D64, 0x823F1D6C` | `0x823F1D84, 0x823F1D94, 0x823F1D98` |
| frame-rate type | `0x823F1DA8` | `0x823F1DD4, 0x823F1DDC, 0x823F1DE4, 0x823F1DEC, 0x823F1DF4, 0x823F1DFC, 0x823F1E04, 0x823F1E0C, 0x823F1E14` | `0x823F1E2C, 0x823F1E3C, 0x823F1E40` |
| resource staging | `0x823F1F70` | `0x823F1F9C, 0x823F1FA4, 0x823F1FAC, 0x823F1FB4, 0x823F1FBC, 0x823F1FC4, 0x823F1FCC, 0x823F1FD4, 0x823F1FDC` | `0x823F1FF4, 0x823F2004, 0x823F2008` |
| input-to-game/final timer sample | `0x823F2040` | `0x823F206C, 0x823F2074, 0x823F207C, 0x823F2084, 0x823F208C, 0x823F2094, 0x823F209C, 0x823F20A4, 0x823F20AC` | `0x823F20C0, 0x823F20D0, 0x823F20D4` |

### Complete ordered direct-call walk

With `A` and every `M` expanded above, the parent function's complete call order is:

1. Prologue and baseline:
   - `0x823F0AFC` -> `__savegprlr_14 @ 0x82C08EB0`.
   - `0x823F0B08` -> `BrnResource::GetAvailableMemory @ 0x82661A38` (baseline value).
   - `0x823F0B1C` -> `CgsDev::PerfMonCpu::StartMonitor @ 0x821F1198`.
   - `0x823F0B20` -> `CgsSystem::GetSystemTimerBaseTime @ 0x828D75A0`.
   - `0x823F0B28` -> `BrnGame::BrnGameModule::ConstructUpdateSetFromFsm @ 0x823BD420`.

2. Output/input buffer construction. Each create is followed, only on failure, by `A` at the three listed sites:
   - `0x823F0B50` -> `??$CreateIOBuffer@VOutputBuffer@InputIO@CgsInput@@@IOBufferStack@CgsModule@@QAA_NPAPAVOutputBuffer@InputIO@CgsInput@@PB @ 0x823AD2B0`; `A = 0x823F0B74/0x823F0B84/0x823F0B88`.
   - `0x823F0BA8` -> `??$CreateIOBuffer@VOutputBuffer@BrnNetworkModuleIO@BrnNetwork@@@IOBufferStack@CgsModule@@QAA_NPAPAVOutputBuffer@BrnNetw @ 0x823AD948`; `A = 0x823F0BB8/0x823F0BC8/0x823F0BCC`.
   - `0x823F0BE4` -> `??$CreateIOBuffer@VOutputBuffer@GameStateModuleIO@BrnGameState@@@IOBufferStack@CgsModule@@QAA_NPAPAVOutputBuffer@GameSt @ 0x823AC6E8`; `A = 0x823F0BF4/0x823F0C04/0x823F0C08`.
   - `0x823F0C20` -> `??$CreateIOBuffer@VUpdateOutputBuffer@BrnWorldIO@@@IOBufferStack@CgsModule@@QAA_NPAPAVUpdateOutputBuffer@BrnWorldIO@@PB @ 0x823AD100`; `A = 0x823F0C30/0x823F0C40/0x823F0C44`.
   - `0x823F0C5C` -> `??$CreateIOBuffer@VInputBuffer@DirectorIO@BrnDirector@@@IOBufferStack@CgsModule@@QAA_NPAPAVInputBuffer@DirectorIO@BrnDi @ 0x823AE280`; `A = 0x823F0C6C/0x823F0C7C/0x823F0C80`.
   - `0x823F0C98` -> truncated root-sound-output create name recorded in section 2, target `0x823AD458`; `A = 0x823F0CA8/0x823F0CB8/0x823F0CBC`.
   - `0x823F0CD4` -> `??$CreateIOBuffer@VOutputBuffer_PreSim@ReplayIO@BrnReplays@@@IOBufferStack@CgsModule@@QAA_NPAPAVOutputBuffer_PreSim@Rep @ 0x823AE428`; `A = 0x823F0CE4/0x823F0CF4/0x823F0CF8`.
   - `0x823F0D10` -> `??$CreateIOBuffer@VOutputBuffer_PostSim@ReplayIO@BrnReplays@@@IOBufferStack@CgsModule@@QAA_NPAPAVOutputBuffer_PostSim@R @ 0x823AE5D0`; `A = 0x823F0D20/0x823F0D30/0x823F0D34`.
   - `0x823F0D4C` -> `??$CreateIOBuffer@VOutputBuffer@EffectsIO@BrnEffects@@@IOBufferStack@CgsModule@@QAA_NPAPAVOutputBuffer@EffectsIO@BrnEff @ 0x823AE778`; `A = 0x823F0D5C/0x823F0D6C/0x823F0D70`.
   - `0x823F0D88` -> truncated root-sound-preupdate-output create name recorded in section 2, target `0x823AD528`; `A = 0x823F0D98/0x823F0DA8/0x823F0DAC`.
   - `0x823F0DE4` -> `BrnGame::BrnGameModule::BridgeTimers @ 0x823BD150`.
   - `0x823F0DEC` -> `CgsDev::PerfMonCpu::StopMonitor @ 0x821F1308`.

3. Resource-live sample and reusable allocator:
   - `0x823F0DFC` -> `CgsDev::PerfMonCpu::StartMonitor @ 0x821F1198`.
   - `0x823F0E04` -> `CgsModule::IOBuffer::LockForRead @ 0x82204C88`.
   - `0x823F0E0C` -> `BrnResource::GameDataIO::OutputBuffer::GetLive @ 0x823B1638`.
   - `0x823F0E20` -> `CgsModule::IOBuffer::UnlockForRead @ 0x82204D50`.
   - `0x823F0E28` -> `CgsDev::PerfMonCpu::StopMonitor @ 0x821F1308`.
   - If the reusable allocator is null, `A` at `0x823F0E48/0x823F0E5C/0x823F0E60`.
   - `0x823F0E68` -> `CgsMemory::LinearMalloc::FreeAll @ 0x82866E60`.
   - Then the first `M` row (`0x823F0E6C` onward).

4. Straight-line per-frame scheduler. Each arrow is immediately followed by the correspondingly labeled `M` row above:
   - `0x823F0F58` -> `BrnGame::BrnGameModule::DoUpdate_InputPreWorld @ 0x823C5650` -> `M(input pre-world)`.
   - `0x823F1010` -> `BrnGame::BrnGameModule::DoUpdate_NetworkPreSim @ 0x823C5858` -> `M(network pre-sim)`.
   - `0x823F10CC` -> `BrnGame::BrnGameModule::DoUpdate_GameStatePreWorld @ 0x823EE0E8` -> `M(game state pre-world)`.
   - `0x823F1180` -> `BrnGame::BrnGameModule::DoUpdate_ReplaysPreSim @ 0x823DD2A0` -> `M(replays pre-sim)`.
   - `0x823F124C` -> `BrnGame::BrnGameModule::DoUpdate_GuiPreWorld @ 0x823DCD78` -> `M(GUI pre-world)`.
   - `0x823F1300` -> `BrnGame::BrnGameModule::DoPreUpdate_Sound @ 0x823EE4D8` -> `M(sound preupdate)`.
   - `0x823F13B0` -> `CgsDev::PerfMonCpu::StartMonitor @ 0x821F1198`; `0x823F13CC` -> `BrnGame::BrnGameModule::ConstructUpdateSet @ 0x823DCB40`; `0x823F13D8` -> `CgsDev::PerfMonCpu::StopMonitor @ 0x821F1308`; then `M(construct update set)`.
   - `0x823F14B4` -> `BrnGame::BrnGameModule::DoUpdate_World @ 0x823E8BD0` -> `M(world)`.
   - `0x823F156C` -> `BrnGame::BrnGameModule::DoUpdate_InputPostWorld @ 0x823C59E8` -> `M(input post-world)`.
   - `0x823F1640` -> `BrnGame::BrnGameModule::DoUpdate_Director @ 0x823E8DE0` -> `M(director)`.
   - `0x823F177C` -> `BrnGame::BrnGameModule::DoUpdate_GUI @ 0x823F0758` -> `M(GUI)`.
   - `0x823F183C` -> `BrnGame::BrnGameModule::DoUpdate_DirectorPostGUI @ 0x823DCE38` -> `M(director post-GUI)`.
   - `0x823F1910` -> `BrnGame::BrnGameModule::DoUpdate_Effects @ 0x823DD0A8` -> `M(effects)`.
   - `0x823F19E8` -> `BrnGame::BrnGameModule::DoUpdate_Sound @ 0x823DCEC0` -> `M(sound update)`.
   - `0x823F1AB4` -> `BrnGame::BrnGameModule::DoUpdate_ReplaysPostSim @ 0x823DD408` -> `M(replays post-sim)`.
   - `0x823F1B78` -> `BrnGame::BrnGameModule::DoUpdate_GameStatePostWorld @ 0x823E92A8` -> `M(game state post-world)`.
   - `0x823F1C44` -> `BrnGame::BrnGameModule::DoUpdate_NetworkPostSim @ 0x823EE580` -> `M(network post-sim)`.

5. Timers and resource staging:
   - `0x823F1CEC` -> `CgsDev::PerfMonCpu::StartMonitor @ 0x821F1198`.
   - `0x823F1CFC` -> `BrnGame::BrnGameModule::UpdateTimers @ 0x823BCFD0` -> `M(timers)`.
   - `0x823F1DA4` -> `BrnGame::BrnGameModule::UpdateFrameRateType @ 0x823BD0A8` -> `M(frame-rate type)`.
   - `0x823F1E74` -> `sub_823B7B80 @ 0x823B7B80`.
   - `0x823F1E88` -> `BrnGame::BrnGameModule::BridgeGuiToResource @ 0x823EE710`.
   - World resource forwards: `0x823F1E90` -> `BrnWorldIO::UpdateOutputBuffer::GetResour @ 0x823B5780`; `0x823F1E9C` -> `??$AppendRequestInterface@$0BAAA@@InputBuffer@GameDataIO@BrnResource@@QAAXPBV?$RequestInterface@$0BAAA@@12@@Z @ 0x823C76B8`; `0x823F1EA4` -> `BrnWorldIO::UpdateOutputBuffer @ 0x823B5828`; `0x823F1EB0` -> `BrnResource::GameDataIO::InputBuffe @ 0x823B1830`; `0x823F1EB8` -> `??$Append@$0IAA@$0BA@@?$VariableEventQueue@$0IAAA@$0BA@@CgsModule@@QAA_NABV?$VariableEventQueue@$0IAA@$0BA@@1@@Z @ 0x823CE908`.
   - Director resource forwards: `0x823F1EC4` -> `BrnDirector::DirectorIO::Output @ 0x823B24A0`; `0x823F1ED0` -> `BrnResource::GameDataIO::InputBuffe @ 0x823B1830`; `0x823F1ED8` -> `??$Append@$0CAA@$0BA@@?$VariableEventQueue@$0IAAA@$0BA@@CgsModule@@QAA_NABV?$VariableEventQueue@$0CAA@$0BA@@1@@Z @ 0x823C7F28`; `0x823F1EE0` -> `BrnDirector::DirectorIO::OutputBuffer::Get @ 0x823B33B0`; `0x823F1EEC` -> `??$AppendRequestInterface@$0CAA@@InputBuffer@GameDataIO@BrnResource@@QAAXPBV?$RequestInterface@$0CAA@@12@@Z @ 0x823CEAC0`.
   - Game-state resource forward: `0x823F1EF8` -> `BrnGameState::GameStateModuleIO::OutputBu @ 0x823B9798`; `0x823F1F04` -> `??$AppendRequestInterface@$0MAA@@InputBuffer@GameDataIO@BrnResource@@QAAXPBV?$RequestInterface@$0MAA@@12@@Z @ 0x823EDF88`.
   - Sound resource forwards: the five calls at `0x823F1F0C/0x823F1F18/0x823F1F20/0x823F1F28/0x823F1F34`, with targets and exact own names recorded in section 2.
   - Replay resource forward: `0x823F1F3C` -> `BrnReplays::ReplayIO::OutputBuffer_PreSim @ 0x823BB128`; `0x823F1F48` -> `??$AppendRequestInterface@$0EAA@@InputBuffer@GameDataIO@BrnResource@@QAAXPBV?$RequestInterface@$0EAA@@12@@Z @ 0x823EE038`.
   - `0x823F1F6C` -> `sub_823B7D20 @ 0x823B7D20` -> `M(resource staging)`.
   - `0x823F2014` -> `CgsModule::IOBuffer::LockForRead @ 0x82204C88`; `0x823F2020` -> `BrnGame::BrnGameModule::BridgeInputToGame @ 0x823BD248`; `0x823F2028` -> `CgsModule::IOBuffer::UnlockForRead @ 0x82204D50`.
   - `0x823F202C` -> `CgsSystem::GetSystemTimerBaseTime @ 0x828D75A0`; `0x823F2030` -> `CgsSystem::GetSystemTimerFrequency @ 0x828D75C8`; `0x823F203C` -> `CgsDev::PerfMonCpu::StopMonitor @ 0x821F1308`; then `M(input-to-game/final timer sample)`.

6. Reverse-order buffer destruction. Each destroy is followed on failure by `A` at the three listed sites:
   - `0x823F20E0` -> `??$DestroyIOBuffer@VRootPreUpdateOutputBuffer@Io@Module@BrnSound@@@IOBufferStack@CgsModule@@QAA_NPAPAVRootPreUpdateOutp @ 0x823C7768`; `A = 0x823F20F8/0x823F210C/0x823F2110`.
   - `0x823F2124` -> `??$DestroyIOBuffer@VOutputBuffer@EffectsIO@BrnEffects@@@IOBufferStack@CgsModule@@QAA_NPAPAVOutputBuffer@EffectsIO@BrnEf @ 0x823AE848`; `A = 0x823F2134/0x823F2144/0x823F2148`.
   - `0x823F2154` -> `??$DestroyIOBuffer@VOutputBuffer_PostSim@ReplayIO@BrnReplays@@@IOBufferStack@CgsModule@@QAA_NPAPAVOutputBuffer_PostSim@ @ 0x823AE6A0`; `A = 0x823F2164/0x823F2174/0x823F2178`.
   - `0x823F2184` -> `??$DestroyIOBuffer@VOutputBuffer_PreSim@ReplayIO@BrnReplays@@@IOBufferStack@CgsModule@@QAA_NPAPAVOutputBuffer_PreSim@Re @ 0x823AE4F8`; `A = 0x823F2194/0x823F21A4/0x823F21A8`.
   - `0x823F21B4` -> `??$DestroyIOBuffer@VRootOutputBuffer@Io@Module@BrnSound@@@IOBufferStack@CgsModule@@QAA_NPAPAVRootOutputBuffer@Io@Module @ 0x823C7840`; `A = 0x823F21C4/0x823F21D4/0x823F21D8`.
   - `0x823F21E4` -> `??$DestroyIOBuffer@VInputBuffer@DirectorIO@BrnDirector@@@IOBufferStack@CgsModule@@QAA_NPAPAVInputBuffer@DirectorIO@BrnD @ 0x823AE350`; `A = 0x823F21F4/0x823F2204/0x823F2208`.
   - `0x823F2214` -> `??$DestroyIOBuffer@VUpdateOutputBuffer@BrnWorldIO@@@IOBufferStack@CgsModule@@QAA_NPAPAVUpdateOutputBuffer@BrnWorldIO@@@ @ 0x823AD1D8`; `A = 0x823F2224/0x823F2234/0x823F2238`.
   - `0x823F2244` -> `??$DestroyIOBuffer@VOutputBuffer@GameStateModuleIO@BrnGameState@@@IOBufferStack@CgsModule@@QAA_NPAPAVOutputBuffer@GameS @ 0x823AC7C0`; `A = 0x823F2254/0x823F2264/0x823F2268`.
   - `0x823F2274` -> `??$DestroyIOBuffer@VOutputBuffer@BrnNetworkModuleIO@BrnNetwork@@@IOBufferStack@CgsModule@@QAA_NPAPAVOutputBuffer@BrnNet @ 0x823ADA20`; `A = 0x823F2284/0x823F2294/0x823F2298`.
   - `0x823F22A4` -> `??$DestroyIOBuffer@VOutputBuffer@InputIO@CgsInput@@@IOBufferStack@CgsModule@@QAA_NPAPAVOutputBuffer@InputIO@CgsInput@@@ @ 0x823ADE58`; `A = 0x823F22B4/0x823F22C4/0x823F22C8`.

At `0x823F22D0` the function uses an unlinked tail branch to the epilogue helper `__restgprlr`; it is not a `bl` call and is not present as a callee in the dossier's `xrefs_from`.

### Loop structure

There is no scheduler loop and no other loop in `BrnGame::BrnGameModule::DoUpdate`: a scan of all branch instructions in the authoritative assembly finds **zero backward branches**. The module sequence and the 22 memory-audit blocks are compiler-unrolled straight-line code. Forward conditional branches skip logging/assertion blocks and select error-free paths, but they do not iterate.
