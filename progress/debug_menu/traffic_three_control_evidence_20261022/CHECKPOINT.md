# Traffic run04: three bounded native dispositions

The retained run04 review passes exactly these three sites against B5 source commit `d9de0ab1d395425eb39d0fdbb5e70f93235d601a`, hosted build run [39736578561](https://github.com/BurnoutDecomp/BP-Decomp_Workflow/actions/runs/39736578561):

- `BrnTraffic::DebugComponent::OnActivate#0001`, Turn traffic off: the HUD/off/cleanup reads are FALSE/TRUE/FALSE. Actual traffic samples fall from 99 alive/17 near to 0/0, remain 0/0 through cleanup, then repopulate to 112/12. Independently reviewed off/cleanup pixels agree. The internal teardown-state entry is not directly logged.
- `BrnTraffic::DebugComponent::OnActivate#0057`, Draw active hulls: HUD is TRUE and lanes is FALSE. A completed native SET/DRAW receipt (epoch 143, draw sequence 1) records hull IDs 101, 102, 122, 123 mapped to four PVS boxes; reviewed frames show the grid appear and disappear. The screenshot is not proven to be the exact receipt frame.
- `BrnTraffic::DebugComponent::OnActivate#0088`, Render special perfmons: HUD is TRUE, lanes and cleanup are FALSE. The table is visibly present/absent in the selected frames. Individual counter accuracy, monitor lifecycle and timing were not independently verified.

The review checked all 42 native records for these sites and five selected 1280x720 BMPs. The exact review is `REVIEW.md` (SHA-256 `26cf4d389d1228df60b6197bd17aaa0699cbf06265fd98eeb592775d97a8aa46`). `SITE_DISPOSITIONS.json` carries the separate site outcomes; `SOURCE_BINDINGS.json` carries the source, log, native-line and image bindings. The copied `INTEGRITY.sha256` preserves the original review packet seal.

This is bounded phase evidence, not same-frame correlation. The historical run04 Traffic74 aggregate remains **FAIL**; all 74 CSV `pre_run_status` rows remain `PENDING_NOT_RUN`, and `runtime_consumer_verified` remains 0. Sites #0045/#0046/#0047/#0050 remain excluded/pending. This review gives no new #0086 credit, no extra 15-hull cycle credit and no full manual-gate pass.

The installed normal package remains the documented `8fec93bd` build. This evidence is for the retained d9 run and does not change delivery or B5 submodule-pointer claims; the later `0bfa585e` Flowtype source checkpoint is not represented as included. No build, CI, native run or source execution occurred during this documentation publication.