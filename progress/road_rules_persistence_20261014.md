# Road Rules persistence repair

Delivered in normal source `ac3f202d6`, executable SHA256
`6a6ff89b5e76678414dd679c9846c0c57715e7368cee2288fa7892a13c6dea5b`.

On native PC, login had no downloaded `ROAD_RULES_RESET_DATE`. The original
timestamp parser converted the empty value to the current epoch. The original
StreetManager reset policy then cleared both Road Rules score types, and a later
successful save persisted that erasure. This explains loss after hours of play.

The PC service boundary now omits the reset-info event for an absent/empty key.
Explicit `"0"`, configured dates, legitimate resets and the original score/save
formats retain their existing behavior. The policy fixture passes 31 checks;
the unchanged exact5ad control fails three preservation checks.

Two final normal-executable processes each pass 13 checks. The second cold-loads
the exact physical save produced by the first. After actual later login and
completed writes, both checksum-valid outputs retain Time3933/Silver, Driver
Details Time1/64, Showtime16550, reset epoch1791996687 and prior progression.
The scores were earned in earlier native runs, then copied unchanged as test
fixtures. A newly earned Showtime medal/Gold road is not claimed.

Ten normal user files and all four normal build artifacts retained their hashes
and modification times. The isolated slot's original lack of a profile was
restored. No save records were fabricated or written into the user's profile.

Frozen source diagnosis, original assembly, RED/GREEN runs and final delivery:

- `scratch/ROAD_RULES_1014/HANDOFF.md`
- `scratch/ROAD_RULES_1014/normal_delivery_20261014/REPORT.md`
- Final 92-artifact manifest SHA256:
  `6bb8fc6151fa18196e215439a8886b55a524a803a30e18d52d6054e90c389bba`

The broader [debug-menu campaign](debug_menu/README.md) remains incomplete.
