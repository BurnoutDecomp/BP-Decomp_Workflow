# Native SatNav event truncation

Recording: Source41 d85e2d5e2526. Dense crops 29/30 at 21.5625/21.6875 seconds show the map texture jump and then return; icon positions remain comparatively steady. The cause of that particular jump is not yet established.

ARTIST 82469680..D0 copies six doublewords (48 bytes) into a channel-41 wrapper and sends {size 48, type 212, offset 16}, total 64 bytes. ARTIST 82449940 case 212 copies 48 payload bytes. These are 32-bit console layout facts, not a native-size constant.

Source45 native SatNavComponent constructed {48,212,16} but the actual native payload is 64 bytes. State output queue stores its full 80-byte wrapper; EventInterpreterModule::ProcessOutEvents channel41 forwards header size 48 into the view queue; SatNavRenderer::RecvEvent assigns the full 64-byte object. Native MSVC x64 layout: map pointer +32; mask +40; route +48; rotate +56; trajectory +57. Thus route and flags are outside forwarded bytes.

Candidate B5 private commit 3f4f9c06e1a694d491effd1cbe28407ce9df1d4b uses the existing GuiEventWrapper<GuiEventRenderSatNav,41>, which records actual sizeof/offset. SatNavComponent.cpp, SatNavRenderer.cpp and CgsEventInterpreterModule.cpp compile under canonical MSVC flags and includes.

queue_test.cpp uses actual native VariableEventQueue for the outer and view queues, with the same wrapper-header forwarding as ProcessOutEvents and an actual adjacent event. Its old sender and zero-filled view tail produce corrupted route (next queue header), rotate=false, trajectory=false despite true producer flags. With tail filled 0x01 and producer flags false, old sender observes both flags true. Both fixed-wrapper cases forward 64 bytes and preserve every compared field, including pointers and flags. Build output: queue_test.exe (exit 0). This is a byte-level counterfactual, not a native game witness; the test reproduces the interpreter forwarding operations rather than calling its full ProcessOutEvents.

TEMP_OLD_EVENT_WITNESS.patch applies to e3d773c6; TEMP_EVENT_WITNESS.patch applies to 3f4f9c06. Both are diagnostic-only and must not be applied to shipping B5 source. Set BRN_SATNAV_EVENT_WITNESS to record up to 3000 sender and receiver tuples, with independent ordinal counters; pair by ordered payload identity rather than counters alone. Compare source and received flags and texture pointers along with position, orientation, speed and zoom. Run old and fixed builds against the same private save and input; capture dense map frames and correlate any flip with mismatched renderer flags. No launch without root coordination.

Diagnostic patches are TEMPORARY, NOT SHIPPING and are not part of the B5 source commit. Both variants passed git apply --check --ignore-space-change against their specified bases; the option accounts for Windows checkout line endings.

To reproduce the queue test, compile queue_test.cpp and GameShared/GameClasses/Development/CgsStrStream.cpp with tools/build/msvc_flags.txt and the repository-relative include directories in tools/build/msvc_includes.txt, then link both objects with /OPT:REF and run the resulting executable. compiler_and_test_receipt.txt records the current run; receipt.json identifies the tested source hashes.
