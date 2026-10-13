# CPU profiler allocator checkpoint - 2026-10-13

**Source passed independent review, is integrated and pushed, and the normal
executable builds. This checkpoint adds no final menu verdict.**

The registry previously ignored its supplied allocator. Candidate `e4acac75f`
restores ARTIST's allocation of 96-byte records, 16-byte alignment, five-lane
descriptor, original failure assertion and complete zeroing. Existing native
QPC and completed-frame counters remain separate. The host-only teardown now
returns the saved resource to its producing allocator.

The whole-production snapshot test retains eight threading/registration/reset
checks and adds four allocation/clear/teardown witnesses. Current source passes
12/12; old `d6da13056` fails exactly the four added witnesses. One production TU
compiles with zero new faithfulness findings. The 2,971-TU shipping build linked
with zero failures. Two isolated native integration regressions passed: Start/
vehicle settings 9/9 and GPU graph 13/13, with zero assertions or exceptions.
These runs establish startup and retained GPU behavior; CPU menu/HUD behavior
still needs its own witness. Producing-allocator lifetime remains required.

Exact branch, source and validation state are in the
[checkpoint receipt](cpu_allocator_20261013.json).
