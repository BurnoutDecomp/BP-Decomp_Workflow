# Debug-menu campaign: complete handoff and stop record

Prepared at the user's request on 1 November 2026. This is a handoff, not a declaration that the campaign is finished. New reconstruction, test launches and agent work were stopped to prepare this document and consolidate branches.

## Read this first

The requested end state remains: every debug-menu entry must behave like the X360 ARTIST build, including genuine original no-ops and broken leftovers. Earlier-build behavior must not be invented to make such entries useful.

**Current final dispositions: 190 verified, 28 original no-ops, 1,137 pending, out of 1,355 original registration sites.** That is 218/1,355, or 16.1%, with a final disposition. A verified disposition is bounded by its recorded scene, input, consumer and evidence; it is not a promise that an entire subsystem or every parameter value is correct.

The 1,355 count is registration sites, not necessarily 1,355 distinct visible rows or separate manual tests. Some sites generate multiple rows, aliases or repeated list entries. The exact ID/caption/state/note/evidence registry is [entries.json](progress/debug_menu/entries.json); the decision overrides are [verdicts.json](progress/debug_menu/verdicts.json).

**The count fully implemented but awaiting behavior verification is still unknown.** Pending includes missing recovery, integration, incorrect supporting systems, missing real producer scenes, insufficient review, and authentic-leftover classification. It is inaccurate to say that all code is recovered and only play-testing remains.

Older figures such as 1,351/1,355 source-audited, 1,196 reviewed-source-cohort sites, 1,222 sites with source/body evidence, 1092-site packet unions, 137 Sound rows or 188 translated actions measure different things. None establishes finished behavior. The historical source coverage explanation is [here](progress/debug_menu/source_coverage_checkpoint_20261021.json).

## What is installed, and what is not

The normal playable executable at handoff start is `D:/Reverse/BP-Decomp_Workflow/build/game/Burnout_PC.exe`, SHA256:

`052112a5aa5286a001015f123d90e80a02142bdb58195552acab6e1e623ace52`.

It was installed on 31 October from b5 `ca80277748eb098822a035093cff9d306d079e2a`, workflow build snapshot `71be01e0cf78a3b4e7afe009a24f8ffa9faaad6a`. The full 3,019-TU build passed, and the isolated actual-save startup/driving baseline passed 12 checks, 235.1 m travel, one gameplay wreck, and zero assertions/exceptions. EA/Criterion completed without SkipIntro. This baseline is not a full-game regression certificate. See [playable refresh](progress/debug_menu/playable_refresh_20261031/README.md).

The most recent source repair restores the GUI audio callback's original raw event457/100-byte publication and exact `ON_LEFTSWEEP`/`ON_RIGHTSWEEP` names/actions11/13. Its code and regression commits are `747a347c8fd9bb8d1637e967c2c9a782f89a5638` and `5a4a19cace1dc080c0b61de4ba15130035706d19`.

That repair passed a full GUI TU compile, faithfulness scan, fresh source review, paired actual-source regression 323/0 against an unchanged-source 323/112 counterfactual, and a full shipping link with 3 rebuilt / 3,016 cached TUs, zero errors/warnings. Its isolated candidate is:

`D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/gui_audio_build_20261101/candidate/Burnout_PC.exe`

SHA256 `de1adb889abf5a4335c98566fdc83a452e2c993f1401b523d706b56e1a827ff6`.

**This candidate was not installed into build/game. Real GUI continuation and audible/native sweep validation were not completed.** The private 62209 native case was prepared, then its review was interrupted for this handoff; it must not be treated as approved or executed. Review had identified a profile timing concern and incomplete final receipt validation. The current source/build proof is [GUI audio checkpoint](progress/debug_menu/gui_audio_route_20261101/README.md). Branch integration below does not upgrade its validation status.

The user's live profile changed during their own use; the last read-only hash observed was `76a311af1fd4af088e921e6b1017e26e59b625598e250197adb0887bd2ed6fef`. Many retained tests use the older independent 4e4526ed… snapshot. **Never copy that fixture over the live profile.** A future ordinary test must freshly copy the then-current save and independently prove that it actually loaded.

## Work performed throughout the campaign

### Inventory, recovery and original-source comparison

