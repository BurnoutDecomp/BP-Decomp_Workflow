"""The console side of a byte match: ARTIST's functions, their extents and their bytes.

Names come from the packed export pack `progress/asmaudit_artist.json.gz` (one row per
function the IDA export of BURNOUT_X360_ARTIST.XEX knows). Extents come from the
image's own `.pdata` (packed unwind records give each framed function's exact length)
and, for frameless leaves that have no record, from the export's instruction count.
The census also includes disjoint unwind extents and attested leaf functions absent
from that export.
Bytes come from the local image through `tools/re/x360rd.py`, a local input that never
leaves the machine: only names, addresses and sizes reach the committed ledger.
"""
from __future__ import annotations

from bisect import bisect_right
import ctypes
import gzip
from itertools import accumulate
import json
import os
from pathlib import Path
import struct
import sys

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "progress" / "asmaudit_artist.json.gz"
UNIDENTIFIED = REPO / "progress" / "unidentified.json"
SOURCE_ALIASES = REPO / "progress" / "source_aliases.json"

# Image layout of BURNOUT_X360_ARTIST.XEX. Packed unwind records also cover the
# executable codec sections after the primary text segment.
PDATA_START, PDATA_END = 0x821BB000, 0x821ED960
TEXT_START, PRIMARY_TEXT_END = 0x821F0000, 0x82C775D0
TEXT_END = 0x82CCFE7C


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


