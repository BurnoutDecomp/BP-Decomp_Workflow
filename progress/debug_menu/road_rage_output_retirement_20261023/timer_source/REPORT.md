# Road Rage3380 /455m26s: timer source supplement

CONCLUSION: retained takedown replay is sufficient at source level to explain both extreme screenshot values. The earlier Gold/expiry conditions do not bound extensions at the displayed30-takedown goal in this host path. No additional concrete timer request-retirement or GUI-delta defect was found in the inspected chain. A repaired native timer has not been demonstrated.

This report supplements the earlier sealed timer/lifetime triage and leaves the accepted one-call retirement source-review pass intact. It audits candidate `3966e936bbc7a4c16afe7ec48527ccf7dab90758` **before** that delta, and compares the relevant path with installed91a and the Oct9 temporal baseline. The screenshot values3380 current takedowns,30 target, TIME455m26s were transcribed by the parent from the new user image; this subagent did not inspect the pixels. No current-session log or elapsed-clock sample was supplied.

## Why the Gold guard does not stop these extensions

1. SetupGameMode seeds RR medal targetGOLD0, achievedNONE3, and the three authored target scores (`BrnModeManager_Prepare.cpp:408..414`). It also explicitly sets `mauiMedalScores[3]=0xFFFFFFFFu` at427.
2. At the actual timer-start latch, UpdateCurrentMode stores current sim time as start, clears the request, calls StartPlayingMode, and for RR calls SetTimeLimitSeconds (`BrnModeManager_UpdateMode.cpp:429..457`). SetTimeLimitSeconds **resets target and achieved toNONE3** (`BrnScoringSystem_Timer.cpp:111..112`). ARTIST0x82310888..0x8231089C also stores literal3 to both fields. This is not a missing reconstruction-only store or an incorrect omission of the earlierGOLD seed.
3. CheckRoadRageMedalAwarded compares the unsigned takedown count with `mauiMedalScores[meCurrentMedalTarget]` (`BrnScoringSystem_UpdateB.cpp:146..174`). ARTIST0x82312864..0x82312878 uses the current-target index and unsigned `cmplw`; it does not unconditionally compare with score0. With current targetNONE and thresholdUINT_MAX,3380 cannot enter the award block. Achieved staysNONE and the separate RoadRageModeScoring target stays30.
4. IncrementPlayerNumTakedowns tests achieved==GOLD **after incrementing its count**. NONE passes that gate, as does every realistic count belowUINT_MAX in the medal check. The prepared extension trigger is1. Each accepted callback therefore adds configured5 seconds +3 cover seconds to the deadline (`BrnRoadRageModeScoring.cpp:208..230`). Its two action255 posts are display notifications; the deadline is increased once per callback, not twice.

Thus the previous statement “if Gold is already achieved, extension returns” remains true, but treating the visible goal30 as proof that this condition will become true was unsupported. This supplement supplies the missing state-order check.

The UINT_MAX write is an explicit **pre-existing PC deviation**, introduced by `4828d2bc9c224feca4b2c6db372cc9977cb45ce1` on Sep3, before the debug-recovery campaign. Its nearby comment asserts native heap residue is large; absence of a native explicit initializer alone does not prove the runtime residue's value, so this report does not adopt that claim as a retail runtime fact. The two originalNONE stores and the current-target comparison are directly supported by assembly. No exact additional “force Gold at30” correction follows from that assembly. Changing those original stores or removing the existing sentinel would be a separate semantic change, not the lifecycle repair under review.

## Numerical consistency with the screenshot

The current local `build/game/PROGRESSION.DAT` was read without executing the game or the transcoder. Its bnd2 header, entry fields and serialised rank table were decoded according to the existing transcoder and the owning ProgressionData/ProgressionRankData declarations. No live memory offsets were guessed.

Asset SHA-256: `6ded91c1051738479f6087e0e38390e9042d357d795bebfb0a11a2d6c58dba56` (56704 bytes). It is platform4/version43 with six112-byte rank records. All six have extension5 seconds; targets are3/6/10/15/20/30 and initial durations180/210/240/270/300/330 seconds. The source Prepare uses trigger1, independently of the unused authored trigger-data word5.

For the default target30 rank, if the screenshot's count and remaining time are from the same normal mode snapshot:

```
initial deadline duration       = 330 s
3380 credited callbacks * 8 s  = 27040 s
extended duration              = 27370 s
455m26s displayed               = 27326 whole seconds remaining
implied elapsed simulation time = greater than43 and at most44 seconds
```

The interval follows the HUD's truncating `%dm%02ds` display of the remaining f32 value. Approximately44 simulation seconds is numerically sufficient; no timestamp-as-delta or multi-hour initial limit is needed. Slow motion/pause can make wall-clock time differ from this simulation-time interval.

This is a consistency result, not a reconstruction of the actual session: its loaded asset, start duration, harness environment and elapsed time are not independently captured. `SCREENSHOT_MODEL.json` includes every extracted rank and the arithmetic inputs. The data bytes and reader-source declarations are sealed here so the calculation is reviewable.

## Active timer request/status lifetime

