#include "GameShared/GameClasses/SceneManager/TriangleCollision/CgsTriangleCollisionDebugComponent.h"

#include "GameShared/GameClasses/Development/PerfMon/Cpu/CgsPerfMonCpu.h"
#include "GameShared/GameClasses/Development/DebugSystem/Render/CgsDebug2DImmediateRender.h"
#include "GameShared/GameClasses/Development/DebugSystem/Render/CgsDebug3DImmediateRender.h"
#include "GameShared/GameClasses/Geometric/Primitives/CgsAxisAlignedBox.h"
#include "GameShared/GameClasses/Geometric/Primitives/CgsAxisAlignedBox4.h"
#include "GameShared/GameClasses/Geometric/Primitives/CgsBox.h"
#include "GameShared/GameClasses/Geometric/Primitives/CgsSphere.h"
#include "GameShared/GameClasses/Geometric/Primitives/CgsSweptSphere.h"
#include "GameShared/GameClasses/Geometric/Primitives/CgsTriangle.h"
#include "GameShared/GameClasses/Geometric/Primitives/CgsTriangle4.h"
#include "GameShared/GameClasses/Geometric/Primitives/PolygonSoup/CgsPolygonSoup.h"
#include "GameShared/GameClasses/Geometric/Primitives/PolygonSoup/CgsPolygonSoupList.h"
#include "GameShared/GameClasses/Geometric/Primitives/PolygonSoup/CgsPolygonSoupSpacialNode.h"
#include "GameShared/GameClasses/Geometric/Primitives/PolygonSoup/CgsPolygonSoupPoly.h"
#include "GameShared/GameClasses/Geometric/Intersection/CgsPolygonSoupTests.h"
#include "GameShared/GameClasses/Geometric/Intersection/CgsTriangleBox.h"
#include "GameShared/GameClasses/Geometric/Intersection/CgsTriangleSphere.h"
#include "GameShared/GameClasses/SceneManager/TriangleCollision/CgsTriangleCollisionManager.h"
#include "GameShared/GameClasses/System/Timer/CgsTimeUtils.h"
#include "SDKs/XboxMath/XMVectorACos.h"
#include "SDKs/XboxMath/XMVectorSinCos.h"

#include <cmath>
#include <cstring>

namespace
{
    using rw::math::vpu::Vector3;

    f32 FloatFromTriangleDebugBits(u32 luBits)
    {
        f32 lfValue;
        std::memcpy(&lfValue, &luBits, sizeof(lfValue));
        return lfValue;
    }

    // Preserve the original packed word while constructing the canonical rw::RGBA.
    // RwRGBA.cpp packs (alpha << 24) | (blue << 16) | (green << 8) | red.
    rw::RGBA RwRGBAFromPackedWord(u32 luPackedColour)
    {
        return rw::RGBA(
            static_cast<u8>(luPackedColour & 0xFFu),
            static_cast<u8>((luPackedColour >> 8u) & 0xFFu),
            static_cast<u8>((luPackedColour >> 16u) & 0xFFu),
            static_cast<u8>((luPackedColour >> 24u) & 0xFFu));
    }

    void SinCosTriangleDebugAngle(f32 lfAngle, f32& rfSine, f32& rfCosine)
    {
        // ARTIST 0x828B40B0/0x828B4404: range reduction, rounded powers,
        // then the original ascending FMA chain from the shared XDK helper.
        XboxMath::XMVectorSinCos(&rfSine, &rfCosine, lfAngle);
    }

    Vector3 RotateTriangleDebugNormal(const Vector3& lrNormal,
                                      const Vector3& lrAxis,
                                      f32 lfSine,
                                      f32 lfCosine)
    {
        const f32 lfAxisDotNormal = lrAxis.x * lrNormal.x
                                  + lrAxis.y * lrNormal.y
                                  + lrAxis.z * lrNormal.z;
        Vector3 lvAxisCrossNormal;
        lvAxisCrossNormal.x =
            std::fma(lrAxis.y, lrNormal.z, -lrAxis.z * lrNormal.y);
        lvAxisCrossNormal.y =
            std::fma(lrAxis.z, lrNormal.x, -lrAxis.x * lrNormal.z);
        lvAxisCrossNormal.z =
            std::fma(lrAxis.x, lrNormal.y, -lrAxis.y * lrNormal.x);
        const f32 lfAxisTerm = lfAxisDotNormal * (1.0f - lfCosine);
        Vector3 lvRotated;
        lvRotated.x = std::fma(lrNormal.x, lfCosine,
                               std::fma(lvAxisCrossNormal.x, lfSine,
                                        lrAxis.x * lfAxisTerm));
        lvRotated.y = std::fma(lrNormal.y, lfCosine,
                               std::fma(lvAxisCrossNormal.y, lfSine,
                                        lrAxis.y * lfAxisTerm));
        lvRotated.z = std::fma(lrNormal.z, lfCosine,
                               std::fma(lvAxisCrossNormal.z, lfSine,
                                        lrAxis.z * lfAxisTerm));
        Vector3 lvResult;
        lvResult.x = lvRotated.x;
        lvResult.y = lvRotated.y;
        lvResult.z = lvRotated.z;
        lvResult.w = 0.0f;
        return lvResult;
    }

    // Matrix44AffineFromEulerXYZ, as the X360 inlines it at
    // TestPolySoupBoxCollision @0x828BFE80: Rx * Ry * Rz for row vectors.
    // Its three SinCos calls and the row products are also present in ARTIST.
    rw::math::vpu::Matrix44Affine Matrix44AffineFromEulerXYZ(const Vector3& lrAngles)
    {
        f32 lfSinX, lfCosX, lfSinY, lfCosY, lfSinZ, lfCosZ;
        XboxMath::XMVectorSinCos(&lfSinX, &lfCosX, lrAngles.x);
        XboxMath::XMVectorSinCos(&lfSinY, &lfCosY, lrAngles.y);
        XboxMath::XMVectorSinCos(&lfSinZ, &lfCosZ, lrAngles.z);

        const f32 lfCosXSinZ = lfCosX * lfSinZ;
        const f32 lfSinXSinZ = lfSinX * lfSinZ;
        const f32 lfSinXCosZ = lfSinX * lfCosZ;
        const f32 lfCosXCosZ = lfCosX * lfCosZ;

        rw::math::vpu::Matrix44Affine lResult;
        lResult.xAxis.x = lfCosY * lfCosZ;
        lResult.xAxis.y = lfCosY * lfSinZ;
        lResult.xAxis.z = -lfSinY;
        lResult.xAxis.w = 0.0f;

        lResult.yAxis.x = lfSinY * lfSinXCosZ - lfCosXSinZ;
        lResult.yAxis.y = std::fma(lfSinY, lfSinXSinZ, lfCosXCosZ);
        lResult.yAxis.z = lfCosY * lfSinX;
        lResult.yAxis.w = 0.0f;

        lResult.zAxis.x = std::fma(lfSinY, lfCosXCosZ, lfSinXSinZ);
        lResult.zAxis.y = lfSinY * lfCosXSinZ - lfSinXCosZ;
        lResult.zAxis.z = lfCosY * lfCosX;
        lResult.zAxis.w = 0.0f;
        lResult.wAxis.SetZero();
        return lResult;
    }
}

namespace CgsSceneManager
{
    DrawCollisionPolyCallbackData
        TriangleCollisionDebugComponent::saDrawPolyCallbacks[KI_MAX_NUM_COLLISION_POLY_CALLBACKS] = {};
    s32 TriangleCollisionDebugComponent::siNumDrawPolyCallbacks = 0;

    void DrawCollisionPolyCallbackData::Construct(DrawCollisionPolyCallback* lpfCallback,
                                                  void* lpUserData)
    {
        mpCallbackFunc = lpfCallback;
        mpUserData = lpUserData;
    }

    DrawCollisionPolyCallbackData::DrawCollisionPolyCallback*
    DrawCollisionPolyCallbackData::GetCallback()
    {
        return mpCallbackFunc;
    }

    void* DrawCollisionPolyCallbackData::GetUserData()
    {
        return mpUserData;
    }

    // ARTIST 0x828AAF18. A full four-entry registry returns false; otherwise the current
    // count selects a slot and is incremented before its callback/user-data pair is stored.
    bool TriangleCollisionDebugComponent::RegisterDrawCollisionPolyCallback(
        DrawCollisionPolyCallbackData::DrawCollisionPolyCallback* lpfCallback,
        void* lpUserData)
    {
        CGS_ASSERT(lpfCallback != 0, "lpHandlerFunc != NULL");
        if (siNumDrawPolyCallbacks >= KI_MAX_NUM_COLLISION_POLY_CALLBACKS)
            return false;

        DrawCollisionPolyCallbackData& lrSlot =
            GetDrawCollisionPolyCallback(siNumDrawPolyCallbacks++);
        CGS_ASSERT(lpfCallback != 0, "lpCallbackFunc != NULL");
        lrSlot.Construct(lpfCallback, lpUserData);
        return true;
    }

