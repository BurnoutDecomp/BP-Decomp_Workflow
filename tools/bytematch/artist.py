"""The console side of a byte match: ARTIST's functions, their extents and their bytes.

Names come from the packed export pack `progress/asmaudit_artist.json.gz` (one row per
function the IDA export of BURNOUT_X360_ARTIST.XEX knows). Extents come from the
image's own `.pdata` (packed unwind records give each framed function's exact length)
and, for frameless leaves, from the export's instruction count or other evidence such
as the CRT initializer table.
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
RDATA_START, RDATA_END = 0x82000600, 0x821BAE78
TEXT_START, PRIMARY_TEXT_END = 0x821F0000, 0x82C775D0
TEXT_END = 0x82CCFE7C
# _cinit loads these bounds at 0x829346BC and 0x829346C0, then calls each non-null entry.
CRT_INITIALIZERS_START, CRT_INITIALIZERS_END = 0x82CD0010, 0x82CD3D34

# Integer, floating-point and VMX operations seen in the registered leaves.
CRT_LEAF_OPCODES = {4, 5, 6, 14, 15, 24, 32, 36, 48, 52, 59, 62}
# Indexed loads, MSR and SPR access, and load-reserve/store-conditional.
CRT_LEAF_EXTENDED_OPS = {0x7C00040E, 0x7C00044E, 0x7C0000A6, 0x7C000164,
                         0x7C000028, 0x7C00012D, 0x7C0003A6}
BLR = 0x4E800020
BCTR = 0x4E800420


def packed_extents(pdata: bytes, start=TEXT_START, end=TEXT_END, *, record_kind=1):
    """{function address: byte length} for the standard two-word PPC .pdata records."""
    entries = list(struct.iter_unpack(">II", pdata))
    sizes = {}
    for index, (address, flags) in enumerate(entries):
        length = ((flags >> 8) & 0x3FFFFF) * 4
        following = entries[index + 1][0] if index + 1 < len(entries) else end
        if flags >> 30 == record_kind and address % 4 == 0 and length:
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
        xdk_aliases = registry.get("xdk_functions", {})
        aliases = registry.get("functions", {}) | xdk_aliases
        for exported_name, proof in aliases.items():
            # A `functions` alias may also stand on name evidence alone (an assert text, a call
            # from a named caller, a vtable slot), as identified_functions do for unnamed bodies:
            # the export is then compared under its full name and reads as nonmatching until the
            # body matches. XDK aliases always need the byte proof.
            named = exported_name not in xdk_aliases and proof.get("name_evidence") is True
            if proof.get("byte_match") is not True and not named:
                continue
            address = f"0x{int(proof['x360_address'], 16):08X}"
            row = functions.get(address)
            if row and row["name"] == exported_name:
                row["name"] = proof["symbol"]
                if exported_name in xdk_aliases and "sdk_provider" in proof:
                    row["sdk_provider"] = proof["sdk_provider"]
        for address, proof in registry.get("folded_functions", {}).items():
            row = functions.get(address)
            if row and row["name"] == proof["exported_name"]:
                row["folded_names"] = tuple(proof["aliases"])
        for address, proof in registry.get("identified_functions", {}).items():
            row = functions.get(address)
            exported = row["name"] if row is not None else None
            if exported == proof["exported_name"]:
                functions.setdefault(address, {"unlisted": True})["identity"] = (
                    proof["symbol"], proof["size"], proof.get("tu"), proof.get("sdk_provider"),
                )
        for kind in ("sdk_leaf", "native_leaf"):
            for address, proof in registry.get(f"{kind}_functions", {}).items():
                if "previous_size" in proof:
                    row = functions.get(address)
                    exported = proof.get("exported_name", proof["symbol"])
                    if row and row.get("name") == exported and (kind == "native_leaf" or proof["symbol"] == exported):
                        row[kind] = proof
                else:
                    functions.setdefault(address, {"unlisted": True, kind: proof})
        for address, proof in registry.get("sdk_entry_groups", {}).items():
            if not proof["entries"] or functions.get(address, {}).get("name") != proof["entries"][0]:
                raise ValueError(f"SDK entry group {address} no longer agrees with the export")
            functions[address]["sdk_entry_group"] = proof
        for address, proof in registry.get("sdk_archive_splits", {}).items():
            if functions.get(address, {}).get("name") != proof["exported_name"]:
                raise ValueError(f"SDK archive split {address} no longer agrees with the export")
            functions[address]["sdk_archive_split"] = proof
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
_DBGHELP = None
_DBGHELP_NAMES = {}
_DBGHELP_CACHE_LIMIT = 65536


def demangle(symbol: str) -> str:
    """Qualified name only (`Ns::Class::method`) for an MSVC decorated name.

    Uses dbghelp's UnDecorateSymbolName (UNDNAME_NAME_ONLY), the same call the native
    branch's census pairs names with. Plain C names come back unchanged; off Windows the
    decorated name is returned as is.
    """
    global _UNDNAME, _DBGHELP
    if not symbol.startswith("?"):
        return symbol
    if _UNDNAME is None:
        try:
            fn = ctypes.WinDLL("dbghelp").UnDecorateSymbolName
            fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint]
            _UNDNAME = _DBGHELP = fn
            _DBGHELP_NAMES.clear()
        except (AttributeError, OSError):
            _UNDNAME = False
    if not _UNDNAME:
        return symbol
    # Only the native DbgHelp decoder has stable answers. Wine installs its own hook.
    use_cache = _UNDNAME is _DBGHELP
    if use_cache:
        name = _DBGHELP_NAMES.get(symbol)
        if name is not None:
            return name
    buffer = ctypes.create_string_buffer(8192)
    if not _UNDNAME(symbol.encode("latin-1"), buffer, len(buffer), 0x1000):
        return symbol
    name = buffer.value.decode("latin-1")
    if use_cache and len(_DBGHELP_NAMES) < _DBGHELP_CACHE_LIMIT:
        _DBGHELP_NAMES[symbol] = name
    return name


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
        self.identified_addresses = set()
        self.unnamed = set()
        self.ida_size = {}
        self.sdk_leaves = {}
        self.leaf_extents = {}
        self._extents = None
        self._trimmed = {}
        identities = {}
        leaves = {}
        entry_groups = {}
        archive_splits = {}
        for text, row in self.pack.items():
            address = int(text, 16)
            if "identity" in row:
                identities[address] = row["identity"]
            if "sdk_leaf" in row:
                leaves[address] = ("sdk_leaf", row["sdk_leaf"])
            elif "native_leaf" in row:
                leaves[address] = ("native_leaf", row["native_leaf"])
            if "sdk_entry_group" in row:
                entry_groups[address] = row["sdk_entry_group"]
            if "sdk_archive_split" in row:
                archive_splits[address] = row["sdk_archive_split"]
            if row.get("unlisted"):
                continue
            self.names[address] = row["name"]
            if "sdk_provider" in row:
                self.sdk_leaves[address] = row["sdk_provider"]
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
        for address, (name, length, tu, sdk_provider) in identities.items():
            if address in self.unnamed and self.size(address)[0] == length:
                self.names[address] = name
                self.unnamed.remove(address)
                self.identified_addresses.add(address)
                if tu is not None:
                    self.identified_tus[address] = tu
                if sdk_provider is not None:
                    self.sdk_leaves[address] = sdk_provider
        if leaves:
            self._include_leaves(leaves)
        if entry_groups:
            self._split_sdk_entry_groups(entry_groups)
        if archive_splits:
            self._split_sdk_archive_extents(archive_splits)
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

    def include_unlisted_exception_functions(self):
        """Recover disjoint primary bodies from the XDK's kind-3 unwind records."""
        pdata = self.bytes(PDATA_START, PDATA_END - PDATA_START)
        occupied = self.extents | {address: self.size(address)[0] for address in self.names}
        for address, size in disjoint_extents(occupied, packed_extents(pdata, record_kind=3).items()):
            self.names[address] = f"sub_{address:08X}"
            self.unnamed.add(address)
            self.leaf_extents[address] = (size, "exception_pdata")

    def include_unlisted_crt_leaves(self):
        """Catalogue registered leaves whose entire extent is readable."""
        occupied = self.extents | {address: self.size(address)[0] for address in self.names}
        for address, size in self._crt_leaf_extents(occupied):
            self.names[address] = f"sub_{address:08X}"
            self.unnamed.add(address)
            self.leaf_extents[address] = (size, "crt_leaf")

    def is_crt_initializer(self, address, slot):
        return (slot % 4 == 0 and CRT_INITIALIZERS_START <= slot < CRT_INITIALIZERS_END
                and struct.unpack(">I", self.bytes(slot, 4))[0] == address)

    def _crt_leaf_extents(self, occupied):
        from compare import branch_target

        table = self.bytes(CRT_INITIALIZERS_START, CRT_INITIALIZERS_END - CRT_INITIALIZERS_START)
        entries = {address for (address,) in struct.iter_unpack(">I", table)
                   if TEXT_START <= address < PRIMARY_TEXT_END and address % 4 == 0}
        starts = sorted(entries | {address for address in occupied if address < PRIMARY_TEXT_END}
                        | {PRIMARY_TEXT_END})
        occupied_end = TEXT_START
        for address, following in zip(starts, starts[1:]):
            if address in occupied:
                occupied_end = max(occupied_end, address + occupied[address])
                continue
            if address < occupied_end:
                continue
            words = [word for (word,) in struct.iter_unpack(">I", self.bytes(address, following - address))]
            while words and words[-1] == 0:
                words.pop()
            if not words:
                continue
            end = address + 4 * len(words)
            last = words[-1]
            if last != BLR and (last & 0xFC000003 != 0x48000000
                               or not occupied.get(branch_target(last, end - 4, 0x03FFFFFC))):
                continue
            if any(
                word >> 26 not in CRT_LEAF_OPCODES
                and word & 0xFC0007FF not in CRT_LEAF_EXTENDED_OPS
                and not (word & 0xFC000003 == 0x40000000
                         and address <= branch_target(word, address + 4 * index, 0xFFFC) < end)
                for index, word in enumerate(words[:-1])
            ):
                continue
            yield address, end - address

    def _include_leaves(self, proofs):
        """Recover leaf entries and omitted tails using references into image gaps."""
        occupied = self.extents | {address: self.size(address)[0] for address in self.names}
        candidates = []
        for address, (kind, proof) in proofs.items():
            previous = proof.get("previous_size", 0)
            if previous and self.size(address) != (previous, "ida"):
                label = "SDK leaf" if kind == "sdk_leaf" else "native leaf"
                raise ValueError(f"{label} extent at {address:08X} no longer agrees with the export")
            if "fragments" in proof:
                if kind != "sdk_leaf":
                    raise ValueError(f"Only SDK archive bodies can subsume fragments at {address:08X}")
                self._remove_sdk_fragments(address, proof, occupied)
            candidates.append((address + previous, address, kind, proof))
        available = dict(disjoint_extents(occupied, ((start, address + p["size"] - start)
                                                     for start, address, _, p in candidates)))
        end = TEXT_START
        pending = sorted(candidates)
        for start, address, kind, proof in pending:
            size = proof["size"]
            label = "SDK leaf" if kind == "sdk_leaf" else "native leaf"
            if (start not in available or start < end or address % 4 or address + size <= start
                    or size % 4 or address + size > TEXT_END):
                raise ValueError(f"Invalid or overlapping {label} extent at {address:08X}")
            end = address + size

        if any("crt_slot" in proof for _, _, _, proof in pending):
            known = occupied | {address: proof["size"] for _, address, _, proof in pending
                                if "crt_slot" not in proof}
            crt_sizes = dict(self._crt_leaf_extents(known))
            for start, address, _, proof in pending:
                if "crt_slot" not in proof:
                    continue
                slot = int(proof["crt_slot"], 16)
                if (start != address or crt_sizes.get(address) != proof["size"]
                        or not self.is_crt_initializer(address, slot)):
                    raise ValueError(f"CRT leaf {address:08X} has no matching registration and extent")

        while pending:
            deferred = []
            for start, address, kind, proof in pending:
                if (not {"crt_slot", "vtable_slots", "function_table_slots", "data_table_slot", "fallthrough"}
                        & proof.keys() and int(proof["caller"], 16) not in occupied):
                    deferred.append((start, address, kind, proof))
                    continue
                self._add_witnessed_leaf(occupied, start, address, kind, proof)
            if len(deferred) == len(pending):
                address = deferred[0][1]
                raise ValueError(f"Leaf {address:08X} has no independently witnessed caller extent")
            pending = deferred

    def _remove_sdk_fragments(self, address, proof, occupied):
        """Remove previously unnamed extents contained in a whole archive body."""
        end = address + proof["size"]
        for fragment in proof["fragments"]:
            start = int(fragment["address"], 16)
            size = fragment["size"]
            if (not address < start < start + size <= end or occupied.get(start) != size
                    or (start in self.names and start not in self.unnamed)):
                raise ValueError(f"SDK fragment {start:08X} does not match an unnamed contained extent")
            del occupied[start]
            self.names.pop(start, None)
            self.unnamed.discard(start)

    def _add_witnessed_leaf(self, occupied, start, address, kind, proof):
        size = proof["size"]
        label = "SDK leaf" if kind == "sdk_leaf" else "native leaf"
        table_slots = proof.get("function_table_slots", proof.get("vtable_slots"))
        if "archive_unwind_records" in proof:
            if (kind != "sdk_leaf" or start == address or not proof.get("fragments")
                    or any(key in proof for key in ("function_table_slots", "vtable_slots", "data_table_slot",
                                                    "crt_slot", "table_entry", "archive_switch_case"))
                    or not self._matches_sdk_unwind_tail(address, start, address + size, proof)):
                raise ValueError(f"{label} {address:08X} has no matching archive unwind tail")
            if "refhi_site" in proof:
                self._check_leaf_address(occupied, address, address, proof)
            else:
                self._check_leaf_branch(proof, occupied, label, address, address, address + size)
        elif table_slots is not None:
            slots = [int(slot, 16) for slot in table_slots]
            if (start != address or not slots or not all(
                    slot % 4 == 0 and RDATA_START <= slot <= RDATA_END - 4
                    and struct.unpack(">I", self.bytes(slot, 4))[0] == address for slot in slots)):
                table_kind = "function table" if "function_table_slots" in proof else "vtable"
                raise ValueError(f"{label} {address:08X} has no matching {table_kind} witness")
        elif "data_table_slot" in proof:
            table = proof["data_table_slot"]
            offset = table["offset"]
            slot = int(table["address"], 16) + offset
            if (kind != "sdk_leaf" or start != address or offset < 0 or offset % 4 or slot % 4
                    or self.bytes(slot, 4) != struct.pack(">I", address)):
                raise ValueError(f"{label} {address:08X} has no matching data table witness")
        elif "fallthrough" in proof:
            if (kind != "native_leaf" or start == address
                    or not self._falls_into_tail(occupied, address, start, address + size)):
                raise ValueError(f"{label} {address:08X} does not fall through into its omitted tail")
        elif "refhi_site" in proof:
            self._check_leaf_address(occupied, start, address, proof)
        elif "crt_slot" not in proof:
            self._check_leaf_branch(proof, occupied, label, address, start, address + size)
        self.names[address] = proof["symbol"]
        self.unnamed.discard(address)
        self.leaf_extents[address] = (size, "crt_leaf" if "crt_slot" in proof else kind)
        if kind == "native_leaf":
            self.identified_addresses.add(address)
        if kind == "sdk_leaf":
            self.sdk_leaves[address] = proof
            if proof.get("archive_aliases"):
                self.folded_names.setdefault(address, set()).update(
                    normal_name(demangle(alias)) for alias in proof["archive_aliases"])
        if "tu" in proof:
            self.identified_tus[address] = proof["tu"]
        occupied[address] = size

    def _matches_sdk_unwind_tail(self, address, tail, end, proof):
        """Bind a primary exception body and its complete attached funclets to ARTIST."""
        records = proof["archive_unwind_records"]
        if len(records) < 2:
            return False

        described = []
        cursor = address
        for index, record in enumerate(records):
            flags = int(record["flags"], 16)
            record_start = address + record["offset"]
            size = ((flags >> 8) & 0x3FFFFF) * 4
            expected_kind = 3 if index == 0 else 1
            if (record_start != cursor or flags >> 30 != expected_kind or not size
                    or cursor + size > end or (index == 0 and cursor + size != tail)):
                return False
            described.append((record_start, flags))
            cursor += size
        if cursor != end:
            return False

        funclets = {(start, start + ((flags >> 8) & 0x3FFFFF) * 4) for start, flags in described[1:]}
        fragments = {(int(fragment["address"], 16), int(fragment["address"], 16) + fragment["size"])
                     for fragment in proof["fragments"]}
        if not funclets <= fragments or any(
                not any(funclet <= start < finish <= funclet_end for funclet, funclet_end in funclets)
                for start, finish in fragments):
            return False

        linked = [record for record in struct.iter_unpack(">II", self.bytes(PDATA_START, PDATA_END - PDATA_START))
                  if address <= record[0] < end]
        return linked == described

    def _falls_into_tail(self, occupied, address, tail, end):
        """Check that a clipped export's last kept instruction runs straight on into its omitted tail.

        The instruction before the tail must be able to fall through (no blr, bctr or b), the tail
        must hold no zero word and end with one of those unconditional transfers, every tail
        instruction that follows an unconditional transfer must be a branch or jump-table target from
        inside the extent, and the extent must stop at alignment padding or at the next known
        function, so the tail cannot be a neighbour.
        """
        from compare import branch_target

        def unconditional(word):
            return word in (BLR, BCTR) or (word >> 26 == 18 and not word & 1)

        body = [word for (word,) in struct.iter_unpack(">I", self.bytes(address, end - address))]
        targets = set(body)
        for index, word in enumerate(body):
            if word >> 26 in (16, 18) and not word & 2:
                targets.add(branch_target(word, address + 4 * index, 0x03FFFFFC if word >> 26 == 18 else 0x0000FFFC))
        cut = (tail - address) // 4
        words = body[cut:]
        last = body[cut - 1]
        if not words or not last or unconditional(last) or not all(words) or not unconditional(words[-1]):
            return False
        if any(unconditional(body[index - 1]) and address + 4 * index not in targets
               for index in range(cut + 1, len(body))):
            return False
        following = self.bytes(end, 4) if end < TEXT_END else b"\0\0\0\0"
        return following == b"\0\0\0\0" or end in occupied

    def _check_leaf_address(self, occupied, start, address, proof):
        from compare import refhi_lo_address

        caller = int(proof["caller"], 16)
        high_site, low_site = int(proof["refhi_site"], 16), int(proof["reflo_site"], 16)
        if (start != address or high_site % 4 or low_site % 4
                or not caller <= high_site < low_site <= caller + occupied[caller] - 4):
            raise ValueError(f"Leaf {address:08X} has an address witness outside its caller extent")
        high, = struct.unpack(">I", self.bytes(high_site, 4))
        low, = struct.unpack(">I", self.bytes(low_site, 4))
        if (high & 0xFC1F0000 != 0x3C000000 or low >> 26 != 14
                or (high >> 21) & 31 != (low >> 16) & 31 or refhi_lo_address(high, low) != address):
            raise ValueError(f"Leaf {address:08X} has no matching address witness")

    def _check_leaf_branch(self, proof, occupied, label, address, start, end):
        from compare import branch_target

        extending = start != address
        caller, site = int(proof["caller"], 16), int(proof["call_site"], 16)
        if (site % 4 or not caller <= site <= caller + occupied.get(caller, 0) - 4
                or (extending and caller != address)):
            raise ValueError(f"{label} {address:08X} has a witness outside its caller")
        if "table_entry" in proof:
            entry = int(proof["table_entry"], 16)
            if not extending:
                raise ValueError(f"{label} {address:08X} has no matching switch table at {site:08X}")
            if "archive_switch_case" in proof:
                reaches_tail = (label == "SDK leaf" and self._archive_switch_reaches_tail(
                    caller, site, entry, start, end, proof["archive_switch_case"]))
            else:
                reaches_tail = self._switch_reaches_tail(caller, site, entry, start, end)
            if not reaches_tail:
                raise ValueError(f"{label} {address:08X} has no matching switch table at {site:08X}")
        else:
            word, = struct.unpack(">I", self.bytes(site, 4))
            opcode = word >> 26
            target = branch_target(word, site, 0x03FFFFFC if opcode == 18 else 0x0000FFFC)
            if (extending and (opcode not in (16, 18) or not start <= target < end)
                    or not extending and (opcode != 18 or target != address)):
                raise ValueError(f"{label} {address:08X} has no matching branch at {site:08X}")

    def _split_sdk_entry_groups(self, groups):
        """Split a single exported extent into disjoint archive entry ranges."""
        occupied = self.extents | {address: self.size(address)[0] for address in self.names}
        for address, proof in sorted(groups.items()):
            names, size = proof["entries"], proof["entry_size"]
            length = len(names) * size
            if (len(names) < 2 or len(set(names)) != len(names) or size <= 0 or size % 4
                    or self.names.get(address) != names[0] or self.size(address) != (length, "ida")):
                raise ValueError(f"SDK entry group {address:08X} does not match its exported extent")
            del occupied[address]
            if next(disjoint_extents(occupied, [(address, length)]), None) is None:
                raise ValueError(f"SDK entry group {address:08X} overlaps another function")
            for index, name in enumerate(names):
                start = address + index * size
                self.names[start] = name
                self.leaf_extents[start] = (size, "sdk_entry")
                self.sdk_leaves[start] = {"symbol": name, "archive_symbol": name, "archive_entry": True,
                                          "lib": proof["lib"], "member": proof["member"], "group": address}
                self.unnamed.discard(start)
                occupied[start] = size

    def _split_sdk_archive_extents(self, splits):
        """Separate a merged IDA span into independently witnessed archive functions."""
        occupied = self.extents | {address: self.size(address)[0] for address in self.names}
        for address, proof in sorted(splits.items()):
            parts, length = proof["parts"], proof["previous_size"]
            if (len(parts) < 2 or parts[0]["offset"] != 0 or parts[0]["symbol"] != proof["exported_name"]
                    or self.names.get(address) != proof["exported_name"] or self.size(address) != (length, "ida")):
                raise ValueError(f"SDK archive split {address:08X} does not match its exported extent")
            del occupied[address]
            if next(disjoint_extents(occupied, [(address, length)]), None) is None:
                raise ValueError(f"SDK archive split {address:08X} overlaps another function")
            previous_end = address
            for part in parts:
                offset, size = part["offset"], part["size"]
                start = address + offset
                end = start + size
                if (offset % 4 or size <= 0 or size % 4 or start < previous_end or end > address + length
                        or (start > previous_end and self.bytes(previous_end, start - previous_end)
                            != bytes(start - previous_end))):
                    raise ValueError(f"SDK archive split {address:08X} contains an invalid function or gap")
                if start != address:
                    self._check_leaf_branch(part, occupied, "SDK archive split", start, start, end)
                self.names[start] = part["symbol"]
                self.unnamed.discard(start)
                self.leaf_extents[start] = (size, "sdk_split")
                # Every split part must resolve all masked calls and data.
                self.sdk_leaves[start] = {"archive_data_targets": {}, **part}
                occupied[start] = size
                previous_end = end
            if previous_end != address + length:
                raise ValueError(f"SDK archive split {address:08X} does not cover the end of the export")

    def _switch_case_target(self, caller, site, entry, tail, end, *, allow_local_escape=False):
        """Resolve an inline XDK absolute jump-table entry within its parent body."""
        from compare import branch_target

        dispatch = site - 28
        if dispatch < caller:
            return None
        bounds, escape, high, low, shift, load, ctr, jump = struct.unpack(">8I", self.bytes(dispatch, 32))
        index = (bounds >> 16) & 31
        base = (high >> 21) & 31
        offset = (shift >> 16) & 31
        # cmplwi cr6; bgtlr cr6; lis; addi; slwi index,2; lwzx; mtctr; bctr.
        local_escape = allow_local_escape and escape & 0xFFFF0000 == 0x41990000
        if (bounds & 0xFFE00000 != 0x2B000000 or not (escape == 0x4D990020 or local_escape)
                or not base or base in (index, offset) or high & 0xFC1F0000 != 0x3C000000
                or low & 0xFFFF0000 != (0x38000000 | base << 21 | base << 16)
                or shift != (0x5400103A | index << 21 | offset << 16)
                or load != (0x7C00002E | offset << 21 | base << 16 | offset << 11)
                or ctr != (0x7C0903A6 | offset << 21) or jump != 0x4E800420):
            return None
        immediate = struct.unpack(">h", struct.pack(">H", low & 0xFFFF))[0]
        table = (((high & 0xFFFF) << 16) + immediate) & 0xFFFFFFFF
        table_end = table + 4 * ((bounds & 0xFFFF) + 1)
        if table != site + 4 or entry % 4 or not table <= entry < table_end <= tail:
            return None
        if local_escape and not table_end <= branch_target(escape, dispatch + 4, 0xFFFC) < end:
            return None
        cases = tuple(target for (target,) in struct.iter_unpack(">I", self.bytes(table, table_end - table)))
        if any(target % 4 or not table_end <= target < end for target in cases):
            return None
        return cases[(entry - table) // 4]

    def _switch_reaches_tail(self, caller, site, entry, tail, end):
        """Check an XDK absolute jump table and a case that reaches the omitted tail."""
        target = self._switch_case_target(caller, site, entry, tail, end)
        if target is None:
            return False
        if target >= tail:
            return True
        # Immediate arithmetic and scalar load/store instructions fall through.
        # Require this straight-line path instead of inferring edges for other opcodes.
        return all(word >> 26 in (14, 15, 32, 38, 48, 52)
                   for (word,) in struct.iter_unpack(">I", self.bytes(target, tail - target)))

    def _archive_switch_reaches_tail(self, caller, site, entry, tail, end, case):
        """Check a bounded SDK case path whose archive relocations are verified separately."""
        if site - 28 < caller:
            return False
        bounds, = struct.unpack(">I", self.bytes(site - 28, 4))
        if bounds & 0xFFFF != 3:
            return False
        target = self._switch_case_target(caller, site, entry, tail, end, allow_local_escape=True)
        expected = tuple(int(word, 16) for word in case["fallthrough_words"])
        if (target is None or target != int(case["target"], 16) or not 0 < len(expected) <= 14
                or tail - target != 4 * len(expected)):
            return False
        words = tuple(word for (word,) in struct.iter_unpack(">I", self.bytes(target, tail - target)))
        # These paths contain arithmetic, memory and VMX instructions. The profile
        # case has one conditional return with a non-return path into the tail.
        conditional_return = 0x4D9A0020
        return (words == expected and words.count(conditional_return) <= 1
                and all(word >> 26 in (4, 10, 11, 14, 15, 32, 36) or word == conditional_return for word in words))

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
