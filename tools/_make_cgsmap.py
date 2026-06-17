#!/usr/bin/env python
"""Generate the binary CgsMapFile the assert/exception call-stack resolver reads.

This is the PC equivalent of the X360 build toolchain's map-generation step: the MSVC linker emits a
TEXT .map (/MAP), but CgsDev::MapFile::MinimalMemoryReader reads a BINARY map (a 16-byte header + an
array of 128-byte records). This converts one to the other.

Record layout (matches CgsDev::MapFile::Record, little-endian for the PC):
    char     macName[120]   function name (from the linker map, truncated to 119 + NUL)
    uint32   mAddress       function RVA   (address - preferred image base; ASLR-independent)
    uint32   muSize         function size  (next function's RVA - this one's)

Header layout (matches CgsDev::MapFile::MapFileHeader on disk, 16 bytes):
    uint32   muRecordCount
    uint32   recordArrayOffset   (= 16; records follow the header)
    uint32   mBaseAddress        (= 0; records are RVAs, so the reader's rebase target base is 0)
    uint32   meVersion           (= 1, E_VERSION_CURRENT)

Usage: py _make_cgsmap.py <in.map> <out.cgsmap>
"""

import ctypes
import re
import struct
import sys

KI_NAME_LENGTH    = 120
E_VERSION_CURRENT = 1

# Turn the linker's decorated (mangled) C++ names into readable ones, e.g.
#   ?HandleAssert@Manager@Assert@CgsDev@@QEAAXPEBD0H@Z -> CgsDev::Assert::Manager::HandleAssert
# A function map should carry readable names (the X360 map tool's equivalent), and the debug vector font
# has no '@' glyph, so the raw decorated form renders as garbage. UNDNAME_NAME_ONLY (0x1000) drops the
# return type / parameters / calling convention so the result stays short (fits the 120-char record).
_UNDNAME_NAME_ONLY = 0x1000
try:
    _UnDecorateSymbolName = ctypes.WinDLL("dbghelp").UnDecorateSymbolName  # ANSI (base name, no 'A' suffix)
    _UnDecorateSymbolName.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint]
    _UnDecorateSymbolName.restype = ctypes.c_uint
except (OSError, AttributeError):
    _UnDecorateSymbolName = None


def demangle(name):
    # Only MSVC-decorated names start with '?'; leave C symbols (WinMain, etc.) untouched.
    if not name.startswith("?") or _UnDecorateSymbolName is None:
        return name
    buf = ctypes.create_string_buffer(512)
    n = _UnDecorateSymbolName(name.encode("ascii", "replace"), buf, 512, _UNDNAME_NAME_ONLY)
    if n > 0 and buf.value:
        return buf.value.decode("ascii", "replace")
    return name


def parse_map(path):
    preferred_base = 0
    records = []          # (rva, name)
    in_publics = False

    with open(path, "r", errors="replace") as f:
        for line in f:
            if preferred_base == 0:
                m = re.search(r"Preferred load address is\s+([0-9A-Fa-f]+)", line)
                if m:
                    preferred_base = int(m.group(1), 16)
                    continue

            if "Publics by Value" in line or "Static symbols" in line:
                in_publics = True
                continue
            if not in_publics:
                continue

            # A symbol line: "0001:00000000  <name>  <rva+base>  f  <lib:obj>".
            parts = line.split()
            if len(parts) < 4 or ":" not in parts[0]:
                continue
            # parts[3] == 'f' marks a function (FUNC); skip data symbols so ranges are code-only.
            if parts[3] != "f":
                continue
            try:
                rva_base = int(parts[2], 16)
            except ValueError:
                continue

            rva = rva_base - preferred_base
            if 0 <= rva < (1 << 32):
                records.append((rva, parts[1]))

    return records


def build_records(records):
    # Sort by RVA, drop aliases at the same RVA (keep the first), then size = next RVA - this RVA.
    records.sort(key=lambda r: r[0])
    uniq = []
    last_rva = None
    for rva, name in records:
        if rva != last_rva:
            uniq.append((rva, demangle(name)))
            last_rva = rva

    out = []
    for i, (rva, name) in enumerate(uniq):
        size = (uniq[i + 1][0] - rva) if i + 1 < len(uniq) else 0x1000
        if size <= 0:
            size = 1
        out.append((rva, size, name))
    return out


def write_cgsmap(path, records):
    with open(path, "wb") as f:
        f.write(struct.pack("<IIII", len(records), 16, 0, E_VERSION_CURRENT))
        for rva, size, name in records:
            name_bytes = name.encode("ascii", "replace")[: KI_NAME_LENGTH - 1]
            f.write(name_bytes.ljust(KI_NAME_LENGTH, b"\x00"))
            f.write(struct.pack("<II", rva & 0xFFFFFFFF, size & 0xFFFFFFFF))


def main():
    if len(sys.argv) != 3:
        print("usage: _make_cgsmap.py <in.map> <out.cgsmap>")
        return 1
    in_path, out_path = sys.argv[1], sys.argv[2]
    try:
        records = build_records(parse_map(in_path))
    except OSError as e:
        print("cgsmap: cannot read %s (%s) - writing empty map" % (in_path, e))
        records = []
    write_cgsmap(out_path, records)
    print("cgsmap: wrote %d records -> %s" % (len(records), out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
