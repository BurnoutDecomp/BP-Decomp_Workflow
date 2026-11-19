# Defect classes: symptom, detection, fix

Every class below produced real, player-visible or behaviour-visible bugs in this tree, and
most of them compile, link and run without a single warning. Each entry gives the symptom, how
to detect it (a command or a grep), what the fix looks like in general terms, and a worked
example. Function names and addresses are examples of the class, not a to-do list: the current
state lives in `progress/` and in the evidence audits.

Tool flags and caveats: [console-evidence/references/tools.md](../../console-evidence/references/tools.md).
Reading the asm: [console-evidence/references/reading-ppc.md](../../console-evidence/references/reading-ppc.md).

## 1. Silent-drop stubs

A function that compiles, links, runs and does nothing, so the bug looks like whatever
consumed its output.

- **Symptom:** data that arrives wrong but plausible (zeros, an identity, the origin, an empty
  list); a behaviour that never happens; no crash, no assert, no log line.
- **Detect:**
  - `python tools/re/hasbody.py <Class::Method>` on every function of the chain. A function the
    console calls, declared in our headers and defined nowhere, **links in complete silence**
    because nothing references it: see class A of `progress/SILENT_LINK_INVENTORY.md`.
  - `python tools/re/stubaudit.py --file <path>`: a defined stand-in (empty `operator=`, an
    accessor returning the wrong member, `return -1`, a constant `GetType()`), with a column saying
    whether a reconstructed caller reaches it today.
  - Is it called? A definition nobody invokes is the same bug with an extra step.
  - Print the value at both ends of the transfer (producer, consumer) in one run: it bisects
    producer from consumer far faster than reasoning.
- **Variants:** a comment that faithfully transcribes the console's list of calls, none of them
  executed; a stub that is the **sole writer** of some state (it is not "doing nothing", it is
  holding something: ask what it alone writes); an engine acquire that "succeeds" with a null
  resource because it was driven before the data was resident ("the state machine completed" is
  not evidence that data arrived: check the bound pointer).
- **Fix:** reconstruct the body from ARTIST and call it where the console calls it. A stub's
  "not on the live path" justification expires the moment someone lights that path: whenever
  you make a path reachable, audit the stubs it now reaches.
- **Example:** `BrnParticle::ParticleModule::EndOfFrame` (`@0x82294C30`) was declared and defined
  nowhere, so the correct `TrailSystem::EndOfFrame` it tail-calls never ran: the tyre-mark emitter
  pool drained one way and tyre marks stopped for the session. Same shape:
  `BrnTraffic::TrafficEntityModule::UpdateRecoveringFromSlam` (`@0x8273E778`), whose absence left
  every slammed traffic car parked until it was deleted.

## 2. Pinned reads and stand-in arguments

- **Symptom:** a selector stuck on one row or arm; a behaviour that never varies with the
  situation; a feature that works until the piece before it starts working.
- **Detect:** the grep in `SKILL.md` step 4; then, function by function, check that every member
  the console's asm loads (`lwz`/`lbz`/`lfs` off the object) is read here as a member, not as a
  literal. Look for arguments fed from a "same condition" flag where the console passes a
  computed value.
- **Fix:** read the member or pass the argument the console uses; recover any missing value from
  the image. Never substitute a stand-in that happens to match today.
- **Examples:** `DeformableObject::UpdateAbsorptionSet` (`@0x825DF9A0`) had
  `lbVehicleInCrash = false; // FLAG` and two more pinned reads, so no crashing car could leave
  the NORMAL absorption row. `GuiModule::Update` received a "gameplay HUD active" flag where the
  console passes the frame's update set; it matched for a month, until a correct fix elsewhere
  made the console's own flag drop real. A term pinned to `false` with a `DELETE-WHEN` "because
  nothing can set mode 2" froze the boost bar once mode 2 existed.

## 3. Switch arm filed under the wrong case id

- **Symptom:** a handler exists, reads correctly, and never runs.
- **Detect:** funcaudit `MISSING_CASE` together with `EXTRA_CASE` (an id the console never
  mentions is a misfiled one). Check the case **label** against the console pseudocode, not just
  the body: search the export JSON for the field offset the arm touches (decimal and hex) to find
  the console's real case. Also check that the id survives any forwarding filter in front of the
  switch.
