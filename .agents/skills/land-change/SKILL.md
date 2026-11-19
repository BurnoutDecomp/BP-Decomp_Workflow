---
name: land-change
description: >-
  How to commit and push in both repositories without breaking the shared build or sweeping in
  someone else's work. b5-decomp: stage only your paths, commit from a message file, fetch,
  rebase onto origin/dev, `git -C b5-decomp push origin dev`, retry on non-fast-forward. Parent
  (BP-Decomp_Workflow): never commit progress/status.json, the CI audit outputs or the b5-decomp
  pointer (a bot does); do commit, in the same sitting, the parent half of your change (mount
  lines in tools/build/build_game_exe.bat, porter fixes under tools/assets/, your tools/ edits)
  on origin/main, checked with `git diff --stat`. Covers the Co-Authored-By trailer, shared
  checkouts (no `git add -A`, stash or --autostash), hash-object pitfalls, CRLF-safe .bat edits,
  retiring landed branches. Load before any git add, commit,
  push or rebase, or when CI goes red after a push ("ahead N", a single LNK2019).
---

# Land a change

How work reaches `origin` in this project's two repositories: what you commit where, in what
order, and the checks that stop you from carrying somebody else's edits or breaking the shared
build. Not for: build and link failures ([`build-and-link`](../build-and-link/SKILL.md)),
folding partfiles ([`fold-partfiles`](../fold-partfiles/SKILL.md)), writing the code itself
([`reconstruct-tu`](../reconstruct-tu/SKILL.md)).

## Which repository holds what

| Repository | Integration branch | You commit | You never commit |
|---|---|---|---|
| `b5-decomp` (submodule) | `dev` | your source, header and test files | another agent's dirty files |
| parent `BP-Decomp_Workflow` | `main` | the parent half of your change: mount lines in `tools/build/build_game_exe.bat`, asset-porter fixes under `tools/assets/`, your own `tools/` edits, a deliberate move of the `tools/nushaders` / `tools/yap` / `tools/volatility` pointer (after that repository's own commit is pushed) | the bot-owned state and local churn listed below |

**Bot-owned (never commit):** the `b5-decomp` pointer, `progress/status.json`, and the CI
outputs. The exact list is `FILES` in `tools/work/publish_snapshot.py`: `.github/workflows/reconcile-status.yml`
commits the pointer plus `status.json`, `class_homes.json`, `funcaudit.json`, `stubs.json` and
`source_status.json` after every push to `dev`; `build-and-publish.yml` commits `asmaudit.json`
and `linked_files.json`. An agent committing them races or duplicates the bot. Leave the
parent's ` M b5-decomp` and that churn uncommitted. `work hooks install` (run by
`work bootstrap`) switches on `tools/githooks/pre-commit`, which refuses any commit that stages
them; the maintainer's override for a deliberate commit is `BP_ALLOW_BOT_FILES=1`.

**Local churn (never commit):** the `active_goal` that `work goal set|clear` writes into
`progress/goals.json` (a deliberate goal change follows [`goal-scoping`](../goal-scoping/SKILL.md)),
local audit renderings such as `progress/asmaudit.md`, and anything under the ignored local
inputs (`references/`, `IDA Files/`, `.ida-exports/`, `scratch/`, `tools/assets/shaders/out/`).

**Commit the parent half anyway, and why.** Nothing reconciles a mount or a porter. A mount is
build configuration paired 1:1 with the b5 commit it serves; leaving it out takes the shared
build red for everyone (three times in 24 h on 2026-08-27/28). A porter fix left out means every
other contributor's `build data` keeps emitting the broken asset ([`port-assets`](../port-assets/SKILL.md)).
An operating-doc edit made on request (AGENTS.md, STRATEGY.md, a skill) is the exception: leave
it uncommitted for the maintainer unless the request says to commit it.

## Before every commit

1. `git status -sb` in the repository you commit, and in the other one. Read ahead/behind and
   every dirty path. A dirty file you did not change belongs to someone else.
