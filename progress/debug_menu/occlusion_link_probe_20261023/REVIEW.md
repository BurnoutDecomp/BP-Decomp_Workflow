# Combined source review: dispatch type tags and occlusion probe

TAG_VERDICT: pass

PROBE_VERDICT: pass

VERDICT: pass

## Pins and scope

Both packets are bounded to source base `e306dbd2a266a53b77cfb8ccbc86e01726dc5395`. I verified that each packet preimage matches the corresponding `e306` Git blob. The tag packet changes three headers; the probe packet changes two implementation files. There is no overlap. This is a static source verdict only: no build, hosted relink, game run, or native evidence was produced here.

| File | `e306` blob | Proposal SHA-256 |
|---|---|---|
| `src/GameShared/GameClasses/Graphics/Dispatch/CgsDispatcher.h` | `9d433053af8905b8f363376a43b6b1c372502da4` | `15F05FB1CA227386F05D429E813C991B83CA5344566C8E0C811953224C772AE1` |
| `src/GameShared/Jobs/ObjectToMesh/ObjectToMesh.h` | `0d0ac6cf19d0798125b5d8b3911af8a8da1df19c` | `D8CDFE709DC7ABE84BCC3A808A74DC408269666B57AD79A0EB781558172CCE8A` |
| `src/GameSource/Graphics/BrnShadowMapRenderManager.h` | `7bf82277939e35623bb2934427ab1ac82010c9e9` | `C3B17A52E2E6F266ACDBDB2F2D4537B3DA80900AECFE44415564A477951DDC4C` |
| `src/GameSource/Graphics/BrnRendererModule.cpp` | `d467e20874629c131ac56b8e01078cefe74c47ba` | `80282EB7140AC32F6EAE3827973E680213CC651E8C953C5DF39198D7F8F71D44` |
| `src/pc/gcm/renderengine/OcclusionQueryProviderPC.cpp` | `69cb9a806386e4d36abde4c25cf86a203609cd38` | `BED6630E5BBB0E0BD3344A95E1111F94391B36FF60E130C555D9906C21998CF5` |

## Findings

The three forward-declaration edits are source-faithful and narrowly fix the reported MSVC class-key mismatch. At `e306`, `CgsDispatcherCommands.cpp` includes `ObjectToMeshJob.h` before `CgsDispatcherCommands.h`; the former's first forward declaration of `DispatchPacketInterpreter` is `class`, while the latter defines it as `struct`. The same mismatch appears in `CgsDispatcher.h` and `BrnShadowMapRenderManager.h`. `git grep` over the pinned tree finds no other class-key forwards; `SceneRender.h` already says `struct`. The DecFIGS declaration is also `struct` (`references/DecFIGS/dwarfdump/GameShared/GameClasses/Graphics/Dispatch/CgsDispatcherCommands.h`, SHA-256 `0299C6C7B59051EE5E022D1EB61A745CB87DA5858C79923C2D6EA9FBE3A37ECB`), and its `DispatchList` prototype takes `const DispatchPacketInterpreter*` plus two 32-bit indices (`CgsDispatcher.h`, SHA-256 `675E549213A4190B8E105B6E149BF0C9B1AE204C07D839278208C233328368DE`). The patch changes only the three class-keys; it changes no signature, layout, body, alias, or linker setting. This is a reasonable fix for the reported decorated-symbol mismatch, but hosted link success remains unverified.

The probe is passive with respect to renderer/provider decisions. It captures the existing query-pass return in `liQueryNext` solely for logging; the existing draw cursor `liNext` still drives the same capped `DispatchPassList` continuation and final `-1` return. List tagging is valid for this lambda's four call sites (19, 11, 15, 20). State and batch rows read existing flags, list counts, and return cursors after the original calls. Provider rows are emitted after the original `Issue(END)`, `GetData(S_OK)` state update, or immediately before the existing conditional decision return; no additional GPU query, `GetData`, draw, query-state write, or branch outcome was added. `XenonD3D9Shims.cpp` sends `OcclusionQueryProviderPCShouldDraw`'s return into the existing `WorldDraw_IndexedUP` early-return gate, so `result` plus same-serial `decision` rows witness the host consumer path. Provider rows omit list/frame, so the native parser must associate them with the `[occ-batch]` summary that immediately follows the corresponding batch's query/draw calls; same-run provider rows alone do not establish list 11.

The exact opt-in is `BRN_OCCLUSION_DIAG=1`; other values produce no rows and do not increment the diagnostic counters. Provider trace call sites still perform a cached-flag check when the query path is active even with diagnostics off, so “opt-in” means no output/counter increments, not a zero-instruction disabled path. The `%u`, `%d`, `%llu`, and `%s` format arguments have matching explicit casts/types; fixed stage strings are short constants. `CgsDev::Log::WriteToLog` copies the stack buffer into its queue before returning, so the local `snprintf` buffers do not escape their lifetime. The renderer and provider counters are mutated synchronously along the existing `Render` → `RenderWorldPasses` → dispatch/shim call path; this matches the provider's existing unsynchronized slot ownership and introduces no new cross-thread handoff. Logging still adds bounded render-thread CPU/lock work, so the candidate is unsuitable for performance claims.

## Limits for the proposed native case

The caps (24 state, 192 batch, 512 provider rows) suppress later output silently; there is no overflow marker. Treat a log at any cap, missing rows, or missing target-list results as truncated/inconclusive rather than evidence that the path did not run. The `unavailable` provider row covers the invalid/no-survey scope branch, but not every later unavailable path (for example, device/query mismatch or a `GetData` error); absence of that row cannot prove there were no such failures. The successful path is still observable through `ended`, same-serial `result` (`S_OK`) and `decision` rows.

The probe reports the provider decision and dispatch cursors, not a separate count of D3D draw API calls. Pair it with the planned >64-record contiguous list-11 query/draw walk and fresh world pixels. D3D9's existing nonzero-samples-means-draw policy and fail-open behavior are host-only evidence; Xenos zero/nonzero polarity remains open. This does not grant ten-site or broader parity credit. The smoke plan at `graphics_occlusion_smoke_plan_20261023_luna01/PLAN.md` remains blocked until the corrected source set passes hosted linking and its exact diagnostic row contract is bound.