    // ARTIST 0x828B3340. Seed the query controls, collision-test state, map defaults and
    // six CPU monitors exactly as stored by the X360 constructor body.
    void TriangleCollisionDebugComponent::Construct(
        const TriangleCollisionManager* lpTriCollisionManager)
    {
        CGS_ASSERT(lpTriCollisionManager != 0, "lpTriCollisionManager != NULL");
        mpTriCollisionManager = lpTriCollisionManager;

        mfSoupDrawDistance = 27.5f;
        mbUpdateViewFrustum = true;
        mbDrawPolySoups = false;
        mbDrawSoupAabbs = false;
        // The X360 does not store mbDrawPolyNormals in this body.
        mbDrawEdgeCosines = false;

        mbTestSphere = false;
        mSpherePos.SetZero();
        mfSphereRad = 0.5f;
        mbNeedToInitSpherePos = true;
        muSphereTestCycles = 0;
        mfSphereTestTimeSecs = 0.0f;
        mfSphereTestTimePercentFrame = 0.0f;
        miSphereTestResultCount = 0;

        mbTestLine = false;
        mbNeedToInitLinePosition = false;

        mbTestBox = false;
        mbNeedToInitBoxPos = true;
        mBoxPos.SetZero();
        mBoxSize.Set(1.0f, 1.0f, 1.0f);
        mBoxOrientation.SetZero();
        muBoxTestCycles = 0;
        miNumBoxTests = 0;
        muBoxTestCyclesPerTriangle = 0;
        mfBoxTestTime = 0.0f;
        mfBoxTestPercent = 0.0f;

        mbTestSweptSphere = false;
        mbNeedToInitSweptSpherePos = true;
        mSweptSpherePos.SetZero();
        mSweptSphereSize = 1.0f;
        mSweptSphereVelocity.SetZero();

        miMaxLevelToDraw = KI_MAX_NUM_LEVELS;
        miMinLevelToDraw = 0;
        mpcSpacialBuffer = 0;
        miNumLevels = 1;
        miLastNumLevels = 0;
        miMemUse = 0;

        const CgsDev::PerfMonCpuPage lePage = CgsDev::E_PMP_4;
        miSphereTestPerfMon = CgsDev::PerfMonCpu::AddMonitor(
            "Sphere test perf mon", lePage, false, 10.0f, true);
        miSphereTestGetListsPerfMon = CgsDev::PerfMonCpu::AddMonitor(
            "  ST: Get lists", lePage, false, 10.0f, true);
        miSphereTestProcessSoupsPerfMon = CgsDev::PerfMonCpu::AddMonitor(
            "  ST: Process soups", lePage, false, 10.0f, true);
        miLineTestPerfMon = CgsDev::PerfMonCpu::AddMonitor(
            "Line test perf mon", lePage, false, 10.0f, true);
        miLineTestGetListsPerfMon = CgsDev::PerfMonCpu::AddMonitor(
            "  LT: Get lists", lePage, false, 10.0f, true);
        miLineTestProcessSoupsPerfMon = CgsDev::PerfMonCpu::AddMonitor(
            "  LT: Process soups", lePage, false, 10.0f, true);
    }

    // ARTIST 0x828CAE88. Preserve the per-frame order: update the current frustum,
    // draw the previous spatial map, rebuild it if the level count changed, then run
    // each enabled collision query. The swept-sphere pass receives a null 2D renderer
    // exactly as the X360 caller's r5=0 argument does.
    void TriangleCollisionDebugComponent::RenderWorld(
        CgsDev::Debug3DImmediateRender* lpRenderer)
    {
        if (mbUpdateViewFrustum)
            UpdateViewFrustum(lpRenderer);

        if (mbDrawPolySoups)
            DrawPolySoups(lpRenderer);

        BuildSpacialMap();

        if (mbTestSphere)
            TestPolySoupSphereCollision(lpRenderer);

        if (mbTestBox)
            TestPolySoupBoxCollision(lpRenderer);

        if (mbTestSweptSphere)
            TestPolySoupSweptSphereCollision(lpRenderer, nullptr);
    }

    // ARTIST 0x828BF8C0. The world pass supplies a null 2D renderer; this
    // separate HUD route supplies the live renderer for swept-sphere text.
    void TriangleCollisionDebugComponent::RenderHUD(
        CgsDev::Debug2DImmediateRender* lpRenderer)
    {
        if (mbTestSweptSphere)
            TestPolySoupSweptSphereCollision(nullptr, lpRenderer);
    }

    // ARTIST 0x828C0E20. Extract the six inward clip planes from the renderer's
    // row-vector view-projection matrix. rw::collision::Frustum uses the native
    // RenderWare plane order: near, far, left, right, top, bottom.
    void TriangleCollisionDebugComponent::UpdateViewFrustum(
        CgsDev::Debug3DImmediateRender* lpRenderer)
    {
        CGS_ASSERT(lpRenderer != 0, "lpDisplay != NULL");

        const rw::math::vpu::Matrix44 lViewProjection =
            lpRenderer->GetViewProjectionMatrix();
        rw::math::vpu::Vector4 lColumn0;
        lColumn0.x = lViewProjection.xAxis.x;
        lColumn0.y = lViewProjection.yAxis.x;
        lColumn0.z = lViewProjection.zAxis.x;
        lColumn0.w = lViewProjection.wAxis.x;
        rw::math::vpu::Vector4 lColumn1;
        lColumn1.x = lViewProjection.xAxis.y;
        lColumn1.y = lViewProjection.yAxis.y;
        lColumn1.z = lViewProjection.zAxis.y;
        lColumn1.w = lViewProjection.wAxis.y;
        rw::math::vpu::Vector4 lColumn2;
        lColumn2.x = lViewProjection.xAxis.z;
        lColumn2.y = lViewProjection.yAxis.z;
        lColumn2.z = lViewProjection.zAxis.z;
        lColumn2.w = lViewProjection.wAxis.z;
        rw::math::vpu::Vector4 lColumn3;
        lColumn3.x = lViewProjection.xAxis.w;
        lColumn3.y = lViewProjection.yAxis.w;
        lColumn3.z = lViewProjection.zAxis.w;
        lColumn3.w = lViewProjection.wAxis.w;

        // ARTIST stores each extracted xyzw column combination unchanged,
        // including its homogeneous W lane; it does not negate the offset.
        rw::math::vpu::Vector4 laClipPlanes[6];
        laClipPlanes[0] = lColumn2;
        laClipPlanes[1].x = lColumn3.x - lColumn2.x;
        laClipPlanes[1].y = lColumn3.y - lColumn2.y;
        laClipPlanes[1].z = lColumn3.z - lColumn2.z;
        laClipPlanes[1].w = lColumn3.w - lColumn2.w;
        laClipPlanes[2].x = lColumn3.x + lColumn0.x;
        laClipPlanes[2].y = lColumn3.y + lColumn0.y;
        laClipPlanes[2].z = lColumn3.z + lColumn0.z;
        laClipPlanes[2].w = lColumn3.w + lColumn0.w;
        laClipPlanes[3].x = lColumn3.x - lColumn0.x;
        laClipPlanes[3].y = lColumn3.y - lColumn0.y;
        laClipPlanes[3].z = lColumn3.z - lColumn0.z;
        laClipPlanes[3].w = lColumn3.w - lColumn0.w;
        laClipPlanes[4].x = lColumn3.x - lColumn1.x;
        laClipPlanes[4].y = lColumn3.y - lColumn1.y;
        laClipPlanes[4].z = lColumn3.z - lColumn1.z;
        laClipPlanes[4].w = lColumn3.w - lColumn1.w;
        laClipPlanes[5].x = lColumn3.x + lColumn1.x;
        laClipPlanes[5].y = lColumn3.y + lColumn1.y;
        laClipPlanes[5].z = lColumn3.z + lColumn1.z;
        laClipPlanes[5].w = lColumn3.w + lColumn1.w;

        for (u32 luPlane = 0; luPlane < 6; ++luPlane)
        {
            mViewFrustum.SetPlane(luPlane, rw::collision::Plane(laClipPlanes[luPlane]));
        }
    }

