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

from coff import ObjectFile, CoffError, archive_members
from artist import Artist, demangle, normal_name
from compare import compare

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
    """Compare every attested leaf against its recorded archive member."""
    members = defaultdict(set)
    addresses = defaultdict(list)
    for address, proof in artist.sdk_leaves.items():
        members[proof["lib"]].add(proof["member"])
        entry = proof.get("archive_entry") is True
        addresses[proof["lib"], proof["member"], proof["archive_symbol"], entry].append(address)

    found = {}
    group_locations = defaultdict(set)
    for lib, member, obj, fn, entry in library_functions(lib_dir, only_members=members):
        for address in addresses.get((lib, member, fn.symbol, entry), ()):
            size, _ = artist.size(address)
            group = artist.sdk_leaves[address].get("group")
            if group is not None and fn.relocs:
                continue
            if (len(fn.code) == size and artist.matches_name(address, demangle(fn.symbol))
                    and compare(fn, obj, artist, address, size, fuzzy=False).status == "exact"):
                found[address] = {"lib": lib, "member": member, "symbol": fn.symbol, "variants": 1}
                if group is not None:
                    group_locations[group].add((fn.section, fn.offset - (address - group)))

    missing = artist.sdk_leaves.keys() - found.keys()
    if missing:
        failed = ", ".join(f"{address:08X}" for address in sorted(missing))
        raise ValueError(f"SDK leaf archive comparison failed at {failed}")
    for address, locations in group_locations.items():
        if len(locations) != 1:
            raise ValueError(f"SDK entry group {address:08X} is not contiguous in its archive member")
    return found


def identify(artist: Artist, lib_dir, log=print):
    """{ARTIST address: {"lib", "member", "symbol"}} for every SDK-provided function."""
    by_size = defaultdict(list)
    by_head = defaultdict(list)   # (size, first word) -> addresses: most library bodies start unrelocated
    for address in artist.names:
        size, _ = artist.size(address)
        if size:
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
    return out
