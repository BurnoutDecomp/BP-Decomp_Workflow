#include "GameSource/GameState/TakedownManager/BrnTakedownManagerDebugComponent.h"
#include "GameSource/GameState/TakedownManager/BrnTakedownManager.h"   // TakedownManager + RaceCarData
#include "GameSource/GameState/BrnGameStateModule.h"                          // GameStateModule::GetLastActiveRaceCarInterface (RecordTakedown)
#include "GameSource/GameState/ModeManager/BrnModeManager.h"                  // ModeManager::GetGameStateModule
#include "GameShared/GameClasses/Development/Log/CgsLog.h"                    // bounded opt-in debug trace
#include "GameSource/World/EntityModules/RaceCarEntityModule/SharedIO/BrnRaceCarEntityModuleOutputInterface.h" // RCEntityActiveRaceCarOutputInterface
#include "GameSource/Physics/VehicleManager/SharedIO/BrnVehicleEvents.h"      // RaceCarState (mi8LastContactedRaceCar / mfTimeSinceLastRaceCarContact)
#include "GameShared/GameClasses/Development/CgsStrStream.h"                  // CgsDev::SimpleStrStream (RenderHUD)
#include "GameShared/GameClasses/Development/DebugSystem/Render/CgsDebug2DImmediateRender.h"
#include "GameShared/GameClasses/Development/DebugSystem/Render/CgsDebug3DImmediateRender.h"

#include <cstdlib>

int MaybeDrawText(CgsDev::Debug2DImmediateRender* lpDisplay, const char* lpcText,
                  f32 lfX, f32 lfY, f32 lfScale, CgsDev::RGBA lColour, bool lbCentred);

// Reconstructed from BURNOUT_X360_ARTIST.XEX. The takedown debug menu registers three display
// toggles + a "force takedown" action with the real CgsDev::DebugComponent debug-menu API. The
// X360 issued these through the (unnamed) DebugComponent registration helpers (now the real
// base-class RegisterVariable / RegisterFunction, called by name). ForceTakedownCallback forces a
// takedown on the player's active race car (maRaceCarData[0]).

namespace BrnGameState
{
    const char* TakedownManagerDebugComponent::GetName() const
    {
        return "TakedownManager";
    }

    // A contact time of -1 means RecordTakedown found no race-car contact on the victim, i.e. the
    // takedown came from a slam or shunt rather than a car-to-car hit.
    void TakedownManagerDebugComponent::RenderHUD(CgsDev::Debug2DImmediateRender* lpRender)
    {
        if (mbShowLastTakedownInfo)
        {
            CgsDev::SimpleStrStream lStream;

            if (meLastAggressorIndex == E_ACTIVE_RACE_CAR_INDEX_INVALID)
            {
                lStream << "Invalid";
            }
            else
            {
                lStream << "Car " << static_cast<s32>(meLastAggressorIndex)
                        << " takes down car " << static_cast<s32>(meLastVictimIndex);

                if (mfLastTakedownContactTime != -1.0f)
                {
                    lStream << ", last contacted: " << mfLastTakedownContactTime << "s";
                }
                else
                {
                    lStream << ", slam/shunt takedown";
                }
            }

            MaybeDrawText(lpRender, lStream.GetBuffer(), 100.0f, 50.0f, 20.0f, 0xFFFFFFFFu, false);
        }
    }

