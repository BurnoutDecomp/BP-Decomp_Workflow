#include "pc/gcm/renderengine/GpuMonitorTiming.h"
#include "pc/gcm/renderengine/GeometryBindings.h"
#include "device.h"
#include "WindowPresentation.h"
#include "DisplayResize.h"
#include "FrameProfile.h"
#include "WorldGeometry.h"
#include "pc/gcm/renderengine/TrailPixelDiagPC.h"

#include <Windows.h>
#include <d3d9.h>
#include <d3d9on12.h>
#undef DrawText
#include "GameShared/GameClasses/Development/AssertSystem/CgsAssertManager.h"
#include "pc/gcm/renderengine/SamplerStateCache.h"
#include "pc/gcm/renderengine/ShaderConstantCache.h"
#include "pc/gcm/renderengine/ShaderBindings.h"
#include <cstring>
#include <cstdio>   // [diag] BRN_FRAME_DUMP back-buffer BMP writer
#include <cstdlib>  // [diag] atoi -- BRN_FRAME_DUMP_EVERY period override
#include <string.h> // [diag] _stricmp -- BRN_FRAME_DUMP_ARM mode select (MSVC canonical)

#include "pc/gcm/renderengine/ShadowPass.h"   // PCInstallDefaultRenderTargetState
#include "GameShared/GameClasses/Development/Log/CgsLog.h"  // [diag] Device::Start failure paths
#include "GameSource/Jobs/Traffic/BrnTrafficSwerveWatch.h"  // [diag] BRN_FRAME_DUMP_ARM
#include "GameShared/GameClasses/Development/BrnDiagFilmLatch.h" // [diag] BRN_FRAME_DUMP_ARM=slomo

// [diag] BRN_FRAME_DUMP_ARM=ram -- the [T5-ram] post-hit window (BrnPhysicalTrafficManager_
// UpdateTrafficPhysics.cpp). >= 0 from the first race-car-vs-traffic outcome onwards. NOT in the
// X360 binary; declared locally by the same convention as the two latches above.
namespace BrnPhysics { namespace Vehicle { extern s32 gT5RamTrafficSlot; extern f32 gT5ArmedPlayerSpeed; } }

// PC / D3D9 renderengine device bring-up, reversed from TUB (Burnout Paradise: The
// Ultimate Box):
//   renderengine::Device::Initialize  @ TUB 0x7CC080  - display + settings init
//   renderengine::Device::Start       @ TUB 0x53E130  - drives initdx (-> initdx9
//                                                       0x9479A0, Direct3DCreate9) and
//                                                       the CreateDevice path (sub_947F10)
// The settings/resolution and the GetDeviceCaps -> CreateDevice flow are faithful; the
// original Device::Start also ran the per-frame render loop, which lives above the
// device and is not reproduced here.

bool renderengine::gFullscreen = false;
s32  renderengine::gDisplayWidth = 640;
s32  renderengine::gDisplayHeight = 480;
s32  renderengine::gAdapterIndex = 0;

// [PC platform leaf] On a laptop with hybrid graphics the D3D9 default adapter is the
// integrated GPU unless the driver is told otherwise. These two exported words are the
// NVIDIA Optimus / AMD PowerXpress contract for "run me on the discrete GPU"; the drivers
// read them out of the exe's export table at process start. Not in the X360 binary (no such
// choice exists there); an owner report of iGPU-level frame rates is what earned them.
extern "C" {
    __declspec(dllexport) DWORD NvOptimusEnablement                  = 0x00000001;
    __declspec(dllexport) int   AmdPowerXpressRequestHighPerformance = 1;
}
s32  renderengine::gAspectRatioIndex = 0;
// THE ANTI-ALIASING KNOB (given its meaning by the anti-aliasing wave, 2026-08-16).
//
// Sourced exactly like gDisplayWidth/gDisplayHeight: seeded here, overwritten from config.ini by
// BrnMain.cpp's LoadConfig (`GetPrivateProfileIntA("Settings", "AntiAliasing", ...)`, clamped to
// [0,16]) and written back by SaveConfig. LoadConfig runs AFTER Device::Initialize (BrnMain.cpp:260
// then :261), so the file value is what survives.
//
// THE VALUES, as the PC render-target leaf reads them
// (renderengine::RenderTarget::Initialize, pc/gcm/renderengine/PostFxRenderTarget.cpp):
//     0  -- USE THE CONSOLE'S OWN MULTISAMPLE FORMAT (the default, and what the shipped X360 build
//           does): the anti-alias buffer's format comes from BrnGraphics::KMSAA_TILING_PLAN, i.e.
//           format 1 == D3DMULTISAMPLE_2_SAMPLES. No other pool target is multisampled.
//     1  -- force the scene target NOT multisampled (the pre-2026-08-16 PC picture, kept as an
//           escape hatch; the frame bracket is unaffected -- see below).
//     2 / 4 / 8 -- force that many samples on the scene target instead of the console's 2.
// Anything the adapter refuses (CheckDeviceMultiSampleType) falls back to the next lower count and
// SAYS SO on the [postfx-rt] line. This is a KNOB: a value other than 0 is the user asking for
// something the console did not do, and it is never chosen silently.
//
// ⚠ IT DOES NOT SELECT THE FRAME BRACKET'S BRANCH, and must not be made to. That is
// BrnRendererModule::mbMultisampledBackbuffer, which is a recovered console constant (1) and not a
// setting -- BrnRendererModule.h. The tiled branch is correct at any sample count including none:
// its two rectangles partition the surface exactly, so the clears and the per-band resolves cover
// the same pixels either way.
//
// ⚠ IT IS ALSO NOT A "0 == OFF" SWITCH, which is the one reading to be careful of. Its Ultimate-Box
// ancestor most likely meant a plain sample count with 0 == off; here 0 has to mean "whatever the
// console did", because the console's answer is ON and this project's default is the console. That
// re-reading is DELIBERATE and is the reason 1 (not 0) is the "off" value. If the TUB setting's own
// semantics are ever recovered, this comment and the leaf's mapping are the two places to change.
s32  renderengine::gAntiAliasing = 0;

// The alpha-to-coverage knob (rung 9). 1 = honour the console's per-material
// ALPHA_TO_MASK request through the D3D9 vendor hook; 0 = never apply it. Semantics and
// the reason it is an off-switch rather than a force-switch are on the declaration in
// device.h. Default 1 because the console's answer IS the request in the shipped
// material data -- the same principle that makes gAntiAliasing default to "whatever the
// console did".
s32  renderengine::gAlphaToCoverage = 1;
// The environment-map (car-reflection) pass knob. 1 = run the console's own six-face pass and bind
// sampler 13; 0 = neither. Semantics, and why this is a SEED for the console's own
// RenderSwitches::mbRenderEnvmap rather than a second switch, are on the declaration in device.h.
// Default 1 because the console's answer is 1 (BrnRendererModule::ConstructRenderSwitches) -- the
// same principle that makes gAntiAliasing default to "whatever the console did".
s32  renderengine::gEnvironmentMap = 1;
// The corona (light-flare) pass knob. 1 = draw it; 0 = never. Semantics, and why this is a SEED for
// BrnRendererModule::mbRenderCoronas rather than a second switch, are on the declaration in
// device.h. Default 1 because the console's answer is 1 (ConstructRenderSwitches) -- the same
// principle that makes gAntiAliasing default to "whatever the console did".
s32  renderengine::gCoronas = 1;
// The sun-corona pass knob. 1 = run it; 0 = never. Semantics, and why this is a SEED for
// BrnSunCorona::mbRenderSunCorona rather than a second switch, are on the declaration in device.h.
// Default 1 because the console's answer is 1 (BrnSunCorona::Construct @0x824009EC).
s32  renderengine::gSunCorona = 1;
// Vertical sync on by default -- see the declaration in device.h.
s32  renderengine::gVSync = 1;
HWND renderengine::hWnd = nullptr;

IDirect3D9*       renderengine::gD3D9 = nullptr;
IDirect3DDevice9* renderengine::gDevice = nullptr;

namespace
{
    renderengine::PCFrameBuffer gFrameBuffer;
    renderengine::PCPresentation gPresentation;
}

HRESULT renderengine::PCGetBackBuffer(IDirect3DSurface9** lppSurface)
{
    return gFrameBuffer.GetBackBuffer(gDevice, lppSurface);
}

// FLAG PC-platform leaf: called between frames, after the scene's replacement
// surfaces have all been allocated. No device Reset and no loss of world assets.
bool renderengine::Device::ResizeDisplay(u32 luWidth, u32 luHeight)
{
    PCFrameBuffer lPending;
    if (!lPending.Resize(gDevice, hWnd, luWidth, luHeight, gVSync != 0)) return false;
    RECT lClient = {};
    if (!GetClientRect(hWnd, &lClient)) return false;
    const HRESULT lPrepare=gPresentation.Prepare(gDevice,hWnd,gVSync!=0,lClient.right,lClient.bottom);
    if (FAILED(lPrepare) && (!gPresentation.IsFlip() || !gPresentation.Ready())) return false;
    gFrameBuffer.Swap(lPending);
    gFrameBuffer.Bind(gDevice);
    PCInstallDefaultRenderTargetState(luWidth, luHeight);
    gDisplayWidth = static_cast<s32>(luWidth);
    gDisplayHeight = static_cast<s32>(luHeight);
    const RECT lScissor = {0, 0, gDisplayWidth, gDisplayHeight};
    gDevice->SetScissorRect(&lScissor);
    char lacMessage[128];
    std::snprintf(lacMessage, sizeof(lacMessage),
                  "[display] rendering at %ux%u (native window pixels)\n", luWidth, luHeight);
    CgsDev::Log::WriteToLog(lacMessage);
    return true;
}

// FLAG PC-platform leaf: the main/window thread calls this before starting a
// frame. Render, uploads and timestamp polling stay stopped after a failed
// ResetEx until either the requested output or its previous size is recovered.
bool renderengine::Device::PreparePresentationPC()
{
    if (!gPresentation.IsFlip()) return true;
    RECT lClient = {};
    if (!GetClientRect(hWnd,&lClient)) return false;
    if (IsIconic(hWnd) || lClient.right<=0 || lClient.bottom<=0) return gPresentation.Ready();
    const unsigned luBefore=gPresentation.OutputGeneration();
    const HRESULT lResult=gPresentation.Prepare(gDevice,hWnd,gVSync!=0,lClient.right,lClient.bottom,true);
    if (gPresentation.Ready() && luBefore!=gPresentation.OutputGeneration())
    {
        gFrameBuffer.Bind(gDevice);
        PCInstallDefaultRenderTargetState(gDisplayWidth,gDisplayHeight);
    }
    static HRESULT shLast = S_OK;
    if (FAILED(lResult) && lResult!=shLast)
    {
        char lacMessage[128];
        std::snprintf(lacMessage,sizeof(lacMessage),"[display] flip output reset hr=0x%08X recovered=%d\n",
            static_cast<unsigned>(lResult),gPresentation.Ready()?1:0);
        CgsDev::Log::WriteToLog(lacMessage);
    }
    shLast=lResult;
    return gPresentation.Ready();
}

