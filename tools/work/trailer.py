#!/usr/bin/env python3
"""work trailer: the Co-Authored-By lines for the models that wrote the change you are committing.

It reads the models the tools themselves recorded, never what a model believes it is (a model
knows its family, rarely its exact version):

  Claude Code  this session's transcript (projects/*/<CLAUDE_CODE_SESSION_ID>.jsonl under ~/.claude
               or CLAUDE_CONFIG_DIR) and its subagents' transcripts (<session>/subagents/*.jsonl)
  Codex        the session log started in this folder or a folder above it whose last record is
               newest (sessions/**/rollout-*.jsonl under ~/.codex or CODEX_HOME; the record's own
               timestamp, never the file time), never a worker's log, and the logs of that
               session's workers (rollout-<time>-<session id>_<worker id>.jsonl)

The first line is the model the session runs now. One more line follows for every other model
(an earlier model of the session, a subagent, a worker) that edited a file of this change after
that file's last commit. The change is the staged paths, or every changed path when nothing is
staged. Edits are tool calls: Claude's Edit, Write, MultiEdit and NotebookEdit, and Codex patches.
A file changed only through shell commands is not seen: add that model's line with --model.

  claude-opus-5-5  ->  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  gpt-6.2-sol      ->  Co-Authored-By: Codex GPT-6.2 Sol <noreply@openai.com>

usage:
  work trailer                       print the lines (exit 1 when no model can be read)
  work trailer --tool codex          when the tool is detected wrongly (claude | codex)
  work trailer --model gpt-6.2-sol   the line for a model id you already know
  work trailer --check MSGFILE       exit 1 unless MSGFILE has every line
  work trailer --why                 also say where each line comes from
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

LABELS = (
    (re.compile(r"claude-([a-z]+)-(\d+)(?:-(\d{1,2}))?(?:-\d{8})?"),
     lambda m: ("Claude {} {}{}".format(m[1].title(), m[2], "." + m[3] if m[3] else ""),
                "noreply@anthropic.com")),
    (re.compile(r"gpt-(\d+(?:\.\d+)?)(?:-([a-z]+))?"),
     lambda m: ("Codex GPT-{}{}".format(m[1], " " + m[2].title() if m[2] else ""),
                "noreply@openai.com")),
)
TAIL_BYTES = 4 << 20          # the newest records sit at the end of a log: read that part first
CODEX_RECENT_S = 12 * 3600    # a Codex log whose last record is this recent counts as a live session
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
CODEX_CALLS = {"custom_tool_call", "function_call", "local_shell_call"}
PATCH_FILE = re.compile(r"\*\*\* (?:Update|Add|Delete) File: (.+?)(?=\\n|\\r|\r|\n|\"|`|$)")
ROLLOUT = re.compile(r"rollout-\d{4}-\d\d-\d\dT\d\d-\d\d-\d\d-([0-9a-f-]{36})(?:_([0-9a-f-]{36}))?\.jsonl$")


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


def parse_ts(ts) -> float | None:
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def pick_claude(rec):
    if rec.get("type") != "assistant":
        return None
    m = (rec.get("message") or {}).get("model") or ""
    return m if m.startswith("claude-") else None             # skips "<synthetic>"


def pick_codex(rec):
    return (rec.get("payload") or {}).get("model") if rec.get("type") == "turn_context" else None


# ------------------------------------------------------------------ the change being committed
def _git(*args):
    r = subprocess.run(["git", *args], capture_output=True)
    return r.stdout.decode("utf-8", "surrogateescape") if r.returncode == 0 else None


def _key(rel: str) -> str:
    return os.path.normcase(os.path.normpath(rel))


def repo_change():
    """(repo top, {path key: epoch of its last commit, 0 if never committed}, basis) for the staged
    paths, or for every changed path when nothing is staged; (None, {}, reason) outside a repo."""
    top = _git("rev-parse", "--show-toplevel")
    if not top:
        return None, {}, "not inside a git repository"
    top = os.path.normpath(top.strip())
    paths = [p for p in (_git("diff", "--cached", "--name-only", "-z") or "").split("\0") if p]
    basis = f"{len(paths)} staged path(s)"
    if not paths:
        entries = (_git("status", "--porcelain", "-z", "--untracked-files=all") or "").split("\0")
        i = 0
        while i < len(entries):
            e = entries[i]
            if len(e) > 3:
                paths.append(e[3:])
                if e[0] in "RC":
                    i += 1                                    # a rename also lists its old path
            i += 1
        basis = f"{len(paths)} changed path(s), nothing staged"
    times = {}
    for p in paths[:400]:
        ct = (_git("-C", top, "log", "-1", "--format=%ct", "--", p) or "").strip()
        times[_key(p)] = int(ct) if ct.isdigit() else 0
    return top, times, basis


def rel_key(top: str, path: str, base: str | None = None) -> str | None:
    if not os.path.isabs(path):
        path = os.path.join(base or os.getcwd(), path)
    try:
        r = os.path.relpath(os.path.abspath(path), top)
    except ValueError:                                         # another drive
        return None
    return None if r.startswith("..") else _key(r)


def claude_edits(path, top, times):
    """(time, model, path key) for each edit tool call in a transcript to a path of this change
    made after that path's last commit."""
    out = []
    with open(path, "rb") as fh:
        for line in fh:
            if b'"tool_use"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            msg = rec.get("message") or {}
            model, ts = msg.get("model") or "", parse_ts(rec.get("timestamp"))
            if rec.get("type") != "assistant" or not model.startswith("claude-") or ts is None:
                continue
            for item in msg.get("content") or []:
                if isinstance(item, dict) and item.get("type") == "tool_use" and item.get("name") in EDIT_TOOLS:
                    inp = item.get("input") or {}
                    key = rel_key(top, inp.get("file_path") or inp.get("notebook_path") or "")
                    if key in times and ts > times[key]:
                        out.append((ts, model, key))
    return out


