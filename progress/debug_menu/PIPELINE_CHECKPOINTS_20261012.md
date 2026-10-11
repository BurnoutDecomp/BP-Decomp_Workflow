# Continuous recovery checkpoints

Source branches are pushed before full-page validation. These are recoverable
checkpoints, not final gameplay verdicts.

| b5 commit | Separate branch | Recovered source | Pending |
| --- | --- | --- | --- |
| e334f93f | codex/debug-menu-traffic-physical-route-150 | 150 sites; 59 production paths; source review and737 grouped checks pass | Full native consumer/phase pixel proof |
| 829e1d44 | codex/debug-menu-vehicle-deformation-131 | In-air storage/consumer | Remaining page and checks |
| 4be7f005 | codex/debug-menu-vehicle-deformation-131 | 83 VehicleManager registrations; contact, wheelie, acceleration and crash-clamp consumers | Deformation audit, compile, source review, native checks |
| 7ba57f72 | codex/debug-menu-environment-148 | 51 Graphics registrations, owner construction, corona and threshold consumers | Prepare registration, GPU/query backend, Environment audit and checks |

The134 new bindings are committed source work with incomplete consumer/lifecycle
audits. They are not added to the310 fully source-covered campaign sites yet.
The active two page lanes and Sol preparation-chain lane continue recovery while
root integrates and validates earlier batches. See recovery_queue.json for state.
