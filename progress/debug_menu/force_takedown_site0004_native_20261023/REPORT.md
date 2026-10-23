# Force takedown: independent source/native review

VERDICT: pass

Site disposition: **verified for `BrnGameState::TakedownManagerDebugComponent::OnActivate#0004` — Force takedown**, on source `9af6a868959578f4eafa9af0d69ccd27081667a0`, hosted run `39965534136`, executable `31de06d9d57a3580091f51eec33acd3d900b815a8b318ad777271a0165206b7f`. This adjudicates one debug site. Inventory and the already verified vulnerability site #0002 were not changed.

ARTIST OnActivate `0x82366378` registers ForceTakedownCallback with this component as its context (r3=this, r4=function, r5=context, r6=label at the original registration call). The target C++ matches. The complete callback at `0x823597F8` and its Clear callee at `0x82355CE8` also match the named C++ side effects: clear all eight revenge flags, waiting, chain and multiple state; set last-taken-down to FLT_MAX, victim-crash time to zero, last-takedown time to -1; then arm player record 0 with victim-crash time zero, waiting=true, aggressor 0, victim 1 and STANDARD type 0. Neither original nor C++ clears the rest of the pending event wholesale. These source bodies are identical at 91a and 9af6. The source comparison covers all original stores; the native logs do not directly measure every private reset field.

The actual retained activation and F2 scripts match the reviewed controls. Fresh original alias/function-path and F2-binding acknowledgements precede one scoped F2, after mode 3/state 2/controllerActive 1, HUD 0/30, empty-queue/no-prior-producer guards and fresh motion at 72.80 mph (before) / 72.63 mph (fixed). F2 is rebound before the sole original CALL. No score or queue is directly written by the stimulus.

| Retained run | Accepted producers after F2 | All GUI translations | Intended type0/aggressor0/victim1 translations |
|---|---:|---:|---:|
| 62054 / 91a before | 2 | 2059 | 1220 |
| 62055 / 9af6 fixed | 3 | 3 | 1 |

These counts were recomputed from raw logs, independently of CASE PASS. The fixed run's other two translated events name aggressors 5 and 1; they are not additional player callback credits. The intended fixed event has a depth-1 push, matching typed translation and visible player count 1/30. The before control shows the old persistent output replay; its inflated count is not a callback-generated score claim.

Independently viewed, hash-verified frames show both baselines at 0/30 and 5m30s (`bb_003240`). Before `bb_003420` shows 314/30 and 47m16s; `bb_003960` shows 1145/30 and 157m51s. Fixed `bb_003420` shows 1/30 and 5m32s. Fixed later `bb_003600` is a crash view; `bb_003780` shows count 1 but hides the clock. **Later timer countdown remains insufficient and pending.** No organic collision, victim-slot activity, raw event424/deadline readback, or broader Road Rage delivery acceptance is claimed.

All 44 before / 43 fixed archived files were rehashed, including every one of the 23/22 BMPs and both frames.csv files. CSV present identifiers match all retained BMPs. Raw private logs match flow copies byte for byte. Root/Stage/runtime-Case binding hashes, the exact reviewed Case, all twelve staged payloads per role, executable/provenance/workflow identities and original terminal hashes were independently verified. Both cases have clean self-exit/code 0, zero asserts, retained matching scripts, owned-script removal and the reported unchanged 24 protected normal files. The fixed executable provenance is 9af6 even though the separately recorded local checkout is 91a.

Before archive SHA: `1debdce774cc55f83e4e116d04f707b611aa54232f0237628f8813ce7951d820`; raw-log SHA: `96d7faa27abddaeb562380cb11e5b3d65eb9d7d30b1228a2ff3852345d1b3f16`.

Fixed archive SHA: `211603aff12b2c91eec3fa37abcca3d3cb5362d22a14608c9794eb90906baaec`; raw-log SHA: `eaf0cb94cdb873be3cec42b628b9265e05367bfd1b482dbb8da36ac3b1ced7b1`.

`NATIVE_EVIDENCE.json` contains exact run paths, every archive/frame hash, raw line anchors, visual observations and source pins; `SITE_DISPOSITION.json` records the site-only decision. No game, harness, test, build, CI or input was executed for this review. Only this new report sibling was written; prior runs, FAIL evidence, production, inventory and Git remain untouched.
