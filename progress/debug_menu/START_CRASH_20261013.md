# Start crash with vehicle INI settings

The normal executable is rebuilt at `41afefeab`. Pressing Start with configured
vehicle LODs had activated the Race Car debug page during loading. Its original
Update then read velocity through an invalid/unattached player slot. The supplied
log identifies that exact call chain and a null read at address `0x50`.

The PC INI adapter now tracks the activation origin outside engine objects.
Its Race Car frame/overlay calls wait for a valid attached player; registration
and settings remain available. Explicit component commands and ordinary
navigation into the materialized page or its children transfer to normal menu
activation. Original engine object layouts and the original velocity calculation
are retained.

The copied configuration also exposed an INI lookup mismatch. Actual grouped
registrations include `Race Car Entity/`, while the absolute vehicle keys only
triggered page activation. The PC adapter now resolves that exact alias, with an
explicit full menu key taking precedence. It preserves the original menu paths.

The normal 2,967-TU build passes. At `3d3ce67d7`, the copied-user-config native
case passes all nine checks: driving, throttle, 2,736.9 m before the first respawn,
all five configured LODs applied, zero asserts and exceptions. The earlier
`2f15d6683` run drove successfully but failed the LOD-application check; it is
retained as an intermediate failure. The latest `41afefeab` menu handoff passes
24 complete-method checks; the old Open body fails two. Existing activation and
Variable/INI groups pass 41 and 82 checks respectively. The exact latest-build
native run at `41afefeab` also passes all nine checks: 2,184.9 m, all five LOD
overrides applied, zero asserts/exceptions. The combined independent source
review passes both repairs and the supporting texture chain; report SHA256:
`762699a24d06de6a0b52bad9fc74e32c22272b60a8353289ef1d884541f168c9`.
Native manual-menu traversal and complete diagnostic/Texture Window behavior
remain outside this startup verdict.

The earlier isolated baseline did not copy `config.ini`. The new regression
case explicitly copies it into its isolated slot, records the used bytes, and
checks actual settings application. The normal configuration/profile is not
used as a writable fixture. Run with an isolated slot:

`powershell -NoProfile -ExecutionPolicy Bypass -File tools/tests/run_case.ps1 -Case debug_ini_vehicle_startup -Slot 23`

The case requires the five vehicle LOD overrides in the source configuration.
The [portable receipt](start_crash_20261013.json) records exact artifact hashes
and states. No debug-menu final-entry count is promoted by this startup fix.

The Resource texture-usage link dependency is also recovered: Model scans its
renderables and MaterialAssembly preserves the positively empty original state
operation, including its null-query quirk. Existing Renderable is now mounted.
Its four affected TUs compile; native Texture Window behavior remains open.
