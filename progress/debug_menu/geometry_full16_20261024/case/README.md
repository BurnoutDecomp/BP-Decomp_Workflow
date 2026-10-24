# Triangle collision and Scene Sweeper case packet

This is a source-only proposal for the 16 registered controls enumerated in `CASE_PLAN.json`: 13 TriangleCollision controls and 3 SceneSweeper controls. It contains one same-process native case. The case activates `Collision` and `Scene sweeper` once, runs the actual typed-owner preflight before the first site action, and drives 48 explicit positive/negative/restore states through the original debug alias setter.

This packet preserves exact36ae preimages; it does not claim the shared B5 checkout or normal executable still match them. Root should re-anchor and compose the three-file patch onto the current dev source while preserving intervening changes, then refresh the candidate/source bindings and host-build receipt for that composite. The original hosted run401033 base executable was SHA256 `6950637c5d3098d41a784701c5d35cf8cded1e1eb0328eb09cd65bd9d97ece5b`; it does not contain the proposed probes and is rejected by the case. The staged executable must be the new hosted build whose receipt binds the exact final patch hash in `source/BINDINGS.json`.

## Evidence gates

- TriangleCollision sites run only after its actual `RenderWorld` dispatch reports at least one live spatial-map soup list. If the map remains empty, those 13 sites are deferred without input.
- SceneSweeper dynamic boxes require `dynamic_intervals > 0`; frozen boxes require `inactive_intervals > 0`; distance requires at least one of the two typed lists. Missing data defers only the dependent site.
- The 16 controls are aliased with names under 9 characters. `component` and `alias` are the original console commands; every step uses `set "Alias" value` followed by an actual alias readback.
- The swept-sphere test is enabled once only after the soup gate. The original lazy source position is captured from the first real component render and retained through field tests. It is not reset to a fabricated zero state.
- Every baseline, support, positive, negative and restore state gets one fresh back-buffer request after the typed owner reports that render state. The new request-only writer requires the exact game PID and positive private slot, uses the existing BMP path, and stops at96 captures. If all owner gates pass, the schedule requests51 images; deferred sites issue no image request. The case launches one game with a240-second cap.
- The machine checker leaves every executed site `awaiting Root visual review`. It cannot assign inventory status. Root supplies `root-visual-judgment.json` only after comparing the captured positive, negative and restore images.

## Root execution order

1. Use `source/BINDINGS.json` to compare each preimage with the current candidate. Preserve current dev changes while composing the exact owner probes and request-only writer; refresh `CASE_SOURCE_BINDINGS.json` and `CASE_PLAN.json` only after the composite is reviewed. Request a hosted build; do not use a local compiler. Confirm the new executable differs from the base 6950… image and the hosted receipt names the final patch hash.
2. Fill `BINDING.json`, `STAGING.json`, and `ROOT_PRELAUNCH_REVIEW.json` from the templates. Create a fresh private slot and private `stage/slot` plus `stage/data`. Keep normal profile/config/source paths pinned and unchanged.
3. Run `Run.proposed.ps1` once. It refuses an already-running game, checks normal protected paths and physical source/index state, verifies the private image and its receipt, then launches only `Case.proposed.ps1` with the strict `run_case.ps1` harness.
4. Review `run_full16_*/geometry-witnesses.json`, `geometry-keys.log`, and each named frame. If any required owner gate was absent, those sites remain deferred. Write a root judgment bound to the evidence-manifest SHA only for sites whose distinct visuals and restore state are visible.

No source, index, ref, normal profile, save, build, test, CI or game state was changed while authoring this packet. No case was launched here.
