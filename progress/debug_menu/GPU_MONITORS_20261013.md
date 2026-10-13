# GPU monitor repair - 2026-10-13

**Both GPU switches are behavior verified in the normal game executable.**

The switches were registered, but the renderer had no monitor registrations,
disabled timing brackets and a no-op platform callback. The repair restores the
original twenty categories, names, budgets, pass boundaries, update-side Swap and
graph/table rendering. Native D3D9 timestamp queries supply completed GPU spans.

The independent combined source review passes candidate `749a190a1`. Its
comment-only successor `8c779e4f8` is integrated and pushed; the normal 2,967-TU
shipping build compiles and links with zero failures.

Three isolated full-game cases pass **39/39 checks** at that exact executable:

| Mode | Evidence |
| --- | --- |
| Graph | Real registered true/true settings; completed queries and nonzero WorldOpaque reach the production graph callback; measured bar and original scale visible. |
| Table | Real true/false settings; readable twenty-category table, nonzero costs and totals visible. |
| Hidden | Real false/true settings; queries continue, overlay/callbacks stop, driving frame has no GPU graph or table. |

All three reach driving and move the car with zero asserts or exceptions. The
captured frames were inspected. These concurrent runs establish behavior, not
standalone performance. Interactive manual menu traversal was not exercised.
Exact paths, hashes, settings, screenshots and limitations are in the
[native receipt](gpu_monitors_native_20261013.json).

The production transport/registry fixture passes 26 checks, the whole-frame
regression 16, and the complete graph/callback fixture 12. Frozen earlier source
fails the positive-data and graph-regression controls. These are grouped checks,
not additional menu entries.

The first native attempts were retained: two setup failures never launched the
game; a third run exposed a duplicate `[Debug]` section in the test fixture. The
fixture now inserts settings into the existing section and caps each capture at
24 frames. The successful runs use this corrected fixture.

Source review packet:
`scratch/DEBUG_MENU_1011/gpu_monitor_recovery_20261013/review_749a190a1/REVIEW_PACKET.md`.
Native cases: `debug_gpu_monitors_graph`, `debug_gpu_monitors_table`,
`debug_gpu_monitors_hidden` under `tools/tests/cases/`.
