# Independent five-packet source review

BATCH_VERDICT: fail

Bound source: `2ceaa5e83aa0abaeb1ffde20867061daf953d673` on `codex/renderer-prepare-recovery-20261023`.
Bound workflow parent: `bd9261621c6a420b617ba4fd3a38dbd0a08edee4`; its `b5-decomp` gitlink names that exact source commit.

The GameData core introduces an unterminated include. No other introduced defect was found in the five bounded recoveries. The four passing packet verdicts below concern their source changes; they do not certify the composed tree as buildable. The allocator packet carries the core's already defective header as its preimage and does not introduce a second instance of the defect.

## Confirmed defect

**F1 — high: close the new debug-interface include.** In [the exact composed BrnGameDataModule.h:7](composed/src/GameSource/Resource/BrnGameDataModule.h), the line is:

```cpp
#include "GameShared/GameClasses/Development/DebugSystem/GameTalk/CgsDebugGameTalkInterface.h
```

The opening quote has no closing quote before the newline. This is an invalid preprocessing directive in a canonical header used by the existing GameData/game consumers, even while the new four-argument path is inactive. Add the closing quote. This finding follows directly from the source bytes; no compiler was run.

Origin: `gamedata_original_core/source/post/src/GameSource/Resource/BrnGameDataModule.h:7`, present in that packet's patch. The core postimage has SHA256 `e99d98c52e1a83acb4efdb9d4884496028663536727661588de8dc5fdbaf730a`. The allocator continuation changes other lines and retains this line; the final header has SHA256 `af030488e6ba43ef2c15d1dcfcfc2738caf4e07daaaf187b0f88ca6eda154c82`, Git blob `abd263e96cc4893e2c44807f6e0f3c717311ae58`. This error is absent from the owner/53961615 preimage and introduced by the core packet.

## Verdicts and exact packet bindings

| Packet | Applied source commit | Source-manifest SHA256 | Bounded source verdict |
| --- | --- | --- | --- |
| owner | `53961615f5f9105568fa37a329f79758451c922d` | `21c53be1da9a727c6f4083a381ea4d80020e61f143229780eb140dec25b9108a` | pass |
| autotest_callbacks | `576740f7430b7cdd1364cab6456c5b88a288f691` | `7fb38e54e1e1a4d7e01d622621fa5b62800d0ce76d432c23a8f69e0e605c9398` | pass |
| gamedata_original_core | `57bbdefbbac12c0595d7eeed03de40729d2a14af` | `51d652b98534b8e69d7063b5c94a6a4c747e33a5403fbaed21d9ce83ed771b6b` | fail: F1 |
| gamedata_allocator_prepares | `abcde0e0731587ba4169189918c257c5a3e86ceb` | `b3cf1684892ff734bcbccd1fc311ca3b727fe2acf12759d77e4d31b3b3b63b92` | pass; inherited F1 remains |
| memory_rw_allocator_services | `2ceaa5e83aa0abaeb1ffde20867061daf953d673` | `574715ace79c432b0c1118e470b6af528ea8c4040cb559cb5f19e4b2daa566ff` | pass |

[BINDINGS.json](BINDINGS.json) records every exact preimage/base blob, postimage/applied blob, last composed blob, manifest/seal/evidence hash and the full applied commit identities. All 35 packet file entries match their source manifests and stated Git bases/applied commits. All 28 final path dispositions match the last applicable postimage, including deletion of the legacy callback split. All 194 evidence-manifest entries and 353 packet-seal entries match. These counts include repeated files across packets; they are not reconstruction/inventory credit.

### 1. Outer owner

VERDICT: pass

No introduced source defect found in this bounded packet. [BrnGameModule::Prepare:722](composed/src/GameSource/Game/BrnGameModule.cpp) preserves ARTIST `823DB848`'s eight states and its five-stack ABI (`823DB854–874`), qualified zero-argument base call, persistent GameData IO pair, actual embedded renderer receiver, both read-lock brackets and failure exits, and signed stage>=3 disk-error tail. The GameData call remains the distinct four-argument virtual API; it is not redirected to the native shortcut. The declared five-stack virtual shape agrees with the frozen DecFIGS game declaration.

The ThreadLayout call passes the typed `IThreadClass*` interface, preserves Resource/ThreadSync/WaitOnDispatch monitor order, stores 60 Hz and 50 percent through named fields, and targets the dispatch manager's write buffer. The FrameRateManager side effect remains outside the assertion. The message handler receives the address of the stored context slot under the actual four-argument GameTalk contract, and completion resets the original prepare/release/system-menu fields (`823DBB1C–4C`). The X360 D3D ownership omission is explicitly a PC platform boundary, not claimed as recovered D3D behavior.

