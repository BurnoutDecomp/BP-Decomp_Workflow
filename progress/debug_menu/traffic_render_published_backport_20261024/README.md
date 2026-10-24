# Traffic render published-fix backport

This source-only packet carries the exact one-file delta from candidate B5 `3f0227ce2bab357a86e42c0ab51aa95b5808713c` to the already-reviewed traffic render file at `656890624d6a3492c3341340da24bbb4e51fb414`. The resulting file blob is byte-identical to the same path at current reference `9503d787dafdb0ebfb126f3fa888d2249f84b6b4`. The complete patch is `source/patch.diff`; `source/pre` and `source/post` are exact `git show` snapshots.

The diff is confined to `src/GameSource/World/EntityModules/TrafficEntityModule/BrnTrafficEntityModule_Render.cpp`. It restores the already-published reflection-capture/null-shadow gate and the source's original broadcast/vector-row representation required by the repository's aggregate `rw::math::vpu` types. Those changes are the path-level content from the earlier reviewed fixes `b9c0e692bc9d8f232b9986923acf07aff26c0639` and `edca934dc502f71f64ad873cdd386afe5e3eeeb2`; they do not introduce a new renderer behavior proposal. No renderer/resource merge or unrelated source path is included.

Hosted run 40116263234 reached the full shipping compile after the selected resource/hierarchy gates passed. Its retained log reports ten unique scalar/vector type errors, all in this file around lines 1619–1652; `HOSTED_ERRORS.txt` records the exact error summary and `BINDINGS.json` binds the full original log hash. The target source snapshot is already committed at both published references, but this packet has not been built or hosted after backport. Root owns composition and validation.

No physical source, index, ref, build, test, CI, native process, or game state was changed while authoring this packet.
