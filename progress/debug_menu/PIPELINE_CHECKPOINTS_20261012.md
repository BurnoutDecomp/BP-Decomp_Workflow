# Continuous recovery checkpoints

Coherent source increments are committed and pushed before full-page validation.
Both repositories use codex/debug-menu-recovery-pipeline for the current integration
log/code. Unverified source remains off main/dev. Recovery continues during checks.

| b5 checkpoint | Scope | Remaining validation/work |
| --- | --- | --- |
| e334f93f | Traffic/Physical/Route 150; 59 production paths; source review and 737 grouped checks pass | Full native consumer and conditional proof |
| 4be7f005 / 2c270c6e | Vehicle/Deformation 131; real bindings, storage and consumers | Three source review defects repaired below; CPU/native pending |
| 3f605ae9 / 21ad74ad | Environment/Graphics 148 source packet integrated | Query/backend/readers/startup gaps; compile/review/native pending |
| 38b6a739 + ceb88eab / c1f551e3 | Original editable sine, takeoff ramp and unsigned preset repairs | Independent review and grouped validation underway |
| 11b37307, e43227ed, b5d927fb | Handling 28 registrations, observer, traction draws and grip windows/graphs | RenderWorld/HUD and listed draw/report helpers incomplete |
| 6c911139 | Original eight-stage Game Prepare and bounded supporting helpers | Resource-core bodies, Lua callbacks, renderer/startup integration pending |
| a82e6dfa, 7eabdb81 | SceneManager 29 bindings, typed owner, counters and RenderWorld dispatch | Draw leaves, Effects and ShadowMap consumers continue |
| 0590289f, 924c2e78 | RaceCar LOD original registration; GameState bindings/owners/Prepare | Shared PC duplicate registration and GameState consumers continue |
| 924c2e78 (unchanged page source) | Power Parking 18 and Reset Player 8 existing-body audits | Compile, fresh review and native verification pending |

The union of recorded source recovery/audit packets is 631 of 1,354 static sites.
Known consumer/backend gaps remain explicit; source coverage is not gameplay
completion. Handling's incomplete 28-site page is excluded. Final dispositions
are 25 verified and three original no-ops. See README.md, batches.json and
verdicts.json for non-overlapping sets and supported states.

57b12968 adds the 35-check production fixture and renderer enum typing fix. The
147 repair supplement passes; canonical compile and both negative controls have
the expected results. This does not add any native working-entry verdict.

The LOD original-registration/PC duplicate follow-up is complete at de73da21.
The production INI fixture passes 79 checks and three affected TUs compile.
Handling source has advanced through 92f4127d and 8ee01f13; Scene cached drawing
is checkpointed at a4cc1d40. Their remaining helpers and validation are explicit.

Progression23 is source-ready at 02a0f889, integrated at 5c7655a1; four C++ TUs
compile with no new faithfulness findings. Source packet union is now 654/1354;
fresh review/native remain pending. Handling is complete at e0a0779a for its
ARTIST-attested consumer scope and is being frozen for integration/review.

The primary workflow checkout now uses the pushed recovery branch. Eleven old
owned dirty copies were verified as exact blobs in published ancestry, backed up
under parent_owned_checkpoint_backup, and replaced by committed branch contents.
Unrelated tracked WIP and the gameplay HEAD were checked unchanged. The previous
publication worktree is clean/detached at 36060d6e.

Handling28 is integrated through5ef9611d, with all four changed C++ TUs compiling
and no new faithfulness findings. One combined199-site Sol review is underway;
both Luna source lanes continue. The source packet union is682/1354; final
working/no-op dispositions remain25/3.
