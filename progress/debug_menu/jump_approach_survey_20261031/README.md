# Jump approach: measured scene limitation

The corrected reverse approach passes the physical road-seat check, but the car falls from road height 12.85 to ground 0.15 before reaching original jump 355882 / region 4413 (centre height 20.007740). A genuine 0.866666 s flight is observed; the required original region latch / action 56 / director jump gate / jump-completed chain is absent. The enabled camera is therefore still untested. No original no-op is inferred.

A single private returning-save run then collected 48 zero-speed placements: 24 X/Z points on the reverse approach at two requested heights. All 48 seat receipts and exact owned phase/cleanup/profile restoration passed, with one bounded original frame and normal files unchanged. No sampled placement reached height 18; the highest result was 14.609 m and had a large placement offset, so it is not an accepted launch. These are terrain observations, not camera or physics-parity proof.

Next: identify the actual route to the elevated trigger, including whether road-only placement snaps beneath an upper non-road surface. Avoid repeating blind jump boots or manufacturing events. The other three backward NO_CUTS records are one-way; the current 68-record asset has no NORMAL camera-type direction. The existing direction and original action gates are retained.

The preparation fixes close real false-success paths: exact PhaseDone/owner/start binding, helper cleanup and profile restoration are required. Tests cover 12 positive/rejection cases. Both prior failed reviews and the subsequent preparation pass are preserved in the original archive. No production source or normal game files changed in this step. [Trajectory](TRAJECTORY_FINDING.json), [survey result](SURVEY_RESULT.json), [archive](ARCHIVE.json).
