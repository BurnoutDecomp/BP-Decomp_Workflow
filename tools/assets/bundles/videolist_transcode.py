#!/usr/bin/env python3
"""Convert an X360 VIDEOLIST.BUNDLE to the native x64 VideoData layout.

The container-only converter cannot handle resource type 0x42: it leaves each
X360 VideoData resource as six 12-byte, big-endian records. The PC runtime expects
six 16-byte records containing little-endian 64-bit self-relative name pointers.
"""

from __future__ import annotations

import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
YAP = ROOT / "build" / "tools" / "yap" / "YAP.exe"
LANGUAGE_COUNT = 6
X360_STRIDE = 12
X64_STRIDE = 16


def run(argv: list[str]) -> None:
    result = subprocess.run(argv, capture_output=True, text=True)
    if result.returncode:
        sys.stderr.write((result.stdout or "") + (result.stderr or ""))
        raise RuntimeError(f"command failed ({result.returncode}): {argv[0]}")


def read_c_string(data: bytes, offset: int, source: Path) -> bytes:
    if offset < LANGUAGE_COUNT * X360_STRIDE or offset >= len(data):
        raise ValueError(f"{source}: name offset 0x{offset:X} is outside the resource")
    end = data.find(b"\0", offset)
    if end < 0:
        raise ValueError(f"{source}: unterminated video name at 0x{offset:X}")
    name = data[offset:end]
    if not name:
        raise ValueError(f"{source}: empty video name at 0x{offset:X}")
    return name


def transcode_resource(source: Path) -> None:
    data = source.read_bytes()
    if len(data) < LANGUAGE_COUNT * X360_STRIDE:
        raise ValueError(f"{source}: resource is too small ({len(data)} bytes)")

    names: list[bytes] = []
    flags: list[bytes] = []
    for index in range(LANGUAGE_COUNT):
        base = index * X360_STRIDE
        relative = struct.unpack_from(">I", data, base)[0]
        names.append(read_c_string(data, base + relative, source))
        flags.append(data[base + 4 : base + 10])

    # Store each distinct name once. Self-relative pointers allow every language
    # entry to share it without changing the represented data.
    output = bytearray(LANGUAGE_COUNT * X64_STRIDE)
    name_offsets: dict[bytes, int] = {}
    for name in names:
        if name in name_offsets:
            continue
        name_offsets[name] = len(output)
        output.extend(name)
        output.append(0)
        while len(output) & 3:
            output.append(0)

    for index, (name, available) in enumerate(zip(names, flags)):
        base = index * X64_STRIDE
        struct.pack_into("<Q", output, base, name_offsets[name] - base)
        output[base + 8 : base + 14] = available

    source.write_bytes(output)


def convert(input_bundle: Path, output_bundle: Path) -> None:
    if not YAP.is_file():
        raise FileNotFoundError(f"YAP was not found at {YAP}")

    work = Path(tempfile.mkdtemp(prefix="videolist_"))
    try:
        extracted = work / "extracted"
        run([str(YAP), "e", str(input_bundle), str(extracted)])

        resources = sorted((extracted / "VideoData").glob("*.dat"))
        if not resources:
            raise ValueError("VIDEOLIST contains no VideoData resources")
        for resource in resources:
            transcode_resource(resource)

        meta = extracted / ".meta.yaml"
        metadata = meta.read_text(encoding="utf-8")
        if "platform: 2" not in metadata:
            raise ValueError("input bundle is not an X360 platform-2 bundle")
        metadata = metadata.replace("platform: 2", "platform: 4", 1)
        metadata = metadata.replace("compressed: true", "compressed: false", 1)
        meta.write_text(metadata, encoding="utf-8")

        output_bundle.parent.mkdir(parents=True, exist_ok=True)
        run([str(YAP), "c", str(extracted), str(output_bundle)])
        print(f"{input_bundle.name}: transcoded {len(resources)} VideoData resources")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {Path(sys.argv[0]).name} IN_X360_BUNDLE OUT_PC_BUNDLE", file=sys.stderr)
        return 2
    convert(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
