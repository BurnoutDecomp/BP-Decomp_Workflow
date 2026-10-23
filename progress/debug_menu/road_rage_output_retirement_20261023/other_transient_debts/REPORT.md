# GameState OutputBuffer transient retirement: bounded audit

AUDIT RESULT: two concrete persistent-queue omissions remain at9af6. Controller bind/unbind request replay was activated by the recovery campaign; the dirty-trick queue omission predates4bbefd. Neither finding changes the accepted takedown retirement review or proves the current offline Road Rage repair unsuccessful. No new fix is proposed here.

Candidate: `9af6a868959578f4eafa9af0d69ccd27081667a0` (3966 plus the accepted one-call TD clear). Exact GameModule SHA-256 is `b1892a1ba9a84909e5515ea2b9ea340d6acffd2ae8788df06da0a9f0b36a1ec7`. Scope is the persistent GameState OutputBuffer's constructed transient members, selected GameMain readers, and reset ownership. This is not a general recovery audit, whole-game pass, or runtime finding.

## Remaining omission1: controller bind/unbind output requests

`OutputBuffer::Construct` builds its GameStateToControllerInterface once on the host (`BrnGameStateModuleIO.cpp:527`). The interface's Construct/Clear initializes and empties both eight-entry request queues. ARTIST OutputBuffer::Construct creates the corresponding two queues at0x823829C4/CC and explicitly zeros their lengths at0x823829D4/D8; fresh native per-step output therefore starts with no controller request.

The selected full PreWorld calls `GameStateInviteManager::Update` (`BrnGameStateModule.cpp:579`). Invite preparation can enqueue an unbind at `BrnGameStateInviteManager.cpp:269` and a bind at285. Update appends its owned queues into the persistent output at399/400, then clears **the manager's own queues** at401/402. It does not clear the output queues.

`DoUpdate_InputPostWorld` later calls BridgeGameStateToController under the normal output read lock. That bridge (`GameBridgeGameStateToX_Controller.cpp:33..61`) loops every output bind/unbind entry, copies each into the frame-owned input buffer, and stamps miInputModuleState3/6 whenever the corresponding source length is positive. The input buffer's teardown does not empty the persistent source. No per-substep Clear of GameStateToControllerInterface or its two output request queues exists in the selected GameMain retirement or examined source access paths.

Therefore, once invite preparation emits one such request, it can be copied and acted on again on later simulation substeps; when both source queues remain nonempty, the bridge's final unbind arm also keeps winning its3/6 state stamp. Repeated requests and retained queue capacity are concrete source risks. A resulting user-visible invite/controller failure has not been runtime demonstrated here. Ordinary offline Road Rage without invite-generated requests does not activate this scenario.

Provenance is split precisely: the output append provider landed in `1cbc56401d57b4b56991d6d6f522eecc6edd02f3` (Oct10), the full PreWorld body/call to InviteManager.Update in `bbac56ac60581ad01d12c89b492f6dc4a336a11f` (Oct12), the full PreWorld selection in `4bbefd59b53dc8dc3b86cb46a6e97801d311ece9` (Oct19), and the actual InputPostWorld/BridgeGameStateToController consumer in `63cf4d3a8323cc28b97f4ca83e2635f552674839` (Oct19). The old selected adapter explicitly did not stage InviteManager.Update. This is a campaign-activated lifetime omission, not a claim that4bbefd alone authored every link.

## Remaining omission2: outbound dirty-trick queue, pre-existing

`OutputBuffer::Construct` constructs GameStateToNetworkInterface at `BrnGameStateModuleIO.cpp:521`. The interface's Construct/Clear empties its DirtyTrickQueue along with scalar/mapping defaults. ARTIST OutputBuffer::Construct has the dirty-trick construction/Clear at0x823829B0/B8; the typed Clear at0x82362528 resets its length.

PaybackManager.Update appends mDirtyTrickOutputQueue into `lpOutput->GetGameStateToNetworkInterface()->GetDirtyTrickQueue()`, then clears only its own manager queue. BridgeGameStateToNetwork copies the persistent interface into the fresh PostSimulation input through AppendGameStateToNetworkInterface. The typed Append is non-consuming. NetworkModule then assigns a copy into its own interface; that assignment clears the **destination**, not the persistent source. NetworkDirtyTrickManager::ProcessDirtyTrickEvents walks the copied events and sends status-bearing ones to finalized peers. There is no selected per-substep source DirtyTrickQueue clear.

