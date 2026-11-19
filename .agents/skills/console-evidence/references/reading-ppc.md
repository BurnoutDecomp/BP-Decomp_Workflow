# Reading PowerPC, Hex-Rays and the image

The traps that have produced wrong reconstructions on this project, and how to read past
them. The asm wins over the pseudocode every time they disagree.

## Calling convention, from the asm

Check, from the prologue and the register traffic at each call site:

- **Parameter count and order.** `r3` is `this` for a member function; integer and pointer
  arguments follow in `r4`, `r5`, ... A parameter the prologue never reads before writing is
  a candidate phantom (below).
- **Float arguments** travel in `f1`, `f2`, ... and **also consume the matching integer slot**:
  `(this, u32, f32, const u32*)` occupies `r3, r4, f1/r5, r6`.
- **Vector arguments** arrive in vector registers: a function that opens with `vmr128 v124, v1`,
  and whose caller loads `lvx128 v1, ...` right before the call, takes a vector by value.
- **Stack arguments** exist: check for loads from the caller's frame before trusting a short list.
- **Signedness and width**: `lbz`/`lhz` zero-extend, `lha`/`extsb`/`extsh` sign-extend, `cmpw`/`cmpwi`
  compare signed, `cmplw`/`cmplwi` unsigned, `clrlwi` masks. A `CgsID` is one 64-bit GPR (`ld`/`std`).
- **`rA = 0`** in a D-form or X-form instruction (`addi`, `lwz`, `lwzx` ...) means the literal 0,
  not register `r0`.
- **Adjustor thunks** (`addi r3, r3, -N; b <target>`) change `this` before the body runs.

When the X360 asm is ambiguous, read the same function in the DecFIGS / External PS3 exports
(another PowerPC compile, with DWARF names); a PS3 mangled name can correct a parameter type.

## Hex-Rays traps

- **Phantom parameter from the f32 ABI.** Because a float eats an integer slot, Hex-Rays sees an
  untouched GPR and invents a parameter for it. The tell: the callee never reads it and every
  call site passes a literal `0`. The DWARF settles the count; `funcaudit.py`'s `FEWER_PARAMS` is
  only a hint for the same reason.
- **Arguments dropped after a CgsID.** Hex-Rays renders the 64-bit GPR as one `__int64` and can
  discard every parameter after it. Treat the pseudocode prototype of any CgsID-taking method as
  noise: recover the signature from the asm.
- **Vector arguments vanish.** A prototype that looks suspiciously empty may take a `Vector3` in
  `v1`: check the entry and the caller.
- **Calls duplicated or collapsed.** Hex-Rays has shown one call duplicated into every switch arm
  where the asm has a single call site, and two different calls rendered with one signature when
  each site builds different arguments. Read each call site's argument setup.
- **Fused wide literals.** A suspicious 64-bit constant is often two operands glued together (an
  unrelated `li` merged into the low word of a store). Decode the raw words before writing a
  constant down, especially when the high half equals a nearby structure offset.
- **Stack spills shown as member writes.** A constructor "writing" uninitialised registers into
  members is usually prologue spills and loop-counter setup. Read the asm.
- **Indexed stores have no literal.** `stwx`/`stdx`/`stbx` render as `*(_R31 + HIDWORD(v74)) = v74`:
  no offset appears in the pseudocode, so a literal grep over pseudocode cannot find the writer.
  Scan the assembly; scan for any literal within a byte range, not one spelling; derive a range's
  base from its start and confirm it against the asm's own `addis`/`addi` pair.
- **Folded constants.** A literal read off a pseudocode site can be a folded or strength-reduced
  form of the real constant (an epsilon recorded one decimal place too small): read the value
  from the image symbol.
- **Names.** IDA truncates long qualified names, and ICF gives one body several names (it prints
  whichever it picked).
- **Argument evaluation order.** When arguments have side effects (random draws), the console's
  order is whatever its asm does (one function drew `z`, `y`, `x`). Write side-effecting arguments
  as separate statements in the asm's order; C++ leaves the order unspecified.

## VMX and VMX128

- **Classic VMX** (opcode 4, plain five-bit register fields): IDA prints operands in raw field
  order `vD, vA, vB, vC`. That is the ISA definition, not an IDA bug:
  `vmaddfp vD, vA, vB, vC` is `vD = vA*vC + vB`; `vnmsubfp vD, vA, vB, vC` is `vD = vB - vA*vC`;
  `vsel` and `vperm` print in the same raw order. Reading left to right gets every expression wrong.
- **VMX128 fused forms** carry three registers and IDA prints a phantom fourth (the implied
  accumulator): `vmaddcfp128 vD, vA, vD, vB` is `vD = vA*vD + vB`, and `vnmsubfp128 vD, vA, vB, vD`
  is `vD = vD - vA*vB`, the opposite of the classic `vnmsubfp`. A `128` suffix means re-derive the
  operand roles.
- **The VMX128 `vA` field.** IDA swaps the two high bits of the `vA` field (one worth 32, one worth
  64) and only that field: `vD` and `vB` always print correctly. So the printed `vA` is wrong by
  ±32 exactly when one of those two bits is set, and right when both or neither are. Never
  blanket-subtract 32 (the old "+32" rule was this symptom). `python tools/re/vmx128.py --func <hex>`
  prints the raw fields beside IDA's text and marks a corrected `vA`. Let semantics referee: a
  corrected register that still has no defining instruction means the correction was wrong, and
  the save helper constrains the set (a function calling `__savevmx_124` may only touch v0-v13,
  v32-v63 and v124-v127).
