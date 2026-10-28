The normal `build/game` package was refreshed on 25 October 2026 from source `412e803e` and workflow `b59368d5`, using hosted run **40208083584**.

- All **3,003 shipping translation units** compiled and linked; eleven selected regression groups passed.
- A private, muted 1280 x 720 run passed nine native checks: startup, junkyard exit, real player input, **308.6 metres driven**, no asserts or exceptions, and owned cleanup. Root inspected the rendered world, car, road, minimap and HUD.
- Captures were capped at six images. `world.bmp` retains the inspected frame. The earlier unsupported request-capture attempt remains a recorded failure.
- Fourteen package outputs were verified. Settings, logs and nine profiles retained their bytes and modification times. The previous package is backed up locally.
- Both `dev` branches received the fixture metadata corrections, preserving the concurrent Network CMake commit. The temporary refresh branches were removed. Every non-CMake source file in merged dev matches the tested source.

This establishes basic playability. Full online/custom-event behavior and the unfinished original-frame recovery remain separate. No new debug-site disposition is claimed.

See [delivery receipt](delivery_receipt.json), [native evidence](ROOT_NATIVE_JUDGMENT.json), [hosted verification](hosted_verification.json), and [dev synchronization](DEV_SYNC.json).
