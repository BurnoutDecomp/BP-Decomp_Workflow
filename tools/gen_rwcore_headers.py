#!/usr/bin/env python3
"""Generate C++ type-vocabulary headers for the Renderware 4 core engine.

Reads the offline Ghidra export of `rwcore_master.obj` (.ghidra-exports/rwcore/,
derived from rwcore.lib + rwcore.pdb) and emits layout-faithful, namespaced
`rw::` struct/enum headers under b5-decomp/vendor/renderware/.

This is the "one-time type pass": the goal is a fixed, shared `rw::` vocabulary
so the re-agent loop references these types instead of re-deriving struct layouts
per function (which causes drift). It does NOT emit function bodies — those come
in lazily/stubbed (see CLAUDE.md "rwcore" strategy).

Scope: only the `rw::` namespace (89 structs, 9 enums). Field types that point
into EA / eastl / std / CRT types are emitted as exact-size opaque byte blobs
(commented with the original type) so the headers stay self-contained and the
PDB-exact layout is preserved without needing those foreign layouts.

The source PDB is x64 (8-byte pointers). Layout static_asserts are emitted but
guarded to only fire on a 64-bit build (RW_VERIFY_LAYOUT + 64-bit pointers).

Re-run after re-exporting rwcore:
    python tools/gen_rwcore_headers.py
"""
from __future__ import annotations
import json, re, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORT = ROOT / ".ghidra-exports" / "rwcore"
OUTDIR = ROOT / "b5-decomp" / "vendor" / "renderware"
INCDIR = OUTDIR / "include" / "rw"

NS = "rw"  # only this top-level namespace is emitted as named types

# Ghidra primitive type -> (C++ type, size). 'pointer'/'undefined' handled specially.
PRIM = {
    "byte":  ("uint8_t",  1),
    "word":  ("uint16_t", 2),
    "dword": ("uint32_t", 4),
    "qword": ("uint64_t", 8),
    "char":  ("char",     1),
    "uchar": ("uint8_t",  1),
    "short": ("int16_t",  2),
    "ushort":("uint16_t", 2),
    "int":   ("int32_t",  4),
    "uint":  ("uint32_t", 4),
    "long":  ("int32_t",  4),
    "ulong": ("uint32_t", 4),
    "longlong":  ("int64_t",  8),
    "ulonglong": ("uint64_t", 8),
    "float": ("float",  4),
    "double":("double", 8),
    "bool":  ("bool",   1),
    "void":  ("void",   0),
}

ARR = re.compile(r"^(.*?)\s*\[(\d+)\]$")