[CheckDiskError:810](composed/src/GameSource/Game/BrnGameModule.cpp) matches `823BC798`'s read lock, controller-port choice, process-lifetime one-shot latch and thread parameters. Output construction and the separate filesystem byte match `82666908`, `823B16E0`, cached `82663EE0` and the independent live byte at +8. The bounded Update/initializer corrections respect the existing lock lifetime. AutoTest Init/library/script/table order matches `823C0438`, `823A9150`, `823A9218`, `823A9300` and the frozen table bytes. No claim is made that the existing base factories or native allocation ownership allow this owner to execute.

### 2. AutoTest callbacks

VERDICT: pass

No introduced source defect found. [The seven callbacks:181](composed/src/GameSource/Game/BrnAutoTestManager.cpp) match the original plain Lua callback ABI, arities, optional RecordLog filename, cleanup and zero return. The helper constructor/count are consistent with the inlined prologues and frozen DecFIGS shape. PressButton preserves filter/log/`lua_isstring` order and writes the typed actual AutoTest action owner: `(0x10A6 * 4) == 0x4298`, confirmed against Init's `AutoTest+0x3C50` at game+0x648. Acquire/Relinquish target the same owner's byte at game+0x438C. No bound check or early return was invented.

Debug callbacks use the actual embedded private manager, enabled by narrow friendship. The three added manager methods match `82832200`, `82828E28`, `8282E308`: lookup/delegate, clear found active flag only, and assert UI then call its actual FunctionManager. Existing `GetUI` and `GetFunctionManager` are direct typed member accessors. The obsolete raw-offset callback file is deleted and all seven bodies are in the canonical original TU.

The explicit shipping list/parser inspection establishes the source-availability boundary: the canonical AutoTest and helper TUs are absent from the bound executable source list. No mounting or link readiness is approved by this pass.

### 3. Original GameData core

VERDICT: fail

F1 blocks a source pass. Apart from that syntax defect, no behavioral mismatch was found in [the recovered caller:160](composed/src/GameSource/Resource/BrnGameDataModule.cpp) against ARTIST `82673F38`: every-entry filesystem reset; stages 0/1/2/3/4/5/16/17/18/6/7/8/9/10/11/12/13/14/19; invalid 15/default; actual package count/index/receiver ownership; one pump while waiting; stage18's required yield before the next package; and success-versus-status-failure tails. The misleading `muPackageCount` name is not an unsigned-comparison defect: its bound declaration is `s32`, matching the signed assembly compares.

Attrib allocator evaluation remains 21,20,19,22 before the call with linear,19,20,21,80; the schema input has the original create/destroy lifetime on either result. GameTalk's bool result, actual derived debug component, LiveUpdate call and ICE reset match the inspected targets. AddPatchRequest retains the native receiver pointer and canonical ownership, with native `sizeof` serialization rather than a truncated console pointer. [UpdateResourceModule:142](composed/src/GameSource/Resource/BrnGameDataModule.cpp) preserves the original enum result and output status-copy/destruction lifetime. The shared destruction thunk is a sole branch to IOBuffer::Destruct.

The retained two-argument Prepare body is byte-identical after newline normalization across this packet and the allocator packet; its normalized body SHA256 is `865ac2fec3ceb40862ff75d64de10436e1e8434234b6204f7d8fc09a12a29c1d`. The native DONE7 remains distinct from the original DONE19. Their shared stage storage is an explicit integration boundary; this review does not approve mixing the lifecycles.

### 4. Stack allocation helpers and response/storage shape

VERDICT: pass

No new defect found in this packet's changes. Inherited F1 still prevents a successful composed source result and must be fixed at its core origin. [CreateBanks:465, CreatePools:505 and CreateAllocators:545](composed/src/GameSource/Resource/BrnGameDataModule.cpp) agree with `8266DA28`, `8266DB88`, `8266DD00`: root-excluding bank count is not subtracted twice; old request-count event IDs and copy/queue order are preserved; pool flags are restricted to IDs3/4/15; all five allocator families retain their order, IDs, registry writes and actual generated-object ownership; audio is published without reinitialization; exact outstanding-count equality gates completion; no response-result policy is added.

All pending paths pump then destroy the carved input. The successful paths intentionally retain the original carve rather than receiving an added RAII pop. Reply drain cases 10/11/12/14 preserve the five raw pointers/descriptor pairs and both RW member/registry mirrors, and the invalid-tag assertion continues as in ARTIST. [The canonical responses:270](composed/src/GameShared/GameClasses/Memory/CgsMemoryModuleIO.h) correctly remove the unattested raw allocator tail and second Linear pointer; the producer and out-parameter consumers share one typed contract. The console sizes are raw76 and Linear20, with native widths handled by canonical members/sizeof.

