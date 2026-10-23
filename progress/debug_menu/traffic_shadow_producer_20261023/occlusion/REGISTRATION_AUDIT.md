# Renderer debug component lookup and registration gate

Read-only reachability audit for the report that `COMPONENT "RendererModule"` returned `Component not found` before the initial SAVE failure. No production edits, builds, launches, native/runtime checks, or Git operations were performed. This report carries no verified-site or runtime credit.

## Exact lookup key

ARTIST `BrnGraphics::DebugComponent::GetName` (`0x823F7B88`) returns `"RendererModule"`. ARTIST `GetPath` (`0x827DD168`) returns `"Renderer"`. `CgsDev::DebugComponent::GetComponentPath` (`0x82822218`) formats `"%s/%s"`, so the full menu path is `Renderer/RendererModule`.

ARTIST `CgsDev::DebugManager::FindComponentByName` (`0x82822400`) skips one optional leading slash on the input, walks the manager's `mComponentList`, obtains each component path, skips one leading slash there if present, and compares case-insensitively against both `GetName()` and the normalized full path. Therefore all of these resolve once the Renderer component is registered:

- `COMPONENT "RendererModule"`
- `COMPONENT "/RendererModule"`
- `COMPONENT "Renderer/RendererModule"`
- `COMPONENT "/Renderer/RendererModule"`

A leading slash is accepted, but the Renderer full path itself has no leading slash because its path is nonempty. The saved `COMPONENT "/World Module"` form is consistent with the same optional-leading-slash rule for components whose path is empty.

## Original construction and registration chain

- ARTIST `BrnRendererModule::Construct` (`0x8240A778`) calls `BrnGraphics::DebugComponent::Construct` at `0x8240BC94`. Current source mirrors this with `mDebugComponent.Construct(this)` at `BrnRendererModule.cpp:1412`.
- ARTIST `BrnRendererModule::Prepare` (`0x82409C20`) calls `CgsDev::DebugComponent::Register` at `0x82409F64` only on its completed/successful path, after `BrnSkyDomeManager::Prepare` and before `MemoryUsage`. Current source mirrors this with `mDebugComponent.Register()` at `BrnRendererModule.cpp:1536`.
- ARTIST `CgsDev::DebugComponent::Register` (`0x828331D8`) acquires the singleton manager, calls `RegisterComponent[Simple]`, then releases it. ARTIST `RegisterComponent` (`0x82832008`) inserts the component into `mComponentList`, clears its active bit, registers the UI row, and calls `OnRegister`. The current corresponding bodies are in `CgsDebugComponent.cpp:64-74` and `CgsDebugManager.cpp:395-422`.
- ARTIST `BrnGameModule::Prepare` (`0x823DB848`) is the caller: after preparing the top-level module and creating GameData input/output buffers, it obtains the GameData output allocator list and calls `BrnRendererModule::Prepare` at `0x823DB9F0`. The renderer's registration call is consequently gated on this outer Prepare lifecycle and successful allocator-backed renderer Prepare.

DecFIGS `BrnRendererModuleDebugComponent.h` confirms the derived component and virtual `GetName`, `GetPath`, and `OnActivate` shape. It is not used to override ARTIST behavior.

## Current host reachability and PC bridge check

The current renderer object is constructed after the game module's debug manager: `BrnGameModule.cpp:328` constructs `mDebugManager`, and line 405 calls `mRenderModule.Construct()`. The current renderer `Construct` reaches the component constructor. The current renderer `Prepare` has the original register call, but no current `mRenderModule.Prepare(...)` call site exists in `GameSource`.

The top-level PC shell's `EnginePrepare()` at `BrnMain.cpp:258` ends by calling `gGameModule.Construct()` at line 293. The file header explicitly marks the 5-stack `BrnGameModule::Prepare` loop as gated. The current `BrnGameModule` has the per-frame helper `GamePrepare()` (`BrnGameModule.cpp:3579`), which is distinct from the console 5-argument module `Prepare`; it prepares GameData and later calls `mRenderModule.PrepareAgain`, not `mRenderModule.Prepare`.

The inspected `pc/debug` code provides INI-driven activation/registration sidecars and a request-context flag. Those operate on an already-registered component; they do not construct or add a component to `mComponentList`. `ComponentMenuRequest` is set around activation after lookup. Renderer has no `EnsureDebug*` helper in its source; its `Ensure*BringUp` helpers cover renderer resources and managers. No current PC runtime-debug registration bridge can make the Renderer component discoverable before its original Prepare call.

## Finding

`RendererModule` is a valid short lookup name; the exact full key is `Renderer/RendererModule`. The original constructor and registration bodies are present, and current renderer source contains both call sites. The current host boot shape constructs the renderer object but does not reach its `Prepare`-time Register call because the original 5-stack `BrnGameModule::Prepare` owner and call loop are absent. The correct repair boundary is that outer lifecycle with its original IO stacks and GameData allocator list; adding a direct call to `EnginePrepare` or activating the member directly would invent the missing arguments/order. No renderer registration patch is proposed.

This source trace explains why an unregistered component can fail lookup. The reported native message itself was not reproduced, and this audit does not establish whether the exact native run had any additional manager-instance or script-parser issue.

## Evidence bindings

ARTIST exports:

- `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x823DB848.json` — SHA256 `2C039B3148E10163B2CF7F87525AE20DB1D1A59610B0EA25F605004DC59881FD`
- `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x8240A778.json` — SHA256 `839E5C4EE9BF7E52796A1B75E93F28D813FEB049FF8049AD4AF25869223AD7B8`
- `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82409C20.json` — SHA256 `9486535B450D3E7EF29A3333606765360191FB63EDA88B6912AFF4A08D4605D7`
- `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x823F7B88.json` — SHA256 `CD9D666C3FD65B205FA1394EF69D842576D4F6813774058B4D730EA940D6C00E`
- `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x827DD168.json` — SHA256 `E33C89343B1283E266B59E9A618EDBDE43E0AF10C9F53417CD2D906B10E8167C`
- `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82822218.json` — SHA256 `A9ACFABB74AB3CEB5D7310BA8219B652F7968D1A0248BB274CDE56C1787FDA93`
- `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82822400.json` — SHA256 `118A5B5FB49C74CF84036E229B3444DE518D51208E1E924AF3A64C42BA6752AA`
- `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x828331D8.json` — SHA256 `5DA949B68E0C4468706311D83F5A02782D418E522F52BD8159B50F5AC0C0C74A`
- `.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82832008.json` — SHA256 `0BEF06F2925A12D1F2FE8D83FBB3DF1B88E30F0FD3A349B8AE07D19DBF432FED`

Current-source references are line-numbered above. The original DecFIGS declaration is `references/DecFIGS/dwarfdump/GameSource/Graphics/BrnRendererModuleDebugComponent.h`.
