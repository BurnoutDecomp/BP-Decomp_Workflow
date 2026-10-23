# Passive occlusion probe review

Review the exact two-file diff against e306dbd2. Confirm original calls, return values,
query state transitions and draws are unchanged; logging only reads existing results.
The exact environment opt-in is BRN_OCCLUSION_DIAG=1. Output is bounded to24state,
192batch and512provider lines per process and uses existing CgsLog. Inspect all printf
formats/argument widths, render-thread ownership, short-string safety, and no extra
GPU queries/GetData calls. The counter is diagnostic and never replaces game time.

A native world11 test must show actual ended surveys, S_OK results and their same-serial
decisions, a complete contiguous >64-record query/draw walk with matching continuation,
plus source flags restored and actual world pixels. This is supporting evidence,
not blanket ten-control parity. No source production edit, build, game or test ran here.