// @ TUB 0x7CC080 - detect the desktop resolution and seed the default graphics
// settings. (TUB additionally seeds motion-blur / shadow / env-map / SSAO / texture
// detail etc.; the display-critical subset is reconstructed here.)
bool renderengine::Device::Initialize()
{
    gAspectRatioIndex = 0;
    gDisplayWidth = 800;
    gDisplayHeight = 600;
    gAdapterIndex = 0;

    DEVMODEA lDevMode;
    std::memset(&lDevMode, 0, sizeof(lDevMode));
    lDevMode.dmSize = sizeof(DEVMODEA);
    if (EnumDisplaySettingsA(nullptr, ENUM_CURRENT_SETTINGS, &lDevMode))
    {
        gDisplayWidth = static_cast<s32>(lDevMode.dmPelsWidth);
        gDisplayHeight = static_cast<s32>(lDevMode.dmPelsHeight);
    }

    // 0 == "use the console's own multisample format" (see the banner on the definition above), so
    // this seeding is the console default, not an off switch and not a placeholder. LoadConfig runs
    // after this (BrnMain.cpp:260/:261) and is what a config.ini value overrides it with.
    gAntiAliasing = 0;
    // Honour the console's alpha-to-mask requests unless config.ini says otherwise.
    // Seeded here for the same reason gAntiAliasing is: LoadConfig runs after this
    // (BrnMain.cpp:260/:261) and is what a config.ini value overrides it with.
    gAlphaToCoverage = 1;
    // Run the environment-map pass unless config.ini `[Settings] EnvironmentMap=0`. Seeded here for
    // the same reason the two above are: LoadConfig runs after this (BrnMain.cpp:260/:261) and is
    // what a config.ini value overrides it with.
    gEnvironmentMap = 1;
    // Draw the corona pass unless config.ini `[Settings] Coronas=0`. Seeded here for the same
    // reason its neighbours are: LoadConfig runs after this (BrnMain.cpp:260/:261) and is what a
    // config.ini value overrides it with.
    gCoronas = 1;
    // Run the sun-corona pass unless config.ini `[Settings] SunCorona=0`. Seeded here for the same
    // reason its neighbours are: LoadConfig runs after this and is what a config.ini value
    // overrides it with.
    gSunCorona = 1;
    // Vertical sync unless config.ini `[Display] VSync=0` (see device.h).
    gVSync = 1;
    // First-run default; LoadConfig restores the saved fullscreen mode next.
    gFullscreen = false;

    // Windowed bring-up renders at the 1280x720 window client size so the back buffer is
    // 1:1 with the window (the desktop res detected above is what TUB uses for fullscreen).
    // The Im2d works in this same 1280x720 logical space, so its map is identity.
    gDisplayWidth = 1280;
    gDisplayHeight = 720;
    return true;
}

// @ TUB 0x53E130 (+ initdx9 0x9479A0 + sub_947F10) - create the D3D9 object and device,
// then show the window.
void renderengine::Device::Start()
{
    // [diag 2026-08-27] every early-return below used to be SILENT, and a failed Start is
    // unrecoverable (nothing retries CreateDevice): the run boots to the end of the load
    // ladder with gDevice null, renders nothing, and the first movie never acquires --
    // indistinguishable in the log from a flow bug. Name the exact step that failed.
    if (hWnd == nullptr)
    {
        CgsDev::Log::WriteToLog("[device] Start: hWnd is null (InitializeHardware made no window) -- NO DEVICE this run\n");
        return;
    }

    IDirect3D9Ex* lpExtendedApi = nullptr;
    // FLAG PC-platform leaf: present retained frames through the native flip
    // model where supported. Keep an explicit legacy control for comparison
    // and fall back automatically if the API/device/output cannot be created.
    const char* lpcFlip = std::getenv("BRN_PRESENT_FLIP");
    if (!lpcFlip || lpcFlip[0]!='0')
    {
        using CreateExtended = HRESULT(WINAPI*)(UINT,IDirect3D9Ex**);
        const auto lpCreateExtended = reinterpret_cast<CreateExtended>(
            GetProcAddress(GetModuleHandleA("d3d9.dll"),"Direct3DCreate9Ex"));
        if (lpCreateExtended) lpCreateExtended(D3D_SDK_VERSION,&lpExtendedApi);
    }
    gD3D9 = lpExtendedApi ? lpExtendedApi : Direct3DCreate9(D3D_SDK_VERSION);
    if (gD3D9 == nullptr)
    {
        CgsDev::Log::WriteToLog("[device] Start: Direct3DCreate9 returned null -- NO DEVICE this run\n");
        return;
    }

    D3DCAPS9 lCaps;
    HRESULT lhCapsResult = gD3D9->GetDeviceCaps(gAdapterIndex, D3DDEVTYPE_HAL, &lCaps);
    if (FAILED(lhCapsResult))
    {
        char lacMsg[128];
        std::snprintf(lacMsg, sizeof(lacMsg),
                      "[device] Start: GetDeviceCaps failed hr=0x%08X -- NO DEVICE this run\n",
                      static_cast<unsigned>(lhCapsResult));
        CgsDev::Log::WriteToLog(lacMsg);
        return;
    }

    // Hardware vertex processing when the GPU supports T&L, else software - matching the
    // TUB caps check that selects HARDWARE / SOFTWARE / PURE vertex processing.
    DWORD luBehaviorFlags = (lCaps.DevCaps & D3DDEVCAPS_HWTRANSFORMANDLIGHT)
                                ? D3DCREATE_HARDWARE_VERTEXPROCESSING
                                : D3DCREATE_SOFTWARE_VERTEXPROCESSING;
    // FLAG PC-platform leaf: the window/message pump remains on the main thread
    // while ThreadLayout dispatches D3D work on its render thread. D3D9 requires
    // MULTITHREADED for that arrangement, even when our resource phase is joined.
    // Keep the same device policy in the serial benchmark control as well.
    // https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dcreate
    luBehaviorFlags |= D3DCREATE_MULTITHREADED;

    D3DPRESENT_PARAMETERS lPresentParams;
    std::memset(&lPresentParams, 0, sizeof(lPresentParams));
    // FLAG PC-platform leaf: F11 uses a borderless window, keeping D3D windowed
    // so toggling does not invalidate the engine's live GPU resources.
    lPresentParams.Windowed = TRUE;
    // COPY (not DISCARD) preserves the back buffer across Present, so an on-screen overlay drawn
    // outside the normal render loop (the assert dialog: FrameBeginNoClear -> draw -> present) can
    // composite over the last presented frame instead of garbage. Invisible to normal rendering -
    // every game frame opens with FrameBegin's Clear anyway.
    lPresentParams.SwapEffect = D3DSWAPEFFECT_COPY;
    lPresentParams.BackBufferWidth = static_cast<UINT>(gDisplayWidth);
    lPresentParams.BackBufferHeight = static_cast<UINT>(gDisplayHeight);
    lPresentParams.BackBufferFormat = D3DFMT_X8R8G8B8;
    lPresentParams.BackBufferCount = 1;
    lPresentParams.EnableAutoDepthStencil = TRUE;
    lPresentParams.AutoDepthStencilFormat = D3DFMT_D24S8;
    lPresentParams.hDeviceWindow = hWnd;
    lPresentParams.PresentationInterval =
        (gVSync != 0) ? D3DPRESENT_INTERVAL_DEFAULT : D3DPRESENT_INTERVAL_IMMEDIATE;

    HRESULT lhCreateResult = E_FAIL;
    if (lpExtendedApi)
    {
        D3DPRESENT_PARAMETERS lFlipParams=lPresentParams;
        RECT lClient={}; GetClientRect(hWnd,&lClient);
        lFlipParams.BackBufferWidth=lClient.right;
        lFlipParams.BackBufferHeight=lClient.bottom;
        lFlipParams.SwapEffect=D3DSWAPEFFECT_FLIPEX;
        lFlipParams.BackBufferCount=2;
        lFlipParams.EnableAutoDepthStencil=FALSE;
        const D3DPRESENT_PARAMETERS lRequested=lFlipParams;
        IDirect3DDevice9Ex* lpExtendedDevice=nullptr;
        lhCreateResult=lpExtendedApi->CreateDeviceEx(gAdapterIndex,D3DDEVTYPE_HAL,hWnd,
            luBehaviorFlags,&lFlipParams,nullptr,&lpExtendedDevice);
        if (SUCCEEDED(lhCreateResult))
        {
            gDevice=lpExtendedDevice;
            if (gFrameBuffer.Resize(gDevice,hWnd,gDisplayWidth,gDisplayHeight,gVSync!=0))
            {
                gFrameBuffer.Bind(gDevice);
                gPresentation.ConfigureFlip(lpExtendedDevice,lRequested);
                CgsDev::Log::WriteToLog("[device] presentation=primary-flip buffers=2\n");
            }
            else { gDevice->Release();gDevice=nullptr; }
        }
        if (!gDevice)
        {
            gD3D9->Release();gD3D9=Direct3DCreate9(D3D_SDK_VERSION);
            CgsDev::Log::WriteToLog("[device] primary flip unavailable; using legacy presentation\n");
        }
    }
    if (!gDevice && gD3D9)
        lhCreateResult = gD3D9->CreateDevice(gAdapterIndex, D3DDEVTYPE_HAL, hWnd,
                                                 luBehaviorFlags, &lPresentParams, &gDevice);
    if (!gDevice && SUCCEEDED(lhCreateResult)) lhCreateResult=E_FAIL;
    if (FAILED(lhCreateResult))
    {
        char lacMsg[128];
        std::snprintf(lacMsg, sizeof(lacMsg),
                      "[device] Start: CreateDevice failed hr=0x%08X -- NO DEVICE this run\n",
                      static_cast<unsigned>(lhCreateResult));
        CgsDev::Log::WriteToLog(lacMsg);
        return;
    }
    CgsDev::Log::WriteToLog("[device] Start: device created, window shown.\n");
    {
        // FLAG PC-platform leaf: identify the live backend once. Loading
        // d3d9on12.dll does not establish that this particular device uses it.
        // Microsoft documents E_NOINTERFACE for devices which are not on 9On12.
        // https://devblogs.microsoft.com/directx/coming-to-directx-12-d3d9on12-and-d3d11on12-resource-interop-apis/
        IDirect3DDevice9On12* lpOn12 = nullptr;
        const HRESULT lhBackend = gDevice->QueryInterface(__uuidof(IDirect3DDevice9On12),
            reinterpret_cast<void**>(&lpOn12));
        const char* lpcBackend = SUCCEEDED(lhBackend) && lpOn12 ? "yes"
            : lhBackend == E_NOINTERFACE ? "no" : "unknown";
        char lacBackend[128];
        std::snprintf(lacBackend, sizeof(lacBackend), "[device] D3D9On12=%s interface_hr=0x%08X\n",
            lpcBackend, static_cast<unsigned>(lhBackend));
        CgsDev::Log::WriteToLog(lacBackend);
        if (lpOn12) lpOn12->Release();
    }
    {
        D3DADAPTER_IDENTIFIER9 lIdent;
        std::memset(&lIdent, 0, sizeof(lIdent));
        if (SUCCEEDED(gD3D9->GetAdapterIdentifier(static_cast<UINT>(gAdapterIndex), 0, &lIdent)))
        {
            char lacAdapter[256];
            std::snprintf(lacAdapter, sizeof(lacAdapter), "[device] adapter %d: %s (%s) vendor=0x%04X device=0x%04X\n",
                          static_cast<int>(gAdapterIndex), lIdent.Description, lIdent.Driver,
                          static_cast<unsigned>(lIdent.VendorId), static_cast<unsigned>(lIdent.DeviceId));
            CgsDev::Log::WriteToLog(lacAdapter);
        }
    }

    // The engine's "device's own surface" state (rw::graphics::postfx::gpDefaultRenderTargetState,
    // X360 dword_83271614) is installed HERE on the console too -- Device::Start is what publishes
    // the front-buffer descriptor. On PC it is the swap chain's back buffer + the auto
    // depth-stencil created above; captured now, while they are exactly what is bound.
    gPCShaderConstantCache.Invalidate();
    gPCSamplerStateCache.Invalidate();
    GeometryBindingsPC::gCache.Invalidate();
    gPCShaderBindingCache.Invalidate();
    PCInstallDefaultRenderTargetState(static_cast<u32>(gDisplayWidth), static_cast<u32>(gDisplayHeight));

    ShowWindow(hWnd, SW_SHOWNORMAL);
}

