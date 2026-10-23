# Initialization boundaries before activation

These are source findings, not runtime observations or source changes to the active host.

ARTIST ModuleSingleBuffered::Construct at8286E768 clears the new-module byte at+4. Its Prepare at8286E7A0 checks that byte before entering the legacy input/output DataStructure factory path. The current base reproduces that decision; its default CreateInput/OutputDataStructure bodies return null after their new-module assertion.

ARTIST renderer Construct ends with `stb r29,4(r31)` at8240BF90; its pseudocode also identifies the value as1. The current private renderer Construct has no matching `mbIsNewModule` assignment and declares no legacy factory overrides. Consequently simply reaching its original Prepare is not sufficient: its current base Prepare can stop in the legacy factory path before any renderer allocation/registration. Recover the original seed at its actual Construct lifetime; do not invent a flag merely to skip a failing gate.

The original game module remains an old-module case in the inspected Construct. Current BrnGameModule derives directly from ModuleSingleBuffered, has no legacy input/output factory overrides, and its current BrnGameModuleIO header models InputBuffer as IOBuffer. DecFIGS names the game IO buffers as DataStructure derivatives and describes their lifecycle. ARTIST's truncated helper827E3100 takes a second pointer, invokes an empty destruction and returns true. That helper is consistent with template destruction but does not by itself identify the complete primary vtable/factory binding. Recover that binding and the actual DataStructure declarations before replacing the direct base or claiming the game owner's manager stage is runnable. A guessed template instantiation is not supplied here.

The newly embedded LiveUpdateModule likewise uses its current direct ModuleSingleBuffered base and has no own Prepare/factory declarations. ARTIST identifies it at GameData+361728 through its ctor/Construct and the original stage8 call, but its exact legacy factory readiness still needs confirmation. No `mbIsNewModule=true` accommodation is added to it.

Current GameData Construct already raises its own `mbIsNewModule` after the base; that particular seed is not missing. The new GameTalk, LiveUpdate and DebugGameTalkInterface member construction calls are missing from the current GameData Construct. Their correct order and initialized inputs must be recovered from82671B90 before activating the original four-argument Prepare.

These dependencies supplement the earlier native allocation hazards: the seven immediate buffers already have owners/capacities, sky-dome geometry has ready/tried state, the current shared GameData output publishes its list later in GamePrepare, LoadingScriptedState stage8 repeats shortened GameData Prepare, and BeginFramesPC already starts ThreadLayout. No original Prepare loop should be introduced into driving to work around those ownership gaps.
