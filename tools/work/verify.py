#!/usr/bin/env python3
"""
Phase 3 - verification: the compile gate + the reviewer packet.

Two tiers, per STRATEGY.md (reconstruction target):
  1. compile_gate(files) - the reconstructed TU compiles against current headers
     (`cl /c`, compile-only, no whole-program link). Deterministic; runs in Python.
  2. reviewer_packet(...) - assembles the dossier + the produced code into a single
     brief for a FRESH-EYES reviewer sub-agent. The LLM review itself is performed by
     the agent/harness (Task tool, etc.), not here; `work review` records its verdict.

The gate compiles with the CANONICAL flag/include lists (tools/build/msvc_flags.txt
+ msvc_includes.txt -- the same set the shipping exe build uses, including /O2 /Gy)
and locates MSVC via tools/build/msvc_env.bat (VCVARS64 env override supported).
If no MSVC environment can be found it returns ('skip', reason) so the loop still
works on compiler-less machines.
"""
import json, os, re, shutil, subprocess, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG = os.path.join(ROOT, "progress", "verify.config.json")  # legacy; soft-read only
REVIEWS = os.path.join(ROOT, "progress", "reviews")
FLAGS_TXT = os.path.join(ROOT, "tools", "build", "msvc_flags.txt")
INCS_TXT = os.path.join(ROOT, "tools", "build", "msvc_includes.txt")
MSVC_ENV = os.path.join(ROOT, "tools", "build", "msvc_env.bat")

import dossier  # same dir


def _abs(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def _read_list(path):
    """Non-comment, non-blank lines of a canonical tools/build/*.txt list."""
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    return out


def compile_gate(files):
    """Compile-only gate. Returns (status, log) with status in pass|fail|skip."""
    if not (os.path.exists(FLAGS_TXT) and os.path.exists(INCS_TXT)):
        return "skip", "canonical flag/include lists missing under tools/build/"
    existing = [f for f in files if os.path.exists(_abs(f))]
    if not existing:
        return "skip", f"no source file(s) on disk: {files}"

    env = dict(os.environ)
    # Legacy soft-import: an old progress/verify.config.json with a valid custom
    # "vcvars" still works, via the resolver's VCVARS64 override.
    if "VCVARS64" not in env and os.path.exists(CONFIG):
        try:
            legacy = json.load(open(CONFIG, encoding="utf-8")).get("vcvars", "")
            if legacy and os.path.exists(legacy):
                env["VCVARS64"] = os.path.normpath(legacy)
        except Exception:
            pass

    objdir = tempfile.mkdtemp(prefix="workgate_")
    try:
        # Run via a temp .bat to avoid cmd.exe nested-quote mangling of paths
        # with spaces. Native backslash paths throughout.
        def win(p):
            return os.path.normpath(p)
        flags = " ".join(sum((ln.split() for ln in _read_list(FLAGS_TXT)), [])) + " /c"
        incs = " ".join(f'/I"{win(os.path.join(ROOT, d))}"' for d in _read_list(INCS_TXT))
        srcs = " ".join(f'"{win(_abs(f))}"' for f in existing)
        bat = os.path.join(objdir, "gate.bat")
        with open(bat, "w", encoding="utf-8") as fh:
            fh.write("@echo off\n")
            fh.write(f'call "{win(MSVC_ENV)}" >nul 2>&1\n')
            fh.write("if errorlevel 1 exit /b 200\n")  # 200 = toolchain absent -> skip
            fh.write(f"cl {flags} {incs} {srcs}\n")
            fh.write("exit /b %ERRORLEVEL%\n")
        p = subprocess.run(["cmd", "/c", bat], cwd=objdir, env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode == 200:
            return "skip", ("MSVC not found (tools/build/msvc_env.bat; set VCVARS64)\n"
                            + (p.stdout or ""))
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
    safe = re.sub(r'[<>:"/\\|?*]', "_", safe)
    path = os.path.join(REVIEWS, safe + ".md")

    body = dossier.assemble(con, tu_row, funcs, with_asm=False)
    parts = [
        f"# Reviewer packet — {tu}",
        "",
        "## Your task (fresh-eyes review)",
        "You did **not** write this code. Compare the **produced C++** below against the",
        "**reference dossier** (Hex-Rays pseudocode, DecFIGS dwarfdump type/declaration",
        "hints, and the original Feb-2007 source when present). Decide whether the C++ is",
        "**semantically faithful** to the source build:",
        "control flow, side effects, return values, field offsets, and call targets.",
        "Semantic fidelity is primary — flag any divergence, missing case, or wrong offset.",
        "CRITICAL QUALITY GATE: Reject (FAIL) any code that uses raw pointer arithmetic,",
        "offset-based reinterpret_casts, or helper offset read/write lambdas to access struct/class",
        "member variables. The code must reconstruct clean class/struct layouts with explicit",
        "padding (e.g., `u8 mPad0[1812]`) and access members by name. Additionally, reject any",
        "code that retains compiler optimizations (such as unrolled loops, inlined functions, strength-reduced",
        "math shifts/multiplies, or optimized branches); these must be reconstructed back to clean,",
        "logical C++ structures (for/while loops, function calls, standard operators, structured branches).",
        "As a secondary check, flag clear violations of the project naming conventions in",
        "`references/CXX_NAMING_CONVENTIONS.md` (scope/type variable prefixes, `K..._` constants,",
        "`E_` enums, PascalCase types/functions); don't fail purely on minor style.",
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
