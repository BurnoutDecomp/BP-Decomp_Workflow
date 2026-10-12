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
final combined repair review remain pending. These are source candidates,
not a source pass, linked executable or native behavior verdict. The cohort stays
outside the917 primary packet union and all its inventory entries stay pending.
Known unclassified flag readers, startup initializer reachability, collision
render traversal and shared PC backends remain explicitly open in the packet.
