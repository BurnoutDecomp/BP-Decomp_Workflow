# Debug-menu behavior campaign

Match every entry to ARTIST, including original no-ops and broken leftovers.
Do not revive removed features in this campaign. The active user goal also
authorizes commits and pushes in both repositories after meaningful progress.
Stage only owned files; leave the general status mirror and submodule pointers
to their existing reconciliation workflow.

`entries.json` records 1,354 original registration call sites in 91 functions,
plus all 64 named debug activation functions. This is a starting inventory, not
an expanded count of visible rows: loops and delegated serialisers can generate
many rows, 15 captions are symbolic, and two registration wrapper exports are
missing. Those uncertainties are retained in the data. PC-specific menu additions
also need their own consumer audit as each page is visited.

`verdicts.json` holds manually reviewed verdicts separately from generated evidence.
States are `pending`, `verified`, `original-noop` and `original-broken`. A final
state requires notes and evidence. An existing body, a registered label or a clean
boot does not qualify by itself.

Regenerate with `python tools/re/debug_menu_inventory.py`. Parser checks:
`python -m unittest discover -s tools/re -p test_debug_menu_inventory.py`.

## Published batches

| Batch | Scope | Evidence |
| --- | --- | --- |
| 1 | Five Race Car Entity / Tailgate... tunables | [Tailgate repair](TAILGATE_20261011.md) |
| 2 | Race Car Entity / Show place on track info; shared 3D debug buffer and original sphere mesh | [Reset overlay repair](RESET_HISTORY_20261011.md) |
| 3 | Forced online lobby spawn; original dormant Apply Ram and Magnitude rows | [Spawn and dormant controls](FORCE_SPAWN_RAM_20261011.md) |

Seven sites are verified; two retain their original no-op behavior. The other
1,345 sites and the expanded
dynamic rows remain pending. Previously delivered presentation/navigation repairs
are documented in `b5-decomp/docs/DEBUG_MENU_REPORT.md`; import their behavioral
verdicts only after checking their actual evidence.

## Continue

1. Finish the race-car page's visual/statistics controls. Reset history and forced
   online spawn are connected and witnessed. Apply Ram and Magnitude retain their
   original dormant state writes. Other primitive algorithms and text remain
   pending, despite sharing the repaired command path.
2. Work through the missing Sound, AI, Renderer, GameData/DLC, Game State, GUI,
   Replays and physics diagnostic lifecycles. Use the original registration sites
   to prevent silently omitting controls.
3. Resolve computed captions, enumerate loop-generated entries, and compare the
   complete native registry. Trace every remaining scalar/action to its consumer,
   including actions whose original behavior is no effect or a failure.

For each batch: original assembly and declaration evidence, production regression,
shipping build, isolated in-game witness, one fresh-eyes review, narrow b5 commit
and push, then its parent tooling/evidence commit and push. The campaign is complete
only when every original and native entry has a supported disposition.
