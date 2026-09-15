#!/usr/bin/env python3
"""
fold_partfiles.py -- fold wave partfiles (<Parent>_w<Wave>_<NN>.cpp) back into their parent TU.

WHY (b5-decomp issue #20). Recovery waves land a class's bodies in per-wave partfiles so that
parallel waves never collide inside one giant .cpp. That split is deliberate and stays. What was
missing is the OTHER half of the cycle: nothing ever folded the partfiles back, so 300+ of them
(~90k lines, ~7.5% of src) had become permanent -- not the shipped file layout, 200+ hand-written
mount lines in the shared build_game_exe.bat, and no way to open <Parent>.cpp and see the class.

WHAT A FOLD DOES (one parent per run):
  1. finds <dir>/<Parent>.cpp and every <dir>/<Parent>_w*.cpp partfile;
  2. orders the partfiles by their MOUNT order in tools/build/build_game_exe.bat (unmounted ones
     are excluded unless --include-unmounted, in which case they go last, alphabetically);
  3. for each partfile splits it into its HEADER comment block (the address annotations -- these
     are the point of the partfile and must survive), its #include lines, and its BODY;
  4. appends every include the parent does not already carry to the parent's include block, and
     appends each partfile's header + body after a FOLDED-FROM banner (C++ lets a namespace be
     reopened, so the bodies keep their own `namespace X { ... }` wrappers verbatim);
  5. runs the per-TU compile gate (tools/work/verify.py compile_gate) on the folded parent and
     REFUSES to touch anything if it fails (duplicate file-scope helpers between two partfiles
     surface here as C2084/C2086/C2374 -- dedupe by hand, then re-run);
  6. on a pass: writes the parent, `git rm`s the partfiles, strips their mount lines from the .bat
     (CRLF preserved -- never edit that file with LF tools), and prints the two commits to make.

CONVENTION (pinned in AGENTS.md by the same change): <Parent>_w<Wave>_<NN>.cpp, Wave = one
capital letter plus optional digits (B, C, Q4, T1, SQ1 ...), NN = two digits. Older ad-hoc
suffixes (_wB_res, _wRR, _wH3b, _wG_Bridges_01 ...) are still recognised for folding, and
`scan` flags them so they can be retired.

USAGE (from the repo root):
  python tools/work/fold_partfiles.py scan                  # every parent with partfiles
  python tools/work/fold_partfiles.py audit                 # the UNMOUNTED partfiles, classified
  python tools/work/fold_partfiles.py fold BrnChallengeManager [--dry-run] [--include-unmounted] [--no-gate]
  python tools/work/fold_partfiles.py check [--baseline]    # the ratchet: partfile count must not grow
"""
import argparse
import collections
import datetime
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
B5 = os.path.join(REPO, "b5-decomp")
SRC = os.path.join(B5, "src")
BAT = os.path.join(REPO, "tools", "build", "build_game_exe.bat")
BASELINE = os.path.join(REPO, "progress", "partfile_baseline.json")

# <Parent>_w<Wave>[_<rest>].cpp -- Wave = capital letter(s) + optional digits [+ one lowercase]
PART_RE = re.compile(r"^(?P<parent>.+?)_w(?P<wave>[A-Z]+[0-9]*[a-z]?)(?:_(?P<rest>[^.]+))?\.cpp$")
CANON_RE = re.compile(r"^.+?_w[A-Z]+[0-9]*_[0-9]{2}\.cpp$")


def read_text(path):
    raw = open(path, "rb").read()
    return raw.decode("utf-8"), (b"\r\n" in raw)


def write_text(path, text, crlf):
    text = text.replace("\r\n", "\n")
    if crlf:
        text = text.replace("\n", "\r\n")
    open(path, "wb").write(text.encode("utf-8"))


def find_partfiles():
    """-> list of (dir, filename, parent_base, wave, rest) for every partfile under src/."""
    out = []
    for dp, _dn, fn in os.walk(SRC):
        for f in fn:
            if not f.endswith(".cpp"):
                continue
            m = PART_RE.match(f)
            if m:
                out.append((dp, f, m.group("parent"), m.group("wave"), m.group("rest")))
    return out


