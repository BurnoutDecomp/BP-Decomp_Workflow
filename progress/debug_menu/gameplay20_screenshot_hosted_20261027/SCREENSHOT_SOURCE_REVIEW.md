# Independent screenshot source review

VERDICT: pass

No blocking source defect was found in the five exact proposals. Approval is for their narrow changes and typed platform adaptation. It does not approve copying the old full device.cpp over the newer private candidate, and supplies no fixture result or native/site disposition.

The writer matches ARTIST 823F6730: it returns without a dispatch request; attempts a front-buffer lock once; increments the counter only after a successful lock and before fopen; unlocks every successful lock even on open failure; and clears the dispatch request after every attempted lock. Header/pixel/close failures preserve the remaining original writes and partial file. The added diagnostics report failures only. No mkdir, redirect, fallback writer or success receipt is introduced.

The independently re-read prefix is `64 3a 5c 00` (`d:\`). The original format and entire-name colon/space replacement produce relative `d_\screenshot...tga`. The TGA layout is correct: 18-byte type 2 header, explicit little-endian 16-bit dimensions, 24bpp and descriptor 0; source rows run height-1 down to 0, each source pixel advances four bytes and writes its first three. Actual pitch is respected while alpha and row padding are discarded. D3D9's accepted A/X8R8G8B8 formats store these bytes as B,G,R,A/X. [D3DFORMAT contract](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dformat).

The naturally widened LockedFrontBuffer shape agrees with DecFIGS and ARTIST 82B63398/82B63450. Failure yields null data, NA format and zero dimensions/pitch. The leaf validates real format/dimensions/pitch, acquires same-format SYSTEMMEM staging and uses the existing resolve/readback helper. A successful lock transfers one surface reference to Unlock; failed validation after lock unlocks before release; other failures release acquired resources. The MSAA resolve produces the non-MSAA source required by GetRenderTargetData. This is the appropriate linear-row replacement for Xenos untile and its obsolete 5120-byte scratch limit. [GetRenderTargetData contract](https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-getrendertargetdata).

Post-Present readback is supported by the inspected host source lifetime: primary flip renders into a separately retained PCFrameBuffer colour surface, while legacy direct/additional chains use COPY. PCPresentation copies into its output without modifying the source and clears its success flag before each present attempt. The screenshot leaf requires a successful presentation. The COPY retention assumption matches the API contract. Actual flip/COPY, device-failure and readback behavior still require the planned runtime checks. [D3DSWAPEFFECT contract](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dswapeffect).

The existing OnActivate bindings, DEBUGTriggerScreenShot producer and EndOfFrame handoff remain. Both actual Render present exits now consume the request after ShowPixelBuffer/StopProfiling. The new thread-square condition matches the original HUD/request/capture-overlays gate at 8240E194..E1E0. Existing developer3D/2D screenshot gates remain; ordinary GUI/HUD and shadow preview keep their independent gates. Current typed declarations and mounted body homes support the proposed calls.

Composition requirement: private candidate `7d5a10bb41f23bd3f4a9f1ab72de047b15a6e789` matches four author preimages after CRLF-to-LF normalization. Its device.cpp is SHA256 `06e6b541d343727a3997d6e20d4e9ffb46c6913f8648949ce477a49819f34c36` and also contains the three retained opt-in frame-request hunks. The screenshot device change is only a 3626-byte LF append after the existing final function. Apply that append/narrow patch to the newer source and preserve the request/ACK hunks; copying the author's full device.cpp would remove them. EVIDENCE.json records the derived composed LF hash without writing or compiling that text.

All ten sealed deliverables, nine pinned source preimages, ten primary exports, two DWARF copies and five literal pre-to-post patches match their hashes. Original image and reader hashes match the retained prefix evidence. Read/hash/static source inspection only: no compiler, tests/fixture imports or evaluation, staging, native game, source/Git/ledger mutation, CON access or child agents. Graphics#0029/#0030 remain pending; #0022 is excluded. The later composed fixture and native TGA/presented-frame/overlay review remain separate gates.

| Exact author postimage | SHA256 |
| --- | --- |
| b5-decomp/src/GameSource/Graphics/BrnRendererModule.h | `ac7b81b1eee7c4088453c7cc82fbaa5fd20746dba673578c75119291c2c25fe2` |
| b5-decomp/src/GameSource/Graphics/BrnRendererModule.cpp | `2c1b5c105528f5932e18c4e8bacbcb9d433fc2b1e275834ce600b63499e3c660` |
| b5-decomp/src/GameSource/Graphics/BrnRendererModule_wBT_01.cpp | `15ae20827a2a4279a3790f42aeba13273287a54bca7403d0b5cbbf8f010009fe` |
| b5-decomp/src/pc/gcm/renderengine/device.h | `aef61b7c53af7d3aa182cc557069c44afdced802e8d6d1cf271702713502f460` |
| b5-decomp/src/pc/gcm/renderengine/device.cpp | `0348eb75789c407dafae5880881f3e5d404517856edb082622504c9309e835d1` |
