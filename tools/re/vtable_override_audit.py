#!/usr/bin/env python3
# ==============================================================================================
# THE VTABLE-OVERRIDE AUDIT.  Written 2026-11-04 for the hole silent_link_sweep.py sees badly:
#
#   A virtual method the CONSOLE overrides and our class does not. It compiles and links in
#   complete silence, because the slot simply falls back on the base class's body. And because a
#   virtual has no direct caller, `xrefs_to` is empty: the sweep files it under its weakest bucket
#   (class C, "no direct named caller").
#
# Measured instance: FaceOffMode overrides Start / PreWorldUpdate / FillInGameModeSpecificResults
# at vtable 0x820D0500. Without them a Face Off runs the GameMode base's versions, and nothing in
# the toolchain says so.
#
# METHOD. Ask the console's tables, not its call graph:
#   1. The tables come out of the ARTIST image (.rdata). A table starts at an address the code
#      materialises (`lis/addi off_XXXXXXXX`); a store of that address into an object
#      (`stw rX, N(rY)`) is the evidence that it is a vptr and not a callback array.
#   2. Each slot's target is named by the export json of that address.
#   3. Each table gets an OWNER: the most-derived class that explains its named slots, using the
#      DecFIGS DWARF inheritance (our own headers fill in classes DWARF does not have), with the
#      constructor/destructor that stores the table as evidence.
#   4. Each virtual body named `C::m` is looked up in our tree. A slot naming something unrelated
#      is an ICF fold and is classified separately, never as a plain miss.
#   5. A method DWARF declares virtual on the class, with no body here, is looked for through
#      related tables too: a fold can match a sibling exactly and still differ from the base.
#
# ⛔ FOUR WAYS THIS WOULD LIE, each handled below rather than assumed away:
#   * ICF. The linker folds identical bodies, so FaceOffMode's slot 8 reads
#     `MovieVideoRenderer::GetRenderingDelay`. A foreign name says nothing about that class: the
#     real question is whether the slot DIFFERS from the parent table's slot, and if so which
#     method the parent names there. See slot_pass().
#   * TRUNCATION. IDA clips qualified names (`...::GetMemor`). An exact-name miss on a clipped
#     name proves nothing. DWARF decides first (an exact DWARF method is not clipped); a prefix
#     match is reported as TRUNCATED_MATCH, never silently matched -- the prefix rule is what once
#     let `~MemcardState` satisfy a constructor (tools/work/coverage_check.py).
#   * GENERATED DESTRUCTORS. A deleting destructor is compiler output, not a method to write.
#   * THE SCANNER. silent_link_sweep's index misses unusual definition shapes, so every would-be
#     miss is re-checked against raw text with hasbody.py's definition test (text_definitions()).
#
# ⭐ IMAGE. tools/re/x360rd.py's artist_i64.raw and image.bin may both be absent. This tool then
# unpacks `IDA Files/BURNOUT_X360_ARTIST.XEX.i64` READ-ONLY into a flat image under %TEMP% (usable
# by x360rd.py itself through $BRN_IMAGE_BIN). It is calibrated against known words on every run.
#
# usage:
#   python tools/re/vtable_override_audit.py             # audit the tree -> progress/VTABLE_OVERRIDE_AUDIT.*
#   python tools/re/vtable_override_audit.py --control   # known cases must come back out; exit 1 if not
#   python tools/re/vtable_override_audit.py --table 0x820D0500      # one table, slot by slot
#   python tools/re/vtable_override_audit.py --src DIR --image FILE --rebuild-cache
# ==============================================================================================
"""Console vtable overrides that have no definition in our tree, classified with a confidence."""
import io, json, os, re, struct, subprocess, sys, tempfile
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import silent_link_sweep as sls  # noqa: E402  (the C++ index, the mount set, the template stripper)

REPO = os.path.dirname(os.path.dirname(HERE))
ART = os.path.join(REPO, ".ida-exports", "BURNOUT_X360_ARTIST.XEX")
I64 = os.path.join(REPO, "IDA Files", "BURNOUT_X360_ARTIST.XEX.i64")
DWARF = os.path.join(REPO, "references", "DecFIGS", "dwarfdump")
VERDICTS = os.path.join(HERE, "vtable_override_verdicts.json")
TMP = tempfile.gettempdir()
IMAGE_CACHE = os.path.join(TMP, "brn_artist_image.bin")
FUNC_CACHE = os.path.join(TMP, "brn_vtable_audit_funcs_v2.json")
DWARF_CACHE = os.path.join(TMP, "brn_vtable_audit_dwarf_v2.json")

FLAT_BASE = 0x82000000
RDATA = (0x82000600, 0x821BB000)    # .rdata in the ARTIST segment table
CODE = (0x821F0000, 0x82C775D0)     # .text

# Known cases, each `(qualified name, address)`. Cases 0-2: FaceOffMode's table, per the header
# note in BrnFaceOffMode.h. Cases 3-5: the online modes' Start overrides.
CONTROL = [
    ("BrnGameState::FaceOffMode::Start", 0x82330440),
    ("BrnGameState::FaceOffMode::PreWorldUpdate", 0x82330670),
    ("BrnGameState::FaceOffMode::FillInGameModeSpecificResults", 0x82315CC0),
    ("BrnGameState::OnlineRaceMode::Start", 0x82338EB8),
    ("BrnGameState::OnlineRoadRageMode::Start", 0x823394A0),
    ("BrnGameState::OnlineBurningHomeRunMode::Start", 0x82339968),
]
# Words read back on every run. Not a proof (x360rd.py's banner: a passing self-test once coexisted
# with a 1594-byte miscalibration) -- so these come from three independent places: an instruction
# encoding, a table cited in a header, and the shape of a table the header describes.
IMAGE_CHECKS = [
    (0x82330440, 0x7D8802A6, "FaceOffMode::Start's first instruction, mflr r12"),
    (0x820D0500 + 5 * 4, 0x82330440, "BrnFaceOffMode.h: slot 5 of 0x820D0500 is Start"),
    (0x820D0500 + 2 * 4, 0x82330670, "BrnFaceOffMode.h: slot 2 of 0x820D0500 is PreWorldUpdate"),
    (0x820D0500 + 15 * 4, 0x82315CC0, "BrnFaceOffMode.h: slot 15 is FillInGameModeSpecificResults"),
    (0x820D0500 + 8 * 4, 0x827EAB30, "BrnFaceOffMode.h: slot 8 is the 0.0f ICF body"),
]

# Console-only code: a miss here is most likely not portable behaviour at all.
PLATFORM_RE = re.compile(
    r"XAudio|Snd9|Wmv|WMV|XCam|Massive|Xbox|Xenon|X360|XMV|XHV|XLive|XUI|\bXam|XNotify|XContent|"
    r"D3D|Direct3D|Xbdm|XMA|XPerf|Kinect|VisionCam|XOnline|DirtySock|Realmc|XGRAPHICS|\bSnd::", re.I)
VENDOR_RE = re.compile(r"^(?:rw|EA|eastl|std|ICE|Apt\w*)(?:::|$)|^Apt|^`")
VENDOR_FILE_RE = re.compile(r"(?:^|/)SDKs/")
DEBUG_RE = re.compile(r"Debug|TestBed|PerfMon|DevTools|DEBUG_|AutoTest|Profil", re.I)
ONLINE_RE = re.compile(r"Online|Network|CgsNetwork|Lobby|Friends|Matchmak", re.I)

# Class tags a row can carry. MISSING is the only one that asserts a behavioural hole by itself.
CLS_HELP = [
    ("MISSING", "The console overrides it, the class exists in our tree, the method has no body. "
                "The slot silently falls back on the base."),
    ("MISSING_CLASS_ABSENT", "The console overrides it but the whole class is absent from our "
                             "tree. A larger gap of a different shape: no fallback, no object."),
    ("ICF_OVERRIDE_MISSING", "Slot differs from the parent's, carries a foreign name because the "
                             "body was folded, and our class has no body for the method the parent "
                             "names there. Real difference, but a small shared body by nature."),
    ("UNNAMED_OVERRIDE_MISSING", "Same, for a `sub_` body IDA could not name."),
    ("ICF_TRIVIAL_OVERRIDE", "Same, but the body is at most 2 instructions (empty, or `li r3,N`). Most "
                             "match the base's behaviour, and these are where the slot mapping is "
                             "weakest. Not listed here: in the JSON."),
    ("TRUNCATED_MATCH", "The console's name is clipped and a method of the class extends it. "
                        "Probably present; candidates listed for a human to confirm."),
    ("AMBIGUOUS_NAMESPACE", "A definition of `Class::method` exists under ANOTHER namespace. A "
                            "name collision may be hiding a miss, or the namespace may be spelled "
                            "differently."),
    ("CLIPPED_NAME", "IDA clipped the name inside its qualifier (`BrnSound::Logic::Collisio`), so "
                     "neither class nor method can be read from it. Unresolved, not a miss."),
    ("TEMPLATE_UNRESOLVED", "An instantiation whose template head IDA dropped; the class cannot "
                            "be recovered from the name."),
    ("ICF_NAME_ONLY", "This body's name belongs to a class unrelated to every table holding it. "
                      "The name is an accident of folding: not a miss of that class."),
    ("ICF_SAME_AS_BASE", "Named for this class, but the parent's slot holds the SAME address: "
                         "identical bodies, so inheriting the base changes nothing."),
    ("DTOR_NONTRIVIAL", "Generated-looking destructor slot with a large body and no destructor "
                        "of ours. Implicit member destruction may cover it: read before acting."),
    ("GENERATED_DTOR", "Deleting destructor: compiler output, nothing to write."),
]
LISTED = [c for c, _ in CLS_HELP if c not in ("GENERATED_DTOR", "ICF_NAME_ONLY", "ICF_SAME_AS_BASE",
                                              "CLIPPED_NAME", "ICF_TRIVIAL_OVERRIDE")]


