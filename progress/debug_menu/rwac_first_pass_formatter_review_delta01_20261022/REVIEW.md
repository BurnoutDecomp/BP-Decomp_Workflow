# RWAC FIRST_PASS formatter delta01 — independent source/design review

VERDICT: pass

I reviewed the exact four-file `SOURCE_DELTA.patch`, its preimage/postimage files, `FINDING.md`, `OVERLAP.md`, and source bindings. The `FIRST_PASS_WITNESS` format has 27 conversions and the preimage call supplies 25 variadic values. It omits `Count(DeviceOpened)` and `Count(DeviceClosed)` immediately after the device-open flag. The patch adds those two values in that exact position, each cast to `unsigned long long`; the resulting 27 arguments match the 27 conversions and types. The existing `StopBeforeWrite` formatter is unchanged.

The production edit is limited to the diagnostic `snprintf` argument list. It changes no `State`, `Counter`, `Event`, producer/consumer/queue behavior, capacity, or overflow stop. The preimage already holds the shared C++17 `inline State`, two 64-bit atomics per counter, and the device event enumerators, so this patch adds no state or ABI fields.

The hosted-only fixture calls the real `EmitFirstActiveOccupancy` after driving its matching trace epoch with the real trace helpers: it begins the System epoch, records a producer frame and engine begin, then records command-pass begin/end for the same System. It seeds three opens/two closes, four submits with one failure, five voice errors, six critical errors, and an `E_ACCESSDENIED` callback-registration result. Its six `CheckFirstPass` assertions validate the matching epoch/frame, device state and counts, submit/error/HRESULT group, voice/critical/registration group, record marker, and bounded newline-terminated output. This checks formatter alignment and the emitter gate; it does not exercise the live audio callbacks or establish audio health.

The original `RWAC_CAPACITY` counters and six intentional baseline failure labels are unchanged. First-pass checks have separate counters and a separate `RWAC_FIRST_PASS` summary. The baseline-control build excludes the witness and must emit neither that summary nor any first-pass failure label. The runner requires exactly six candidate first-pass checks with zero failures, and its baseline classifier requires zero first-pass summaries while retaining the original six capacity labels. `/we4473` and `/we4477` are passed only on the two fixture compiler commands; they do not change production build flags.

All eight refreshed LF source pins match the proposed postimages or the unchanged 968 source checkout. The retained baseline producer’s LF Git blob also matches its pinned original. The packet binds the source base to clean candidate commit `9683347ca74e3564986e19cf7bf43f46b5c7c05e` and tree `186a6377871f872535deb2cd3421e74b62ae74e8`.

This review gives no runtime, audio-health, hang-cause, or behavior credit. The hosted build and native 62040 logs are prior evidence for the existing candidate and malformed formatter; the proposed delta has not been compiled or run. No fixture, test, build, CI, game, or native execution was performed.

Full postimage SHA-256 values:

- `src/GameShared/GameClasses/System/PC/CgsRwacCommandTracePC.h`: `d9c24a0ba6a3fcd3fb368803c5740f38a34b4382592b2d93b3ae67fccad2455e`
- `tests/RwacCommandCapacity.cpp`: `09aff733a8d23336a23f7524ff47ee3616a98b210cf4ef6979c651dab85cb027`
- `tests/run_rwac_command_capacity.py`: `e67e25288b2c6c62aa827e68510027e926906442a70f4343f49565bfe171976a`
- `tests/evidence/rwac_command_capacity/source_pins.json`: `826888f88d3264d5d946c4b3338692a9ed881fc4d574c1f60a6395ab9a1543f2`
