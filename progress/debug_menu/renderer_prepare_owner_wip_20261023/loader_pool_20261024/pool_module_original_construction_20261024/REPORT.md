# Original pool construction checkpoint

This four-path source proposal targets large WIP **eb4dcbb1e7810f71dc16cd50e49707b2a54bc9b9**, parent **ade2096e15a3f6663a432ed0d27dfa3ee6dd0e02**. It is disjoint from the frozen loader child checkpoint and native startup packet. It adds the complete canonical PoolModule::Construct body at ARTIST0x828FC0B8 and the precise inlined ScratchPool::Construct helper. No owner is activated and no checkout, Git state, build, tests, CI or game/input is changed.

The pool signature has three explicit inputs by DecFIGS virtual declaration. ARTIST saves only options/resource fromr4/r5; it does not consume the incoming debug allocator inr6. The new body preserves that declaration without fabricating a debug allocation. Its existing native two-input overload remains available, with its body unchanged apart from the explicit selection of the retained native scratch reset.

The original body initializes the base, pool stages,128 embedded pools and16KiB receiver queue, then registers the actual allocated/cached IDList type and every supplied game type. It does not introduce the native loop's count clamp, null/type skip or additional allocation assertion. The original null type-allocation behavior is retained. The actual canonical type and cached-ID methods are used.

Scratch options copy all five descriptor/resource lanes, original entry limit and bank999. The real overhead provider and allocation precede the original scratch construction/Prepare/InitPool sequence. Three allocation-request counts are reset individually; the request-result array is not cleared prematurely. Each memory type receives4096 request and result records. The working arrays retain4096 addressed requests,36863 relocation/source/shared records and65543 linear-heap nodes. Native sizeof/alignment is the explicit host-width adjustment; original counts and128-byte alignments remain. Distribution and relocation point to one real shared allocation, using both actual named record types.

The real relocator is constructed before binding the actual shared-operation and supplied bounce-buffer fields. The original allocation assertions retain their predicates/messages and lines119/130/131/164–168. Existing native assert-buffer ownership is reused only inside those assertion paths. The actual state constructors retain their original typed owners and cached-ID behavior. Both pending-request FIFOs are initialized at the tail, followed by the original new-module classification.

## Exact scratch initialization

ARTIST828FC4D8..530 clears entries/IDs/counts/capacity, sets prepare0/release1/bank-1, constructs the primary linear allocator and both scatter streams, stores the10MiB-per-update limits, then constructs three resource linear allocators. The canonical scratch body now expresses exactly those operations in that order.

The previous helper additionally reset update stage, current memory type, distribution pointer and import-hash state, and used a different subobject order. Its complete body is preserved as ConstructNativePC; the existing native pool overload selects that same body. Original InitPool is the later owner for its working cursor/hash/distribution state. The new canonical pool owner calls the precise original helper rather than borrowing the broader native reset and claiming it matches.

## Remaining chain and validation

This supplies complete pool/scratch construction bodies, not readiness of the complete original ResourceModule or GameData startup. The next FileSystem owner still needs the actual files/streams, patch manager,16-slot physical devices and remap devices. The top ResourceModule owner must allocate/initialize its real filesystem allocator, seed the pending-response pool and register the complete monitor set in original order.

Both changed CPPs are already mounted through the exact shipping build_game_exe.bat/compile_exe.py path. Canonical vendor selection, complete primary assembly, DWARF and the actual helper/type/record providers are bound. Static source/removal checks do not establish compilation, linking or runtime parity. No buffers, native budgets, sky/thread state, registration/site counts or delivered files changed. Fresh review remains required.
