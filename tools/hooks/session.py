"""Codex and Claude Code lifecycle hooks for a local byte-matching session."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile

from match_guard import ROOT, git, git_text, ledger_status, match

sys.path.insert(0, str(ROOT / "tools" / "work"))
from faithfulness_lint import SOURCE_SUFFIXES, mask_code, scan_text

MATCH_COMMAND = re.compile(r"(?:^|[\s;&|])(?:work(?:\.cmd)?\s+match|[\w./\\-]*bytematch\.py)\s+"
                           r"(next|show|diff|measure|compile|refresh)\b")
PATCH_PATH = re.compile(r"^\*\*\* (?:Add|Update) File: (.+)$|^\*\*\* Move to: (.+)$", re.MULTILINE)
HUNK = re.compile(r"^@@ .* \+(\d+)(?:,(\d+))? @@", re.MULTILINE)
NATIVE_SUFFIXES = {*SOURCE_SUFFIXES, ".c", ".hxx", ".inc"}
NATIVE_CONSTRUCT = re.compile(r"\b(?:volatile|alignas|__declspec\s*\(\s*align)\b|^\s*#\s*pragma\b")
JOURNAL_TEMPLATE = "# Byte matching\n\nFunction and ARTIST address\n\nEvidence and owning helper/type\n\nAttempts and remaining byte difference\n\nNext check\n"


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        json.dump(data, output)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def notes(path):
    if not path.is_file():
        return ""
    with path.open(encoding="utf-8", errors="replace") as stream:
        text = stream.read(4000)
    return text.strip() if text != JOURNAL_TEMPLATE else ""


def edited_paths(event):
    args = event.get("tool_input", {})
    if event.get("tool_name") == "apply_patch":
        return [path or moved for path, moved in PATCH_PATH.findall(args.get("command", ""))]
    return [args["file_path"]] if args.get("file_path") else []


def comparison_excerpt(response):
    if isinstance(response, dict):
        response = response.get("stdout", "")
    if not isinstance(response, str):
        return ""
    report = [line.strip()[:240] for line in response.splitlines()
              if line.lstrip().startswith(("ours: ", "ARTIST ", "wrong calls: ", "wrong constants: ", "~ "))]
    return "\n".join(report[:5])


def fidelity_warnings(tree, cwd, paths):
    warnings = []
    for name in dict.fromkeys(paths):
        path = (cwd / name).resolve()
        if not path.is_relative_to(tree) or not path.is_file() or path.suffix.lower() not in NATIVE_SUFFIXES:
            continue
        rel = path.relative_to(tree)
        if rel.parts[0] != "src" or "pc" in rel.as_posix().casefold().split("/"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        diff = git_text(tree, "diff", "--no-ext-diff", "--no-textconv", "--no-color", "-U0", "HEAD", "--", rel.as_posix())
        if diff:
            added = {line for start, count in HUNK.findall(diff)
                     for line in range(int(start), int(start) + int(count or "1"))}
        elif git(tree, "cat-file", "-e", f"HEAD:{rel.as_posix()}", check=False).returncode:
            added = set(range(1, len(text.splitlines()) + 1))
        else:
            continue
        hits = {(item.line, item.category) for item in scan_text(rel.as_posix(), text) if item.line in added}
        for line, code in enumerate(mask_code(text).splitlines(), 1):
            if line in added and NATIVE_CONSTRUCT.search(code):
                hits.add((line, "verify alignment, qualifier or compiler directive"))
        warnings.extend(f"{rel.as_posix()}:{line} {reason}" for line, reason in sorted(hits))
    return warnings


def handle(tree, event):
    session_id = event.get("session_id", "")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", session_id):
        return ""
    journal = ROOT / "scratch" / "byte-match" / f"{session_id}.md"
    state_path = journal.with_suffix(".json")
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
    stage = event["hook_event_name"]
    if stage == "PostToolUse":
        if event.get("tool_name") == "Bash":
            command = MATCH_COMMAND.search(event.get("tool_input", {}).get("command", ""))
            if not command:
                return ""
            if command[1] in {"show", "diff"}:
                excerpt = comparison_excerpt(event.get("tool_response"))
                if excerpt:
                    state["last_comparison"] = excerpt
                    atomic_json(state_path, state)
            if not journal.exists():
                journal.parent.mkdir(parents=True, exist_ok=True)
                with journal.open("x", encoding="utf-8") as output:
                    output.write(JOURNAL_TEMPLATE)
                return (f"Byte-match checkpoint: {journal}. Keep the function, ARTIST evidence, attempts, "
                        "remaining difference and next check here while iterating.")
            return ""
        cwd = Path(event.get("cwd") or ROOT)
        warnings = fidelity_warnings(tree, cwd, edited_paths(event))
        if warnings:
            return "Byte-match source review flags. Confirm these against the original evidence.\n" + "\n".join(warnings[:12])
        return ""
    if not journal.exists():
        return ""
    if stage == "PreCompact":
        state["snapshot"] = {
            "native_head": git_text(tree, "rev-parse", "HEAD"),
            "native_status": git_text(tree, "status", "--short", "--untracked-files=normal").splitlines()[:14],
            "notes": notes(journal),
            "last_comparison": state.get("last_comparison", ""),
        }
        atomic_json(state_path, state)
    elif stage == "Stop":
        warning = ledger_status(tree)
        if not warning or warning == state.get("ledger_warning"):
            return ""
        state["ledger_warning"] = warning
        atomic_json(state_path, state)
        return warning
    elif stage != "SessionStart" or event.get("source") not in {"compact", "resume"}:
        return ""
    snapshot = state.get("snapshot", {})
    if not snapshot:
        return ""
    status = "\n".join(snapshot["native_status"]) or "clean"
    sections = [f"Byte-match checkpoint from {journal}", f"Native HEAD {snapshot['native_head']}",
                f"Native working tree before compaction\n{status}"]
    if snapshot.get("last_comparison"):
        sections.append("Last observed comparison\n" + snapshot["last_comparison"])
    sections.append(snapshot["notes"] or "The session journal has no function or evidence notes yet.")
    return "\n".join(sections)


def main(client):
    if os.environ.get("BP_BYTE_MATCH_HOOKS") != "1":
        return
    try:
        event = json.load(sys.stdin)
        tree = match.find_tree()
        if not (tree / "tools" / "build_x360.py").is_file():
            return
        message = handle(tree, event)
        stage = event["hook_event_name"]
        if not message or (client == "codex" and stage == "PreCompact"):
            return
        if client == "claude" and stage == "PreCompact":
            print(message)
        elif stage == "Stop":
            print(json.dumps({"systemMessage": message}))
        else:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": stage, "additionalContext": message}}))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"byte-match session hook: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1])
