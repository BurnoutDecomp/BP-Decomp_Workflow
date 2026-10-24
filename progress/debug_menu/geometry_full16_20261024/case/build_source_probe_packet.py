"""Create immutable proposal snapshots from exact36ae. Only packet scratch is written."""
from __future__ import annotations
import difflib
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
B5 = ROOT / "b5-decomp"
COMMIT = "36ae3ffed6e8fb3ea89ca91947647aa9465c8658"
TRI = "src/GameShared/GameClasses/SceneManager/TriangleCollision/CgsTriangleCollisionDebugComponent.cpp"
SWP = "src/GameShared/GameClasses/SceneManager/ContactGen/CgsSceneSweeperDebugComponent.cpp"
DEV = "src/pc/gcm/renderengine/device.cpp"

def show(path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(B5), "show", f"{COMMIT}:{path}"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

tri_include_old = b"#include <cmath>\n#include <cstring>\n"
tri_include_new = b"""#include "GameShared/GameClasses/Development/Log/CgsLog.h" // [case witness] bounded RenderWorld readbacks
#include <cmath>
#include <cstring>
#include <cstdlib> // [case witness] opt-in read-only geometry owner diagnostics
"""
tri_body_old = b"""        if (mbTestSweptSphere)
            TestPolySoupSweptSphereCollision(lpRenderer, nullptr);
    }
"""
tri_body_new = b"""        if (mbTestSweptSphere)
            TestPolySoupSweptSphereCollision(lpRenderer, nullptr);

        // [case witness] Read-only owner/dispatch evidence. Inert unless the launched
        // process has BRN_DEBUG_GEOMETRY_WITNESS. Log the first owner row, stored
        // control-tuple changes, and soup empty/nonempty transitions only. The one-game
        // schedule needs at most37 control transitions + 1 initial row + 2 readiness rows;
        // the 40-row cap is exact and does not sample frames or growing soup counts.
        static const bool sbGeometryWitnessEnabled =
            std::getenv("BRN_DEBUG_GEOMETRY_WITNESS") != nullptr;
        static bool sbGeometryWitnessHasPrevious = false;
        static u32 suGeometryWitnessRows = 0;
        static bool sbPreviousSoupReady = false;
        static s32 siPreviousRequestedLevels = -1;
        static f32 sfPreviousSoupDistance = 0.0f;
        static bool sbPreviousDrawWorld = false;
        static bool sbPreviousDrawAabbs = false;
        static bool sbPreviousDrawEdges = false;
        static bool sbPreviousSweepTest = false;
        static f32 sfPreviousPosX = 0.0f;
        static f32 sfPreviousPosY = 0.0f;
        static f32 sfPreviousPosZ = 0.0f;
        static f32 sfPreviousRadius = 0.0f;
        static f32 sfPreviousVelX = 0.0f;
        static f32 sfPreviousVelY = 0.0f;
        static f32 sfPreviousVelZ = 0.0f;
        if (sbGeometryWitnessEnabled && mpTriCollisionManager != nullptr)
        {
            const CgsGeometric::PolygonSoupListSpatialMap* lpMap =
                mpTriCollisionManager->GetPolySoupListSpacialMap();
            const s32 liSoupLists = lpMap->GetNumPolySoupLists();
            const s32 liMapLevels = lpMap->GetNumLevels();
            const bool lbSoupReady = liSoupLists > 0;
            const f32 lfSoupDistance = mfSoupDrawDistance;
            const f32 lfPosX = mSweptSpherePos.X();
            const f32 lfPosY = mSweptSpherePos.Y();
            const f32 lfPosZ = mSweptSpherePos.Z();
            const f32 lfRadius = mSweptSphereSize;
            const f32 lfVelX = mSweptSphereVelocity.X();
            const f32 lfVelY = mSweptSphereVelocity.Y();
            const f32 lfVelZ = mSweptSphereVelocity.Z();
            const bool lbChanged = !sbGeometryWitnessHasPrevious ||
                lbSoupReady != sbPreviousSoupReady || miNumLevels != siPreviousRequestedLevels ||
                lfSoupDistance != sfPreviousSoupDistance ||
                mbDrawPolySoups != sbPreviousDrawWorld ||
                mbDrawSoupAabbs != sbPreviousDrawAabbs ||
                mbDrawEdgeCosines != sbPreviousDrawEdges ||
                mbTestSweptSphere != sbPreviousSweepTest ||
                lfPosX != sfPreviousPosX || lfPosY != sfPreviousPosY ||
                lfPosZ != sfPreviousPosZ || lfRadius != sfPreviousRadius ||
                lfVelX != sfPreviousVelX || lfVelY != sfPreviousVelY ||
                lfVelZ != sfPreviousVelZ;
            if (lbChanged && suGeometryWitnessRows < 40u &&
                CgsDev::Log::gpDebugPrint != nullptr)
            {
                sbGeometryWitnessHasPrevious = true;
                sbPreviousSoupReady = lbSoupReady;
                siPreviousRequestedLevels = miNumLevels;
                sfPreviousSoupDistance = lfSoupDistance;
                sbPreviousDrawWorld = mbDrawPolySoups;
                sbPreviousDrawAabbs = mbDrawSoupAabbs;
                sbPreviousDrawEdges = mbDrawEdgeCosines;
                sbPreviousSweepTest = mbTestSweptSphere;
                sfPreviousPosX = lfPosX;
                sfPreviousPosY = lfPosY;
                sfPreviousPosZ = lfPosZ;
                sfPreviousRadius = lfRadius;
                sfPreviousVelX = lfVelX;
                sfPreviousVelY = lfVelY;
                sfPreviousVelZ = lfVelZ;
                ++suGeometryWitnessRows;
                CgsDev::Log::gpDebugPrint->AppendFormat(
                    "[geometry-witness] owner=triangle sample=%u soup_lists=%d map_levels=%d requested_levels=%d memory_bytes=%d soup_distance=%.6f draw_world=%u draw_aabbs=%u draw_edges=%u sweep_test=%u pos_x=%.6f pos_y=%.6f pos_z=%.6f radius=%.6f vel_x=%.6f vel_y=%.6f vel_z=%.6f\\n",
                    suGeometryWitnessRows, liSoupLists, liMapLevels, miNumLevels, miMemUse, lfSoupDistance,
                    static_cast<unsigned>(mbDrawPolySoups),
                    static_cast<unsigned>(mbDrawSoupAabbs),
                    static_cast<unsigned>(mbDrawEdgeCosines),
                    static_cast<unsigned>(mbTestSweptSphere),
                    lfPosX, lfPosY, lfPosZ, lfRadius, lfVelX, lfVelY, lfVelZ);
            }
        }
    }
"""
swp_include_anchor = b'#include "GameShared/GameClasses/SceneManager/ContactGen/CgsSceneSweeper.h"\n'
swp_include_add = swp_include_anchor + b'#include "GameShared/GameClasses/Development/Log/CgsLog.h" // [case witness] bounded RenderWorld readbacks\n\n#include <cstdlib> // [case witness] opt-in read-only interval owner diagnostics\n'
swp_body_old = b"""    // ARTIST 0x828B6708.
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
"""
swp_body_new = b"""    // ARTIST 0x828B6708.
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
                    "[geometry-witness] owner=sweeper sample=%u owner_ready=%u dynamic_intervals=%u inactive_intervals=%u draw_dynamic=%u draw_frozen=%u draw_distance=%.6f\\n",
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
"""

dev_gate_old = b'''    if (sacDir[0] == 0 || (renderengine::guDispatchPresentCountPC % renderengine::FrameDumpEvery()) != 0u)
    {
        return;
    }
'''
dev_gate_new = b'''    // [case capture] BRN_FRAME_DUMP_REQUEST=1 switches this private positive-slot
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
        if (lpEnd == lacSlot || *lpEnd != '\\0' || luSlot == 0u || luSlot > 65535u) return 0u;
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
                          "Local\\\\BurnoutPC_FrameRequest_%lu_%lu",
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
'''
dev_close_old = b'''                fclose(lpFile);

                // [diag] Stamp the SIMULATION timestep'''
dev_close_new = b'''                if (sbNamedFrameRequest)
                {
                    const int liFrameWriteError = ferror(lpFile);
                    const int liFrameCloseResult = fclose(lpFile);
                    if (liFrameWriteError == 0 && liFrameCloseResult == 0 &&
                        shNamedFrameRequest != nullptr && ResetEvent(shNamedFrameRequest))
                    {
                        ++suNamedFrameSequence;
                        char lacAck[256];
                        std::snprintf(lacAck, sizeof(lacAck),
                                      "[frame-request] pid=%lu slot=%u seq=%u present=%u file=bb_%06u.bmp\\n",
                                      static_cast<unsigned long>(GetCurrentProcessId()), suNamedFrameSlot,
                                      suNamedFrameSequence, renderengine::guDispatchPresentCountPC,
                                      renderengine::guDispatchPresentCountPC);
                        CgsDev::Log::WriteToLog(lacAck);
                    }
                }
                else { fclose(lpFile); }

                // [diag] Stamp the SIMULATION timestep'''

def main() -> None:
    rows = {}
    diffs = []
    for source_path, name in ((TRI, "triangle"), (SWP, "sweeper"), (DEV, "device")):
        original = show(source_path)
        if name == "triangle":
            if original.count(tri_include_old) != 1 or original.count(tri_body_old) != 1:
                raise SystemExit(f"exact36ae triangle anchors not unique: {source_path}")
            updated = original.replace(tri_include_old, tri_include_new, 1)
            updated = updated.replace(tri_body_old, tri_body_new, 1)
        elif name == "sweeper":
            if original.count(swp_include_anchor) != 1 or original.count(swp_body_old) != 1:
                raise SystemExit(f"exact36ae sweeper anchors not unique: {source_path}")
            updated = original.replace(swp_include_anchor, swp_include_add, 1)
            updated = updated.replace(swp_body_old, swp_body_new, 1)
        else:
            if original.count(dev_gate_old) != 1 or original.count(dev_close_old) != 1:
                raise SystemExit(f"exact36ae frame-writer anchors not unique: {source_path}")
            updated = original.replace(dev_gate_old, dev_gate_new, 1)
            updated = updated.replace(dev_close_old, dev_close_new, 1)
        for subdir, content in (("pre", original), ("post", updated)):
            path = PACKET / "source" / subdir / source_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        diffs.extend(difflib.unified_diff(
            original.decode("utf-8").splitlines(keepends=True),
            updated.decode("utf-8").splitlines(keepends=True),
            fromfile=f"a/{source_path}", tofile=f"b/{source_path}"))
        rows[source_path] = {
            "pre_bytes": len(original), "pre_sha256": digest(original),
            "post_bytes": len(updated), "post_sha256": digest(updated),
            "post_image": f"source/post/{source_path}",
        }
    patch_bytes = "".join(diffs).encode("utf-8")
    manifest = {"base_source": COMMIT, "files": rows,
                "patch_bytes": len(patch_bytes), "patch_sha256": digest(patch_bytes),
                "purpose": "env-gated typed owner/dispatch readbacks and one-shot PID/slot frame requests; hosted build required"}
    (PACKET / "source" / "patch.diff").write_bytes(patch_bytes)
    (PACKET / "source" / "BINDINGS.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
