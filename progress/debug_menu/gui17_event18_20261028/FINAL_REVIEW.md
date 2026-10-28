VERDICT: pass

SOURCE approval for the eight-path event18 ABI correction, with the exact GUI-controls header composition below. No unresolved source finding.

All 314 author manifest members, seal and eight raw Git 7fd preimages authenticate. SOURCE_DELTA.patch applies to all eight exact postimages with automatic EOL conversion disabled. Its SHA-256 is `9cfb3be5dfc6f626b30c9c1c88a36fc49afff667ed459a256dfea484e0a87ae2`. Author seal SHA-256 is `3e4bc5857047196aba3889e90151cd7920f3c1581e5bffac6da4ed9ec1ff540a`.

Original ARTIST StateInterface::PlayAptMovie 82436F10 builds the flat pointer/level payload and wrapper {8,18,12}, total20. Independent raw excerpts show BootLegal 82477EAC..EE8, BootProfile 82478538..578 and ScreenLoading 824D0D30..DA4 post the same data and original levels1,3,(3 then1). Their replacements call the original central helper at the same point and preserve order. The canonical payload is now flat native16; the genuine wrapper records size16/offset16/total32. SetRawEvent copies the actual typed payload and derives its member offset; the existing copy-constructor path is unchanged.

ARTIST ProcessOutEvents 8285E648..660 reads wrapper offset+8, size+0 and type+4, then adds the raw body to the real view queue. Large VariableEventQueue AddEvent 8243522C and 824353D0..424 retains its own16-byte header, exact memcpy size and rounded record stride; GetNextEvent walks that size plus original padding. No queue/capacity/alignment workaround is introduced.

The original consumer 8285EAE8 dispatches on r6; caller8285FE70..80 explicitly passes payload r4,size r5,id r6. DecFIGS CgsGuiViewModule.h:291 agrees with the restored three explicit parameters. The size remains unused, matching assembly. Case18 retains its original pointer, level and strlen assertions and subsequent movie-name/load behavior; no guard, rotation, null stub, or substitute data is shipped.

Exact exe8aacdc9873d8f7f59cbbde5258e6124a9812fba5c9dc18b4e3b2a8e1ec7428e8 independently confirms producer RVA68CA10 stores pointer at16,level24,total32 while advertising8/12. Consumer RVA5941F6 reads pointer0 and level8. The observed malformed pointer946589E800007FF6 rotates32 to00007FF6946589E8, the real PE main string atRVA8589E8. No event payload memory/minidump was captured; the stale-padding fixture is an explicit input projection, not claimed live payload capture.

Fresh reviewer execution: eight actual production TUs compile with canonical workflow flags, final raw CRLF StateInterface files and composed header; zero diagnostics, zero physical-source fallbacks,293 source/header pins. The author receipts used LF equivalents for the two StateInterface files; their only difference from final raw files is EOL, and this fresh compile closes the exact-file gap. Fresh source-chain fixture passes46/46; genuine old production bodies compile and fail16/32, reproducing ptr946589E800007FF6/body8. Exact source/extracted-method bindings were reverified. Both fixture build logs are clean. Fixture boundaries are orchestration field shells, Apt load and renderer-manager observations, and fixture-only old-pointer inspection before strlen. No gameplay, timeline, rendering, whole-link or normal-boot credit.

All actual canonical event18 field users and local bypass producers were searched in exact7fd; ScreenLoading and both local boot wrappers are covered, the DriverDetails alias is unused, and remaining active callers use the central helper. Immediate event19/20 tags and25 scalar body retain their valid layouts. Event21 sender uses existing native GuiEventAptTriggerPayload and typed consumers; event22 explicitly sends its bare100-byte string fields; resource39 already carries a native flat filename pointer. No change to those formats is warranted by this defect.

Composition is independently byte-exact: apply only the wrapper addition to approved delta01 CgsGuiEvent.h pre951290946fbb8647a810b35e668b6f88f876f570261a62c35381e700ef2d61ac, producing6d48b325214f7ebf3824c1f8b61b3899a7d327d70546050c7ce0e6ea885e0047. Every other approved eventbase/tag byte survives. Delta02 has no intersecting source path. Use this composed header in the current private batch; the standalone7fd header postcb6f24c0... is approved only on its own7fd base.

Approved current-private-batch raw postimages (full paths and alternate standalone hashes in VERDICT.json):

| Path | SHA-256 |
|---|---|
| b5-decomp/src/GameShared/GameClasses/Gui/CgsGuiEvent.h | `6d48b325214f7ebf3824c1f8b61b3899a7d327d70546050c7ce0e6ea885e0047` |
| b5-decomp/src/GameShared/GameClasses/Gui/Model/State/CgsGuiStateInterface.cpp | `e9e50cdb2e765918c82fdd35e6b9ebfa3912216fd7a3f6d72001ae84d91b4e24` |
| b5-decomp/src/GameShared/GameClasses/Gui/Model/State/CgsGuiStateInterface.h | `9aa3e14baa0c4d1200553057ee23350b808bade66478b371e1ca5aa891cd066e` |
| b5-decomp/src/GameShared/GameClasses/Gui/View/CgsGuiViewModule.cpp | `313ce88a2c51a30ac5310d410e30b902bec8fa6c3d314dfcce574d007aff4a13` |
| b5-decomp/src/GameShared/GameClasses/Gui/View/CgsGuiViewModule.h | `898d0fd3449d2ba8dce797aee35df21437a6660c6ca94f5dcb59a12022e6f820` |
| b5-decomp/src/GameSource/Gui/Flow/HUD/States/BrnBootLegal.cpp | `0b0261d06d3f4692789cc4083ea4b079ba76ff2512698674cda154ce06f143a7` |
| b5-decomp/src/GameSource/Gui/Flow/HUD/States/BrnBootProfile.cpp | `f844cd4fb58d78f31b410c03d153291b4b585b25f33e090cc46ff951c2148c94` |
| b5-decomp/src/GameSource/Gui/Flow/Screen/States/BrnScreenLoading.cpp | `860a2470c648ff612883336741548b29a2a3da3fc2396ce445779b7aebce5ca1` |

No shared source, Git index/ref, author seal, game files or native process was changed. All fresh outputs are confined to this review directory.
