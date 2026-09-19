#!/usr/bin/env python3
"""
asmaudit.py -- INSTRUCTION-SHAPE AUDIT: the exe we BUILT against the console's MACHINE CODE.
==============================================================================================

WHY. funcaudit.py compares what the console's pseudocode NAMES with what our source names.
It cannot see a constant the compiler folded, a branch a macro added, a callee the optimiser
inlined, or a body whose source reads right and compiles to something else. JeBobs's proposal
(Discord, 2026-09-19): measure instruction accuracy against ARTIST for functions that are
identical. Byte-matching is impossible here -- the tree is x64-widened and built by MSVC for a
different ISA -- so this tool measures the next best thing the two binaries share: the SHAPE of
each function. For every paired function it extracts an architecture-neutral fingerprint from
both sides and scores their agreement:

    calls   the multiset of named direct callees (CRT/assert/logging helpers dropped)
    cond    how many conditional branches, and how many go backwards (loops)
    ind     how many indirect calls (virtual dispatch, function pointers)
    imm     the set of small integer immediates (li / cmp*i / mulli / andi on the console;
            cmp / test / mov / and / or / xor / imul / add / sub immediates on x64) and the
            float constants each side loads (flt_/dbl_ symbols resolved from the image via
            x360rd.py on the console; rip-relative scalar SSE loads on x64)
    n mem fp vec   instruction / load-store / float / vector counts (information only)

    score = 0.45*calls + 0.35*cond + 0.2*imm over the components that exist (ind is shown, not scored)
    tier  A >= 80 "same shape"   B >= 55 "close"   C < 55 "diverges"
          T trivial (nothing to score, or a console body of <= 8 instructions)
          X the ledger names the function but the exe we built has no symbol for it

WHAT IT CANNOT SAY. A tier A function is "the same calls, branch count and constants", not a
match: argument order, field offsets and arithmetic between the constants are invisible. A
tier C function is NOT necessarily wrong: inlining decisions differ per compiler, and a callee
MSVC inlined shows here as a missing call. Read the DIFF (which callees / constants exist on
one side only) before calling it a defect; `--func NAME` prints it, `--asm` adds both streams.
The exact tier -- compile a portable function with the X360 SDK and diff instruction streams
decomp.me-style -- is tools/re/asmmatch.py.

PAIRING. progress/identity.json: canonical name -> X360 addresses (+ primary_file). The PC
symbol is the map's public whose demangled name-only form equals the canonical name (templates
and spaces stripped). Overloads: every console/PC pair is scored and the best pairing kept, with
`ambiguous: N` in the notes. ICF-folded symbols (several names, one address) are scored and
noted. Static (file-local) functions are not in a MSVC map: the callee of a `call` into one is
"unnamed" on the PC side, exactly like `bl sub_82xxxxxx` on the console, and neither side's
unnamed calls are scored. A function's PC code ends at the first `int3` after its symbol (MSVC
pads functions with 0xCC), never at the next public, so an intervening static does not bleed in.

MODES.
  --pack              read the ARTIST IDA exports once -> progress/asmaudit_artist.json.gz
                      (fingerprint + parameter count per export, ~2 MB). Needs the exports and,
                      for float constants, the ARTIST image (x360rd.py). Re-run when they change.
  (default)           audit: --exe build/game/Burnout_PC.exe --map build/game/Burnout_PC.map
                      + the pack + identity.json -> progress/asmaudit.json (+ .md unless --no-md)
  --func NAME         one function: both fingerprints, the diff, the score (--asm: both streams)
  --tu FILE           only the functions identity files under that source file (audit spelling)
  --meta k=v          stamp the JSON header (exe_commit, b5_commit, toolchain ...)

CI. The exe only exists after a build, so this runs in build-and-publish.yml (daily / on
demand), not per commit; the result is committed as progress/asmaudit.json and the work server
imports it as the "instruction accuracy" tier of the evidence layer. Windows only for the map
demangler (dbghelp); a pure-Python fallback covers the plain `?name@scope@@` shapes elsewhere.
Needs `pip install capstone pefile`.
==============================================================================================
"""
import argparse
import collections
import gzip
import io
import json
import os
import posixpath
import re
import struct
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IDENTITY = os.path.join(REPO, "progress", "identity.json")
EXPORTS = os.environ.get("BP_IDA_EXPORTS") or os.path.join(REPO, ".ida-exports", "BURNOUT_X360_ARTIST.XEX")
EXE = os.path.join(REPO, "build", "game", "Burnout_PC.exe")
MAP = os.path.join(REPO, "build", "game", "Burnout_PC.map")
PACK = os.path.join(REPO, "progress", "asmaudit_artist.json.gz")
OUT = os.path.join(REPO, "progress", "asmaudit")

# ind is reported, not scored: Xenon emits bctrl for import/TOC calls as well as virtual ones,
# so the count says more about the toolchain than about the body.
WEIGHTS = {"calls": 0.45, "cond": 0.35, "imm": 0.2}
TIER_A, TIER_B = 80.0, 55.0
TRIVIAL_N = 8
IMM_LIMIT = 0x10000
DIFF_LIMIT = 6

