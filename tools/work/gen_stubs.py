#!/usr/bin/env python3
"""
Demand-driven stub generator (the step that lets a NON-self-contained TU compile
and link before its callees are reconstructed).

For a TU, finds every function it calls (`xrefs_from`) that is **not yet
reconstructed**, and emits a trap-stub *definition* for each, using the callee's
own pseudocode signature. Reconstructing a stubbed callee later just replaces the
trap body with the real one.

Honest limit (see STRATEGY.md): a stub for a class method `A::B::foo(...)` only
compiles where class `A::B` is declared. The type must come from a **reconstructed
header you #include**, not a local fork — so this tool handles the mechanical body-stub
side AND names the owning header for each callee (and whether it already exists in
b5-decomp/src or must be rebuilt, and from which reference). See AGENTS.md
("Reconstruct includes; don't fake them").

    python tools/work/gen_stubs.py "<TU key>"            # write progress/stubs/<tu>.cpp
    python tools/work/gen_stubs.py "<TU key>" --list      # just list unresolved callees
"""
import argparse, json, os, re, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IDENTITY = os.path.join(ROOT, "progress", "identity.json")
TU_INDEX = os.path.join(ROOT, "progress", "tu_index.json")
DB = os.path.join(ROOT, "progress", "ledger.sqlite")
OUT_DIR = os.path.join(ROOT, "progress", "stubs")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_skeleton import load_export, signature_from_pseudocode

DONE = ("compiles", "reviewed")
CC = re.compile(r"\b__(fastcall|cdecl|thiscall|stdcall|usercall|userpurge)\b|"
                r"__(return_ptr|struct_ptr|hidden|noreturn)\b")
# Hex-Rays pseudo-types -> the project's types.hpp aliases. Order matters
# (unsigned forms and wider names first).
HEXRAYS = [
    (r"\bunsigned __int64\b", "u64"), (r"\bunsigned __int32\b", "u32"),
    (r"\bunsigned __int16\b", "u16"), (r"\bunsigned __int8\b", "u8"),
    (r"\b__int64\b", "s64"), (r"\b__int32\b", "s32"),
    (r"\b__int16\b", "s16"), (r"\b__int8\b", "s8"),
    (r"\b_QWORD\b", "u64"), (r"\b_DWORD\b", "u32"),
    (r"\b_WORD\b", "u16"), (r"\b_BYTE\b", "u8"),
]
# Compiler/runtime helpers (PPC save/restore, thunks) — never real callees.
RUNTIME = re.compile(r"^(__sav|__rest|__c_|_purecall|__mem|j_|nullsub|sub_)")


def clean_sig(sig: str) -> str:
    sig = CC.sub("", sig)
    for pat, rep in HEXRAYS:
        sig = re.sub(pat, rep, sig)
    return re.sub(r"\s+", " ", sig).strip()


def is_void(sig: str) -> bool:
    head = sig.split("(", 1)[0]
    return "void" in head and "*" not in head


def resolved_names(con):
    return {r[0] for r in con.execute(f"SELECT name FROM func WHERE status IN {DONE}")}


def collect(tu, identity, index, con):
    """Return list of (callee_name, addr, signature) for unresolved callees."""
    own = set(index[tu]["functions"])
    done = resolved_names(con) if con else set()
    seen, out = set(), []
    for nm in index[tu]["functions"]:
        e = identity.get(nm) or {}
        addr = (e.get("x360_addrs") or [None])[0]
        exp = load_export(addr) if addr else None
        if not exp:
            continue
        for xr in exp.get("xrefs_from", []):
            cn = xr.get("name")
            if not cn or cn in own or cn in done or cn in seen or RUNTIME.match(cn):
                continue
            seen.add(cn)
            cexp = load_export(xr.get("address"))
            sig = clean_sig(signature_from_pseudocode(cexp.get("pseudocode"))) if cexp else None
            out.append((cn, xr.get("address"), sig))
    return out


SRC_ROOT = os.path.join(ROOT, "b5-decomp", "src")
REF_TREES = [
    ("Feb-2007", os.path.join(ROOT, "references", "Feb-2007")),
    ("DWARF",    os.path.join(ROOT, "references", "DecFIGS", "DWARFDump")),
]


def build_func2tu(index):
    """Reverse map: function name -> owning TU key (a path or a 'class:' key)."""
    out = {}
    for tu, meta in index.items():
        for fn in meta.get("functions", []):
            out.setdefault(fn, tu)
    return out


