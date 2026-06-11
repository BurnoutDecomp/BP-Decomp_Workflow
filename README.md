# Burnout Paradise Decompilation workflow

The orchestration workspace for reverse-engineering and decompiling Burnout 5 /
Burnout Paradise. This repository is **not** the decomp itself — it is the
scaffolding around it: the disassembly databases, the reference material recovered
from various builds, and the tooling that turns those databases into structured
data the decomp can consume. The actual recovered C++ lives in the
[`b5-decomp`](b5-decomp/) submodule.

## Why several builds?

No single binary gives everything. The decomp triangulates between builds, each
contributing a different kind of ground truth:

- **Symbols & function names** come from the binaries with the richest symbol
  tables (PS3 ELFs).
- **Original source file/line/inlining attribution** comes from the DecFIGS PS3
  build, which still carries DWARF line info — see [`references/DecFIGS`](references/DecFIGS/).
- **A genuine slice of original source** (one translation unit) comes from the
  Feb-2007 PS3 leak — see [`references/Feb-2007`](references/Feb-2007/).
- **High-fidelity Renderware type layouts** come from the shipped `rwcore` PDB.
- **Module/offset maps** for the PC build come from [`references/BPR`](references/BPR/).

## Layout

| Path | What it is |
|------|------------|
| [`IDA Files/`](IDA%20Files/) | The IDA Pro databases (`.i64`) for every analyzed build, plus the `rwcore.lib`/`.pdb` used for Renderware types. The primary disassembly source. |
| [`.ida-exports/`](.ida-exports/) | Generated: one JSON per function (pseudocode, prototype, locals, asm, xrefs), exported from the IDBs by the tools below. The machine-readable form of the disassembly. |
| [`references/`](references/) | Recovered ground-truth material that is *not* a disassembly: leaked source, DWARF-derived source trees, module offset maps. See its README. |
| [`tools/`](tools/) | IDAPython exporters and post-processors that produce `.ida-exports/` and the DecFIGS artifacts, plus the [`work`](tools/work/) ledger CLI. |
| [`progress/`](progress/) | The agent-agnostic ledger: the cross-build identity table, the translation-unit work list, and the status ledger that drives the reconstruction loop. See its README. |
| [`b5-decomp/`](b5-decomp/) | Submodule: the actual decompilation project (recovered C++, vendored EA libraries, Renderware type headers, CMake build). |
| [`build/`](build/) | Local CMake build tree for `b5-decomp` (not the source of truth). |

## Agentic workflow

This repo is set up so AI agents (Claude Code, Codex, …) can drive the decomp from
a single chat. The plan, conventions, and operating guide live in three files —
**read them in this order**:

1. [`AGENTS.md`](AGENTS.md) — operating guide every agent reads first (tool-agnostic).
2. [`STRATEGY.md`](STRATEGY.md) — the plan: build roles, the name-join identity
   model, translation-unit work units, the stub scaffold, verification, phases.
3. [`progress/`](progress/) — the live ledger, driven by the `work` CLI.

### Fresh clone — one command, then "continue"

```powershell
work bootstrap   # init submodules + rebuild the ledger from committed state
```

`bootstrap` makes a freshly-cloned repo workable and **resumes exactly where the
last commit left off** — progress (which TUs are done) and the leaf-first
dependency graph are committed as `progress/status.json` + `progress/tu_deps.json`,
so the ledger rebuilds with no IDA and no `.ida-exports/` needed. After it, an agent
can just be told **"continue"**: it reads [`AGENTS.md`](AGENTS.md), runs `work next`,
and picks up the next translation unit. (Reconstructing *new* functions still needs
`.ida-exports/`, which are regenerated from the IDBs with `tools/export_db.ps1`.)

   ```powershell
   work status            # where things stand
   work next -n 5         # next leaf-first ready translation units
   work show <tu>         # concise overview of one unit
   work show <tu> --full  # the full reconstruction dossier for it
   work start <tu>        # claim it, reconstruct into b5-decomp, then:
   work submit <tu>       # mark it done
   ```

## Typical workflow

1. Analyze a build in IDA Pro → `IDA Files/<build>.i64`.
2. Run the exporters in [`tools/`](tools/) to dump per-function JSON into
   `.ida-exports/` and the DWARF line-attribution artifacts into
   `references/DecFIGS/`.
3. Cross-reference those exports against the leaked source
   ([`references/Feb-2007`](references/Feb-2007/)) and the recovered source-tree
   skeleton (DecFIGS) to rebuild each translation unit.
4. Commit the recovered, compiling C++ to the [`b5-decomp`](b5-decomp/) submodule.
