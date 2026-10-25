VERDICT: fail

ONE combined source-and-mount review of exact source `3a0445b48c502f4f331a7d6ca36b076131a75ead`, tree `e32ccd2858ce9236f3dcb340bc7e397da07b403f`, workflow `da719ad47aace3274dfa8a84e6df2f1bffa9f05e`, against last source PASS `e5471505d1057c51e18feb45e962772f85390ddc`. Four confirmed fidelity defects remain in the newly exposed GameTalk transport. They fail this immutable source even though original outer startup is still unselected. No forthcoming correction was substituted into this review.

The author packets bind actual intermediate source 65952ee10a92e8f8a2b026efdc9397efed1da2b5 / workflow b95b757e5ee968c91718f687e77e3f4130d851c0, then the exact final pair above:

- dlc_prepare_e547_20261025 SEAL.json SHA256 `068e6a7a601397c85900da96d805cd3bcafac7517faf261120cdb0c848784d10`.
- link_provider_mounts_reviewable_6595_20261025 SEAL.json SHA256 `4270b063668641fdf855d3c8b872353fba577ebad0b3d9c6cbb85947bb95e5bf`.

All complete pre/post source files, actual Git parents/trees and workflow links, packet rows, named original primary/declaration copies, historical/effective provider snapshots and Root publication receipts agree. BYTE_BINDINGS.json contains twelve changed B5 paths and the one BAT path, 73 primary/declaration records and 48 initial provider records. Additional actual canonical provider/primary reads are separately hash-bound. This used actual original evidence and exact source objects, not a prior review statement as proof.

F1 [P1] - OnMessageReceived uses the wrong native message layout.

At CgsGameTalkProtocolX360.cpp:469-479, a local MessageLayout models an eight-byte header followed by the entry table and count, then reinterprets the genuine GameTalkMessage through it. Actual GameTalkMessage in SDKs/EA/GameTalk/GameTalk.h:172-176 begins with a pointer-sized mpVTable followed by s32 mbParsed, then its entry table/count. On the native target, the overlay reads the table over mbParsed and the count over the real table region. A real incoming PingRequest can therefore be skipped or dereferenced through invalid fields. This is a concrete declaration/body contradiction, independent of a runtime reproduction.

Named ARTIST 82838F50 confirms traversal of the genuine count, entry table, key and content, including its case-sensitive PingRequest comparison. Existing actual GetNumKeys/GetKey/GetContent accessors already use the canonical owner. Recover that typed traversal and preserve the original comparison/loop semantics; a second fixed-prefix message view cannot stand in for the real native class.

F2 [P2] - ping-response message allocation changes the original owner and failure ordering.

At CgsGameTalkProtocolX360.cpp:514-518, ordinary new GameTalkMessage allocates the outgoing object. The actual class/header/source provides no class operator new. ARTIST 828389B4-82838A5C explicitly checks the GameTalk linear allocator, calls the package allocator's Malloc, conditionally initializes the returned object and allocates its data buffer, then takes the original assertion continuation on allocation failure. Ordinary new changes both allocator ownership and failure behavior. Its native object size is not the defect.

The genuine existing EA::GameTalk::Alloc path already reaches the GameTalk package allocator. Preserve that owner, native sizeof and original allocation/construction/data-buffer/failure ordering. The source comment describing this ordinary new as the original inlined package allocation is not supported by the actual declaration.

F3 [P1] - transport and transitive SDK use the wrong application wire byte order.

At CgsGameTalkProtocolX360.cpp:399-402 and :431-434, the newly exposed framing code assembles big-endian length words. Actual ARTIST 828383B4 and 82838424 use lwbrx on the big-endian PPC target, which reads little-endian wire words. Original CreateBuffer 82837B50 likewise reverses a numeric big-endian local word and stores/copies the reversed bytes, producing little-endian wire data. These actual instructions arbitrate over the old source comments claiming big-endian framing.

The existing native SDK GameTalk.cpp readers/writers unconditionally byte-swap native little-endian words, yielding the opposite format. On exposure of this real transport, framing and the transitive serialized length/string/count/type words must preserve the original little-endian contract coherently. A valid original little-endian length can currently be interpreted as a huge incomplete message. Native socket-port htons is a separate, appropriate host API mapping; it does not establish the application's message encoding. No packet fixture or network execution was used to establish this finding.

F4 [P2] - protocol status/error text is sent to a private stand-in sink.

