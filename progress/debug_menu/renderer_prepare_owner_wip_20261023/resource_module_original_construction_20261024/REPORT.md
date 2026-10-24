# Original ResourceModule and PatchManager construction

This14-path source checkpoint recovers the complete original `ResourceModule::Construct` body and its genuine PatchManager construction dependency. It is bound to **7854e7fdd8b7c659d1b25d015c1321f0297df304**, workflow **1a998f007d13d151b22440675b4c94be2c8fa10d**, plus the separately sealed F1 FileSystem correction. All fourteen candidate preimages are exact785 Git blobs. The corrected FileSystem CPP is a required dependency, not another changed candidate path.

No original construction chain was activated. No production source, refs, inventory, build, tests, CI or game/input changed. Source bodies are complete for the scope below; the full GameData/resource lifecycle remains unready. This packet awaits fresh review and compilation.

## Recovered owners

| Owner | ARTIST | Result |
|---|---|---|
| ResourceModule::Construct |829055B0–82906568 | Base construction, prepare/release stages, Memory→Loader→Pool→Debug construction, genuine filesystem allocator, FileSystem owner,16-slot pending-response pool, all42 monitor registrations,11 trace resets, final new-module byte and pending-patch latch. |
| Filesystem allocator |8290565C–829056F8 | Actual supplied resource allocator receives the GeneralResourceAllocator descriptor derived from main capacity0x160000/alignment16, other lanes0/1, null name. The real Initialize return is retained in `mpFileSystemAllocator` and passed to FileSystem. No guessed allocator or budget substitution. |
| Pending response pool |829056FC–82905718 | Real `IndexedPool<PendingFileResponse,16,s8>` binds its own sixteen typed records and free indices. Member order is allocator→pool→records→indices, matching target roles. |
| Monitor owners |8290571C–829064F0 | All42 exact names, original order, page1/minimum=false/budget5.0/scaled=false, register only when handle==-1, retain each failure assertion and source line100–159. |
| Relocator handles | Resource constructor + original Relocator users | Three existing TU-local inert handles become the original public class statics. Existing timing bodies change only their handle identifiers, so the real constructor registration reaches their actual consumers. |
| Trace IDs |829064F4–82906554 | Complete eleven zero stores to original ResourceModule/PoolModule/Pool/BundleLoader trace owners. Declarations follow DecFIGS; group/order bindings are recorded separately. |
| Pending patch storage |8290655C;828FD5C8;828EC788 | Original final byte is a pending-patch latch. AddAddPatchRequest sets it and retains the complete request; ProcessResourceResponses later sends event25 and clears it. This packet adds typed retained storage and the original Construct=false store; current consumers are unchanged and their missing patch slice remains explicit. |
| PatchManager::Construct |828F0980–828F0A74 | Two distinct0x4000/alignment16 main requests with null names, separate keys/values,4096 slots, mbPatching=false, actual singleton publish. The old incorrect single interleaved allocation is removed. |
| u32 SOA Initialize |828E9BC8–828E9CBC | Exact original power-of-two assertion at CgsLinearSOAHashTable.h167, length/key/value/invalid-key stores, then key-only clear. Values remain untouched. Complete original definition; no trap/forwarding substitute. |

`MONITOR_MAP.json` binds all42 target globals to assertion-named class fields. The prior owned primary read verifies every initial word isFFFFFFFF and budget8200426C is40A00000. Twenty-six missing monitor declarations/definitions are added; sixteen existing originals remain. `TRACE_RESET_MAP.json` records the eleven grouped trace stores. The constructor's final `mbIsNewModule=true` is the actual original tail store; the existing native Prepare behavior is preserved separately and is not used as proof of this owner.

The ResourceModule pending-patch identifiers are descriptive X360-only names, not claimed PS3 DWARF names. Their role is positively established by both original producer and consumer. The retained request uses the real `Events::AddPatchRequest` with native pointer width, rather than a268-byte host blob.

## Genuine separate-array table

The existing `CgsContainers::LinearSOAHashTable` supplies the real container. PatchManager now uses its existing native ValueType-first convention as `<s32,u32>`: u32 hash/length and s32 owning-patch value. Target AddEntry828DF260 and FindEntry828DF3E0 use unsigned division/remainder, unsigned comparisons, four-byte key/value strides, and distinct key/value pointers. The initializer read independently confirms that shape. Hash values with the high bit set must retain unsigned probing; the previous interleaved table and signed-key interpretation cannot stand in for this target.

The exact u32 initializer is explicitly declared in the real container header and fully defined in its canonical CPP home. The original u64/import instantiation and all existing generic AddEntry/FindEntry bodies remain unchanged. No compatibility flag, dual storage mode, pointer view or new table implementation is introduced.

PatchManager's new constructor uses the existing original `IResourceAllocator::AllocateMemoryResource` helper twice. Both the previous descriptor and the new descriptors have valid identity lanes from the real `BaseResourceDescriptor` constructor; they are not uninitialized. The difference is the original two allocation owners and separate table arrays. Each new request is16384 bytes, matching4096 four-byte entries; total payload remains32768 bytes before allocator overhead.

The old Patch constructor has no working native owner to preserve: it is unmounted, and exact785's sole Construct caller is the unactivated original four-input FileSystem owner. Native ResourceModule's two-input Construct calls FileSystem's no-argument path, which never invokes PatchManager::Construct. This caller/body/mount evidence is frozen. The existing native path is not redirected to a new table adapter.

The one authorized owned-copy read completed in **1.7492 seconds**, PID37332, exit0, hidden/BelowNormal, analysis off. It read only the248-byte initializer, called no decompiler/cache/analysis APIs, created no new DB copy and did not open the original IDB. `IDB_PATCH_READ_RECEIPT.json` records completion; Root was notified before further native work.

## Preserved behavior and boundaries

- ResourceModule's existing two-input Construct, Prepare, Release, Destruct, Update and request consumers remain byte-identical. Pool/PoolModule/BundleLoader CPP changes add only original static definitions. Relocator method bodies are exact after three monitor-name substitutions. Private typed storage/order changes are explicit; unchanged function bytes alone do not establish runtime equivalence for the larger WIP layout.
- FileSystem F1 is a required overlay: only `mbPrepared=false` replaces the wrong count store in the original four-input owner. No additional used-stream-count store is added. The prior sealed FS packet remains immutable.
- Shipping authority is `build_game_exe.bat -> compile_exe.py`. PatchManager CPP, LinearSOAHashTable CPP and PhysicalX360Device CPP are still unmounted. The newly complete initializer therefore has a precise mount boundary. No mount or CMake change is made; this is not a link-ready claim.
- The existing patch scanner still omits its allocator-owned directory scratch chain. AddPatch/worker/native OS policy and the pending-patch response slice need separate recovery before patch activation. Their bodies are not replaced with traps or empty completions.
- Original singleton selection, queue scalar byte provenance, worker/release lifetime and later FileSystem lifecycle limits from the FS packet remain. The original manager cannot be constructed a second time during native driving.
- Outer GameData Construct/Prepare integration, original global allocations and native allocation reconciliation remain separate. No renderer registration, native buffers, sky, threads or player state is activated or re-prepared by this packet.

Counts remain50 verified /7 no-ops /1298 pending. Root's survey-state native pass is separate shared-chain evidence and grants no independent control credit here. `POSTMORTEM.md` and `REVIEW_REQUEST.md` define this source checkpoint's review scope.
