# Independent GUI12 reporting fallback delta04 review

VERDICT: pass

The narrow F1 repair is correct for the reviewed exact source bytes. The corrected Run.ps1 is coherent with the exact unchanged delta03 report_run.py and launch_watchdog.py. This is source approval of that composition; Root's separate wrapper pin, integrity and Root-binding rebinding remains a prerequisite to later use. No runtime or gameplay credit is added.

No complete interrupted delta04 independent review was found among matching sibling directories or retained review/seal files. This report is an independent review, and accepts no earlier conversational indication as approval.

## F1 is resolved

At Run.post.ps1:176-177, the reporter error is converted to a string and bounded independently to its first 1,000 characters. At line 185 that value becomes reporter_error. Existing run_error and preflight_error bounds are preserved at 174-175; post-launch preflight_error remains null.

The same ordered fallback object is serialized once at 188. Its compact JSON goes to structured stdout at 189 and to probe_receipt.json at 190. A full existing run-error prefix can still fill run_error, but can no longer erase reporter_error from that fallback object. Classification remains INCOMPLETE_EVIDENCE_RETAINED, manual review remains pending, and behavior_credit remains false.

The entire pre/post images were inspected. Reconstructing the postimage from the preimage using only the two added local statements and one added field reproduces its exact UTF-8 byte hash, including LF line endings: three inserted lines, 188 bytes, no other byte change. The delta04 preimage is identical to delta03 post/Run.ps1. The prior delta03 FAIL remains retained and unmodified.

## Retained bounded fallback evidence

The smoke source parses the complete supplied postimage, finds exactly one Write-FallbackReceipt function AST, and invokes only that function's exact text. It supplies synthetic local variables and four output paths. It does not invoke Run/Stage or any native entrypoint. Its assertions decode both the captured structured stdout object and the written JSON object.

| Retained case | run_error chars | preflight_error chars | reporter_error chars | launch_attempted |
| --- | ---: | ---: | ---: | --- |
| long_preflight | 1000 | 1000 | 31 | false |
| oversized_preflight | 1000 | 1000 | 1000 | false |
| launched_failure | 1000 | null | 29 | true |
| empty_preflight | 47 | 0 | 37 | false |

Direct inspection of all four retained JSON files confirms the exact expected strings and fields, not only their lengths. Each keeps the incomplete classification and behavior_credit=false. The retained stdout has four PASS summaries; stderr is empty. The manifest records exit 0 and four synthetic cases. The task identifies this as a PS5.1 check; these delta04 output files do not independently record the host version or complete invocation, and the raw structured stdout is consumed by the assertions rather than retained. This review therefore treats the records as retained synthetic evidence, not an independent rerun or full Run/watchdog execution proof.

## Source composition and unchanged protections

Run.post.ps1:138-165 still uses the reporter's existing terminal/archive modes and option names, including the single --run-error= token for an empty value. reporter_error is a local PowerShell fallback field; it introduces no Python argument or parser requirement. The unchanged Python parser at report_run.py:353-396 accepts the Run arguments.

The reporter still calls write_terminal(args) before archive work (202), accepts a singleton raw-channel object or a list of at most two object rows (234-249), and binds each retained raw copy's bytes/hash to the run_case manifest. Run:339-352 retains source/copy containment and source hash/byte checks. Python report/archive classifications still distinguish original CASE_FAIL from a structurally complete case pending visual review; behavior_credit remains false.

Python writes normal reporting metadata from its own schema, as before. A later successful Python report may replace the earlier fallback receipt; this pass approves reporter_error in the emitted/persisted fallback object, and does not claim permanent schema extension of every later Python receipt. Structured fallback output remains emitted before the file write. The existing last-resort catch emits a diagnostic text marker if structured receipt creation itself fails; it is not a successful JSON receipt.

launch_watchdog.py:129-136 still derives the Desktop PowerShell module root, copies the environment and sets the child module path; line 170 supplies that child environment. Its launcher arguments match Run's RepoRoot/RunDir parameters. The watchdog still refuses stale script pins before launch (137-146).