def log(*a):
    print(*a, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------------------------
# 1. THE IMAGE.
# ---------------------------------------------------------------------------------------------
def unpack_image(dest):
    """Flat image from the zstd-packed .i64, read-only. id1 ('VA*\\0') holds 4 bytes per image
    byte, the low byte being the value; offset = VA - FLAT_BASE, unmapped gaps read as zero."""
    import zstandard
    with open(I64, "rb") as f:
        blob = f.read()
    start = blob.find(b"\x28\xb5\x2f\xfd")
    if blob[:4] != b"IDA2" or start < 0:
        raise SystemExit("vtable audit: %s is not the zstd-packed IDA2 layout this reader knows"
                         % I64)
    raw = io.BytesIO()
    rd = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(blob[start:]), read_across_frames=True)
    while True:
        b = rd.read(1 << 24)
        if not b:
            break
        raw.write(b)
    del blob
    m = raw.getbuffer()
    pos, id1 = 0, None
    data = bytes(m)
    while True:                                 # two 'VA*' sections exist; the image has many segs
        pos = data.find(b"VA*\0", pos)
        if pos < 0:
            break
        if struct.unpack_from("<I", data, pos + 8)[0] > 4:
            id1 = pos
            break
        pos += 4
    if id1 is None:
        raise SystemExit("vtable audit: no id1 section in the unpacked .i64")
    nseg = struct.unpack_from("<I", data, id1 + 8)[0]
    segs, off, cum = [], id1 + 20, 0
    for _ in range(nseg):
        s, e = struct.unpack_from("<QQ", data, off)
        off += 16
        segs.append((s, e, cum))
        cum += e - s
    base = id1 + 0x2000
    img = bytearray(segs[-1][1] - FLAT_BASE)
    for s, e, c in segs:
        img[s - FLAT_BASE:e - FLAT_BASE] = data[base + c * 4:base + (c + e - s) * 4][0::4]
    tmp = dest + ".%d.tmp" % os.getpid()     # other sessions may want the same file: atomic only
    with open(tmp, "wb") as f:
        f.write(img)
    os.replace(tmp, dest)


def load_image(path=None):
    path = path or os.environ.get("BRN_IMAGE_BIN") or IMAGE_CACHE
    if not os.path.exists(path):
        log("unpacking the ARTIST image from the .i64 ->", path)
        unpack_image(path)
    with open(path, "rb") as f:
        img = f.read()
    for ea, want, why in IMAGE_CHECKS:
        got = struct.unpack_from(">I", img, ea - FLAT_BASE)[0]
        if got != want:
            raise SystemExit("vtable audit: image miscalibrated at 0x%08X: read 0x%08X, want "
                             "0x%08X (%s)" % (ea, got, want, why))
    return img


# ---------------------------------------------------------------------------------------------
# 2. THE EXPORTS: names, sizes, and which tables each function materialises and stores.
# ---------------------------------------------------------------------------------------------
RE_ASM = re.compile(r"^0x([0-9A-Fa-f]{8})\s+(\S+)\s*(.*)$")
RE_ADDI_SYM = re.compile(r"^(r\d+),\s*r\d+,\s*[A-Za-z_]\w*?_?(82[01][0-9A-F]{5})(?:\+0x[0-9A-Fa-f]+)?@l")
RE_LIS_SYM = re.compile(r"^(r\d+),\s*[A-Za-z_]\w*?_?(82[01][0-9A-F]{5})@ha")
RE_STW = re.compile(r"^(r\d+),\s*(-?(?:0x)?[0-9A-Fa-f]+)\((r\d+)\)")
NOWRITE = {"stw", "stb", "sth", "std", "stwu", "stfs", "stfd", "cmpw", "cmpwi", "cmplw", "cmplwi",
           "cmpd", "cmpdi", "b", "bl", "beq", "bne", "blt", "bgt", "ble", "bge", "blr", "bctr",
           "bctrl", "mtctr", "mtlr", "nop", "twi", "tw"}


def vptr_stores(asm):
    """-> ([tables materialised], [(table, displacement)] stored into an object, in order).
    Linear scan, no dataflow: a store on one path of a value loaded on another is possible but
    is still a store of that table address."""
    reg, labels, stores = {}, [], []
    for raw in asm.splitlines():
        m = RE_ASM.match(raw.strip())
        if not m:
            continue
        mn, ops = m.group(2), m.group(3).strip()
        if mn == "addi":
            mm = RE_ADDI_SYM.match(ops)
            if mm:
                a = int(mm.group(2), 16)
                reg[mm.group(1)] = a
                if a not in labels:
                    labels.append(a)
                continue
        if mn == "stw":
            mm = RE_STW.match(ops)
            if mm and mm.group(1) in reg:
                try:
                    disp = int(mm.group(2), 0)
                except ValueError:
                    continue
                stores.append((reg[mm.group(1)], disp))
            continue
        if mn in NOWRITE or mn.startswith(("st", "cmp", "b")):
            continue
        reg.pop(ops.split(",")[0].strip(), None)
    return labels, stores


def load_funcs(rebuild=False):
    n_now = sum(1 for f in os.listdir(ART) if f.endswith(".json"))
    if not rebuild and os.path.exists(FUNC_CACHE):
        try:
            with open(FUNC_CACHE, encoding="utf-8") as f:
                c = json.load(f)
            if c.get("n") == n_now:
                return {int(k): v for k, v in c["g"].items()}
        except Exception:
            pass
    log("indexing %d export jsons (once; cached in %%TEMP%%)" % n_now)
    g = {}
    for fn in os.listdir(ART):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(ART, fn), encoding="utf-8", errors="replace") as f:
                j = json.load(f)
        except Exception:
            continue
        asm = j.get("assembly") or ""
        labels, stores = vptr_stores(asm)
        first = RE_ASM.match((asm.splitlines() or [""])[0].strip())
        g[int(j.get("address") or fn[:-5], 16)] = {
            "n": j.get("name") or "",
            "i": asm.count("\n") + (1 if asm else 0),
            "l": labels, "s": stores,
            "fr": [x.get("name") or "" for x in (j.get("xrefs_from") or [])],
            # A body that IS one branch. xrefs_from leaves tail calls out.
            "tail": first.group(3).strip().replace("__", "::") if first and first.group(2) == "b" else "",
        }
    tmp = FUNC_CACHE + ".%d.tmp" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"n": n_now, "g": {str(k): v for k, v in g.items()}}, f)
    os.replace(tmp, FUNC_CACHE)
    return g


# ---------------------------------------------------------------------------------------------
# 3. NAMES.
# ---------------------------------------------------------------------------------------------
def split_q(name):
    """Split on `::` outside template brackets."""
    out, cur, d, i = [], [], 0, 0
    while i < len(name):
        c = name[i]
        if c == "<":
            d += 1
        elif c == ">":
            d = max(0, d - 1)
        if c == ":" and d == 0 and name[i:i + 2] == "::":
            out.append("".join(cur))
            cur = []
            i += 2
            continue
        cur.append(c)
        i += 1
    out.append("".join(cur))
    return out


def norm_class(c):
    return "::".join(re.sub(r"<.*$", "", p) for p in split_q(c) if p)


class Name:
    """One console name, taken apart. `dtor` = deleting/plain destructor; `clipped_template` = the
    head of a template instantiation was dropped (`...Vector3,8>::GetCurre`), so the text in front
    of the method is NOT the class."""
    __slots__ = ("raw", "cls", "leaf", "dtor", "thunk", "clipped_template", "named")

    def __init__(self, raw):
        self.raw = raw
        self.named = bool(raw) and not raw.startswith(("sub_", "nullsub", "loc_", "j_", "unk_"))
        s = raw
        self.thunk = "`adjustor" in s or "`vcall" in s
        s = re.sub(r"`(adjustor|vcall)[^']*'\s*", "", s).strip()
        self.dtor = "deleting destructor" in s
        s = re.sub(r"::`[^']*'", "::~dtor", s)
        unbalanced = s.count(">") > s.count("<")
        self.clipped_template = unbalanced
        if unbalanced:
            s = s[s.rfind(">") + 1:].lstrip(":")
            self.cls, self.leaf = "", s
            return
        parts = split_q(s)
        self.leaf = parts[-1] if parts else s
        self.cls = norm_class("::".join(parts[:-1]))
        if self.leaf.startswith("~") and self.leaf != "~dtor":
            self.dtor = True


def leaf_of(cls):
    return cls.rsplit("::", 1)[-1]


# ---------------------------------------------------------------------------------------------
# 4. INHERITANCE + DECLARED METHODS, from the DWARF dump and our own headers.
# ---------------------------------------------------------------------------------------------
RE_D_CLASS = re.compile(r"^\s*(?:struct|class)\s+([A-Za-z_][^;{]*?)\s*\{\s*$")
RE_D_NS = re.compile(r"^\s*namespace\s+([A-Za-z_]\w*)\s*\{\s*$")
RE_D_METHOD = re.compile(r"(virtual\s+)?(?:[^()=;]*?[\s*&])?(~?[A-Za-z_]\w*)\s*\([^;]*\)[^;]*;\s*$")
RE_BASE = re.compile(r"(?:public|private|protected|virtual|\s)*([A-Za-z_][\w:]*(?:<.*?>)?)")