2. Decide which checkout you are in. **Private:** only your files and bot churn are dirty and no
   other agent or session works here. **Shared:** anything else (a campaign, a second session,
   another agent's dirty file). In a shared checkout follow
   [references/shared-checkout.md](references/shared-checkout.md).
3. Fetch both and read what landed: `git -C b5-decomp fetch origin`, then
   `git -C b5-decomp log --oneline HEAD..origin/dev`; `git fetch origin`, then
   `git log --oneline HEAD..origin/main`. Another contributor may have landed the same body or
   mount; read origin's `.bat` before you write mount lines.
4. Write the commit message to a file with your file-writing tool (a unique name in your scratch
   folder, never a heredoc), ending with the trailer (see "Commit trailer"). Commit with `-F`.
5. Commit after every green gate, not at the end of a unit of work: a shared tree has been reset
   under a live wave and the uncommitted work vanished without an error (2026-08-29).

## Land in b5-decomp

1. `git -C b5-decomp add -- <your paths>` (never `-A`, never a directory), then
   `git -C b5-decomp diff --cached --stat`. A staged file that is not yours means another agent
   is active: leave it alone.
2. `git -C b5-decomp commit -F <msgfile> -- <your paths>`. The pathspec commits only those
   paths, whatever else sits in the index. Then `git -C b5-decomp show --stat HEAD`: the file
   count must be yours alone.
3. `git -C b5-decomp fetch origin`, then `git -C b5-decomp rebase origin/dev`. In a private
   checkout, `--autostash` may carry your own uncommitted work around the rebase. In a shared
   checkout never rebase in place: [references/shared-checkout.md](references/shared-checkout.md).
4. If origin changed a file you touched, re-run your gate (`python tools/work/selfcheck.py <files>`).
5. `git -C b5-decomp push origin dev` (from another branch: `HEAD:dev`). Rejected as
   non-fast-forward? Other agents push to `dev` and the remote moved under you: go back to 3.
   Never force.

## Land the parent half (same sitting, right after the b5 push)

Order: the b5 commit first, then the parent. The bot moves the pointer within minutes of your
b5 commit reaching `dev`; your mount reaches `origin/main` only when you push it. A mount that
lands before its b5 half makes `build exe` refuse to start for everyone (2026-08-29).

**Route A (private checkout, and every path you commit carries only your edits):**

1. `git add -- <your paths>`; `git diff --cached --stat`.
2. `git commit -F <msgfile> -- <your paths>`.
3. `git fetch origin`, then `git rebase --autostash origin/main` (carries the bot churn around
   the rebase; private checkout only). If re-applying the autostash conflicts in a bot-owned
   file, take origin's version (`git checkout HEAD -- <that file>`; the next `work` command
   re-syncs it), and drop the kept stash entry only once nothing else in it is missing.
4. Check before pushing: `git diff --stat origin/main HEAD` names only your files, with the line
   count you actually wrote, and `git show HEAD` contains your hunks and nothing else. A bigger
   number means you are carrying somebody else's work.
5. `git push origin HEAD:main`. Rejected? Back to 3.

