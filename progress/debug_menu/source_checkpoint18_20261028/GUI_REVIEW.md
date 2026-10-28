# Combined GUI follow-on review

VERDICT: pass for the exact source packet scope.

## Source findings

The invite and cache changes follow ARTIST at the cited sites. In AlwaysAvailableComponentsManager::Update, case 175 uses the original empty argument and host-start type; case 43 checks both original pointers, reads the second event byte, sets the news latch before the movie-playing display gate, and case 44 clears it; case 105 distinguishes invite, buddy-online, count, and invalid unsigned values, including the original streamed assert and fallback message. The original case 503 body is real and remains explicitly out of scope.

GuiCache::Construct zeroes the two original bytes. RecEvent cases 91/471 and 92/96 copy the raw first byte to the original offsets. OnlineInviteMessageComponent::IsMessageAllowed preserves the nonzero test at +0x13B98 and the exact == 1 test at +0x13B99, along with the other three predicates.

The invite component's class shape, field order, overload signatures, and logical void callback agree with DecFIGS. ARTIST assembly confirms the queue and state-machine details, including the channel 40, size 16, one-byte tag 106 completion record, the uninitialized payload byte, queued-name termination, transition labels, and the original zero seeds. The 106/107 cross-build difference is handled in favor of ARTIST.

The new invite tick is under the original Prepare-success and container-playing gates. It remains separate from the host EATrax/achievement frame-bit tick. The delta does not claim full overlay-schedule parity.

For delta02, ARTIST GuiModule::Update copies r7 into r21, passes r21 as the second argument to UpdateWorstCaseHUD, then calls GetFirstEvent immediately afterward. DecFIGS identifies both parameters as CgsGuiModuleIO::InputBuffer*. The host assignment to mpGuiEventInputBuffer occurs before the new call, and DispatchInboundGuiEvents performs the first queue drain. The helper body is unchanged.

The Ginsu change narrows the original u64 HashString result only at the existing %08x boundary. ARTIST Attach calls HashString, passes its result to the original format string, and uses a 64-byte buffer. HashString at the pinned B5 baseline returns a zero-extended CRC32; ARTIST clears the upper 32 bits. The original and corrected output fixtures match for 1,285 names, including 629 high-bit CRCs. The full production TU control emits C4477 before the cast and no diagnostics after it.

## Composition and verification

The B5 base resolves to commit e2ca9665933ef5faa186e4cec0cb2e341c21abd2 and tree e0bfa4dee02b3fa7e6ddf756c8772e61b4e23a0b. Delta02 layers on delta01 manifest 35b34a9c08929dbfc6779261885ada50f1aa1fe1b7a31417aaf7f8948b1c4935; its final GuiModule.cpp supersedes delta01's intermediate image. The three change patches apply to their pinned preimages, and the normalized resulting contents match every declared post snapshot.

Windows long-path SHA-256 verification found no member errors: delta01 64/64, delta02 23/23, Ginsu 159/159. Delta01 and delta02 compile object and log hashes match their sealed receipts. Ginsu source pins and old/corrected production compile object, log, and response-file hashes also match.

The final source paths and SHA-256 values are listed in INTEGRATION_READY_HASHES.json. No shared source or refs were changed. No full link, game run, or native behavior credit is claimed.

## Scope notes

AlwaysAvailableComponentsManager::Update remains incomplete at ARTIST case 503. Do not mark that TU complete on the strength of this delta.

The requested workflow ref WFf55c3add does not resolve in the current workflow checkout; this review authenticates the B5 snapshots only. The source packets make no workflow-file change.

Delta01 retains an unmanifested legacy root-level COMPILE_RECEIPT.json. The manifest-listed compile/COMPILE_RECEIPT.json is the current sealed receipt; the legacy copy is not used for this verdict.
