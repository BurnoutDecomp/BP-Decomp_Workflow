# Independent retained hosted-artifact review

VERDICT: pass

Bounded artifact PASS for run 40228345369/attempt 1, source `120871b7a97aed5a4882e430088584554661f901`, workflow `706d9cc02cb532c6ade1a3b2aeb438c98596d8ac`. No local verifier/runner/fixture import or evaluation, compilation, native execution, source edit or Git action occurred.

The raw shipping log reports 3003 TUs compiled, 0 cached, 0 failed, jobs 4. All 14 retained payload hashes/sizes match input-receipt.json; source/workflow/provenance and eleven pass statuses agree with verified_eleven_groups.json. The rebound verifier text contains 157 assertions; its contract/source-binding hashes match that receipt, and all 23 frozen source-binding snapshots match. I inspected its source and retained evidence without executing it or claiming a fresh replay of all157 checks.

The low-memory result records a clean detached candidate and exact f0b8 baseline. Candidate source/header/runner/helper pins equal the approved postimages. Both variants compiled the same harness and complete production TUs. Dependency reports select the real variant-specific low-memory header/types, without a shadow producer. Four baseline blob copies match their raw Git stdout, hashes and Git-blob identities. Maps bind XPhysicalAlloc/Free to source2.obj: the unchanged control resolves _aligned_malloc/_aligned_free from libucrt:align.obj; the candidate resolves ReserveAligned in source1.obj and real Kernel32 VirtualAlloc/VirtualFree imports. Correct paired-free ownership is preserved.

Raw stdout and retained witness rows agree: candidate exit 0, four PASS rows at actual low reservation bases, writable private PAGE_READWRITE ranges, page/last-byte touches, and full former spans MEM_FREE after release. Tested spans are 4096, 1179648, 1572864 and16777216 bytes. The unchanged control exits 31 with four ALLOCATION_BASE_MISMATCH rows, no other failure; alignment/touches/free calls remain successful. Its high addresses are observations, not the selected negative-control condition.

All 44 checked low-memory artifact/log identities match. All 24 owned Git/compile/link/native records report no timeout, complete handle/stdio cleanup, final active descendants 0 and transcript hashing after cleanup. Native exit codes are 31/0; both links and all six compiles exit 0. Root's verified low-memory result hash matches the actual result file.

This accepts the recorded hosted primitive-family evidence only. Exhaustion, invalid-request behavior, forced VirtualAlloc2-versus-scan coverage, Xbox cache/DMA semantics, original-arena activation, native audio/movie reachability, gameplay and current-owner acceptance remain unproved. It grants no 62088 launch, visual or debug-site credit and does not replace the normal playable package.
