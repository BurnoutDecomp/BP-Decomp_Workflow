# Preparation note — F1

The correction is bound to source7854e7fdd8b7c659d1b25d015c1321f0297df304 / workflow1a998f007d13d151b22440675b4c94be2c8fa10d. Root reported that the final FS review has F1 as its sole changed-path blocker and authorized sealing. `REPORT.md` is the final correction summary.

The recovery incorrectly mapped ARTIST82903664's single `stb r29,0x6C00(r30)` to `muNumUsedReadStreams`. DWARF CgsFileSystem.h252–255 and the complete surrounding ARTIST member/buffer/stream offsets identify the byte as `mbPrepared`. The original four-input Construct must assign `mbPrepared=false`; this delta removes the incorrect count store. It does not retain both stores.

The native no-argument Construct and every other source byte remain exact. No native counter/reset policy, activation, build, test or game action is included. The earlier16-path packet remains immutable and its report's stream-count interpretation is superseded by this finding and forthcoming correction.