# The PDB exposes the resource family only as template instantiations
# (rw::BaseResources<4>, rw::BaseResourceDescriptors<4>) whose '<4>' is not a legal
# identifier chain, so the data-driven emitter skipped them and fell back to opaque
# 32-byte blobs. Emit a faithful, hand-maintained prelude (the templates + the
# concrete Resource/ResourceDescriptor + the shared BaseResourceDescriptor) at the
# top of the rw namespace instead, and skip the emitter's opaque bodies for them.
# Keeping the bases as templates lets the X360 build's 5-entry serialised descriptor
# be spelled rw::BaseResourceDescriptors<5> from the same vocabulary (see
# CgsResource::ResourceDescriptor in CgsResourceType.h).
RESOURCE_FAMILY_PRELUDE = """\
// --- Resource family (hand-maintained; see gen_rwcore_headers.py) ----------
// The PDB exposes these as template instantiations the data-driven emitter
// cannot name. Layout-faithful to rwcore.pdb (x64):
//   rw::BaseResourceDescriptor        sizeof =  8  { uint m_size; uint m_alignment; }
//   rw::BaseResources<4>              sizeof = 32  { void* m_baseResources[4]; }
//   rw::BaseResourceDescriptors<4>    sizeof = 32  { BaseResourceDescriptor[4]; }
//   rw::Resource           : BaseResources<4>
//   rw::ResourceDescriptor : BaseResourceDescriptors<4>
// CROSS-BUILD DRIFT: the X360 game build instantiates the *serialised* resource
// descriptor with FIVE entries (rw::BaseResourceDescriptors<5>, 40B); PC rwcore
// uses <4> (32B). The X360 form is spelled rw::BaseResourceDescriptors<5> (see
// CgsResource::ResourceDescriptor in CgsResourceType.h).
struct BaseResourceDescriptor {  // sizeof = 8 (rwcore.pdb, x64)
    uint32_t m_size;       // +0
    uint32_t m_alignment;  // +4
};
RW_SIZE_ASSERT(rw::BaseResourceDescriptor, 8);

template <uint32_t Count>
struct BaseResources {
    void* m_baseResources[Count];
};

template <uint32_t Count>
struct BaseResourceDescriptors {
    BaseResourceDescriptor m_baseResourceDescriptors[Count];

    // RenderWare accumulates each sub-allocation's requirement: round this entry's
    // running size up to the other's alignment, widen to the larger alignment, then
    // add the other's size. (Real caller lives in rwcore.lib's allocators.)
    BaseResourceDescriptors& operator+=(const BaseResourceDescriptors& lOther)
    {
        for (uint32_t luIndex = 0; luIndex < Count; ++luIndex)
        {
            BaseResourceDescriptor& lDescriptor = m_baseResourceDescriptors[luIndex];
            const BaseResourceDescriptor& lOtherDescriptor = lOther.m_baseResourceDescriptors[luIndex];
            if (lOtherDescriptor.m_alignment > 1)
                lDescriptor.m_size = (lOtherDescriptor.m_alignment - 1 + lDescriptor.m_size) & ~(lOtherDescriptor.m_alignment - 1);
            if (lDescriptor.m_alignment < lOtherDescriptor.m_alignment)
                lDescriptor.m_alignment = lOtherDescriptor.m_alignment;
            lDescriptor.m_size += lOtherDescriptor.m_size;
        }
        return *this;
    }
};

struct Resource : public BaseResources<4> {};
RW_SIZE_ASSERT(rw::Resource, 32);

struct ResourceDescriptor : public BaseResourceDescriptors<4> {};
RW_SIZE_ASSERT(rw::ResourceDescriptor, 32);
// --------------------------------------------------------------------------""".splitlines()

# Names provided by RESOURCE_FAMILY_PRELUDE: keep them in `emitted` (so by-value
# references such as LinearResourceAllocator::m_heapResource / m_heapCapacity still
# resolve) but skip the emitter's opaque-blob bodies for them.
SKIP_EMIT_BODY = {"rw::Resource", "rw::ResourceDescriptor", "rw::BaseResourceDescriptor"}


def load():
    structs = json.loads((EXPORT / "_structs.json").read_text())
    enums = json.loads((EXPORT / "_enums.json").read_text())
    vtables = json.loads((EXPORT / "_vtables.json").read_text())
    return structs, enums, vtables


def is_rw(name: str) -> bool:
    return name.split("::")[0] == NS


def legal_ident_chain(name: str) -> bool:
    """True if every component is a plain C++ identifier (no templates/unnamed)."""
    for part in name.split("::"):
        if not re.fullmatch(r"[A-Za-z_]\w*", part):
            return False
    return True


def parse_field_type(t: str):
    """Return (base, count) where count is array length (1 if scalar)."""
    m = ARR.match(t)
    if m:
        return m.group(1).strip(), int(m.group(2))
    return t, 1


def cpp_ref(base: str, emitted: set[str]) -> str | None:
    """Map a base type token to a C++ type name, or None if it must be a blob."""
    if base == "pointer":
        return "void*"
    if base in PRIM:
        return PRIM[base][0]
    if base in emitted:
        return "::" + base
    return None