# callees that say nothing about the body: prologue/epilogue helpers, asserts, logging, libc,
# intrinsics, CRT plumbing on either side. Mirrors funcaudit.CALLEE_SKIP plus the x64 CRT.
SKIP = re.compile(
    r"^(?:__?save(?:gpr|fpr|vmx)|__?rest(?:gpr|fpr|vmx)|_savegprlr|_restgprlr|_savevmx|_restvmx"
    r"|CgsDev::Assert::|CgsDev::StrStream|CgsDev::Log::|CgsDev::Message::|CgsContainers::BasePriorityQueue::Clear"
    r"|memset|memcpy|memmove|memcmp|strlen|strcmp|strncpy|strstr|_stricmp|sprintf|_snprintf|vsprintf|sqrt|sqrtf"
    r"|sinf|cosf|tanf|atan2f|acosf|asinf|fabs|floorf|ceilf|fmodf|powf|expf|logf|rand|abs|_fltused"
    r"|XM[A-Z]|_cntlzw|__cntlzw|_rotl|_rotr|__rlwinm|Cgs(?:Dev::)?ID(?:Un)?Compress|CgsIDCompress|CgsIDUnCompress"
    r"|`|operator|nullsub_|_purecall|__purecall|RtlUnwind|_C_specific_handler|__C_specific_handler|\?"
    r"|__security_check_cookie|__security_init_cookie|__chkstk|__GSHandlerCheck|__CxxFrameHandler|_CxxThrowException"
    r"|__std_|__acrt_|__vcrt_|__scrt_|_invalid_parameter|__report_|_RTC_|__local_stdio|__stdio_common|atexit"
    r"|__dyn_tls|_guard_|__imp_|_alloca_probe|__ArrayUnwind|__ehvec|__InternalCxxFrameHandler"
    r"|DebugBreak|__debugbreak|IsDebuggerPresent|_Init_thread|getenv|v?snprintf|_v?snprintf|printf"
    r"|CgsDev::SimpleStrStream|CgsDev::DebugUI::|CgsDev::PerfMon|rw::core::debug::|XMem|CgsCore::S[Nn]?Printf"
    r"|Attrib::AssertOnClassCheck|savegprlr|restgprlr|savefpr|restfpr|savevmx|restvmx"
    r"|Rtl[A-Z]|Nt[A-Z]|Ke[A-Z]|Xam[A-Z]|Xex[A-Z]|Xapi|XGet|XSet|_errno|Burnout_X360|EnterCriticalSection|LeaveCriticalSection)"
)
TEMPLATE_RE = re.compile(r"<[^<>]*>")


def skip_callee(name):
    """True for helpers that say nothing about the body (either side, raw or normalised)."""
    return bool(SKIP.match(name)) or "::operator" in name or name.startswith("operator")


# ------------------------------------------------------------------ name normalisation
def strip_templates(name):
    prev = None
    while prev != name:
        prev, name = name, TEMPLATE_RE.sub("", name)
    return name


def norm_name(name):
    """Canonical comparable form for a qualified name from either side."""
    name = name.strip()
    name = re.sub(r"::`?scalar[ _]deleting[ _]destructor'?_*$", "::`sdd'", name)
    name = re.sub(r"::`?vector[ _]deleting[ _]destructor'?_*$", "::`vdd'", name)
    name = re.sub(r"\s+", "", strip_templates(name))
    name = name.replace("(void)", "()")
    return name


def console_callee(raw):
    """IDA symbol in a `bl` operand -> qualified name, "" for a helper to skip, or None for an
    unnamed target.

    IDA spells `A::B<65536,16>::~C<T>` as `A__B_65536_16____C_T`: `::` -> `__`, and every
    template/dtor character -> `_`. Undone component-wise: numeric template args are
    stripped, a component that repeats the previous one behind an extra `_` is a destructor,
    and a `_Upper` inside a component starts a type template argument, which ends the name.
    """
    raw = re.split(r"\s*[#;]", raw)[0].strip()
    if raw.startswith("j_"):
        raw = raw[2:]
    if not raw or raw.startswith(("sub_", "nullsub_", "loc_", "unk_", "off_")):
        return None
    if skip_callee(raw.lstrip("_")) or skip_callee(raw):
        return ""
    comps = []
    for i, comp in enumerate(raw.split("__")):
        if not comp:
            continue
        dtor = False
        if comps and comp.startswith("_"):
            comp = comp.lstrip("_")
            dtor = comp == comps[-1]
        comp = re.sub(r"(?:_\d+)+$", "", comp)              # <65536,16>
        comp = re.sub(r"_(?:u?int|float|double|bool|u?char|u?short|u?long|unsigned|signed|void"
                      r"|[us](?:8|16|32|64)|f32|f64|size_t)(?:_\w*)?$", "", comp)   # Array<int>
        m = re.match(r"^([A-Za-z]\w*?)_[A-Z]", comp)         # AddEvent<CgsSound::...>
        if m and comps:
            comps.append(("~" if dtor else "") + m.group(1))
            break
        comps.append(("~" if dtor else "") + comp)
    name = "::".join(c for c in comps if c)
    name = norm_name(name)
    return "" if skip_callee(name) else name


# ------------------------------------------------------------------ console fingerprints
PPC_LINE = re.compile(r"^0x([0-9A-Fa-f]+)\s+(\S+)\s*(.*)$")
PPC_IMM_MN = {"li", "cmpwi", "cmplwi", "cmpdi", "cmpldi", "mulli", "andi.", "andis.", "subfic"}
PPC_MEM_RE = re.compile(r"^(?:l(?:bz|hz|ha|wz|wa|d|fs|fd|vx|vlx|vrx|vsl|vsr|vewx|vehx|vebx|wbrx|hbrx|dbrx|swi|mw)"
                        r"|st(?:b|h|w|d|fs|fd|vx|vlx|vrx|vewx|vehx|vebx|wbrx|hbrx|dbrx|swi|mw))(?:128)?(?:u|x|ux)?$")
