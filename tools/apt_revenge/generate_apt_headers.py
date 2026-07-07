#!/usr/bin/env python3
"""Generate Apt type-vocabulary headers from the Burnout Revenge B4Extern PDB.

Source of truth: `IDA Files/B4Extern.pdb` (Apt 0.19.02, Xenon /
PPC, 32-bit big-endian) exported to text with llvm-pdbutil. This emits readable,
offset-annotated C++ declarations for every `Apt*` class/struct plus per-class
method prototypes recovered from the module symbols.

REFERENCE ONLY. This is Apt **0.19.02** (Burnout Revenge, 2005). The Paradise/B5
project's Apt is a later (2008) version, so these headers are a *vocabulary to
consult and verify against* -- NOT files to drop into b5-decomp/src (that is the
VERSION-DRIFT TRAP; see AGENTS.md). The raw PDB dumps in pdb-dump/ are the
authoritative ground truth; this generated header is a convenience rendering.

Layouts are 32-bit (4-byte pointers) as they appear in the console PDB. When
adopting a layout for the PC x64 target, widen pointers and re-verify offsets
against the x64 build (Burnout_External_Xbox_One), exactly as the RenderWare PDB
rule requires.

Inputs  (produced by capture_dumps.sh / llvm-pdbutil):
    pdb-dump/apt_layouts.txt        pretty -classes -class-definitions=layout -include-types=Apt
    pdb-dump/apt_enums.txt          pretty -enums -include-types=Apt
    pdb-dump/apt_module_syms.txt    filtered pretty -module-syms -sym-types=funcs
Output:
    include/apt_types.gen.h         consolidated reference header

Re-run:  python tools/apt_revenge/generate_apt_headers.py
"""
from __future__ import annotations
import re, sys
from pathlib import Path
from collections import OrderedDict, defaultdict

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "references" / "B4Extern"
DUMP = REF / "pdb-dump"
OUTDIR = REF / "include"

# B4Extern.pe ImageBase. llvm-pdbutil reports func RVAs; IDA loads at 0x400000, so
# the VA a user sees in IDA (and the .json export filename) is RVA + IMAGE_BASE.
# Header method comments and the exported ida-export/*.json therefore use VAs.
IMAGE_BASE = 0x400000

TYPE_RE = re.compile(r'^    (class|struct|union) (\S+) \[sizeof = (\d+)\]')
BASE_RE = re.compile(r'^      : (?:public|private|protected) (\S+) \{')
# member line: <indent><kind> +0xNN [sizeof=S] <rest>
MEM_RE = re.compile(r'^(\s+)(base|vfptr|data) \+0x([0-9a-fA-F]+) \[sizeof=\s*(\d+)\]\s?(.*)$')
BITFIELD_RE = re.compile(r'^(.*?)\s+(\S+)\s+:\s+(\d+)$')  # "<type> <name> : <bits>"


def parse_layouts(text):
    """Return OrderedDict name -> {size, kind, bases:[], members:[lines]} using
    only the class-header line, the base line, and the direct members (indent 6)."""
    lines = text.splitlines()
    types = OrderedDict()
    i = 0
    n = len(lines)
    while i < n:
        m = TYPE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        kind, name, size = m.group(1), m.group(2), int(m.group(3))
        # optional base line
        bases = []
        j = i + 1
        while j < n and BASE_RE.match(lines[j]):
            bases.append(BASE_RE.match(lines[j]).group(1))
            j += 1
        # collect the body until the matching '    }' at indent 4
        body = []
        while j < n and not re.match(r'^    \}\s*$', lines[j]):
            body.append(lines[j])
            j += 1
        types[name] = dict(size=size, kind=kind, bases=bases, body=body)
        i = j + 1
    return types


def direct_members(entry):
    """Yield (offset, size, kind, rest, subs[]) for direct members (indent 6).
    subs = the deeper-indented expansion lines for that member (for bitfields)."""
    body = entry["body"]
    out = []
    idx = 0
    while idx < len(body):
        m = MEM_RE.match(body[idx])
        if not m:
            idx += 1
            continue
        indent = len(m.group(1))
        if indent != 6:  # not a direct member
            idx += 1
            continue
        off, size, kind, rest = int(m.group(3), 16), int(m.group(4)), m.group(2), m.group(5)
        # gather sub-lines (indent > 6) until the next indent<=6 member
        subs = []
        k = idx + 1
        while k < len(body):
            mm = MEM_RE.match(body[k])
            if mm and len(mm.group(1)) <= 6:
                break
            if mm:
                subs.append((int(mm.group(3), 16), int(mm.group(4)), mm.group(2), mm.group(5)))
            k += 1
        out.append((off, size, kind, rest, subs))
        idx = k
    return out


def clean_type(t):
    return t.replace("__ptr32 ", "").replace("__ptr32", "").strip()