def emit_struct(name, st, emitted, vtable_for):
    """Yield lines for one struct (namespace opened/closed by caller)."""
    short = name.split("::")[-1]
    out = []
    vt = vtable_for.get(name)
    if vt:
        out.append(f"// vtable {vt['symbol']} @ {vt['address']} ({vt['entry_count']} entries):")
        for e in vt.get("entries", []):
            out.append(f"//   [{e['index']:>2}] +{e['offset']:<3} {e['name']}")
    out.append(f"struct {short} {{  // sizeof = {st['size']} (rwcore.pdb, x64)")

    cursor = 0
    pad_idx = 0
    used_names: set[str] = set()
    def uniq(nm: str) -> str:
        if nm not in used_names:
            used_names.add(nm)
            return nm
        k = 2
        while f"{nm}_{k}" in used_names:
            k += 1
        nm2 = f"{nm}_{k}"
        used_names.add(nm2)
        return nm2
    # coalesce consecutive `undefined` 1-byte filler fields into padding arrays
    fields = st["fields"]
    i = 0
    n = len(fields)
    while i < n:
        f = fields[i]
        off, ftype, fsize = f["offset"], f["type"], f["size"]
        # insert explicit padding if there is a gap
        if off > cursor:
            out.append(f"    uint8_t _gap{pad_idx}[{off - cursor}];  // +{cursor}")
            pad_idx += 1
            cursor = off
        if ftype == "undefined":
            # gather the run of undefined/filler bytes
            run = 0
            while i < n and fields[i]["type"] == "undefined":
                run += fields[i]["size"]
                i += 1
            out.append(f"    uint8_t _pad{pad_idx}[{run}];  // +{off}")
            pad_idx += 1
            cursor = off + run
            continue
        base, count = parse_field_type(ftype)
        ref = cpp_ref(base, emitted)
        fname = uniq(sanitize_ident(f["name"]))
        if ref is None:
            # opaque blob preserving exact size, original type in comment
            out.append(f"    uint8_t {fname}[{fsize}];  // +{off}  was: {ftype}")
        elif count > 1:
            out.append(f"    {ref} {fname}[{count}];  // +{off}")
        else:
            out.append(f"    {ref} {fname};  // +{off}")
        cursor = off + fsize
        i += 1
    if cursor < st["size"]:
        out.append(f"    uint8_t _tail[{st['size'] - cursor}];  // +{cursor}")
    out.append("};")
    out.append(f"RW_SIZE_ASSERT({name}, {st['size']});")
    return out


def struct_deps(name, st, emitted):
    """Names of other emitted rw structs embedded BY VALUE (need full def first)."""
    deps = set()
    for f in st["fields"]:
        if f["type"] == "pointer":
            continue
        base, _ = parse_field_type(f["type"])
        if base != "pointer" and base in emitted and base != name:
            deps.add(base)
    return deps


def toposort(names, structs, emitted):
    order, seen, temp = [], set(), set()
    def visit(n):
        if n in seen:
            return
        if n in temp:  # cycle (shouldn't happen for by-value); break it
            return
        temp.add(n)
        for d in sorted(struct_deps(n, structs[n], emitted)):
            visit(d)
        temp.discard(n)
        seen.add(n)
        order.append(n)
    for n in sorted(names):
        visit(n)
    return order


def open_ns(prev: str, cur: str, out: list):
    """Switch namespace context from prev qualified-name to cur.

    Uses C++17 nested-namespace blocks (`namespace a::b::c { ... }`), which take a
    single closing brace regardless of depth.
    """
    pprev = prev.split("::")[:-1] if prev else []
    pcur = cur.split("::")[:-1]
    if pprev == pcur:
        return
    if pprev:
        out.append("}  // namespace " + "::".join(pprev))
    if pcur:
        out.append("namespace " + "::".join(pcur) + " {")


def sanitize_ident(name: str) -> str:
    """Coerce a Ghidra field name into a legal C++ identifier."""
    s = re.sub(r"[^0-9A-Za-z_]", "_", name)
    if not s or s[0].isdigit():
        s = "_" + s
    return s


def gen_enums(enums, struct_names):
    def nested_in_struct(name):
        parts = name.split("::")
        return any("::".join(parts[:k]) in struct_names for k in range(1, len(parts)))
    rw = {n: e for n, e in enums.items()
          if is_rw(n) and legal_ident_chain(n) and not nested_in_struct(n)}
    L = [HEADER_NOTE, "#pragma once", "#include <cstdint>", ""]
    prev = ""
    for name in sorted(rw):
        open_ns(prev, name, L)
        e = rw[name]
        short = name.split("::")[-1]
        L.append(f"enum class {short} : uint32_t {{  // size {e.get('size')}")
        for v in e["values"]:
            L.append(f"    {v['name']} = {v['value']},")
        L.append("};")
        prev = name
    open_ns(prev, "", L)  # close trailing namespace
    return "\n".join(L) + "\n"


