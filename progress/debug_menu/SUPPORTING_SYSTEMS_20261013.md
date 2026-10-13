# Collision, occlusion and memory source checkpoint - 2026-10-13

**Source compiles; combined independent review and repairs are in progress.
Integration and native behavior remain pending. No final entry verdict is added.**

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
the host GlobalGraphics arena has 256 KiB. The evidence-backed host proposal is
576 KiB, including the accounted current consumers and alignment reserve. It is
not applied, and it makes no claim about console capacity or working queries.

Exact candidates, hashes, compile states and limits are in the
[source receipt](supporting_systems_20261013.json). Long Windows evidence paths
have immutable short aliases with identical bytes; no original packet changed.
