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

WHEN THERE IS NO PARENT TU. `scan` prints `** NO <Parent>.cpp **` for families whose bodies only
ever existed in partfiles. Two shapes, two flags:
  * the class DOES have a home TU under another basename (PropManager's bodies live in
    BrnPropManager.cpp, DispatchBin's in CgsDispatcher.cpp -- the partfile headers say so):
    `--parent-file BrnPropManager`. Nothing is created; the fold is the ordinary one.
  * the class has NO home TU at all (BoostBurnout2, BrnPreRaceFlyBy ...): `--create-parent`
    synthesises <Parent>.cpp from the partfiles in MOUNT order -- a generated banner plus the
    first partfile's own header, then the union of every partfile's #include lines (first
    occurrence wins, order kept), then every partfile's header + body behind the same FOLDED-FROM
    banner an ordinary fold writes. The compile gate runs on it exactly as it does on a fold, and
    the .bat gets the parent's mount line in the FIRST partfile's slot (the created TU must be
    mounted or the bodies leave the exe). --dry-run writes <Parent>.cpp.folded.txt and creates
    nothing.

CONVENTION (pinned in AGENTS.md by the same change): <Parent>_w<Wave>_<NN>.cpp, Wave = one
capital letter plus optional digits (B, C, Q4, T1, SQ1 ...), NN = two digits. Older ad-hoc
suffixes (_wB_res, _wRR, _wH3b, _wG_Bridges_01 ...) are still recognised for folding, and
`scan` flags them so they can be retired.

USAGE (from the repo root):
  python tools/work/fold_partfiles.py scan                  # every parent with partfiles
  python tools/work/fold_partfiles.py audit                 # the UNMOUNTED partfiles, classified
  python tools/work/fold_partfiles.py fold BrnChallengeManager [--dry-run] [--include-unmounted] [--no-gate] [--dedupe-identical]
  python tools/work/fold_partfiles.py fold PropManager --parent-file BrnPropManager   # parent TU has another basename
  python tools/work/fold_partfiles.py fold BrnPreRaceFlyBy --create-parent            # scan printed ** NO <Parent>.cpp **
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


def bat_mentions():
    """Basenames named in the .bat's `rem` commentary -- a partfile that is talked about but not
    mounted was EXCLUDED ON PURPOSE (usually a measured unresolved-external cost), not forgotten."""
    bat, _ = read_text(BAT)
    out = set()
    for line in bat.replace("\r\n", "\n").split("\n"):
        if line.lstrip().lower().startswith("rem"):
            for m in re.finditer(r"([A-Za-z0-9]+_w[A-Z]+[0-9]*[a-z]?(?:_[A-Za-z0-9]+)?)(?:\.cpp)?", line):
                out.add(m.group(1).lower())
    return out


# Families the .bat's rem notes exclude ON PURPOSE (a measured unresolved-external cost); the note
# to read is quoted so the audit does not send anyone re-deriving it.
DELIBERATE = {
    "brngamestatestreetmanager": "build_game_exe.bat 'The REST of the StreetManager family stays out' "
                                 "(score-entry factories / ProcessScoreRequestEvent / road-rules tallies: LNK2019 chains)",
    "brnstreetmanagerdebugcomponent": "build_game_exe.bat 'the embedded StreetManagerDebugComponent's vtable' "
                                      "(16 link-measured externals; two vtable slots gated in BrnBaselineLinkStubs.cpp)",
}
CONTENT_ONLINE = re.compile(r"dirtysdk|dirtysock|LobbyNameCmp|online", re.I)
CONTENT_UNHOMED = re.compile(r"not[- ]yet[- ]homed|un-homed|unhomed", re.I)


