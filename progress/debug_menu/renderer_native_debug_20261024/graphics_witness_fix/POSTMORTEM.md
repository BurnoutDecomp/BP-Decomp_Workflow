# Access correction self-review

- The exact55eaf header places mpInternalGraphicsAllocator under private, with no Renderer friendship. The frozen proposal's direct read was invalid C++; this packet removes it.
- The alternative uses only the existing canonical public APIs. No private member becomes public, no original friendship is invented and no new API is introduced.
- The public raw getter's producer is fully inspected: both non-null returns are the same concrete static rw::LinearResourceAllocator. The reverse related-base static_cast is justified by that exact producer, not RTTI guessing, an offset or a cast to the unrelated game wrapper.
- Failure is rejected before conversion/query use. The existing ready publication follows actual AdoptMemory and genuine wrapper Construct, so either successful raw return follows that binding.
- The selected shipping RW provider returns its own member by reference. The game-wrapper getter delegates the reference. Equality compares those actual member addresses, not copies or pointer/descriptor contents. A resource alias from a different allocator would fail.
- The renderer's genuine wrapper identity, non-null resource and nonempty capacity checks remain. No readiness stage is seeded and no allocation/provider call is substituted.
- The actual private declarations, raw getter and all allocation capacities/lifetimes remain byte-identical. The only changed file is the renderer CPP; the new diagnostic fields are read-only addresses.
- Exact source/pre/post hashes and a narrow expected-diff audit bind the correction. No C++ build/tests/CI/game/input/activation were performed.
