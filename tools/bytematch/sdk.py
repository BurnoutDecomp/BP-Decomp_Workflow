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

from coff import ObjectFile, CoffError, archive_members
from artist import Artist, demangle, normal_name
from compare import compare

TINY = 12  # bytes: three instructions or fewer match too many unrelated bodies


def library_functions(lib_dir):
    for lib in sorted(Path(lib_dir).glob("*.lib")):
        data = lib.read_bytes()
        try:
            members = list(archive_members(data, lib.name))
        except CoffError:
            continue
        for member, body in members:
            try:
                obj = ObjectFile(body, f"{lib.name}:{member}")
            except (CoffError, IndexError, ValueError):
                continue  # LTCG intermediate code, import objects, non-PPC members
            for fn in obj.functions():
                if fn.code:
                    yield lib.name, member, obj, fn


def identify(artist: Artist, lib_dir, log=print):
    """{ARTIST address: {"lib", "member", "symbol"}} for every SDK-provided function."""
    by_size = defaultdict(list)
    by_head = defaultdict(list)   # (size, first word) -> addresses: most library bodies start unrelocated
    for address in artist.names:
        size, _ = artist.size(address)
        if size:
            by_size[size].append(address)
            by_head[(size, artist.bytes(address, 4))].append(address)
    claims = defaultdict(dict)   # address -> {(lib, member, symbol): named?}
    seen = 0
    current = None
    for lib, member, obj, fn in library_functions(lib_dir):
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
        named = [a for a, n in hits if n is not None and normal_name(n) == name]
        if named:
            chosen = named
        elif len(hits) == 1 and len(fn.code) > TINY:
            chosen = [hits[0][0]]
        else:
            continue
        for address in chosen:
            claims[address][(lib, member, fn.symbol)] = bool(named)
    log(f"sdk: {seen} library functions scanned, {len(claims)} ARTIST functions provided")
    out = {}
    for address, providers in claims.items():
        # Prefer a name-confirmed provider, then the release library over d/i variants.
        (lib, member, symbol), _ = sorted(providers.items(), key=lambda kv: (not kv[1], kv[0][0].endswith(("d.lib", "i.lib")), kv[0]))[0]
        out[address] = {"lib": lib, "member": member, "symbol": symbol, "variants": len(providers)}
    return out
