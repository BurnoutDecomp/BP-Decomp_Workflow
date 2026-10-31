# Combined fresh review packet

## Review decision

No native run has been performed and no site has credit. Review the complete SCOPE.json and the proposed runner before Root starts its private slot 62190 run.

## Inventory

Published workflow main a6e4457a6d09c4d321dc0c9b066dfd70fd0e6c7b pins entries Git blob 7d5e87f61fa33a9a100668de53079d9c92b91d4d and verdicts Git blob d2e213f3fc49223fdebfd11e5fd842ade0b3f549. The Git-content SHA-256 values are recorded in RECONCILIATION.json. All 28 candidates are present and have no verdict row. Two Director candidates were already verified and are excluded: #0021 and #0027.

## Source authority and evidence

The target code is the user-specified published B5 3f4f9c06e1a694d491effd1cbe28407ce9df1d4b. SOURCE_PINS.json includes exact blob IDs for the selected Source41 registration/consumer files and hashes for the original ARTIST evidence. The mutable RendererModule and WorldModule worktree files were not read.

The clean installed binary hash is 39b62961b59261ac8e1b9894d5a69c8ab365bf7ea39e89793d654fcf93ca47da. The packet uses the immutable build_clean artifact and records the build receipt's older workflow field.

## Controls and UI values

For Scene Manager floats, Source41 registers step sizes of 0.025 for TriX/TriY/TriZ and 0.25 for TriScale/Padding; the selected registration does not call SetRange. Defaults are TriX/TriY/TriZ 0, TriScale 1, Padding 0.3. Bool Scene Manager flags default false.

The five ShadowMap targets are bool variables with Source41 defaults true. Director bool defaults and the three clipping f32 defaults are carried from the Source41 cohort, with selected UI steps 0.01, 0.01 and 100 for E43/E44/E45. The exact selected registration body has no SetRange for these fields. The draft uses finite values within the original typed editor behavior and restores the same-run captured baseline. Scene f32 targets are skipped without mutation if the natural baseline is not the exact Source41 default; that is an unresolved baseline, not a failure.

Each target has a unique alias and raw three-command read: alias, value, alias. The log acceptance rule requires matching alias/path lines before and after the typed value.

## Required fresh review checks

- Confirm all 28 aliases, paths and raw triplets are unique and match the published entry snapshot.
- Confirm all positive/negative values are finite and follow the Source41 registration steps; no bounds are inferred where the original SetRange is absent.
- Confirm every target's consumer witness and live producer/scene gate in RUNTIME_GATES.md.
- Confirm temporary SC02, SC03, SH02, E17 and E21 context changes always restore the same-run captured value.
- Confirm the 87-frame plan stays under the whole-batch cap of 90 and the capture helper rejects any overrun.
- Confirm the profile fixture is only for a future private slot 62190 stage, and the asset identity roster remains a read-only reference.
- Reject site credit for missing geometry, missing shadow caster/receiver, inactive Director state or an unobserved consumer. A missing scene is not a no-op verdict.

## Preserved history

The first Source41 Director runner's failed profile-gate transport and the corrected run's zero-eligible/zero-setter result remain untouched and are indexed in RECONCILIATION.json. Neither is overwritten or promoted to a verdict by this prep.
Exact published-3f full-path derivations, including GetPath/GetName, MakeFullPath, and literal ShadowMap registration, are in PATH_ATTESTATION.md. CONTROL_MATRIX.md lists all 28 aliases, source defaults, probe values, UI steps, and live gates.
The fresh review should check PATH_ATTESTATION.md against the path source blobs in SOURCE_PINS.json. This path proof uses the exact current 3f component and variable-manager implementation, including the root literal-group route for ShadowMap.
