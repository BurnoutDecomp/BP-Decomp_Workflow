#!/usr/bin/env python3
"""MSDKB: build + run the MassiveAd hashing known-answer test against the real SDK TUs.
Usage: python tools/tests/tools/STUBS_MSDKB_cryptotest.py   (prints RESULT PASS|FAIL)"""
import os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "tools", "work"))
import verify  # noqa: E402

SDK = os.path.join(ROOT, "b5-decomp", "src", "SDKs", "Packages", "MassiveAd")
SRCS = [
    os.path.join(ROOT, "tools", "tests", "tools", "STUBS_MSDKB_cryptotest.cpp"),
    os.path.join(SDK, "MassiveAdClient3Crypto.cpp"),
    os.path.join(SDK, "MassiveAdClient3Random.cpp"),
    os.path.join(SDK, "LibTomCrypt", "md5.cpp"),
    os.path.join(SDK, "LibTomCrypt", "zeromem.cpp"),
    os.path.join(SDK, "LibTomCrypt", "burn_stack.cpp"),
    os.path.join(SDK, "LibTomCrypt", "crypt_argchk.cpp"),
]


def main():
    out = tempfile.mkdtemp(prefix="msdkb_crypto_")
    flags = " ".join(sum((ln.split() for ln in verify._read_list(verify.FLAGS_TXT)), []))
    incs = " ".join('/I"%s"' % os.path.normpath(os.path.join(ROOT, d)) for d in verify._read_list(verify.INCS_TXT))
    srcs = " ".join('"%s"' % s for s in SRCS)
    exe = os.path.join(out, "cryptotest.exe")
    bat = os.path.join(out, "b.bat")
    with open(bat, "w", encoding="utf-8") as fh:
        fh.write("@echo off\n")
        fh.write('call "%s" >nul 2>&1\n' % os.path.normpath(verify.MSVC_ENV))
        fh.write('cl %s %s %s /Fe"%s" /link /INCREMENTAL:NO\n' % (flags, incs, srcs, exe))
        fh.write("exit /b %ERRORLEVEL%\n")
    p = subprocess.run(["cmd", "/c", bat], cwd=out, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0 or not os.path.exists(exe):
        print(p.stdout[-6000:])
        print("RESULT FAIL (build)")
        return 1
    r = subprocess.run([exe], capture_output=True, text=True)
    print(r.stdout)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
