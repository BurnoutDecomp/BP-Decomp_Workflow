# Collision, occlusion and memory source checkpoint - 2026-10-13

**The combined repair source review passes. The exact 42-path integration
compiles; shipping link dependencies and native behavior remain pending.
No final entry verdict is added.**

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

The repaired source is integrated at `66ee49a71` and pushed on the supporting
branch. All 2,972 shipping files compile. Linking exposed the missing position-only
BeginRendering and allocator ReportHeap bodies; their recoveries compile and are
under a separate combined review. The healthy `e4acac75f` executable is preserved.

Exact candidates, hashes, compile states and limits are in the
[original source receipt](supporting_systems_20261013.json) and
[repair receipt](supporting_systems_repairs_20261013.json). Long Windows evidence paths
have immutable short aliases with identical bytes; no original packet changed.
