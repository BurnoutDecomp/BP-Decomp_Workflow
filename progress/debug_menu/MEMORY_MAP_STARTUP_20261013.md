# Memory map and statistics checkpoint - 2026-10-13

**Eight production files compile; independent review, integration and native
behavior remain pending. No debug-menu entry is promoted by this checkpoint.**

Sourceb020144557 restores InitMemoryMap -> FixUp -> initial default allocator ->
GameData map handoff. The native image contains all seven typed tables:16 banks,
27 pools and1/7/8/4/4 allocator rows. The five-lane ARTIST bank shape is retained.
Sourcef74822285 adds the original allocator-statistics producer/HUD chain.

The parent YAML/generator reproduces the private typed header. Compilation found
one generator bug: the initializer struct's closing `};` was missing. The repaired
generator changes no table values. Its output is saved on the validation branch
at9c6956091; a0a9454df also reuses two canonical TriggerData element includes.

Six affected files plus MemoryModule/MemoryModuleIO compile with zero new
faithfulness findings. Exact commits, output hash and compile receipts are in the
[compile checkpoint](memory_map_compile_20261013.json). The normal game source and
executable have not adopted this memory-map change yet.

PrintConsoleMemory's original filter/lines and native host memory query are saved
separately ate72b07de. DLC owner/Prepare and canonical async-file frontend work
continue on the source lane. Source review and full startup/statistics checks
remain open. Unattested map getters/FixDown are not treated as recovered functions.

Original frozen packet:
`scratch/DEBUG_MENU_1011/recovery_lanes/remaining143_20261012/evidence/memory_map_startup_checkpoint_b020144557/packet.json`.