    // ARTIST 0x828C09D8. Cull each soup list against the camera, then cull each
    // soup by its typed AxisAlignedBox4 bounds or the original strict 100-unit
    // squared-distance limit. Polygon and optional AABB drawing retain soup-list
    // order, and the callback-facing liSoup remains the soup index within its list.
    void TriangleCollisionDebugComponent::DrawPolySoups(
        CgsDev::Debug3DImmediateRender* lpRenderer)
    {
        CGS_ASSERT(lpRenderer != 0, "lpDisplay != NULL");

        static const u32 KAU_SOUP_COLOURS[16] =
        {
            0x608080FFu, 0x6000FFFFu, 0x6080FF80u, 0x60FF0000u,
            0x60400080u, 0x60808040u, 0x60FFFF00u, 0x600080FFu,
            0x60FF0080u, 0x60C0C0C0u, 0x60008000u, 0x600000FFu,
            0x60800040u, 0x60000000u, 0x60FFFFFFu, 0x60C08000u
        };

        const CgsGeometric::PolygonSoupListSpatialMap* lpSpatialMap =
            mpTriCollisionManager->GetPolySoupListSpacialMap();
        const s32 liNumPolySoupLists = lpSpatialMap->GetNumPolySoupLists();
        const rw::math::vpu::Vector3 lvCameraPosition = lpRenderer->GetCameraPosition();
        rw::math::vpu::Vector4 lvCameraPoint;
        lvCameraPoint.x = lvCameraPosition.x;
        lvCameraPoint.y = lvCameraPosition.y;
        lvCameraPoint.z = lvCameraPosition.z;
        lvCameraPoint.w = lvCameraPosition.w;

        for (s32 liSoupList = 0; liSoupList < liNumPolySoupLists; ++liSoupList)
        {
            const CgsGeometric::PolygonSoupList* lpSoupList =
                lpSpatialMap->GetPolySoupList(liSoupList);

            CgsGeometric::AxisAlignedBox lSoupListBounds;
            lSoupListBounds.mMin.x = lpSoupList->mOverallAabb[0];
            lSoupListBounds.mMin.y = lpSoupList->mOverallAabb[1];
            lSoupListBounds.mMin.z = lpSoupList->mOverallAabb[2];
            lSoupListBounds.mMin.w = lpSoupList->mOverallAabb[3];
            lSoupListBounds.mMax.x = lpSoupList->mOverallAabb[4];
            lSoupListBounds.mMax.y = lpSoupList->mOverallAabb[5];
            lSoupListBounds.mMax.z = lpSoupList->mOverallAabb[6];
            lSoupListBounds.mMax.w = lpSoupList->mOverallAabb[7];
            if (!lSoupListBounds.ContainsPoint(lvCameraPoint))
                continue;

            for (s32 liSoup = 0; liSoup < lpSoupList->GetNumPolygonSoups(); ++liSoup)
            {
                const CgsGeometric::PolygonSoup* lpPolySoup =
                    lpSoupList->GetPolygonSoup(liSoup);
                const CgsGeometric::AxisAlignedBox lSoupBounds =
                    lpSoupList->Get4Boxes(liSoup / 4)->GetAxisAlignedBox(
                        static_cast<u32>(liSoup % 4));
                const rw::math::vpu::Vector4& lrMin = lSoupBounds.mMin;
                const rw::math::vpu::Vector4& lrMax = lSoupBounds.mMax;
                const f32 lfDx = lvCameraPosition.x - (lrMin.x + lrMax.x) * 0.5f;
                const f32 lfDy = lvCameraPosition.y - (lrMin.y + lrMax.y) * 0.5f;
                const f32 lfDz = lvCameraPosition.z - (lrMin.z + lrMax.z) * 0.5f;
                const f32 lfSqDistToSoup = lfDx * lfDx + lfDy * lfDy + lfDz * lfDz;

                if (!lSoupBounds.ContainsPoint(lvCameraPoint) && !(lfSqDistToSoup < 10000.0f))
                    continue;

                for (u32 lu8Poly = 0; lu8Poly < lpPolySoup->GetNumPolygons(); ++lu8Poly)
                {
                    DrawPolySoupPoly(lpRenderer, lpPolySoup, liSoup,
                                     static_cast<u8>(lu8Poly), true);
                }

                if (mbDrawSoupAabbs)
                {
                    rw::math::vpu::Vector3 lvMin;
                    lvMin.x = lSoupBounds.mMin.x;
                    lvMin.y = lSoupBounds.mMin.y;
                    lvMin.z = lSoupBounds.mMin.z;
                    lvMin.w = lSoupBounds.mMin.w;
                    rw::math::vpu::Vector3 lvMax;
                    lvMax.x = lSoupBounds.mMax.x;
                    lvMax.y = lSoupBounds.mMax.y;
                    lvMax.z = lSoupBounds.mMax.z;
                    lvMax.w = lSoupBounds.mMax.w;
                    const u32 luColour = KAU_SOUP_COLOURS[static_cast<u32>(liSoup) % 16u]
                                       | 0xFF000000u;
                    lpRenderer->DrawBox(lvMin, lvMax, RwRGBAFromPackedWord(luColour));
                }
            }
        }
    }

