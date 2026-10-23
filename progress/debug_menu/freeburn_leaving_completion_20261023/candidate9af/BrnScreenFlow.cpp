#include "GameSource/Gui/Flow/Screen/BrnScreenFlow.h"

#include <new>   // placement new (the pool states are carved from the linear allocator)

#include "GameShared/GameClasses/Core/CgsID.h"                          // CgsIDCompress
#include "GameShared/GameClasses/Core/CgsAssert.h"                      // CGS_ASSERT
#include "GameShared/GameClasses/Memory/CgsLinearMalloc.h"             // CgsMemory::LinearMalloc
#include "GameShared/GameClasses/Gui/Model/State/CgsGuiStateMachine.h" // CgsGui::StateMachine
#include "GameShared/GameClasses/Gui/Model/State/CgsGuiState.h"        // CgsGui::State

// The committed screen states (REAL classes; constructed exactly as the X360 Prepare does).
#include "GameSource/Gui/Flow/Screen/States/BrnIntro.h"
#include "GameSource/Gui/Flow/Screen/States/BrnCarSelectVehicle.h"
#include "GameSource/Gui/Flow/Screen/States/BrnCarSelectUnlock.h"  // the real CS_UNLOCK (p0 wave; NewPoolState needs the complete type)
#include "GameSource/Gui/Flow/Screen/States/BrnCarSelectLivery.h"
#include "GameSource/Gui/Flow/Screen/States/BrnCarSelectOnlineEnd.h"
#include "GameSource/Gui/Flow/Screen/States/BrnScreenLoading.h"
#include "GameSource/Gui/Flow/Screen/States/BrnInGame.h"
#include "GameSource/Gui/Flow/Screen/States/BrnCrashNavMapEvent.h" // the real CN_MAP_EVENT (p0 wave; NewPoolState needs the complete type)
#include "GameSource/Gui/Flow/Screen/States/BrnCrashNavMapMain.h"  // the real CN_MAP_MAIN (main-menu wave; NewPoolState needs the complete type)
#include "GameSource/Gui/Flow/Screen/States/BrnCrashNavStats.h"
#include "GameSource/Gui/Flow/Screen/States/BrnCrashNavSettings.h"
#include "GameSource/Gui/Flow/Screen/States/BrnCrashNavProfile.h"   // the real CN_PROFILE (NewPoolState needs the complete type)
#include "GameSource/Gui/Flow/Screen/States/BrnCrashNavOptions.h"
#include "GameSource/Gui/Flow/Screen/States/BrnCrashNavAccountManagement.h"
#include "GameSource/Gui/Flow/Screen/States/BrnCrashNavTrax.h"
#include "GameSource/Gui/Flow/Screen/States/BrnCredits.h"
#include "GameSource/Gui/Flow/Screen/States/BrnCrashNavColourCalibrate.h"
#include "GameSource/Gui/Flow/Screen/States/BrnCrashNavDriverDetails.h"
#include "GameSource/Gui/Flow/Screen/States/BrnCrashNavEnterOnlineMod.h"
#include "GameSource/Gui/Flow/Screen/States/BrnPauseScreen.h"
#include "GameSource/Gui/Flow/Screen/States/BrnVideo.h"
#include "GameSource/Gui/Flow/Screen/States/BrnImageGallery.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlinePlay.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineCustomMatch.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineCreateFreeburn.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineSelectRoute.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineGameOptions.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineGameOptionsSummary.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineScoreboards.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineStats.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineQuickMatch.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineGameRoomPlayerInfo.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineNews.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineRivals.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineQuickCustomCreate.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineFBurnQuickCustomCreate.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineViewChallenges.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineLoading.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlinePause.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineMarkMan.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlinePreEvent.h"
#include "GameSource/Gui/Flow/Screen/States/OnlineYouWin.h"
#include "GameSource/Gui/Flow/Screen/States/BrnGenericForwardState.h"
#include "GameSource/Gui/Flow/Screen/States/BrnReplayLoading.h"
#include "GameSource/Gui/Flow/Screen/States/BrnReplayMain.h"
#include "GameSource/Gui/Flow/Screen/States/BrnReplayOutro.h"
#include "GameSource/Gui/Flow/Screen/States/BrnNull.h"
#include "GameSource/Gui/Flow/Screen/States/BrnOnlineTeamSelection.h"
#include "GameSource/Gui/Flow/Screen/States/Replays/BrnReplayClips.h"
#include "GameSource/Gui/Flow/Screen/States/Replays/BrnReplayClipsOnline.h"
#include "GameSource/Gui/Flow/Screen/States/Replays/BrnReplayOptions.h"
#include "GameSource/Gui/Flow/Screen/States/Replays/BrnReplayIntro.h"
#include "GameSource/Gui/Flow/Screen/States/Replays/BrnReplayCredits.h"
#include "GameSource/Gui/Flow/Screen/States/BrnBrnDebug.h"
#include "GameSource/Gui/Flow/PostEvent/States/Offline/BrnOfflineInstantResults.h"
#include "GameSource/Gui/Flow/PostEvent/States/Offline/BrnCompletedGame.h"
#include "GameSource/Gui/Flow/PostEvent/States/Offline/BrnOfflineRivalShutdown.h"
#include "GameSource/Gui/Flow/PostEvent/States/Offline/BrnOfflineTrophyCarUnlock.h"
#include "GameSource/Gui/Flow/PostEvent/States/Online/BrnOnlineInstantResults.h"
#include "GameSource/Gui/Flow/PostEvent/States/Showtime/BrnShowtimeInstantResults.h"