// ⭐ 2026-08-16 (boot audit F-P1-9) -- the PC realisation of the console's display-mode
// refresh-rate read. GetAdapterDisplayMode reports 0 for some windowed modes, which is
// D3D's way of saying "whatever the desktop is doing"; the caller keeps its own default in
// that case rather than inventing one here.
namespace renderengine
{
    u32 GetDisplayRefreshRate()
    {
        if (gD3D9 == nullptr)
            return 0u;
        D3DDISPLAYMODE lMode;
        std::memset(&lMode, 0, sizeof(lMode));
        if (FAILED(gD3D9->GetAdapterDisplayMode(static_cast<UINT>(gAdapterIndex), &lMode)))
            return 0u;
        return static_cast<u32>(lMode.RefreshRate);
    }
}

// Begin a frame: clear to black (the loading screen fades up from black) and open the
// scene so immediate-mode draws are accepted. Returns false if the device is not ready.
bool renderengine::Device::FrameBegin()
{
    if (gDevice == nullptr || !gPresentation.Ready())
    {
        return false;
    }
    WorldGeometry_BeginFrame();
    GpuFrameTimingPC::Begin(gDevice);
    gDevice->Clear(0, nullptr, D3DCLEAR_TARGET | D3DCLEAR_ZBUFFER, D3DCOLOR_XRGB(0, 0, 0), 1.0f, 0);
    return SUCCEEDED(gDevice->BeginScene());
}

// Open a scene WITHOUT clearing, so a draw composites over whatever is already in the back buffer
// (the last presented frame, preserved by D3DSWAPEFFECT_COPY). Used by the assert dialog to overlay
// the frozen frame. Returns false if the device is not ready or a scene is already open.
bool renderengine::Device::FrameBeginNoClear()
{
    if (gDevice == nullptr || !gPresentation.Ready())
    {
        return false;
    }
    GpuFrameTimingPC::AbandonCurrentFrame();
    GpuMonitorTimingPC::AbandonCurrentFrame();
    return SUCCEEDED(gDevice->BeginScene());
}

// [diag] present counter shared with the draw-trace diagnostics (CgsIm2d.cpp reads it to
// stamp traced draws with their frame). The live counters stay on dispatch.
namespace renderengine {
    static u32 guDispatchPresentCountPC = 0;
    static bool gbDispatchLastPresentBlackPC = false;
    u32 guPresentCount = 0;
    bool gbDiagLastPresentBlack = false;
    u32 GetDispatchPresentCountPC()
    {
        return guDispatchPresentCountPC;
    }
    // FLAG PC-platform leaf: publish after join so update-side diagnostics
    // never read counters while dispatch modifies the next present.
    void PublishPresentDiagnosticsPC()
    {
        guPresentCount = guDispatchPresentCountPC;
        gbDiagLastPresentBlack = gbDispatchLastPresentBlackPC;
    }
}
// [DIAG] NOT IN THE X360 BINARY -- what the game submitted during the present being watched
// (issue #30): draws through the two Xenon draw shims, EDRAM resolves and the last resolve's
// destination. A black present with draws == 0 is the game skipping its frame; one with the
// usual thousands of draws and no resolve to the back buffer is a routing/composite defect.
namespace renderengine { u32 guDiagDraws = 0; u32 guDiagResolves = 0; void* gpDiagLastResolveDest = nullptr;
                         u32 guDiagWorldDraws = 0; u32 guDiagImBatches = 0; u32 guDiagImFullBlack = 0; u32 guDiagComposites = 0; }   // [DIAG] the watched present was black -- game-side prints key on it

// [diag] BRN_FRAME_DUMP=<dir>: save the back buffer as BMP into <dir> every Nth present
// (PrintWindow returns black against this device, so the game dumps its own frames).
//
// N defaults to 30 and is overridden by BRN_FRAME_DUMP_EVERY=<n>.  ⭐ WHY THIS IS TUNABLE:
// a 30-present period is ~0.4 s on an uncapped PC boot, which is COARSER THAN THE UI
// TRANSITIONS IT IS USED TO JUDGE -- a GUI animation that plays over ~1 s lands in two or
// three samples and is indistinguishable from a pop.  Judging "does this animate?" from a
// 30-present dump is measuring the sampler, not the game.  Set BRN_FRAME_DUMP_EVERY=1 for
// a per-present capture of a transition; leave it unset for the ordinary flow run (657
// frames / 2.3 GB at 30 -- a period of 1 is ~30x that, so use it for short windows).
// ⛔ THE PERIOD IS SHARED, NOT COPIED. Other diagnostics (the CXFORM batch trace in
// CgsImRenderBufferTemplate.cpp) deliberately gate on the SAME presents this writer does, so
// that a logged number and a dumped pixel come from ONE frame -- a trace correlated against a
// dump of a DIFFERENT frame has already produced a false lead in this tree. A second hardcoded
// 30 in those consumers would silently desync the moment the period is overridden, so they call
// this accessor instead.
namespace renderengine
{
    u32 FrameDumpEvery()
    {
        static u32 suEvery = 0u;
        if (suEvery == 0u)
        {
            suEvery = 30u;
            char lacEvery[32];
            DWORD luEveryLen =
                GetEnvironmentVariableA("BRN_FRAME_DUMP_EVERY", lacEvery, sizeof(lacEvery));
            if (luEveryLen != 0 && luEveryLen < sizeof(lacEvery))
            {
                const int liEvery = atoi(lacEvery);
                if (liEvery > 0) { suEvery = static_cast<u32>(liEvery); }
            }
        }
        return suEvery;
    }
}

// [diag] BRN_BLACK_FRAME_WATCH=<threshold 0..255>: after EVERY present, shrink the back buffer to
// 32x18 on the GPU (StretchRect, linear filter), read that tiny surface back and log ONE
// `[black-frame] BEGIN` line the first present whose mean 8-bit luminance falls below the
// threshold, and one `[black-frame] END` line when it recovers. NOT IN THE X360 BINARY. It exists
// for b5-decomp issue #30 ("around every 5 minutes the screen briefly turns black"): a frame dump
// cannot film a ten-minute drive (16 GB per 130 s, and filming that hard starves the sim), while a
// present counter + wall clock on one log line is what pairs the blink with the streaming / save /
// GUI lines around it. ~2 MB/frame of GPU copy plus a 2 KB read-back: cheap, but still opt-in.
// Inert unless the variable names a value. DELETE-WHEN-STABLE.
// [DIAG] NOT IN THE X360 BINARY -- issue #30: mean 8-bit luminance of a D3D texture's level 0
// (a 32x18 StretchRect + readback, the black-frame watch's own method), so the composite's SOURCE
// can be measured on the presents the watch calls black. Returns -1 when it cannot sample.
float renderengine::DiagTextureMeanLuma(void* lpD3DBaseTexture)
{
    static IDirect3DSurface9* spSmall = nullptr;
    static IDirect3DSurface9* spSys   = nullptr;
    if (gDevice == nullptr || lpD3DBaseTexture == nullptr)
        return -1.0f;
    IDirect3DBaseTexture9* lpBase = static_cast<IDirect3DBaseTexture9*>(lpD3DBaseTexture);
    if (lpBase->GetType() != D3DRTYPE_TEXTURE)
        return -1.0f;
    IDirect3DTexture9* lpTex = static_cast<IDirect3DTexture9*>(lpBase);
    IDirect3DSurface9* lpLevel = nullptr;
    const HRESULT lhrLevel = lpTex->GetSurfaceLevel(0, &lpLevel);
    if (FAILED(lhrLevel) || lpLevel == nullptr)
        return -1.0f;
    if (spSmall == nullptr
        && (FAILED(gDevice->CreateRenderTarget(32, 18, D3DFMT_A8R8G8B8, D3DMULTISAMPLE_NONE, 0, FALSE, &spSmall, nullptr))
            || FAILED(gDevice->CreateOffscreenPlainSurface(32, 18, D3DFMT_A8R8G8B8, D3DPOOL_SYSTEMMEM, &spSys, nullptr))))
    {
        lpLevel->Release();
        return -1.0f;
    }
    const HRESULT lhrStretch = gDevice->StretchRect(lpLevel, nullptr, spSmall, nullptr, D3DTEXF_LINEAR);
    lpLevel->Release();
    if (FAILED(lhrStretch) || FAILED(gDevice->GetRenderTargetData(spSmall, spSys)))
        return -1.0f;
    D3DLOCKED_RECT lLock;
    if (FAILED(spSys->LockRect(&lLock, nullptr, D3DLOCK_READONLY)))
        return -1.0f;
    u64 luSum = 0u;
    for (u32 luY = 0u; luY < 18u; ++luY)
    {
        const u8* lpRow = static_cast<const u8*>(lLock.pBits) + luY * lLock.Pitch;
        for (u32 luX = 0u; luX < 32u; ++luX)
            luSum += lpRow[luX * 4u] + lpRow[luX * 4u + 1u] + lpRow[luX * 4u + 2u];
    }
    spSys->UnlockRect();
    return static_cast<float>(luSum) / static_cast<float>(32u * 18u * 3u);
}

