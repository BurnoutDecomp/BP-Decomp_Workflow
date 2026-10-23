# Renderer Construct's original IO-mode seed

This one-path proposal restores `mbIsNewModule=true` at normal renderer Construct completion. It is the original IO-model classification store, not a prepared/allocator-ready flag. It adds no Prepare call, registration, allocation, source mount or native integration.

ARTIST8240BB9C loads r29=1. The full primary stream has no later redefinition ofr29 before8240BF90 stores it at this+4, after LoadingScreen Construct, calibration-handle initialization and MemoryUsage. DecFIGS/current Module declaration identify the inherited bool; original ModuleSingleBuffered::Construct clears it. Original base Prepare tests this bool to select the legacy DataStructure lifecycle. The proposal restores the actual owner/lifetime seed with typed member access.

The entire source702 CPP preimage is preserved after removing the added payload. All native immediate/dispatch/assert buffer preparation, capacities, allocator selection, sky-dome state, thread work, diagnostics and early returns remain unchanged. Failed native allocation returns do not acquire a new store. This packet does not claim full renderer Construct parity or permit its original Prepare to be activated over current live allocations.

Changing the real IO-mode field affects inherited module behavior when composed; it must be reviewed as that original semantic change, not treated as evidence that the renderer is ready. Current actual PC owners and GameData Construct-order evidence are recorded separately in CURRENT_PC_OWNERS_702.md. In particular, the old first-packet plan's native root-lane0/1 description is historical: current source702 writes lanes0/2 while retaining the GameDataRoot1 diagnostic name.

The existing CPP is already shipping-mounted. No compiler, tests, CI, game, input, Git state or physical source was touched. Root owns fresh review, composition, allocation reconciliation and activation.
