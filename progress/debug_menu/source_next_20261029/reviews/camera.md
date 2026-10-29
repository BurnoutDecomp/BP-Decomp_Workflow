# Independent CameraX360 compressed-picture review

VERDICT: pass

This verdict covers the sealed private implementation of `BrnNetwork::CameraX360::GetCompressedLocalCameraPicture` and the current host queue/compression fixture. No body defect was found. It is not a claim that camera capture, the full game link, or event-buffer lifetime works at runtime. Strict delivery verification is **unverified**: the author packet contains no delivery patch, apply record, or post-apply manifest.

## Evidence integrity and exact change

The author root is `scratch/DEBUG_MENU_1011/swarm_camera_x360_compressed_picture_recovery_20261029/`. All 59 `PINS.json` file hashes and sizes matched the current bytes. The `SEAL.json` report and pins hashes also matched. All 59 author pins still matched after this review. See `pin_verification.json`.

I independently derived `independently_derived.patch` from the pinned canonical preimages to the sealed overlay. It changes exactly three files: the camera cpp body, camera header declaration/comments, and the compressor header's fixture friend. The camera header also contains an unused fixture friend (`CameraX360TestAccess`), which is absent from the report's description but has no storage or runtime effect. The compressor friend is needed by the fixture. Neither friend demonstrates layout parity.

`derived_pre_post_bindings.json` records the exact preimage and overlay byte hashes. Applying every independently derived hunk against its exact canonical context in `private_patch_replay/` produced byte-identical CRLF postimages for all three files (`private_patch_replay.json`). This validates the recoverable canonical-to-overlay change; it does not validate a nonexistent author delivery patch or authorize applying it to shared source. A later delivery must bind its actual patch, preimages, apply result, and postimages explicitly.

## Raw function, signature, and callers

- ARTIST `0x82586890`: the prologue saves destination `r4`, quality `r5`, callback `r6`, callback data `r7`, and `this` `r3`. Destination/null and DXT1-format assertions precede `XCamGetStatus`; only status 2 reaches the compressor assertion and enqueue.
- The prepared texture is `this+0x43B50`, with bits-per-pixel `+4`, width `+8`, height `+0xC`, format `+0x10`, pixels `+0x14`. `0x82586978–0x825869A0` computes `(height*width*bpp+7)/8`. This is the existing typed texture member, not geometry read from an opaque stream engine.
- `0x825869A4–0x825869E8` obtains destination and source stride, then passes compressor, pixels, size, width, height, source stride, destination stride, quality, source format, false YUYV flag, callback, and user data. The recovered accessors supply the same values. Their C++ evaluation order does not alter these pure reads.
- ARTIST raw xrefs list exactly two direct callers. `NetworkImageManager::GetCompressedTexture` (`0x8256BC38`, call at `0x8256BD00`) passes its destination, quality 0, its callback, and `this`; it ignores the result. `StateManager::ProcessNetworkEvents` (`0x82571610`, call at `0x82572738`) loads quality and destination from the request payload and passes its callback and `this`, then branches away without reading the result. The current source calls at `BrnNetworkImageManager.cpp:1383` and `BrnNetworkStateManager_wN1_03.cpp:647` agree.
- The X360 decompiler's three-argument/int prototype is wrong/incomplete. `r3` retains status on early exit and the enqueue callee's residue on ready exit; no explicit semantic return is constructed. DecFIGS `BrnNetworkCameraPS3.h:173` and `.cpp:14` declare the analogous four-argument method `void`; its compressor declaration (`CgsNetworkTextureDXTCompress.h:91`) is also `void`. The candidate's `void` declaration is supported, with the limit that PS3 is a role analogue and X360 instructions alone do not encode a formal C++ return type.

## Compressor and stride chain

ARTIST enqueue `0x8287EF60` copies into the selected uncompressed slot at `0x8287F058–0x8287F070` before storing metadata, callback/user data, and the pending flag through `0x8287F0AC`. The current compressor cpp `:145–177` preserves that sequence. ARTIST update `0x8287ECC0` selects its own source/output slots, schedules DXT work, and on completion clears callback registration and calls the callback with the compressed ring-slot pointer (`0x8287EDBC–0x8287EE04`, `0x8287EF44–0x8287EF50`). Current host `Update()` `:235–275` retains the queue and callback ownership while invoking the DXT entrypoint locally; it does not prove console scheduler parity.

