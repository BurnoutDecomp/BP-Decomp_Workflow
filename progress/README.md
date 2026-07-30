# progress/ — the shared ledger

Agent-agnostic state for the decomp. This directory is the single source of truth
for *what has been done* and *what the work units are*, readable by any agent
(Claude Code, Codex, Antigravity, API loops). See [`../STRATEGY.md`](../STRATEGY.md)
for the plan and [`../AGENTS.md`](../AGENTS.md) for how to work against it.

## Artifacts

### Structure — the work units (derived from IDA; regenerate, don't hand-edit)

| File | Built by | What it is |
|------|----------|------------|
| `identity.json` | `tools/work/build_identity.py` | Cross-build identity table. One entry per X360 function, keyed by **normalized qualified name**, with its X360 address(es), DecFIGS `primary_file` (if any), and PS3 corroboration. The canonical map between builds. |
| `tu_index.json` | `tools/work/build_tu_index.py` | The work-unit list: every function grouped into a translation unit, with a `source` recording *how* it was grouped — `decfigs` (real original file), `class` (fallback by `Namespace::Class`), or `vendor`/`module` (reclassified out of the `<global>` bucket, see `references/*_classification.json`). |
| `tu_deps.json` | committed, `work seed --deps` | The TU→TU dependency graph, mirrored from the xref analysis **plus** DWARF-derived inheritance/by-value-containment edges, so leaf-first `next` works after a clone **without** `.ida-exports/` or IDA. |

### State — what has been done

| File | Built by | What it is |
|------|----------|------------|
| `status.json` | committed, auto-written | The mutable progress (which TUs/funcs are done, owners, blockers) — only non-default rows. Committed so a fresh clone resumes where the last commit left off. On `main` it is regenerated **by CI** on every `b5-decomp` commit; don't hand-edit it. |
| `ledger.sqlite` | `work seed` | **The ledger** — live store for per-TU/per-function status, owners, blockers, the TU dependency graph, the offline outbox, and an event log. *Git-ignored* (local working store): rebuilt from the committed files above. |
| `class_homes.json` | `work resolve-class-homes` | Maps each `class:`-keyed TU to its real committed home `.cpp`. `class:` TUs carry no source path, so this is what lets the dashboard attribute them; ambiguous classes are left unmapped rather than guessed. |
| `sweep/` | the verify sweep | `VERIFY_SWEEP_HANDOFF.md` (the operating guide) + `verify_sweep.json` (its per-TU queue/state). A correctness re-audit of already-`done` TUs; see [`../AGENTS.md`](../AGENTS.md). |

### Config and policy

| File | Built by | What it is |
|------|----------|------------|
| `verify.config.json` | committed | Compile-gate config: vcvars path, compiler, flags, include dirs. |
| `review.config.json` | committed | Reviewer **menu + policy** — providers/models/thinking ranges and selection guidance. It auto-runs nothing; the agent reads it and chooses. Also carries the `batch` and `faithfulness` blocks. |
| `goals.json` | committed, `work goal` | Milestone/subsystem scopes for `work next`, in two buckets (`milestones` from traces, `pattern_slices` from globs) plus the `active_goal`. Schema: [`../references/GOAL_SCOPING.md`](../references/GOAL_SCOPING.md). |
| `faithfulness_baseline.json` | `work faithfulness --baseline` | Grandfathered invention-smell fingerprints, so the hard faithfulness gate fails only on **new** ones. **Shrink it as debt is paid; never blind-regenerate it** — that hides fresh invention. |
| `memory_map_artist.yaml` | `tools/assets/memory_map/export_yaml.py` | The X360 ARTIST memory map extracted for the PC build. |

### Generated, git-ignored

| Path | Built by | What it is |
|------|----------|------------|
| `reviews/` | `work submit` | Per-TU fresh-eyes reviewer packets (produced code + dossier). |
| `skeletons/` | `tools/work/gen_skeleton.py` | Per-TU reconstruction seeds (signatures + pseudocode + trap stubs). |
| `stubs/` | `work stubs` | Emitted trap-stub definitions for a TU's not-yet-done callees. |

## Scale of the problem

These describe the *shape* of the work and only move when the IDA export is regenerated,
so they are safe to write down — unlike progress, which changes on every commit and is
**not** recorded in any doc. For that, run `work status`.

- 27,549 named X360 functions identified.
- 11,357 (~41%) have real DecFIGS file attribution; the rest are grouped by class.
- 4,412 translation units — 1,655 file-backed, 2,740 class-backed, 10 module, 7 vendor.

Recompute rather than trusting the above after a re-export:

```powershell
python -c "import json,collections; t=json.load(open('progress/tu_index.json')); i=json.load(open('progress/identity.json')); print(len(i),'funcs;',sum(1 for v in i.values() if v.get('primary_file')),'attributed;',len(t),'TUs',dict(collections.Counter(v['source'] for v in t.values())))"
```

