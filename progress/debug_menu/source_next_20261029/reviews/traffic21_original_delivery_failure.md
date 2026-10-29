# Independent Traffic chunk21 review

VERDICT: fail

The sealed packet needs one packaging correction. The source/ABI review passes; no behavior change is requested. Scope is only `chunk21_reinsert_caller`, located without the `module_` component in the delegated path. Chunks20/22/23 were not re-reviewed.

## Finding

**[P2] Normalize changes.patch to LF and reseal before integration.** All 91 patch lines currently use CRLF, while both sealed source snapshots use LF. A plain `git apply --check changes.patch` fails against a fresh exact preimage, including with `core.autocrlf=false` or `core.whitespace=cr-at-eol`. `--ignore-space-change` passes but introduces 43 CRLF lines in Module.cpp and 2 in Vehicle.h, yielding bytes different from the sealed postimages. Converting only the patch transport CRLF to LF, then applying with `core.autocrlf=false`, produces byte-exact sealed postimages for both changed files. Evidence: `PATCH_TRANSPORT.json`, `changes.lf.patch`, `apply/`, and `raw_apply_probe/`. Regenerate the author patch with LF, update MANIFEST/SEAL, and verify its raw application; source bodies and existing source validation can remain unchanged.

## Independent source review

ARTIST complete caller `827247F0..827249F4` and the DecFIGS declaration confirm `void(this, u32 param)` (`r3=this`, `r4=param`). The two transform calls use PPC structure-return buffers and retain independent position and direction reads. Query vectors and GPR output pointers preserve position/splat20/direction/splat0.8 and hull/section/f32-along/u32-segment ordering. The u16 budget accepts 0/1, increments only after a returning query, and consumes failed/inactive attempts. Failed queries do not inspect unwritten outputs. Only the membership key narrows hull to u16; GetHull and repair retain full u32.

The success path preserves GetHull, GetSection, typed Param repair, sampling using the repaired current segment, ParamTransform pose/right/speed initialization, and Vehicle physical-time reset5.0. The sampler wrapper's output register ordering and the existing sampler/initializer bodies confirm third-vector RIGHT despite its lrUp spelling. No new alive assertion belongs in ResetPhysicalTime: ARTIST ends with a bare float store to the physical-time field. The counter reset matches the supplied original PreSceneUpdate prologue: r28=0, both IO locks, `sthx` at8274AA74, then divergence banner/state processing. Five original JSON exports equal the canonical ARTIST exports; all261 supplied raw instruction words match their accompanying asm listings (caller130, reset70, sampler61). No live IDA database was opened or altered.

The complete owning source is BrnTrafficEntityModule.cpp for caller/reset, plus the original named inline setter in BrnTrafficVehicle.h. The unchanged complete Vehicle source was compiled with the candidate header. The existing outer UpdateParams call remains present; no positive current producer of mParamsToReinsert is established.

## Packet and execution evidence

All341 MANIFEST records and the SEAL manifest hash `91747a7f26ea9fe1253dd9a23e81d16f9936268e328e879b4b9f9dc4933caf5e` verify. SOURCE_DELTA pre/post hashes verify. All259 frozen dependencies match both their recorded blob hashes and actual d1585cfbb9a99db4ee6aa8c6b2848f399cc01ad2 path-to-blob mapping. The pre Module equals chunk19's declared post context and the Param header equals the declared chunk20 context; these were dependency equality checks only. Six preexisting dependency objects match their recorded hashes.

Fresh private compilation with the packet's canonical flags/include order passed both complete pre/post Module TUs and the complete Data-query, Section, PVS, Array-short400 and Vehicle support TUs (seven exit0), then rebuilt the CPU control (exit0). The502 compiler-read paths had no fallback into shared b5-decomp/src; frozen/private source contexts supplied all source headers. The complete pre/post caller methods and frame lock/reset blocks in the control were compared directly to their sealed source extraction. The fresh executable reproduced27/27 candidate cases versus8/27 preimage cases and byte-identical sealed control output. See INDEPENDENT_RESULTS.json, INTEGRITY.json, FINAL_BINDINGS.json and independent_compile_*.log/exit.

All writes and compilation outputs were confined to this exclusive review root. The author manifest and every listed author file were re-hashed after verification and remained unchanged. No author/shared/canonical/ref/native source, state, ledger or executable was modified.

## Limits

Controlled owner/resource getters, outer PVS hull selection, IO lock recording/faults and first-assert trapping remain explicit seams. Prior dependency objects are hash-bound reused artifacts. These controls do not execute full PreSceneUpdate, module/network/streaming/PVS enumeration, renderer or native game and do not prove the missing request-list producer, whole-query numerical parity or physical Xenon arithmetic. No site/original-no-op/gameplay completion credit is granted.
