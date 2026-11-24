# Byte-match hooks

The hooks use the native checkout selected by `work match` and are opt-in per environment.
From the Workflow checkout where you want to try them, install the existing Git hooks and
start Codex or Claude Code from that directory with the environment variable set.

```powershell
$env:BP_BYTE_MATCH_HOOKS = "1"
work hooks install
work hooks status
```

On Bash, use `export BP_BYTE_MATCH_HOOKS=1` and
`python tools/work/githooks.py install`. Codex asks you to trust the project hooks
through `/hooks`. Check that the client starts with the opt-in variable in its environment.

| Check | When it runs |
| --- | --- |
| Exact-match regressions | Before a native `x360` push, compare affected objects with cached XDK build provenance for the candidate commit. Before a Workflow `main` push with record changes, compare the old and new published record sets. A verified loss blocks the push. Copies of an exact ARTIST extent count once. |
| Ledger handoff | Before the next native push and at the end of an active matching turn, report when the published ledger still trails the known pushed native tip. Follow the existing source push, `work match refresh --record`, ledger push sequence. The reminder uses local refs and does not make a network call. |
| Compaction recovery | The first recognized `work match` command opens a journal in `scratch/byte-match/`. Add the function, evidence, attempts, unresolved difference and next check as you work. Before compaction, the hook saves those notes, the last observed comparison excerpt and the native HEAD and changed files. The client receives the snapshot after compaction. |
| Source fidelity | After supported editor tool calls, point out suspicious constructs on changed native source lines. Use the original declarations and ARTIST evidence to review them. |

The native push check uses cached objects and reports any coverage it could not verify.
Run `work match compile <source> ...` after committing the candidate to give those objects
clean-build provenance. For shared header changes, include the affected sources. The hooks
never compile during an edit or push, and they leave the ledger and measurement caches alone.
If they flag a deliberate regression, a maintainer can authorize it by setting
`BP_ALLOW_MATCH_REGRESSION=1` for the affected push.

The source warnings cover Claude Code editor tools and Codex's patch tool. The journal and
comparison excerpts are local files under the ignored `scratch/` directory.

```sh
python -m pytest tools/hooks/test_hooks.py -q
```
