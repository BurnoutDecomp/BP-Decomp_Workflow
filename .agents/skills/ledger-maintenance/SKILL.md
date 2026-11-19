---
name: ledger-maintenance
description: >-
  User-invoked only: maintaining the ledger and the coordination server. Reconciling
  progress/status.json with the committed b5-decomp files (work reconcile-from-files: dry
  run, --apply, --allow-demote), rebuilding the local cache (work seed [--deps] [--reset],
  work bootstrap), class homes (work resolve-class-homes [--apply]), manual status (work set),
  re-baselining a ratchet (work faithfulness --baseline only after deliberately paying debt
  down; tools/work/fold_partfiles.py check [--baseline]), and server operations (work sync,
  server-sync, server-update, server-reset, worker-add, worker-list, worker-revoke). Hard
  rules: never reset or rebuild the server database without the maintainer's explicit OK in
  that session; reviewed in status.json is a default, not a verdict; a committed file with
  author TODOs is not done. Load only when the user explicitly asks to reconcile the ledger,
  re-baseline a ratchet or run a server operation.
disable-model-invocation: true
---

Stop unless the user explicitly asked, in their own words, for ledger maintenance, a ratchet re-baseline or a server operation. A routine fresh-clone `work bootstrap` belongs to `reconstruct-tu`.

# Ledger maintenance

What the ledger is made of, how each maintenance command changes it, and which commands
destroy something no command brings back.

Not for: the work loop (`reconstruct-tu`); folding partfiles (`fold-partfiles`); goals
(`goal-scoping`); committing (`land-change`).

## The stores

| Store | What it is | Written by |
|---|---|---|
| committed files in b5-decomp | ground truth for "done": a complete reconstructed file | contributors |
| `progress/status.json` | the durable mirror: non-default TU and function rows | `work` commands locally; CI exports it from the server and commits it |
| `progress/ledger.sqlite` | git-ignored local cache: status, dependency graph, event log, offline outbox; re-imports `status.json` whenever that file changes under it | `work` |
| the server database | live claims, leases, owners, transient statuses, the event log | the server; never committed and not recoverable from git |
| `progress/identity.json`, `progress/tu_index.json` | structure: every function, grouped into TUs | `tools/work/build_identity.py`, `tools/work/build_tu_index.py` |
| `progress/tu_deps.json` | the TU dependency graph mirror | `work seed --deps` |
| `progress/class_homes.json` | `class:` TU to home file, for attribution | `work resolve-class-homes --apply`; CI on every b5 push |

## Hard rules

1. **Never reset or rebuild the server database**, or run anything that drops its event log,
   without the maintainer's explicit OK in this session naming the destructive effect. A
   rebuild once destroyed the server's real event history and overwrote its only backup;
   there is no event-reconstruction tool, and git holds only a lossy projection of the events.
   A missing `WORK_SERVER` in your `.env` means your commands run locally, not that no server exists.
2. **`reviewed` in `progress/status.json` is the default, not a verdict.** It says nothing
   about whether a body was written. Ask the tree: `python tools/re/hasbody.py <Class::Method> [--status]`
   (a trap stub counts as a definition: open the file).
3. **A committed file that still carries author TODOs is not done.** Never mark a partial
   done; "done" means a complete reconstructed file committed in b5-decomp, not necessarily
   LLM-reviewed.
4. **Dry run first.** Read the change list before any `--apply`.
5. **Never commit `progress/status.json` or the submodule pointer**: CI owns them. Leave the
   local churn uncommitted (`land-change`); a large `status.json` diff after a `work` command
   is a sync artifact, not your edit.
6. **Update the ledger, not your memory**: progress that is not in `progress/` did not
   happen for the next agent, and work is never completed off-ledger.

## Procedures

### Reconcile status with the committed files

`work reconcile-from-files` (the same code as `tools/work/reconcile_from_files.py`):

1. It reads the b5-decomp commit the parent's index records (`git rev-parse :b5-decomp`),
   not your working tree and not b5-decomp's checked-out HEAD. Land the b5 commit and record
   the pointer locally first, or you reconcile older code.
2. With no flags it is a dry run: before/after TU counts and every change with its evidence
   file. Nothing is written.
3. The default is promote-only: it adds and promotes, never demotes, except on explicit
   contradictory evidence (a durable partial-count note, an explicit reconstruction trap, an
   incomplete marker in the resolved file).
4. `--allow-demote` lets file evidence demote or remove existing rows; run it as a dry run
   to see what the files contradict.
5. `--apply` writes `progress/status.json` and runs a verification pass; the local cache
   re-imports the file on the next `work` command.

AGENTS.md's `--no-demote --apply` is now the default behaviour (`--no-demote` survives as a
hidden alias). How reconcile decides, and where it is blind: [references/reconcile.md](references/reconcile.md).
Its incomplete markers are narrow on purpose, so it misses most author TODOs, and an engine
stub (`return null;`) is a `work faithfulness` finding, not a reconcile one: read the file
before believing a `done`.

### Rebuild the local cache

- `work seed`: upserts TUs and functions from `identity.json` and `tu_index.json` (existing
  status kept), restores status from `status.json`, loads `tu_deps.json`, then rewrites
  `status.json` from the ledger.
