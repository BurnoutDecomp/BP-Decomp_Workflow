# RaceCar replay producer and typed frame

Source-only continuation from private B5 `f32c7d531d98c811a89f69a6f868fdc10b74716a` and workflow `5a73986a22c5a4f5f3f242dfec678688e75bad13`. Eleven owned files are isolated in `postimage/b5-decomp`; `source.patch` applies to that exact B5 base using a temporary index. The shared checkouts, ledgers, native package and menu credit are unchanged.

The previous unsealed `swarm_replays_racecar_traffic_producers_20261029` postimage supplied the initial recovery. Its ten preimages exactly match V3. This continuation adds the original stream-pump access and repairs assembly discrepancies before freezing fresh evidence.

## Recovered chain

| Original ARTIST record | Recovered responsibility |
| --- | --- |
| `0x822EA8F8`, `0x822B6878`, `0x8279E9C0` | PostPhysics output owns the actual eleven-serialiser replay registry. Construct clears those slots and constructs the following vehicle interface; lock-qualified getters return the real member. |
| `0x822B6488`, `0x822B6920` | Correct attribution: Director input at console `+826992`; vehicle input at `+855200`. Replay registry is `+855152`. |
| `0x822FD898`, `0x8264C4C0` | RaceCar module embeds and constructs serialiser id 0 at console `+0x18600`; BaseSerialiser receives the original skip flag and native typed capacities. |
| `0x8230D928` | PreScene detects replay entry/exit, clears the static frames, reads the playing frame when permitted, then invokes UpdateSerialiser. |
| `0x822D2C88`, `0x822D2DC0` | Eight replay scene placeholders are added/removed using the original entity id, flags, radius and latch stores. |
| `0x822F5CF8` | Playback publishes recorded active/global output interfaces and rebound deformation handles. Recording produces both interfaces, attached-slot model ids and render records. |
| `0x82306120`, `0x82301BB0` | Scene positions, replay resource requests/readiness, restore rebinds and physics validation events come from the typed live frame and actual native ResourcePtr aliases. |
| `0x822EB168`, `0x822EB500` | Loaded and invalidated resource paths maintain the two real ResourcePtr aliases; invalidation emits the original false validation event before clearing handles. |
| `0x82307538` | PostPhysics registers the embedded serialiser before unlocking, then writes recording data and refreshes the previous snapshot on keyframes. |
| `0x82657748`, `0x822E7820` | Typed frame Clear and queue-aware assignment cover both interfaces, eight RenderParams, and both CgsID arrays. |

Raw records, including their assembly, are copied under `evidence/ARTIST`. DecFIGS corroboration retained from the prior packet is under `evidence/DECFIGS`.

## Assembly corrections in this continuation

`Frame::Clear` loads `r20=-1` at `0x82657804`, stores it twice at `0x826579C8/CC`, and stores LOD 4 at `0x82657A08/0C`. The unsealed packet used Hex-Rays' invented `0x1FFFFFFFF` mask and omitted LOD. Both are corrected.

The recording producer's initialization is the actual memset, two all-ones stores and event-queue Construct before RenderParams assignment. Extra identity/colour/flag resets from the prior packet were removed. Model-id validation follows the copy in the original order.

Replay streaming inlines the five component pumps and UpdateDesiredCars. Calling `RaceCarStreamer::Update(...,0)` also wrote the timer; the recovery now accesses the real typed members through friendship, with no new engine wrapper and no timer write. Restore mode retains the original full Update call.

## Native types and scope

The original frame is `0xD7E0`: active interface at 0, global at 10480, eight 5280-byte RenderParams at 12896, car ids at 55136 and wheel ids at 55200. The actual native active interface widens by 64 bytes, producing a 55328-byte frame and a 110720-byte two-frame owner with the original 64-byte tail. Static assertions pin each native offset and size. Raw Read/Write now use `sizeof` these native types. Cross-bitness replay-file compatibility is not claimed.

Real common replay registry declarations already exist in V3. No GameModule/Main/common ReplayIO changes are included. ResourcePtr/queue methods and other providers remain the existing recovered implementations; this packet does not certify their full behavior.

## Verification

`audit_controls.py` checks the producer ordering against the actual frozen sources and the original mask/LOD instructions. It rejects omitted serialiser construction, registry publication, keyframe copy, the bad mask and the missing LOD store. This is source topology evidence.

`immutable_gates/final_*` contains fresh canonical MSVC `/c` results for the actual serialiser, IO, ActiveRaceCar and RaceCar module TUs. Include roots are the frozen packet, exact V3 Git delta overlay and the reused immutable f1 Git snapshot. Every opened header is hashed; vendor Gitlink headers are verified. `COMPILE_CONTROLS.json` reports positive gates and two actual-consumer omission controls: restore the wrong ResourceRequestInterface alias, or restore the opaque frame header. Each must fail compilation.

The superseded `resume_serialiser` attempt intentionally remains visible: the no-concurrent-drift guard rejected a comment-only edit during that attempt. Only `final_*` receipts apply to the final source hash.

No whole link, gameplay run, visual playback, native replay-file roundtrip, or menu-site verification was performed. Integration and the independent combined review belong to the coordinator.
