# HUD-over-black-world campaign plan (FBURN_MAIN bring-up)

Session 2026-07-17. Owner: the "storage/HUD" Claude session (NOT the aptruntime-retirement
session — see coordination rules at the bottom).
TAKEN OVER 2026-07-17 evening by the (former) retirement session — the HUD session died
mid-verify; its 3 uncommitted fixes reviewed + kept; new goal = boot+drive+HUD verified,
merge to dev, then world rendering.

## 2026-07-17 evening: the loading-screen-over-InGame diagnosis (this session)

Symptom: boot reaches FBURN_MAIN RUNNING (B5RaceHud mounted) but the SCREEN still shows
the boot loading art (cityscape) — the HUD/world are hidden beneath it.

Recovered console chain (ALL attested from the ARTIST exports):
- SCREEN flow FSM (BRNSCREENFSM.BUNDLE Lua, original data): starts at LOADING(46);
  "ENTER_GAME" -> INGAME(4) directly. BrnScreenLoading waits for GUI event 137.
- Event 137 producer: GameState posts game action 191 (payload!=0 -> GuiEvent<136> load
  started / ==0 -> GuiEvent<137> load complete), forwarded by
  BrnGameModule::TranslateGameActionsToGuiEvents @0x823E9CE0 case 191 (file
  GameBridgeGameStateToX.cpp). The producer side is the UNRECONSTRUCTED world/GameState.
- Loading screen visual = BrnGame::LoadingScreenRenderer, command slot +39312 of the
  dispatch input buffer, written by BridgeGuiToGame @0x823CB758: 19->1 SHOW, 20->2 HIDE,
  138->3 SHOWSAVELOADBG (BootProfile posts it), 589->4 / 590->5 fades (BootLegal).
  Type-20 posters on X360 (exhaustive): StateInterface::StopLoadingScreen @0x82476FE0
  (callers: CarSelectMain::Update, Intro::Update — both off the boot path),
  BootLoading::OnLeave @0x82478E88 (BF_LOADING, BRNFLOADFSM — runner not recoverable
  from exports, data-driven), CarSelectUnlock::OnEnter, OnlineNews::OnEnter.
- InGame::OnEnter posts {1,65,12,1} ch40 -> BridgeGuiToGameState @0x823DDB78 case 65 ->
  GameState action 106 ("in-game screen entered"); the world side closes the
  loading-screen lifecycle from there (unreconstructed).
- GuiCache::Construct @0x82505860 calls OptionsDataProfile::Construct(this+47224)
  (defaults brightness/contrast 50) — was missing on PC; ScreenLoading's
  ApplyOptionsDataProfileSettings asserted on the zeroed profile.

