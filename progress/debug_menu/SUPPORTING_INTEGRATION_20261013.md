# Supporting integration - 2026-10-13

**Built, reviewed and pushed at `058f17072`. Startup and retained GPU behavior
pass 22 native checks. This checkpoint adds no final menu-entry dispositions.**

The 42-path collision/occlusion/memory source integration is now in the normal
executable. Its missing position-only BeginRendering and heap report/snapshot
dependencies are recovered. A second renderer program cache was removed so
new rendering brackets and other binders share the original shadow owner.

The first native integration caught a startup regression: InitMemoryMap installed
the original 2 KiB scratch allocator, but the PC adapter omitted the later system
handoff and supplied null debug params. The repair passes the original public
debug wrapper and restores the existing five-lane native system provider after
device startup. It preserves scratch sizes and allocation failure behavior.
The full engine Allocators::Construct path remains unrecovered on this adapter.

Validation is bounded:

- Combined source reviews pass for the source batch, dependencies, cache and handoffs.
- Heap reporting passes 18 whole-production allocator checks. Renderer cache
  checks pass 6/6 at a deterministic shadow boundary; old source fails two.
- All 2,972 shipping files compile and link. The two native cases pass 9 and 13
  checks, reaching driving with no assertions or exceptions. GPU query values
  reach real graph callbacks, and the captured graph frame was inspected.

These runs establish startup and retained GPU behavior. They do not establish
resource/CPU HUD effects, collision controls, occlusion predication, complete
allocator construction, or later loading/renderer candidates. Those remain
separate recovery/review/integration work. The healthy executable and symbols
are preserved in a byte-exact local snapshot before further builds.

Exact commits, failed pre-repair runs, passing results, hashes, backup and limits:
[runtime receipt](supporting_runtime_integration_20261013.json).
