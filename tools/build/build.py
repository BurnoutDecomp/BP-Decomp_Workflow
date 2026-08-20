#!/usr/bin/env python3
"""The one build driver: `build <subcommand>` from the repo root (via build.cmd).

Sequences the existing workhorse scripts -- it does NOT reimplement any build:
  doctor   readiness report (read-only; exit 0 = no FAIL)
  tools    YAP + Volatility        -> tools/build/build_tools.ps1
  lua      lua515.lib              -> tools/build/build_lua.bat
  ffmpeg   vendor/ffmpeg-build     -> tools/build/build_ffmpeg.bat [--prebuilt]
  xaudio2  vendor/xaudio2redist     -> tools/build/fetch_xaudio2_redist.bat
  exe      Burnout_PC.exe          -> tools/build/build_game_exe.bat
  data     converted game data     -> tools/assets/build_game_data.py (args forwarded)
  all      tools -> lua -> ffmpeg -> xaudio2 -> exe -> data, skip-if-present
  run      launch the exe from its own folder (the schema.vlt CWD contract)

Machine paths come from build.config.toml (copy build.config.example.toml); the
driver loads it once and exports the values as env vars, so every child script
behaves exactly as it would standalone. Precedence: CLI > env > config > probed.
"""
import argparse
import ast
import glob
import os
import shutil
import subprocess
import sys
import time

if sys.version_info < (3, 11):
    sys.exit("build.py needs Python 3.11+ for tomllib (found %s)" % sys.version.split()[0])

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_config  # noqa: E402  (sibling module)

REPO = build_config.REPO
B5 = os.path.join(REPO, "b5-decomp")
TOOLS_BUILD = os.path.join(REPO, "tools", "build")
GAME_OUT = os.path.join(REPO, "build", "game")
EXE = os.path.join(GAME_OUT, "Burnout_PC.exe")
FFMPEG_BUILD = os.path.join(B5, "vendor", "ffmpeg-build")
LUA_LIB = os.path.join(B5, "vendor", "lua", "lua515.lib")
XAUDIO2_REDIST = os.path.join(B5, "vendor", "xaudio2redist")
YAP_EXE = os.path.join(REPO, "build", "tools", "yap", "YAP.exe")
VOLA_EXE = os.path.join(REPO, "build", "tools", "volatility", "Volatility.Cli.exe")
STAGER = os.path.join(REPO, "tools", "assets", "build_game_data.py")
DEFAULT_X360_ROOT = os.path.join(REPO, "references", "private", "Burnout_tcartwright")

VS_EDITIONS = ("Community", "Enterprise", "Professional", "BuildTools")
VSWHERE = os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                       "Microsoft Visual Studio", "Installer", "vswhere.exe")


# ---------------------------------------------------------------- child spawns
def _pwsh():
    return shutil.which("pwsh") or shutil.which("powershell")


def run_bat(bat, *args, dry=False):
    cmd = ["cmd.exe", "/c", bat, *args]
    if dry:
        print("  would run:", subprocess.list2cmdline(cmd))
        return 0
    return subprocess.run(cmd).returncode


def run_ps1(ps1, *args, dry=False):
    sh = _pwsh()
    if not sh:
        print("ERROR: neither pwsh nor powershell found on PATH.")
        return 2
    cmd = [sh, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1, *args]
    if dry:
        print("  would run:", subprocess.list2cmdline(cmd))
        return 0
    return subprocess.run(cmd).returncode


def run_py(script, *args, dry=False):
    cmd = [sys.executable, script, *args]
    if dry:
        print("  would run:", subprocess.list2cmdline(cmd))
        return 0
    return subprocess.run(cmd).returncode


# ---------------------------------------------------------------- probes
def resolve_vcvars():
    """(path|None, provenance). Shallow mirror of tools/build/msvc_env.bat --
    the bat is authoritative at build time; this is for doctor/preflight."""
    v = os.environ.get("VCVARS64")
    if v:
        return (v, "env/config") if os.path.exists(v) else (None, f"VCVARS64 set but missing: {v}")
    for e in VS_EDITIONS:
        p = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                         "Microsoft Visual Studio", "2022", e,
                         "VC", "Auxiliary", "Build", "vcvars64.bat")
        if os.path.exists(p):
            return p, "probed"
    if os.path.exists(VSWHERE):
        return VSWHERE, "vswhere-available"
    return None, "not found"


