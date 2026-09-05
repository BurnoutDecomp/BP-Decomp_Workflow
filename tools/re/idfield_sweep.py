#!/usr/bin/env python3
"""idfield_sweep.py -- which ID FIELD does each reconstructed body index/key with?

WHY THIS EXISTS.  On 2026-09-05 waking the hinge path exposed an access violation whose
root cause was a *field* confusion, not a logic error: DeformableObject::DoBodyPart-
WorldContactGeneration took its triangle-cache slot from mGlobalEntityId (console +0x6718,
the WORLD entity index) where the console reads mHandlingBodyID (console +0x6710, the
PHYSICS-BODY index).  TriangleCacheManager::Prepare allocates exactly 298 slots and the
witness printed `ent 404 -> slot 1`, so the old spelling wrote 106 slots past the array.
The same confusion is SILENT wherever the id is a lookup KEY rather than a subscript: the
lookup simply misses and a behaviour quietly disappears.

Nothing in the compile gate, the parity fingerprint or the faithfulness lint can see this:
both spellings are named members of the same object with the same type.  Only the asm can.

WHAT IT DOES.  For every reconstructed body under the given source roots it pairs the C++
with its X360 original (progress/identity.json -> .ida-exports/<build>/0x<addr>.json) and
compares, per function:

    console: does the asm load  +0x6710 (mHandlingBodyID) / +0x6718 (mGlobalEntityId)?
    ours:    does the body name mHandlingBodyID / mGlobalEntityId (or their accessors)?

and reports the four disagreement classes.  The interesting one is
"ours=GLOBAL console=HANDLING" -- that is the shape of the bug above.

USAGE
    python tools/re/idfield_sweep.py                       # the deformation lane
    python tools/re/idfield_sweep.py --root src/GameSource/Physics --all
    python tools/re/idfield_sweep.py --offsets 0x6710,0x6718 --members mHandlingBodyID,...

CAVEATS, STATED SO THE NUMBER IS NOT OVER-READ
  * The C++ side is matched by a `Class::Method(` definition scan, so a body the console
    INLINED into its caller is attributed to whichever of our functions spells it.  A
    function our tree splits differently from the console will read as a mismatch; each hit
    still has to be read against the asm by hand.  This tool NARROWS, it does not decide.
  * A function whose console body reads NEITHER field is not evidence of anything; those
    are counted and dropped.
"""
import argparse
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IDENTITY = os.path.join(REPO, "progress", "identity.json")
EXPORTS = os.path.join(REPO, ".ida-exports", "BURNOUT_X360_ARTIST.XEX")
SUBMODULE = os.path.join(REPO, "b5-decomp")

DEFAULT_ROOTS = [
    "src/GameSource/Physics/DeformationManager",
    "src/GameSource/Physics/VehicleManager",
]

# offset -> the member it is on a DeformableObject (the console field), and the spellings
# our C++ uses for it.
DEFAULT_FIELDS = [
    ("HANDLING", "0x6710",
     r"(mHandlingBodyID|GetHandlingBodyId|GetHandlingBodyID|GetHandlingEntityId"
     r"|GetHandlingBodyVolumeInstanceId|GetHandlingBodyIdHighByte)"),
    ("GLOBAL", "0x6718",
     r"(mGlobalEntityId|GetGlobalEntityId)"),
]

DEF_RE = re.compile(
    r'^[ \t]*(?:[A-Za-z_][\w:<>,\*&\s]*?[\s\*&])?'
    r'([A-Za-z_]\w*)::([~A-Za-z_]\w*)\s*\(')


def load_identity():
    with open(IDENTITY, "r", encoding="utf-8") as fh:
        return json.load(fh)


def addr_of(identity, qualified):
    """Return the X360 address for a normalized qualified name, or None."""
    row = identity.get(qualified)
    if not isinstance(row, dict):
        return None
    addrs = row.get("x360_addrs")
    if isinstance(addrs, list) and addrs:
        return addrs[0]            # overloads collapse; the table flags the collision
    return None


def asm_of(addr):
    path = os.path.join(EXPORTS, "%s.json" % addr)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return json.load(fh).get("assembly", "")


def function_bodies(path):
    """Very small C++ definition splitter: yields (class, method, body_text)."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    marks = []
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("//") or stripped.startswith("*"):
            continue
        m = DEF_RE.match(line)
        if m:
            marks.append((i, m.group(1), m.group(2)))
    for n, (start, cls, method) in enumerate(marks):
        end = marks[n + 1][0] if n + 1 < len(marks) else len(lines)
        body = []
        for line in lines[start:end]:
            body.append(line.split("//")[0])
        yield cls, method, "\n".join(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", action="append", default=None,
                    help="source root under b5-decomp (repeatable)")
    ap.add_argument("--all", action="store_true",
                    help="print every paired function, not just the disagreements")
    args = ap.parse_args()

    roots = args.root or DEFAULT_ROOTS
    identity = load_identity()

    files = []
    for root in roots:
        base = os.path.join(SUBMODULE, root)
        for dp, _dn, fn in os.walk(base):
            for f in fn:
                if f.endswith(".cpp"):
                    files.append(os.path.join(dp, f))
    files.sort()

    n_bodies = 0
    n_paired = 0
    n_console_uses = 0
    findings = []
    unpaired = []

    for path in files:
        rel = os.path.relpath(path, SUBMODULE).replace(os.sep, "/")
        for cls, method, body in function_bodies(path):
            n_bodies += 1
            addr = None
            qualified = None
            for prefix in ("BrnPhysics::Deformation::", "BrnPhysics::", "BrnPhysics::Vehicle::", ""):
                cand = "%s%s::%s" % (prefix, cls, method)
                a = addr_of(identity, cand)
                if a:
                    addr, qualified = a, cand
                    break
            if addr is None:
                unpaired.append("%s  %s::%s" % (rel, cls, method))
                continue
            asm = asm_of(addr)
            if asm is None:
                unpaired.append("%s  %s::%s (no export)" % (rel, cls, method))
                continue
            n_paired += 1

            console = set()
            ours = set()
            for name, off, spell in DEFAULT_FIELDS:
                if off in asm:
                    console.add(name)
                if re.search(spell, body):
                    ours.add(name)
            if console:
                n_console_uses += 1
            if not console and not ours:
                continue
            if console != ours:
                findings.append((rel, qualified, addr,
                                 "|".join(sorted(ours)) or "-",
                                 "|".join(sorted(console)) or "-"))
            elif args.all:
                findings.append((rel, qualified, addr, "ok", "ok"))

    print("ROOTS                : %s" % ", ".join(roots))
    print("C++ bodies scanned   : %d" % n_bodies)
    print("paired with an export: %d" % n_paired)
    print("  of which the console reads one of the id fields: %d" % n_console_uses)
    print("unpaired (inlined / split / no export): %d" % len(unpaired))
    print("")
    print("%-58s %-9s %-14s %s" % ("FUNCTION", "ADDR", "OURS", "CONSOLE"))
    for rel, q, addr, ours, console in findings:
        print("%-58s %-9s %-14s %s" % (q[-58:], addr, ours, console))
    print("")
    print("disagreements: %d" % len([f for f in findings if f[3] != "ok"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
