"""Find the ARTIST functions the XDK's own libraries provide.

ARTIST statically links Microsoft's runtime and system libraries (the CRT, XAPI, D3D,
XAudio, ...). Those bodies are not ours to write: on the native branch they come from
linking the same `lib/xbox/*.lib`. A function counts as SDK-provided when one library
function is byte-identical to it outside its relocated fields and, where ARTIST names
the function or its callees, the names agree. Tiny bodies that match several ARTIST
functions are only claimed when the names confirm which one.

The result also checks the toolchain: if ARTIST's CRT matches XDK 6534's libcMT byte
for byte, that is the SDK release the game was linked against.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import struct

from coff import (ObjectFile, CoffError, REL_ADDR32, REL_REFHI, REL_REFLO, REL_PAIR, REL_REL14, REL_REL24,
                  archive_members, be_words, ordinal_code_import)
from artist import Artist, demangle, normal_name
from compare import branch_target, compare, refhi_lo_address

TINY = 12  # bytes: three instructions or fewer match too many unrelated bodies
MTCTR_R11, BCTR = 0x7D6903A6, 0x4E800420


def import_stub(words):
    """(ordinal, module) when four words are an XEX import stub, else None.

    The linker emits one per imported kernel/XAM/network function from the XDK's import
    libraries. In the image the loader has not patched it yet: `li r3,<module index>;
    li r4,<ordinal>; mtctr r11; bctr` (ARTIST's XGetLaunchData: module 0, ordinal 424).
    A patched one reads `lis r11; lwz r11; mtctr; bctr` and gives (-1, -1).
    """
    if len(words) != 4 or words[2] != MTCTR_R11 or words[3] != BCTR:
        return None
    if words[0] >> 16 == 0x3860 and words[1] >> 16 == 0x3880:
        return words[1] & 0xFFFF, words[0] & 0xFFFF
    if words[0] >> 16 == 0x3D60 and words[1] >> 16 == 0x816B:
        return -1, -1
    return None


def library_functions(lib_dir, *, only_members=None):
    for lib in sorted(Path(lib_dir).glob("*.lib")):
        if only_members is not None and lib.name not in only_members:
            continue
        data = lib.read_bytes()
        try:
            members = list(archive_members(data, lib.name))
        except CoffError:
            continue
        for member, body in members:
            if only_members is not None and member not in only_members[lib.name]:
                continue
            try:
                obj = ObjectFile(body, f"{lib.name}:{member}")
            except (CoffError, IndexError, ValueError):
                continue  # LTCG intermediate code, import objects, non-PPC members
            for fn in obj.functions():
                if fn.code:
                    yield lib.name, member, obj, fn, False
            for fn in obj.entry_points():
                if fn.code:
                    yield lib.name, member, obj, fn, True


def verify_leaf_providers(artist, lib_dir):
    """Compare every attested leaf or linker import against its recorded library."""
    members = defaultdict(set)
    addresses = defaultdict(list)
    imports = defaultdict(list)
    for address, proof in artist.sdk_leaves.items():
        if "import_anchor" in proof:
            imports[proof["lib"]].append((address, proof))
            continue
        members[proof["lib"]].add(proof["member"])
        entry = proof.get("archive_entry") is True
        for symbol in [proof["archive_symbol"], *proof.get("archive_aliases", ())]:
            addresses[proof["lib"], proof["member"], symbol, entry].append(address)

    found = {}
    group_locations = defaultdict(set)
    verified_aliases = defaultdict(set)
    for lib, member, obj, fn, entry in library_functions(lib_dir, only_members=members):
        for address in addresses.get((lib, member, fn.symbol, entry), ()):
            size, _ = artist.size(address)
            proof = artist.sdk_leaves[address]
            group = proof.get("group")
            if group is not None and fn.relocs:
                continue
            if len(fn.code) != size or not artist.matches_name(address, demangle(fn.symbol)):
                continue
            result = compare(fn, obj, artist, address, size, fuzzy=False)
            if result.status != "exact":
                continue
            if "fragments" in proof and not _verify_archive_fragments(artist, address, fn, obj, proof, result):
                continue
            if "crt_slot" in proof and not _verify_crt_archive_leaf(artist, address, fn, obj, proof, result):
                continue
            if ("archive_literals" in proof or "archive_data_targets" in proof) and not _verify_archive_data(
                    artist, address, fn, obj, proof, result):
                continue
            if "data_table_slot" in proof and not _verify_data_table_slot(
                    artist, fn, obj, proof["data_table_slot"]):
                continue
            if proof.get("archive_aliases"):
                if result.calls_unverified or result.data_unchecked:
                    continue
                if fn.symbol != proof["archive_symbol"]:
                    verified_aliases[address].add(fn.symbol)
                    continue
            found[address] = {"lib": lib, "member": member, "symbol": fn.symbol, "variants": 1}
            if group is not None:
                group_locations[group].add((fn.section, fn.offset - (address - group)))
    found.update(_verify_linker_imports(artist, lib_dir, imports))

    missing = artist.sdk_leaves.keys() - found.keys()
    if missing:
        failed = ", ".join(f"{address:08X}" for address in sorted(missing))
        raise ValueError(f"SDK leaf archive comparison failed at {failed}")
    for address, locations in group_locations.items():
        if len(locations) != 1:
            raise ValueError(f"SDK entry group {address:08X} is not contiguous in its archive member")
    for address, proof in artist.sdk_leaves.items():
        if set(proof.get("archive_aliases", ())) != verified_aliases[address]:
            raise ValueError(f"SDK archive alias comparison failed at {address:08X}")
    return found


def _verify_crt_archive_leaf(artist, address, fn, obj, proof, result):
    """Require the archive's initializer registration and its linked data targets."""
    if result.calls_unverified or not artist.is_crt_initializer(address, int(proof["crt_slot"], 16)):
        return False
    if not any(rel.type == REL_ADDR32 and fn.target(obj, rel) == fn.symbol
               and struct.unpack_from(">I", section.data, rel.offset)[0] == 0
               for section in obj.sections.values() if section.name == ".CRT$XCU" for rel in section.relocs):
        return False

    targets = {name: int(target, 16) for name, target in proof["crt_data_targets"].items()}
    return _verify_data_targets(artist, address, fn, obj, targets, result)


def _verify_archive_data(artist, address, fn, obj, proof, result):
    literals = proof.get("archive_literals", {})
    targets = {name: int(target, 16) for name, target in proof.get("archive_data_targets", {}).items()}
    if targets.keys() & literals.keys():
        return False
    targets.update({name: int(row["address"], 16) for name, row in literals.items()})
    if result.calls_unverified or not _verify_data_targets(artist, address, fn, obj, targets, result):
        return False
    for rel in fn.relocs:
        if rel.type != REL_REFLO or fn.target(obj, rel) not in literals:
            continue
        symbol = obj.symbols[rel.symbol]
        section = obj.sections.get(symbol.section)
        size = literals[symbol.name]["size"]
        start, end = symbol.value, symbol.value + size
        if (section is None or not section.name.startswith(".rdata") or size <= 0 or end > len(section.data)
                or any(start <= item.offset < end for item in section.relocs)
                or artist.bytes(targets[symbol.name], size) != section.data[start:end]):
            return False
    return True


def _verify_data_targets(artist, address, fn, obj, expected, result):
    checked = _linked_data_targets(artist, address, fn, obj, expected.keys())
    return (checked is not None and len(checked) == result.data_unchecked
            and {name: address for _, name, address in checked} == expected
            and all(expected[name] == address for _, name, address in checked))


def _linked_data_targets(artist, address, fn, obj, symbols):
    """Decode the linked address at each zero-addend reference to these symbols."""
    linked = be_words(artist.bytes(address, len(fn.code)))
    ours = be_words(fn.code)
    addends = {rel.offset for rel in fn.relocs if rel.type == REL_PAIR and rel.symbol}
    highs = {}
    checked = []
    for rel in sorted(fn.relocs, key=lambda item: item.offset):
        if rel.type not in (REL_REFHI, REL_REFLO):
            continue
        name = fn.target(obj, rel)
        if name not in symbols:
            continue
        word = linked[rel.offset // 4]
        opcode = word >> 26
        if rel.offset in addends or ours[rel.offset // 4] & 0xFFFF:
            return None
        if rel.type == REL_REFHI and word & 0xFC1F0000 == 0x3C000000:
            highs[rel.symbol] = word
        elif rel.type == REL_REFLO and (opcode == 14 or 32 <= opcode <= 55) and rel.symbol in highs:
            high = highs[rel.symbol]
            base = (word >> 16) & 31
            if base and (high >> 21) & 31 == base:
                checked.append((rel.offset, name, refhi_lo_address(high, word)))
    return checked


def _verify_data_table_slot(artist, fn, obj, proof):
    """Bind an initialized data table to the image through a same-member code relocation."""
    symbols = {symbol.name: symbol for symbol in obj.symbols.values() if symbol.section > 0}
    table, anchor = symbols.get(proof["symbol"]), symbols.get(proof["anchor_symbol"])
    if table is None or anchor is None or table.section != anchor.section:
        return False
    section = obj.sections[table.section]
    offset = table.value + proof["offset"]
    if (not section.name.startswith(".data") or offset + 4 > len(section.data)
            or section.data[offset:offset + 4] != bytes(4)
            or not any(rel.type == REL_ADDR32 and rel.offset == offset and fn.target(obj, rel) == fn.symbol
                       for rel in section.relocs)):
        return False
    caller = next((body for body in obj.functions() if body.symbol == proof["anchor_caller_symbol"]), None)
    caller_va = int(proof["anchor_caller"], 16)
    caller_size = artist.size(caller_va)[0]
    if (caller is None or len(caller.code) != caller_size
            or not artist.matches_name(caller_va, demangle(caller.symbol))
            or compare(caller, obj, artist, caller_va, caller_size, fuzzy=False).status != "exact"):
        return False
    expected = int(proof["address"], 16) + anchor.value - table.value
    site = int(proof["anchor_reflo_site"], 16) - caller_va
    checked = _linked_data_targets(artist, caller_va, caller, obj, {anchor.name})
    return checked is not None and (site, anchor.name, expected) in checked


def _verify_archive_fragments(artist, address, fn, obj, proof, result):
    """Check the offsets of archive labels and any branches to internal symbols."""
    labels = {(sym.name, sym.value - fn.offset) for sym in obj.symbols.values() if sym.section == fn.section}
    if any((part["archive_symbol"], int(part["address"], 16) - address) not in labels
           for part in proof["fragments"]):
        return False
    words = be_words(artist.bytes(address, len(fn.code)))
    local_calls = 0
    for reloc in fn.relocs:
        symbol = obj.symbols.get(reloc.symbol)
        if (reloc.type not in (REL_REL24, REL_REL14) or symbol is None or symbol.section != fn.section
                or not fn.offset <= symbol.value < fn.offset + len(fn.code)):
            continue
        site = address + reloc.offset
        mask = 0x03FFFFFC if reloc.type == REL_REL24 else 0x0000FFFC
        target = branch_target(words[reloc.offset // 4], site, mask)
        if target != address + symbol.value - fn.offset:
            return False
        if artist.name_at(target) is None:
            local_calls += 1
    return result.calls_unverified == local_calls and result.data_unchecked == 0


def _verify_linker_imports(artist, lib_dir, claims):
    """Tie the image's module index to a known import in the same XDK library."""
    found = {}
    libraries = {path.name: path for path in Path(lib_dir).glob("*.lib")}
    for lib, entries in claims.items():
        if lib not in libraries:
            continue
        exports = defaultdict(set)
        archive = libraries[lib].read_bytes()
        for member, data in archive_members(archive, lib, include_imports=True):
            decoded = ordinal_code_import(data)
            if decoded is not None:
                symbol, dll, ordinal = decoded
                exports[member, symbol].add((dll, ordinal))

        for address, proof in entries:
            anchor = int(proof["import_anchor"], 16)
            anchor_symbol = artist.name_at(anchor)
            if (anchor == address or anchor_symbol is None or not artist.matches_name(address, proof["archive_symbol"])
                    or artist.size(anchor)[0] != 16 or artist.size(address)[0] != 16):
                continue
            anchor_stub = import_stub(struct.unpack(">4I", artist.bytes(anchor, 16)))
            stub = import_stub(struct.unpack(">4I", artist.bytes(address, 16)))
            if anchor_stub is None or stub is None:
                continue
            ordinal, module = stub
            if module < 0 or anchor_stub[1] != module:
                continue
            member, symbol = proof["member"], proof["archive_symbol"]
            if any(o == ordinal and (dll, anchor_stub[0]) in exports[member, anchor_symbol]
                   for dll, o in exports[member, symbol]):
                found[address] = {"lib": "import stub", "member": f"module {module} ordinal {ordinal}",
                                  "symbol": symbol, "ordinal": ordinal, "variants": 1}
    return found


def matching_provider_names(artist, provided):
    """Drop archive guesses contradicted by an independently recovered function name."""
    return {address: proof for address, proof in provided.items()
            if address not in artist.identified_addresses
            or artist.matches_name(address, demangle(proof["symbol"]))}


def identify(artist: Artist, lib_dir, log=print):
    """{ARTIST address: {"lib", "member", "symbol"}} for every SDK-provided function."""
    by_size = defaultdict(list)
    by_head = defaultdict(list)   # (size, first word) -> addresses: most library bodies start unrelocated
    for address in artist.names:
        size, origin = artist.size(address)
        if size and origin != "crt_leaf":  # registration alone gives no archive provenance
            by_size[size].append(address)
            by_head[(size, artist.bytes(address, 4))].append(address)
    claims = defaultdict(dict)   # address -> {(lib, member, symbol): name evidence rank}
    stubs = {}
    for address in artist.names:
        size, _ = artist.size(address)
        if size == 16:
            stub = import_stub(list(struct.unpack(">4I", artist.bytes(address, 16))))
            if stub:
                stubs[address] = stub
    log(f"sdk: {len(stubs)} XEX import stubs")
    seen = 0
    current = None
    for lib, member, obj, fn, entry in library_functions(lib_dir):
        seen += 1
        if lib != current:
            current = lib
            log(f"sdk: {lib} ({seen} library functions so far, {len(claims)} ARTIST functions claimed)")
        if len(fn.code) not in by_size:
            continue
        head_relocated = any(r.offset == 0 and r.type not in (0x00, 0x12) for r in fn.relocs)
        candidates = by_size[len(fn.code)] if head_relocated else by_head.get((len(fn.code), fn.code[:4]), ())
        if not candidates:
            continue
        name = normal_name(demangle(fn.symbol))
        hits = []
        for address in candidates:
            result = compare(fn, obj, artist, address, len(fn.code), fuzzy=False)
            if result.status == "exact":
                hits.append((address, artist.name_at(address)))
        if not hits:
            continue
        named = {
            a: 2 if n is not None and normal_name(n) == name else 1
            for a, n in hits if artist.matches_name(a, name)
        }
        if named:
            chosen = named
        elif entry:
            continue   # an assembly entry point is claimed only where the names agree
        elif len(hits) == 1 and len(fn.code) > TINY:
            chosen = [hits[0][0]]
        else:
            continue
        for address in chosen:
            claims[address][(lib, member, fn.symbol)] = named.get(address, 0)
    log(f"sdk: {seen} library functions scanned, {len(claims)} ARTIST functions provided")
    out = {}
    for address, (ordinal, module) in stubs.items():
        if address not in claims:
            member = f"module {module} ordinal {ordinal}" if module >= 0 else "patched by the loader"
            out[address] = {"lib": "import stub", "member": member, "symbol": artist.names.get(address, ""),
                            "ordinal": ordinal, "variants": 1}
    for address, providers in claims.items():
        # Prefer the canonical export, then a confirmed folded name, then the release library.
        (lib, member, symbol), _ = min(providers.items(), key=lambda kv: (-kv[1], kv[0][0].endswith(("d.lib", "i.lib")), kv[0]))
        out[address] = {"lib": lib, "member": member, "symbol": symbol, "variants": len(providers)}
    return matching_provider_names(artist, out)
