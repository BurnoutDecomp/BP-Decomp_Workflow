# Traffic EnterReplay successor for combined re-review

The previous combined review failed the producer packet because `EnterReplay`
omitted ARTIST's `mbReplayAssetsReady = false` store. Construct sets this readiness
flag true, so the omission bypasses the first playback streaming poll. The old
sealed producer and renderer packets remain byte-for-byte intact.

This successor restores exactly that one store in the private module CPP. It
changes no header, layout, activation policy, stream codec, or other method.
`ENTER_REPLAY.patch` applies after the original sealed producer patch. Compose
the old producer postimages, this successor postimage, and the renderer postimages.

ARTIST evidence is `evidence/EnterReplay.asm.txt`: `82708224 li r10,0`,
`82708228 ori r11,r11,0x2521`, `8270822C stbx r10,r31,r11`, after the optional
log call and before return. The recovered member at `+0x72521` is
`mbReplayAssetsReady`; the store belongs at the end of `EnterReplay`.

`fixture.py` extracts the actual successor `EnterReplay` body and compiles it
against the frozen original owner type. It enters from true twice, verifies
false on both calls, verifies false remains false, and checks the adjacent
playback sentinel stays true. Positive exits 0. A second compiling fixture omits
only the store and exits 3 at the first true-to-false check. The source is pinned
before and after both executions.

The affected full module CPP is compiled against frozen f1 dependencies with
opened-header provenance and private pre/post source pinning. `SEAL.json` replaces
only that producer module gate; the other three producer gates and the codec
checks are carried unchanged from the old seal. The renderer gate remains valid:
neither its source nor any opened header changed, and the modified module CPP is
not among its opened dependencies. The successor seal records this comparison.

Please re-review the single restored store and the new regression evidence.
All other combined leaf review passes carry forward. No game run, public source
change, executable build, installation, or native/full-traffic completion claim
is made by this packet.