PPC_UNCOND = {"b", "ba", "blr", "bctr", "bl", "bla", "bctrl"}
LOC_RE = re.compile(r"loc_([0-9A-Fa-f]+)")
FLT_RE = re.compile(r"\b(flt|dbl)_([0-9A-Fa-f]{8})\b")

_x360rd = None


def _load_x360rd():
    global _x360rd
    if _x360rd is not None:
        return _x360rd or None
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import x360rd  # noqa: E402
        x360rd.f32(0x82000000)
        _x360rd = x360rd
    except BaseException:  # SystemExit at import when the image is absent
        _x360rd = False
    return _x360rd or None


def parse_int(tok):
    tok = tok.strip().rstrip("h")
    neg = tok.startswith("-")
    if neg:
        tok = tok[1:]
    try:
        if tok.lower().startswith("0x"):
            v = int(tok, 16)
        elif tok.isdigit():
            v = int(tok, 10)
        elif re.fullmatch(r"[0-9A-Fa-f]+", tok) and any(c in "ABCDEFabcdef" for c in tok):
            v = int(tok, 16)
        else:
            return None
    except ValueError:
        return None
    return -v if neg else v


def round_float(v):
    if v != v or v in (float("inf"), float("-inf")) or abs(v) > 1e30 or (v != 0 and abs(v) < 1e-30):
        return None
    return float("%.7g" % v)


VEC_SYM_RE = re.compile(r"\b(?:unk|xmmword|flt|dbl|dword|off|stru)_([0-9A-Fa-f]{8})@l\b")


def vector_floats(raw16, big_endian):
    """The plausible float lanes of a 16-byte constant (masks, NaNs and zeros dropped)."""
    out = set()
    fmt = ">4f" if big_endian else "<4f"
    for v in struct.unpack(fmt, raw16):
        v = round_float(v)
        if v is not None and v != 0 and 1e-6 <= abs(v) <= 1e6:
            out.add(v)
    return out


def ppc_fingerprint(asm, want_floats=True):
    fp = {"n": 0, "calls": [], "unnamed": 0, "ind": 0, "cond": 0, "back": 0, "imm": set(), "flt": set(),
          "mem": 0, "fp": 0, "vec": 0}
    rd = _load_x360rd() if want_floats else None
    parsed = []
    for line in asm.splitlines():
        m = PPC_LINE.match(line)
        if m:
            parsed.append((int(m.group(1), 16), m.group(2), re.split(r"\s*[#;]", m.group(3))[0].strip()))
    for i, (addr, mn, ops) in enumerate(parsed):
        fp["n"] += 1
        nxt = parsed[i + 1] if i + 1 < len(parsed) else None
        if rd is not None and mn in ("addi", "la") and "@l" in ops:
            t = VEC_SYM_RE.search(ops)
            if t:
                try:
                    fp["flt"].update(vector_floats(rd.rd(int(t.group(1), 16), 16), True))
                except Exception:
                    pass
        base = mn.rstrip("+-")
        if base in ("bl", "bla"):
            name = console_callee(ops)
            if name is None:
                fp["unnamed"] += 1
            elif name:
                fp["calls"].append(name)
            continue
        if base == "bctrl":
            fp["ind"] += 1
            continue
        if base.startswith("b") and base not in ("bctr", "blr", "b", "ba"):
            # bne/beq/blt/bgt/ble/bge/bdnz/bdz/bso/bns/bnl/bng/bun/bnu/bc..., incl. *lr forms
            fp["cond"] += 1
            t = LOC_RE.search(ops)
            if t and int(t.group(1), 16) < addr:
                fp["back"] += 1
            continue
        if base in ("b", "ba"):
            t = LOC_RE.search(ops)
            if t and int(t.group(1), 16) < addr:
                fp["back"] += 1
            continue
        # `li r0, N` = save/restore area offsets; `li rX, N` right before a load/store that
        # indexes with rX = address arithmetic (lvx v0, r11, r10), not a value the body uses
        feeds_load = (mn == "li" and nxt is not None and PPC_MEM_RE.match(nxt[1]) is not None
                      and re.search(r"\b%s\b" % re.escape(ops.split(",")[0].strip()), nxt[2]) is not None)
        if mn in PPC_IMM_MN and not ops.startswith("r0,") and not feeds_load:
            v = parse_int(ops.split(",")[-1]) if "," in ops else None
            if v is not None and -IMM_LIMIT < v < IMM_LIMIT and v not in (0, 1):
                fp["imm"].add(v)
        if PPC_MEM_RE.match(mn):
            fp["mem"] += 1
            if rd is not None and mn in ("lfs", "lfd"):
                t = FLT_RE.search(ops)
                if t:
                    try:
                        ea = int(t.group(2), 16)
                        v = rd.f32(ea) if t.group(1) == "flt" else struct.unpack(">d", rd.rd(ea, 8))[0]
                        v = round_float(v)
                        if v is not None:
                            fp["flt"].add(v)
                    except Exception:
                        pass
        if mn.startswith("f"):
            fp["fp"] += 1
        elif mn.startswith("v") or mn.startswith(("lvx", "stvx", "lvlx", "lvrx", "stvlx", "stvrx")):
            fp["vec"] += 1
    return fp


def proto_nparams(proto):
    """Parameter count of an IDA prototype, counting `this` (IDA lists it as a1)."""
    if not proto or "(" not in proto:
        return None
    inner = proto[proto.find("(") + 1: proto.rfind(")")]
    inner = inner.strip()
    if not inner or inner == "void":
        return 0
    depth, n = 0, 1
    for ch in inner:
        if ch in "(<[":
            depth += 1
        elif ch in ")>]":
            depth -= 1
        elif ch == "," and depth == 0:
            n += 1
    return n