- **Fix:** move the arm under the console's id; delete any arm copied from a sibling class that
  the console's own function does not have (that is class 6).
- **Example:** `GuiCache::RecEvent` carried the crash-bar arm under `case 132`; the console's arm
  is `case 377`, and its 132 is two byte clears. The "DAMAGE CRITICAL" banner never fired.

## 4. Guessed string literals and hashes

- **Symptom:** a UI element simply absent; a lookup that misses with no error.
- **Detect:** any string that crosses into Apt/ActionScript, a resource or bundle name, a hash
  input or a tag table is an interface: compare it with the image (`x360rd.py` on the pointer
  table, then on each string). funcaudit `MISSING_STRING` helps. A census of every distinct value
  a consumer receives in one run shows which values match nothing.
- **Fix:** read the literal from the image like a constant. Never derive it from a DWARF symbol
  name: console tag strings are often abbreviations.
- **Example:** `MenuToggle::KAC_STATE_NAMES` carried `"Unhighlighted"`/`"Highlighted"`; the
  console's table reads `{Invisible, Invisible, Disabled, Unselected, Selected}`. The string feeds
  the movie's `gotoAndPlay`, which resolved to no frame, and the `>= 0` gate then skipped both the
  jump and the dirty flag: a perfect silent no-op on every screen embedding the component.

## 5. Misnamed fields

- **Symptom:** right logic on the wrong member; "no writer anywhere" for a field the console
  plainly sets; an index that walks off an array, or a key that never matches.
- **Detect:** search by **offset** and by the **value written**, not only by name: producers
  write through differently named locals, or `memcpy` into a payload offset. Grep the tree for a
  comment naming the right offset (it is often written next to the bug). When two members of one
  type compete (two ids, two flags), compare which one the console's asm loads:
  `python tools/re/idfield_sweep.py --root src/<dir>` does this for one id pair. Let the consumer
  settle a disputed name: what does it do with the byte?
- **Fix:** read the member the console reads; keep one definition under its DWARF name.
- **Examples:** `DeformableObject::DoBodyPartWorldContactGeneration` took a triangle-cache slot
  from the global entity id where the console reads the handling-body id, writing far past the
  array. `BaseResourcePtr::GetResourceHandle` returned the cached identity words instead of the
  handle words, so every main-memory resource got a plausible zero.

## 6. Invented arms, clamps and early-outs (and the C4715 ratchet)

Every other class is about something dropped; this one is about something **added**.

- **Symptom:** a branch that silently skips work, a clamp that caps a value, a null check that
  looks prudent and is the bug.
- **Detect:** diff every guard, branch, clamp and early return in our body against the asm. A
  `CGS_ASSERT(x)` immediately followed by `if (x)` is a candidate (sometimes it is the console's own
  code: disassemble each one). Look for arms copied from a sibling class, and for "simplifications"
  justified by a comment about what the caller supposedly guarantees.
- **The ratchet:** `tools/build/msvc_flags.txt` carries `/w14715 /w14716 /w14703` (not all control
  paths return a value; uninitialised local pointer) as a permanent ratchet at zero. A new hit is
  a real defect, typically an invented `break` falling off a non-void function. It only sees code
  that reaches code generation.
- **The inverse:** the console re-loads and re-tests a pointer after every call that can null it.
  Never hoist the load or its guard across such a call: a repeated test is the contract, not
  redundancy.
- **Fix:** delete the invention. Never invent a return value to go with it.
- **Examples:** `CgsSceneManager::SpatialPartitionManager::Release` (`@0x828AA860`) carried a null
  test the console lacks; its `break` fell off a `bool` function and garbage decided whether
  teardown advanced. `ModeManager::UpdateCurrentMode` hoisted six console null tests into one and
  crashed reloading a pointer the intervening call had nulled. `rw::math::vpu::OrthoNormalize3x3`
  was three `Normalize()` calls "because the caller feeds orthogonal axes"; the console runs a
  Gram-Schmidt with pivot selection, and normalisation cannot remove shear (the car's basis
  sheared in the air).

