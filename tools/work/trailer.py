#!/usr/bin/env python3
"""work trailer: the Co-Authored-By line for the model that runs this session.

It reads the model the tool itself recorded, never what the model believes it is (a model
knows its family, rarely its exact version):

  Claude Code  the newest assistant message of this session's transcript
               (projects/*/<CLAUDE_CODE_SESSION_ID>.jsonl under ~/.claude or CLAUDE_CONFIG_DIR)
  Codex        the newest turn_context of the newest session log started in this folder or a
               folder above it (sessions/**/rollout-*.jsonl under ~/.codex or CODEX_HOME)

and turns the model id into the label the history uses:

  claude-opus-5-5  ->  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  gpt-6.2-sol      ->  Co-Authored-By: Codex GPT-6.2 Sol <noreply@openai.com>

usage:
  work trailer                       print the line (exit 1 when no model can be read)
  work trailer --tool codex          when the tool is detected wrongly (claude | codex)
  work trailer --model gpt-6.2-sol   the line for a model id you already know
  work trailer --check MSGFILE       exit 1 unless MSGFILE has that line
  work trailer --why                 also say which log the model came from, and every
                                     model that session recorded
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time

LABELS = (
    (re.compile(r"claude-([a-z]+)-(\d+)(?:-(\d{1,2}))?(?:-\d{8})?"),
     lambda m: ("Claude {} {}{}".format(m[1].title(), m[2], "." + m[3] if m[3] else ""),
                "noreply@anthropic.com")),
    (re.compile(r"gpt-(\d+(?:\.\d+)?)(?:-([a-z]+))?"),
     lambda m: ("Codex GPT-{}{}".format(m[1], " " + m[2].title() if m[2] else ""),
                "noreply@openai.com")),
)
TAIL_BYTES = 4 << 20          # the newest records sit at the end of a log: read that part first
CODEX_RECENT_S = 12 * 3600    # a Codex log written this recently counts as a live session


def trailer_for(model: str) -> str | None:
    for rx, make in LABELS:
        m = rx.fullmatch(model.strip().lower())
        if m:
            label, mail = make(m)
            return f"Co-Authored-By: {label} <{mail}>"
    return None


def records(path: str, tail_only: bool):
    """The JSON records of a .jsonl log in file order; only its last TAIL_BYTES when tail_only."""
    with open(path, "rb") as fh:
        if tail_only and os.fstat(fh.fileno()).st_size > TAIL_BYTES:
            fh.seek(-TAIL_BYTES, os.SEEK_END)
            fh.readline()                                     # drop the line the seek cut
        for line in fh:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def newest(path: str, pick):
    """The model of the last record `pick` accepts: the tail first, the whole log if needed."""
    for tail_only in (True, False):
        found = None
        for rec in records(path, tail_only):
            found = pick(rec) or found
        if found or os.path.getsize(path) <= TAIL_BYTES:
            return found
    return None


def every(path: str, pick) -> list:
    """Every model `pick` accepts in a log, in order of first use."""
    return list(dict.fromkeys(m for m in (pick(r) for r in records(path, False)) if m))


def pick_claude(rec):
    if rec.get("type") != "assistant":
        return None
    m = (rec.get("message") or {}).get("model") or ""
    return m if m.startswith("claude-") else None             # skips "<synthetic>"


def pick_codex(rec):
    return (rec.get("payload") or {}).get("model") if rec.get("type") == "turn_context" else None


def claude_log(why: list):
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not sid:
        why.append("not a Claude Code shell (CLAUDE_CODE_SESSION_ID is not set)")
        return None
    home = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    hits = glob.glob(os.path.join(home, "projects", "*", sid + ".jsonl"))
    if not hits:
        why.append(f"no transcript {sid}.jsonl under {os.path.join(home, 'projects')}")
        return None
    path = max(hits, key=os.path.getmtime)
    why.append(f"model read from the Claude Code transcript {path}")
    return path


def _inside(child: str, parent: str) -> bool:
    child, parent = (os.path.normcase(os.path.abspath(p)) for p in (child, parent))
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:                                         # different drives
        return False


def codex_log(why: list, recent_only: bool):
    home = os.environ.get("CODEX_HOME") or os.path.join(os.path.expanduser("~"), ".codex")
    logs = glob.glob(os.path.join(home, "sessions", "**", "rollout-*.jsonl"), recursive=True)
    here, now = os.getcwd(), time.time()
    for path in sorted(logs, key=os.path.getmtime, reverse=True):
        if recent_only and now - os.path.getmtime(path) > CODEX_RECENT_S:
            break
        try:
            with open(path, encoding="utf-8") as fh:
                first = json.loads(fh.readline())
        except (OSError, ValueError):
            continue
        cwd = (first.get("payload") or {}).get("cwd") if first.get("type") == "session_meta" else None
        if cwd and _inside(here, cwd):
            why.append(f"model read from the Codex session log {path} (started in {cwd})")
            return path
    why.append(f"no Codex session log started in {here} or a folder above it"
               + (" was written in the last 12 hours" if recent_only else ""))
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="work trailer", description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("usage:", 1)[1])
    ap.add_argument("--tool", choices=("claude", "codex"), help="which tool runs this session")
    ap.add_argument("--model", help="label this model id instead of reading a session log")
    ap.add_argument("--check", metavar="MSGFILE", help="exit 1 unless this commit message has the line")
    ap.add_argument("--why", action="store_true", help="say where the model came from")
    args = ap.parse_args(argv)

    why, path, pick, model = [], None, None, args.model
    if not model:
        tool = args.tool
        if tool in (None, "claude"):
            path, pick = claude_log(why), pick_claude
            tool = "claude" if path else tool
        if tool in (None, "codex") and not path:
            path, pick = codex_log(why, recent_only=args.tool is None), pick_codex
        model = newest(path, pick) if path else None
        if not model:
            print("work trailer: no model recorded for this session: " + "; ".join(why), file=sys.stderr)
            print("  pass --tool claude|codex, or --model <exact model id> read from your tool's own "
                  "settings (never a family name from memory)", file=sys.stderr)
            return 1
    line = trailer_for(model)
    if not line:
        print(f"work trailer: no label rule for model id {model!r}: write the line as "
              "'Co-Authored-By: <Tool> <exact model> <vendor noreply address>' and add a rule "
              "to LABELS in tools/work/trailer.py", file=sys.stderr)
        return 1

    if args.why:
        for w in why:
            print(f"# {w}")
        seen = every(path, pick) if path else [model]
        if len(seen) > 1:
            print("# this session recorded several models, oldest first: " + ", ".join(seen))
            print("# one trailer per model that wrote part of the change:")
            for m in seen:
                print("#   " + (trailer_for(m) or m))
    if args.check:
        with open(args.check, encoding="utf-8", errors="replace") as fh:
            lines = [l.strip() for l in fh]
        if line not in lines:
            ai = [l for l in lines if l.lower().startswith("co-authored-by:")]
            print(f"work trailer: {args.check} lacks this session's line:\n  {line}", file=sys.stderr)
            if ai:
                print("  it has: " + " | ".join(ai), file=sys.stderr)
            return 1
        print(f"ok: {args.check} has {line}")
        return 0
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
