---
name: diagnose-parity-bug
description: >-
  Ordered triage for "our game behaves differently from the original": a missing, weak or
  wrong behaviour, wrong-but-plausible data (zeros, identity, the origin), a UI element
  that never shows, a feature that does nothing, an access violation (even one "reading
  0xFFFFFFFFFFFFFFFF"), a PC-only assert, a player report or GitHub issue, a campaign
  lane's console mismatch. Ask the tree first (tools/re/hasbody.py; the ledger's
  `reviewed` is a default, not a verdict), grep the chain for pinned reads and
  placeholders (FLAG, GATE, parked, placeholder, TODO, DELETE-WHEN), then walk the defect
  classes: silent-drop stubs, misfiled case ids, guessed strings, misnamed fields, invented
  arms, shadowing and ODR forks, hollow shells, valid pointer/invalid object, x64-widening
  ghosts, wrong vtable slots, AttribSys key truncation, stale gates and banners, ledger
  holes, diagnostics that lie. Every fix ends with a regression test that fails on the old
  body.
---

# Diagnose a parity bug

Use this when the game we build does something the original does not, or fails to do
something it does. The job is to find the function whose body, glue or data differs from the
console's, prove it against the ARTIST asm, fix it faithfully, and lock it with a test.

Not for: deciding which build is authoritative or how a tool works
([console-evidence](../console-evidence/SKILL.md), which this skill leans on throughout);
reconstructing a TU from scratch ([reconstruct-tu](../reconstruct-tu/SKILL.md)); driving the
game and writing harness cases ([bug-test](../bug-test/SKILL.md)).

## Frame it first

- **A report is a symptom, not a diagnosis.** "Collision is missing" once meant "I fell
  through at one spot". Reproduce and measure before believing the shape of a report.
- **"Not 1:1" needs the console's number, not intuition.** Some console behaviour looks wrong
  and is faithful: get the number from the asm before calling anything a defect, and record
  a faithful oddity as a console quirk, not a fix (catalogue class 26).
- **No tuning.** Every constant is read from the image and cited by its address. No invented
  thresholds, no scaling "to feel right", no clamps the console lacks. If the console's number
  produces a behaviour that looks wrong, the number stays and you say so.
- **State the terminal condition** before you start: the result that ends the investigation (a
  defect found, fixed and tested, or the whole chain measured faithful).

## The triage, in order

### 1. Name the runtime chain

From the symptom, find the console functions that produce the behaviour: the event or action
id, string, asset, constant or state that should change, then the console functions that post,
read or write it. Walk callers (`xrefs_to`) and callees (`xrefs_from`) in the ARTIST export, and
the virtual hops (`python tools/re/vdispatch_audit.py <hex>`). Verify the **whole** chain,
including functions the ledger calls done and rows the audits call clean: the defect is often in
the glue between two correct bodies (which value feeds which argument, which id files which arm).

### 2. Ask the tree, not the ledger

`progress/status.json`'s `reviewed` is the default, not a verdict: it is not evidence that a
body exists, and it carries no information about whether anything was written. Functions marked
`reviewed` have had zero definitions anywhere in the tree (`BrnGame::BrnGameModule::BridgeDirectorToGui`,
`BrnGui::EffectsArbitrator::StartHook`, `BrnGui::EffectsArbitrator::LookupColourCube` were all
once in that state); several waves read it as evidence and lost time, and one shipped a
declaration whose definition did not exist, caught only by the exe link. A hollow-shell class can
declare 1 of 22 console methods and every row still reads `reviewed`.

```
python tools/re/hasbody.py <Class::Method> [more...] [--status]
```

A bare `grep name(` is not a substitute: one wave got a fact backwards because `grep | head -5`
returned five comment hits and cut off the real definition. The tool separates definitions from
mentions for exactly that reason. For every function on the chain:

- **NO DEFINITION**: a silent link (class 1). Check `progress/SILENT_LINK_INVENTORY.md`.
- **HAS BODY**: is it a stand-in (`python tools/re/stubaudit.py --file <path under src>`)? Does
  our caller actually call it (grep the call expression, `->Detach(`, not just the qualified
  name)? Is its TU mounted (search `tools/build/build_game_exe.bat` for the file)? Is it declared
  in a header, so anything can call it? For a virtual, does our class override it where the
  console does (`progress/VTABLE_OVERRIDE_AUDIT.md`)?

### 3. Read the evidence audits

