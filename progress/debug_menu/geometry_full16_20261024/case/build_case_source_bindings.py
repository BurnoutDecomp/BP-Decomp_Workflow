"""Bind source evidence for the full16 case to exact36ae and pinned artifacts."""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[2]
B5 = ROOT / "b5-decomp"
B5_COMMIT = "36ae3ffed6e8fb3ea89ca91947647aa9465c8658"

B5_FILES = {
    "src/GameShared/GameClasses/Development/DebugSystem/Core/CgsDebugComponent.cpp": ["void DebugComponent::Register()", "GetPath()"],
    "src/GameShared/GameClasses/Development/DebugSystem/Core/CgsDebugComponent.h": ["virtual const char* GetName() const", "virtual const char* GetPath() const"],
    "src/GameShared/GameClasses/Development/DebugSystem/Core/CgsDebugManager.cpp": ["void DebugManager::RenderWorld", "lpComponent->RenderWorld(mp3dRender)"],
    "src/GameShared/GameClasses/Development/DebugSystem/Core/CgsDebugManager.h": ["RenderWorld("],
    "src/GameShared/GameClasses/Development/DebugSystem/Core/UI/ScriptInterface/CgsScriptInterface.cpp": ["CreateAlias(", "SetValueFromString", "<PATH/NAME> - Activate the debug component"],
    "src/GameShared/GameClasses/Geometric/Primitives/PolygonSoup/CgsPolygonSoupListSpatialMap.h": ["GetNumLevels() const", "GetNumPolySoupLists() const"],
    "src/GameShared/GameClasses/RenderWare/RwRGBA.cpp": ["RGBA::RGBA(uint8_t", "lu8Alpha) << 24"],
    "src/GameShared/GameClasses/SceneManager/CgsSceneManagerModule.cpp": ["BridgeInputSceneUpdateInterfaceToSubModules", "mOverlapGenerator.Update"],
    "src/GameShared/GameClasses/SceneManager/ContactGen/CgsIntervalList.h": ["GetNumIntervals() const"],
    "src/GameShared/GameClasses/SceneManager/ContactGen/CgsOverlapGenerationModule.cpp": ["mSweeper.Update", "GenerateOverlaps"],
    "src/GameShared/GameClasses/SceneManager/ContactGen/CgsSceneSweeper.cpp": ["mDebugComponent.Register()", "SceneSweeper::Update"],
    "src/GameShared/GameClasses/SceneManager/ContactGen/CgsSceneSweeper.h": ["GetDynamicIntervalList()", "GetInactiveIntervalList()"],
    "src/GameShared/GameClasses/SceneManager/ContactGen/CgsSceneSweeperDebugComponent.cpp": ["SceneSweeperDebugComponent::OnActivate", "SceneSweeperDebugComponent::RenderWorld"],
    "src/GameShared/GameClasses/SceneManager/ContactGen/CgsSceneSweeperDebugComponent.h": ["GetName() const override", "GetPath() const override"],
    "src/GameShared/GameClasses/SceneManager/TriangleCollision/CgsTriangleCollisionDebugComponent.cpp": ["TriangleCollisionDebugComponent::OnActivate", "TriangleCollisionDebugComponent::RenderWorld", "TestPolySoupSweptSphereCollision"],
    "src/GameShared/GameClasses/SceneManager/TriangleCollision/CgsTriangleCollisionDebugComponent.h": ["GetName() const override", "GetPath() const override"],
    "src/GameShared/GameClasses/SceneManager/TriangleCollision/CgsTriangleCollisionManager.cpp": ["mDebugComponent.Register()", "ProcessAddPolySoupListEvents"],
    "src/GameShared/GameClasses/SceneManager/TriangleCollision/CgsTriangleCollisionManager.h": ["GetPolySoupListSpacialMap() const", "GetNumPolySoupLists() const"],
    "src/GameSource/Game/BrnGameModule.cpp": ["DebugManagerRender", "DebugManager::Render"],
    "src/GameSource/GameFlowController/TopLevel/BrnGameMainFlowStates.cpp": ["DriveWorldUpdateFrame", "PrepareWorldCollision"],
    "src/GameSource/Graphics/BrnRendererModule.cpp": ["mIm3dDebugRenderBuffer", "Dispatch"],
    "src/GameSource/World/BrnWorldModule.cpp": ["PrepareWorldCollision", "WorldEntityModule"],
    "src/GameSource/World/EntityModules/WorldEntityModule/BrnWorldEntityModule.cpp": ["AddPolySoupList", "PrepareWorldCollision"],
    "src/pc/gcm/renderengine/device.cpp": ["static void DumpBackBufferIfRequested()", "BRN_FRAME_DUMP_EVERY", "PCGetBackBuffer(&lpBack)", "GetRenderTargetData(lpBack, lpSys)", "bb_%06u.bmp"],
    "vendor/renderware/include/rw/rwcore_structs.h": ["struct RGBA", "m_rgba"],
}

