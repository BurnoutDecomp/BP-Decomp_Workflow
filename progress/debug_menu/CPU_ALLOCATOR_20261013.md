# CPU profiler allocator checkpoint - 2026-10-13

**Source is pushed and compiles; independent review, integration and native
behavior remain pending. This checkpoint adds no final menu verdict.**

The registry previously ignored its supplied allocator. Candidate `e4acac75f`
restores ARTIST's allocation of 96-byte records, 16-byte alignment, five-lane
descriptor, original failure assertion and complete zeroing. Existing native
QPC and completed-frame counters remain separate. The host-only teardown now
returns the saved resource to its producing allocator.

The whole-production snapshot test retains eight threading/registration/reset
checks and adds four allocation/clear/teardown witnesses. Current source passes
12/12; old `d6da13056` fails exactly the four added witnesses. One production TU
compiles with zero new faithfulness findings. No full-game run has used this
private candidate yet.

Exact branch, source and validation state are in the
[checkpoint receipt](cpu_allocator_20261013.json).