def classify(rel, mentioned=frozenset()):
    low = rel.lower()
    base = os.path.splitext(os.path.basename(rel))[0].lower()
    parent = re.sub(r"_w[a-z]+[0-9]*[a-z]?(?:_[^.]+)?$", "", base)
    if parent in DELIBERATE:
        return "deliberately excluded -- " + DELIBERATE[parent]
    if base in mentioned or re.sub(r"_[0-9]{2}$", "", base) in mentioned:
        return "deliberately excluded -- named in build_game_exe.bat's rem notes (read the reason there)"
    if "x360" in low or low.startswith("sdks/") or "/sdks/" in low or "massivead" in low or "realmc" in low             or "xcam" in low or "xgraphics" in low:
        return "platform-x360/SDK (excluded from the PC build by design)"
    if "online" in low or "network" in low or "enteronline" in low or "scoreboards" in low             or "playerstats" in low or "gameroom" in low:
        return "online (no PC network layer yet)"
    # Content sniff of the header comment block (first 40 lines).
    try:
        with open(os.path.join(SRC, rel), encoding="utf-8", errors="replace") as fh:
            head = "".join(fh.readline() for _ in range(40))
    except OSError:
        head = ""
    if CONTENT_ONLINE.search(head):
        return "online (no PC network layer yet) -- by header comment"
    if CONTENT_UNHOMED.search(head):
        return "declares un-homed callees (a link cost) -- home the callees, then mount"
    return "UNCLASSIFIED -- decide: mount it or delete it"


def cmd_audit(_args):
    parts = find_partfiles()
    mounted = mount_order()
    unm = [(dp, f) for dp, f, *_ in parts if rel_src(os.path.join(dp, f)) not in mounted]
    unm.sort(key=lambda t: rel_src(os.path.join(*t)))
    print(f"{len(unm)} of {len(parts)} partfiles are NOT mounted in build_game_exe.bat")
    mentioned = bat_mentions()
    groups = collections.defaultdict(list)
    for dp, f in unm:
        rel = rel_src(os.path.join(dp, f))
        groups[classify(rel, mentioned)].append(rel)
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


# ---------------------------------------------------------------------------------------------
# --dedupe-identical: waves copy the same anonymous-namespace constants / records / helpers into
# several partfiles (KAC_ASSERT_FILE, KI_CHANNEL_*, a GuiEventWrapper payload struct...). Folded
# into one TU they are C2374/C2086/C2011/C2084 redefinitions. When the later copy is TEXTUALLY
# IDENTICAL to the first (comments and whitespace ignored) it is dropped and a one-line marker
# left in its place; a copy that differs in any token is NOT touched -- the fold refuses and names
# it, because two different definitions under one name is exactly the ODR fork this repo's
# history warns about, and only a human can say which one the console has.
# ---------------------------------------------------------------------------------------------
REDEF_RE = re.compile(r"\((\d+)\): error (C2374|C2086|C2011|C2084|C2371|C2365)\b")
KEYWORDS = {"const", "static", "struct", "class", "enum", "char", "int", "unsigned", "signed",
            "s32", "u32", "s16", "u16", "s8", "u8", "f32", "f64", "bool", "void", "inline", "extern",
            "namespace", "anonymous"}


def redef_name(err_line):
    m = re.search(r"error C\d+: (.*)$", err_line)
    if not m:
        return None
    msg = m.group(1)
    # C2374/C2086/C2011: "'<qualified name>[N]': redefinition ..."; C2084: "function '<name>(<params>)'
    # already has a body". Cut the tail, then a parameter list, then take the last identifier.
    msg = re.sub(r"(': |' already has a body).*$", "", msg)
    if "(" in msg:
        msg = msg[:msg.index("(")]
    idents = [w for w in re.findall(r"[A-Za-z_]\w*", msg) if w not in KEYWORDS]
    return idents[-1] if idents else None


