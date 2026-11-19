# The evidence tools, one by one

For each tool: the question it answers, how to call it (every flag checked against its
`--help` or its source), what it needs, what it writes, and how it misleads. Run from the
repository root. Tools live in `tools/re/` unless the path says otherwise.

## Before running anything: hazards

- **Several tools have no argument parser, so `--help` is not help.**
  `vtable_override_audit.py` and `silent_link_sweep.py` treat any unknown argument (including
  `--help`) as a full run that **rewrites tracked inventories under `progress/`**;
  `tools/work/wiki_index.py` with any argument other than `--lookup <Type>` rebuilds
  `references/Wiki/types.json`. For these, the source header is the help.
- `asmaudit.py` without `--func` or `--pack-exports` writes its report to the `--out` stem, whose
  default overwrites the CI-committed `progress/asmaudit.json` (and writes a `.md` beside it). Pair
  `--tu` with `--out scratch/<name>`.
- **Repo-root searches skip `.ida-exports/`** (gitignored; ripgrep-based tools honour that) and
  return a confident empty result. Search the build folder itself, or use a shell or Python.
- **A sweep you have not seen find a known instance is not a sweep.** Use the built-in positive
  controls (`silent_link_sweep.py --control`, `vtable_override_audit.py --control`,
  `widening_sweep.py --self-test`, `findinit.py --check`), and give any ad hoc search a
  known-positive target first.
- Image readers (`x360rd.py`, `ppcdis.py`, `findinit.py`, `vmx128.py`, `vcallsites.py`) need the
  ARTIST image, a local input: `artist_i64.raw` beside `tools/re/x360rd.py` or at `$BRN_ARTIST_RAW`,
  or a flat dump at `$BRN_IMAGE_BIN`. `vtable_override_audit.py` can unpack one from
  `IDA Files/BURNOUT_X360_ARTIST.XEX.i64` into the temp folder itself.

## Committed evidence (read before regenerating)

| File | Holds | Produced by |
|---|---|---|
| `progress/identity.json` | qualified name → X360 addresses, PC `primary_file` | the identity build |
| `progress/funcaudit.json` | every paired function's console-vs-ours findings | CI, per b5-decomp commit |
| `progress/stubs.json` | every stand-in body, tiered, with live-caller flags | CI, per b5-decomp commit |
| `progress/asmaudit.json` | every built function's instruction-shape tier | the build job, per published exe |
| `progress/funcaudit_features.json.gz` | the packed console feature cache (funcaudit/stubaudit without exports) | repacked when the export set changes |
| `progress/asmaudit_artist.json.gz` | the packed console fingerprints for asmaudit | `asmaudit.py --pack-exports` |
| `progress/SILENT_LINK_INVENTORY.md` (+ `progress/silent_link_inventory.json`) | declared-here, defined-nowhere console callees, classes A/B/C | `silent_link_sweep.py` |
| `progress/VTABLE_OVERRIDE_AUDIT.md` (+ its `.json` twin) | console overrides our classes lack; hand verdicts in `tools/re/vtable_override_verdicts.json` | `vtable_override_audit.py` |

Each report names the b5-decomp revision it was generated against: if the tree has moved, a
row may already be fixed or newly wrong.

## The dossier and the per-TU audit (`work`)

- `work show <tu>`: concise overview (functions, signatures, dependency TUs, the console audit
  block). `work show <tu> --full [--asm] [-o FILE]`: the full dossier (pseudocode, locals, DecFIGS
  dwarfdump hints, LegacySrc source, callee signatures, matching wiki tables under
  `--- WIKI TYPES ---`); `--asm` adds the disassembly.
- `work postmortem <tu> [-o FILE]`: the dossier with asm plus the ladder checklist. When to run it
  is [reconstruct-tu](../../reconstruct-tu/SKILL.md)'s business.
- `work audit <tu> [--items N] [--refresh]`: takes a TU id or a bare source file. Prints the TU's
  funcaudit findings per function, the stub bodies in its file and its asmaudit rows worst-first,
  read from the committed files above. `--refresh` re-runs funcaudit live for the TU's file from
  the packed cache (no exports needed; output under `scratch/funcaudit/`). High-signal categories:
  `NO_BODY`, `MISSING_CASE`, `EXTRA_CASE`, `MISSING_EVENT`, `MISSING_CALLEE`, `MISSING_ASSERT`.
  Context only: `MISSING_EVENT?`, `MISSING_STRING`, `UNCITED_DATA`, `FEWER_PARAMS`, `INFO_*`. A
  function with a high-signal finding is not verified, whatever the ledger says.

