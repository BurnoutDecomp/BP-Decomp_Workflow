# Current8fec GPU frontend native refresh review

VERDICT: pass

Scope: the completed four **separate cold-launch frontend phases** at `D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\gpu_monitor_phase_probe_delta05\runs\native_sequence_20261022_134615`, source8fec93bd4d2806ca9b60fb53dc272fe28081f8b8, hosted39753965931, executable `06aa61a49ac249c75b194d3210a48e109296702a87adefe4e59f464f49748c5e`. This refreshes the two already-verified GPU controls; **new aggregate site credit is zero**. It does not approve another source/build, DRIVING/world/race behavior, audio, save functionality, full UI parity or in-process setting transitions.

## Actual native chain and cleanup

The sequence completed all four technical phases in115.421 seconds, with no sequence error, under its120-second bound. Actual marks end at24.1/24.2/24.1/24.3 seconds for the four24-second requests; polling explains the small per-phase overshoot. Each phase reached CARSELECT at21.3/20.9/20.8/20.9 seconds after real TitleStart readiness and scoped sends at9.630/9.042/9.048/9.018 seconds. No driving stimulus or teleport was armed. These are distinct process launches using the same returning-profile fixture and private config seed, rather than changes inside one running process.

| Phase | Owned PID | Valid query packets | Bar/row callbacks | BMP captures |
| --- | --- | --- | --- | --- |
| baseline_off | 53640 | 37 | 0/0 | 15 |
| graph_true | 19788 | 38 | 315/0 | 16 |
| table_false | 41724 | 38 | 0/345 | 16 |
| restored_off | 52136 | 37 | 0/0 | 15 |

I independently counted actual fresh per-phase logs and compared them with result.json and sequence checks. Each process registered the original Core/Debug/Performance/GPU Monitors component once and applied exactly the two expected bool readbacks: false/false, true/true, true/false, false/false. Each private config.used.ini matches these paths and1280x720/windowed/VSync1 settings. Valid completed query packets have frequency100000000 and positive totalMs. Graph and table phases each contain30 positive MenusAndHud/Debug2d callback values, from their actual bar or row consumers respectively. Hidden phases contain no bar/row callback records. No assertion or exception marker occurs in any captured game log. This review does not infer per-counter timing accuracy or same-frame callback/image correlation from these records.

All four result files and complete checks are PASS; their original strict flow-terminal receipts hash-match the actual flow/terminal-status.json files. The receipts retain distinct PIDs, exact private image/start identities, original creation handles, success, input reset, owned cleanup complete, no foreign game and zero asserts. Marks show BelowNormal priority, muted audio and NoAssertRelease disabled. Every process was still alive at the24-second harness stop; cleanup was harness-owned, not a natural game exit.

## Independent pixel and table visual review

I directly viewed all four requested BMPs with view_image. Baseline and restored frames show the car-selection frontend with no GPU graph/table. Graph mode shows the horizontal graph and percentage scale. The exact bound table frame visibly contains the **GPU Render Cost** heading, labeled monitor/value rows including MenusAndHud and Debug2d, and totals. The same content-update notice remains behind/under these overlays; no unrelated UI-completion inference follows.

The graph run actually retained a later bb_003600.bmp as its case-selected final capture, in addition to requested bb_003360.bmp. I independently viewed and bound that fifth image too; both show the graph. All inspected images are1280x720,32-bit BMPs. The manual table pass is recorded separately in `MANUAL_TABLE_VISUAL_REVIEW.json` against the exact frame path and hash originally left pending in sequence_receipt.json. The original pending receipt is preserved unchanged; this follow-on record supplies the requested visual result.

| Phase | Viewed frame | SHA-256 |
| --- | --- | --- |
| baseline_off | bb_003360.bmp | `cc6988b403351644e6839eafca02b898922832a05d0246919658ccfea3039137` |
| graph_true | bb_003360.bmp | `9a8ac2f31b946c324c57d4198467973814bdc2ce2572ac4a9352979873e981d0` |
| table_false | bb_003600.bmp | `9da7eb6d4af0aa4bf96e69aa4b660d4c7335f98daac3196ecdc2ee351570e698` |
| restored_off | bb_003360.bmp | `a1db66f7570da2fdcb4bdacdee09344d576eba1b340a2bcaebe4eb5cd3924984` |
| graph_true | bb_003600.bmp | `5ae0205ee8842051e96119bfe879a14f4f66c0115367bfc01daf0a3938d383dc` |

The table visual result is a positive observation of that retained phase frame. It is not derived merely from graph-grid exclusion or log mode. No historical GPU run is substituted for this candidate, and no same-frame callback/screenshot match is claimed. Across these four cold launches, the expected hidden/graph/table/hidden visual sequence is observed.

## Executable, private stage and protected files

All twelve private staged outputs still match all twelve hosted payload hashes/lengths, including executable, provenance and map. The staging receipt hash matches the actual sequence binding. The enclosing reviewed proposal files, nineteen source/harness pins and eight staging inputs remain exact, and the previously sealed source-policy review is bound in SOURCE_BINDINGS.json.

All twelve normal protected fingerprint entries independently match the pre-stage values, including file existence, bytes, SHA-256 and mtime_ns. These cover the normal executable/config/log and recorded profile saves. Normal game_slots/62032 and Memcard_62032 remain absent. Actual runtime marks use the private stage/slot executable and log with stage/data CWD. The private config has returned byte-for-byte to its seed (`8017ab56482068335a91022ed93aa5329c1510c0fbbbc4274fbcb04c396f818f`); private profile and immutable fixture match `9387be51fdeae0edfad3061379bc60db1d3d82c33f53b12822f36a9f164aa668`. Each case also records its profile restoration complete. Shared asset hardlinks/junctions remain the documented recipe and are not an OS write sandbox.

`SOURCE_BINDINGS.json` retains exact hashes of all108 run files, the source/proposal inputs, five inspected BMPs, stage receipt, twelve payloads, protected fingerprints and restored private inputs. `PHASE_NATIVE_AUDIT.json` retains independent per-phase counts, original terminal data, source/readback/query/callback line witnesses and observations. No extra launch, fixture/helper/case execution, build, CI, source edit, install, commit, publication or additional reviewer was performed by this review. Only the new review directory was written.
