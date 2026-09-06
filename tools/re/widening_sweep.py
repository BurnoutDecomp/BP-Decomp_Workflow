#!/usr/bin/env python3
"""widening_sweep.py -- X64-WIDENING GHOSTS: a CONSOLE byte offset or CONSOLE element
stride applied to a WIDENED HOST object.

=========================== WHY THIS EXISTS ===========================================
Every other defect class in this tree has a tool.  Vtable dispatch has vdispatch_sweep;
wrong id fields have idfield_sweep; constants have constaudit; struct widths have the
static_assert pins.  The widening ghost -- the class that has bitten this project at
least four separate times -- had none, and was found one at a time, by accident, usually
by an access violation.

  * PhysicalWheel::Update            read a frozen bit at CONSOLE +0x9C
  * DogmaAllocator                   shifted slots `>> 2` (a CONSOLE pointer size)
  * DeformableObject                 read `*(this + 6476)` for the attached vehicle
  * SendGlassUpdateEvents            wrote `lpOutEM + 15920` for the glass queue
  * UpdateGlassSmashedState  x2      `this + 15120 + 32*i`, `this + 19232 + 48*i`
  * OutputState, GetWheelTagPoints   the same two seats again -- SILENTLY

The 2026-09-06 glass wave found SIX reads across FOUR functions at once, in a file where
a SIBLING had already been fixed TWELVE LINES AWAY by an earlier wave.  That is the proof
that one-at-a-time does not work here.

⭐⭐ THE DANGEROUS HALF IS SILENT.  Two of those six only ever read `element + 0`, so they
never dereferenced garbage and never faulted -- they PUBLISHED WRONG NUMBERS on every
frame of every run for the entire life of the build.  A ghost that crashes gets fixed in
an afternoon.  A ghost that does not crash is invisible to the compile gate, to the
parity fingerprint, to the faithfulness lint and to the human eye.  [[diagnostics-that-lie]]

=========================== WHAT A GHOST ACTUALLY LOOKS LIKE ===========================
⚠️ IT IS ALMOST NEVER A BARE LITERAL.  A `grep 'this + 15120'` finds NOTHING in the file
that carried four of the six.  What it carried was:

    static const u32 KU_TAG_POINT_ARRAY_OFFSET = 15120;  // &maTagPoints[0]  (stride 32)
    static const u32 KU_TAG_POINT_STRIDE       = 32;     // sizeof(TagPoint)
    ...
    const char* lpcThis    = reinterpret_cast<const char*>(this);          <-- BYTE VIEW
    const char* lpcElement = lpcThis + KU_TAG_POINT_ARRAY_OFFSET           <-- CONSOLE SEAT
                                     + KU_TAG_POINT_STRIDE * li16PointIndex;  <-- CONSOLE STRIDE
    const char* lpcSpec    = *reinterpret_cast<const char* const*>(lpcElement + 16);
                                                                           <-- and it is a PTR

i.e. a NAMED CONSTANT, a BYTE-POINTER ALIAS of `this`, and arithmetic that reads perfectly
well and is wrong by kilobytes.  Measured, live, on that object:

        host tagSeat 16832 stride 48        drivenSeat 22992 stride 64
     console      15120        32                    19232        48

so the seats were out by 1,712 and 3,760 bytes and the strides by 50% and 33% -- because
mLocatorData, mImpulsePasser, mVehicleBody and maDeformationSensors[20] all sit in front
of the tables and all contain POINTERS, which are 4 bytes on the console and 8 on the host.
[[literal-scans-miss-real-stores]]

⇒ THIS TOOL TRACKS THE ALIAS AND THE CONSTANT, not the literal.

=========================== HOW IT DECIDES ============================================
Per function body it builds three sets and intersects them:

  (1) BYTE VIEWS   a variable of a 1-byte pointer type (char*/u8*/uintptr_t) bound to an
                   OBJECT expression -- `this` above all, else a typed pointer.  Inline
                   casts `(u8*)X + N` and `reinterpret_cast<const char*>(X) + N` count too.
  (2) OFFSETS      a numeric literal, OR a named constant whose definition this tool
                   already read out of the same TU (`static const u32 KU_* = N;`,
                   `constexpr`, `enum { ... }`).  The constant's own trailing comment is
                   carried along as evidence, because in this tree it usually SAYS
                   "console".
  (3) STRIDES      the `* index` half of `base + SEAT + STRIDE * i`.

A hit is a byte view combined with an offset.  It is then classified:

  BASE RESOLUTION
    this      -> the enclosing `Class::Method` names the class exactly.  DECIDABLE.
    local     -> the declared type of the alias source, when it is in scope.
    unknown   -> reported separately; a human reads it.

  SERIALISED EXEMPTION (AGENTS.md allows raw offsets here, and they are CORRECT here)
    A streamed/on-disc record has no host pointers to widen, so the console number IS the
    host number.  Recognised by the base's name/type vocabulary (Spec, Resource, Blob,
    Payload, Stream, Bundle, Record, Data, lpRaw...) or by an explicit inline allowance
    marker on or above the line (FLAG, serialised, on-disc, file format, REFERENCE-ONLY).

  SEVERITY -- the field the prompt cares about most
    FATAL   the result is dereferenced AS A POINTER (`*reinterpret_cast<T* const*>(e+N)`,
            `*(T**)(e+N)`).  A wrong seat here faults, so a run finds it.
    SILENT  the result is only read as DATA (`*reinterpret_cast<const Vector3*>(e)`), or
            written through.  It never faults.  It has been wrong since the day it landed.
            THESE ARE THE PRIORITY.

  CONSOLE CORROBORATION (optional, --asm)
    Pair the enclosing function with its X360 original via progress/identity.json ->
    .ida-exports/BURNOUT_X360_ARTIST.XEX/0x<addr>.json and ask whether the offset appears
    in that function's assembly as a displacement/immediate.  When it does, our C++ is
    provably carrying the CONSOLE's own number rather than a host offsetof.  That is the
    difference between "a raw offset" and "an x64-widening ghost".

=========================== CAVEATS, STATED SO THE COUNT IS NOT OVER-READ =============
  * This tool NARROWS.  It does not decide.  Every hit still has to be read against the
    header (is the member homed?) and, for the seat value, against a live probe or an
    offsetof.  The one thing it decides on its own is the SHAPE.
  * A ghost whose console number was already SIMPLIFIED AWAY -- someone wrote the arithmetic
    with a host-computed constant -- is invisible to every tool including this one, because
    it agrees with itself.  Only a live probe or offsetof can see that.  Stated plainly:
    THIS SWEEP CANNOT SEE A GHOST THAT IS SPELLED AS A CORRECT-LOOKING NUMBER.
  * Comments and string literals are blanked before scanning, so the many asm-provenance
    banners in this tree (`// *(this+0x30) = 0;`) do not inflate the count.  Verified: the
    naive line grep returns 7,929 hits, 98% of them comments.
  * `>> 2` / `<< 2` on a POINTER or pointer difference is the DogmaAllocator shape and is
    reported under --shifts; it is noisy (bit twiddling uses it constantly), so it is off
    by default and is a lead list, not a finding list.

=========================== USAGE =====================================================
    python tools/re/widening_sweep.py                    # the physics/vehicle/world lane
    python tools/re/widening_sweep.py --all-roots        # the whole reconstructed tree
    python tools/re/widening_sweep.py --asm              # + X360 console corroboration
    python tools/re/widening_sweep.py --severity silent  # only the ones that never fault
    python tools/re/widening_sweep.py --shifts           # + the `>> 2` slot-shift leads
    python tools/re/widening_sweep.py --root src/... --verbose
    python tools/re/widening_sweep.py --self-test        # prove it on the known ghosts
"""
import argparse
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SUBMODULE = os.path.join(REPO, "b5-decomp")
IDENTITY = os.path.join(REPO, "progress", "identity.json")
EXPORTS = os.path.join(REPO, ".ida-exports", "BURNOUT_X360_ARTIST.XEX")

