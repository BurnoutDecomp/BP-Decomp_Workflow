#!/usr/bin/env python3
"""
asmmatch.py -- the EXACT tier: PowerPC instruction streams diffed decomp.me-style.
==============================================================================================

asmaudit.py scores the SHAPE of a function across two ISAs. This tool is for the case JeBobs
named: a function whose C++ is portable enough to compile for the console itself, whose
instruction stream can then be diffed line by line against ARTIST -- a real match percentage,
like decomp.me shows. Two ways to get a second PowerPC stream:

  --decfigs NAME      the PS3 DecFIGS export of the same function (progress/identity.json
                      knows the address). Not our code -- a different compiler's rendering of
                      the same source -- but it calibrates what "same source, other build" looks
                      like on this scorer and needs nothing but the exports.
  --listing FILE.asm  a MSVC-style listing produced by the Xbox 360 SDK compiler
                      (`cl /c /FAs /Fa<out> ...` in an XEDK environment) -- OUR body, compiled
                      for the console. --compile drives that for one source file when the SDK
                      is installed (XEDK env / --sdk); it is a thin wrapper, adjust the flags
                      in XEDK_FLAGS to the build you want to match.

SCORING. Each line becomes (mnemonic, operands) with everything position-dependent
abstracted: branch targets and code addresses -> L, stack-slot names -> S, .rdata symbols
-> D, callee names normalised as asmaudit does. Registers and immediates are kept, so a
different register allocation or a different constant counts as a difference. The score is
difflib's ratio over the two sequences (2*matches/total) as a percentage, and the diff
prints the aligned streams: `  ` same, `- ` only ARTIST, `+ ` only ours.

Only functions without struct-offset dependence can approach 100% here: every field offset
in this tree is x64-widened, so a load/store displacement differs by construction. The
scorer keeps displacements (they ARE what differs) but --loose masks them, which shows
whether anything BUT the widening differs.
==============================================================================================
"""
import argparse
import difflib
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import asmaudit  # noqa: E402

REPO = asmaudit.REPO
DECFIGS = os.environ.get("BP_IDA_EXPORTS_DECFIGS") or os.path.join(REPO, ".ida-exports", "DecFIGS_Burnout_Internal_PS3.ELF")
XEDK_FLAGS = ["/c", "/nologo", "/O2", "/Oi", "/Ob2", "/GR-", "/GS-", "/EHs-c-", "/FAs", "/D_XBOX", "/DXBOX", "/D_M_PPCBE"]

IDA_LINE = re.compile(r"^0x([0-9A-Fa-f]+)\s+(\S+)\s*(.*)$")
LISTING_LINE = re.compile(r"^\s*([0-9A-Fa-f]{5,8})?\s*(?:[0-9A-Fa-f]{8}\s+)?\s*([a-z][a-z0-9.+-]*)\s+(.*?)\s*(?:;.*)?$")


def normalise(mn, ops, loose=False):
    mn = mn.rstrip("+-")
    ops = re.split(r"\s*[#;]", ops)[0].strip()
    if mn in ("bl", "bla"):
        name = asmaudit.console_callee(ops)
        return (mn, name or "?")
    ops = re.sub(r"\bloc_[0-9A-Fa-f]+\b", "L", ops)
    ops = re.sub(r"\b0x8[0-9A-Fa-f]{7}\b", "L", ops)
    ops = re.sub(r"\$[A-Za-z_][\w$]*", "L", ops)           # listing labels ($LN12)
    ops = re.sub(r"\b(?:0x[0-9A-Fa-f]+\+)?(?:var|arg|back_chain|sender_lr)_?\w*\((r1|r31)\)", r"S(\1)", ops)
    ops = re.sub(r"\b(?:flt|dbl|unk|dword|word|byte|off|stru|qword|a[A-Z]\w*)_?[0-9A-Fa-f]*(?:@[hl]a?)?\b", "D", ops)
    ops = re.sub(r"\b[A-Za-z_][\w.$?@]*@[hl]a?\b", "D", ops)  # symbol@ha / @l
    ops = re.sub(r"\([^()]*\)\((r\d+)\)", r"D(\1)", ops)      # (sym-0x..)(rN) TOC/base-relative data
    if loose:
        ops = re.sub(r"(?<![\w.])-?(?:0x[0-9A-Fa-f]+|\d+)\((r\d+)\)", r"O(\1)", ops)
    ops = re.sub(r"\s+", "", ops)
    return (mn, ops)


def seq_from_ida(asm, loose=False):
    out = []
    for line in asm.splitlines():
        m = IDA_LINE.match(line)
        if m:
            out.append(normalise(m.group(2), m.group(3), loose))
    return out


def seq_from_listing(text, func_dec=None, loose=False):
    """Instructions of one PROC (by decorated name, or the first) in a MSVC-style listing."""
    out = []
    inside = func_dec is None
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"^\S+\s+PROC\b", s):
            inside = func_dec is None or s.split()[0] == func_dec
            continue
        if re.match(r"^\S+\s+ENDP\b", s):
            if inside and func_dec is not None:
                break
            inside = func_dec is None
            continue
        if not inside or not s or s.startswith((";", "$", "?", "_", ".", "PUBLIC", "EXTRN", "END", "include", "TITLE")):
            continue
        m = LISTING_LINE.match(line)
        if m and m.group(2):
            out.append(normalise(m.group(2), m.group(3) or "", loose))
    return out


def match_score(a, b):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return round(100.0 * sm.ratio(), 1), sm


