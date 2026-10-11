# Online debug spawn and dormant ram controls

`Force Online Freeburn Spawn Position` now reaches both original lobby consumers.
Previously both read constant false, and the menu row was read-only. The default
retains a same-model local lobby car at its current pose; true forces a respawn at
the original table entry for the player's grid row. Model changes, non-lobby grids
and remote-car origin behavior are unchanged.

`Apply Ram` and `Magnitude` are restored as **original no-ops**. The original
callback's only side effect is latching `mbAirRam`; Magnitude stores `mMag` in its
original range 0..100. ARTIST has no engine consumer for either field. Adding a
physics ram here would invent behavior, so the obsolete effect is not revived.

## Console evidence

- `OnActivate` @822C2538 registers the callback and float, sets range 0..100, and
  registers the writable forced-spawn bool.
- `AirRamAddNew` @822A79A8 is `li 1; stb @+0x15; blr`. Magnitude is component
  +0x24. Their module offsets are +0x17D05 and +0x17D14.
- All original component helper/virtual bodies were inspected. The module's
  embedded-component pointer escapes go to construction, registration, teardown
  and reset-history producers. No direct consumer of the two dormant fields was
  found in the ARTIST exports. A fresh reviewer independently checked this scan
  and the component bodies. Existing physics ram producers elsewhere are separate.
- `HandlePrepareForModeAction` @823092F0, @82309704..82309720 reads the force bool
  at module +0x17D06 and ORs it into the local respawn decision.
- `AddRaceCarToStartingGridOrFreeburnLobby` @82300B38, @82300E08..82300E24 reads
  the same bool to select the original table position for a local lobby car.
- DecFIGS declares `mbAirRam` and `mMag`; the forced-spawn field is ARTIST-only,
  attested by its Construct, registration and two readers.

## Validation

`run_race_car_debug_spawn.py` reads production consumers and the real callback.
Before repair it passes **10/16**; afterward **16/16**. It covers both settings,
model-change/non-lobby behavior, roster-row selection, local/remote transforms,
original table landmarks, registration/range and repeated flag latching.

Compile/selfcheck, faithfulness and the canonical 2,949-TU shipping-driver link
pass. The executable **be683ae1c6e6** was linked to an isolated output because the
main game executable was in use. One combined fresh-eyes review passes; no whole
race-car TU parity claim is made.

The final case uses a copied `DISCO_collect_base.sav` (SHA1 prefix
`1AC773F168B3`) in private slot 16, real COMPONENT/SET/CALL/SAVE commands and F2.
An existing LAN-host harness starts original mode 15; no external game service or
second player is required. Controls are restored after the mode transition.

| Run under `scratch/bugtest/runs/debug_menu_racecar_spawn/` | Result |
| --- | --- |
| `20261011_155513` | Forced true: **9/9**, zero asserts/exceptions; respawn=1, selected `(3008.17,-1.16,-1874.3)`, player physics within **0.0201 m** in XZ. |
| `20261011_155750` | Default false: **9/9**, zero asserts/exceptions; respawn=0, current pose retained, player physics within **0.0196 m** of it in XZ. |
| `20261011_155127` | Prior executable **9c24d98e4a91**: **3/8**, real console sequence completes but toggle is read-only, Magnitude is missing, callbacks do not run and requested true still yields respawn=0. |

The first negative fixture omitted Drive, so its teleport did not fire; it is
credited for missing controls/respawn decision only. The corrected positive runs
include a one-second setup pulse and use actual physics samples as their placement
witness. Their GAS/DRIVE summary is not a driving pass: gas stayed zero. These are
control and placement checks, not driving/performance or complete online-parity
claims.

`BRN_RACECAR_RAM_TRACE` is a passive callback witness capped at four lines. The
spawn witness uses the existing bounded LAN observer. Original method/member
inspection is retained locally in `scratch/DEBUG_MENU_1011/`.

Seven registration sites are verified and two are original no-ops. The remaining
1,345 original sites, dynamic rows and native additions still need dispositions.

Implementation published as b5-decomp commit `691e56ec`.
