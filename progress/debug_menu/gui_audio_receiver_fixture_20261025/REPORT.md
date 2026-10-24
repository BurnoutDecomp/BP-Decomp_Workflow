# GUI audio fixture: receiver binding correction

Status: **fixture-only source proposal; no production code or event semantics changed.** B5 candidate base is `c18c333098a18871059a06c51b958f2e7e3de82c`, workflow base is `ebeed3d59d69d27369629962bb85e383e8892124`, and baseline is `4c7c6ba2f97533315d5663d22499042cb007df31`. The exact source patch, preimages, postimages, source bindings, and input pins are recorded in this packet.

## Failure and root cause

Hosted run `40136323622` failed in the new GUI audio trigger fixture at candidate `audio_extracted.inc:147` and ID-only `audio_extracted.inc:198`: `AddGuiOutEvent` was called on the test shadow `VariableEventQueue<18432,16>`. The actual candidate receiver is `CgsGui::CgsGuiModuleIO::OutputBuffer`, which owns the inline `AddGuiOutEvent<T>` API. The fixture had collapsed three distinct source roles into one receiver type:

- Candidate source callback uses `OutputBuffer::AddGuiOutEvent<T>`.
- Baseline source callback uses a raw queue and `AddEvent`.
- ID-only mode compiles the candidate callback and separately invokes an old callback body; those callback bodies need different receiver types.

This is an extractor/harness binding gap. The current production callback and OutputBuffer header already agree.

## Bounded correction

The patch changes only the source-extracted test runner, the test harness, and the hosted script’s two exact LF-normalized input pins:

- Candidate mode binds the extracted current callback to the real `OutputBuffer` type. It compiles the exact `CgsGuiModuleIO_OutputBuffer.cpp` and `CgsIOBuffer.cpp` providers, constructs and clears that buffer, locks it for writing around the unchanged callback, unlocks it, then reads its `mOutEvents` through the harness’s existing `private=public` introspection flags.
- Baseline mode keeps its original raw `VariableEventQueue<18432,16>` receiver and `AddEvent` callback. This preserves the baseline’s expected numeric failures.
- ID-only mode compiles the candidate callback against `OutputBuffer` while assigning the legacy callback a distinct `LegacyGuiModule` with the original raw queue type. It reaches the intended payload mismatch control instead of failing to compile.

The runner includes the exact OutputBuffer header in the revision shadow. The ID-only legacy method is renamed and retyped only inside its generated fixture projection so both source versions can compile in one control build. No fake `AddGuiOutEvent` method is added to the queue, and no test predicate is loosened.

## Controls and limits

All 50 existing `Check(...)` expression lines are identical in the proposed preimage and postimage. The CI script changes only the pinned SHA-256 values for the updated runner and harness; both expected failure markers remain unchanged.

The candidate positive path still covers all 14 action names, unknown-action handling, string truncation and termination, raw `457/100`, sound message 6 with payload 100 and total size 116, cache-201 bypass, channel-40 unwrap, caller-input ordering, and once-only inbox retirement. The bounded legacy `{0,201,12}+100` compatibility case and the real `201/8` HideDriveThru preservation control remain intact.

The baseline must still exit with the original numeric failure marker `EXPECTED_BASELINE_NEGATIVE id=201 size=112 cache201=1 message=128 assertions=0`. ID-only must still execute and fail numerically with `EXPECTED_ID_ONLY_NEGATIVE id=457 size=112 message=116 payload_match=0 assertions=0`. Both controls require zero assertions; a compile failure does not satisfy them.

No local C++ compile, fixture or test import/execution, CI, game or native run, Git mutation, or index mutation occurred. Root owns review, application, hosted compilation, and execution of the three modes. A fixture pass will not by itself establish audible playback or native debug-site behavior.