The full sources retain the 240-second accounting/wall limits, 512 MiB working-set limits, 0.1-second watchdog polling, BelowNormal priority, one-shot CreateNew boundary, exact owned-wrapper termination, and disclosure that descendant cleanup/restoration is unverified after a watchdog guard trip. Run retains exact source/artifact attribution, Root/case/staging binding, foreign-game refusal, private-state fingerprint restoration, normal profile membership/fingerprints, and hash-checked generated-script cleanup. None of these paths changes in delta04.

## Root prerequisite and frozen evidence

The delta03 proposed wrapper pins still contain Run hash 9e4b483af0af1695996b1c5cbd2e3c4b4cb1d5edf2fc58dde31fea5c1db313d8. That pin does not approve delta04's 2739dd4473f33c47d19d826f8be83bb12abcf35c6611336b07f8c9c7cddf7963. Root must construct a new derivative with the correct complete script pins, packet integrity and corresponding Root/case/staging binding chain. Existing binding values or prior reviews must not be reused as approval of changed bytes. This review does not perform rebinding or authorize an execution; Root owns publication and any later execution.

Case.ps1, Case.reviewed.ps1, CONTROLS.json, PINS.json, CASE_PINS.template.json and Stage.py have identical exact delta03 pre/post hashes. Their six hashes are retained in REVIEWED_INPUTS.json. The unchanged reporter/watchdog hashes below pin the reviewed composition.

The original native run native_20261022_224327_cc3d2d0d remains FAIL, solely on the recorded exact-readback defect b006 value-count=0. Its result still records 0 asserts and flow exit 0. Its receipt records 24 normal fingerprints, 12 payload checks and successful cleanup/restoration. Seven selected actual original evidence files still match their bound bytes/hashes, including result.json SHA-256 993aab5e54660b7b6a3fda423b49d773c5b8ddb8c34898b4429acabdc0d7a0d5. No case verdict, baseline, result, raw log, frame, frozen packet, index, production file or commit was changed.

## Exact SHA-256

| Complete file | Bytes | SHA-256 |
| --- | ---: | --- |
| delta04 Run.pre.ps1 / delta03 post/Run.ps1 | 32445 | 9e4b483af0af1695996b1c5cbd2e3c4b4cb1d5edf2fc58dde31fea5c1db313d8 |
| delta04 Run.post.ps1 | 32633 | 2739dd4473f33c47d19d826f8be83bb12abcf35c6611336b07f8c9c7cddf7963 |
| delta03 post/report_run.py | 19438 | eb629ce857ed8cc0056a8afafddfba0f08f05066d18a2503a9e6c62b56d0cdee |
| delta03 post/launch_watchdog.py | 11535 | 8e2185ac515da37a600734ab68845045f153af6686432e0c46b07507fbbf79fb |
| Retained delta03 FAIL report | 11436 | 90e54af760e4de8247d0890aab498c96a6a8283592676eb11300aee0901ec2db |
| delta04 smoke.ps1 | 2314 | 845d46a4d496f2cb82f3684d7f74ace9a6fcd75b107cea0e52189fcf06250d4e |

All 13 delta04 seal entries verify; INTEGRITY.sha256 hashes to aff0c1b53fea8a6224703f4ec116460e1577f79a58fe63e3847328a13c15822a.
All 114 delta03 seal entries verify; INTEGRITY.sha256 hashes to e2f57bfee566fdd1a34ce3d0ed005325ef030ad43b5d7a13bb54edc700883f75.
All 16 original source-packet seal entries verify; INTEGRITY.sha256 hashes to ccebbbfee87f1f41bd2b4c44d4e97f0c500648be516db924cee13dabba911956.
The previous delta03 review's three SHA256SUMS entries also verify.

REVIEWED_INPUTS.json distinguishes seal-verified inventory from the exact sources/evidence reviewed. INTEGRITY.json binds this report and that input manifest; SHA256SUMS.txt additionally seals INTEGRITY.json without self-reference. Only this new sibling review folder was written. No candidate, smoke, fixture, C++, game, native harness, Run, Stage, watchdog, CI or IDA was executed, and no subagent was spawned.
