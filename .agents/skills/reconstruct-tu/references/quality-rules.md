# Reconstruction quality rules

How to write the C++ in `b5-decomp/src`. Which evidence wins is `console-evidence`; this
file says how to write what the evidence tells you. Reviewers enforce the same list
(`review-tu`). Subsystem rules (vendor SDKs, Apt, RenderWare 4, `rw::audio::core`) are in
[subsystem-rules.md](subsystem-rules.md).

The goal is to reconstruct what the original C++ source **looked like**, not to translate
raw decompiler output literally.

## Members and layout

- **No raw offset pointer hacks.** Never access a member through a raw offset cast
  (`*reinterpret_cast<Type*>(lThis + offset)`, `*(int*)(this + offset)`) or an offset helper
  lambda (`Word(offset)`). Recover the type and access the member by name.
- **Exception: external serialised / platform data.** Raw offset access is allowed, and
  expected, for serialised file-format blobs and other external byte streams whose layout
  is fixed by the data, not by a C++ class: a RenderWare resource blob walked during fix-up
  (`*(u32*)(lRes + 68)`), `rw::collision` data. Document it inline. It covers the data
  being processed; the rw runtime objects themselves (`rw::Resource`) still get named
  members (recover the type per the RenderWare rule in subsystem-rules.md).
- The faithfulness lint exempts an offset access whose own line mentions serial, blob,
  file-format, bnd2, `.apt`, resource header, external data, byte stream or `FLAG`. Use that
  only for the exception above; reviewers fail it anywhere else. A named constant in place
  of the literal (`p + KU_FOO`) is still an offset hack.
- **Layout recovery with padding.** Infer class and struct members from the offsets
  accessed. Where the preceding members are unknown, keep alignment with an explicit
  padding buffer (`u8 mPad0[1812];`). Access every member by name.
- **The compile target is x64: parity by named members, not byte offsets.** Model named
  logical members (mutexes, list anchors, sub-objects); padding stands only for unrecovered
  spans between known members. Do not build giant byte-exact padded layouts.