## 7. Shadowing redeclarations and reduced re-declarations

- **Symptom (shadowing):** a derived class re-declares members its base owns ("declare-only here,
  owned by the base TU"); the redeclaration shadows the base, so every call site mangles to a
  symbol no TU defines. Each TU compiles; only a **link** fails.
- **Symptom (reduced copy):** a header carries its own reduced copy of a type it also includes;
  reading it, members and virtuals look missing that the real base has. The copy is either dead
  or an ODR fork, and work gets wrongly declared "blocked".
- **Detect:** mount the TUs and link, even before anything calls them. To settle "does the base
  really declare this?", compile a probe that overrides the virtual and touches the members:
  `override` only compiles if the base declares it (`python tools/work/selfcheck.py <probe.cpp>`).
  A member declared non-virtual in the derived class does not override anything.
- **Fix:** delete the re-declaration and include the canonical header.
- **Example:** `BrnEffectObject.h` and `BrnEffectControl.h` each carried a reduced copy of
  `CgsSound::Logic::EffectBase`/`EffectControl` behind a shared include guard while including the
  canonical header; three bodies had been reported as blocked on members that already existed.

## 8. ODR forks that link silently

- **Mechanism:** mangling encodes a class's name, not its size, class-key or bases, so a
  function defined against the real class satisfies a call site compiled against a slice. The
  link is clean; the array strides wrong; nothing warns. (A shadowing redeclaration fails the
  link; a fork passes it. "It linked" is evidence of nothing here.)
- **Symptom:** wrong strides, a buffer allocated at a stand-in's size, a class whose size was
  computed from one-byte placeholders.
- **Detect:** `python tools/work/find_local_redefs.py` (local definitions of types that have a real
  header); grep for local stand-ins (`u8 maFoo[N]`, a small local struct) of a type that has an
  owner elsewhere; a `void*` in a reconstructed signature where the DWARF names a type; comments
  of the form "until X is committed" or "never included in the same TU", which are timers. Before
  calling a symbol "one body away", diff the mangled name the linker demands against the DWARF
  signature. A `static` local inside a template body is one object per instantiation where the
  console has one word: `python tools/re/template_static_sweep.py`.
- **Fix:** de-fork: one definition, included everywhere. Re-derive every dependent drift
  constant and re-measure host sizes (a de-fork can shrink a class); replace a host-`sizeof` gate
  that only proved the stand-in was still a stand-in with console arithmetic.
- **Examples:** `TrafficPhysics` as a `u8[5168]` slice at the call site;
  `struct ArticulatedJointCreateBuffer { u8 mOpaque[16]; }` standing in for a 2032-byte class, so
  mounting would have allocated 16 bytes for the IO buffer; a local 4-byte `Random` in place of the
  48-byte `CgsNumeric::Random`.

## 9. Hollow-shell classes

- **Symptom:** an object that allocates, prepares, reports ready and produces a valid, wrong
  result every frame (often an identity at the origin), while the ledger says done.
- **Detect:**
  - Diff the header's declarations, virtuals above all, against the DecFIGS DWARF method list for
    the class (gated on the X360 ledger). `grep -c "Class::"` finds only a total shell; the partial
    shell is the common one.
  - The prologue tell: if the class is really derived, its `Construct`/`OnEnter`/`Update` open with
    a `bl` to the base's function of the same name.
  - Console overrides we lack: `progress/VTABLE_OVERRIDE_AUDIT.md`, or
    `python tools/re/vtable_override_audit.py --table <vtable hex>`.
  - A `u8 maReserved[N]` blob "not individually recoverable" is a hypothesis: sum the candidate
    members' sizes and see whether it closes.
  - An empty override is not a missing one: the image-wide `{}` fold in a slot is not `_purecall`.
- **Fix:** declare the real base and every DWARF virtual the X360 ledger attests, then transcribe
  the bodies.
- **Examples:** `BehaviourRotateAboutVehicle` declared one of its eight virtuals, so the camera eye
  sat bit-identical at the origin. `BehaviourSpirallingDeathcam` had no `Behaviour` base and
  crashed the moment a fix made its path reachable. `FaceOffMode`'s `Start`, `PreWorldUpdate` and
  `FillInGameModeSpecificResults` overrides were missing, so Face Off ran the base `GameMode`'s.

## 10. Valid pointer, invalid object

- **Symptom:** the chain is fully bound and the data provably right, and the first virtual call
  faults; null guards pass because the pointer is valid and the object is not.
- **Detect:** objects carved from a raw pool or resource memory never ran a constructor, so the
  vptr is garbage. Look for the placement-new over pool slots, a vptr stamp in a
  `Prepare`/`Reset` path, or a per-object `Construct` the PC build skips. A bodied constructor is
  not a called constructor. Also: a member nothing in the tree ever assigns (it holds whatever was
  there, often 0, which passes `IsValid()`).
- **Fix:** construct the objects where and how the console does.
- **Example:** `DeformationModel`s are carved from a resource pool; every `DeformationSensor`'s
  vptr was uninitialised, so `ImpulsePasser::PassOnImpulse`'s dispatch jumped into garbage the
  moment the impulse chain went live.

## 11. Below-4GB heap and alignment faults

- **Rules:** the game-data heap sits deliberately below 4 GB (the boot log prints its roots) so
  32-bit pointers baked into serialized bundles can be rebased. A zero upper dword is the normal
  shape of a game-data pointer, not a truncation. Triage a fault value by:
  1. **alignment**: allocator and rebased pointers are at least 4-, normally 8- or 16-aligned; an
     odd address is a non-pointer used as one;
  2. **range** against the printed roots;
  3. **reinterpretation** as f32 (a value like `1.2e34` is an uninitialised float).
- **An access violation "reading 0xFFFFFFFFFFFFFFFF" with a valid pointer in the register is an
  alignment fault** (`movaps` on a 16-byte type seated at an 8-aligned address raises #GP, which
  Windows reports that way). Disassemble the faulting instruction (capstone over the exe plus the
  linker map resolves `Func+0xNN`) before chasing the pointer.
- **Fix:** `alignas(16)` on the member or span the console seats 16-aligned, with `sizeof`
  unchanged; never a resize.
- **Check** any "signature" of a bad pointer against a known-good pointer from the same run: a
  property the healthy cases share explains nothing.
- **Example:** `MainDirector::maRandom` was an 8-aligned byte span where the console seats a
  16-aligned `CgsNumeric::Random`; `Looker::Update` takes it by value and faulted on the copy.

## 12. AttribSys u32 key truncation

- **Symptom:** an asset-keyed construct silently yields zeros: an effect comes out black or
  neutral, with no error.
- **Detect:** a generated `Attrib::Gen::<asset>` constructor taking a 32-bit collection key
  (`git -C b5-decomp grep -nE "u32 lu[A-Za-z]*CollectionKey" -- src`). The X360 passes the low word of
  `Attrib::StringToKey`, but our vaults hold full 64-bit keys and `Attrib::FindCollection(u64, u64)`
  compares whole keys; on a miss the instance hands out the zeroed default data area. Witness
  `IsValid()` on the instance.
- **Fix:** widen the key to `u64` (the full `StringToKey`).
- **Caveat:** a key missing from every vault can be deliberate (an effect whose data is meant to
  be zeros).
- **Example:** the post-FX vignette asset produced a black screen the first time a weight-1.0
  hook played.

## 13. x64-widening ghosts

- **Symptom:** a value read or written at the console's byte offset or element stride on a
  struct whose host layout moved (pointers are 4 bytes on the console and 8 here). If the result
  is dereferenced it faults and gets found; if it is read as data it publishes wrong numbers
  forever, silently.
- **Detect:** `python tools/re/widening_sweep.py --root src/<dir> --base this --unpinned`, SILENT
  hits first. The ghost is rarely a bare literal: it is a byte-pointer alias of `this` plus a named
  offset constant (`KU_..._OFFSET`) plus a console stride. Also suspect any console byte-size
  literal in a request or record (posting a record at the console's size truncates the x64 one)
  and `>> 2` pointer-slot arithmetic.
- **Fix:** read the field by name: the host struct has the member. Serialised file records are
  the exception (raw offsets are allowed and correct there, because nothing in them widens).
- **Example:** `PhysicalWheel::Update` read its frozen bit at the console's `+0x9C`, which is
  padding on the host, so a settled wheel never froze and an assert fired hundreds of thousands of
  times a run.

## 14. The f32 phantom parameter and dropped arguments

- **Symptom:** a declaration with an extra parameter that every caller passes as a literal `0`;
  or the inverse, a declaration that lost a parameter the console signature carries (the
  dropped-argument trap), so the callee never receives something it needs.
- **Detect:** take the signature from the asm and count it against the DWARF (a float argument
  eats an integer slot; a CgsID swallows the arguments after it; a vector arrives in `v1`); see
  [reading-ppc.md](../../console-evidence/references/reading-ppc.md). funcaudit `FEWER_PARAMS` is a
  hint. When two sibling classes disagree about a signature, the DWARF settles it.
- **Fix:** change the declaration and let the compiler enumerate the call sites; check each one
  (an apparent over-correction may be a different class with its own signature).
- **Examples:** `CgsSound::Logic::Voice::SetGain` was declared with four parameters where the
  DWARF has three (the fourth was the float's integer slot). `RaceCarEntityModule::Prepare`'s stub
  had dropped its `OutputBuffer_Prepare*` argument (`r4` in the asm), so the module had no request
  queue to write to.

## 15. Wrong vtable slot, slot-0 adjustor thunks, slot-0 shims

- **Wrong slot:** a virtual call that lands on a same-signature neighbour compiles, links, runs and
  silently disables behaviour. Detect with `python tools/re/vdispatch_audit.py <hex>` against our
  call, or `python tools/re/vdispatch_sweep.py <subtree>` across a subsystem. Example:
  `GetVehicleWorldRestitution` called slot `+0x14` where the console dispatches `+0x10`.
- **Adjustor thunk pinning `this`:** when two functions of one class disagree about a member's
  offset by exactly N, find the vtable that holds them. If its slot 0 is an `adjustor{N}` thunk, the
  table belongs to a secondary base and every virtual in it receives `this == primary + N`: add N
  and re-read before calling the layouts irreconcilable. Example: `BrnSubmixesEffect`'s `Attach`,
  `ProcessUpdate` and `Notify` sit in a table whose slot 0 is `adjustor{4}`; with +4 every offset
  landed on the committed model, and two "blocked" bodies were written.
- **Slot-0 shim:** a `reinterpret_cast` onto a locally re-declared one-virtual interface. A class
  whose first declared virtual is `Create` puts it in slot 0, where the real class keeps its
  virtual destructor. Example: a local `ResourceAllocator { virtual void* Create(...) = 0; }` made
  every `Create` call run the allocator's scalar deleting destructor. Rule: a cast to a locally
  re-declared abstract interface is unsound unless it reproduces the real vtable order,
  destructor first; call the real method by name instead.

## 16. Gates that are stale, not dead

- **Rule:** an unmounted TU's `static_assert`s are not dead (the per-TU gate compiles them at
  `work submit`), but they are **stale**: a gate re-runs only when its own TU is re-submitted, so
  it gives no protection against another wave editing the shared header. Ask "when did this last
  run?", not "does this run?". A mounted TU cannot hide a compile failure; an unmounted one marked
  done can.
- **Vacuous gates:** a size gate on an over-aligned type is absorbed by tail padding (gate
  offsets instead); a gate spelled in type names only restates the header (spell each term as
  `sizeof(Class::member)`); a total-`sizeof` gate on a type with embedded pointers can pass
  *because of* the defect and reject the correct code; a gate on POD types says nothing about the
  pointer-owning struct next to it. Tamper-test every gate; a tamper that produces no errors is
  suspect before the gate is.
- **Runtime gates expire too:** a justification in a comment ("off the live path", "harmless
  today", `DELETE-WHEN`) dies silently when the path goes live. Grep for `DELETE-WHEN` and such
  notes whenever you land a new mode, state or flag.
- **Fix:** mount a layout-check TU built on console arithmetic; never delete the prose claim to
  silence a failing gate.

## 17. Placeholder identity elements

- **Rule:** a flagged-zero placeholder for an un-recovered value is correct only when 0 is the
  identity element of the expression it feeds. Ask "what does this function return if the value
  is inert?" and "is 0 the value of the arm the shipped game actually takes?". A `0.0f` timeout
  means "immediately", and zero absorption is the invincible row.
- **Detect:** for every flagged constant, write out the expression it feeds; check multi-way
  selects for a missing arm.
- **Fix:** recover the value from the image (class 25); until then the placeholder must be the
  expression's identity (1.0 for a factor or a lerp from 1, 0 for a sum), never a shared value
  copied from a sibling lookup.
- **Example:** `VehiclePhysics::GetSurfaceGrip` (`@0x825D51B8`) computes
  `1 - (1 - grip[id]) * blend`, whose identity is 1.0; it shared a zero placeholder with roughness
  and drag (where zero is the identity), which turned into a permanent grip cut on one axle and a
  car that spun. `ApplySensorImpulse`'s select was written two-way; the console's is three-way, and
  the missing arm was the one the game takes.

## 18. Work hiding in a `Prepare` stage

- **Symptom:** a handler looks inert, a loader looks "unowned", a feature does nothing.
- **Detect:** before implementing the handler you think is missing, check whether the real work
  lives in a staged `Prepare` (or `Construct`) state machine and whether the PC version skips the
  stage (`[gated]`, `lbDone = true; break;`, an inert `return true`). Constructors the X360 inlined
  have no symbol and are easy to miss. A comment listing what the console constructs is
  documentation, not code.
- **Fix:** run the stage the console runs, in the console's order. Never invent a handler the
  console does not have.
- **Example:** `TRIGGERS.DAT` never loaded. The loader is `TriggerQueryManager::Prepare`, called by
  `GameStateModule::Prepare` stage 3, called by `BrnGameModule::GamePrepare` stage 4, which already
  existed on PC gated to `lbDone = true`. The proposed new loader would have been an invention.

## 19. The GUI event-queue payload convention

- **Rule:** producer and consumer must agree on whether the 12-byte `GuiEvent<N>` header travels.
  `CgsGui::GuiModule::AddGuiEvent(T&, InputBuffer*)` posts the payload only (`sizeof(T) - 12`
  bytes past the header; the id rides the queue entry), while records posted whole
  (`queue->AddEvent(&whole, id, sizeof)`) keep the +0 layout.
- **Symptom:** a GUI consumer reads every field 12 bytes off: a GUID that is a float's bits, a name
  that is the tail of the name.
- **Detect:** for each consumer cast, find the producer that wrote the record and which form it
  used.
- **Fix:** view the record in its producer's convention (a payload-only struct, or step back over
  the header), never by guess.
- **Example:** every named post-FX hook ("Crash", "Car_Reset") resolved to the fallback hook,
  because the consumer cast a header-bearing struct over a payload-only record.

## 20. Materialised GUI resource banks

- **Symptom:** a GUI-routed bundle logs as loaded with N resources, then asserts on first use
  ("has no main memory resource").
- **Detect:** search the run log for `not materialised on PC` with that bank id: the PC GUI
  resource module answers banks it does not know with an empty completion.
- **Fix:** add the bank's pool and its load (and unload) arm in the PC GUI resource module,
  following the existing banks.
- **Example:** the post-FX colour-cube dictionary lives on a bank the PC module did not
  materialise, so every 3D-tint hook had a null cube.

## 21. "Deterministic, therefore initialised" is invalid

- **Rule:** the game-data heap is at a fixed, non-ASLR base and CI builds share one toolchain, so
  data-derived values, including uninitialised stack contents, can repeat exactly across runs and
  builds. "This value repeats, so it is not uninitialised" is valid only where the non-determinism
  you rely on actually exists: name it and check it.
- **Also:** read a record through its own declared type and table directory, not by eyeballing
  a hex dump; a raw byte search cannot succeed on a compressed file, so its silence is not
  absence.
- **Example:** a crash value repeated byte-for-byte across two builds; it was 528 bytes of
  uninitialised stack in an `ICE::CameraSpaceHandler` whose address was published unconditionally
  but which was constructed only behind a guard.

## 22. Diagnostics that lie

A diagnostic is code, exactly as likely to be wrong as the code it watches, and trusted more
because it reads like an observation.

- **Ask before believing a number:** which instance does it measure (a probe once printed race car
  0 while the player was car 2)? What does the counter actually count (one was constant by design)?
  Does it test the thing or a pointer near it? Could the branch it reports be the wrong one (print
  the selector)?
- **Check the window:** is the sample period shorter than the phenomenon? Can the probe print at
  all in the state you care about (its filter, its line cap)? A `max` can only freeze; prefer a
  histogram and a distinct-value count. A cumulative table that resets on state change shows only
  its last window. A 100% ratio may have a numerator that cannot be anything else.
- **Check the coverage:** a trace named after a subsystem may see only one of its two backends. An
  assert flood can starve the harness that is measuring.
- **Measure in pairs:** some numbers mean nothing alone (a deformation depth without the
  absorption set for the same frames).
- **Fix:** correct the probe first, then re-measure. Harness and witness mechanics are in
  [bug-test](../../bug-test/SKILL.md).

## 23. Stale `[BLOCKED]` banners

- **Rule:** a `[BLOCKED]`, `FLAG ... no type home`, "would require inventing layouts" or "not in
  the export set" banner is a claim with a timestamp. Before inheriting it, grep for the named
  blockers, run `hasbody.py` on them, check their mount, and check that the producer of the
  behaviour exists. A mount gap reads exactly like a missing body from the call site.
- **Example:** `EATraxInGameComponent` had every console body and was mounted, but the arms that
  reach it in `AlwaysAvailableComponentsManager::Update` were `break;` behind a banner whose three
  blockers all existed. The in-game producer of the event was missing too; scanning the image for
  `li rX, <event id>` found it.

## 24. Ledger holes: find the caller, not the name

- **Rule:** `hasbody.py` and `progress/identity.json` answer "is this name known", not "is this
  code present". Two holes follow:
  1. the body is in the image but unnamed, or an export hole: find the caller (scan `.text` for
     `bl <target>`, walk back to `mflr r12`; read the callers' `xrefs_from`), then disassemble;
  2. the definition exists but no header declares it, so nothing can call it:
     `git -C b5-decomp grep -n "<name>" -- "*.h"`.
- **Example:** `HUDEffect::UpdateParams` carried a note that its body was "not in the export set"
  and derived one statement from an invariant. The body sits at `0x827037E0` and has three
  statements; the two missing calls were the only entry point of the game-mode HUD audio lane.

## 25. Wrong or un-homed constants

- **Symptom:** a threshold never reached, a force identically zero, a timer that fires at once.
- **Detect:** `python tools/re/constaudit.py --wide <subtree>`; funcaudit `UNCITED_DATA`; flagged
  `0.0f` "value not recovered" constants; `python tools/re/findinit.py <hex>` for a `.bss` slot.
  Mind constaudit's false-positive classes before changing a number.
- **Fix:** recover the value from the image and cite its address. A zero produced by the console's
  own static-init order (the thunk runs before its dependency) is the shipped value: keep it.
- **Example:** `GetDownForce` returned zero at every speed because both aerodynamic constants were
  unrecovered zeros; an off-by-one-thunk read made a brake lock-up threshold 100.0 instead of
  `FLT_EPSILON`, so the latch was unreachable in ordinary driving.

## 26. Console quirks (not defects)

- **Rule:** some console behaviour looks wrong and is faithful: undefined behaviour the shipped
  binary really has (an uninitialised handle passed down a default arm); a constant that is zero
  because its initialiser runs too early; a deliberate over-read of an adjacent static the
  console lays out end to end; a field the console's data builder left byte-swapped. Ask which
  side a size mismatch is on and whether it is a read or a write. Pin a struct size more than one
  way (an in-tree `static_assert`, the stride between adjacent statics, the DWARF).
- **Do:** record it as a console quirk, keep the behaviour, and leave a note in the file so
  nobody "fixes" it.
