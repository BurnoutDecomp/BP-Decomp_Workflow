#!/usr/bin/env python3
"""
Reconcile progress/status.json from the implementation files in the exact
b5-decomp commit recorded by this workflow checkout, plus external/vendor coverage
represented by the TU index.

This is deliberately local and conservative:
  * no work-server calls;
  * no dependence on ledger.sqlite as an authority;
  * `done` requires implementation evidence, or explicit corrected-path evidence;
  * source evidence wins over stale historical notes/status rows;
  * vendor/runtime buckets are explicitly blocked because their bodies come from
    platform libraries or checked-in vendor source rather than reconstruction.

Default mode is a dry run and preserves existing non-todo status entries. Use
--apply to write progress/status.json. Use --allow-demote only when you want
file evidence to remove or demote existing status rows.

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
CLASS_HOMES_JSON = ROOT / "progress" / "class_homes.json"

SOURCE_SUFFIXES = (".cpp", ".h", ".hpp", ".inl")
TRAP_MARKERS = ("__debugbreak", "__builtin_trap", "CGS_ASSERT(false)", "CGS_ASSERT( false )")

# Narrow on purpose. "placeholder" and "incomplete" often document honest type
# boundaries in otherwise finished reconstructions.
#
# The trailing group are INVENTION-ACCOMMODATION markers: a file that carries a
# home-grown-format signature scan ("LocateMovieRoot"), reads "our converted"
# bundle bytes, or documents a "converter accommodation" is not a faithful
# decompile -- it is bent around invented data, so a `done` row is wrong. These
# strings are specific enough that they only occur in genuinely-unfaithful code;
# the mechanical gate is tools/work/faithfulness_lint.py (see `work faithfulness`).
INCOMPLETE_FILE_RE = re.compile(
    r"TODO:\s*Implement|"
    r"committed file is partial|"
    r"needs finishing|"
    r"skeleton, not faithful|"
    r"All function implementations are guessed|"
    r"\bnot implemented\b|"
    r"\bunimplemented\b|"
    r"\bLocateMovieRoot\w*|"
    r"our\s+converted|"
    r"converter[-\s]format\s+accommodation|"
    r"converter\s+accommodation",
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
KNOWN_PARTIAL_TUS = {
    "GameSource/GameState/BrnGameStateSharedIO.h",
}

VENDOR_BLOCKED_NOTE = (
    "Vendor/runtime code; supplied by platform libraries or checked-in vendor source, "
    "so no game-source reconstruction is required."
)

_COMMITTED_REF: str | None = None
_SOURCE_TEXT_CACHE: dict[str, str] = {}


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


def recorded_b5_ref() -> str:
    """The gitlink commit the workflow/server imports, independent of B5's checkout."""
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", ":b5-decomp"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def committed_files() -> list[str]:
    """Source-like blobs in the recorded B5 commit, relative to workflow root."""
    global _COMMITTED_REF, _SOURCE_TEXT_CACHE
    _COMMITTED_REF = recorded_b5_ref()
    _SOURCE_TEXT_CACHE = {}
    return [
        "b5-decomp/" + line.replace("\\", "/")
        for line in _git_text(
            ["ls-tree", "-r", "--name-only", _COMMITTED_REF, "--", "src", "vendor"]
        ).splitlines()
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
    if rel_root_path in _SOURCE_TEXT_CACHE:
        return _SOURCE_TEXT_CACHE[rel_root_path]
    if _COMMITTED_REF:
        rel_b5 = rel_root_path.removeprefix("b5-decomp/")
        return _git_text(["show", f"{_COMMITTED_REF}:{rel_b5}"])
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
    global _SOURCE_TEXT_CACHE
    paths = list(files)
    if _COMMITTED_REF:
        specs = [f"{_COMMITTED_REF}:{path.removeprefix('b5-decomp/')}" for path in paths]
        result = subprocess.run(
            ["git", "-C", str(B5), "cat-file", "--batch"],
            input=("\n".join(specs) + "\n").encode("utf-8"),
            check=True,
            capture_output=True,
        )
        raw = result.stdout
        cursor = 0
        loaded: dict[str, str] = {}
        for path in paths:
            end = raw.index(b"\n", cursor)
            header = raw[cursor:end].decode("utf-8", errors="replace")
            cursor = end + 1
            parts = header.rsplit(" ", 2)
            if len(parts) != 3 or parts[1] != "blob":
                raise RuntimeError(f"unable to read committed source {path}: {header}")
            size = int(parts[2])
            data = raw[cursor:cursor + size]
            cursor += size + 1  # cat-file's record separator newline
            loaded[path] = data.decode("utf-8", errors="ignore")
        _SOURCE_TEXT_CACHE = loaded

    out: dict[str, str] = {}
    for path in paths:
        try:
            out[path] = strip_comment_lines(read_source(path))
        except (OSError, subprocess.CalledProcessError):
            continue
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


def resolve_mapped_files(
    tu_id: str,
    mapped_homes: dict[str, str],
    file_index: dict[str, list[str]],
) -> list[str]:
    """Resolve a pseudo-TU's derived home and its same-stem source/header siblings."""
    home = mapped_homes.get(tu_id)
    if not home:
        return []
    candidates = [home]
    if not home.startswith("b5-decomp/"):
        candidates.append("b5-decomp/src/" + home)
    files: list[str] = []
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

QUALIFIED_METHOD_DEF_RE = re.compile(
    r"((?:[A-Za-z_]\w*\s*::\s*)+)(~?[A-Za-z_]\w*)\s*\([^;{}]*\)\s*[^;{}]*\{"
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


def function_definition_keys(function_name: str) -> tuple[str, str] | None:
    """Return full and short owner/method keys for an ordinary C++ method."""
    if "`" in function_name:
        return None
    name = function_name.split("(", 1)[0]
    parts = name.split("::")
    if len(parts) < 2 or not re.fullmatch(r"~?[A-Za-z_]\w*", parts[-1]):
        return None
    full = "::".join(parts)
    short = "::".join(parts[-2:])
    return full, short


def build_definition_index(code_by_file: dict[str, str]) -> dict[str, set[str]]:
    """Index ordinary qualified method definitions once for full-TU coverage checks."""
    index: dict[str, set[str]] = {}
    for path, code in code_by_file.items():
        for match in QUALIFIED_METHOD_DEF_RE.finditer(code):
            owner = re.sub(r"\s+", "", match.group(1)).removesuffix("::")
            method = match.group(2)
            full = f"{owner}::{method}"
            short = f"{owner.split('::')[-1]}::{method}"
            index.setdefault(full, set()).add(path)
            index.setdefault(short, set()).add(path)
    return index


def indexed_function_definition_files(
    function_name: str,
    definition_index: dict[str, set[str]],
    fallback_code_by_file: dict[str, str],
) -> list[str]:
    keys = function_definition_keys(function_name)
    if keys:
        full, short = keys
        matches = definition_index.get(full) or definition_index.get(short)
        if matches:
            return sorted(matches)
    # Operators, templates, and unusual demangler spellings take the slower exact
    # regex path. They are a small minority after the ordinary methods are indexed.
    return function_definition_files(
        function_name,
        fallback_code_by_file,
        allow_method_only=False,
    )


def all_non_thunk_functions_have_indexed_bodies(
    functions: list[str],
    definition_index: dict[str, set[str]],
    fallback_code_by_file: dict[str, str],
) -> bool:
    required = [fn for fn in functions if "`" not in fn]
    if not required:
        return True
    return all(
        indexed_function_definition_files(fn, definition_index, fallback_code_by_file)
        for fn in required
    )


def all_non_thunk_functions_are_indexed(
    functions: list[str],
    definition_index: dict[str, set[str]],
) -> bool:
    required = [fn for fn in functions if "`" not in fn]
    if not required:
        return True
    for function_name in required:
        keys = function_definition_keys(function_name)
        if not keys or not (definition_index.get(keys[0]) or definition_index.get(keys[1])):
            return False
    return True


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
    mapped_homes: dict[str, str] | None = None,
    global_code_by_file: dict[str, str] | None = None,
    definition_index: dict[str, set[str]] | None = None,
) -> tuple[str, str | None, list[str]]:
    current_status = current_entry.get("status", "todo")
    current_notes = str(current_entry.get("notes", ""))
    mapped_homes = mapped_homes or {}
    global_code_by_file = global_code_by_file or code_by_file
    definition_index = definition_index or build_definition_index(code_by_file)
    source = tu_meta.get("source")
    functions = list(tu_meta.get("functions") or [])

    # These buckets intentionally have no reconstructed home under src/. Keeping
    # them explicit makes status.json/server inventory match the full TU index.
    if source == "vendor" or tu_id.startswith("vendor:"):
        return "blocked", current_notes or VENDOR_BLOCKED_NOTE, []

    if tu_id in KNOWN_PARTIAL_TUS:
        return "todo", None, []

    # Class/module TUs have no path-shaped id. A resolved, non-partial home is the
    # same file-level evidence used for path-shaped TUs. Without a home, accept only
    # complete qualified-definition evidence from the source index.
    if source == "class" or tu_id.startswith("class:"):
        home_files = resolve_mapped_files(tu_id, mapped_homes, file_index)
        if home_files and classify_files(home_files) == "done":
            return "done", current_notes or None, home_files
        if functions and all_non_thunk_functions_are_indexed(functions, definition_index):
            return "done", current_notes or None, home_files
        return "todo", None, home_files

    if source == "module" or tu_id.startswith("module:"):
        if functions and all_non_thunk_functions_have_indexed_bodies(
            functions,
            definition_index,
            global_code_by_file,
        ):
            return "done", current_notes or None, []
        return "todo", None, []

    note_files = resolve_note_files(current_notes, file_index)
    if note_files and functions:
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
        local_code_by_file = {path: code_by_file[path] for path in files if path in code_by_file}
        if tu_id.lower().endswith(".cpp") and not any(path.lower().endswith(".cpp") for path in files):
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
        return "todo", None, files
    if kind == "skeleton":
        return "todo", None, files

    # Corrected-path or misattributed TUs can be implemented under a different
    # file. Every non-thunk function must have exact qualified definition evidence.
    if functions:
        definitions: list[str] = []
        for function_name in functions:
            definitions.extend(
                indexed_function_definition_files(function_name, definition_index, global_code_by_file)
            )
        non_thunk_count = len([fn for fn in functions if "`" not in fn])
        if non_thunk_count and all_non_thunk_functions_have_indexed_bodies(
            functions,
            definition_index,
            global_code_by_file,
        ):
            return "done", current_notes or None, [
                path for path in definitions if path in code_by_file
            ]

    return "todo", None, []


def set_functions(
    func_status: dict,
    functions: Iterable[str],
    status: str | None,
    no_demote: bool = False,
) -> None:
    for function_name in functions:
        old_entry = func_status.get(function_name)
        old_status = old_entry.get("status", "todo") if isinstance(old_entry, dict) else "todo"
        if status is None:
            if no_demote and old_entry is not None and old_status != "todo":
                continue
            func_status.pop(function_name, None)
        else:
            if no_demote and status_rank(status) < status_rank(old_status):
                continue
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
    no_demote: bool = True,
    mapped_homes: dict[str, str] | None = None,
) -> tuple[dict, list[tuple[str, str, str, str | None]], dict[str, list[str]]]:
    current_tu = status.setdefault("tu", {})
    current_func = status.setdefault("func", {})

    files = list(tracked)
    file_index = build_file_index(files)
    code_by_file = build_code_text_by_file(files)
    # Cross-path evidence searches used to loop over every tracked file for every
    # function. A single corpus preserves the same regex semantics while avoiding
    # millions of Python-level iterations during a full class-TU reconciliation.
    global_code_by_file = {
        "<all tracked source>": "\n;\n".join(code_by_file.values())
    }
    definition_index = build_definition_index(code_by_file)

    new_tu: dict[str, dict] = {}
    new_func = dict(current_func)
    changes: list[tuple[str, str, str, str | None]] = []
    evidence: dict[str, list[str]] = {}

    # Promote-only retains durable rows that may belong to an older index. The
    # files-authoritative mode deliberately projects exactly the current index.
    all_tus = sorted(set(tu_index) | (set(current_tu) if no_demote else set()))
    for tu_id in all_tus:
        tu_meta = tu_index.get(tu_id, {})
        current_entry = current_tu.get(tu_id, {})
        old_status = current_entry.get("status", "todo")
        target, notes, files_for_tu = target_for_tu(
            tu_id,
            tu_meta,
            current_entry,
            file_index,
            code_by_file,
            mapped_homes=mapped_homes,
            global_code_by_file=global_code_by_file,
            definition_index=definition_index,
        )

        if no_demote and transition_is_demotion(old_status, target):
            target = old_status
            notes = current_entry.get("notes")
            files_for_tu = []

        functions = list(tu_meta.get("functions") or [])
        if target == "todo":
            set_functions(new_func, functions, None, no_demote=no_demote)
            if tu_id in current_tu:
                changes.append((tu_id, old_status, target, notes))
            continue

        entry = {"status": target}
        if notes:
            entry["notes"] = notes
        new_tu[tu_id] = entry
        evidence[tu_id] = files_for_tu

        if target == "done":
            set_functions(new_func, functions, "reviewed", no_demote=no_demote)
        elif target in ("in_progress", "blocked") and old_status == "done":
            set_functions(new_func, functions, "recovered", no_demote=no_demote)

        if old_status != target or current_entry.get("notes") != entry.get("notes"):
            changes.append((tu_id, old_status, target, notes))

    return {"func": dict(sorted(new_func.items())), "tu": dict(sorted(new_tu.items()))}, changes, evidence


