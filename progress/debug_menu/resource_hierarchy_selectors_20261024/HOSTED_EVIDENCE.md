# Hosted evidence and scope

## Run identity

- Workflow: `10614b8b27a5123be34700b93d6ef21c3c1e5266`.
- Candidate B5 source: `951b2dc6c1b571bc677ef859ed9a1bd87d485f2d`.
- Hosted run: [40115091362](https://github.com/BurnoutDecomp/BP-Decomp_Workflow/actions/runs/40115091362).
- Retained local log artifact: `scratch/DEBUG_MENU_1011/resource_shuttle_const_hosted_20261024/failed-steps.log`; its byte count and SHA-256 are in `BINDINGS.json`.
- The workflow selected 11 groups overall. This packet concerns only the `run_resource_regressions` group; failures from other selected suites are outside this delta.

## Resource runner order and outcomes

The exact workflow script `ci/check-candidate-build.ps1` runs the PoolCreateProtocol positive modes first, then PCResourceShuttle and PCGuiPoolAcquire, then GameDataPoolHierarchy, and only after that hierarchy fixture passes does it run four PoolCreateProtocol negative controls.

The retained log shows:

- `PoolCreateProtocol`: protocol mode 24 checks / 0 failures and layout mode 22 checks / 0 failures (log lines 923–929).
- `PCResourceShuttle`: 14 checks / 0 failures (lines 930–946).
- `PCGuiPoolAcquire`: 27 checks / 0 failures (lines 947–952).
- `GameDataPoolHierarchy`: compile failure begins at line 953. The first reported errors are `C2511` for `GameDataPoolFixture::CreateBanks(IOBufferStack*, IOBufferStack*)` and then `C2027` for incomplete `IOBufferStack`; the same mismatch repeats for `CreatePools`. The log also shows member-access errors because these free-standing extracted definitions no longer match the fixture members. The run stops here (line 1077), before the four pool negative controls.

## Signature evidence

In the exact B5 source `src/GameSource/Resource/BrnGameDataModule.cpp`, the first matching definitions are the stack-backed originals:

- `CreateBanks(CgsModule::IOBufferStack*, CgsModule::IOBufferStack*)`, line 466.
- `CreatePools(CgsModule::IOBufferStack*, CgsModule::IOBufferStack*)`, line 506.

The same production source later defines the fixture-compatible overloads:

- `CreateBanks(void*, void*)`, line 1309.
- `CreatePools(void*, void*)`, line 1353.

`tests/GameDataPoolHierarchy.cpp` declares those exact two `void*, void*` member signatures at lines 143–144, then invokes them with null pointers throughout the bank and pool checks (lines 224–235 and 270–299). The runner extracts production definitions and changes only the owner qualification to `GameDataPoolFixture`; its shared `definition()` helper in `tests/fxgs_common.py` locates the first `source.index(signature)`. Therefore, the old prefix strings select the stack overloads before the declarations the fixture actually provides.

The correction names `bool GameDataModule::CreateBanks(void*, void*)` and `bool GameDataModule::CreatePools(void*, void*)`. This selects the actual later production PC adaptation bodies already paired with the fixture declarations. The patch does not rewrite or emulate those bodies.

## Limits

This is a static source-selector correction supported by the exact production definitions, fixture declarations/calls, and retained compile diagnostic. There is no post-change compile/run result. Root owns fresh hosted dispatch and acceptance. Pool negative-control results remain unobserved in run 40115091362 because workflow order places them after the failing hierarchy runner.