// ===========================================================================
//  BrnGui::BrnScreenFlow -- reconstructed from BURNOUT_X360_ARTIST.XEX. The screen flow owns
//  the 61-state front-end pool and installs it into the embedded CgsGui::StateMachine; the
//  BRNSCREENFSM Lua script the GuiFsmController loads (PrepareLua) then SetState()s the
//  matching script id (NULL, INTRO, CS_VEHICLE, ...).
//
//  Prepare @0x82523E50 (this TU) -- the BrnHudFlow/BrnOverlayFlow idiom: the inlined
//  BrnBaseFlow::Prepare (EventObserver::Prepare + StateMachine::SetStateInterface, de-inlined
//  back to the base call), the PrintStateSizes virtual dispatch (vtbl +0x18 @0x82523E94),
//  then sixty-one LinearMalloc carve-outs -- each placement-constructed (the X360 inlines the
//  trivial ctors as vtable stores; the C++ default ctors reproduce them) -- the gathered
//  61-slot state table, the per-slot null assert (BrnScreenFlow.cpp:227), one
//  Construct(CgsIDCompress(script id), &state machine) per state (vtbl +0x18; CN_PROFILE's is
//  the DIRECT wider CrashNavProfile::Construct(id, fsm, ProfileManager&)), and one
//  SetStates(..., 61).
// ===========================================================================