    // ARTIST 0x828B3B98. Unpack the polygon, compute its plane/centre, run the
    // original visibility and optional draw-distance gates, then dispatch its
    // callback. The optional edge-cosine pass draws the axis-angle normal marker
    // once per stored perimeter edge.
    void TriangleCollisionDebugComponent::DrawPolySoupPoly(
        CgsDev::Debug3DImmediateRender* lpRenderer,
        const CgsGeometric::PolygonSoup* lpPolySoup,
        s32 liSoup,
        u8 lu8Poly,
        bool lbCullPolys)
    {
        CGS_ASSERT(lpRenderer != 0, "lpDisplay != NULL");

        const CgsGeometric::PolygonSoupPoly* lpPoly =
            reinterpret_cast<const CgsGeometric::PolygonSoupPoly*>(
                lpPolySoup->GetPolygon(lu8Poly));
        const bool lbIsQuad = lu8Poly < lpPolySoup->GetNumQuads();
        const s32 liNumVertices = lbIsQuad ? 4 : 3;

        rw::math::vpu::Vector3 laPolyPoints[4];
        for (s32 liVertex = 0; liVertex < liNumVertices; ++liVertex)
        {
            // ARTIST sub_828AF0D0: shared packed-vertex expansion (native halfwords).
            laPolyPoints[liVertex] =
                lpPolySoup->GetVertexPosition(lpPoly->mau8VertexIndex[liVertex]);
        }

        const rw::math::vpu::Vector3& lrVertex0 = laPolyPoints[0];
        const rw::math::vpu::Vector3& lrVertex1 = laPolyPoints[1];
        const rw::math::vpu::Vector3& lrVertex2 = laPolyPoints[2];
        const f32 lfEdge01X = lrVertex1.x - lrVertex0.x;
        const f32 lfEdge01Y = lrVertex1.y - lrVertex0.y;
        const f32 lfEdge01Z = lrVertex1.z - lrVertex0.z;
        const f32 lfEdge12X = lrVertex2.x - lrVertex1.x;
        const f32 lfEdge12Y = lrVertex2.y - lrVertex1.y;
        const f32 lfEdge12Z = lrVertex2.z - lrVertex1.z;
        rw::math::vpu::Vector3 lPolyNormal;
        lPolyNormal.x = std::fma(lfEdge01Y, lfEdge12Z, -lfEdge01Z * lfEdge12Y);
        lPolyNormal.y = std::fma(lfEdge01Z, lfEdge12X, -lfEdge01X * lfEdge12Z);
        lPolyNormal.z = std::fma(lfEdge01X, lfEdge12Y, -lfEdge01Y * lfEdge12X);
        const f32 lfNormalLength = std::sqrt(
            lPolyNormal.x * lPolyNormal.x +
            lPolyNormal.y * lPolyNormal.y +
            lPolyNormal.z * lPolyNormal.z);
        const f32 lfInvNormalLength = 1.0f / lfNormalLength;
        lPolyNormal.x *= lfInvNormalLength;
        lPolyNormal.y *= lfInvNormalLength;
        lPolyNormal.z *= lfInvNormalLength;
        lPolyNormal.w = 0.0f;

        rw::math::vpu::Vector3 lAveragePoint;
        lAveragePoint.x = 0.0f;
        lAveragePoint.y = 0.0f;
        lAveragePoint.z = 0.0f;
        for (s32 liVertex = 0; liVertex < liNumVertices; ++liVertex)
        {
            lAveragePoint.x += laPolyPoints[liVertex].x;
            lAveragePoint.y += laPolyPoints[liVertex].y;
            lAveragePoint.z += laPolyPoints[liVertex].z;
        }
        const f32 lfInverseVertexCount = 1.0f / static_cast<f32>(liNumVertices);
        lAveragePoint.x *= lfInverseVertexCount;
        lAveragePoint.y *= lfInverseVertexCount;
        lAveragePoint.z *= lfInverseVertexCount;
        lAveragePoint.w = 0.0f;

        const rw::math::vpu::Vector3 lvCameraPosition = lpRenderer->GetCameraPosition();
        const f32 lfCameraDx = lvCameraPosition.x - lAveragePoint.x;
        const f32 lfCameraDy = lvCameraPosition.y - lAveragePoint.y;
        const f32 lfCameraDz = lvCameraPosition.z - lAveragePoint.z;
        const f32 lfSqDistToPoly =
            lfCameraDx * lfCameraDx + lfCameraDy * lfCameraDy + lfCameraDz * lfCameraDz;

        if (IsPolyVisible(laPolyPoints, liNumVertices, lpRenderer) &&
            (!lbCullPolys || lfSqDistToPoly < mfSoupDrawDistance * mfSoupDrawDistance))
        {
            DrawCollisionPoly(lpRenderer, laPolyPoints, liNumVertices, lPolyNormal,
                              lpPoly->muSurfaceTag, liSoup);
        }

        if (!mbDrawEdgeCosines)
            return;

        static const u8 KAU_QUAD_EDGE_START[4] = { 0, 1, 2, 3 };
        static const u8 KAU_QUAD_EDGE_END[4]   = { 1, 3, 0, 2 };
        static const u8 KAU_TRI_EDGE_START[3]  = { 0, 1, 2 };
        static const u8 KAU_TRI_EDGE_END[3]    = { 1, 2, 0 };
        static const u32 KAU_QUAD_EDGE_COLOURS[4] =
        {
            0xFFFFFFFFu, 0xFF00FF00u, 0xFFFF0000u, 0xFF000000u
        };
        const s32 liNumEdges = lbIsQuad ? 4 : 3;
        for (s32 liEdge = 0; liEdge < liNumEdges; ++liEdge)
        {
            const u8 luStart = lbIsQuad ? KAU_QUAD_EDGE_START[liEdge]
                                         : KAU_TRI_EDGE_START[liEdge];
            const u8 luEnd = lbIsQuad ? KAU_QUAD_EDGE_END[liEdge]
                                       : KAU_TRI_EDGE_END[liEdge];
            const rw::math::vpu::Vector3& lrPointA = laPolyPoints[luStart];
            const rw::math::vpu::Vector3& lrPointB = laPolyPoints[luEnd];
            rw::math::vpu::Vector3 lvEdge;
            lvEdge.x = lrPointB.x - lrPointA.x;
            lvEdge.y = lrPointB.y - lrPointA.y;
            lvEdge.z = lrPointB.z - lrPointA.z;
            const f32 lfEdgeLength = std::sqrt(
                lvEdge.x * lvEdge.x + lvEdge.y * lvEdge.y + lvEdge.z * lvEdge.z);
            const f32 lfInverseEdgeLength = 1.0f / lfEdgeLength;
            rw::math::vpu::Vector3 lAxis;
            lAxis.x = lvEdge.x * lfInverseEdgeLength;
            lAxis.y = lvEdge.y * lfInverseEdgeLength;
            lAxis.z = lvEdge.z * lfInverseEdgeLength;
            lAxis.w = 0.0f;

            rw::math::vpu::Vector3 lEdgeCentre;
            lEdgeCentre.x = (lrPointA.x + lrPointB.x) * 0.5f;
            lEdgeCentre.y = (lrPointA.y + lrPointB.y) * 0.5f;
            lEdgeCentre.z = (lrPointA.z + lrPointB.z) * 0.5f;
            lEdgeCentre.w = 0.0f;
            const f32 lfEdgeCosine = static_cast<f32>(
                lpPoly->GetEdgeCosineUncompressed(static_cast<u32>(liEdge)));
            const f32 lfEdgeAngle = XboxMath::XMVectorACos(lfEdgeCosine);
            f32 lfSine;
            f32 lfCosine;
            SinCosTriangleDebugAngle(lfEdgeAngle, lfSine, lfCosine);
            const rw::math::vpu::Vector3 lRenderEdgeCos =
                RotateTriangleDebugNormal(lPolyNormal, lAxis, lfSine, lfCosine);
            const rw::math::vpu::Vector3 lPointA = lEdgeCentre;
            rw::math::vpu::Vector3 lPointB;
            lPointB.x = lEdgeCentre.x + lRenderEdgeCos.x;
            lPointB.y = lEdgeCentre.y + lRenderEdgeCos.y;
            lPointB.z = lEdgeCentre.z + lRenderEdgeCos.z;
            lPointB.w = 0.0f;
            const u32 luColour = lbIsQuad ? KAU_QUAD_EDGE_COLOURS[liEdge]
                                           : 0xFF0000FFu;
            lpRenderer->DrawLine(lPointA, lPointB, RwRGBAFromPackedWord(luColour));
        }
    }

