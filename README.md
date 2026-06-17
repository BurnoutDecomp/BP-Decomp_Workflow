# Burnout Paradise Decompilation Workflow

This repository is the orchestration workspace for reverse-engineering Burnout 5 /
Burnout Paradise. It is not the decompilation source tree itself. It holds the
analysis databases, reference material, work ledger, and automation that let agents
reconstruct the Xbox 360 build as compilable PC C++.

Recovered C++ lives in the [`b5-decomp`](https://github.com/Adriwin06/b5-decomp) submodule. This repo answers:

- which functions exist in the X360 target build;
- which translation unit owns each function;
- what reference evidence is available for each unit;
- which units are todo, in progress, compiled, reviewed, blocked, or done;
- how to claim, reconstruct, verify, review, and coordinate work.

## Read First

For reconstruction work, read these in order:

1. [`AGENTS.md`](AGENTS.md) - the operating guide for every agent and maintainer.
2. [`STRATEGY.md`](STRATEGY.md) - the technical plan and rules of evidence.
3. [`progress/README.md`](progress/README.md) - the ledger and `work` CLI reference.

`CLAUDE.md` exists only as a redirect for Claude Code. The canonical instructions are
shared in `AGENTS.md` so all agents follow the same process.

## Why Several Builds Are Used

No single binary contains enough information. The workflow triangulates:

| Build or artifact | Role |
| --- | --- |
| `BURNOUT_X360_ARTIST.XEX` | Target/spine. Its symbols, pseudocode, asm, and xrefs define what is reconstructed. |
| `Burnout_External_PS3.ELF` | Symbol-rich PS3 corroboration for names and behavior. |
| `DecFIGS_Burnout_Internal_PS3.ELF` | DWARF source/file attribution plus declaration, type, enum, global, signature, and local-variable hints. |
| `BurnoutPR.exe` and `TUB_Burnout_PC_External.exe` | Stripped PC references, consulted selectively for platform-specific code paths. |
| `rwcore.lib` / `rwcore.pdb` / `rwcore_master.obj` | RenderWare core type and layout evidence. |
| `references/Feb-2007/` | A real source-code slice used as the highest-fidelity template where it overlaps. |
| `references/Wiki/` | burnout.wiki-derived type tables. Use names/types/semantics, never offsets. |

The canonical identity is a normalized qualified function name, not an address.
Addresses are build-local and must not be treated as stable across binaries.

## Repository Layout

| Path | What it is |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | Tool-agnostic operating guide: resume behavior, work loop, server coordination, reconstruction rules, review policy, and "don't" rules. |
| [`STRATEGY.md`](STRATEGY.md) | Design document for the workflow: target, build roles, identity model, TU model, stubs, verification, goals, and phase status. |
| [`IDA Files/`](IDA%20Files/) | IDA Pro databases and RenderWare library/PDB inputs. Some large `.i64` files are intentionally git-ignored and must be supplied locally. |
| [`.ida-exports/`](.ida-exports/) | Generated per-function JSON exports from IDA: names, prototypes, locals, pseudocode, asm, callers, and callees. Git-ignored. |
| [`references/`](references/) | Non-disassembly evidence: Feb-2007 source slice, DecFIGS DWARF artifacts, BPR module map, wiki index, and naming conventions. |
| [`tools/`](tools/) | IDAPython exporters, post-processors, RenderWare header generation, and the `tools/work/` ledger/reconstruction helpers. |
| [`progress/`](progress/) | Shared ledger inputs and outputs: identity, TU index, dependencies, status mirror, goals, verification/review configs, and generated review packets. |
| [`b5-decomp/`](https://github.com/Adriwin06/b5-decomp) | Submodule containing recovered C++, vendor libraries, RenderWare headers, and CMake project files. |
| [`build/`](build/) | Local build tree for `b5-decomp`; not source of truth. |
| [`.env.example`](.env.example) | Optional work-server configuration template. Copy to `.env` only if a maintainer gives you a worker id. |

Generated review packets under `progress/reviews/` and vendor Markdown under
`b5-decomp/vendor/` are artifacts/upstream documentation, not primary workflow docs.

## Prerequisites

Required for normal ledger work:

- Python 3
- Git
- PowerShell on Windows
- initialized submodules under `b5-decomp/vendor/`

Required for the compile gate:

- Visual Studio/MSVC
- `progress/verify.config.json` pointing at a real `vcvars64.bat`

If `vcvars` is missing, `work submit` reports a skipped compile gate and continues;
that is useful for bookkeeping but does not catch compiler errors.

Required only for regenerating analysis exports or generating new skeletons from IDA:

- IDA Pro with Hex-Rays (`idat.exe`)
- The relevant `.i64` databases under `IDA Files/`
- Generated `.ida-exports/` for the target databases. If they are missing or stale,
  run the IDA export script before doing reconstruction work:

  ```powershell
  tools/export_db.ps1
  ```

Large or licensed local inputs are intentionally not all committed. At minimum, local
work that regenerates exports may need the git-ignored PS3/PC IDBs and the Feb-2007
source tree documented in the reference READMEs.

## Fresh Clone / Resume

From the repo root:

```powershell
work bootstrap
```

`bootstrap` initializes submodules and rebuilds `progress/ledger.sqlite` from the
committed state: `progress/status.json`, `progress/tu_deps.json`,
`progress/identity.json`, and `progress/tu_index.json`.

That is enough to resume the queue and status ledger. It does not regenerate the
git-ignored IDA export cache. If `.ida-exports/` is absent or no longer matches the
local IDA databases, generate it before reconstructing TUs:

```powershell
tools/export_db.ps1                          # all configured IDA databases
tools/export_db.ps1 -DbName "BURNOUT_X360_ARTIST.XEX"
```

After that, the short instruction "continue" means:

```powershell
work claim
work show <claimed-tu> --full
```

Then reconstruct the TU into `b5-decomp/src/<mirrored path>`, compile/submit it, and
record the review verdict.

## Core Work Loop

```powershell
work status                         # ledger counts and active goal
work next -n 5                      # preview ready work; reserves nothing
work claim [-n N]                   # claim next ready TU(s)
work claim <tu> [<tu> ...]          # claim specific TU(s)
work show <tu> --full [--asm]       # reconstruction dossier
work stubs <tu> --list              # unresolved callees and owning headers
work submit <tu> [--files path ...] # compile gate, parity, reviewer packet
work parity <tu>                    # standalone deterministic parity check
work review <tu> --verdict pass     # mark done after review/self-check
work review <tu> --verdict fail     # return to in_progress with notes
work block <tu> "reason"            # stop it being reclaimed
```

The compile gate is per translation unit (`cl /c`, no link). The target is semantic
parity with the X360 build expressed as source-like PC C++, not byte matching.

## Tool Inventory

The authoritative inventory of repo tools is [`tools/README.md`](tools/README.md).
At a glance:

| Tool area | Entry points |
| --- | --- |
| Day-to-day ledger work | `work bootstrap`, `work status`, `work next`, `work claim`, `work show`, `work submit`, `work parity`, `work review`, `work block` |
| Goal scoping and traces | `work goal ...`, `work goal import-trace`, `tools/work/trace_import.py` |
| IDA export pipeline | `tools/export_db.ps1`, `tools/ida_export_all.py`, `tools/ida_export_lineinfo.py`, `tools/ida_decompile.py` |
| Derived ledger builders | `tools/work/build_identity.py`, `tools/work/build_tu_index.py`, `tools/work/build_type_deps.py`, `work seed --deps` |
| Reconstruction helpers | `tools/work/dossier.py`, `tools/work/gen_stubs.py`, `tools/work/gen_skeleton.py`, `tools/work/auto_draft.py` |
| Verification/review | `tools/work/verify.py`, `tools/work/parity.py`, `progress/verify.config.json`, `progress/review.config.json` |
| Reference and maintenance | `tools/work/wiki_index.py`, `tools/work/check_vendor_lib.py`, `tools/work/reconcile_from_files.py`, `tools/work/find_local_redefs.py`, `tools/gen_rwcore_headers.py` |
| Optional server coordination | `work sync`, `work server-sync`, `work server-reconcile-events`, `work server-reset`, `work worker-add`, `work worker-list`, `work worker-revoke` |

## Goals And Execution Traces

By default `work next` ranks the whole program leaf-first. A goal scopes the queue to a
membership set, either hand-authored globs or an execution-derived Xenia trace:

```powershell
work goal
work goal show boot-trace
work goal set boot-trace
work goal clear
work goal import-trace <name> [--trace-dir .trace/funcdata]
```

Goals live in [`progress/goals.json`](progress/goals.json). The full schema and Xenia
trace procedure are documented in [`references/GOAL_SCOPING.md`](references/GOAL_SCOPING.md).

## Optional Coordination Server

The default mode is local: the ledger and git are the only state. If a maintainer gives
you a server URL and worker id, copy `.env.example` to `.env` and set:

```text
WORK_SERVER=https://...
WORK_AGENT=<server-issued-worker-id>
WORK_LEASE_SECONDS=7200
```

With a server configured, `work claim` is atomic across agents and live claims live on
the server. Durable states tied to committed code (`done`, `blocked`) still sync through
`progress/status.json`.

### Resilience to an unreachable server

A configured server that is *down* does not break the work loop — the CLI degrades
gracefully and self-heals on reconnect, so agents never have to manage outages.

- **Connection failure vs. rejection.** A server that *can't be reached* is treated as a
  recoverable outage; a server that *answers with an error* (HTTP) is a real decision.
  Only a genuine **auth rejection** (missing/invalid `WORK_AGENT`) still stops a command —
  that's a config error, not an outage.
- **Degrade locally.** While the server is unreachable, reads (`work next`, `work status`)
  fall back to the local leaf-first ranking and counts; writes (`work claim`,
  `work submit` → compiled, `work review`, `work block`/`unblock`) apply to the local
  ledger and are recorded in an **offline outbox** (a `pending_op` table in the git-ignored
  ledger cache).
- **Self-heal on reconnect.** The outbox **replays automatically** before the next
  server-mode command, or on demand with `work sync`. `work status` shows the queued-op
  count and whether it is reporting the server or the local ledger.
- **Nothing finished is ever lost.** `done`/`blocked` are durable in git
  (`progress/status.json`), so even after a long outage they reconcile into the server via
  `work server-sync`. Only the *ephemeral* claim layer can drift offline (a lease may lapse
  on the server, or an offline claim may collide with another agent). Such conflicts are
  **reported** during sync — never silently dropped, never overwriting local state.

```powershell
work sync                                 # flush queued offline ops (auto-runs otherwise)
```

Maintainer commands:

```powershell
work server-sync [--branch <branch>]      # preserve live claims/events
work server-reconcile-events --actor JeBobs [--apply]
                                           # reconstruct missing review_pass events from b5-decomp commits
work server-reset [--to <ref>]            # local reset + server reseed
work worker-add "Name" [--admin]
work worker-list
work worker-revoke <worker-id>
```

### Automated status reconcile

Because every claim/submit/review is mirrored to the server, the committed
`progress/status.json` is a *derived* view of the server's durable state, not an
independent source. A GitHub Action keeps git in step with the server automatically, so
**the people doing the decompilation only ever push to `b5-decomp` — they need no write
access to this workflow repo and never hand-edit `status.json`.**

It runs **once per b5-decomp commit**. The notifier workflow
[`b5-decomp/.github/workflows/notify-workflow.yml`](b5-decomp/.github/workflows/notify-workflow.yml)
fires on every push to b5-decomp's `dev` branch and sends a `repository_dispatch` (carrying
the new commit SHA) to [`.github/workflows/reconcile-status.yml`](.github/workflows/reconcile-status.yml)
in this repo, which then:

1. regenerates `progress/status.json` from the server's `GET /export/status`. The server
   is the **only full authority**: a files-only reconcile can recover `done` (its file
   exists) but not `blocked` (a blocked TU leaves no file), so the durable set is pulled
   straight from the server;
2. advances the `b5-decomp` submodule pointer to the commit that triggered the run;
3. cross-checks the server's `done` set against the committed b5-decomp files with
   `reconcile_from_files.py` (non-blocking — it only emits a warning if the server marks a
   TU `done` whose committed file is missing or still a trap-stub/partial);
4. commits and pushes the regenerated `status.json` + bumped pointer under a bot identity.

**Setup (one-time):** the notifier needs a `WORKFLOW_DISPATCH_TOKEN` secret on the
b5-decomp repo — a token that can send `repository_dispatch` to this repo. Without it the
notifier no-ops (so nothing breaks), but the automatic reconcile won't fire. The reconcile
Action also has a manual `workflow_dispatch` trigger (optionally pin a specific
`b5_sha`) for backfills.

You can refresh the committed mirror manually too:

```powershell
python tools/work/fetch_server_status.py            # rewrite status.json from the server
python tools/work/fetch_server_status.py --check    # report drift, write nothing (exit 1 if stale)
```

If commits reached `b5-decomp` without the workflow reporting its normal review event to
the server, an admin can backfill only those missing live events from the committed git
history:

```powershell
work server-reconcile-events --actor JeBobs          # dry run
work server-reconcile-events --actor JeBobs --apply  # append missing reconstructed events
```

The backfill adds `review_pass` events marked as reconstructed from `b5-decomp`; it skips
real workflow events that are already present, so it should not duplicate normal claims,
compiled events, or reviews.

Two operational notes:

- **The server is now a durable store for `blocked`.** `done` is always recoverable from
  the committed files, but a blocked TU's state and reason live only on the server — so
  back up its DB (`/var/lib/bp-work-server`). The bot-committed `status.json` doubles as a
  backup of the `done`/`blocked` set.
- **The Action pushes to the default branch.** If it is protected against direct pushes,
  point the Action at a side branch with an auto-PR instead of allowing the bot to push.

## Automated Helpers

These helpers are optional. They do not replace manual reconstruction:

```powershell
work auto --scan              # find fully mechanical TUs
work auto --run [-n N]        # draft/gate safe forwarder/thunk-only TUs
python tools/work/reconcile_from_files.py [--apply]
python tools/work/find_local_redefs.py [--summary]
python tools/work/wiki_index.py [--lookup <Type>]
python tools/work/check_vendor_lib.py <tu>
```

Vendor SDK TUs must be checked with `check_vendor_lib.py` before decompiling. If the
script prints `PRESENT`, block the TU as vendor code already covered by a PC library or
open-source vendor source. If it prints `MISSING`, reconstruct it normally.

## Regeneration Pipeline

Most agents do not need to regenerate exports if `.ida-exports/` is already present
and current. On a fresh machine without that cache, or whenever IDA analysis changes,
run the IDA database export first:

```powershell
tools/export_db.ps1                          # generate .ida-exports/ from IDA Files/*.i64
tools/export_db.ps1 -DbName "BURNOUT_X360_ARTIST.XEX"
```

Then rebuild derived DecFIGS/ledger artifacts as needed:

```powershell
python tools/build_source_tree.py
python tools/work/build_identity.py
python tools/work/build_tu_index.py
work seed --deps --reset
```

Use `tools/README.md` for the full script inventory and command details.