def mount_order():
    """-> {src-relative forward-slash path: line index in the .bat} for every mounted TU."""
    bat, _ = read_text(BAT)
    order = {}
    for i, line in enumerate(bat.replace("\r\n", "\n").split("\n")):
        m = re.match(r'\s*echo "%SRC%\\(.+?)"\s*$', line)
        if m:
            order[m.group(1).replace("\\", "/")] = i
    return order


def rel_src(path):
    return os.path.relpath(path, SRC).replace("\\", "/")


def cmd_scan(_args):
    parts = find_partfiles()
    mounted = mount_order()
    by_parent = collections.defaultdict(list)
    for dp, f, parent, wave, rest in parts:
        by_parent[(dp, parent)].append((f, wave, rest))
    rows = []
    total_lines = 0
    for (dp, parent), lst in by_parent.items():
        lines = 0
        n_mounted = 0
        odd = 0
        for f, wave, rest in lst:
            p = os.path.join(dp, f)
            lines += sum(1 for _ in open(p, "rb"))
            if rel_src(p) in mounted:
                n_mounted += 1
            if not CANON_RE.match(f):
                odd += 1
        total_lines += lines
        has_parent = os.path.exists(os.path.join(dp, parent + ".cpp"))
        rows.append((len(lst), parent, rel_src(dp), lines, n_mounted, odd, has_parent))
    rows.sort(reverse=True)
    print(f"{len(parts)} partfiles, {total_lines} lines, {len(rows)} parents")
    print(f"{'files':>5} {'mounted':>7} {'odd':>3} {'lines':>6}  parent  (dir)")
    for n, parent, d, lines, n_mounted, odd, has_parent in rows:
        flag = "" if has_parent else "   ** NO <Parent>.cpp **"
        print(f"{n:5d} {n_mounted:7d} {odd:3d} {lines:6d}  {parent}  ({d}){flag}")


def classify(rel):
    low = rel.lower()
    if "x360" in low or "/sdks/" in low or "massivead" in low or "realmc" in low or "xcam" in low \
            or "xgraphics" in low:
        return "platform-x360/SDK (excluded from the PC build by design)"
    if "online" in low or "network" in low or "enteronline" in low or "scoreboards" in low \
            or "playerstats" in low or "gameroom" in low:
        return "online (no PC network layer yet)"
    return "UNCLASSIFIED -- decide: mount it or delete it"


def cmd_audit(_args):
    parts = find_partfiles()
    mounted = mount_order()
    unm = [(dp, f) for dp, f, *_ in parts if rel_src(os.path.join(dp, f)) not in mounted]
    unm.sort(key=lambda t: rel_src(os.path.join(*t)))
    print(f"{len(unm)} of {len(parts)} partfiles are NOT mounted in build_game_exe.bat")
    groups = collections.defaultdict(list)
    for dp, f in unm:
        rel = rel_src(os.path.join(dp, f))
        groups[classify(rel)].append(rel)
    for k in sorted(groups):
        print(f"\n[{k}]  ({len(groups[k])})")
        for rel in groups[k]:
            print("   " + rel)


def split_partfile(text):
    """-> (header_lines, include_lines, body_lines). Header = the leading run of comment/blank
    lines. Includes = every `#include` line between the header and the first code line that is
    not an include/blank/comment. Body = everything after the last include (verbatim)."""
    lines = text.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines) and (lines[i].strip() == "" or lines[i].lstrip().startswith("//")):
        i += 1
    header = lines[:i]
    includes = []
    leftovers = []
    last_inc = i
    j = i
    while j < len(lines):
        s = lines[j].strip()
        if s.startswith("#include"):
            includes.append(lines[j])
            last_inc = j + 1
        elif s == "" or s.startswith("//"):
            pass
        elif s.startswith("#") or s.startswith("using "):
            # a #define / #if / using in the include region: keep it, in order, at the body top
            leftovers.append(lines[j])
            last_inc = j + 1
        else:
            break
        j += 1
    body = lines[last_inc:]
    return header, includes, leftovers, body