    // ARTIST 0x828BF8E0. Initialize and draw the selected sphere, reject soup lists
    // whose whole-list AABB does not strictly contain its center, then run the
    // original four-lane sphere contact and valid-triangle debug passes.
    void TriangleCollisionDebugComponent::TestPolySoupSphereCollision(
        CgsDev::Debug3DImmediateRender* lpRenderer)
    {
        if (mbNeedToInitSpherePos)
        {
            const rw::math::vpu::Vector3 lvCameraPosition =
                lpRenderer->GetCameraPosition();
            mSpherePos.X() = lvCameraPosition.x;
            mSpherePos.Y() = lvCameraPosition.y;
            mSpherePos.Z() = lvCameraPosition.z;
            mbNeedToInitSpherePos = false;
            mSpherePos.Z() += 10.0f; // flt_82004A20
        }

        const rw::math::vpu::Vector3 lvSphereCentre{
            mSpherePos.X(), mSpherePos.Y(), mSpherePos.Z(), mfSphereRad
        };
        const CgsGeometric::Sphere lSphere{
            rw::math::vpu::Vector4{
                mSpherePos.X(), mSpherePos.Y(), mSpherePos.Z(), mfSphereRad
            }
        };
        lpRenderer->DrawSphere(lvSphereCentre, mfSphereRad,
                               RwRGBAFromPackedWord(0xFFFFFFFFu));

        const CgsGeometric::PolygonSoupListSpatialMap* lpSpatialMap =
            mpTriCollisionManager->GetPolySoupListSpacialMap();
        const s32 liNumPolySoupLists = lpSpatialMap->GetNumPolySoupLists();
        const f32 KF_EXTRACTIONRADIUS = 5.0f;    // flt_820F2718
        const f32 KF_SPHERECONTACTPADDING = 1.0f; // 0x828BFB08..0x828BFB1C
        const f32 KF_TRIANGLEOFFSET = 0.02f;       // flt_82005574
        const VecFloat lvSphereContactPadding{
            KF_SPHERECONTACTPADDING, KF_SPHERECONTACTPADDING,
            KF_SPHERECONTACTPADDING, KF_SPHERECONTACTPADDING
        };

        for (s32 liSoupList = 0; liSoupList < liNumPolySoupLists; ++liSoupList)
        {
            const CgsGeometric::PolygonSoupList* lpPolySoupList =
                lpSpatialMap->GetPolySoupList(liSoupList);

            // ARTIST calls AxisAlignedBox::ContainsPoint on the resource's first
            // eight floats: a strict center-in-whole-list test, not a radius overlap.
            const f32* const lapOverallAabb = lpPolySoupList->mOverallAabb;
            CgsGeometric::AxisAlignedBox lOverallAabb;
            lOverallAabb.Set(
                rw::math::vpu::Vector4{
                    lapOverallAabb[0], lapOverallAabb[1], lapOverallAabb[2], lapOverallAabb[3]
                },
                rw::math::vpu::Vector4{
                    lapOverallAabb[4], lapOverallAabb[5], lapOverallAabb[6], lapOverallAabb[7]
                });
            if (!lOverallAabb.ContainsPoint(lSphere.mPositionRadius))
                continue;

            const CgsGeometric::PolygonSoup* const* lpapPolySoups =
                reinterpret_cast<const CgsGeometric::PolygonSoup* const*>(
                    lpPolySoupList->mpapPolySoups);
            for (s32 liPolySoup = 0; liPolySoup < lpPolySoupList->miNumPolySoups;
                 ++liPolySoup)
            {
                CGS_ASSERT(liPolySoup >= 0 && liPolySoup < lpPolySoupList->miNumPolySoups,
                           "liPolySoupIndex >= 0 && liPolySoupIndex < GetNumPolygonSoups()");
                const CgsGeometric::PolygonSoup& lrPolySoup = *lpapPolySoups[liPolySoup];

                CgsGeometric::Triangle4 laTriangle4s[1024];
                // ARTIST temporarily writes 5.0 into sphere W for extraction,
                // then restores the selected radius before the contact tests.
                CgsGeometric::Sphere lExtractionSphere = lSphere;
                lExtractionSphere.mPositionRadius.w = KF_EXTRACTIONRADIUS;
                const s32 liNumTriangle4s =
                    CgsGeometric::ExtractTriangle4ListIntersectingSphere(
                        lrPolySoup, lExtractionSphere, laTriangle4s, 0x400, nullptr);
                for (s32 liTriangle4 = 0; liTriangle4 < liNumTriangle4s; ++liTriangle4)
                {
                    rw::math::vpu::Vector3 laContactNormals[4];
                    rw::math::vpu::Vector3 laTriangleNormals[4];
                    rw::math::vpu::Vector3Plus laSphereContactPoints[4];
                    rw::math::vpu::Vector3Plus laTriangleContactPoints[4];
                    const CgsGeometric::Triangle4::Mask4 lContactMask =
                        CgsGeometric::IntersectTriangle4Sphere_HackyBurnoutVersion(
                            lSphere, laTriangle4s[liTriangle4], lvSphereContactPadding,
                            laContactNormals[0], laTriangleNormals[0],
                            laSphereContactPoints[0], laTriangleContactPoints[0],
                            laContactNormals[1], laTriangleNormals[1],
                            laSphereContactPoints[1], laTriangleContactPoints[1],
                            laContactNormals[2], laTriangleNormals[2],
                            laSphereContactPoints[2], laTriangleContactPoints[2],
                            laContactNormals[3], laTriangleNormals[3],
                            laSphereContactPoints[3], laTriangleContactPoints[3]);

                    const f32 lafContactMask[4] = {
                        lContactMask.x, lContactMask.y, lContactMask.z, lContactMask.w
                    };
                    for (s32 liLane = 0; liLane < 4; ++liLane)
                    {
                        // IntersectTriangle4Sphere returns full-word masks for hits.
                        if (lafContactMask[liLane] != 0.0f)
                        {
                            // The X360 vector call orders triangle contact before sphere contact.
                            lpRenderer->DrawLine(
                                laTriangleContactPoints[liLane].GetVector3(),
                                laSphereContactPoints[liLane].GetVector3(),
                                RwRGBAFromPackedWord(0xFF0000FFu));
                        }
                    }

                    const f32 lafValidMask[4] = {
                        laTriangle4s[liTriangle4].mValidMasks.x,
                        laTriangle4s[liTriangle4].mValidMasks.y,
                        laTriangle4s[liTriangle4].mValidMasks.z,
                        laTriangle4s[liTriangle4].mValidMasks.w
                    };
                    for (s32 liLane = 0; liLane < 4; ++liLane)
                    {
                        // The extractor marks unused tail lanes with an all-zero valid mask.
                        if (lafValidMask[liLane] == 0.0f)
                            continue;

                        CgsGeometric::Triangle4::AOSTriangle lAOSTriangle;
                        laTriangle4s[liTriangle4].GetAOSTriangle(liLane, lAOSTriangle);
                        // VMX vmaddfp computes normal*0.02 + vertex before the solid draw.
                        const rw::math::vpu::Vector3 lvV0{
                            std::fma(lAOSTriangle.mNormal.x, KF_TRIANGLEOFFSET,
                                     lAOSTriangle.mVertex0.x),
                            std::fma(lAOSTriangle.mNormal.y, KF_TRIANGLEOFFSET,
                                     lAOSTriangle.mVertex0.y),
                            std::fma(lAOSTriangle.mNormal.z, KF_TRIANGLEOFFSET,
                                     lAOSTriangle.mVertex0.z),
                            std::fma(lAOSTriangle.mNormal.w, KF_TRIANGLEOFFSET,
                                     lAOSTriangle.mVertex0.w)
                        };
                        const rw::math::vpu::Vector3 lvV1{
                            std::fma(lAOSTriangle.mNormal.x, KF_TRIANGLEOFFSET,
                                     lAOSTriangle.mVertex1.x),
                            std::fma(lAOSTriangle.mNormal.y, KF_TRIANGLEOFFSET,
                                     lAOSTriangle.mVertex1.y),
                            std::fma(lAOSTriangle.mNormal.z, KF_TRIANGLEOFFSET,
                                     lAOSTriangle.mVertex1.z),
                            std::fma(lAOSTriangle.mNormal.w, KF_TRIANGLEOFFSET,
                                     lAOSTriangle.mVertex1.w)
                        };
                        const rw::math::vpu::Vector3 lvV2{
                            std::fma(lAOSTriangle.mNormal.x, KF_TRIANGLEOFFSET,
                                     lAOSTriangle.mVertex2.x),
                            std::fma(lAOSTriangle.mNormal.y, KF_TRIANGLEOFFSET,
                                     lAOSTriangle.mVertex2.y),
                            std::fma(lAOSTriangle.mNormal.z, KF_TRIANGLEOFFSET,
                                     lAOSTriangle.mVertex2.z),
                            std::fma(lAOSTriangle.mNormal.w, KF_TRIANGLEOFFSET,
                                     lAOSTriangle.mVertex2.w)
                        };
                        lpRenderer->DrawSolidTriangle(
                            lvV0, lvV1, lvV2, RwRGBAFromPackedWord(0x64FFFFFFu));
                    }
                }
            }
        }
    }

