#include "GameShared/GameClasses/SceneManager/ContactGen/CgsSceneSweeperDebugComponent.h"

#include "GameShared/GameClasses/Core/CgsAssert.h"
#include "GameShared/GameClasses/Development/DebugSystem/Render/CgsDebug3DImmediateRender.h"
#include "GameShared/GameClasses/SceneManager/ContactGen/CgsIntervalList.h"
#include "GameShared/GameClasses/SceneManager/ContactGen/CgsSceneSweeper.h"

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