`work audit <tu>` (add `--refresh` after an edit), or per function
`python tools/re/funcaudit.py --func <Class::Method>` and
`python tools/re/asmaudit.py --func <Class::Method> --asm`. Every high-signal finding on the
chain (`NO_BODY`, `MISSING_CASE`, `EXTRA_CASE`, `MISSING_EVENT`, `MISSING_CALLEE`,
`MISSING_ASSERT`) is a defect to fix or explain. A clean audit is "nothing nameable differs":
inlined callees, virtual dispatch, argument order, offsets and constant values are invisible to
it.

### 4. Grep the chain for pinned reads and placeholders

```
git -C b5-decomp grep -nE "FLAG|GATE|parked|placeholder|TODO|pinned|stand-in|bring-up|DELETE-WHEN|deferred|stub" -- src/<files on the chain>
```

(Any search tool works here: `b5-decomp/src` is tracked, unlike `.ida-exports/`.) Then read
every hit, plus every hard-coded value where the console reads a member: a
`= false;`, `= true;`, `-1`, `0.0f` or `nullptr` beside a console offset or address comment. Each
is a claim with a timestamp ("off the live path", "until X is committed", "nothing can set mode
2"): re-test the claim before inheriting it. One sweep of this kind found three pinned reads in
`DeformableObject::UpdateAbsorptionSet` (`@0x825DF9A0`): every crashing rival absorbed on the
NORMAL row, so rivals deformed less and flew more.

### 5. Walk the defect classes

Each class, with its symptom, a command or grep that detects it, the shape of the fix and a
worked example, is in [references/defect-classes.md](references/defect-classes.md). Check them in
roughly this order of yield:

| # | Class | First check |
|---|---|---|
| 1 | Silent-drop stubs | `hasbody.py`; `stubaudit.py --file`; is it called; print both ends of the transfer |
| 2 | Pinned reads and stand-in arguments | step 4; every console member read has a member read here |
| 3 | Switch arm under the wrong case id | funcaudit `MISSING_CASE` + `EXTRA_CASE`; find the case by the field offset it touches |
| 4 | Guessed string literals and hashes | read the string table from the image; census the values a consumer receives |
| 5 | Misnamed fields | search by offset and value written, not by name; `idfield_sweep.py` |
| 6 | Invented arms, clamps, early-outs (C4715 ratchet) | every guard and branch in our body has one in the asm |
| 7 | Shadowing and reduced re-declarations | link; a probe compile with `override` |
| 8 | ODR forks that link silently | `tools/work/find_local_redefs.py`; demanded mangled name vs DWARF |
| 9 | Hollow-shell classes | header virtuals vs DWARF method list; base call in the prologue |
| 10 | Valid pointer, invalid object | pool-carved objects whose constructor never ran |
| 11 | Below-4GB heap, alignment faults | an AV at `0xFFFF...` is an alignment fault: read the faulting instruction |
| 12 | AttribSys u32 key truncation | 32-bit collection keys; `IsValid()` on the instance |
| 13 | x64-widening ghosts | `widening_sweep.py --root src/<dir>`; read fields by name |
| 14 | The f32 phantom parameter, dropped arguments | signature from the asm and the DWARF |
| 15 | Wrong vtable slot, slot-0 adjustor, slot-0 shims | `vdispatch_audit.py`; slot 0 of the table |
| 16 | Gates that are stale, not dead | when did this `static_assert` last run; tamper it |
| 17 | Placeholder identity elements | is 0 the identity of the expression, for the arm we run? |
| 18 | Work hiding in a `Prepare` stage | staged `Prepare` the PC skips or gates |
| 19 | GUI event-queue payload convention | which producer wrote the record: header stripped or not |
| 20 | Materialised GUI resource banks | log line `not materialised on PC` |
| 21 | "Deterministic, therefore initialised" | which non-determinism are you relying on? |
| 22 | Diagnostics that lie | what does the number measure, on which object, in which window |
| 23 | Stale `[BLOCKED]` banners | grep the named blockers, `hasbody.py`, the mount |
| 24 | Ledger holes | find the caller in the image, not the name in the ledger |
| 25 | Wrong or un-homed constants | `constaudit.py --wide`; `findinit.py`; thunk order |
| 26 | Console quirks (not defects) | the console's own asm does it: record it, keep it |

### 6. Prove it against the console

- Derive the expected behaviour from the ARTIST asm, not the pseudocode alone; read every
  constant by address (`x360rd.py`, `findinit.py`, `constaudit.py`).
- **Probe, don't reason**, when two explanations fit. Print the value at both ends of a transfer
  (producer and consumer) in one run; print the selector of a branch, not the branch you infer;
  print pointers as `u64` (the engine's string stream renders `void*` as its low 32 bits).
- Prefer values a probe prints directly in one run, and controlled A/B pairs on one value, over
  comparing two runs. "It drives better now" is not evidence.

### 7. Fix it faithfully

- The fix is the console's code: delete an invention (never invent a return value to go with
  it), thread the console's real argument, file the arm under the console's id, read the string
  or constant from the image, declare the missing base or override, de-fork the type and
  `#include` its real header.
- Keep the change to the defect. A fix that makes a dormant path reachable must first diff every
  class on that path against the DWARF and audit the stubs it now reaches: their "unreachable"
  justification has just expired.
- Code-writing rules (naming, no offset casts, the faithfulness gate) are
  [reconstruct-tu](../reconstruct-tu/SKILL.md)'s.

### 8. Lock it with a test, then land it

- **Every fix gets a regression test that fails on the old body and passes on the new one**,
  and you prove both: the usual shape is `b5-decomp/tests/<Name>.cpp` plus `run_<name>.py`, which
  extract the production function text from the real source file, compile it with the canonical
  flags against small fixtures, and check numbers derived from the ARTIST asm. Run it against
  the pre-fix source and record "old body fails N/M checks, new passes M/M" in the commit
  message. Mechanics: [bug-test](../bug-test/SKILL.md).
- Behaviour that is only observable live gets a harness case with a witness line armed by a
  `BRN_*` variable. **A green run validates nothing unless the changed code was dispatched in
  it**: arm a witness that proves it ran.
- In a campaign, log a verdict for every function you verify (MATCH, FIXED, DEFECT-OPEN,
  CONSOLE-QUIRK, NOT-CALLED) as you go: [campaign-lane](../campaign-lane/SKILL.md). Commit and
  push per [land-change](../land-change/SKILL.md), one defect per commit, citing the ARTIST
  addresses that prove it.

## Never

- Never read `reviewed`, `done`, a clean audit or a green run as proof that a body exists, matches
  or ran.
- Never accept "no callers", "no writers" or "not in the export set" from a search you have not
  seen find a known positive.
- Never add a clamp, guard, early-out, damping term or scale to make a symptom go away, and never
  invent a return value to accompany an invented arm.
- Never tune a constant: read it from the image and cite the address.
- Never "fix" a console quirk (faithful undefined behaviour, a faithful static-init zero, a
  console over-read): record it, and leave a note so nobody else does.
- Never hoist a load or its null test across a call that can write the thing loaded.
- Never downgrade a failing console assert to a log on the argument that it cannot matter here.
- Never feed a "same condition" stand-in where the console passes a real argument.
- Never guess a string literal, hash, case id or event id: read it from the image.
- Never read a console byte offset on a widened host struct: name the field.
- Never inherit a `[BLOCKED]`, `FLAG`, "not in the export set" or "no type home" banner without
  re-testing it.
- Never ship a fix that makes a dormant path reachable without auditing what that path reaches.

## Tools

| Need | Command |
|---|---|
| Does a body exist? | `python tools/re/hasbody.py <Class::Method> --status` |
| What does the console state that we do not? | `work audit <tu> [--refresh]`; `python tools/re/funcaudit.py --func <name>` |
| Is it a stand-in, and is it live? | `python tools/re/stubaudit.py --file <path>` |
| Machine-code shape against the console | `python tools/re/asmaudit.py --func <name> --asm` |
| Constants | `python tools/re/constaudit.py --wide <subtree>`; `python tools/re/findinit.py <hex>`; `python tools/re/x360rd.py <hex> [n]` |
| Virtual dispatch | `python tools/re/vdispatch_audit.py <hex>`; `python tools/re/vcallsites.py <slot-hex> --name` |
| Missing overrides / silent links | `progress/VTABLE_OVERRIDE_AUDIT.md`; `progress/SILENT_LINK_INVENTORY.md` |
| Widening ghosts | `python tools/re/widening_sweep.py --root src/<dir> --base this --unpinned` |
| Local type forks | `python tools/work/find_local_redefs.py`; `python tools/re/template_static_sweep.py` |
| A probe compile | `python tools/work/selfcheck.py <probe.cpp>` |

Flags, inputs and false positives for each: [console-evidence/references/tools.md](../console-evidence/references/tools.md).

## Read next

- [references/defect-classes.md](references/defect-classes.md): the catalogue (symptom, detection,
  fix, example) for every class above.
- [console-evidence](../console-evidence/SKILL.md): which build wins, reading PowerPC and VMX,
  every tool in detail.
- [bug-test](../bug-test/SKILL.md) for the regression test and the live witness;
  [campaign-lane](../campaign-lane/SKILL.md) inside a campaign;
  [land-change](../land-change/SKILL.md) to commit and push.