At CgsGameTalkProtocolX360.cpp:101-102, the protocol invents a private char[256] plus StrStream. Original normal status calls use stream 82F3300C. Original GameTalk::Construct owns LogWindow 82F32FD4; the stream is its +0x38 mLog subobject. The actual canonical LogWindow declaration has this public owned stream, whose sink forwards to the window's line ring. Current CgsGameTalk.cpp owns sLogWindow and prepares Core/GameTalk/Log, but protocol status is appended to the unrelated private buffer instead, disconnecting the original menu log consumer.

Original protocol error branches also format their error context in the actual assert message buffer. Current code sends the formatted values to the private stream and passes shortened literals to CGS_ASSERT. Restore the genuine owned status stream and original formatted assertion context. A private sink is not a recovered substitute for the original owner.

The remaining bounded review found no further actionable blocker:

- DLC Prepare uses the real ten-state 8266AF50 control flow. The full pseudocode and assembly were checked for unused allocator-list argument, monitor status/flag handling, monitor-derived HDD packages, four ordered physical disc checks, actual raw p_hdd:/d/ prefix and package stores. Empty discovery sets DONE but returns false once. Open, exact sixteen-byte clear/read, Close, nonconsuming poll followed by Wait, result failures and shift-removal preserve the original continuation. Parsing does not invent a terminator or success guard; enabled/mask assertions, availability stores, priority wrap and untouched version word follow the original. The PS3 two-stage body was used only for its attested declaration shape.
- New IsDone uses the original operating assertion and actual semaphore count >0, without consuming it. The nonconst compound Handle getter preserves its wait assertion and real member copy. Original raw provider bytes, hidden result/this handling and by-value handle calls were read. The actual EAThread declarations/implementation and gitlink were bound; other preexisting AsyncOp and DLC bodies remain intact.
- Newly mounted one-shot AsyncOp issue/wait/callback methods share the same canonical class with the already mounted constructor/result/provider TU. They preserve actual callback/context, result/handle/size stores, semaphore post and wait consumption. No second operation owner or synthetic completion was added.
- The real monitor and StartDLCMonitor preserve their actual lock/count/thread and XContent call flow. A bounded original raw worker read covers 82665A58-82665DC4; bytes after that boundary in the saved window are not claimed as part of the worker. No package cap, fake successful-empty enumeration or new backend was added. XContent records retain their real no-pointer field shapes; no host backend is certified.
- PatchManager preserves its two real allocator-owned arrays, unsigned-key initializer, worker scratch/free domain, thread context/name/priority, recursive traversal, priority clash/remapping and physical path handling. The corrected 0x80 mask matches actual 828F0B30. Existing native FindClose mapping is retained. Its only original caller ignores the legacy bool return; this review does not invent a recovered return-type claim from a trailing callee result.
- PhysicalX360 owns the actual sixteen-record typed pool. Its open access/dispositions, read/cursor/seek and directory count/handle/pool-return paths were compared with primary bodies/assembly. FindFirstFileA is paired with native FindClose, retaining the original invalid sentinel, error callback and pool-return flow. This is an explicit platform mapping, not an assertion of complete host filesystem parity.
- LiveUpdate lifecycle, singleton, resumable preparation, actual request/response queue and status accessors preserve the original locks/stages/request fields and actual completion interpretation. The newly mounted output-buffer provider supplies the real transitive Get/SetStatus operations. Entry formatting uses the real resource owner; canonical GetResource is an actual main-memory pointer copy, with the native pointer formatter retaining stream mode. The GameTalk front door, base destructor and DebugSystem callback use actual classes/registration/manager acquisition; their transport exception is F1-F4.
- Native Winsock declarations now supply real SOCKET, WSADATA, fd_set and sockaddr_in storage. The actual SDK headers/excerpts and original request arguments were inspected. The thirteen-byte XNet request is genuinely zeroed with the original size/flag bytes. The same true reuse option, host port byte order and exact existing XMemCpy return/count shape are accounted for. These intentionally change host storage/API representation; unchanged native ABI or complete XNet behavior is not claimed.

MOUNT_DATA_BINDINGS.json closes the exact fourteen new shipping paths and their scoped CMake entries. All fourteen were absent from the prior canonical BAT list and have one new literal entry. The five CMake aggregates expose the named providers; CMake remains a partial historical aggregate rather than a certified alternate shipping build. Candidate duplicate definitions were inspected: same-basename IO buffers and AsyncOps belong to distinct namespaces or comments, and the split filesystem AsyncOp files home different methods. This is source accounting, not a successful link proof.

