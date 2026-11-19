# Publishing from a shared checkout

A checkout is **shared** when any tracked file you did not change is dirty, or a campaign, a
second session or another agent is working in the same tree. Assume shared when unsure.
[`campaign-lane`](../../campaign-lane/SKILL.md) and [`campaign-conductor`](../../campaign-conductor/SKILL.md)
point here for publication.

## What never happens in a shared checkout

- No `git add -A`, `git add .`, `git commit -a`, and no adding a directory: a wave that ran
  `git add -A src/` adopted another wave's four uncommitted files (286 lines) into a commit its
  message did not describe (2026-08-29).
- No commit without a pathspec. `git commit` takes the whole index, so another agent's `git add`
  becomes your commit: 19 files of a live wave went out that way (2026-09-02). Use
  `git commit -F <msgfile> -- <paths>`, and check the file count before (`git diff --cached --stat`)
  and after (`git show --stat HEAD`).
- No `git stash`, `stash pop`, `--autostash`, `reset --hard`, and no `checkout --` / `restore`
  of a file you do not own. On a clean tree a bare `git stash` saves nothing and the `pop`
  applies an old, unrelated stash (2026-09-23); an `--autostash` re-apply silently left a lane's
  file at HEAD (2026-09-24, the third incident). Every one of these rewrites files that another
  agent is editing.
- No in-place rebase: it needs a clean tree, and the only ways to get one are the commands above.

## b5-decomp: publish your commit

After `git -C b5-decomp commit -F <msgfile> -- <your paths>`:

1. `git -C b5-decomp fetch origin`.
2. If `git -C b5-decomp merge-base --is-ancestor origin/dev HEAD` succeeds, origin did not move
   past your base: `git -C b5-decomp push origin HEAD:dev` is a fast-forward. Done.
3. Otherwise replay your commit onto `origin/dev` without touching the working tree (Git 2.40 or
   later). For several commits, run this oldest first, feeding each result in as the next
   `BASE`:

   ```bash
   S=<absolute path of your own scratch folder>
   BASE=origin/dev
   C=<your commit>
   tree=$(git -C b5-decomp merge-tree --write-tree --merge-base="$C^" "$BASE" "$C"); echo "exit $?"
   ```

   Exit 1 means a conflict (the output then lists the conflicted files): stop, do not push, and
   resolve it with whoever owns the other change. Exit 0 prints only the tree id; then:

   ```bash
   git -C b5-decomp log -1 --format=%B "$C" > "$S/msg-replay.txt"
   new=$(git -C b5-decomp commit-tree "$tree" -p "$BASE" -F "$S/msg-replay.txt")
   ```
4. Verify: `git -C b5-decomp diff --stat origin/dev "$new"` names only your files, and
   `git -C b5-decomp show "$new"` holds only your hunks.
5. `git -C b5-decomp push origin "$new":refs/heads/dev`. Rejected: fetch and redo step 3 from
   `origin/dev`. Never force.
6. Confirm it is on the remote: `git -C b5-decomp fetch origin`, then
   `git -C b5-decomp merge-base --is-ancestor "$new" origin/dev`. Work you depend on must be on
   the remote, not just in a log: another agent's rebase in a shared checkout can drop a local
   commit.
7. Leave the shared checkout as it is: its branch still holds your pre-replay commit and its
   working tree lacks origin's newer changes. Never reset or rebase it to catch up. Whoever owns
   the tree re-syncs it when no agent is mid-edit; that rebase drops your original commit as
   already applied.

## Parent: publish your commit

Always the side commit: [parent-side-commit.md](parent-side-commit.md). In a campaign, only the
agent the brief names commits parent files; a lane adds its mount line locally (CRLF-preserving
edit), before its first call site reaches the tree, and reports the exact line.

## Signs of a concurrent session

Two sessions under the same git identity can run in one checkout without knowing it.

- `git reflog -15` shows rebases or commits you did not make; `git log --oneline -10` shows
  commits under your identity you do not recognise; a file you verified vanished or changed; a
  coordination-server claim answers `HTTP 409: TU is todo, not in progress`.
- Then: stop broad operations, stage only individually verified files, prefer read-only
  verification to rewriting a file someone else is editing, let a correct further-along result
  stand, and tell the user straight away (uncommitted work can be lost to the other session's
  clean, rebase or checkout).
- Before you blame a concurrent session for a collision, check whether one of your own agents
  did it: the evidence reads the same from the victim's side.
- A red shared build on a TU that is not yours, possibly untracked, is usually another agent's
  in-flight work, not an outage. Check whether the failing file is yours, and tracked, before
  you diagnose; never edit it.

## Scratch is shared too

- Give scratch files names unique to your task or lane (never `run.ps1`, `tmp.py`,
  `build_page.py`): another session overwrote a generic name mid-wave (2026-08-29).
- "Parked out of tree" is not storage: a whole scratch folder vanished with its session. Commit
  finished work, behind its blocker if it must wait.
