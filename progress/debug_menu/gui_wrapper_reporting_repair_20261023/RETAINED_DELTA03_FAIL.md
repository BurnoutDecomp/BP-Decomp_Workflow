# Independent GUI12 reporting repair delta03 review

VERDICT: fail

One remaining diagnostic defect prevents approval of the stated fallback contract. The empty-argument repair, Python archive call repair, singleton log-manifest support and Desktop PowerShell module-path change are otherwise consistent with the inspected sources and retained bounded checks. No candidate script or fixture was executed for this review, and no behavior credit is added.

## F1 — P2: keep reporter failure text independently of the existing error prefix

Location: `post/Run.ps1:170..175`, with the persisted/emitted fields at `182..187`.

`Write-FallbackReceipt` copies `$runError`, appends `reporter: $ReporterError`, then truncates the **combined** string to its first 1,000 characters. It separately copies/truncates the same old prefix into `preflight_error`, but has no separate reporter-error field. Both the JSON file and structured stdout therefore lose the reporter failure when the existing error already fills the bound.

Source-only counterexample: `$runError` contains 1,000 `P` characters and `$ReporterError` is `Python terminal reporter exited 1`. After line 174, `run_error` consists solely of the 1,000 `P` characters. `preflight_error` carries the same prefix. `report_status` indicates that a reporter failed, but the failure text supplied to the helper is gone. The new helper is called after appending additional terminal/final reporter errors at 329/428 as well, so tail loss can also occur as errors accumulate. This reasoning follows the assignments directly; no PowerShell/fixture execution was used.

Required correction: preserve a separately bounded `reporter_error` alongside `preflight_error`, or reserve bounded space for the reporter text before clipping the combined summary. Keep the incomplete classification and `behavior_credit=false`. The existing static `FALLBACK_SOURCE_INSPECTION.json` only lists matching source lines and does not exercise this case.

No source correction was made. Root can resolve F1 in a new sealed derivative while retaining this packet and the original failed native run.

## Exact source review coverage

The complete exact pre/post byte streams and all 11 changed-source hunks were inspected; in-memory application of each diff reproduces its complete postimage. The full postimage bodies of Run.ps1, report_run.py and launch_watchdog.py were read, including their unchanged execution/ownership/protection paths. All ten preimages equal the sealed original packet's actual files.

### Run.ps1

- Source 159 builds one argument, `('--run-error='+[string]$runError)`, so an empty error produces the single token `--run-error=`. The retained PowerShell 5.1 argument smoke records exactly one argument and an empty parsed value. The legacy split empty argument that caused the original argparse failure is removed.
- Source 167..187 constructs a compact incomplete fallback with actual error text, case/launch state and `behavior_credit=false`, emits its JSON before the file write, and writes it before Python reporting is attempted. Terminal/archive reporter failures route back through this helper. F1 is the remaining text-preservation problem.
- The last-resort catch emits a text marker if fallback serialization/write fails; it should be treated as emergency diagnostics rather than a successful structured receipt. This review grants no fallback-execution credit: the retained packet deliberately did not execute Run.ps1.
- Original 240-second accounting, 512 MiB working-set checks, one-shot CreateNew attempt marker, BelowNormal priority, exact source/artifact/Root binding checks, private-state backup/restore, foreign-game refusal, private-only slot checks, normal profile membership/fingerprints and hash-checked owned-script cleanup remain present. No cap, callback/control, game argument or original-case baseline was changed by these hunks.
- Source 333..350 still checks raw manifest source/copy containment, source existence/hash/bytes and retained-copy bytes; the reporter subsequently hashes and binds the retained-copy bytes to the same manifest. No duplicate raw copy or raw rewrite was added.

### report_run.py

- Source 202 calls the actual `write_terminal(args)` function before archive work and returns 1 if it fails, replacing the original undefined `terminal(args)` call.
- Source 234..249 accepts a singleton object by wrapping it in a one-row list, accepts a list of at most two object rows, rejects other shapes/non-object rows, checks source/copy path containment and binds the retained copy's hashed bytes and SHA-256 to the run_case raw manifest. The actual source hash/byte comparison remains in Run.ps1 as described above.
- File/frame/log/total-byte caps, chunked hashing, stat checks before/after hashing, memory/deadline checks, incomplete manifests on failures, preservation of original CASE_FAIL, and unconditional `behavior_credit=false` remain in the full source. Output mutations are the reporting metadata files; case result/raw evidence is read, not rewritten.
- Synthetic byte blobs prove the bounded archive/reporting paths only. The tiny synthetic BMP is not visual/gameplay evidence, and `STRUCTURAL_CASE_COMPLETE_VISUAL_REVIEW_PENDING` remains separate from a behavior approval.

### launch_watchdog.py and proposed pins

- Source 129..136 derives and checks `%SystemRoot%\System32\WindowsPowerShell\v1.0\Modules`, copies the parent environment and supplies that explicit child PSModulePath at 170. It does not change the global environment.
- The 240-second wall guard, 512 MiB working-set guard, 0.1-second polling, BelowNormal creation/verification, exact created wrapper handle termination and unverified-descendant-cleanup disclosure are unchanged. No watchdog or helper was launched by this reviewer.
- The retained PS5.1 module probe uses an isolated child environment and resolves Get-FileHash with the Desktop module root present. Its recorded hash matches the retained module-target bytes. The independent retained root probe also records successful Get-CimInstance, Get-Process, Copy-Item and ConvertTo-Json resolution; its raw stdout/stderr copies were inspected.
- Windows os.environ uses uppercase keys, and CPython 3.12.6's CreateProcess environment builder normalizes case-equivalent keys while keeping the last inserted one. This supports the supplied explicit child value for the observed runtime. References: [Python 3.12 os.environ](https://docs.python.org/3.12/library/os.html#os.environ), [CPython v3.12.6 environment builder](https://raw.githubusercontent.com/python/cpython/v3.12.6/Modules/_winapi.c).
- `WRAPPER_PINS.proposed.json` differs from the preimage only in the three repaired Run/reporter/watchdog hash fields; all three match the proposed postimages. The ordinary post/WRAPPER_PINS.json retains the original pins, so this is a proposal awaiting Root's explicit rebinding, not an executable deployment. Root's existing hashes/seals must not be reused as approval of the changed scripts.

