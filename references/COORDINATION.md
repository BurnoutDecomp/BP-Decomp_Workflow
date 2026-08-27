# Coordination Server & Maintainer Ops

> Opt-in infrastructure. **By default you work locally** and never need anything here.
> Read this only if the maintainer gave you a server URL + worker id, or you are the
> maintainer managing the server. The operational loop lives in
> [`AGENTS.md`](../AGENTS.md).

## Coordination server (optional; access via a worker id)

By **default you work locally** — the ledger and git are the only state, exactly like a
solo workflow. Nothing here is required. The work server is an **opt-in** layer the
maintainer runs. Access is gated by a **server-issued worker id**, not by the URL: the URL
can be shared freely; without a valid id you can't claim or submit on the server. If you
have no id, ignore this section and just `work claim` / `work submit` locally.

**If the maintainer gave you a worker id**, put it (and the URL) in `.env` (config lives
there, not shell exports):

```
cp .env.example .env        # set WORK_SERVER to the URL, WORK_AGENT to your issued id
```

`work` loads `.env` automatically (a real shell environment variable overrides it). `.env`
is git-ignored; only `.env.example` is committed. Keys:

- `WORK_SERVER` — the server URL. **Unset/blank = local mode (the default).** Setting it
  is what turns coordination on. It does not need to be secret — the id is the gate.
- `WORK_AGENT` — **your worker id** (the token the maintainer minted). Sent as the
  `X-Work-Token` header; the server links it to your username and records the username as
  owner — the id itself is never stored or shown. Offline it is just the local owner label.
- `WORK_LEASE_SECONDS` — claim lease length (default 7200).

There is **no separate admin token** — admin is a role on a worker id. Token enforcement
is **on by default** (the server runs with `BP_WORK_REQUIRE_TOKEN=1`; set it to `0` only
for a fully private/trusted deployment).

**Maintainer — managing worker ids.** Bootstrap the first admin on the server host with
the direct-DB CLI (no existing admin needed):

```
bp-work-server worker add "<contributor-name>" --admin   # prints WORK_AGENT=… ; this id is admin
bp-work-server worker list
bp-work-server worker revoke <id>
```

Once you hold an admin id (set as your `WORK_AGENT`), you can manage ids over HTTP too:

```
work worker-add "Alice"           # mint a regular id for Alice
work worker-add "Bob" --admin     # mint another admin
work worker-list                  # ids, usernames, roles, last-seen
work worker-revoke <id>           # disable an id
```

With a server configured, claims are deconflicted centrally so you never duplicate
someone else's in-flight TU, and there are **two state stores with different lifetimes**:

- **Durable layer — git (`progress/status.json`).** The `done`/`blocked` states tied to
  committed code. It is the seed for both the server (`/admin/sync`) and a fresh
  `work bootstrap`. In server mode the CLI writes **only** these durable states to
  `status.json` — never `owner` or transient `in_progress`/`compiled` — so concurrent
  agents don't collide on the same file. Keep committing it. (Locally, `status.json`
  keeps its full mirror as before.)
- **Live layer — server DB.** Claims, leases, `owner`, transient statuses, and the event
  log. Ephemeral; never committed.

When a server is configured you **don't have to push `status.json` or bump the submodule**:
a GitHub Action reconciles both from the server automatically, so contributors push only
to `b5-decomp`.

**Checking out work:** `work claim <tu> ...` claims those specific TUs; `work claim -n N`
(no id) claims the next N ready ones from the queue. With a server every claim is atomic
across everyone — two agents pulling the queue at once get *different* TUs, and a specific
TU already held by someone else is refused (reported, not stolen) — and leases auto-expire,
so if you claim more than you finish the rest return to `todo`. Without a server it claims
locally. `work next` only previews (reserves nothing). `work start <tu>` is the older alias
for claiming one TU and also prints its dossier.

**If the server is unreachable, keep working — don't stop.** A `[work] server unreachable`
warning is not an error: the CLI transparently falls back to the local ledger, and your
claims/submits/reviews are queued and synced automatically when it reconnects. Finished
work is never lost. You don't manage this; just carry on.

**Reverting everything** (the post-server equivalent of "git reset + delete the db"):

```
work server-reset --to <good-ref>   # git-resets repo + b5-decomp, drops the local
                                    #   ledger cache, reseeds the server (reset=true)
```

`reset=true` discards live claims and the server event log (claims are ephemeral; event
history is not recoverable) — it is the deliberate clean-slate path. Omit `--to` to keep
the working tree and only drop the cache + reseed. Then `work bootstrap` to rebuild the
local ledger. **Without a server configured**, `work server-reset` just does the local
half (git reset + drop the ledger cache) — the same revert you did before the server
existed.

**Updating the server's dashboard.** When committed work outpaces the server (the
reconcile bot ran, or commits landed outside the claim/submit flow), run
`work server-update` — it refreshes `progress/class_homes.json`, pushes, and asks the
server to pull + re-import (`reset=false`: live claims + event log preserved); the
dashboard re-warms attribution on its next view. Per-contributor credit is **git-derived**
(surviving-line authorship of each TU's committed files), shown as "contributed to" (any
author) and "primary on" (dominant author). `class:` TUs carry no source path, so they are
attributed via `progress/class_homes.json` (`work resolve-class-homes` maps each to its
real committed home file; ambiguous ones are left unmapped, never guessed). There is **no
event-reconstruction tool** — the removed `server-reconcile-events` fabricated `review_pass`
events from git history and is gone; any such rows are hidden by default
(`BP_HIDE_RECONSTRUCTED`).