def finalize(fp):
    fp["calls"] = sorted(fp["calls"], key=lambda c: c if isinstance(c, str) else c[0])
    fp["imm"] = sorted(fp["imm"])
    fp["flt"] = sorted(fp["flt"])
    return fp


def resolve_folds(pfp, console_calls):
    """PC callees whose address is ICF-folded carry every name at that address; keep the one
    the console also calls, else the first. Returns a copy with plain string callees."""
    out = dict(pfp)
    want = collections.Counter(console_calls)
    calls = []
    for c in pfp["calls"]:
        if isinstance(c, str):
            calls.append(c)
            continue
        pick = next((n for n in c if want[n] > 0), c[0])
        if want[pick] > 0:
            want[pick] -= 1
        calls.append(pick)
    out["calls"] = sorted(calls)
    return out


def align_truncated(console_calls, pc_calls):
    """IDA truncates long symbol names; a console callee that is a strict prefix (>= 6 chars)
    of exactly one PC callee is taken to be that callee."""
    pc_only = sorted(set(pc_calls) - set(console_calls))
    out = []
    for c in console_calls:
        if c in pc_calls or len(c) < 6:
            out.append(c)
            continue
        hits = [p for p in pc_only if p.startswith(c)]
        if hits:
            out.append(hits[0])          # unique, or the first of several truncation victims
        elif "::" not in c and len(c) < 12:
            continue                     # an unscoped stump like `BrnDirec`: IDA cut it, drop it
        else:
            out.append(c)
    return sorted(out)


