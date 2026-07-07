# Apt reference — Burnout Revenge `B4Extern` (Apt 0.19.02)

A **reference vocabulary** for the EATech **Apt** UI runtime, recovered from a
fully-symbolized Xbox 360 build of *Burnout Revenge* ("Burnout 4"). Its value to
this (Paradise/B5) project is that it **names, shapes, and signs the Apt engine**
— the ActionScript VM, CIH timeline, GC, and value system — which are only
partially named in our other builds.

> **REFERENCE ONLY — not authority, not for `b5-decomp/src`.**
> This is Apt **0.19.02** (Revenge, 2005). Paradise's Apt is a later (~2008)
> version. Dropping these layouts into the ledger as-is is the **VERSION-DRIFT
> TRAP** (see [`AGENTS.md`](../../AGENTS.md)). Use it to *name* engine functions,
> recover the *class hierarchy*, and confirm *method signatures* — then verify
> every offset/width against `Burnout_External_Xbox_One` (x64) and every behavior
> against ARTIST before adopting anything.

## Provenance

| | |
|---|---|
| Source binary | `IDA Files/B4Extern.pe` (raw PE) / `default.xex` (packaged) |
| Symbols | `B4Extern.pdb` (MSVC PDB 7.00, `HasPrivateSymbols`, GUID `2E534D38-9330-4D39-B607-3715DDDA2C81`) |
| Platform | Xenon / **PowerPC, 32-bit, big-endian**, ImageBase `0x400000` |
| Apt package | `C:\Packages\Apt\0.19.02\build\xenon-vc7-release` |
| Ladder role | **Naming / class-hierarchy / signature corroboration** for Apt. Not the behavioral spine (ARTIST) and not the PC-width arbiter (x64 XB1). |

`B4Extern` is Burnout Revenge's **external host shell** — its ~941 compilands are
the Xbox XDK runtime, EA DirtySDK networking, EA realcore/realmemcard middleware,
a video codec, and the Apt UI runtime. There is **no gameplay** in it. Only the
**Apt** slice is extracted here; the rest is vendor middleware we link/skip.

## Address convention

llvm-pdbutil reports function **RVAs**; IDA loads at ImageBase `0x400000`, so the
**VA** you see in IDA — and the `<VA>.json` export filename, and the address
comments in the generated header — is `RVA + 0x400000`. E.g. `AptCIH::AptCIH` is
RVA `0x4292f8` → VA `0x8292f8` → `.ida-exports/B4Extern/ida-export/0x8292F8.json`.

## Contents

This bundle (committed) holds the **PDB-derived** material — the durable reference:

```
pdb-dump/                 raw llvm-pdbutil output — the authoritative ground truth
  apt_layouts.txt           161 Apt class/struct layouts (members, offsets, bitfields, bases, sizeof)
  apt_enums.txt             Apt enums (AptVirtualFunctionTable_Indices, opcodes, …)
  apt_module_syms.txt       1105 Apt func signatures with RVAs, grouped by .cpp
  all_module_syms.txt       full B4Extern func-symbol dump (all libraries; for context)
  apt_addrs.txt             1028 unique Apt VAs — the export allowlist
include/
  apt_types.gen.h           GENERATED convenience header: 151 Apt types + per-class
                            method prototypes with VAs. Readable rendering of pdb-dump/.
```

The **per-function Hex-Rays pseudocode + PPC asm + xrefs** (1028 `<VA>.json`, schema
matches the other builds' exports) is a **local, git-ignored cache** at
`.ida-exports/B4Extern/ida-export/` — regenerate it from `IDA Files/B4Extern.pe.i64`
with the export command below (it is derived, so it is not committed).

## How to regenerate

```bash
# 1. Raw PDB dumps (needs llvm-pdbutil, e.g. VS-bundled):
#    "…/VC/Tools/Llvm/x64/bin/llvm-pdbutil.exe"
PDB="IDA Files/B4Extern.pdb"
llvm-pdbutil pretty -classes -class-definitions=layout -include-types=Apt "$PDB" > pdb-dump/apt_layouts.txt
llvm-pdbutil pretty -enums   -include-types=Apt "$PDB"                       > pdb-dump/apt_enums.txt
llvm-pdbutil pretty -module-syms -sym-types=funcs "$PDB"                     > pdb-dump/all_module_syms.txt
#    (filter the Apt compilands out of all_module_syms.txt -> apt_module_syms.txt)

# 2. Header + VA allowlist:
python tools/apt_revenge/generate_apt_headers.py

# 3. IDA per-function export (Apt only, via the allowlist):
#    idat -A "-S<repo>\tools\ida\export_all.py" <copy of B4Extern.pe.i64>
#    with env:  EXPORT_ADDR_FILE=pdb-dump/apt_addrs.txt
#               EXPORT_OUT_DIR=.ida-exports/B4Extern/ida-export
#               EXPORT_DB_NAME=B4Extern.pe
```

## Using it (the discipline)

When reconstructing a Paradise Apt function:
1. **Names & hierarchy** — trust this build for *which engine classes exist* and how
   they relate (`AptValue → AptValueGC/AptValueNoGC → …`, the `AptScriptFunction*`
   family, the `AptValueGC*` GC). This is its strongest contribution.
2. **Signatures** — take return/param types and `virtual`/`const` from the method
   list, cross-checked against ARTIST asm (Hex-Rays gets PPC signatures wrong).
3. **Offsets / widths** — **do not** trust 0.19.02 offsets for the PC target. Confirm
   member placement against ARTIST pseudocode and pointer widths against the x64
   `Burnout_External_Xbox_One` build (the established Apt width arbiter).
4. **Behavior** — the pseudocode here is a *second opinion* on an older Apt; ARTIST
   remains the behavioral authority. Use it to disambiguate an inlined/folded body.
