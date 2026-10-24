"""Fetch the pinned SDL3 MSVC x64 headers, import library, DLL and license."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile

VERSION = "3.4.18"
SHA256 = "78d84602ae616cfe26b33a73b7d3b9b6b56e8a6650e53d92c9c6ca938f747acd"
URL = (f"https://github.com/libsdl-org/SDL/releases/download/release-{VERSION}/"
       f"SDL3-devel-{VERSION}-VC.zip")
DEST = Path(__file__).resolve().parents[2] / "b5-decomp/vendor/sdl3"
REQUIRED = ("include/SDL3/SDL.h", "lib/x64/SDL3.lib", "lib/x64/SDL3.dll",
            "cmake/SDL3Config.cmake", "LICENSE.txt")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    stamp = DEST / "VERSION.txt"
    if (not args.force and stamp.exists() and stamp.read_text().strip() == VERSION
            and all((DEST / name).is_file() for name in REQUIRED)):
        print(f"SDL3 {VERSION} already present in {DEST}")
        return 0
    with tempfile.TemporaryDirectory(prefix="brn_sdl3_") as directory:
        stage = Path(directory)
        archive = stage / "sdl3.zip"
        print(f"Downloading SDL3 {VERSION} from libsdl-org/SDL ...", flush=True)
        with urllib.request.urlopen(URL, timeout=120) as response, archive.open("wb") as output:
            shutil.copyfileobj(response, output)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
            raise RuntimeError("SDL3 archive SHA-256 does not match the pinned release")
        unpack = stage / "unpacked"
        with zipfile.ZipFile(archive) as package:
            for name in package.namelist():
                if not (unpack / name).resolve().is_relative_to(unpack.resolve()):
                    raise RuntimeError("SDL3 archive contains an unsafe path")
            package.extractall(unpack)
        source = unpack / f"SDL3-{VERSION}"
        if not all((source / name).is_file() for name in REQUIRED):
            raise RuntimeError("SDL3 package is missing required build/runtime files")
        shutil.copytree(source, DEST, dirs_exist_ok=True)
        stamp.write_text(VERSION + "\n", encoding="ascii")
    print(f"SDL3 {VERSION} installed to {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
