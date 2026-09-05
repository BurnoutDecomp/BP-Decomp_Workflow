#!/usr/bin/env python3
"""vdispatch_sweep.py -- audit EVERY virtual dispatch on a reconstructed subsystem.

    python tools/re/vdispatch_sweep.py GameSource/Physics GameSource/Vehicle ...

Pairs each reconstructed body in the given b5-decomp/src subtrees with its X360 original and
prints, per function, the console's dispatch slots next to the virtual calls our C++ makes --
so a wrong slot (the defect class that produced FOUR silent behaviour losses in the crash
subsystem in one day; see vdispatch_audit.py) is visible without reading an `lwz` by hand.

OUR SIDE. A "virtual call" is a call `x->Method(` / `x.Method(` whose Method is declared
`virtual` somewhere in b5-decomp/src (the header set is scanned once). This over-collects
slightly -- a non-virtual same-named method on an unrelated class counts -- and that is the safe
direction for an audit.

CONSOLE SIDE. vdispatch_audit.dispatches() over the exported `assembly` listing.

The output is a WORKSHEET, not a verdict: matching counts do not prove matching slots, and the
tool cannot type the dispatch base. Read the rows where the counts differ first; then read the
rows where they agree but the names look implausible for the slot.
"""
import sys, os, re, json, glob, collections

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, "b5-decomp", "src")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vdispatch_audit as VA

DEF = re.compile(r"^[\w:<>&*\s]*?\b([A-Z]\w+)::(~?\w+)\s*\(", re.M)
VIRT = re.compile(r"^\s*(?:\[\[[^\]]*\]\]\s*)?virtual\b[^;{]*?\b(~?\w+)\s*\(", re.M)
# `p->Method(` / `r.Method(` and the IMPLICIT-THIS form `Method(` -- the implicit form is what a
# virtual call on `this` looks like in every reconstructed body, and leaving it out made the
# "ours" column read 0 for functions that plainly do dispatch (VehiclePhysics::UpdateCrashing
# has three IsCrashingNormally() calls and scored 0 before this).
CALL = re.compile(r"(?:(?:->|\.)\s*|(?<![\w.>:]))(\w+)\s*\(")


def virtual_names():
    names = set()
    for p in glob.glob(os.path.join(SRC, "**", "*.h"), recursive=True):
        try:
            t = open(p, "r", encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in VIRT.finditer(t):
            names.add(m.group(1))
    return names


def strip_comments(t):
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    return re.sub(r"//[^\n]*", "", t)


def bodies(path):
    """-> [(Class, Method, body_text)] for each top-level definition in a .cpp"""
    raw = open(path, "r", encoding="utf-8", errors="replace").read()
    txt = strip_comments(raw)
    out = []
    for m in DEF.finditer(txt):
        i = txt.find("{", m.end() - 1)
        if i < 0:
            continue
        depth, j = 0, i
        while j < len(txt):
            if txt[j] == "{":
                depth += 1
            elif txt[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append((m.group(1), m.group(2), txt[i:j]))
    return out


def addr_index():
    raw = json.load(open(os.path.join(REPO, "progress", "identity.json"), "r", encoding="utf-8"))
    by_tail = collections.defaultdict(list)
    for name, row in raw.items():
        addrs = (row or {}).get("x360_addrs") or []
        if not addrs:
            continue
        parts = name.split("::")
        if len(parts) >= 2:
            by_tail["::".join(parts[-2:])].append((name, [int(a, 16) for a in addrs]))
    return by_tail


def main():
    subtrees = sys.argv[1:] or ["GameSource/Physics"]
    virt = virtual_names()
    tails = addr_index()
    tot_fn = tot_console = tot_ours = 0
    rows = []
    for st in subtrees:
        for p in sorted(glob.glob(os.path.join(SRC, st, "**", "*.cpp"), recursive=True)):
            for cls, meth, body in bodies(p):
                key = "%s::%s" % (cls, meth)
                cands = tails.get(key)
                if not cands:
                    continue
                name, addrs = cands[0]
                if len(cands) > 1:
                    name = "%s (+%d amb)" % (name, len(cands) - 1)
                ours = [c for c in CALL.findall(body) if c in virt]
                for a in addrs[:1]:
                    _, asm = VA.load_asm(a)
                    if asm is None:
                        continue
                    hits = VA.dispatches(asm)
                    tot_fn += 1
                    tot_console += len(hits)
                    tot_ours += len(ours)
                    rows.append((os.path.relpath(p, SRC).replace("\\", "/"), key, a, hits, ours))
    for rel, key, a, hits, ours in rows:
        slots = ["+0x%02X@%s" % (s, ("0x%08X" % ea)) if s is not None else "?@0x%08X" % ea
                 for ea, s, _b, _l in hits]
        flag = "" if len(hits) == len(ours) else "   <-- COUNT DIFFERS"
        print("%-58s 0x%08X  console %d / ours %d%s" % (key, a, len(hits), len(ours), flag))
        print("      file    %s" % rel)
        if hits:
            print("      console %s" % ", ".join(slots))
            for ea, s, b, _l in hits:
                if s is not None:
                    print("               0x%08X  +0x%02X on %s" % (ea, s, b))
        if ours:
            print("      ours    %s" % ", ".join(ours))
    print()
    print("AUDITED %d reconstructed bodies; %d console CTR dispatches; %d virtual calls in our C++"
          % (tot_fn, tot_console, tot_ours))
    return 0


if __name__ == "__main__":
    sys.exit(main())
