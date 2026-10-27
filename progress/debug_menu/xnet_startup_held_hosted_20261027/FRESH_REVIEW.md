# Independent XNet hosted-job integration review

VERDICT: pass

This pass covers only the exact proposed workflow integration against B5 `72fe9e2115ed38f7d89ebd5c56a3ae0b73f1017b` and workflow preimage `464a6c95a8ded797b4aed87e11f63bcf61084ec9`. The separate source/fixture composition review remains unchanged. This report records no hosted test result, compiler result, shipping build success, native behavior or menu disposition; dispatch and integration remain Parent-owned future actions.

| Exact reviewed input | SHA256 |
| --- | --- |
| Seal | `49f187200bae522fa8e24499d1d78445c5ec89d1b11721fc058dd7f4a9db2ed6` |
| Manifest, 17 files | `e30a07ff80038b85fea9060d00d2b266fa76b318a733f59feeaee23a5dd24b90` |
| Reviewer packet | `b60019a42959e62e67588072f1cff5a0056b31a0b875fac65136c2f914d554c9` |
| Bindings | `1542938800c7cdd7e5d33d51557b0864350cd0a3fc210cd4602cc9ebbeec2104` |
| Workflow preimage | `9887a9298b4869d96adcba2bccfc951481afe63e7e8ef98a3de505fad660238f` |
| Workflow postimage | `e723ea0f33edba772cf7a2029efcd33c1371eede3974130879cb49f85b7d916b` |
| Literal workflow diff | `9163930ccd35f6ce8389246ed7118eb10cb0f75a871e572892d3a62f20354501` |

The proposed workflow's Git blob is `8bb04ac77e818db72fbfcdadd47f98ca6b1305d4`. The preimage is raw-byte-identical to the actual `464a6c95` Git object. All 17 manifest entries match bytes and hashes. `EVIDENCE.json` records 91 successful static/hash/parse checks and no failed joins. `POWERSHELL_PARSE.json` records zero syntax errors in both new PowerShell blocks, parsed with PowerShell 7.6.9 and never invoked. YAML was parsed with duplicate-key rejection; the three retained Python files were parsed as AST only.

## Default shipping lane preservation

There are 16 original dispatch inputs. Every existing input, description, required/type/default setting, shipping step, environment value, action, compiler cache key, command, artifact path, permission and concurrency setting is preserved. Removing only the new input block, the one candidate job condition and the appended job restores every byte of the original workflow. The parsed original workflow structure is also equal after exactly those removals; the supplied literal diff reconstructs the postimage.

`run_xnet_startup_held_only` is an optional boolean with default false. The original candidate job adds only `if: ${{ !inputs.run_xnet_startup_held_only }}`; the new job uses the complementary positive condition. Thus default dispatch retains the original candidate lane, while explicit true selects only the source regression lane, even when other existing regression switches are set. It does not imply that a skipped shipping build passed. GitHub documents the typed `inputs` context, `github.workflow_sha` as the workflow file's commit, and `runner.environment` values used by these conditions/guards. [GitHub Actions contexts](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts).

The workflow retains read-only contents permission and its existing concurrency group with cancellation disabled. The new lane does not invoke the shipping checker, publish a normal package or activate original main/outer code.

## Compiler context verified from both actual revisions

Each retained compiler-provider file is raw-byte-identical in **both actual Git objects**, `464a6c95a8ded797b4aed87e11f63bcf61084ec9` and previously reviewed `9b0cfc8afe7fa247866464df5a781456d8b2991a`. This conclusion is independently derived rather than inherited from the Root composition narrative. `EVIDENCE.json` retains both Git blob identities and SHA256 values.

| Canonical provider | Same raw SHA256 at both revisions |
| --- | --- |
| tools/build/msvc_env.bat | `64a57b7edcbc7ba793316cdafc19a74b64106ae276f3771d93996e766c76f3b6` |
| tools/build/msvc_flags.txt | `f409e36fd3bb17cd8ced47f33fb9488c667a260d4dd274a7b6a1a6643356bfc2` |
| tools/build/msvc_includes.txt | `e08ea1f7a1243ec960cc41d4d2137796e86a13e949cd6e59fe5baf6c82e80acc` |

The SDL3 include tail is present in those identical include files. All three canonical provider files satisfy the retained runner's existing LF hash contract. The workflow checks out its own exact workflow revision, selects Windows 2022/MSVC x64, and does not substitute an ad hoc compiler-provider file.

## Exact source, hosted guards and invocation

The six-step source job uses Windows 2022 with a 30-minute outer job timeout. It checks out the workflow at `github.workflow_sha`, validates the B5 input as exactly lowercase 40-hex through an environment variable, then checks out `BurnoutDecomp/b5-decomp` at that input under `b5-decomp` with recursive vendor submodules. Both checkout steps disable credential persistence. User input is not interpolated into shell source.

The execution step supplies the exact source input, actual `runner.environment`, and Jobs4, then explicitly calls the retained `python -B .../run_xnet_startup_held.py --workflow-root "$env:GITHUB_WORKSPACE" --out build/candidate/artifacts/xnet-startup-held --run`. A nonzero exit throws. Default working directory and the nested checkout layout agree with the runner's actual REPO/root resolution. Its retained guards require Windows/X64/win22, genuine GitHub-hosted context, positive run/attempt IDs, exact actual source HEAD, tracked source/input hashes, and a dedicated output below the workflow artifact root. Existing evidence cannot be overwritten.

The full runner and both helpers were read. Seven fixture/helper context files exactly match the actual `72fe9e21` Git objects and the previously reviewed composition files. All twelve B5 source/provider/fixture contract entries independently match the actual `72fe9e21` source, including the three production snapshots. The prior composition review hash remains `01631364e0bc1e6aa184059aee53521dfe0bd934e44eeab1713fbf212fe0adee`. No original caller, expected failure, production extraction or owned-job requirement was relaxed.

The actual runner still creates a suspended, hidden, below-normal worker inside its kill-on-close Windows Job before resuming it. Compiler and fixture descendants inherit that ownership. The worker is bounded at 900 seconds; cleanup has its separate five-second bound. Failed assignment terminates the still-suspended owned child. A pass requires zero owned descendants, signalled child, closed job/process/thread/stdio handles and the post-cleanup transcript hash. The parent re-derives generated production inputs and verifies each raw check roster, numeric exit, executable and input hash after cleanup. No global process search or cleanup is introduced.

## Retention and limits

An `always()` artifact step retains only the dedicated source-regression directory with run/attempt identity, one-day retention and missing-files-as-error. Failure receipts/raw candidate and old-control outputs are retained when produced; a missing artifact remains an error. This source lane does not upload a shipping executable as a completed build or relabel the original aggregate/full-link failures.

The intended 117/0 candidate checks and genuine unchanged-caller 14/2 negative control are still authored expectations, not observed results. Native Winsock, owner activation, successful balanced release, full transport and the unresolved full-frame link remain outside this review. Only this new scratch review directory was written. No supplied runner, test, case, fixture or checker was evaluated; no compiler, game, input, CON, shared source, Git or ledger action was performed.
