# Continuous recovery checkpoints

Current totals and validation state are in [the 319-site checkpoint](SOURCE_BATCH_319_20261012.md):
917 of 1355 distinct static sites have source/audit packets; final dispositions remain
25 verified plus 3 original no-ops. The chronology below records earlier states.

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

SceneManager29 is frozen/pushed at cd9f99bf, with five source pins independently
verified and archived. It remains separate from the frozen199-site review and
awaits integration/compile/review/native. Packet coverage is now711/1354; this
is source recovery/audit coverage, not711 working controls. The ongoing199 review
has raised four renderer/environment discrepancies; no pass is claimed.

fdc74c9b checkpoints the first two199-review source repairs on a separate branch:
full environment color W stores and original occlusion defaults. The primary
review snapshot stays frozen; further findings and validation remain open.

## 8743b279 / d2a25d16: review repairs while recovery continues

The combined199 source review failed with eight bounded findings. Root pushed
five default/math source candidates in fdc74c9b and 8743b279; Sky/grip canonical
compile and zero-new faithfulness checks pass. Sol pushed preview color and early
threshold candidates in d2a25d16 and continues the full typed rendering bracket.
The immutable report and versioned repair snapshots are recorded in
REVIEW_REPAIRS_20261012.md. Both Luna recovery lanes continue. These candidates
have not received the combined repair review or native verdicts; counts remain
711 source-packet sites and 28 final dispositions.

## 235701ca / 67de01e7: root repairs tested; SceneManager integrated

Five root source repairs and the extracted-body fixture are integrated and
pushed. The focused group passes54/54; pre-repair5ef9611d fails28 with the same
fixture. SceneManager29 is imported from the pinnedcd9f99bf cohort: all5 source
pins match, both changed C++ TUs compile and no new faithfulness findings exist.
Its review/native checks and two unclassified non-cached flags remain pending.

GameState renderers are separately pushed atbfd81989 and frozen in a5-path ZIP;
12 chains are complete,11 candidates remain unresolved, and the original
PreWorldUpdate/EmmPreWorldUpdate caller/writer are missing. No count promotion is
made for that partial page. Source union remains711/1354; final dispositions
remain25 verified+3 original no-ops. Sol continues the renderer repair and both
Luna lanes continue recovery.

## Resumed:6cba4b3a / d62fe25b GameState source checkpoints

The saved GameState cohort and EMM/paused-mode increment are committed and pushed
on a separate branch. Three import TUs and two update TUs compile with zero new
faithfulness findings. The full PreWorldUpdate caller remains in progress; no
page-count or final-verdict promotion. GAMESTATE_UPDATE_CHAIN_20261012.md records
the versioned evidence. Both Luna recovery lanes and Sol renderer checks resumed.