**Route B (shared checkout, or a path you commit also carries someone else's uncommitted
lines: the shared `.bat` usually does):** build the commit off to the side from origin/main's
blob plus only your hunk, verify it, push it. Never `git add` or `git hash-object` the
working-tree file: either one commits their edits with yours (2026-08-29: a "4-line" mount
commit carried 28 lines, including another wave's mount of a TU whose b5 half was not on `dev`).
Exact commands: [references/parent-side-commit.md](references/parent-side-commit.md).

**Mount lines: use `work mount`.** `work mount <b5 file> --push -m "<message>" -m "<trailer>"`
is Route B automated: it adds the lines beside their siblings in your working `.bat` (CRLF kept,
everyone else's lines untouched), builds a commit of only those lines on origin/main's own blob,
verifies the numstat, refuses while the file is not on b5-decomp's `origin/dev`, and pushes.
`--commit` alone builds the commit and prints the push command; `--dry-run` shows the plan.

**Never leave the parent "ahead N".** An unpushed mount commit turned Build & Publish red three
runs in a row (2026-09-14) while every local build linked: CI builds origin's `.bat` against the
pointer the bot already advanced, and re-running CI never picks up an unpushed commit. A red
Build & Publish with one LNK2019: run `git status -sb` in the parent first.

## Commit trailer

- Every commit ends with a `Co-Authored-By:` trailer naming the model that **actually ran** the
  work. The commit author stays whatever identity the committing contributor's git is
  configured with; only the trailer names the model.
- Copy the trailer from AGENTS.md's commit-trailer line ("current value"). That line is the
  authority, and the user's most recent explicit instruction outranks it. An agent that is not
  Claude names its own model in the same trailer form.
- Do not trust the harness to tell you which model you are: after a mid-session model switch,
  both the default co-author string and the "you are powered by" line were stale (2026-08-27).
- Never rewrite pushed commits to correct a trailer: others have built on them, and a stale
  label is cheaper than rewritten shared history. An older trailer naming an earlier model is
  correct for its date (commits before 2026-08-27 stamped `Claude Fable 5` really were that
  model); do not "fix" the record.

## CRLF-safe edits and byte-exact content

- Never edit a `.bat`/`.cmd` with `sed -i`, `tee` or any Git-Bash tool that writes LF.
  `.gitattributes` sets `eol=crlf`, so an LF rewrite hashes like the CRLF blob: `git status`
  reports the file clean while `cmd.exe` cannot parse it, and the build dies in parse garbage
  with nothing in `git diff`. `build doctor` and every `build` step that runs a batch file now
  refuse a tracked `.bat`/`.cmd` that is not pure CRLF, so the damage fails loudly.
- Edit with Python that preserves the existing endings, then check the file still has one
  carriage return per line (CR count equals line count). Snippet, check and repair:
  [references/crlf-and-content.md](references/crlf-and-content.md).
- Repair when nobody's uncommitted lines are in the file: delete it, then `git checkout -- <file>`.
  When the file carries uncommitted lines (yours or another agent's), re-terminate it in place
  with Python instead; `checkout` would discard them.
- Content with backslashes (regexes, Windows paths, `\n`) never goes through a bash heredoc: the
  transport unescapes it. Write it with your file-writing tool and use it by path. A Python
  `SyntaxWarning: invalid escape sequence` from heredoc-fed code is transport corruption, not
  noise.

## Retire landed branches

- Once a branch's changes have landed in its repository's integration branch (`dev` for
  b5-decomp, `main` for the parent), delete its remote and local refs as part of the same
  delivery.
- Prove it landed: ancestry (`git merge-base --is-ancestor <branch> origin/dev`), or, for
  cherry-picked or squashed work, exact changed-path equivalence. Matching names prove nothing.
  Commands: [references/retire-branches.md](references/retire-branches.md).
- Retire duplicate or older refs only when a retained, published successor preserves their
  complete work.
- Preserve unmerged work and dirty or active checkouts. A clean retired checkout may be detached
  at its exact existing commit before its branch is removed; keep any needed files and evidence.
- Do not accumulate completed campaign branches.

## Pushed history and local inputs

- Never force-push the public repositories or rewrite pushed history without the maintainer's
  explicit go-ahead.
- `references/`, `IDA Files/`, `.ida-exports/`, `scratch/` and `tools/assets/shaders/out/` are
  local inputs: never `git add -f` them.

## Never

- Never `git add -A`, `git add .`, `git commit -a`, or add a whole directory, in either repository.
- Never commit the `b5-decomp` pointer, `progress/status.json` or another bot-owned file.
- Never stage, commit, restore, revert or stash another agent's dirty file.
- Never `git add` or `git hash-object` a shared working-tree file to commit "your" lines of it.
- Never push a mount before its b5 commit is on `origin/dev`; never leave the parent ahead of
  `origin/main` once its b5 half is pushed.
- Never force-push, and never rewrite a pushed commit (not even to fix a trailer).
- Never edit a `.bat`/`.cmd` with an LF-writing tool; never feed backslashed content through a
  heredoc.
- Never trust a commit message: it is a claim. Diff the commit against its own parent.

## Tools

| Tool | Use |
|---|---|
| `git -C b5-decomp status -sb` / `git status -sb` | dirty paths, ahead/behind, before every commit |
| `git commit -F <msgfile> -- <paths>` | commit only your paths, message from a file |
| `git diff --stat origin/main <commit>`, `git show --stat <commit>` | the file count and line count you are about to push |
| `tools/work/publish_snapshot.py` | the bot's publisher: `FILES` is the bot-owned list; its temp-index commit is the model for Route B |
| `.github/workflows/reconcile-status.yml`, `.github/workflows/build-and-publish.yml` | what the bot commits, and when |
| `.gitattributes` | `*.bat` / `*.cmd` are `eol=crlf`; `*.sh` is `eol=lf` |
| `python tools/work/selfcheck.py <files>` | re-gate your files after a rebase touched them |

## Read next

- [references/parent-side-commit.md](references/parent-side-commit.md): Route B, step by step.
- [references/shared-checkout.md](references/shared-checkout.md): publishing from a tree other
  agents are editing; signs of a concurrent session.
- [references/crlf-and-content.md](references/crlf-and-content.md): the CRLF-preserving edit,
  its check and repair; message files.
- [references/retire-branches.md](references/retire-branches.md): proving a branch landed.
- [`build-and-link`](../build-and-link/SKILL.md) (what a mount is, the parent-staleness rule),
  [`fold-partfiles`](../fold-partfiles/SKILL.md), [`port-assets`](../port-assets/SKILL.md),
  [`campaign-lane`](../campaign-lane/SKILL.md), [`campaign-conductor`](../campaign-conductor/SKILL.md).
