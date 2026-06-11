#!/usr/bin/env python3
"""
Phase 0 - cross-build identity table.

Anchors on the X360 spine and left-joins the DecFIGS PS3 build (for the original
`primary_file` of every function) and, optionally, the PS3-External build (for a
second-opinion / corroboration flag). The join key is the NORMALIZED QUALIFIED
NAME -- `Namespace::Class::method` with parameters/return/calling-convention
stripped -- because addresses are per-build and meaningless across builds, and
DecFIGS names are Itanium-mangled while X360 names are already demangled.

Output: progress/identity.json  (+ a match-rate report to stdout)

Run from the repo root inside an environment where `c++filt` is on PATH:
    python tools/work/build_identity.py            # X360 x DecFIGS
    python tools/work/build_identity.py --with-ps3 # also fold in PS3-External
"""
import argparse, json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXPORTS = os.path.join(ROOT, ".ida-exports")
DECFIGS_FILES = os.path.join(ROOT, "references", "DecFIGS", "decfigs_func_files.json")
OUT = os.path.join(ROOT, "progress", "identity.json")

X360 = "BURNOUT_X360_ARTIST.XEX"
PS3EXT = "Burnout_External_PS3.ELF"

AUTO = re.compile(r"^(sub_|j_|nullsub|unknown|loc_|off_|byte_|dword_|word_|qword_|unk_|Burnout_X360_Artist_)")


def strip_params(demangled: str) -> str:
    """Keep the qualified path; drop the parameter list and trailing qualifiers.
    Cuts at the first top-level '(' (ignoring those inside template <>)."""
    depth = 0
    for i, c in enumerate(demangled):
        if c == "<":
            depth += 1
        elif c == ">":
            depth = max(0, depth - 1)
        elif c == "(" and depth == 0:
            return demangled[:i].strip()
    return demangled.strip()


def normalize_demangled(name: str) -> str:
    """X360 / IDA-demangled names: already a qualified path, just trim params if any."""
    return strip_params(name.strip())


def is_named(name: str) -> bool:
    return bool(name) and not AUTO.match(name)


def batch_demangle(mangled: list[str]) -> list[str]:
    """Demangle Itanium names in one c++filt pass (order preserved, 1 line out per in)."""
    if not mangled:
        return []
    proc = subprocess.run(
        ["c++filt"], input="\n".join(mangled),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        sys.exit(f"c++filt failed: {proc.stderr}")
    out = proc.stdout.split("\n")
    return out[: len(mangled)]


def read_export(path: str):
    try:
        d = json.load(open(path, encoding="utf-8", errors="replace"))
        return d.get("address"), d.get("name"), bool(d.get("pseudocode"))
    except Exception:
        return None, None, False


def load_build(db: str):
    """Return {normalized_name: {'canonical','addrs','has_pseudo','raw_collisions'}} for a build."""
    base = os.path.join(EXPORTS, db)
    files = [os.path.join(dp, f) for dp, _, fs in os.walk(base) for f in fs if f.endswith(".json")]
    table: dict[str, dict] = {}
    n_named = 0
    with ThreadPoolExecutor(max_workers=16) as ex:
        for addr, name, has_pseudo in ex.map(read_export, files):
            if not addr or not is_named(name):
                continue
            n_named += 1
            key = normalize_demangled(name)
            if not key:
                continue
            e = table.setdefault(key, {"canonical": name, "addrs": [], "has_pseudo": False})
            e["addrs"].append(addr)
            e["has_pseudo"] = e["has_pseudo"] or has_pseudo
    return table, len(files), n_named


def load_decfigs():
    """Return {normalized_name: {'primary_file','ps3_addr'}} from the DWARF attribution."""
    raw = json.load(open(DECFIGS_FILES, encoding="utf-8", errors="replace"))
    items = list(raw.items())
    mangled = [v["name"].lstrip(".") for _, v in items]
    demangled = batch_demangle(mangled)
    table: dict[str, dict] = {}
    for (ps3_addr, v), dem in zip(items, demangled):
        key = strip_params(dem.strip())
        if not key:
            continue
        # first writer wins; collisions (overloads) share a primary_file anyway
        table.setdefault(key, {"primary_file": v.get("primary_file"), "ps3_addr": ps3_addr})
    return table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-ps3", action="store_true", help="fold in PS3-External corroboration (slow, ~29k files)")
    args = ap.parse_args()

    print(f"[1/3] loading X360 spine ({X360}) ...", flush=True)
    x360, x360_total, x360_named = load_build(X360)
    print(f"      {x360_total} files, {x360_named} named, {len(x360)} unique normalized names")

    print("[2/3] loading + demangling DecFIGS attribution ...", flush=True)
    decfigs = load_decfigs()
    print(f"      {len(decfigs)} unique normalized names with primary_file")

    ps3 = {}
    if args.with_ps3:
        print(f"[3/3] loading PS3-External corroboration ({PS3EXT}) ...", flush=True)
        ps3, ps3_total, ps3_named = load_build(PS3EXT)
        print(f"      {ps3_total} files, {ps3_named} named, {len(ps3)} unique normalized names")
    else:
        print("[3/3] skipping PS3-External (pass --with-ps3 to include)")

    # Left-join, anchored on X360.
    identity = {}
    with_file = with_ps3 = collisions = 0
    for key, e in x360.items():
        df = decfigs.get(key)
        pc = ps3.get(key)
        if len(e["addrs"]) > 1:
            collisions += 1
        if df:
            with_file += 1
        if pc:
            with_ps3 += 1
        identity[key] = {
            "canonical": e["canonical"],
            "x360_addrs": e["addrs"],
            "has_pseudocode": e["has_pseudo"],
            "primary_file": df["primary_file"] if df else None,
            "decfigs_ps3_addr": df["ps3_addr"] if df else None,
            "ps3ext_addrs": pc["addrs"] if pc else None,
        }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(identity, open(OUT, "w", encoding="utf-8"), indent=1)

    n = len(identity)
    print("\n=== identity report ===")
    print(f"X360 functions (canonical names) : {n}")
    print(f"  with DecFIGS primary_file      : {with_file}  ({100*with_file//max(n,1)}%)")
    if args.with_ps3:
        print(f"  with PS3-External corroboration: {with_ps3}  ({100*with_ps3//max(n,1)}%)")
    print(f"  overload-collisions (>1 addr)  : {collisions}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
