# Source postmortem

1. ARTIST lifetime: `DoUpdate` creates a new GameState `OutputBuffer` each simulation step (`0x823F0BE4`) and destroys it after the cascade (`0x823F2244`). `OutputBuffer::Construct` calls the typed takedown-queue constructor (`0x823829A4`), whose construction resets its length. The active `PreWorldUpdate` queue append and event processing therefore operate on a one-step source queue on X360.
2. PC lifetime: current host code allocates `mpOutputBuffer` once during `GameStateModule::Construct`. Full `DoUpdate_GameStatePreWorld` passes this persistent buffer to the selected `PreWorldUpdate`. The existing late retirement has a write lock and runs after the queue's same-step readers.
3. Proposed semantics: one existing `Clear()` call at the last safe retirement point gives the persistent queue the next-step empty state of the original newly constructed queue, without hiding the current step's events from consumers.
4. Declaration shape: `OutputBuffer` already declares a non-const write-side takedown queue accessor returning `TakedownEventOutputQueueType*`; DecFIGS identifies the typed member as `PreWorldInputBuffer::TakedownEventQueue`. No new API or structure is proposed.
5. Verification limit: no C++ compile, hosted fixture, game, or runtime validation was run. Root must establish those separately before publication or behavior credit.