def parse_bases(txt):
    bases, d, cur = [], 0, []
    for c in txt:
        if c == "<":
            d += 1
        elif c == ">":
            d -= 1
        if c == "," and d == 0:
            bases.append("".join(cur))
            cur = []
        else:
            cur.append(c)
    bases.append("".join(cur))
    out = []
    for b in bases:
        m = RE_BASE.match(b.strip())
        if m:
            out.append(norm_class(m.group(1)))
    return out


def split_class_head(head):
    """`A::B<C::D,8u> : public E` -> (`A::B<C::D,8u>`, `public E`). The base list starts at the first
    lone colon outside template brackets; a regex cannot tell it from the colons of a `::`."""
    d, i = 0, 0
    while i < len(head):
        c = head[i]
        if c == "<":
            d += 1
        elif c == ">":
            d -= 1
        elif c == ":" and d == 0:
            if head[i:i + 2] == "::":
                i += 2
                continue
            return head[:i].strip(), head[i + 1:].strip()
        i += 1
    return head.strip(), None


def load_dwarf(rebuild=False):
    """{class: {"b": [bases], "v": [virtual methods], "m": [all methods], "sig": {m: decl}}}"""
    if not rebuild and os.path.exists(DWARF_CACHE):
        try:
            with open(DWARF_CACHE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    log("parsing the DecFIGS dwarfdump (once; cached in %TEMP%)")
    cl = defaultdict(lambda: {"b": [], "v": set(), "m": set(), "sig": {}})
    for dp, _, files in os.walk(DWARF):
        for fn in files:
            try:
                with open(os.path.join(dp, fn), encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
            except OSError:
                continue
            stack = []                      # ('ns'|'class', name) | ('other', None)
            for ln in lines:
                t = ln.strip()
                if not t or t.startswith("//"):
                    continue
                m = RE_D_NS.match(ln)
                if m:
                    stack.append(("ns", m.group(1)))
                    continue
                m = RE_D_CLASS.match(ln)
                if m:
                    name, base_txt = split_class_head(m.group(1))
                    if not stack or stack[-1][0] != "other":
                        q = norm_class("::".join([x for k, x in stack if k in ("ns", "class")] + [name]))
                        stack.append(("class", name))
                        if base_txt:
                            for b in parse_bases(base_txt):
                                if b not in cl[q]["b"]:
                                    cl[q]["b"].append(b)
                        cl[q]
                        continue
                opens, closes = t.count("{"), t.count("}")
                if stack and stack[-1][0] == "class" and opens == closes and t.endswith(";"):
                    mm = RE_D_METHOD.match(t)
                    if mm:
                        q = norm_class("::".join(x for k, x in stack if k in ("ns", "class")))
                        cl[q]["m"].add(mm.group(2))
                        if mm.group(1) or t.startswith("virtual"):
                            cl[q]["v"].add(mm.group(2))
                            cl[q]["sig"].setdefault(mm.group(2), t)
                for _ in range(opens - closes):
                    stack.append(("other", None))
                for _ in range(closes - opens):
                    if stack:
                        stack.pop()
    out = {k: {"b": v["b"], "v": sorted(v["v"]), "m": sorted(v["m"]), "sig": v["sig"]}
           for k, v in cl.items()}
    tmp = DWARF_CACHE + ".%d.tmp" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f)
    os.replace(tmp, DWARF_CACHE)
    return out


class Hierarchy:
    """Class relations by qualified name, falling back to the last component because a base may be
    spelled relative to its namespace (`GameMode` vs `BrnGameState::GameMode`)."""

    def __init__(self, dwarf, tree_bases):
        self.bases = {}
        for k, v in dwarf.items():
            if v["b"]:
                self.bases[k] = list(v["b"])
        self.by_leaf = defaultdict(set)
        for k in dwarf:
            self.by_leaf[leaf_of(k)].add(k)
        # Our headers fill in only classes DWARF does not describe: DWARF outranks them.
        for k, bs in tree_bases.items():
            lf = leaf_of(k)
            if k in self.bases or any(q in self.bases for q in self.by_leaf.get(lf, ())):
                continue
            self.bases[k] = bs
            self.by_leaf[lf].add(k)
        for k in self.bases:
            self.by_leaf[leaf_of(k)].add(k)
        self._anc = {}

    def resolve(self, c):
        if c in self.bases or c not in self.by_leaf.get(leaf_of(c), ()):
            hits = [q for q in self.by_leaf.get(leaf_of(c), ()) if q in self.bases]
            if c in self.bases:
                return c
            if len(hits) == 1:
                return hits[0]
        return c

    def ancestors(self, c):
        c = self.resolve(c)
        if c in self._anc:
            return self._anc[c]
        self._anc[c] = out = []      # cycle guard: seen-before reads as empty
        for b in self.bases.get(c, ()):
            b = self.resolve(b)
            if b not in out:
                out.append(b)
            for a in self.ancestors(b):
                if a not in out:
                    out.append(a)
        return out

    def is_ancestor(self, a, c):
        anc = self.ancestors(c)
        ra = self.resolve(a)
        return ra in anc or any(leaf_of(x) == leaf_of(ra) and len(self.by_leaf[leaf_of(ra)]) <= 1
                                for x in anc)

    def same(self, a, b):
        return a == b or self.resolve(a) == self.resolve(b)


# ---------------------------------------------------------------------------------------------
# 5. OUR TREE.
# ---------------------------------------------------------------------------------------------
RE_T_CLASS = re.compile(r"\b(?:class|struct)\s+(?:__declspec\s*\([^)]*\)\s*)?([A-Za-z_]\w*)\s*(?:final\s*)?"
                        r"(?::\s*([^;{()]+))?\{")
RE_T_QUAL = re.compile(r"(?<![\w:])((?:[A-Za-z_]\w*\s*::\s*)*[A-Za-z_]\w*)\s*::\s*(~?[A-Za-z_]\w*)\s*\(")
RE_T_ADDR = re.compile(r"0x(8[23][0-9A-Fa-f]{6})\b")


# ⛔ FOUND BY THE HAND SAMPLE, 2026-11-04. silent_link_sweep's TRAILERS repeats its alternatives with
# no whitespace between them, so `const char* GetName() const override { ... }` stops at `const`,
# sees `override {`, and reads as neither a definition nor a declaration. Every inline `const
# override` body in the tree read "defined nowhere": 23 MISSING rows at the time. Patched
# here for this tool's index only; silent_link_sweep.py itself still has the bug (see the report).
sls.TRAILERS = re.compile(r"^(?:[\s\)]|const\b|noexcept\b|override\b|final\b|throw\s*\([^)]*\)|"
                          r"__restrict\b|volatile\b|&&|&|=\s*0|=\s*default|=\s*delete)*")


class Tree:
    def __init__(self, src):
        self.src = src
        self.defs, self.decls, self.nfiles = sls.build_index(src)
        self.class_marks = defaultdict(list)    # leaf -> [rel path]
        self.bases = {}                         # leaf-or-qualified -> [bases]
        self.text = defaultdict(list)           # "Class::m" -> [mark] (hasbody's definition test)
        self.cites = defaultdict(list)          # address -> ["file:line: text"], comments included
        self._scan_text()
        self.tails = defaultdict(set)           # "Class::m" -> {full keys of 3+ components}
        self.methods = defaultdict(set)         # class leaf -> {method leaf}
        for k in list(self.defs) + list(self.decls):
            p = k.split("::")
            if len(p) >= 2:
                self.methods[p[-2]].add(p[-1])
                if len(p) >= 3:
                    self.tails["::".join(p[-2:])].add(k)
        try:
            self.mounts = sls.mount_set()
        except OSError:
            self.mounts = set()

    def _scan_text(self):
        roots = [self.src, os.path.join(os.path.dirname(self.src), "vendor")]
        for root in roots:
            for dp, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if d != ".git"]
                for fn in files:
                    if not fn.endswith((".cpp", ".h", ".hpp", ".inl", ".cc", ".c")):
                        continue
                    p = os.path.join(dp, fn)
                    try:
                        with open(p, "rb") as f:
                            raw = f.read().decode("utf-8", "replace")
                        s = sls.strip_comments(raw)
                    except OSError:
                        continue
                    rel = os.path.relpath(p, self.src).replace("\\", "/")
                    for no, line in enumerate(raw.split("\n"), 1):
                        if "0x8" in line:
                            for m in RE_T_ADDR.finditer(line):
                                self.cites[int(m.group(1), 16)].append(
                                    "%s:%d: %s" % (rel, no, line.strip()[:140]))
                    for m in RE_T_CLASS.finditer(s):
                        self.class_marks[m.group(1)].append(rel)
                        if m.group(2):
                            self.bases.setdefault(m.group(1), parse_bases(m.group(2)))
                    text_definitions(rel, s, self.text)

    def lookup(self, cls, leaf):
        """-> ('exact'|'tail'|'other_ns'|None, [marks])."""
        full = cls + "::" + leaf
        if full in self.defs:
            return "exact", self.defs[full]
        tail = "::".join(full.split("::")[-2:])
        if tail not in self.defs:
            return None, []
        fulls = self.tails.get(tail, set())
        # A longer key that is not a suffix of ours names a different namespace; a mark that
        # belongs to no longer key was written bare (`using namespace`) and is compatible.
        compat, other = [], []
        marks_in_fulls = set()
        for k in fulls:
            if k not in self.defs:
                continue
            marks_in_fulls.update(self.defs[k])
            (compat if full.endswith("::" + k) or k.endswith("::" + full) else other).append(k)
        bare = [h for h in self.defs[tail] if h not in marks_in_fulls]
        if compat or bare:
            ms = bare + [h for k in compat for h in self.defs[k]]
            return "tail", ms
        return "other_ns", [h for k in other for h in self.defs[k]]

    def declared(self, cls, leaf):
        tail = "::".join((cls + "::" + leaf).split("::")[-2:])
        return self.decls.get(cls + "::" + leaf) or self.decls.get(tail) or []

    def mounted(self, marks):
        return any(h.rsplit(":", 1)[0] in self.mounts for h in marks)

    def class_mounted(self, cls):
        lf = leaf_of(cls)
        for f in self.class_marks.get(lf, ()):
            if f in self.mounts:
                return True
        for m in self.methods.get(lf, ()):
            for h in self.defs.get(lf + "::" + m, ()):
                if h.rsplit(":", 1)[0] in self.mounts:
                    return True
        return False


