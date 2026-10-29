# Traffic chunk 22 constructor policy: independent source review

VERDICT: pass

PASS covers the two exact source postimages and **reviewed-changes.patch** in this review root. The author's sealed changes.patch has CRLF context against LF Git preimages and is rejected by direct Git apply; it is preserved unchanged. The reviewer copy normalizes only patch line endings, applies exactly in an isolated index/object store, and reproduces both author postimages byte-for-byte. Use the reviewed LF patch for integration.

All 121 author manifest members and its seal/manifest hashes verify at entry and again before this seal. Both preimages exactly equal d1585cfbb9a99db4ee6aa8c6b2848f399cc01ad2 Git blobs. Executable-token comparison confirms the CPP changes only the final BaseClass::Construct argument from false to true; header executable tokens are unchanged. The rest of the diff replaces obsolete export-hole comments. No declaration, layout, callback or state-machine algorithm changes.

## Original ABI and request path

The four retained ARTIST raw windows were independently reread and match: the owner call neighborhood, complete TrafficCarStreamer constructor, complete InternalBaseStreamer constructor and complete UpdateLoading. TrafficEntityModule's direct call at 82740854 reaches 827539A0. Constructor this is r3; four storage arrays are supplied in r4-r7, length 64 in r8, pool 15 in r9 and slot-pool false in r10. Graphics asset set 0 is stored at caller SP+54; byte 1 is stored at SP+5F by 827539C4. After the base prologue subtracts 60, 827C4A80/84 reads those original slots as new SP+B4/BF; 827C4AB4 stores the latter byte as allow-failure. This is a real final stack argument, not a decompiler-inferred extra parameter.

DecFIGS confirms void TrafficCarStreamer::Construct, the four explicit BaseStreamer arguments, the nine explicit InternalBaseStreamer arguments and bool mbAllowFailure. The source wrapper passes the typed pool/slot/asset/failure arguments in that order. No original absolute displacement is imposed on the host class.

The existing real InternalBaseStreamer::PostLoadRequest copies mbAllowFailure directly into the typed LoadGameDataEvent::mbFailFlag and posts type 26. The complete original UpdateLoading copies the same member in all three open-coded event-build sites: 827D4330/433C, 827D45A8/45B0 and 827D4600/4634. The policy therefore reaches a genuine outbound request field; it is not a stored-but-unused constructor value. The loader's eventual interpretation and failure completion remain outside this review.

## Fresh validation

Both full actual pre/post CarStreamer TUs, all nine real support TUs and both fixture objects were rebuilt privately with canonical flags/includes. Both explicit link operations pass: all 15 compiler/linker invocations exit 0. The support sources and adjacent headers match their exact d158 Git blobs. The 259-header frozen include roster also matches its recorded content hashes and actual d158 tree/blob IDs; this checks context provenance without reopening chunk 21 semantics. Additional physical dependency hashes have no drift.

The retained integer-instruction interpreter was rerun privately against the independently reread constructor bytes and derives arrays/length/pool/slot/asset/failure arguments directly. Fresh executables run the real class constructors, catalogue and Update methods, base request state machine, resource pointer/null-handle implementation, IDs and typed queues. Only assertion UI and disabled diagnostic log globals are fixture boundaries; no replacement streamer or queue body is supplied.

The candidate passes **38/38**, baseline **2/38**, with both executables exiting 0 and zero assertions. Each emits 56 actual typed requests. All 56 rows preserve type 26, native event size 56, catalogue identity/index, pool 15, graphics set 0, receiver identity and loading-state checks; the false failure flag is the baseline's sole compared discrepancy. Cases cover catalogue sizes 0, 1, 2, 3, 8, 31, 63; all/last/end selections and repeated Construct/reset cycles. The two empty-catalogue cases are genuine unchanged controls.

This is constructor/request-transport evidence. It does not execute GameData replies, loader IO or asset-failure completion, full module/owner update, rendering, a game, native controls or hardware. Request padding and existing mHandle are not read. Existing base reply-handling qualifications are unchanged. No site, canonical, original-no-op or runtime completion credit is granted.

Traffic 10-19 and the closed 20-30 audit were not reopened. No shared source, refs, status, profile, game or author member was changed. Exact pins and provenance are in INPUT_CHECKS.json, FROZEN_CONTEXT_VERIFIED.json, EXECUTABLE_DELTA_CHECK.json and FINAL_COMPILE_CHECKS.json; fresh control results are in CPU_RESULTS.json, ORIGINAL_ARGUMENT_MODEL.json, RUN_EXITS.json and VERIFIER_RUN.log. The author patch failure is retained in AUTHOR_PATCH_APPLY_CHECK.log.