def resolve_qt6():
    for env in ("QT6_DIR", "CMAKE_PREFIX_PATH"):
        v = os.environ.get(env)
        if v and os.path.isdir(v):
            return v, f"env {env}"
    hits = sorted(glob.glob(r"C:\Qt\6.*\msvc*_64"))
    if hits:
        return hits[-1], "probed"
    return None, "not found"


def resolve_fxc():
    v = os.environ.get("PC_FXC")
    if v and os.path.exists(v):
        return v, "env/config"
    hits = sorted(glob.glob(os.path.join(os.environ.get("ProgramFiles(x86)",
                                                        r"C:\Program Files (x86)"),
                                         "Windows Kits", "10", "bin", "*", "x64", "fxc.exe")))
    if hits:
        return hits[-1], "probed"
    w = shutil.which("fxc")
    return (w, "PATH") if w else (None, "not found")


def resolve_x360_root(cfg):
    v = os.environ.get("BRN_X360_ROOT")
    if v:
        return v, "env/config"
    if os.path.isdir(DEFAULT_X360_ROOT):
        return DEFAULT_X360_ROOT, "repo default"
    return None, "not found"


def bnd2_platform(path):
    """Local 12-byte reimplementation of the stager's platform sniff: magic 'bnd2',
    u32 at +8 read both endiannesses, the plausible small value wins."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(12)
    except OSError:
        return None
    if len(head) < 12 or head[:4] not in (b"bnd2", b"BND2"):
        return None
    le = int.from_bytes(head[8:12], "little")
    be = int.from_bytes(head[8:12], "big")
    for v in (le, be):
        if 1 <= v <= 16:
            return v
    return None


def exe_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Burnout_PC.exe", "/NH"],
                             capture_output=True, text=True).stdout
        return "Burnout_PC.exe" in (out or "")
    except OSError:
        return False


# ---------------------------------------------------------------- doctor
class Report:
    def __init__(self):
        self.fails = 0

    def row(self, level, text, needed_by=None, fix=None):
        tag = {"ok": "[ OK ]", "warn": "[WARN]", "fail": "[FAIL]", "info": "[INFO]"}[level]
        print(f"{tag} {text}")
        if needed_by:
            print(f"         needed by: {needed_by}")
        if fix:
            print(f"         fix: {fix}")
        if level == "fail":
            self.fails += 1

    def section(self, title):
        print(f"\n-- {title} --")


def cmd_doctor(cfg, args):
    r = Report()
    r.section("general")
    r.row("ok", f"Python {sys.version.split()[0]} ({sys.executable})")
    if not shutil.which("py"):
        r.row("warn", "the 'py' launcher is absent -- build_game_exe.bat warns and skips "
                      "the .cgsmap (assert call-stack names) when it can't find it")
    if os.path.isfile(build_config.CONFIG_PATH):
        unknown = build_config.unknown_keys(cfg)
        if unknown:
            r.row("warn", "build.config.toml has unknown keys (typos?): " + ", ".join(unknown))
        else:
            r.row("ok", "build.config.toml present")
    else:
        r.row("warn", "no build.config.toml -- probing defaults for everything",
              fix="copy build.config.example.toml build.config.toml, then edit")

    r.section("for the exe build")
    subs = [
        ("b5-decomp sources", os.path.join(B5, "src"),
         "git submodule update --init b5-decomp"),
        ("EABase", os.path.join(B5, "vendor", "EABase", "include", "Common"),
         "git -C b5-decomp submodule update --init vendor/EABase"),
        ("EASTL", os.path.join(B5, "vendor", "EASTL", "include"),
         "git -C b5-decomp submodule update --init vendor/EASTL"),
        ("EAThread", os.path.join(B5, "vendor", "EAThread", "include"),
         "git -C b5-decomp submodule update --init vendor/EAThread"),
    ]
    for name, marker, fix in subs:
        if os.path.exists(marker):
            r.row("ok", f"{name} populated")
        else:
            r.row("fail", f"{name} NOT populated ({marker} missing)", "exe", fix)
    vc, how = resolve_vcvars()
    if vc:
        r.row("ok", f"MSVC: {vc} ({how})")
    else:
        r.row("fail", f"MSVC not found ({how})", "exe, lua, ffmpeg, compile gate",
              "install VS2022 'Desktop development with C++', or set VCVARS64 / "
              "[toolchain].vcvars64")
    if os.path.exists(os.path.join(FFMPEG_BUILD, "bin", "avcodec.lib")) and \
       os.path.exists(os.path.join(FFMPEG_BUILD, "include", "libavcodec", "avcodec.h")):
        r.row("ok", "FFmpeg dev tree (vendor/ffmpeg-build)")
    else:
        r.row("fail", "FFmpeg dev tree missing (vendor/ffmpeg-build)", "exe",
              "build ffmpeg   (or: tools\\build\\build_ffmpeg.bat --prebuilt)")
        bash = os.path.join(os.environ.get("MSYS2_ROOT", r"C:\msys64"), "usr", "bin", "bash.exe")
        straw = os.path.join(os.environ.get("STRAWBERRY_ROOT", r"C:\Strawberry"), "c", "bin")
        if not os.path.exists(bash) or not os.path.isdir(straw):
            r.row("info", "MSYS2/Strawberry absent too -- use the prebuilt "
                          "(build ffmpeg --prebuilt) instead of the source build")
    if os.path.exists(LUA_LIB):
        r.row("ok", "Lua static lib (lua515.lib)")
    else:
        r.row("fail", "lua515.lib missing", "exe", "build lua")
    if os.path.exists(os.path.join(XAUDIO2_REDIST, "include", "xaudio2Redist.h")) and        os.path.exists(os.path.join(XAUDIO2_REDIST, "bin", "x64", "xaudio2_9redist.dll")):
        r.row("ok", "XAudio2 redist (vendor/xaudio2redist)")
    else:
        r.row("fail", "XAudio2 redist missing (vendor/xaudio2redist) -- the audio backend "
                      "includes its header and ships its DLL", "exe", "build xaudio2")
    if exe_running():
        r.row("warn", "Burnout_PC.exe is RUNNING -- the link would fail with LNK1104; "
                      "close it before `build exe`")

    r.section("for the tool build (YAP + Volatility)")
    for name, marker, fix in (
            ("tools/yap sources", os.path.join(REPO, "tools", "yap", "CMakeLists.txt"),
             "git submodule update --init tools/yap"),
            ("tools/volatility sources", os.path.join(REPO, "tools", "volatility", "Volatility.sln"),
             "git submodule update --init tools/volatility")):
        if os.path.exists(marker):
            r.row("ok", f"{name} populated")
        else:
            r.row("fail", f"{name} NOT populated", "tools", fix)
    for exe_name, why in (("dotnet", "Volatility"), ("cmake", "YAP")):
        if shutil.which(exe_name):
            r.row("ok", f"{exe_name} on PATH")
        else:
            r.row("fail", f"{exe_name} not on PATH", f"tools ({why})",
                  f"install the {'.NET SDK' if exe_name == 'dotnet' else 'CMake'}")
    qt, how = resolve_qt6()
    if qt:
        r.row("ok", f"Qt6 prefix: {qt} ({how})")
    else:
        r.row("fail", "Qt6 MSVC x64 prefix not found", "tools (YAP)",
              "install Qt6 or set QT6_DIR / [toolchain].qt6_dir")

    r.section("for the game-data build")
    if os.path.exists(YAP_EXE) and os.path.exists(VOLA_EXE):
        r.row("ok", "YAP.exe + Volatility.Cli.exe built")
    else:
        r.row("fail", "YAP.exe / Volatility.Cli.exe missing under build/tools", "data",
              "build tools   (skipping this is the classic 'run that fails 970 times')")
    x360, how = resolve_x360_root(cfg)
    if not x360:
        r.row("fail", "X360 game folder not found", "data",
              "set [inputs].x360_root in build.config.toml (or BRN_X360_ROOT) to your "
              "dumped retail X360 Burnout Paradise folder")
    else:
        shaders = os.path.join(x360, "SHADERS.BNDL")
        plat = bnd2_platform(shaders) if os.path.isfile(shaders) else None
        if plat == 2:
            r.row("ok", f"X360 root: {x360} ({how}; SHADERS.BNDL platform-2)")
        elif plat is None:
            r.row("fail", f"X360 root {x360} ({how}) has no readable SHADERS.BNDL", "data",
                  "point it at the dumped retail X360 game folder")
        else:
            r.row("fail", f"X360 root {x360} is platform {plat}, not X360 (2)", "data",
                  "this pass converts X360 data, not PC/PS3 bundles")
    tub = os.environ.get("NUSHADERS_TUB")
    tub_src = "env/config" if tub else None
    if not tub:
        # Mirror the converter/stager resolution: the in-repo submodule is the portable
        # default; the historical external clone remains a final compatibility fallback.
        candidates = [
            (os.path.join(REPO, "tools", "nushaders", "Source", "Bundle", "gamedb",
                          "burnout5"), "repo submodule"),
            (os.path.join(REPO, "tools", "nushaders", "Reference", "TUB", "Bundle",
                          "gamedb", "burnout5"), "repo submodule"),
            (r"D:\Burnout Paradise\Source\NuShaders\Reference\TUB\Bundle\gamedb\burnout5",
             "legacy external clone"),
        ]
        for candidate, source in candidates:
            if os.path.isdir(os.path.join(candidate, "Shaders")):
                tub, tub_src = candidate, source
                break
    if tub and os.path.isdir(os.path.join(tub, "Shaders")):
        r.row("ok", f"nushaders TUB HLSL: {tub} ({tub_src})")
    elif tub:
        r.row("warn", f"nushaders TUB HLSL configured but missing: {tub} -- "
                      "SHADERS.BNDL conversion will refuse",
              fix="correct [inputs].nushaders_tub / NUSHADERS_TUB")
    else:
        r.row("warn", "nushaders TUB HLSL tree not configured -- SHADERS.BNDL conversion "
                      "will refuse (every technique would fall back)",
              fix="git submodule update --init tools/nushaders, or set "
                  "[inputs].nushaders_tub to a gamedb root containing Shaders/")
    fxc, how = resolve_fxc()
    if fxc:
        r.row("ok", f"fxc.exe: {fxc} ({how})")
    else:
        r.row("warn", "fxc.exe not found (Windows SDK) -- shader conversion will fail",
              fix="install a Windows 10/11 SDK or set PC_FXC / [toolchain].fxc")
    bpr = os.environ.get("BRN_BPR_ROOT", r"C:\Program Files (x86)\Steam\steamapps\common\BurnoutPR")
    r.row("info", f"BPR oracle {'present' if os.path.isdir(bpr) else 'absent'} ({bpr}) -- "
                  "optional, only for --verify transcoder modes")
    try:
        ast.parse(open(STAGER, encoding="utf-8").read())
        r.row("ok", "build_game_data.py parses")
    except SyntaxError as e:
        r.row("fail", f"build_game_data.py DOES NOT PARSE: line {e.lineno}: {e.msg}", "data",
              "fix the stager before any data run")
    out_dir = build_config.get(cfg, "output", "game_data") or (x360 + "_decomp" if x360 else None)
    if out_dir:
        anchor = out_dir
        while anchor and not os.path.exists(anchor):
            parent = os.path.dirname(anchor)
            if parent == anchor:
                break
            anchor = parent
        try:
            free = shutil.disk_usage(anchor).free
            if free < 10 * (1 << 30):
                r.row("warn", f"only {free / (1 << 30):.1f} GiB free for {out_dir} "
                              "(a full conversion wants ~10 GiB)")
            else:
                r.row("ok", f"{free / (1 << 30):.0f} GiB free for data output ({out_dir})")
        except OSError:
            pass
    ida = os.environ.get("IDA_PATH")
    r.row("info", f"IDA_PATH {'= ' + ida if ida else 'unset'} -- ledger tooling only, "
                  "not needed to build")

    print()
    if r.fails:
        print(f"doctor: {r.fails} FAIL(s) -- fix the lines above and re-run `build doctor`.")
        return 1
    print("doctor: ready.")
    return 0


# ---------------------------------------------------------------- build steps
def step_tools(cfg, args, dry=False):
    if os.path.exists(YAP_EXE) and os.path.exists(VOLA_EXE) and not getattr(args, "force", False):
        print("tools: YAP.exe + Volatility.Cli.exe already built -- skipping (--force to rebuild)")
        return 0
    for exe_name, what in (("dotnet", ".NET SDK (Volatility)"), ("cmake", "CMake (YAP)")):
        if not shutil.which(exe_name):
            print(f"ERROR: {exe_name} not on PATH -- install the {what} first.")
            return 2
    qt, _ = resolve_qt6()
    if not qt:
        print("ERROR: Qt6 MSVC x64 prefix not found -- install Qt6 or set QT6_DIR / "
              "[toolchain].qt6_dir in build.config.toml.")
        return 2
    extra = []
    if getattr(args, "qt_prefix", None):
        extra += ["-QtPrefix", args.qt_prefix]
    if getattr(args, "skip_yap", False):
        extra += ["-SkipYap"]
    if getattr(args, "skip_volatility", False):
        extra += ["-SkipVolatility"]
    return run_ps1(os.path.join(TOOLS_BUILD, "build_tools.ps1"), *extra, dry=dry)


def step_lua(cfg, args, dry=False):
    if os.path.exists(LUA_LIB) and not getattr(args, "force", False):
        print("lua: lua515.lib already built -- skipping (--force to rebuild)")
        return 0
    if not os.path.exists(os.path.join(B5, "vendor", "lua", "src", "lapi.c")):
        print("ERROR: b5-decomp/vendor/lua sources missing -- run: "
              "git submodule update --init b5-decomp")
        return 2
    return run_bat(os.path.join(TOOLS_BUILD, "build_lua.bat"), dry=dry)


def step_ffmpeg(cfg, args, dry=False):
    if os.path.exists(os.path.join(FFMPEG_BUILD, "bin", "avcodec.lib")) and \
            not getattr(args, "force", False):
        print("ffmpeg: vendor/ffmpeg-build already present -- skipping (--force to rebuild)")
        return 0
    extra = ["--prebuilt"] if getattr(args, "prebuilt", False) else []
    return run_bat(os.path.join(TOOLS_BUILD, "build_ffmpeg.bat"), *extra, dry=dry)


def step_xaudio2(cfg, args, dry=False):
    """Fetch Microsoft's XAudio2 Redistributable -- the 2.9 engine
    CgsSystem::AudioOutputPC compiles against and ships beside the exe."""
    hdr = os.path.join(XAUDIO2_REDIST, "include", "xaudio2Redist.h")
    dll = os.path.join(XAUDIO2_REDIST, "bin", "x64", "xaudio2_9redist.dll")
    if os.path.exists(hdr) and os.path.exists(dll) and not getattr(args, "force", False):
        print("xaudio2: vendor/xaudio2redist already present -- skipping (--force to re-fetch)")
        return 0
    extra = ["--force"] if getattr(args, "force", False) else []
    return run_bat(os.path.join(TOOLS_BUILD, "fetch_xaudio2_redist.bat"), *extra, dry=dry)


def step_exe(cfg, args, dry=False):
    if exe_running():
        print("ERROR: Burnout_PC.exe is running -- the link would fail with LNK1104. "
              "Close the game first.")
        return 2
    return run_bat(os.path.join(TOOLS_BUILD, "build_game_exe.bat"), dry=dry)


def step_data(cfg, args, passthrough, dry=False):
    fwd = list(passthrough)
    joined = " ".join(fwd)
    if "--jobs" not in joined:
        jobs = build_config.get(cfg, "build", "jobs")
        if jobs:
            fwd += ["--jobs", str(jobs)]
    if "--borrow-dir" not in joined:
        borrow = build_config.get(cfg, "build", "borrow_dir")
        if borrow:
            fwd += ["--borrow-dir", borrow]
    if "--out" not in joined:
        out = build_config.get(cfg, "output", "game_data")
        if out:
            fwd += ["--out", out]
    return run_py(STAGER, *fwd, dry=dry)


def cmd_all(cfg, args, passthrough):
    dry = args.dry_run
    steps = [
        ("tools", lambda: step_tools(cfg, argparse.Namespace(force=args.force_tools,
                                                             qt_prefix=None, skip_yap=False,
                                                             skip_volatility=False), dry)),
        ("lua", lambda: step_lua(cfg, argparse.Namespace(force=args.force_lua), dry)),
        ("ffmpeg", lambda: step_ffmpeg(cfg, argparse.Namespace(force=args.force_ffmpeg,
                                                               prebuilt=args.prebuilt), dry)),
        ("xaudio2", lambda: step_xaudio2(cfg, argparse.Namespace(force=args.force_xaudio2), dry)),
        ("exe", lambda: step_exe(cfg, args, dry)),
        ("data", lambda: step_data(cfg, args, list(passthrough)
                                   + (["--dry-run"] if dry else []), False)),
    ]
    results = []
    for name, fn in steps:
        print(f"\n=== build {name} ===")
        t0 = time.time()
        rc = fn()
        results.append((name, rc, time.time() - t0))
        if rc != 0:
            print(f"*** {name} failed (exit {rc}) -- see the log above")
            break
    print("\n--- build all summary ---")
    for name, rc, dt in results:
        print(f"  {name:<7} {'ok' if rc == 0 else f'FAILED ({rc})':<12} {dt:6.1f}s")
    return 0 if all(rc == 0 for _, rc, _ in results) else 1


def cmd_devdata(cfg, args):
    """Refresh the GENERATED artifacts in the live dev folder build/game --
    schema.vlt/schema.bin + LOADINGSCREEN/*.dds. These come from the ARTIST XEX,
    not from a converted output folder, and the stager refuses --out build/game
    (shared run dir), so without this they go stale the way the gibberish
    loading screens and the 'PC schema file missing' assert did."""
    import tempfile
    x360, how = resolve_x360_root(cfg)
    if not x360:
        print("ERROR: X360 game folder not found (set [inputs].x360_root / BRN_X360_ROOT).")
        return 2
    xex = os.path.join(x360, "BURNOUT_X360_ARTIST.XEX")
    if not os.path.isfile(xex):
        print(f"ERROR: ARTIST XEX not found: {xex}")
        return 2
    env = dict(os.environ)
    env["BRN_X360_ROOT"] = x360
    print(f"devdata: XEX = {xex} ({how})")
    rc = subprocess.run([sys.executable,
                         os.path.join(REPO, "tools", "assets", "bundles",
                                      "attribsys_schema_port.py"),
                         "--xex", xex, "--out", GAME_OUT], env=env).returncode
    if rc != 0:
        print(f"*** attribsys_schema_port failed (exit {rc})")
        return rc
    work = tempfile.mkdtemp(prefix="devdata_")
    try:
        rc = subprocess.run([sys.executable,
                             os.path.join(REPO, "tools", "assets", "textures",
                                          "extract_xex.py")],
                            cwd=work, env=env).returncode
        if rc != 0:
            print(f"*** extract_xex failed (exit {rc})")
            return rc
        src = os.path.join(work, "build", "loadingscreen")
        dst = os.path.join(GAME_OUT, "LOADINGSCREEN")
        os.makedirs(dst, exist_ok=True)
        n = 0
        for f in os.listdir(src):
            shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
            n += 1
        print(f"devdata: schema.vlt + schema.bin -> build/game; {n} textures -> "
              f"build/game/LOADINGSCREEN")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return 0


def cmd_run(cfg, args):
    d = args.dir
    if not d:
        out = build_config.get(cfg, "output", "game_data")
        d = out if out and os.path.exists(os.path.join(out, "Burnout_PC.exe")) else GAME_OUT
    exe = os.path.join(d, "Burnout_PC.exe")
    if not os.path.exists(exe):
        print(f"exe not found: {exe} (run 'build exe' first)")
        return 1
    # CWD must be the exe's own folder: schema.vlt/BrnGame.log open with bare
    # relative fopen; a wrong CWD presents as "PC schema file missing".
    print(f"launching {exe} (cwd={d})")
    subprocess.Popen([exe], cwd=d)
    return 0


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(prog="build", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", help="alternate build.config.toml path")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="readiness report (read-only)")
    p = sub.add_parser("tools", help="build YAP + Volatility (build_tools.ps1)")
    p.add_argument("--force", action="store_true")
    p.add_argument("--qt-prefix")
    p.add_argument("--skip-yap", action="store_true")
    p.add_argument("--skip-volatility", action="store_true")
    p = sub.add_parser("lua", help="build lua515.lib (build_lua.bat)")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("ffmpeg", help="build or fetch vendor/ffmpeg-build (build_ffmpeg.bat)")
    p.add_argument("--force", action="store_true")
    p.add_argument("--prebuilt", action="store_true",
                   help="download the CI prebuilt instead of compiling (no MSYS2 needed)")
    p = sub.add_parser("xaudio2", help="fetch vendor/xaudio2redist "
                                      "(fetch_xaudio2_redist.bat)")
    p.add_argument("--force", action="store_true")
    sub.add_parser("exe", help="build Burnout_PC.exe (build_game_exe.bat)")
    p = sub.add_parser("data", help="convert the game data (build_game_data.py; "
                                    "unknown args are forwarded verbatim)")
    p = sub.add_parser("all", help="tools -> lua -> ffmpeg -> xaudio2 -> exe -> data "
                                   "(skip-if-present)")
    p.add_argument("--force-tools", action="store_true")
    p.add_argument("--force-lua", action="store_true")
    p.add_argument("--force-ffmpeg", action="store_true")
    p.add_argument("--force-xaudio2", action="store_true")
    p.add_argument("--prebuilt", action="store_true",
                   help="if ffmpeg must be built, fetch the CI prebuilt instead")
    p.add_argument("--dry-run", action="store_true",
                   help="print each step's command line and run nothing "
                        "(data's own plan mode remains `build data --dry-run`)")
    sub.add_parser("devdata", help="refresh generated dev assets in build/game "
                                   "(schema.vlt/bin + LOADINGSCREEN, from the ARTIST XEX)")
    p = sub.add_parser("run", help="launch Burnout_PC.exe from its own folder")
    p.add_argument("--dir", help="folder holding the exe (default: [output].game_data "
                                 "if it has one, else build/game)")

    args, passthrough = ap.parse_known_args(argv)
    if passthrough and args.cmd not in ("data", "all"):
        ap.error(f"unrecognized arguments: {' '.join(passthrough)}")

    cfg = build_config.load_config(args.config)
    prov = build_config.apply_env(cfg)
    if prov and args.cmd != "doctor":
        srcs = ", ".join(f"{k} ({v})" for k, v in sorted(prov.items()))
        print(f"config: {srcs}")

    if args.cmd == "doctor":
        return cmd_doctor(cfg, args)
    if args.cmd == "tools":
        return step_tools(cfg, args)
    if args.cmd == "lua":
        return step_lua(cfg, args)
    if args.cmd == "ffmpeg":
        return step_ffmpeg(cfg, args)
    if args.cmd == "xaudio2":
        return step_xaudio2(cfg, args)
    if args.cmd == "exe":
        return step_exe(cfg, args)
    if args.cmd == "data":
        return step_data(cfg, args, passthrough)
    if args.cmd == "devdata":
        return cmd_devdata(cfg, args)
    if args.cmd == "all":
        return cmd_all(cfg, args, passthrough)
    if args.cmd == "run":
        return cmd_run(cfg, args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