- Built the original registration-site inventory, stable IDs, action/caption maps, source audit cohorts and per-site disposition/evidence records. Added assembly supplements for exporter holes instead of treating absent JSON as absent original code.
- Recovered and integrated debug registration/storage/callback paths across core monitoring, race-car diagnostics, gameplay/actions, Sound, GUI/HUD, Environment, Renderer/Scene/Director, Traffic/AI, Resource/Memory, World, network/progression and related lifecycle paths. Supporting systems had to be recovered as controls reached them; this was much larger than enabling menu rows.
- Compared authoritative ARTIST assembly/pseudocode, used DecFIGS for declaration/member shape, and used Feb2007 only for style/inlined idioms. Apt runtime layouts use the existing native64 XB1 exception. These rules remain required.
- Added focused actual-source fixtures, original-source counterfactuals, compile/faithfulness checks, full shipping builds and fresh reviews. Source audits and successful compilation were kept distinct from native behavior credit, although earlier reporting did not consistently make that distinction clear enough.
- Recovered the original debug action translator, including 188 unique IDs across 189 labels. This is source coverage, not 188 separately verified controls.

The canonical chronology and linked cohorts are [campaign README](progress/debug_menu/README.md) and [earlier history](progress/debug_menu/HISTORY_BEFORE_INTRO_REPAIR_20261020.md). The machine registry is the exact answer for an individual entry; prose summaries must not override it.

### Early visible/debug/system repairs

- Tailgate parameters, race-car state/HUD/mean-speed displays, related reset callbacks, forced spawning and original reset/render behavior were recovered and tested in bounded cases. Genuine inert actions were retained as inert.
- Restored GPU monitor registry/pass brackets, native D3D9 timing production and original measured graph/table behavior. Both GPU menu controls have final verified dispositions with graph/table/hidden evidence. They were not supposed to count as working merely because their Boolean values changed.
- Recovered resource/allocator creation/lifecycle paths, controller preparation, GUI preparation/language/startup, and supporting rendering/streaming behaviors exposed by the menu. Many source cohorts remain behavior-unverified.

### Later bounded behavior acceptance

Accepted evidence accumulated for Environment/sky/fog controls; traffic population/PVS/hull displays; collision render diagnostics; screenshot controls; world/prop circles; BoostBar presets/colors/grid; GUI visibility/safe-area controls; original forced-takedown output/countdown; resource heap/bundle/texture windows and navigation; Director/camera and Props displays; Scene triangle/padding/TriZ/cache/moment diagnostics; and shadow-map/car-casting controls.

These were partial cohort decisions, not blanket suite passes. Several original aggregate cases remain FAIL because of independent checker, timing, restore, scene or missing-producer failures. Their retained positive/negative/restore evidence supports only the individual accepted IDs and limits in their `ROOT_DECISION.json` files.

Recent concrete checkpoints:

| Cohort | Accepted result | Important remaining limit | Evidence |
|---|---|---|---|
| GUI17 | PC keyboard open/cancel and EA Trax notification |15 others pending, including font/PFX, invite residual icon and HUD restoration | [GUI17](progress/debug_menu/gui17_native_20261031/ROOT_DECISION.json) |
| Scene28 |7 bounded outcomes |21 need genuine producer/visible scene; aggregate not blanket-pass | [Scene28](progress/debug_menu/scene28_native_20261031/ROOT_DECISION.json) |
| Shadow5 | Render Shadow map and Cast shadows from cars |world/props/multiple-cascade receiver scenes pending | [Shadows](progress/debug_menu/shadow5_native_20261031/README.md) |
| Trigger16 |6 visible controls |10 pending; counters alone did not prove boxes, roaming/spawn geometry or planes/spheres | [Triggers](progress/debug_menu/trigger16_native_20261031/README.md) |
| Sound32 |15 total settled: 13 log gates, one loop-ID display (two labels), one query-sphere control |17 require AI/collision/GUI/passby/deformation producers | [Sound32](progress/debug_menu/sound32_native_20261101/ROOT_DECISION.json) |

### Player-jump filming

Recovered 13 original bodies covering collection preparation/failure/switching, camera-update cases and typed behavior accessors. Source/fixtures/fresh review passed and the source is in dev `ca8027774` and the installed 052 executable. This repaired a real trap/unhomed path; it did not establish that the enabled-jump camera works.

The genuine trigger355882/index4413 is elevated around y=20.00774. A valid lower-road launch produced airtime but passed below the trigger. A 48-point zero-speed road-seat survey found lower surfaces, not a valid elevated approach. No synthetic jump event, invented transform or no-op classification was used. **Allow Jump Moment native producer/camera proof remains pending.** See [source recovery](progress/debug_menu/jump_filming_recovery_20261031/README.md) and [approach survey](progress/debug_menu/jump_approach_survey_20261031/README.md).

### Most recent Sound work