    // ARTIST @0x8236F200. The first menu toggle draws a 2 m sphere at each active car's
    // transform position while its shunt is active, its slam life is positive, or its most
    // recent car contact is less than 2 seconds old. Shunt/slam use 0x400000FF; recent contact
    // uses 0x4000FFFF. The second toggle draws the first colour at every active car recorded in
    // the player's RaceCarData::mabRevengeRelationships. The named state, transform, and manager
    // fields below are the DecFIGS declaration shape; the predicates, colors, radius, and loop
    // bounds are read from the X360 assembly. ARTIST's callee label `RCEntityActiveRaceCarO` is
    // truncated; DecFIGS names the call GetRaceCarState, and its bounds asserts are retained in
    // that accessor. IsRaceCarActive carries the same bounds asserts. The enum-increment
    // post-loop assert is unreachable for these fixed 0..7 loops.
    void TakedownManagerDebugComponent::RenderWorld(CgsDev::Debug3DImmediateRender* lpRender)
    {
        static s32 siTraceTransitionsRemaining = 32;
        static s32 siTraceSamplesRemaining = 8;
        static s32 siTraceCallsSinceSample = 0;
        static bool sbHasTraceSnapshot = false;
        static u32 suPreviousToggleMask = 0;
        static u32 suPreviousActiveCarMask = 0;
        static u32 suPreviousVulnerabilityShuntOrSlamMask = 0;
        static u32 suPreviousVulnerabilityRecentContactMask = 0;
        static u32 suPreviousRevengeMask = 0;
        static u32 suPreviousGeometryCount = 0;
        static s32 siPreviousPlayerIndex = E_ACTIVE_RACE_CAR_INDEX_INVALID;
        static bool sbPreviousPlayerCarActive = false;
        const char* lpcTraceSetting = std::getenv("BRN_TAKEDOWN_DEBUG_TRACE");
        const bool lbTraceThisCall = lpcTraceSetting != 0 && lpcTraceSetting[0] != '\0' &&
                                     lpcTraceSetting[0] != '0' &&
                                     CgsDev::Log::gpDebugPrint != 0;
        u32 luActiveCarMask = 0;
        u32 luVulnerabilityShuntOrSlamMask = 0;
        u32 luVulnerabilityRecentContactMask = 0;
        u32 luRevengeMask = 0;
        u32 luGeometryCount = 0;
        bool lbPlayerCarActive = false;
        EActiveRaceCarIndex lePlayerActiveRaceCarIndex = E_ACTIVE_RACE_CAR_INDEX_INVALID;

        if (mbShowVulnerability)
        {
            const BrnWorld::RaceCarEntityModuleIO::RCEntityActiveRaceCarOutputInterface* lpActiveCarInterface =
                mpTakedownManager->mpModeManager->GetGameStateModule()->GetLastActiveRaceCarInterface();

            for (s32 liIndex = 0; liIndex < E_ACTIVE_RACE_CAR_INDEX_COUNT; ++liIndex)
            {
                const EActiveRaceCarIndex leActiveRaceCarIndex = static_cast<EActiveRaceCarIndex>(liIndex);
                if (!lpActiveCarInterface->IsRaceCarActive(leActiveRaceCarIndex))
                {
                    continue;
                }
                luActiveCarMask |= (1u << liIndex);

                const BrnPhysics::Vehicle::RaceCarState* lpRaceCarState =
                    lpActiveCarInterface->GetRaceCarState(leActiveRaceCarIndex);
                if (lpRaceCarState->mShuntEffect.IsActive() || lpRaceCarState->mSlamEffect.mfSlamLife > 0.0f)
                {
                    luVulnerabilityShuntOrSlamMask |= (1u << liIndex);
                    lpRender->DrawSolidSphere(lpRaceCarState->mTransform.Pos(), 2.0f, rw::RGBA(255, 0, 0, 0x40));
                    ++luGeometryCount;
                }
                else if (lpRaceCarState->mfTimeSinceLastRaceCarContact < 2.0f)
                {
                    luVulnerabilityRecentContactMask |= (1u << liIndex);
                    lpRender->DrawSolidSphere(lpRaceCarState->mTransform.Pos(), 2.0f, rw::RGBA(255, 255, 0, 0x40));
                    ++luGeometryCount;
                }
            }
        }

        if (mbShowRevengeTakedownInfo)
        {
            const BrnWorld::RaceCarEntityModuleIO::RCEntityActiveRaceCarOutputInterface* lpActiveCarInterface =
                mpTakedownManager->mpModeManager->GetGameStateModule()->GetLastActiveRaceCarInterface();
            lbPlayerCarActive = lpActiveCarInterface->IsPlayerCarActive();
            if (lbPlayerCarActive)
            {
                lePlayerActiveRaceCarIndex = lpActiveCarInterface->GetPlayerActiveRaceCarIndex();
                CGS_ASSERT(lePlayerActiveRaceCarIndex != E_ACTIVE_RACE_CAR_INDEX_INVALID,
                           "Player car index hasn't been set");
                const TakedownManager::RaceCarData* lpPlayerRaceCarData =
                    mpTakedownManager->GetRaceCarData(lePlayerActiveRaceCarIndex);

                for (s32 liIndex = 0; liIndex < E_ACTIVE_RACE_CAR_INDEX_COUNT; ++liIndex)
                {
                    const EActiveRaceCarIndex leActiveRaceCarIndex = static_cast<EActiveRaceCarIndex>(liIndex);
                    if (!lpActiveCarInterface->IsRaceCarActive(leActiveRaceCarIndex))
                    {
                        continue;
                    }
                    luActiveCarMask |= (1u << liIndex);
                    if (!lpPlayerRaceCarData->mabRevengeRelationships[liIndex])
                    {
                        continue;
                    }

                    luRevengeMask |= (1u << liIndex);
                    const BrnPhysics::Vehicle::RaceCarState* lpRaceCarState =
                        lpActiveCarInterface->GetRaceCarState(leActiveRaceCarIndex);
                    lpRender->DrawSolidSphere(lpRaceCarState->mTransform.Pos(), 2.0f, rw::RGBA(255, 0, 0, 0x40));
                    ++luGeometryCount;
                }
            }
        }

        // [PC trace only] Log up to 32 state transitions and eight samples (each after 60 stable
        // enabled calls) from the same cached interface. Stable disabled frames cost no budget;
        // separate caps preserve transitions for a scenario driven from the menu at high frame
        // rates. The trace submits no extra geometry and changes no gameplay state. Set
        // BRN_TAKEDOWN_DEBUG_TRACE=1 for the joint vulnerability/revenge scenario.
        if (lbTraceThisCall)
        {
            const u32 luToggleMask = (mbShowVulnerability ? 1u : 0u) |
                                     (mbShowLastTakedownInfo ? 2u : 0u) |
                                     (mbShowRevengeTakedownInfo ? 4u : 0u);
            const s32 liPlayerIndex = static_cast<s32>(lePlayerActiveRaceCarIndex);
            const bool lbStateChanged = !sbHasTraceSnapshot ||
                                        luToggleMask != suPreviousToggleMask ||
                                        luActiveCarMask != suPreviousActiveCarMask ||
                                        luVulnerabilityShuntOrSlamMask != suPreviousVulnerabilityShuntOrSlamMask ||
                                        luVulnerabilityRecentContactMask != suPreviousVulnerabilityRecentContactMask ||
                                        luRevengeMask != suPreviousRevengeMask ||
                                        luGeometryCount != suPreviousGeometryCount ||
                                        liPlayerIndex != siPreviousPlayerIndex ||
                                        lbPlayerCarActive != sbPreviousPlayerCarActive;
            bool lbWriteTrace = false;
            const char* lpcTraceEvent = "sample";
            if (lbStateChanged)
            {
                const bool lbHasVisibleState = sbHasTraceSnapshot || luToggleMask != 0;
                sbHasTraceSnapshot = true;
                suPreviousToggleMask = luToggleMask;
                suPreviousActiveCarMask = luActiveCarMask;
                suPreviousVulnerabilityShuntOrSlamMask = luVulnerabilityShuntOrSlamMask;
                suPreviousVulnerabilityRecentContactMask = luVulnerabilityRecentContactMask;
                suPreviousRevengeMask = luRevengeMask;
                suPreviousGeometryCount = luGeometryCount;
                siPreviousPlayerIndex = liPlayerIndex;
                sbPreviousPlayerCarActive = lbPlayerCarActive;
                siTraceCallsSinceSample = 0;
                if (lbHasVisibleState && siTraceTransitionsRemaining > 0)
                {
                    --siTraceTransitionsRemaining;
                    lbWriteTrace = true;
                    lpcTraceEvent = "transition";
                }
            }
            else if ((mbShowVulnerability || mbShowRevengeTakedownInfo) &&
                     siTraceSamplesRemaining > 0 && ++siTraceCallsSinceSample >= 60)
            {
                --siTraceSamplesRemaining;
                siTraceCallsSinceSample = 0;
                lbWriteTrace = true;
            }

            if (lbWriteTrace)
            {
                CgsDev::SimpleStrStream lTrace;
                lTrace << "[BRN_TAKEDOWN_DEBUG_TRACE] event=" << lpcTraceEvent
                       << " slots=" << luActiveCarMask
                       << " vulnerability-shunt-slam=" << luVulnerabilityShuntOrSlamMask
                       << " vulnerability-recent-contact=" << luVulnerabilityRecentContactMask
                       << " revenge=" << luRevengeMask
                       << " player-active=" << (lbPlayerCarActive ? 1 : 0)
                       << " player-slot=" << liPlayerIndex
                       << " toggles=" << luToggleMask
                       << " geometry-submissions=" << luGeometryCount << "\n";
                *CgsDev::Log::gpDebugPrint << lTrace.GetBuffer();
            }
        }
    }