def text_definitions(rel, stripped, out):
    """Second opinion on the index: hasbody.py's test for a definition form on a comment-stripped
    file. Not on its own a body proof (a macro argument can look the same), so a hit downgrades a
    MISSING rather than settling it."""
    for ln_no, code in enumerate(stripped.split("\n"), 1):
        if "::" not in code or "(" not in code:
            continue
        for m in RE_T_QUAL.finditer(code):
            prefix = code[:m.start()]
            if code.rstrip().endswith(";"):
                continue
            if re.search(r"[=(),!?;{}|+\-/%^~\[\]\"']", prefix) or \
                    re.search(r"\b(?:return|new|delete|throw|case|if|while|for|switch)\b", prefix):
                continue
            cls = re.sub(r"\s+", "", m.group(1)).split("::")[-1]
            out[cls + "::" + m.group(2)].append("%s:%d" % (rel, ln_no))


# ---------------------------------------------------------------------------------------------
# 6. THE TABLES.
# ---------------------------------------------------------------------------------------------
class Table:
    __slots__ = ("addr", "slots", "owner", "owner_why", "stores", "labelled", "parent", "parent_why")

    def __init__(self, addr, slots, labelled):
        self.addr, self.slots, self.labelled = addr, slots, labelled
        self.owner, self.owner_why, self.parent, self.parent_why = None, "", None, ""
        self.stores = []


def word(img, ea):
    return struct.unpack_from(">I", img, ea - FLAT_BASE)[0]


def is_code_ptr(v, g):
    return v in g or (CODE[0] <= v < CODE[1] and v % 4 == 0)


def split_on_second_dtor(slots, g):
    pieces, cur, seen = [], [], False
    for v in slots:
        # `destructor'` also catches IDA's clipped spelling, "destructor'`adjustor{".
        is_dtor = v in g and "destructor'" in g[v]["n"]
        if is_dtor and seen:
            pieces.append(cur)
            cur, seen = [], False
        seen = seen or is_dtor
        cur.append(v)
    pieces.append(cur)
    return pieces


def build_tables(img, g):
    labels, stores = set(), defaultdict(list)
    for a, f in g.items():
        for t in f["l"]:
            if RDATA[0] <= t < RDATA[1]:
                labels.add(t)
        for t, disp in f["s"]:
            if RDATA[0] <= t < RDATA[1]:
                stores[t].append((a, disp))
    ordered = sorted(labels)
    tables, covered = {}, set()
    for idx, lab in enumerate(ordered):
        nxt = ordered[idx + 1] if idx + 1 < len(ordered) else RDATA[1]
        slots, ea = [], lab
        while ea < nxt and ea % 4 == 0:
            v = word(img, ea)
            if not is_code_ptr(v, g):
                break
            slots.append(v)
            ea += 4
        if not slots or not all(s in g or is_code_ptr(s, g) for s in slots):
            continue
        # A vtable holds one destructor, so a second one starts another table the code never
        # materialises (a secondary vptr, usually). Left merged, TrafficState's table reads as
        # TrafficControl's and its overrides as folds of the wrong methods.
        start = lab
        for piece in split_on_second_dtor(slots, g):
            t = Table(start, piece, start == lab)
            t.stores = stores.get(start, [])
            tables[start] = t
            start += 4 * len(piece)
        covered.update(range(lab, ea, 4))
    # Runs nobody materialises: an abstract base whose ctor was inlined away. No store evidence,
    # so everything derived from them is low confidence.
    ea = RDATA[0] + (-RDATA[0] % 4)
    while ea < RDATA[1] - 4:
        if ea in covered or not is_code_ptr(word(img, ea), g) or word(img, ea) not in g:
            ea += 4
            continue
        start, slots = ea, []
        while ea < RDATA[1] and ea not in covered and word(img, ea) in g:
            slots.append(word(img, ea))
            ea += 4
        if len(slots) >= 3:
            tables[start] = Table(start, slots, False)
    return tables


def ctor_evidence(t, g):
    """Classes whose own ctor/dtor stores this table at +0. A ctor stores base tables first and
    its own last, a dtor the reverse, so only that extreme store counts."""
    out = []
    for fa, disp in t.stores:
        if disp != 0:
            continue
        f = g.get(fa)
        if not f:
            continue
        nm = Name(f["n"])
        if not nm.named or not nm.cls:
            continue
        lf = leaf_of(nm.cls)
        zero = [x for x, d in f["s"] if d == 0 and RDATA[0] <= x < RDATA[1]]
        if nm.leaf == lf and zero and zero[-1] == t.addr:
            out.append(nm.cls)
        elif (nm.dtor or nm.leaf in ("~" + lf, "~dtor")) and zero and zero[0] == t.addr:
            out.append(nm.cls)
    return out


def assign_owners(tables, g, hy):
    # ⛔ A plain slot count picks the wrong owner: FaceOffMode's table holds 8 slots of the empty
    # body IDA named BaseCollisionGenerator::Destruct, more than any real name. Evidence is
    # weighted by how much a body can say: one shared by a crowd of tables says nothing, a tiny one
    # says little (it is what folds), a real one says this class wrote it.
    spread = Counter()
    for t in tables.values():
        for s in set(t.slots):
            spread[s] += 1

    def weight(s):
        if spread[s] > 12:
            return 0
        return 1 if g[s]["i"] <= 4 else 3

    own_named = defaultdict(int)    # class -> bodies named for it, across all tables
    for t in tables.values():
        for s in t.slots:
            if s in g:
                n = Name(g[s]["n"])
                if n.named and n.cls and not n.dtor and not n.clipped_template:
                    own_named[hy.resolve(n.cls)] += 1

    for t in tables.values():
        named, weighted = Counter(), Counter()
        for s in t.slots:
            if s not in g:
                continue
            n = Name(g[s]["n"])
            if n.named and n.cls and not n.clipped_template:
                named[n.cls] += 1
                weighted[n.cls] += weight(s)
        ctors = Counter(ctor_evidence(t, g))
        cands = set(named) | set(ctors)
        if not cands:
            continue

        def score(c):
            ex = sum(k for x, k in weighted.items() if hy.same(x, c) or hy.is_ancestor(x, c))
            un = sum(k for x, k in named.items() if hy.same(x, c) or hy.is_ancestor(x, c))
            return (ex + 3 * ctors.get(c, 0), un, len(hy.ancestors(c)), named.get(c, 0), c)

        best = max(cands, key=score)
        # A derived class whose table holds only inherited bodies has no slot of its own: its ctor
        # is the only thing that can name it. Prefer it when it descends from the best slot class.
        # ...unless that class visibly has a table of its own and this one names nothing of it:
        # then the store is a base-subobject store (DeviceMemFileSystem storing DeviceDriver's).
        for c in ctors:
            if hy.is_ancestor(best, c) and not (named.get(c, 0) == 0 and own_named.get(hy.resolve(c))):
                best = c
        t.owner = best
        t.owner_why = "ctor/dtor store" if ctors.get(best) else "slot names + hierarchy"


def assign_parents(tables, g, hy):
    """Nearest table to compare slots with: an ancestor's when the hierarchy has one, else the most
    similar table (same index, same target), which is weaker evidence and marked so."""
    by_owner = defaultdict(list)
    for t in tables.values():
        if t.owner:
            by_owner[hy.resolve(t.owner)].append(t)
    for t in tables.values():
        if not t.owner:
            continue
        best, bestn = None, 0
        for depth, a in enumerate(hy.ancestors(t.owner)):
            for p in by_owner.get(a, ()):
                if p is t:
                    continue
                n = sum(1 for x, y in zip(t.slots, p.slots) if x == y)
                if n > bestn:
                    best, bestn = p, n
            if best is not None:
                break               # nearest ancestor holding a table wins over a farther one
        if best is not None:
            t.parent, t.parent_why = best.addr, "hierarchy"


def similar_parents(tables):
    """Hierarchy unknown: the table sharing the most same-index slots, if it shares most of them.
    The candidate must be no larger, or it would be a child rather than a parent."""
    by_slot = defaultdict(set)
    for t in tables.values():
        for i, s in enumerate(t.slots):
            by_slot[(i, s)].add(t.addr)
    for t in tables.values():
        if t.parent is not None or not t.owner or len(t.slots) < 4:
            continue
        c = Counter()
        for i, s in enumerate(t.slots):
            hits = by_slot[(i, s)]
            if len(hits) > 60:
                continue
            for a in hits:
                if a != t.addr and len(tables[a].slots) <= len(t.slots):
                    c[a] += 1
        if c:
            a, n = c.most_common(1)[0]
            if n >= max(3, len(t.slots) * 0.6):
                t.parent, t.parent_why = a, "similarity"


