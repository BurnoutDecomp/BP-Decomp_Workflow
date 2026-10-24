# Selector audit for the complete hosted resource-regression group

The audit used only `git show` snapshots at B5 `951b2dc6c1b571bc677ef859ed9a1bd87d485f2d`; it did not import/evaluate any runner or fixture. `tests/fxgs_common.py::definition` takes `source.index(signature)` and returns the brace-balanced definition at that first occurrence. The exact common helper, all four runners and fixture sources, relevant production files, workflow, and build inputs are hash-bound in `BINDINGS.json`.

## PoolCreateProtocol

The runner selects `Manager::Manager()`; `GetManagementHashLength`; `Pool::GetOverheadMemoryRequired` and `Pool::GetOverheadMemoryAlignment`; `PoolModule::GetPoolIndex`, `CreatePool`, `ProcessReceiverQueue`, `ProcessInputBuffer`, `SendCreatePoolMemoryRequest`, `DoCreatePoolRequest`, `ConvertPoolRequestOptions`, `GetRequiredResourceDescriptor`, `DoDeletePoolRequest`, and `DoUnacquireResourceRequest`; `Pool::GetId`; and, in layout mode, `Pool::Construct`, `InitPool`, `InitManagementData`, and `CreateBatchEntrySlots`. The selected production source bodies compile and the positive protocol/layout modes report 24/24 and 22/22 in run 40115091362. No same-name competing body was observed for these selected definitions in the exact inputs. The workflow's four explicit negative controls are after GameDataPoolHierarchy and were not reached in this run.

## PCResourceShuttle

The runner selects ten `ResourceModule` bodies: `AddOpenReadStreamRequest`, `AddCloseReadStreamRequest`, `ProcessPendingFileSystemResponses`, `ProcessResourceRequests(const ResourceIO::InputBuffer* lpResIn, ...)`, `ProcessBundleLoaderStreamRequests`, `ProcessPoolOutputResponses`, `ProcessResourceResponses`, `ProcessPoolResourceRequests`, `ProcessMemoryResponses`, and `Update`. It also extracts three Construct bodies, `InputBuffer::Destruct`, and three IO accessors from `CgsResourceModuleIO.cpp`; the full signatures on the two resource accessors include their const-qualified input/output shape.

Two method names have other overloads in the exact production source, and the runner selectors distinguish the intended body: `ProcessResourceRequests` uses the full `const ResourceIO::InputBuffer*` first parameter (the other starts with mutable `ResourceIO::InputBuffer*` and has a second pool input); `Update` includes the `bool` return type and selects the existing host update overload, while the console-style `EUpdateResult` overload has a different return type/IO-buffer signature. The hosted transport fixture reports 14/14. No change is indicated for this runner.

## PCGuiPoolAcquire

The runner extracts `Pool::FindResourceIndex`, `Entry* Pool::FindResource`, `PoolModule::GetPool`, and `PoolModule::DoAcquireResourceRequest`. The exact source input has one matching definition for each selector. The hosted positive fixture reports 27/27. No change is indicated for this runner.

## GameDataPoolHierarchy

The runner extracts the pool layout helpers and two `GameDataModule` construction bodies, renaming only their owner qualification to the fixture class. The other selected helper signatures are unique within their exact production source. The two create-method prefixes are the only selectors in the resource group that collide with earlier overload definitions and that fail to match the fixture declaration:

| Old selector | First body in production order | Later body the fixture declares/calls | Exact fixture anchors |
| --- | --- | --- | --- |
| `bool GameDataModule::CreateBanks(` | `IOBufferStack*, IOBufferStack*`, `BrnGameDataModule.cpp:466` | `void*, void*`, `BrnGameDataModule.cpp:1309` | declaration `GameDataPoolHierarchy.cpp:143`; calls `:224–235` |
| `bool GameDataModule::CreatePools(` | `IOBufferStack*, IOBufferStack*`, `BrnGameDataModule.cpp:506` | `void*, void*`, `BrnGameDataModule.cpp:1353` | declaration `GameDataPoolHierarchy.cpp:144`; calls `:270–299` |

Both signatures must be selected explicitly because the helper is first-occurrence based. The production file's host `Prepare` path calls these pointer-shaped routines (`BrnGameDataModule.cpp:355–362`), while its separate stack-backed prepare path calls the IOBufferStack versions (`:187–192`). The test declarations and null-pointer calls intentionally exercise the existing `void*, void*` production bodies. The proposed literal change pins those signatures without changing body extraction, tests, or semantics.
