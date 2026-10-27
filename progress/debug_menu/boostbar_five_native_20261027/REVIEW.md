# Independent remaining-five native evidence review

VERDICT: pass

Pass for final per-site dispositions of exactly `BrnGui::GuiCustRendererDebugComponent::OnActivate#0011`, `#0014`, `#0015`, `#0016` and `#0017`, on private slot 62091 in `run_boostbar_remaining5_20261027_064445`. This is the hosted image from source `f0b8f37b39b89390f61f1f0264c8b704950fb030`, executable SHA256 `5072c6c3bcf0e64913dc7f15ba51e9395c2417d844324b70e6e7e83c8a8a282e`. It does not establish current-dev behavior.

I independently viewed all sixteen original 1280x720 BMPs. The stationary front-facing car, world, natural boost HUD and minimap remain visible; no active wreck or obscuring menu prevents comparison. Seeded windshield texture/cracks remain, so no intact-glass or damage-free-car claim is made.

| Site | Positive / negative / restore | Independent visible result |
| --- | --- | --- |
| 0011, grid toggle | TRUE / FALSE / FALSE | Original flame grid appears, disappears, then remains hidden; ordinary HUD persists. |
| 0014, outer Blue | 0.25 / 0.75 / 0.575 | Outer flame changes orange to mauve/pink, then returns to its original muted pink; inner green remains. |
| 0015, inner Red | 0.25 / 0.75 / 0.375 | Inner flame changes green to yellow-green and returns to original green; outer pink remains. |
| 0016, inner Green | 0.25 / 0.75 / 0.95 | Inner flame changes mauve/pink to green/yellow and returns to original green; outer pink remains. |
| 0017, inner Blue | 0.25 / 0.75 / 0.3 | Inner flame changes green to cyan and returns to original green; outer pink remains. |

All fifteen contiguous state windows independently match the retained raw-log complete-line prefix hashes. The recorded zero-based F1 position is the first exact ACK; all six indexed F2 label/value pairs follow it, with exactly the two expected BOutR label occurrences. State values equal their requested values; other channels retain captured baselines. Every capture has the unique raw ACK for PID 15476, slot 62091, its sequence, present and original BMP. All sixteen BMP byte counts/hashes, four overview hashes, overview source roster, same-frame CSV rows and actual plan/binding copies agree. The raw-log SHA256 is `bae317bd5032ba6f50f94e37ac3f7939106c10797f6bb5bbe2558ec397476761`.

Startup plus nineteen write and sixteen capture acceptance receipts resolve to 144 fresh raw motion rows and 144 raw player 0 physics rows: engine2, zero receipt motion, brake/handbrake 1, gas/steer 0, valid contact and no crashing, forceFrozen, boost or Showtime. Held receipt line numbers are one-based; F1/window/capture indexes are zero-based. The larger post-attach interval has 804 advancing motion rows, maximum speed 0.165604 m/s and planar displacement about 0.0453 m; after natural startup reaches engine2 it does not leave it. Console input spells `exec b1.cfg` followed by Enter, activates the exact component and closes before every frame, with no later reopen.

Hash-checked source evidence connects the registered fields and callbacks to the same manager-owned BoostBarRenderer, its custom RGB setter and debug-grid render branch. All 22 retained source/input/harness evidence hashes match their bindings. stage_019.txt invokes the original custom setter and the final raw six-channel readback restores every captured baseline. The private profile, private config and fourteen runtime payload hashes also remain bound.

The actual native case reports six passing checks; canonical and trigger exits are zero. The final Run.ps1 wrapper remains FAIL: its retained console error identifies only the DateTime.Parse call in the final owned-exit guard at line 255, after the case and normal comparison. For these five site dispositions, the retained canonical direct-creation-handle cleanup, input reset and profile restoration receipts plus Root's later exact PID/image absence check suffice to close that evidence gap. I also independently rehashed all 27 protected normal files, including sizes and timestamps, and confirmed the ten-profile roster against the fresh staging snapshot. No aggregate wrapper result has been relabelled.

Excluded from new credit: OnActivate#0007, #0008, #0009, #0010, #0012 and #0013. Their earlier evidence remains separate. No all-menu, online, allocator-frame or current-dev claim follows. This review used read/hash/static evidence analysis and original-image viewing only; no new execution or source/Git/ledger changes occurred. EVIDENCE.json retains the exact artifacts, frame hashes, state windows, accepted IDs and exclusions.