def codex_edits(path, top, times):
    """(time, model, path key) for each patch in a Codex log to a path of this change made after
    that path's last commit; the model is the one of the turn the patch belongs to."""
    out, model, cwd = [], None, None
    with open(path, "rb") as fh:
        for line in fh:
            if b"session_meta" not in line and b"turn_context" not in line and b"Begin Patch" not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            kind, pl = rec.get("type"), rec.get("payload") or {}
            if kind == "session_meta":
                cwd = pl.get("cwd") or cwd
            elif kind == "turn_context":
                model = pl.get("model") or model
            elif kind == "response_item" and pl.get("type") in CODEX_CALLS and model:
                text = pl.get("input") or pl.get("arguments") or ""
                text = text if isinstance(text, str) else json.dumps(text)
                ts = parse_ts(rec.get("timestamp"))
                for fp in PATCH_FILE.findall(text):
                    key = rel_key(top, fp.strip(), cwd)
                    if ts is not None and key in times and ts > times[key]:
                        out.append((ts, model, key))
    return out


# ------------------------------------------------------------------ the session's own log
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


def claude_helpers(path: str) -> list:
    return sorted(glob.glob(os.path.join(os.path.splitext(path)[0], "subagents", "*.jsonl")))


def _inside(child: str, parent: str) -> bool:
    child, parent = (os.path.normcase(os.path.abspath(p)) for p in (child, parent))
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:                                         # different drives
        return False


def last_record_time(path: str) -> float:
    """Epoch of the log's last record. Not the file time: Windows leaves a log's modified time at
    its creation while Codex keeps the file open (a log that showed 13:10 was written until 14:18)."""
    with open(path, "rb") as fh:
        size = os.fstat(fh.fileno()).st_size
        fh.seek(max(0, size - (64 << 10)))
        lines = fh.read().splitlines()
    for line in reversed(lines):
        try:
            at = parse_ts(json.loads(line).get("timestamp"))
        except (ValueError, AttributeError):
            continue
        if at is not None:
            return at
    return os.path.getmtime(path)


def _codex_logs():
    home = os.environ.get("CODEX_HOME") or os.path.join(os.path.expanduser("~"), ".codex")
    return glob.glob(os.path.join(home, "sessions", "**", "rollout-*.jsonl"), recursive=True)