## Static comparison against the console

### `funcaudit.py`: what the console states that our body does not

`--all` | `--dir DIR` (PC `primary_file` prefix, repeatable) | `--tu FILE` (exact `primary_file`,
repeatable) | `--func Class::Method` (repeatable); `--out PREFIX` (default `scratch/funcaudit/<stamp>`),
`--min-lines N`, `--no-info`, `--cache FILE` (default `scratch/funcaudit/exports.cache.json`; a
`.gz` is read-only), `--meta k=v`, `--no-md`.

- Needs `pip install -r tools/re/requirements.txt` (tree-sitter). Without exports, use
  `--cache progress/funcaudit_features.json.gz`; with exports, the first run builds its cache (slow).
- Findings: `NO_BODY`, `MISSING_CALLEE` (named console callee our code never names; "(comment
  only)" when only a comment does), `MISSING_CASE`, `EXTRA_CASE` (a case id the console never
  mentions: a misfiled id), `MISSING_ASSERT` (usually an absent arm or a silent early-out),
  `MISSING_STRING`, `MISSING_EVENT` (an `AddEvent` id we never post), `UNCITED_DATA` (a console data
  symbol our body never cites), `FEWER_PARAMS` (hint only). Bodies containing `[FLAG` are marked.
- It merges PC-only helpers (same file, no console identity, two levels deep) before declaring
  something missing, and pairs on the exact qualified name only.
- Noise: truncated callee names; `FEWER_PARAMS` overcounts (the f32 ABI); `MISSING_STRING`
  includes pure log lines; a console callee inlined by hand reads as missing; header-inline
  operators can read `NO_BODY`.

### `stubaudit.py`: which definitions are still stand-ins

`--dir DIR` (repeatable) | `--file FILE` (exact path under `b5-decomp/src`, repeatable);
`--tier high|medium|low` (lowest tier reported), `--out PREFIX` (default
`scratch/funcaudit/stubs_<stamp>`), `--cache FILE`, `--meta k=v`, `--no-md`.

- HIGH: a `*Stub*` file, a trapping body (`CGS_ASSERT(false ...)`, `__debugbreak`), or an explicit
  marker (link scaffold, PC-platform leaf, not reconstructed, honest stub ...). MEDIUM: a trivial
  body (empty, constant return, only `(void)` casts, or hollow: only latches a function-local
  static) under a soft marker (stand-in, placeholder, bring-up, `DELETE-WHEN`, `[FLAG`). LOW: a
  trivial unmarked body whose console function is not trivial.
- The priority column is "a reconstructed caller reaches it": that stub runs wrong today.
- Not covered: a function defined nowhere (`silent_link_sweep.py`, funcaudit `NO_BODY`).
- Misleads when a banner above a real body talks about another function ("not reconstructed"):
  read the quoted reason. A trivial body can be faithful: compare the console's line count.

### `asmaudit.py`: does the exe we built have the console's shape

`--func NAME [--asm]` (one function: both fingerprints, the diff, the score; `--asm` prints both
instruction streams) | `--tu FILE` (functions filed under one source file) | default whole-exe
audit. `--exe` / `--map` (default `build/game/Burnout_PC.exe` / `.map`), `--pack FILE` (default
`progress/asmaudit_artist.json.gz`), `--pack-exports` (rebuild the pack from the exports, then
exit), `--exports DIR`, `--out STEM` (default: the stem of `progress/asmaudit.json`), `--meta k=v`,
`--no-md`.

- Needs a built exe and its map, plus `capstone` and `pefile`.
- Score `0.45 calls + 0.35 cond + 0.2 imm`. Tier A ≥ 80 (same shape), B ≥ 55 (close), C < 55
  (diverges), T trivial, X named by the ledger but absent from the exe. Indirect calls are shown,
  not scored.