    // ARTIST 0x828BFE80. Initialize the box from the debug camera when requested,
    // draw its oriented wire/fill/axis, gather candidate Triangle4 batches through
    // the map's typed box query and sphere extractor, then run the four-lane
    // IntersectTriangleBox contact pass.
    void TriangleCollisionDebugComponent::TestPolySoupBoxCollision(
        CgsDev::Debug3DImmediateRender* lpRenderer)
    {
        if (mbNeedToInitBoxPos)
        {
            const rw::math::vpu::Vector3 lvCameraPosition =
                lpRenderer->GetCameraPosition();
            mBoxPos.Set(lvCameraPosition.x, lvCameraPosition.y, lvCameraPosition.z);
            mbNeedToInitBoxPos = false;
            mBoxPos.Z() += 10.0f; // flt_82004A20
        }

        rw::math::vpu::Vector3 lvBoxPosition;
        lvBoxPosition.x = mBoxPos.X();
        lvBoxPosition.y = mBoxPos.Y();
        lvBoxPosition.z = mBoxPos.Z();
        lvBoxPosition.w = 0.0f;
        rw::math::vpu::Vector3 lvBoxAngles;
        lvBoxAngles.x = mBoxOrientation.X();
        lvBoxAngles.y = mBoxOrientation.Y();
        lvBoxAngles.z = mBoxOrientation.Z();
        lvBoxAngles.w = 0.0f;
        rw::math::vpu::Matrix44Affine lTransform =
            Matrix44AffineFromEulerXYZ(lvBoxAngles);
        lTransform.wAxis = lvBoxPosition;

        rw::math::vpu::Vector3 lvBoxHalfSize;
        lvBoxHalfSize.x = mBoxSize.X() * 0.5f;
        lvBoxHalfSize.y = mBoxSize.Y() * 0.5f;
        lvBoxHalfSize.z = mBoxSize.Z() * 0.5f;
        lvBoxHalfSize.w = 0.0f;
        CgsGeometric::Box lBox;
        lBox.Set(lTransform, lvBoxHalfSize,
                 rw::math::vpu::Vector4{0.0f, 0.0f, 0.0f, 0.0f});

        const rw::math::vpu::Vector3 lvLocalMin{
            -lvBoxHalfSize.x, -lvBoxHalfSize.y, -lvBoxHalfSize.z, 0.0f
        };
        const rw::math::vpu::Vector3 lvLocalMax{
            lvBoxHalfSize.x, lvBoxHalfSize.y, lvBoxHalfSize.z, 0.0f
        };
        lpRenderer->DrawBox(lvLocalMin, lvLocalMax, lTransform,
                            RwRGBAFromPackedWord(0xFFFFFFFFu));
        lpRenderer->DrawSolidBox(lvLocalMin, lvLocalMax, lTransform,
                                 RwRGBAFromPackedWord(0x1EFFFFFFu));
        lpRenderer->DrawAxis(lTransform);

        // The console uses half of the largest authored dimension for both the
        // query sphere radius and its AABB, including the w lane initialized from
        // a zero Vector3 center. Keep that original broad-phase shape.
        const f32 lfSizeXY = (mBoxSize.X() - mBoxSize.Y() >= 0.0f)
                           ? mBoxSize.X() : mBoxSize.Y();
        const f32 lfMaxSize = (lfSizeXY - mBoxSize.Z() >= 0.0f)
                            ? lfSizeXY : mBoxSize.Z();
        const f32 lfRadius = lfMaxSize * 0.5f;

        CgsGeometric::Sphere lBoundingSphere;
        lBoundingSphere.mPositionRadius.x = lvBoxPosition.x;
        lBoundingSphere.mPositionRadius.y = lvBoxPosition.y;
        lBoundingSphere.mPositionRadius.z = lvBoxPosition.z;
        lBoundingSphere.mPositionRadius.w = lfRadius;

        CgsGeometric::AxisAlignedBox lBoundingBox;
        lBoundingBox.mMin = rw::math::vpu::Vector4{
            lvBoxPosition.x - lfRadius,
            lvBoxPosition.y - lfRadius,
            lvBoxPosition.z - lfRadius,
            -lfRadius};
        lBoundingBox.mMax = rw::math::vpu::Vector4{
            lvBoxPosition.x + lfRadius,
            lvBoxPosition.y + lfRadius,
            lvBoxPosition.z + lfRadius,
            lfRadius};

        // RunQuery publishes its leaf-index list into the mutable spatial map.
        // The console stores this manager as const but calls that mutator directly.
        TriangleCollisionManager* lpManager =
            const_cast<TriangleCollisionManager*>(mpTriCollisionManager);
        CgsGeometric::PolygonSoupListSpatialMap* lpSpatialMap =
            lpManager->GetPolySoupListSpacialMap();
        const s32 liNumSoupLists = lpSpatialMap->RunQuery(lBoundingBox);

        CgsGeometric::Triangle4 laTriangles[1024];
        s32 liNumTriangle4s = 0;
        if (liNumSoupLists > 0)
        {
            const u16* lpaLeafIndices = lpSpatialMap->GetOutputQueryBuffer();
            const CgsGeometric::PolygonSoupLeafNode* lpaLeafNodes =
                lpSpatialMap->GetLeafNodes();

            for (s32 liSoupList = 0; liSoupList < liNumSoupLists; ++liSoupList)
            {
                const CgsGeometric::PolygonSoupLeafNode& lrLeaf =
                    lpaLeafNodes[lpaLeafIndices[liSoupList]];
                const CgsGeometric::AxisAlignedBox& lrLeafBox = lrLeaf.mBox;

                // The X360 SIMD reduction is inclusive on all four vector lanes.
                const bool lbLeafOverlapsBox =
                    (lrLeafBox.mMax.x >= lBoundingBox.mMin.x) &&
                    (lrLeafBox.mMax.y >= lBoundingBox.mMin.y) &&
                    (lrLeafBox.mMax.z >= lBoundingBox.mMin.z) &&
                    (lrLeafBox.mMax.w >= lBoundingBox.mMin.w) &&
                    (lBoundingBox.mMax.x >= lrLeafBox.mMin.x) &&
                    (lBoundingBox.mMax.y >= lrLeafBox.mMin.y) &&
                    (lBoundingBox.mMax.z >= lrLeafBox.mMin.z) &&
                    (lBoundingBox.mMax.w >= lrLeafBox.mMin.w);
                if (!lbLeafOverlapsBox)
                    continue;

                const s32 liRemainingTriangle4s = 1024 - liNumTriangle4s;
                liNumTriangle4s += CgsGeometric::ExtractTriangle4ListIntersectingSphere(
                    *lrLeaf.mpPolygonSoup,
                    lBoundingSphere,
                    laTriangles + liNumTriangle4s,
                    liRemainingTriangle4s,
                    nullptr);
            }
        }

        miNumBoxTests = 0;
        u64 luTotalIntersectionTicks = 0;
        rw::math::vpu::Vector3 laTriangleNormals[32];
        rw::math::vpu::Vector3 laContactNormals[32];
        rw::math::vpu::Vector3 laTrianglePoints[32];
        rw::math::vpu::Vector3 laContactPoints[32];
        for (s32 liTriangle4 = 0; liTriangle4 < liNumTriangle4s; ++liTriangle4)
        {
            const CgsGeometric::Triangle4& lrTriangle4 = laTriangles[liTriangle4];
            const f32* lapValidMaskLanes = &lrTriangle4.mValidMasks.x;
            for (s32 liLane = 0; liLane < 4; ++liLane)
            {
                CGS_ASSERT(liLane < 4, "liIndex < 4");
                if (lapValidMaskLanes[liLane] == 0.0f)
                    continue;

                CgsGeometric::Triangle4::AOSTriangle lAOSTriangle;
                lrTriangle4.GetAOSTriangle(liLane, lAOSTriangle);
                lpRenderer->DrawSolidTriangle(
                    lAOSTriangle.mVertex0,
                    lAOSTriangle.mVertex1,
                    lAOSTriangle.mVertex2,
                    RwRGBAFromPackedWord(0x320000FFu));
                lpRenderer->DrawHollowTriangle(
                    lAOSTriangle.mVertex0,
                    lAOSTriangle.mVertex1,
                    lAOSTriangle.mVertex2,
                    RwRGBAFromPackedWord(0xFF000000u));

                CgsGeometric::Triangle lTriangle;
                lTriangle.Set(lAOSTriangle.mVertex0,
                              lAOSTriangle.mVertex1,
                              lAOSTriangle.mVertex2);
                s32 liNumContacts = 0;
                const rw::math::vpu::Vector4 lvPadding{
                    0.1f, 0.1f, 0.1f, 0.1f}; // flt_82004014
                const rw::math::vpu::MaskScalar lvClampPenetration{
                    0.0f, 0.0f, 0.0f, 0.0f}; // unk_8327F240+0x10, raw initial zero

                const u64 luIntersectionStart = CgsSystem::GetSystemTimerBaseTime64();
                (void)CgsGeometric::IntersectTriangleBox(
                    lBox,
                    lTriangle,
                    lvPadding,
                    lvClampPenetration,
                    laTriangleNormals,
                    laContactNormals,
                    laTrianglePoints,
                    laContactPoints,
                    &liNumContacts,
                    0x20);
                luTotalIntersectionTicks +=
                    CgsSystem::GetSystemTimerBaseTime64() - luIntersectionStart;
                ++miNumBoxTests;

                for (s32 liContact = 0; liContact < liNumContacts; ++liContact)
                {
                    lpRenderer->DrawPoint(
                        laTrianglePoints[liContact],
                        RwRGBAFromPackedWord(0xFF00FFFFu));
                    lpRenderer->DrawPoint(
                        laContactPoints[liContact],
                        RwRGBAFromPackedWord(0xFFFF00FFu));
                    lpRenderer->DrawLine(
                        laTrianglePoints[liContact],
                        laContactPoints[liContact],
                        RwRGBAFromPackedWord(0xFFFFFFFFu));

                    rw::math::vpu::Vector3 lvNormalEnd;
                    lvNormalEnd.x =
                        laTrianglePoints[liContact].x + laTriangleNormals[liContact].x;
                    lvNormalEnd.y =
                        laTrianglePoints[liContact].y + laTriangleNormals[liContact].y;
                    lvNormalEnd.z =
                        laTrianglePoints[liContact].z + laTriangleNormals[liContact].z;
                    lvNormalEnd.w =
                        laTrianglePoints[liContact].w + laTriangleNormals[liContact].w;
                    lpRenderer->DrawArrow(
                        laTrianglePoints[liContact],
                        lvNormalEnd,
                        RwRGBAFromPackedWord(0xFF0000FFu));
                }
            }
        }

        const u64 luTimerFrequency = CgsSystem::GetSystemTimerFrequency64();
        muBoxTestCycles = static_cast<u32>(
            (luTotalIntersectionTicks * 0xCCCCCCCCu) / luTimerFrequency);
        mfBoxTestTime = static_cast<f32>(
            static_cast<f64>(luTotalIntersectionTicks * 1000u) /
            static_cast<f64>(luTimerFrequency));
        muBoxTestCyclesPerTriangle = muBoxTestCycles /
            static_cast<u32>(miNumBoxTests);
        mfBoxTestPercent = static_cast<f32>(
            static_cast<f64>(luTotalIntersectionTicks * 6000u) /
            static_cast<f64>(luTimerFrequency));
    }

