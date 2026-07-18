# BrnGuiAptRuntime.cpp retirement plan (2026-07-16, Fable session)

## STATUS 2026-07-17 ~01:30 (updated live)

DONE + PUSHED (l2-drive-clean):
- a359638b faithful text-wrap fix (autoSize map + collapse gate)
- 2d1e6149 AAC = real registered observer (hand-fan retired)
- 9f9b823e slice 1: engine-native play path (AptLoadAnimation real @ Apt/Apt.cpp;
  AptLinker::Load loader-name + isDefined-gate fixes; GlobalNotificationFunction
  @0x82B00C78 real -- the {} stub was why nothing ever mounted)
- ae5adac2 slice 2/3: slot machinery DELETED (committed by the PARALLEL session /
  user account at 00:59 -- coordinate!). Boot verified end-to-end to FBURN_MAIN.

SLICE 4 (fonts/language via the real module) -- DESIGN COMPLETE, NOT IMPLEMENTED:
- ViewModule::Construct is REAL + already called (AptAux::Construct inside).
- ViewModule::Prepare (staged: outqueue -> base -> mLanguageManager.Prepare ->
  mAptAux.Prepare) is REAL but NEVER CALLED -- PrepareRuntime bypasses it (drives
  AptAux::Prepare directly; AptBringUpTextSystem does language.Prepare itself).
  => swap PrepareRuntime step 5 + text bring-up for the real staged
  s_pViewModule->Prepare(&aptHeap, nullptr, &languageHeap, nullptr) loop.
- The real GuiResourceModule (CgsGuiResourceModule.cpp) has path formats
  [14] "Language\Fonts\%s.font" (HD) / [15] SD; its START state loads
  PERSISTENTAPT + GUITEXTURES.BIN fire-and-forget. Find who posts font/language
  requests on console (RequestResource ch39? request types: 16=font, 12=language)
  and mirror; the PC servicer (CgsGuiResourceModulePC.cpp ServicePlatformRequests)
  currently answers unknown banks with "completed without IO" -- materialise a
  font bank + language bank there (mirror MaterialiseAptStreamedBankPool),
  CreateTextureState after load (device-gated defer-retry), emit notifications
  type 16 (per font) / 12 (language) via lpOutput->AddLoadNotification -> GuiModule
  bridge -> ViewModule::ProcessIncomingLoadNotification (arms 12/16 already REAL).
- THEN delete from BrnGuiAptRuntime.cpp: AptBringUpTextSystem, AptLoadOneGuiFont,
  AptLoadLanguageBundle, s_aAptFontPools/s_AptLanguagePool/s_pAptBodyFont (only
  self-referenced), s_aLanguageHeap, the s_aPendingLoadNotifications ring +
  QueueLoadNotification + PopPendingLoadNotification (+ the 2 GuiModule drain
  sites ~455/1266), and the facade method. KEEP ordering: fonts' notifications
  must reach the view BEFORE FLAPTHUD's stage-13 instantiation (currently
  guaranteed because the up-front loads precede FLAPTHUD.BUNDLE).
- GetLoadedAptBundleLeadHeader (PC servicer) is now DEAD (DriveFaithfulLoad was
  its only consumer) -- delete it + the lead registry with slice 4.

REMAINING after slice 4: slice 5 (render buffer + dispatch + StartAsyncLoad/
LoadImportBundle re-home to a PC TU), slice 6 (PrepareRuntime remains ->
GuiModule/ViewModule), slice 7 (facade queries + file deletion; BootLegalBoundary
IsMovieComposed -> real GuiCache handshake). Then the USER'S VISUALS: background
image (SaveLoadComponent RedDirt texids 5/8 unbound vs ParadiseLogo 11/14 --
likely GUITEXTURES bank 6, now requestable once materialised!) + save icon.
NOTE: GUITEXTURES.BIN "completed without IO" may be EXACTLY the background-image
root cause -- the imported panel's textures live in that never-loaded bank.

GOAL: delete b5-decomp/src/GameSource/Gui/BrnGuiAptRuntime.cpp(+.h) — the whole Apt/AS
system 1:1 so nothing needs the stand-in. Boot must stay green after every slice
(title → menu → autosave prompt → intro → loading), verified with
tools/diagnostics/boot_test.ps1 + compared against scratch/xenia_truth/ captures.

## Ground facts (verified this session)