def owning_header(cn, identity, func2tu):
    """Best-effort owning header (mirrored, relative to b5-decomp/src) for a callee,
    or None when there's no file attribution (class-only TU, no DecFIGS primary_file)."""
    pf = (identity.get(cn) or {}).get("primary_file")
    if not pf:
        tu = func2tu.get(cn)
        if tu and not tu.startswith("class:") and ("/" in tu or "\\" in tu):
            pf = tu
    if not pf:
        return None
    stem, _ = os.path.splitext(pf.replace("\\", "/"))
    return stem + ".h"


def build_ref_index():
    """basename -> sorted set of ref tags that contain a header of that name."""
    idx = {}
    for tag, root in REF_TREES:
        if not os.path.isdir(root):
            continue
        for dp, _, files in os.walk(root):
            for f in files:
                if f.endswith((".h", ".hpp")):
                    idx.setdefault(f, set()).add(tag)
    return idx


def report_headers(callees, identity, index):
    """Group unresolved callees by owning header; print which to #include vs rebuild."""
    func2tu = build_func2tu(index)
    by_header = {}        # header (rel to src) -> [callee names]
    no_attrib = {}        # class path -> [callee names]
    for cn, _addr, _sig in callees:
        h = owning_header(cn, identity, func2tu)
        if h:
            by_header.setdefault(h, []).append(cn)
        else:
            cls = cn.rsplit("::", 1)[0] if "::" in cn else "(global)"
            no_attrib.setdefault(cls, []).append(cn)

    if not by_header and not no_attrib:
        return
    ref_idx = build_ref_index() if any(
        not os.path.exists(os.path.join(SRC_ROOT, h)) for h in by_header) else {}

    print("\nHeaders to reconstruct & #include (rebuild the real header; do not fork the type locally):")
    for h in sorted(by_header):
        if os.path.exists(os.path.join(SRC_ROOT, h)):
            status = "EXISTS in b5-decomp/src -- just #include it"
        else:
            refs = sorted(ref_idx.get(os.path.basename(h), []))
            status = ("NEEDS REBUILD -- reference: " + ", ".join(refs)) if refs \
                     else "NEEDS REBUILD -- no reference header found (forward-decl may be justified)"
        print(f'  #include "{h}"   [{status}]')
        for cn in sorted(by_header[h]):
            print(f"      - {cn}")
    for cls in sorted(no_attrib):
        print(f"  (no file attribution for {cls} -- locate its header by class name in references/)")
        for cn in sorted(no_attrib[cls]):
            print(f"      - {cn}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tu")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    identity = json.load(open(IDENTITY, encoding="utf-8"))
    index = json.load(open(TU_INDEX, encoding="utf-8"))
    if args.tu not in index:
        sys.exit(f"unknown TU: {args.tu!r}")
    con = sqlite3.connect(DB) if os.path.exists(DB) else None

    callees = collect(args.tu, identity, index, con)
    if not callees:
        print(f"{args.tu}: no unresolved callees — self-contained, no stubs needed.")
        return

    needs_class = [c for c in callees if c[0] and "::" in c[0]]
    print(f"{args.tu}: {len(callees)} unresolved callee(s); "
          f"{len(needs_class)} are class methods whose type must come from a reconstructed header "
          f"(rebuild + #include it -- do not fork the type locally; see AGENTS.md).")

    # Drive the header-first workflow: name the owning header for each callee.
    report_headers(callees, identity, index)

    if args.list:
        print("\nunresolved callees:")
        for cn, addr, sig in callees:
            print(f"  {addr}  {sig or cn}")
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    safe = args.tu.replace("/", "__").replace(":", "_").replace("\\", "__")
    path = os.path.join(OUT_DIR, safe + ".cpp")
    lines = [
        "// === generated trap stubs (demand-driven) ===",
        f"// for TU: {args.tu}",
        "// Replace a body with the real implementation when you reconstruct that callee.",
        "// NOTE: these are trap-stub BODIES (link time). The TYPES they need must come",
        "//       from reconstructed headers (#include them) — do NOT fork a type locally.",
        "//       `work stubs` printed the owning header for each callee. See AGENTS.md",
        "//       (\"Reconstruct includes; don't fake them\").",
        "",
    ]
    for cn, addr, sig in callees:
        if not sig:
            lines.append(f"// (no signature) {cn}  @ {addr}")
            continue
        body = "{ __debugbreak(); }" if is_void(sig) else "{ __debugbreak(); return {}; }"
        lines.append(f"// {cn}  @ {addr}")
        lines.append(f"{sig} {body}")
        lines.append("")
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    print(f"wrote {len(callees)} stub(s) -> {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
