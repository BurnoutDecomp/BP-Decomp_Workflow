# Audio output shipping-owner correction

**Status:** sealed exact-source correction proposal, ready for bounded review. It is not applied to the shipping tree and has not been built. Base is the committed source checkpoint `a761bf9fc3b1bc960bc77d3f0f36c0a0c34e5f7c`. The original 35-path audio-family packet remains immutable.

The family packet placed the audio-specific `StateInterface::OutputGuiEvent<GuiAudioTriggerEvent>` definition in `CgsGuiStateInterface_OutputGuiEvent_Inst.cpp`. The build-source list does not mount that file and no mounted source includes it, so the declaration in `CgsGuiStateInterface.h` would be unresolved in the shipping executable.

This correction moves that one specialization definition to `BrnGuiEventTypeDefs.cpp`, beside the canonical payload and its `Construct` implementation, and removes its duplicate from the generic-instantiation TU. The exact source list at workflow commit `2bd1b23bc6e97eb528c166f6f06d40513d4625ce` includes `BrnGuiEventTypeDefs.cpp` (line 4145) and `CgsGuiStateInterface.cpp` (line 4902); it has no `CgsGuiStateInterface_OutputGuiEvent_Inst.cpp` entry. The evidence excerpt is in `evidence/build_source_mounts.txt` and its source binding is in `bindings.json`.

The explicit specialization declaration remains in the shared `CgsGuiStateInterface.h`, so every caller resolves the type-specific method. `BrnGuiEventTypeDefs.cpp` includes that declaration, then defines the same wrapper body that emits `{100,457,12}+payload` on channel40. The generic template remains unchanged. This source move is expected to make the symbol available to the mounted build, but only Root's full shipping build can establish that it links.

## Package contents

- `pre/` and `post/` are exact `a761` before/after source snapshots for the two affected files.
- `bindings.json` maps each image to its source path, `a761` blob, and SHA-256.
- `patch/source.patch` contains the proposed move only.
- `evidence/build_source_mounts.txt` records the two mounted-source lines from the workflow's exact build-source list; the binding includes the build file hash.

No production files, Git refs/index, build, CI, game launch, or native runtime were changed or run by this proposal.