Mapped the full remaining Sound registration/source cohort, then ran 32 original log/display controls through actual current-save boot and per-target positive/negative/captured restoration. The successful run has 99 attributed frames, 3,267 unique native alias triplets, 98 command hashes, terminal/post restore, exact owned cleanup and no asserts/exceptions.

Three engine/RPM/loop log gates were accepted from a retained partial run. Twelve more effects were accepted from the complete run: Loop Data, Boost, Wheel/Skid/Wheel Side, Traffic Engine/Management, Passby Effect/Cull/State logs; two original road-noise-loop IDs; and static-sound-entity query-radius wire drawing. These do not certify audible playback or attached-emitter audio. Seventeen targets remain pending, listed below. The complete archive is pinned by [ARCHIVE.json](progress/debug_menu/sound32_native_20261101/ARCHIVE.json).

The GUI-audio source work then found two real callback deviations:201/112 instead of457/100, and two wrong authored sweep strings. Ordinary audio had a compatibility consumer, so the producer mismatch alone did not prove every GUI sound was silent. The write-lock assertion already existed; an early hypothesis that it was missing was corrected before publication.

## User-reported gameplay regressions and support issues

| Report | What was repaired or established | What remains unproved |
|---|---|---|
| Road Rules vanish after restart |Missing/empty server reset-date was parsed as a current reset epoch; PC boundary now omits the absent reset event. Original save/reset formats retained.31-check fixture, exact old failures, two cold-load/login/save processes passed. [Report](progress/road_rules_persistence_20261014.md). |Newly earning every Silver/Gold/Showtime outcome was not exhaustively re-tested. |
| Road Rage thousands of takedowns and absurd time |Persistent TD output was retired after all same-step consumers, addressing repeated consumption. Source/hosted and bounded native count/countdown evidence exists. [State](progress/debug_menu/road_rage_output_retirement_20261023/STATE.json). |No fresh exhaustive offline-event campaign at the final merged head; historic STATE fields contain superseded pending notes. |
| Leaving overlay stuck for host and join |Original GUI completion/overlay path restored; bounded one-player host departure passed, including pixels/control return. [State](progress/debug_menu/freeburn_leaving_completion_20261023/STATE.json). |Joined-peer departure and full multi-peer sessions remain unverified. |
| Create Match / route/checkpoint placement freezes or crashes |Recovered source/GUI/caller paths and289-bound snap capacity; native placement/movement/Back passed on the recorded build. Supporting fixes integrated in prior deliveries. [Chronology](progress/debug_menu/README.md). |Complete multi-peer creation/racing, every route edit, save/overwrite/load and cold persistence are not certified. |
| Paradise Drives freeze / missing start icons / transparent map |Separate source/consumer/map-start-icon recovery packets exist under `progress/debug_menu/paradise_*`. |Whole flow and every visual state need independent end-to-end validation; source recovery is not that proof. |
| Saving custom route on another PC crashes |Original missing `SetFromGameParams` transfer, defaults/counts and getters were recovered with source/hosted evidence. [State](progress/debug_menu/custom_route_save_recovery_20261023/STATE.json). |Native save/overwrite/load/cold persistence on the affected flow remain explicitly pending. |
| Startup crash / junkyard black screen / magenta world |Separate startup, native allocation/lifecycle, config-owner and rendering repairs were made and bounded deliveries tested. See [startup report](progress/debug_menu/START_CRASH_20261013.md), [runtime owners](progress/debug_menu/runtime_owners_20261015.json), latest playable receipt. |A boot/no-assert pass does not prove all later gameplay or every config choice. |
| EA/Criterion intro hangs |The current 052 baseline runs the real branding movies without SkipIntro. |No claim that every video/content configuration is covered. |
| Minimap flicker/glitch recording |Native model-to-view event copied48 console bytes instead of64 PC bytes, truncating route pointer/map flags. Correct typed forwarding integrated; paired native raw data proved the fix. [Report](progress/debug_menu/minimap_native_payload_20261030/README.md). |The recorded brief visual glitch is still UNVERIFIED: requested screenshot timing was not met. Payload repair is not complete visual closure. |
| Repeated global End and PC disruption |Global END fallback removed; newer runs use exact process/slot/start ownership, scoped input, bounded jobs, isolated saves and mute. User later authorized full resources. |Old helper copies are not all suitable for reuse; do not reactivate global-input fallback. |
| Disk/branch clutter |Old captures removed; recent cleanup recovered about 39 GB, with important originals in verified lossless archives. Branch consolidation is recorded below. |Keep captures capped and retire refs as part of delivery. Do not delete user OBS recordings, unique evidence or unknown WIP. |