def render_member(off, size, kind, rest, subs):
    """Return a list of C++ lines for one direct member."""
    if kind == "vfptr":
        return [f"    /* +0x{off:02x} */ void* __vftable;"]
    rest = rest.strip()
    bf = BITFIELD_RE.match(rest)
    if bf:  # a direct bitfield member
        ty, nm, bits = clean_type(bf.group(1)), bf.group(2), bf.group(3)
        return [f"    /* +0x{off:02x} */ {ty} {nm} : {bits};"]
    # split "<type> <name>" -- name is the last whitespace-separated token
    if "<unnamed-tag>" in rest and subs:
        # anonymous bitfield / union container: inline the sub-members
        lines = [f"    /* +0x{off:02x} */ struct {{"]
        for so, ss, sk, sr in subs:
            sr = sr.strip()
            sbf = BITFIELD_RE.match(sr)
            if sbf:
                ty, nm, bits = clean_type(sbf.group(1)), sbf.group(2), sbf.group(3)
                lines.append(f"        {ty} {nm} : {bits};")
            else:
                parts = sr.rsplit(" ", 1)
                if len(parts) == 2:
                    lines.append(f"        {clean_type(parts[0])} {parts[1]};")
        lines.append("    };")
        return lines
    parts = rest.rsplit(" ", 1)
    if len(parts) == 2:
        ty, nm = clean_type(parts[0]), parts[1]
        # arrays render as "<elem> name[N]" already in the pdb text
        return [f"    /* +0x{off:02x} */ {ty} {nm};"]
    return [f"    /* +0x{off:02x} [sizeof={size}] {rest} */"]


def parse_methods(text):
    """name(class) -> list of (address, signature) from filtered module syms."""
    by_class = defaultdict(list)
    fre = re.compile(r'^\s*func \[0x([0-9a-fA-F]+).*?\]\s+(?:\(FPO\)\s+)?(.*)$')
    qual = re.compile(r'([A-Za-z_]\w*(?:::[A-Za-z_~]\w*)+)\s*\(')
    for ln in text.splitlines():
        m = fre.match(ln)
        if not m:
            continue
        va = int(m.group(1), 16) + IMAGE_BASE
        sig = m.group(2).strip()
        q = qual.search(sig)
        cls = q.group(1).rsplit("::", 1)[0] if q else "<free>"
        by_class[cls].append((f"{va:X}", sig))
    return by_class


def main():
    layouts = parse_layouts((DUMP / "apt_layouts.txt").read_text(errors="replace"))
    methods = parse_methods((DUMP / "apt_module_syms.txt").read_text(errors="replace"))
    OUTDIR.mkdir(parents=True, exist_ok=True)

    apt_names = [n for n in layouts if n.startswith("Apt")]
    out = []
    out.append("// AUTO-GENERATED from Burnout Revenge B4Extern.pdb (Apt 0.19.02, Xenon/PPC).")
    out.append("// REFERENCE ONLY -- version-drift vs Paradise Apt (2008). Do NOT compile into")
    out.append("// b5-decomp/src. Raw ground truth: ../pdb-dump/. Regenerate with")
    out.append("// tools/apt_revenge/generate_apt_headers.py . Layouts are 32-bit (4-byte ptr).")
    out.append("#pragma once")
    out.append("")
    out.append(f"// {len(apt_names)} Apt types, {sum(len(v) for k,v in methods.items() if k.startswith('Apt'))} methods.")
    out.append("")
    # forward declarations for all Apt types
    for n in apt_names:
        out.append(f"{layouts[n]['kind']} {n};")
    out.append("")

    for name in apt_names:
        e = layouts[name]
        meths = methods.get(name, [])
        hdr = f"{e['kind']} {name}"
        if e["bases"]:
            hdr += " : " + ", ".join(f"public {b}" for b in e["bases"])
        out.append(f"// ---- {name}  (sizeof = {e['size']}) ----")
        out.append(hdr + " {")
        base_set = set(e["bases"])
        emitted = False
        for off, size, kind, rest, subs in direct_members(e):
            # skip the base-class rows (their members belong to the base's own header)
            if kind == "base":
                continue
            for line in render_member(off, size, kind, rest, subs):
                out.append(line)
            emitted = True
        if meths:
            out.append("    // --- methods (address @ B4Extern) ---")
            for addr, sig in meths:
                out.append(f"    // 0x{addr}: {sig}")
            emitted = True
        if not emitted:
            out.append("    // (no direct members; see bases / raw dump)")
        out.append("};")
        out.append(f"// static_assert(sizeof({name}) == {e['size']});  // 32-bit console layout")
        out.append("")

    outfile = OUTDIR / "apt_types.gen.h"
    outfile.write_text("\n".join(out))

    # VA-based address allowlist for the IDA per-function export (idat +
    # tools/ida/export_all.py via EXPORT_ADDR_FILE). VAs = RVA + IMAGE_BASE. Covers
    # ALL Apt functions (incl. struct/helper classes with no data layout, e.g.
    # AptActionInterpreter), not just the laid-out classes emitted above.
    vas = sorted({int(a, 16) for funcs in methods.values() for a, _ in funcs})
    (DUMP / "apt_addrs.txt").write_text("\n".join(f"0x{v:x}" for v in vas) + "\n")
    print(f"wrote {outfile}  ({len(apt_names)} types, "
          f"{sum(len(methods.get(n, [])) for n in apt_names)} methods)")
    print(f"wrote {DUMP/'apt_addrs.txt'}  ({len(vas)} unique VAs)")


if __name__ == "__main__":
    main()
