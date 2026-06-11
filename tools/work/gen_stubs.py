#!/usr/bin/env python3
"""
Demand-driven stub generator (the step that lets a NON-self-contained TU compile
and link before its callees are reconstructed).

For a TU, finds every function it calls (`xrefs_from`) that is **not yet
reconstructed**, and emits a trap-stub *definition* for each, using the callee's
own pseudocode signature. Reconstructing a stubbed callee later just replaces the
trap body with the real one.

Honest limit (see STRATEGY.md): a stub for a class method `A::B::foo(...)` only
compiles where class `A::B` is declared. Declaring the class is type-recovery work
the agent still does — this tool handles the mechanical *definition* side and tells
you which callees need a type declaration first.

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
          f"{len(needs_class)} are class methods (need their class declared first).")
    if args.list:
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
        "// NOTE: class-method stubs require their class to be declared (type recovery)",
        "//       before this file will compile. See STRATEGY.md.",
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
