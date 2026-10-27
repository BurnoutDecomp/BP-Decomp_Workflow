# Fresh combined Traffic repair review

VERDICT: pass

Scope: the two function changes in authored packet seal `5df6a183055634c92ecfb7f0f94223daee5f3e2b1cef7ee016a9134787262a37`, based on B5 `9bd05cfc1de3a26837728325c5e563f019683560`. All 48 seal entries match; both preimages match the Git commit, and both raw ARTIST windows match this reviewer's independently retained bytes. Approval is pinned to these post files:

| File | Approved raw SHA-256 |
| --- | --- |
| BrnTrafficDebugComponent.cpp | `9a86a59168c78acff2e01f70081f971c086885ccbc38a2976923828c3a7c0213` |
| BrnTrafficEntityModule.cpp | `4fa51e94f9a5e1e8475b2ac4361da099d79cff56e4ac51e2d14f544f46d877a2` |

`UpdateCrashSlider` matches the decoded !LT/!GT branch tests, literal fsel choices, store order and single-precision fused operations. The explicit float `std::fma` calls preserve the intended fmadds/fnmsubs evaluation. Independent recompilation and rerun of the copied extraction reproduces **229/229 post**, **207/229 pre**; the interpreter consumes the original instruction bytes and replaces only the unchanged RNG-ring block with its stated deterministic seam. Fixture equality tolerates NaN payload/sign differences and does not prove status-register effects.

`ShouldObjectBeCulled` preserves its assertion, position-minus-camera operation, scalar square, W-independent dot and inverted strict comparison. The local existing `Dot3` call is the documented numerical model for the original `vmsum3fp128`. Independent cull rerun reproduces **17/17 post**, **15/17 pre**, including the finite radius200 cutoff witness and subnormal-threshold origin.

The new `fpclassify` block is supported semantic modeling: the [AltiVec ISA](https://www.nxp.com/docs/en/reference-manual/ALTIVECPIM.pdf) specifies comparison-input denormal truncation when VSCR[NJ]=1. It implements that rule for the scalar-produced squared threshold before its original VMX comparison. [Pinned Xenia defaults](https://github.com/xenia-canary/xenia-canary/blob/48b318a2ad7c36f8f3901a94e290ba70ae0ffec5/src/xenia/cpu/backend/x64/x64_backend.h#L105-L108) enable FTZ/DAZ, and its [dot implementation](https://github.com/xenia-canary/xenia-canary/blob/48b318a2ad7c36f8f3901a94e290ba70ae0ffec5/src/xenia/cpu/backend/x64/x64_sequences.cc#L2238-L2336) corroborates the wide-accumulation/overflow model. This evidence supports the stated model, not universal hardware accuracy or a captured Burnout thread's VSCR setting. No arbitrary bounds guard, fallback, invented offset, loader accommodation or global math change was added.

No blocking finding remains in this bounded source repair. The cull fixture is a model oracle and cannot independently prove that model's hardware accuracy. Full translation-unit compilation, shipping linkage, RNG-ring validation and native behavior remain outside this approval. Other scalar-dot readers and action predicates from the baseline Traffic100 review are outside this exact delta. Campaign/native credit remains **zero**.

`REVIEW.json` retains per-body verdicts, exact source bindings, fixture receipts and numerical limits. All fresh compilation and fixture outputs are isolated under this review's `fixture_run/`; shared source, refs, ledger, game/input state and CON were untouched.
