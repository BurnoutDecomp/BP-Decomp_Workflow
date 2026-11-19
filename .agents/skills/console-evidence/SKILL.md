---
name: console-evidence
description: >-
  Which build is authoritative for what, and which tool answers which question about the
  original game. Load before deciding what the console does or how a function is called:
  reading ARTIST (X360) pseudocode or assembly, an `.ida-exports/<build>/0x<addr>.json`,
  DecFIGS DWARF, LegacySrc, the Xbox One x64 export (Apt, 64-bit widths), B4Extern, the
  X360 audio PDB (`rw::audio::core`), BPR/TUB or burnout.wiki; before trusting a signature,
  an offset, a constant, a vtable slot or a "not in the export set"; and before running
  `work show --full --asm`, `work audit`, funcaudit.py, stubaudit.py, asmaudit.py,
  asmmatch.py, constaudit.py, findinit.py, hasbody.py, ppcdis.py, x360rd.py, vmx128.py,
  vcallsites.py, vdispatch_audit.py, vtable_override_audit.py, silent_link_sweep.py,
  widening_sweep.py or wiki_index.py. Also covers VMX operand order (vmaddfp), export
  holes, and searches that come back empty.
---

# Console evidence

What the original game does is decided by evidence from several builds, and they are not
equal. This skill says which one wins for which question, and which tool answers it.

Not for: the TU work loop and the code-writing rules ([reconstruct-tu](../reconstruct-tu/SKILL.md)),
running the game ([bug-test](../bug-test/SKILL.md)), or the end-to-end triage of a behaviour
gap ([diagnose-parity-bug](../diagnose-parity-bug/SKILL.md), which uses this skill).

## 1. The source-of-truth ladder

A lower rung never overrides a higher one.

1. **ARTIST (X360, `BURNOUT_X360_ARTIST.XEX`) is the spine.** Its pseudocode **and assembly**
   are authoritative for what each function does and how it is called. It also supplies
   identity, names and file structure.
2. **DecFIGS (Internal PS3, DWARF) is the authority for declaration shape**: signatures,
   types, `virtual`/`const`, vtable order, member names. It is **gated on X360 attestation**:
   a DWARF declaration enters a header only if that `Class::Fn` is in the X360 ledger
   (`progress/status.json` → `func`); a method the ledger lacks is PS3-only and stays out.
   Also use it for file attribution and local-variable hints. It is never offset authority.
3. **LegacySrc** is a **styling / inlining reference only**:
   idiom, and the shape of helpers the X360 compiler inlined. Heavy version drift makes its
   layouts and logic non-authoritative.

Why this order (build lineage): LegacySrc b5_main → Dec-2007 DecFIGS (branch B5_FIGS) →
FIGS merged into `main` **before** ARTIST compiled → Jan-2008 ARTIST (X360 `main`, the
target). So DecFIGS is a high-confidence near-ancestor of ARTIST, the ARTIST asm arbitrates
the small merge-window delta, and LegacySrc (pre-merge old main) is the stalest source for
any FIGS-touched code.

**What only the PS3 builds give** (the X360 stripped it to data):

- RTTI class `ObjectID`s and `typeName`s: the DecFIGS `__static_initialization_and_destruction_*`
  functions construct each `Class::sTypeInfo` with literal values. Pin any arbitrary or
  placeholder class id from these.
- Member and enum names and signatures (DWARF, dumped under `references/DecFIGS/dwarfdump/`,
  a local input that `work show --full` surfaces).
- Inlined or ICF-folded bodies the X360 dropped: decompile from the PS3 export, then confirm
  the entity (offset, value, role) in the ARTIST asm before attaching a name.
  `references/DecFIGS/decfigs_inlining.json` (local input) lists what was inlined into each
  PS3 function and from which file.
- Names for nameless X360 data: a `.bss`/`.data` symbol the X360 shows as `unk_`/`flt_` usually
  carries its DWARF name in the DecFIGS export of the same function.

Every ladder rule with its reason, including DWARF gating and the version-drift trap:
[references/ladder.md](references/ladder.md).

## 2. Exceptions and side references