def disjoint_extents(occupied, candidates):
    """Yield candidate intervals that do not overlap the occupied intervals."""
    starts = sorted(occupied)
    max_ends = list(accumulate((start + occupied[start] for start in starts), max))
    for address, length in candidates:
        index = bisect_right(starts, address)
        if address in occupied or (index and max_ends[index - 1] > address):
            continue
        if index < len(starts) and starts[index] < address + length:
            continue
        yield address, length


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
        for address, proof in registry.get("folded_functions", {}).items():
            row = functions.get(address)
            if row and row["name"] == proof["exported_name"]:
                row["folded_names"] = tuple(proof["aliases"])
        for address, proof in registry.get("identified_functions", {}).items():
            row = functions.get(address)
            exported = row["name"] if row is not None else None
            if exported == proof["exported_name"]:
                functions.setdefault(address, {"unlisted": True})["identity"] = (
                    proof["symbol"], proof["size"], proof.get("tu"),
                )
        for kind in ("sdk_leaf", "native_leaf"):
            for address, proof in registry.get(f"{kind}_functions", {}).items():
                if "previous_size" in proof:
                    row = functions.get(address)
                    if kind == "native_leaf" and row and row.get("name") == proof["symbol"]:
                        row[kind] = proof
                else:
                    functions.setdefault(address, {"unlisted": True, kind: proof})
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
        self.folded_names = {}   # verified call targets sharing a linked body
        self.identified_tus = {}  # optional ledger placement for recovered identities
        self.unnamed = set()
        self.ida_size = {}
        self.sdk_leaves = {}
        self.leaf_extents = {}
        self._extents = None
        self._trimmed = {}
        identities = {}
        leaves = {}
        for text, row in self.pack.items():
            address = int(text, 16)
            if "identity" in row:
                identities[address] = row["identity"]
            if "sdk_leaf" in row:
                leaves[address] = ("sdk_leaf", row["sdk_leaf"])
            elif "native_leaf" in row:
                leaves[address] = ("native_leaf", row["native_leaf"])
            if row.get("unlisted"):
                continue
            self.names[address] = row["name"]
            if row.get("folded_names"):
                self.folded_names[address] = {normal_name(name) for name in row["folded_names"]}
            self.ida_size[address] = 4 * int(row.get("n") or 0)
            # unnamed: the ledger's unidentified set when known, else an IDA placeholder name
            if (address in unidentified) if unidentified is not None else row["name"].startswith("sub_"):
                self.unnamed.add(address)
        # A name recovered for an export gap must already belong to a disjoint unwind
        # extent. The evidence supplies an identity, and does not add code to the census.
        unlisted = identities.keys() - self.names.keys()
        if unlisted:
            self.include_unlisted_unwind_functions(unlisted)
        for address, (name, length, tu) in identities.items():
            if address in self.unnamed and self.size(address)[0] == length:
                self.names[address] = name
                self.unnamed.remove(address)
                if tu is not None:
                    self.identified_tus[address] = tu
        if leaves:
            self._include_leaves(leaves)
        self.by_name = {}
        for address, name in self.names.items():
            if address not in self.unnamed:
                self.by_name.setdefault(normal_name(name), []).append(address)

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
        if text is not None and TEXT_START <= address and address + length <= PRIMARY_TEXT_END:
            return text[address - TEXT_START:address - TEXT_START + length]
        return self.read(address, length)

    _text = None

    def preload(self):
        """Cache the contiguous primary text segment. Read the codec segments on demand."""
        if self._text is None:
            self._text = self.read(TEXT_START, PRIMARY_TEXT_END - TEXT_START)
        return self

    # -- extents ----------------------------------------------------------------------
    @property
    def extents(self):
        if self._extents is None:
            self._extents = packed_extents(self.read(PDATA_START, PDATA_END - PDATA_START))
        return self._extents

    def include_unlisted_unwind_functions(self, addresses=None):
        """Include disjoint function extents missing from the name export in the census."""
        occupied = {address: self.size(address)[0] for address in self.names}
        extents = self.extents
        entries = extents.items() if addresses is None else ((address, extents[address]) for address in addresses if address in extents)
        for address, _ in disjoint_extents(occupied, entries):
            self.names[address] = f"sub_{address:08X}"
            self.unnamed.add(address)

    def _include_leaves(self, proofs):
        """Recover leaf entries and omitted tails using branches into image gaps."""
        from compare import branch_target

        occupied = self.extents | {address: self.size(address)[0] for address in self.names}
        candidates = []
        for address, (kind, proof) in proofs.items():
            previous = proof.get("previous_size", 0)
            if previous and self.size(address) != (previous, "ida"):
                raise ValueError(f"Native leaf extent at {address:08X} no longer agrees with the export")
            candidates.append((address + previous, address, kind, proof))
        available = dict(disjoint_extents(occupied, ((start, address + p["size"] - start)
                                                     for start, address, _, p in candidates)))
        end = TEXT_START
        for start, address, kind, proof in sorted(candidates):
            size = proof["size"]
            extending = start != address
            label = "SDK leaf" if kind == "sdk_leaf" else "native leaf"
            if (start not in available or start < end or address % 4 or address + size <= start
                    or size % 4 or address + size > TEXT_END):
                raise ValueError(f"Invalid or overlapping {label} extent at {address:08X}")
            caller, site = int(proof["caller"], 16), int(proof["call_site"], 16)
            if (site % 4 or not caller <= site <= caller + occupied.get(caller, 0) - 4
                    or (extending and caller != address)):
                raise ValueError(f"{label} {address:08X} has a witness outside its caller")
            word, = struct.unpack(">I", self.bytes(site, 4))
            opcode = word >> 26
            target = branch_target(word, site, 0x03FFFFFC if opcode == 18 else 0x0000FFFC)
            if (extending and (opcode not in (16, 18) or not start <= target < address + size)
                    or not extending and (opcode != 18 or target != address)):
                raise ValueError(f"{label} {address:08X} has no matching branch at {site:08X}")
            self.names[address] = proof["symbol"]
            self.leaf_extents[address] = (size, kind)
            if kind == "sdk_leaf":
                self.sdk_leaves[address] = proof
            if "tu" in proof:
                self.identified_tus[address] = proof["tu"]
            end = address + size

    def size(self, address: int):
        """(byte length, source) from .pdata, an attested leaf, or the export.

        IDA counts the alignment padding after a frameless leaf (zero words) as part of it,
        so an IDA-derived length drops its trailing zero words; a .pdata length is exact.
        """
        if address in self.extents:
            return self.extents[address], "pdata"
        if address in self.leaf_extents:
            return self.leaf_extents[address]
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

    def matches_name(self, address: int, name: str):
        original = self.name_at(address)
        if original is None:
            return False
        normalized = normal_name(name)
        return normalized == normal_name(original) or normalized in self.folded_names.get(address, ())
