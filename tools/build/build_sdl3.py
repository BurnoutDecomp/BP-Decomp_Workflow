"""Build the b5-decomp SDL3 submodule into the MSVC x64 package layout the exe uses.

The source is the BurnoutDecomp/SDL fork pinned as b5-decomp/vendor/SDL (release
3.4.18 plus the Steam Controller haptics backport). The result keeps the layout the
shipping bat, the tests and CI already consume:

  b5-decomp/vendor/sdl3/include/SDL3/*.h
  b5-decomp/vendor/sdl3/lib/x64/SDL3.lib, SDL3.dll
  b5-decomp/vendor/sdl3/LICENSE.txt, VERSION.txt (version + submodule commit)

A rebuild is skipped while VERSION.txt names the submodule's current commit.
CMake and Ninja come from the MSVC environment (VS2022's bundled copies).
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "b5-decomp/vendor/SDL"
DEST = ROOT / "b5-decomp/vendor/sdl3"
BUILD = ROOT / "build/sdl3"
MSVC_ENV = ROOT / "tools/build/msvc_env.bat"
REQUIRED = ("include/SDL3/SDL.h", "lib/x64/SDL3.lib", "lib/x64/SDL3.dll", "LICENSE.txt")
OPTIONS = ("-DCMAKE_BUILD_TYPE=Release", "-DSDL_SHARED=ON", "-DSDL_STATIC=OFF",
           "-DSDL_TEST_LIBRARY=OFF", "-DSDL_TESTS=OFF", "-DSDL_EXAMPLES=OFF",
           "-DSDL_INSTALL_DOCS=OFF", "-DSDL_VENDOR_INFO=BurnoutDecomp")


def source_stamp() -> str:
    if not (SOURCE / "CMakeLists.txt").is_file():
        raise RuntimeError(f"SDL submodule missing at {SOURCE} -- run: "
                           "git -C b5-decomp submodule update --init vendor/SDL")
    commit = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], check=True,
                            capture_output=True, text=True).stdout.strip()
    version = "unknown"
    fields = {}
    for line in (SOURCE / "include/SDL3/SDL_version.h").read_text(encoding="utf-8").splitlines():
        words = line.split()
        if len(words) == 3 and words[0] == "#define" and words[1] in (
                "SDL_MAJOR_VERSION", "SDL_MINOR_VERSION", "SDL_MICRO_VERSION"):
            fields[words[1]] = words[2]
    if len(fields) == 3:
        version = ".".join(fields[k] for k in ("SDL_MAJOR_VERSION", "SDL_MINOR_VERSION", "SDL_MICRO_VERSION"))
    return f"{version}+{commit}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    stamp = source_stamp()
    stamp_file = DEST / "VERSION.txt"
    if (not args.force and stamp_file.exists() and stamp_file.read_text().strip() == stamp
            and all((DEST / name).is_file() for name in REQUIRED)):
        print(f"SDL3 {stamp} already built in {DEST}")
        return 0
    with tempfile.TemporaryDirectory(prefix="brn_sdl3_") as directory:
        stage = Path(directory)
        prefix = stage / "install"
        script = stage / "build.cmd"
        configure = ["cmake", "-S", str(SOURCE), "-B", str(BUILD), "-G", "Ninja", *OPTIONS]
        lines = ["@echo off", f'call "{MSVC_ENV}"', "if errorlevel 1 exit /b 1",
                 subprocess.list2cmdline(configure), "if errorlevel 1 exit /b 1",
                 subprocess.list2cmdline(["cmake", "--build", str(BUILD)]), "if errorlevel 1 exit /b 1",
                 subprocess.list2cmdline(["cmake", "--install", str(BUILD), "--prefix", str(prefix)]),
                 "exit /b %ERRORLEVEL%"]
        script.write_text("\r\n".join(lines) + "\r\n", encoding="ascii")
        print(f"Building SDL3 {stamp} from {SOURCE} ...", flush=True)
        if subprocess.run(["cmd", "/c", str(script)]).returncode:
            raise RuntimeError("SDL3 CMake build failed")
        if DEST.exists():
            shutil.rmtree(DEST)
        shutil.copytree(prefix / "include", DEST / "include")
        (DEST / "lib/x64").mkdir(parents=True)
        shutil.copy2(prefix / "lib/SDL3.lib", DEST / "lib/x64/SDL3.lib")
        shutil.copy2(prefix / "bin/SDL3.dll", DEST / "lib/x64/SDL3.dll")
        shutil.copy2(SOURCE / "LICENSE.txt", DEST / "LICENSE.txt")
        if not all((DEST / name).is_file() for name in REQUIRED):
            raise RuntimeError("SDL3 build is missing required headers/library/runtime files")
        stamp_file.write_text(stamp + "\n", encoding="ascii")
    print(f"SDL3 {stamp} installed to {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