- **Widening, decided per struct and per slot.** A pointer slot inside a serialised record
  stays 32 bits on x64 (FixUp rebases it; the record's stride does not grow), so following
  the DWARF's pointer type there reads garbage. A struct carved at runtime widens its
  pointers. A struct with no pointers keeps the console offsets.
- **Widening can break alignment, and no gate sees it.** After widening anything in a
  struct that holds SIMD data, check the alignment of every buffer after it and prefer an
  explicit `alignas`. A raw `u8[]` standing in for a 16-aligned type faults on the first
  by-value copy (aligned SIMD moves).
- A layout `static_assert` proves a **host** size or offset. One that pins a console offset
  on a host-widened object protects a bug; when such a check fights a fix, suspect the check.
- A `u8 maReserved[N]` blob whose comment says its contents "are not recoverable" is a
  hypothesis: check its size against the sum of the candidate members before believing it.
- Do not guess past the end of a struct: an access beyond its proven size means the console
  indexes a type you do not model yet.

## From evidence to code

- **Calling conventions come from the assembly, not the pseudocode.** Hex-Rays regularly
  gets the signature wrong (parameter count and order, register vs stack passing, the
  implicit `this`, return type, signedness, value width), especially on PowerPC. The
  per-function `assembly` is dumped for every build (`.ida-exports/<build>/0x<addr>.json`,
  local input) and surfaced by `work show <tu> --full --asm` and `work postmortem`. When the
  X360 asm is ambiguous, cross-check the same function's asm and DWARF in the PS3 exports.
- **The f32 phantom parameter.** On the X360 ABI a float argument takes an FPR and also an
  integer slot, so a register-counting decompiler invents an integer parameter. The tell: the
  callee never reads it and every caller passes a literal 0. The DWARF settles it; change the
  declaration and let the compiler enumerate the call sites.
- **Which base is `this`.** A virtual found in a vtable whose slot 0 is an `adjustor{N}'`
  thunk is entered with `this == primary + N`: add N to every offset the body uses before
  concluding two functions disagree about a layout.
- **Hex-Rays invents structure.** It renders stack-spill stores and uninitialised registers
  as member writes, duplicates a single call into every switch arm, and can fuse an
  unrelated `li` into a wide literal (a suspicious wide constant is often two operands glued
  together). When the pseudocode looks odd, read the asm.
- **LegacySrc partial source = styling and inlining reference only, not the blueprint.**
  `references/LegacySrc/` (a local input) predates the X360 ARTIST + DecFIGS spine by a long
  way: class layouts, member sets, function boundaries and logic all drift. Do not use it as
  the primary template or copy its structure or layout wholesale. Use it for (a) code style
  and idiom (naming feel, helper patterns, comment style) and (b) outlining inlined
  functions the X360 compiler folded (their shape and names). Authority stays with the X360
  pseudocode + asm (what the code does, its layout) and the DecFIGS DWARF (declaration
  shape); where LegacySrc overlaps, reconcile it to those, never the reverse.
- **Use the DecFIGS dwarfdump hints.** For DecFIGS-backed TUs, `references/DecFIGS/dwarfdump/`
  (a local input, auto-surfaced by `work show --full`) holds C++-shaped DWARF declarations:
  class/struct outlines, enum values, member names and types, globals, function signatures,
  local-variable names and types. It is reconstruction guidance, not complete source, and not
  offset authority: verify member placement and behaviour against the X360 pseudocode/asm.
  LegacySrc is a style cross-check only; where they differ, DecFIGS (the near-ancestor) wins.
  The DWARF sometimes carries the real header: look for it before reconstructing a shape.
- **DWARF supplies names and types; the X360 ledger decides what exists.** DecFIGS is the
  internal PS3 build (Dec-2007) of the FIGS branch, which was merged into main before ARTIST
  (X360 main, Jan-2008) compiled: a near-ancestor, high-confidence for names, types and
  shape, but the merge-window delta means a few PS3 things are not in ARTIST (and vice
  versa). Never bulk-import every DWARF member or method into a recon header. Gate each
  DWARF declaration on X360 attestation: add or correct it only if that `Class::Fn` appears
  in the X360 ledger
  (`progress/status.json` -> `func`), using the DWARF signature for names and types. A DWARF
  method absent from the X360 ledger is PS3-only: leave it out (a minimal, identity-only recon
  can then be correct, e.g. a class X360 exposes only via `GetName`/`GetPath`).
- **The DWARF (or LegacySrc header) declaration is authoritative for a method's shape, not
  just its name.** For a method the X360 ledger attests, take `virtual`, trailing `const`,
  return type, parameter types and vtable order from it, not from Hex-Rays: pseudocode renders
  a virtual call as a direct call, drops `const` and never shows vtable slot order (so
  `virtual uint32_t GetTypeID() const` must not become a plain non-virtual `int`).
- **Diff every class you touch against the DWARF method list.** A class that declares fewer
  virtuals than it has (a hollow shell) compiles, links and runs while every undeclared call
  falls to the base default. A derived class's `Construct`/`OnEnter`/`Update` usually opens
  with a call to the base's function of the same name: the prologue shows the real base. A
  vtable slot holding the image-wide empty-body fold is an empty override, not `_purecall`:
  disassemble the slot before declaring a virtual `= 0`. A member declared non-virtual in the
  derived class does not override.
- **Version-drift trap.** A recon header can declare a whole different class version than
  X360 (typically copied from older LegacySrc, or from the Revenge PDB for Apt). Diagnose by
  intersecting the X360 ledger's function set for that class with both the recon and the
  DWARF: whichever the X360 set matches is the correct version; rewrite the recon toward it.
  A rewrite is blocked if it needs types not yet reconstructed in `b5-decomp/src` (e.g.
  value-passed RenderWare `MaskScalar`/`RGBA`/`VolRef::Volume`), because the sibling `.cpp`
  includes the header and the compile gate would break: leave such headers until those types
  exist (they self-correct when those TUs are worked). Validate any header edit with the
  compile gate (`tools/work/verify.py` `compile_gate`) before considering it done.
- **burnout.wiki is authoritative for field names, types and semantics, never for offsets.**
  The community format docs (`references/Wiki/`, a local input, indexed into
  `references/Wiki/types.json` by `tools/work/wiki_index.py`) already use this project's
  Hungarian convention (`mfLuminance`, `mv4Scale`, `miNodeCount`): adopt their member names and
  types directly. Each page was authored against some build (entries are build-tagged;
  Paradise/PS3 is marked primary and is name-authoritative where the X360 export is missing),
  whose layout may differ from the X360 spine, so the pseudocode/asm is the only source of
  truth for offsets and member placement. The dossier surfaces matching tables under
  `--- WIKI TYPES ---`; look up anything else with `python tools/work/wiki_index.py --lookup
  <Type>`, matching on the namespace-qualified name (a short-name match collides across
  namespaces). When a lookup misses, search the raw dump `references/Wiki/burnoutwiki-*.xml`:
  the index skips some table shapes and page spellings vary. Rebuild the index (run the
  script with no arguments) only when the dump changes. Where wiki and data disagree, the
  data wins. A wiki offset trusted over the pseudocode is a review fail.

## Code shape

- **Eliminate decompiler temporaries.** Do not keep arbitrary decompiler locals (`v1`, `v2`,
  `result`): fold them into clean, logical expressions and rename survivors after their use.
- **Eliminate gotos.** Restructure decompiler gotos into `if`/`else`, `switch`, `while`, or
  `break`/`continue`, unless a goto clearly existed in the original (standard C-style error
  cleanup, rare in this OOD codebase).
- **Logical type restoration.** Restore logical types the compiler reduced to primitives:
  `bool` instead of `int`/`BOOL` for flags, real enum names and values instead of raw integers.
- **Undo compiler optimisations (de-optimisation).** Reconstruct the human-written source:
  - re-roll unrolled loops (duplicated blocks over array indices back into `for`/`while`);
  - reverse inlining (extract inlined utility/helper code back into its own declaration and call);
  - reverse strength reduction (shifts, masks, magic multiplications back to `/`, `%`, `*`);
  - restore tail calls and branches (merged conditions and optimised jumps back into
    `if`/`else`, returns or recursion).
- **Evaluation order is explicit.** When argument expressions have side effects (RNG draws,
  stream reads), take their order from the asm and sequence them into locals: C++ leaves
  argument evaluation order unspecified, and the console's order is part of the behaviour.
- Placement-new into a class that declares its own `operator new` is `::new (p) T(...)`; the
  class operator hides the global placement form (MSVC C2660).

## Types and includes

- **Reconstruct includes; don't fake them (types live in real headers).** When a TU needs a
  type or function from another file, reconstruct that file's header at its mirrored path
  under `b5-decomp/src/` and `#include` it, extending it if it exists. Do not locally
  re-declare, redefine or padding-fork a type that has a real home. Shared headers are global
  state: the compile gate surfaces conflicts, and that error is the desired signal (extend
  the header, don't re-fork it). Recover the layout from `references/LegacySrc/` (where
  in scope) or the DecFIGS dwarfdump (project-wide outlines, gated on
  the X360 ledger). The per-TU gate is `cl /c`: declarations are enough to compile against.
  `work stubs <tu>` names the owning header of each unresolved callee and whether it exists.
- **Why forks are banned:** name mangling encodes a class's name, not its size or bases, so
  a body written against the real class links cleanly against a call site compiled against
  a stand-in, then strides arrays by the wrong size. "It linked" proves nothing.
- **A re-declaration of a type the same header also includes** is either dead or an ODR
  fork: assume nothing from reading it. Derive a base's real surface from a compile probe
  (an `override` only compiles if the base declares it; `tools/_gate_one.bat` compiles one
  file), not from a reduced copy.
- **Never re-declare a base-owned member in a derived class** ("declare-only, owned by the
  base"): it shadows the base member and mangles every call site to a symbol no TU defines.
  Only the full link catches it (`build-and-link`).
- **Never leave `void*` in a signature** where the DWARF names a type: it switches off the
  compiler's fork detection.
- **Publish every body in its header.** A definition no header declares cannot be called,
  and nothing complains.
- **Reconstruct base and contained types before the classes that use them.** A class that
  derives from another (`class B : public A`) or embeds one by value (`struct B { A a; }`)
  needs that type's complete header first: the base's virtuals are the override signatures,
  and a by-value member needs the full layout. These are hard dependencies but not calls, so
  call-graph leaf-first `work next` won't reliably schedule them first: reconstruct the base
  yourself. (This prevents building many leaf handlers as standalone classes and then
  retrofitting a shared base like `CgsResource::Type`.) Inheritance and by-value containment
  edges from the DecFIGS dwarfdump (`tools/work/build_type_deps.py`) are folded into
  `work seed --deps`, so a TU ranks after its bases and embedded types when they are known.
  Type-web code (functions that build complex objects through offsets) needs its struct
  headers recovered before its functions, which call-graph order never gives.
- **Forward declaration is the exception.** Use a local forward declaration, with the reason
  inline, only when (a) it breaks a genuine include cycle (A <-> B); (b) a pointer- or
  reference-only use would otherwise force a large transitive header cascade and an
  incomplete type suffices; or (c) no reference exists to reconstruct the type (truly
  opaque / platform). Otherwise rebuild the header and `#include` it.
- A comment of the form "safe because X never happens" or "until Y is committed" is a
  scheduled failure: re-check it when you widen an include.

## Bodies: stubs, ports and faithfulness

- **Stubs over guesses, for function bodies, not types.** A call to a not-yet-reconstructed
  function gets a trap-stub body (`work stubs <tu>`), not an invented one. The scaffold
  satisfies missing bodies at link time; it is not a way to satisfy a missing type: never
  fake a type with a local stub, reconstruct its header and `#include` it. Working
  leaf-first, most callees are already real when you reach a caller, so even body stubs are
  the exception; under the per-TU `cl /c` gate a callee's declaration is all you need.
- **The trap is the only honest "not done yet".** `__debugbreak()` (what the generators
  emit; `__builtin_trap()` or `CGS_ASSERT(false)` are accepted) declares the function
  unfinished and crashes if reached. `{ return nullptr; }` / `{ return 0; }` / `{}` engine
  bodies, offset hacks and `Class_verb` free-function shims look finished and lie.
- **Port bodies when the reference has them.** When you reconstruct a header and the
  reference has the bodies (chiefly `references/LegacySrc/`), port them too rather than
  leaving trap stubs, then update the ledger for the functions/TUs you thereby complete (run
  their compile gate, record status; never complete work off-ledger). Where bodies are not
  available the callee keeps a trap body as its own TU. Never invent a body.
- **Add nothing the console does not have.** A defensive null check, early-out, default or
  case arm that the asm lacks is an invented arm and can be the bug (one fell off the end of a
  `bool` function). Delete the invention; never invent a return value to go with it. An arm
  copied from a sibling class is invented too.
- **Drop nothing the console has.** A null test repeated after a call that can null the
  pointer is the contract, not redundancy: never hoist a load or its guard across a call that
  writes the thing loaded. Keep every console assert: never downgrade a failing console
  assert to a log because "it cannot matter here".
- **Check each case label against the console**, not just the arm's body: an arm filed
  under the wrong id never runs.
- **Thread the console's real arguments.** Never substitute a "same condition" flag or a
  stand-in value for the argument the console passes.
- **Faithful console bugs stay.** Undefined behaviour in the shipped binary, a constant that
  is zero because of static-initialisation order, a benign over-read the console's layout
  makes safe: reproduce them and leave a note so nobody "fixes" them.
- **Undecoded console data keeps its real shape.** A table the asm reads with a hard-coded
  count keeps that count and its console symbol; recover the values with the data tools
  (`console-evidence`) and never shrink the table to the entries you could read.
- **A placeholder value must be inert.** A flagged stand-in for an unrecovered table must be
  the identity element of the expression it feeds (1.0 for a lerp from 1, 0 for a scale).
- **Cite the console.** Every recovered constant names its console symbol in a comment (the
  audit reports an uncited data read as `UNCITED_DATA`); a known gap or deliberate PC
  divergence carries a `[FLAG ...]` comment so the audit reads it as known.
- **A genuine PC-platform leaf** is marked `// FLAG PC-platform leaf: <reason>` (placement:
  submit-gates.md); only genuinely host-specific code qualifies.
- Compile warnings C4715, C4716 and C4703 are promoted in `tools/build/msvc_flags.txt` on
  purpose: each one (falls off a non-void function, no return, possibly uninitialised
  pointer) is a defect.

## Files and the ledger

- **Mirror original paths.** A function whose `primary_file` is `GameSource/Replays/Foo.cpp`
  lands at `b5-decomp/src/GameSource/Replays/Foo.cpp`.
- **A `class:` TU has no path.** Put it where the class's header and siblings live
  (`progress/class_homes.json` maps class TUs to their committed homes) and pass the file
  with `work submit <tu> --files <path>` the first time.
- **Misattributed TUs.** Some TU ids are a PPC toolchain header path (an inlined intrinsic
  idiom) or a header whose bodies belong in the sibling `.cpp`. Find the real file
  (`progress/identity.json` `decfigs_ps3_addr` -> `references/DecFIGS/decfigs_func_files.json`
  `home_file`, a local input), land the code there, pass it with `--files`, and put
  `corrected path <repo path>` in the TU note (the `--note`/`--notes` you record) so
  reconcile can find the file. `work review --notes` replaces the note: repeat it there.
- **Update the ledger, not your own memory.** Progress that is not in `progress/` did not
  happen as far as the next agent is concerned. The git-ignored `ledger.sqlite` is a cache:
  ground truth for "done" is the reconstructed file committed in `b5-decomp`. `work submit`
  compiles only a recorded `dest_path` or explicit `--files` (an older submit guessed from
  `git status` and marked TUs done with no source). If the ledger disagrees with the files,
  re-anchoring it is `ledger-maintenance` (`work reconcile-from-files`).
- **A committed file is not done if it admits it is unfinished.** "Done" means a complete
  reconstructed file, not necessarily LLM-reviewed: don't mark partials done. Reconcile reads
  explicit incompleteness phrases (for example `TODO: Implement`, `needs finishing`, `not
  fully reconstructed`, or a `CGS_ASSERT(false, "... not reconstructed")` body) as an
  unfinished TU, and a file of trap stubs alone as todo. Keep such phrases when they are
  true; never leave them in a file you call done.
- **The ledger's `reviewed` is the default, not a verdict.** A function row in
  `progress/status.json` reads `reviewed` even when the function has no definition anywhere,
  so it is not evidence a body exists (several waves lost time to it; one shipped a
  declaration whose definition only the exe link found missing). Ask the tree:
  `python tools/re/hasbody.py <Class::Method> [--status]`. A bare `grep name(` is no
  substitute (comment hits); and `hasbody.py` counts a trap stub as a definition, so open
  the file.

## Naming

- All new owned C/C++ (types, functions, variables with scope + type prefixes such as
  `mpBoostStrategy` and `lfTimeStep`, constants `KI_`/`KU_`/`KF_`, enums `E_` upper snake,
  files, namespaces) follows `references/CXX_NAMING_CONVENTIONS.md` (a local input), which is
  derived from the project's own code and is the single source of truth for style. When the
  Hex-Rays pseudocode or a recovered name disagrees with it, the convention wins, except
  where you match an external, generated or platform API. Reviewers check against it too.

## Reviewer enforcement

Reviewers must FAIL any TU that uses offset-based cast hacks, leaves raw decompiler
temporaries or gotos, or fails to structure code cleanly; and any TU that trusts a wiki
offset over the pseudocode, stubs an Apt engine method, invents behaviour, or contradicts
the asm's calling convention or the DWARF's declaration shape (`review-tu`).