def codex_log(why: list, recent_only: bool):
    here, now, started_here = os.getcwd(), time.time(), []
    for path in _codex_logs():
        m = ROLLOUT.search(os.path.basename(path))
        if m and m[2]:
            continue                                           # a worker's log is never the session
        try:
            with open(path, encoding="utf-8") as fh:
                first = json.loads(fh.readline())
        except (OSError, ValueError):
            continue
        cwd = (first.get("payload") or {}).get("cwd") if first.get("type") == "session_meta" else None
        if cwd and _inside(here, cwd):
            started_here.append((last_record_time(path), path, cwd))
    if started_here:
        at, path, cwd = max(started_here)
        if not recent_only or now - at <= CODEX_RECENT_S:
            when = datetime.fromtimestamp(at, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            why.append(f"model read from the Codex session log {path} (started in {cwd}, last record {when})")
            return path
    why.append(f"no Codex session log started in {here} or a folder above it"
               + (" has a record from the last 12 hours" if recent_only else ""))
    return None


def codex_helpers(path: str) -> list:
    m = ROLLOUT.search(os.path.basename(path))
    if not m:
        return []
    return sorted(p for p in _codex_logs()
                  if (w := ROLLOUT.search(os.path.basename(p))) and w[1] == m[1] and w[2])


# ------------------------------------------------------------------ main
def models_for_change(path, current, edits, helpers, why):
    """[current, then every other model that edited this change, by first edit]."""
    top, times, basis = repo_change()
    if not times:
        why.append(f"line 1: the model this session runs ({current}); no other model counted ({basis})")
        return [current]
    why.append(f"the change: {basis}")
    why.append(f"line 1: the model this session runs ({current})")
    first = {}
    for label, log in [("this session, an earlier model", path)] + [(f"helper {os.path.basename(h)}", h) for h in helpers]:
        for at, model, key in edits(log, top, times):
            if model == current:
                continue
            entry = first.setdefault(model, [at, label, set()])
            entry[0] = min(entry[0], at)
            entry[2].add(key)
    order = sorted(first, key=lambda m: first[m][0])
    for n, model in enumerate(order, 2):
        at, label, keys = first[model]
        shown = ", ".join(sorted(keys)[:3]) + (f" and {len(keys) - 3} more" if len(keys) > 3 else "")
        why.append(f"line {n}: {model}, {label}, edited {shown} after their last commit")
    if helpers and not order:
        why.append(f"{len(helpers)} subagent/worker log(s) found; none edited a path of this change "
                   "with another model")
    return [current] + order


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="work trailer", description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("usage:", 1)[1])
    ap.add_argument("--tool", choices=("claude", "codex"), help="which tool runs this session")
    ap.add_argument("--model", help="label this model id instead of reading a session log")
    ap.add_argument("--check", metavar="MSGFILE", help="exit 1 unless this commit message has every line")
    ap.add_argument("--why", action="store_true", help="say where each line comes from")
    args = ap.parse_args(argv)

    why, models = [], [args.model] if args.model else []
    if not models:
        tool, path = args.tool, None
        if tool in (None, "claude"):
            path = claude_log(why)
            if path:
                tool, pick, edits, helpers = "claude", pick_claude, claude_edits, claude_helpers
        if tool in (None, "codex") and not path:
            path = codex_log(why, recent_only=args.tool is None)
            if path:
                tool, pick, edits, helpers = "codex", pick_codex, codex_edits, codex_helpers
        current = newest(path, pick) if path else None
        if not current:
            print("work trailer: no model recorded for this session: " + "; ".join(why), file=sys.stderr)
            print("  pass --tool claude|codex, or --model <exact model id> read from your tool's own "
                  "settings (never a family name from memory)", file=sys.stderr)
            return 1
        models = models_for_change(path, current, edits, helpers(path), why)

    lines = []
    for model in models:
        line = trailer_for(model)
        if not line:
            print(f"work trailer: no label rule for model id {model!r}: write the line as "
                  "'Co-Authored-By: <Tool> <exact model> <vendor noreply address>' and add a rule "
                  "to LABELS in tools/work/trailer.py", file=sys.stderr)
            return 1
        if line not in lines:
            lines.append(line)

    if args.why:
        for w in why:
            print(f"# {w}")
    if args.check:
        with open(args.check, encoding="utf-8", errors="replace") as fh:
            have = [l.strip() for l in fh]
        missing = [l for l in lines if l not in have]
        if missing:
            print(f"work trailer: {args.check} lacks " + ("this line:" if len(missing) == 1 else "these lines:"),
                  file=sys.stderr)
            for l in missing:
                print(f"  {l}", file=sys.stderr)
            ai = [l for l in have if l.lower().startswith("co-authored-by:")]
            if ai:
                print("  it has: " + " | ".join(ai), file=sys.stderr)
            return 1
        print(f"ok: {args.check} has " + " | ".join(lines))
        return 0
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
