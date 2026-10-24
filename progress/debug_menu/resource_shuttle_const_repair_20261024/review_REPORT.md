# Fresh source review: Resource shuttle const repair

VERDICT: pass

SOURCE_CORRECTNESS_VERDICT: pass

SOURCE_COMPOSITION_VERDICT: pass

HOSTED_COMPILE_AND_14_CHECK_RESULT: not_established

NATIVE_READINESS: not_established

The four-path proposal correctly selects the complete dispatcher and makes the fixture/production pointer declarations agree. The production helper already uses const queue access, and its body is unchanged. No defect was found in this bounded repair. This is source approval, not a successful fixture execution or a fresh full ResourceModule parity audit.

## Exact inputs and composition

| Binding | Identity |
| --- | --- |
| Source base | `6713958aa111ca62c0586d09352053a5d3803a1c` |
| Declared workflow | `67c27ec3153aed0c175c4768a5e03d0db05b617f` |
| Author seal SHA256 | `749b8cdf719d55b6c9f2478d3b87e9bb15ca878d0f9e27bbeee97c3cbea380d7` |
| Author manifest SHA256 | `9bafcea4bd60bb3ca50fa8dfe5799e85a6b98ef8e87c93586ca355c53d295eb3` |
| Proposal patch SHA256 | `c5590b28046b69927b29c820c74bac2e57aa3b30d7339d314864893c98e898bf` |
| Hypothetical composed tree | `c7513dd1763ccbb9de8b00ef667cbf3eb1945487` |

Every preimage was matched to its exact source Git object, and all 14 author manifest entries were verified. [BINDINGS.json](BINDINGS.json) records the full before/after hashes/blobs and all 27 captured inputs. The hypothetical tree was calculated from Git tree bytes in reviewer memory; no Git object/index/ref or checkout was written.

| Path | Postimage SHA256 | Postimage Git blob |
| --- | --- | --- |
| `tests/run_pc_resource_shuttle.py` | `4ee25e7d57208524c937f49faf3831d9e28453d2aca439452ebedf13385232a8` | `6a558736c556c7f4450e434eaca90c330b01ae31` |
| `tests/PCResourceShuttle.cpp` | `e4005a252eb9252b210a4a0bd84c4d51251656300d000921df2b03af0a234972` | `0336f5ed16f4bd4a16d60855c158d362ba55f380` |
| `src/GameShared/GameClasses/System/Resource/CgsResourceModule.cpp` | `2a131911893bacd2b7f8bf260600a9c57d59c01678635a5cb7cde7ea6f9744ab` | `3be5f75eb1479d811bc284cb7616df7cb489c13c` |
| `src/GameShared/GameClasses/System/Resource/CgsResourceModule.h` | `7739fafe2c7543f067446de2e2682d62d5c8ae40930fd0eb7b7e42a0dbf7fd3d` | `c7d6f0485481c1f80d2cc3abfcd498615b0ebc1e` |

## Dispatcher and declaration pairs

The old runner selector identifies `ProcessResourceRequests(ResourceIO::InputBuffer*, PoolIO::InputBuffer*)` at production source318. That is the two-input partial dispatcher, whereas the fixture declares and calls the complete four-input dispatcher. The repaired selector at runner15 uniquely identifies the genuine source353 definition with const Resource input, Memory input, loader-update input and Pool input. The real `fxgs_common.definition` helper at42–55 starts at the selected literal and returns its complete balanced definition; I read that helper but did not import or execute it.

The runner changes only that selector. Its ten production selectors remain unique, and its provider list, IO selectors, compiler invocation, result handling and expected14 count remain byte-identical. The seven unchanged IO selectors also match their exact source definitions.

[SIGNATURE_AUDIT.json](SIGNATURE_AUDIT.json) records all ten production definition/header/fixture declaration pairs. They agree after the repair:

- Open-read/close-read adders retain their const event pointers; pending-response processing remains no-argument.
- The complete request dispatcher takes const Resource input and mutable Memory/loader/Pool inputs.
- Loader stream requests take const loader output.
- Pool-output forwarding takes const Pool output in both production declaration/definition and fixture declaration.
- Resource responses take const loader and Pool outputs; pool-resource requests take mutable Memory input and const Pool output; memory responses take const Memory output.
- The selected bool Update retains its two `void*` parameters; it is distinct from the existing typed stack-backed Update overload.

The fixture changes only five declaration lines70/72–75. Four now match previously const production inputs; the Pool-output declaration follows the repaired production helper. No fabricated implementation or replacement provider is introduced.

## Const access and actual caller

Production `ProcessResourceResponses` already takes `const PoolIO::OutputBuffer*` at source412–413 and calls the helper once at429. The new helper signature at587 and matching header152 accept that actual argument directly. Mutable buffers can still be passed through ordinary qualification conversion. The exact source reference inventory found no other production definition/declaration or member-function-address contract requiring a repair; the additional GameModule mention is a comment.

The helper body remains byte-identical. It already casts to a const Pool-output reference, obtains a const queue, and traverses through `GetFirstEvent`/`GetNextEvent` (`CgsResourceModule.cpp:589–612`). The real provider's const getter checks the read lock and returns the contained queue (`CgsPoolModuleIO_OutputBuffer.cpp:65–68`; header70). The queue traversal methods are const. The helper posts replies into the separately addressed receiver queues; it does not modify or clear the source Pool output. Allowing a const source pointer therefore matches its existing access contract.

Only the parameter qualifier changes in the production implementation/header. All dispatch bodies, event mappings, sizes, native pointers, request identity, error paths, update order, lock calls and response timing remain unchanged. No new const_cast is added. The fixture's existing fake-loader cast is retained as part of its unchanged boundary code.

## Complete14-check preservation and limits

The entire fixture `main()` at81–149 is byte-identical, including all14 Check calls, inputs, expected values, labels, final failure return and output. This retains the bundle intake/native pointer check; complete raw CreatePool request check; Pool tag and seven Memory-request checks; stream ring-buffer forwarding; pending/open/close/failure response identity and cleanup checks; and loader/Pool/record/memory order, busy result, next-update visibility and zero-assert condition. Fake boundaries, assertion accounting and helper code are also unchanged. These are preserved assertions, not new passing results.

The immutable error excerpt is bound as SHA256 `e91e187addd62d56d0b6261553fa610dd629c03460e64953483f6900b4ae66a8`. It records the prior C2511/C2664 mismatches and zero-of14 setup failure for the stated hosted run40113375770. The packet separately claims full-log SHA256 `65d7457b0d9a69f55dd36226cc53449ed904350d16fe250b53782ac5a30b44e5`; that full log was not supplied or independently read in this review. No hosted result is inferred from the excerpt or this repair.

Compilation, linkage, execution of all14 checks, remaining gates, normal-package delivery and native/gameplay readiness remain unestablished. The change does not certify the full resource subsystem or alter earlier packets/verdicts. Root owns publication and any later hosted/native work.

## Method

[STATIC_CHECKS.json](STATIC_CHECKS.json) contains 86 reviewer-owned static checks, all passing: exact packet/Git bindings, complete literal deltas, source declarations/definitions, selector uniqueness, untouched test main/fakes, and actual const queue/caller access. Python AST inspection read literal source metadata only. No runner, fxgs function, generated fixture, provider or numeric test was evaluated, imported or executed. The reviewer-owned scripts performed only file/hash/source inspection and in-memory tree hashing.

No compiler, build/test, CI, game/input or IDB action ran. No source, Git state, normal configuration/profiles/logs, ledger, earlier packet or earlier report was changed. All new artifacts are confined to this review folder.