def slot_method(t, i, tables, g, hy, seen=None):
    """The method a slot means, walking up the parent chain until a table names it for a class on
    this table's own side of the hierarchy. None when the chain never does."""
    seen = seen or set()
    p = tables.get(t.parent) if t.parent else None
    while p is not None and p.addr not in seen:
        seen.add(p.addr)
        if i < len(p.slots) and p.slots[i] in g:
            n = Name(g[p.slots[i]]["n"])
            if n.named and n.cls and not n.clipped_template and p.owner and \
                    (hy.same(n.cls, p.owner) or hy.is_ancestor(n.cls, p.owner)):
                return n.leaf, n.cls
        p = tables.get(p.parent) if p.parent else None
    return None, None


# ---------------------------------------------------------------------------------------------
# 7. THE CLASSIFICATION.
# ---------------------------------------------------------------------------------------------
def method_status(tree, cls, leaf, dw):
    """-> (state, marks, full_name_if_resolved, trunc_candidates).
    state: present | truncated | other_ns | missing."""
    kind, marks = tree.lookup(cls, leaf)
    if kind in ("exact", "tail"):
        return "present", marks, leaf, []
    t = tree.text.get(leaf_of(cls) + "::" + leaf)
    if t:
        return "present_text", t, leaf, []
    lf = leaf_of(cls)
    drec = dw.get(cls) or {}
    dm = set(drec.get("m", ()))
    if leaf in dm:                 # DWARF has this exact spelling: the name is not clipped
        return ("other_ns" if kind == "other_ns" else "missing"), marks, leaf, []
    dcand = sorted(x for x in dm if x.startswith(leaf) and x != leaf)
    if dcand and len(leaf) >= 3:
        for c in dcand:            # clipped, DWARF knows the whole name: decide on that name
            k2, m2 = tree.lookup(cls, c)
            if k2 in ("exact", "tail") or tree.text.get(lf + "::" + c):
                return "present", m2, c, dcand
        return "missing", [], dcand[0], dcand
    tcand = sorted(x for x in tree.methods.get(lf, ()) if x.startswith(leaf) and x != leaf)
    if tcand and len(leaf) >= 3:
        return "truncated", [], leaf, tcand
    return ("other_ns" if kind == "other_ns" else "missing"), marks, leaf, []


def bucket_of(name, file):
    blob = "%s %s" % (name, file or "")
    if PLATFORM_RE.search(blob):
        return "console"
    if VENDOR_RE.search(name) or VENDOR_FILE_RE.search(file or ""):
        return "vendor"
    return "game"


def subsystem_of(name, file):
    if file:
        p = re.sub(r"^.*?/\.\./", "", file.replace("\\", "/"))
        p = re.sub(r"^(?:GameSource|GameShared|SharedClasses)/", "", p)
        parts = p.split("/")
        if len(parts) > 1 and parts[0] not in ("Unity", "Generated"):
            return parts[0]
    return name.split("::")[0] if "::" in name else "<global>"


def seems_clipped(raw, leaf):
    """No DWARF to ask: a name right at the clipping widths, cut mid-word."""
    return len(raw) in range(38, 43) and bool(re.search(r"[a-z]$|[A-Z]$", leaf)) \
        and not re.search(r"(Update|Start|Init\w*|Name|Type|Size|Count|Data|Render|Stop|Event|End|"
                          r"Reset|Clear|Enter|Exit|Load|Save|Close|Open|Create|Destroy|Id|ID|Add|"
                          r"Remove|Get|Set|Is)$", leaf)


def audit(src=None, image=None, rebuild=False):
    src = src or os.path.join(REPO, "b5-decomp", "src")
    img = load_image(image)
    g = load_funcs(rebuild)
    dw = load_dwarf(rebuild)
    with open(os.path.join(REPO, "progress", "identity.json"), encoding="utf-8") as f:
        ident = json.load(f)
    addr_file = {}
    for k, rec in ident.items():
        for a in rec.get("x360_addrs") or []:
            addr_file.setdefault(int(a, 16), rec.get("primary_file"))
    tree = Tree(src)
    hy = Hierarchy(dw, tree.bases)
    tables = build_tables(img, g)
    assign_owners(tables, g, hy)
    assign_parents(tables, g, hy)
    similar_parents(tables)
    rows, counts, st = [], Counter(), {}
    # target -> [(table, slot)]
    where = defaultdict(list)
    for t in tables.values():
        for i, s in enumerate(t.slots):
            where[s].append((t.addr, i))
    purecall = {a for a, f in g.items() if f["n"] == "_purecall"}
    known_q = set(dw) | set(hy.bases)
    ns_prefixes = set()      # everything a known class is qualified by: namespaces and outer classes
    for q in known_q:
        parts = q.split("::")
        for k in range(1, len(parts)):
            ns_prefixes.add("::".join(parts[:k]))

    def rowbase(name, addr, ninstr, cls, slots):
        file = addr_file.get(addr)
        return dict(name=name, addr="0x%08X" % addr, ninstr=ninstr, cls=cls, file=file,
                    bucket=bucket_of(name, file), subsystem=subsystem_of(name, file),
                    debug=bool(DEBUG_RE.search(name)), online=bool(ONLINE_RE.search(name)),
                    slots=[{"table": "0x%08X" % a, "slot": i,
                            "owner": tables[a].owner, "owner_why": tables[a].owner_why,
                            "stored": len(tables[a].stores)} for a, i in slots][:6],
                    nslots=len(slots), cited=tree.cites.get(addr, [])[:3])

    # --- A. every body with a name: is it in our tree?
    for addr, slots in where.items():
        if addr in purecall or addr not in g:
            counts["pure_or_noexport"] += 1
            continue
        nm = Name(g[addr]["n"])
        if not nm.named:
            continue
        ninstr = g[addr]["i"]
        if nm.clipped_template:
            hits = [c for c, ms in tree.methods.items()
                    if any(x == nm.leaf or x.startswith(nm.leaf) for x in ms)] if len(nm.leaf) >= 3 else []
            if hits:
                counts["PRESENT_TEMPLATE"] += 1
                continue
            rows.append(dict(rowbase(g[addr]["n"], addr, ninstr, "TEMPLATE_UNRESOLVED", slots),
                             confidence="low", why="template head clipped by IDA; leaf `%s` is "
                             "defined nowhere in the tree" % nm.leaf))
            continue
        if not nm.cls:
            counts["free_function_in_table"] += 1
            continue
        cls, leaf = nm.cls, nm.leaf
        # The clip fell inside the qualifier: `Ns::Logic::` (no leaf), `Ns::Clas` or
        # `Ns::Playback::GenericRwacMasterVoice` (the "method" is the start of a class name),
        # `Ns::Input,cla` (inside a template list). Nothing here can be looked up.
        if not leaf or "," in leaf or any(q.startswith(cls + "::" + leaf) for q in known_q) or                 (cls in ns_prefixes and cls not in known_q and leaf_of(cls) not in tree.class_marks):
            if tree.lookup(cls, leaf)[0] not in ("exact", "tail"):
                rows.append(dict(rowbase(g[addr]["n"], addr, ninstr, "CLIPPED_NAME", slots),
                                 confidence="medium", why="name clipped inside its qualifier"))
                continue
        owners = [tables[a].owner for a, _ in slots if tables[a].owner]
        own_tables = [(a, i) for a, i in slots
                      if tables[a].owner and (hy.same(cls, tables[a].owner)
                                              or hy.is_ancestor(cls, tables[a].owner))]
        legit = bool(own_tables)

        if nm.dtor:
            has_dtor = tree.lookup(cls, "~" + leaf_of(cls))[0] in ("exact", "tail")
            if has_dtor or ninstr < 30:
                counts["GENERATED_DTOR"] += 1
                if not has_dtor:
                    rows.append(dict(rowbase(g[addr]["n"], addr, ninstr, "GENERATED_DTOR", slots),
                                     confidence="high", why="deleting destructor, small body"))
                continue
            callees = [x for x in g[addr]["fr"] if x and not x.startswith(("__", "sub_"))
                       and "free" not in x.lower() and "delete" not in x.lower()]
            rows.append(dict(rowbase(g[addr]["n"], addr, ninstr, "DTOR_NONTRIVIAL", slots),
                             confidence="low", callees=callees[:12],
                             class_in_tree=leaf_of(cls) in tree.class_marks,
                             why="%d-instruction destructor and no `~%s` in the tree"
                             % (ninstr, leaf_of(cls))))
            continue

        state, marks, resolved, cand = method_status(tree, cls, leaf, dw)
        if state in ("present", "present_text"):
            counts["PRESENT" if state == "present" else "PRESENT_TEXT_ONLY"] += 1
            if state == "present" and marks and not tree.mounted(marks) and legit \
                    and any(h.split(":")[0].endswith(".cpp") for h in marks):
                counts["present_but_unmounted"] += 1
            continue

        if not legit:
            rows.append(dict(rowbase(g[addr]["n"], addr, ninstr, "ICF_NAME_ONLY", slots),
                             confidence="medium",
                             why="no table holding this body belongs to %s or a class derived from "
                             "it (owners: %s)" % (cls, ", ".join(sorted(set(filter(None, owners))))[:160])))
            continue

        # Same address in the parent's slot: the name was picked for the derived class, the body
        # is the base's. Dropping the override changes nothing, so this is not a behavioural miss.
        same = []
        for a, i in own_tables:
            t = tables[a]
            p = tables.get(t.parent) if t.parent else None
            if p is not None and i < len(p.slots) and p.slots[i] == addr and p.owner and \
                    not hy.same(p.owner, cls) and hy.is_ancestor(p.owner, cls):
                same.append(a)
        if same and len(same) == len(own_tables):
            rows.append(dict(rowbase(g[addr]["n"], addr, ninstr, "ICF_SAME_AS_BASE", slots),
                             confidence="medium",
                             why="parent table 0x%08X holds the same address" % tables[same[0]].parent))
            continue

        class_in = leaf_of(cls) in tree.class_marks or leaf_of(cls) in tree.methods
        drec = dw.get(cls) or {}
        dvirt = resolved in set(drec.get("v", ()))
        own_stored = any(tables[a].stores for a, _ in own_tables)
        ctor_owned = any(tables[a].owner_why == "ctor/dtor store" for a, _ in own_tables)
        exact_owner = any(hy.same(tables[a].owner, cls) for a, _ in own_tables)
        clipped_guess = not cand and leaf not in set(drec.get("m", ())) and seems_clipped(g[addr]["n"], leaf)
        fallback = None
        for a in hy.ancestors(cls):
            if tree.lookup(a, resolved)[0] in ("exact", "tail"):
                fallback = a + "::" + resolved
                break
        declared = tree.declared(cls, resolved)[:2]

        if state == "truncated":
            c, conf, why = "TRUNCATED_MATCH", "medium", "clipped name; tree candidates: " + ", ".join(cand[:4])
        elif state == "other_ns":
            c, conf = "AMBIGUOUS_NAMESPACE", "low"
            why = "defined under another namespace: " + ", ".join(marks[:2])
        else:
            c = "MISSING" if class_in else "MISSING_CLASS_ABSENT"
            score = (2 if dvirt else 0) + (1 if own_stored else 0) + (1 if exact_owner else 0) \
                + (1 if ctor_owned else 0) - (2 if clipped_guess else 0) - (1 if ninstr <= 2 else 0)
            conf = "high" if score >= 3 and own_stored else ("medium" if score >= 2 else "low")
            # The tree cites this very address. A note saying it is not reconstructed yet reads the
            # same as a body renamed or absorbed elsewhere (RemapDevice::Init landed as Connect):
            # the address cannot settle it, so the row stays and a human reads the citation.
            if tree.cites.get(addr):
                conf = {"high": "medium", "medium": "low"}.get(conf, conf)
            bits = ["table stored by code" if own_stored else "table has NO store evidence",
                    "DWARF: virtual" if dvirt else ("DWARF: not declared virtual" if drec else "not in DWARF")]
            if clipped_guess:
                bits.append("name may be clipped")
            if resolved != leaf:
                bits.append("clipped name resolved via DWARF")
            if tree.cites.get(addr):
                bits.append("address cited in the tree: may be renamed or absorbed, read the citation")
            why = "; ".join(bits)
        rows.append(dict(rowbase(g[addr]["n"], addr, ninstr, c, slots), confidence=conf, why=why,
                         method=resolved, class_name=cls, class_in_tree=class_in,
                         class_mounted=tree.class_mounted(cls), fallback=fallback,
                         declared=declared, dwarf_sig=(drec.get("sig") or {}).get(resolved),
                         candidates=cand[:6],
                         forwards_to_base=forwards_to_base(g[addr], resolved, cls, hy)))

    # --- B. slots whose body carries a foreign name (or none): the override is folded/unnamed.
    slot_pass(tables, g, hy, tree, dw, rows, counts, addr_file, rowbase)

    st.update(n_tables=len(tables),
              n_tables_owned=sum(1 for t in tables.values() if t.owner),
              n_tables_stored=sum(1 for t in tables.values() if t.stores),
              n_tables_unlabelled=sum(1 for t in tables.values() if not t.labelled),
              n_tables_parent_hier=sum(1 for t in tables.values() if t.parent_why == "hierarchy"),
              n_tables_parent_sim=sum(1 for t in tables.values() if t.parent_why == "similarity"),
              n_slots=sum(len(t.slots) for t in tables.values()),
              n_bodies=len(where), files=tree.nfiles)
    return rows, counts, st, tables, g, tree