## Regenerate

```powershell
python tools/work/build_identity.py            # -> identity.json
python tools/work/build_tu_index.py            # -> tu_index.json  (reads identity.json)
python tools/work/build_type_deps.py           # -> inheritance/containment edges for seed
python tools/work/gen_skeleton.py "<TU key>"   # -> a skeleton on stdout / -o file
```

The first two need `.ida-exports/`; the dependency and skeleton builders read the committed
JSONs. After regenerating, re-seed with `work seed --deps --reset`.

## The `work` CLI

```powershell
work bootstrap            # fresh clone: submodules + rebuild ledger from committed state
work seed --deps          # build ledger.sqlite from the JSONs + the dep graph (--reset to rebuild)
work status               # counts by status, % done, active goal, server-vs-local
work next -n 5            # next leaf-first ready TUs (fewest unresolved deps first); previews only
work goal [set|show|clear|import-trace] <name>   # scope `next` to a milestone/subsystem
work claim [-n N] [<tu>…] # claim the next N ready TUs, or specific ones by id
work show <tu>            # concise overview: functions, signatures, dependency TUs
work show <tu> --full     # the full reconstruction dossier (pseudocode, locals,
                          #   DecFIGS dwarfdump hints, Feb-2007 original source,
                          #   callee sigs; --asm, -o file)
work start <tu>           # older alias: claim one TU and print its dossier
work stubs <tu> [--list]  # trap-stub defs for the TU's not-yet-done callees; --list
                          #   shows what must be declared (the gate is compile-only,
                          #   so the emitted .cpp matters at the future link phase)
work postmortem <tu>      # self-review packet: full dossier WITH asm + a verify checklist
work submit <tu>          # compile gate (cl /c) -> parity -> faithfulness; on pass,
                          #   emit a reviewer packet
work parity <tu>          # standalone structural parity check (no status change)
work faithfulness         # standalone invented-code scan (--all / --files / --baseline)
work review <tu> --verdict pass|fail [--notes "…"]   # record the reviewer verdict
work block <tu> "reason"  # / work unblock <tu>
work auto --scan | --run  # NO-LLM drafter for purely mechanical (forwarder/thunk) TUs
work reset-tu <tu>        # delete produced files and return the TU/functions to todo
work reconcile-from-files [--apply] [--allow-demote]   # re-anchor the ledger to committed files
```

Optional server-mode commands (`sync`, `server-sync`, `server-update`, `server-reset`,
`worker-*`) are documented in [`../references/COORDINATION.md`](../references/COORDINATION.md).

`work` (the `work.cmd` shim) is what the in-chat agent shells out to — it is not an
agent launcher. The ledger is its durable memory *between* sessions and tools.

## Phase 2 — the dossier (live)

`work show <tu> --full` ([`tools/work/dossier.py`](../tools/work/dossier.py))
assembles the full reconstruction brief for a TU: per-function clean signature,
decompiler locals, full pseudocode, callee signatures (with "already recovered ->
path" status), caller context, matching **DecFIGS dwarfdump declaration/type/local
variable hints** for DecFIGS-backed source paths, the **original Feb-2007 source
file** when the TU's `primary_file` exists in the leak, and a type-header pointer.
Expect that last one rarely: the leak is one translation unit's include closure, so it
overlaps only a small fraction of TUs.
`--asm` adds disassembly; `-o <file>` writes it out.

## Phase 3 — verification (live)

`work submit` runs three gates in order, then hands off to the reviewer policy:

1. the per-TU **compile gate** (`cl /c`, no link;
   [`tools/work/verify.py`](../tools/work/verify.py), configured by
   [`verify.config.json`](verify.config.json)) — on failure it prints the MSVC
   diagnostics and returns the TU to `in_progress`;
2. **structural parity** ([`tools/work/parity.py`](../tools/work/parity.py)) — advisory
   GREEN/YELLOW/RED, never auto-fails;
3. the **faithfulness ratchet**
   ([`tools/work/faithfulness_lint.py`](../tools/work/faithfulness_lint.py)) — hard: a TU
   introducing a *new* invention smell goes back to `in_progress` and never reaches a
   reviewer packet.

On a clean pass it writes a fresh-eyes **reviewer packet** to `reviews/<tu>.md` (produced
code + dossier, including DecFIGS dwarfdump hints when the TU has a matching source path).
After a reviewer sub-agent judges it, `work review <tu> --verdict pass|fail` records the
verdict — a pass marks the TU `done`. Whether a given TU needs that pass at all is a policy
decision from [`review.config.json`](review.config.json); see
[`../AGENTS.md`](../AGENTS.md) for the reviewer protocol and
[`../STRATEGY.md`](../STRATEGY.md) for why each gate exists.

Prereq for non-trivial TUs: check out the EA submodules
(`git -C b5-decomp submodule update --init`) so EASTL/EABase headers resolve.