## Why this took so long, and where checking was inadequate

There was genuine missing or incorrect code below the menu, but the process also wasted time and failed to protect against enough regressions. Recovery, registration coverage, compilation, field readback and full behavior were too easily conflated in updates. There is no reliable defensible global implementation percentage beyond the disposition count above.

Early checks were too narrow to establish full gameplay. A successful boot or a native run with no assert could still miss broken counters/timers, inactive render consumers, missing event producers, route persistence and multiplayer cleanup. Some source changes reached delivery without the broad gameplay coverage the user expected. Root caused or missed regressions and did not catch them promptly enough; not every reported issue has been bisected to prove its introducing commit.

Later evidence became stricter, but authoring/reviewing bespoke test harnesses became another bottleneck. Concrete test-protocol failures included overlong native aliases, missing/late profile-load evidence, inappropriate early Sound INI activation before RWAC existed, Boolean/enum conversion mistakes, schema mismatches, stale scene/motion receipts and an anchored frame-ACK parser that missed audio-prefixed records. Those are not repaired game features and must not inflate progress.

Original failures are retained. Partial acceptance is valid only for independently joined raw source/input/consumer/positive/negative/restore evidence. It must never turn a failed whole suite into a claimed whole-suite pass.

## Exactly what remains

### Blocking delivery/validation work at stop

1. The GUI audio repair is source-reviewed and fully built, but its real GUI/native continuation was not completed. Private62209 preparation is **not approved**: review was interrupted for this handoff, with confirmed concerns about waiting on `one-profile` before `OnProfileLoaded`, and final consumer joins/cleanup/profile/input-restoration validation. Fix those producer/consumer tests before launching; the 38 helper tests do not cover the whole new timing/receipt path.
2. Do not install de1 into the normal folder solely because this handoff merged source history. Native UI/asset/audio validation and a controlled15-payload refresh are still separate tasks. Preserve current config/profile/logs and record the exact candidate/installed SHA pair.
3. Seven selected Trigger controls still lack a valid scene. Both private 62208 attempts fired shot0 before CarSelect Exit. Even `BRN_SWEEP_WAIT_ROAMING=1` saw the initial roaming state and did not guarantee post-exit placement. Requested warehouse pose stayed 4,577 m away at the initial junkyard. Scene guards correctly stopped before activation/setters; 0 targets/frames, no control credit. The sweep's `seat ok` text alone is not proof of placement. Use an original post-exit teleport/control path or a genuinely synchronized fixture; do not loosen pose gates or invent transforms.
4. Minimap transient, custom route save/reload, joined-peer Leaving, complete online/custom events and wider normal-event regression coverage remain open as above.

### Remaining 17 in the collected Sound cohort

- `#0003` Closest AI; `#0056` AI Skids: require actual attached/updating offline rivals and the real nearest-AI selection.
- `#0058` Collision Info; `#0061` Detaching; `#0062` Ducking; `#0063` All Inputs; `#0076/#0077` Scrape info/drawing; `#0080` collision spheres; `#0081/#0082` orientation text/geometry; `#0083` prop IDs: require their exact collision, state-replacement, scrape/material-lookup and geometry producers, repeated in every relevant phase.
- `#0085` Draw Attached and `#0088` Passby Verbose: require actual attached engine/passby lifecycle/cull transitions; visible traffic alone is insufficient.
- `#0104` HUD Messages; `#0105` GUI Messages: require the real Sound5/6 message route and matched UI/event producer in positive, negative and restored phases. A key tap alone is not an event-consumer witness.
- `#0117` Deformation: requires real deformation updates with serializer non-playing.

The bounded next-run plan is frozen in [SOUND17_SCENE_PLAN.md](progress/debug_menu/shutdown_20261101/pending_work/SOUND17_SCENE_PLAN.md); it maps existing Marked Man, Road Rage/impact, prop-hit, traffic and GUI cases. It creates no new behavior credit.

Two omitted Sound flags `#0057` Print Collision Bins and `#0102` Crash Streams also remain pending. Adjacent active flags and a functioning audio path do not establish readers for those cells. The existing `tools/re/x360rd.py`, `ppcdis.py` and `sound_batch/full_image_cell_references.json` are available; do not repeat the claim that original bytes are inaccessible merely because an export/IDA-worker route is missing. Full reader/xref closure is still needed before any no-op verdict.

### Whole-campaign work

