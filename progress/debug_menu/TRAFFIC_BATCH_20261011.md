# Traffic, Physical traffic and Route Map recovery

This batch recovers **150 original static registration sites**: Traffic 108,
Physical traffic 18 and Route Map 24. It restores their original owners, bindings,
metadata, callbacks, producer paths and drawing consumers. The source batch is
separate from final behavior verdicts; native verification is still in progress.

## Recovered systems

- Traffic's embedded debug component, lifecycle, telemetry, camera cache, fuzzy
  score ring, picking/kill-zone actions and world/HUD drawing families.
- Physical traffic diagnostics, driver controls, air-ram geometry, articulated
  joint creation/frames/limits and the actual shared-input event path.
- Original 16-byte route nodes, Route/AICar/response ownership, producers and
  Route Map module lifecycle, A* names, portal/section/dead-end drawing.
- Shared 2D box/bar contracts and affected callers; original 4x4 inverse and
  matrix-to-quaternion operations; vector-font world labels in their owning 3D
  command bank. The original fixed bank capacities/overflow contract remain.

The original unusual Traffic hull-selector range target is preserved. Checking/
traffic-jam cells and articulated break cells with unclassified original readers
remain unresolved. No consumer or original-no-op verdict was invented for them.

## Evidence and current limits

The main combined source review passed 55 production paths plus two unchanged
dependencies and four build mounts. The four additional renderer/font paths and their
projection/size supplement also pass review against the ARTIST assembly. `traffic_batch_20261011.json` pins the published source set.

Grouped CPU regressions exercise actual recovered bodies, typed records,
geometry, numerical edge cases and renderer command/pixel context. The earlier
15 groups passed 616 checks; the extended renderer group passes 121 checks,
for **737 checks in 16 groups**. Canonical compilation and faithfulness checks
pass for the changed production paths. The shipping executable links.

Both preliminary grouped native sequences completed with **zero assertions and
zero exceptions** after correcting test inputs and invalid combinations:

- Route Map options accept original names `Plain`, `Type`, `Speed`; numeric input
  misses the original name table and can crash. The parser was not changed.
- Traffic world overlays run in smaller groups within one boot. Before turning
  traffic off, the harness disables the original player-hull readout, which
  requires a live hull. No guard/capacity workaround was added to production.
- Read-only Traffic cells are omitted by original SAVE; native alias resolution
  checks their presence without editing them. Five callback aliases are separate
  from the generated asset caption.

The physical/route run passed all **507 native field reads**, all 42 native
registrations and the `1 -> 101 -> 1` section callbacks. The initial frame budget
expired before all phases, so complete pixel review remains pending. The updated
capture spacing/budget and final renderer arithmetic require a new attributable
run. These results do not certify all 150 consumers.

Air-ram slots, new articulated joints, live A* searches, routes/car information,
dead ends, section geometry and the reset action need eligible scene witnesses.
Finite estimate ULPs/NaN payloads are not hardware-verified; numerical lowering
retains the documented rounded-estimate VMX model and original refinements.

## Reproduce

Run the six new grouped runners under `b5-decomp/tests`: `run_traffic_debug_menu.py`,
`run_route_map_debug_lifecycle.py`, `run_route_map_draw_helpers.py`,
`run_ai_route_storage.py`, `run_articulated_debug_frames.py`,
`run_debug_2d_box_contract.py`; `run_pc_im3d_buffer.py` covers the shared renderer.
Existing route/AI fixture adapters use the recovered records and inlined bodies.

Build through `tools/tests/build_exe_locked.ps1`. The native cases are
`debug_menu_traffic_batch` (private slot16) and `debug_menu_physical_route_batch`
(private slot15). Retain executable/provenance, case hashes, logs and phase-frame
hashes. Inspect actual pixels before writing `witness-review.json`; re-evaluate
that same run with `run_case.ps1 -NoRun`. Boot/registry success alone is insufficient.

Detailed original packets, combined reviews, build logs and failed-run diagnoses
live in `scratch/DEBUG_MENU_1011/traffic_batch/`. Superseded unreferenced BMPs are
losslessly archived with SHA256 manifests in their run directories; referenced
phase frames remain directly accessible.

Recovery checkpoint: b5 `e334f93fb2cb1056547bc0211f6c4e81a913ff87`, branch `codex/debug-menu-traffic-physical-route-150`.
It is published separately while remaining native evidence is collected.
Recovery continues in two isolated agent lanes with frequent source commits.
The active goal remains open.