def forwards_to_base(f, leaf, cls, hy):
    """A body that only tail-calls an ancestor's method of the same name: the console has the
    override, inheriting changes nothing. FaceOffMode::PreWorldUpdate is exactly this."""
    if f.get("tail"):
        callee = f["tail"]
    elif f["i"] <= 3 and len(f["fr"]) == 1 and f["fr"][0]:
        callee = f["fr"][0]
    else:
        return False
    n = Name(callee)
    return n.leaf == leaf and bool(n.cls) and hy.is_ancestor(n.cls, cls)


def dwarf_pass(tables, g, hy, tree, dw, rows, counts, rowbase, seen):
    """DWARF says C declares virtual m, our tree has no body, and a RELATED table names m at slot i.
    C's slot i then holds a body carrying someone else's name. The parent walk misses this when
    the only comparable table is a sibling's and the bodies match: BoostBurnout5 slot 14 is
    `BoostBurnout2::OnEndCrashPlay`, the same address as its sibling and not the empty base."""
    reported = {r["name"] for r in rows}
    by_base = defaultdict(list)
    for t in tables.values():
        if t.owner:
            for a in hy.ancestors(t.owner):
                by_base[a].append(t)
    for t in tables.values():
        if not t.owner:
            continue
        cls = hy.resolve(t.owner)
        drec = dw.get(cls) or dw.get(t.owner) or {}
        for m in drec.get("v", ()):
            if m.startswith("~") or (cls, m) in seen or t.owner + "::" + m in reported:
                continue
            if method_status(tree, t.owner, m, dw)[0] != "missing":
                continue
            found = None
            for a in hy.ancestors(t.owner):
                for other in by_base.get(a, ()):
                    if other is t:
                        continue
                    for i, s in enumerate(other.slots):
                        if i < len(t.slots) and s in g and Name(g[s]["n"]).leaf == m:
                            found = (i, other, a)
                            break
                    if found:
                        break
                if found:
                    break
            if not found:
                continue
            i, other, base = found
            s = t.slots[i]
            if s not in g:
                continue
            nm = Name(g[s]["n"])
            if nm.named and nm.cls and hy.same(nm.cls, t.owner):
                continue            # named for this class: pass A reports it
            if nm.named and nm.cls and hy.is_ancestor(nm.cls, t.owner):
                continue            # the ancestor's own body: truly inherited
            seen.add((cls, m))
            trivial = g[s]["i"] <= 2
            r = rowbase(t.owner + "::" + m, s, g[s]["i"],
                        "ICF_TRIVIAL_OVERRIDE" if trivial else "ICF_OVERRIDE_MISSING", [(t.addr, i)])
            # The slot is mapped through a sibling, so this never reaches high.
            r.update(confidence="low" if trivial or not t.stores else "medium", method=m, class_name=t.owner,
                     folded_as=g[s]["n"], parent_table="0x%08X" % other.addr, parent_why="dwarf+sibling",
                     class_in_tree=leaf_of(t.owner) in tree.class_marks,
                     class_mounted=tree.class_mounted(t.owner), fallback=base + "::" + m,
                     dwarf_sig=(drec.get("sig") or {}).get(m),
                     forwards_to_base=forwards_to_base(g[s], m, t.owner, hy),
                     why="DWARF declares it virtual on this class; sibling table 0x%08X names `%s` at "
                         "slot %d; here the slot holds `%s`" % (other.addr, m, i, g[s]["n"] or "sub_"))
            rows.append(r)
            counts["dwarf_pass_rows"] += 1


def slot_pass(tables, g, hy, tree, dw, rows, counts, addr_file, rowbase):
    seen = set()
    for t in tables.values():
        if not t.owner or not t.parent:
            continue
        p = tables[t.parent]
        for i, s in enumerate(t.slots):
            if s not in g or (i < len(p.slots) and p.slots[i] == s):
                continue            # inherited: same address as the parent
            nm = Name(g[s]["n"])
            if nm.named and nm.cls and (hy.same(nm.cls, t.owner) or hy.is_ancestor(nm.cls, t.owner)):
                continue            # handled by pass A under its own name
            if i >= len(p.slots):
                counts["new_virtual_foreign_name"] += 1
                continue            # a new virtual nobody up the chain names: unknowable here
            leaf, base = slot_method(t, i, tables, g, hy)
            if not leaf or leaf == "~dtor" or leaf.startswith("~"):
                counts["icf_slot_unknown_method"] += 1
                continue
            # A similarity parent can point the wrong way (a sibling or a child). The slot then
            # proves nothing about this class's override.
            if hy.same(base, t.owner) or hy.is_ancestor(t.owner, base):
                counts["icf_slot_wrong_way_parent"] += 1
                continue
            key = (hy.resolve(t.owner), leaf)
            if key in seen:
                continue
            seen.add(key)
            state, _, _, _ = method_status(tree, t.owner, leaf, dw)
            if state in ("present", "present_text", "truncated"):
                counts["ICF_OVERRIDE_PRESENT"] += 1
                continue
            # What actually runs here is the nearest real ancestor's body, not a similar table's.
            for a in hy.ancestors(t.owner):
                if tree.lookup(a, leaf)[0] in ("exact", "tail"):
                    base = a
                    break
            cls = "ICF_TRIVIAL_OVERRIDE" if g[s]["i"] <= 2 else (
                "ICF_OVERRIDE_MISSING" if nm.named else "UNNAMED_OVERRIDE_MISSING")
            name = t.owner + "::" + leaf
            r = rowbase(name, s, g[s]["i"], cls, [(t.addr, i)])
            drec = dw.get(t.owner) or {}
            dvirt = leaf in set(drec.get("v", ()))
            conf = "high" if dvirt and t.parent_why == "hierarchy" and t.stores else (
                "medium" if t.parent_why == "hierarchy" else "low")
            r.update(confidence=conf, method=leaf, class_name=t.owner, folded_as=g[s]["n"],
                     parent_table="0x%08X" % t.parent, parent_why=t.parent_why,
                     class_in_tree=leaf_of(t.owner) in tree.class_marks,
                     class_mounted=tree.class_mounted(t.owner), fallback=base + "::" + leaf,
                     dwarf_sig=(drec.get("sig") or {}).get(leaf),
                     forwards_to_base=forwards_to_base(g[s], leaf, t.owner, hy),
                     why="slot %d differs from parent 0x%08X (%s), which names `%s`; body is folded "
                         "as `%s`%s" % (i, t.parent, t.parent_why, leaf, g[s]["n"] or "sub_",
                                        "; DWARF: virtual" if dvirt else ""))
            rows.append(r)
    dwarf_pass(tables, g, hy, tree, dw, rows, counts, rowbase, seen)


