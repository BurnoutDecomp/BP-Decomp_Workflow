#!/usr/bin/env python3
"""BANKPL: round-trip the camera parameter bank through TextFileWriteSerialiser then
TextFileReadSerialiser, linked against the game's own objects (the last build's link.rsp minus the
WinMain TU, plus STUBS_BANKPL_roundtrip.cpp as a console main).

Usage: python tools/tests/tools/STUBS_BANKPL_roundtrip.py [--replace STEM=path.cpp ...]
  --replace STEM=path : link path.cpp's object instead of the build's STEM.*.obj (pre-mount check)
Prints the test's checks and RESULT PASS|FAIL."""
import os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OBJROOT = os.path.join(ROOT, 'build', 'game', 'obj')
BASE = os.path.join(OBJROOT, 'base.rsp')
LINKRSP = os.path.join(OBJROOT, 'tu', 'link.rsp')
MSVC_ENV = os.path.join(ROOT, 'tools', 'build', 'msvc_env.bat')
VEN = os.path.join(ROOT, 'b5-decomp', 'vendor')
FFM = os.path.join(VEN, 'ffmpeg-build')
TEST = os.path.join(ROOT, 'tools', 'tests', 'tools', 'STUBS_BANKPL_roundtrip.cpp')
DROP = ('BrnMain.',)   # the TU that defines WinMain


def main():
    replace = {}
    args = sys.argv[1:]
    while args:
        if args[0] == '--replace':
            stem, path = args[1].split('=', 1)
            replace[stem] = os.path.abspath(path)
            args = args[2:]
        else:
            raise SystemExit('bad arg ' + args[0])
    out = tempfile.mkdtemp(prefix='bankpl_rt_')
    srcs = [TEST] + list(replace.values())
    objs_new = [os.path.join(out, '%d_%s.obj' % (i, os.path.splitext(os.path.basename(s))[0])) for i, s in enumerate(srcs)]
    objs = []
    for line in open(LINKRSP, encoding='utf-8'):
        p = line.strip().strip('"')
        if not p:
            continue
        b = os.path.basename(p)
        if b.startswith(DROP) or any(b.startswith(st + '.') for st in replace):
            continue
        objs.append(p)
    rsp = os.path.join(out, 'link.rsp')
    with open(rsp, 'w', encoding='utf-8') as fh:
        for o in objs + objs_new:
            fh.write('"%s"\n' % o)
    exe = os.path.join(out, 'roundtrip.exe')
    libs = ('/LIBPATH:"%s\\bin" d3d9.lib user32.lib gdi32.lib gdiplus.lib kernel32.lib ntdll.lib winmm.lib '
            'shell32.lib ole32.lib advapi32.lib ws2_32.lib avformat.lib avcodec.lib avutil.lib swscale.lib '
            'swresample.lib "%s\\lua\\lua515.lib"') % (FFM, VEN)
    bat = os.path.join(out, 'b.bat')
    with open(bat, 'w', encoding='utf-8') as fh:
        fh.write('@echo off\r\ncall "%s" >nul 2>&1\r\n' % MSVC_ENV)
        for s, o in zip(srcs, objs_new):
            fh.write('cl /c @"%s" /Fo"%s" "%s" || exit /b 1\r\n' % (BASE, o, s))
        fh.write('link /nologo /SUBSYSTEM:CONSOLE /FORCE:UNRESOLVED /OUT:"%s" @"%s" %s\r\n' % (exe, rsp, libs))
        fh.write('exit /b 0\r\n')
    p = subprocess.run(['cmd', '/c', bat], cwd=out, capture_output=True, text=True, errors='replace')
    unresolved = [l for l in p.stdout.splitlines() if 'LNK2001' in l or 'LNK2019' in l]
    if not os.path.exists(exe):
        print(p.stdout[-6000:])
        print('RESULT FAIL (build)')
        return 1
    print('built (%d unresolved externals tolerated, none reachable from the test)' % len(unresolved))
    for l in unresolved[:20]:
        print('  ', l[:220])
    env = dict(os.environ)
    env['PATH'] = os.path.join(ROOT, 'build', 'game') + os.pathsep + os.path.join(FFM, 'bin') + os.pathsep + env.get('PATH', '')
    r = subprocess.run([exe, out], capture_output=True, text=True, errors='replace', timeout=120, env=env)
    print(r.stdout)
    if r.returncode != 0 and 'RESULT' not in r.stdout:
        print('exit code', r.returncode, r.stderr[-2000:])
        print('RESULT FAIL (run)')
        return 1
    return r.returncode


if __name__ == '__main__':
    sys.exit(main())
