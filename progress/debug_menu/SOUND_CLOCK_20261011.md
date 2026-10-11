# Sound statistics clock and history follow-up

Source commit: `b5-decomp 90ba951a`. This follows the [137-site Sound batch](SOUND_BATCH_20261011.md).
The original statistics display, reset and mixer-graph entries now have their
shared clock dependency corrected and a focused native witness.

## Original contract and correction

ARTIST GetCpuCycle @82B64558 is `mftb; blr`. Original QPC @82926EC8 reads the same
counter, and EA::Jobs::TicksToSeconds @82BC9988 divides by **49,875,000**.
Mixer, command/timer/voice profiling and the load balancer use these units.
The PC leaf instead returned raw RDTSC, inflating every duration passed to the
unchanged original coefficients. The earlier native capture showed Mixer
633.239 current / 281.193 average / 1363.280 maximum and an offscreen graph.

System.cpp's genuine PC adapter now returns
`floor(QPC * 49,875,000 / QPF) modulo 2^32`. Whole-second reduction and a 128-bit
fraction product prevent overflow. The original u32 wrap domain, statistics
coefficient 0.000375 and balancer factor/budget stay intact. All six direct
consumer translation units were checked for a consistent counter domain.

## Validation

- Independent combined reviewer: VERDICT pass; all three source/test hashes
  match the review packet. Canonical TU compile and faithfulness gates pass.
- `b5-decomp/tests/run_rw_audio_core_clock_rate_regression.py`: **18/18**.
  An independent GetTickCount64 wall-time check allows 4% for its coarse clock;
  17 arbitrary-precision oracles cover rounding, long uptime, overflow and wrap.
  The old production leaf completes but fails the independent rate check at
  about 2.436 GHz. The corrected sample is about 50.413 MHz within that allowance.
  This measures the clock contract; it is not a game performance benchmark.
- Canonical shipping compile/link driver: 2,950 units, one compiled and 2,949
  reused, no warnings/errors. The normal executable was initially running, so
  only the RSP output target was changed to a separate frozen file, with the
  same source list, object cache, flags and link inputs under the normal locks.
  After the user stopped the game, its exe/map/cgsmap/provenance were copied to
  the normal game path under the locks. No process was killed to permit linking.
- Actual executable SHA256:
  `e9f93ddc67f5d314c3cf4ef29c1fef57fd380173f3e09d6104abe14d4e8a21bb`.
  Build provenance is e6aac121 + reviewed System.cpp delta. Its source hash is
  `040f3536a349ec827e2f4c2b001b90d6cce1d384db8b69f5a77e1a2dcdf61fd9`.
  Later unreviewed traffic work was excluded from this frozen build.

Native run: `scratch/bugtest/runs/debug_menu_sound_clock/20261011_203720`,
slot 16, copied DISCO profile, **5/5**, zero asserts/exceptions, flow exit 0.
The real console sets screen on, graph on, holds reset, releases it, then hides
both. Fifteen saved-cell checks match. Five phase captures were inspected:

| Capture | Observed behavior |
| --- | --- |
| statistics.bmp | Live memory/object rows; Mixer 5.635 / 6.172 / 21.041 |
| graph.bmp | Visible history curve near the original y=700 baseline; Mixer 8.540 / 5.662 / 24.662 |
| held-reset.bmp | History mostly cleared; Mixer average 0.191, maximum 10.990; PPU maximum falls from 65.274 to 0.410 |
| refilled.bmp | History fills again; Mixer 12.262 / 5.835 / 17.289 |
| hidden.bmp | Statistics and graph are both absent |

Update resets and RenderHUD samples are separate original stages: held reset
need not show a permanently zero current value or exactly one render sample.
Memory/object high-water marks survive, as the original code requires. The
case's initial Teleport option was ignored because driving was not armed; the
published case omits that ineffective option and makes no placement claim.

## Supported dispositions

Original DebugComponent::OnActivate sites #0132 Main Screen Turn On, #0133 Main
Screen Reset and #0134 Draw Mixer Graph are verified. Together with the earlier
four Sound sites, four Marked Man tunables and vulnerability path, this brings
the campaign to **25 verified, two original no-ops and 1,327 pending static sites**.
The large batch's source-reviewed set remains 145 sites; clock follow-up sites
are a subset, not additional source coverage. No timing result is a general
performance, audible-output or all-Sound-behaviors certification.

Reproducible native case: `tools/tests/cases/debug_menu_sound_clock.ps1`.
Original producer audit, source review, regression logs, build snapshot and frozen
output are under `scratch/DEBUG_MENU_1011/sound_batch/validation/`.
