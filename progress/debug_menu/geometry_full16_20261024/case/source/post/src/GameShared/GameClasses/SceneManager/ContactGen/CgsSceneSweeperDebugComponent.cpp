#include "GameShared/GameClasses/SceneManager/ContactGen/CgsSceneSweeperDebugComponent.h"

#include "GameShared/GameClasses/Core/CgsAssert.h"
#include "GameShared/GameClasses/Development/DebugSystem/Render/CgsDebug3DImmediateRender.h"
#include "GameShared/GameClasses/SceneManager/ContactGen/CgsIntervalList.h"
#include "GameShared/GameClasses/SceneManager/ContactGen/CgsSceneSweeper.h"
#include "GameShared/GameClasses/Development/Log/CgsLog.h" // [case witness] bounded RenderWorld readbacks

#include <cstdlib> // [case witness] opt-in read-only interval owner diagnostics

namespace CgsSceneManager
{
    // Inlined by OverlapGenerationModule::Construct in ARTIST.
    void SceneSweeperDebugComponent::Construct(SceneSweeper* lpSceneSweeper)
    {
        CgsDev::DebugComponent::Construct();
        mpSceneSweeper = lpSceneSweeper;
        mfDrawDistance = 50.0f;
        mbRenderDynamicBoxes = false;
        mbRenderInactiveBoxes = false;
    }

    void SceneSweeperDebugComponent::Destruct()
    {
        CGS_ASSERT(mpSceneSweeper != 0, "mpSceneSweeper != NULL");
        mpSceneSweeper = 0;
        CgsDev::DebugComponent::Destruct();
    }

    // ARTIST 0x828AC240.
    void SceneSweeperDebugComponent::OnActivate()
    {
        RegisterVariable(&mbRenderDynamicBoxes,
                         "Render scene sweeper boxes for dynamic objects");
        RegisterVariable(&mbRenderInactiveBoxes,
                         "Render scene sweeper boxes for frozen objects");
        RegisterVariable(&mfDrawDistance, "Scene sweeper render draw distance");
    }

    // ARTIST 0x828AC2A0. Each min endpoint owns the Y/Z bounds and maps to the
    // matching max endpoint for X max. Only boxes within mfDrawDistance are emitted.
    void SceneSweeperDebugComponent::RenderIntervalList(
        CgsDev::Debug3DImmediateRender* lpDisplay,
        const IntervalList* lpIntervalList,
        rw::RGBA lColour)
    {
        const Vector3 lCameraPosition = lpDisplay->GetCameraPosition();
        const f32 lfMaxDistanceSquared = mfDrawDistance * mfDrawDistance;

        for (u32 luIndex = 0; luIndex < lpIntervalList->GetNumIntervals(); ++luIndex)
        {
            const Interval* lpMinInterval = lpIntervalList->GetInterval(luIndex);
            if (lpMinInterval->mu16Flags != IntervalList::KI_MIN_INDEX)
                continue;

            const Vector3 lMin = {
                lpMinInterval->mfXInterval,
                lpMinInterval->mfYMinInterval,
                lpMinInterval->mfZMinInterval,
                0.0f,
            };

            const f32 lfDeltaX = lCameraPosition.x - lMin.x;
            const f32 lfDeltaY = lCameraPosition.y - lMin.y;
            const f32 lfDeltaZ = lCameraPosition.z - lMin.z;
            const f32 lfDistanceSquared =
                lfDeltaX * lfDeltaX + lfDeltaY * lfDeltaY + lfDeltaZ * lfDeltaZ;
            if (lfDistanceSquared >= lfMaxDistanceSquared)
                continue;

            const Interval* lpMaxInterval = lpIntervalList->GetObjectInterval(
                lpMinInterval->mu16ObjectIndex, IntervalList::KI_MAX_INDEX);
            CGS_ASSERT(lpMaxInterval->mu16ObjectIndex == lpMinInterval->mu16ObjectIndex,
                       "lpMaxInterval->GetObjectIndex() == lpMinInterval->GetObjectIndex()");

            const Vector3 lMax = {
                lpMaxInterval->mfXInterval,
                -lpMinInterval->mfMinusYMaxInterval,
                -lpMinInterval->mfMinusZMaxInterval,
                0.0f,
            };
            lpDisplay->DrawBox(lMin, lMax, lColour);
        }
    }