Candidate3966 contains the same relevant scorer/timer bodies as installed91a. Its exact full GameModule preimage is `cdde690ad876bab5cb5f6231be631869d685166aedb876cbdca7b996a17c1d62`, matching the approved delta's3966 preimage.

| Boundary | Candidate3966 evidence | Result |
|---|---|---|
| Substep accumulator reset and status snapshot | GameMain calls BridgeTimers before input/state/world. BridgeTimers clears mTimerRequestInterface then StoreTimers (`BrnGameModule.cpp:2255..2265`). ARTIST0x823BD198..0x823BD1A8 matches. | Requests do not retain prior-step flags. |
| Director request | Fresh per-step Director output, plus pre-GUI clear before MainDirector update (`:2977..2982`). | Starts empty for the current producer. |
| Request merge/apply | UpdateTimers reads GS and Director request interfaces under read locks, merges them once, applies start/stop/scale, then updates both live timers (`:2099..2150`). ARTIST0x823BCFD0 and0x828D7468 corroborate the flags/scale path. | These requests do not add seconds to the scoring deadline. |
| Persistent GS request retirement | Existing final write lock clears GetTimerRequestInterface at`:5079`, after UpdateTimers5045. | The GS timer-request lifetime already retires; it is not the omitted TD output queue. |
| Reply/status value | StoreTimers copies game/sim clock status, and full PreWorld/EMM copies it to the module/ModeManager. | The selected path uses typed snapshots, not a retained timer-reply queue that increments the RR deadline. |
| Old path | Baseline GameMain also resets/snapshots before its extracted adapter, drains UpdateTimers once late, and clears GS requests. Its TakedownPreWorldLeg additionally clears the TD output. | The regression transition lost the TD clear, not this timer-request reset. |

Timer::Update advances its integer-seconds/fraction accumulator by rate*scale when running. Even a wrong scale request would change elapsed simulation time; it would not produce the exact+8 seconds per accepted callback that the screenshot supports. No second unretired timer request or reply object was found in this bounded path.

## StartEvent, duration and GUI delta

StartEvent is a harness/input-routing label, not a separate C++ RR clock owner. The checked-out flow_run StartEvent flag sets BRN_START_EVENT; the old adapter's one-shot helper calls StartModeAtLights and bypasses the0.35-second input hold. It does not add or repeatedly reset the scoring deadline. That adapter is not the selected full GameMain pre-world path. The parent's separately composed normal input route still reaches the same mode setup/start-latch logic.

The relevant start-time/duration gate is the one-shot timer-start request above: it is cleared before leaving the arm. ModeManager caches `GameModeParams::mfModeTimeLimit`; RoadRageMode::Start sets it from the rank's u16 duration. No minimum-time harness setting is required to get455m26s. There is an existing opt-in `BRN_LOSE_TIME_LIMIT` override in UpdateCurrentMode513..542: if explicitly set to a positive value it replaces the RR initial duration once at start. It is not evidence that such an override was active for this normal user session, and it is not a repeated extension mechanism.

GUI event26 is `{f32 delta, f32 now}`. BridgeGameStateToGui emits game timer base*scale as delta and seconds+fraction as now; ARTIST0x823EF2C0..0x823EF300 has the same order. GuiCache::RecTimeInfo latches the two named values. No absolute-time/delta interchange was found.

Most importantly, the RR TIME field does not integrate GUI delta: its event424 carries max(scoring deadline-sim now,0), GuiCache stores that event time, and EventInfoComponent::UpdateRoadRage formats it directly. Repeated event424 delivery alone overwrites with the same remaining value; it does not accumulate. The actual deadline increases on repeated accepted takedown callbacks before publication.

## Repair implication and remaining witness

The missing persistent TD-output retirement is the additional per-step replay defect already identified and addressed by the accepted one-call delta. That single correction removes the repeated callback source for **both** counter and extension inflation. The new source evidence supports sufficiency of that repair mechanism; it does not certify the resulting native timer.

A fresh-mode witness must observe both outcomes: one accepted takedown gives one count increment and one deadline increase of8 seconds for this data, then with no new takedown, count stays fixed while the displayed timer follows elapsed simulation time. Correct pause/slow-motion behavior must be judged in that same time domain. An already inflated live mode is not retroactively restored by clearing a queue. No such run was performed here; root owns the authorized validation.

## Pins and boundary

SOURCE_BINDINGS.json binds35 whole candidate3966 postimages to git blobs/SHA-256 and compares each with installed91a and the Oct9 baseline. All relevant ModeManager/scorer files are unchanged between91a and3966. EXPORT_BINDINGS.json binds11 existing ARTIST exports. The Sep3 sentinel introduction, selected history diff, three baseline whole files, checked-out harness sources, serialised data and decoder-source file are retained. This is a bounded source/data audit, not whole-game or native original-behavior credit.

No production file, prior sealed packet, refs/index/Git state, build, test, fixture, game, CI, or IDA worker was changed or executed. Python performed only static reads, decoding, arithmetic and hashing plus writes inside this new sibling packet. No new production correction is introduced by this report.
