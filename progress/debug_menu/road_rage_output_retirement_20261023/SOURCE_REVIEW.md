# Independent review: Road Rage takedown output retirement

VERDICT: pass

Scope: the one-call persistent-output repair in `roadrage_takedown_output_retire_proposal_20261023/REVIEW_REQUEST.md` and that packet's explicit dependencies. No material finding remains for this delta. This pass is source-only; hosted compilation, fixture and native behavior results are not granted by it.

## Exact input and postimage

- Proposal base: `3966e936bbc7a4c16afe7ec48527ccf7dab90758`.
- Whole preimage:364447 bytes,5976 lines; SHA-256 `cdde690ad876bab5cb5f6231be631869d685166aedb876cbdca7b996a17c1d62`.
- Computed git blob from those bytes: `ec2a7640ab3102a5f582841148cc7f3f29215c83`, matching the packet binding.
- Whole postimage:364742 bytes,5979 lines; SHA-256 `b1892a1ba9a84909e5515ea2b9ea340d6acffd2ae8788df06da0a9f0b36a1ec7`.
- Exact proposed diff SHA-256: `f53400a4eae401b4bed042c9eee2a5672ecbcbadb2bb9700b10417887fedcae7`.
- Input manifest SHA-256: `32586e9396514682d1df9072fd1ea13814476a1f3458b84dac5f134b2b666c24`; all8 listed payloads rehashed successfully. All32 referenced lifetime payloads, its manifest/report hashes, the three referenced ARTIST exports, and DecFIGS shape file also match.

Byte-for-byte subtraction of the single295-byte insertion reproduces the entire preimage. Independently regenerated unified diff equals proposed.diff exactly. Thus all other3966 code, including the pre-existing private replay/GUI bodies, is retained unchanged by this proposal. The review makes no separate claim about external checkout cleanliness.

## Lifetime and consumer order

The complete postimage and its active GameMain substep body were inspected. The inserted call is postimage line5103. The same persistent output is passed to full GameState PreWorld at4596..4599; that method copies output takedown records into its own cache. The output lifetime is otherwise unchanged.

| Same-step use | Postimage evidence | Position relative to clear |
|---|---|---|
| World | selected flow update4605; DoUpdate_World1789/BridgeGameStateToWorld1843; source queue copied at2497..2499 | Before |
| Director | pre-GUI call4640; source read-lock3074..3087; BridgeGameStateToDirector reads source records2329..2346 | Before |
| GUI | source read-lock4710, BridgeGameStateToGui4711, unlock4712 | Before |
| Effects, Sound, GameState PostWorld |4932,4947,4996 | Before |
| NetworkPostSim |5018..5022; referenced network bridge copies the const source takedown queue | Before |
| Timer request drain |5045 | Before |
| Queue retirement |write lock5059, Clear5103, unlock5104 | Final persistent-output bracket |

The remaining substep tail consumes input binding replies, clears GUI output, latches the camera, and tears down frame-owned buffers; it has no later takedown source reader. The next iteration starts after the clear. The clear is outside the GUI frame-step guard and runs for each actual simulation substep with a non-null output, including paused/skipped-GUI steps. Zero-substep frames produce no new takedown events.

Clearing this output queue does not clear the distinct module-cache copy already used by ProcessTakedownEvents and retained for its own lifecycle. It preserves every same-step source-queue consumer and prevents the next PreWorld pass from re-importing a retained producer record.

## Existing API, lock and original semantics

The postimage includes the complete `BrnGameStateModuleIO.h` at line51. The referenced sealed declaration provides a non-const `TakedownEventOutputQueueType* GetTakedownEventOutputQueue()`; its definition at BrnGameStateModuleIO.cpp679 asserts IsBufferLockedForWriting and returns the owned queue. The local pointer at5055 is non-const, so the added expression selects that existing write-side overload inside its already-held write lock. No declaration or ABI change is introduced.

The existing type is `CgsModule::EventQueue<BrnGameState::TakedownEvent,8>`, inheriting BaseEventQueue::Clear. Clear writes only `miLength=0`; storage and capacity remain constructed. EventQueue::Construct binds its owned inline storage and also seeds length0. Reusing that already-constructed storage with empty length therefore matches the next-step empty state the original fresh output provides. It introduces no event copy, new lifetime, or aliasing conversion.

ARTIST DoUpdate creates a fresh GameState output at0x823F0BE4 and destroys it at0x823F2244. OutputBuffer::Construct initializes the typed takedown queue at0x823829A4. The original full PreWorld copies and processes the queue at0x823A59F4..0x823A5A6C. The proposed late reset supplies the missing fresh-per-step state for the host's persistent adaptation while retaining the current step's records through their final readers. DecFIGS also attests the typed member and const/non-const accessor pair.

The4bbefd transition evidence remains intact. The delta repairs the selected3966 GameMain boundary; it does not rely on changing the dormant TakedownPreWorldLeg helper, suppressing scorer callbacks, or changing the original extension rules.

## Validation boundary

Only static text/byte inspection, hashing and creation of this new sibling report were performed. The input proposal and referenced sealed packets were not edited. No production source, Git/index/refs, controller/runner, compiler/C++ fixture/test, game, CI, or IDA worker execution or mutation occurred. No new renderer or broader mode work was added. Root owns composition with its separately reviewed inputs, publication, hosted checks and the authorized native witness.