def extract_block(lines, i):
    """(start, end) inclusive line indices of the definition that begins at line i: contiguous //
    comment lines directly above are part of it; it ends at the first ';' at brace depth 0, or at
    the line that closes its outermost brace (struct/function) -- a trailing '};' included."""
    start = i
    # A declaration may begin on earlier lines (a return type on its own line: the compiler reports
    # the line that carries the NAME). Walk up over non-blank, non-comment lines that do not end a
    # statement or open/close a block, then over the comment lines directly above.
    while start > 0:
        prev = re.sub(r"//.*$", "", lines[start - 1]).strip()   # a trailing comment hides the ';'
        if not prev or prev.endswith((";", "{", "}")) or prev.startswith("#"):
            break
        start -= 1
    while start > 0 and lines[start - 1].strip().startswith("//"):
        start -= 1
    depth, seen_brace, j = 0, False, i
    while j < len(lines):
        code = re.sub(r"//.*$", "", lines[j])   # a trailing comment hides the ';' and may hold braces
        for ch in code:
            if ch == "{":
                depth += 1
                seen_brace = True
            elif ch == "}":
                depth -= 1
        if seen_brace and depth == 0:
            return start, j
        if not seen_brace and depth == 0 and code.rstrip().endswith(";"):
            return start, j
        j += 1
    return start, min(j, len(lines) - 1)


def norm_block(block):
    out = []
    for l in block:
        l = re.sub(r"//.*$", "", l).strip()
        if l:
            out.append(re.sub(r"\s+", " ", l))
    return " ".join(out)


def dedupe_identical(parent_path, text, crlf, rounds=8):
    """Gate, drop identical later copies of every reported redefinition, gate again."""
    lines = text.split("\n")
    dropped = []
    for _round in range(rounds):
        write_text(parent_path, "\n".join(lines), crlf)
        status, log = compile_gate(parent_path)
        if status == "pass":
            return status, log, "\n".join(lines), dropped
        hits = {}
        for l in log.splitlines():
            m = REDEF_RE.search(l)
            if m:
                nm = redef_name(l)
                if nm:
                    hits.setdefault(int(m.group(1)), nm)
        if not hits:
            return status, log, "\n".join(lines), dropped
        for ln in sorted(hits, reverse=True):
            nm = hits[ln]
            i = ln - 1
            if i >= len(lines) or not re.search(r"\b" + re.escape(nm) + r"\b", lines[i]):
                sys.exit(f"dedupe: line {ln} does not name '{nm}' any more -- the folded text drifted; "
                         f"fold by hand")
            s, e = extract_block(lines, i)
            blk = norm_block(lines[s:e + 1])
            found = None
            for k in range(0, s):
                if lines[k].strip().startswith("//") or not re.search(r"\b" + re.escape(nm) + r"\b", lines[k]):
                    continue
                ks, ke = extract_block(lines, k)
                if ke < s and norm_block(lines[ks:ke + 1]) == blk:
                    found = (ks, ke)
                    break
            if found is None:
                sys.exit(f"dedupe REFUSED: '{nm}' at folded line {ln} is a redefinition but no earlier "
                         f"IDENTICAL definition exists -- two different bodies under one name; reconcile "
                         f"by hand (parent restored)\n   later copy (lines {s + 1}-{e + 1}): {blk[:300]}")
            marker = (f"// (fold: an identical definition of {nm} was dropped here -- this TU defines it "
                      f"once, above)")
            lines[s:e + 1] = [marker]
            dropped.append(nm)
    write_text(parent_path, "\n".join(lines), crlf)
    status, log = compile_gate(parent_path)
    return status, log, "\n".join(lines), dropped


