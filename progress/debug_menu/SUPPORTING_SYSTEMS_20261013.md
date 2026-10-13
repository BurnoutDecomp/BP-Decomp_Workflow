# Collision, occlusion and memory source checkpoint - 2026-10-13

**The combined source reviews pass. The 42-path integration and its dependencies
are built and pushed at `058f17072`; startup/GPU regressions pass 22 checks.
Specific collision/resource menu effects remain pending. No final entry verdict is added.**

The frozen geometry lane covers collision query/draw helpers, the occlusion
manager and its dispatch walker. The memory lane covers the typed map, initial
allocator chain and statistics/HUD. Twelve production files compile with zero
new faithfulness findings. All source and original evidence are pinned.

The review caught an unrelated old renderer-header hunk that would reset GPU
IDs to zero. Repair `c92b1556c` preserves the current primary minus-one stores
and applies only the canonical Im3dZOnly type seam; the affected files compile.
A later, separately frozen TriangleCollisionManager constructor is pushed at
`d7800739a` and also compiles. The scene-owner caller work continues separately.

Occlusion activation is still missing. ARTIST's matrix request alone is 512 KiB;
the host GlobalGraphics arena has 256 KiB. No arena increase is applied. Capacity
must account for the complete shared renderer state and query allocation lifetime;
the earlier 576 KiB proposal is not an accepted budget or working-query claim.

The exact source integration began at `66ee49a71`. Missing position-only
BeginRendering and heap reporting bodies were recovered and reviewed, followed
by a shared program-cache repair. Native checks then caught an omitted startup
allocator handoff. The original debug-wrapper caller and explicit existing native
system-provider handoff are repaired and reviewed; scratch sizes are unchanged.
All 2,972 shipping files compile and link at `058f17072`. See the
[runtime integration](SUPPORTING_INTEGRATION_20261013.md) for the checks and limits.

Exact candidates, hashes, compile states and limits are in the
[original source receipt](supporting_systems_20261013.json) and
[repair receipt](supporting_systems_repairs_20261013.json). Long Windows evidence paths
have immutable short aliases with identical bytes; no original packet changed.