- The REAL play chain is ALREADY live end-to-end EXCEPT the engine entry:
  flow state posts channel-41 event 18 → GuiModule DrainFlowOutputQueue case 41 →
  view input queue → ViewModule::Update → ProcessIncomingViewEvents case 18 →
  AptAux::LoadFlashAnimation ("_level%d") → **AptLoadAnimation ← the ONLY stand-in hop**
  (BrnGuiAptRuntime.cpp:2020 parses the level back out and calls AptRuntimeHost::PlayMovie).
- The real AptLoadAnimation @0x82B07AC8 IS exported (the old "no export" comment is wrong):
  strip ".swf" (EndWithRemoveIgnoreCase), reset gbAptBackgroundColourSet (byte_8324D807),
  EAStringC refcount ops, then gpAptTarget->mpLinker->Load(&nameStr, &targetStr).
- AptLinker::Load @0x82B06660 is reconstructed (AptLinker.cpp:282): resolves the
  "_levelN" TARGET VARIABLE via gAptActionInterpreter.getVariable from level-0 root
  (interpreter _level support exists: AptInterp_LookupGlobalFallback), then
  AptLoader::IsLoaded/Load + Notify + thingy list; EMPTY/unloaded name → stub AptFile
  state 6 → that IS the engine-native unload of a level.
- AptLinker::Update @0x82B0CC68 is reconstructed: ticks the loader, mounts completed
  files (MakeCharacterAnimationInst → SetCharacterInst → play-state seed → link notify).
- Per-frame: GuiModule::Update already calls mViewModule.Update (event 26 timestep) →
  AptAux::Update(ms) (mbUpdateFlash=true from ViewModule::Prepare) → AptUpdateTarget
  (AptUpdate.cpp, real) → engine paces/ticks all levels. AptAux::Render → AptRenderTarget
  (AptRenderWalk.cpp, real) fills the Im2d buffer.
- AptLoaderStartAsyncLoad (BrnGuiAptRuntime.cpp:2053) is the ONE permanent PC-platform
  leaf (no async .apt stream on PC): registered-data-first (FindAptData), bundle-IO
  fallback; drives the faithful completion. It must MOVE to a proper PC TU, not die.
- The bundle IO already rides the real GuiResourceModule ([PC] servicer in
  CgsGuiResourceModulePC.cpp); MAIN/PERSISTENTAPT requests already go through it.
- On console BF_PRELOAD (BootPreload) plays "main" @ level 0 via the same channel-41
  path (asm string xref @0x82478110) — check BrnBootPreload recon posts it; the host
  EnsureFrameworkMovie is a stand-in for that.
- PERSISTENTAPT at "level 2" is a HOST INVENTION ("host bring-up choice" comment);
  console keeps it resident as an import/data library via GuiResourceModule state-0
  up-front load — verify whether the console ever MOUNTS it as a movie (audit before
  keeping/removing the level-2 mount).

## RECOVERED DATA (2026-07-17): BootPreload's REAL second-phase preload table

Dumped from the ARTIST i64 via idat 9.3 batch (script pattern:
scratchpad dump_preload_table2.py; idat -A -S<script> "IDA Files/BURNOUT_X360_ARTIST.XEX.i64"
— get_name_ea needs the "BrnGui::BootPreload::..." :: form via idautils.Names()).
Raw dump: scratch/preload_table_dump.txt.
- maSecondPhaseResourcesToLoad @ 0x82F25D10, muSecondPhaseNumResourcesToLoad @ 0x82F25D0C = 68.
- Content by X360 request type: type 7 (FLAPT_HD_BUNDLE) ×58 = the FLApt HUD components
  (B5RaceHud/B5CrashedHud/B5IdleHud/B5ComponentUnity/CountdownIcon/SatNav*/...);
  type 11 (TEXTURE) ×8 = PreRaceBackgroundMask, MainMapBackgroundMask,
  Icons_EventIcon_NotAttempted_Anim, Icons_EventIcon_Completed_Anim, Icons_CrashNavIcon,
  RoadSigns_0, SatNavMap, SatNavMask; type 18 = BRNEVENTFSM; type 20 = pfxhooks (PFX).
- NO fonts/language here — they load via a different console path (find it: who posts
  types 14/15/16 (font) + 12 (localised text)? candidates: the language/SKU system,
  GuiModule's own boot stages, or the first-phase table (maFirstPhaseResourcesToLoad —
  NOT in the IDA names; DWARF says [1])).
