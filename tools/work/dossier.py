#!/usr/bin/env python3
"""
Phase 2 - the dossier assembler.

Builds the full reconstruction brief for one translation unit, joining everything
an agent needs into a single document so it never has to hunt through
.ida-exports/ by hand:

  - per-function: clean signature, decompiler locals, full pseudocode, (opt) asm
  - callee signatures + whether each callee is already recovered (and where)
  - caller context
  - the ORIGINAL Feb-2007 source file, when the TU's primary_file exists in the leak
  - a pointer to relevant type headers

Used by `work show <tu> --full`. Kept separate from work.py so the assembly logic
is reusable and testable.
"""
import json, os, re
from functools import lru_cache

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
X360_EXPORTS = os.path.join(ROOT, ".ida-exports", "BURNOUT_X360_ARTIST.XEX")
FEB2007 = os.path.join(ROOT, "references", "Feb-2007", "BrnEntityModuleUnity")
RW_INCLUDE = "b5-decomp/vendor/renderware/include"

import gen_skeleton  # same dir; provides load_export + signature_from_pseudocode
load_export = gen_skeleton.load_export
sig_of = gen_skeleton.signature_from_pseudocode

MAX_SRC_LINES = 500
MAX_CALLEES = 24


# ---------------------------------------------------------------- Feb-2007 overlay
@lru_cache(maxsize=1)
def feb2007_index():
    """Map normalized path-suffix -> absolute path for every source file in the leak."""
    idx = {}
    if not os.path.isdir(FEB2007):
        return idx
    for dp, _, fs in os.walk(FEB2007):
        for f in fs:
            if f.endswith((".cpp", ".h", ".hpp", ".inl", ".c")):
                full = os.path.join(dp, f)
                rel = os.path.relpath(full, FEB2007).replace("\\", "/")
                idx[rel] = full
    return idx


def normalize_primary_file(primary_file: str) -> str | None:
    """Resolve `GameSource/Unity/../../SharedClasses/AI/X.cpp` -> `SharedClasses/AI/X.cpp`."""
    if not primary_file:
        return None
    parts = []
    for seg in primary_file.replace("\\", "/").split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
        else:
            parts.append(seg)
    return "/".join(parts)


def find_feb2007_source(primary_file: str):
    """Return (rel_path, abspath) if the original source file is in the leak."""
    norm = normalize_primary_file(primary_file)
    if not norm:
        return None
    idx = feb2007_index()
    if norm in idx:
        return norm, idx[norm]
    # fall back to longest matching suffix on the file name + parent dirs
    tail = "/".join(norm.split("/")[-3:])
    for rel, full in idx.items():
        if rel.endswith(tail):
            return rel, full
    base = norm.split("/")[-1]
    for rel, full in idx.items():
        if rel.endswith("/" + base) or rel == base:
            return rel, full
    return None


# ---------------------------------------------------------------- callee signatures
def callee_brief(addr, name, con):
    """Signature of a callee (from its X360 pseudocode) + recovered status."""
    sig = None
    exp = load_export(addr) if addr else None
    if exp:
        sig = sig_of(exp.get("pseudocode"))
    row = con.execute("SELECT status, tu_id, dest_path FROM func WHERE name=?", (name,)).fetchone()
    if row and row["status"] in ("compiles", "reviewed"):
        loc = row["dest_path"] or row["tu_id"]
        status = f"RECOVERED -> {loc}"
    elif row and row["status"] == "recovered":
        # drafted but never passed the compile gate — don't trust its signature blindly
        loc = row["dest_path"] or row["tu_id"]
        status = f"DRAFTED (not yet compiled) -> {loc}"
    elif row:
        status = row["status"]
    else:
        status = "external/unknown"
    return sig or name, status


# ---------------------------------------------------------------- goal-trace overlay
def _active_goal_executed():
    """(goal_name, executed-function-name set) for the active goal's execution trace.
    Empty set when no goal is active or the goal has no `executed_funcs` (glob goals,
    imports made before the field existed)."""
    import work  # lazy, same-dir; work.py imports this module lazily too
    goals = work.load_goals()
    name = goals.get("active_goal")
    if not name:
        return None, set()
    _, g = work.find_goal(goals, name)
    return name, set((g or {}).get("executed_funcs") or [])


