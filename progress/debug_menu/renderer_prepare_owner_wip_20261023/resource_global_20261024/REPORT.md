# Original GlobalResource initialization and root selection

This four-path source packet recovers three genuine definitions: `Allocators::ConstructGlobalResourceMemory(const CgsMemory::MemoryBank::Params*)`, the canonical free `BrnResource::GetResourceAllocator()`, and `CgsMemory::MemoryMap::GetRootBank() const`. It supplies the original typed resource globals. Exact base is source `65a8992bdfc29e2ba7c92e4024a965a653a6af27`, parent `53098be903b5abc42b7cf2b70951cbd9f4509615`. Both allocator preimages are verified byte-identical to the already-published graphics packet postimages, so the graphics definitions are preserved in full.

The requested global-resource getter is named **GetResourceAllocator** in DecFIGS h393. No `GetGlobalResourceAllocator` alias or new API is invented. ARTIST8266D5AC..5BC loads the actual GlobalResource wrapper address before RegisterResourceTypes; the getter returns that genuine object. It adds no backing assertion or lazy native allocation. The real wrapper allocation entry, recovered in the preceding packet, validates its backing before use.

## Actual owner contract

ARTIST82666C58 reads the incoming Params' size words at+40 and+48: main and physical lanes0/2. DecFIGS cpp185/h330 independently gives the exact Params pointer type. The body derives main capacity `root.mauBankSize[0]+0xFC0000` and physical capacity `root.mauBankSize[2]+0x200000`, using unsigned32-bit additions. The descriptor alignments are both64KiB; the two XPhysicalAlloc calls instead request128KiB alignment, each with physical address0xFFFFFFFF and flag0x20000004. Those distinct alignments are preserved.

The real canonical vendor GetResourceDescriptor computes the actual allocator/object carve. Both present lanes are filled with original0xCD, then the canonical vendor Initialize produces the real RW Linear allocator. The genuine game wrapper receives that backing pointer and name GlobalResource through its recovered two-store Construct. No guessed reserve size, new arena, failure-success adapter, trap body or null-skip policy is added.

Primary birth bytes show the resource's five pointers and internal allocator pointer are zero, while the wrapper is `{vptr,0,0}`. Descriptor lanes1..4 initially contain{0,1}; primary82C5FF68..FFA8 initializes lane0 to{0,1}. The typed static objects therefore have the original logical birth state. No extra readiness flag is created.

The raw original root record is `Root Bank`, parent-1, id0, main0x7000000 and physical0xCB00000. For that recorded input the derived capacities are0x7FC0000 and0xCD00000. These are evidence examples; the recovered body uses its supplied typed Params, not hardcoded root totals or current native budgets.

## Original root-Params caller selection

The two actual instructions are independently decoded from primary bytes:

| Instruction | Raw word | Meaning |
|---|---|---|
| 8266AF08 in Allocators::Construct | 83EB0024 | load r31 from map header+36 |
| 8266D5B4 in GameData::ConstructResourceModule | 83FF0024 | load r31 from map header+36 |

Header+36 is the first relocated bank-array pointer. It is not a pointer to the full map passed as Params. `MemoryMapBank::GetParams` has no subobject adjustment, so the genuine declaration `GetRootBank()` (DecFIGS CgsMemoryMap.h72) exactly represents this first-pointer load. The ordinary GetBank body82663C88 uses `(index+1)*84` and GetNumBanks excludes the root; GetBank(0) selects the first child. No sentinel-index workaround, fabricated `GetBinaryMemoryMapBank` accessor, private-field cast or raw-offset C++ is added.

`CALLER_SELECTION.md` records the exact full original allocator phase sequence and the typed selection expression. The full top-level Allocators::Construct body is **not** introduced in this packet, because its system/debug/child owners and initial-budget check remain separate unavailable definitions/globals. This packet introduces no unresolved calls to those owners. It closes the resource phase and genuine accessor while preserving that explicit dependency boundary.

The header also restores the preceding graphics phase's private accessibility, as declared by DecFIGS h327, while adding resource construction privately per h330. This is a separate declaration-shape correction to the published graphics packet, not an edit to its immutable evidence or a change to its method symbol/ABI.

## Availability and integration limits

All three new bodies have available callees after the preceding graphics checkpoint. Both CPPs are already in the shipping list; no mount is needed. The exact canonical vendor header, static method signatures and existing shipping XPhysicalAlloc declaration are bound. C++ compile/link and fresh review are pending; source byte checks are not tests.

No call activates either global constructor, the wrapper is not adopted by the native graphics helper, and no original Prepare, renderer registration or thread startup is selected. Both native allocator arenas, root budgets, immediate buffers, sky state and thread ownership remain unchanged. Getter non-nullness is not backing readiness. The original MemoryUsage body remains unchanged and still requires a properly initialized backing owner before use.

A single hidden BelowNormal idat read reused the same retained owned copy for about4.2s, with analysis disabled and no decompiler/cache API. It read birth bytes, the84-byte root record, two instruction words and the short existing descriptor initializer. No original/shared IDB was opened/saved, no duplicate copy was created, and no cleanup retry occurred.

No physical source, Git/index/ref, ledger, build/test, CI, native game or input was changed. Every earlier frozen packet is preserved. Counts remain50 verified /7 no-ops /1298 pending of1355.
