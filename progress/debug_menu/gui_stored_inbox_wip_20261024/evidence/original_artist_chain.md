# Original GUI queue and frame evidence

All listed ARTIST files are copied byte-for-byte in `artist/` and include the full exported pseudocode and assembly. Their SHA-256 values are in `source_hashes.tsv`.

## Persistent GUI member and ordering

`CgsGui::GuiModule::Update @ 0x828602C8` finishes by reading the output buffer's canonical event queue and appending it to `this + 0x1B41C`, decimal 111644 (`mStoredGuiEvents`). The assembly at `0x82860564..0x82860578` calls `OutputBuffer::GetOutEventQueue`, forms `this + 111644`, then calls `VariableEventQueue<18432,16>::Append<18432,16>`. This copies the entire output queue and leaves it available for the caller's same-step bridges.

`BrnGui::GuiModule::Update @ 0x82527A58` obtains the caller's GUI input queue before the per-event walk. Pseudocode lines 298-300 append the member queue at `this+111644` to that input, then clear the persistent source. The relevant assembly is:

```text
0x82527D58  addis r31,r26,2
0x82527D60  addi  r31,r31,-0x4BE4       ; this + 111644
0x82527D64  mr    r4,r31
0x82527D6C  bl    VariableEventQueue<32768,16>::Append<18432,16>
0x82527D70  mr    r3,r31
0x82527D74  bl    VariableEventQueue<18432,16>::Clear
```

The same function calls the base update at `0x8252A314`, then `HandleEventsPostBaseModuleUpdate` at `0x8252A330`. Its event walk includes the native handlers for 141 (emit keyboard response), 144 (RunFsm), 507 (UpdatePlayerName), 356 (autosave latch), and 22 (resolve movie from layer and emit sound output). The full event body and assembly are in `artist/0x82527A58.json`.

## Output channels and separate internal loopback

`CgsGui::EventInterpreterModule::ProcessOutEvents @ 0x8285E1D0` unwraps channel-40 records into the module output queue. The exact assembly used by the current drain is at `0x8285E568..0x8285E57C`: read payload offset/size/type from the wrapper, form the payload pointer, and call `VariableEventQueue<18432,16>::AddEvent`.

The same function handles channel 41 as a ViewIO record and channel 42 as an internal event posted to the interpreter member queue at `this+0x15C0`. `EventInterpreterModule::Update @ 0x8285F670` appends and clears that private queue at `0x8285F6A0..0x8285F6B0` before `ProcessInEvents`. The candidate leaves the current channel-42 route intact: it is a different owner and is not also copied through `mGuiOutQueue`.

## Frame-buffer lifetime

`LoadingScriptedState::Update @ 0x823F22D8` and `MainGameFlowStateInGame::Update @ 0x823F3048` are the two ARTIST frame-owner callers; the loading state is a directly readable buffer-lifetime example. It creates GUI input/output IO buffers on the update IO stacks, fills input via the game/controller bridges, calls the embedded GUI module's virtual Update slot at `0x823F2A00..0x823F2A0C` (vtable offset `0x60`), runs same-step bridges, and destroys the GUI output/input at `0x823F2C48` and `0x823F2C58`. `BrnGameModule::DoUpdate @ 0x823F0AF8` is called by loading and in-game owners. The full exports are included in `artist/`.

The exact PC frame owner is in `pc_base/BrnGameModule.cpp`: `CreateStaticIOBuffers` creates the substep GUI buffers; after filling/unlocking input, it passes the pointer to `GuiModule::Update`; after the GUI tick it copies `mGuiOutQueue` into the frame-owned output and runs game/director bridges; it clears the module queue after consumers and destroys the substep IO buffers. The new persistent queue copy therefore occurs before `mGuiOutQueue` retires, while `mStoredGuiEvents` survives buffer destruction.

## Declaration shape

DecFIGS `CgsGuiModule.h` declares `mStoredGuiEvents` at line 1144 as the base GUI member queue. Current PC `CgsGuiModule.h` exposes the protected `GuiNotificationQueue mStoredGuiEvents`. ARTIST pins its target offset and `18432` record capacity; the candidate uses the existing current-PC declaration rather than adding a second queue.