def cmd_fold(args):
    parts = [t for t in find_partfiles() if t[2] == args.parent]
    if not parts:
        sys.exit(f"no partfiles named {args.parent}_w*.cpp under src/")
    if args.exclude:
        keep = {(e[:-4] if e.lower().endswith(".cpp") else e) + ".cpp" for e in args.exclude}
        known = {t[1] for t in parts}
        for k in keep:
            if k not in known:
                sys.exit(f"--exclude {k}: not a {args.parent} partfile")
        parts = [t for t in parts if t[1] not in keep]
        print(f"excluded (left as its own TU, mount line kept): {', '.join(sorted(keep))}")
        if not parts:
            sys.exit("every partfile was excluded -- nothing to fold")
    dirs = {t[0] for t in parts}
    if len(dirs) != 1:
        sys.exit(f"{args.parent} partfiles live in more than one directory: {sorted(dirs)}")
    d = dirs.pop()
    parent_base = args.parent_file or args.parent
    parent_path = os.path.join(d, parent_base + ".cpp")
    created = False
    if not os.path.exists(parent_path):
        if not args.create_parent:
            sys.exit(f"no parent TU at {parent_path} -- the class usually has a home TU under another "
                     f"basename (read a partfile's header; pass --parent-file <BASENAME>). If it truly "
                     f"has none, pass --create-parent to synthesise it from the partfiles.")
        created = True
        print(f"--create-parent: {rel_src(parent_path)} does not exist; it will be synthesised from "
              f"the partfiles in mount order")

    mounted = mount_order()
    parent_rel = rel_src(parent_path)
    if parent_rel not in mounted and not created:
        # Folding into a parent the link has never seen puts the PARENT'S OWN bodies into the exe for
        # the first time -- and a parent left unmounted while its partfiles were mounted was almost
        # always left out for a measured unresolved-external cost (build_game_exe.bat's rem notes say
        # which). 2026-09-15: CgsFineIntersectionTestModule + ICEWrapper cost 7 LNK2019 + 2 LNK2005
        # that way. So this is opt-in.
        if not args.mount_parent:
            sys.exit(f"REFUSED: the parent {parent_rel} is not mounted, only its partfiles are. Folding "
                     f"would mount the parent's own bodies for the first time (a link cost the .bat "
                     f"notes usually explain). Read those notes; pass --mount-parent to do it anyway, "
                     f"then LINK before committing.")
        print(f"WARNING: the parent {parent_rel} is not mounted; --mount-parent given, its mount line "
              f"will be added in the first partfile's slot -- LINK before you commit")
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

    stamp = datetime.date.today().isoformat()
    if created:
        # The skeleton: a generated banner + the FIRST partfile's own header block. Its includes
        # (and everyone else's) are unioned below; its body comes in the appendix like the rest, so
        # the mount-ordered evidence trail reads in one direction.
        first_text, crlf = read_text(os.path.join(d, victims[0]))
        first_header, _fi, _fl, _fb = split_partfile(first_text)
        # Some partfiles open with their #include line and put the commentary after it; there is
        # then no header block to hoist and the appendix keeps the commentary where it is.
        hoisted = bool([l for l in first_header if l.strip()])
        plines = [
            f"// {parent_rel}",
            "//",
            f"// Created {stamp} by tools/work/fold_partfiles.py --create-parent (b5-decomp issue #20).",
            f"// This family had NO parent TU: its bodies lived in {len(victims)} wave partfile(s), each",
            "// with its own hand-written mount line in tools/build/build_game_exe.bat. They are folded",
            "// here in MOUNT ORDER; every partfile's own header comment block is kept verbatim above",
            "// its bodies (the address annotations are the evidence trail). No body was edited.",
            "//",
            "// Folded, in mount order:",
        ] + [f"//     {f}" for f in victims] + ([
            "//",
            f"// The header of the first of them ({victims[0]}) follows verbatim, as this file's own.",
            "",
        ] + first_header if hoisted else [""])
        while plines and plines[-1].strip() == "":
            plines.pop()
        have = set()
        last_inc_idx = len(plines) - 1
    else:
        parent_text, crlf = read_text(parent_path)
        plines = parent_text.replace("\r\n", "\n").split("\n")
        have = {include_key(l) for l in plines if l.strip().startswith("#include")}
        last_inc_idx = max((i for i, l in enumerate(plines) if l.strip().startswith("#include")),
                           default=-1)
        if last_inc_idx < 0:
            sys.exit("the parent has no #include block to extend")

    new_includes = []
    appendix = []
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
        if created and f == victims[0] and hoisted:
            appendix.append("// Its header is THIS FILE'S header, at the top -- not repeated here.")
            appendix.append("// " + "=" * 76)
        else:
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
        folded.append(
            f"// the union of the {args.parent}_w*.cpp partfiles' #include lines, first occurrence "
            f"wins, mount order ({stamp})" if created else
            f"// includes folded in from the {args.parent}_w*.cpp partfiles ({stamp})")
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

    def restore():
        """Put the tree back exactly as it was: a pre-existing parent gets its text back, a
        --create-parent one never existed and is removed."""
        if created:
            if os.path.exists(parent_path):
                os.remove(parent_path)
        else:
            write_text(parent_path, backup, crlf)

    backup = None if created else parent_text
    write_text(parent_path, folded_text, crlf)
    if not args.no_gate:
        if args.dedupe_identical:
            try:
                status, log, folded_text, dropped = dedupe_identical(parent_path, folded_text, crlf)
            except SystemExit:
                restore()
                raise
            if dropped:
                print(f"dedupe: dropped {len(dropped)} identical later definition(s): "
                      + ", ".join(sorted(set(dropped))))
        else:
            status, log = compile_gate(parent_path)
        print(f"compile gate: {status}")
        if status == "fail":
            restore()
            failed_out = parent_path + ".gate-failed.txt"
            write_text(failed_out, folded_text, crlf)
            print(f"(the text that failed the gate is kept at {failed_out}; delete it when done)")
            print(log[-4000:])
            sys.exit("gate FAILED -- "
                     + ("the created parent was removed" if created else "parent restored")
                     + ", partfiles untouched. Dedupe the reported "
                     "symbols by hand (or pass --dedupe-identical for textually identical copies) "
                     "and re-run.")

    if created:
        subprocess.run(["git", "-C", B5, "add", "--", os.path.relpath(parent_path, B5)],
                       capture_output=True, text=True)

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
    if parent_rel not in mounted and not parent_added:
        print(f"WARNING: {parent_rel} carries the bodies now but has NO mount line (none of the "
              f"partfiles had one either) -- add it by hand or the link never sees them.")
    print("\nNext:")
    print(f"  git -C b5-decomp add {os.path.relpath(parent_path, B5)}  && commit: "
          f"'fold: {args.parent} partfiles into {parent_base}.cpp (issue #20)'")
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
    f.add_argument("--exclude", metavar="FILE", action="append", default=[],
                   help="a partfile to LEAVE as its own TU (repeatable; basename, .cpp optional). For "
                        "partfiles whose ISOLATION is the point -- an *_embed_check.cpp layout oracle "
                        "that includes a header the rest of the family must not see. Its mount line "
                        "stays.")
    f.add_argument("--parent-file", metavar="BASENAME",
                   help="the parent TU's basename when it is not <Parent>.cpp (e.g. --parent-file "
                        "BrnPropManager for the PropManager_w*.cpp family)")
    f.add_argument("--create-parent", action="store_true",
                   help="the family has no parent TU at all: synthesise <Parent>.cpp from the partfiles "
                        "(mount order) and mount it in the first partfile's slot")
    f.add_argument("--mount-parent", action="store_true",
                   help="allow folding into a parent that is not mounted itself (adds its mount line; LINK before committing)")
    f.add_argument("--dedupe-identical", action="store_true",
                   help="drop later anonymous-namespace definitions that are textually identical to an earlier one")
    f.set_defaults(fn=cmd_fold)
    c = sub.add_parser("check")
    c.add_argument("--baseline", action="store_true")
    c.set_defaults(fn=cmd_check)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