    // ARTIST 0x828B3580. Build the swept sphere from the menu's start/velocity,
    // gather Triangle4 candidates in the original padded query box, and draw the
    // valid triangles plus the single-triangle swept-contact results.
    void TriangleCollisionDebugComponent::TestPolySoupSweptSphereCollision(
        CgsDev::Debug3DImmediateRender* lp3DRenderer,
        CgsDev::Debug2DImmediateRender* lp2DRenderer)
    {
        if (mbNeedToInitSweptSpherePos)
        {
            mSweptSpherePos.X() = 3027.28f;       // flt_820F47AC
            mSweptSpherePos.Y() = -2.5220001f;    // flt_820F47A8
            mSweptSpherePos.Z() = -1945.551f;     // flt_820F47A4
            mbNeedToInitSweptSpherePos = false;
        }

        if (lp2DRenderer)
        {
            lp2DRenderer->DrawText("Testing polygon soup swept sphere collision",
                                   50.0f, 50.0f, 12.0f,
                                   0xFFFFFFFFu);
        }

        const rw::math::vpu::Vector3 lvStartPosition{
            mSweptSpherePos.X(), mSweptSpherePos.Y(), mSweptSpherePos.Z(), 0.0f
        };
        const rw::math::vpu::Vector3 lvVelocity{
            mSweptSphereVelocity.X(), mSweptSphereVelocity.Y(),
            mSweptSphereVelocity.Z(), 0.0f
        };

        // ARTIST computes length from the three velocity lanes. Its scalar broad-phase
        // path uses fused multiply-adds for the squared-length accumulation.
        const f32 lfVelocityXYLengthSquared =
            std::fma(lvVelocity.x, lvVelocity.x, lvVelocity.y * lvVelocity.y);
        const f32 lfVelocityLengthSquared =
            std::fma(lvVelocity.z, lvVelocity.z, lfVelocityXYLengthSquared);
        const f32 lfVelocityLength = std::sqrt(lfVelocityLengthSquared);

        // The broad-phase sphere/AABB uses (length + 2*radius) * 1.05 (raw
        // flt_82005448); the narrow-phase SweptSphere retains the authored radius.
        const f32 lfBroadPhaseRadius =
            std::fma(mSweptSphereSize, 2.0f, lfVelocityLength) * 1.05f;

        CgsGeometric::Sphere lBroadPhaseSphere;
        lBroadPhaseSphere.mPositionRadius = rw::math::vpu::Vector4{
            lvStartPosition.x, lvStartPosition.y, lvStartPosition.z, lfBroadPhaseRadius
        };

        CgsGeometric::AxisAlignedBox lQueryBox;
        lQueryBox.Set(
            rw::math::vpu::Vector4{
                lvStartPosition.x - lfBroadPhaseRadius,
                lvStartPosition.y - lfBroadPhaseRadius,
                lvStartPosition.z - lfBroadPhaseRadius,
                -lfBroadPhaseRadius
            },
            rw::math::vpu::Vector4{
                lvStartPosition.x + lfBroadPhaseRadius,
                lvStartPosition.y + lfBroadPhaseRadius,
                lvStartPosition.z + lfBroadPhaseRadius,
                lfBroadPhaseRadius
            });

        rw::math::vpu::Vector3 lvSweepDirection;
        if (lfVelocityLength <= 0.00001f) // flt_82004884
        {
            // The console selects rw::math::vpu::detail::gIVector in this arm.
            lvSweepDirection = rw::math::vpu::GetVector3_XAxis();
        }
        else
        {
            const f32 lfInverseLength = 1.0f / lfVelocityLength;
            lvSweepDirection = rw::math::vpu::Vector3{
                lvVelocity.x * lfInverseLength,
                lvVelocity.y * lfInverseLength,
                lvVelocity.z * lfInverseLength,
                0.0f
            };
        }

        CgsGeometric::SweptSphere lSweptSphere;
        lSweptSphere.Set(
            rw::math::vpu::Vector3Plus{
                lvStartPosition.x, lvStartPosition.y, lvStartPosition.z, mSweptSphereSize
            },
            rw::math::vpu::Vector3Plus{
                lvSweepDirection.x, lvSweepDirection.y, lvSweepDirection.z, lfVelocityLength
            });

        if (lp3DRenderer)
        {
            lp3DRenderer->DrawSphere(lvStartPosition, mSweptSphereSize,
                                     RwRGBAFromPackedWord(0xFFFF0000u));
            const rw::math::vpu::Vector3 lvSweepEnd{
                lvStartPosition.x + lvVelocity.x,
                lvStartPosition.y + lvVelocity.y,
                lvStartPosition.z + lvVelocity.z,
                0.0f
            };
            lp3DRenderer->DrawArrow(lvStartPosition, lvSweepEnd,
                                    RwRGBAFromPackedWord(0xFFFF00FFu));
        }

        // RunQuery mutates the map's result buffer; the X360 stores this manager as
        // const but calls the map's non-const query directly through its first member.
        TriangleCollisionManager* lpManager =
            const_cast<TriangleCollisionManager*>(mpTriCollisionManager);
        CgsGeometric::PolygonSoupListSpatialMap* lpSpatialMap =
            lpManager->GetPolySoupListSpacialMap();
        const s32 liNumLeaves = lpSpatialMap->RunQuery(lQueryBox);

        CgsGeometric::Triangle4 laTriangle4s[1024];
        s32 liNumTriangle4s = 0;
        if (liNumLeaves > 0)
        {
            const u16* lpaLeafIndices = lpSpatialMap->GetOutputQueryBuffer();
            const CgsGeometric::PolygonSoupLeafNode* lpaLeafNodes =
                lpSpatialMap->GetLeafNodes();

            for (s32 liQueryResult = 0; liQueryResult < liNumLeaves; ++liQueryResult)
            {
                const CgsGeometric::PolygonSoupLeafNode& lrLeaf =
                    lpaLeafNodes[lpaLeafIndices[liQueryResult]];
                const CgsGeometric::AxisAlignedBox& lrLeafBox = lrLeaf.mBox;

                // The console's VMX reduction is inclusive on all four lanes.
                const bool lbLeafOverlapsQuery =
                    (lrLeafBox.mMax.x >= lQueryBox.mMin.x) &&
                    (lrLeafBox.mMax.y >= lQueryBox.mMin.y) &&
                    (lrLeafBox.mMax.z >= lQueryBox.mMin.z) &&
                    (lrLeafBox.mMax.w >= lQueryBox.mMin.w) &&
                    (lQueryBox.mMax.x >= lrLeafBox.mMin.x) &&
                    (lQueryBox.mMax.y >= lrLeafBox.mMin.y) &&
                    (lQueryBox.mMax.z >= lrLeafBox.mMin.z) &&
                    (lQueryBox.mMax.w >= lrLeafBox.mMin.w);
                if (!lbLeafOverlapsQuery)
                    continue;

                const s32 liRemainingTriangle4s = 1024 - liNumTriangle4s;
                liNumTriangle4s += CgsGeometric::ExtractTriangle4ListIntersectingSphere(
                    *lrLeaf.mpPolygonSoup, lBroadPhaseSphere,
                    laTriangle4s + liNumTriangle4s, liRemainingTriangle4s, nullptr);
            }
        }

        for (s32 liTriangle4 = 0; liTriangle4 < liNumTriangle4s; ++liTriangle4)
        {
            const CgsGeometric::Triangle4& lrTriangle4 = laTriangle4s[liTriangle4];
            const f32 lafValidMask[4] = {
                lrTriangle4.mValidMasks.x, lrTriangle4.mValidMasks.y,
                lrTriangle4.mValidMasks.z, lrTriangle4.mValidMasks.w
            };
            for (s32 liLane = 0; liLane < 4; ++liLane)
            {
                CGS_ASSERT(liLane < 4, "liIndex < 4");
                if (lafValidMask[liLane] == 0.0f)
                    continue;

                CgsGeometric::Triangle4::AOSTriangle lAOSTriangle;
                lrTriangle4.GetAOSTriangle(liLane, lAOSTriangle);
                if (lp3DRenderer)
                {
                    lp3DRenderer->DrawSolidTriangle(
                        lAOSTriangle.mVertex0, lAOSTriangle.mVertex1, lAOSTriangle.mVertex2,
                        RwRGBAFromPackedWord(0x320000FFu));
                    lp3DRenderer->DrawHollowTriangle(
                        lAOSTriangle.mVertex0, lAOSTriangle.mVertex1, lAOSTriangle.mVertex2,
                        RwRGBAFromPackedWord(0xFF000000u));
                }

                CgsGeometric::Triangle lTriangle;
                lTriangle.Set(lAOSTriangle.mVertex0, lAOSTriangle.mVertex1,
                              lAOSTriangle.mVertex2);
                rw::math::vpu::Vector3 lContactNormal;
                rw::math::vpu::Vector3 lTriangleNormal;
                rw::math::vpu::Vector3Plus lSphereContactPoint;
                rw::math::vpu::Vector3Plus lTriangleContactPoint;
                const rw::math::vpu::MaskScalar lHitMask =
                    CgsGeometric::IntersectTriangleSweptSphere(
                        lSweptSphere, lTriangle, lContactNormal, lTriangleNormal,
                        lSphereContactPoint, lTriangleContactPoint);
                if (lHitMask.x == 0.0f || !lp3DRenderer)
                    continue;

                const rw::math::vpu::Vector3 lvTriangleContactPoint{
                    lTriangleContactPoint.x, lTriangleContactPoint.y,
                    lTriangleContactPoint.z, lTriangleContactPoint.w
                };
                const rw::math::vpu::Vector3 lvSphereContactPoint{
                    lSphereContactPoint.x, lSphereContactPoint.y,
                    lSphereContactPoint.z, lSphereContactPoint.w
                };
                lp3DRenderer->DrawPoint(
                    lvTriangleContactPoint, RwRGBAFromPackedWord(0xFF00FFFFu));
                lp3DRenderer->DrawPoint(
                    lvSphereContactPoint, RwRGBAFromPackedWord(0xFFFF00FFu));
                lp3DRenderer->DrawLine(
                    lvTriangleContactPoint, lvSphereContactPoint,
                    RwRGBAFromPackedWord(0xFFFFFFFFu));

                const rw::math::vpu::Vector3 lvArrowEnd{
                    lvTriangleContactPoint.x + lContactNormal.x,
                    lvTriangleContactPoint.y + lContactNormal.y,
                    lvTriangleContactPoint.z + lContactNormal.z,
                    lvTriangleContactPoint.w + lContactNormal.w
                };
                lp3DRenderer->DrawArrow(
                    lvTriangleContactPoint, lvArrowEnd,
                    RwRGBAFromPackedWord(0xFF0000FFu));
            }
        }
    }