    void TakedownManagerDebugComponent::OnActivate()
    {
        RegisterVariable(&mbShowLastTakedownInfo, "Show last takedown info");
        RegisterVariable(&mbShowVulnerability, "Show vulnerability");
        RegisterVariable(&mbShowRevengeTakedownInfo, "Show revenge takedown info");
        RegisterFunction(&ForceTakedownCallback, this, "Force takedown");
    }

    // Inlined into GameStateModule::Construct @0x82380404..0x82380434 (r3 = &gsm.mTakedownManager
    // .mTakedownManagerDebugComponent, r23 = &gsm.mTakedownManager):
    //   0x82380418  stfs -1.0, +0x18   mfLastTakedownContactTime
    //   0x8238041C  stw  r23,  +0x0C   mpTakedownManager
    //   0x82380420  stb  0,    +0x1D   mbShowLastTakedownInfo
    //   0x82380424  stb  0,    +0x1E   mbShowRevengeTakedownInfo
    //   0x82380428  stb  0,    +0x1C   mbShowVulnerability
    //   0x8238042C  stw  -1,   +0x10   meLastAggressorIndex
    //   0x82380430  stw  -1,   +0x14   meLastVictimIndex
    //   0x82380434  bl   CgsDev::DebugComponent::Register
    // (the base Construct() is NOT called on the console; only Register()).
    void TakedownManagerDebugComponent::Construct(TakedownManager* lpTakedownManager)
    {
        mfLastTakedownContactTime = -1.0f;
        mpTakedownManager         = lpTakedownManager;
        mbShowLastTakedownInfo    = false;
        mbShowRevengeTakedownInfo = false;
        mbShowVulnerability       = false;
        meLastAggressorIndex      = E_ACTIVE_RACE_CAR_INDEX_INVALID;
        meLastVictimIndex         = E_ACTIVE_RACE_CAR_INDEX_INVALID;

        Register();
    }