All 1,137 pending IDs need an explicit final outcome. For each: establish actual original registration/storage/callback/consumer chain; recover/fix missing code against assembly; integrate; run appropriate source/build checks; then prove actual output and restoration in the right scene or prove authentic original inert/broken behavior. Group related controls into large cohorts, but keep per-site limits.

Remaining areas include unverified GUI/font/PFX/invite/HUD controls, Director/camera producer scenes and jump filming, world/prop/shadow receiver scenes, trigger locations/boxes/planes/spheres/grid, resource/replay/numeric/control domains, AI/traffic/game-state/progression/network behaviors, and many rows whose source was mapped but full consumer behavior was never established. Physical controllers, hardware-specific graphics, audio/audibility and multi-PC/multi-peer cases need their own real validation.

## Exact remaining scope by original registration function

This table is generated from the authoritative 1,355-site inventory at 190 / 28 / 1,137. It is the complete count breakdown; use per-ID registry notes/evidence for exact acceptance limits.

| Original registration function | Total | Verified | Original no-op | Pending |
|---|---:|---:|---:|---:|
| `??$Process@H@DebugMenuSerialiser@Camera@BrnDirector@@QAAXPBDAAH@Z` | 1 | 0 | 0 | 1 |
| `??$Process@I@DebugMenuSerialiser@Camera@BrnDirector@@QAAXPBDAAI@Z` | 1 | 0 | 0 | 1 |
| `??$Process@M@DebugMenuSerialiser@Camera@BrnDirector@@QAAXPBDAAM@Z` | 1 | 0 | 0 | 1 |
| `??$Process@_N@DebugMenuSerialiser@Camera@BrnDirector@@QAAXPBDAA_N@Z` | 1 | 0 | 0 | 1 |
| `??$Serialise@VDebugMenuSerialiser@Camera@BrnDirector@@@ICEMoviePlaylist@BrnDirector@@QAAXAAVDebugMenuSerialiser@Camera@` | 4 | 0 | 0 | 4 |
| `??$SerialiseBehaviourParameters@VTestbedSetupSerialiser@Camera@BrnDirector@@@Camera@BrnDirector@@YAXPBDAAVParameters@Be` | 1 | 0 | 0 | 1 |
| `BrnAI::RaceBalancingDebugComponent::OnActivate` | 2 | 0 | 0 | 2 |
| `BrnAI::ResetOnTrackDebugComponent::OnActivate` | 9 | 0 | 2 | 7 |
| `BrnAI::RouteMapDebugComponent::OnActivate` | 24 | 4 | 0 | 20 |
| `BrnDirector::ArbStateTestbed::RegisterIceAnimsWithDebugComponent` | 1 | 0 | 0 | 1 |
| `BrnDirector::DebugComponent::OnActivate` | 55 | 6 | 0 | 49 |
| `BrnEffects::EffectsDebugComponent::OnActivate` | 67 | 0 | 6 | 61 |
| `BrnEffects::EffectsDebugComponent::SetupBoostMenu` | 4 | 0 | 1 | 3 |
| `BrnEffects::EffectsDebugComponent::SetupJumpMenu` | 5 | 0 | 0 | 5 |
| `BrnEffects::EffectsDebugComponent::SetupLionMenu` | 8 | 0 | 0 | 8 |
| `BrnGame::BrnGameModule::Construct` | 6 | 0 | 0 | 6 |
| `BrnGameState::ChallengeManagerDebugComponent::OnActivate` | 5 | 0 | 0 | 5 |
| `BrnGameState::CrashScoreDebugComponent::OnActivate` | 2 | 0 | 0 | 2 |
| `BrnGameState::GameStateDebugComponent::OnActivate` | 25 | 0 | 0 | 25 |
| `BrnGameState::ModeManagerDebugComponent::OnActivate` | 10 | 4 | 0 | 6 |
| `BrnGameState::PaybackDebugComponent::OnActivate` | 2 | 0 | 0 | 2 |
| `BrnGameState::ResetPlayerDebugComponent::OnActivate` | 8 | 0 | 0 | 8 |
| `BrnGameState::RoadRulesDebugComponent::OnActivate` | 5 | 0 | 0 | 5 |
| `BrnGameState::ScoringSystemDebugComponent::OnActivate` | 1 | 0 | 0 | 1 |
| `BrnGameState::StreetManagerDebugComponent::OnActivate` | 6 | 0 | 0 | 6 |
| `BrnGameState::StuntManagerDebugComponent::OnActivate` | 6 | 0 | 0 | 6 |
| `BrnGameState::TakedownManagerDebugComponent::OnActivate` | 4 | 2 | 0 | 2 |
| `BrnGameState::TriggerQueryManagerDebugComponent::OnActivate` | 11 | 5 | 0 | 6 |
| `BrnGraphics::DebugComponent::OnActivate` | 51 | 9 | 0 | 42 |
| `BrnGui::EffectsArbitrator::Construct` | 8 | 0 | 0 | 8 |
| `BrnGui::GuiCacheDebugComponent::OnActivate` | 3 | 0 | 0 | 3 |
| `BrnGui::GuiCustRendererDebugComponent::OnActivate` | 17 | 14 | 0 | 3 |
| `BrnGui::GuiDebugComponent::OnActivate` | 43 | 8 | 0 | 35 |
| `BrnGui::GuiHudMessagesDebugComponent::OnActivate` | 6 | 0 | 0 | 6 |
| `BrnGui::SatNavDebugComponent::OnActivate` | 15 | 1 | 0 | 14 |
| `BrnMassive::BrnMassiveDebugComponent::OnActivate` | 3 | 0 | 0 | 3 |
| `BrnNetwork::BrnNetworkModule::Prepare` | 2 | 0 | 0 | 2 |
| `BrnNetwork::BuddyManagerDebugComponent::OnActivate` | 12 | 0 | 4 | 8 |
| `BrnNetwork::EventScoresManagerDebugComponent::OnActivate` | 1 | 0 | 0 | 1 |
| `BrnNetwork::ImageManagerDebugComponent::OnActivate` | 2 | 0 | 1 | 1 |
| `BrnNetwork::LiveRevengeDebugComponent::AddPlayer` | 5 | 0 | 0 | 5 |
| `BrnNetwork::LiveRevengeDebugComponent::OnActivate` | 3 | 0 | 0 | 3 |
| `BrnNetwork::LiveRevengeDebugComponent::RegisterRelationship` | 16 | 0 | 0 | 16 |
| `BrnNetwork::RoadRulesManagerDebugComponent::OnActivate` | 2 | 0 | 0 | 2 |
| `BrnNetwork::ScoreboardDebugComponent::HandleScoreboardHeadingEvent` | 3 | 0 | 0 | 3 |
| `BrnNetwork::ServerInterfaceDebugComponent::OnActivate` | 4 | 0 | 0 | 4 |
| `BrnNetwork::StatsDebugComponent::AddStats` | 1 | 0 | 0 | 1 |
| `BrnNetwork::StatsDebugComponent::OnActivate` | 5 | 0 | 0 | 5 |
| `BrnNetwork::TrafficManager::Prepare` | 1 | 0 | 0 | 1 |
| `BrnPhysics::Deformation::DeformationDebugComponent::OnActivate` | 48 | 0 | 1 | 47 |
| `BrnPhysics::Props::PropDebugComponent::OnActivate` | 16 | 1 | 0 | 15 |
| `BrnPhysics::Vehicle::DebugComponent::InitWindows` | 2 | 0 | 0 | 2 |
| `BrnPhysics::Vehicle::DebugComponent::OnActivate` | 26 | 0 | 0 | 26 |
| `BrnPhysics::Vehicle::PhysicalTrafficManagerDebugComponent::OnActivate` | 18 | 1 | 4 | 13 |
| `BrnPhysics::Vehicle::VehicleManagerDebugComponent::OnActivate` | 83 | 0 | 0 | 83 |
| `BrnProgression::ProgressionDebugComponent::OnActivate` | 23 | 0 | 0 | 23 |
| `BrnReplays::DebugComponent::OnActivate` | 8 | 0 | 0 | 8 |
| `BrnResource::DLCDebugComponent::OnActivate` | 1 | 0 | 0 | 1 |
| `BrnResource::DebugComponent::OnActivate` | 3 | 3 | 0 | 0 |
| `BrnSound::Debug::DebugComponent::InstallConsole` | 1 | 0 | 0 | 1 |
| `BrnSound::Debug::DebugComponent::OnActivate` | 136 | 22 | 0 | 114 |
| `BrnTraffic::DebugComponent::OnActivate` | 108 | 19 | 0 | 89 |
| `BrnWorld::BoostDebugComponent::OnActivate` | 8 | 0 | 0 | 8 |
| `BrnWorld::BoostDebugComponent::RegisterBoostVariables` | 8 | 0 | 0 | 8 |
| `BrnWorld::CollisionDebugComponent::OnActivate` | 4 | 0 | 0 | 4 |
| `BrnWorld::CrashPlayDebugComponent::OnActivate` | 4 | 0 | 1 | 3 |
| `BrnWorld::EnvironmentSettings::DebugComponent::OnActivate` | 97 | 41 | 0 | 56 |
| `BrnWorld::EnvironmentSettings::EnvironmentManager::Construct` | 7 | 0 | 0 | 7 |
| `BrnWorld::PVSDebugComponent::OnActivate` | 12 | 0 | 0 | 12 |
| `BrnWorld::PowerParkingDebugComponent::OnActivate` | 18 | 0 | 0 | 18 |
| `BrnWorld::PropEntityDebugComponent::OnActivate` | 15 | 4 | 0 | 11 |
| `BrnWorld::PropEntityModule::Construct` | 7 | 1 | 0 | 6 |
| `BrnWorld::RaceCarEntityModuleDebugComponent::OnActivate` | 57 | 13 | 2 | 42 |
| `BrnWorld::ShadowMap::Construct` | 34 | 2 | 0 | 32 |
| `BrnWorld::TriggerEntityModuleDebugComponent::OnActivate` | 5 | 1 | 0 | 4 |
| `BrnWorld::WorldDebugComponent::OnActivate` | 20 | 0 | 3 | 17 |
| `BrnWorld::WorldEntityModule::Construct` | 13 | 1 | 0 | 12 |
| `CgsDev::DebugComponentMessageFilter::OnActivate` | 4 | 0 | 0 | 4 |
| `CgsDev::DebugComponentPerfMonCpu::OnActivate` | 5 | 0 | 0 | 5 |
| `CgsDev::DebugComponentPerfMonGpu::OnActivate` | 2 | 2 | 0 | 0 |
| `CgsDev::DebugManager::RegisterComponent` | 1 | 0 | 0 | 1 |
| `CgsDev::DebugManager::RegisterComponentSimple` | 1 | 0 | 0 | 1 |
| `CgsDev::DebugUI::DebugUI::Construct` | 1 | 0 | 0 | 1 |
| `CgsNetwork::HostMigrationDebugComponent::OnActivate` | 4 | 0 | 0 | 4 |
| `CgsNetwork::PlayerManagerDebugComponent::OnActivate` | 5 | 0 | 0 | 5 |
| `CgsResource::DebugComponent::InitWindows` | 18 | 16 | 0 | 2 |
| `CgsResource::DebugComponent::OnActivate` | 2 | 0 | 0 | 2 |
| `CgsSceneManager::SceneManagerDebugComponent::OnActivate` | 29 | 6 | 2 | 21 |
| `CgsSceneManager::SceneSweeperDebugComponent::OnActivate` | 3 | 0 | 0 | 3 |
| `CgsSceneManager::TriangleCollisionDebugComponent::OnActivate` | 17 | 4 | 1 | 12 |
| `sub_8224F218` | 3 | 0 | 0 | 3 |

