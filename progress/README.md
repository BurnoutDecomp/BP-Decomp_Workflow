# progress/ — the shared ledger

Agent-agnostic state for the decomp. This directory is the single source of truth
for *what has been done* and *what the work units are*, readable by any agent
(Claude Code, Codex, Antigravity, API loops). See [`../STRATEGY.md`](../STRATEGY.md)
for the plan and [`../AGENTS.md`](../AGENTS.md) for how to work against it.

## Artifacts

| File | Built by | What it is |
|------|----------|------------|
| `identity.json` | `tools/work/build_identity.py` | Cross-build identity table. One entry per X360 function, keyed by **normalized qualified name**, with its X360 address(es), DecFIGS `primary_file` (if any), and PS3 corroboration. The canonical map between builds. |
| `unidentified.json` | `tools/work/build_unidentified.py` | The counterpart to `identity.json`: every function IDA found in the X360 binary that has **no name**, so no DWARF file and no RTTI class can claim it. Addresses + instruction counts only — no code. Without it these fall out of the denominator entirely (neither done nor todo), and completion is measured against the part of the binary already named. |
| `tu_index.json` | `tools/work/build_tu_index.py` | The work-unit list: every function grouped into a translation unit, `source` = `decfigs` (real file, ~43%) or `class` (fallback, ~57%). Each TU has a `status` (todo/in_progress/done/blocked). |
| `skeletons/` | `tools/work/gen_skeleton.py` | *Generated, git-ignored.* Per-TU reconstruction seeds (signatures + pseudocode + trap stubs). Regenerate on demand. |
| `ledger.sqlite` | `tools/work/work.py seed` | **The ledger** — live store for per-TU/per-function status, owners, blockers, the TU dependency graph, and an event log. *Git-ignored* (local working store): rebuilt from the committed files below. |
| `status.json` | committed, auto-written | The mutable progress (which TUs/funcs are done, owners, blockers) — only non-default rows. Committed so a fresh clone resumes where the last commit left off. |
| `tu_deps.json` | committed, `work seed --deps` | The TU→TU dependency graph (21,548 edges) mirrored from the xref analysis, so leaf-first `next` works after a clone **without** `.ida-exports/` or IDA. |

## Current state (Phase 0)

- 30,082 functions in the X360 binary: **27,549 named/identified**, **2,533 still unnamed**
  (~6% of the executable's code — real bodies, median 39 instructions, 320 of them over 100).
- 11,357 (43%) have real DecFIGS file attribution; the rest are grouped by class.
- 4,412 translation units (1,655 file-backed, 2,740 class-backed, plus module/vendor).
  The unnamed functions belong to none of them: they live in one synthetic bucket that
  counts toward the *function* totals and never toward the TU totals.

## Regenerate

```powershell
python tools/work/build_identity.py     # -> identity.json
python tools/work/build_unidentified.py --apply  # -> unidentified.json (needs .ida-exports/)
python tools/work/build_tu_index.py      # -> tu_index.json  (reads identity.json)
python tools/work/gen_skeleton.py "<TU key>"   # -> a skeleton on stdout / -o file
```

## The `work` CLI (Phase 1 — live)

```powershell
work bootstrap            # fresh clone: submodules + rebuild ledger from committed state
work seed --deps          # build ledger.sqlite from the JSONs + the dep graph
work status               # counts by status, % done
work next -n 5            # next leaf-first ready TUs (fewest unresolved deps first)
work show <tu>            # concise overview: functions, signatures, dependency TUs
work show <tu> --full     # the full reconstruction dossier (pseudocode, locals,
                          #   DecFIGS dwarfdump hints, Feb-2007 original source,
                          #   callee sigs; --asm, -o file)
work start <tu>           # claim (todo -> in_progress)
work stubs <tu> [--list]  # trap-stub defs for the TU's not-yet-done callees; --list
                          #   shows what must be declared (the gate is compile-only,
                          #   so the emitted .cpp matters at the future link phase)
work submit <tu>          # compile gate (cl /c); on pass, emit a reviewer packet
work review <tu> --verdict pass|fail [--notes "…"]   # record the reviewer verdict
work block <tu> "reason"  # / work unblock <tu>
```

`work` (the `work.cmd` shim) is what the in-chat agent shells out to — it is not an
agent launcher. The ledger is its durable memory *between* sessions and tools.

## Phase 2 — the dossier (live)

`work show <tu> --full` ([`tools/work/dossier.py`](../tools/work/dossier.py))
assembles the full reconstruction brief for a TU: per-function clean signature,
decompiler locals, full pseudocode, callee signatures (with "already recovered ->
path" status), caller context, matching **DecFIGS dwarfdump declaration/type/local
variable hints** for DecFIGS-backed source paths, the **original Feb-2007 source
file** when the TU's `primary_file` exists in the leak (483 TUs touch it), and a
type-header pointer.
`--asm` adds disassembly; `-o <file>` writes it out.

## Phase 3 — verification (live)

`work submit` runs the per-TU **compile gate** (`cl /c`, no link;
[`tools/work/verify.py`](../tools/work/verify.py); flags/includes from the canonical
`tools/build/msvc_flags.txt` + `msvc_includes.txt`, MSVC located by
`tools/build/msvc_env.bat`). On a compile failure it prints the
MSVC diagnostics and returns the TU to `in_progress`. On pass it writes a fresh-eyes
**reviewer packet** to `reviews/<tu>.md` (produced code + dossier, including
DecFIGS dwarfdump hints when the TU has a matching source path). After a reviewer
sub-agent judges it, `work review <tu> --verdict pass|fail` records the verdict —
a pass marks the TU `done`. See [`../AGENTS.md`](../AGENTS.md) for the reviewer
protocol.

Prereq for non-trivial TUs: check out the EA submodules
(`git -C b5-decomp submodule update --init`) so EASTL/EABase headers resolve.

| File | Built by | What it is |
|------|----------|------------|
| `reviews/` | `work submit` | *Generated, git-ignored.* Per-TU reviewer packets. |
