# Combined fresh source review — GUI prerequisites

Review date: 2026-10-27. This is a read-only source/assembly review of two separate prerequisites. No supplied script, fixture, test, case, checker, runner, compiler or game was executed. No source, Git ref, ledger, profile, or `CON` path was mutated or accessed. Full reviewed artifact hashes are in [EVIDENCE.json](EVIDENCE.json).

## 1. LanguageManager Release and readiness checkpoint

**LanguageManager::Release source correction — VERDICT: pass.**

The packet is pinned to B5 `82a080ef104758d708dd4c687c46e75ffbb9c71d`; it explicitly leaves the paired workflow identity to Root. Its sole source delta changes `CgsLanguage::LanguageManager::Release`. The pinned source preimage blob matches the B5 commit. The 36-byte ARTIST range `0x82864000..0x82864020` has the exact sequence: call `UnloadStringTable` at `0x8286400C`, load return value 1 at `0x82864010`, and return. It has no release-stage, prepare-stage, or allocator-pointer stores. The post body makes those same two operations. The pre/post file hashes are `598f0d867b0a9243ace457cb392d3ae76c3c09b8306a3db915d696f77b0e7a58` and `bbf613bc615bfde06d31cac78756d0cd310f08d3b0d41fbb0e828c9a8bb7e815`; the literal patch hash is `e3d2587530cdf6ca17753c6f19482d71eda9e32302cec9149523a15f20f25367`.

`UnloadStringTable` preserves its original no-table early return. With a loaded table, its existing body resets the hash, frees owned dynamic string copies and nodes through the stored language heap, frees only the nodes for borrowed strings, releases the static element block, and restores default formatting. `LanguageManager::Construct`, `Prepare`, `Destruct`, object members and the container/header layouts are unchanged. The one-file proposal does not clear the allocator pointer or reset lifecycle stages.

The source establishes the positive fresh initialization route: `BrnGameModule::Construct` invokes the GUI constructor; `BrnGui::ViewModule::Construct` chains through the real base view constructor and the contained `LanguageManager::Construct`; then the normal staged `ViewModule::Prepare` calls `LanguageManager::Prepare` before `AptAux::Prepare`. The proposed fix does not change that ordering.

**Complete selected GUI activation/readiness — VERDICT: fail / not ready.**

The exact current `BrnGuiModule::PrepareAptRuntime` source retains two readiness shortcuts: an early return when process-global `s_bRuntimeReady` is true, and a separate live-`GetTarget()` arm that marks the global readiness flags without proving the current contained view ran its language preparation. The Apt source packet’s unchanged `CgsAptAux::Release` is still a state-only transition and does not run the original `UnInitializeApt` sequence. The language receiver’s actual selected-channel producer/whole-input boundaries also remain as recorded in the source packet. These are concrete owner-path gaps; the Release body pass does not close them. Keep `complete_selected_path_ready_for_activation=false` and do not activate the GUI path from this review.

## 2. Apt allocator shutdown helper

**Three source-body recovery claims — VERDICT: pass, bounded to the helper sources.**

The packet is pinned to B5 `fc2bb7a8f40a4db942d3e9f290cb0480ef43f64b` and workflow `dffab36387ac7d33546114ff24ef0ff0846a79c3`. All three preimage Git blobs match the pinned B5 tree. Only `AptInit.cpp`, `AptInit.h`, and `DogmaAllocator.cpp` change. `DogmaAllocator.h`, the manager object members, `AptAllocatorInitialize`, `WireAllocatorGlobals`, the manager constructor/destructor, sized delete, allocation/free paths, and GC iterator bodies are unchanged; exact equality hashes are retained in `UNCHANGED_LIFECYCLE_BODIES.json`.

The authority supports the recovered control and layout:

- ARTIST raw `0x82AE9298..0x82AE9380` retains 236 bytes and 59 instructions. The non-GC diagnostic loop is only list-pointer adjustment/load/test/branch; it contains no call, write, assertion, logging, allocation, or free. Its GC branch calls `GetFirstAptValue` and `GetNextAptValue`; the corresponding ARTIST bodies and native64 `0x140838950` / `0x1408394C0` paths perform read-only pool/list traversal and return pointers, with no omitted calls or reports. The empty C++ loop bodies therefore preserve the valid-list traversal’s observable source effect: none. Corrupt-list fault behavior is not claimed; an optimizing compiler may elide a side-effect-free walk, and no emitted-code result is claimed here.
- Native64 `sub_14082DB90` is cross-referenced from the real owner release at `0x1400C8DE0`. It repeats the same gates and read-only walks, calls the real manager destructor, frees each 72-byte object through the sized host callback, and reloads the GC global after the non-GC free. The candidate’s `delete gpGCPoolManager` likewise reloads the global after deleting the first pool; it does not use the stale cached traversal pointer.
- Native64 initializer `0x14082D9F0` allocates `0x48` bytes for each manager, matching the candidate’s 72-byte assertions. The existing placement construction uses `sizeof`, and the existing `DOGMA_PoolManager::operator delete(void*, size_t)` routes to `DOGMA_FreeSized` / `pfnMemFreeSize`. The typed `delete` expressions select the class-specific destructor/deallocation path by source declarations. This is source-level overload resolution only; no compiler run was used to claim the emitted calls.
- Native64 named outside-allocation helpers give a 16-byte two-pointer header (`GetReturnedPointer` = +16, `GetStructOverHead` = 16, `GetStructPointerFromReturnedPointer` = -16); the ARTIST 32-bit form uses the corresponding 8-byte displacement. The candidate uses `2*sizeof(void*)` and existing typed node fields, so it follows the native64 width without adding object fields, offset casts, or alias writes.
- Source delta hashes are recorded per file in `EVIDENCE.json`. The raw ARTIST shutdown hash is `35cf8562ce41bc1c31443e98e57d07b85d8140b0a7589504102f270d0aa5593f`; the native64 shutdown assembly SHA-256 is recorded alongside the retained initializer, destructor, outside-header helpers, and owner-release assembly.

**Apt shutdown activation/integration — VERDICT: fail / not ready.**

This proposal intentionally does not wire the recovered helper into game glue. `CgsAptAux::Release` remains unchanged and only advances its state fields; `UnInitializeApt` is not implemented in the current source. ARTIST `AptAux::Release` calls `UnInitializeApt`, whose original sequence performs update shutdown, target destroy/null, render shutdown, then allocator shutdown. The helper alone does not recover that owning lifecycle, retained-view handling, or post-shutdown alias lifetime. Keep it uncalled, keep pool aliases unchanged, and do not treat helper recovery as approval to enable selected shutdown.

## Review disposition

Both narrow source corrections pass against their pinned primary evidence. Both integrated readiness/activation gates remain not ready. The checkpoints contain no hosted build, fixture result, runtime witness or native site credit. Root owns the next source composition, fresh identity binding, hosted validation, and any activation decision.
