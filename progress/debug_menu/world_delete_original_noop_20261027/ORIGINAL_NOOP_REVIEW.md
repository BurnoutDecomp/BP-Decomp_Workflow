# World Delete original no-op

VERDICT: pass

Exact ID: `BrnWorld::WorldDebugComponent::OnActivate#0009`, caption `Delete`, group `Dumped file to hd`. This is a positive original callback no-op finding, not native control availability, a file-deletion implementation, a full World lifecycle pass, or an inference from missing consumers.

In the original OnActivate `0x827BF4A8`, raw instructions at `0x827BF620` and `0x827BF624` construct callback register r4 as `0x82850000 + signed(0xcb38) = 0x8284cb38`; r5 is the same component this pointer. The linked call at `0x827BF628` independently decodes to grouped RegisterFunction `0x8282F6D0`. That wrapper forwards the callback and user parameter to FunctionManager. Original raw captions at `0x8207B608` and `0x820CBF54` are exactly `Delete\0` and `Dumped file to hd\0`.

The actual target is the complete `4e800020` return instruction followed by zero padding. Its retained export matches the actual ARTIST export, SHA256 `f8e89aefa607244646c790a0d7a7fab7c8c3bc603bee5ea1601d783be2120129`; the four-byte original body SHA256 is `f332ea5b5437103cbb6f1508679da89eec9288ad775c96c439a17fccabe3de8e`. This is an actual pointer-to-complete-body proof, even though IDA gives that folded body a collision destructor name.

The exact source registration is `RegisterFunction(&WorldDebugComponent::ClearStoredFile, this, "Dumped file to hd", "Delete")`. Current ClearStoredFile has no executable statement and ignores its `void*` parameter. Its retained body hash is `2879a3b8e43ba4a4ae18a481d3c18ce6e3780a30c4f0039d67e0b88696966941`, joined to the exact pinned source. Current Function::DebugCallbackFunction is `void (*)(void*)`, and Function::Select invokes the nonnull stored function with its stored user parameter. These two actual current source files were read from pinned Git and retained in the review; no guessed pointer ABI is needed.

The source postimage changes Construct only, so this callback and registration remain unchanged. The no-op finding is independent of the still-unclosed native initial construction and World AI default. No actual registry write was made here; this is one source-proven original-no-op candidate for the parent to record within the normal provenance workflow.

No other selected callback inherits this finding. PrimeGunCallback's absent per-function export is positively filled by the actual 200-byte range `0x827B1CF8..0x827B1DC0`, SHA256 `c24317011da76da09ed256558355569675500c895141fa97b78f3b662fd45ea0`. It contains owner access, branches and stores, including a true primed flag; it is not an empty function. Its unresolved VMX/owner/effect chain remains unresolved. Other callbacks that set pending flags, queue requests or call providers are likewise not no-ops by absence.
