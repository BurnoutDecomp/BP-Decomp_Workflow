#!/usr/bin/env python3
"""Does this function actually have a BODY in the tree?

WHY THIS EXISTS (2026-08-29). progress/status.json marks 21,245 of its 21,254 function rows
"reviewed". It is the DEFAULT state, not a verdict, and it says NOTHING about whether a body
exists. Five separate waves read it as evidence and lost time; one shipped a declaration whose
definition did not exist and only the exe LINK caught it.

Measured examples that are marked reviewed and have zero definitions anywhere:
    BrnGame::BrnGameModule::BridgeDirectorToGui
    BrnGui::EffectsArbitrator::StartHook
    BrnGui::EffectsArbitrator::LookupColourCube

So: ask the tree, not the ledger.

usage:  python tools/re/hasbody.py <Class::Method> [more...]
        python tools/re/hasbody.py --status <Class::Method>    (also print the ledger's claim,
                                                                for contrast)
Exit code 1 if any name has no definition.

NOTE: a bare `grep name(` is not a substitute -- a wave got a fact backwards this week because
`grep | head -5` returned five COMMENT hits and cut off the real definition. This searches for a
definition form (`Type Class::Method(`) and reports comment-only matches separately.
"""
import json, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, "b5-decomp", "src")


def find(qname):
    """Return (definition_files, mention_files) for Class::Method or a bare method."""
    meth = qname.split("::")[-1]
    cls = qname.split("::")[-2] if "::" in qname else None
    pat = (cls + "::" + meth) if cls else ("::" + meth)
    try:
        out = subprocess.run(
            ["grep", "-rn", "--include=*.cpp", "--include=*.h", pat, SRC],
            capture_output=True, text=True, timeout=180).stdout
    except Exception as exc:
        print("grep failed:", exc)
        return [], []
    defs, mentions = [], []
    for line in out.splitlines():
        # ⛔ NOT line.split(":", 2) -- SRC is an ABSOLUTE WINDOWS path, so the drive letter's
        # colon eats the first field: "D:\...\x.cpp:113:body" split into ("D", "\...x.cpp",
        # "113:body"). The line number then stays GLUED to the front of the text, so the character
        # preceding a definition that starts at column 0 is ':' -- which no "looks like a definition"
        # test accepts. Measured 2026-08-29: it reported a real body as NO DEFINITION IN THE TREE.
        # It only ever bit column-0 definitions, because "void Foo::Bar(" still offers a space.
        m = re.match(r"^(.*?):(\d+):(.*)$", line)
        if not m:
            continue
        path, _, text = m.group(1), m.group(2), m.group(3)
        stripped = text.strip()
        if stripped.startswith(("//", "*", "/*")):
            mentions.append(line)
            continue
        # a definition looks like  <something> Class::Method(   -- not a call, not a declaration
        # ⚠️ the qualified name may start the line, with the return type on the PREVIOUS one:
        #     bool
        #     BoostBurnout5::AreWeAllowedToBoost(...)
        # Requiring a character before it made those read as MENTIONS -- a false negative that
        # told a wave a real body did not exist (measured 2026-08-29). A qualified CALL never
        # sits at column 0 (statements are inside a function, hence indented), so anchoring at
        # ^ strictly removes false negatives without admitting call sites.
        if re.search(r"(?:^|[\w>&*\s])" + re.escape(pat) + r"\s*\(", text) and ";" not in text.split("(")[0]:
            defs.append(line)
        else:
            mentions.append(line)
    return defs, mentions


def ledger(qname):
    try:
        d = json.load(open(os.path.join(REPO, "progress", "status.json"), encoding="utf-8"))
    except Exception:
        return None
    f = d.get("func", {})
    if qname in f:
        return f[qname].get("status")
    for k, v in f.items():
        if k.endswith("::" + qname.split("::")[-1]):
            return v.get("status") + "  (matched " + k + ")"
    return None


def main(argv):
    show_status = "--status" in argv
    names = [a for a in argv if not a.startswith("--")]
    if not names:
        print(__doc__)
        return 2
    bad = 0
    for qname in names:
        defs, mentions = find(qname)
        verdict = "HAS BODY" if defs else "** NO DEFINITION IN THE TREE **"
        print(qname + ": " + verdict)
        for d in defs[:3]:
            print("    def: " + d[:140])
        if not defs and mentions:
            print("    (" + str(len(mentions)) + " mention(s), comments/declarations only)")
            for m in mentions[:2]:
                print("    ...  " + m[:140])
        if show_status:
            print("    ledger says: " + str(ledger(qname))
                  + "   <- remember: 'reviewed' is the default on 21,245 of 21,254 rows")
        if not defs:
            bad = 1
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
