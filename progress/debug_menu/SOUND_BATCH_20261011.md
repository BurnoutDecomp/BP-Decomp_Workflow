# Complete Sound page and shared gameplay diagnostics

Published source: `b5-decomp e6aac121`. This batch covers 137 original Sound
registration sites (136 OnActivate plus Console), four Marked Man tunables and
all four Takedown Manager controls. Recovery and review are complete for the
named changes; final behavior dispositions remain separate in `verdicts.json`.

## Recovered code

The Sound page now registers every original binding, type, range, step and
option. Duplicate Clutch and Panning Distance captions remain as in ARTIST.
Eight missing component bodies restore update, HUD, 3D callback, maximum-RPM
readout, material/action/bank lists and splice audition. The callback is installed
once and obeys the original gate. Shared storage now reaches the confirmed
engine, wheel, collision, traffic, passby, environment, presentation, music,
deformation, allocator and external-body readers.

Statistics restores its original histories, held reset, text and graph producers.
Root Sound runs the original allocator sanity/dump tail and one-shot actions.
World-scene sphere drawing and engine-loading diagnostics share the real fields.
Collision records retain original initialization, including indeterminate fields
on legacy forced paths; no invented defaults repair those original leftovers.

Marked Man's menu and SurvivorMode share the four actual tunables. The original
FMA order, integer conversion and opponent cap are preserved. Takedown restores
the two missing world overlays, reading cached active-car/contact/revenge data,
with original radius and packed red/yellow colours. Its existing HUD and force
callback were reviewed too. The existing opt-in event-start harness can wait
for the real menu configuration to be saved before starting the test event.

## One grouped validation round

Parallel source specialists produced the batch before testing. One independent
GPT-6.1 Sol Max review approved the 75 named Sound/integration paths; Marked Man
and Takedown had their own earlier source reviews. The named Sound diff SHA256 is
`c7577dda35fc9d6b2df473e5ca7188ee29832e154ef539870258b0a9bf1c5b46`.
All reviewed file hashes matched the final recovery marker. The bounded
79-production-path faithfulness gate reports no new findings.

Nine regression groups ran together and pass 2,330 checks:

| Group | Passed checks |
| --- | ---: |
| Sound bindings, metadata, callbacks and mixer | 2,116 |
| Statistics and collision | 37 + 32 |
| World, root sound and physics | 7 + 10 + 9 |
| Speed/music streams | 27 |
| Marked Man | 49 |
| Takedown Manager | 43 |

The initial Sound/stream fixture scaffolding errors were repaired without
production changes; their successful author reruns are recorded separately.
Shipping build `20261011_195740_debug-sound-137-final.log` compiles seven changed
units, reuses 2,943 and links all 2,950. A preceding full affected build found a
missing original const qualifier on LoopModelData's dump method; that correction
received a separate delta review before the successful link.

Two private-slot scenarios then ran in parallel against executable SHA256
`c19fd41e8a5aa6b72f88c750e8a74984b32d1f85574ca4e5602a0d38ef44da8f`:

- Sound, slot 16, `scratch/bugtest/runs/debug_menu_sound_batch/20261011_195901`:
  8/8 evaluator checks, no asserts/exceptions, real console sequence, native
  registry, allocator dump, one-shot cleanup, eight retained screenshots and
  engine PCM. Original duplicate captions are validated by the source fixture;
  saved-path presence alone cannot distinguish duplicate registration sites.
- Marked Man/Takedown, slot 15,
  `scratch/bugtest/runs/debug_menu_markedman_takedown/20261011_195827`:
  11/11, no asserts/exceptions. SurvivorMode starts with one rival, two grid
  locations and ramp limit 17 after edits 1/1/11/17. It enters progress and its
  clock advances. The real cached snapshot has three slots and produces recent
  contact sphere submissions. Settings restore to 2/4/5/5 afterward.

Both use copied profiles. Build/run provenance, initial failures and final
results remain in those scratch directories. Sound's two evaluator context-path
errors were corrected by re-evaluating the same retained run with NoRun; no
second successful game execution is implied.

## Behavior evidence and remaining work

Master Gain is witnessed at the actual engine-fill PCM tap: nine stable
0.512-second windows at gain 0 have exactly zero RMS and peak; gain 4 has nonzero
output before and after (mean RMS 1284.16 and 1640.04). Boundary windows are
excluded. This witnesses the engine mix; the harness mutes speaker output.
Statistics and maximum-RPM text are visible and disappear on cleanup. Maximum
RPM remains zero, consistent with the original unwritten monitored value.
Allocator dump records and their original footer are produced. Splice Stats Dump
prints five live bank sections and 775 indexed rows, with 11 nonzero play counts;
both one-shot fields clear. These four Sound sites, four Marked Man tunables and
the recent-contact vulnerability path receive final verified verdicts. Revenge
and populated last-takedown records remain pending.

Native statistics exposed a pre-existing platform clock mismatch: PC
GetCpuCycle returns raw TSC ticks while ARTIST's counter is 49,875,000 ticks/s.
The original statistics coefficient and CPU balancer therefore receive the
wrong units. Clock calibration remains pending at this checkpoint; the huge
captured percentages are not accepted as correct timing values.

Hold/spin changed real menu fields but the captured player car did not visibly
hold/lift/spin. The restored reader belongs to ExternallySimulatedBody and is
called through physical body parts; a player-car effect is not claimed. Original
no-reader findings, the copied InAir slope parameters, crash-stream/fade/roll
leftovers and unexercised collision/audition/revenge branches remain pending.
No missing-feature revival is included in this campaign.

Reproduce the grouped checks with the nine `b5-decomp/tests/run_*debug_menu.py`
/ `run_sound_statistics_batch*.py` runners listed above. Shared native cases are
`tools/tests/cases/debug_menu_sound_batch.ps1` and
`tools/tests/cases/debug_menu_markedman_takedown.ps1`. Detailed original-address
maps, PCM measurements, review packets and timing audit are under
`scratch/DEBUG_MENU_1011/sound_batch/`; the committed batch manifest records
reviewed site IDs independently of final verdicts.
