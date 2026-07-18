# World-rendering campaign plan (opened 2026-07-18)

User goal (phase 3 of the 2026-07-17 /goal): "start anything needed to get the world
rendering (while staying 1:1 the original game)". Original files:
`D:\Emulation\Emulators\Xenia\Xenia Burnout 5 v6\Burnout_tcartwright`.

## Ground state (2026-07-18)
- dev == l2 content, boot-green to FBURN_MAIN over a black world (fe4d5dc4).
- World data NOW STAGED into build/game (this session): 396 TRK_UNIT<N>_GR.BNDL
  (track-unit graphics, ~700MB), WORLDCOL.BIN (13.4MB collision), WORLDTEX.BIN,
  WORLDVAULT.BIN, MAP_ARTIST/EXTERNAL/INTERNAL.BIN, PVS.BNDL (potentially-visible
  set), GLOBALBACKDROPS.BNDL, GLOBAL/MASSIVETEXTUREDICTIONARY.BIN, MASSIVETABLE,
  SHADERS.BNDL, GLOBALPROPS.BIN + PROPS/, B5TRAFFIC.BNDL, AI.DAT, TRIGGERS.DAT,
  STREETDATA.DAT, DISTRICTS.DAT, SURFACELIST.BIN, CAMERAS/PARTICLES bundles,
  ENVIRONMENTSETTINGS/, POSTFX/, progression + popup + hudmessage data.
  NOT yet staged: VEHICLES/ (619MB), WHEELS/, ENGINES/ (car bring-up phase).

## What exists in the decomp (survey so far)
- BrnRendererModule::Render = frame begin + GUI + loading screen + present; ALL
  world passes ("shadow maps, env map, world/car opaque + transparent, sky,
  coronas, particles, post-fx, MSAA resolve") are documented but data-gated OFF —
  "reconstructed incrementally as their subsystems come online".
- BrnGameModule::Construct builds WorldModule as an EMPTY placeholder class
  (ODR-trap note in BrnGameModule.hpp); GameSource/World/ has IO-layer TUs
  (BrnWorldModuleIO*, WorldEntityModule IO buffers, RaceCar/Traffic entity module
  slices) but no world module body.
- GameDataModule::Prepare creates the 27 memory pools for real ("[5b POOLS]") and
  deliberately skips the streaming-test scaffolding — the GameData ASYNC pipeline
  (VIDEOLIST/track-unit acquire) is the resource edge the world load rides.
- Renderer comment: FOPEN "%sMAP_ARTIST.BIN" memory-map name globals gated in
  BrnGameModule::Construct step 4 — the console memory-maps MAP_ARTIST.BIN at
  boot (the world layout/streaming index).
- The main-flow gates already model the world stages: MemoryCard::Update gates on
  X360 meLoadingStateStage == 8, CompleteLoading stamps stage 7 + gates on
  mbIsCollisionWorldPrepared; ScreenLoading consumes world-load 137 (now fed by
  the PC stand-in); ProfileManager bootup swaps the collision world
  (INVALIDATE→VALIDATE via SetCollisionWorldValid @0x82517F50).

## Campaign slices (leaf-first)
1. **MAP_ARTIST.BIN reader**: the memory-mapped world index. Recover its layout
   from the ARTIST asm (the FOPEN + parse path in BrnGameModule/WorldModule) —
   it names/locates the streamed units. Likely the keystone for everything.
2. **Track-unit bundle format**: TRK_UNIT<N>_GR.BNDL are 'bnd2' bundles (same
   container family as the GUI bundles — the BundleLoader already parses bnd2 on
   PC for FSM/GUIAPT). Enumerate resource types inside a big unit (renderables,
   textures, models — the CgsRw*ResourceType family in
   GameShared/GameClasses/RenderWare/ is partially reconstructed: Raster/
   TextureState/MaterialState/Model/ClusteredMesh/KdTree/Renderable already have
   TUs + the build list carries them!).
3. **WorldModule skeleton**: replace the ODR placeholder with the real module
   (Construct/Prepare/Update per ARTIST), driving the streaming: position →
   PVS/unit selection → GameData async load → RenderWare resource registration.
4. **The renderer world pass**: BrnRendererModule world opaque/transparent walk
   over the registered renderables (D3D9 backend leaf like the Apt one).
5. **Collision (WORLDCOL.BIN)**: the ProfileManager already drives the
   collision-world VALIDATE protocol; wire the real load so
   mbIsCollisionWorldPrepared is real.
6. Vehicles/wheels staging + the player car (separate campaign).

## Verification loop
- tools/diagnostics/hud_shot_pw.ps1 (PrintWindow captures, NEVER foreground) +
  in-game frames; compare against scratch/xenia_truth/.
- cdb-from-launch for crashes; map-resolve via build/game/Burnout_PC.map.

## Session notes
- 2026-07-18: files staged; plan opened. TWO anchors resolved:
  * **MAP_ARTIST.BIN is NOT the world index** — it is the ARTIST build's binary
    DEBUG SYMBOL MAP: header {count=0x7e99 (32409 symbols), 0x10, image base
    0x82000000, 1} then symbol-name records ("void __cdecl `vector constructor
    iterator'..."). The ctor @0x823C9EA8 sprintfs its path into byte_82FAE990
    and registers {off_83018F20, dword_83018F24} for CgsDev::Assert::Manager::
    DisplayCallstack (the console's on-screen callstack symboliser). SIDE VALUE:
    32k name+address pairs = a free extra symbol source for the ARTIST XEX.
  * **The REAL world-streaming entry**: BrnResource::GameDataModule::
    ProcessLoadPropInstancesRequest @0x8266F178 (+ ProcessUnloadPropInstances
    @0x82670F50) builds the "TRK_UNIT%d_GR.BNDL" names — world units stream
    through the GameDataModule REQUEST pipeline (the BrnGameDataRequestQueue /
    RequestInterface_<N> TUs already exist on PC, and GameDataModule::Prepare
    already creates the 27 real pools incl. OpenWorldGr id 3). Slice 1 is now:
    dossier 0x8266F178 (work show / exports), recover the request record + the
    bundle load + the pool-3 registration, and find the REQUEST PRODUCER (the
    WorldModule / PVS side posting unit ids from the camera position).
