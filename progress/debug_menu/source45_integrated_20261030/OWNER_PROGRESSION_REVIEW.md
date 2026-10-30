The current PC source ignores Progression's “Set Game Mode Type” control (#0019) when building the preset-race list, recording a newly discovered event's mode, presenting junction event information, and starting the event. This candidate reconnects those four reads to the existing registered field. Value 6 keeps the authored mode; values 0–5 override it, exactly as ARTIST does.

Base: B5 `d85e2d5e2526783406d69fedc0ab17b219eb69bc`. All work is contained in this packet. No shared source, ledger, branch, build configuration, game, or profile/config files were changed.

The earlier `swarm_progression_debug_controls_11_18_recovery_20261029` directory contains an older source pin and snapshots, with no patch/reviewer packet present at inspection. Its source bodies and pin were read before tracing the distinct tail sites. The exact requested inventory rows are in `entries_0019_0023.json`.

| ARTIST function | Read / decision / mapping instructions | Current omitted PC binding |
| --- | --- | --- |
| `GameStateModule::SendSpecificPreSetRacesModesAction`, `0x8236B6C0` | `0x8236B924`–`0x8236B940` | `GameStateModule_SendSpecificPreSetRacesModes.cpp`, offline preset filtering |
| `GameStateModule::CheckIfPlayerIsAtJunctionWithAnEvent`, `0x82390418` | `0x82390758`–`0x82390780` | `GameStateModule_gSR_00.cpp`, discovery counter |
| same function | `0x82390AB0`–`0x82390AC8` | same TU, junction action's runtime mode |
| `GameStateModule::StartModeAtLights`, `0x82396CF8` | `0x82396F08`–`0x82396F20` | same TU, runtime mode passed into event start |

ARTIST's load is manager+133052, matching the by-value debug component at manager+133000 and `meDebugGameModeType` at component+52. `OnActivate` at `0x823A0950`–`0x823A0988` registers that word, range 0–6 and its option table. `Construct` at `0x82371A30` seeds it to 6 and names option 6 `DISABLED`. The consumer instructions compare exactly against 6, conditionally load the authored mode byte, then call `ProgressionManager::GetEvent`. The original exports are copied unchanged under `evidence/artist/`.

The patch uses named fields. DecFIGS supplies only the declaration shape: `RaceEventData::EModeType ProgressionManager::GetGameModeForEvent(const RaceEventData*) const` (`BrnProgressionManager.h:592`) and the existing debug field's name/type (`BrnProgressionDebugComponent.h:304`). The getter is inline in the owning manager header; friendship permits its direct field read. No state or validation was added. The existing null guards and other behavior in the consumer bodies were left in place. The central `GameStateModule.h` and IO headers were not changed. Root confirmed these two consumer TUs were unowned before candidate construction.

For #0020–#0023, the inspected callback/entry bodies already match their ARTIST control flow, counts, and stores; no correction was made to them:

- #0020: callback `0x8237E908` → `UnlockAllCars` `0x8237E790`: livery 3/4, unlock type 4, mark sequence shown, add absent parent. `UnlockGiftCarsUpToRank` `0x8237E690` uses rank range `[1, rank-1)`, gift type 1, deformation 0.85.
- #0021: callback `0x8239E4D8` → `GetToOneWinBelowBurnoutLicense` `0x8239E418`: rank 4, race/road-rage/marked-man/stunt counts 14/10/10/5, reset knobs, unlock gifts through rank 4.
- #0022: callback `0x8239E4D0` → `GetToOneWinBelowEliteLicense` `0x8239E300`: rank 5, counts 39/16/15/14/35, reset knobs, gift rank 5, mark all profile events discovered.
- #0023: callback `0x8239E4C8` → `GetToOneWinBelowEliteLicenseBR` `0x8239E1E8`: same shape with counts 40/16/15/14/34.

Validation:

- `compile/result.json`: both modified real consumer TUs compile successfully, plus the unchanged `BrnProgressionDebugComponent.cpp` against the changed headers. `compile_owners.py` uses canonical `msvc_flags.txt` and `msvc_includes.txt`; overlay headers precede shared includes, and the original Progression quote-include directory is appended to reproduce relative header lookup. Outputs stay in `compile/`. All three final exit codes are 0.
- `control/result.json`: the exact candidate getter and four exact consumer expressions are extracted into a small hosted facade. The 6 authored modes × 7 debug values × 4 reads give 168 passing cases. All four variants that restore one original omission compile and fail, with 36 failures each. The check also requires zero authored-mode reads while an override is active and one read when disabled. The unchanged mapper's ARTIST table is 0/3/7/8/5/4 (`0x82359850` export).
- `git -C b5-decomp apply --check ../scratch/DEBUG_MENU_1011/fleet_refill_20261029/progression_tail/candidate.patch`: pass. The patch and after snapshots use LF. `PRE_PIN.json` holds exact Git blobs and live-source checks; `POST_PIN.json` holds after/patch hashes; `FINAL_CHECK.json` confirms shared files still match the pre-pin.

Limits: the hosted facade isolates the changed expressions and getter; it does not instantiate or link the production manager, execute the complete GameState functions, exercise debug UI dispatch, or validate native gameplay. The actual owner compile checks type/header integration separately. #0020–#0023 are direct source comparisons, not new end-to-end behavior dispositions. No Scoring/CPU body was edited. No child reviewer agent was spawned; this packet awaits the parent's independent review. No public patch application, commit, ledger change, full build, or native run occurred.

Review entry points: `candidate.patch`, `PRE_PIN.json`, `POST_PIN.json`, the original exports above, `compile/result.json`, and `control/result.json`. Reproduce with `python compile_owners.py` and `python verify_omission.py` from this directory.
