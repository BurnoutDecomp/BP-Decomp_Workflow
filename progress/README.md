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
| `ledger.sqlite` | `tools/work/work.py seed` | **The ledger** — live store for per-TU/per-function status, owners, blockers, the TU dependency graph, and an event log. *Git-ignored* (local working store): it persists on disk between sessions and is fully rebuildable from the committed `identity.json` + `tu_index.json` via `work seed --deps`. |

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

## The `work` CLI (Phase 1 — live)

```powershell
work seed --deps          # build ledger.sqlite from the JSONs + the dep graph
work status               # counts by status, % done
work next -n 5            # next leaf-first ready TUs (fewest unresolved deps first)
work show <tu>            # TU dossier: functions, signatures, dependency TUs
work start <tu>           # claim (todo -> in_progress)
work submit <tu>          # mark reconstructed (compile/review gates: Phase 3)
work block <tu> "reason"  # / work unblock <tu>
```

`work` (the `work.cmd` shim) is what the in-chat agent shells out to — it is not an
agent launcher. The ledger is its durable memory *between* sessions and tools.

## Not yet built (Phase 2+)

- **Phase 2** — richer `work show`: full pseudocode/asm, Feb-2007 source overlay,
  recovered sibling/callee signatures.
- **Phase 3** — `work submit` runs the per-TU compile gate + reviewer sub-agent.
