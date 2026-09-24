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
# 2026-09-24: bodies also live under b5-decomp/vendor (e.g. rw::physics::Quaternion in
# vendor/renderware/src/rw/physics/Quaternion.cpp, mounted as %VEN%) -- search both roots.
ROOTS = [SRC, os.path.join(REPO, "b5-decomp", "vendor")]


def find(qname):
    """Return (definition_files, mention_files) for Class::Method or a bare method."""
    meth = qname.split("::")[-1]
    cls = qname.split("::")[-2] if "::" in qname else None
    pat = (cls + "::" + meth) if cls else ("::" + meth)
    try:
        # ⛔ NOT text=True. A handful of committed sources carry bytes that are not valid in the
        # console's ANSI code page (a stray 0x90 in one of the ChallengeManager TUs, for one), and
        # text=True decodes grep's whole output with locale.getpreferredencoding() -- so the
        # decoder raised UnicodeDecodeError INSIDE subprocess's reader thread and the tool died
        # with a traceback instead of an answer. Measured 2026-08-29 on
        # `hasbody.py BrnGameModule::TranslateGameActionsToGuiEvents`: the crash is a bad answer
        # dressed as a tool failure, and the previous defect in this same function was also
        # "reports something other than what its name says".
        out = subprocess.run(
            ["grep", "-rn", "--include=*.cpp", "--include=*.h", "--include=*.hpp", pat] + ROOTS,
            capture_output=True, timeout=180).stdout.decode("utf-8", "replace")
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
        if stripped.startswith(("//", "*", "/*", "#")):
            mentions.append(line)
            continue
        # Only the CODE part of the line counts. 2026-09-24: `#include "...BrnMath.h"  // BrnMath::IsNormal(...)`
        # and `x = y;  // see Foo::Bar(` were read as definitions (a trailing comment after code).
        code = text.split("//", 1)[0]
        # a definition looks like  <something> Class::Method(   -- not a call, not a declaration
        # ⚠️ the qualified name may start the line, with the return type on the PREVIOUS one:
        #     bool
        #     BoostBurnout5::AreWeAllowedToBoost(...)
        # Requiring a character before it made those read as MENTIONS -- a false negative that
        # told a wave a real body did not exist (measured 2026-08-29).
        # ⚠️ 2026-09-24: it may also carry a NAMESPACE qualifier in front of the class,
        #     void
        #     CgsSystem::TimerStatusInterface::Clear()
        # -- the character before the pattern is then ':' and the old class [\w>&*\s] rejected it:
        # "NO DEFINITION" for a real body (FX-XLANE, crash parity wave 5). The old class also let ANY
        # word character precede the class name, so `RaceCar::Update` matched `ActiveRaceCar::Update(`
        # (a suffix hit): now the pattern must follow the line start, whitespace, a return-type
        # character (> & *) or a `::` qualifier -- and, for a bare `::Method` query, an identifier.
        before = r"(?:^|(?<=[\s>&*])|(?<=::)" + (r"|(?<=\w)" if not cls else "") + r")"
        hit = re.search(before + re.escape(pat) + r"\s*\(", code)
        prefix = code[:hit.start()] if hit else ""
        # A call or a declaration, not a definition: the statement ends on this line (`;`), or the
        # text in front of the name is an expression (`= ( , ! ? return new ...`).
        is_call = (code.rstrip().endswith(";")
                   or re.search(r"[=(),!?;{}|+\-/%^~\[\]\"']", prefix) is not None
                   or re.search(r"\b(?:return|new|delete|throw|case|if|while|for|switch)\b", prefix) is not None)
        if hit and not is_call:
            defs.append(line)
        else:
            mentions.append(line)
    return defs, mentions


def find_unqualified(qname):
    """Fallback for bodies whose definition does not spell `Class::Method` at all: free functions
    inside a `namespace Ns { ... }` block and bodies written inside the class definition. Search the
    files that open `namespace <Cls>` / `class <Cls>` / `struct <Cls>` for `[type] Method(` whose
    statement opens a `{` before it ends with `;`.
    2026-09-24: `BrnMath::IsNormal` (bodied in a namespace block) only ever read as HAS BODY through
    a false positive -- a trailing comment on an `#include` line."""
    if "::" not in qname:
        return []
    meth = qname.split("::")[-1]
    cls = qname.split("::")[-2]
    try:
        files = subprocess.run(
            ["grep", "-rlE", "--include=*.cpp", "--include=*.h", "--include=*.hpp",
             # POSIX classes, not \s / \b: the grep that Python finds on PATH here matched nothing
             # with them (measured 2026-09-24), while the same pattern worked from bash.
             r"(namespace|class|struct)[[:space:]]+" + re.escape(cls) + r"([^[:alnum:]_]|$)"] + ROOTS,
            capture_output=True, timeout=180).stdout.decode("utf-8", "replace").split()
    except Exception:
        return []
    defs = []
    sig = re.compile(r"^\s*(?:[\w:<>,*&~]+\s+)*[*&]*" + re.escape(meth) + r"\s*\(")
    for path in files:
        try:
            lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        for i, text in enumerate(lines):
            code = text.split("//", 1)[0]
            if not sig.match(code) or code.lstrip().startswith(("#", "*", "return ", "else ")):
                continue
            # the statement must reach a `{` before a `;` (a body, not a declaration or a call)
            tail = code[code.index("(") :]
            for nxt in lines[i + 1 : i + 6]:
                if "{" in tail or ";" in tail:
                    break
                tail += " " + nxt.split("//", 1)[0]
            brace, semi = tail.find("{"), tail.find(";")
            if brace >= 0 and (semi < 0 or brace < semi):
                defs.append(f"{path}:{i + 1}:{text}")
    return defs


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
        if not defs:
            loose = find_unqualified(qname)
            if loose:
                defs = loose
                verdict = ("HAS BODY (unqualified: inside a namespace/class block of that name -- check the "
                           "scope and the signature, an overload of another class can match too)")
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