## Branch consolidation and preserved local work

The final branch journal is [branch consolidation record](progress/debug_menu/shutdown_20261101/BRANCH_CONSOLIDATION.json). It records before/after refs, complete tip hashes, patch-equivalence/ancestry/merge-preview checks and each retirement decision. A deleted branch name is not deleted work: retained parents/history preserve its commit objects.

**Code integration and history consolidation are deliberately distinguished.** The current GUI audio repair and the AI velocity/speed accessor candidate are normal content integrations. The latter still needs independent source/caller/native review. Old variants that conflict with newer source are retained as historical parents with current production implementations preserved; that does not mean every old alternative was activated, reviewed or made correct. Their unresolved source alternatives remain inspectable by the recorded original commit IDs. Never describe a history-only consolidation as finished gameplay implementation.

Unrelated dirty main-checkout work is preserved, including workflow IDA databases/status/tool submodule changes and these four gameplay files: `BrnRendererModule.cpp`, `BrnWorldModule.cpp`, `BrnWorldModuleIO_DispatchInputBuffer.cpp/.h`. Unknown/untracked files are preserved. Other contributors' active experimental/physics/Apt/pause work is not silently merged or deleted. Checked-out campaign refs are detached only at the same exact commit while retaining their files/evidence; no recursive worktree deletion or broad reset is part of this handoff.

