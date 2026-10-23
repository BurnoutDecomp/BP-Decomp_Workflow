# Event 356 CompletedGame channel-40 producer proposal

This source-only proposal restores the original event-356 wire record at both active `BrnGui::CompletedGame` publication sites in `BrnCompletedGame.cpp`. ARTIST `StateInterface::OutputGuiEvent<GuiAutosaveRequestEvent>` at `0x824937E0` copies the one-byte `GuiAutosaveRequestEvent`, writes header `(1, 356, 12)`, and calls `VariableEventQueue<65536,16>::AddEvent` with channel `40` and size `16`. The two callers at `0x824D2078` and `0x824D2978` set the payload byte to `1` before publication.

At base `b9c0e692bc9d8f232b9986923acf07aff26c0639`, the two source sites call the generic C++ template. That template direct-queues the type ID and `sizeof(T)`. The current PC flow-output drain has no raw-ID 356 arm; its channel-40 record path unwraps header/payload, sets the existing autosave latch for event 356, and then rekeys the record for the existing output route. The proposal therefore wraps the unchanged payload object in `GuiEventWrapper<...,40>` at exactly those two callers. It leaves the generic template and the existing GuiModule drain/latch untouched.

The patch owns exactly `src/GameSource/Gui/Flow/PostEvent/States/Offline/BrnCompletedGame.cpp`. It adds a wrapper alias and layout assertions for the one-byte payload, +12 payload offset, and 16-byte complete record, then replaces the two raw generic posts with channel-40 queue posts. This is a producer contract repair; it does not assert that a profile save completed in runtime.

## Evidence

- ARTIST publisher: `evidence/ARTIST/0x824937E0.json`, with the exact one-byte copy, header stores, channel 40 and size 16.
- ARTIST callers: `evidence/ARTIST/0x824D2078.json` and `0x824D2978.json`; their assembly sets byte 1 and invokes the publisher.
- DecFIGS corroboration: `evidence/DecFIGS/0x34D430.json` shows `GuiModule::AddGuiEvent<GuiAutosaveRequestEvent>` inserting a one-byte typed event. Its PS3 event key is not used to override ARTIST's X360 event ID 356.
- Exact-base C++ behavior and types: `evidence/current/`. The current shared GUI-module files are evidence only and are excluded from patch ownership.
- Exact preimage, postimage and unified patch are saved beside this README; `bindings.json` pins the base blob and file hashes.

## Counts and limits

Two actual producer sites are changed in one source file. This is not a debug registration count, a runtime pass, or a complete save lifecycle proof. No production source, Git ref/index, build, CI, game, or input state was changed or tested.