def status_rank(status: str) -> int:
    return {
        "todo": 0,
        "in_progress": 1,
        "recovered": 1,
        "compiled": 2,
        "compiles": 2,
        "done": 3,
        "reviewed": 3,
        "blocked": 3,
    }.get(status, 0)


def transition_is_demotion(old_status: str, target: str) -> bool:
    """Whether promote-only reconciliation must retain the existing state.

    ``blocked`` and ``done`` used to share a numeric rank, which accidentally
    allowed stale notes to turn reviewed work into blocked work. File evidence may
    promote blocked -> done, but the reverse is never a promote-only transition.
    """
    if old_status == "done":
        return target != "done"
    if old_status == "blocked":
        return target not in ("blocked", "done")
    return status_rank(target) < status_rank(old_status)


def print_report(old_status: dict, new_status: dict, changes: list, evidence: dict[str, list[str]], apply: bool) -> None:
    if _COMMITTED_REF:
        print(f"b5 source ref: {_COMMITTED_REF}")
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


def reconcile(con=None, tracked=None, apply=False, no_demote=True):
    """Compatibility entry point used by work.py."""
    old_status = load_json(STATUS_JSON)
    tu_index = load_json(TU_INDEX_JSON)
    mapped_homes = load_json(CLASS_HOMES_JSON) if CLASS_HOMES_JSON.exists() else {}
    tracked = list(tracked) if tracked is not None else committed_files()
    new_status, changes, evidence = build_reconciled_status(
        old_status,
        tu_index,
        tracked,
        no_demote=no_demote,
        mapped_homes=mapped_homes,
    )
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
    mapped_homes = load_json(CLASS_HOMES_JSON) if CLASS_HOMES_JSON.exists() else {}
    tracked = list(tracked) if tracked is not None else committed_files()
    file_index = build_file_index(tracked)
    code_by_file = build_code_text_by_file(tracked)
    global_code_by_file = {
        "<all tracked source>": "\n;\n".join(code_by_file.values())
    }
    definition_index = build_definition_index(code_by_file)

    bad_notes = []
    no_evidence = []
    corrected_path = []
    class_done = 0
    for tu_id, entry in status.get("tu", {}).items():
        if entry.get("status") != "done":
            continue
        target, _, evidence = target_for_tu(
            tu_id,
            tu_index.get(tu_id, {}),
            entry,
            file_index,
            code_by_file,
            mapped_homes=mapped_homes,
            global_code_by_file=global_code_by_file,
            definition_index=definition_index,
        )
        if target == "done":
            if tu_id.startswith("class:"):
                class_done += 1
            elif not resolve_files(tu_id, file_index) and evidence:
                corrected_path.append(tu_id)
            continue
        if BAD_DONE_NOTE_RE.search(str(entry.get("notes", ""))):
            bad_notes.append(tu_id)
        if evidence:
            corrected_path.append(tu_id)
        else:
            no_evidence.append(tu_id)

    print("\n=== verification ===")
    print(f"  done rows with explicit bad notes: {len(bad_notes)}  {'OK' if not bad_notes else bad_notes[:5]}")
    print(f"  terminal done rows preserved without a fresh mechanical mapping: {len(no_evidence)}")
    print(f"  done rows preserved by corrected-path symbol evidence: {len(corrected_path)}")
    print(f"  class-derived done rows with implementation evidence: {class_done}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write progress/status.json")
    parser.add_argument(
        "--allow-demote",
        action="store_true",
        help="allow file evidence to demote/remove existing status entries",
    )
    parser.add_argument("--no-demote", dest="allow_demote", action="store_false", help=argparse.SUPPRESS)
    args = parser.parse_args()
    tracked = committed_files()
    reconcile(None, tracked, args.apply, no_demote=not args.allow_demote)
    if args.apply:
        verify(None, tracked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