- ⚠️ LANDING RISK: writing the real table arms BootPreload::Update's
  GuiCache::EnsureResourcesAreLoaded(68) — every type's acquire must round-trip a load
  NOTIFICATION back to the cache (OnLoadNotification) or the state waits forever
  (current PC servicer answers unknown types "completed without IO" with NO
  notification → pfxhooks/texture acquires would hang the boot). Wire the per-type
  acquire+notification path in the servicer FIRST, then land the table.
- X360 request-type space (DecFIGS enum +1 for values ≥13; verify per use):
  4/5/6=apt movie, 7=flapt HD, 10=flapt persistent, 11=texture, 12=localised-text
  bundle, 14/15=font HD/SD bundle, 16=font data, 18=fsm bundle, 20=pfx.
  DecFIGS enum (CgsGuiResourceModuleIO.h dwarfdump): 13/14=font bundles, 15=fontdata,
  16=fsm bundle — the ViewModule notification arms (12 language, 16 font) are the
  X360-verified values; do NOT trust the DecFIGS values for request numerics.

## Slices (boot-test after each; commit per slice)

1. **AptLoadAnimation real body** (home: SDKs/EATech/Apt/ — check 3.02.02 SDK file
   attribution; likely with AptUpdate.cpp's public-entry family). Delete the stand-in
   at BrnGuiAptRuntime.cpp:2020. The play path then goes engine-native:
   linker Load/Update mounts flow/aux movies; slots stop receiving play calls.
   RISK: DriveFaithfulLoad did extra host steps (resolve movie name via lead header
   for MAIN/PERSISTENTAPT; STEP3 import drive; STEP5 probes) — the linker/loader chain
   covers these via pfnLoadAnimation (AptCallbackFile::LoadAnimation, real) +
   StartAsyncLoad leaf. Framework ordering (FrameworkClassesLive gate) becomes the
   engine's own init-action sequencing.
2. **Framework/persist bring-up**: BootPreload must post PlayAptMovie("main",0)
   (verify recon; fix if it still relies on EnsureFrameworkMovie). Decide PERSISTENTAPT
   mount faithfully (audit console: does any state play it? or data-library only?).
3. **Unload**: route StopMovie/empty-name events through the engine (event 18 with
   empty name already reaches LoadFlashAnimation → linker stub path). Retire
   StopRuntimeMovie/StopRuntimeMovieAtLevel/UnlinkRuntimeMovieSlot + s_bMovieStopped.
   BootLegal's attract remount must still work (b3596d13 fixed the display-list unlink
   — the engine path must reproduce that; test attract loop!).
4. **Fonts/language**: move AptBringUpTextSystem/AptLoadOneGuiFont/AptLoadLanguageBundle
   IO into the GuiResourceModule PC servicer (banks; FONTS + LANGUAGE requests), with
   notifications through the module output (retire the s_aPendingLoadNotifications ring
   + PopPendingLoadNotification; GuiModule already forwards 14s).
5. **PC render backend re-home**: s_AptRenderBuffer + allocator + DispatchRenderBuffer +
   Get3dRendererAssertSatisfier + the ImRendererSet seeding → new marked PC TU (e.g.
   src/pc/gui/AptIm2dRenderBackendPC.cpp or GameShared/.../View/PC/). GuiModule::Render
   consumes it from there. AptLoaderStartAsyncLoad + LoadImportBundle move here too
   (or a sibling PC IO TU) as permanent FLAG'd PC leaves.
6. **PrepareRuntime → real ViewModule::Prepare**: the render-buffer construct + AptAux
   Prepare drive belong in ViewModule::Prepare (@0x82858448 — check its real body for
   the font/text construction) / GuiModule::Prepare. Retire the s_b*Ready flags.
7. **Facade deletion**: replace AptRuntimeHost uses in BrnGuiModule (IsReady/IsMovieLive/
   IsMovieComposed/GetAptRenderBuffer/DispatchRenderResidue/UpdateShimResidue/
   PopPendingLoadNotification) + BrnBootLegalBoundary (IsMovieComposed → the real
   GuiCache AreAllAptComponentsInitialised handshake / 567) + CgsGuiResourceModulePC's
   GetLoadedAptBundleLeadHeader consumer. Delete BrnGuiAptRuntime.cpp/h from tree +
   tools/build_game_exe.bat source list. Full boot verify + Xenia compare.