def gen_structs(structs, vtable_for):
    # emittable rw structs: rw namespace, legal identifier chain, and no prefix
    # that is itself a struct (would be a nested class -> namespace/class clash)
    all_struct_names = set(structs)
    def has_struct_prefix(name):
        parts = name.split("::")
        for k in range(1, len(parts)):
            if "::".join(parts[:k]) in all_struct_names:
                return True
        return False

    emitted = {n for n in structs
               if is_rw(n) and legal_ident_chain(n) and not has_struct_prefix(n)}
    order = toposort(emitted, structs, emitted)

    L = [HEADER_NOTE, "#pragma once", "#include <cstdint>", '#include "rwcore_enums.h"', "",
         "// Layout verification (PDB is x64; only meaningful on a 64-bit build).",
         "#if defined(RW_VERIFY_LAYOUT) && (UINTPTR_MAX == 0xFFFFFFFFFFFFFFFFull)",
         "  #include <cstddef>",
         "  #define RW_SIZE_ASSERT(T, N) static_assert(sizeof(T) == (N), #T \" size\")",
         "#else",
         "  #define RW_SIZE_ASSERT(T, N)",
         "#endif",
         ""]
    prev = ""
    prelude_done = False
    for name in order:
        open_ns(prev, name, L)
        prev = name
        # Inject the hand-maintained resource family at the top of the first
        # top-level `rw` block (before any struct that embeds rw::Resource).
        if not prelude_done and name.startswith("rw::") and name.count("::") == 1:
            L.append("")
            L.extend(RESOURCE_FAMILY_PRELUDE)
            prelude_done = True
        if name in SKIP_EMIT_BODY:
            continue
        L.append("")
        L.extend(emit_struct(name, structs[name], emitted, vtable_for))
    open_ns(prev, "", L)
    L.append("")
    L.append("#undef RW_SIZE_ASSERT")
    return "\n".join(L) + "\n", emitted, order


HEADER_NOTE = (
    "// GENERATED by tools/gen_rwcore_headers.py — do not edit by hand.\n"
    "// Source: rwcore_master.obj (rwcore.lib + rwcore.pdb) via .ghidra-exports/rwcore.\n"
    "// Renderware 4 core `rw::` type vocabulary for the Burnout PC decomp.\n"
    "// Layout-faithful to the x64 PDB; foreign (EA/eastl/std/CRT) fields are\n"
    "// exact-size opaque blobs tagged `was: <type>`. Re-run the generator to refresh."
)


def main():
    if not EXPORT.exists():
        sys.exit(f"export dir not found: {EXPORT} — run the rwcore Ghidra export first")
    structs, enums, vtables = load()

    # map struct qualified-name -> its vtable (demangle ??_7Class@ns@..@@6B@)
    vtable_for = {}
    for sym, vt in vtables.items():
        m = re.match(r"\?\?_7(.+?)@@6B@?$", sym)
        if not m:
            continue
        parts = m.group(1).split("@")
        qual = "::".join(reversed([p for p in parts if p]))
        vt = dict(vt, symbol=sym)
        vtable_for[qual] = vt

    INCDIR.mkdir(parents=True, exist_ok=True)
    (INCDIR / "rwcore_enums.h").write_text(gen_enums(enums, set(structs)), encoding="utf-8")
    structs_src, emitted, order = gen_structs(structs, vtable_for)
    (INCDIR / "rwcore_structs.h").write_text(structs_src, encoding="utf-8")

    umbrella = (HEADER_NOTE + "\n#pragma once\n"
                '#include "rw/rwcore_enums.h"\n#include "rw/rwcore_structs.h"\n')
    (INCDIR.parent / "rwcore.h").write_text(umbrella, encoding="utf-8")

    print(f"emitted {len(emitted)} rw:: structs, "
          f"{sum(1 for n in enums if is_rw(n) and legal_ident_chain(n))} enums, "
          f"{len(vtable_for)} vtables matched")
    print(f"  -> {INCDIR/'rwcore_structs.h'}")
    print(f"  -> {INCDIR/'rwcore_enums.h'}")
    print(f"  -> {INCDIR.parent/'rwcore.h'}")
    # report skipped rw structs (nested/template/unnamed) for transparency
    skipped = [n for n in structs if is_rw(n) and n not in emitted]
    if skipped:
        print(f"  skipped {len(skipped)} non-emittable rw types (nested/template/unnamed):")
        for n in sorted(skipped):
            print(f"     - {n}")


if __name__ == "__main__":
    main()