    // ARTIST 0x828B6708.
    void SceneSweeperDebugComponent::RenderWorld(CgsDev::Debug3DImmediateRender* lpDisplay)
    {
        // [case witness] Read-only typed interval counts and actual component dispatch.
        // Inert unless BRN_DEBUG_GEOMETRY_WITNESS is set; log first observation,
        // stored control changes and first owner/list eligibility observations. The
        // full16 schedule is bounded by 7 changed tuples + 1 initial row + 3 readiness
        // observations (owner plus two lists); the11-row cap is exact.
        static const bool sbGeometryWitnessEnabled =
            std::getenv("BRN_DEBUG_GEOMETRY_WITNESS") != nullptr;
        static bool sbGeometryWitnessHasPrevious = false;
        static u32 suGeometryWitnessRows = 0;
        static bool sbLoggedOwnerReady = false;
        static bool sbLoggedDynamicReady = false;
        static bool sbLoggedInactiveReady = false;
        static bool sbPreviousDrawDynamic = false;
        static bool sbPreviousDrawInactive = false;
        static f32 sfPreviousDrawDistance = 0.0f;
        if (sbGeometryWitnessEnabled)
        {
            const bool lbOwnerReady = mpSceneSweeper != nullptr;
            const u32 luDynamicIntervals = lbOwnerReady
                ? mpSceneSweeper->GetDynamicIntervalList().GetNumIntervals() : 0u;
            const u32 luInactiveIntervals = lbOwnerReady
                ? mpSceneSweeper->GetInactiveIntervalList().GetNumIntervals() : 0u;
            const bool lbDynamicNonEmpty = luDynamicIntervals != 0u;
            const bool lbInactiveNonEmpty = luInactiveIntervals != 0u;
            const bool lbReadinessChanged = (lbOwnerReady && !sbLoggedOwnerReady) ||
                (lbDynamicNonEmpty && !sbLoggedDynamicReady) ||
                (lbInactiveNonEmpty && !sbLoggedInactiveReady);
            const bool lbChanged = !sbGeometryWitnessHasPrevious || lbReadinessChanged ||
                mbRenderDynamicBoxes != sbPreviousDrawDynamic ||
                mbRenderInactiveBoxes != sbPreviousDrawInactive ||
                mfDrawDistance != sfPreviousDrawDistance;
            if (lbChanged && suGeometryWitnessRows < 11u &&
                CgsDev::Log::gpDebugPrint != nullptr)
            {
                sbGeometryWitnessHasPrevious = true;
                sbLoggedOwnerReady = sbLoggedOwnerReady || lbOwnerReady;
                sbLoggedDynamicReady = sbLoggedDynamicReady || lbDynamicNonEmpty;
                sbLoggedInactiveReady = sbLoggedInactiveReady || lbInactiveNonEmpty;
                sbPreviousDrawDynamic = mbRenderDynamicBoxes;
                sbPreviousDrawInactive = mbRenderInactiveBoxes;
                sfPreviousDrawDistance = mfDrawDistance;
                ++suGeometryWitnessRows;
                CgsDev::Log::gpDebugPrint->AppendFormat(
                    "[geometry-witness] owner=sweeper sample=%u owner_ready=%u dynamic_intervals=%u inactive_intervals=%u draw_dynamic=%u draw_frozen=%u draw_distance=%.6f\n",
                    suGeometryWitnessRows, static_cast<unsigned>(lbOwnerReady),
                    luDynamicIntervals, luInactiveIntervals,
                    static_cast<unsigned>(mbRenderDynamicBoxes),
                    static_cast<unsigned>(mbRenderInactiveBoxes), mfDrawDistance);
            }
        }
        if (mbRenderDynamicBoxes)
        {
            RenderIntervalList(lpDisplay, &mpSceneSweeper->GetDynamicIntervalList(),
                               rw::RGBA(255, 0, 0, 255));
        }
        if (mbRenderInactiveBoxes)
        {
            RenderIntervalList(lpDisplay, &mpSceneSweeper->GetInactiveIntervalList(),
                               rw::RGBA(255, 255, 255, 255));
        }
    }
}
