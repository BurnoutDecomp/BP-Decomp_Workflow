# Independent chunk23 source review

VERDICT: pass

No actionable correctness findings in the submitted chunk23 delta. This verdict covers only restoration of `TrafficEntityModule::Pressure_PickSplitToTake`'s destination-span occupancy score on the packet's prepared-runtime domain.

Reviewed packet: `scratch/DEBUG_MENU_1011/swarm_traffic_source_backlog_20261028/chunk23_pressure_split_occupancy/REVIEWER_PACKET.md`.

## Evidence checked

- All 75 sealed manifest entries and all 497 recorded compile dependencies match their hashes. The manifest digest is `549d77b180c545ec14ecec0c76b455d51b57aaf5aecfc1bc187acff883928676`. The submitted patch is the exact unified pre/post difference. Its only production path is Module.cpp; context headers match across both sides.
- The preimage hash `c7130b6258e84176afc87d63eea08d3518b20607ca407aa57915076f200adb0a` matches the sealed predecessor Module postimage and its manifest entry. Frozen dependency parent-manifest and roster bindings match. Prior chunks were treated only as named immutable dependencies; their reviews were not repeated.
- Both raw ARTIST windows and all four constant words match the original raw input. Complete retained caller, counter-producer, reset and runtime-prepare exports match the cached original exports. Whole-raw historical authentication was not independently repeated.
- The entire original body `8272BC68..8272C00C` preserves `this`/Section/output ABI in r3..r7, four first guards, local FF/FFFF/0 outputs, FLT_MAX minimum, left/right zero-probability penalty100, invalid-section skip, missing-runtime score1, ordered strict minimum, and final section/hull/direction stores.
- `8272BF38` selects an eight-byte destination SectionSpan; `8272BF68` reads its f32 reciprocal at +4. `8272BF78` reads the corresponding u16 count; the conversion is exact for this range. Word `EC0C683A` at `8272BF98` is `fmadds f0,f12,f0,f13`, i.e. count * reciprocal + directionPenalty with one f32 rounding. The submitted `std::fma` operand order is correct. `fcmpu` plus the `!LT` branch skips ties and unordered scores.
- Existing typed SectionSpan, Hull section/span accessors and HullRuntime count methods supply the data; no type, asset, layout or global-math change is introduced. The getter's existing prepared assertion is explicitly retained and excludes unprepared-runtime parity from this verdict.
- The original reset clears all 256 u16 counters. Original UpdateParams ends with reset then UpdateLinkedList, whose alive-param path increments the selected span. Prepare does not initialize this count table. The fixture uses actual Construct/Prepare/Reset/Increment/Get methods and real asset getters instead of assuming fresh zeroed counters.
- The audit's two named hull-assert omissions are represented by the exact GetHull and GetHullRuntimeSafe bodies now called by the method. Resource-handle access is via the existing production getter; the CPU fixture substitutes only its controlled TrafficData pointer boundary. The retained asmaudit row describes an earlier built executable and is not evidence for a new native build.

## Independent replay

All replay output is under this exclusive directory, primarily `packet_copy/`. The author packet remained unchanged, verified after replay.

- Recompiled both complete owning Module.cpp TUs with the canonical shipping flags, preserving the include precedence and redirecting all outputs into the review copy. Both returned 0.
- Recompiled the real HullRuntime source and exact source-derived whole pre/post methods plus exact GetHull/GetHullRuntimeSafe bodies; linked with the hash-bound existing real string-support objects. All returned 0. There is no unresolved-symbol suppression or replacement engine body in the fixture.
- Ran all 45 controls independently: candidate45/45, baseline21/45. Counter tuples match actual reset/populate/wrap results. The crowded-straight witness selects left only after the repair. The finite FMA witness uses count22223, reciprocal bits1009164510: fused bits1134756237 versus split-rounding bits1134756238; this changes the chosen direction. The verifier attests the original opcode operands and comparison words before using its fmaf model.
- Controls cover runtime-presence masks, penalties, ties, output sentinels, first asserts, sparse/boundary sections and spans, absent-runtime no-access behavior, u16 count wrap/reset, and finite FMA order. Eight nonfinite/degenerate cases remain host scalar models, not console hardware certification.

Reproduction evidence: `review_verify.py`, `INTEGRITY_RESULT.json`, `PREIMAGE_BINDING_RESULT.json`, `controls_output.txt`, and `packet_copy/CPU_RESULTS.json`. Local compile logs and response files are in `packet_copy/`.

## Boundary

No #0029 original boolean reader, whole module scheduling, traffic movement, native game behavior, loader/rendering/hardware behavior, or completed menu-control coverage is established. `affected_sites` stays empty; site credit stays zero. Shared/canonical source, refs and native state were not modified.