Both complete schema initializers were parsed strictly as literal octets and compared with the actual original XEX ranges: BIN 20,352 bytes, SHA256 `d55b848e894b2ce099b6d9401150c2ef16bf810352389615a76c3a5c91a9cbdd`; VLT 5,664 bytes, SHA256 `93190b2d679a18c0974dc6d720162a8ddb8930e982cbfa827e969b5608a7559f`. Their existing char declarations and original big-endian data remain intact. The selected native LE loader, native two-argument GameData Prepare, GameModule/main and original four-argument startup selection are unchanged by the complete exact source delta. Mounting definitions does not by itself start the DLC worker, network transport or original outer preparation.

The exact changed-source scope relative to b5-decomp is:

- src/CMakeLists.txt
- src/GameShared/GameClasses/Containers/CMakeLists.txt
- src/GameShared/GameClasses/Development/CMakeLists.txt
- src/GameShared/GameClasses/System/CMakeLists.txt
- src/GameShared/GameClasses/System/FileSystem/CgsDeviceAsyncOp.h
- src/GameShared/GameClasses/System/FileSystem/CgsPatchManager.cpp
- src/GameShared/GameClasses/System/FileSystem/Devices/CgsDeviceAsyncOp.cpp
- src/GameShared/GameClasses/System/FileSystem/Devices/CgsDevicePhysicalX360.cpp
- src/GameShared/GameClasses/System/GameTalk/X360/CgsGameTalkProtocolX360.cpp
- src/GameShared/GameClasses/System/GameTalk/X360/CgsGameTalkProtocolX360.h
- src/GameSource/AttribSys/CMakeLists.txt
- src/GameSource/Resource/BrnDLCManager.cpp

The workflow code scope is tools/build/build_game_exe.bat. Exact newly exposed whole-TU bodies/data, including their hashes, primary addresses and per-provider disposition, are in MOUNT_DATA_BINDINGS.json and MANUAL_REVIEW_MATRIX.json:

- SDKs/Packages/GameTalk/1.8.0/source/IGameTalkProtocol.cpp
- GameShared/GameClasses/System/FileSystem/CgsPatchManager.cpp
- GameShared/GameClasses/System/FileSystem/Devices/CgsDevicePhysicalX360.cpp
- GameShared/GameClasses/System/FileSystem/CgsDeviceAsyncOp.cpp
- GameShared/GameClasses/Containers/CgsLinearSOAHashTable.cpp
- GameShared/GameClasses/System/Resource/CgsLiveUpdateModule.cpp
- GameShared/GameClasses/System/Resource/CgsLiveUpdateModuleIO_OutputBuffer.cpp
- GameShared/GameClasses/System/Resource/CgsResourceBasePool.cpp
- GameShared/GameClasses/System/GameTalk/CgsGameTalk.cpp
- GameShared/GameClasses/System/GameTalk/X360/CgsGameTalkProtocolX360.cpp
- GameShared/GameClasses/Development/DebugSystem/GameTalk/CgsDebugGameTalkInterface.cpp
- GameSource/AttribSys/Schema/X360/BrnAttribSchemaBinX360.cpp
- GameSource/AttribSys/Schema/X360/BrnAttribSchemaVltX360.cpp
- GameSource/Resource/BrnDLCManagerMonitor.cpp

406 byte-binding and 49 static mount/data checks passed. Manual semantic inspection yielded the four explicit failures above. No compiler, fixture/test or native case was evaluated. The genuine XLaunchNewImage, sub_82C208F0, XNetStartup and three XContent platform providers remain absent; the packet itself does not claim an exhaustive transitive link closure. Existing XEnumerate absent-enumerator policy does not supply a complete XContent backend. Further engine polling/helper provider recovery and all forthcoming GameTalk fixes require their own exact publication/review.

This FAIL closes the named immutable 3a scope. Excluded: c005 and every later/unpublished correction, the gametalk_review7 correction packet, all native/visual protocol outcomes, full platform/backend lifetime parity, actual link closure, original outer/main/five-stack activation and native/site credits. Root's hosted work is separate evidence; no new compile/link result is asserted here. Prior e547 PASS and old 21aced FAIL seals remain unchanged. No local C++ build, implementation/fixture/test import or evaluation, CI dispatch, native/game/IDB launch, Git/source/ledger mutation, work claim or normal asset/profile operation was performed. Only this reviewer scratch directory was written. Root owns fixes, publication and execution.
