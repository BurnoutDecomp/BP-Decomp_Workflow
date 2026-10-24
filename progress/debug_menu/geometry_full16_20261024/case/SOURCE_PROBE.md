# Bounded owner diagnostics proposed for hosted build

`source/patch.diff` changes the two actual component `RenderWorld` bodies and adds an opt-in capture request in the existing PC back-buffer writer. It does not change variable registrations, field values, geometry, colors, collision inputs, interval lists, or production decisions.

- `TriangleCollisionDebugComponent::RenderWorld` logs the typed spatial-map soup-list count and live/requested level counts after the existing map build, the paired memory-use value, collision/AABB/edge/swept-sphere fields, swept-sphere position/radius/velocity, and the source draw distance.
- `SceneSweeperDebugComponent::RenderWorld` logs its actual typed owner, `GetDynamicIntervalList().GetNumIntervals()`, `GetInactiveIntervalList().GetNumIntervals()`, current draw toggles, and draw distance at the real component consumer.
- `DumpBackBufferIfRequested` reads `BRN_FRAME_DUMP_REQUEST=1` and the positive `BRN_HARNESS_SLOT`, opens `Local\\BurnoutPC_FrameRequest_<GetCurrentProcessId()>_<slot>`, and uses its existing back-buffer-to-BMP writer only while that event is signaled. It resets the request and logs the sequence/present/filename only after a successful file close. The case helper checks the same game's PID and slot before setting the event, then waits for this matching acknowledgement and image before the next site state.
- The two geometry blocks are inert unless `BRN_DEBUG_GEOMETRY_WITNESS` is present. They sample the first observation, stored control tuple changes, and bounded readiness transitions only. Triangle reports exact current soup-list counts, but the trigger uses empty/nonempty readiness, not each growing count. The frame request path is separately inert unless `BRN_FRAME_DUMP_REQUEST=1` and a positive harness slot are present. No frame number, changing address, animated position, physics mutation, or synthetic query result is included in the geometry diagnostics.
- Triangle cap is40 rows per process: at most37 control-state transitions +1 initial owner row +2 soup-readiness transitions. Sweeper cap is11: at most7 control-state transitions +1 initial row +3 one-time owner/list-ready observations. Both maxima come from the actual full16 schedule; no per-frame sampler is present.
- All three source files are already mounted in `tools/build/build_game_exe.bat`; no build-list change is proposed. Their exact36ae preimages and postimage hashes are bound in `source/BINDINGS.json` and `CASE_SOURCE_BINDINGS.json`.

## Candidate and provider identity

- B5 source: `36ae3ffed6e8fb3ea89ca91947647aa9465c8658`, tree `11d65ea7620c833b4fe36d943f85bfdc2a186128`.
- Original case base artifact: hosted workflow `1c7766f9da14ef677bac273e16921196ea58f9fc`, run401033, installed executable SHA256 `6950637c5d3098d41a784701c5d35cf8cded1e1eb0328eb09cd65bd9d97ece5b`.
- The original color path remains `rw::RGBA(255,0,0,255)` for dynamic intervals and `rw::RGBA(255,255,255,255)` for inactive intervals. The provider is `RwRGBA.cpp`, already mounted. The case does not add a mock or duplicate provider.

The red constructor stores `m_rgba = 0xFF0000FF`; the white constructor stores `0xFFFFFFFF` using the existing canonical `(alpha << 24) | (blue << 16) | (green << 8) | red` packer. Exact36ae provider bytes are bound in `CASE_SOURCE_BINDINGS.json` (`RwRGBA.cpp`, SHA256 `d99f46e767dcb2ea7a95528da8e6f4960d05d7832e871d3c0ec52a09e83c63a1`), and the shipping manifest already lists it at `tools/build/build_game_exe.bat:783`.