def include_key(line):
    m = re.search(r'#include\s*[<"]([^">]+)[">]', line)
    return m.group(1).replace("\\", "/").lower() if m else line.strip()


def compile_gate(parent_path):
    sys.path.insert(0, os.path.join(REPO, "tools", "work"))
    import verify  # noqa: E402  (tools/work/verify.py)
    return verify.compile_gate([parent_path])


def cmd_fold(args):
    parts = [t for t in find_partfiles() if t[2] == args.parent]
    if not parts:
        sys.exit(f"no partfiles named {args.parent}_w*.cpp under src/")
    dirs = {t[0] for t in parts}
    if len(dirs) != 1:
        sys.exit(f"{args.parent} partfiles live in more than one directory: {sorted(dirs)}")
    d = dirs.pop()
    parent_path = os.path.join(d, args.parent + ".cpp")
    if not os.path.exists(parent_path):
        sys.exit(f"no parent TU at {parent_path} -- create it first (or the class has another home)")

    mounted = mount_order()
    parent_rel = rel_src(parent_path)
    if parent_rel not in mounted:
        print(f"WARNING: the parent {parent_rel} is not mounted; folding into it changes nothing "
              f"in the exe until it is")
    ordered, unmounted = [], []
    for dp, f, *_ in parts:
        rel = rel_src(os.path.join(dp, f))
        (ordered if rel in mounted else unmounted).append((mounted.get(rel, 1 << 30), f))
    ordered.sort()
    unmounted.sort(key=lambda t: t[1])
    if unmounted and not args.include_unmounted:
        print(f"NOTE: {len(unmounted)} unmounted partfile(s) left alone (pass --include-unmounted):")
        for _, f in unmounted:
            print("   " + f)
    victims = [f for _, f in ordered] + ([f for _, f in unmounted] if args.include_unmounted else [])
    if not victims:
        sys.exit("nothing to fold")

    parent_text, crlf = read_text(parent_path)
    plines = parent_text.replace("\r\n", "\n").split("\n")
    have = {include_key(l) for l in plines if l.strip().startswith("#include")}
    last_inc_idx = max((i for i, l in enumerate(plines) if l.strip().startswith("#include")), default=-1)
    if last_inc_idx < 0:
        sys.exit("the parent has no #include block to extend")

    new_includes = []
    appendix = []
    stamp = datetime.date.today().isoformat()
    for f in victims:
        text, _ = read_text(os.path.join(d, f))
        header, includes, leftovers, body = split_partfile(text)
        for inc in includes:
            k = include_key(inc)
            if k not in have:
                have.add(k)
                new_includes.append(inc)
        m = PART_RE.match(f)
        wave = m.group("wave") if m else "?"
        appendix.append("")
        appendix.append("// " + "=" * 76)
        appendix.append(f"// FOLDED FROM {f} (wave {wave}) on {stamp} by tools/work/fold_partfiles.py.")
        appendix.append("// The partfile's own header follows verbatim (its address annotations are the")
        appendix.append("// evidence trail); its bodies come after it.")
        appendix.append("// " + "=" * 76)
        appendix.extend(header)
        if leftovers:
            appendix.append("// (preprocessor / using lines carried from the partfile's include region)")
            appendix.extend(leftovers)
        appendix.extend(body)
        while appendix and appendix[-1].strip() == "":
            appendix.pop()

    folded = plines[:last_inc_idx + 1]
    if new_includes:
        folded.append("")
        folded.append(f"// includes folded in from the {args.parent}_w*.cpp partfiles ({stamp})")
        folded.extend(new_includes)
    folded.extend(plines[last_inc_idx + 1:])
    while folded and folded[-1].strip() == "":
        folded.pop()
    folded.extend(appendix)
    folded.append("")
    folded_text = "\n".join(folded)

    print(f"fold {args.parent}: {len(victims)} partfile(s), +{len(new_includes)} include(s), "
          f"{len(plines)} -> {len(folded)} lines")
    if args.dry_run:
        out = parent_path + ".folded.txt"
        write_text(out, folded_text, crlf)
        print(f"dry run: wrote {out}; nothing else touched")
        return

    backup = parent_text
    write_text(parent_path, folded_text, crlf)
    if not args.no_gate:
        status, log = compile_gate(parent_path)
        print(f"compile gate: {status}")
        if status == "fail":
            write_text(parent_path, backup, crlf)
            print(log[-4000:])
            sys.exit("gate FAILED -- parent restored, partfiles untouched. Dedupe the reported "
                     "symbols by hand and re-run.")

    # delete the partfiles (tracked -> git rm; untracked -> unlink)
    for f in victims:
        p = os.path.join(d, f)
        r = subprocess.run(["git", "-C", B5, "rm", "-q", "--", os.path.relpath(p, B5)],
                           capture_output=True, text=True)
        if r.returncode != 0 and os.path.exists(p):
            os.remove(p)

    # strip the mount lines, CRLF preserved
    bat, bat_crlf = read_text(BAT)
    blines = bat.replace("\r\n", "\n").split("\n")
    victim_rels = {rel_src(os.path.join(d, f)) for f in victims}
    kept = []
    removed = 0
    parent_added = False
    for line in blines:
        m = re.match(r'\s*echo "%SRC%\\(.+?)"\s*$', line)
        if m and m.group(1).replace("\\", "/") in victim_rels:
            removed += 1
            # A parent that was never mounted (only its partfiles were) takes the FIRST
            # partfile's mount slot, or the bodies just moved into a TU the link never sees.
            if parent_rel not in mounted and not parent_added:
                indent = line[:len(line) - len(line.lstrip())]
                kept.append(f'{indent}echo "%SRC%\\{parent_rel.replace("/", chr(92))}"')
                parent_added = True
            continue
        kept.append(line)
    write_text(BAT, "\n".join(kept), bat_crlf)
    cr = open(BAT, "rb").read().count(b"\r\n")
    print(f"mount lines removed: {removed}"
          + ("; the parent's mount line ADDED in the first partfile's slot" if parent_added else "")
          + f"; {BAT} now {cr} CRLF lines")
    print("\nNext:")
    print(f"  git -C b5-decomp add {os.path.relpath(parent_path, B5)}  && commit: "
          f"'fold: {args.parent} partfiles back into {args.parent}.cpp (issue #20)'")
    print("  git add tools/build/build_game_exe.bat  (that file only) && commit the mount change")
    print("  then build the exe -- the fold changed which TU carries the bodies, so LINK it.")