def pack_exports(exports_dir, out_path):
    names = sorted(f for f in os.listdir(exports_dir) if f.endswith(".json"))
    print(f"packing {len(names)} exports from {exports_dir} ...")
    floats = _load_x360rd() is not None
    if not floats:
        print("  (ARTIST image not readable: float constants will be missing from the console side)")
    pack = {}
    t0 = time.time()
    for i, fn in enumerate(names):
        try:
            with io.open(os.path.join(exports_dir, fn), "r", encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        addr = d.get("address") or fn[:-5]
        fp = finalize(ppc_fingerprint(d.get("assembly") or "", want_floats=floats))
        fp["np"] = proto_nparams(d.get("prototype"))
        fp["name"] = d.get("name")
        pack[addr] = fp
        if (i + 1) % 5000 == 0:
            print(f"  {i + 1}/{len(names)} ({time.time() - t0:.0f}s)")
    meta = {"tool": "asmaudit --pack", "exports": len(pack), "floats": floats,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with gzip.open(out_path, "wt", encoding="utf-8") as fh:
        json.dump({"meta": meta, "functions": pack}, fh, separators=(",", ":"), sort_keys=True)
    print(f"wrote {out_path} ({os.path.getsize(out_path) / 1e6:.1f} MB, {len(pack)} functions, {time.time() - t0:.0f}s)")


def load_pack(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------ PC side: map + exe
_undname = None


def demangle(sym, name_only=True):
    """MSVC decorated name -> readable, via dbghelp on Windows, a small fallback elsewhere."""
    global _undname
    if not sym.startswith("?"):
        return sym
    if _undname is None:
        try:
            import ctypes
            dll = ctypes.windll.dbghelp  # type: ignore[attr-defined]
            buf = ctypes.create_string_buffer(8192)

            def _u(s, flags):
                n = dll.UnDecorateSymbolName(s.encode(), buf, 8192, flags)
                return buf.value.decode(errors="replace") if n else None
            _undname = _u
        except Exception:
            _undname = False
    if _undname:
        out = _undname(sym, 0x1000 if name_only else 0)
        if out:
            return out
    return _fallback_demangle(sym)


def _fallback_demangle(sym):
    m = re.match(r"^\?(\?[0-9_A-Z]|\$?[A-Za-z_][\w$]*)@((?:\$?[A-Za-z_][\w$]*@)*)@", sym)
    if not m:
        return None
    leaf, scopes = m.group(1), [s for s in m.group(2).split("@") if s]
    scopes = [re.sub(r"^\$", "", s) for s in scopes]
    cls = scopes[0] if scopes else ""
    special = {"?0": cls, "?1": "~" + cls, "?_G": "`scalar deleting destructor'",
               "?_E": "`vector deleting destructor'", "?_7": "`vftable'"}
    if leaf.startswith("?"):
        leaf = special.get(leaf, "operator?")
    return "::".join(reversed(scopes) + [leaf]) if scopes else leaf


def load_map(path):
    """[(va, decorated, name_only)] for every public function in the code section, sorted."""
    syms = []
    in_pub = False
    with io.open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "Publics by Value" in line:
                in_pub = True
                continue
            if not in_pub:
                continue
            m = re.match(r"\s+0001:([0-9a-f]{8})\s+(\S+)\s+([0-9a-f]{16})\s+(f)?", line)
            if m and m.group(4):
                syms.append((int(m.group(3), 16), m.group(2)))
    syms.sort()
    return syms


def load_exe(path):
    import pefile
    pe = pefile.PE(path, fast_load=True)
    return pe.OPTIONAL_HEADER.ImageBase, pe.get_memory_mapped_image()


class PcCode(object):
    """Disassembly + fingerprints for the built exe, symbol lookup through the linker map."""

    def __init__(self, exe, map_path):
        import capstone
        self.cs = capstone
        self.base, self.image = load_exe(exe)
        self.syms = load_map(map_path)
        self.va_of = {}
        self.by_va = collections.defaultdict(list)
        self.by_norm = collections.defaultdict(list)
        for va, dec in self.syms:
            self.by_va[va].append(dec)
            nm = demangle(dec, True)
            if nm:
                self.by_norm[norm_name(nm)].append((va, dec))
        self.vas = sorted(self.by_va)
        self.md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
        self.md.detail = True
        self._fp = {}
        self._insns = {}

    def symbol_at(self, va):
        decs = self.by_va.get(va)
        if decs:
            return demangle(decs[0], True)
        return None

    def names_at(self, va):
        """Every normalised, non-helper name at a code address (several when ICF folded);
        [] when the address has no public symbol, None when only helpers live there."""
        decs = self.by_va.get(va)
        if not decs:
            return []
        names = []
        for dec in decs:
            nm = demangle(dec, True)
            if not nm:
                continue
            nm = norm_name(nm)
            if not skip_callee(nm) and nm not in names:
                names.append(nm)
        return names or None

    def bounds(self, va):
        import bisect
        i = bisect.bisect_right(self.vas, va)
        end = self.vas[i] if i < len(self.vas) else va + 0x10000
        return va, end

    def insns(self, va):
        if va in self._insns:
            return self._insns[va]
        start, end = self.bounds(va)
        code = bytes(self.image[start - self.base: end - self.base])
        out = []
        for ins in self.md.disasm(code, start):
            if ins.mnemonic == "int3":
                break
            out.append(ins)
        self._insns[va] = out
        return out

    def is_import_thunk(self, va):
        try:
            code = bytes(self.image[va - self.base: va - self.base + 6])
        except Exception:
            return False
        return code[:2] == b"\xff\x25"

    def fingerprint(self, va):
        if va in self._fp:
            return self._fp[va]
        x86 = self.cs.x86
        fp = {"n": 0, "calls": [], "unnamed": 0, "ind": 0, "cond": 0, "back": 0, "imm": set(), "flt": set(),
              "mem": 0, "fp": 0, "vec": 0}
        ins_list = self.insns(va)
        start = va
        end = ins_list[-1].address + ins_list[-1].size if ins_list else va
        for ins in ins_list:
            fp["n"] += 1
            mn = ins.mnemonic
            ops = ins.operands
            if mn == "call" or (mn == "jmp" and ops and ops[0].type == x86.X86_OP_IMM
                                and not (start <= ops[0].imm < end)):
                if ops and ops[0].type == x86.X86_OP_IMM:
                    tgt = ops[0].imm
                    if self.is_import_thunk(tgt):
                        continue
                    names = self.names_at(tgt)
                    if names is None:
                        continue                       # only helpers live there
                    if not names:
                        fp["unnamed"] += 1             # a static: not in the map
                    else:
                        fp["calls"].append(names[0] if len(names) == 1 else names)
                elif ops and ops[0].type == x86.X86_OP_MEM and ops[0].mem.base == x86.X86_REG_RIP:
                    continue  # import through the IAT
                else:
                    fp["ind"] += 1
                continue
            if mn == "jmp":
                if ops and ops[0].type == x86.X86_OP_IMM and ops[0].imm < ins.address:
                    fp["back"] += 1
                continue
            if mn.startswith("j") or mn.startswith("loop"):
                fp["cond"] += 1
                if ops and ops[0].type == x86.X86_OP_IMM and ops[0].imm < ins.address:
                    fp["back"] += 1
                continue
            if mn in ("cmp", "test", "and", "or", "xor", "mov", "movabs", "imul", "add", "sub"):
                if not (mn in ("add", "sub") and ops and ops[0].type == x86.X86_OP_REG
                        and ops[0].reg in (x86.X86_REG_RSP, x86.X86_REG_RBP, x86.X86_REG_ESP)):
                    for o in ops:
                        if o.type == x86.X86_OP_IMM and -IMM_LIMIT < o.imm < IMM_LIMIT and o.imm not in (0, 1):
                            fp["imm"].add(int(o.imm))
            has_mem = any(o.type == x86.X86_OP_MEM for o in ops)
            if has_mem and mn not in ("lea", "nop"):
                fp["mem"] += 1
            if mn[-2:] in ("ss", "sd", "ps", "pd") and mn[:3] in ("add", "sub", "mul", "div", "sqr", "min", "max",
                                                                 "cvt", "com", "uco", "rsq", "rcp", "rou", "and",
                                                                 "xor", "orp", "mov", "sha", "shu", "unp"):
                if mn[:3] != "mov" or not has_mem:
                    fp["fp"] += 1
                if mn[-2:] in ("ss", "sd") and has_mem and mn[:3] in ("mov", "add", "sub", "mul", "div", "com", "uco", "min", "max", "cvt"):
                    for o in ops:
                        if o.type == x86.X86_OP_MEM and o.mem.base == x86.X86_REG_RIP:
                            ea = ins.address + ins.size + o.mem.disp
                            try:
                                off = ea - self.base
                                if mn[-2:] == "ss":
                                    v = struct.unpack("<f", bytes(self.image[off: off + 4]))[0]
                                else:
                                    v = struct.unpack("<d", bytes(self.image[off: off + 8]))[0]
                                v = round_float(v)
                                if v is not None:
                                    fp["flt"].add(v)
                            except Exception:
                                pass
                if mn[-2:] in ("ps", "pd"):
                    fp["vec"] += 1
                    if has_mem:
                        for o in ops:
                            if o.type == x86.X86_OP_MEM and o.mem.base == x86.X86_REG_RIP:
                                ea = ins.address + ins.size + o.mem.disp
                                try:
                                    off = ea - self.base
                                    fp["flt"].update(vector_floats(bytes(self.image[off: off + 16]), False))
                                except Exception:
                                    pass
        self._fp[va] = finalize(fp)
        return self._fp[va]


# ------------------------------------------------------------------ scoring
def jaccard_multiset(a, b):
    ca, cb = collections.Counter(a), collections.Counter(b)
    keys = set(ca) | set(cb)
    if not keys:
        return None
    inter = sum(min(ca[k], cb[k]) for k in keys)
    union = sum(max(ca[k], cb[k]) for k in keys)
    return inter / float(union)


def ratio_sim(a, b):
    if not a and not b:
        return None
    return 1.0 - abs(a - b) / float(max(a, b))


def recall_precision(console, pc):
    """(recall, precision) of the console multiset in the PC multiset; None when both empty."""
    cc, cp = collections.Counter(console), collections.Counter(pc)
    if not cc and not cp:
        return None, None
    inter = sum(min(cc[k], cp[k]) for k in cc if k in cp)
    recall = inter / float(sum(cc.values())) if cc else 1.0
    precision = inter / float(sum(cp.values())) if cp else 1.0
    return recall, precision


def score(cfp, pfp):
    """Missing console callees and constants are what a defect looks like; extra PC callees are
    more often a helper the console's compiler inlined, so calls weigh recall 3:1 over precision
    and constants count recall only."""
    r, p = recall_precision(cfp["calls"], pfp["calls"])
    ri, _ = recall_precision([("i", v) for v in cfp["imm"]] + [("f", v) for v in cfp["flt"]],
                             [("i", v) for v in pfp["imm"]] + [("f", v) for v in pfp["flt"]])
    comps = {
        "calls": None if r is None else 0.75 * r + 0.25 * p,
        "cond": ratio_sim(cfp["cond"], pfp["cond"]),
        "imm": ri,
        "ind": ratio_sim(cfp["ind"], pfp["ind"]),
    }
    have = {k: v for k, v in comps.items() if v is not None and k in WEIGHTS}
    if not have:
        return None, comps
    tot = sum(WEIGHTS[k] for k in have)
    return round(100.0 * sum(WEIGHTS[k] * v for k, v in have.items()) / tot, 1), comps


def tier_of(s, cfp):
    if s is None or cfp["n"] <= TRIVIAL_N:
        return "T"
    if s >= TIER_A:
        return "A"
    if s >= TIER_B:
        return "B"
    return "C"


def multiset_diff(a, b):
    ca, cb = collections.Counter(a), collections.Counter(b)
    only_a = sorted((ca - cb).elements())
    only_b = sorted((cb - ca).elements())
    return only_a, only_b


def diff_block(cfp, pfp):
    co, po = multiset_diff(cfp["calls"], pfp["calls"])
    ic = sorted(set(cfp["imm"]) - set(pfp["imm"]))
    ip = sorted(set(pfp["imm"]) - set(cfp["imm"]))
    fc = sorted(set(cfp["flt"]) - set(pfp["flt"]))
    fpc = sorted(set(pfp["flt"]) - set(cfp["flt"]))
    return {
        "calls_only_console": co[:DIFF_LIMIT], "calls_only_pc": po[:DIFF_LIMIT],
        "calls_only_console_n": len(co), "calls_only_pc_n": len(po),
        "imm_only_console": (ic + fc)[:DIFF_LIMIT], "imm_only_pc": (ip + fpc)[:DIFF_LIMIT],
    }


def counts_block(cfp, pfp, full=False):
    keys = ("n", "cond", "back", "ind", "unnamed", "mem", "fp", "vec") if full else ("n", "cond", "ind")
    out = {k: [cfp[k], pfp[k]] for k in keys}
    out["calls"] = [len(cfp["calls"]), len(pfp["calls"])]
    out["imm"] = [len(cfp["imm"]) + len(cfp["flt"]), len(pfp["imm"]) + len(pfp["flt"])]
    return out


# ------------------------------------------------------------------ pairing + audit
def audit_file(primary_file):
    if not primary_file:
        return None
    p = posixpath.normpath(primary_file.replace("\\", "/"))
    if re.match(r"^(?:[A-Za-z]:|/)", p):
        return None   # a DWARF decl_file (altivec.h under a build box's temp): not a tree file
    return p


def prepare(cfp, pfp_raw):
    """Both fingerprints made comparable: PC fold groups resolved against the console's
    callees, the console's truncated names aligned to the PC's full ones."""
    pfp = resolve_folds(pfp_raw, cfp["calls"])
    cfp2 = dict(cfp)
    cfp2["calls"] = align_truncated(cfp["calls"], pfp["calls"])
    return cfp2, pfp


def pair_and_score(name, entry, pack, pc):
    """One result row for an identity entry, or None when the console side has no export."""
    addrs = [a for a in (entry.get("x360_addrs") or []) if a in pack["functions"]]
    if not addrs:
        return None
    file = audit_file(entry.get("primary_file"))
    cands = pc.by_norm.get(norm_name(name), [])
    row = {"name": name, "addr": addrs[0], "file": file}
    if not cands:
        row.update({"tier": "X", "score": None, "pc_symbol": None, "console_n": pack["functions"][addrs[0]]["n"]})
        return row
    # distinct PC addresses (ICF folds several decorated names onto one)
    seen = {}
    for va, dec in cands:
        seen.setdefault(va, dec)
    pairs = []
    for a in addrs:
        for va, dec in seen.items():
            cfp, pfp = prepare(pack["functions"][a], pc.fingerprint(va))
            s, comps = score(cfp, pfp)
            pairs.append((-1.0 if s is None else s, a, va, dec, cfp, pfp, s, comps))
    pairs.sort(key=lambda p: (-p[0], p[1], p[2]))
    _, a, va, dec, cfp, pfp, s, comps = pairs[0]
    notes = []
    if len(addrs) > 1 or len(seen) > 1:
        notes.append(f"ambiguous: {len(addrs)} console x {len(seen)} PC overloads, best pair kept")
    if len(pc.by_va.get(va, [])) > 1:
        notes.append(f"folded: {len(pc.by_va[va]) - 1} other symbol(s) share this PC address")
    row.update({
        "addr": a, "pc_va": "0x%X" % va,
        "tier": tier_of(s, cfp), "score": s,
        "components": {k: (None if v is None else round(v, 2)) for k, v in comps.items()},
        "counts": counts_block(cfp, pfp), "diff": diff_block(cfp, pfp), "notes": notes,
    })
    return row


def run_audit(args):
    t0 = time.time()
    pack = load_pack(args.pack)
    with io.open(IDENTITY, "r", encoding="utf-8") as fh:
        ident = json.load(fh)
    pc = PcCode(args.exe, args.map)
    print(f"map: {len(pc.syms)} public functions, {len(pc.by_norm)} distinct names; pack: {len(pack['functions'])} console functions")
    # identity has no primary_file for ~4k functions (class TUs, headers); the ledger's
    # tu_index files every function somewhere, so fall back to it for the per-file rollups.
    tu_file_of = {}
    try:
        with io.open(os.path.join(REPO, "progress", "tu_index.json"), "r", encoding="utf-8") as fh:
            for tu_path, row in json.load(fh).items():
                f = audit_file(tu_path)
                if f:
                    for fn in row.get("functions") or []:
                        tu_file_of.setdefault(fn, f)
    except (OSError, ValueError):
        pass
    for name, entry in ident.items():
        if not audit_file(entry.get("primary_file")) and name in tu_file_of:
            entry["primary_file"] = tu_file_of[name]
    tu = args.tu.replace("\\", "/") if args.tu else None
    results = []
    no_export = 0
    not_in_exe = 0
    for name in sorted(ident):
        entry = ident[name]
        if tu:
            f = audit_file(entry.get("primary_file")) or ""
            if f != tu and not f.endswith("/" + tu) and tu not in f:
                continue
        row = pair_and_score(name, entry, pack, pc)
        if row is None:
            no_export += 1
            continue
        if row["tier"] == "X" and not args.tu:
            not_in_exe += 1          # counted, not listed: 17k rows the server derives itself
            continue
        results.append(row)
    results.sort(key=lambda r: (r["file"] or "~", r["name"]))
    tiers = collections.Counter(r["tier"] for r in results)
    tiers["X"] += not_in_exe
    scoreable = tiers["A"] + tiers["B"] + tiers["C"]
    scores = [r["score"] for r in results if r["score"] is not None and r["tier"] in "ABC"]
    stats = {
        "identity": len(ident), "no_export": no_export, "paired_in_exe": len(results) - (tiers["X"] - not_in_exe),
        "not_in_exe": tiers["X"], "A": tiers["A"], "B": tiers["B"], "C": tiers["C"], "T": tiers["T"],
        "scoreable": scoreable,
        "shape_percent": round(100.0 * tiers["A"] / scoreable, 1) if scoreable else 0.0,
        "mean_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
        "files": len({r["file"] for r in results if r["file"]}),
    }
    meta = {"tool": "asmaudit", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "exe": os.path.basename(args.exe), "exe_mtime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.path.getmtime(args.exe))),
            "pack_generated_at": (pack.get("meta") or {}).get("generated_at"),
            "weights": WEIGHTS, "tier_a": TIER_A, "tier_b": TIER_B}
    for kv in args.meta or []:
        k, _, v = kv.partition("=")
        meta[k] = v
    # a local run stamps the commits itself; CI passes them explicitly (--meta wins)
    import subprocess
    for key, cwd in (("b5_commit", os.path.join(REPO, "b5-decomp")), ("exe_commit", REPO)):
        if not meta.get(key):
            try:
                meta[key] = subprocess.run(["git", "-C", cwd, "rev-parse", "HEAD"], capture_output=True,
                                           text=True, check=False, timeout=20).stdout.strip() or None
            except (OSError, subprocess.SubprocessError):
                meta[key] = None
    out = {"meta": meta, "stats": stats, "results": results}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with io.open(args.out + ".json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, separators=(",", ":"), sort_keys=True)
    if not args.no_md:
        with io.open(args.out + ".md", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(markdown(out))
    print(f"asmaudit: {stats}  ({time.time() - t0:.0f}s) -> {args.out}.json")


def markdown(out):
    s = out["stats"]
    L = ["# Instruction-shape audit: built exe vs ARTIST", "",
         f"generated {out['meta']['generated_at']} from {out['meta']['exe']} (built {out['meta']['exe_mtime']})", "",
         f"- identity names: {s['identity']}; with a console export: {s['identity'] - s['no_export']}",
         f"- in the exe: {s['paired_in_exe']}  |  named but not in the exe: {s['not_in_exe']}",
         f"- A same shape: {s['A']}  B close: {s['B']}  C diverges: {s['C']}  T trivial: {s['T']}  "
         f"-> {s['shape_percent']}% of scoreable functions are tier A (mean score {s['mean_score']})", "",
         "## Largest divergences (tier C, by console size)", ""]
    worst = sorted((r for r in out["results"] if r["tier"] == "C"), key=lambda r: -r["counts"]["n"][0])[:40]
    for r in worst:
        d = r["diff"]
        L.append(f"- **{r['name']}** @{r['addr']} ({r['file']}) score {r['score']} -- console {r['counts']['n'][0]} insns / "
                 f"pc {r['counts']['n'][1]}; cond {r['counts']['cond'][0]} vs {r['counts']['cond'][1]}; "
                 f"calls only console: {', '.join(d['calls_only_console'][:5]) or '-'}; only pc: {', '.join(d['calls_only_pc'][:5]) or '-'}")
    L += ["", "## Per file (worst 40 by tier-C count)", "", "| file | in exe | A | B | C | T | not in exe |", "|---|---|---|---|---|---|---|"]
    per = collections.defaultdict(collections.Counter)
    for r in out["results"]:
        per[r["file"] or "(no file)"][r["tier"]] += 1
    for f, c in sorted(per.items(), key=lambda kv: -kv[1]["C"])[:40]:
        L.append(f"| {f} | {c['A'] + c['B'] + c['C'] + c['T']} | {c['A']} | {c['B']} | {c['C']} | {c['T']} | {c['X']} |")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ one function
def show_func(args):
    pack = load_pack(args.pack)
    with io.open(IDENTITY, "r", encoding="utf-8") as fh:
        ident = json.load(fh)
    name = args.func
    entry = ident.get(name)
    if entry is None:
        hits = [k for k in ident if k.endswith("::" + name) or k == name or name in k]
        if len(hits) == 1:
            name, entry = hits[0], ident[hits[0]]
        else:
            sys.exit(f"{name}: not in identity.json" + (f"; candidates: {hits[:10]}" if hits else ""))
    pc = PcCode(args.exe, args.map)
    row = pair_and_score(name, entry, pack, pc)
    if row is None:
        sys.exit(f"{name}: no console export in the pack")
    print(f"{name}  X360 {row['addr']}  file {row['file']}")
    if row["tier"] == "X":
        print("  tier X: the exe we built has no public symbol with this name (not linked, inlined everywhere, or not written)")
        return
    va = int(row["pc_va"], 16)
    print(f"  PC {row['pc_va']}  {demangle(pc.by_va[va][0], False)}")
    print(f"  tier {row['tier']}  score {row['score']}  components {row['components']}")
    for n in row["notes"]:
        print(f"  note: {n}")
    cfp, pfp = prepare(pack["functions"][row["addr"]], pc.fingerprint(va))
    c = counts_block(cfp, pfp, full=True)
    print("  counts (console, pc): " + "  ".join(f"{k}={v[0]}/{v[1]}" for k, v in c.items()))
    d = row["diff"]
    print(f"  callees only on the console ({d['calls_only_console_n']}): {', '.join(d['calls_only_console']) or '-'}")
    print(f"  callees only in our exe     ({d['calls_only_pc_n']}): {', '.join(d['calls_only_pc']) or '-'}")
    print(f"  constants only on the console: {d['imm_only_console'] or '-'}")
    print(f"  constants only in our exe    : {d['imm_only_pc'] or '-'}")
    print(f"  console calls: {', '.join(cfp['calls']) or '-'}")
    print(f"  pc calls     : {', '.join(pfp['calls']) or '-'}")
    print(f"  console imm {cfp['imm']} flt {cfp['flt']}")
    print(f"  pc imm      {pfp['imm']} flt {pfp['flt']}")
    if args.asm:
        ex = os.path.join(EXPORTS, row["addr"] + ".json")
        print("\n=== console (ARTIST) ===")
        try:
            with io.open(ex, "r", encoding="utf-8") as fh:
                print(json.load(fh).get("assembly") or "(no assembly in export)")
        except OSError:
            print(f"(export {ex} not on this box)")
        print("\n=== ours (x64) ===")
        for ins in pc.insns(int(row["pc_va"], 16)):
            print("0x%X  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))


def main():
    ap = argparse.ArgumentParser(description="instruction-shape audit: built exe vs the console's machine code")
    ap.add_argument("--pack", default=PACK, help="packed console fingerprints (default progress/asmaudit_artist.json.gz)")
    ap.add_argument("--pack-exports", action="store_true", help="build the pack from the IDA exports, then exit")
    ap.add_argument("--exports", default=EXPORTS)
    ap.add_argument("--exe", default=EXE)
    ap.add_argument("--map", default=MAP)
    ap.add_argument("--out", default=OUT, help="output stem (default progress/asmaudit)")
    ap.add_argument("--tu", help="only functions identity files under this source file")
    ap.add_argument("--func", help="print one function's fingerprints, diff and score")
    ap.add_argument("--asm", action="store_true", help="with --func: print both instruction streams")
    ap.add_argument("--meta", action="append", help="k=v stamped into the JSON header")
    ap.add_argument("--no-md", action="store_true")
    args = ap.parse_args()
    if args.pack_exports:
        pack_exports(args.exports, args.pack)
        return
    if not os.path.exists(args.pack):
        sys.exit(f"pack {args.pack} not found: run `asmaudit.py --pack-exports` on a box with the IDA exports")
    for p in (args.exe, args.map):
        if not os.path.exists(p):
            sys.exit(f"{p} not found: build the exe first (build.cmd exe)")
    if args.func:
        show_func(args)
    else:
        run_audit(args)


if __name__ == "__main__":
    main()
