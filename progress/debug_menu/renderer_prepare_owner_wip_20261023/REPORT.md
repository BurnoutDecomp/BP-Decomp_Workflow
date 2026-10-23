# Original renderer prepare owner

The complete original five-stack `BrnGameModule::Prepare` owner is recovered as an isolated, typed source proposal. It preserves GameData readiness and allocator ownership before entering renderer Prepare. It is **not an activation patch**: the original four-argument GameData core and seven AutoTest table targets remain unavailable to the shipping target, and the existing native buffer/sky-dome allocations need a separate integration change.

The proposal is `source/renderer_prepare_owner.patch`, with full files in `source/pre/` and `source/post/`. `SOURCE_MANIFEST.json` binds all 13 changed paths by full pre/post SHA256. Its base is `6e3253f4d1b5b0ea7ead1ddf5eee2685e281f826`; every inspected preimage was also compared byte-for-byte with private successor `e8e4918bae6f71736a191ca17a900f9212e52630` in `BASE_SUCCESSOR_COMPARISON.json`.

No shared source/worktree, Git index/refs, inventory, build, tests, hosted service, executable, game, or input was changed. All writes are under this packet directory. No compile/link/runtime or verified-site credit is claimed. The aggregate remains 50 verified, 7 no-ops, 1298 pending.

## Original owner

ARTIST `main` constructs and prepares five stacks, constructs its one game module, then calls `Prepare` virtually at `0x827E65D4` with those stacks in `r4..r8`. The game-module constructor installs the primary vtable at `0x820D14A8` and the thread-interface vtable at `+0x640`. The Prepare export has no direct-call xrefs because the observed caller is virtual. An empty direct-xref list is not absence of an owner.

ARTIST `0x823DB848` has eight resumable states:

| Stage | Original effect |
| --- | --- |
| 0/1 | Clear termination at START; prepare hardware; initialize the embedded AutoTest manager after hardware succeeds. |
| 2 | Prepare the base; retain update/resource stacks; create persistent GameData input/output buffers on the resource stacks; construct the dispatch pair on its dedicated stack. |
| 3 | Call the original virtual four-argument GameData Prepare with resource stacks and the persistent pair. |
| 4 | Read-lock that GameData output; borrow its allocator list; call the embedded renderer's Prepare; unlock on either result. |
| 5 | Read-lock the same output; initialize Massive heap bank 63 from that same list; unlock on either result. |
| 6 | Begin threads with the three original monitor IDs; set 60 Hz and resource percentage 50; post the initial loading command; prepare the frame-rate manager. |
| 7 | Register the Camera message receiver with this module's context; reset prepare/release stages to START and the system-menu latch to false; return true. |

Incomplete stages at or beyond 3 run CheckDiskError after releasing any renderer/Massive read lock. Hardware failure returns directly. No allocator is fabricated, no offset-cast class is introduced, and the proposal does not register the Renderer component directly.

## Live instance and caller coverage

The private source's boot, update, dispatch, scripted-load accessors, and renderer debug owner converge on the one file-static `gGameModule` in BrnMain and its by-value `mRenderModule`. `GetMainGameModule()` returns that object; `GetRenderModule()` returns that same member. Construct calls `mRenderModule.Construct()`, which constructs its debug component; DispatchThread eventually calls `mRenderModule.Render(...)`.

Renderer `Prepare(const AllocatorList*)` is nonvirtual in both ARTIST's DecFIGS declaration and the current header. Its sole exported **direct** caller is `BrnGameModule::Prepare`, at `0x823DB9F0`. The current base virtual Prepare is zero-argument, as are the buffer Prepare calls in ModuleSingleBufferedTemplate: neither can dispatch to the renderer's required-list overload. The current renderer derives directly from ModuleSingleBuffered. Source inspection found no renderer Prepare call/member-pointer binding and no five-stack game Prepare declaration/body before this proposal. Together these type and owner facts establish the missing C++ lifecycle edge; textual absence or the graph alone was not used as proof. Arbitrary unmodeled binary dispatch is not certified by this source-only packet.

`tools/ida/export_all.py::get_callers` filters to near/far **call** references. It excludes data references and tail jumps. Consequently the exported xref lists are not an exhaustive virtual/function-pointer inventory; this packet separately inspected the original main vcall, the constructor's interface stores, current base declarations, and the module template.

The graphify query was read-only and produced generic import nodes rather than this ownership chain. It supplies no runtime or reachability credit here.

## Bounded dependency recovery

The source proposal also carries the original CheckDiskError observer, the exact GameData output filesystem status at ARTIST `+9`, the Massive member/const-list ABI, the two inlined ThreadLayout setters, and the five bounded AutoTest initialization helpers. The native thread callback's integer/context conversion and absence of X360 D3D thread-ownership release are explicitly marked PC platform leaves.

The filesystem status is distinct from the LiveUpdate byte at `+8`. ARTIST Construct `0x82666908` initializes the IO base, constructs file status at `+9`, and clears the allocator-list pointer; it makes no LiveUpdate store. Getter `0x823B16E0` returns `this+9`. Setter `0x82663EE0` copies one byte to `this+9` under a write-lock assertion. This corrects the current header's unsupported claim that the file-status member was PS3-only drift.

Because original OutputBuffer Construct resets IO lock state, its existing loading initializer now calls it before locking. The existing GameData Update clears only the filesystem-status payload through its typed setter while retaining its current output write lock. It does not re-Construct the IO base during publication. This is narrower than the old checkpoint's construct-before-lock Update adaptation.

The owner and most dependency bodies reuse checkpoint `6c911139683fecc617e6a525a51a255804d291e6`, rechecked against the frozen ARTIST evidence and transplanted as bounded hunks onto the current base. Old whole-file images were not substituted for current sources. The original four-argument GameData declaration is supplied without a fabricated forwarding body.

## Precise remaining boundary

1. Original `GameDataModule::Prepare(IOBufferStack*, IOBufferStack*, const InputBuffer*, OutputBuffer*)` has no body in the current private source. Its ARTIST core includes DLC stages 16â€“18, GameTalk/debug preparation at 7 and another module at 8, original stack-scoped schema/list helper transport, success allocator publication, and failure filesystem-status publication. The later stage-18 packet recovers part of this chain but still defers GameTalk/module preparation and retains shortened helpers; it is not proof of a complete core.
2. The original resource core's four-argument Update/status-production path and its stack-scoped helper must be composed from their exact source evidence. Current two-buffer Update cannot be relabeled as that original API.
3. Six AutoTest Lua callback bodies are absent. PressButton has an existing unmounted source file with a raw offset write; it is not an available, faithful shipping definition. All seven original static callback table targets remain link dependencies even when automatic testing is disabled. The bounded Init/LoadScripts/GetScriptName/OpenLUALibs/LuaAllocator bodies are supplied; no quiet callback stubs are introduced.
4. Native buffer and sky-dome ownership must be reconciled before invoking original renderer Prepare. See `INTEGRATION_PLAN.md`.

`POSTMORTEM.md` records the assembly walk and limits. `EVIDENCE_BINDINGS.md` and `EVIDENCE_MANIFEST.json` bind the original/declaration artifacts. `REVIEW_REQUEST.md` is ready for Root's existing single reviewer; no reviewer was spawned here.
