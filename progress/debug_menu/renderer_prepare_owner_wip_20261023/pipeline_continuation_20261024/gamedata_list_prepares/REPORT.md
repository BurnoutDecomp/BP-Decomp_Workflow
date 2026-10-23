# Original list prepares: five complete caller bodies

This source proposal adds the original two-stack challenge, ICE, wheel, HUD and popup helpers. Each submits real resource requests, pumps the original ResourceModule dependency while pending, and adopts the returned resource through the existing typed owner. It adds no activation, native adapter, artificial success, trap or source mount.

The sole changed path is `src/GameSource/Resource/BrnGameDataModule.cpp`, bound to source `2ceaa5e83aa0abaeb1ffde20867061daf953d673`. Removing the single added method payload reproduces the entire exact preimage byte for byte. All existing methods, including the active two-argument Prepare and native zero-argument helpers, retain their complete byte payloads.

| Original helper | ARTIST | Pool | Load / acquire | Completion |
|---|---|---:|---|---|
| PrepareFreeburnChallengeList | 8266C088 | 26 | OnlineChallenges.bndl / B5ChallengeList | AddListResource; stage5; clear receiver |
| PrepareICEList | 8266CEB0 | 5 | Cameras.bundle / StandardICETakes | AddListResource; stage5; clear receiver |
| PrepareWheelList | 8266D1F8 | 5 | Wheels/WheelList.bundle / B5WheelList | AddListResource; stage2; clear receiver |
| PrepareHudMessages | 8266C8E0 | 11 | HudMessages.hm / HudMessages.hm | AddMessages; stage5; retain receiver |
| PreparePopups | 8266CBA0 | 11 | Popups.pup / Popups.pup | AddPopupResource; clear receiver; stage5 |

The wheel's success store is positively `2` at ARTIST8266D4EC. The prior native generic helper deliberately used5; its body remains unchanged. The original five helpers also preserve their different receiver-clear timing and failure-permitted load flags. HUD does not assert response event-id0; the other four do. No new null-handle skip, result-code policy or allocation guard is introduced.

All five create and write-lock a Resource input before inspecting their substage, including completed and invalid substages. Pending paths unlock, call original UpdateResourceModule, destroy the input, and return false. Success paths unlock and destroy the input without pumping. This differs from the allocation helpers, which retain the newest carve on success; the original owner governs each lifetime.

The entire sealed sixth packet is a semantic and link prerequisite: it supplies original ResourceModule Update and the real buffer destructor chain. `PREREQUISITE_OVERLAY.json` binds every sixth-packet pre/post path and its full manifest hash; no sixth-packet path overlaps this packet's caller preimage. The reviewer has identified the still-missing canonical SetDiskErrorOccured setter in that dependency. A separate correction must supply it; this packet does not claim link readiness. Root has separately frozen and reviewed the one-byte GameData header include correction; it is not duplicated here.

Two original GameData helpers remain: schema registration and the vehicle list. Vehicle recovery must retain its real ResourcePtr/Entry diagnostic stream dependencies; schema recovery must identify the actual builtin blob owner and the PC data boundary. Initialization, original Construct/factory ownership, existing native allocation capacity, thread order and renderer activation remain separate work.

Shipping mount checks use the exact parent `build_game_exe.bat` and `compile_exe.py` source route. The changed caller and every named canonical CPP provider are already explicitly listed. CMake is not executable authority. No compile, link, test, CI or native run was performed; Root owns those gates and publication. Debug registration counts are unchanged.