def cmd_check(args):
    import json
    parts = find_partfiles()
    count = len(parts)
    odd = sorted(f for _, f, *_ in parts if not CANON_RE.match(f))
    if args.baseline:
        json.dump({"count": count, "odd_names": len(odd)}, open(BASELINE, "w"), indent=2)
        print(f"baseline written: {count} partfiles, {len(odd)} off-convention names")
        return
    if not os.path.exists(BASELINE):
        print(f"no baseline at {BASELINE}; {count} partfiles now ({len(odd)} off-convention). "
              f"Run with --baseline to pin.")
        return
    base = json.load(open(BASELINE))
    print(f"partfiles: {count} (baseline {base['count']}); off-convention names: {len(odd)} "
          f"(baseline {base.get('odd_names', 0)})")
    if count > base["count"] or len(odd) > base.get("odd_names", 0):
        for f in odd:
            print("   off-convention: " + f)
        sys.exit("RATCHET: the partfile population grew -- fold a parent back before landing more, "
                 "or re-baseline deliberately (--baseline) with a reason in the commit.")
    print("ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scan").set_defaults(fn=cmd_scan)
    sub.add_parser("audit").set_defaults(fn=cmd_audit)
    f = sub.add_parser("fold")
    f.add_argument("parent")
    f.add_argument("--dry-run", action="store_true")
    f.add_argument("--include-unmounted", action="store_true")
    f.add_argument("--no-gate", action="store_true")
    f.set_defaults(fn=cmd_fold)
    c = sub.add_parser("check")
    c.add_argument("--baseline", action="store_true")
    c.set_defaults(fn=cmd_check)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
