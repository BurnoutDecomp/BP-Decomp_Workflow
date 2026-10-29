@echo off
call "D:\Reverse\BP-Decomp_Workflow/tools/build/msvc_env.bat"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029\pre_BrnDirectorArbitrator.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029/pre_BrnDirectorArbitrator.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029/pre_BrnDirectorArbitrator.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029\pre_BrnDualGinsuExhaustEffect.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029/pre_BrnDualGinsuExhaustEffect.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029/pre_BrnDualGinsuExhaustEffect.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029\pre_BrnArbStateTestbed.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029/pre_BrnArbStateTestbed.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029/pre_BrnArbStateTestbed.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029\post_BrnDirectorArbitrator.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029/post_BrnDirectorArbitrator.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029/post_BrnDirectorArbitrator.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029\post_BrnDualGinsuExhaustEffect.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029/post_BrnDualGinsuExhaustEffect.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029/post_BrnDualGinsuExhaustEffect.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029\post_BrnArbStateTestbed.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029/post_BrnArbStateTestbed.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_followon40_20261029/post_BrnArbStateTestbed.exit"
if errorlevel 1 exit /b 1
