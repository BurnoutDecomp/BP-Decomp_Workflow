# Main-map event-payload source review

VERDICT: pass

Reviewed the one-header proposal against immutable B5 `5093cdb07f74fe0cfa6a6a32283fb6195be790ab` (tree `684d10b1b878200cdebf1b6fab29ce03646ea828`), the current b6 source object, the pinned ARTIST producer/wrapper/consumer exports, and DecFIGS. The exact preimage matches the 5093 Git blob and b6 `HEAD`; the proposal changes only the event base and adds its explicit type accessor. The payload fields and their order remain unchanged.

ARTIST `MainMapComponent::Prepare @0x8244F4A8` seeds the component active byte at `+0x67C`; `SetActive` writes that same member. `MainMapComponent::Update @0x824696E8` copies it into the final active field at `var_74`, after the two 16-byte rects, active-texture pointer, zoom and map type. It calls the named `OutputViewState<GuiEventRenderMainMap> @0x82465E50` with the first field at `var_A0`.

The actual X360 wrapper resolves the event id independently of size. Its assembly copies six qwords (48 bytes), writes wrapper size `48`, type `0xDF` (223), and payload offset `0x10`, then posts the 64-byte wrapper through AddEvent channel `0x29` (41). `CustomRendererManager::RecvEvent @0x824443D0` has a case for 223, and `MainMapRenderer::RecvEvent @0x82449E98` checks 223 and copies 48 bytes to renderer storage at `this+0x10`. The DecFIGS `GuiEvent<221>` base annotation conflicts with this concrete ARTIST producer and both consumers, so 223 is the event type for behavior. ARTIST independently posts 221 for `GuiEventSetBlackBars` at `0x823CEE50`, further distinguishing the ids.

The proposal removes the reconstructed generic three-word `GuiEvent` prefix while retaining `CgsModule::Event` and `GetEventType() == 223`, matching the raw X360 field sequence and separate output wrapper. The 48-byte payload is the X360 32-bit shape; the source keeps a native-width pointer on PC, so this review makes no host `sizeof` or runtime queue-size claim.

The active bit remains separate from the tile/event gate: `MainMapComponent::RecvEvent @0x82458370` handles event 213 for the main-map type and writes its show byte to `MapManager::mbEnabled`; `Update` reads that gate for map refresh and emission, while publishing `mbIsActive` from `+0x67C`. The renderer receives the active field through event 223. `RenderComponent @0x82460130` uses alpha `0x80` when inactive with no fade, and `mu8Alpha` when active or fading; `UpdateAlphaForFadeState @0x824465E8` supplies the fade alpha. This layout correction does not establish the cause of the reported opacity. No opacity fix or runtime behavior credit is claimed.

Exact source preimage SHA-256: `8127f5fb1bb74f4827da3057ebff8f8f844fd5ab130492071d9513612ecdf45a` (21414 bytes). Exact full postimage SHA-256: `a89deda96b977771cbcd9be1661a593ab1b7f63806a5f70d0e78b39b2b61a8bc` (21467 bytes). Patch SHA-256: `e083cd492db63f2b9ab4ea9e6cdd36032f00b38ffe02681726bb7a5d86b4de46`.

Source/design review only. No build, fixture, game, CI or IDA action was run.