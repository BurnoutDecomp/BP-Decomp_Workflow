# Agent skills

Procedures an agent loads when it is about to do a particular kind of work. `AGENTS.md`
stays the always-loaded core (what we are doing, the source-of-truth ladder, the hard
rules) and its **routing table** says which skill to load before which work. A skill holds
the procedure for that work, so the rules arrive at the moment they apply instead of
being buried in one long file.

```
.agents/skills/<name>/
  SKILL.md             required: frontmatter + the procedure
  references/*.md      optional: depth that SKILL.md links to
  agents/openai.yaml   optional: Codex policy (user-invoked-only skills)
```

## How each tool finds them

| Tool | Reads | Setup |
|---|---|---|
| Codex | `.agents/skills/` in the repo (and parent folders), `~/.agents/skills/` | none |
| Antigravity | `.agents/skills/` (legacy `.agent/skills/` too) | none |
| Claude Code | `.claude/skills/` only | `work skills link` makes `.claude/skills` a junction (Windows) or symlink to `.agents/skills`. `work bootstrap` runs it; `.claude/` is gitignored. |
| API / LiteLLM loops | nothing | the conductor pastes the SKILL.md body, plus any `references/` file it names, into the prompt |

Invoke a skill by name with `/name` (Claude Code, the Antigravity app) or `$name` (Codex).
Agents also load a skill on their own when its description matches the task, except the
user-invoked ones below.

## Index

| Skill | Load it before | Invoked by |
|---|---|---|
| [`reconstruct-tu`](reconstruct-tu/SKILL.md) | claiming, continuing or submitting a TU; writing code under `b5-decomp/src` | agent |
| [`review-tu`](review-tu/SKILL.md) | reviewing a TU's reviewer packet (runs as a fresh subagent) | agent |
| [`console-evidence`](console-evidence/SKILL.md) | deciding what the console does: which build wins, which tool answers which question | agent |
| [`diagnose-parity-bug`](diagnose-parity-bug/SKILL.md) | chasing a behaviour difference from the original game | agent |
| [`bug-test`](bug-test/SKILL.md) | writing or running a harness case, or any run of the game | agent |
| [`land-change`](land-change/SKILL.md) | any commit or push, in either repository | agent |
| [`build-and-link`](build-and-link/SKILL.md) | building the exe or game data; any compile or link failure in the full build | agent |
| [`fold-partfiles`](fold-partfiles/SKILL.md) | creating, mounting or folding wave partfiles | agent |
| [`port-assets`](port-assets/SKILL.md) | changing or running an asset converter | agent |
| [`verify-sweep`](verify-sweep/SKILL.md) | the verification sweep of already-done TUs | agent |
| [`goal-scoping`](goal-scoping/SKILL.md) | setting, tuning or importing a `work goal` | agent |
| [`byte-match`](byte-match/SKILL.md) | byte-matching functions on the native X360 tree; reading or landing byte-match progress | agent |
| [`x360-toolchain`](x360-toolchain/SKILL.md) | setting up the XDK and the `x360` worktree; compiling or linking the native tree | agent |
| [`campaign-lane`](campaign-lane/SKILL.md) | working as one lane of a multi-agent campaign | agent |
| [`campaign-conductor`](campaign-conductor/SKILL.md) | planning and running a multi-agent campaign | agent |
| [`apt-completion`](apt-completion/SKILL.md) | the one-time Apt path consolidation, once ActionScript works end to end | user only |
| [`ledger-maintenance`](ledger-maintenance/SKILL.md) | reconciling the ledger, re-baselining a ratchet, coordination-server operations | user only |
| [`debug-menu-campaign`](debug-menu-campaign/SKILL.md) | the debug-menu parity campaign | user only |
| [`sound-pass`](sound-pass/SKILL.md) | the sound parity campaign | user only |
| [`menu-coverage`](menu-coverage/SKILL.md) | the menu coverage campaign | user only |

## Writing a skill

### Frontmatter

```yaml
---
name: reconstruct-tu
description: >-
  What it does, then when to use it, in the words an agent will actually see.
---
```

- `name` is the folder name: lowercase letters, digits and hyphens.
- `description` is at most 1,024 characters. It is the only part of a skill that is
  always in an agent's context, so it decides whether the skill ever loads. Name the
  commands (`work submit`), files, error text ("unresolved external") and user phrasing
  ("continue") that should trigger it.
- Claude Code-only keys, which the other tools ignore:
  - `disable-model-invocation: true` for a user-invoked skill;
  - `context: fork` for a skill that must run as a fresh subagent (`review-tu`).
- A user-invoked skill also needs `agents/openai.yaml` for Codex:

  ```yaml
  policy:
    allow_implicit_invocation: false
  ```

  Antigravity has no such flag, so its description must start with "User-invoked only:"
  and its body's first line must tell the agent to stop unless the user asked for it.

### Body

- Under 500 lines (Claude Code's limit); aim for about 250. Depth goes in `references/`.
- Shape: what it is for, and not for, then the steps, then a **Never** list, then the
  tools, then where to read next.
- Procedure, not state. No counts, percentages, SHAs or "currently" figures: they are
  wrong a week later. Point at the `progress/` file that holds the state instead.
- Tools by repo-relative path. Every flag is checked against the tool's `--help` or its
  source before it goes in.
- One line per rule. A dated incident ("measured 2026-08-28") is provenance: keep it to a
  clause and link the write-up if a tracked one exists.

### Public-repository hygiene

This repository is public.

- No personal data: no e-mail addresses, no user-profile paths, and none of one
  contributor's working preferences (agent counts, model choice, which issues they take).
  Those belong in that contributor's personal skills (`~/.agents/skills`,
  `~/.claude/skills`).
- `references/`, `IDA Files/`, `.ida-exports/` and `scratch/` are ignored local inputs, not
  part of a clone. A skill may name a path there where AGENTS.md does, and must say it is
  a local input; it never copies content out of them, and never says more about what they
  hold than AGENTS.md does.

### Check

`work skills check` validates every skill: frontmatter, name equals folder, description
length, body length, relative links, tool paths that exist, the user-invoked flags, and
that every skill is in this index and in AGENTS.md's routing table. It also rejects e-mail
addresses, user-profile paths and any pattern in the clone's untracked
`.git/info/public-denylist` (one regex per line), which the git hooks apply to every commit.