- A tier A is "same calls, branch count and constants", not a match: argument order, offsets and
  the arithmetic between constants are invisible. A tier C is a diff to read: a callee MSVC
  inlined shows as "only on the console"; a constant we never load is exactly what it looks like;
  a PC body folded to a bare `ret` against a real console body is a silent stub.

### `asmmatch.py`: exact PowerPC instruction diff

`asmmatch.py <func> [--decfigs] [--listing FILE.asm [--dec DECORATED]] [--compile SRC [--sdk XEDK]
[--cl-arg ARG]] [--loose] [--quiet]`. `<func>` is a canonical name or a unique suffix.

- `--decfigs` diffs ARTIST against the PS3 DecFIGS rendering of the same function: another
  compiler on the same source, so a low score is normal; it calibrates the scorer.
- `--listing` takes our body compiled by the Xbox 360 SDK compiler; `--compile` drives that and
  needs the SDK (`$XEDK`), which is rarely installed. `--loose` masks load/store displacements (the
  x64 widening) to show whether anything else differs.

### `constaudit.py`: are the cited constants right

`constaudit.py [--wide] <subtree> [...]` (subtrees under `b5-decomp/src`); `constaudit.py --symbol
<hex> [...]` resolves symbols and stops.

- Re-derives every `K<F|I|D>_NAME = <number>; // <sym>_8XXXXXXX` from the image (initialised data
  directly, `.bss` slots through their CRT thunk). `--wide` also checks member initialisers, inline
  literals, integer and colour constants, constant expressions, call-argument tuning tables, and
  lazy first-call caches. The default net sees a fraction of what `--wide` sees.
- A worksheet, not a verdict. Its false-positive classes (unit conversion in the thunk, chained or
  multi-operand thunks, anchor-register displacement, `f64` width, guard-versus-slot) are spelled
  out in its header and in [reading-ppc.md](reading-ppc.md): dump the thunk with `ppcdis.py` before
  changing a number. A thunk that runs before its dependency is filled yields a faithful zero.

### `findinit.py`: who writes a silent-zero slot

`findinit.py <hex> [<hex> ...]`; `findinit.py --check` (self-test on two known controls).
Prints every site that materialises the address (`lis`/`@l` pairs). Readers are in game code; the
writer is the outlier in the CRT init bank: disassemble it with `ppcdis.py`. Its register tracker
is conservative, so it can miss a site, never invent one: corroborate a recovered value against
its role.

## The tree

### `hasbody.py`: does a definition exist

`hasbody.py <Class::Method> [...]`; add `--status` to print the ledger's claim for contrast. Exit
code 1 when any name has no definition. Searches `b5-decomp/src` and `b5-decomp/vendor`, separates
definitions from comment and declaration mentions (a bare `grep name(` does not), and falls back
to bodies inside `namespace X { }` blocks or class definitions ("HAS BODY (unqualified ...)":
check the scope and signature yourself). It answers "is this name defined", not "is the body
real" (`stubaudit.py`), "is its TU mounted" (search `tools/build/build_game_exe.bat` for the file),
"is it declared in a header, so callable", or "is the other overload defined".

### `widening_sweep.py`: console offsets on widened host objects

`--root src/<dir>` (under `b5-decomp`, repeatable) | `--all-roots`; `--asm` (corroborate each offset
against the paired X360 asm), `--severity all|silent|fatal`, `--base all|this|local` (`this` is the
decidable class), `--compact`, `--unpinned` (only numbers no `static_assert` pins: the short list),
`--shifts` (also `>> 2` / `<< 2` pointer-slot leads; noisy), `--show-exempt`, `--min-offset N`,
`--self-test`. Tracks byte-pointer aliases of an object plus named offset constants, not just
literals. SILENT hits (read as data, never dereferenced) are the priority: they never fault.
Serialised records are exempt by design.

### `idfield_sweep.py`: which id field a body keys on

`--root src/<dir>` (repeatable), `--all`. Compares, per function, which of two same-typed id
members the console's asm loads and which one our body names. It is wired to one pair (the
handling-body id versus the global entity id on `DeformableObject`) and narrows, never decides:
the worked example for the misnamed-field class.

### `template_static_sweep.py` and `tools/work/find_local_redefs.py`: forks

`template_static_sweep.py [path ...]` (default `b5-decomp/src`) lists `static` locals inside
template bodies: one object per instantiation where the console has one word.
`python tools/work/find_local_redefs.py [--summary]` lists local struct/class definitions in
`.cpp` files whose type already has a real header. Both are triage: read each hit.