// FLAG PC-platform leaf: optional readback of the actual final-composite
// source/bloom textures. A band already in source0 belongs to an earlier pass;
// a clear source paired with a bad final BMP directs the audit to the composite.
// Only reads native bindings/surfaces:30 paired presents by default, at most128
// when explicitly requested. Samples one in twenty configured BMPs after
// present3000. Observation start/cadence/cap do not change render behavior.
void renderengine::DiagDumpPostFxSourcesPC()
{
    static const bool sbEnabled = []() {
        const char* lpValue = std::getenv("BRN_POSTFX_SOURCE_DUMP");
        return lpValue && lpValue[0] == '1';
    }();
    static const u32 suStartPresent = []() {
        const char* lpValue = std::getenv("BRN_POSTFX_SOURCE_START");
        char* lpEnd = nullptr;
        const unsigned long luValue = lpValue ? std::strtoul(lpValue, &lpEnd, 10) : 0;
        return lpValue && lpEnd != lpValue && *lpEnd == '\0' && luValue <= 1000000u
            ? static_cast<u32>(luValue) : 3000u;
    }();
    static const u32 suCadence = []() {
        const char* lpValue = std::getenv("BRN_POSTFX_SOURCE_EVERY");
        char* lpEnd = nullptr;
        const unsigned long luValue = lpValue ? std::strtoul(lpValue, &lpEnd, 10) : 0;
        return lpValue && lpEnd != lpValue && *lpEnd == '\0' && luValue > 0 && luValue <= 1000000u
            ? static_cast<u32>(luValue) : FrameDumpEvery() * 20u;
    }();
    static const u32 suMaxSamples = []() {
        const char* lpValue = std::getenv("BRN_POSTFX_SOURCE_MAX");
        char* lpEnd = nullptr;
        const unsigned long luValue = lpValue ? std::strtoul(lpValue, &lpEnd, 10) : 0;
        return lpValue && lpEnd != lpValue && *lpEnd == '\0' && luValue > 0 && luValue <= 128u
            ? static_cast<u32>(luValue) : 30u;
    }();
    static const char* const spFrameDirectory = std::getenv("BRN_FRAME_DUMP");
    static u32 suAttempts = 0u;
    static u32 suLastPresent = ~0u;
    const u32 luPresent = GetDispatchPresentCountPC();
    if (!sbEnabled || !spFrameDirectory || !spFrameDirectory[0] || !gDevice || luPresent < suStartPresent
        || suAttempts >= suMaxSamples || suLastPresent == luPresent
        || (luPresent % suCadence) != 0u)
        return;
    if (suAttempts == 0u)
    {
        char lacConfiguration[128];
        std::snprintf(lacConfiguration, sizeof(lacConfiguration),
            "[postfx-source] observation start=%u every=%u cap=%u\n", suStartPresent, suCadence, suMaxSamples);
        CgsDev::Log::WriteToLog(lacConfiguration);
    }
    suLastPresent = luPresent;
    ++suAttempts;
    char lacDirectory[768];
    const int liDirectoryLength = std::snprintf(lacDirectory, sizeof(lacDirectory),
        "%s/inputs", spFrameDirectory);
    if (liDirectoryLength <= 0 || liDirectoryLength >= static_cast<int>(sizeof(lacDirectory)))
        return;
    CreateDirectoryA(lacDirectory, nullptr); // caller's unique frame directory already exists

    for (u32 luUnit = 0u; luUnit < 2u; ++luUnit)
    {
        IDirect3DBaseTexture9* lpTexture = nullptr;
        IDirect3DSurface9 *lpSource = nullptr, *lpReadback = nullptr;
        HRESULT lhr = gDevice->GetTexture(luUnit, &lpTexture);
        D3DSURFACE_DESC lDesc = {};
        if (SUCCEEDED(lhr) && lpTexture && lpTexture->GetType() == D3DRTYPE_TEXTURE)
            lhr = static_cast<IDirect3DTexture9*>(lpTexture)->GetSurfaceLevel(0, &lpSource);
        else
            lhr = E_FAIL;
        if (SUCCEEDED(lhr)) lhr = lpSource->GetDesc(&lDesc);
        if (SUCCEEDED(lhr) && lDesc.Format != D3DFMT_A8R8G8B8
            && lDesc.Format != D3DFMT_X8R8G8B8)
            lhr = E_NOTIMPL; // no guessed encoding or GPU conversion of the evidence
        if (SUCCEEDED(lhr))
            lhr = gDevice->CreateOffscreenPlainSurface(lDesc.Width, lDesc.Height,
                lDesc.Format, D3DPOOL_SYSTEMMEM, &lpReadback, nullptr);
        if (SUCCEEDED(lhr)) lhr = gDevice->GetRenderTargetData(lpSource, lpReadback);
        bool lbWritten = false;
        D3DLOCKED_RECT lLock = {};
        if (SUCCEEDED(lhr)) lhr = lpReadback->LockRect(&lLock, nullptr, D3DLOCK_READONLY);
        if (SUCCEEDED(lhr))
        {
            char lacPath[850];
            const int liLength = std::snprintf(lacPath, sizeof(lacPath), "%s/%s_%06u.bmp",
                lacDirectory, luUnit == 0u ? "source" : "bloom", luPresent);
            FILE* lpFile = liLength > 0 && liLength < static_cast<int>(sizeof(lacPath))
                ? std::fopen(lacPath, "wb") : nullptr;
            if (lpFile)
            {
                BITMAPFILEHEADER lFile = {};
                BITMAPINFOHEADER lInfo = {};
                lFile.bfType = 0x4d42;
                lFile.bfOffBits = sizeof(lFile) + sizeof(lInfo);
                lFile.bfSize = lFile.bfOffBits + lDesc.Width*lDesc.Height*4u;
                lInfo.biSize = sizeof(lInfo);
                lInfo.biWidth = lDesc.Width;
                lInfo.biHeight = -static_cast<LONG>(lDesc.Height);
                lInfo.biPlanes = 1;
                lInfo.biBitCount = 32;
                lInfo.biCompression = BI_RGB;
                lInfo.biSizeImage = lDesc.Width*lDesc.Height*4u;
                lbWritten = fwrite(&lFile, sizeof(lFile), 1, lpFile) == 1u
                    && fwrite(&lInfo, sizeof(lInfo), 1, lpFile) == 1u;
                for (u32 luRow = 0u; luRow < lDesc.Height && lbWritten; ++luRow)
                    lbWritten = fwrite(static_cast<const u8*>(lLock.pBits) + luRow*lLock.Pitch,
                        4u, lDesc.Width, lpFile) == lDesc.Width;
                lbWritten = fclose(lpFile) == 0 && lbWritten;
            }
            lpReadback->UnlockRect();
        }
        char lacMessage[220];
        std::snprintf(lacMessage, sizeof(lacMessage),
            "[postfx-source] present=%u unit=%u size=%ux%u format=%u written=%u hr=%08X\n",
            luPresent, luUnit, lDesc.Width, lDesc.Height, static_cast<u32>(lDesc.Format),
            lbWritten ? 1u : 0u, static_cast<u32>(lhr));
        CgsDev::Log::WriteToLog(lacMessage);
        if (lpReadback) lpReadback->Release();
        if (lpSource) lpSource->Release();
        if (lpTexture) lpTexture->Release();
    }
}

// FLAG PC-platform leaf: four bounded before/after native colour readbacks
// identify pixels actually covered by the original glass-array draw. They do
// not rebind a surface, shader, texture or state, and issue no additional draw.
namespace renderengine
{
namespace
{
    IDirect3DSurface9* spGlassPixelTarget = nullptr;
    IDirect3DSurface9* spGlassPixelBefore = nullptr;
    D3DSURFACE_DESC sGlassPixelDesc = {};
    u32 suGlassPixelAttempts = 0, suGlassPixelPresent = 0, suGlassPixelLastPresent = 0;
    const char* GlassPixelDirectoryPC()
    {
        static const char* const directory = std::getenv("BRN_FRAME_DUMP");
        return directory;
    }
    void ReleaseGlassPixelsPC()
    {
        if (spGlassPixelBefore) spGlassPixelBefore->Release();
        if (spGlassPixelTarget) spGlassPixelTarget->Release();
        spGlassPixelBefore = nullptr; spGlassPixelTarget = nullptr;
    }
    HRESULT ReadNativeColourTargetPC(IDirect3DSurface9* target, IDirect3DSurface9* readback,
                                    const D3DSURFACE_DESC& desc)
    {
        if (desc.MultiSampleType == D3DMULTISAMPLE_NONE)
            return gDevice->GetRenderTargetData(target,readback);
        // Native colour resolve, same format/dimensions as the actual surface.
        // The scratch RT is never bound or drawn into. This is the D3D9 MSAA
        // copy path also used by the engine's normal Target::Resolve.
        IDirect3DSurface9* resolved=nullptr;
        HRESULT hr=gDevice->CreateRenderTarget(desc.Width,desc.Height,
            desc.Format,D3DMULTISAMPLE_NONE,0,FALSE,&resolved,nullptr);
        if (SUCCEEDED(hr)) hr=gDevice->StretchRect(target,nullptr,resolved,nullptr,D3DTEXF_NONE);
        if (SUCCEEDED(hr)) hr=gDevice->GetRenderTargetData(resolved,readback);
        if (resolved) resolved->Release(); return hr;
    }
    bool WriteNativeColourPixelsPC(const char* path, IDirect3DSurface9* surface,
                                  const D3DSURFACE_DESC& desc)
    {
        D3DLOCKED_RECT lock = {};
        if (FAILED(surface->LockRect(&lock, nullptr, D3DLOCK_READONLY))) return false;
        FILE* file = std::fopen(path, "wb"); bool written = file != nullptr;
        if (file)
        {
            BITMAPFILEHEADER header = {}; BITMAPINFOHEADER info = {};
            header.bfType = 0x4d42; header.bfOffBits = sizeof(header)+sizeof(info);
            header.bfSize = header.bfOffBits+desc.Width*desc.Height*4u;
            info.biSize = sizeof(info); info.biWidth = desc.Width;
            info.biHeight = -static_cast<LONG>(desc.Height); info.biPlanes = 1;
            info.biBitCount = 32; info.biCompression = BI_RGB;
            info.biSizeImage = desc.Width*desc.Height*4u;
            written = fwrite(&header,sizeof(header),1,file)==1 && fwrite(&info,sizeof(info),1,file)==1;
            for (u32 y=0;y<desc.Height && written;++y)
                written = fwrite(static_cast<const u8*>(lock.pBits)+y*lock.Pitch,
                    4u,desc.Width,file)==desc.Width;
            written = fclose(file)==0 && written;
        }
        surface->UnlockRect(); return written;
    }
}
bool GlassPixelDiag_BeginPC()
{
    static const bool enabled = []() {
        const char* value=std::getenv("BRN_GLASS_PIXEL_DUMP"); return value && value[0]=='1';
    }();
    const char* directory=GlassPixelDirectoryPC(); const u32 present=GetDispatchPresentCountPC();
    if (!enabled || !directory || !directory[0] || !gDevice || suGlassPixelAttempts>=4
        || (suGlassPixelAttempts && present-suGlassPixelLastPresent<10u)) return false;
    suGlassPixelPresent=present; suGlassPixelLastPresent=present; ++suGlassPixelAttempts;
    ReleaseGlassPixelsPC();
    HRESULT hr=gDevice->GetRenderTarget(0,&spGlassPixelTarget);
    if (SUCCEEDED(hr)) hr=spGlassPixelTarget->GetDesc(&sGlassPixelDesc);
    if (SUCCEEDED(hr) && sGlassPixelDesc.Format!=D3DFMT_A8R8G8B8
        && sGlassPixelDesc.Format!=D3DFMT_X8R8G8B8) hr=E_NOTIMPL;
    if (SUCCEEDED(hr)) hr=gDevice->CreateOffscreenPlainSurface(sGlassPixelDesc.Width,
        sGlassPixelDesc.Height,sGlassPixelDesc.Format,D3DPOOL_SYSTEMMEM,&spGlassPixelBefore,nullptr);
    if (SUCCEEDED(hr)) hr=ReadNativeColourTargetPC(spGlassPixelTarget,spGlassPixelBefore,sGlassPixelDesc);
    if (FAILED(hr))
    {
        char message[256]; std::snprintf(message,sizeof(message),
            "[glass-pixels] present=%u attempt=%u stage=before size=%ux%u format=%u msaa=%u written=0 hr=%08X\n",
            present,suGlassPixelAttempts,sGlassPixelDesc.Width,sGlassPixelDesc.Height,
            static_cast<u32>(sGlassPixelDesc.Format),static_cast<u32>(sGlassPixelDesc.MultiSampleType),static_cast<u32>(hr));
        CgsDev::Log::WriteToLog(message); ReleaseGlassPixelsPC(); return false;
    }
    return true;
}
void GlassPixelDiag_EndPC(u32 batches,u64 acceptedDraws)
{
    if (!spGlassPixelBefore || !spGlassPixelTarget) return;
    IDirect3DSurface9* target=nullptr; IDirect3DSurface9* after=nullptr;
    HRESULT hr=gDevice->GetRenderTarget(0,&target);
    if (SUCCEEDED(hr) && target!=spGlassPixelTarget) hr=E_UNEXPECTED;
    if (SUCCEEDED(hr)) hr=gDevice->CreateOffscreenPlainSurface(sGlassPixelDesc.Width,
        sGlassPixelDesc.Height,sGlassPixelDesc.Format,D3DPOOL_SYSTEMMEM,&after,nullptr);
    if (SUCCEEDED(hr)) hr=ReadNativeColourTargetPC(target,after,sGlassPixelDesc);
    bool beforeWritten=false,afterWritten=false;
    u32 rgbChanged=0,alphaChanged=0,minX=~0u,minY=~0u,maxX=0,maxY=0;
    if (SUCCEEDED(hr))
    {
        D3DLOCKED_RECT a={},b={};
        hr=spGlassPixelBefore->LockRect(&a,nullptr,D3DLOCK_READONLY);
        if (SUCCEEDED(hr))
        {
            hr=after->LockRect(&b,nullptr,D3DLOCK_READONLY);
            if (SUCCEEDED(hr))
            {
                // Native A8/X8 RGB dwords; no guessed depth/half-float decoding.
                for (u32 y=0;y<sGlassPixelDesc.Height;++y) for (u32 x=0;x<sGlassPixelDesc.Width;++x)
                {
                    u32 av,bv;
                    std::memcpy(&av,static_cast<const u8*>(a.pBits)+y*a.Pitch+x*4u,4);
                    std::memcpy(&bv,static_cast<const u8*>(b.pBits)+y*b.Pitch+x*4u,4);
                    if ((av^bv)&0xffffffu)
                    {
                        ++rgbChanged;
                        if (x<minX) minX=x; if (y<minY) minY=y;
                        if (x>maxX) maxX=x; if (y>maxY) maxY=y;
                    }
                    alphaChanged+=((av^bv)&0xff000000u)!=0;
                }
                after->UnlockRect();
            }
            spGlassPixelBefore->UnlockRect();
        }
    }
    if (SUCCEEDED(hr))
    {
        char directory[768],beforePath[850],afterPath[850];
        const int n=std::snprintf(directory,sizeof(directory),"%s/glass",GlassPixelDirectoryPC());
        if (n>0 && n<static_cast<int>(sizeof(directory)))
        {
            CreateDirectoryA(directory,nullptr);
            const int na=std::snprintf(beforePath,sizeof(beforePath),"%s/before_%06u.bmp",directory,suGlassPixelPresent);
            const int nb=std::snprintf(afterPath,sizeof(afterPath),"%s/after_%06u.bmp",directory,suGlassPixelPresent);
            if (na>0 && na<static_cast<int>(sizeof(beforePath))) beforeWritten=WriteNativeColourPixelsPC(beforePath,spGlassPixelBefore,sGlassPixelDesc);
            if (nb>0 && nb<static_cast<int>(sizeof(afterPath))) afterWritten=WriteNativeColourPixelsPC(afterPath,after,sGlassPixelDesc);
        }
    }
    char message[384]; std::snprintf(message,sizeof(message),
        "[glass-pixels] present=%u attempt=%u batches=%u accepted=%llu size=%ux%u format=%u msaa=%u resolved=%u written=%u/%u rgb=%u alpha=%u bbox=%u,%u,%u,%u hr=%08X\n",
        suGlassPixelPresent,suGlassPixelAttempts,batches,static_cast<unsigned long long>(acceptedDraws),
        sGlassPixelDesc.Width,sGlassPixelDesc.Height,static_cast<u32>(sGlassPixelDesc.Format),
        static_cast<u32>(sGlassPixelDesc.MultiSampleType),sGlassPixelDesc.MultiSampleType!=D3DMULTISAMPLE_NONE?1u:0u,
        beforeWritten?1u:0u,afterWritten?1u:0u,rgbChanged,alphaChanged,minX,minY,maxX,maxY,static_cast<u32>(hr));
    CgsDev::Log::WriteToLog(message);
    if (after) after->Release(); if (target) target->Release(); ReleaseGlassPixelsPC();
}

namespace
{
    IDirect3DSurface9* spTrailPixelTarget = nullptr;
    IDirect3DSurface9* spTrailPixelBefore = nullptr;
    D3DSURFACE_DESC sTrailPixelDesc = {};
    D3DVIEWPORT9 sTrailPixelViewport = {};
    TrailPixelClockPC sTrailPixelClock;
    TrailPixelTrackPC sTrailPixelTrack;
    TrailPixelRectPC sTrailPixelRect;
    f32 sfTrailPixelTime = 0;
    u32 suTrailPixelPresent = 0;
    u32 suTrailPixelSubmitted = 0;
    u64 suTrailPixelDraws = 0;

