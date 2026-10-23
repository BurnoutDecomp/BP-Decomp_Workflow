# Independent static review: route-save GUI packet delta02

VERDICT: pass

The two remaining delta01 findings are resolved in this exact full composition. No additional material defect was identified within the requested static scope. This is a source review pass only: no Stage, Run, Setup, fixture, harness, test, game, build, CI, C++, or IDA execution occurred. No production, Git, index, or ledger mutation occurred. Only this new review sibling was written.

## Resolved findings

**Case A menu composition.** Lines 105 and 147 now parenthesize each entire dynamic mark expression. Static PowerShell AST inspection records one 67-element suffix array, zero binary-plus nodes with array operands, and both marks as individual `ParenExpressionAst` elements. For the pinned count-zero seed the resulting dynamic mark strings are `mark:save1_empty_slot_1` and `mark:overwrite_same_slot_1`; this correction cannot emit the former separate numeric `1` steps. The case was not evaluated. Case B's correctly parenthesized mark remains unchanged.

**Actual private slot roster.** `Run.ps1:158-175` validates 12 unique hosted basenames, excludes `config.ini` from those payload names, recursively enumerates the actual slot with `-Force -Recurse -ErrorAction Stop`, rejects every directory entry, and requires exact equality with the 13 allowed flat filenames. Thus additional files (including hidden files), nested directories/files, and omissions fail. Reparse-point payload/config entries are rejected by the subsequent existing per-file attribute checks; directory symlinks/junction entries fail the directory check, and extra links fail membership. Each expected payload still receives actual length/SHA-256 validation against hosted pins and its Stage metadata. Config retains its pin/Stage/hash checks, and the initial private seed and selected ProfileFixture retain their exact hash/reparse checks. The receipt includes the actual roster and is written only after the complete preflight returns (`:304-305`); `Start-Process` follows at `:306`, so failure stops before Setup/native input.

## Retained complete composition

The full delta01-to-delta02 comparison is captured in `DELTA01_TO_DELTA02.diff`. Executable-script changes are limited to those two parentheses, the actual roster correction/receipt field, and packet identity strings in Run and Stage. Observer, Probe, Case B, both menu prefixes, and the entire canonical runner proposal are byte-identical to delta01. Remaining edits update packet metadata, hashes, and the report-versus-seal labels.

Both cases retain `close.ready.requested`; the observer appends `.requested` to `close.ready`, validates final readback, performs the exact-owner WM_CLOSE action and creates `close.sent`. The full runner proposal retains the exact three-line MenuScript-only refresh after Setup, beside DiagEnv. Its preimage/postimage/diff are unchanged. Physical `tools/tests/run_case.ps1` is still the raw preimage (`2f6b63b8b42edc8032bbaf0a90461a4f297f602509539a3a88f8055e3d0bdb6f`) and equals the supplied preimage after LF normalization. The fe64 provenance was independently established in the earlier sealed review; this review confirms the full bytes and narrow transformation without invoking Git.

The full scripts retain the normal GUI empty-slot Save, one-landmark edit, same-slot overwrite through `CNOnlOvGOQn`, two fresh autosave-request/WRITTEN observations and stable validated payloads, exact independent Case B profile copy, ordinary Option0 cold load, full settings/ordered-landmark comparison, strict original terminal receipts, owned cleanup, private profile/config restoration, and unchanged normal-file fingerprints. The 0..5 initial count guard remains in Stage and Case A; Root's count-zero seed observation and exact SHA `1d8360f829a7ab5e1b8b42536455e0786ea21b97eacc677911591cc3562f28e8` remain explicit. N>=6 and original scrolling behavior remain outside acceptance; no game C++ workaround is introduced.

A/B flow limits remain 330/210 seconds, outer limits 450/330, autosave wait 120 seconds per request, and close wait 30 seconds. Archive checks remain 1..96 frames and <=64 MiB logs. Root's selected-row/overlay/map visual comparison remains a required later gate. No claim of actual Save, overwrite, disk persistence, cold-load success, or timer repair follows from this static pass.

## Exact pins and validation

All 17 input manifest members were rehashed successfully. Input manifest seal: `4a823bf7b44fda27b251f38bb5e65ec35a6ca9aa2356922d2eaf2132a8f931d2`.

| Input | SHA-256 |
|---|---|
| Case A | `7fcc1ff2c2ff107168703d05f0bd5c6f4720e4cdd29472c32d28cf6be00478bf` |
| Run.ps1 | `698585f97bd02ace480d8075c5988473d0b9097efcb4b305d5fc0ae77792ca50` |
| Stage.py | `fb22e283eb4de3b9a3fe89a167fe7bf9e3508d0aa76b0be59dc4c7db0b0acf43` |
| Runner normalized preimage | `93c1ab4d66b13dac86e7207bb3f21df65b944be85f0fbc902b2120b6fefa63f8` |
| Runner postimage | `bfe2028ebbb9a6c22f6762aaef15cc92eebfcb713326c22aed9c672809d96e16` |
| Runner diff | `34fa95ef77eb1868858034c5f0bb35c21e4d37e963692be4cd867d2b1a547200` |

Five PowerShell static parses passed; both Python AST parses and packet JSON parsing passed. All eight template packet-file pins match the actual files. `STATIC_POWERSHELL_AST.json` and `REVIEW_INPUTS.json` contain the evidence and complete binding inventory; the full reviewed packet and reference snapshots are preserved under `inputs/`.

The two previous FAIL reviews remain intact and their manifests were fully verified. Original report SHA `bac04b9a3f17e21a7bb714413342a26e4ba31f6f18a51416bae23bcaa43f7ca7` is correctly distinguished from manifest seal `9508f728a45add578604dda68c866194b3b3692debeca5c6c50d01fc9478a64d`. Delta01 report SHA `9cff027521217febcdec51dc20aa87996f3c2df7bd87113537bf9c7cbf58862a` is correctly distinguished from seal `94ee4160e31e39c099960feae1204d9b6fbce619ed2cc4dbc348da3ceb556a18`. This pass applies only to delta02 and does not change those earlier verdicts.

There is no pins.json, stage, or run in delta02 at review. Root still must apply and bind the reviewed runner proposal, bind the final source/tree/workflow/executable/host/config inputs, review a fresh stage and its normal-file protection receipt, and own any later execution and visual acceptance. This report authorizes no execution.