namespace BrnGui
{
namespace
{
    // Carve one state object out of the flow's linear allocator and default-construct it in
    // place. The X360 placement-new'd a fixed sizeof into each LinearMalloc block (and stored
    // 0 on overflow -- the state-list assert below is the tripwire); the PC-faithful
    // translation uses sizeof(T) (x64 layouts differ) + the C++ ctor.
    template <typename T>
    T* NewPoolState(CgsMemory::LinearMalloc* lpLinearMalloc)
    {
        void* lpMem = lpLinearMalloc->Malloc(sizeof(T));
        return lpMem ? new (lpMem) T() : 0;
    }
}

// BrnScreenFlow.cpp:42 (DWARF) -- tail-chains BrnBaseFlow::Construct (the GUI cache passes
// straight through; the X360 emitted no TU-local copy -- ICF with BrnHudFlow @0x824F1E78).
void BrnScreenFlow::Construct(GuiCache* lpGuiCache)
{
    BrnBaseFlow::Construct(lpGuiCache);
}

// BrnScreenFlow.cpp:293 (DWARF) -- BrnBaseFlow::Update wrapped in the screen-flow CPU perf
// monitor (BrnGuiPerfmons' "Gui - ScreenFlow Update"); no TU-local X360 copy (ICF with
// BrnHudFlow @0x82508620).
void BrnScreenFlow::Update()
{
    // FLAG: the X360 brackets this with CgsDev::PerfMonCpu::Start/StopMonitor (the
    // ScreenFlow-update monitor id) -- a profiling-only span, omitted exactly as the
    // reviewed sibling BrnHudFlow::Update omits its HUD-flow monitor.
    BrnBaseFlow::Update();
}

// BrnScreenFlow.h:226 (DWARF: declared with an inline header body; the X360 emitted no
// out-of-line copy, so the body is reconstructed from the declaration + the enter-online
// state pair). Out-of-line on PC because the header only forward-declares the state types.
bool BrnScreenFlow::IsInEnterOnlineState()
{
    CgsGui::State* lpCurrentState = GetStateMachine().GetCurrentState();
    return lpCurrentState == static_cast<CgsGui::State*>(mpStateCrashNavEnterOnlineFull)
        || lpCurrentState == static_cast<CgsGui::State*>(mpStateCrashNavEnterOnlineNoTitle);
}

// @ 0x824F2150 -- dev dump of every state's name + X360 sizeof + the pool total, streamed
// through BrnGui::BrnBaseFlow::PrintSingleSize behind the CgsDev::Message log filter
// ("BrnScreenFlow" / "NullState 56" ... "TOTAL : <sum>"). The roster it prints is the
// authoritative state/size table documented on the header's member list.
// FLAG PC-platform leaf: print-only dev diagnostic deferred -- BrnBaseFlow::PrintSingleSize
// (the X360 helper every line goes through) is not yet reconstructed in BrnBaseFlow.h, and
// this TU cannot fork a local copy of it; no game-visible behaviour is lost.
void BrnScreenFlow::PrintStateSizes()
{
}

// @ 0x82523E50 -- base prepare, the PrintStateSizes dispatch, then build + install the
// 61-state screen pool.
bool BrnScreenFlow::Prepare(CgsGui::GuiAccessPointers* lpAccessPointers,
                            rw::IResourceAllocator* lpAllocator,
                            CgsMemory::LinearMalloc* lpLinearMalloc,
                            ProfileManager& lrProfileManager)
{
    // Base flow prepare (the X360 inlines it: EventObserver::Prepare + the state machine's
    // SetStateInterface), then the state-size dev dump (vtbl +0x18 dispatch @0x82523E94).
    BrnBaseFlow::Prepare(lpAccessPointers, lpAllocator);
    PrintStateSizes();

    CgsGui::StateMachine& lStateMachine = GetStateMachine();

    // Allocate the 61 states (X360 build order -- note CS_VEHICLE before CS_UNLOCK and
    // ON_PRE_EVENT before ON_MARK_MAN, exactly as the X360 Prepare interleaves them).
    mpStateNull                       = NewPoolState<NullState>(lpLinearMalloc);
    mpStateIntro                      = NewPoolState<Intro>(lpLinearMalloc);
    mpStateCarSelectVehicle           = NewPoolState<CarSelectVehicle>(lpLinearMalloc);
    mpStateCarSelectUnlock            = NewPoolState<CarSelectUnlock>(lpLinearMalloc);
    mpStateCarSelectLivery            = NewPoolState<CarSelectLivery>(lpLinearMalloc);
    mpStateCarSelectOnlineEnd         = NewPoolState<CarSelectOnlineEnd>(lpLinearMalloc);
    mpStateLoading                    = NewPoolState<ScreenLoading>(lpLinearMalloc);
    mpStateInGame                     = NewPoolState<InGame>(lpLinearMalloc);
    mpStateCrashNavMapEvent           = NewPoolState<CrashNavMapEvent>(lpLinearMalloc);
    mpStateCrashNavMapMain            = NewPoolState<CrashNavMapMain>(lpLinearMalloc);
    mpStateCrashNavStats              = NewPoolState<CrashNavStats>(lpLinearMalloc);
    mpStateCrashNavSettings           = NewPoolState<CrashNavSettings>(lpLinearMalloc);
    mpStateCrashNavProfile            = NewPoolState<CrashNavProfile>(lpLinearMalloc);
    mpStateCrashNavOptions            = NewPoolState<CrashNavOptions>(lpLinearMalloc);
    mpStateCrashNavAccountManagement  = NewPoolState<CrashNavAccountManagement>(lpLinearMalloc);
    mpStateCrashNavTrax               = NewPoolState<CrashNavTrax>(lpLinearMalloc);
    mpStateCredits                    = NewPoolState<Credits>(lpLinearMalloc);
    mpStateColourCalibration          = NewPoolState<CrashNavColourCalibrate>(lpLinearMalloc);
    mpStateDriverDetails              = NewPoolState<CrashNavDriverDetails>(lpLinearMalloc);
    mpStateCrashNavEnterOnlineFull    = NewPoolState<CrashNavEnterOnlineFull>(lpLinearMalloc);
    mpStateCrashNavEnterOnlineNoTitle = NewPoolState<CrashNavEnterOnlineNoTitle>(lpLinearMalloc);
    mpStatePause                      = NewPoolState<PauseScreen>(lpLinearMalloc);
    mpStateVideo                      = NewPoolState<Video>(lpLinearMalloc);
    mpStateImageGallery               = NewPoolState<ImageGalleryState>(lpLinearMalloc);
    mpStateOnlinePlay                 = NewPoolState<OnlinePlay>(lpLinearMalloc);
    mpStateOnlineGameRoom             = NewPoolState<OnlineGameRoomPlayerInfo>(lpLinearMalloc);
    mpStateOnlineCustomMatch          = NewPoolState<OnlineCustomMatch>(lpLinearMalloc);
    mpStateOnlineCreateFreeburn       = NewPoolState<OnlineCreateFreeburn>(lpLinearMalloc);
    mpStateOnlineSelectRoute          = NewPoolState<OnlineSelectRoute>(lpLinearMalloc);
    mpStateOnlineGameOptions          = NewPoolState<OnlineGameOptions>(lpLinearMalloc);
    mpStateOnlineGameOptionsSummary   = NewPoolState<OnlineGameOptionsSummary>(lpLinearMalloc);
    mpStateOnlineScoreboards          = NewPoolState<OnlineScoreboards>(lpLinearMalloc);
    mpStateOnlineStats                = NewPoolState<OnlineStats>(lpLinearMalloc);
    mpStateOnlineQuickMatch           = NewPoolState<OnlineQuickMatch>(lpLinearMalloc);
    mpStateOnlineNews                 = NewPoolState<OnlineNews>(lpLinearMalloc);
    mpStateOnlineRivals               = NewPoolState<OnlineRivals>(lpLinearMalloc);
    mpStateOnlineTeamSelection        = NewPoolState<OnlineTeamSelection>(lpLinearMalloc);
    mpStateOnlineQuickCustomCreate    = NewPoolState<OnlineQuickCustomCreate>(lpLinearMalloc);
    mpStateOnlineFBurnQuickCustCreate = NewPoolState<OnlineFBurnQuickCustomCreate>(lpLinearMalloc);
    mpStateOnlineViewChallenges       = NewPoolState<OnlineViewChallenges>(lpLinearMalloc);
    mpStateOnlineLoading              = NewPoolState<OnlineLoading>(lpLinearMalloc);
    mpStateOnlinePause                = NewPoolState<OnlinePause>(lpLinearMalloc);
    mpStateOnlinePreEvent             = NewPoolState<OnlinePreEvent>(lpLinearMalloc);
    mpStateOnlineMarkMan              = NewPoolState<OnlineMarkMan>(lpLinearMalloc);
    mpStateOfflineInstantResults      = NewPoolState<InstantResultsState>(lpLinearMalloc);
    mpStateOfflineCompletedGame       = NewPoolState<CompletedGame>(lpLinearMalloc);
    mpStateOfflineRivalShutdown       = NewPoolState<OfflineRivalShutdown>(lpLinearMalloc);
    mpStateOfflineTrophyCarUnlock     = NewPoolState<OfflineTrophyCarUnlock>(lpLinearMalloc);
    mpStateOnlineInstantResults       = NewPoolState<OnlineInstantResultsState>(lpLinearMalloc);
    mpStateOnlineYouWin               = NewPoolState<OnlineYouWin>(lpLinearMalloc);
    mpStateShowtimeInstantResults     = NewPoolState<ShowtimeInstantResultsState>(lpLinearMalloc);
    mpStateGenericForward             = NewPoolState<GenericForwardState>(lpLinearMalloc);
    mpStateReplayClips                = NewPoolState<ReplayClips>(lpLinearMalloc);
    mpStateReplayClipsOnline          = NewPoolState<ReplayClipsOnline>(lpLinearMalloc);
    mpStateReplayOptions              = NewPoolState<ReplayOptions>(lpLinearMalloc);
    mpStateReplayLoading              = NewPoolState<ReplayLoading>(lpLinearMalloc);
    mpStateReplayIntro                = NewPoolState<ReplayIntro>(lpLinearMalloc);
    mpStateReplayMain                 = NewPoolState<ReplayMain>(lpLinearMalloc);
    mpStateReplayOutro                = NewPoolState<ReplayOutro>(lpLinearMalloc);
    mpStateReplayCredits              = NewPoolState<ReplayCredits>(lpLinearMalloc);
    mpStateDebug                      = NewPoolState<BrnDebug>(lpLinearMalloc);

    // Gather into the table the state machine installs (the X360 v332 stack table -- its
    // order differs from both the member and the construction order: CS_VEHICLE before
    // CS_UNLOCK, INGAME before LOADING, and the post-event block interleaved).
    CgsGui::State* lapStates[KI_NUM_SCREEN_STATES];
    lapStates[0]  = mpStateNull;
    lapStates[1]  = mpStateIntro;
    lapStates[2]  = mpStateCarSelectVehicle;
    lapStates[3]  = mpStateCarSelectUnlock;
    lapStates[4]  = mpStateCarSelectLivery;
    lapStates[5]  = mpStateCarSelectOnlineEnd;
    lapStates[6]  = mpStateInGame;
    lapStates[7]  = mpStateLoading;
    lapStates[8]  = mpStateCrashNavMapEvent;
    lapStates[9]  = mpStateCrashNavMapMain;
    lapStates[10] = mpStateCrashNavStats;
    lapStates[11] = mpStateCrashNavSettings;
    lapStates[12] = mpStateCrashNavProfile;
    lapStates[13] = mpStateCrashNavOptions;
    lapStates[14] = mpStateCrashNavAccountManagement;
    lapStates[15] = mpStateCrashNavTrax;
    lapStates[16] = mpStateCredits;
    lapStates[17] = mpStateColourCalibration;
    lapStates[18] = mpStateDriverDetails;
    lapStates[19] = mpStateCrashNavEnterOnlineFull;
    lapStates[20] = mpStateCrashNavEnterOnlineNoTitle;
    lapStates[21] = mpStatePause;
    lapStates[22] = mpStateVideo;
    lapStates[23] = mpStateImageGallery;
    lapStates[24] = mpStateOnlinePlay;
    lapStates[25] = mpStateOnlineGameRoom;
    lapStates[26] = mpStateOnlineCustomMatch;
    lapStates[27] = mpStateOnlineCreateFreeburn;
    lapStates[28] = mpStateOnlineSelectRoute;
    lapStates[29] = mpStateOnlineGameOptions;
    lapStates[30] = mpStateOnlineGameOptionsSummary;
    lapStates[31] = mpStateOnlineScoreboards;
    lapStates[32] = mpStateOnlineStats;
    lapStates[33] = mpStateOnlineQuickMatch;
    lapStates[34] = mpStateOnlineNews;
    lapStates[35] = mpStateOnlineRivals;
    lapStates[36] = mpStateOnlineTeamSelection;
    lapStates[37] = mpStateOnlineQuickCustomCreate;
    lapStates[38] = mpStateOnlineFBurnQuickCustCreate;
    lapStates[39] = mpStateOnlineViewChallenges;
    lapStates[40] = mpStateOnlineLoading;
    lapStates[41] = mpStateOnlinePause;
    lapStates[42] = mpStateOnlinePreEvent;
    lapStates[43] = mpStateOnlineMarkMan;
    lapStates[44] = mpStateOfflineInstantResults;
    lapStates[45] = mpStateOnlineInstantResults;
    lapStates[46] = mpStateOnlineYouWin;
    lapStates[47] = mpStateShowtimeInstantResults;
    lapStates[48] = mpStateOfflineCompletedGame;
    lapStates[49] = mpStateOfflineRivalShutdown;
    lapStates[50] = mpStateOfflineTrophyCarUnlock;
    lapStates[51] = mpStateGenericForward;
    lapStates[52] = mpStateReplayClips;
    lapStates[53] = mpStateReplayClipsOnline;
    lapStates[54] = mpStateReplayOptions;
    lapStates[55] = mpStateReplayLoading;
    lapStates[56] = mpStateReplayIntro;
    lapStates[57] = mpStateReplayMain;
    lapStates[58] = mpStateReplayOutro;
    lapStates[59] = mpStateReplayCredits;
    lapStates[60] = mpStateDebug;

    // BrnScreenFlow.cpp:227 -- the X360 walks the gathered table before registering and
    // asserts on every null slot ("Invalid state pointer in state list: " << index).
    for (s32 li = 0; li < KI_NUM_SCREEN_STATES; ++li)
        CGS_ASSERT(lapStates[li] != 0, "Invalid state pointer in state list");

    // Construct each state with its script-id name + the owning state machine (the X360
    // dispatches ScriptedState::Construct virtually, vtbl +0x18 -- in the X360 registration
    // order, which interleaves CS_UNLOCK back before CS_VEHICLE). CN_PROFILE alone goes
    // through the DIRECT wider CrashNavProfile::Construct that threads the profile manager.
    mpStateNull->Construct(CgsIDCompress("NULL"), &lStateMachine);
    mpStateIntro->Construct(CgsIDCompress("INTRO"), &lStateMachine);
    mpStateCarSelectUnlock->Construct(CgsIDCompress("CS_UNLOCK"), &lStateMachine);
    mpStateCarSelectVehicle->Construct(CgsIDCompress("CS_VEHICLE"), &lStateMachine);
    mpStateCarSelectLivery->Construct(CgsIDCompress("CS_LIVERY"), &lStateMachine);
    mpStateCarSelectOnlineEnd->Construct(CgsIDCompress("CS_ON_END"), &lStateMachine);
    mpStateLoading->Construct(CgsIDCompress("LOADING"), &lStateMachine);
    mpStateInGame->Construct(CgsIDCompress("INGAME"), &lStateMachine);
    mpStateCrashNavMapEvent->Construct(CgsIDCompress("CN_MAP_EVENT"), &lStateMachine);
    mpStateCrashNavMapMain->Construct(CgsIDCompress("CN_MAP_MAIN"), &lStateMachine);
    mpStateCrashNavStats->Construct(CgsIDCompress("CN_STATS"), &lStateMachine);
    mpStateCrashNavSettings->Construct(CgsIDCompress("CN_SETTINGS"), &lStateMachine);
    mpStateCrashNavProfile->Construct(CgsIDCompress("CN_PROFILE"), &lStateMachine,
                                      lrProfileManager);
    mpStateCrashNavOptions->Construct(CgsIDCompress("CN_OPTIONS"), &lStateMachine);
    mpStateCrashNavAccountManagement->Construct(CgsIDCompress("CN_ACCT_MAN"), &lStateMachine);
    mpStateCrashNavTrax->Construct(CgsIDCompress("CN_TRAX"), &lStateMachine);
    mpStateCredits->Construct(CgsIDCompress("CN_CREDITS"), &lStateMachine);
    mpStateColourCalibration->Construct(CgsIDCompress("CN_COLOUR"), &lStateMachine);
    mpStateDriverDetails->Construct(CgsIDCompress("CN_D_DETAIL"), &lStateMachine);
    mpStateCrashNavEnterOnlineFull->Construct(CgsIDCompress("CN_ENTER_ON"), &lStateMachine);
    mpStateCrashNavEnterOnlineNoTitle->Construct(CgsIDCompress("CN_ENTER_ONT"), &lStateMachine);
    mpStatePause->Construct(CgsIDCompress("PAUSED"), &lStateMachine);
    mpStateVideo->Construct(CgsIDCompress("FMV_VIDEO"), &lStateMachine);
    mpStateImageGallery->Construct(CgsIDCompress("ON_IMG_GAL"), &lStateMachine);
    mpStateOnlinePlay->Construct(CgsIDCompress("ON_PLAY"), &lStateMachine);
    mpStateOnlineGameRoom->Construct(CgsIDCompress("ON_GAME_ROOM"), &lStateMachine);
    mpStateOnlineCustomMatch->Construct(CgsIDCompress("ON_CUST_MAT"), &lStateMachine);
    mpStateOnlineCreateFreeburn->Construct(CgsIDCompress("ON_CREATE_FB"), &lStateMachine);
    mpStateOnlineSelectRoute->Construct(CgsIDCompress("ON_SEL_ROUTE"), &lStateMachine);
    mpStateOnlineGameOptions->Construct(CgsIDCompress("ON_GAME_OPT"), &lStateMachine);
    mpStateOnlineGameOptionsSummary->Construct(CgsIDCompress("ON_GAME_SUM"), &lStateMachine);
    mpStateOnlineScoreboards->Construct(CgsIDCompress("ON_SCOREB"), &lStateMachine);
    mpStateOnlineStats->Construct(CgsIDCompress("ON_STATS"), &lStateMachine);
    mpStateOnlineQuickMatch->Construct(CgsIDCompress("ON_QWK_MAT"), &lStateMachine);
    mpStateOnlineNews->Construct(CgsIDCompress("ON_NEWS"), &lStateMachine);
    mpStateOnlineRivals->Construct(CgsIDCompress("ON_RIVALS"), &lStateMachine);
    mpStateOnlineTeamSelection->Construct(CgsIDCompress("ON_TEAMS"), &lStateMachine);
    mpStateOnlineQuickCustomCreate->Construct(CgsIDCompress("ON_QK_CST_CR"), &lStateMachine);
    mpStateOnlineFBurnQuickCustCreate->Construct(CgsIDCompress("ON_FB_QKCTCR"), &lStateMachine);
    mpStateOnlineViewChallenges->Construct(CgsIDCompress("ON_VIW_CHL"), &lStateMachine);
    mpStateOnlineLoading->Construct(CgsIDCompress("ON_LOADING"), &lStateMachine);
    mpStateOnlinePause->Construct(CgsIDCompress("ON_PAUSE"), &lStateMachine);
    mpStateOnlinePreEvent->Construct(CgsIDCompress("ON_PRE_EVENT"), &lStateMachine);
    mpStateOnlineMarkMan->Construct(CgsIDCompress("ON_MARK_MAN"), &lStateMachine);
    mpStateOfflineInstantResults->Construct(CgsIDCompress("POST_INST"), &lStateMachine);
    mpStateOfflineCompletedGame->Construct(CgsIDCompress("PE_COMPLETED"), &lStateMachine);
    mpStateOfflineRivalShutdown->Construct(CgsIDCompress("POST_RIVAL"), &lStateMachine);
    mpStateOfflineTrophyCarUnlock->Construct(CgsIDCompress("TRPHY_UNLOCK"), &lStateMachine);
    mpStateOnlineInstantResults->Construct(CgsIDCompress("POST_ON_IR"), &lStateMachine);
    mpStateOnlineYouWin->Construct(CgsIDCompress("ON_YOU_WIN"), &lStateMachine);
    mpStateShowtimeInstantResults->Construct(CgsIDCompress("POST_ST_IR"), &lStateMachine);
    mpStateGenericForward->Construct(CgsIDCompress("GEN_FORWARD"), &lStateMachine);
    mpStateReplayClips->Construct(CgsIDCompress("RE_CLIPS"), &lStateMachine);
    mpStateReplayClipsOnline->Construct(CgsIDCompress("RE_CLIPS_ON"), &lStateMachine);
    mpStateReplayOptions->Construct(CgsIDCompress("RE_OPTIONS"), &lStateMachine);
    mpStateReplayLoading->Construct(CgsIDCompress("RE_LOADING"), &lStateMachine);
    mpStateReplayIntro->Construct(CgsIDCompress("RE_INTRO"), &lStateMachine);
    mpStateReplayMain->Construct(CgsIDCompress("RE_MAIN"), &lStateMachine);
    mpStateReplayOutro->Construct(CgsIDCompress("RE_OUT"), &lStateMachine);
    mpStateReplayCredits->Construct(CgsIDCompress("RE_CREDITS"), &lStateMachine);
    mpStateDebug->Construct(CgsIDCompress("DEBUG"), &lStateMachine);

    lStateMachine.SetStates(lapStates, KI_NUM_SCREEN_STATES);
    return true;
}

} // namespace BrnGui
