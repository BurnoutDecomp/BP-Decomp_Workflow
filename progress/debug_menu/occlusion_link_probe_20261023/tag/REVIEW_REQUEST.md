# Review request: DispatchPacketInterpreter class-key normalization

Base: private source commit `e306dbd2a266a53b77cfb8ccbc86e01726dc5395` in `b5-decomp`.

The hosted link failed with unresolved `CgsGraphics::DispatchList::DispatchAllMeshOcclusionQueries(struct CgsGraphics::DispatchPacketInterpreter const*, int, int)` from `BrnRendererModule.obj`, while the body in `CgsDispatcherCommands.cpp` compiled. The source signature otherwise matches the declaration: same owner, const pointer parameter, and two `int` indices. This proposal changes only three forward declaration class-keys from `class` to `struct`; no signature, layout, body, alias, stub, or linker setting changes.

## Evidence

- DecFIGS `GameShared/GameClasses/Graphics/Dispatch/CgsDispatcherCommands.h:363` defines `struct CgsGraphics::DispatchPacketInterpreter`; its `SetTime`/`GetTime` members and `DispatchList` signatures appear in the same declaration chain. SHA-256: `0299C6C7B59051EE5E022D1EB61A745CB87DA5858C79923C2D6EA9FBE3A37ECB`.
- DecFIGS `CgsDispatcher.h` declares `DispatchList::DispatchAllMeshOcclusionQueries(const DispatchPacketInterpreter*, int32_t, int32_t)` at h:257; `DispatchPacketInterpreter` is the type defined as a struct above. SHA-256: `675E549213A4190B8E105B6E149BF0C9B1AE204C07D839278208C233328368DE`.
- The implementation TU `CgsDispatcherCommands.cpp` includes `GameShared/Jobs/ObjectToMesh/ObjectToMeshJob.h` before `CgsDispatcherCommands.h`. That chain reaches `ObjectToMesh.h`, whose class forward is currently the first declaration in that TU. This is the candidate reason the body object uses a different class-key encoding.
- The hosted unresolved symbol spells the parameter as `struct ... const*` and its decorated name encodes that type. The body source definition is present and was compiled, per the hosted report.
- The remaining relevant source forwards are inventoried with `rg`: `CgsDispatcher.h`, `ObjectToMesh.h`, and `BrnShadowMapRenderManager.h` currently use `class`; `pc/gcm/renderengine/reflections/SceneRender.h` already uses `struct`.

## Proposed owned source delta

1. `src/GameShared/GameClasses/Graphics/Dispatch/CgsDispatcher.h`: `class DispatchPacketInterpreter;` → `struct DispatchPacketInterpreter;` (the declaration used by `DispatchList` methods).
2. `src/GameShared/Jobs/ObjectToMesh/ObjectToMesh.h`: `class DispatchPacketInterpreter;` → `struct DispatchPacketInterpreter;` (included before the implementation body/header in the failing TU).
3. `src/GameSource/Graphics/BrnShadowMapRenderManager.h`: `class DispatchPacketInterpreter;` → `struct DispatchPacketInterpreter;` (keep all pointer declarations consistent with DecFIGS).

The `CgsDispatcherCommands.h` definition is already `struct`; `SceneRender.h` is already `struct`. No forward declaration or alias is added. No production files were edited: baseline and proposal snapshots are private copies under this directory. No compile, local build, or runtime check was performed. Confirm by a hosted link after applying the bounded delta.
