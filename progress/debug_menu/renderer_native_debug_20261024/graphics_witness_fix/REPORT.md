# Native graphics ownership witness access correction

This one-path corrective proposal targets exact source **55eaf3b09ff617604503c801732619d19f14d7fc**, parent-repository checkpoint **378ebeb08b9fc005aca07aaefdd2ea3f97f76c9a**. The source commit's own parent is **e315d38ac437a07e5df4903851aaaa43788c3168**. The original frozen startup packet is unchanged.

The fresh reviewer found a real C++ defect in that packet: RendererModule directly reads Allocators::mpInternalGraphicsAllocator, which is private. This correction removes that access and uses existing public typed queries to prove the actual wrapper backing. It adds no API, friendship, accessor declaration or visibility change.

## Producer, type and lifetime proof

In the exact source, the native Allocators::GetGlobalGraphicsAllocator has one actual return object: its anonymous rw::LinearResourceAllocator. Both success returns implicitly convert that same object's pointer to its public rw::IResourceAllocator base. Failure returns null. The renderer checks that result before reversing this known related base conversion with static_cast to the actual RW type. It never casts to the distinct game-side LinearResourceAllocator.

That raw allocator is a static object in BrnResourceAllocator.cpp. Its256KiB backing is allocated once, adopted by that actual object, bound through genuine game-wrapper Construct, and only then published through the existing ready flag. The ready return cannot precede wrapper initialization. No getter, arena, allocation order, budget or lifetime changes here.

The canonical shipping RW GetLinearHeapBase returns **its own m_heapResource member by const reference**; it does not return a global/external alias. The public game-wrapper GetLinearHeapBase delegates that same reference from its actual backing pointer. Equality of the two returned reference addresses therefore proves that the actual game wrapper points to the actual retained raw allocator's Resource subobject. Two different allocators over equal memory cannot satisfy this reference-identity predicate merely because their resource bytes match.

The existing check also requires the real renderer field to equal GetGraphicsAllocator(), which returns the genuine game wrapper. Non-null backing and nonempty real capacity checks remain. The new reference-identity predicate is substantive and directly tests the wrapper's actual backing, rather than merely trusting the inaccessible private bookkeeping pointer.

## Bounded change and validation

Only BrnRendererModule.cpp changes: remove the illegal comparison, perform the justified existing-type conversion and compare the two real resource-reference addresses. Existing optional ownership diagnostics now print both addresses. No resource is allocated, adopted, reset or freed by these reads. Every other startup, preparation, buffer, sky, registration, MemoryUsage and thread operation remains unchanged.

The source/header/provider definitions are bound in this packet. Header access sections and original private declarations are untouched. Root reported that hosted55eaf failed and owns its exact diagnostic receipt. This lane ran no C++ compilation, build, tests, CI, game/input or activation. This correction still needs fresh review and Root-owned validation; no registration/site credit follows.
