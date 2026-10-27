# Independent XNet held-composition review

VERDICT: pass

This pass covers the exact two-file source composition onto B5 `994c1be9976445d86e80308ff4fb72bec4e218db` and the separately authored, unexecuted five-file hosted regression proposal. It does not approve activation, integration, a successful compile/link, complete GameTalk transport, native networking, or full owner teardown. No supplied code was evaluated.

The sealed input is `xnet_startup_held_composition_20261027/SEALED.json`, SHA256 `1f63889ee4d242e3fc6039e9e6eadb40f0ef9a4ad48550852bf544be8b1cc1e9`. All 63 sealed files match. The independently read Git objects match all seven retained source preimages exactly, including raw bytes and Git blob identities. The complete canonical source patch reconstructs the supplied postimages. `EVIDENCE.json` records 144 successful read/hash/static checks and no failed joins; those are review checks, not executed product tests.

| Reviewed artifact | SHA256 |
| --- | --- |
| Reviewer packet | `1c8aa3dd269b5ec199f31f246f56d93e5a76669253ef9725b66f90c340baaeee` |
| Source pre/post manifest | `3645a3386f9a8dd07a3ad59e64c6e8887f45a091f98385a0a5a229b8ee6a5d3a` |
| Source delta | `9d84e472f0e464d6d3e2fccdde166818ddfdbd4f3275c1224134486ff09d21ad` |
| Hosted tests proposal delta | `b05633952f7f75928481ef13d040a1927b75de1485dc90cce0244c638b9fd35f` |
| Protocol postimage | `0216520373e6990049b6e368003f861c98918c3db6ee7bcd165542210300854e` |
| Provider postimage | `2c3b7bedbf293fac4ac492b6fd012a6105619e1147c4651d909ea55046fb9509` |
| Exact accepted startup append | `489d48215ea3c51d69ac13390678811b4cd321948ead31017ae53563d6bf7f62` |

## Composition and original ABI

Independent comparisons of all eleven protocol definitions show that only Construct changes. The native WinSock declarations, `SOCKET` assertion/storage width, `htons`/`sockaddr_in`, BOOL-sized reuse option, real fd_set/select, typed log window, and placement-constructed packages remain the held bytes. Removing only the new native include block and the exact appended body restores every prior provider byte. XShowSigninUI, its success behavior, comment, and constants are preserved; no dev sign-in replacement is imported.

The seven retained ARTIST JSON exports are byte-identical to the canonical `.ida-exports/BURNOUT_X360_ARTIST.XEX` files, and each assembly excerpt matches its export. In `82836E88`, the stores at `82836EE4..6F00` clear thirteen contiguous bytes and set `{13,1}` before startup; the postimage supplies all thirteen bytes and explicit four-byte alignment. `8295EDD0` forwards one incoming argument and returns the int result. The actual B4 PDB lines 2397-2398 corroborate the opaque `int __cdecl XNetStartup(XNetStartupParams*)` declaration; no opaque-record member layout is inferred. The NetConn no-security configuration is corroborating context, not approval of its separate parameter variant.

The provider validates only that exact request, uses native WORD/WSADATA, and serializes startup and status through its real mutex. Invalid requests do not modify cached state or call WSA. Startup failure returns the native code and permits retry; a negotiated version mismatch attempts one rollback and preserves the observed version; rollback failure latches its reported error to prevent another acquisition. A successful 2.2 negotiation is cached. The caller reads status/version and cannot acquire a second reference. Microsoft documents the direct startup return code, negotiated version check and rollback requirement, and cleanup error retrieval; those uses agree with the proposed host leaf. [WSAStartup](https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-wsastartup), [WSACleanup](https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-wsacleanup).

The original held assertions, formatted messages, source lines 90/101/107 and continuation remain. The source does not introduce an early-return recovery policy or claim that continuing after failed initialization makes transport usable.

## Hosted regression source

The optional runner pins the actual candidate HEAD, three source files, held helper and assert/StrStream inputs, fixture files and canonical compiler inputs. The held helpers and workflow compiler context `9b0cfc8afe7fa247866464df5a781456d8b2991a` independently match their exact Git objects. The embedded complete original caller is exactly the held protocol preimage, blob `e3fbeef513e19faf7bcdbaa8ff626b217f44937f`.

Static inspection supports the intended eight isolated candidate scenarios and 117 authored checks, plus the genuine unchanged full-caller 14-check control with two expected ownership failures. The same real new provider is used in that control, making the old direct WSAStartup produce the additional modeled acquisition. A compile failure or dummy old provider cannot satisfy the required numeric/executable/raw-check evidence. Fresh executable processes initialize the real production static state; fixture reset code does not write it. Native headers precede the three injected WSA endpoints, whose function-pointer signatures are compared to the SDK. The complete Construct, actual scalar/enum/socket declarations, original MessageBufferPC type and real StrStream formatting are used. The projected aggregate, timer observer, private assert storage and WSA reference model remain explicit boundaries.

The hosted-only guard requires Windows2022/X64/Jobs4 and real run identifiers. Its unchanged helper assigns a suspended worker to a kill-on-close owned job before resume, bounds the job at 900 seconds and cleanup separately, and requires zero owned descendants, closed handles and the final transcript hash. The parent re-derives generated source and rechecks retained per-case raw output, numeric exits, compiler inputs and executable hashes after cleanup. No workflow is activated. Python was parsed as syntax only; no generator, runner, fixture, compiler or checker was evaluated in this review.

## Deferred obligations

The success policy retains one GameTalk WSA acquisition for process lifetime, replacing the old direct acquisition. Actual held GameTalk::Release returns true, and original GameData Release positively calls folded `82C296C8`, whose complete body is `li r3,1; blr`. No successful cleanup hook is invented. This pass does not certify balanced release, unload safety or native reference state after failed cleanup. Separate PcLan/NetConn/FFmpeg ownership must not supply a borrowed cleanup.

The actual held front door calls protocol Construct with port 9876; `82837648` corroborates that call. The retained selected GameData source does not establish the Construct front door. Original main/outer and source-list activation remain held. Full held-link work, a new link remainder, assertion UI/service lifetimes and real transport still require their own evidence. Earlier failed composition/link results are unchanged; this report grants no debug-menu disposition or native-control credit.