## The image

### `ppcdis.py`: disassemble a function the exports lack

`ppcdis.py <hex> [n]` (default 200 instructions). Reads the image through `x360rd.py`, decodes with
capstone, names branch targets and globals from `progress/identity.json` and
`tools/re/extra_names.json`. A disassembler: there is no pseudocode for a hole.

### `x360rd.py`: read image bytes

`x360rd.py <hex> [nbytes]` (default 16): big-endian words with their f32 reading. Also a library
(`rd`, `u32`, `f32`, `_segs`) for ad hoc scans. Its self-test is necessary, not sufficient.

### `vmx128.py`: VMX128 register fields

`vmx128.py --func <hex-entry>` (whole function, listing from the export) | `vmx128.py <hex-start>
[n]` (default 32). Prints the raw `vD`/`vA`/`vB` fields beside IDA's text and marks a wrong `vA`.
A cross-check, not a disassembler; the `vA` column is an immediate on some forms.

## Virtual dispatch

### `vdispatch_audit.py`: the slots a console function dispatches

`vdispatch_audit.py <hex> [...]` | `--dir <path under b5-decomp>` (every console address cited in
that C++) | `--vtable <hex> [n]` (name a table's slots; default 48). Per hit: the slot, the base it
dispatches on (`r30+0x194C`), and the defining `lwz`. A linear scan, not dataflow.

### `vdispatch_sweep.py`: console slots against our virtual calls

`vdispatch_sweep.py <subtree> [...]` (under `b5-decomp/src`; default `GameSource/Physics`). A
worksheet: read the rows whose counts differ first, then the rows whose names look implausible
for the slot.

### `vcallsites.py`: who dispatches slot N

`vcallsites.py <slot-hex> [--name]`. Every `lwz rA,<slot>(rB) ... mtctr ... bctrl` site image-wide;
`--name` resolves each to its containing function. Slots are shared across hierarchies, so expect
many hits and narrow by function. CTR dispatch only.

### `vtable_override_audit.py`: console overrides our classes lack

`--table <hex>` (one table, slot by slot) and `--control` (known cases must come back) leave the
tree alone. A bare run regenerates `progress/VTABLE_OVERRIDE_AUDIT.md` and its `.json` twin;
`--src DIR`, `--image FILE`, `--rebuild-cache` adjust it. Only class `MISSING` asserts a
behavioural hole by itself; ICF, truncated and clipped-name classes need a human. Read
`tools/re/vtable_override_verdicts.json` for rows already judged by hand.

### `silent_link_sweep.py`: declared here, defined nowhere

A bare run regenerates `progress/SILENT_LINK_INVENTORY.md` and `progress/silent_link_inventory.json`;
`--control` re-runs it against a historical tree in a temp folder and asserts the seed bugs come
back; `--src DIR` sweeps another checkout. Class A (a mounted caller of ours) is running wrong now;
B is latent; C has no direct named caller, which is not absence (virtuals have no `xrefs_to`:
resolve with `vcallsites.py`). "Mounted" is not "executed"; a name shared by two classes can mask
a miss; an overload set with one defined member reads as defined.

## Names, types and other builds

- `python tools/work/wiki_index.py --lookup <Type>`: the wiki's tables for a type, build-tagged
  (`*` marks a Paradise-era page). Names and semantics only.
- `python tools/ida/export_index.py <export_dir> <out_base>`: index an export folder into
  `<out_base>.tsv` (address, name, xref counts, sizes, prototype), `.edges` and `.floats`. Put
  `<out_base>` under `scratch/`. Settles "is this name anywhere in the set" before anyone writes
  "absent".
- `python tools/ida/find_by_signature.py <export_dir> [--sig NAME] [--validate <hex>] [--top N]`:
  find a known function in a stripped build by a control-flow signature. Validate on a build
  where the answer is known first: a signature that does not rank the known answer first is not a
  signature.
- `llvm-pdbutil pretty -classes -class-definitions=layout -include-types="<regex>" <pdb>`: class
  layouts from a PDB (the X360 audio PDB for `rw::audio::core`, B4Extern for Apt). An LLVM tool, not
  shipped in this repository.