- **Form-dependent fields.** `vrlimi128 vD, vB, MASK, SHIFT` keeps its mask in the `vA` slot (mask
  bits 8/4/2/1 = x/y/z/w); single-source forms (`vrfin128`, `vcsxwfp128`, `vrefp128`,
  `vspltisw128`) carry their source in `vB`.
- **No FPR-to-VR move.** Every float-to-vector splat round-trips through the stack (`stfs`, then
  `lvx`/`lvlx`, `vspltw`). Collapse that idiom before judging a body by its instruction count, and
  map stack-assembled vectors lane by stack offset.
- **Swizzles.** VMX selects lanes with `vperm` against an `.rdata` permutation table, so a second
  PowerPC build hides exactly the lane choice; an x86-SSE build (BPR) encodes it as an immediate.

## Data out of the image

- `python tools/re/x360rd.py <hex> [nbytes]` prints big-endian words with their f32 reading. Its
  data file is a local input (`artist_i64.raw` beside the script or at `$BRN_ARTIST_RAW`, else a
  flat image at `$BRN_IMAGE_BIN`). If neither exists, regenerate one: never conclude that image
  data is unreadable.
- **A reader is a claim.** An earlier reader passed its own self-test while mis-calibrated by 1594
  bytes. Corroborate a value with a second, independent derivation: an in-tree `static_assert`, the
  stride between adjacent statics, the DWARF, or a decode that reproduces a known listing
  instruction for instruction.
- **`.data` or `.bss`.** A slot that reads non-zero is initialised data: the image word is the C++
  initialiser. A slot that reads 0 is filled at run time by one of:
  - a CRT static-init thunk: `python tools/re/findinit.py <hex>` lists every site that materialises
    the address (`lis`/`@l` pairs); the writer is the outlier in the CRT init bank; disassemble it
    with `python tools/re/ppcdis.py <hex> [n]` and read the `lfs` source with `x360rd.py`;
  - a lazy first-call cache (a function-local `static` guard): one reference site, the guard's
    conditional branch, then the `lfs` within a few instructions;
  - a `CgsNumeric::CreateFloatVector` / `CreateIntegerVector` initialiser;
  - ordinary game code: the slot is genuinely stateful and has no compile-time value.
- **Thunk-decode pitfalls** (`constaudit.py`'s false-positive classes): a unit conversion inside
  the thunk (mph to m/s, degrees to radians: the source correctly holds the product); chained or
  multi-operand thunks (a divide, a `cos`, several lanes, a source that is itself a `.bss` slot:
  dump the thunk and read it); anchor-register displacement (IDA names a base register after one
  `.rdata` word and the body loads `(flt_OTHER - flt_ANCHOR)(rBase)`); width (an `f64` is 8 bytes);
  a guard word mistaken for the slot.
- **Static-init order.** Finding the thunk is half the job: place it in the CRT initialiser table
  relative to its dependencies. A thunk that runs before the slot it reads produces 0 on the
  console, and reproducing that 0 is correct.
- "No writer among the exported functions" is the expected result for every dyn-init slot: the
  thunks are not in the export set. When the X360 image will not settle a constant, the PS3 twin
  may reach it through its TOC.

## Finding callers and writers

- `xrefs_to` names the exported callers. A virtual has none (it is reached through a vtable): use
  `vcallsites.py` and the vtable notes below.
- An unnamed `sub_` body is identified by its caller set and order, and by its asserts' own
  `__FILE__`/`__LINE__` strings.
- Callers the exports miss: scan `.text` for `bl <target>` (primary opcode 18, LK set,
  sign-extended LI), then walk back to the enclosing prologue (`mflr r12` = `0x7D8802A6`). The
  nearest preceding ledger symbol is often an adjustor thunk and misattributes the hit.
- The producer of an event or action id: scan the image for `li rX, <id>` (`addi rX, r0, imm`, i.e.
  `(w & 0xFC1FFFFF) == (0x38000000 | id)`). Walk `x360rd`'s segment map: the raw image is not a
  flat `0x82000000` map, and a flat scan silently returns zero hits. Validate any scanner against a
  site you have already disassembled before trusting a zero.
- A writer can hide behind a different local name or a `memcpy` into a payload offset: search by
  offset and by the value written, not only by the member's name.

## Vtables

- A console dispatch is `lwz rV, 0(rObj)` (the vptr), `lwz rT, N(rV)` (slot N), `mtctr rT`,
  `bctrl`. `python tools/re/vdispatch_audit.py <hex>` lists every slot a function dispatches and on
  which base, in order (a linear scan, not dataflow: check the defining `lwz` it prints).
- **Read the slot index, never the printed name.** Identical one-line bodies (`return false`,
  `return true`, `{}`) are ICF-folded onto unrelated functions, so IDA prints a foreign name in the
  slot. An image-wide empty fold is not `_purecall`: declaring that slot pure makes the class
  abstract or routes live calls into `_purecall`.
- Slot numbers are per hierarchy: name a slot only against the concrete table of the dispatched
  object's class.
- Which table holds a function: scan the image for 4-byte words equal to its address (a virtual is
  normally in exactly one table), then `vdispatch_audit.py --vtable <table> [n]` lists its slots.
  **If slot 0 is an `adjustor{N}` thunk**, the table belongs to a secondary base and every virtual
  in it receives `this == primary + N`: add N to every offset the body uses before calling two
  functions' layouts irreconcilable. The slot order should reproduce the DWARF virtual order.
- A tail-called virtual (`bctr`, no link) and a devirtualised direct `bl` are invisible to
  `vcallsites.py` and `vdispatch_audit.py`: no hit is not proof of no caller.
