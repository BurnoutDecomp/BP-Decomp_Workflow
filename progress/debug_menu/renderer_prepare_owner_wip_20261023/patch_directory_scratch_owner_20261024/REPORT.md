# Patch directory-worker scratch owner

This two-path source proposal recovers the original worker's missing allocation/free lifetime and corrects `GetPhysicalPath` to a static declaration. It follows the sealed14-path Resource/Patch construction packet on exact785; every preimage is bound to that packet's full postimage hash. The earlier packets remain immutable.

ARTIST828F0B88–828F0C8C allocates main memory0x6590/alignment16 with null name from the manager's actual retained RW allocator. It stores the returned pointer at+0x89C, invokes the scan, constructs a five-lane Resource with only that main pointer, and calls the same allocator's virtual DoFree. It loads the current patch index, clears mbPatching, then stores index+1 and returns zero. The proposal represents all those effects with real typed allocator/resource APIs.

The old `s32 miSearchHandleCount` is an incorrect kind of field. It becomes a native-width `void* mpDirectorySearchScratch`; the name is descriptive, not claimed DWARF. All seven original PatchManager exports were inspected: this field is stored/read as an allocation pointer by this worker and is not dereferenced by the retained scanner. No guessed search-record layout is needed. The pointer is not cleared after freeing because the original adds no such store; each worker overwrites it before use.

The real Resource constructor clears all five pointer lanes before lane0 is assigned. The existing AllocateMemoryResource helper constructs the original five-lane descriptor. No fake allocator, raw offset access, skipped request, extra readiness flag, allocation-success guard or empty/trap completion is added. The existing scan invocation is preserved; full scanner/platform parity is not claimed.

`GetPhysicalPath` is static by actual caller/callee ABI: SearchFolder828F0AAC–B8 supplies dest/length/source in r3/r4/r5, and828DCF40 consumes those registers without an implicit manager pointer. Its existing implementation is instance-independent and remains byte-identical. Only the declaration changes.

The callback caller is the existing real EAThread worker entry, with one context input. The callback's pseudo-signature with extra arguments is rejected by the assembly. The new pointer changes the native private layout as pointer widening requires; no packing or console-sized host field is retained. Root must review that layout with the larger unactivated owner.

This is unreviewed, uncompiled and unactivated. Shipping still does not mount PatchManager CPP. AddPatch thread parameters/return shape, the host scan's attribute0x20 versus target0x80, dot-entry behavior, logical path mapping and native enumeration-handle cleanup remain separate platform/lifecycle boundaries. No scan, thread, build, test, CI, IDB or game was launched by this packet. Counts remain unchanged.
