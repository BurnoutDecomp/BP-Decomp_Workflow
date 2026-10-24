# Source-to-consumer reconciliation

This mapping is for the exact `edca` preimage and proposed postimage only.

| Source stream | Preimage behavior | Proposed single delivery |
|---|---|---|
| Flow channel 40 | `DrainFlowOutputQueue` unwraps into `mGuiOutQueue`, then immediately calls cache/renderer/flow consumers; IDs 141/144/507 also execute shortcut handlers there. | Keep unwrapping and same-step output queue. Store the whole queue at update tail; run existing 141/144/507/356/22 input handlers and the common cache/renderer/observer tail next update. |
| Profile-manager out queue | Copy to `mGuiOutQueue` and immediate `RouteEventToFlow`. | Copy only. The same batch reaches the common input tail once. |
| Custom-renderer out queue | `BridgeFromViewToOutput` omits it; a later loop immediately sends cache/flow copies before `CustomRendererManager::Update` clears it. | Append it to module output in the original base order, then use the stored input tail once. |
| ViewIO output queue | Event 21 cache/flow direct handling; event 22 is converted immediately to 201 by a second PC loop. | Copy the complete queue to `mStoredGuiEvents`, clear after copy, and consume input once next update. Case 21 uses the common cache/manager/observer path; case 22 calls `FlaptSoundTriggerCallback` and emits 201. |
| Overlay director subset 184/186/188/189/190/279/322 | A separate late copy runs after the HUD analyzer; other immediate flow fanout occurs at drain. | No subset queue. The complete batch is input before inbound dispatch and shared by the analyzer and overlays director. |
| Channel 42 internal-state queue | `DrainFlowOutputQueue` unwraps into the flow observer queues after their current-frame update, effecting next-frame delivery. | Unchanged. ARTIST stores channel 42 on EventInterpreterModule's private `+0x15C0` queue, not the module output queue being restored here. |
| Resource ModelIO notifications | Separate PC `DispatchGuiResourceModule` and ModelOutput/ViewInput handoff; direct cache/renderer processing before queue clear. | Unchanged and explicitly outside this packet. The native ModelIO-to-stored bridge needs its own coordinated consumer migration before being combined. |

`DispatchInboundGuiEvents` calls the module-specific event handler first, then the ARTIST `LABEL_181` per-event cache tail, renderer-manager feed, and subscription-filtered observer fanout. The candidate restores those common tails for this input stream, with 14/16 left on the selected PC ModelIO notification path so the same completion is not passed to cache or the renderer manager twice.
