# World, AI and network debug recovery

The130-site source/audit cohort is frozen ated232a94 on
`codex/debug-menu-world-network130`. Its42 owned source files include22 changed
paths;29 registrations were recovered and101 existing sites were audited.
The original packet and all seven subgroup packets remain immutable under
`scratch/DEBUG_MENU_1011/recovery_lanes/world_network_20261012`.

Root's separate `codex/debug-menu-world130-compile-repairs` branch is pushed
atad62bcf8. Two new renderers initially failed the canonical compile gate because
their packed colour arguments did not match the typed renderer and a local
vector helper collided with ADL. Those corrections compile. The independent
review also found a Boost callback writing chain size instead of boost level,
and destruction missing its owner assertion/null store; both are repaired.
All20 owned production TUs now compile with zero new faithfulness findings.

One combined source reviewer is still inspecting the full130-site cohort and has
additional Reset, Collision and Prop findings. These repairs are candidates,
not a source pass, linked executable or native behavior verdict. The cohort stays
outside the917 primary packet union and all its inventory entries stay pending.
Known unclassified flag readers, startup initializer reachability, collision
render traversal and shared PC backends remain explicitly open in the packet.