## In-flight (pre-goal) debts that fold into this campaign
- Background image (task 5): SaveLoadComponent's own RedDirt (147)×6 + logo010 (149)
  shapes place fine but don't render; ParadiseLogo shapes (152/154, texids 11/14) DO.
  texids 5/8 vs 11/14 — texture bind at draw time is the open question. The real
  load chain (AddAptData registrations + GUITEXTURES bank) may fix this natively —
  re-test after slices 1-4; if not, root-cause the mesh mpTexture bind
  (AptFixupGeometryFileNative8 / tex registration in CgsAptRenderHandler).
- Save icon (task 4): drive chain is real now (355 via subscription filter); icon
  render position/visibility verify pending — re-test after the campaign.
- Xenia ground truth: scratch/xenia_truth/x_03_prompt.png shows the full prompt
  background composite + red circular-arrow save icon TOP-LEFT.
- Harness fixes (uncommitted, parent repo): boot_test.ps1 — no ShowWindow (hides the
  game window!), named-event-only input (double-fire fix), by-PID window lookup,
  prompt-accept step. xenia_prompt_capture.ps1 added (scratch/).

## SLICE 4 — FINAL WIRING FACTS (2026-07-17, ready to implement)

- The console requester for fonts IS GuiModule::Prepare stage 13's FIRST table:
  {17,16},{18,16},{19,16} (the comment at BrnGuiModule.cpp:~446 records this from
  ARTIST). Drive it EXACTLY like the second table ({125,7},{196,10} — the working
  64-pass cache/module/RecEvent loop at BrnGuiModule.cpp:476-520): add
  kaFontResources before the FLAPTHUD table, EnsureResourcesAreLoaded + the same
  pump. Fonts then arrive as type-16 notifications BEFORE FLAPTHUD instantiates
  (the ordering trap solved the console way).
- Module banks: miFontBundleBank (type 16) / miLanguageBundleBank (type 12) exist
  (CgsGuiResourceModule.h:193/195). Path templates: type 16 acquires "%s" (font
  DATA name) whose CONTAINER is type 14 "Language\Fonts\%s.font"; type 12 "%s.lang"
  container 13 "Language\%s.bundle".
- The PC servicer needs FOUR new arms: LoadBundleRequest for the font bank (load
  bundle into a new font bank pool + CreateTextureState on each Font entry) and
  for the language bank; AcquireResourceRequest (case 4 ~line 516 — currently FSM
  bank only) for both banks (find-by-name in the bank pool, echo + handle).
- OPEN: how the module maps "<LANG DATABASE>" (id 0) to the SKU bundle name
  ("0002") — grep the real module's RequestResource/name resolution. If deep,
  SPLIT the slice: swap FONTS only (delete the host font loads + their ring
  notifications; keep the host language load + a 1-deep ring for its type-12
  notification), language follows. NEVER let both host+module font loads run in
  one boot — FontCollection has 3 slots and overflows.
- After the swap, delete from BrnGuiAptRuntime.cpp: AptLoadOneGuiFont +
  s_aAptFontPools + s_pAptBodyFont + the font part of AptBringUpTextSystem (+
  language part if slice completes) + the ring when empty + facade
  PopPendingLoadNotification + the GuiModule drain block at ~445-467 (replaced by
  the stage-13 first-table pump). PrepareRuntime's language-manager Prepare moves
  to the real ViewModule::Prepare staged call (slice 6 core; atomic here if the
  language part moves too).

## SLICE 4a DONE (fdf9db3a, 2026-07-17): fonts ride the REAL chain
Stage-13 font table {17,16},{18,16},{19,16} -> cache pump -> module container
("Language\Fonts\%s.font") -> PC servicer font bank (+CreateTextureState) ->
type-16 notifications -> ViewModule::AddFont. AptLoadOneGuiFont + font pools +
body-font latch DELETED (-127 lines; file ~1,050). Boot green (3 fonts register,
title + attract OK). REMAINING text IO: the LANGUAGE bundle only -- its console
request site ("<LANG DATABASE>" id 0 -> SKU bundle name mapping) is NOT in any
reconstructed TU (grep empty); recover it from the X360 module's RequestResource
/name-resolution path (work show dossiers) before swapping; until then the host
queue carries its single type-12 record.

