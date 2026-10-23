# Fresh source review: traffic reflection shadow contract

Date: 2026-10-24
Base: `ea5ce572baedd4ad8918f6d5bfcdfd756250d411` (parent `b9c0e692bc9d8f232b9986923acf07aff26c0639`).

## VERDICT: pass

The one-file delta uses the existing reflection-capture scope to keep the PC-only cubemap geometry call out of the original ground-shadow producer. It preserves the main-view buffer contract and existing shadow-map gate. This is a source review only; the retained native smoke remains RED, and this review gives no runtime or gameplay credit.

ARTIST `BrnTraffic::TrafficEntityModule::RenderTrafficCar` at `0x82728B08` has one X360 caller: `TrafficEntityModule::GenerateDispatchLists` at `0x8273B280`. That owner obtains the shadow-map and blobby-shadow buffer from the traffic dispatch input, asserts `lpBlobbyShadowRenderer`, and passes it to `RenderTrafficCar`. The G6 AddShadow branch at `0x827292D8..0x82729554` is guarded by `!IsRenderingShadowMap()` and the original physical/physics condition. The branch invokes `AddShadow`; the shadow-map pass stays excluded by that existing flag.

The pinned PC `WorldModule::GenerateDispatchLists` calls `TrafficCapture::Submit` separately for each enabled environment-map face, after the main-screen traffic dispatch and before the later shadow-map cascade. `TrafficCapture::Submit` creates `VehicleScope(E_CAPTURE_TRAFFIC, ...)` before calling `RenderTrafficCar` and passes a null blobby buffer. `VehicleScope` saves and restores the thread-local capture category, vehicle draw distance, and face list; its destructor runs after the direct render loop and input unlock. `IsVehicleCapture()` reads that same capture-category state, and this direct call is synchronous on the same thread.

The patch adds the capture predicate as the first conjunct around G6. In the reflection face, short-circuit evaluation skips only ground-shadow calculation/publication, avoiding the null `this` read in `AddShadow`. The traffic body and wheel geometry path continues. The normal main dispatch runs outside `VehicleScope`, so its original ground-shadow producer remains enabled when the prior map/physical gates permit it. The shadow-map pass remains excluded by the original `IsRenderingShadowMap()` gate. The buffer pointer, transform, and `AddShadow` call are otherwise unchanged; no null fallback or mutation of shared shadow-map state was introduced. The one-file preimage is byte-identical to the pinned base, and the patch changes only the G6 comment and guard.

The retained pre-fix native evidence remains a RED crash: the exception reads address zero in `BrnBlobbyShadowBuffer::AddShadow + 0x3`, called from `RenderTrafficCar` via `CgsPC::Reflections::TrafficCapture::Submit`. Its executable hash is bound in `BINDING.json`. This supports the caller-contract diagnosis; it does not validate the proposed fix. The earlier hosted 11-group result is not a build or runtime result for this new delta.

No local C++ compilation, tests, CI, post-fix native launch, game, input, source edit, or Git mutation was performed.

See `BINDING.json` for exact pre/post, original ARTIST, PC scope/source, and RED capture hashes.
