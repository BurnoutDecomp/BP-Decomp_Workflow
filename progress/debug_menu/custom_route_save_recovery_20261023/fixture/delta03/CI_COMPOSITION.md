This is the separate bounded CI composition for the delta03 diagnostic dependency change. Exact preimages come from parent 87c07f006e0667e96ead895791ac21237bc17cfb. The workflow file is retained byte-for-byte. Only ci/check-candidate-build.ps1 changes.

| Contract | Before | Delta03 |
| --- | --- | --- |
| Installed payload LF hash/size rows | 7 | 8 |
| Pinned b5 source/helper/fixture inputs | 20 | 24 |
| Compile rows required per variant | 6 | 8 |
| Mode checks | 71 / 13 / 1 / 1 | Unchanged |
| Mode failures | 0 / 6 / 1 / 1 | Unchanged |

The eight-payload table retains five exact rows, updates the binder and source-pins identities, and adds OnlineSaveRouteDiagnosticGlobals.cpp. The binder pins the actual formatter cpp/header, actual Log header and new provider, then appends the formatter/provider after the original six sources. The existing runner already compiles and records every composed source and therefore remains unchanged. INSTALL_BINDINGS.json supplies the full eight-payload installation map.

The controller changes only that literal pin table, its b5 source-pin count guard and three compile-count/loop/receipt fields. All other controller bytes recover exactly when those bounded changes are reversed. Workflow inputs, dispatch count, hosted Windows 2022/x64/Jobs4, all existing groups, cleanup/transcript checks, source/provenance handling, parent gitlink behavior, artifact upload and final shipping validation are unchanged. The original failure's catch-generated flags for other groups do not establish that those groups executed.

Root advanced the private parent to 95d85b7cf2848f92e3fab80689297487815181fd for separate retained evidence. Both CI preimages still match 87c; Root must assert equality before grafting. Actual delta03 b5/workflow commits and hosted rerun remain pending. No controller, runner, fixture, compiler, CI or game was executed to prepare this composition.
