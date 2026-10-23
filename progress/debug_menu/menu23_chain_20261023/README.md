# Menu-music event 23: producer and consumer representation repair

Status: source-only proposal frozen against B5 source commit 7e455d8854a32df1ca1934a54cc279c1e268a103. No production source, refs, index, build, compile, or runtime was changed or run.

The four existing menu-music producer posts already represent ARTIST's 20-byte {8,23,12}+8 record and channel 40. The generic producer header is left unchanged. The PC channel-40 drain unwraps that record and enqueues its 8-byte inner event-23 payload. The pinned sound consumer cast that short payload as the full record and read the hash and flags at +12/+16/+17.

The packet keeps the prior four producer changes and adds one matching change to SoundLogicModule::ProcessGuiEvents case 23. It reads hash/flags from the existing GetGuiPayload result for the unwrapped event-23 body. It preserves the separate channel-155 path: BrnGuiModule translates the full event-155 record to event id 23 without stripping its header, so the same case retains full-record reads only when the event-155 id and offset-12 header are present.

Owned source files are BrnCredits.cpp, BrnOfflineInstantResults.cpp, and BrnSoundLogicModule.cpp. The proposal changes four producer calls and one consumer case. It does not touch the generic OutputGuiEvent<T> template, BrnGuiModule channel drains/translators, event 508/509, or any other event consumer. ARTIST pins the producer wire and consumer field offsets; DecFIGS corroborates the declaration shape only.

preimage/ and postimage/ hold exact LF source images; patch.diff is generated from those images. bindings.json records base blob/hash identities and evidence hashes. evidence/current_source/menu23_receiver_representations.txt documents how the existing payload helper distinguishes the raw 8-byte channel-40 body from the full channel-155 compatibility event.

Counts are actual source sites: four repaired producer calls and one repaired consumer switch arm. They do not count registrations or xrefs to the shared publisher. Static source validation only; compilation and runtime audio checks remain with the integrating root.