- `--deps`: with `.ida-exports/` present (a local input) it rebuilds the dependency graph
  from the xrefs plus the structural type edges and rewrites `progress/tu_deps.json`;
  without the exports it loads the committed mirror. If the ledger is missing, build it
  once with `work seed --deps`.
- `--reset`: deletes every TU, function, dependency and event row first. The local event log
  and anything `status.json` does not mirror (in server mode: transient statuses, owners) are lost.
- `work bootstrap`: inits missing submodules (never touches a populated b5-decomp), checks
  `identity.json` and `tu_index.json`, may launch IDA to build
  `references/DecFIGS/decfigs_inlining.json` (a local input) when it is missing, runs
  `work seed` (with `--deps` when the exports exist, so it rewrites `tu_deps.json`), then
  refreshes the wiki type index.

### Class homes

`work resolve-class-homes` prints the `class:` TU to home-file map (dry run); `--apply`
writes `progress/class_homes.json` and never any status. It is conservative: an ambiguous
class stays unmapped, never guessed. CI applies it on every b5 push; apply it locally only
before a `server-update`, or dry-run it to see the effect of a file move.

### Manual status

`work set <tu> --status S [--note T]`, where S is `todo`, `in_progress`, `compiled`, `done`,
`blocked` or `external`. It writes the local ledger and rewrites `status.json`, makes no
server call, leaves function rows alone (except on the external transitions) and records no
evidence. A hand-set `done` is exactly the phantom-done shape: prefer `work submit`,
`work review`, `work block` or `work external`, and always give a note.

### Ratchets

- **Faithfulness** (`progress/faithfulness_baseline.json`): re-baseline only after you
  deliberately paid debt down. `work faithfulness` must pass first (no NEW finding); then
  `work faithfulness --baseline` snapshots the smaller set. A fingerprint is category, path
  and snippet, so a move or rename re-keys entries as NEW: re-baseline over those only after
  checking each is the same smell. Never blind-regenerate: that hides fresh invention.
- **Partfiles** (`progress/partfile_baseline.json`): `python tools/work/fold_partfiles.py check`
  fails when the partfile population or the off-convention count grew. `check --baseline`
  re-pins it, after a fold brought it down or deliberately with the reason in the commit.
  Folding itself: `fold-partfiles`.

### Coordination server

Only on a server you run or were invited to. Configuration lives in `.env`, copied from
`.env.example` (`WORK_SERVER`, `WORK_AGENT`, `WORK_LEASE_SECONDS`); the full reference is
`references/COORDINATION.md`, a local input.

| Command | Effect | Safety |
|---|---|---|
| `work sync` | flushes the offline outbox (also runs before every server command) | safe |
| `work server-sync [--branch B]` | the server re-pulls its workflow checkout and re-imports the committed artifacts with reset=false (an admin endpoint) | safe: claims, workers and events kept |
| `work server-update [--reconcile] [--no-push] [--branch B]` | `resolve-class-homes --apply` (plus a promote-only `reconcile-from-files --apply` with `--reconcile`), commits `progress/class_homes.json` (and `status.json`) in the parent, pushes unless `--no-push`, then `server-sync` | commits and pushes the parent (passing the pre-commit hook's `BP_ALLOW_BOT_FILES` override itself): the maintainer's command |
| `work server-reset [--to REF]` | with `--to`: `git reset --hard REF` of the workflow repo plus a submodule update; always deletes `progress/ledger.sqlite`; with a server, reseeds it with reset=true, discarding live claims and the event log | destructive: rule 1, then `work bootstrap` |
| `work worker-add <name> [--admin]` | mints a worker id (needs an admin `WORK_AGENT`) | hand the id over privately |
| `work worker-list`, `work worker-revoke <id>` | lists ids, usernames and last-seen; disables one id | the list is secret |

What CI does on every b5 push, and the read-only drift check: [references/server.md](references/server.md).

## Never

- Never reset, reseed or rebuild the server database, or run `work server-reset`, without
  the maintainer's explicit OK in this session.
- Never `--apply` a reconcile you have not read as a dry run.
- Never read `reviewed` as evidence that a body exists.
- Never mark a file with author TODOs done, or any partial work done.
- Never blind-regenerate the faithfulness or the partfile baseline.
- Never commit `status.json` or the submodule pointer; `server-update` commits the parent,
  so it is the maintainer's command.
- Never put a worker id anywhere but your own git-ignored `.env`: not in a commit, an
  issue, a log or a report.
- Never use `work set` to make the ledger say what the tree does not.

## Tools

- `tools/work/work.py` (`work`); `work status` gives the counts.
- `tools/work/reconcile_from_files.py`, `tools/work/resolve_class_homes.py`: what the two
  `work` subcommands run.
- `tools/work/faithfulness_lint.py` (`work faithfulness [--files F ...] [--all] [--baseline]`).
- `tools/work/fold_partfiles.py check [--baseline]`.
- `python tools/re/hasbody.py <Class::Method> [--status]`.
- `python tools/work/fetch_server_status.py --check`: compares `status.json` with the
  server's export without writing.

## Read next

- [references/reconcile.md](references/reconcile.md): reconcile's decision table, its blind
  spots, and the drift history behind the rules.
- [references/server.md](references/server.md): the two state stores, offline behaviour,
  what CI runs, worker administration.
- Skills: `reconstruct-tu`, `fold-partfiles`, `land-change`, `goal-scoping`.
