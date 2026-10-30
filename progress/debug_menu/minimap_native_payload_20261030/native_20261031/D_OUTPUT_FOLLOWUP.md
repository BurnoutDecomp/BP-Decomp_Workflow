# D: output follow-up

NATIVE_RUNNER_DESIGN_VERDICT: PASS
RUNTIME_DATA_PRESERVATION_PLAN_VERDICT: PASS

These verdicts apply to manifest `8eea2e64476a49c6d5014fe76a33657d156fa37ede0ca9887fefb271359e94cd`, subject to its runtime free-space and frozen-input gates. No game was launched, so actual native preservation remains UNVERIFIED. The original review's production-source PASS and full-visual-verification FAIL remain unchanged. The planned run supplies data-preservation evidence plus frames for inspection; it does not certify the complete reported visual repair.

The runner is at `D:/Reverse/BP-Decomp_Workflow/scratch/minimap_regression_20261030/native_pair`. I compared its preserved `MANIFEST_7453b8d8_before_D_output.json` with current `MANIFEST.json` and independently verified both hashes. Only the Run.py, freeze.py and OfflineTest.py file hashes differ. Build receipts/artifacts, production commits, diagnostic patches, profile/config/asset identities, external dependencies, capture parameters and all budget amounts are unchanged. Reversing exactly the stated edits reproduces each original CRLF file hash, which bounds the change beyond a manifest declaration.

## Capacity and output change

- `Run.py:7` now places retained run output at `P/native_pair_runs` on D:.
- `Run.py:23–30` adds remaining stages and remaining captures/logs to the unchanged 2 GiB floor in one D: free-space check, before output/stage creation. The explicit drive check rejects an output root outside the budgeted D: volume. Existing reparse-path checks remain.
- The initial requirement is `2147483648 + 219407916 + 445579264 = 2812470828` bytes. The fixed-side requirement is `2147483648 + 109703958 + 256344064 = 2513531670` bytes. Subtracting the first side's allocated stage share and 189235200-byte run allocation from the initial total gives the fixed total exactly. Thus the second side reserves only the still-needed storage while retaining the same floor and shared reserve. The fields still named `C_capture_*` are reused budget values; their application is now to D:.
- `Run.py:57–61` gives the harness process a private `run/temp` directory through both TMP and TEMP; its child processes inherit it. The actual command and invocation log use the new run directory. The changed freeze.py line 58 prints the combined D: requirement instead of separate D:/C: figures. OfflineTest.py lines 50,58–61 check the output location and both derived requirements.

The new helper does not relax source/save/config/asset checks, record caps, log limits, process ownership, cleanup receipts or postchecking. C: remains a read source for the retained diagnostic builds; the runner's retained captures and logs now use D:. This review does not audit the separately reported scratch compression operation.

## Independent verification

I reevaluated current freeze.collect() and obtained exact equality with the new manifest, including all 31 runner file hashes, six external dependencies and 30 diagnostic artifacts. Old/fixed stage receipts, OLD_TRIGGER.json and PAIR_RESULT.json remained absent.

I reran the actual OfflineTest main with only its transient fixture directory redirected into this review directory, and reran TestProfileGate.ps1. All passed: output/budget assertions, actual postchecker positive fixture and corrupt-frame/malformed-event negatives, PowerShell parsing, profile identity/sign-in negatives, FIFO/ambiguity/sequence/CRLF/cap tests. Temporary fixtures were removed.

I also tested Run.run_side's actual free-space branch without allowing any output or stage mutation: each side rejected its threshold minus one byte with `D floor + remaining stages and capture/log bound`; each accepted exactly its threshold and then stopped at an injected exception before OUTPUT.mkdir could write anything. This verifies the real guard beyond the arithmetic assertions. Actual disk capacity and subsequent concurrent disk consumption are still checked by the runner at execution time.

No material defect was found in this targeted change. No production source or diagnostic binary was changed; no game, publication or cleanup action was performed by the reviewer. Original REVIEW.md/REVIEW.json are preserved.