## LANGUAGE REQUEST SITE — DATA FOUND (2026-07-17)
The console maps language enum -> bundle name via a 48-byte-record .rdata array
(XEX file off ~0xE8BAF; records carry "0001","0002","0003","0006","0005","0007",
"0004" at +0 of each, i.e. enum order != numeric order; English -> "0002" matching
the host's static pick). No "%04d" format exists — the name comes from this table,
then "Language\%s.bundle" (template 13). NEXT: find the reader (the language/SKU
selection TU — CgsLanguage/BrnLanguage family; work show dossiers around
LanguageManager + the E_LANGUAGE enum asserts) and reconstruct the request site;
then the language swap mirrors slice 4a exactly (language bank arm exists in the
plan; ViewModule arm 12 is real). Until then the host queue carries one type-12
record (AptLoadLanguageBundle).

## SLICE 5a ATTEMPT FAILED + REVERTED (2026-07-17 ~13:00)
Re-homing the Im2d buffer/allocator/dispatch/sentinel to
GameShared/GameClasses/Gui/PC/CgsAptRenderBackendPC.cpp(+.h) (files still on
disk, NOT in the build) broke the boot REPRODUCIBLY: BootLegal stalls at stage 0
(WAIT_CACHE), no render dispatch one-shot, no view font-registration prints --
while fonts/movies/imports all load normally. Reverting ONLY the
BrnGuiAptRuntime.cpp edits + the build-list line restored green. Root cause NOT
identified -- prime suspects: (a) the python anchor-cut in PrepareRuntime
removed/reordered something between the STEP 3/STEP 4 anchors beyond step 3
itself (do the re-do with hand-reviewed Edit diffs, not regex surgery); (b) the
renderer-set seed in step 4 now reads the PC TU accessors -- verify the seed
still happens BEFORE the first GuiModule::Render (static-init/link-order of the
new TU vs the runtime TU is a real difference); (c) GuiModule::Render's
lpAptBuffer null-gate vs IsAptIm2dRenderBufferReadyPC timing. Next attempt:
smallest possible diff -- move ONLY the dispatch body first (keep the buffer +
seed in place), boot-test, then move the buffer.

## SLICE 5 STEP A LANDED (9e26d802); STEP B FAILED TWICE + REVERTED (2026-07-17)
Step A (the parameterised Swap->Clear->Dispatch flush in
GameShared/GameClasses/Gui/PC/CgsAptRenderBackendPC.cpp) is GREEN + pushed.
Step B (moving the AptIm2dRenderBuffer INSTANCE + bump allocator + 3d sentinel
into that TU) reproducibly kills the boot: BootLegal stalls at stage -1->0 (the
per-frame cache event stops arriving => almost certainly a CRASH at the first
render after BF_LEGAL entry), no dispatch probe. Mirroring the runtime TU's full
render include set did NOT fix it => not a simple include-order/ODR effect at
compile level. Suspects for the dedicated debug session: instantiation
differences of ImRenderBuffer<V>'s D3D9 method bodies across TUs (compare the
.map/COMDAT pick for Swap/Clear/Dispatch/Prepare between step A and step B
builds), or a layout/alignment delta of the buffer object between the two TUs
(dump sizeof/offsetof from both TUs). Debug with cdb + Burnout_PC.map (the
filtered cdb one-liner missed the fault; use scratch resolve_map.py pattern).
Meanwhile the tree is at step A (buffer stays in BrnGuiAptRuntime.cpp).