Thus a nonempty outbound source can be resent on following network passes, and additional records can accumulate toward the28-entry capacity. This is a concrete source lifetime debt, but it was already present before4bbefd: the Oct9 adapter calls TakedownPreWorldLeg, which calls PaybackManager.Update, and the pre-Oct10 network bridge already appends this interface. The producer/consumer history and baseline whole files are retained. It must not be presented as a new Road Rage regression or silently added to the accepted TD repair.

## Inventory of the remaining OutputBuffer members

The declared storage and Construct list were reconciled as follows. Snapshot rows were examined for this FIFO/event-replay question only; their inclusion does not certify every skipped-update or mode-transition value.

| Member/group | Retirement or producer/consumer disposition | Bounded result |
|---|---|---|
| IOBuffer base/padding | Lock/construction metadata, no event payload | No replay claim |
| GameActionQueue | Existing final GameMain Clear after all readers | Covered |
| ResourceRequestInterface.mRequestQueue | GamePrepare's GameData append is followed by a write-locked source Clear; selected main-loop readers do not newly replay this queue | Prepare boundary covered; no new4bb replay demonstrated |
| TimerRequestInterface | UpdateTimers consumes flags/scale once late; existing final Clear | Covered |
| FrameRateTypeRequestInterface | Mode/event code writes request/value; no active GameModule read consumer was found in the examined selected path | No replay proven; no delivery/implementation credit granted |
| TakedownEventOutputQueue | Accepted final write-locked Clear at GameModule5103 | Covered by9af6 |
| GameStateToNetworkInterface.DirtyTrickQueue | Appended producer, copied non-consuming consumer, no final clear | Omission2; pre-existing |
| Network mapping/online/mode/challenge flags | Published snapshot state, copied into Network; not an event queue | Not a FIFO replay finding; full stale-state parity not certified |
| GameStateToControllerInterface bind/unbind queues | Appended one-shot producer, non-consuming input bridge, no final clear | Omission1; campaign-activated |
| GameStateToGuiInterface | Existing final Construct empties all nine contained event queues and resets player index | Covered |
| Raw GUI event queue | Existing final Clear | Covered |
| Trigger management add/remove queues | Existing final Clears after World consumption | Covered |
| Trigger query queue | Existing final Clear after World consumption | Covered |
| ActivePaybackType/Aggressor, elapsed mode time | Scalar/Time snapshot setters; World copies snapshot | Not FIFO queues; no additional concrete replay shown |
| RaceCarRaceDistanceInterface | ModeManager fills the per-car race-distance snapshot; World copies | Snapshot, not queued events |
| ScoringOutputInterface, including stunt-to-display slot | WriteDataToOutput refreshes per-car/scoring scalars; OutputStuntsToDisplay first invalidates each output slot before selecting a current stunt | No FIFO accumulation in the inspected publication |
| OnlineScoringOutputInterface | Online scorer snapshot, not a transient event queue | No FIFO replay finding; full cross-mode stale-value parity outside this audit |
| GameModeOutputInterface | ModeManager publishes previous/current mode/state snapshot | No queued replay finding |
| SetUpAllEventStartsInterface + valid flag | Final clear of valid flag masks the retained payload until a new publish | Covered for replay |
| SpecificGameModeEventInterface + valid flag | Final clear of valid flag masks retained payload | Covered for replay |
| ControllerActive | Full PreWorld overwrites the scalar; World copies it | No queued replay finding |

## Schedule and evidence limits

The two unretired output queues are distinct objects from the manager-owned producer queues and from their frame-owned downstream copies. Clearing a producer-local queue or a destination input queue therefore does not consume their persistent source. Generic BaseEventQueue::Append/GetEvent preserve source length. Original DoUpdate allocates a fresh GameState OutputBuffer each step and destroys it after the cascade, so both output queues are originally one-step records.

This packet contains26 exact9af6 whole source postimages, three ARTIST exports, the relevant recovery diffs/logs, and three pre-Oct10 baseline whole files, with byte counts/blob/SHA-256 pins. The existing retirement still holds its write lock after the current substep readers and before the next iteration. No new patch, build, test, game, CI, ref/index mutation, or IDA worker operation was performed. Previous packets remain untouched.

Controller and dirty-trick findings remain explicit pending debts. The native count/timer witness and delivery review can proceed on the separately accepted TD delta without treating this bounded inventory as proof that the whole game is healthy.
