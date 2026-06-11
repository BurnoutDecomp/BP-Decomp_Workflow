# progress/ — the shared ledger

Agent-agnostic state for the decomp. This directory is the single source of truth
for *what has been done* and *what the work units are*, readable by any agent
(Claude Code, Codex, Antigravity, API loops). See [`../STRATEGY.md`](../STRATEGY.md)
for the plan and [`../AGENTS.md`](../AGENTS.md) for how to work against it.

## Artifacts

| File | Built by | What it is |
|------|----------|------------|
| `identity.json` | `tools/work/build_identity.py` | Cross-build identity table. One entry per X360 function, keyed by **normalized qualified name**, with its X360 address(es), DecFIGS `primary_file` (if any), and PS3 corroboration. The canonical map between builds. |
| `tu_index.json` | `tools/work/build_tu_index.py` | The work-unit list: every function grouped into a translation unit, `source` = `decfigs` (real file, ~43%) or `class` (fallback, ~57%). Each TU has a `status` (todo/in_progress/done/blocked). |
| `skeletons/` | `tools/work/gen_skeleton.py` | *Generated, git-ignored.* Per-TU reconstruction seeds (signatures + pseudocode + trap stubs). Regenerate on demand. |

## Current state (Phase 0)

- 27,549 named X360 functions identified.
- 11,357 (43%) have real DecFIGS file attribution; the rest are grouped by class.
- 4,319 translation units (1,655 file-backed, 2,664 class-backed).

## Regenerate

```powershell
python tools/work/build_identity.py     # -> identity.json
python tools/work/build_tu_index.py      # -> tu_index.json  (reads identity.json)
python tools/work/gen_skeleton.py "<TU key>"   # -> a skeleton on stdout / -o file
```

## Not yet built (Phase 1+)

The SQLite ledger and the `work` CLI (`next`/`show`/`submit`/`block`) that will
track per-function status and drive the reconstruction loop. Until then,
`tu_index.json` *is* the ledger — its `status` fields are edited as units progress.
