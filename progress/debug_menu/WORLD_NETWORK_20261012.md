# World, AI and network debug recovery

The130-site source/audit cohort is frozen ated232a94 on
`codex/debug-menu-world-network130`. Its42 owned source files include22 changed
paths;29 registrations were recovered and101 existing sites were audited.
The original packet and all seven subgroup packets remain immutable under
`scratch/DEBUG_MENU_1011/recovery_lanes/world_network_20261012`.

Root's separate `codex/debug-menu-world130-compile-repairs` branch is pushed
at8fc5f2ec. Two new renderers initially failed the canonical compile gate because
their packed colour arguments did not match the typed renderer and a local
vector helper collided with ADL. Those corrections compile. The independent
review also found a Boost callback writing chain size instead of boost level,
and destruction missing its owner assertion/null store; both are repaired.
All20 owned production TUs now compile with zero new faithfulness findings.

The one combined source review is complete: VERDICT fail, with17 actionable
findings across Boost, Reset, Collision, Prop, Trigger, RaceBalancing and the
owned WorldEntity consumer. Report SHA-256 is
07080c78e5c528a74011c7c0126def0585655c2cdf4e88f307bfe5455ce75d03.
All17 findings now have source candidates. The first16 candidates at8c153373
compile in8 affected TUs and satisfy the same reviewer's provisional source
counterexamples. The8fc5f2ec increment restores loaded-cell quads, used-slot
prop markers and the final player marker, plus the VMX projector and the original
cell-ID helper call shape/assertions/low-halfword division. Its3 affected TUs
compile with zero new faithfulness findings. Grouped regression checks and the
final combined repair review then followed. The same independent reviewer now
passes all17 findings at6231f3d8; report SHA-256 is
ac33f23e01bcbd7fdaee743fb2856b2a097156bf23e226f7469e2aa63711ad62.
The34 focused checks pass; compile-cleanad62bcf8 fails24 of the same34.
World130 and the reviewed GameState chain are integrated through0a42189ca.
The shipping source list now mounts five missing consumers, the TriggerQuery
forward class-key matches its canonical definition, and the original surface
getter/typed track-data access chain link. The normal2962-TU build passes.
These narrow link followups are separately original-backed; the frozen source
review does not retrospectively cover new lines. World130 joins the1,072 primary
packet union. Native dispositions and the listed implementation gaps remain pending.
Known unclassified flag readers, startup initializer reachability, collision
render traversal and shared PC backends remain explicitly open in the packet.

Integrated0a42189ca also passes the140-second fresh-boot baseline (driving,
throttle,1662.8m motion; zero asserts/exceptions). The shorter50-second attempt
timed out at the opening flyby before throttle. This checks baseline integration
only and closes none of the listed per-control/query implementation gaps.