DEFAULT_ROOTS = [
    "src/GameSource/Physics",
    "src/GameSource/World",
    "src/SharedClasses/Physics",
    "src/SharedClasses/Traffic",
    "src/GameShared/GameClasses/SceneManager",
]

SOURCE_EXT = (".cpp", ".h", ".hpp", ".inl", ".c", ".cc")

# ---------------------------------------------------------------------------------------
# Lexical scrub.  Comments carry the asm provenance banners this tree is full of; scanning
# them would drown the signal (7,929 raw hits vs 13 real ones).  Keep line numbers intact.
# ---------------------------------------------------------------------------------------


def strip_comments(text):
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, min(j, n)):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        elif c in "\"'":
            q = c
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == q:
                    j += 1
                    break
                if text[j] == "\n":
                    break
                j += 1
            for k in range(i, min(j, n)):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


# ---------------------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------------------

# 1-byte-granular pointer/integer types.  Adding N to one of these advances N BYTES, which
# is what makes a console offset expressible at all.
BYTE_TYPES = r"(?:const\s+)?(?:unsigned\s+char|signed\s+char|char|u8|s8|uint8_t|int8_t|BYTE|uintptr_t|intptr_t|size_t)"

# A byte-pointer alias bound to something:   const char* lpcThis = reinterpret_cast<...>(this);
ALIAS_RE = re.compile(
    r"\b(?:const\s+)?(?:unsigned\s+char|signed\s+char|char|u8|s8|uint8_t|int8_t|BYTE)\s*\*+\s*(?:const\s+)?"
    r"([A-Za-z_]\w*)\s*=\s*([^;]+);", re.S)

# uintptr_t lAddr = reinterpret_cast<uintptr_t>(x);
UINTPTR_ALIAS_RE = re.compile(
    r"\b(?:const\s+)?(?:uintptr_t|intptr_t|size_t)\s+(?:const\s+)?([A-Za-z_]\w*)\s*=\s*"
    r"(reinterpret_cast\s*<[^>]*>\s*\([^;]*?\)|\([^;]*?\)[^;]*?);", re.S)

