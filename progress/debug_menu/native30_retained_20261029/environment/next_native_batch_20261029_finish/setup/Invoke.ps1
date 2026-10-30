$ErrorActionPreference='Stop'
$env:BPH_KEEP_SLOT_EXE='1'
try {
 & 'D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\next_native_batch_20261029_finish\runtime_harness\tools\tests\run_case.ps1' -Case 'D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\next_native_batch_20261029_finish\Case.ps1' -RunDir 'D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\next_native_batch_20261029_finish\run_62181_game01' -RunsRoot 'D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\next_native_batch_20261029_finish\runs' -Slot 62181 -GameDir 'D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\next_native_batch_20261029_finish\stage\slot' -WorkingDirectory 'D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\next_native_batch_20261029_finish\stage\data' -LockTimeoutSec 1 -Label 'Environment24 cohort unfinished13 controls; private source32; stationary PNR;43frame cap640x360;64MiB log; RootV8 normal41 guard and V5 concurrency'
 $code=$LASTEXITCODE
} finally { Remove-Item Env:\BPH_KEEP_SLOT_EXE -ErrorAction SilentlyContinue }
exit $code