## Retained checks: independently inspected, not rerun

| Retained scenario | Inspected outcome |
| --- | --- |
| single_object_case_fail | terminal/archive exits 0/0; singleton raw object; verified archive with 5 rows; CASE_FAIL preserved; behavior_credit=false. |
| two_channel_list_complete | terminal/archive exits 0/0; two-row raw list; verified archive with 6 rows; STRUCTURAL_CASE_COMPLETE_VISUAL_REVIEW_PENDING; behavior_credit=false. |
| single_object_file_limit | archive exit 1; incomplete archive and receipt; error `evidence file cap exceeded: 5`; zero rows hashed; raw source/copy bytes remain identical to their recorded before/after hashes. |
| Windows PowerShell argument | recorded 5.1.26100.9711, one `--run-error=` token, parsed empty string, exit 0. |
| Windows PowerShell module | recorded 5.1.26100.9711 child, Desktop root present (PowerShell also prepends the Program Files module directory), Get-FileHash target hash matches, exit 0. |

The retained successful smoke summary equals the copy embedded in SOURCE_BINDINGS.json. Its per-scenario probe receipts, result JSON, archive rows and raw log source/copies were read directly; each retained archive row matches its actual bytes/hash. The first attempt's overstrict module-path equality check is explicitly retained as a diagnostic. It is not evidence that the entire Run/watchdog path was executed. No such execution is claimed or credited here.

## Unchanged case/native evidence

Case.ps1, Case.reviewed.ps1, CONTROLS.json, PINS.json, CASE_PINS.template.json and Stage.py are byte-identical pre/post. Their six protected hashes are included below and in the reviewed-input manifest.

The original native result remains FAIL, with exactly one failed check: b006 `value-count=0` in the exact readback check. Its retained result still records 0 asserts and flow exit 0, and its probe receipt records 24 normal fingerprints, 12 payload checks, successful owned/helper cleanup and private restoration. Original selected result/report/receipt/raw-manifest/launch-result/stdout/stderr evidence still matches its bound hashes. No case verdict, roster, baseline, original run, raw log, frame or production file was changed by this review. No pixel, gameplay, newer-source active-wiring or reporting-completion credit is inferred from these receipts.

## Complete proposed postimage hashes

SHA-256 covers the entire files. Only the first three scripts and the separately proposed wrapper pins change; the six protected source inputs remain unchanged.

| Postimage | Bytes | SHA-256 |
| --- | ---: | --- |
| `Run.ps1` | 32445 | `9e4b483af0af1695996b1c5cbd2e3c4b4cb1d5edf2fc58dde31fea5c1db313d8` |
| `report_run.py` | 19438 | `eb629ce857ed8cc0056a8afafddfba0f08f05066d18a2503a9e6c62b56d0cdee` |
| `launch_watchdog.py` | 11535 | `8e2185ac515da37a600734ab68845045f153af6686432e0c46b07507fbbf79fb` |
| `Case.ps1` | 42914 | `f9cc0f23f709f9e7d01bc59fb7c192458752b6b37f524a4caed74c1d088d4f6e` |
| `Case.reviewed.ps1` | 42914 | `f9cc0f23f709f9e7d01bc59fb7c192458752b6b37f524a4caed74c1d088d4f6e` |
| `Stage.py` | 15498 | `facc14c6a65d9177dbc2f32f382fa4fde4f44777cd8971ef16f8baa997468436` |
| `CONTROLS.json` | 24788 | `752488b092dc3f2047eaa5dc85f8484bc95186fe16df6cd0d49aa9c8f86aefe0` |
| `PINS.json` | 3289 | `5339c11905fff4b0f8e7fb47f1d08fe5fcfb43c3ba48f79b1c33955945100347` |
| `CASE_PINS.template.json` | 2929 | `8e33e990d1e55088719c08a4a161ac078a3442c90c8607e177bb85bfc12b9419` |
| `WRAPPER_PINS.proposed.json` | 11744 | `2bcda7d4b58244c0bd7dd62d1394a8c0c5d716df08ab6c2f1b9f3d8bbbf35334` |

## Review integrity

The packet seal file's SHA-256 is `e2f57bfee566fdd1a34ce3d0ed005325ef030ad43b5d7a13bb54edc700883f75`; all 114 listed entries match. `REVIEWED_INPUTS.json` records all frozen packet files, the original external preimages/seal and bound original native evidence, complete proposed postimage hashes and F1. Its SHA-256 is `6f293d386a30b92d70db8e498a5251feef38a98726cc117fc2c88935f1b0f5e3`. `INTEGRITY.json` and `SHA256SUMS.txt` seal this report and the input manifest without a self-referential report hash.

Only this new sibling review directory was written. The reviewer did not run Setup, Stage, Run, launch-case, launch_watchdog, helper, fixtures, a game, C++ compile, CI or IDA, and did not modify a frozen/original/production file, Git state or commit. Root owns any correction/rebinding or later execution. No subagent was used.
