---
name: commit-trailer
description: >-
  Put the exact model that ran the work in a commit's Co-Authored-By trailer. Run `work trailer`
  (tools/work/trailer.py): it reads the model from the tool's own session log (the Claude Code
  transcript, the Codex rollout), not from the model's memory, and prints the line, such as
  `Co-Authored-By: Codex GPT-6.2 Sol <noreply@openai.com>` or
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Covers the label form (version and
  variant always: `Codex GPT-6` or `Claude` alone are wrong), `work trailer --check <msgfile>`
  before committing, `--model <id>` when no log can be read, a session that switched models
  (`--why`), committing another agent's work, and a wrong trailer on an unpushed commit (amend)
  or a pushed one (leave it). Load before every git commit in either repository, together with
  land-change, whenever you are about to write "Co-Authored-By", and whenever you are unsure
  which model you are.
---

# Commit trailer

Every commit in both repositories ends with a `Co-Authored-By:` trailer naming the **exact**
model that ran the work. This skill is how an agent gets that name right. Not for: staging,
committing and pushing ([`land-change`](../land-change/SKILL.md)).

## Why a tool and not your memory

- A model knows its family, rarely its exact version: Codex sessions that ran `gpt-6.2-sol`
  signed `Codex GPT-6` (2026-11-21), and after a mid-session switch Claude's harness strings
  still named the previous model (2026-08-27).
- Each tool writes the model of every turn into its own session log. `work trailer` reads that
  record and prints the line.

## Steps

1. Run `work trailer` in the repository you are committing in. It prints one line.
2. End your commit message file with exactly that line: copy it, never retype it.
3. Run `work trailer --check <msgfile>`. It exits 1, and prints the right line, when the file
   lacks it.
4. Commit from the message file as [`land-change`](../land-change/SKILL.md) says.
5. Confirm: `git log -1 --format=%B` ends with the line.

When `work trailer` cannot read a model it says why and exits 1. Then:

- it guessed the wrong tool: `work trailer --tool claude` or `work trailer --tool codex`;
- no log can be read: `work trailer --model <id>`, with the exact model id your tool shows in
  its own settings or status display.

A family name from memory is never the fallback.

## Where the model comes from

| Tool | Log `work trailer` reads | Record |
|---|---|---|
| Claude Code | `projects/*/<CLAUDE_CODE_SESSION_ID>.jsonl` under `~/.claude` (or `CLAUDE_CONFIG_DIR`) | `message.model` of the newest assistant message |
| Codex | the newest `sessions/**/rollout-*.jsonl` under `~/.codex` (or `CODEX_HOME`) started in this folder or a folder above it | `payload.model` of the newest `turn_context` |

`work trailer --why` names the log it read and lists every model that session recorded.

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

- **The session switched models during the change:** one trailer per model that wrote part of
  it. `work trailer --why` lists them, oldest first.
- **You commit another agent's work** (a lane's files, a cherry-pick): keep the trailer that
  work carries, and add your own only for what you wrote.
- **A wrong trailer on your own unpushed commit:** correct the message file, then
  `git commit --amend -F <msgfile>`. Never amend another agent's commit.
- **A wrong trailer on a pushed commit:** leave it and tell the maintainer. Pushed commits are
  never rewritten to fix a trailer ([`land-change`](../land-change/SKILL.md)).
- The commit **author** stays the contributor's git identity; only the trailer names the model.

## Never

- Never write the trailer from memory, from an earlier commit or from an example in a doc.
- Never write a family name without its version and variant.
- Never put the model in the commit author.
- Never rewrite a pushed commit to fix a trailer.

## Tools

| Tool | Use |
|---|---|
| `work trailer` (`tools/work/trailer.py`) | the trailer line for this session |
| `work trailer --check <msgfile>` | exit 1 unless the message file has that line |
| `work trailer --model <id>` | the line for a model id you already know |
| `work trailer --tool claude` / `--tool codex` | override the detected tool |
| `work trailer --why` | which log the model came from; every model the session recorded |

## Read next

- [`land-change`](../land-change/SKILL.md): staging, committing and pushing in both repositories.
