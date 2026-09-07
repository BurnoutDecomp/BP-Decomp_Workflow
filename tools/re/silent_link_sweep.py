#!/usr/bin/env python3
# ==============================================================================================
# THE SILENT-LINK SWEEP.  Written 2026-09-07 for one defect class:
#
#   A function the console CALLS, declared in our headers, DEFINED NOWHERE, and referenced by
#   nothing, links in COMPLETE SILENCE -- no compiler warning, no linker error, no assert, no
#   log line. Nothing in the toolchain can see it, because there is no reference to resolve.
#
# It produced three player-visible bugs in one session:
#   * BrnParticle::ParticleModule::EndOfFrame  @0x82294C30  (b5 c227a165, issue #17) -- the
#     96-emitter tyre-mark pool drained one way only; once AttachTrailEmitter returned null no
#     tyre mark could be laid again for the session.
#   * BrnTraffic::TrafficEntityModule::UpdateRecoveringFromSlam @0x8273E778 (b5 51cd862d,
#     issue #14) -- a slammed traffic car never drove again and was deleted 6 s later.
#   * BrnGui::GuiModule::EndOfFrame @0x824F1008 (b5 2f0e038a) -- the player-image triple
#     buffer's two ring cursors froze at 1 and 2, so a received picture could never be shown.
#
# ⭐ WHY A LEDGER QUERY CANNOT FIND THESE. progress/status.json marks 21,245 of 21,254 function
# rows "reviewed"; that is the DEFAULT, not a verdict (see tools/re/hasbody.py). And a bare grep
# cannot find them either, because the interesting property is an ABSENCE joined against the
# CONSOLE's call graph -- you have to ask the binary who calls what.
#
# ⛔⛔ TWO WAYS THIS SWEEP CAN PRODUCE A FALSE EMPTY, both hit during development:
#   1. SCOPE. b5-decomp/vendor is a SIBLING of b5-decomp/src, not inside it. Indexing only src
#      made every EA::Thread::Mutex::Lock-class symbol read "defined nowhere" -- 5 phantom
#      entries. The definition scan MUST cover both trees.
#   2. GRAMMAR. A call statement `Foo(a, b);` inside a function body is also ")" followed by
#      ";" -- i.e. it looks exactly like a declaration. Without a scope check the first run
#      "found" rw::core::stdc::ConvertI64ToA declared in a .cpp. A declaration only ever occurs
#      at class or namespace/global scope, never with a plain '{' block innermost.
# Also: the Grep TOOL silently skips .ida-exports/ (it is .gitignore'd). This reads it directly.
#
# ⭐ POSITIVE CONTROL (--control). Re-runs the whole sweep against the tree as it stood at
# b5 488e7e82 == c227a165^ and at a given rev, and asserts the seed bugs come back out of it.
# A sweep you have not seen SUCCEED on a known instance is not a sweep.
# [[harness-answers-the-wrong-question]]
#
# usage:
#   python tools/re/silent_link_sweep.py                 # sweep the working tree -> progress/
#   python tools/re/silent_link_sweep.py --control       # run the historical positive control
#   python tools/re/silent_link_sweep.py --src DIR       # sweep some other checkout of src
# ==============================================================================================
"""Every declaration in b5-decomp with no definition anywhere in the tree, cross-referenced
against the X360 ARTIST export set and classified A / B / C."""
import json, os, re, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ART = os.path.join(REPO, ".ida-exports", "BURNOUT_X360_ARTIST.XEX")
CACHE = os.path.join(tempfile.gettempdir(), "brn_art_callgraph.json")

OURS = ("GameSource/", "GameShared/", "SharedClasses/", "SDKs/", "pc/")