Branch results and final integration hashes are appended below when consolidation completes. They do not imply another gameplay build/test occurred.

## Evidence, storage and resuming safely

- Canonical accepted results: `progress/debug_menu/verdicts.json`, `entries.json`, per-cohort `ROOT_DECISION.json` and independent reviews. `progress/status.json`/TU `done` means something else and does not certify menu behavior.
- Raw archive receipts point to `D:/Reverse/BP-Decomp_Evidence/debug_menu/` and the verified scratch-frame archive. Do not delete those archives or rewrite original FAIL receipts. Latest raw captures remain bounded; one optional14-frame/~52MB deletion was blocked by automatic approval review with only "blocked by policy" and left unchanged.
- User recording: `C:/Users/adri1/Videos/OBS/2026-10-29 20-46-33.mp4`, retained. Existing old105.1GB cleanup history and recent~39GB cleanup are different dated receipts; do not double-count them as today's gain.
- No tests should touch `build/game/Memcard/Profile.sav`. Copy the latest save into a private slot and prove actual runtime load before input. Match exact PID/image/start, use scoped input only, cap logs/frames, restore typed baseline and clean up only owned processes. Never reintroduce repeated global End.
- Before using a retained scratch package, verify its exact source/build/helper pins and producer/consumer coverage. Some packages are failed or superseded by design; old queue files/graphs are navigation/history, not current truth.
- User model preferences: no Astra; Luna Max for routine preparation, Sol medium/high for harder work and Sol Max for demanding ABI/assembly. Follow the currently applicable AGENTS reviewer-concurrency rule rather than silently changing the user's intended work policy.
- Do not resume any reconstruction, builds, agents or game launches automatically after this handoff. The user explicitly requested a stop after documentation/consolidation. Resume only when they ask, starting with this document and live Git/status/evidence rather than the stale chat narrative.