| Source | Use it for | Never for |
|---|---|---|
| Xbox One x64 export (`.ida-exports/Burnout_External_Xbox_One.exe/`) | **Rung 1 for the Apt runtime** (`SDKs/EATech/Apt`, `SDKs/EATech/include/Apt`, the `CgsApt*` glue): the only native little-endian 64-bit build; a named symbol's mangled name is the exact prototype. **The 64-bit ABI arbiter** for widths, offsets and alignment in Apt and other vendor layers. | Behaviour outside Apt (a later retail build: expect drift). Physics names: its named symbols are almost all Apt, so descend the call graph from an identified twin instead. |
| B4Extern (Burnout Revenge X360 PDB, Apt 0.19.02) | Naming Apt engine functions the x64 build leaves `sub_`, the class hierarchy, method signatures. | Offsets, widths or behaviour (32-bit big-endian, 2005). Its layouts adopted wholesale are the version-drift trap. |
| The X360 audio PDB + MAP in `IDA Files/` (another game, same era) | `rw::audio::core` types: field order, names, types. | Burnout's own `CgsSound`/`BrnSound` shape; host widths (model x64). |
| BPR / TUB (stripped PC builds) | Per-function reference for platform layers (SIMD, GPU/D3D, codecs) where the PC shape differs. Not in the ledger; never decompiled. | The spine. Offsets: BPR is a 32-bit i386 remaster. |
| RenderWare 4 | ARTIST for behaviour and game-facing structure, DecFIGS for declaration names and shapes; the vocabulary lives in `b5-decomp/vendor/renderware/include/rw/`. | Structural drift imported from another RenderWare revision. |
| burnout.wiki (`python tools/work/wiki_index.py --lookup <Type>`) | Field names, types and semantics: adopt its member names directly. | Offsets and member placement: only the pseudocode/asm decides those. |
| External PS3 export | A second opinion on names and pseudocode; it often covers an X360 export hole. | Layout. |
| The supplemental RenderWare object (`rwtypes_master.obj`) | x64 RenderWare ABI corroboration. | Paradise structure or behaviour. |

## 3. Identity

- **Identity is the normalized qualified name** (`Namespace::Class::method`), not an address.
  Never assume an address means the same thing in two builds.
- X360 names come demangled; PS3 names are Itanium-mangled with a `.` prefix
  (`._ZN6Attrib8TypeDesc6LookupEy`): strip the dot, demangle, drop the parameter list.
  `progress/identity.json` is the left join anchored on X360.
- Overloads collapse onto one key (identity keeps every address). IDA truncates some X360
  names (`GetPl`, `...::GetMemor`): a prefix match is a candidate, never a match.
- No global structural matching (Diaphora, BinDiff) as a prerequisite. Names join the
  symbolized builds; structural matching is an optional per-function last resort, for an
  unnamed X360 function or a BPR/TUB platform function (anchor it on string literals and
  named neighbour calls).

## 4. Signatures come from the assembly

Hex-Rays regularly gets the signature wrong (parameter count and order, register-vs-stack
passing, the implicit `this`, return type, signedness, value width), especially on PowerPC,
X360 and PS3 alike. When a parameter list, return type or by-ref/by-value choice is
load-bearing, confirm it from the prologue and register usage in the asm
(`work show <tu> --full --asm`, and always in `work postmortem <tu>`). When the X360 asm is
ambiguous, cross-check the same function's asm and DWARF in the DecFIGS / External PS3 exports.

The recurring traps (an f32 argument eating a GPR slot, a CgsID swallowing every later
argument, vector arguments in `v1`, fused literals, VMX operand order, the VMX128 `vA` field):
[references/reading-ppc.md](references/reading-ppc.md).

## 5. Reading the exports

- `.ida-exports/<build>/0x<addr>.json` (local input, one file per function) carries `address`,
  `name`, `prototype`, `variables`, `pseudocode`, `assembly`, `xrefs_to` and `xrefs_from` (each
  xref an `{address, name}` object). Build folders: `BURNOUT_X360_ARTIST.XEX`,
  `DecFIGS_Burnout_Internal_PS3.ELF`, `Burnout_External_PS3.ELF`,
  `Burnout_External_Xbox_One.exe` (its `name` is the MSVC-mangled form), `BurnoutPR.exe`,
  `TUB_Burnout_PC_External.exe`, `rwtypes_master.obj`, `B4Extern`.
- **A search started at the repo root silently skips `.ida-exports/`**: it is gitignored and
  ripgrep-based search tools honour that, so "no files found" there means nothing. Point the
  search at the build folder itself, or use a shell or Python. A recursive grep over the BPR
  folder times out: index it once with `tools/ida/export_index.py`.
- **The export set has holes.** IDA knows functions whose JSON was never written; they have
  no ledger row and look exactly like an ICF fold or an inlined body. A hole's name sits in
  its callees' `xrefs_to` and its callers' `xrefs_from`; `ppcdis.py` gives its body. Sorting
  the export addresses finds them: a gap between one function's last instruction and the
  next file's address is an unexported function.
- **The exports carry no data.** A constant shows as `flt_`/`unk_`/`dword_8xxxxxxx` with no
  value: read it with `x360rd.py`. A `.bss` slot reads 0 **by definition** (a CRT thunk or a
  first-call cache fills it: `findinit.py`); a slot that reads non-zero is initialised `.data`
  and has already answered.

