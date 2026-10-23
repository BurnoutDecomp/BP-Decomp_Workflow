# Original GameData allocation helpers

This source-only WIP recovers the three original stack-backed helpers at ARTIST8266DA28,8266DB88,8266DD00. Exact base is `57bbdefbbac12c0595d7eeed03de40729d2a14af`, Root's third owner checkpoint. Four source paths have full pre/post bindings in `SOURCE_MANIFEST.json`. No mount, call-site activation, source checkout edit, build, test or runtime claim is included.

Banks and pools publish the actual memory-map requests, wait for exactly the outstanding reply count, clear that count/receiver on completion, and otherwise pump the original stack-backed resource helper. `MemoryMap::GetNumBanks()` already returns the non-root count; `GetBank(i)` selects row i+1. ARTIST's 16-row map therefore submits 15 banks, followed by all 27 pools. Pools3/4/15 receive the original defragmentation flag. No native capacity allowances enter these original overloads.

Allocators submit raw, Linear, Heap, RW Linear and RW General records in that order. The map supplies 1/7/8/4/4 populated rows, for 24 requests. The real module-owned audio allocator is published without re-Constructing it. The receiver stores raw resource/descriptor replies and RW allocator pointers into the actual member storage/registry. Wrapper replies need no store because the memory service constructs the supplied member objects. Reply result codes are not tested by the original caller.

Canonical response accessors are restored from DecFIGS shape and ARTIST's inlined reads. ARTIST sends 76 bytes for the raw response and 20 for a Linear response on X360; the current unattested trailing raw allocator pointer and second Linear pointer are removed. All native transport uses native `sizeof`/dynamic response sizes. Current consumers use the canonical resource/descriptor fields; this remains an ABI-affecting source change awaiting integration review.

Primary member spans pin eight Linear and nine Heap storage slots, with one unpopulated spare in each family. Both the generated objects and the one canonical registry now have those ARTIST capacities. The map and active native loop bounds remain unchanged. No parallel registry or synthetic allocator was added.

The original helpers create their Resource input before checking completion. All three success paths return without destroying that input carve; pending paths pump, destroy it and return false. This observed lifetime is preserved explicitly, including the zero-request pending behavior. No RAII cleanup or success check was invented.

`NATIVE_BODY_BINDINGS.json` proves the current two-argument Prepare and all three void-pointer helpers remain byte-identical after newline normalization. The existing Construct body is also unchanged. Its registry initialization still clears only the populated 7/8 slots, and its broader original construction order remains a separate recovery boundary. The new spare slots are not made ready by an invented initializer.

Eight definitions from the preceding eleven-symbol boundary remain unavailable. Current RW memory service handlers are also concrete empty bodies, so this packet does not make the allocator phase runnable. See `READINESS_AND_OWNERSHIP.md` and `MISSING_LINK_SYMBOLS.json`. Registration counts and the playable build are unchanged.
