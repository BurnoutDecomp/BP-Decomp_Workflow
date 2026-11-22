# Reading a byte-match diff

`work match diff NAME --compile` prints our function (left, offsets from its start) beside
ARTIST's (right, absolute addresses), aligned the way `compare.py` scores them. `~` marks a
changed pair, `-` a line only we have, `+` a line only ARTIST has. Call targets are named on both
sides (`-> Ns::Class::method`); an ARTIST callee with no name prints as `sub_<addr>`. The header
line gives both sizes, the verdict and the score, and lists `wrong calls` and `wrong constants`
when a body lines up but a callee or a literal-pool value differs.

Work from the top of the diff down and change one thing per round: the first difference often
causes the rest (one extra register live shifts the whole allocation).

## The difference classes

These are heuristics about how the PowerPC compiler responds to source; each says what usually
moves the difference. Confirm every change with another `diff --compile`.

| What the diff shows | Usually caused by | Try |
|---|---|---|
| The same instructions with other register numbers | a different order in which values become live, or a temporary the original did not have (or lacked one it had) | verify types, dataflow and helper boundaries before changing declarations or local lifetimes |
| The same instructions in another order | statement order, or independent loads and stores the scheduler placed differently | verify the order of source operations and observable effects; record any remaining scheduling difference |
| `bl __savegprlr_N` / `__restgprlr_N` with another N | `__savegprlr_N` saves rN to r31 and the link register: a different N means a different number of callee-saved registers, so a different number of values live across a call | find the value that lives across a call in one version and not the other |
| `stwu r1,-X(r1)` with another X | a different frame: locals, spill slots, outgoing arguments | an extra or missing local, a struct passed by value, a larger array |
| Branch polarity or block order differs | `if`/`else` order, an early return, the order of `&&`/`||` operands, `for` against `while` | mirror the console's block order; test the condition the way the first branch reads |
| We call a function ARTIST inlined (or the reverse) | the callee's definition is or is not visible and inline where the original had it | check its owning declaration and definition visibility; use compiler directives only with independent source or SDK evidence |
| `wrong calls` | a different overload or a different function with the same shape | call the function ARTIST calls; check the argument types that pick the overload |
| `wrong constants` | a literal with the wrong value | read the value from the image at the address in the report (`python tools/re/x360rd.py <addr> 4`) |
| Signed/unsigned comparisons or extra/missing extensions (`extsh`, `extsb`, `clrlwi`, `rlwinm`) | a placeholder or a type with the wrong width or signedness | check the owning field, enum, container or API and verify all its consumers; recover that type before adding any cast |
| Our body is longer or shorter | dropped or invented behaviour: a missing check, an assert the console does not have, a call to a helper it does not make | read ARTIST's extra or missing block; never pad or trim to fit |

## When it will not move

- A body whose instructions are identical but `calls_unverified` is non-zero calls an unnamed
  ARTIST function: the match is real but unverified. Name the callee in the ledger when you can
  prove what it is.
- Vector code: VMX128 instructions differ from classic AltiVec, and IDA prints some operands in
  raw field order. Read [`console-evidence`](../../console-evidence/SKILL.md) before trusting an
  operand order, and use the XDK's `ppcintrinsics.h` / `vectorintrinsics.h` intrinsics the console
  code used.
- A difference that only a compiler flag explains (inlining depth, scheduling, frame-pointer
  use) is a toolchain question for the maintainer, not a source change: flags are fixed by the
  branch's `build_x360.py` for every object ([`x360-toolchain`](../../x360-toolchain/SKILL.md)).
- After several rounds without progress, stop and record what you learned in the function's
  source comment or a handoff, rather than drifting into code the original could not have had.

## Open source-fidelity questions

- **AttribSys bucket removal (`0x82808980`, `0x82808A98`).** Both exact versions use a
  local `volatile` reference to reproduce the second sentinel load. The existing `Node::Key()`
  helper expresses the logical operation and builds to 268 bytes in both functions, compared
  with ARTIST's 276 bytes. The helper trial scored 95.6% in both. The second load alone is
  insufficient evidence for volatile storage. Retain the exact baseline while investigating
  the original accessor and the optimizer's load elimination.
- **Folded I/O buffer initializers (`0x823AEB7C`, `0x827B6C54`).** The calls establish an
  out-of-line initialization boundary in ARTIST. The reconstructed wrapper's `noinline`
  directive still needs independent evidence for its source declaration or a replacement that
  preserves those calls.
- **Sound state detachment (`0x826C9C58`).** `StreamingState::Detach` shares the base operation
  with `State::Detach`. ARTIST inlines the tail at `0x826C9CDC`, while this build emits a call
  to the base method. DecFIGS puts the base method in `CgsState.cpp`. Recover the original
  inlining context and the streaming busy checks before changing the method's visibility.