ARTIST_FILES = [
    ".ida-exports/BURNOUT_X360_ARTIST.XEX/0x821F05B0.json",
    ".ida-exports/BURNOUT_X360_ARTIST.XEX/0x828AAA68.json",
    ".ida-exports/BURNOUT_X360_ARTIST.XEX/0x828AC240.json",
    ".ida-exports/BURNOUT_X360_ARTIST.XEX/0x828AC2A0.json",
    ".ida-exports/BURNOUT_X360_ARTIST.XEX/0x828B3580.json",
    ".ida-exports/BURNOUT_X360_ARTIST.XEX/0x828B6708.json",
    ".ida-exports/BURNOUT_X360_ARTIST.XEX/0x828CAE88.json",
]
DECFIGS_FILES = [
    "references/DecFIGS/dwarfdump/GameShared/GameClasses/SceneManager/TriangleCollision/CgsTriangleCollisionDebugComponent.h",
    "references/DecFIGS/dwarfdump/GameShared/GameClasses/SceneManager/ContactGen/CgsSceneSweeperDebugComponent.h",
    "references/DecFIGS/dwarfdump/GameShared/GameClasses/SceneManager/ContactGen/CgsSceneSweeper.h",
]

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def git_blob(repo: Path, revision: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), "show", f"{revision}:{path}"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

def anchors(data: bytes, patterns: list[str]) -> list[dict[str, object]]:
    lines = data.decode("utf-8", errors="replace").splitlines()
    result = []
    for pattern in patterns:
        match = next(((n, line.strip()) for n, line in enumerate(lines, 1) if pattern in line), None)
        result.append({"pattern": pattern, "line": match[0] if match else None, "source_text": match[1] if match else None})
    return result

def main() -> None:
    b5_rows = {}
    for path, patterns in B5_FILES.items():
        data = git_blob(B5, B5_COMMIT, path)
        b5_rows[path] = {"source": "b5-decomp exact36ae Git blob", "bytes": len(data), "sha256": sha(data), "anchors": anchors(data, patterns)}
    outer_head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
    build_path = "tools/build/build_game_exe.bat"
    build_data = git_blob(ROOT, outer_head, build_path)
    outer_rows = {build_path: {"outer_head": outer_head, "bytes": len(build_data), "sha256": sha(build_data),
        "anchors": anchors(build_data.decode("utf-8", errors="replace").encode("utf-8"), [
            r'echo "%SRC%\GameShared\GameClasses\SceneManager\Contactgen\CgsSceneSweeperDebugComponent.cpp"',
            r'echo "%SRC%\GameShared\GameClasses\SceneManager\TriangleCollision\CgsTriangleCollisionDebugComponent.cpp"',
            r'echo "%SRC%\GameShared\GameClasses\RenderWare\RwRGBA.cpp"',
            r'echo "%SRC%\pc\gcm\renderengine\device.cpp"'])}}
    artifact_rows = {}
    for rel in ARTIST_FILES + DECFIGS_FILES:
        path = ROOT / rel
        data = path.read_bytes()
        artifact_rows[rel.replace("\\", "/")] = {"bytes": len(data), "sha256": sha(data)}
    doc = {
        "candidate_source": B5_COMMIT,
        "candidate_tree": "11d65ea7620c833b4fe36d943f85bfdc2a186128",
        "purpose": "read-only provenance for the exact full16 case code paths and original ARTIST/DecFIGS witnesses",
        "b5_sources": b5_rows,
        "outer_build_mount": outer_rows,
        "artist_and_decfigs": artifact_rows,
    }
    (PACKET / "CASE_SOURCE_BINDINGS.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