ARTIST `NetworkTexture::GetStride` `0x8288B958–0x8288B96C` multiplies width in blocks by `(16*bpp)/8` for DXT1. For 160 pixels, 40 blocks times 8 bytes gives **320 bytes**, not 40. The source G8B8 pitch is also 320 bytes; source data is 38,400 bytes, compressed output is 9,600 bytes. The current texture accessors and fixture agree. Network-manager buffer capacities are 76,800/9,600 bytes, and `BrnNetworkManager_wN1_02.cpp:148` services compressor `Update()`.

## Required correction to the author report

The author searched only `GameSource/Network` for the event consumer. The resulting statement that no in-tree handler reads the compressed pixel pointer is too broad:

- `GameSource/Game/GameBridgeNetworkToX.cpp:1130–1139` handles network event 72, reads the compressed format/size/pointer, and forwards those fields as `GuiEventCamPicCompressed`.
- `GameSource/Gui/BrnGuiDemangledEventTypes.h:200–206` identifies that GUI event as 569.
- GUI states dispatch the payload to `PhotoBoothComponent::HandleCompressedStillImageEvent`; examples are `BrnIntro.cpp:714–715` and `BrnCrashNavDriverDetails.cpp:835–836`.
- `BrnPhotoBoothComponent.cpp:539–571` reads the payload and copies its pixels into `mCachedPicture` when the component is waiting for a still image. The source uses the differently spelled field `mpacCompressedPixels`, which the author's exact-field search missed.

These source consumers exist. Their queue scheduling and copy-before-output-ring-reuse have not been validated here. The author's borrowed-pointer lifetime limit therefore remains valid, but its missing-consumer explanation should be replaced with this observed chain. Extra reviewed sources are hashed in `extra_source_pins.json`.

The other consumer, `NetworkImageManager::_GetCompressedCameraPicCallback` at `:1443–1453`, copies the callback bytes into `MugshotData`. That callback receives the compressor output slot, not the destination texture passed into the camera method.

## Independent build and fixture verification

The actual sealed owner cpp compiled successfully using `tools/build/msvc_env.bat`. Its response-file flag line exactly matches `tools/build/msvc_flags.txt`; its include list exactly matches `tools/build/msvc_includes.txt` after one prepended private overlay include. The only owner response-file change was its object output path. See `owner_compile/compile_owner.log`, `owner_compile/owner_compile.rsp`, and `build_control_checks.json`.

I verified that `fixture/camera_method.inc` contains the exact extracted candidate body after only the documented owning-type rename. The fixture uses a minimal named-field view, so its runtime execution does not validate actual CameraX360 layout; compiling the actual owner TU separately validates declaration/body compatibility.

All fixture compile/link response files and its build script were reproduced under `fixture_build/`, rebasing only author build output/response paths. The fixture was rebuilt from the current source inputs and ran with exit 0. See `fixture_build/build_fixture.log` and `fixture_build/fixture_run.log`. The fixture checks ready/not-ready submission, sizes/geometry/320-byte pitches/quality/format/YUYV, staging-copy stability, owned source/output pointers, callback timing/data/clear, changed DXT output, and the untouched destination texture. XCAM status/assert functions and an unrelated thread-sleep link dependency are fixture substitutes. This proves the exercised host queue path, not device capture, DXT quality equivalence, arbitrary image geometry, concurrency, or repeated ring-buffer lifetime.

The author pin set binds its selected inputs, response files and build artifacts; it is not a complete transitive compiler dependency manifest. The independent rerun proves the current build inputs work, not that every source/header/toolchain dependency can be reproduced from the author seal alone.

## Limits and writes

`CameraX360::Prepare`, `Update`, and `GetLocalCameraPicture` remain placeholders in canonical source. The fixture explicitly seeds the prepared source texture and controls status. Real XCAM frame production, host camera support, full game integration, and GUI/event timing remain incomplete or unverified. No canonical state/count or function-completion status is advanced by this verdict.

All review writes and compiler outputs are inside this exclusive review folder. No author artifact, shared source, reference, ref, native binary, or game/device state was changed. Graphify's existing graph was read only for owner navigation (vocabulary: camera, compressed, texture, compress); raw/source checks determine this verdict.