[AllocatorList rows:89](composed/src/GameSource/Resource/SharedIO/BrnGameDataAllocatorList.h) and GameData storage use ARTIST capacities8/9. Pointer-row spans and the constructor's nine heap interiors support those capacities; populated map counts remain7/8. This does not certify the pre-existing initializer's spare-slot behavior. Five native GameData bodies, including Construct and all native helpers, independently match both packet hashes and the final composition.

### 5. RW Linear/General services

VERDICT: pass

No introduced defect found in [Linear:310 and General:393](composed/src/GameShared/GameClasses/Memory/CgsMemoryModule.cpp). Their entire normalized method chunks match both prior56676 and the packet chunk bindings exactly: Linear `49b1b6a8a162508e97ccde5e9f51a5327b297c1317d14907b110b608704045bc`; General `2bd84678a05489bbf2a689a20b708c05d55b6aa7c517e00f0ae01d4130ac669b`. The actual assembly, including General's r3/r4/r5 prologue rather than its incorrect decompiler prototype, agrees with typed const-request/void declarations and dispatcher casts.

Both preserve requested capacity separately from expanded backing requirements, all five parent lookups (including empty lanes), u16 KiB granules, signed quotient/32-bit product, one block per populated lane, unsigned64MiB assertion and signed waste warning with continuation, null backing on failure, unconditional real Initialize, and actual request receiver/id/type/result/pointer replies with native sizeof. Mutable GetBank returns the real MemoryBank view required by GetData. Ten existing MemoryModule methods independently match their packet hashes and final bodies.

## Actual shipping provider resolution

Parentbd926's canonical include file, batch source list and compile driver are byte-identical to the packet's parent19b953 evidence. The quoted rw headers first resolve to `vendor/renderware/include`, after the Memory TU directory and earlier include roots have no matching path. This was checked against the exact source commit, not a src/SDKs mirror or the active working tree. See [the copied include order](shipping/tools/build/msvc_includes.txt) and [BINDINGS.json](BINDINGS.json).

| Selected provider | SHA256 |
| --- | --- |
| `vendor/renderware/include/rw/rwcore_structs.h` | `875f826a99a90e52898df2968a39c74160314646b4a822f2105951ae46970210` |
| `vendor/renderware/include/rw/rwcore_general_alloc.h` | `e7678bdf193b3cf7d41c56d255a86255ef17eb00b7356577376ef98e667511aa` |
| `vendor/renderware/src/rwcore_alloc.cpp` | `dae86d2de81104033784adba6ea88be74576bfb0209c630f8985bb62de7067f1` |
| `vendor/renderware/src/rw/BaseResourceDescriptor.cpp` | `08329bb5c5d058b9d049ecd9334cd6fc498b881bb99e28d6df3ed9735ca92169` |

The selected Resource constructor nulls all five lanes. Linear's descriptor API returns ResourceDescriptor*, General's returns BaseResourceDescriptors<5>*; the supplied canonical output objects satisfy both contracts. Both Initialize methods are actual static pointer-returning methods with const Resource/ResourceDescriptor references and null-lane-zero behavior. Their selected implementations reserve native sizeof/alignof placement storage and preserve requested heap capacity. The explicit list contains their two provider TUs and MemoryModule.cpp; the offline count is3021 entries/3002 unique paths. This is source-resolution evidence only, not a mount/link execution verdict.

## Continuing boundary and review procedure

This is one fresh source reviewer for the entire batch. The five REVIEW_REQUEST entry points led the review; frozen ARTIST assembly arbitrated behavior and calling conventions, DecFIGS supplied declaration shape, and exact Git/vendor bytes arbitrated the composed source/provider contracts. Earlier author postmortems were checked against the actual material rather than accepted as verdicts. No additional agent was used.

No compiler, build, C++ tests, CI, game/input, IDB, activation, source gate or ledger/inventory mutation was run. No normal source, Git ref/index, earlier packet, build configuration, profile or log was changed. New files are confined to this report/binding folder. Read-only Git/blob/hash/source-list inspection and report snapshots are recorded by capture_bindings.py.

Fixing F1 will require a new exact source binding and review result; this report remains bound to source2ceaa5e83. Even a corrected source pass cannot establish link, initialization, mount, activation, registration-site, native readiness or gameplay credit. The original four-argument Resource Update and seven schema/list helpers remain unresolved; current native/raw/wrapper/bank providers are not blanket-approved. Actual GameData member Construct order, renderer new-module seed, game/LiveUpdate factory bindings, native bank capacities/ownership, sky-dome reuse, output-list publication, duplicate LoadingScriptedState preparation and existing ThreadLayout ownership remain integration work owned by Root.