    void ReleaseTrailPixelsPC()
    {
        if (spTrailPixelBefore) spTrailPixelBefore->Release();
        if (spTrailPixelTarget) spTrailPixelTarget->Release();
        spTrailPixelBefore = nullptr; spTrailPixelTarget = nullptr;
    }
}

bool TrailPixelDiag_EnabledPC()
{
    static const bool enabled = []() {
        const char* value = std::getenv("BRN_TRAIL_PIXEL_DUMP"); return value && value[0] == '1';
    }();
    return enabled;
}

bool TrailPixelDiag_BeginPC(f32 now, Matrix44::InParam matrix, const TrailPixelBatchPC* batches)
{
    static const f32 start = []() {
        const char* value = std::getenv("BRN_TRAIL_PIXEL_START");
        const f32 parsed = value ? static_cast<f32>(std::atof(value)) : 0.0f;
        return std::isfinite(parsed) && parsed >= 0 ? parsed : 0.0f;
    }();
    const char* directory = GlassPixelDirectoryPC();
    if (!TrailPixelDiag_EnabledPC() || !directory || !directory[0] || !gDevice
        || !std::isfinite(now) || now < start || sTrailPixelClock.attempts >= 12
        || (sTrailPixelClock.attempts && now-sTrailPixelClock.last < 1.0f)) return false;
    ReleaseTrailPixelsPC(); sTrailPixelDesc = {};
    HRESULT hr = gDevice->GetRenderTarget(0,&spTrailPixelTarget);
    if (SUCCEEDED(hr)) hr = spTrailPixelTarget->GetDesc(&sTrailPixelDesc);
    if (SUCCEEDED(hr) && sTrailPixelDesc.Format != D3DFMT_A8R8G8B8
        && sTrailPixelDesc.Format != D3DFMT_X8R8G8B8) hr = E_NOTIMPL;
    if (SUCCEEDED(hr)) hr = gDevice->GetViewport(&sTrailPixelViewport);
    if (SUCCEEDED(hr))
    {
        sTrailPixelTrack.Observe(batches,matrix,sTrailPixelViewport.Width,sTrailPixelViewport.Height,now);
        // Wait for a real in-view strip; after selecting it, retain its metadata
        // and sample the unchanged empty pass too, even when it is expired.
        if (!sTrailPixelTrack.selected) { ReleaseTrailPixelsPC(); return false; }
        sTrailPixelRect = sTrailPixelTrack.Project(matrix,sTrailPixelViewport.Width,sTrailPixelViewport.Height);
        sTrailPixelRect.left += sTrailPixelViewport.X; sTrailPixelRect.right += sTrailPixelViewport.X;
        sTrailPixelRect.top += sTrailPixelViewport.Y; sTrailPixelRect.bottom += sTrailPixelViewport.Y;
        if (sTrailPixelRect.right > sTrailPixelDesc.Width) sTrailPixelRect.right = sTrailPixelDesc.Width;
        if (sTrailPixelRect.bottom > sTrailPixelDesc.Height) sTrailPixelRect.bottom = sTrailPixelDesc.Height;
        sTrailPixelRect.valid = sTrailPixelRect.valid && sTrailPixelRect.right > sTrailPixelRect.left
            && sTrailPixelRect.bottom > sTrailPixelRect.top;
        hr = gDevice->CreateOffscreenPlainSurface(sTrailPixelDesc.Width,sTrailPixelDesc.Height,
            sTrailPixelDesc.Format,D3DPOOL_SYSTEMMEM,&spTrailPixelBefore,nullptr);
        if (SUCCEEDED(hr)) hr = ReadNativeColourTargetPC(spTrailPixelTarget,spTrailPixelBefore,sTrailPixelDesc);
    }
    sTrailPixelClock.Take(now,start); sfTrailPixelTime = now;
    suTrailPixelPresent = GetDispatchPresentCountPC();
    if (FAILED(hr))
    {
        char message[300]; std::snprintf(message,sizeof(message),
            "[trail-pixels] present=%u attempt=%u now=%.6f stage=before size=%ux%u format=%u msaa=%u written=0 hr=%08X\n",
            suTrailPixelPresent,sTrailPixelClock.attempts,double(now),sTrailPixelDesc.Width,sTrailPixelDesc.Height,
            u32(sTrailPixelDesc.Format),u32(sTrailPixelDesc.MultiSampleType),u32(hr));
        CgsDev::Log::WriteToLog(message); ReleaseTrailPixelsPC(); return false;
    }
    suTrailPixelDraws = WorldDrawCallCount();
    // CPU submitted batches, not a native acceptance counter. Native RGB
    // before/after differences establish writes by the original trail pass.
    suTrailPixelSubmitted = BrnParticle::Native::TrailRenderer::guProbeDraws;
    return true;
}

void TrailPixelDiag_EndPC()
{
    if (!spTrailPixelBefore || !spTrailPixelTarget) return;
    const u64 accepted = WorldDrawCallCount()-suTrailPixelDraws;
    const u32 submitted = BrnParticle::Native::TrailRenderer::guProbeDraws-suTrailPixelSubmitted;
    IDirect3DSurface9* target = nullptr; IDirect3DSurface9* after = nullptr;
    HRESULT hr = gDevice->GetRenderTarget(0,&target);
    if (SUCCEEDED(hr) && target != spTrailPixelTarget) hr = E_UNEXPECTED;
    D3DVIEWPORT9 viewport = {};
    if (SUCCEEDED(hr)) hr = gDevice->GetViewport(&viewport);
    if (SUCCEEDED(hr) && (viewport.X != sTrailPixelViewport.X || viewport.Y != sTrailPixelViewport.Y
        || viewport.Width != sTrailPixelViewport.Width || viewport.Height != sTrailPixelViewport.Height
        || viewport.MinZ != sTrailPixelViewport.MinZ || viewport.MaxZ != sTrailPixelViewport.MaxZ)) hr = E_UNEXPECTED;
    if (SUCCEEDED(hr)) hr = gDevice->CreateOffscreenPlainSurface(sTrailPixelDesc.Width,sTrailPixelDesc.Height,
        sTrailPixelDesc.Format,D3DPOOL_SYSTEMMEM,&after,nullptr);
    if (SUCCEEDED(hr)) hr = ReadNativeColourTargetPC(target,after,sTrailPixelDesc);
    TrailPixelDeltaPC delta;
    if (SUCCEEDED(hr))
    {
        D3DLOCKED_RECT a = {}, b = {};
        hr = spTrailPixelBefore->LockRect(&a,nullptr,D3DLOCK_READONLY);
        if (SUCCEEDED(hr))
        {
            hr = after->LockRect(&b,nullptr,D3DLOCK_READONLY);
            if (SUCCEEDED(hr))
            {
                for (u32 y = 0; y < sTrailPixelDesc.Height; ++y) for (u32 x = 0; x < sTrailPixelDesc.Width; ++x)
                {
                    u32 av, bv;
                    std::memcpy(&av,static_cast<const u8*>(a.pBits)+y*a.Pitch+x*4u,4);
                    std::memcpy(&bv,static_cast<const u8*>(b.pBits)+y*b.Pitch+x*4u,4);
                    delta.Add(av,bv,x,y,sTrailPixelRect);
                }
                after->UnlockRect();
            }
            spTrailPixelBefore->UnlockRect();
        }
    }
    bool beforeWritten = false, afterWritten = false;
    if (SUCCEEDED(hr))
    {
        char directory[768], beforePath[850], afterPath[850];
        const int n = std::snprintf(directory,sizeof(directory),"%s/trail",GlassPixelDirectoryPC());
        if (n > 0 && n < static_cast<int>(sizeof(directory)))
        {
            CreateDirectoryA(directory,nullptr);
            const int na = std::snprintf(beforePath,sizeof(beforePath),"%s/before_%06u.bmp",directory,suTrailPixelPresent);
            const int nb = std::snprintf(afterPath,sizeof(afterPath),"%s/after_%06u.bmp",directory,suTrailPixelPresent);
            if (na > 0 && na < static_cast<int>(sizeof(beforePath))) beforeWritten = WriteNativeColourPixelsPC(beforePath,spTrailPixelBefore,sTrailPixelDesc);
            if (nb > 0 && nb < static_cast<int>(sizeof(afterPath))) afterWritten = WriteNativeColourPixelsPC(afterPath,after,sTrailPixelDesc);
        }
    }
    const Vector3 a = sTrailPixelTrack.ends[0].mPosition.GetVector3();
    const Vector3 b = sTrailPixelTrack.ends[1].mPosition.GetVector3();
    const f32 laidA = sTrailPixelTrack.ends[0].mTangent.GetPlus();
    const f32 laidB = sTrailPixelTrack.ends[1].mTangent.GetPlus();
    char message[1000]; std::snprintf(message,sizeof(message),
        "[trail-pixels] present=%u attempt=%u now=%.6f type=%d segment=%d active=%u matches=%u "
        "a=%.6f,%.6f,%.6f b=%.6f,%.6f,%.6f laid=%.6f,%.6f lastAdded=%.6f elapsed=%.6f "
        "expired=%u worldIndexedAccepted=%llu submitted=%u size=%ux%u format=%u msaa=%u resolved=%u viewport=%u,%u,%u,%u roiValid=%u roi=%u,%u,%u,%u "
        "written=%u/%u rgb=%u alpha=%u roiRgb=%u roiMagnitude=%llu hr=%08X\n",
        suTrailPixelPresent,sTrailPixelClock.attempts,double(sfTrailPixelTime),sTrailPixelTrack.type,sTrailPixelTrack.segment,
        sTrailPixelTrack.active,sTrailPixelTrack.matches,double(a.x),double(a.y),double(a.z),double(b.x),double(b.y),double(b.z),
        double(laidA),double(laidB),double(sTrailPixelTrack.lastAdded),double(sfTrailPixelTime-sTrailPixelTrack.lastAdded),
        sfTrailPixelTime-sTrailPixelTrack.lastAdded > 10.0f ? 1u : 0u,static_cast<unsigned long long>(accepted),
        submitted,
        sTrailPixelDesc.Width,sTrailPixelDesc.Height,u32(sTrailPixelDesc.Format),u32(sTrailPixelDesc.MultiSampleType),
        sTrailPixelDesc.MultiSampleType != D3DMULTISAMPLE_NONE ? 1u : 0u,
        sTrailPixelViewport.X,sTrailPixelViewport.Y,sTrailPixelViewport.Width,sTrailPixelViewport.Height,
        sTrailPixelRect.valid ? 1u : 0u,
        sTrailPixelRect.left,sTrailPixelRect.top,sTrailPixelRect.right,sTrailPixelRect.bottom,
        beforeWritten ? 1u : 0u,afterWritten ? 1u : 0u,delta.rgb,delta.alpha,delta.roiRgb,
        static_cast<unsigned long long>(delta.roiMagnitude),u32(hr));
    CgsDev::Log::WriteToLog(message);
    if (after) after->Release(); if (target) target->Release(); ReleaseTrailPixelsPC();
}
}