## 6. What the audits cannot see

`funcaudit`, `stubaudit` and `asmaudit` compare what each side names. They cannot see inlined
callees, virtual dispatch, argument order, field offsets, the arithmetic between constants, or
the value of a cited constant. A clean audit means "nothing nameable differs", never "matches";
an asmaudit tier C is a diff to read, not a verdict. Cover the blind spots with
`vdispatch_audit.py` (dispatch), `constaudit.py` and `findinit.py` (values), and the asm itself
(argument order, offsets).

## Never

- Never let a lower rung override a higher one, or a 32-bit build arbitrate an Apt pointer
  width or offset over the x64 build.
- Never take a load-bearing signature from the pseudocode: read the asm.
- Never trust a wiki offset over the pseudocode; a reviewer fails it.
- Never import a DWARF member or method that the X360 ledger does not attest.
- Never adopt B4Extern or BPR layouts wholesale: they corroborate, they are not the source.
- Never compare addresses across builds: join on the qualified name.
- Never read "no hits" as absence until the same search has found a known positive, and
  never from a repo-root search over `.ida-exports/`.
- Never blanket-correct VMX128 registers by ±32: decode the fields.
- Never treat a clean audit, or an image-reading tool's self-test, as proof.
- Never run another build of the game to learn its behaviour: other builds are evidence to
  read, and the method is decompilation.

## Tools: which one answers which question

Under `tools/re/` unless a path says otherwise. Flags, inputs, outputs, false-positive classes
and hazards (some of these tools rewrite tracked files when run bare):
[references/tools.md](references/tools.md).

| Question | Tool |
|---|---|
| What does the console function do; what does this TU need? | `work show <tu> --full --asm [-o FILE]` |
| What does the console state that our body does not (case ids, event posts, named callees, asserts, missing bodies)? | `work audit <tu> [--refresh]`; `funcaudit.py --func NAME` (or `--tu`, `--dir`, `--all`) |
| Which bodies are still stand-ins, and does a live caller reach one? | `stubaudit.py --file F` (or `--dir`, `--tier`) |
| Does the exe we built have the console's shape (callees, branches, constants)? | `asmaudit.py --func NAME [--asm]` |
| Exact PowerPC diff of a portable function | `asmmatch.py NAME --decfigs` (or `--listing`, `--compile`) |
| Is a cited constant's value right? | `constaudit.py [--wide] <src subtrees>`; `constaudit.py --symbol <hex>` |
| Who fills a `.data`/`.bss` slot that reads 0? | `findinit.py <hex>`, then `ppcdis.py` on the writer |
| Does a definition exist anywhere in the tree? | `hasbody.py <Class::Method> [--status]` |
| Disassemble a function the export set lacks | `ppcdis.py <hex> [n]` |
| Read image bytes, a table, a float | `x360rd.py <hex> [nbytes]` |
| Decode VMX128 register fields | `vmx128.py --func <hex>`; `vmx128.py <hex> <n>` |
| Which vtable slots does this console function dispatch? | `vdispatch_audit.py <hex>...`; `--dir src/<dir>`; `--vtable <hex> [n]` |
| Who dispatches through vtable slot N? | `vcallsites.py <slot-hex> --name` |
| Which console overrides does our class lack? | `progress/VTABLE_OVERRIDE_AUDIT.md`; `vtable_override_audit.py --table <hex>` |
| Which console callees are declared here and defined nowhere? | `progress/SILENT_LINK_INVENTORY.md` (regenerated by `silent_link_sweep.py`) |
| A console byte offset applied to a widened host object? | `widening_sweep.py --root src/<dir>` |
| Which wiki fields does a type have? | `tools/work/wiki_index.py --lookup <Type>` |
| A PDB type's layout | `llvm-pdbutil pretty -classes -class-definitions=layout -include-types="<regex>" <pdb>` |
| Is a name anywhere in an export set? | `tools/ida/export_index.py <export_dir> <out_base>`, then search the `.tsv` |

## Read next

- [references/ladder.md](references/ladder.md): every ladder rule and exception, with its reason.
- [references/reading-ppc.md](references/reading-ppc.md): ABI and Hex-Rays traps, VMX, data, vtables.
- [references/tools.md](references/tools.md): per-tool flags, inputs, outputs, false positives, hazards.
- [diagnose-parity-bug](../diagnose-parity-bug/SKILL.md): the triage that puts these tools in order.
- [reconstruct-tu](../reconstruct-tu/SKILL.md) for writing the code, [review-tu](../review-tu/SKILL.md)
  for reviewing it.