# ---------------------------------------------------------------------------------------------
# 1. THE C++ INDEX -- every member-function DEFINITION and DECLARATION in a source tree.
# ---------------------------------------------------------------------------------------------
IDENT = r"[A-Za-z_~][A-Za-z0-9_]*"
RE_NS = re.compile(r"\bnamespace\s+(" + IDENT + r")\s*\{")
RE_ANONNS = re.compile(r"\bnamespace\s*\{")
RE_CLASS = re.compile(r"\b(class|struct|union)\s+(?:__declspec\s*\([^)]*\)\s*)?(" + IDENT + r")\b")
# ⛔ `template <class T>` -- the `class T` inside a TEMPLATE PARAMETER LIST is not a class
# definition. Without this the scanner took `class T` as an opener, scanned forward to the
# next '{' (the FUNCTION BODY's), and swallowed the whole definition: the one shared body of
# CgsGui::GuiModule::AddGuiEvent<T> read as "defined nowhere", and with it 206 instantiations.
# Skip the parameter list outright. (`template<typename T>` never tripped it, which is why the
# bug hid: it only bites the `class`/`struct` spelling.)
RE_TEMPLATE = re.compile(r"\btemplate\s*<")
# ⛔ THE QUALIFIER CAN CARRY TEMPLATE ARGUMENTS:
#     void VariableEventQueue<BUFSIZE, ALIGN>::Construct() { ... }
# Without the optional <...> group the scanner lost the class and filed that body under
# `CgsModule::Construct` -- so 195 VariableEventQueue instantiations read "defined nowhere".
TARGS = r"(?:<[^<>{};]*(?:<[^<>{};]*>[^<>{};]*)*>)?"
RE_HEAD = re.compile(r"(" + IDENT + TARGS + r"(?:\s*::\s*" + IDENT + TARGS + r")*)\s*\(")
TRAILERS = re.compile(r"^[\s\)]*(?:const\b|noexcept\b|override\b|final\b|throw\s*\([^)]*\)|"
                      r"__restrict\b|volatile\b|&&|&|=\s*0|=\s*default|=\s*delete)*")
KEYWORDS = {
    'if', 'for', 'while', 'switch', 'return', 'sizeof', 'catch', 'do', 'else', 'new', 'delete',
    'static_cast', 'reinterpret_cast', 'const_cast', 'dynamic_cast', 'throw', 'typeid',
    'defined', 'alignof', 'decltype', 'operator', '__declspec', 'assert', 'case', 'template',
    'noexcept', 'and', 'or', 'not', 'union', 'enum', 'typedef', 'using', 'friend', 'explicit',
    'EA_ASSERT', 'static_assert', 'offsetof',
}