# ---------------------------------------------------------------------------------------------
# 8. CONTROL. A sweep you have not watched find a known instance is not a sweep.
# ---------------------------------------------------------------------------------------------
def tree_has_body(name, tree):
    """The arbiter is hasbody.py's question, asked of the same tree: is there a definition form?"""
    parts = name.split("::")
    k, marks = tree.lookup("::".join(parts[:-1]), parts[-1])
    return k in ("exact", "tail") or bool(tree.text.get("::".join(parts[-2:]))), marks


def evaluate_control(rows, tree, tables, g):
    """-> (ok, lines). A known case with no body MUST come out as MISSING at its address; a case
    with a body has been fixed and passes as such (the fix is the point). Three negative checks
    guard the opposite failure, a tool that calls everything missing."""
    by = {r["name"]: r for r in rows}
    ok, out = True, []
    for name, addr in CONTROL:
        body, marks = tree_has_body(name, tree)
        r = by.get(name)
        if body:
            out.append("  fixed   %-58s body exists: %s" % (name, (marks or ["?"])[0]))
            if r and r["cls"] in ("MISSING", "MISSING_CLASS_ABSENT"):
                out.append("  FAIL    ...but the audit still reports it %s" % r["cls"])
                ok = False
            continue
        if not r:
            out.append("  FAIL    %-58s no body, and the audit did not report it" % name)
            ok = False
            continue
        if r["cls"] != "MISSING" or r["addr"] != "0x%08X" % addr:
            out.append("  FAIL    %-58s reported as %s at %s (want MISSING at 0x%08X)"
                       % (name, r["cls"], r["addr"], addr))
            ok = False
            continue
        s0 = r["slots"][0]
        out.append("  found   %-58s %s %s slot %d of %s, conf %s"
                   % (name, r["addr"], r["cls"], s0["slot"], s0["table"], r["confidence"]))
    t = tables.get(0x820D0500)
    if t is None or hy_leaf(t.owner) != "FaceOffMode":
        out.append("  FAIL    table 0x820D0500 is not owned by FaceOffMode (owner: %s)"
                   % (t.owner if t else None))
        ok = False
    else:
        out.append("  owner   table 0x820D0500 -> %s (%s), parent 0x%08X"
                   % (t.owner, t.owner_why, t.parent or 0))
    # An ICF fold must not read as a miss of the class whose name it happens to carry.
    r = by.get("CgsGraphics::MovieVideoRenderer::GetRenderingDelay")
    if r and r["cls"] in ("MISSING", "MISSING_CLASS_ABSENT"):
        out.append("  FAIL    the 0.0f fold GetRenderingDelay reads as a plain miss")
        ok = False
    else:
        out.append("  icf     GetRenderingDelay (FaceOffMode slot 8's fold) is not a plain miss")
    # A body we do have must not be listed.
    for name in ("BrnGameState::FaceOffMode::GetName", "BrnGameState::FaceOffMode::GetOutroTimeout"):
        if name in by and by[name]["cls"] in LISTED:
            out.append("  FAIL    %s has a body and is listed as %s" % (name, by[name]["cls"]))
            ok = False
    out.append("  present FaceOffMode::GetName / GetOutroTimeout have bodies and are not listed")
    return ok, out


def hy_leaf(c):
    return leaf_of(c) if c else None


