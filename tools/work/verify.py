#!/usr/bin/env python3
"""
Phase 3 - verification: the compile gate + the reviewer packet.

Two tiers, per STRATEGY.md (reconstruction target):
  1. compile_gate(files) - the reconstructed TU compiles against current headers
     (`cl /c`, compile-only, no whole-program link). Deterministic; runs in Python.
  2. reviewer_packet(...) - assembles the dossier + the produced code into a single
     brief for a FRESH-EYES reviewer sub-agent. The LLM review itself is performed by
     the agent/harness (Task tool, etc.), not here; `work review` records its verdict.

The gate is configured by progress/verify.config.json. If the MSVC environment is
absent it returns ('skip', reason) so the loop still works.
"""
import json, os, shutil, subprocess, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG = os.path.join(ROOT, "progress", "verify.config.json")
REVIEWS = os.path.join(ROOT, "progress", "reviews")

import dossier  # same dir


def load_config():
    if not os.path.exists(CONFIG):
        return None
    return json.load(open(CONFIG, encoding="utf-8"))


def _abs(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def compile_gate(files):
    """Compile-only gate. Returns (status, log) with status in pass|fail|skip."""
    cfg = load_config()
    if not cfg:
        return "skip", "no progress/verify.config.json"
    vcvars = cfg.get("vcvars", "")
    if not vcvars or not os.path.exists(vcvars):
        return "skip", f"vcvars not found: {vcvars!r} (install/point to MSVC)"
    existing = [f for f in files if os.path.exists(_abs(f))]
    if not existing:
        return "skip", f"no source file(s) on disk: {files}"

    objdir = tempfile.mkdtemp(prefix="workgate_")
    try:
        # Run via a temp .bat to avoid cmd.exe nested-quote mangling of the
        # vcvars path (which contains spaces). Native backslash paths throughout.
        def win(p):
            return os.path.normpath(p)
        incs = " ".join(f'/I"{win(_abs(d))}"' for d in cfg.get("include_dirs", []))
        flags = " ".join(cfg.get("flags", ["/nologo", "/c", "/EHsc", "/std:c++17"]))
        srcs = " ".join(f'"{win(_abs(f))}"' for f in existing)
        bat = os.path.join(objdir, "gate.bat")
        with open(bat, "w", encoding="utf-8") as fh:
            fh.write("@echo off\n")
            fh.write(f'call "{win(vcvars)}" >nul 2>&1\n')
            fh.write(f'{cfg.get("compiler","cl")} {flags} {incs} {srcs}\n')
            fh.write("exit /b %ERRORLEVEL%\n")
        p = subprocess.run(["cmd", "/c", bat], cwd=objdir,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        status = "pass" if p.returncode == 0 else "fail"
        return status, (p.stdout or "") + (p.stderr or "")
    finally:
        shutil.rmtree(objdir, ignore_errors=True)


def _read(path):
    try:
        return open(_abs(path), encoding="utf-8", errors="replace").read()
    except Exception as e:
        return f"(could not read {path}: {e})"


def reviewer_packet(con, tu_row, funcs, files):
    """Build the fresh-eyes reviewer brief: produced code + the ground-truth dossier."""
    os.makedirs(REVIEWS, exist_ok=True)
    tu = tu_row["id"]
    safe = tu.replace("/", "__").replace(":", "_").replace("\\", "__")
    path = os.path.join(REVIEWS, safe + ".md")

    body = dossier.assemble(con, tu_row, funcs, with_asm=False)
    parts = [
        f"# Reviewer packet — {tu}",
        "",
        "## Your task (fresh-eyes review)",
        "You did **not** write this code. Compare the **produced C++** below against the",
        "**reference dossier** (Hex-Rays pseudocode, and the original Feb-2007 source when",
        "present). Decide whether the C++ is **semantically faithful** to the source build:",
        "control flow, side effects, return values, field offsets, and call targets.",
        "Ignore style. Flag any divergence, missing case, or wrong offset.",
        "",
        "Respond with: `VERDICT: pass` or `VERDICT: fail`, then a short bullet list of",
        "findings. The agent will record it via `work review <tu> --verdict <pass|fail>`.",
        "",
        "## Produced code",
    ]
    for f in files:
        parts += [f"\n### `{f}`", "```cpp", _read(f), "```"]
    parts += ["", "## Reference dossier (ground truth)", "", "```", body, "```"]

    open(path, "w", encoding="utf-8").write("\n".join(parts))
    return path
