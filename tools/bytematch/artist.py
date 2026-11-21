"""The console side of a byte match: ARTIST's functions, their extents and their bytes.

Names come from the packed export pack `progress/asmaudit_artist.json.gz` (one row per
function the IDA export of BURNOUT_X360_ARTIST.XEX knows). Extents come from the
image's own `.pdata` (packed unwind records give each framed function's exact length)
and, for frameless leaves that have no record, from the export's instruction count.
Bytes come from the local image through `tools/re/x360rd.py`, a local input that never
leaves the machine: only names, addresses and sizes reach the committed ledger.
"""
from __future__ import annotations

import ctypes
import gzip
import json
import os
from pathlib import Path
import struct
import sys

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "progress" / "asmaudit_artist.json.gz"
UNIDENTIFIED = REPO / "progress" / "unidentified.json"
SOURCE_ALIASES = REPO / "progress" / "source_aliases.json"

# Image layout of BURNOUT_X360_ARTIST.XEX (the same constants the native branch's
# tools/x360/count_matches.py validated against its strict-linked census).
PDATA_START, PDATA_END = 0x821BB000, 0x821ED960
TEXT_START, TEXT_END = 0x821F0000, 0x82C775D0


def packed_extents(pdata: bytes, start=TEXT_START, end=TEXT_END):
    """{function address: byte length} for the standard two-word PPC .pdata records."""
    entries = list(struct.iter_unpack(">II", pdata))
    sizes = {}
    for index, (address, flags) in enumerate(entries):
        length = ((flags >> 8) & 0x3FFFFF) * 4
        following = entries[index + 1][0] if index + 1 < len(entries) else end
        if flags >> 30 == 1 and address % 4 == 0 and length:
            if start <= address < address + length <= min(following, end):
                sizes[address] = length
    return sizes


def load_pack(path=PACK, *, aliases_path=SOURCE_ALIASES):
    """Read exported names and apply opted-in aliases at their attested addresses."""
    with open(path, "rb") as fh:
        functions = json.loads(gzip.decompress(fh.read()))["functions"]
    if aliases_path.is_file():
        with aliases_path.open(encoding="utf-8") as fh:
            registry = json.load(fh)
        aliases = registry.get("functions", {}) | registry.get("xdk_functions", {})
        for exported_name, proof in aliases.items():
            if proof.get("byte_match") is not True:
                continue
            address = f"0x{int(proof['x360_address'], 16):08X}"
            row = functions.get(address)
            if row and row["name"] == exported_name:
                row["name"] = proof["symbol"]
    return functions


def load_unidentified(path=UNIDENTIFIED):
    """The ledger's functions without a name (tools/work/build_unidentified.py).

    The export pack's own `unnamed` flag is not this: it is set on thousands of properly
    named functions, so pairing must never key on it.
    """
    if not Path(path).is_file():
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {int(row["addr"], 16) for row in data.get("functions", [])}


def normal_name(name: str) -> str:
    """The form both demanglers agree on: no spaces."""
    return name.replace(" ", "")


_UNDNAME = None


def demangle(symbol: str) -> str:
    """Qualified name only (`Ns::Class::method`) for an MSVC decorated name.

    Uses dbghelp's UnDecorateSymbolName (UNDNAME_NAME_ONLY), the same call the native
    branch's census pairs names with. Plain C names come back unchanged; off Windows the
    decorated name is returned as is.
    """
    global _UNDNAME
    if not symbol.startswith("?"):
        return symbol
    if _UNDNAME is None:
        try:
            fn = ctypes.WinDLL("dbghelp").UnDecorateSymbolName
            fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint]
            _UNDNAME = fn
        except (AttributeError, OSError):
            _UNDNAME = False
    if not _UNDNAME:
        return symbol
    buffer = ctypes.create_string_buffer(8192)
    if not _UNDNAME(symbol.encode("latin-1"), buffer, len(buffer), 0x1000):
        return symbol
    return buffer.value.decode("latin-1")


class Artist:
    """Names, extents and (lazily) bytes of every ARTIST function."""

    def __init__(self, pack=None, read=None, unidentified=None):
        self.pack = pack if pack is not None else load_pack()
        self._read = read
        if unidentified is None and pack is None:
            unidentified = load_unidentified()
        self.names = {}          # address -> name
        self.unnamed = set()
        self.ida_size = {}
        for text, row in self.pack.items():
            address = int(text, 16)
            self.names[address] = row["name"]
            self.ida_size[address] = 4 * int(row.get("n") or 0)
            # unnamed: the ledger's unidentified set when known, else an IDA placeholder name
            if (address in unidentified) if unidentified is not None else row["name"].startswith("sub_"):
                self.unnamed.add(address)
        self.by_name = {}
        for address, name in self.names.items():
            if address not in self.unnamed:
                self.by_name.setdefault(normal_name(name), []).append(address)
        self._extents = None
        self._trimmed = {}

    # -- bytes ------------------------------------------------------------------------
    @property
    def read(self):
        if self._read is None:
            sys.path.insert(0, str(REPO / "tools" / "re"))
            import x360rd  # noqa: E402  (local input: the ARTIST image)
            self._read = x360rd.rd
        return self._read

    def bytes(self, address: int, length: int) -> bytes:
        text = self._text
        if text is not None and TEXT_START <= address and address + length <= TEXT_END:
            return text[address - TEXT_START:address - TEXT_START + length]
        return self.read(address, length)

    _text = None

    def preload(self):
        """Read the whole .text once (about 13 s); every later read of code is a slice."""
        if self._text is None:
            self._text = self.read(TEXT_START, TEXT_END - TEXT_START)
        return self

    # -- extents ----------------------------------------------------------------------
    @property
    def extents(self):
        if self._extents is None:
            self._extents = packed_extents(self.read(PDATA_START, PDATA_END - PDATA_START))
        return self._extents

    def size(self, address: int):
        """(byte length, source): the .pdata length, else the export's instruction count.

        IDA counts the alignment padding after a frameless leaf (zero words) as part of it,
        so an IDA-derived length drops its trailing zero words; a .pdata length is exact.
        """
        if address in self.extents:
            return self.extents[address], "pdata"
        size = self.ida_size.get(address) or 0
        if not size:
            return 0, "none"
        trimmed = self._trimmed.get(address)
        if trimmed is None:
            try:
                data = self.bytes(address, size)
            except KeyError:
                data = b""
            trimmed = size
            while trimmed > 4 and data[trimmed - 4:trimmed] == b"\0\0\0\0":
                trimmed -= 4
            self._trimmed[address] = trimmed
        return trimmed, "ida"

    def name_at(self, address: int):
        name = self.names.get(address)
        return None if name is None or address in self.unnamed else name