PC fixes (this session, uncommitted at time of writing):
1. CgsGuiResourceModule.cpp:669 mbParsed assert — PC guard for MISSING bundles (3rd
   guard alongside the HUD session's two).
2. BrnGameModule.cpp: world-load stand-in — posts GuiEvent<137> per sub-step while
   gBrnInGameStateActive (FLAG'd, action-191 equivalent; registration-filtered).
3. BrnGameModule.cpp BridgeGuiToGame: case 65 consumes the in-game entry notice ->
   gBrnLoadingScreenShouldShow=false (FLAG'd world-load stand-in; console = GameState
   action 106 path).
4. BrnGuiCache.cpp GuiCache::Construct: + GetOptionsDataProfile()->Construct()
   (attested @0x82505860 mid-body).

## Goal
The free-drive HUD (FBURN_MAIN) composes over the (still-black) world when the flow
reaches InGame. Today FBURN_MAIN is a logging link-stub
(BrnHudStatesLinkStubs.cpp: "[HudFlow] FBurnMainHudState::OnEnter -- un-reconstructed").

## Ground truth recovered (IDA 9.3 batch dump of BURNOUT_X360_ARTIST.XEX.i64 — use
## "C:\Program Files\IDA Professional 9.3\idat.exe", the 9.0 install can't open the db;
## always set ida_loader.set_database_flag(DBFL_KILL) before qexit)
- Full dossier: scratch/fburn_dossier.md (11 reviewed functions, pseudocode+callees).
- .rdata dumps: scratch/fburn_rdata.txt + scratch/fburn_rdata2.txt. Highlights:
  * maResourcesToLoad @0x82F26230, count @0x82F2622C = **42 tuples** — verbatim C table
    with names in fburn_rdata2.txt (B5RaceHud + 39 type-7 aux component imports +
    SatNavMap/SatNavMask type-11 textures).
  * Observed events @0x8205AED8 = 56 ids (full list in fburn_rdata.txt).
  * off_82F27BE0 apt-name table: [0]=B5RaceHud [1]=B5CrashedHud [2]=B5CrashedStuntHud
    [3]=B5IdleHud [4]=FLAPTHUD [5]=Overlays.
  * RACE_MAIN: tuples @0x82F25F88, count @0x82F25F84 = 21 (same dump recipe when needed).
  * NOTE: BootProfile's event table @0x8205AB98 dumps as [64, 352, 6] — the committed
    BrnBootProfile.cpp guesses {64, 6, 189} "pinned from dispatch". Re-verify when the
    other agent's BootProfile work lands (do NOT touch now — their file).

## What the X360 state actually does (from the dossier)
- OnEnter @0x8247B0E8: RegisterForEvents(56 ids); post view-option record {8,25,12,1,1.0}
  ch41; FLAPT: FlaptManager::GetFile → root clip → FindChildMovieClip("RaceMainHUD_mc")
  → SetVisible(true) + ResetTimeline; GuiModuleSerialiser::GetStaticLayout→EndMessage;
  Construct+Prepare ~12 components against the FLAPT file ref:
  SatNav(+0x160-ish, X360 offsets), InGameMessages("hudMessages_mc", queue = cache+16512),
  DistrictMarker("marker_mc"), BoostMessageManager("BoostManager"),
  EventHudAnimator("EventHud_Animator", vtbl-dispatched), RoadRule("RoadRule_mc"),
  FriendsList("friendList") + FriendsListChangeIcon("FriendListChange_mc"),
  JunctionInfo("JunctionInfo_mc"), Odometer("Odometer_mc"),
  IdentAnimator("Ident_Animator", vtbl-dispatched); posts GuiEvent records
  {1,94 ch40}, {1,215 ch41 flag=1}, {1,96 ch40 flag=1}, {1,308 ch40}.
- UpdateLoading @0x8247C640: EnsureResourcesAreLoaded(42-tuple list) → optional
  SatNavComponent::LoadResources → post ch41 event-18 record {8,18,12,"B5RaceHud",1}
  (mount/play the HUD apt) → SetExpectedAptComponentList (CLEARS + sets an EMPTY
  64-slot list, count 0 — no init handshake gating!).
- Phase machine: E_INTERNALSTATE loading → WFInit (UpdateWFInit @0x8247C710) →
  SetupState (UpdateSetupState @0x82480EA0) → Running (UpdateRunning @0x8247B660, the
  big per-frame event dispatcher, ~600 lines) + UpdatePermenant @0x824810F0.
- OnLeave @0x82480B88; ProcessAptEvents/ProcessBoostInfo/UpdateSatNav helpers.
- The ctor @0x82508388 (class:BrnGui::FBurnMainHudState, BLOCKED note) installs ~50
  sub-object vtables spanning ~0x5350 bytes — the aggregate layout comes from the
  OnEnter field offsets (field_160 satnav, field_3E8 messages, field_834 marker,
  field_8B0 boost, field_A40/field_ACC event-hud animator pair, field_B10 roadrule,
  field_1040 friends, field_5160 friendChange, field_5178 junction, field_52A8 odometer,
  field_5390 ident animator, tail scalars @0x53C8..0x53D8).

## Distilled phase semantics (from the dossier read, 2026-07-17)
- Internal state member = field_38 (mirrors BootProfile's meInternalState pattern);
  mpGuiCache @+320 (captured from event 64 in UpdateSetupState, asserted
  "Invalid cache in FBurnMainHudState::OnEnter" cpp:1322).
- Phase order: LOADING (UpdateLoading) → SETUP (UpdateSetupState) → WFINIT
  (UpdateWFInit) → RUNNING (UpdateRunning + UpdatePermenant every frame). Update()
  itself is header-inline on X360 (not exported) — reconstruct as the dispatch switch.
  (Order inferred: Loading posts the B5RaceHud mount; Setup captures the cache from
  event 64 and returns 0 until it arrives; WFInit gates on
  AreAllAptComponentsInitialised(flow 1) — trivially true, the expected list is empty.)
- UpdateSetupState: **PAUSE gate** — `cache+19256 == -1 && !cache+80784` →
  SendStateEvent("PAUSE"), stay. (cache+19256 = game-mode/engine-adjacent word set by
  game events; on a world-less PC boot this decides whether the HUD shows or pauses —
  keep faithful, diagnose at runtime.) Then: component-enable bytes +333..+341 all 1,
  +332=1; SatNav SetCachePointer(+352); satnav words from cache+32820/+32824 →
  Enable/DisableSatNavEventsFilter; post {1,555} ch40; InGameMessages gets
  HudMessageController/Director from cache (GuiCache getters TODO) + game mode from
  cache+40536; RoadRule SetCachePointer+InitialiseMode (byte +336).
- UpdateWFInit: if field_150: post {8,327} ch40 24B + road-rule begin sweep
  (IsRoadRuleActive(0..1) → HandleRoadRuleBegin); engine-state byte = cache word
  +19220 (assert <2, "GetPlayerEngineState"); ==1 (ENGINE_ON): post {12,213,1.0,flag1}
  ch41 24B + same ch42, AddOutputAptViewState(field_A40 "apt_Transition","visible"),
  FlaptAnimatorComponent::Run(field_ACC,"visible"), then {1,214,hi1} ch41 16B; else
  the "invisible" mirror ({1,214,hi0} ch41 16B first, {12,213,flag0} ch41 24B, ch42).
  If field_14C: SatNav RecvEvent(213). cache byte +16496 = 1 (hud-ready). If
  field_151: FriendsList SetGuiCachePointer + (cache byte +46870==1 → ChangeIcon
  ShowNow) + AttemptStateRestore. If field_155: field_89A = cache byte +19264. If
  field_153: Odometer TransIn. Return 1 → RUNNING.
- FlaptAnimatorComponent (field_ACC) is RECOVERED (BrnGuiFlaptIconComponent.cpp);
  the vtbl-dispatched pair field_A40/field_ACC = a GuiComponent("EventHud_Animator") +
  FlaptAnimatorComponent. field_5390 = the "Ident_Animator" twin.
- OnLeave @0x82480B88: state word +56 = 4 (leaving); if byte +337 && cache word
  +47212 → FriendsList Close(+4160); UnRegisterForEvents(56); ch41 event-18 EMPTY-name
  unmount {8,18,12,"",1} (B5RaceHud unload, BootProfile's OnLeave idiom);
  MovieClipRef::SetVisible(+324 clipref, false); "transout" on the vtbl animator pair
  (+2112/+2132 slot +12), JunctionInfo::Run(+20856,"transout"),
  FlaptAnimatorComponent::Run(+2764,"transout"), Odometer TransOutActiveText(+21160);
  ch41 {12,213,flag0} 24B; if +332: SatNav RecvEvent(213)+Destruct; if +336: RoadRule
  EndTimers; ch41 {16?,214}16B, ch41 {16,215}16B, ch40 {16,94}16B, ch40 {2,536,hi256}16B,
  ch41 {12,204, 5,6}24B (exact u64-split payloads in the dossier lines 533-590 —
  re-derive when writing; Hex-Rays splits them as v13 u64 constants).
  Member offset cross-check (OnLeave raw vs OnEnter fields): +324 clipref(field_144),
  +352 satnav, +1000 messages, +2100 marker, +2764 flaptAnim(field_ACC), +2832 roadrule,
  +4160 friends(field_1040), +20856 junction(field_5178), +21160 odometer(field_52A8),
  +20880 identAnim(field_5390) region, +2112/+2132 = two vtbl'd sub-animators
  (inside the 0x840..0x854 region — the EventHud pair's inner components).
- UpdatePermenant @0x824810F0 (every frame, all phases): pump the 18432-queue —
  event 309 payload {1,0} → SendStateEvent("PAUSE"); 21 → ProcessAptEvents; 148:
  payload!=0 → re-Enable/DisableSatNavEventsFilter per word +996, payload==0 →
  OutputGuiEvent<GuiAudioEvent>{2,0,-1,-1,-1} + SendStateEvent("PAUSE"); 377 payload
  0-or-2 → (byte +337: FriendsList SaveCurrentState) + SendStateEvent("START_CRASH").
  Then per-frame tails: byte +336 && cache → RoadRule UpdateRoadSignDistances(+2832)
  with the player-position VECTOR loaded from cache+19168 (lvx128 — pseudocode DROPS
  this argument, take it from asm); byte +337 → byte +6361 = (cache word +40536 == -1),
  FriendsList UpdateAptVariables(+4160).
- ProcessAptEvents @0x82475048 (from event 21; payload word0=type, word2=clip-name ptr
  or frame): assert on null; type 1: (+332) SatNav RecvEvent(ev,21); (+341) the
  DistrictMarker frame handler — the callee shows as ICF-folded
  "BaseCollisionGenerator::Destruct"(+2100) (known fold, see
  [[debug-component-and-framework-blocks]] memory — it's really the marker's per-frame
  member init/handler); (+338) JunctionInfo Refresh(+20856, name). type 4
  (transition-complete): strcmp payload name: "RoadRule_mc" → RoadRule
  TransitionComplete(+2832, word1); "hudMessages_mc" → InGameMessages
  EndTransition(+1000); else (+341) DistrictMarker ProcessCountyTransitionComplete +
  ProcessDistrictTransitionComplete(+2100, name). ALWAYS after: (+335) BoostMessageManager
  RecvEvent(+2224, ev, 21, cache). Offsets: boost=+2224 (0x8B0), marker=+2100 (0x834).
- ProcessBoostInfo @0x82474F60: assert non-null ("Invalid event" cpp:1631) then
  (+335) BoostMessageManager RecvEvent(+2224, ev, 206, cache). Called by UpdateRunning.
- UpdateSatNav @0x82475268: assert non-null (" invalid event passed " cpp:1828) then
  (+332) SatNav RecvEvent(+352, ev, id). Called by UpdateRunning (the pass-through for
  the many satnav event ids).
- UpdateRunning @0x8247B660 (RUNNING per-frame; dossier 1001-1622 — re-read when
  writing, this is the summary): pre-loop: if +332, word +656 = 0 and satnav
  sub-object ptr +948 → *(ptr+2448)=0. Event pump over the 18432-queue:
  6 → (+337 && !cache+19287) FriendsList HandleControllerInput(+4160, 8-byte copy);
  79 → (+337 && cache+47212) FriendsList Close; 94 → ChangeIcon Hide(+20832);
  95 → EndWait; 101 → SetTotalFriends(*p); 102 → ProcessNewEntryData(p);
  103 → RequestRefreshedData; 104 → (!cache+19287) ReshowShortcuts;
  106 → (!cache+47212) ChangeIcon AnimateIn(+20832); 154 → (+333) InGameMessages
  AddMessage(+1000,p); 156 → TerminateMessages; 199/200 → UpdateSatNav(p,id);
  205 → OutputViewState<GuiEventShowHideSatNav>{1,0,byte=*p} + (+332) SatNav
  RecvEvent(213); 206 → ProcessBoostInfo; 218 → boost-manager fanout (below);
  221 (boost amount f32): if != prev(+21460): >=0.01 → animator pair (+2624
  AddOutputAptViewState "apt_Transition" "invisible", +2764 FlaptAnimator Run
  "invisible") + OutputViewState<ShowHideBoostBar>{0}; else if cache+19232==1 →
  same pair "visible" + {1}; then ShowHideSatNav{1,0} OutputViewState+
  OutputInternalState; tail: (+332) SatNav RecvEvent(213); prev=+21460=*p;
  222 (PP toggle, +340; assert "lpPPToggle" cpp:909): *p==1 → FlaptAnimator
  Run(+21392,"transIn") + +21448=1,+21456=1,+21452=GuiCache::GetTime+32.0; else
  Run(+21392,"invisible") + zeros; 226 → post {1,60} ch41 16B; 227 → post {1,61}
  ch41 16B; 309/311/314 (>227 switch): 311 → (+338) JunctionInfo
  HandleJunctionChange(+20856, cache+19192, cache+19196) + DistrictMarker
  SetHideCountyIcon(+2100, byte +21145); (+339) Odometer HandleJunctionChange(+21160,p);
  314 → (+339) Odometer HandleDriveThruDiscovered; 333/335/336/338/339/340/341/343 →
  (+336) RoadRule HandleEnterRoadEvent/HandleRoadRuleBegin(*p)/HandleRoadRuleEnd/
  UpdateCurrentTime(*p f32; + words +4140/+4148 lap bookkeeping from p[3],p[4])/
  HandleRoadRuleTargetUpdate (assert "lpRRTargetUpdate" cpp:669)/HandleLeaveRoadEvent
  (*p,p[1] — STATIC call, no this)/HandleUpcomingRoadEvent/SwitchModes(*p);
  350 (progression loaded {Profile*,ProgressionData*}): if profile+112==data+20 →
  byte +21147=1; once (+21464): scan data trophy unlocks (count data+68,
  GetTrophyUnlock(i), skip if +8 car-id 0; FindCar(profile,carId); if
  !GetSeenTrophyUnlockSequence(profile, unlock+4) && car && !car->byte+10 →
  OutputGuiEvent<GuiEventTrophyCarUnlock>{unlock+4, carId} once) then +21464=1;
  364/365/367/368/382-391/394/400/401/218 → assert cache ("mpCache != NULL" cpp:595)
  + BoostMessageManager RecvEvent(+2224, p, id, cache); 379 (engine change, assert
  <2 cpp:772): 1 → animator pair (+2624/+2764) "transin" + ShowHideBoostBar{1}; 0 →
  "transout" + {0}; both → ShowHideSatNav{1,0} view+internal; tail (+332) SatNav
  RecvEvent(213). Post-loop per-frame: (+341) marker frame-handler(+2100)
  (ICF-folded name) + county/district refresh from cache+20384/+20388/+20392
  (SetCounty/SetDistrict + GuiCache::RecEvent(&{county,district,flag},169), guarded by
  hi-byte flag + word +2220, district!=18); (+332) SatNav Update(+352); (+335)
  Boost Update(+2224, *cache f32); (+333) Messages Update(+1000); (+337) Friends
  Update(+4160); (+336) RoadRule Update(+2832, cache mfTimeNow +4; assert
  "mfTimeNow!=-FLT_MAX"); (+339) Odometer Update(+21160); (+340 && +21448) PP-toggle
  re-run timer: if time > +21452 → Run(+21392,"invisible")+Run("transIn"),
  ++*(+21456), +21452 = time + fsel(max(0, n*20-300)... re-derive fsel from asm) + 12.
- Dossier FULLY read + distilled. Write Slice A from these notes; re-read specific
  dossier sections only to double-check payload splits.

## Component audit (2026-07-17, file-existence pass)
- EXIST (headers + cpp): BrnSatNavComponent (Flow/hud/Components/), BrnInGameMessagesComponent,
  BrnRoadRuleComponent, BrnFriendsList + BrnFriendsListChangeIcon (Flow/HUD/Components/),
  BrnDistrictMarkerComponent (GameSource/Gui/View/ !), FlaptAnimator family
  (Flow/Shared/FlaptComponents/BrnGuiFlaptIconComponent.h), BrnBoostMessageItem/Slot.
- MISSING entirely (no files): **BrnOdometerComponent, BrnJunctionInfoComponent,
  BrnBoostMessageManager** — the dossier's "RECOVERED → BrnJunctionInfoComponent.cpp"
  callee note is a stale/phantom ledger mapping (no file on disk; same phantom class as
  the state TU itself). BoostMessageManager symbols are mis-homed to CgsStrStream.h in
  the ledger (demangle artifact — see [[apt-decomp-campaign]] demangle-partials wave).
- The "EventHud_Animator"/"Ident_Animator" vtbl pair = GuiComponent + FlaptAnimatorComponent
  combos (headers exist); OnEnter dispatches their Construct/Prepare via vtable.
- Signature audit: SatNav header = SatNav/BrnSatNavComponent.h but carries ONLY
  SetCachePointer (@0x82473638; ptr @+0x25C) — Construct/Prepare/LoadResources/
  RecvEvent/Update/Destruct NOT reconstructed → DEFER SatNav calls in Slice A.
  RoadRuleComponent.h: Construct(name, iface, ?, ?)+Prepare(name, FileRef&) real —
  check which Handle* exist in its .cpp before wiring the event cases.
  InGameMessagesComponent.h: setters exist (SetController/SetDirector/SetGameMode/
  SetInGameMessagesQueue); Construct/Prepare are [todo] per dossier — check header.
  FlaptAnimatorComponent (Flow/Shared/FlaptComponents/BrnGuiFlaptIconComponent.h):
  virtual Construct(DEBUGName, iface, ?)/Prepare(name, FileRef)/Prepare(clipRef)/Run —
  real, X360-attested. DistrictMarker: GameSource/Gui/View/BrnDistrictMarkerComponent.h.
  FriendsList/ChangeIcon: done TUs.
- Slice A defer set (FLAG'd per call, BootProfile precedent): SatNav, InGameMessages
  Construct/Prepare (header = partial layout, setters real: SetController/SetDirector/
  SetGameMode/SetInGameMessagesQueue), Odometer, JunctionInfo, BoostMessageManager,
  DistrictMarker Construct/Prepare/ProcessCounty*/ProcessDistrict* (View/
  BrnDistrictMarkerComponent.h is a NARROW slice — only SetHideCountyIcon real; the
  dossier's "RECOVERED → Flow/hud/Components/BrnDistrictMarker.cpp" is phantom, no such
  file). Real in Slice A: the clip show + B5RaceHud mount (the actual pixels), phase
  machine, RoadRule (Construct/Prepare real; verify Handle* coverage in its .cpp),
  FriendsList+ChangeIcon (done TUs), FlaptAnimator pairs, DistrictMarker
  SetHideCountyIcon, InGameMessages setters, all event/view-channel records.
- Embedding rule for the aggregate header: per the x64 gate (semantic parity by NAMED
  members, not byte offsets) embed by value the components with complete headers
  (RoadRule, FriendsList, ChangeIcon, FlaptAnimator x2, DistrictMarker, InGameMessages)
  and document each deferred component as an explicit padded/absent member note — do
  NOT invent layouts for Odometer/JunctionInfo/BoostMessageManager/SatNav (SatNav gets
  its narrow existing type only if needed; else a FLAG'd absent-member note).
- Next concrete steps: (1) verify Construct/Prepare signatures of the EXISTING components
  against the dossier calls; (2) write the aggregate BrnFBurnMainHudState.h layout
  (State base @+0x18 iface/+0x18 queue... raw offsets: +24=in-queue, +28=StateInterface,
  +0x38=meInternalState (OnLeave stores 4=LEAVING; enum LOADING=0→SETUP→WFINIT→RUNNING→
  LEAVING like BootProfile), +320=mpGuiCache, +324=clip ref pair {inst,file},
  +332..+341 = the ten component-enable bytes, +352 satnav, +948 satnav-sub ptr,
  +992/+996 satnav words, +1000 messages, +2100 marker, +2224 boost-mgr, +2624/+2764
  eventhud animator pair, +2832 roadrule, +4140/+4148 roadrule laps, +4160 friends,
  +6361 friends byte, +20832 changeicon, +20856 junction, +21145/+21147 bytes,
  +21160 odometer, +21392 ident animator, +21448..+21464 pp-toggle/trophy words);
  (3) write the .cpp replacing the stale fragment: real 42-tuple table + OnEnter/
  Update dispatch/UpdateLoading/SetupState/WFInit/Running/Permenant/OnLeave/
  ProcessAptEvents/ProcessBoostInfo/UpdateSatNav/SetExpectedAptComponentList, with
  Odometer/JunctionInfo/BoostMessageManager calls DEFERRED behind FLAG'd notes (their
  TUs missing — reconstruct in Slice B) exactly like the BootProfile precedent;
  (4) drop FBURN_MAIN from BrnHudStatesLinkStubs.cpp (keep RACE_MAIN/CRASHEDSTNT);
  (5) compile gate + build + boot check for "[HudFlow] FBurnMainHudState" gap-log
  ABSENCE + apt mount log for B5RaceHud.

## Staged slices (leaf-first, per AGENTS.md)
1. **Slice A (visible pixels):** reconstruct the state TU onto the shared header:
   real resource table (42 tuples) + OnEnter's FLAPT clip show + UpdateLoading's
   B5RaceHud mount + the phase machine, with the un-reconstructed component TUs
   deferred exactly like the BootProfile precedent (construct only the components whose
   TUs exist: FriendsList, DistrictMarker, BoostMessageManager; defer SatNav/
   InGameMessages/RoadRule/Odometer/JunctionInfo/animators behind their own TU
   reconstructions — each deferral logged + documented, NOT silently dropped).
   Check first: does the converted FLAPT file in the PC data actually contain
   "RaceMainHUD_mc" and do the GUIAPT bundles carry the 42 aux imports (ids above)?
   (The aux-import-visual gap task #4 in [[gui-fsm-controller-flow]] memory is this.)
2. **Slice B:** component TUs one by one (Odometer → JunctionInfo → RoadRule →
   InGameMessages → SatNav last, it's the minimap/biggest; the two animator components
   need their class TUs identified from the vtbl dispatch).
3. **Slice C:** UpdateRunning's full 56-event dispatch (needs the component surface).
4. RACE_MAIN/CRASHEDSTNT later (same recipe, tables already locatable).

## Verification
- Boot to InGame via the FSM (the flow already enters FBURN_MAIN — the link-stub log
  line proves it); screenshot: HUD elements over black world.
- The interactive harnesses (profile_test.ps1 etc.) are blocked for the agent by the
  permission classifier (keystroke injection) — either the user runs them, or drive
  the accept path via the named event "Local\BurnoutPC_Input_Accept" (see
  profile_test.ps1:41 — SetEvent-only, no keybd_event) if CgsInputPadsPC honours it
  standalone.

## Coordination (CRITICAL)
- Other session owns: BrnGuiAptRuntime.cpp (dirty in main checkout), BrnGuiProfile.{cpp,h}
  + BrnBootProfile.cpp (their worktree), the bootup-prompt rework, save-icon visuals.
- This session owns: GameSource/Gui/Flow/HUD/States/* in-game states (FBurnMain*),
  BrnHudStatesLinkStubs.cpp (will shrink), CgsSaveLoadPC/CgsSaveLoadPS3/CgsSaveLoadX360
  (already pushed e5b6fee0), scratch/fburn_* + this plan.
- Commit only files you authored, by explicit path. Fast-forward push to
  b5-decomp l2-drive-clean; never rebase over the other session's dirty files.
