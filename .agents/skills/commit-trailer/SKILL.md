---
name: commit-trailer
description: >-
  Put the exact models that wrote a commit in its Co-Authored-By trailers. Stage your paths, run
  `work trailer` (tools/work/trailer.py): it reads the models from the tools' own logs (the Claude
  Code transcript and its subagents', the Codex rollout and its workers'), not from a model's
  memory, and prints the session's line, such as `Co-Authored-By: Codex GPT-6.2 Sol
  <noreply@openai.com>` or `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, plus one
  line per subagent, worker or earlier model that edited a staged file. Covers the label form
  (version and variant always: `Codex GPT-6` or `Claude` alone are wrong), `work trailer --check
  <msgfile>` before committing, `--model <id>` when no log can be read, `--why`, committing
  another agent's work, and a wrong trailer on an unpushed commit (amend) or a pushed one (leave
  it). Load before every git commit in either repository, together with land-change, whenever
  you are about to write "Co-Authored-By", and whenever you are unsure which model you are.
---

# Commit trailer

Every commit in both repositories ends with one `Co-Authored-By:` trailer per model that wrote
it, each naming the **exact** model. This skill is how an agent gets those names right. Not for:
staging, committing and pushing ([`land-change`](../land-change/SKILL.md)).

## Why a tool and not your memory

- A model knows its family, rarely its exact version: Codex sessions that ran `gpt-6.2-sol`
  signed `Codex GPT-6` (2026-11-21), and after a mid-session switch Claude's harness strings
  still named the previous model (2026-08-27).
- Each tool writes the model of every turn into its own session log, and every subagent or
  worker gets a log of its own. `work trailer` reads those records.

## Steps

1. Stage your paths first (land-change). `work trailer` decides which subagents and workers
   count by the staged paths, and falls back to every changed path when nothing is staged.
2. Run `work trailer` in the repository you are committing in. Line 1 is the model the session
   runs now. One more line follows for every other model that edited a staged file, with an
   edit tool, after that file's last commit: an earlier model of the session, a Claude subagent,
   a Codex worker.
3. End your commit message file with exactly those lines: copy them, never retype them.
4. Run `work trailer --check <msgfile>`. It exits 1, and prints the missing lines, when the file
   lacks one.
5. Commit from the message file as [`land-change`](../land-change/SKILL.md) says.
6. Confirm: `git log -1 --format=%B` ends with the lines.

When `work trailer` cannot read a model it says why and exits 1. Then:

- it guessed the wrong tool: `work trailer --tool claude` or `work trailer --tool codex`;
- no log can be read: `work trailer --model <id>`, with the exact model id your tool shows in
  its own settings or status display.

A family name from memory is never the fallback.

## Where the models come from

| Tool | The session | Its helpers | Record |
|---|---|---|---|
| Claude Code | `projects/*/<CLAUDE_CODE_SESSION_ID>.jsonl` under `~/.claude` (or `CLAUDE_CONFIG_DIR`) | `<session>/subagents/*.jsonl` next to it | `message.model` of each assistant message; edits are its `Edit`, `Write`, `MultiEdit` and `NotebookEdit` calls |
| Codex | the `sessions/**/rollout-*.jsonl` under `~/.codex` (or `CODEX_HOME`) started in this folder or a folder above it whose last record is newest (by the record's own `timestamp`: Windows leaves an open log's file time stale); never a worker's log | `rollout-<time>-<session id>_<worker id>.jsonl` | `payload.model` of the turn's `turn_context`; edits are its patches (`*** Update File:` and the like) |

`work trailer --why` names the session log, the change it compared against (staged or changed
paths), and, for every extra line, which helper or earlier model edited which files.

## The label

| Model id in the log | Trailer |
|---|---|
| `claude-<family>-<major>[-<minor>]` | `Co-Authored-By: Claude <Family> <major>[.<minor>] <noreply@anthropic.com>` |
| `gpt-<version>[-<variant>]` | `Co-Authored-By: Codex GPT-<version>[ <Variant>] <noreply@openai.com>` |

- The version and the variant are part of the name: `Claude Opus 5.5`, `Codex GPT-6.2 Sol`,
  `Codex GPT-6 Luna`. `Codex GPT-6`, `Claude` or `Codex` alone are wrong.
- `work trailer --model <id>` prints the line for any id of those forms. An id it cannot label
  (another tool, another vendor) first gets a rule in `LABELS` in `tools/work/trailer.py`;
  until then write `Co-Authored-By: <Tool> <exact model> <vendor noreply address>`.

## Special cases

- **A helper that only read, searched or reviewed:** no line. Only edits to staged files made
  after their last commit count.
- **A helper that changed files only through shell commands** (a script, `sed`, a generator): not
  seen. Append its line from `work trailer --model <id>`.
- **You commit another agent's work** (a lane's files, a cherry-pick): keep the trailers that
  work carries, and add your own only for what you wrote.
- **A wrong trailer on your own unpushed commit:** correct the message file, then
  `git commit --amend -F <msgfile>`. Never amend another agent's commit.
- **A wrong trailer on a pushed commit:** leave it and tell the maintainer. Pushed commits are
  never rewritten to fix a trailer ([`land-change`](../land-change/SKILL.md)).
- The commit **author** stays the contributor's git identity; only the trailers name the models.

## Never

- Never write a trailer from memory, from an earlier commit or from an example in a doc.
- Never write a family name without its version and variant.
- Never drop a line `work trailer` printed: a model that edited a staged file wrote part of the commit.
- Never put the model in the commit author.
- Never rewrite a pushed commit to fix a trailer.

## Tools

| Tool | Use |
|---|---|
| `work trailer` (`tools/work/trailer.py`) | the trailer lines for this session and its helpers |
| `work trailer --check <msgfile>` | exit 1 unless the message file has every line |
| `work trailer --model <id>` | the line for a model id you already know |
| `work trailer --tool claude` / `--tool codex` | override the detected tool |
| `work trailer --why` | the session log, the change compared against, and where each extra line comes from |

## Read next

- [`land-change`](../land-change/SKILL.md): staging, committing and pushing in both repositories.