# ---------------------------------------------------------------- assembly
def assemble(con, tu_row, funcs, with_asm=False):
    out = []
    w = out.append
    tu = tu_row["id"]
    w(f"===== DOSSIER: {tu} =====")
    w(f"source: {tu_row['source']}   status: {tu_row['status']}   functions: {tu_row['n_funcs']}")
    w(f"dest  : {tu_row['dest_path'] or '(class TU — pick a path under b5-decomp/src)'}")
    w("naming: all new owned code follows references/CXX_NAMING_CONVENTIONS.md "
      "(scope+type prefixes mpX/lfX, KI_/KU_/KF_ constants, E_ enums, PascalCase types). "
      "Convention wins over Hex-Rays names, except for external/generated/platform APIs.")

    # which of this TU's functions the active goal's milestone actually exercised
    gname, executed = _active_goal_executed()
    if executed:
        ran = sum(1 for f in funcs if f["name"] in executed)
        w(f"goal  : [{gname}] the milestone trace executed {ran}/{len(funcs)} of this TU's "
          f"functions (marked per function below; unmarked ones did not run before the milestone)")

    # original source overlay
    src = None
    if tu_row["source"] == "decfigs":
        src = find_feb2007_source(tu)
    if src:
        w(f"\n--- ORIGINAL SOURCE (Feb-2007 leak): {src[0]} ---")
        w("    GROUND TRUTH. Prefer this over reconstructing from pseudocode where it covers the function.")
        lines = open(src[1], encoding="utf-8", errors="replace").read().splitlines()
        for ln in lines[:MAX_SRC_LINES]:
            w("    " + ln)
        if len(lines) > MAX_SRC_LINES:
            w(f"    ... [{len(lines)-MAX_SRC_LINES} more lines — open {src[1]}]")
    else:
        w("\n--- ORIGINAL SOURCE: none in the Feb-2007 leak for this TU ---")

    # type pointers
    w("\n--- TYPES ---")
    w(f"    RenderWare rw:: layouts: {RW_INCLUDE}/   |   primitives: b5-decomp/src/types.hpp")
    ns = sorted({f["name"].rsplit("::", 1)[0] for f in funcs if "::" in f["name"]})
    if ns:
        w(f"    namespaces in this TU: {', '.join(ns[:8])}{' ...' if len(ns) > 8 else ''}")

    # per-function brief
    for f in funcs:
        addr = f["x360_addr"]
        exp = load_export(addr) if addr else None
        tag = ""
        if executed:
            tag = "  [EXECUTED in goal trace]" if f["name"] in executed \
                  else "  [not executed in goal trace]"
        w(f"\n================ {f['name']}  @ {addr}  [{f['status']}]{tag} ================")
        if not exp:
            w("  (no export found)")
            continue
        sig = sig_of(exp.get("pseudocode"))
        if sig:
            w(f"  signature: {sig}")
        variables = exp.get("variables") or []
        if variables:
            w("  locals:")
            for v in variables:
                nm = v.get("name") or "(unnamed)"
                w(f"    {v.get('type','?'):24s} {nm}  (size {v.get('size','?')}{', reg' if v.get('is_reg') else ''})")
        w("  pseudocode:")
        for pl in (exp.get("pseudocode") or "").splitlines():
            w("    " + pl)
        # callees
        outs = exp.get("xrefs_from") or []
        if outs:
            w(f"  calls ({len(outs)}):")
            for xr in outs[:MAX_CALLEES]:
                csig, cstat = callee_brief(xr.get("address"), xr.get("name"), con)
                w(f"    -> [{cstat}] {csig[:100]}")
            if len(outs) > MAX_CALLEES:
                w(f"    ... +{len(outs)-MAX_CALLEES} more callees")
        # callers
        ins = exp.get("xrefs_to") or []
        if ins:
            names = ", ".join(x.get("name", "?") for x in ins[:6])
            w(f"  called by ({len(ins)}): {names}{' ...' if len(ins) > 6 else ''}")
        # asm (opt-in; verbose)
        if with_asm and exp.get("assembly"):
            w("  assembly:")
            for al in exp["assembly"].splitlines():
                w("    " + al)

    return "\n".join(out)