    // ARTIST 0x828AAD50. Rebuild only when the menu-selected level count changes.
    // The 2 MiB backing store is retained for the component's lifetime; subsequent
    // rebuilds rewind the same LinearMalloc arena before carving the map.
    void TriangleCollisionDebugComponent::BuildSpacialMap()
    {
        if (miNumLevels == miLastNumLevels)
            return;

        miLastNumLevels = miNumLevels;
        if (mpcSpacialBuffer == 0)
        {
            mpcSpacialBuffer = new char[KI_SPACIAL_BUFFER_SIZE];
            mMalloc.Construct();
            mMalloc.Create(mpcSpacialBuffer, KI_SPACIAL_BUFFER_SIZE);
            mMalloc.SetAlignment(16);
        }
        else
        {
            mMalloc.FreeAll();
        }

        // The original member is const-qualified in DecFIGS, while ARTIST calls the
        // map's mutating BuildSpacialPartition through that stored manager pointer.
        // Remove only that qualification to reach the existing typed mutator.
        TriangleCollisionManager* lpManager =
            const_cast<TriangleCollisionManager*>(mpTriCollisionManager);
        lpManager->GetPolySoupListSpacialMap()->BuildSpacialPartition(
            &mMalloc, miNumLevels, 0x800);
        miMemUse = static_cast<s32>(mMalloc.GetUsage());
    }

    // ARTIST 0x828AAE08 repeats the first stored plane six times; the plane
    // address never advances. Preserve that original behavior and its exactly
    // three-negative-vertices rejection, including for four-vertex polygons.
    bool TriangleCollisionDebugComponent::IsPolyVisible(
        const rw::math::vpu::Vector3* lapVertices,
        s32 liNumVertices,
        CgsDev::Debug3DImmediateRender* lpRenderer)
    {
        if (liNumVertices <= 0)
            return true;

        const rw::math::vpu::Vector3 lvCameraPosition = lpRenderer->GetCameraPosition();
        const rw::collision::Frustum& lrFrustum = mViewFrustum;
        for (u32 luPlane = 0; luPlane < 6; ++luPlane)
        {
            const rw::collision::Plane& lrPlane = lrFrustum.GetPlane(0);
            const f32 lfNormalLength = std::sqrt(
                lrPlane.x * lrPlane.x + lrPlane.y * lrPlane.y + lrPlane.z * lrPlane.z);
            const f32 lfInverseNormalLength = 1.0f / lfNormalLength;
            const f32 lfNormalX = lrPlane.x * lfInverseNormalLength;
            const f32 lfNormalY = lrPlane.y * lfInverseNormalLength;
            const f32 lfNormalZ = lrPlane.z * lfInverseNormalLength;

            s32 liVerticesBehindPlane = 0;
            for (s32 liVertex = 0; liVertex < liNumVertices; ++liVertex)
            {
                const rw::math::vpu::Vector3& lrVertex = lapVertices[liVertex];
                const f32 lfSignedDistance =
                    (lrVertex.x - lvCameraPosition.x) * lfNormalX +
                    (lrVertex.y - lvCameraPosition.y) * lfNormalY +
                    (lrVertex.z - lvCameraPosition.z) * lfNormalZ;
                if (lfSignedDistance < 0.0f)
                    ++liVerticesBehindPlane;
            }

            if (liVerticesBehindPlane == 3)
                return false;
        }

        return true;
    }

    // ARTIST 0x828AAFC0. DrawPolySoupPoly calls this class-scoped routine with the
    // renderer in r3 (no component `this`); each registered callback receives the
    // original geometry, normal, surface tag, and polygon index after its user data.
    void TriangleCollisionDebugComponent::DrawCollisionPoly(
        CgsDev::Debug3DImmediateRender* lpRenderer,
        const rw::math::vpu::Vector3* lapVertices,
        s32 liNumVertices,
        rw::math::vpu::Vector3 lrNormal,
        u32 luSurfaceTag,
        s32 liPolyIndex)
    {
        for (s32 liCallback = 0; liCallback < siNumDrawPolyCallbacks; ++liCallback)
        {
            DrawCollisionPolyCallbackData& lrCallback =
                GetDrawCollisionPolyCallback(liCallback);
            lrCallback.GetCallback()(lpRenderer,
                                     lrCallback.GetUserData(),
                                     lapVertices,
                                     liNumVertices,
                                     lrNormal,
                                     luSurfaceTag,
                                     liPolyIndex);
        }
    }

    // ARTIST 0x828AAA68. Register each original field, its range/step/read-only rule, then
    // seed the two test-position refresh flags and copy the live spatial-map level count.
    void TriangleCollisionDebugComponent::OnActivate()
    {
        RegisterVariable(&mbDrawPolySoups, "Draw collision world");
        RegisterVariable(&mbDrawSoupAabbs, "Draw soup AABBs");

        RegisterVariable(&mfSoupDrawDistance, "Draw distance");
        SetRange(&mfSoupDrawDistance, 0.5f, 100.0f);
        SetStep(&mfSoupDrawDistance, 0.5f);

        RegisterVariable(&mbDrawEdgeCosines, "Draw edge cosines");
        RegisterVariable(&mbTestSweptSphere, "Test swept sphere collision");

        RegisterVariable(&mSweptSpherePos.X(), "S.Sphere X pos");
        SetStep(&mSweptSpherePos.X(), 0.25f);
        RegisterVariable(&mSweptSpherePos.Y(), "S.Sphere Y pos");
        SetStep(&mSweptSpherePos.Y(), 0.25f);
        RegisterVariable(&mSweptSpherePos.Z(), "S.Sphere Z pos");
        SetStep(&mSweptSpherePos.Z(), 0.25f);
        RegisterVariable(&mSweptSphereSize, "S.Sphere Radius");
        SetStep(&mSweptSphereSize, 0.05f);
        RegisterVariable(&mSweptSphereVelocity.X(), "S.Sphere X vel");
        SetStep(&mSweptSphereVelocity.X(), 0.05f);
        RegisterVariable(&mSweptSphereVelocity.Y(), "S.Sphere Y vel");
        SetStep(&mSweptSphereVelocity.Y(), 0.05f);
        RegisterVariable(&mSweptSphereVelocity.Z(), "S.Sphere Z vel");
        SetStep(&mSweptSphereVelocity.Z(), 0.05f);

        RegisterVariable(&miNumListsSearched, "Num lists searched");
        SetReadOnly(&miNumListsSearched, true);
        RegisterVariable(&miNumLevels, "Num spacial levels");
        SetRange(&miNumLevels, 1, KI_MAX_NUM_LEVELS);
        RegisterVariable(&miMemUse, "Spacial map memory use");
        SetReadOnly(&miMemUse, true);
        RegisterVariable(&miMaxLevelToDraw, "Max Draw Spacial Level");
        SetRange(&miMaxLevelToDraw, 0, KI_MAX_NUM_LEVELS);
        RegisterVariable(&miMinLevelToDraw, "Min Draw Spacial Level");
        SetRange(&miMinLevelToDraw, 0, KI_MAX_NUM_LEVELS);

        mbNeedToInitSpherePos = true;
        mbNeedToInitLinePosition = true;
        const s32 liNumLevels =
            mpTriCollisionManager->GetPolySoupListSpacialMap()->GetNumLevels();
        miLastNumLevels = liNumLevels;
        miNumLevels = liNumLevels;
    }
}