static void WatchBlackFramesIfRequested()
{
    static int                siThreshold = -2;   // -2 = not read yet, -1 = off
    static IDirect3DSurface9* spSmall     = nullptr;
    static IDirect3DSurface9* spSys       = nullptr;
    static u32                suBlackRun  = 0u;
    static f32                sfPrevMean  = -1.0f;
    const u32 KU_W = 32u, KU_H = 18u;

    if (siThreshold == -2)
    {
        char lacValue[32];
        DWORD luLen = GetEnvironmentVariableA("BRN_BLACK_FRAME_WATCH", lacValue, sizeof(lacValue));
        siThreshold = (luLen != 0 && luLen < sizeof(lacValue)) ? atoi(lacValue) : -1;
        if (siThreshold >= 0)
        {
            char lacMsg[160];
            std::snprintf(lacMsg, sizeof(lacMsg),
                          "[black-frame] watch armed: threshold=%d (mean 8-bit luminance of a 32x18 shrink of every present)\n",
                          siThreshold);
            CgsDev::Log::WriteToLog(lacMsg);
        }
    }
    if (siThreshold < 0 || renderengine::gDevice == nullptr)
    {
        return;
    }

    IDirect3DSurface9* lpBack = nullptr;
    if (FAILED(renderengine::PCGetBackBuffer(&lpBack)) || lpBack == nullptr)
    {
        return;
    }
    if (spSmall == nullptr)
    {
        if (FAILED(renderengine::gDevice->CreateRenderTarget(KU_W, KU_H, D3DFMT_A8R8G8B8, D3DMULTISAMPLE_NONE, 0,
                                                             FALSE, &spSmall, nullptr))
            || FAILED(renderengine::gDevice->CreateOffscreenPlainSurface(KU_W, KU_H, D3DFMT_A8R8G8B8,
                                                                         D3DPOOL_SYSTEMMEM, &spSys, nullptr)))
        {
            CgsDev::Log::WriteToLog("[black-frame] watch DISARMED: could not create the 32x18 surfaces\n");
            siThreshold = -1;
            lpBack->Release();
            return;
        }
    }
    const HRESULT lhrStretch = renderengine::gDevice->StretchRect(lpBack, nullptr, spSmall, nullptr, D3DTEXF_LINEAR);
    lpBack->Release();
    if (FAILED(lhrStretch) || FAILED(renderengine::gDevice->GetRenderTargetData(spSmall, spSys)))
    {
        return;
    }
    D3DLOCKED_RECT lLock;
    if (FAILED(spSys->LockRect(&lLock, nullptr, D3DLOCK_READONLY)))
    {
        return;
    }
    u64 luSum = 0u;
    for (u32 luY = 0u; luY < KU_H; ++luY)
    {
        const u8* lpRow = static_cast<const u8*>(lLock.pBits) + luY * lLock.Pitch;
        for (u32 luX = 0u; luX < KU_W; ++luX)
        {
            luSum += lpRow[luX * 4u] + lpRow[luX * 4u + 1u] + lpRow[luX * 4u + 2u];   // B, G, R
        }
    }
    spSys->UnlockRect();
    const f32 lfMean = static_cast<f32>(luSum) / static_cast<f32>(KU_W * KU_H * 3u);
    renderengine::gbDispatchLastPresentBlackPC = (lfMean < static_cast<f32>(siThreshold)) && renderengine::guDispatchPresentCountPC > 2000u;

    if (lfMean < static_cast<f32>(siThreshold))
    {
        if (suBlackRun == 0u)
        {
            char lacMsg[200];
            std::snprintf(lacMsg, sizeof(lacMsg),
                          "[black-frame] BEGIN present=%u tick=%llu mean=%.1f prevMean=%.1f draws=%u resolves=%u lastResolveDest=%p world=%u im2d=%u imFullBlack=%u composites=%u\n",
                          renderengine::guDispatchPresentCountPC,
                          static_cast<unsigned long long>(GetTickCount64()), lfMean, sfPrevMean,
                          renderengine::guDiagDraws, renderengine::guDiagResolves, renderengine::gpDiagLastResolveDest,
                          renderengine::guDiagWorldDraws, renderengine::guDiagImBatches, renderengine::guDiagImFullBlack, renderengine::guDiagComposites);
            CgsDev::Log::WriteToLog(lacMsg);
        }
        ++suBlackRun;
        if (suBlackRun > 1u && suBlackRun <= 16u)
        {
            char lacRun[160];
            std::snprintf(lacRun, sizeof(lacRun),
                          "[black-frame]   present=%u mean=%.1f draws=%u resolves=%u lastResolveDest=%p world=%u im2d=%u imFullBlack=%u composites=%u\n",
                          renderengine::guDispatchPresentCountPC, lfMean, renderengine::guDiagDraws,
                          renderengine::guDiagResolves, renderengine::gpDiagLastResolveDest,
                          renderengine::guDiagWorldDraws, renderengine::guDiagImBatches, renderengine::guDiagImFullBlack, renderengine::guDiagComposites);
            CgsDev::Log::WriteToLog(lacRun);
        }

        // Keep the PICTURE of the first two black presents of a window (mid-drive only: presents
        // before 2000 are the boot's loading screens), as top-down 32-bit BMPs beside the exe
        // (`blackframe_<present>.bmp`), so "black" can be told apart from "world missing, HUD
        // drawn" -- a mean of 1.1 with a HUD on screen is the scene / post-fx path, a mean of 0.0
        // is the presenter. Two files per window, cost only when a window opens.
        if (suBlackRun <= 2u && renderengine::guDispatchPresentCountPC > 2000u)
        {
            IDirect3DSurface9* lpFull = nullptr;
            if (SUCCEEDED(renderengine::PCGetBackBuffer(&lpFull)) && lpFull != nullptr)
            {
                D3DSURFACE_DESC lFullDesc;
                lpFull->GetDesc(&lFullDesc);
                IDirect3DSurface9* lpFullSys = nullptr;
                if (SUCCEEDED(renderengine::gDevice->CreateOffscreenPlainSurface(
                        lFullDesc.Width, lFullDesc.Height, lFullDesc.Format, D3DPOOL_SYSTEMMEM, &lpFullSys, nullptr))
                    && SUCCEEDED(renderengine::gDevice->GetRenderTargetData(lpFull, lpFullSys)))
                {
                    D3DLOCKED_RECT lFullLock;
                    if (SUCCEEDED(lpFullSys->LockRect(&lFullLock, nullptr, D3DLOCK_READONLY)))
                    {
                        char lacPath[128];
                        std::snprintf(lacPath, sizeof(lacPath), "blackframe_%06u.bmp", renderengine::guDispatchPresentCountPC);
                        FILE* lpFile = std::fopen(lacPath, "wb");
                        if (lpFile != nullptr)
                        {
                            const u32 luW = lFullDesc.Width, luH = lFullDesc.Height;
                            const u32 luImageBytes = luW * luH * 4u;
                            u8 laHdr[54] = { 'B', 'M' };
                            *reinterpret_cast<u32*>(laHdr + 2)  = 54u + luImageBytes;       // BMP file-format header blob
                            *reinterpret_cast<u32*>(laHdr + 10) = 54u;                      // BMP file-format header blob
                            *reinterpret_cast<u32*>(laHdr + 14) = 40u;                      // BMP file-format header blob
                            *reinterpret_cast<s32*>(laHdr + 18) = static_cast<s32>(luW);    // BMP file-format header blob
                            *reinterpret_cast<s32*>(laHdr + 22) = -static_cast<s32>(luH);   // top-down BMP file-format header blob
                            *reinterpret_cast<u16*>(laHdr + 26) = 1;                        // BMP file-format header blob
                            *reinterpret_cast<u16*>(laHdr + 28) = 32;                       // BMP file-format header blob
                            *reinterpret_cast<u32*>(laHdr + 34) = luImageBytes;             // BMP file-format header blob
                            fwrite(laHdr, 1, sizeof(laHdr), lpFile);
                            for (u32 luRow = 0; luRow < luH; ++luRow)
                            {
                                fwrite(static_cast<const u8*>(lFullLock.pBits) + luRow * lFullLock.Pitch, 1, luW * 4u, lpFile);
                            }
                            fclose(lpFile);
                            CgsDev::Log::WriteToLog("[black-frame] picture written beside the exe\n");
                        }
                        lpFullSys->UnlockRect();
                    }
                }
                if (lpFullSys != nullptr) { lpFullSys->Release(); }
                lpFull->Release();
            }
        }
    }
    else if (suBlackRun != 0u)
    {
        char lacMsg[200];
        std::snprintf(lacMsg, sizeof(lacMsg),
                      "[black-frame] END present=%u tick=%llu after=%u presents mean=%.1f (this present: world=%u im2d=%u composites=%u)\n",
                      renderengine::guDispatchPresentCountPC,
                      static_cast<unsigned long long>(GetTickCount64()), suBlackRun, lfMean,
                      renderengine::guDiagWorldDraws, renderengine::guDiagImBatches, renderengine::guDiagComposites);
        CgsDev::Log::WriteToLog(lacMsg);
        suBlackRun = 0u;
    }
    sfPrevMean = lfMean;
}