def print_diff(a, b, sm, width=44):
    def fmt(t):
        return f"{t[0]} {t[1]}"[:width].ljust(width)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                print(f"   {fmt(a[i1 + k])}   {fmt(b[j1 + k])}")
        else:
            left = [fmt(x) for x in a[i1:i2]]
            right = [fmt(x) for x in b[j1:j2]]
            for k in range(max(len(left), len(right))):
                l_ = left[k] if k < len(left) else " " * width
                r_ = right[k] if k < len(right) else " " * width
                mark = "~ " if tag == "replace" else ("- " if k < len(left) and k >= len(right) else "+ ")
                print(f"{mark} {l_}   {r_}")


def load_export(dir_, addr):
    for fn in (f"{addr}.json", f"0x{addr}.json", f"0x{addr.upper()}.json", f"0x{addr.upper().lstrip('0X')}.json"):
        p = os.path.join(dir_, fn)
        if os.path.exists(p):
            with io.open(p, "r", encoding="utf-8") as fh:
                return json.load(fh)
    return None


def resolve(name):
    with io.open(asmaudit.IDENTITY, "r", encoding="utf-8") as fh:
        ident = json.load(fh)
    if name in ident:
        return name, ident[name]
    hits = [k for k in ident if k.endswith("::" + name) or name in k]
    if len(hits) == 1:
        return hits[0], ident[hits[0]]
    sys.exit(f"{name}: not in identity.json" + (f"; candidates: {hits[:10]}" if hits else ""))


def find_sdk(explicit):
    for cand in (explicit, os.environ.get("XEDK")):
        if cand and os.path.exists(os.path.join(cand, "bin", "win32", "cl.exe")):
            return cand
    return None


def compile_listing(src, sdk, extra, out_asm):
    cl = os.path.join(sdk, "bin", "win32", "cl.exe")
    env = dict(os.environ)
    env["PATH"] = os.path.join(sdk, "bin", "win32") + os.pathsep + env.get("PATH", "")
    inc = [os.path.join(sdk, "include", "xbox"), os.path.join(REPO, "b5-decomp", "src")]
    env["INCLUDE"] = os.pathsep.join(inc + [env.get("INCLUDE", "")])
    cmd = [cl] + XEDK_FLAGS + ["/Fa" + out_asm, "/Fo" + out_asm + ".obj"] + extra + [src]
    print("$ " + " ".join(cmd))
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, errors="replace")
    sys.stdout.write(proc.stdout[-4000:])
    sys.stderr.write(proc.stderr[-4000:])
    if proc.returncode != 0:
        sys.exit(f"cl exited {proc.returncode}")
    return out_asm


def main():
    ap = argparse.ArgumentParser(description="PowerPC instruction-stream match vs ARTIST (decomp.me-style)")
    ap.add_argument("func", help="canonical function name (or a unique suffix)")
    ap.add_argument("--decfigs", action="store_true", help="compare ARTIST with the PS3 DecFIGS rendering")
    ap.add_argument("--listing", help="MSVC-style .asm listing holding our compiled body")
    ap.add_argument("--dec", help="decorated name of the PROC to take from the listing (default: first PROC)")
    ap.add_argument("--compile", metavar="SRC", help="compile SRC with the Xbox 360 SDK compiler into a listing first")
    ap.add_argument("--sdk", help="XEDK root (default: $XEDK)")
    ap.add_argument("--cl-arg", action="append", default=[], help="extra cl.exe argument (repeatable)")
    ap.add_argument("--loose", action="store_true", help="mask load/store displacements (the x64 widening)")
    ap.add_argument("--quiet", action="store_true", help="score only, no diff")
    args = ap.parse_args()

    name, entry = resolve(args.func)
    addrs = entry.get("x360_addrs") or []
    if not addrs:
        sys.exit(f"{name}: no X360 address in identity.json")
    artist = load_export(asmaudit.EXPORTS, addrs[0])
    if not artist:
        sys.exit(f"{name}: ARTIST export {addrs[0]} not on this box")
    a = seq_from_ida(artist.get("assembly") or "", args.loose)

    if args.decfigs:
        ps3 = entry.get("decfigs_ps3_addr")
        if not ps3:
            sys.exit(f"{name}: identity.json has no DecFIGS address for it")
        other = load_export(DECFIGS, ps3)
        if not other:
            sys.exit(f"{name}: DecFIGS export {ps3} not on this box")
        b = seq_from_ida(other.get("assembly") or "", args.loose)
        label = f"DecFIGS PS3 0x{ps3}"
    else:
        listing = args.listing
        if args.compile:
            sdk = find_sdk(args.sdk)
            if not sdk:
                sys.exit("Xbox 360 SDK not found: set XEDK or pass --sdk <root> (needs bin/win32/cl.exe)")
            out_dir = os.path.join(REPO, "scratch", "asmmatch")
            os.makedirs(out_dir, exist_ok=True)
            listing = compile_listing(args.compile, sdk, args.cl_arg, os.path.join(out_dir, os.path.basename(args.compile) + ".asm"))
        if not listing:
            sys.exit("give --decfigs, --listing FILE.asm or --compile SRC")
        with io.open(listing, "r", encoding="utf-8", errors="replace") as fh:
            b = seq_from_listing(fh.read(), args.dec, args.loose)
        if not b:
            sys.exit(f"no instructions found in {listing}" + (f" for PROC {args.dec}" if args.dec else ""))
        label = f"listing {listing}"

    pct, sm = match_score(a, b)
    print(f"{name}  ARTIST {addrs[0]} ({len(a)} insns)  vs  {label} ({len(b)} insns)")
    print(f"match {pct}%{' (loose: displacements masked)' if args.loose else ''}")
    if not args.quiet:
        print()
        print_diff(a, b, sm)


if __name__ == "__main__":
    main()