def strip_comments(text):
    """Blank out comments and string/char literal content, PRESERVING byte offsets so line
    numbers and brace positions stay exact."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '/' and i + 1 < n:
            if text[i + 1] == '/':
                j = text.find('\n', i)
                j = n if j < 0 else j
                for k in range(i, j):
                    out[k] = ' '
                i = j
                continue
            if text[i + 1] == '*':
                j = text.find('*/', i + 2)
                j = n if j < 0 else j + 2
                for k in range(i, j):
                    if out[k] != '\n':
                        out[k] = ' '
                i = j
                continue
        if c in '"\'':
            q, j = c, i + 1
            while j < n:
                if text[j] == '\\':
                    j += 2
                    continue
                if text[j] == q:
                    j += 1
                    break
                if text[j] == '\n':
                    break
                j += 1
            for k in range(i + 1, min(j - 1, n) + 1):
                if k < n and out[k] != '\n':
                    out[k] = ' '
            i = j
            continue
        i += 1
    return ''.join(out)


def _line_of(pos, lineidx):
    lo, hi = 0, len(lineidx)
    while lo < hi:
        mid = (lo + hi) // 2
        if lineidx[mid] <= pos:
            lo = mid + 1
        else:
            hi = mid
    return lo


def scan_file(rel, text, defs, decls):
    s = strip_comments(text)
    lineidx = [m.start() for m in re.finditer('\n', s)]
    stack, pending = [], None
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == '{':
            stack.append(pending if pending else ('block', None))
            pending = None
            i += 1
            continue
        if c == '}':
            if stack:
                stack.pop()
            i += 1
            continue
        if c == ';':
            pending = None
            i += 1
            continue
        if c.isalpha() or c == '_':
            m = RE_TEMPLATE.match(s, i)
            if m:
                p, d = m.end() - 1, 0
                while p < n:
                    if s[p] == '<':
                        d += 1
                    elif s[p] == '>':
                        d -= 1
                        if d == 0:
                            break
                    p += 1
                i = p + 1
                continue
            m = RE_NS.match(s, i) or RE_ANONNS.match(s, i)
            if m:
                pending = ('ns', m.group(1) if m.re is RE_NS else None)
                i = m.end() - 1
                continue
            m = RE_CLASS.match(s, i)
            if m:
                k = m.end()
                while k < n and s[k] not in '{;':
                    k += 1
                if k < n and s[k] == '{':
                    pending = ('class', m.group(2))
                    i = k
                    continue
                i = m.end()
                continue
            m = RE_HEAD.match(s, i)
            if m:
                name = strip_templ(re.sub(r"\s+", "", m.group(1)))
                if name.split('::')[-1] in KEYWORDS or name.split('::')[0] in KEYWORDS:
                    i = m.end()
                    continue
                p, d = m.end() - 1, 0
                while p < n:
                    if s[p] == '(':
                        d += 1
                    elif s[p] == ')':
                        d -= 1
                        if d == 0:
                            break
                    p += 1
                if p >= n:
                    i = m.end()
                    continue
                tailtxt = s[p + 1:p + 400]
                t = TRAILERS.match(tailtxt)
                rest = (tailtxt[t.end():] if t else tailtxt).lstrip()
                if rest.startswith(':') and not rest.startswith('::'):   # ctor-init list
                    q, semi = s.find('{', p), s.find(';', p)
                    rest = '{' if (q >= 0 and (semi < 0 or q < semi)) else rest
                # ⛔ see banner note 2: innermost scope must not be a plain block, or every
                # call statement in every function body reads as a declaration.
                innermost = stack[-1][0] if stack else 'ns'
                isdef = rest.startswith('{') and innermost != 'block'
                isdecl = rest.startswith(';') and innermost != 'block'
                # = 0 / = delete / = default is not a missing body -- it cannot link silently.
                notabody = bool(re.search(r"=\s*(0|delete|default)", tailtxt[:t.end()] if t else ''))
                if isdef or isdecl:
                    nspath = [x for k, x in stack if k == 'ns' and x]
                    clspath = [x for k, x in stack if k == 'class' and x]
                    if '::' not in name and not clspath and isdecl:
                        full = '::'.join(nspath + [name])
                    else:
                        full = '::'.join(nspath + clspath + [name])
                    ln = _line_of(i, lineidx) + 1
                    tgt = defs if (isdef or notabody) else decls
                    mark = "%s:%d" % (rel, ln)
                    tgt.setdefault(full, []).append(mark)
                    parts = full.split('::')
                    if len(parts) >= 2:                       # fuzzy tail key
                        tgt.setdefault('::'.join(parts[-2:]), []).append(mark)
                i = m.end()
                continue
            j = i
            while j < n and (s[j].isalnum() or s[j] == '_'):
                j += 1
            i = j
            continue
        i += 1


def build_index(src):
    """defs/decls over src AND its sibling vendor/ (bodies only) -- see banner note 1."""
    defs, decls = {}, {}
    roots = [(src, True)]
    vendor = os.path.join(os.path.dirname(src), "vendor")
    if os.path.isdir(vendor):
        roots.append((vendor, False))
    nfiles = 0
    for root, is_ours in roots:
        for dirpath, dirnames, files in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != '.git']
            for f in files:
                if not f.endswith(('.cpp', '.h', '.hpp', '.inl', '.cc', '.c')):
                    continue
                p = os.path.join(dirpath, f)
                try:
                    text = open(p, 'rb').read().decode('utf-8', 'replace')
                except Exception:
                    continue
                rel = os.path.relpath(p, src).replace('\\', '/')
                try:
                    scan_file(rel, text, defs, decls if is_ours else {})
                except Exception as exc:
                    print("scan fail", rel, exc, file=sys.stderr)
                nfiles += 1
    return defs, decls, nfiles


# ---------------------------------------------------------------------------------------------
# 2. THE ARTIST CALL GRAPH -- one pass over 30,084 export jsons, cached under %TEMP%.
# ---------------------------------------------------------------------------------------------
def load_graph(rebuild=False):
    if not rebuild and os.path.exists(CACHE):
        try:
            return json.load(open(CACHE))
        except Exception:
            pass
    g = {}
    for f in os.listdir(ART):
        if not f.endswith('.json'):
            continue
        try:
            j = json.load(open(os.path.join(ART, f), encoding='utf-8', errors='replace'))
        except Exception:
            continue
        asm = j.get('assembly') or ''
        g[j.get('address') or f[:-5]] = {
            'n': j.get('name') or '',
            'i': asm.count('\n') + (1 if asm else 0),
            'to': [x.get('name') or ('@' + (x.get('address') or '')) for x in (j.get('xrefs_to') or [])],
            'fr': [x.get('name') or ('@' + (x.get('address') or '')) for x in (j.get('xrefs_from') or [])],
        }
    json.dump(g, open(CACHE, 'w'))
    return g


# ---------------------------------------------------------------------------------------------
# 3. THE JOIN.
# ---------------------------------------------------------------------------------------------
DEBUGRE = re.compile(r"Debug|TestBed|PerfMon|DEBUG_|AutoTest", re.I)
NETRE = re.compile(r"Network|Online|CgsNetwork|Realmc|DirtySock|MassiveAd|Friends|Live", re.I)
SATNAV = re.compile(r"SatNav|MapTransform|MapUtils|MapManager|MapIcon|Minimap|Compass", re.I)


def strip_templ(x):
    """`CgsGui::GuiModule::AddGuiEvent<BrnGui::GuiEventUpdateSatNav>` -> `...::AddGuiEvent`.

    ⛔ THE FALSE POSITIVE THIS EXISTS FOR. The console emits one BODY PER INSTANTIATION, so
    identity.json carries 1,867 names with template arguments; our tree carries ONE generic
    template. Without this, every instantiation reads "defined nowhere" -- 960 phantom class-A
    rows, among them AddGuiEvent<GuiEventUpdateSatNav>, whose real definition is right there in
    CgsGuiModule_AddGuiEvent_Inst.cpp. (It does NOT touch the declared-and-undefined table:
    zero of the 1,867 are declared with their template arguments in our headers.)
    """
    if '<' not in x or 'operator' in x:
        return x
    out, d = [], 0
    for ch in x:
        if ch == '<':
            d += 1
        elif ch == '>':
            d = max(0, d - 1)
        elif d == 0:
            out.append(ch)
    return ''.join(out)


def sweep(src, defs, decls, graph, mounts, ident, execset):
    def tail(x):
        p = x.split('::')
        return '::'.join(p[-2:]) if len(p) >= 2 else x

    def hits(tbl, x):
        out, seen = [], set()
        keys = [x, tail(x)]
        s = strip_templ(x)
        if s != x:
            keys += [s, tail(s)]
        for k in keys:
            for h in tbl.get(k, []):
                if h not in seen:
                    seen.add(h)
                    out.append(h)
        return out

    def best_def(x):
        best = None
        for h in hits(defs, x):
            f, ln = h.rsplit(':', 1)
            mnt = (f in mounts) if f.endswith('.cpp') else (not f.startswith('../vendor'))
            if best is None or (mnt and not best[2]):
                best = (f, int(ln), mnt)
        return best

    lines = {}

    def decl_text(h):
        f, ln = h.rsplit(':', 1)
        if f not in lines:
            try:
                lines[f] = open(os.path.join(src, f.replace('/', os.sep)), 'rb'
                                ).read().decode('utf-8', 'replace').split('\n')
            except Exception:
                lines[f] = []
        L, i = lines[f], int(ln) - 1
        return L[i].strip() if 0 <= i < len(L) else ''

    # address of each named function, for the xrefs_to <-> xrefs_from symmetry check
    byname = {}
    for a, r in graph.items():
        if r['n']:
            byname.setdefault(r['n'], a)

    rows = []
    for name, rec in ident.items():
        if '::' not in name or '`' in name or name.startswith('sub_'):
            continue
        addrs = rec.get('x360_addrs') or []
        if not addrs or addrs[0] not in graph:
            continue
        addr, gr = addrs[0], graph[addrs[0]]
        if best_def(name):
            continue                                     # we have a body: not this defect
        ourdecls = [h for h in hits(decls, name) if h.rsplit(':', 1)[0].startswith(OURS)]
        callers = [c for c in gr['to']
                   if c and not c.startswith('sub_') and not c.startswith('@') and '`' not in c]
        live, latent = [], []
        for cn in callers:
            cd = best_def(cn)
            (live if (cd and cd[2]) else latent).append((cn, cd))
        cls = 'A' if live else ('B' if callers else 'C')
        rows.append(dict(
            name=name, addr=addr, ninstr=gr['i'], cls=cls,
            declared=bool(ourdecls), decls=ourdecls[:3],
            decl_text=(decl_text(ourdecls[0]) if ourdecls else ''),
            virtual=any('virtual' in decl_text(h) for h in ourdecls),
            n_console_xrefs=len(gr['to']), n_named_callers=len(callers),
            live_callers=[[c, "%s:%d" % (d[0], d[1])] for c, d in live][:10],
            # the export's xrefs_to says "C calls me"; the CALLER's own xrefs_from must agree.
            # A disagreement means the name resolved to the wrong address (two classes, one
            # method name) -- so this counts how much of the join is double-confirmed.
            xref_confirmed=sum(1 for c, _ in live
                               if byname.get(c) and name in graph[byname[c]]['fr']),
            latent_callers=[c for c, _ in latent][:10],
            caller_in_boot_trace=[c for c, _ in live if c in execset][:5],
            debugish=bool(DEBUGRE.search(name)), netish=bool(NETRE.search(name)),
            satnav=bool(SATNAV.search(name) or any(SATNAV.search(d) for d in ourdecls)),
            primary_file=rec.get('primary_file')))
    return rows


def mount_set():
    bat = open(os.path.join(REPO, "tools", "build", "build_game_exe.bat"), 'rb'
               ).read().decode('utf-8', 'replace')
    return {m.group(1).replace('\\', '/')
            for m in re.finditer(r'%SRC%\\([^"\r\n]+\.cpp)', bat)}


def run(src):
    ident = json.load(open(os.path.join(REPO, "progress", "identity.json")))
    goals = json.load(open(os.path.join(REPO, "progress", "goals.json")))
    execset = set(goals['goals']['milestones']['boot-trace'].get('executed_funcs') or [])
    defs, decls, nfiles = build_index(src)
    graph = load_graph()
    rows = sweep(src, defs, decls, graph, mount_set(), ident, execset)
    return rows, nfiles


def summarise(rows, label=""):
    from collections import Counter
    c = Counter()
    for r in rows:
        c[r['cls']] += 1
        if r['declared']:
            c['declared/' + r['cls']] += 1
    print("%s  A=%d B=%d C=%d  |  DECLARED-and-undefined: A=%d B=%d C=%d  (total %d)" % (
        label, c['A'], c['B'], c['C'], c['declared/A'], c['declared/B'], c['declared/C'],
        c['declared/A'] + c['declared/B'] + c['declared/C']))
    return c


def control():
    """Re-run the sweep on the tree at 488e7e82 (== c227a165^) and assert the seed bugs
    come back out of it. Extracts into a temp dir; leaves the working tree alone."""
    b5 = os.path.join(REPO, "b5-decomp")
    tmp = os.path.join(tempfile.gettempdir(), "brn_silentlink_control")
    subprocess.run(["rm", "-rf", tmp], check=False)
    os.makedirs(tmp, exist_ok=True)
    p1 = subprocess.Popen(["git", "-C", b5, "archive", "488e7e82", "src"], stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", tmp], stdin=p1.stdout, check=True)
    p1.wait()
    rows, _ = run(os.path.join(tmp, "src"))
    by = {r['name']: r for r in rows}
    ok = True
    for want, wantcls in (("BrnParticle::ParticleModule::EndOfFrame", 'A'),
                          ("BrnTraffic::TrafficEntityModule::UpdateRecoveringFromSlam", None)):
        r = by.get(want)
        if not r:
            print("CONTROL FAIL: %s not found in the 488e7e82 sweep" % want)
            ok = False
            continue
        print("CONTROL: %-62s class %s  callers=%s" %
              (want, r['cls'], [c[0] for c in r['live_callers']] or r['latent_callers'][:2]))
        if wantcls and r['cls'] != wantcls:
            print("   ...expected class %s" % wantcls)
            ok = False
    print("CONTROL", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def bucket(r):
    """Which consequence bucket a row lands in. The CALLER SET is the discriminator, not the
    callee's name: BrnGui::HelpBar reads like HUD, but every reconstructed caller it has is an
    Online* screen."""
    if r['satnav']:
        return 'satnav'
    if r['debugish']:
        return 'debug'
    if r['netish']:
        return 'net'
    if r['live_callers'] and all(('Online' in c[0] or 'Network' in c[0] or 'Friends' in c[0])
                                 for c in r['live_callers']):
        return 'net'
    return 'core'


def emit_md(rows, path, rev):
    from collections import Counter
    for r in rows:
        r['bucket'] = bucket(r)
    A = [r for r in rows if r['cls'] == 'A' and r['declared']]
    B = [r for r in rows if r['cls'] == 'B' and r['declared']]
    C = [r for r in rows if r['cls'] == 'C' and r['declared']]
    UA = [r for r in rows if r['cls'] == 'A' and not r['declared']]

    def tbl(sub, owner=''):
        out = ["| console function | addr | insns | reconstructed + mounted caller | ran at boot |"
               + (" owner |" if owner else ""),
               "|---|---|---|---|---|" + ("---|" if owner else "")]
        for r in sub:
            cal = r['live_callers'][0][0] if r['live_callers'] else ''
            more = (" +%d" % (len(r['live_callers']) - 1)) if len(r['live_callers']) > 1 else ""
            out.append("| `%s` | `%s` | %d | `%s`%s | %s |%s" % (
                r['name'], r['addr'], r['ninstr'], cal, more,
                'yes' if r['caller_in_boot_trace'] else '',
                (" %s |" % owner) if owner else ""))
        return '\n'.join(out)

    L = []
    W = L.append
    W("# Silent-link inventory -- declared, defined nowhere, referenced by nothing")
    W("")
    W("<!-- GENERATED by tools/re/silent_link_sweep.py -- do not hand-edit the tables. -->")
    W("b5-decomp rev `%s`." % rev)
    W("")
    W("A function the console CALLS, declared in our headers, DEFINED NOWHERE, and referenced by")
    W("nothing **links in complete silence** -- no compiler warning, no linker error, no assert,")
    W("no log line. There is no reference for the linker to fail on, so nothing in the toolchain")
    W("can see it. Three player-visible bugs of this exact shape landed in one session:")
    W("`ParticleModule::EndOfFrame` (#17, `c227a165`), `UpdateRecoveringFromSlam` (#14,")
    W("`51cd862d`), and `GuiModule::EndOfFrame` (`2f0e038a`).")
    W("")
    W("## Counts")
    W("")
    W("| | class A (a mounted caller of ours) | class B (latent) | class C (no direct caller) | total |")
    W("|---|---|---|---|---|")
    W("| **declared in our headers, defined nowhere** | **%d** | %d | %d | **%d** |"
      % (len(A), len(B), len(C), len(A) + len(B) + len(C)))
    W("| not declared either (superset -- not yet reconstructed) | %d | %d | %d | %d |"
      % (len(UA), sum(1 for r in rows if r['cls'] == 'B' and not r['declared']),
         sum(1 for r in rows if r['cls'] == 'C' and not r['declared']),
         len(rows) - len(A) - len(B) - len(C)))
    W("")
    W("* **A** -- the console calls it from a body we have reconstructed *and* mounted into the")
    W("  exe. Since the callee has no definition, that mounted caller **cannot** be calling it:")
    W("  our reconstruction of the caller silently dropped the call. Running wrong right now.")
    W("* **B** -- the console has callers, but none of them is a mounted body of ours. Latent.")
    W("* **C** -- the ARTIST export lists no *direct* named caller. **This is not proof of")
    W("  absence** -- see the caveat at the bottom.")
    W("")
    W("Class A by consequence bucket: " + ", ".join(
        "%s %d" % (k, v) for k, v in Counter(r['bucket'] for r in A).most_common()) + ".")
    W("")
    W("## Class A / CORE -- the actionable list (%d)" % len([r for r in A if r['bucket'] == 'core']))
    W("")
    W("Ranked: caller proven to execute in the boot trace first, then caller count, then size.")
    W("")
    W(tbl([r for r in A if r['bucket'] == 'core']))
    W("")
    W("## Class A / SAT-NAV + minimap -- ANOTHER CONTRIBUTOR'S TICKET (#9, `derneuere`)")
    W("")
    W("⛔ **Do not fix these.** Reported so they can be handed over, not taken.")
    W("")
    W(tbl([r for r in A if r['bucket'] == 'satnav'], owner='#9?'))
    W("")
    W("The same sweep with the declaration requirement dropped adds the rest of the minimap set")
    W("-- these are declared nowhere either, so they are invisible twice over:")
    W("")
    W(tbl([r for r in UA if r['bucket'] == 'satnav']))
    W("")
    hud = [r for r in rows if r['cls'] == 'A' and not r['debugish'] and r['bucket'] != 'satnav'
           and any(('HudState' in c[0] or 'HUDMessageLogic' in c[0]) for c in r['live_callers'])]
    W("## Class A / IN-RACE HUD -- POSSIBLY #11 (`derneuere`), CHECK BEFORE TOUCHING (%d)" % len(hud))
    W("")
    W("Selected by CALLER, not by name: every row here is called by a `*HudState` or by")
    W("`HUDMessageLogic::PostWorldUpdate` -- i.e. it is in-race HUD. Issue #11 is titled")
    W("\"in-game events UI\"; the issue text was not available here, so this is a routing hint,")
    W("not a determination. `HUDMessageLogic::GenerateRaceModeMessages` in particular is the")
    W("generator for the in-race event messages.")
    W("")
    W(tbl(hud))
    W("")
    W("## Class A / ONLINE (%d) and DEBUG (%d)" %
      (len([r for r in A if r['bucket'] == 'net']), len([r for r in A if r['bucket'] == 'debug'])))
    W("")
    W("Real class-A rows, deprioritised because the caller is an `Online*`/`Network*` screen or a")
    W("`DebugComponent`/`PerfMon` path -- mounted, but there is no evidence it runs in this build.")
    W("")
    W(tbl([r for r in A if r['bucket'] == 'net']))
    W("")
    W(tbl([r for r in A if r['bucket'] == 'debug']))
    W("")
    W("## Class B -- latent (%d)" % len(B))
    W("")
    W("By bucket: " + ", ".join("%s %d" % (k, v)
                                for k, v in Counter(r['bucket'] for r in B).most_common()) + ".")
    W("The network half is genuinely latent (we do not run online). The %d CORE rows become class"
      % len([r for r in B if r['bucket'] == 'core']))
    W("A the moment their caller is reconstructed -- re-run this sweep after any wave lands one.")
    W("")
    W(tbl(sorted([r for r in B if r['bucket'] == 'core'],
                 key=lambda r: -r['n_named_callers'])[:40]))
    W("")
    W("## Class C -- no direct named caller in ARTIST (%d)" % len(C))
    W("")
    W("⚠️ **C is the weakest bucket and must not be read as \"faithfully absent\".** A virtual")
    W("function has no `xrefs_to` at all: it is reached by `lwz`/`mtctr`/`bctrl` through a vtable,")
    W("so base and override both look like dead code (this is the whole reason")
    W("`tools/re/vcallsites.py` exists). The bucket is visibly dominated by overrides --")
    W("`ArbState*::Update`, `*TakedownPlayer::Prepare`, `*DebugComponent::RenderWorld`. Resolve an")
    W("individual C row with `vcallsites.py <slot-hex> --name` before calling it absent.")
    W("")
    W(tbl(sorted(C, key=lambda r: -r['ninstr'])[:25]))
    W("")
    W("## The companion snapshot: `progress/sweep/silent_declarations.json`")
    W("")
    W("A **declaration-first** pass over the same question, run earlier the same day against the")
    W("working tree at `465fa81b`. It is a frozen snapshot -- its generator was not kept, so it")
    W("does not regenerate and must not be read as current. It is retained for the two axes this")
    W("tool does not produce:")
    W("")
    W("* **`bucket not-in-console` (2,312)** -- declarations in OUR headers for which the ARTIST")
    W("  export has no function at all. Candidate **inventions**, the mirror of this inventory.")
    W("* **`dropped_has_call_site` (1,154)** -- a declaration with no body that our tree")
    W("  nonetheless *calls*. It only links because the calling TU is not mounted; mounting that")
    W("  TU turns each into an unresolved external.")
    W("")
    W("It also carries 12 positive controls and two blind spots worth repeating here: **ICF")
    W("folding** (identical one-line console bodies are folded, so IDA can print a neighbour's")
    W("name on the fold target) and **macros** (a call generated by a macro body is invisible to a")
    W("text call index). And it quantifies the class-C caveat: **25.3% of all 30,084 console")
    W("functions have no `xrefs_to` at all**.")
    W("")
    W("## What this evidence CANNOT distinguish")
    W("")
    W("1. **Class C is not \"uncalled\".** Virtual dispatch is invisible to `xrefs_to` (above).")
    W("2. **\"Mounted\" is not \"executed\".** The exe compiles the caller in; whether that caller")
    W("   runs is a separate question. Only the `ran at boot` column is evidence of execution, and")
    W("   it comes from a 30 s boot-to-main-menu Xenia trace (`progress/goals.json`,")
    W("   `boot-trace.executed_funcs`, 1,880 functions) -- so a blank cell means *not proven*, not")
    W("   *not executed*. Nothing here proves an in-race gameplay path runs.")
    W("3. **An absent call may have been INLINED into the caller by hand.** The sweep asks whether")
    W("   a definition exists, not whether the behaviour does. Read the caller before fixing.")
    _e = sum(len(r['live_callers']) for r in A)
    _k = sum(r['xref_confirmed'] for r in A)
    W("4. **A name match is a name match.** Matching falls back to the last two components")
    W("   (`Class::Method`), so a name shared by two unrelated classes can mask one of them.")
    W("   %d of the %d class-A caller edges are double-confirmed against the CALLER's own" % (_k, _e))
    W("   `xrefs_from`; the %d that are not are name collisions of this kind -- check those rows"
      % (_e - _k))
    W("   by hand.")
    W("5. **Overload sets collapse.** A class with two `SetScore` overloads, one defined and one")
    W("   not, reads as defined.")
    W("6. **Ownership flags are inferred from issue TITLES only** (#9 \"minimap: no blips\", #11")
    W("   \"in-game events UI\"); the issue text was not available to this sweep.")
    W("")
    W("## Regenerating / the positive control")
    W("")
    W("```")
    W("python tools/re/silent_link_sweep.py            # rewrite progress/silent_link_inventory.*")
    W("python tools/re/silent_link_sweep.py --control  # prove the sweep can still FIND a known one")
    W("```")
    W("")
    W("`--control` re-runs the whole sweep against the tree at b5 `488e7e82` (= `c227a165^`, the")
    W("commit *before* the tyre-mark fix) and asserts the seed bugs come back out of it. It")
    W("currently reports both `ParticleModule::EndOfFrame` and `UpdateRecoveringFromSlam` as class")
    W("A with their real console callers. A sweep you have not watched succeed on a known instance")
    W("is not a sweep. [[harness-answers-the-wrong-question]]")
    open(path, 'w', encoding='utf-8').write('\n'.join(L) + '\n')


def main():
    if '--control' in sys.argv:
        return control()
    src = os.path.join(REPO, "b5-decomp", "src")
    if '--src' in sys.argv:
        src = sys.argv[sys.argv.index('--src') + 1]
    rows, nfiles = run(src)
    summarise(rows, "swept %d files:" % nfiles)
    out = os.path.join(REPO, "progress", "silent_link_inventory.json")
    rev = subprocess.run(["git", "-C", os.path.join(REPO, "b5-decomp"), "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    rows.sort(key=lambda r: (r['cls'], not r['declared'], -len(r['caller_in_boot_trace']),
                             r['debugish'], r['netish'], -r['n_named_callers'], -r['ninstr']))
    # Commit the rows that carry a claim: everything DECLARED (the inventory proper, all three
    # classes) plus the undeclared class-A superset. The undeclared B/C rows are just "not
    # reconstructed yet" -- 4,128 of them, and they regenerate from this same command.
    keep = [r for r in rows if r['declared'] or r['cls'] == 'A']
    json.dump({'b5_rev': rev, 'source': src.replace('\\', '/'),
               'counts': {'declared_A': sum(1 for r in rows if r['declared'] and r['cls'] == 'A'),
                          'declared_B': sum(1 for r in rows if r['declared'] and r['cls'] == 'B'),
                          'declared_C': sum(1 for r in rows if r['declared'] and r['cls'] == 'C'),
                          'undeclared_A': sum(1 for r in rows if not r['declared'] and r['cls'] == 'A'),
                          'undeclared_B_C_omitted': sum(1 for r in rows if not r['declared'] and r['cls'] != 'A')},
               'rows': keep},
              open(out, 'w'), separators=(',', ':'))
    md = os.path.join(REPO, "progress", "SILENT_LINK_INVENTORY.md")
    emit_md(rows, md, rev)
    print("wrote", os.path.relpath(out, REPO), "+", os.path.relpath(md, REPO))
    return 0


if __name__ == '__main__':
    sys.exit(main())