static void DumpBackBufferIfRequested()
{
    static char sacDir[512];
    static int siChecked = 0;
    if (siChecked == 0)
    {
        siChecked = 1;
        DWORD luLen = GetEnvironmentVariableA("BRN_FRAME_DUMP", sacDir, sizeof(sacDir));
        if (luLen == 0 || luLen >= sizeof(sacDir)) { sacDir[0] = 0; }
    }
    // [case capture] BRN_FRAME_DUMP_REQUEST=1 switches this private positive-slot
    // run to one requested back-buffer image per owner-checked event. The event name
    // includes this process PID and BRN_HARNESS_SLOT. The unset/default path preserves
    // the existing periodic sampler.
    // FLAG PC-platform leaf: opt-in screenshot request; it does not change game input, state or physics.
    static const bool sbNamedFrameRequest = []() {
        char lacMode[8];
        const DWORD luLen = GetEnvironmentVariableA("BRN_FRAME_DUMP_REQUEST", lacMode, sizeof(lacMode));
        return luLen == 1u && lacMode[0] == '1';
    }();
    static const u32 suNamedFrameSlot = []() {
        if (!sbNamedFrameRequest) return 0u;
        char lacSlot[32];
        const DWORD luLen = GetEnvironmentVariableA("BRN_HARNESS_SLOT", lacSlot, sizeof(lacSlot));
        if (luLen == 0u || luLen >= sizeof(lacSlot)) return 0u;
        char* lpEnd = nullptr;
        const unsigned long luSlot = std::strtoul(lacSlot, &lpEnd, 10);
        if (lpEnd == lacSlot || *lpEnd != '\0' || luSlot == 0u || luSlot > 65535u) return 0u;
        return static_cast<u32>(luSlot);
    }();
    static HANDLE shNamedFrameRequest = nullptr;
    static u32 suNamedFrameSequence = 0u;
    if (sacDir[0] == 0)
    {
        return;
    }
    if (!sbNamedFrameRequest &&
        (renderengine::guDispatchPresentCountPC % renderengine::FrameDumpEvery()) != 0u)
    {
        return;
    }
    if (sbNamedFrameRequest)
    {
        if (suNamedFrameSlot == 0u) return;
        if (shNamedFrameRequest == nullptr)
        {
            char lacEventName[128];
            std::snprintf(lacEventName, sizeof(lacEventName),
                          "Local\\BurnoutPC_FrameRequest_%lu_%lu",
                          static_cast<unsigned long>(GetCurrentProcessId()),
                          static_cast<unsigned long>(suNamedFrameSlot));
            shNamedFrameRequest = OpenEventA(EVENT_MODIFY_STATE | SYNCHRONIZE,
                                             FALSE, lacEventName);
        }
        if (shNamedFrameRequest == nullptr ||
            WaitForSingleObject(shNamedFrameRequest, 0) != WAIT_OBJECT_0)
        {
            return;
        }
    }

    // FLAG PC-platform leaf: align a bounded consecutive final-frame window
    // with optional source readbacks. Default0 retains the existing writer.
    static const u32 suStartPresent = []() {
        const char* lpValue = std::getenv("BRN_FRAME_DUMP_START");
        char* lpEnd = nullptr;
        const unsigned long luValue = lpValue ? std::strtoul(lpValue, &lpEnd, 10) : 0;
        return lpValue && lpEnd != lpValue && *lpEnd == '\0' && luValue <= 1000000u
            ? static_cast<u32>(luValue) : 0u;
    }();
    if (renderengine::guDispatchPresentCountPC < suStartPresent)
        return;

    // [diag] BRN_FRAME_DUMP_ARM=1 -- HOLD the writer until the traffic swerve camera latches,
    // and BRN_FRAME_DUMP_MAX=<n> -- stop after n frames. Both default off, so an ordinary
    // BRN_FRAME_DUMP run is byte-for-byte unchanged.
    //
    // ⭐ WHY, MEASURED. Dumping every 2nd present for a 130 s run writes ~16 GB, and this
    // simulation is FRAME-COUPLED: the run that filmed itself that hard produced ZERO traffic
    // swerves and zero junction-FUP action, where the SAME BINARY unfilmed produced seven
    // swerves and nine RemoveVehicle removals. Filming the whole run destroys the event the
    // film exists to show. Armed + capped, the capture is a few seconds at every present.
    {
        // BRN_FRAME_DUMP_ARM selects WHICH latch holds the writer:
        //   unset / "0"  -- no arm; dump from the first present (the original behaviour)
        //   "slomo"      -- hold until the simulation timestep leaves real time
        //                   (BrnDiag::gFilmLatch, raised by BrnGameModule::UpdateTimers)
        //   "ram[:<mps>]" -- hold until a race-car-vs-traffic outcome opens the [T5-ram]
        //                   window (gT5RamTrafficSlot >= 0) with the player at or above <mps>
        //                   metres per second (default 0), so a traffic-hit film starts at THE
        //                   impact that matters instead of at boot or at the first brush
        //   "skid"       -- hold until the FIRST TYRE MARK is laid (BrnDiag::gFilmLatch.
        //                   muSkidLatched, raised by EffectsModule::HandleWheels beside its
        //                   TrailSystem::AddTrailSegment call), so a drift film starts at the
        //                   frame a mark exists instead of at boot
        //   "dv"         -- hold until the [dv] ONE-STEP VELOCITY WITNESS fires (BrnDiag::
        //                   gFilmLatch.muDvLatched, raised by ExternalPhysicsBody::
        //                   DvWitnessEndStep on the first step whose |dv| crosses BRN_DV_PROBE's
        //                   threshold), so a film of "the car lost 9 m/s in one step" starts at
        //                   that step. Needs BRN_DV_PROBE set as well -- without it the witness
        //                   never runs, the latch never rises and the writer holds for ever,
        //                   which is a SILENT no-dump; check for "[dv] STEP" in the log before
        //                   reading anything into an empty frame directory.
        //   "x15"        -- hold until the SHOWTIME VICTIM GAIN fires (BrnDiag::gFilmLatch.
        //                   muVictimGainLatched, raised by DeformableObject::ApplySensorImpulse
        //                   the first time a car is struck BY a car that is in showtime, i.e.
        //                   the x15 arm at @0x82607D78..0x82607DD0). That event needs three
        //                   things at once that no harness flag can force -- the player in
        //                   showtime, traffic in reach, and a contact between them -- so it is
        //                   rare: one run in six, 48 sensor rows over 15 presents. ⛔ `dv` is
        //                   NOT a substitute: in the run where the gain did fire, the dv latch
        //                   rose 520 presents earlier and a 48-frame strip from it ended long
        //                   before the event. Needs BRN_SHOWTIME_WATCH only for the matching log
        //                   lines; the latch itself is unconditional.
        //   "spark"      -- hold until a SPARK RIBBON REACHES THE DEVICE (BrnDiag::gFilmLatch.
        //                   muSparkDrawLatched, raised by SparkRenderer::Dispatch on its first
        //                   DrawVertices with a non-zero count). Use this and NOT `slomo` to film
        //                   contact sparks: measured 2026-09-06, a 600-frame `slomo` strip over a
        //                   six-shot crash sweep armed at present 2114 and ran out at 3312, while
        //                   the two spark bursts were at ~1530 and ~3430 -- it missed both.
        //   anything else truthy -- hold until the traffic swerve camera latches (the
        //                   original arm; unchanged, so every existing recipe still works)
        static int siArm = -1;      // 0 none, 1 swerve camera, 2 slomo, 3 traffic ram, 4 skid,
                                    // 5 [dv] one-step velocity, 6 showtime victim gain,
                                    // 7 spark ribbon drawn
        static f32 sfRamMinSpeed = 0.0f;
        static u32 suMax = 0u;
        if (siArm < 0)
        {
            char lacArm[32];
            DWORD luArmLen = GetEnvironmentVariableA("BRN_FRAME_DUMP_ARM", lacArm, sizeof(lacArm));
            if (luArmLen == 0 || luArmLen >= sizeof(lacArm) || lacArm[0] == '0')
            {
                siArm = 0;
            }
            else if (_stricmp(lacArm, "slomo") == 0)
            {
                siArm = 2;
            }
            else if (_strnicmp(lacArm, "ram", 3) == 0)
            {
                siArm = 3;
                if (lacArm[3] == ':') { sfRamMinSpeed = static_cast<f32>(atof(lacArm + 4)); }
            }
            else if (_stricmp(lacArm, "skid") == 0)
            {
                siArm = 4;
            }
            else if (_stricmp(lacArm, "dv") == 0)
            {
                siArm = 5;
            }
            else if (_stricmp(lacArm, "x15") == 0)
            {
                siArm = 6;
            }
            else if (_stricmp(lacArm, "spark") == 0)
            {
                siArm = 7;
            }
            else if (_stricmp(lacArm, "assert") == 0)
            {
                siArm = 8;
            }
            else
            {
                siArm = 1;
            }

            char lacMax[32];
            DWORD luMaxLen = GetEnvironmentVariableA("BRN_FRAME_DUMP_MAX", lacMax, sizeof(lacMax));
            if (luMaxLen != 0 && luMaxLen < sizeof(lacMax))
            {
                const int liMax = atoi(lacMax);
                if (liMax > 0) { suMax = static_cast<u32>(liMax); }
            }
        }
        if (siArm == 1 && BrnTraffic::gSwerveWatch.muCameraLatched == 0u)
        {
            return;
        }
        if (siArm == 2 && BrnDiag::gFilmLatch.muSlomoLatched == 0u)
        {
            return;
        }
        if (siArm == 3 && (BrnPhysics::Vehicle::gT5RamTrafficSlot < 0
                           || BrnPhysics::Vehicle::gT5ArmedPlayerSpeed < sfRamMinSpeed))
        {
            return;
        }
        if (siArm == 4 && BrnDiag::gFilmLatch.muSkidLatched == 0u)
        {
            return;
        }
        if (siArm == 5 && BrnDiag::gFilmLatch.muDvLatched == 0u)
        {
            return;
        }
        if (siArm == 6 && BrnDiag::gFilmLatch.muVictimGainLatched == 0u)
        {
        // "spark" -- hold until a spark ribbon actually reaches the device.
        if (siArm == 7 && BrnDiag::gFilmLatch.muSparkDrawLatched == 0u)
        {
            return;
        }
            return;
        }
        if (siArm == 8 && !CgsDev::Assert::gAssertManager.HasAssert())
            return;
        if (suMax != 0u)
        {
            static u32 suWritten = 0u;
            if (suWritten >= suMax) { return; }
            ++suWritten;
        }
    }

    IDirect3DSurface9* lpBack = nullptr;
    if (FAILED(renderengine::PCGetBackBuffer(&lpBack)) || lpBack == nullptr)
    {
        return;
    }
    D3DSURFACE_DESC lDesc;
    lpBack->GetDesc(&lDesc);
    IDirect3DSurface9* lpSys = nullptr;
    if (SUCCEEDED(renderengine::gDevice->CreateOffscreenPlainSurface(
            lDesc.Width, lDesc.Height, lDesc.Format, D3DPOOL_SYSTEMMEM, &lpSys, nullptr)) &&
        SUCCEEDED(renderengine::gDevice->GetRenderTargetData(lpBack, lpSys)))
    {
        D3DLOCKED_RECT lLock;
        if (SUCCEEDED(lpSys->LockRect(&lLock, nullptr, D3DLOCK_READONLY)))
        {
            char lacPath[600];
            std::snprintf(lacPath, sizeof(lacPath), "%s\\bb_%06u.bmp",
                          sacDir, renderengine::guDispatchPresentCountPC);
            FILE* lpFile = std::fopen(lacPath, "wb");
            if (lpFile != nullptr)
            {
                const u32 luW = lDesc.Width, luH = lDesc.Height;
                const u32 luImageBytes = luW * luH * 4u;
                u8 laHdr[54] = { 'B','M' };
                *reinterpret_cast<u32*>(laHdr + 2)  = 54u + luImageBytes;       // BMP file-format header blob
                *reinterpret_cast<u32*>(laHdr + 10) = 54u;                      // BMP file-format header blob
                *reinterpret_cast<u32*>(laHdr + 14) = 40u;                      // BMP file-format header blob
                *reinterpret_cast<s32*>(laHdr + 18) = static_cast<s32>(luW);    // BMP file-format header blob
                *reinterpret_cast<s32*>(laHdr + 22) = -static_cast<s32>(luH);   // top-down BMP file-format header blob
                *reinterpret_cast<u16*>(laHdr + 26) = 1;                        // BMP file-format header blob
                *reinterpret_cast<u16*>(laHdr + 28) = 32;                       // BMP file-format header blob
                *reinterpret_cast<u32*>(laHdr + 34) = luImageBytes;             // BMP file-format header blob
                fwrite(laHdr, 1, sizeof(laHdr), lpFile);
                for (u32 y = 0; y < luH; ++y)
                {
                    fwrite(static_cast<const u8*>(lLock.pBits) + y * lLock.Pitch, 1, luW * 4u, lpFile);
                }
                if (sbNamedFrameRequest)
                {
                    const int liFrameWriteError = ferror(lpFile);
                    const int liFrameCloseResult = fclose(lpFile);
                    if (liFrameWriteError == 0 && liFrameCloseResult == 0 &&
                        shNamedFrameRequest != nullptr && ResetEvent(shNamedFrameRequest))
                    {
                        ++suNamedFrameSequence;
                        char lacAck[256];
                        std::snprintf(lacAck, sizeof(lacAck),
                                      "[frame-request] pid=%lu slot=%u seq=%u present=%u file=bb_%06u.bmp\n",
                                      static_cast<unsigned long>(GetCurrentProcessId()), suNamedFrameSlot,
                                      suNamedFrameSequence, renderengine::guDispatchPresentCountPC,
                                      renderengine::guDispatchPresentCountPC);
                        CgsDev::Log::WriteToLog(lacAck);
                    }
                }
                else { fclose(lpFile); }

                // [diag] Stamp the SIMULATION timestep this frame was rendered under into a
                // sidecar CSV beside the dump. ⭐ WITHOUT IT A CAPTURE OF A TIME DILATION
                // CANNOT BE READ: a drive-thru / crash dilation scales the SIM timer only, so
                // the camera and the HUD keep running at full rate and no eye can tell a
                // dilated frame from an ordinary one. With it, every frame names its own
                // timestep and a strip is self-labelling.
                char lacCsv[620];
                std::snprintf(lacCsv, sizeof(lacCsv), "%s\\frames.csv", sacDir);
                FILE* lpCsv = std::fopen(lacCsv, "a");
                if (lpCsv != nullptr)
                {
                    // Column 4 is the LIVE BOOST/SHOWTIME METER FRACTION the GUI was last
                    // handed (-1 == none published yet). Same argument as columns 2-3: a
                    // bitmap of a bar cannot say whether the bar is tracking anything, and
                    // the log ticks on SIM frames while this ticks on PRESENTS, so pairing
                    // them by time means guessing a frame rate. Stamped here, each frame
                    // names the value it is supposed to be drawing.
                    // Columns 5-10 are THE CHAIN-CRASHING TRAFFIC CAR: its index, its
                    // sympathetic-crash state (1 HEADON 2 ACCEL 3 HANDBRAKE 4 LOCKUP), its
                    // live world position, and the publish counter. Same argument as columns
                    // 2-4 and the same reason they exist: a bitmap of a pile-up cannot say
                    // WHICH car chose to crash, and pairing a log line to a frame means
                    // guessing a frame rate (the log ticks on SIM frames, this ticks on
                    // PRESENTS). With the position stamped into the row, a marker can be
                    // projected from the car's own coordinates into its own frame -- the
                    // trick that turned "a traffic car swerved" into a measured 56 deg over
                    // 13.2 m. Column 10 makes staleness visible: a row whose count equals the
                    // previous row's carries a position nothing refreshed that frame.
                    // Columns 11-14 are THE TYRE MARK: the running count of trail segments
                    // laid (EffectsModule::HandleWheels -> TrailSystem::AddTrailSegment) and
                    // the last one's contact point. Same argument again -- the row where the
                    // count first rises IS the frame the mark started, with no frame-rate
                    // guess, and the position lets a marker be projected into the picture from
                    // the game's own coordinates instead of pointed at by eye.
                    // Columns 15-17 are that segment's SCREEN position: the NDC the skid
                    // vertex program's own transform put it at, and the clip w. They make
                    // "no mark visible" a claim about a named pixel instead of a picture.
                    // Columns 18-20 are THE [dv] ONE-STEP VELOCITY LATCH: the step index, the
                    // [kerb] frame counter and the |dv| of the step that raised it. Same
                    // argument as every column above -- the log's "[dv] STEP n f m" line and
                    // this strip otherwise have no common index, and a `dv`-armed strip is by
                    // construction a picture of ONE event whose identity has to travel with
                    // it. All zero on a run where the witness never fired, which is also the
                    // run where an empty frame directory means the arm held, not that the
                    // dump broke.
                    // Columns 21-24 are THE SCENE-MATCH KEY: the player car's world position
                    // and the live boost-effect mask (BoostStateMachine::OnTick). Same argument
                    // as every column above and one more besides -- they are what lets a
                    // before/after pair of RUNS be matched by where the car was, which a
                    // frame-coupled sim makes impossible by frame index. See the banner on
                    // BrnDiag::FilmLatch::mfCarPosX.
                    std::fprintf(lpCsv, "%u,%.6f,%.6f,%.6f,%d,%d,%.3f,%.3f,%.3f,%u,%u,%.3f,%.3f,%.3f,%.4f,%.4f,%.4f,%u,%u,%.4f,%.3f,%.3f,%.3f,%u\n",
                                 renderengine::guDispatchPresentCountPC,
                                 BrnDiag::gFilmLatch.mfLiveSimScale,
                                 BrnDiag::gFilmLatch.mfLiveSimStep,
                                 BrnDiag::gFilmLatch.mfLiveBoostFraction,
                                 BrnTraffic::gSwerveWatch.miSympVehicle,
                                 BrnTraffic::gSwerveWatch.miSympState,
                                 BrnTraffic::gSwerveWatch.mfSympPosX,
                                 BrnTraffic::gSwerveWatch.mfSympPosY,
                                 BrnTraffic::gSwerveWatch.mfSympPosZ,
                                 BrnTraffic::gSwerveWatch.muSympPublishes,
                                 BrnDiag::gFilmLatch.muTrailSegments,
                                 BrnDiag::gFilmLatch.mfLastSegX,
                                 BrnDiag::gFilmLatch.mfLastSegY,
                                 BrnDiag::gFilmLatch.mfLastSegZ,
                                 BrnDiag::gFilmLatch.mfSegNdcX,
                                 BrnDiag::gFilmLatch.mfSegNdcY,
                                 BrnDiag::gFilmLatch.mfSegClipW,
                                 BrnDiag::gFilmLatch.muDvLatchedStep,
                                 BrnDiag::gFilmLatch.muDvLatchedFrame,
                                 BrnDiag::gFilmLatch.mfDvLatchedMagnitude,
                                 BrnDiag::gFilmLatch.mfCarPosX,
                                 BrnDiag::gFilmLatch.mfCarPosY,
                                 BrnDiag::gFilmLatch.mfCarPosZ,
                                 BrnDiag::gFilmLatch.muBoostEffectMask);
                    std::fclose(lpCsv);
                }
            }
            lpSys->UnlockRect();
        }
    }
    if (lpSys != nullptr) { lpSys->Release(); }
    lpBack->Release();
}

