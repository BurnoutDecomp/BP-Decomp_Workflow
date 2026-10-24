# Standalone native graphics prerequisites

This source-only package targets delivered consumer `d3ec7d2dd65a37b489d1dbf61a53b9ce030385ee`, parent `c3a572aaef931462fcd9078fd84ec6f2becebe03`. It selects only the original graphics prerequisites and a bounded native adoption change. It does not copy the larger GameData, game legacy-IO or five-argument game Prepare owner into the consumer.

Four original graphics preimages (allocator header/CPP and vendor header/CPP) are exactly equal to the consumer's current Git blobs. The consumer renderer CPP is exactly the immutable seed packet's preimage; applying that genuine classification store produces the graphics packet's exact renderer preimage. `GRAPHICS_PREREQUISITE_BINDINGS.json` binds the reused graphics postimages. The original graphics constructor's private accessibility correction is retained without importing the separate GlobalResource globals/constructor or root accessor.

The reused original code recovers the real game-side wrapper, its allocation/free methods, typed graphics globals, unactivated original global constructor, GetAvailable dependency and renderer pointer binding. All those bodies are the preceding immutable graphics recovery. Fresh review of their original semantics remains required; prior packets are unchanged.

## New native adoption

The existing native `Allocators::GetGlobalGraphicsAllocator()` still returns **the same raw anonymous RW Linear allocator** at both return sites. Its256KiB backing allocation, per-lane capacity, AdoptMemory call, ready flag and all current caller return identities remain unchanged. Immediately after that actual AdoptMemory and before its existing ready publication, the method records the actual backing in the genuine internal graphics pointer and calls the genuine two-store game wrapper Construct with that pointer and name GlobalGraphics.

No native client is redirected through the game wrapper's DoAllocate/Free methods. Their old descriptor validation/free behavior and underlying allocation object therefore remain unchanged. The native object is not cast to an unrelated class or wrapped around a guessed arena; the actual `rw::LinearResourceAllocator` object is passed to the exact typed Construct API. The game wrapper and renderer field already denote the real original objects. A successful native getter now establishes their backing from the actual retained owner.

The only other new PC change is printed-address arithmetic in the existing MemoryUsage body. A main-only native arena has a null physical base and zero physical capacity. Calculating its printed end in native integer-address space avoids null-pointer arithmetic while preserving the original base-plus-capacity result. The report's providers, sizes, messages, filter checks and call position remain unchanged.

## Scope and remaining preparation owner

This package contains six full source pre/post paths because it is standalone against the active consumer. Its semantic native delta beyond the original graphics recovery is the adoption block and two printed end-address calculations. It adds no Prepare invocation, no Register invocation and no startup call. The genuine renderer new-module classification is not a resource-ready flag; it restores the original IO mode and does not complete Prepare.

Original global graphics allocation remains **uncalled**. Both the raw native graphics arena and WorldDispatch arena/budgets, all native buffers and sky state, GameData's existing native path, and thread startup stay unchanged. No new readiness boolean is introduced. Real buffer/sky ownership checks and the single pre-thread preparation owner are the next separate proposal, required before component lookup can succeed.

All affected CPPs are already shipping mounted, and canonical vendor methods are selected using the actual shipping include order. No CMake/source-list change is needed. No C++ compilation, tests, CI, game input or runtime activation was performed. Source/evidence audits are not validation of gameplay or registration. Counts remain50 verified /7 no-ops /1298 pending of1355.
