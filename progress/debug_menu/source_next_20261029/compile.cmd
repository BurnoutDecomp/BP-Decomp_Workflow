@echo off
call "D:\Reverse\BP-Decomp_Workflow/tools/build/msvc_env.bat"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029\pre_BrnGuiEffectsArbitrator.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/pre_BrnGuiEffectsArbitrator.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/pre_BrnGuiEffectsArbitrator.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029\pre_BrnNetworkCameraX360.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/pre_BrnNetworkCameraX360.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/pre_BrnNetworkCameraX360.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029\pre_BrnTrafficCarStreamer.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/pre_BrnTrafficCarStreamer.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/pre_BrnTrafficCarStreamer.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029\pre_BrnTrafficEntityModule.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/pre_BrnTrafficEntityModule.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/pre_BrnTrafficEntityModule.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029\pre_BrnNetworkImageManager.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/pre_BrnNetworkImageManager.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/pre_BrnNetworkImageManager.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029\pre_BrnNetworkStateManager_wN1_03.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/pre_BrnNetworkStateManager_wN1_03.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/pre_BrnNetworkStateManager_wN1_03.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029\post_BrnGuiEffectsArbitrator.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/post_BrnGuiEffectsArbitrator.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/post_BrnGuiEffectsArbitrator.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029\post_BrnNetworkCameraX360.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/post_BrnNetworkCameraX360.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/post_BrnNetworkCameraX360.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029\post_BrnTrafficCarStreamer.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/post_BrnTrafficCarStreamer.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/post_BrnTrafficCarStreamer.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029\post_BrnTrafficEntityModule.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/post_BrnTrafficEntityModule.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/post_BrnTrafficEntityModule.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029\post_BrnNetworkImageManager.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/post_BrnNetworkImageManager.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/post_BrnNetworkImageManager.exit"
if errorlevel 1 exit /b 1
cl @"D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029\post_BrnNetworkStateManager_wN1_03.rsp" > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/post_BrnNetworkStateManager_wN1_03.log" 2>&1
echo %errorlevel% > "D:\Reverse\BP-Decomp_Workflow\scratch\DEBUG_MENU_1011\source_next_20261029/post_BrnNetworkStateManager_wN1_03.exit"
if errorlevel 1 exit /b 1