// End the scene and present the back buffer to the window.
void renderengine::Device::ShowPixelBuffer()
{
    if (gDevice == nullptr || !gPresentation.Ready())
    {
        return;
    }
    gDevice->EndScene();
    GpuFrameTimingPC::SceneComplete();
    DumpBackBufferIfRequested();
    WatchBlackFramesIfRequested();   // [diag] BRN_BLACK_FRAME_WATCH (issue #30)
    IDirect3DSurface9* lpFrame = nullptr;
    PCGetBackBuffer(&lpFrame);
    HRESULT lhrPresent;
    {
        FrameProfile::Scope lPresentProfile(FrameProfile::PRESENT);
        lhrPresent = gPresentation.Present(gDevice, hWnd, gVSync != 0, lpFrame);
        GpuFrameTimingPC::OutputComplete(); // also closes an early-out/minimized frame
        if (gPresentation.LastPresentSucceeded()) FrameProfile::Present();
    }
    if (lpFrame) lpFrame->Release();
    // [DIAG] NOT IN THE X360 BINARY -- issue #30: Present's result and the cooperative level, on every
    // present that is not S_OK and on every black present (the watch's flag), rate-limited.
    {
        static u32 suPrinted = 0u;
        static HRESULT shrLast = S_OK;
        if ((lhrPresent != S_OK && lhrPresent != shrLast) || (renderengine::gbDispatchLastPresentBlackPC && suPrinted < 64u))
        {
            shrLast = lhrPresent;
            ++suPrinted;
            IDirect3DSurface9* lpRt0 = nullptr;
            IDirect3DSurface9* lpBb  = nullptr;
            gDevice->GetRenderTarget(0, &lpRt0);
            renderengine::PCGetBackBuffer(&lpBb);
            char lacMsg[200];
            std::snprintf(lacMsg, sizeof(lacMsg),
                          "[present-diag] present=%u hrPresent=0x%08X coop=0x%08X rt0=%p backbuffer=%p%s\n",
                          renderengine::guDispatchPresentCountPC, static_cast<unsigned>(lhrPresent),
                          static_cast<unsigned>(gDevice->TestCooperativeLevel()), static_cast<void*>(lpRt0), static_cast<void*>(lpBb),
                          renderengine::gbDispatchLastPresentBlackPC ? " (black present)" : "");
            if (lpRt0 != nullptr) lpRt0->Release();
            if (lpBb != nullptr) lpBb->Release();
            CgsDev::Log::WriteToLog(lacMsg);
        }
    }
    if (gPresentation.LastPresentSucceeded()) ++renderengine::guDispatchPresentCountPC;
    renderengine::guDiagDraws = 0;   // [DIAG] issue #30 per-present counters
    renderengine::guDiagResolves = 0;
    renderengine::gpDiagLastResolveDest = nullptr;
    renderengine::guDiagWorldDraws = 0; renderengine::guDiagImBatches = 0; renderengine::guDiagImFullBlack = 0; renderengine::guDiagComposites = 0;
}
