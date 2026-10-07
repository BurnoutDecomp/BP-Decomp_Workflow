#!/usr/bin/env python3
"""MSDKB link probe: compile a set of .cpp files with the canonical exe flags into a
persistent obj dir, then list (a) external symbols the set references but does not
define and (b) symbols defined by more than one obj of the set (strong defs only).

Usage: python STUBS_MSDKB_linkprobe.py <objdir> <file.cpp>... [--filter REGEX] [--nocompile]
"""
import os, re, subprocess, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "tools", "work"))
import verify  # noqa: E402


def compile_all(objdir, files):
    os.makedirs(objdir, exist_ok=True)
    flags = " ".join(sum((ln.split() for ln in verify._read_list(verify.FLAGS_TXT)), [])) + " /c"
    incs = " ".join('/I"%s"' % os.path.normpath(os.path.join(ROOT, d)) for d in verify._read_list(verify.INCS_TXT))
    srcs = " ".join('"%s"' % os.path.normpath(verify._abs(f)) for f in files)
    bat = os.path.join(objdir, "probe.bat")
    with open(bat, "w", encoding="utf-8") as fh:
        fh.write("@echo off\n")
        fh.write('call "%s" >nul 2>&1\n' % os.path.normpath(verify.MSVC_ENV))
        fh.write("cl %s %s %s\n" % (flags, incs, srcs))
        fh.write("exit /b %ERRORLEVEL%\n")
    p = subprocess.run(["cmd", "/c", bat], cwd=objdir, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    errs = [l for l in (p.stdout or "").splitlines() if " error " in l]
    return p.returncode, errs


def dumpbin(objdir, obj):
    bat = os.path.join(objdir, "dump.bat")
    with open(bat, "w", encoding="utf-8") as fh:
        fh.write("@echo off\n")
        fh.write('call "%s" >nul 2>&1\n' % os.path.normpath(verify.MSVC_ENV))
        fh.write('dumpbin /symbols "%s"\n' % obj)
    p = subprocess.run(["cmd", "/c", bat], cwd=objdir, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.stdout or ""


SYM = re.compile(r"^[0-9A-F]{3,}\s+[0-9A-F]{8}\s+(\S+)\s+(?:\S+\s+)?(\(\)|)\s*(\w+)\s+\|\s+(\S+)(.*)$")


def main():
    args = sys.argv[1:]
    filt = None
    nocompile = False
    if "--filter" in args:
        i = args.index("--filter"); filt = re.compile(args[i + 1]); del args[i:i + 2]
    if "--nocompile" in args:
        args.remove("--nocompile"); nocompile = True
    objdir = os.path.abspath(args[0]); files = args[1:]
    if not nocompile:
        rc, errs = compile_all(objdir, files)
        print("COMPILE rc=%d" % rc)
        for e in errs[:40]:
            print("  " + e)
    defined = collections.defaultdict(list)
    undef = collections.defaultdict(set)
    for f in files:
        obj = os.path.join(objdir, os.path.splitext(os.path.basename(f))[0] + ".obj")
        if not os.path.exists(obj):
            print("NO OBJ", obj); continue
        comdat = set()
        for line in dumpbin(objdir, obj).splitlines():
            m = SYM.match(line)
            if not m:
                continue
            sect, _, scl, name = m.group(1), m.group(2), m.group(3), m.group(4)
            if scl != "External":
                continue
            if sect == "UNDEF":
                undef[name].add(os.path.basename(f))
            else:
                defined[name].append(os.path.basename(f))
    print("== UNRESOLVED (referenced, not defined in set)")
    for n in sorted(undef):
        if n in defined:
            continue
        if filt and not filt.search(n):
            continue
        print("  %s   <- %s" % (n, ", ".join(sorted(undef[n]))))
    print("== MULTIPLY DEFINED (may be COMDAT/inline; check)")
    for n, l in sorted(defined.items()):
        if len(l) > 1 and (not filt or filt.search(n)):
            print("  %s   in %s" % (n, ", ".join(l)))


if __name__ == "__main__":
    main()
