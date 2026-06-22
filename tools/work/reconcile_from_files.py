#!/usr/bin/env python3
"""
Reconcile progress/status.json from the implementation files that actually exist
in b5-decomp/src.

This is deliberately local and conservative:
  * no work-server calls;
  * no dependence on ledger.sqlite as an authority;
  * `done` requires implementation evidence, or explicit corrected-path evidence;
  * explicit partial/skeleton/blocking notes win over "a file exists".

Default mode is a dry run. Use --apply to write progress/status.json.

Compatibility notes:
  work.py imports committed_files(), reconcile(), and verify() from this module.
  The `con` argument is accepted for that old call shape, but this script treats
  status.json as the artifact to reconcile. The local SQLite cache will re-import
  status.json on the next normal work command through work.py's cache-coherence path.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
B5 = ROOT / "b5-decomp"
STATUS_JSON = ROOT / "progress" / "status.json"
TU_INDEX_JSON = ROOT / "progress" / "tu_index.json"

SOURCE_SUFFIXES = (".cpp", ".h", ".hpp", ".inl")
TRAP_MARKERS = ("__debugbreak", "__builtin_trap", "CGS_ASSERT(false)", "CGS_ASSERT( false )")

# Narrow on purpose. "placeholder" and "incomplete" often document honest type
# boundaries in otherwise finished reconstructions.
INCOMPLETE_FILE_RE = re.compile(
    r"TODO:\s*Implement|"
    r"committed file is partial|"
    r"needs finishing|"
    r"skeleton, not faithful|"
    r"All function implementations are guessed|"
    r"\bnot implemented\b|"
    r"\bunimplemented\b",
    re.I,
)

BAD_DONE_NOTE_RE = re.compile(
    r"committed file is partial|"
    r"needs finishing|"
    r"skeleton, not faithful|"
    r"\bBLOCKED on\b|"
    r"\bUnblock when\b",
    re.I,
)

BLOCKED_NOTE_RE = re.compile(r"\bBLOCKED on\b|\bUnblock when\b", re.I)
CORRECTED_PATH_RE = re.compile(r"\b(?:corrected|Landed at corrected)\s+path\s+([^\s,)]+)", re.I)


def normalize_path(path: str) -> str:
    p = PurePosixPath(path.replace("\\", "/"))
    parts: list[str] = []
    for part in p.parts:
        if not part or part == ".":
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)


def stem_key(path: str) -> str:
    base, _ = os.path.splitext(normalize_path(path))
    return base.lower()


def _git_text(args: list[str]) -> str:
    return subprocess.run(
        ["git", "-C", str(B5)] + args,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout


def committed_files() -> list[str]:
    """Tracked source-like files under b5-decomp/src, relative to workflow root."""
    return [
        "b5-decomp/" + line.replace("\\", "/")
        for line in _git_text(["ls-files", "src"]).splitlines()
        if line.endswith(SOURCE_SUFFIXES)
    ]


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def source_path(rel_root_path: str) -> Path:
    if not rel_root_path.startswith("b5-decomp/"):
        raise ValueError(f"not a b5-decomp-relative path: {rel_root_path}")
    return ROOT / rel_root_path.replace("/", os.sep)


def read_source(rel_root_path: str) -> str:
    return source_path(rel_root_path).read_text(encoding="utf-8", errors="ignore")


def strip_comment_lines(text: str) -> str:
    lines = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue
        lines.append(raw)
    return "\n".join(lines)


def build_file_index(files: Iterable[str]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for path in files:
        index.setdefault(stem_key(path), []).append(path)
    return index


def build_code_text_by_file(files: Iterable[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in files:
        full = source_path(path)
        if full.exists():
            out[path] = strip_comment_lines(read_source(path))
    return out


def resolve_files(tu_id: str, file_index: dict[str, list[str]]) -> list[str]:
    return list(dict.fromkeys(file_index.get(stem_key("b5-decomp/src/" + tu_id), [])))


def resolve_note_files(notes: str, file_index: dict[str, list[str]]) -> list[str]:
    files: list[str] = []
    for match in CORRECTED_PATH_RE.finditer(notes):
        noted = match.group(1).strip().strip(".")
        candidates = [noted]
        if not noted.startswith("b5-decomp/"):
            candidates.append("b5-decomp/src/" + noted)
        for candidate in candidates:
            files.extend(file_index.get(stem_key(candidate), []))
    return list(dict.fromkeys(files))


def is_real_reconstruction(text: str) -> bool:
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("//") or line.startswith("/*") or line.startswith("*"):
            continue
        if line in ("{", "}", "};"):
            continue
        if line.startswith("#") or line.startswith("namespace "):
            continue
        if any(marker in line for marker in TRAP_MARKERS):
            continue
        return True
    return False


def classify_files(files: list[str]) -> str:
    texts = [read_source(path) for path in files if source_path(path).exists()]
    if not texts:
        return "none"
    if not any(is_real_reconstruction(text) for text in texts):
        return "skeleton"
    if any(INCOMPLETE_FILE_RE.search(text) for text in texts):
        return "partial"
    return "done"


BODY_SUFFIX = (
    r"\s*\([^;{}]*\)\s*"
    r"(?:const\s*)?"
    r"(?:volatile\s*)?"
    r"(?:noexcept(?:\s*\([^)]*\))?\s*)?"
    r"(?:override\s*)?"
    r"(?:final\s*)?"
    r"(?:->\s*[^{};]+)?"
    r"(?::\s*[^{};]*)?"
    r"\{"
)


def definition_patterns(function_name: str, allow_method_only: bool = True) -> list[re.Pattern[str]]:
    if "`" in function_name:
        return []

    name = function_name.split("(", 1)[0]
    if "::" not in name:
        return [re.compile(r"\b" + re.escape(name) + BODY_SUFFIX, re.S)]

    parts = name.split("::")
    method = parts[-1]
    owner = parts[-2]
    full = r"\s*::\s*".join(re.escape(part) for part in parts)
    owner_method = re.escape(owner) + r"\s*::\s*" + re.escape(method)
    patterns = [
        re.compile(full + BODY_SUFFIX, re.S),
        re.compile(owner_method + BODY_SUFFIX, re.S),
    ]
    if allow_method_only:
        method_only = r"\b" + re.escape(method)
        patterns.append(re.compile(method_only + BODY_SUFFIX, re.S))
    return patterns


def function_definition_files(
    function_name: str,
    code_by_file: dict[str, str],
    allow_method_only: bool = True,
) -> list[str]:
    patterns = definition_patterns(function_name, allow_method_only=allow_method_only)
    if not patterns:
        return []
    for path, code in code_by_file.items():
        if any(pattern.search(code) for pattern in patterns):
            return [path]
    return []


def find_definition_files(
    functions: list[str],
    code_by_file: dict[str, str],
    allow_method_only: bool = True,
) -> list[str]:
    matches: list[str] = []
    for function_name in functions:
        matches.extend(function_definition_files(function_name, code_by_file, allow_method_only=allow_method_only))
    return list(dict.fromkeys(matches))


def all_non_thunk_functions_have_bodies(
    functions: list[str],
    code_by_file: dict[str, str],
    allow_method_only: bool = True,
) -> bool:
    required = [fn for fn in functions if "`" not in fn]
    if not required:
        return True
    return all(function_definition_files(fn, code_by_file, allow_method_only=allow_method_only) for fn in required)


def function_definition_files_split(
    function_name: str,
    local_code_by_file: dict[str, str],
    code_by_file: dict[str, str],
) -> list[str]:
    return (
        function_definition_files(function_name, local_code_by_file, allow_method_only=True)
        or function_definition_files(function_name, code_by_file, allow_method_only=False)
    )


def all_non_thunk_functions_have_split_bodies(
    functions: list[str],
    local_code_by_file: dict[str, str],
    code_by_file: dict[str, str],
) -> bool:
    required = [fn for fn in functions if "`" not in fn]
    if not required:
        return True
    return all(function_definition_files_split(fn, local_code_by_file, code_by_file) for fn in required)


def find_split_definition_files(
    functions: list[str],
    local_code_by_file: dict[str, str],
    code_by_file: dict[str, str],
) -> list[str]:
    matches: list[str] = []
    for function_name in functions:
        matches.extend(function_definition_files_split(function_name, local_code_by_file, code_by_file))
    return list(dict.fromkeys(matches))


def target_for_tu(
    tu_id: str,
    tu_meta: dict,
    current_entry: dict,
    file_index: dict[str, list[str]],
    code_by_file: dict[str, str],
) -> tuple[str, str | None, list[str]]:
    current_status = current_entry.get("status", "todo")
    current_notes = str(current_entry.get("notes", ""))

    if current_status == "blocked":
        return "blocked", current_notes or None, []

    if current_status in ("done", "in_progress", "compiled") and BAD_DONE_NOTE_RE.search(current_notes):
        target = "blocked" if BLOCKED_NOTE_RE.search(current_notes) else "in_progress"
        return target, current_notes, []

    if tu_id.startswith("class:"):
        return current_status, current_notes or None, []

    functions = list(tu_meta.get("functions") or [])
    note_files = resolve_note_files(current_notes, file_index)
    if current_status == "done" and note_files and functions:
        local_code_by_file = {path: code_by_file[path] for path in note_files if path in code_by_file}
        if classify_files(note_files) == "done" and all_non_thunk_functions_have_bodies(
            functions,
            local_code_by_file,
            allow_method_only=True,
        ):
            return "done", current_notes or None, find_definition_files(
                functions,
                local_code_by_file,
                allow_method_only=True,
            )

    files = resolve_files(tu_id, file_index)
    kind = classify_files(files)

    if kind == "done":
        if tu_id.lower().endswith(".cpp") and not any(path.lower().endswith(".cpp") for path in files):
            local_code_by_file = {path: code_by_file[path] for path in files if path in code_by_file}
            if all_non_thunk_functions_have_bodies(functions, local_code_by_file, allow_method_only=True):
                return "done", current_notes or None, find_definition_files(functions, local_code_by_file, allow_method_only=True)
            if current_status == "done" and all_non_thunk_functions_have_split_bodies(
                functions,
                local_code_by_file,
                code_by_file,
            ):
                return "done", current_notes or None, find_split_definition_files(
                    functions,
                    local_code_by_file,
                    code_by_file,
                )
            return "todo", None, files
        return "done", current_notes or None, files
    if kind == "partial":
        return "in_progress", current_notes or "local implementation reconcile: file is partial/incomplete; not done", files
    if kind == "skeleton":
        return "todo", None, files

    # Corrected-path or misattributed TUs can be implemented under a different
    # file. Preserve already-reviewed work only when every non-thunk function has
    # definition evidence somewhere in tracked source.
    if current_status == "done" and functions:
        definitions = find_definition_files(functions, code_by_file, allow_method_only=False)
        non_thunk_count = len([fn for fn in functions if "`" not in fn])
        if non_thunk_count and all_non_thunk_functions_have_bodies(functions, code_by_file, allow_method_only=False):
            return "done", current_notes or None, definitions

    return "todo", None, []


def set_functions(func_status: dict, functions: Iterable[str], status: str | None) -> None:
    for function_name in functions:
        if status is None:
            func_status.pop(function_name, None)
        else:
            entry = func_status.setdefault(function_name, {})
            entry["status"] = status


def count_statuses(entries: dict[str, dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries.values():
        status = entry.get("status", "todo")
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def build_reconciled_status(
    status: dict,
    tu_index: dict,
    tracked: Iterable[str],
    no_demote: bool = False,
) -> tuple[dict, list[tuple[str, str, str, str | None]], dict[str, list[str]]]:
    current_tu = status.setdefault("tu", {})
    current_func = status.setdefault("func", {})

    files = list(tracked)
    file_index = build_file_index(files)
    code_by_file = build_code_text_by_file(files)

    new_tu: dict[str, dict] = {}
    new_func = dict(current_func)
    changes: list[tuple[str, str, str, str | None]] = []
    evidence: dict[str, list[str]] = {}

    all_tus = sorted(set(tu_index) | set(current_tu))
    for tu_id in all_tus:
        tu_meta = tu_index.get(tu_id, {})
        current_entry = current_tu.get(tu_id, {})
        old_status = current_entry.get("status", "todo")
        target, notes, files_for_tu = target_for_tu(tu_id, tu_meta, current_entry, file_index, code_by_file)

        if no_demote and status_rank(target) < status_rank(old_status):
            target = old_status
            notes = current_entry.get("notes")
            files_for_tu = []

        functions = list(tu_meta.get("functions") or [])
        if target == "todo":
            set_functions(new_func, functions, None)
            if tu_id in current_tu:
                changes.append((tu_id, old_status, target, notes))
            continue

        entry = {"status": target}
        if notes:
            entry["notes"] = notes
        new_tu[tu_id] = entry
        evidence[tu_id] = files_for_tu

        if target == "done":
            set_functions(new_func, functions, "reviewed")
        elif target in ("in_progress", "blocked") and old_status == "done":
            set_functions(new_func, functions, "recovered")

        if old_status != target or current_entry.get("notes") != entry.get("notes"):
            changes.append((tu_id, old_status, target, notes))

    return {"func": dict(sorted(new_func.items())), "tu": dict(sorted(new_tu.items()))}, changes, evidence


def status_rank(status: str) -> int:
    return {"todo": 0, "in_progress": 1, "compiled": 2, "done": 3, "blocked": 3}.get(status, 0)


def print_report(old_status: dict, new_status: dict, changes: list, evidence: dict[str, list[str]], apply: bool) -> None:
    print("TU status counts:")
    print(f"  before: {count_statuses(old_status.get('tu', {}))}")
    print(f"  after:  {count_statuses(new_status.get('tu', {}))}")
    print(f"changes: {len(changes)}")
    for tu_id, old, new, notes in changes[:80]:
        suffix = ""
        if evidence.get(tu_id):
            short = [path.removeprefix("b5-decomp/src/") for path in evidence[tu_id][:2]]
            suffix = "  [" + ", ".join(short) + "]"
        elif notes:
            suffix = "  [note]"
        print(f"  {old:11s} -> {new:11s}  {tu_id}{suffix}")
    if len(changes) > 80:
        print(f"  ... +{len(changes) - 80} more")
    if not apply:
        print("\n(dry run; use --apply to write progress/status.json)")


def reconcile(con=None, tracked=None, apply=False, no_demote=False):
    """Compatibility entry point used by work.py."""
    old_status = load_json(STATUS_JSON)
    tu_index = load_json(TU_INDEX_JSON)
    tracked = list(tracked) if tracked is not None else committed_files()
    new_status, changes, evidence = build_reconciled_status(old_status, tu_index, tracked, no_demote=no_demote)
    print_report(old_status, new_status, changes, evidence, apply)

    if apply:
        with STATUS_JSON.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(new_status, f, indent=1, sort_keys=True)
            f.write("\n")
        print(f"\nwrote {STATUS_JSON.relative_to(ROOT)}")
    return new_status, changes


def verify(con=None, tracked=None):
    status = load_json(STATUS_JSON)
    tu_index = load_json(TU_INDEX_JSON)
    tracked = list(tracked) if tracked is not None else committed_files()
    file_index = build_file_index(tracked)
    code_by_file = build_code_text_by_file(tracked)

    bad_notes = []
    no_evidence = []
    corrected_path = []
    class_done = 0
    for tu_id, entry in status.get("tu", {}).items():
        if entry.get("status") != "done":
            continue
        if BAD_DONE_NOTE_RE.search(str(entry.get("notes", ""))):
            bad_notes.append(tu_id)
        if tu_id.startswith("class:"):
            class_done += 1
            continue
        if resolve_files(tu_id, file_index):
            continue
        funcs = list(tu_index.get(tu_id, {}).get("functions") or [])
        definitions = find_definition_files(funcs, code_by_file)
        non_thunk_count = len([fn for fn in funcs if "`" not in fn])
        if non_thunk_count and len(definitions) >= non_thunk_count:
            corrected_path.append(tu_id)
        else:
            no_evidence.append(tu_id)

    print("\n=== verification ===")
    print(f"  done rows with explicit bad notes: {len(bad_notes)}  {'OK' if not bad_notes else bad_notes[:5]}")
    print(f"  done file-TUs without implementation evidence: {len(no_evidence)}  {'OK' if not no_evidence else no_evidence[:5]}")
    print(f"  done rows preserved by corrected-path symbol evidence: {len(corrected_path)}")
    print(f"  class-derived done rows preserved: {class_done}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write progress/status.json")
    parser.add_argument("--no-demote", action="store_true", help="suppress status demotions")
    args = parser.parse_args()
    tracked = committed_files()
    reconcile(None, tracked, args.apply, args.no_demote)
    if args.apply:
        verify(None, tracked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