def control(src=None, image=None, rebuild=False):
    rows, counts, st, tables, g, tree = audit(src, image, rebuild)
    ok, lines = evaluate_control(rows, tree, tables, g)
    print("\n".join(lines))
    print("CONTROL", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ---------------------------------------------------------------------------------------------
# 9. THE REPORT.
# ---------------------------------------------------------------------------------------------
def load_verdicts():
    if not os.path.exists(VERDICTS):
        return {}
    with open(VERDICTS, encoding="utf-8") as f:
        return json.load(f)


def md_table(rows):
    L = ["| method | addr | insns | conf | class in tree / mounted | falls back on | table / slot |",
         "|---|---|---:|---|---|---|---|"]
    for r in rows:
        s = r["slots"][0] if r["slots"] else {"table": "?", "slot": 0}
        L.append("| `%s` | `%s` | %d | %s | %s / %s | %s | `%s` / %d |" % (
            r["name"], r["addr"], r["ninstr"],
            r["confidence"] + (", forwards to base" if r.get("forwards_to_base") else ""),
            "yes" if r.get("class_in_tree") else "no", "yes" if r.get("class_mounted") else "no",
            ("`%s`" % r["fallback"]) if r.get("fallback") else "", s["table"], s["slot"]))
    return L


def emit(rows, counts, st, rev, control_lines, control_ok, out_md, out_json):
    verdicts = load_verdicts()
    rows.sort(key=lambda r: (r["cls"], -r["ninstr"], r["name"]))
    for r in rows:
        if r["name"] in verdicts:
            r["verdict"] = verdicts[r["name"]].get("verdict")
    c_cls = Counter(r["cls"] for r in rows)
    with open(out_json, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"b5_rev": rev, "stats": st, "counts": dict(sorted(counts.items())),
                   "by_class": dict(sorted(c_cls.items())), "control_pass": control_ok,
                   "rows": rows}, f, indent=0, sort_keys=True)
        f.write("\n")

    L = []
    W = L.append
    W("# Vtable override audit -- console overrides our classes do not have")
    W("")
    W("<!-- GENERATED by tools/re/vtable_override_audit.py. Hand verdicts live in "
      "tools/re/vtable_override_verdicts.json; do not edit this file. -->")
    W("b5-decomp rev `%s`. Control: **%s**." % (rev, "PASS" if control_ok else "FAIL"))
    W("")
    W("A virtual the console overrides and we do not **compiles and links in silence**: the slot "
      "falls back on the base. Being virtual, it has no direct caller either, so "
      "`silent_link_sweep.py` can only file it in its class C. This audit reads the console's "
      "tables instead of its call graph.")
    W("")
    W("%d tables, %d slots, %d distinct bodies. %d tables have an owner, %d are stored into an "
      "object by code. Parent table known from the hierarchy for %d, by similarity for %d."
      % (st["n_tables"], st["n_slots"], st["n_bodies"], st["n_tables_owned"], st["n_tables_stored"],
         st["n_tables_parent_hier"], st["n_tables_parent_sim"]))
    W("")
    W("## Counts")
    W("")
    W("| class | rows | game | console | vendor | high | medium | low | meaning |")
    W("|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for c, why in CLS_HELP:
        sub = [r for r in rows if r["cls"] == c]
        n = counts[c] if c == "GENERATED_DTOR" else len(sub)
        b = Counter(r["bucket"] for r in sub)
        k = Counter(r["confidence"] for r in sub)
        W("| %s | %d | %d | %d | %d | %d | %d | %d | %s |" % (
            c, n, b["game"], b["console"], b["vendor"], k["high"], k["medium"], k["low"], why))
    W("")
    W("Bodies with a definition, not listed: **%d** (of which %d found only by the raw-text second "
      "opinion). Folded overrides whose method we do define: %d. Foreign-name slots whose method "
      "cannot be named from the chain: %d."
      % (counts["PRESENT"] + counts["PRESENT_TEXT_ONLY"] + counts["PRESENT_TEMPLATE"],
         counts["PRESENT_TEXT_ONLY"], counts["ICF_OVERRIDE_PRESENT"], counts["icf_slot_unknown_method"]))
    W("")
    W("**Confidence.** `high`: the table is stored by code and at least two of: DWARF declares the "
      "method virtual on this class, the table's owner is exactly this class, a ctor/dtor of the "
      "class stores it. `medium`: part of that, or the tree cites the address (it may be renamed or absorbed "
      "elsewhere). `low`: no store evidence, or the name may be "
      "clipped. Confidence says how sure the row is that the console has this override; it does "
      "not say the row matters.")
    W("")
    # verification
    W("## Hand verification")
    W("")
    render_verification(W, rows, verdicts)
    W("")
    W("## The 20 most important true gaps")
    W("")
    W("Game code, hand-checked and ranked by hand: what a player reaches offline first, then the "
      "online modes, then latent or teardown code. The order is a judgement, not a measurement; "
      "nothing here was run. A sort by size would put teardown stages above a 6-instruction boost "
      "payout. Other sessions may be filling some of these on other branches: this reads the b5 "
      "revision named at the top.")
    W("")
    render_top(W, rows, verdicts)
    W("")
    # game
    game = [r for r in rows if r["bucket"] == "game" and r["cls"] in LISTED]
    W("## Game code (%d rows)" % len(game))
    W("")
    render_subsystems(W, game)
    W("")
    W("## Console-only code (%d rows)" % sum(1 for r in rows if r["bucket"] == "console" and r["cls"] in LISTED))
    W("")
    W("XAudio, Snd9, WMV, XCam, MassiveAd and the like, selected by name or source path. A miss "
      "here is usually a platform decision rather than a defect: read it as a list of decisions to "
      "confirm. A subset of `rw::` sits here because its name matches, not because it was reviewed.")
    W("")
    render_subsystems(W, [r for r in rows if r["bucket"] == "console" and r["cls"] in LISTED])
    W("")
    W("## Vendor / SDK (%d rows)" % sum(1 for r in rows if r["bucket"] == "vendor" and r["cls"] in LISTED))
    W("")
    W("`rw::`, `EA::`, `Apt*`, anything under `SDKs/`. Largest 40; the rest are in the JSON. Vendor "
      "code is often supplied whole by an original source or a host implementation "
      "(`tools/work/check_vendor_lib.py`), which this audit does not model.")
    W("")
    W("\n".join(md_table(sorted([r for r in rows if r["bucket"] == "vendor" and r["cls"] in LISTED],
                                key=lambda r: -r["ninstr"])[:40])))
    W("")
    W("## What this audit cannot see")
    W("")
    W("0. **`--control` cannot prove completeness.** It proves known cases come out, nothing about "
      "cases nobody has found. `BoostBurnout5::OnEndCrashPlay` slipped past the first design and "
      "only surfaced by reading a neighbouring row.")
    W("1. **A body is not a behaviour.** A row without a definition may have been inlined by hand "
      "into a caller; a row with one may be wrong. This only asks whether `Class::method` exists.")
    W("2. **Overloads collapse.** One defined overload hides a missing one. A definition whose "
      "signature differs from the base's virtual hides the base instead of overriding it, and is "
      "counted as present.")
    W("3. **Table boundaries.** A table starts at a materialised address. An unmaterialised table "
      "directly after a labelled one reads as extra slots of the first, usually with foreign names, "
      "so it lands in the ICF classes rather than MISSING. It errs towards under-reporting.")
    W("4. **New virtuals with folded bodies.** A slot past the end of the parent's table whose body "
      "is folded has no method name to look up (%d such slots)." % counts["new_virtual_foreign_name"])
    W("5. **DWARF is the PS3 build.** The hierarchy and the `virtual` flags come from DecFIGS, a "
      "near-ancestor. Where ARTIST moved, the owner of a table can be wrong: the table address and "
      "slot are given so the claim can be read directly.")
    W("6. **`class in tree` matches the last name component** and is not proof of the same class.")
    W("7. **Mounted is not executed.** Nothing here shows the mode or object is ever reached.")
    W("")
    W("## Control")
    W("")
    W("```")
    W("\n".join(control_lines))
    W("CONTROL " + ("PASS" if control_ok else "FAIL"))
    W("```")
    W("")
    W("## Regenerating")
    W("")
    W("```")
    W("python tools/re/vtable_override_audit.py            # rewrite progress/VTABLE_OVERRIDE_AUDIT.*")
    W("python tools/re/vtable_override_audit.py --control  # exit 1 if a known case is lost")
    W("python tools/re/vtable_override_audit.py --table 0x820D0500")
    W("```")
    with open(out_md, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def render_subsystems(W, sub):
    groups = defaultdict(list)
    for r in sub:
        groups[r["subsystem"]].append(r)
    W("| subsystem | rows | insns |")
    W("|---|---:|---:|")
    ordered = sorted(groups.items(), key=lambda kv: -sum(r["ninstr"] for r in kv[1]))
    for k, v in ordered:
        W("| %s | %d | %d |" % (k, len(v), sum(r["ninstr"] for r in v)))
    W("")
    for k, v in ordered:
        rows = sorted(v, key=lambda r: -r["ninstr"])
        W("### %s (%d)" % (k, len(v)))
        W("")
        W("\n".join(md_table(rows[:40])))
        if len(rows) > 40:
            W("")
            W("...and %d smaller rows, in the JSON." % (len(rows) - 40))
        W("")


VERDICT_HELP = [
    ("true", "the console override has no equivalent in our tree: behaviour is lost"),
    ("equivalent", "the override exists on console and not here, but inheriting changes nothing"),
    ("platform", "a PC backend replaces this on purpose, so there is nothing to port as such"),
    ("false", "the audit is wrong: renamed, absorbed elsewhere, or the slot was mapped wrongly"),
]


def render_verification(W, rows, verdicts):
    by = {r["name"]: r for r in rows}
    if not verdicts:
        W("Not done yet.")
        return
    sets = defaultdict(list)
    for name, v in verdicts.items():
        sets[v.get("set", "sample")].append((name, v))
    W("Each row below was read by hand: the table slot, the console body, our class and its base, "
      "and `tools/re/hasbody.py`. Verdicts:")
    W("")
    for k, why in VERDICT_HELP:
        W("* `%s`: %s." % (k, why))
    W("")
    W("`sample_*` rows were drawn at random with a fixed seed, before any verdict on them, from the "
      "game-code rows of one class. **Only they measure the error rate.** `sample_missing` is the "
      "MISSING class. `sample_icf` is the folded class as it stood before bodies of 2 instructions "
      "or fewer were split off: most of its false rows moved to ICF_TRIVIAL_OVERRIDE, so it "
      "describes that older, wider class. `sample_dwarf` is the DWARF pass (8 drawn, one dropped "
      "when the row turned out to duplicate a MISSING row). `read` rows were picked because they "
      "looked important or suspicious, so their rate means nothing; the false positives found "
      "there are the ones to remember. A first sample, before the `const override` scanner fix, is "
      "not counted: it exposed that bug and was redrawn.")
    W("")
    W("| set | checked | true | equivalent | platform | false | true rate |")
    W("|---|---:|---:|---:|---:|---:|---:|")
    for s, items in sorted(sets.items()):
        c = Counter(v["verdict"] for _, v in items)
        W("| %s | %d | %d | %d | %d | %d | %.0f%% |" % (
            s, len(items), c["true"], c["equivalent"], c["platform"], c["false"],
            100.0 * c["true"] / max(1, len(items))))
    W("")
    W("| set | method | addr | insns | verdict | evidence |")
    W("|---|---|---|---:|---|---|")
    for s, items in sorted(sets.items()):
        for name, v in items:
            r = by.get(name)
            W("| %s | `%s` | `%s` | %s | %s | %s |" % (
                s, name, r["addr"] if r else "?", r["ninstr"] if r else "?",
                v["verdict"] if r else v["verdict"] + " (no longer reported)", v.get("note", "")))


def render_top(W, rows, verdicts):
    by = {r["name"]: r for r in rows}
    top = [(n, v) for n, v in verdicts.items() if v.get("verdict") == "true" and "rank" in v]
    if not top:
        W("Not selected yet.")
        return
    W("| # | method | addr | insns | falls back on | what is lost |")
    W("|---:|---|---|---:|---|---|")
    for n, v in sorted(top, key=lambda kv: kv[1]["rank"]):
        r = by.get(n)
        if not r:
            W("| %d | `%s` | | | | **Fixed since, no longer reported.** %s |" % (v["rank"], n, v.get("lost", "")))
            continue
        W("| %d | `%s` | `%s` | %d | %s | %s |" % (
            v["rank"], n, r["addr"], r["ninstr"],
            ("`%s`" % r["fallback"]) if r.get("fallback") else "", v.get("lost", v.get("note", ""))))


def print_table(addr, tables, g, hy_rows):
    t = tables.get(addr)
    if not t:
        print("no table at 0x%08X" % addr)
        return 1
    print("table 0x%08X owner=%s (%s) parent=%s (%s) stores=%d"
          % (addr, t.owner, t.owner_why, "0x%08X" % t.parent if t.parent else None, t.parent_why, len(t.stores)))
    by = {r["addr"]: r for r in hy_rows}
    p = tables.get(t.parent) if t.parent else None
    for i, s in enumerate(t.slots):
        same = "=" if p is not None and i < len(p.slots) and p.slots[i] == s else " "
        r = by.get("0x%08X" % s)
        print("  %2d +0x%02X %s 0x%08X %5d  %-62s %s" % (
            i, i * 4, same, s, g[s]["i"] if s in g else 0, (g[s]["n"] if s in g else "<no export>"),
            r["cls"] if r else ""))
    return 0


def main(argv):
    def opt(flag):
        return argv[argv.index(flag) + 1] if flag in argv else None
    src, image, rebuild = opt("--src"), opt("--image"), "--rebuild-cache" in argv
    if "--control" in argv:
        return control(src, image, rebuild)
    rows, counts, st, tables, g, tree = audit(src, image, rebuild)
    if "--table" in argv:
        return print_table(int(opt("--table"), 16), tables, g, rows)
    ok, lines = evaluate_control(rows, tree, tables, g)
    print("\n".join(lines))
    print("CONTROL", "PASS" if ok else "FAIL")
    rev = subprocess.run(["git", "-C", os.path.join(REPO, "b5-decomp"), "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    md = os.path.join(REPO, "progress", "VTABLE_OVERRIDE_AUDIT.md")
    js = os.path.join(REPO, "progress", "VTABLE_OVERRIDE_AUDIT.json")
    emit(rows, counts, st, rev, lines, ok, md, js)
    print("by class:", dict(sorted(Counter(r["cls"] for r in rows).items())))
    print("counters:", dict(sorted(counts.items())))
    print("stats:", st)
    print("wrote", os.path.relpath(md, REPO), "+", os.path.relpath(js, REPO))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
