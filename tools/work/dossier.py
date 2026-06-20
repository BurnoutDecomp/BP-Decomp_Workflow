#!/usr/bin/env python3
"""
Phase 2 - the dossier assembler.

Builds the full reconstruction brief for one translation unit, joining everything
an agent needs into a single document so it never has to hunt through
.ida-exports/ by hand:

  - per-function: clean signature, decompiler locals, full pseudocode, (opt) asm
  - callee signatures + whether each callee is already recovered (and where)
  - caller context
  - the ORIGINAL LegacySrc source file, when the TU's primary_file exists in the LegacySrc partial source
  - DecFIGS dwarfdump declaration/type/local-variable hints for the TU/source file
  - a pointer to relevant type headers

Used by `work show <tu> --full`. Kept separate from work.py so the assembly logic
is reusable and testable.
"""
import json, os, re
from functools import lru_cache

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
X360_EXPORTS = os.path.join(ROOT, ".ida-exports", "BURNOUT_X360_ARTIST.XEX")
FEB2007 = os.path.join(ROOT, "references", "LegacySrc", "BrnEntityModuleUnity")
DECFIGS_DWARFDUMP = os.path.join(ROOT, "references", "DecFIGS", "dwarfdump")
RW_INCLUDE = "b5-decomp/vendor/renderware/include"
WIKI_TYPES = os.path.join(ROOT, "references", "Wiki", "types.json")

import gen_skeleton  # same dir; provides load_export + signature_from_pseudocode
load_export = gen_skeleton.load_export
sig_of = gen_skeleton.signature_from_pseudocode

MAX_SRC_LINES = 500
MAX_DWARF_FILES = 6
MAX_DWARF_LINES = 220
MAX_CALLEES = 24
MAX_WIKI_TYPES = 12
MAX_WIKI_FIELDS = 40


# ---------------------------------------------------------------- LegacySrc overlay
@lru_cache(maxsize=1)
def feb2007_index():
    """Map normalized path-suffix -> absolute path for every source file in the LegacySrc partial source."""
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
    """Return (rel_path, abspath) if the original source file is in the LegacySrc partial source."""
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


# ---------------------------------------------------------------- DecFIGS dwarfdump overlay
@lru_cache(maxsize=1)
def decfigs_dwarfdump_index():
    """Map normalized DecFIGS source paths -> absolute dwarfdump hint files."""
    idx = {}
    if not os.path.isdir(DECFIGS_DWARFDUMP):
        return idx
    for dp, _, fs in os.walk(DECFIGS_DWARFDUMP):
        for f in fs:
            if f.endswith((".cpp", ".h", ".hpp", ".inl", ".c")):
                full = os.path.join(dp, f)
                rel = os.path.relpath(full, DECFIGS_DWARFDUMP).replace("\\", "/")
                idx[rel] = full
    return idx


def _add_dwarfdump_candidate(out, idx, rel):
    if rel and rel in idx and rel not in {r for r, _ in out}:
        out.append((rel, idx[rel]))


def find_decfigs_dwarfdump_sources(primary_file: str):
    """Return DWARF-derived declaration/type hint files relevant to a DecFIGS TU."""
    norm = normalize_primary_file(primary_file)
    if not norm:
        return []
    idx = decfigs_dwarfdump_index()
    if not idx:
        return []

    found = []
    stem, ext = os.path.splitext(norm)
    if ext.lower() in (".cpp", ".c"):
        for alt in (".h", ".hpp", ".inl"):
            _add_dwarfdump_candidate(found, idx, stem + alt)
        _add_dwarfdump_candidate(found, idx, norm)
    elif ext.lower() in (".h", ".hpp", ".inl"):
        _add_dwarfdump_candidate(found, idx, norm)
        for alt in (".cpp", ".c"):
            _add_dwarfdump_candidate(found, idx, stem + alt)
    else:
        _add_dwarfdump_candidate(found, idx, norm)

    if found:
        return found[:MAX_DWARF_FILES]

    # Fallback for path-normalization drift: require a filename match plus nearby
    # parent directories, then add the sibling header/source around that match.
    tail = "/".join(norm.split("/")[-3:])
    base = norm.split("/")[-1]
    for rel, full in idx.items():
        if rel.endswith(tail) or rel.endswith("/" + base) or rel == base:
            _add_dwarfdump_candidate(found, idx, rel)
            stem, ext = os.path.splitext(rel)
            if ext.lower() in (".cpp", ".c"):
                found = []
                for alt in (".h", ".hpp", ".inl"):
                    _add_dwarfdump_candidate(found, idx, stem + alt)
                _add_dwarfdump_candidate(found, idx, rel)
            elif ext.lower() in (".h", ".hpp", ".inl"):
                found = []
                _add_dwarfdump_candidate(found, idx, rel)
                for alt in (".cpp", ".c"):
                    _add_dwarfdump_candidate(found, idx, stem + alt)
            break

    return found[:MAX_DWARF_FILES]


# ---------------------------------------------------------------- callee signatures
# ---------------------------------------------------------------- Wiki type overlay
@lru_cache(maxsize=1)
def wiki_types():
    """type-name -> [records] from the burnout.wiki struct/enum index (may be absent)."""
    if not os.path.isfile(WIKI_TYPES):
        return {}
    try:
        return json.load(open(WIKI_TYPES, encoding="utf-8")).get("types", {})
    except Exception:
        return {}


_TYPE_TOK = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# wiki section titles too generic to be a confident type match
_WIKI_STOP = {"Data", "Count", "Entry", "Header", "Value", "Size", "Name", "Type",
              "Colour", "Color", "Graph", "Instance", "Index", "Flags", "Info",
              "Table", "List", "Block", "Field", "Offset", "Id"}


