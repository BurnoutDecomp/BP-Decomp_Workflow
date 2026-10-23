# ProfileHost collision-world handshake dependency map

## Decision

This is a source dependency and call-order map against exact B5 commit 840d83b3c3390d1786ed571b3bf87e3947b89a9e, tree 61cc572fa627b0a79a0e39c5d8d638c7235e105d. No code delta is proposed. The selected PC ProfileManager bridge is live: it consumes the manager's pending transition and calls SetCollisionWorldValid so ProfileManager can continue. Removing it before the corresponding PreWorld/GameData response path is selected would leave the manager in INVALIDATING or VALIDATING. Activating that path requires caller/frame wiring that is expressly outside this increment.

## Ownership and distinct state machines

GuiModule owns ProfileHost by value at ARTIST module+0xA66D0. ProfileHost owns ProfileManager by value; its GetProfileManager() returns a reference to that member, whose ARTIST address is module+681696 (host+0x10). The selected code calls this same owner through mProfileHost.GetProfileManager(); it does not hold a separate manager copy or pointer.

The collision protocol has two separate states. GuiModule::meCollisionWorldStateValidationState is the 13-state controller at ARTIST GuiModule+130104. ProfileManager::meCollisionWorldState is its six-state save/load handshake at ProfileManager+267300 (the ARTIST GUI-module address in the validator is +948996). Do not conflate them.

ProfileManager's state values are VALID=0, INVALIDATE=1, INVALIDATING=2, INVALID=3, VALIDATE=4, VALIDATING=5. Bootup sets INVALIDATE and starts its task. PendingCollisionWorldInvalidate consumes 1->2; PendingCollisionWorldValidate consumes 4->5. SetCollisionWorldValid(false) accepts INVALIDATING, changes it to INVALID, then starts SaveLoadSystem::Bootup. SetCollisionWorldValid(true) accepts VALIDATING, changes it to VALID, then reports the profile task complete. These methods advance the profile manager; SetCollisionWorldValid itself does not perform the collision-pool swap.

## ARTIST call order and asynchronous completion

ARTIST 0x8251A3D0 GuiModule::PreWorldUpdate calls 0x82519578 UpdateCollisionWorldValidation while the GUI output buffer is write-locked, before UpdateCarPoolValidation, LoadProfileUpgradeData, and the base CgsGui::GuiModule::PreWorldUpdate. The native Xrefs show UpdateCollisionWorldValidation has this PreWorldUpdate as its caller; SetCollisionWorldValid at 0x82517F50 has UpdateCollisionWorldValidation as its only caller. The ARTIST GuiModule::Update at 0x82527A58 separately updates the embedded SaveLoadSystem. It does not call UpdateCollisionWorldValidation or SetCollisionWorldValid.

For ProfileManager requests, the validator's IDLE branch consumes PendingCollisionWorldInvalidate only in its boot-movie path, stages GameData request 67 with mCollisonPoolValidationReceiverQueue, and moves to INVALIDATING_FOR_SAVELOAD. It does not call SetCollisionWorldValid yet. It waits until that receiver queue contains event 67; only then it sets the GUI controller's world-invalid latch and calls SetCollisionWorldValid(false), which starts SaveLoadSystem::Bootup. After BootupResult marks the manager VALIDATE, the validator consumes PendingCollisionWorldValidate, stages request 68, and moves to VALIDATING_FOR_SAVELOAD. It waits for event 68 before clearing the GUI controller's latch, calling SetCollisionWorldValid(true), and returning its state machine to IDLE.

The 67/68 queue is an asynchronous GameData route, distinct from GUI event 493. PreWorld writes each typed SwapOut/SwapIn request into the GUI OutputBuffer resource-request queue. The native DoUpdate_GuiPreWorld wrapper appends that queue into GameDataInput. GameDataModule dispatches 67/68 to ProcessSwapOut/ProcessSwapIn, performs the collision bundle/pool operations through ResourceIO, then posts a response with the captured receiver queue and response id 67/68 after the resource completion path. The validator consumes those replies on a later PreWorldUpdate invocation. Separately, GUI event 493 values 0/1 and their 2/3 completion events are the movie/network invalidation path; that event path is not a substitute for the ProfileManager's 67/68 swap handshake.

## Selected PC path

In exact source 840d, GuiModule::Update calls ProfileManager::Update, then immediately consumes PendingCollisionWorldInvalidate and calls SetCollisionWorldValid(false), and immediately consumes PendingCollisionWorldValidate and calls SetCollisionWorldValid(true). Comments label the world pool free/restore as PC stand-ins because the world collision pool is absent from the selected PC boot path. This preserves ProfileManager boot-task progress while omitting the native collision-world wait.

The selected BrnGameModule frame path calls no-argument GuiModule::Update and then publishes mGuiOutQueue to its frame OutputBuffer. Loading-state PC call sites also use the selected GuiModule::Update overload and publish output afterward. The recovered DoUpdate_GuiPreWorld wrapper can call GuiModule::PreWorldUpdate and append its resource requests to GameDataInput, but exact PC source search finds only the wrapper declaration and definition; its source comment says it has no selected invocation. ARTIST shows the wrapper's native callers in BrnGameModule::DoUpdate and LoadingScriptedState::Update, so that original caller schedule cannot be assumed for the selected host path.

## Safe next prerequisites

1. Select a real PC frame owner/caller for DoUpdate_GuiPreWorld that supplies the proper IOBuffer stacks, GUI and model OutputBuffers, and GameDataInput, with the original pre-world ordering. This task does not choose or activate that policy.
2. Keep the GameData request queue path alive through GameDataModule::Update and the ResourceIO unload/invalidate/validate responses so event 67/68 reaches the exact mCollisonPoolValidationReceiverQueue supplied by the validator.
3. Keep the direct ProfileManager SetCollisionWorldValid bridge until the replacement path is selected and can advance the same manager state from actual 67/68 completion. Removing it now would stall profile boot/load. Calling PreWorld at the wrong point relative to ProfileManager::Update can let the selected direct branch consume a transition before the 67/68 request is issued, so the frame order must be selected before adding a caller.
4. Keep the separate GUI event493 request/output/completion route distinct and ensure its recovered handler is eventually connected before claiming the whole 13-state controller is active.

No source was changed or applied. The map does not claim runtime parity or justify removing the selected PC bridge. No build, test, fixture, CI, game/native run, IDA, index change, commit, or subagent was used.
