# F1 correction

The original four-input `FileSystem::Construct` now assigns **mbPrepared=false**, replacing the erroneous `muNumUsedReadStreams=0`. ARTIST82903664 stores one zero byte at+0x6C00; full array/stream offsets and DecFIGS fields252–255 identify mbPrepared. The later u32 count is at+0x9908. The proposal adds only the correct store.

Exact source base7854e7fdd8b7c659d1b25d015c1321f0297df304 / workflow1a998f007d13d151b22440675b4c94be2c8fa10d. One line in one path changes. Whole-TU reversal reproduces the Git preimage; native no-argument Construct and every other body remain byte-identical.

Root reported F1 as the final FS review's sole changed-path blocker. This correction still awaits fresh review; no compilation, tests, activation or native run occurred. The earlier16-path packet and its mistaken count interpretation remain immutable; this packet supersedes that interpretation. Existing mount, allocator-lifetime and later lifecycle limits remain explicit.