## SLICE 6 RETRY (2026-07-17 later): mbIsNewModule FOUND + LANDED; the swap still stalls
The base-stage hang was solved: guest `*(this+4)=1` in ViewModule::Construct is
mbIsNewModule=true (stage stores go to +8 -- see the ALLOCINPUT comment's asm),
landed as its own commit. WITH the store, ViewModule::Prepare COMPLETES (step5
logs done; fonts pump green) but the boot then stalls in GuiModule::Prepare's
SECOND stage-13 pump: FLAPTHUD's bundle loads, but the module never posts MAIN's
LoadBundleRequest (no GuiApt\MAIN.bundle line; 38-line log). Something about
running the FULL ViewModule::Prepare (out-queue Prepare + skipped base stages +
language at step 5) perturbs the module request machine or an assert blocks
between the FLAPTHUD registration and the MAIN request. NEXT: instrument the
64-pass pump (log per-pass EnsureResourcesAreLoaded verdicts + the module
acquire stage) OR run cdb for a blocked-assert stack. The swap edits are exact
in this section's history -- re-apply from the reflog once the stall is solved.

## SLICE 6 LANDED (5b434352, 2026-07-17): the REAL staged ViewModule::Prepare drives the bring-up
Root cause of the earlier stall/crash chain, in order: (1) mbIsNewModule=true was
the missing guest store (2b263729); (2) the "stall" after the pump was actually
an AV -- Prepare is VIRTUAL, dispatching to BrnGui::ViewModule::Prepare whose
FLAPT stage prepared the FlaptManager with the null 4th arg; the one-shot state
machine then never re-seeded, and FLAPTHUD's registration Malloc'd from null
(cdb stack resolved via the map). Fix: the Flapt linear rides
AptRuntimeHost::Prepare(view, linear) explicitly, created before the view
prepare; GuiModule's separate FlaptManager::Prepare call retired. Boot green.
REMAINING in BrnGuiAptRuntime.cpp (~1,010 lines): PrepareRuntime (thin driver +
readiness flags now), language bundle IO + the 1-record ring, LoadImportBundle +
AptLoaderStartAsyncLoad (permanent PC leaf -> re-home), the render buffer +
allocator (step-B, blocked on the cross-TU mystery), facade queries.

## STEP-B ROOT CAUSE NARROWED + EXPERIMENT STAGED (2026-07-17 afternoon)
The step-B failure is NOT a crash: a non-invasive cdb attach caught an INFINITE
LOOP in ImRenderBuffer<V>::Dispatch -> GetNextCommand (a never-terminating
command-stream walk) under GuiModule::Render -> DispatchRenderResidue. Step A
(green) already used the PC TU's Dispatch instantiation, so the delta is the
buffer's Construct/Prepare instantiating in the PC TU => a writer/reader
stream-format disagreement. EXPERIMENT STAGED (uncommitted, gate-passing):
the buffer OBJECT stays in CgsAptRenderBackendPC.cpp but the runtime TU performs
Construct+Prepare through new accessors (GetAptRenderBufferAllocatorPC /
SetAptIm2dRenderBufferReadyPC) -- green boot pins the instantiation context as
the poison; still-looping pins object placement. BLOCKED ON LINK: the concurrent
session's in-flight HUD work (BrnFBurnMainHudState.h edits + a new
RoadRuleComponent::Construct overload) breaks the shared exe link; my 3
cooperative build-list additions were reverted (their dependency web is
incomplete mid-flight). Run the experiment as soon as the shared tree links.

## LANGUAGE READER LANDED (e27f2afe, 2026-07-17): Sku::Update @0x828662B8 homed
The console language-request pump is fully reconstructed in CgsSku.cpp with the
recovered rodata tables (BUNDLE "000N" @0x820E5AD0 / RESOURCE "*.lang"
@0x820E5DD0, ELanguage-indexed: EN_US=7->0001, EN_UK=8->0002, FR=10, DE=11,
IT=15, JA=16, ES=22). The caller is GuiModule::Update (xref-attested).
REMAINING FOR THE LANGUAGE SWAP (4b, boot-blocked until the shared tree links):
1. GuiModule: an mSku member (Construct'd with the module) + mSku.Update(
   &mModelInputBuffer's load-requests path, mpOutputBuffer) in Update -- CHECK
   how the ch-39 model-input requests reach the resource module (the cache's
   StateLoadingHelper posts into the same queue; Sku posts DIRECTLY via
   AddResourceRequests) -- likely already drained by DispatchGuiResourceModule.
2. A PC arm: SetLanguage(E_LANGUAGE_ENGLISH_UK /*0002, the attested PC table*/)
   at GuiModule::Prepare (FLAG PC leaf: console arms from the dash language via
   HardwareSku::FindLanguage -- the PC HardwareSku can return EN_UK faithfully).
3. Servicer: the language bank arm (case 2 LoadBundleRequest miLanguageBundleBank
   -> load "Language\0002.bundle" into a language bank pool; case 4 acquire arm
   FindResource by the hashed "english_uk.lang" id) -- NOTE the PC data ships
   LANGUAGE/0002.bundle (upper dir) vs template "Language\%s.bundle" ✓ case-
   insensitive FS. VERIFY the loaded Language resource (0x27) rides the generic
   SEND_NOTIFICATIONS type-12 sweep -> ViewModule LoadStringTable arm (real).
4. DELETE from BrnGuiAptRuntime.cpp: AptLoadLanguageBundle + s_AptLanguagePool +
   the ring + PopPendingLoadNotification + facade + the GuiModule drain block;
   AptBringUpTextSystem then reduces to nothing -> delete + its call.