    // @ 0x823597F8 - clear the player's active-car takedown state then arm a standard takedown
    // (aggressor car 0 -> victim car 1). The X360 reaches the car via the takedown manager (whose
    // first member is maRaceCarData[]), then writes the fields below; reconstructed as named
    // member access with named enumerators (the takedown enums are now full/deduped).
    void TakedownManagerDebugComponent::ForceTakedownCallback(void* lpContext)
    {
        TakedownManagerDebugComponent* lpThis = static_cast<TakedownManagerDebugComponent*>(lpContext);
        TakedownManager::RaceCarData& lrRaceCar = lpThis->mpTakedownManager->maRaceCarData[0];

        lrRaceCar.Clear();
        lrRaceCar.mfTimeSinceVictimCrashed = 0.0f;
        lrRaceCar.mbWaitingOnTakedown = true;
        lrRaceCar.mPendingTakedownEvent.meAggressorIndex = E_ACTIVE_RACE_CAR_INDEX_0;
        lrRaceCar.mPendingTakedownEvent.meVictimIndex    = E_ACTIVE_RACE_CAR_INDEX_1;
        lrRaceCar.mPendingTakedownEvent.meType           = E_TAKEDOWN_STANDARD;
    }

    // @ 0x823663F8 -- DWARF BrnTakedownManagerDebugComponent.cpp:216. Reached from
    // DetectStandardTakedown (`bl RecordTakedown(this+676, aggressor, victim)` @0x8237A5E8).
    //   0x82366414  lwz r9, 0xC(this)         mpTakedownManager
    //   0x82366420  lwz r10, 0x28C(r9)        ->mpModeManager
    //   0x82366424  lwz r10, 0x6D58(r10)      ->mpGameStateModule
    //   0x82366430/38 r29 = gsm + 0x397E0     the module's cached active-race-car interface
    //   0x82366428  stfs -1.0, 0x18(this)     mfLastTakedownContactTime = -1
    //   0x8236642C  stw  aggressor, 0x10      meLastAggressorIndex
    //   0x82366434  stw  victim, 0x14         meLastVictimIndex
    //   IsRaceCarActive(victim) -> GetRaceCarState(victim): `lbz 0x445` (mi8LastContactedRaceCar)
    //   != 0xFF -> `lfs 0x430` (mfTimeSinceLastRaceCarContact) -> mfLastTakedownContactTime.
    // The console reads the three pointers raw; GetGameStateModule() adds its own non-null assert
    // (assert-is-not-a-guard: the read still happens either way).
    void TakedownManagerDebugComponent::RecordTakedown(EActiveRaceCarIndex leAggressorIndex,
                                                       EActiveRaceCarIndex leVictimIndex)
    {
        const BrnWorld::RaceCarEntityModuleIO::RCEntityActiveRaceCarOutputInterface* lpActiveCarInterface =
            mpTakedownManager->mpModeManager->GetGameStateModule()->GetLastActiveRaceCarInterface();

        mfLastTakedownContactTime = -1.0f;
        meLastAggressorIndex      = leAggressorIndex;
        meLastVictimIndex         = leVictimIndex;

        if (lpActiveCarInterface->IsRaceCarActive(static_cast<::EActiveRaceCarIndex>(leVictimIndex)))
        {
            const BrnPhysics::Vehicle::RaceCarState* lpVictimRaceCarState =
                lpActiveCarInterface->GetRaceCarState(static_cast<::EActiveRaceCarIndex>(leVictimIndex));
            if (lpVictimRaceCarState->mi8LastContactedRaceCar != -1)
            {
                mfLastTakedownContactTime = lpVictimRaceCarState->mfTimeSinceLastRaceCarContact;
            }
        }
    }
}