# A named byte-offset constant defined in the TU.
CONST_RE = re.compile(
    r"^[ \t]*(?:static\s+)?(?:const|constexpr)\s+(?:u8|u16|u32|u64|s32|int|unsigned|size_t|ptrdiff_t|uintptr_t)"
    r"\s+([A-Za-z_]\w*)\s*=\s*(0x[0-9A-Fa-f]+|\d+)\s*[uU]?[lL]{0,2}\s*;(.*)$", re.M)

ENUM_CONST_RE = re.compile(
    r"^[ \t]*([A-Z][A-Z0-9_]{3,})\s*=\s*(0x[0-9A-Fa-f]+|\d+)\s*[uU]?[lL]{0,2}\s*,(.*)$", re.M)

# The definition line of a method body, e.g. `void DeformableObject::OutputState(...)`.
DEF_RE = re.compile(
    r"^[ \t]*(?:[A-Za-z_][\w:<>,\*&\s]*?[\s\*&])?"
    r"([A-Za-z_]\w*)::([~A-Za-z_]\w*)\s*\(")

# Inline byte cast immediately followed by arithmetic:
#   (u8*)this + 100      reinterpret_cast<const char*>(x) + N
INLINE_CAST_RE = re.compile(
    r"(?:reinterpret_cast\s*<\s*" + BYTE_TYPES + r"\s*\*+\s*>\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)"
    r"|\(\s*" + BYTE_TYPES + r"\s*\*+\s*\)\s*\(?\s*([A-Za-z_][\w\.\->:\[\]]*)\s*\)?)"
    r"\s*\+\s*([A-Za-z_]\w*|0x[0-9A-Fa-f]+|\d+)")

# `expr + TERM` where TERM is a literal or an identifier, used after a known byte view.
TERM = r"(?:0x[0-9A-Fa-f]+|\d+|[A-Za-z_]\w*)"

# A dereference of the computed address AS A POINTER -> a wrong seat FAULTS.
PTR_DEREF_RE = re.compile(
    r"\*\s*(?:reinterpret_cast\s*<[^>]*\*\s*(?:const\s*)?\*\s*>|\(\s*[\w:]+\s*\*\s*\*\s*\))")

# Vocabulary that marks a base as EXTERNAL SERIALISED DATA -- console offsets are correct
# there (a streamed record has no host pointers to widen) and AGENTS.md explicitly allows
# raw offsets on it.
#
# ⚠️ THIS LIST IS DELIBERATELY NARROW, AND THE VALIDATION RUN IS WHY.  The first version
# also carried `index|table|data|raw|entry|header|buffer`, and those words are so common in
# ordinary C++ that the exemption swallowed FOUR REAL GHOSTS in the ground-truth file: the
# `lpcElement + mpSpec` chain of UpdateGlassSmashedState was exempted because the word
# "Index" appeared in `li16PointIndex` further along the same declaration.  An exemption
# heuristic that silently eats real findings is the [[diagnostics-that-lie]] shape and is
# worse than no heuristic at all.  Two hard rules now bound it:
#   (1) it is matched against the base's NAME ONLY, never the whole declaration expression;
#   (2) it can NEVER fire on something that transitively roots at `this` (see root_of).
SERIALISED_WORDS = re.compile(
    r"(?i)(spec|resource|blob|payload|bundle|ondisc|disc|dds|apt|attrib|"
    r"streamed|filedata|rawdata|wireform)")

# An explicit inline allowance the author wrote.
ALLOWANCE = re.compile(
    r"(?i)(FLAG PC-platform leaf|serialised|serialized|on-disc|on disc|file[- ]format|"
    r"REFERENCE[- ]ONLY|external data|byte stream|streamed record|wire format)")

SHIFT_RE = re.compile(r"([A-Za-z_][\w\.\->:\[\]]*)\s*(>>|<<)\s*2\b")

# ---------------------------------------------------------------------------------------
# THE PIN INDEX -- what turns this sweep from advisory into decisive.
#
# ⭐⭐ Not every console offset on a live object is a ghost.  Some console layouts REPRODUCE
# exactly on x64, and this tree already knows which: it pins them with `static_assert`.
# Three of the first candidates this sweep raised were all refuted that way --
#   * mfSpeedMPH @0x6C0 / mDeformableAABB @0x6D0 / mbCrashing @0x710 / sizeof 0x720:
#     "MEASURED on this tree's x64 build ... every one IDENTICAL to the console literal",
#     pinned in VehiclePhysics_layout_check.cpp::_AssertOwnBlockLayout;
#   * ExternallySimulatedBody's whole base chain: pointer-free, "the console offsets
#     reproduce EXACTLY on x64 -- asserted in ExternallySimulatedBody_embed_check.cpp";
#   * sizeof(AICar) == 0x1560, pinned in BrnAICar.h with a banner naming this exact hazard.
# The SimpleVehiclePhysics banner even records the cost of getting this wrong the other way:
#   "⛔ Do not re-derive this by reasoning -- it was measured with offsetof, and the previous
#    reasoning-only claim sent this wave hunting a widening ghost that does not exist."
#
# ⇒ A pin is EVIDENCE, so the sweep reads the pins and reports them beside each hit.  It does
#   not silently drop a hit: a pin on the same NUMBER is shown and named, and the reader
#   decides whether it pins THIS base.  (Matching is by value, so an unrelated class pinning
#   the same integer will show up -- which is why the pin is printed, never just counted.)
#
# ⚠️ THE RHS IS OFTEN A NAMED CONSTANT, NOT A LITERAL, and the first version of this index
# only matched literals -- so it MISSED the very pin that refuted this sweep's first
# candidate: VehiclePhysics_layout_check.cpp writes
#     static_assert(offsetof(VehiclePhysics, mfSpeedMPH) == X360LayoutCheck::KU_A_SPEEDMPH,
# That is [[literal-scans-miss-real-stores]] a second time, in the tool built to catch it.
# The RHS is therefore resolved through the same constant table the hit side uses.
PIN_OFFSETOF_RE = re.compile(
    r"static_assert\s*\(\s*offsetof\s*\(\s*([\w:]+)\s*,\s*([\w\.\[\]]+)\s*\)\s*"
    r"(?:==|!=|>=|<=)\s*([\w:]+(?:\s*\+\s*\d+)?)")