## Finalization record

Completed on 1 November 2026, then work stopped:

- **Gameplay dev, pushed:** `435d3dbe3f061d282cbc4566013eecbfdaab5d36`. The GUI audio repair was fast-forwarded to `5a4a19cace1dc080c0b61de4ba15130035706d19`. The AI velocity/speed accessor candidate `a963bba6a5ffc92ebce621668e773ffeea020f4a` was content-merged as `28de046ad8b4563538acc84af9e47f277341d5c9`; earlier compile/hosted eight-slot evidence exists, but independent review, invalid-index/caller and live validation remain pending. The final combined head was not rebuilt.
- **Workflow main, history consolidation pushed:** `f1aed7b5c9d9f494b89d7e01613b7546398c61f4`. This handoff, journal and frozen unfinished files are published in the following documentation commit on main; its exact hash is available from Git history.
- **Historical variants:** the gameplay and workflow history merges retained 50 and 7 parent tips respectively with the current integration trees unchanged. Conflicting or unvalidated alternatives were **not content-integrated**. Their exact commits are reachable from published integration history and indexed in the journal. Reviewing/recovering any still-useful unmatched differences remains unfinished work; this cleanup does not establish they were all superseded correctly.
- **Deleted after ancestry/publication proof:** gameplay 55 local + 31 remote refs; workflow 11 local + 8 remote refs. Total: **66 local and 39 remote branch refs retired**. Exact names, tips, merge previews and same-head worktree detach receipts are in the [journal](progress/debug_menu/shutdown_20261101/BRANCH_CONSOLIDATION.json). Worktree files/evidence were retained.
- **Remaining branches:** gameplay has 2 local (`dev`, `wip/pause-driverdetails`) and 5 remote (`dev`, `apt-audit`, `physics`, `codex/experimental-x360-byte-match`, `wip/pause-driverdetails`). Workflow has 4 local (`main`, `codex/experimental-x360-byte-match`, `docs/reconcile-with-repo-state`, `worktree-agent-a7f8d48e1b9570604`) and 4 remote (`main`, `dev`, `boot_goal_progress`, `docs/reconcile-with-repo-state`), excluding symbolic HEAD. Separate active/unique work was preserved; the experimental remote advanced during the audit.
- **Preserved WIP and build:** unrelated dirty/untracked files and the existing workflow submodule pin were not staged/reset. The active gameplay checkout is published dev; the workflow's committed b5 gitlink still pins `ca80277748eb098822a035093cff9d306d079e2a`. No game was built, launched or installed during finalization. The installed executable remains **052112a5aa52**, and final dispositions remain **190 / 28 / 1,137**.
- **Unfinished authored files:** the unapproved private 62209 native preparation, its runner and Sound plans are frozen in [pending_work](progress/debug_menu/shutdown_20261101/pending_work/README.md), with original hashes in [ARTIFACT_MANIFEST.json](progress/debug_menu/shutdown_20261101/ARTIFACT_MANIFEST.json). No save binaries, executable payloads or frame dumps were added.

All recovery, agents, builds and native testing are stopped. The overall campaign remains incomplete and is paused at the user's request. Resume only after a new explicit instruction.