def wiki_matches(funcs):
    """Collect type tokens used as decompiler local-variable *types* in this TU
    that the wiki documents. Local-var types are the high-precision signal (the
    concrete data types the function manipulates) — pseudocode/callee tokens are
    deliberately NOT scanned because they share words with generic format structs
    (every CgsFont fn would spuriously hit the `Font` format). Returns an ordered,
    de-duplicated list of (token, record), preferring the primary (Paradise-era)
    record per type."""
    idx = wiki_types()
    if not idx:
        return []
    tokens = set()
    for f in funcs:
        addr = f["x360_addr"]
        exp = load_export(addr) if addr else None
        if not exp:
            continue
        for v in (exp.get("variables") or []):
            tokens.update(_TYPE_TOK.findall(v.get("type") or ""))
    matched = []
    for tok in sorted(tokens):
        # require a C++-type shape (drops Hex-Rays temps v4/a1 and snake_case save
        # fields) and skip over-generic section titles
        if len(tok) < 3 or tok in _WIKI_STOP or not any(c.isupper() for c in tok):
            continue
        recs = idx.get(tok)
        if recs:
            matched.append((tok, recs[0]))   # recs[0] = primary-first sorted
    return matched


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
        w(f"\n--- LEGACYSRC PARTIAL SOURCE (STYLING / INLINING REFERENCE ONLY): {src[0]} ---")
        w("    NOT a blueprint and NOT offset/logic authority — heavy version drift from the")
        w("    X360 ARTIST/\"Breaker\" + DecFIGS spine. Use ONLY for (a) code style/idiom and")
        w("    (b) recovering the shape/names of inlined helpers. Authority for behavior+layout")
        w("    is the X360 pseudocode+asm; authority for declaration shape is the DecFIGS DWARF.")
        lines = open(src[1], encoding="utf-8", errors="replace").read().splitlines()
        for ln in lines[:MAX_SRC_LINES]:
            w("    " + ln)
        if len(lines) > MAX_SRC_LINES:
            w(f"    ... [{len(lines)-MAX_SRC_LINES} more lines — open {src[1]}]")
    else:
        w("\n--- ORIGINAL SOURCE: none in the LegacySrc partial source for this TU ---")

    # DWARF-derived declaration/type/local-variable hints from DecFIGS.
    if tu_row["source"] == "decfigs":
        dwarf_sources = find_decfigs_dwarfdump_sources(tu)
    else:
        dwarf_sources = []
    if dwarf_sources:
        w("\n--- DECFIGS DWARFDUMP HINTS ---")
        w("    DWARF-derived C++-shaped declarations and local-variable hints for this source path.")
        w("    Use names, enums, logical types, member lists, globals, signatures, and locals as")
        w("    reconstruction hints. This is NOT complete implementation source and NOT offset")
        w("    authority; verify behavior and member placement against the X360 pseudocode/asm.")
        for rel, full in dwarf_sources:
            w(f"\n  --- {rel} ---")
            lines = open(full, encoding="utf-8", errors="replace").read().splitlines()
            for ln in lines[:MAX_DWARF_LINES]:
                w("    " + ln)
            if len(lines) > MAX_DWARF_LINES:
                w(f"    ... [{len(lines)-MAX_DWARF_LINES} more lines - open {full}]")
    else:
        w("\n--- DECFIGS DWARFDUMP HINTS: none found for this TU/source path ---")

    # type pointers
    w("\n--- TYPES ---")
    w(f"    RenderWare rw:: layouts: {RW_INCLUDE}/   |   primitives: b5-decomp/src/types.hpp")
    ns = sorted({f["name"].rsplit("::", 1)[0] for f in funcs if "::" in f["name"]})
    if ns:
        w(f"    namespaces in this TU: {', '.join(ns[:8])}{' ...' if len(ns) > 8 else ''}")

    # burnout.wiki field-name overlay (names/types AUTHORITATIVE; offsets advisory)
    wm = wiki_matches(funcs)
    if wm:
        w("\n--- WIKI TYPES (burnout.wiki) ---")
        w("    Field NAMES/TYPES/semantics are AUTHORITATIVE -- adopt these member names "
          "(they already follow CXX_NAMING_CONVENTIONS). OFFSETS/SIZES are per the tagged")
        w("    build and may differ from our X360 spine: VERIFY layout against the "
          "pseudocode/asm below; do NOT trust wiki offsets for member placement.")
        for tok, rec in wm[:MAX_WIKI_TYPES]:
            tag = f"build={rec['build']}, primary (name-authoritative)" if rec["primary"] \
                  else f"build={rec['build']}, NOT confirmed our build"
            w(f"\n  {rec['type']} ({rec['kind']}; {tag}; page: {rec['page']})")
            for fld in rec["fields"][:MAX_WIKI_FIELDS]:
                if rec["kind"] == "struct":
                    line = f"    {fld['offset']:>6} {fld['size']:>5}  {fld['type']:22} {fld['name']}"
                    if fld["desc"]:
                        line += f"   ; {fld['desc']}"
                else:
                    line = f"    {fld['id']:>5}  {fld['name']}"
                    if fld["alt"]:
                        line += f"   (alt: {fld['alt']})"
                w(line)
            if len(rec["fields"]) > MAX_WIKI_FIELDS:
                w(f"    ... +{len(rec['fields'])-MAX_WIKI_FIELDS} more "
                  f"(python tools/work/wiki_index.py --lookup {rec['type']})")
        if len(wm) > MAX_WIKI_TYPES:
            extra = ", ".join(t for t, _ in wm[MAX_WIKI_TYPES:])
            w(f"\n  +{len(wm)-MAX_WIKI_TYPES} more documented types: {extra}")

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