PIN_SIZEOF_RE = re.compile(
    r"static_assert\s*\(\s*sizeof\s*\(\s*([\w:]+)\s*\)\s*(?:==)\s*([\w:]+(?:\s*\+\s*\d+)?)")
# `static_assert(KU_A_SPEEDMPH == 0x6C0u, ...)` -- the layout checks build their offsets as a
# CHAIN of symbolic additions (KU_A_SPEEDMPH = KU_A_WHEELPLANE + 0x10) and then anchor the
# chain to the asm literal with a value assert like this.  Harvesting it is what lets the
# offsetof pin on the next line resolve to a number.
PIN_VALUE_RE = re.compile(
    r"static_assert\s*\(\s*([A-Za-z_]\w*)\s*==\s*(0x[0-9A-Fa-f]+|\d+)\s*[uU]?[lL]{0,2}\s*,")


# ---------------------------------------------------------------------------------------
# Console corroboration
# ---------------------------------------------------------------------------------------


def build_pin_index(files):
    """value -> [ 'sizeof(AICar)==5472 @file', 'offsetof(VehiclePhysics,mfSpeedMPH)==1728 @file' ]

    Read from the WHOLE tree regardless of the sweep's roots: a pin usually lives in a
    *_layout_check.cpp / *_embed_check.cpp beside the header, not beside the use site.
    """
    pins = {}
    # Two passes: constants first (a pin's RHS may name a constant defined in another file,
    # e.g. the X360LayoutCheck namespace), then the asserts themselves.
    consts = {}
    texts = {}
    for path in files:
        try:
            raw = open(path, "r", encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if "static_assert" not in raw and "const" not in raw:
            continue
        code = strip_comments(raw)
        texts[path] = code
        for name, (val, _c) in collect_constants(code, raw).items():
            consts.setdefault(name, val)
        # value anchors win over any literal definition -- they ARE the measurement
        for m in PIN_VALUE_RE.finditer(code):
            try:
                consts[m.group(1)] = int(m.group(2), 0)
            except ValueError:
                pass

    def resolve(expr):
        expr = expr.strip()
        m = re.match(r"^([\w:]+)\s*(?:\+\s*(\d+))?$", expr)
        if not m:
            return None
        head, extra = m.group(1), int(m.group(2) or 0)
        try:
            return int(head, 0) + extra
        except ValueError:
            pass
        leaf = head.split("::")[-1]
        if leaf in consts:
            return consts[leaf] + extra
        return None

    for path, code in texts.items():
        if "static_assert" not in code:
            continue
        rel = os.path.basename(path)
        for m in PIN_OFFSETOF_RE.finditer(code):
            v = resolve(m.group(3))
            if v is None:
                continue
            pins.setdefault(v, []).append(
                "offsetof(%s,%s)==%d @%s" % (m.group(1), m.group(2), v, rel))
        for m in PIN_SIZEOF_RE.finditer(code):
            v = resolve(m.group(2))
            if v is None:
                continue
            pins.setdefault(v, []).append("sizeof(%s)==%d @%s" % (m.group(1), v, rel))
    return pins


def load_identity():
    try:
        with open(IDENTITY, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except OSError:
        return {}


def addr_of(identity, qualified):
    row = identity.get(qualified)
    if isinstance(row, dict):
        addrs = row.get("x360_addrs")
        if isinstance(addrs, list) and addrs:
            return addrs[0]
    return None


_ASM_CACHE = {}


def asm_of(addr):
    if addr in _ASM_CACHE:
        return _ASM_CACHE[addr]
    path = os.path.join(EXPORTS, "%s.json" % addr)
    text = None
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = json.load(fh).get("assembly", "")
        except (OSError, ValueError):
            text = None
    _ASM_CACHE[addr] = text
    return text


def console_has(asm, value):
    """Does the console asm carry `value` as a displacement or an immediate?"""
    if not asm:
        return False
    pats = [
        r"[,\s]%d\s*\(" % value,          # lwz r3, 15120(r11)
        r"[,\s]0x%X\b" % value,           # ..., 0x3B10
        r"[,\s]0x%x\b" % value,
        r"[,\s]-?%d\b" % value,           # addi r3, r11, 15120
    ]
    return any(re.search(p, asm) for p in pats)


# ---------------------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------------------


class Hit(object):
    def __init__(self, path, line, cls, method, base, base_kind, offsets,
                 stride, severity, snippet, evidence):
        self.path = path
        self.line = line
        self.cls = cls
        self.method = method
        self.base = base
        self.base_kind = base_kind        # "this" | "local" | "unknown"
        self.offsets = offsets            # [(name_or_literal, value)]
        self.stride = stride              # (name_or_literal, value) or None
        self.severity = severity          # "FATAL" | "SILENT"
        self.snippet = snippet
        self.evidence = evidence          # constant comments etc.
        self.console = None               # set by --asm
        self.exempt = None                # reason string when exempt
        self.via = None                   # the alias hop, when base != the chain root
        self.pins = []                    # static_asserts naming this hit's numbers


def collect_constants(code, raw):
    """name -> (value, comment).  The comment usually says 'console' in this tree."""
    consts = {}
    raw_lines = raw.splitlines()
    for rx in (CONST_RE, ENUM_CONST_RE):
        for m in rx.finditer(code):
            name, val = m.group(1), m.group(2)
            try:
                value = int(val, 0)
            except ValueError:
                continue
            ln = code.count("\n", 0, m.start())
            comment = ""
            if 0 <= ln < len(raw_lines):
                line = raw_lines[ln]
                pos = line.find("//")
                if pos >= 0:
                    comment = line[pos + 2:].strip()
            consts[name] = (value, comment)
    return consts


def split_functions(code, raw):
    """Yield (cls, method, start_line, end_line, body_code)."""
    lines = code.splitlines()
    marks = []
    for i, line in enumerate(lines):
        m = DEF_RE.match(line)
        if m:
            marks.append((i, m.group(1), m.group(2)))
    if not marks:
        yield (None, None, 0, len(lines), code)
        return
    if marks[0][0] > 0:
        yield (None, None, 0, marks[0][0], "\n".join(lines[: marks[0][0]]))
    for n, (start, cls, method) in enumerate(marks):
        end = marks[n + 1][0] if n + 1 < len(marks) else len(lines)
        yield (cls, method, start, end, "\n".join(lines[start:end]))


def resolve_alias(expr):
    """What object is this byte view a view OF?  Returns (name, kind)."""
    e = expr.strip()
    if re.search(r"\bthis\b", e):
        return ("this", "this")
    m = re.search(r"reinterpret_cast\s*<[^>]*>\s*\(\s*&?\s*([A-Za-z_][\w\.\->:]*)", e)
    if m:
        return (m.group(1), "local")
    m = re.search(r"\(\s*[\w:]+\s*\*+\s*\)\s*&?\s*([A-Za-z_][\w\.\->:]*)", e)
    if m:
        return (m.group(1), "local")
    m = re.search(r"^&?\s*([A-Za-z_][\w\.\->:]*)", e)
    if m:
        return (m.group(1), "local")
    return (e[:40], "unknown")


def root_of(base, views, depth=0):
    """Follow the alias chain to its ROOT object.

    `lpcSpec = *(...)(lpcElement + 16)`, `lpcElement = lpcThis + SEAT`, `lpcThis = (char*)this`
    is THREE aliases deep and every one of them is arithmetic on the same live object.  A
    sweep that only looks one hop up calls the inner two "some local" and lets the exemption
    heuristic reach them.  Resolving the chain is what makes "rooted at `this`" decidable --
    and `this` is the one base that is CERTAIN to be a widened host object.
    """
    seen = set()
    cur, kind = base, None
    while depth < 12 and cur in views and cur not in seen:
        seen.add(cur)
        cur, kind, _expr = views[cur]
        depth += 1
    return cur, ("this" if cur == "this" else (kind or "local"))


def is_serialised(base, root, snippet, raw_lines, line_no):
    """Console offsets on external serialised data are CORRECT and are allowed.

    A streamed on-disc record has no host pointers to widen, so its console offsets ARE its
    host offsets; AGENTS.md explicitly permits raw offset access there.  A live C++ object
    is the opposite case and is never exempt.
    """
    if root == "this":
        return None                     # a widened host object, always. Never exempt.
    ctx = " ".join(raw_lines[max(0, line_no - 4): line_no + 1])
    if ALLOWANCE.search(ctx):
        return "documented allowance"
    # name only -- never the declaration expression (see the banner on SERIALISED_WORDS)
    leaf = re.split(r"[\.\-\>:]+", root)[-1] or root
    if SERIALISED_WORDS.search(leaf):
        return "serialised-record base (%s)" % root
    return None


def scan_file(path, rel, want_shifts):
    try:
        raw = open(path, "r", encoding="utf-8", errors="replace").read()
    except OSError:
        return [], [], 0
    code = strip_comments(raw)
    raw_lines = raw.splitlines()
    consts = collect_constants(code, raw)

    hits = []
    shifts = []
    nfuncs = 0

    for cls, method, start, end, body in split_functions(code, raw):
        nfuncs += 1
        # --- byte views declared in this body -------------------------------------------
        views = {}
        for m in list(ALIAS_RE.finditer(body)) + list(UINTPTR_ALIAS_RE.finditer(body)):
            name, expr = m.group(1), m.group(2)
            base, kind = resolve_alias(expr)
            views[name] = (base, kind, expr)

        # --- arithmetic on a byte view ---------------------------------------------------
        for name, (base, kind, decl) in views.items():
            use_re = re.compile(
                r"\b" + re.escape(name) + r"\s*\+\s*(" + TERM + r")"
                r"((?:\s*\+\s*" + TERM + r"(?:\s*\*\s*" + TERM + r")?)*)")
            for m in use_re.finditer(body):
                terms = [m.group(1)] + re.findall(TERM, m.group(2) or "")
                offsets, stride, evidence = [], None, []
                for t in terms:
                    if re.match(r"^(0x[0-9A-Fa-f]+|\d+)$", t):
                        offsets.append((t, int(t, 0)))
                    elif t in consts:
                        val, comment = consts[t]
                        offsets.append((t, val))
                        if comment:
                            evidence.append("%s = %d  // %s" % (t, val, comment))
                if not offsets:
                    continue
                # a `* index` after a term marks that term as a STRIDE
                tail = m.group(2) or ""
                sm = re.search(r"(" + TERM + r")\s*\*\s*(" + TERM + r")", tail)
                if sm:
                    for cand in (sm.group(1), sm.group(2)):
                        if cand in consts:
                            stride = (cand, consts[cand][0])
                        elif re.match(r"^(0x[0-9A-Fa-f]+|\d+)$", cand):
                            stride = (cand, int(cand, 0))

                ln = start + body.count("\n", 0, m.start()) + 1
                snippet = raw_lines[ln - 1].strip() if 0 <= ln - 1 < len(raw_lines) else ""
                # severity: is the computed address dereferenced AS A POINTER?
                window = body[max(0, m.start() - 200): m.start() + 400]
                severity = "FATAL" if PTR_DEREF_RE.search(window) else "SILENT"
                root, rkind = root_of(name, views)
                h = Hit(rel, ln, cls, method, root, rkind, offsets, stride,
                        severity, snippet, evidence)
                h.via = name if name != root else None
                h.exempt = is_serialised(base, root, snippet, raw_lines, ln - 1)
                hits.append(h)

        # --- inline `(u8*)x + N` with no alias -------------------------------------------
        for m in INLINE_CAST_RE.finditer(body):
            src = m.group(1) or m.group(2) or ""
            term = m.group(3)
            if re.match(r"^(0x[0-9A-Fa-f]+|\d+)$", term):
                value = int(term, 0)
            elif term in consts:
                value = consts[term][0]
            else:
                continue
            if value == 0:
                continue
            base, kind = resolve_alias(src)
            root, rkind = root_of(base, views)
            ln = start + body.count("\n", 0, m.start()) + 1
            snippet = raw_lines[ln - 1].strip() if 0 <= ln - 1 < len(raw_lines) else ""
            window = body[max(0, m.start() - 200): m.start() + 400]
            severity = "FATAL" if PTR_DEREF_RE.search(window) else "SILENT"
            h = Hit(rel, ln, cls, method, root, rkind, [(term, value)], None,
                    severity, snippet, [])
            h.via = base if base != root else None
            h.exempt = is_serialised(base, root, snippet, raw_lines, ln - 1)
            hits.append(h)

        if want_shifts:
            for m in SHIFT_RE.finditer(body):
                name = m.group(1)
                if name in views or re.search(r"(?i)(ptr|addr|slot|offset|p[A-Z])", name):
                    ln = start + body.count("\n", 0, m.start()) + 1
                    shifts.append((rel, ln, cls, method,
                                   raw_lines[ln - 1].strip() if ln - 1 < len(raw_lines) else ""))

    return hits, shifts, nfuncs


# ---------------------------------------------------------------------------------------
# Self-test -- a verification you have not seen FAIL is not a verification.
# ---------------------------------------------------------------------------------------

SELF_TEST = r"""
namespace Deformation {
    static const u32 KU_TAG_POINT_ARRAY_OFFSET    = 15120;  // &maTagPoints[0]  (stride 32)
    static const u32 KU_TAG_POINT_STRIDE          = 32;     // sizeof(TagPoint)
    static const u32 KU_DRIVEN_POINT_ARRAY_OFFSET = 19232;  // &maDrivenPoints[0]
    static const u32 KU_DRIVEN_POINT_STRIDE       = 48;     // sizeof(IKDrivenPoint)
    static const u32 KU_TAG_POINT_SPEC_PTR        = 16;     // TagPoint::mpSpec

void DeformableObject::UpdateGlassSmashedState(f32 lfTimeStep)
{
    const char* lpcThis = reinterpret_cast<const char*>(this);
    const char* lpcElement = lpcThis + KU_TAG_POINT_ARRAY_OFFSET + KU_TAG_POINT_STRIDE * liIndex;
    lLive = *reinterpret_cast<const Vector3*>(lpcElement);
    const char* lpcSpec = *reinterpret_cast<const char* const*>(lpcElement + KU_TAG_POINT_SPEC_PTR);
    const char* lpcDriven = lpcThis + KU_DRIVEN_POINT_ARRAY_OFFSET + KU_DRIVEN_POINT_STRIDE * liIndex;
    const char* lpcCtl = *reinterpret_cast<const char* const*>(lpcDriven + 32);
}

void DeformableObject::GetWheelTagPoints(Vector3* lpOut) const
{
    const char* lpcThis = reinterpret_cast<const char*>(this);
    const char* lpcElement = lpcThis + KU_TAG_POINT_ARRAY_OFFSET + KU_TAG_POINT_STRIDE * liTagPointIndex;
    lpOut[i] = *reinterpret_cast<const Vector3*>(lpcElement);
}

void PhysicalWheel::Update(f32 lfDt)
{
    const bool lbFrozen = *((const u8*)this + 0x9C);
}
}
"""


def run_self_test():
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "widening_selftest.cpp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(SELF_TEST)
    hits, _shifts, _n = scan_file(tmp, "selftest.cpp", False)
    live = [h for h in hits if not h.exempt]
    print("SELF-TEST -- the tool run against the KNOWN ghosts it was built for")
    print("-" * 86)
    for h in live:
        print("  %-28s L%-4d %-7s base=%-6s offsets=%s%s"
              % ("%s::%s" % (h.cls, h.method), h.line, h.severity, h.base,
                 ",".join("%s(%d)" % (n, v) for n, v in h.offsets),
                 "  stride=%s(%d)" % h.stride if h.stride else ""))
    print("-" * 86)
    want = {
        ("UpdateGlassSmashedState", 15120),
        ("UpdateGlassSmashedState", 19232),
        ("GetWheelTagPoints", 15120),
        ("Update", 0x9C),
    }
    got = set()
    for h in live:
        for _n, v in h.offsets:
            got.add((h.method, v))
    missing = want - got
    silent = [h for h in live if h.severity == "SILENT"]
    print("expected ghost seats found : %d / %d" % (len(want) - len(missing), len(want)))
    if missing:
        print("MISSING                    : %s" % sorted(missing))
    print("classified SILENT          : %d  (GetWheelTagPoints must be one)" % len(silent))
    ok = not missing and any(h.method == "GetWheelTagPoints" for h in silent)
    print("RESULT: %s" % ("PASS" if ok else "FAIL"))
    try:
        os.remove(tmp)
    except OSError:
        pass
    return 0 if ok else 1


# ---------------------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", action="append", default=None,
                    help="source root under b5-decomp (repeatable)")
    ap.add_argument("--all-roots", action="store_true",
                    help="sweep the whole reconstructed tree (src/)")
    ap.add_argument("--asm", action="store_true",
                    help="corroborate each offset against the paired X360 assembly")
    ap.add_argument("--severity", choices=("all", "silent", "fatal"), default="all")
    ap.add_argument("--base", choices=("all", "this", "local"), default="all",
                    help="'this' = only hits whose alias chain roots at the enclosing "
                         "object. That is the DECIDABLE class: the class is named by the "
                         "definition line, so offsetof can arbitrate it without guessing "
                         "what the base points at.")
    ap.add_argument("--compact", action="store_true",
                    help="one line per hit (triage table)")
    ap.add_argument("--unpinned", action="store_true",
                    help="only hits where NO static_assert in the tree pins any of the "
                         "numbers used. This is the short list: a pinned number has already "
                         "been measured against the host, an unpinned one has not.")
    ap.add_argument("--shifts", action="store_true",
                    help="also list `>> 2` / `<< 2` pointer-slot shift leads (noisy)")
    ap.add_argument("--show-exempt", action="store_true",
                    help="list the serialised-data hits the sweep exempted")
    ap.add_argument("--min-offset", type=int, default=1,
                    help="ignore offsets below this (default 1)")
    ap.add_argument("--self-test", action="store_true",
                    help="run the tool against the known ghosts and assert it finds them")
    args = ap.parse_args()

    if args.self_test:
        return run_self_test()

    roots = args.root or (["src"] if args.all_roots else DEFAULT_ROOTS)

    files = []
    for root in roots:
        base = os.path.join(SUBMODULE, root.replace("/", os.sep))
        if not os.path.isdir(base):
            print("!! root not found: %s" % base, file=sys.stderr)
            continue
        for dp, dn, fn in os.walk(base):
            dn[:] = [d for d in dn if d not in (".git", "__pycache__")]
            for f in fn:
                if f.endswith(SOURCE_EXT):
                    files.append(os.path.join(dp, f))
    files.sort()

    all_hits, all_shifts, nfuncs = [], [], 0
    for path in files:
        rel = os.path.relpath(path, SUBMODULE).replace(os.sep, "/")
        h, s, n = scan_file(path, rel, args.shifts)
        all_hits.extend(h)
        all_shifts.extend(s)
        nfuncs += n

    # The pin index is built over the WHOLE tree, never just the swept roots: a layout pin
    # lives in a *_layout_check.cpp beside the header, not beside the use site.
    pin_files = []
    for dp, dn, fn in os.walk(os.path.join(SUBMODULE, "src")):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__")]
        for f in fn:
            if f.endswith(SOURCE_EXT):
                pin_files.append(os.path.join(dp, f))
    pins = build_pin_index(pin_files)
    for h in all_hits:
        for name, val in h.offsets:
            h.pins.extend(pins.get(val, [])[:2])
        if h.stride:
            h.pins.extend(pins.get(h.stride[1], [])[:2])

    exempt = [h for h in all_hits if h.exempt]
    live = [h for h in all_hits if not h.exempt]
    live = [h for h in live if max(v for _n, v in h.offsets) >= args.min_offset]
    if args.severity != "all":
        live = [h for h in live if h.severity == args.severity.upper()]
    if args.base != "all":
        live = [h for h in live if (h.base_kind == "this") == (args.base == "this")]
    if args.unpinned:
        live = [h for h in live if not h.pins]

    if args.asm:
        identity = load_identity()
        for h in live:
            if not h.cls:
                continue
            addr = None
            for prefix in ("", "BrnPhysics::", "BrnPhysics::Deformation::",
                           "Deformation::", "BrnPhysics::Vehicle::", "Vehicle::"):
                addr = addr_of(identity, "%s%s::%s" % (prefix, h.cls, h.method))
                if addr:
                    break
            if not addr:
                h.console = "unpaired"
                continue
            asm = asm_of(addr)
            if asm is None:
                h.console = "no-export"
                continue
            marks = []
            for name, val in h.offsets:
                if console_has(asm, val):
                    marks.append("%d" % val)
            if h.stride and console_has(asm, h.stride[1]):
                marks.append("stride %d" % h.stride[1])
            h.console = ("CONSOLE:" + ",".join(marks)) if marks else "not-in-asm"

    # ---------------------------------------------------------------- report
    print("=" * 94)
    print("X64-WIDENING GHOST SWEEP")
    print("=" * 94)
    print("roots                       : %s" % ", ".join(roots))
    print("files swept                 : %d" % len(files))
    print("function bodies swept       : %d" % nfuncs)
    print("byte-offset expressions     : %d" % len(all_hits))
    print("  exempt (serialised data)  : %d" % len(exempt))
    print("  LIVE OBJECT (candidates)  : %d" % len(live))
    print("    SILENT (never faults)   : %d" % len([h for h in live if h.severity == "SILENT"]))
    print("    FATAL  (would fault)    : %d" % len([h for h in live if h.severity == "FATAL"]))
    print("layout pins read (tree-wide): %d distinct values" % len(pins))
    print("  candidates WITH a pin     : %d  (the number is measured against the host)"
          % len([h for h in live if h.pins]))
    print("  candidates with NO pin    : %d  <-- the short list (--unpinned)"
          % len([h for h in live if not h.pins]))
    print("")

    order = {"SILENT": 0, "FATAL": 1}
    live.sort(key=lambda h: (order.get(h.severity, 2), h.path, h.line))

    if args.compact:
        print("%-6s %-58s %-34s %-12s %s"
              % ("SEV", "FILE:LINE", "FUNCTION", "BASE", "OFFSETS"))
        for h in live:
            print("%-6s %-58s %-34s %-12s %s%s"
                  % (h.severity,
                     ("%s:%d" % (h.path.replace("src/", ""), h.line))[-58:],
                     ("%s::%s" % (h.cls or "<file>", h.method or "<scope>"))[-34:],
                     h.base[-12:],
                     ",".join("%d" % v for _n, v in h.offsets),
                     ("  x%d" % h.stride[1]) if h.stride else ""))
        print("")
        print("shown: %d" % len(live))
        return 0

    for h in live:
        loc = "%s:%d" % (h.path, h.line)
        who = "%s::%s" % (h.cls or "<file>", h.method or "<scope>")
        offs = ", ".join("%s = %d" % (n, v) for n, v in h.offsets)
        print("[%s] %s" % (h.severity, loc))
        print("    in      : %s   base: %s (%s)%s"
              % (who, h.base, h.base_kind, ("  via %s" % h.via) if h.via else ""))
        print("    offsets : %s%s" % (offs,
                                      ("   stride: %s = %d" % h.stride) if h.stride else ""))
        if h.console:
            print("    console : %s" % h.console)
        if h.pins:
            for p in sorted(set(h.pins))[:3]:
                print("    PIN     : %s" % p[:110])
        else:
            print("    PIN     : none -- this number is not measured against the host anywhere")
        print("    code    : %s" % h.snippet[:120])
        for e in h.evidence[:4]:
            print("      evid  : %s" % e[:110])
        print("")

    if args.show_exempt:
        print("-" * 94)
        print("EXEMPT (external serialised data -- console offset IS the host offset):")
        for h in exempt:
            print("  %s:%d  %s::%s  base=%s  [%s]"
                  % (h.path, h.line, h.cls, h.method, h.base, h.exempt))
        print("")

    if args.shifts:
        print("-" * 94)
        print("POINTER-SLOT SHIFT LEADS (`>> 2` / `<< 2`) -- %d  [leads, not findings]"
              % len(all_shifts))
        for rel, ln, cls, method, snip in all_shifts:
            print("  %s:%d  %s::%s  %s" % (rel, ln, cls, method, snip[:90]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
