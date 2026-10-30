@echo off
call "D:\Reverse\BP-Decomp_Workflow/tools/build/msvc_env.bat"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029\pre_CgsDebugComponentPerfMonCpu.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029/pre_CgsDebugComponentPerfMonCpu.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029/pre_CgsDebugComponentPerfMonCpu.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029\pre_GameStateModule_ProcessGameEvents_wBT_05.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029/pre_GameStateModule_ProcessGameEvents_wBT_05.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029/pre_GameStateModule_ProcessGameEvents_wBT_05.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029\pre_BrnScoringSystemDebugComponent.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029/pre_BrnScoringSystemDebugComponent.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029/pre_BrnScoringSystemDebugComponent.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029\pre_BrnScoringSystem_UpdateB.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029/pre_BrnScoringSystem_UpdateB.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029/pre_BrnScoringSystem_UpdateB.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029\post_CgsDebugComponentPerfMonCpu.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029/post_CgsDebugComponentPerfMonCpu.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029/post_CgsDebugComponentPerfMonCpu.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029\post_GameStateModule_ProcessGameEvents_wBT_05.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029/post_GameStateModule_ProcessGameEvents_wBT_05.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029/post_GameStateModule_ProcessGameEvents_wBT_05.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029\post_BrnScoringSystemDebugComponent.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029/post_BrnScoringSystemDebugComponent.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029/post_BrnScoringSystemDebugComponent.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029\post_BrnScoringSystem_UpdateB.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029/post_BrnScoringSystem_UpdateB.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_followon43_20261029/post_BrnScoringSystem_UpdateB.exit"
if errorlevel 1 exit /b 1
