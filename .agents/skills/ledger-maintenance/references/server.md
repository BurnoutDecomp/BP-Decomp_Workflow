# Coordination server: stores, CI and administration

Depth for [`../SKILL.md`](../SKILL.md). The maintainer's full reference is
`references/COORDINATION.md` (a local input, not part of a clone); the behaviour below is
read from `tools/work/work.py` and `.github/workflows/reconcile-status.yml`.

## Configuration

`work` loads the repo-root `.env` (copied from `.env.example`, git-ignored); a real
environment variable overrides it.

- `WORK_SERVER`: the server URL. Unset or blank means local mode. `.env.example` ships with
  it set, so comment it out in your copy to work locally.
- `WORK_AGENT`: your worker id, sent as the `X-Work-Token` header; the server links it to a
  username and records that username as the owner. Offline it is only the local owner label.
- `WORK_LEASE_SECONDS`: how long a claim lasts before the server returns it to `todo`.

## Two stores with different lifetimes

- **Durable, in git:** `progress/status.json`, the `done`, `blocked` and `external` states
  tied to committed code. With a server configured the CLI writes only these durable states
  to it (no owners, no `in_progress` or `compiled`); locally it keeps the full mirror.
- **Live, on the server:** claims, leases, owners, transient statuses and the event log.
  Ephemeral by design, never committed, and the event log cannot be rebuilt from git.
- A files-only reconcile can recover `done` (its file exists) but never `blocked` (a blocked
  TU leaves no file): the server is the full authority for the durable set.

## Unreachable server

Commands fall back to the local ledger and queue the change in an offline outbox; the queue
replays before the next server-mode command or on `work sync`. Only the claim layer can
drift (a lease may lapse, an offline claim may collide); conflicts are reported on sync. A
rejected worker id stops immediately.

## What CI does on every b5-decomp push

`.github/workflows/reconcile-status.yml`, also hourly as a repair:

1. checks out the exact b5-decomp commit;
2. `python tools/work/resolve_class_homes.py --apply`;
3. the evidence audits (`tools/re/funcaudit.py`, `tools/re/stubaudit.py`) from the packed
   feature cache;
4. `tools/work/source_status.py --publish`: source evidence to the server, recorded as
   `recovered`, never as a review verdict;
5. `tools/work/fetch_server_status.py`: exports the server's durable ledger as
   `progress/status.json`;
6. `tools/work/publish_snapshot.py publish`: commits `status.json`, `class_homes.json`,
   `funcaudit.json`, `stubs.json` and `source_status.json` with the new pointer, refusing a
   superseded snapshot;
7. a metadata-only, non-reset server sync for the dashboard.

So nobody commits those files by hand. `python tools/work/fetch_server_status.py --check`
compares the committed `status.json` with the server's export and writes nothing (exit 1 on
drift).

## Administration

- The first admin id is minted on the server host with the server's own command line;
  after that an admin `WORK_AGENT` can run `work worker-add <name> [--admin]`,
  `work worker-list` and `work worker-revoke <id>`. Admin is a role on a worker id, not a
  separate token.
- A worker id is a credential: give it to its owner privately; never commit, paste or log it.
- Per-contributor credit on the dashboard is derived from git (surviving-line authorship of
  each TU's files); `class:` TUs are attributed through `progress/class_homes.json`. There
  is no event-reconstruction tool: one that fabricated review events from git history was
  removed.

## The destructive path

`work server-reset [--to REF]` is the post-server equivalent of "git reset and delete the
database": with `--to` it hard-resets the workflow repository and updates the b5-decomp
submodule to the recorded commit; it always deletes the local `ledger.sqlite` (and its WAL
files); with a server configured it reseeds the server with reset=true, which discards the
live claims and the event log. Without a server it does only the local half. Afterwards
rebuild the local ledger with `work bootstrap`. Never run it without the maintainer's
explicit OK in the same session.
