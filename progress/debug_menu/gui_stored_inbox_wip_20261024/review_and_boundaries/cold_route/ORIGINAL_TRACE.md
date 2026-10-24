# Original live/stored options-profile trace

## 1. Two distinct owners and the serialized route fields

DecFIGS declares `ProfileStoredData::mOptionsDataProfile` as a `FixedSizeOpaqueBuffer<OptionsDataProfile>` of 29,552 bytes (`evidence/decfigs/BrnGuiProfile.h`, lines 245-260). `GuiCache` separately embeds a live `OptionsDataProfile` (`evidence/decfigs/BrnGuiCache.h`). These are different owning objects.

DecFIGS names ten created and ten received `OnlineSaveRoute` entries and the two counters (`evidence/decfigs/BrnGuiOptionsDataProfile.h`, lines 128-145). ARTIST offsets and the current source layout pin the counters at options-profile `+0x7308/+0x730C` (29,448/29,452); the created array begins at `+8`, the received array at `+0x3988`. The `OnlineSaveRoute` record is 0x5C0 bytes. On a `GuiCache`, ARTIST places the live options profile at `+0xB878` (47,224), so the two UI gates read cache `+76,672/+76,676`.

ARTIST `GuiCache::Construct` (`0x82505860`) constructs the embedded live options profile; `OptionsDataProfile::Construct` (`0x824FF558`) zeroes both counts. This establishes a fresh live-cache baseline, not the later state of any particular run.

## 2. Cold boot and explicit load both read the manager's stored image

ARTIST `ProfileManager::ReadProfileData` (`0x824FF298`) obtains `GuiCache::GetOptionsDataProfile()` and copies 29,552 bytes **from live cache to** `ProfileManager::mStoredData.mOptionsDataProfile` (`this+0x25530` in the relevant ARTIST layout). This is the serialization/preload direction. `ProfileManager::Bootup` (`0x82513870`) calls it before binding `BootupResult` and starting the save/load task.

ARTIST `CgsGui::SaveLoadSystem::BootupStart` (`0x82855A60`) builds the profile-load operation against the destination supplied by the manager metadata. The current PC adapter snapshot uses the captured stored-data view for the container read (`evidence/pc_d3ec/CgsSaveLoadPS3.cpp`, lines 846-895); this describes the PC storage edge, while the ARTIST export is authority for the original owner and callback sequence.

On boot, `HandleSaveLoadTaskResult` (`0x824EF7A0`) delivers the bound result; `BootupResult` (`0x82510F80`) records load success. The completion path later reaches `SetCollisionWorldValid` (`0x82517F50`) and `ReportTaskCompleted` (`0x82513EC0`) when the required world condition is met. For explicit profile loads, `ProfileManager::Load` (`0x82523D78`) binds `LoadResult`; `SaveLoadSystem::Load` (`0x82859B70`) and `LoadHandleConfirmLoad` (`0x82855EC0`) read into the stored-data destination, and successful `LoadResult` (`0x82517FB8`) calls `ReportTaskCompleted`. Both paths converge at the same completion routine.

The retained cold-boot profile was valid and had one created route in the copied disk image. That establishes stored-image content, not live-cache hydration.

## 3. What successful original completion does with options data

ARTIST `ProfileManager::ReportTaskCompleted` (`0x82513EC0`) first validates the stored profile. In its successful-profile case, its assembly:

1. deserializes the stored progression image into the live progression profile;
2. copies the stored live-revenge segment into the live revenge profile and posts its pointer event;
3. calls `OptionsDataProfile::NotifyOtherModulesLoadComplete` (`0x82511098`) with `this+0x25530`, the stored options-profile address;
4. posts event id 19 via `AddEvent` with payload size 1 (the stack byte/`li r6,1`), then reads the progression new-profile flag and writes only that byte to the GuiCache field at `+0x4B78`;
5. invokes the bound task-result handler and finishes the task.

The `memcpy` visible immediately before the Notify call is the live-revenge transfer (`this+0x1DFF0` to the live-revenge destination, size `0x7540`), not an options-profile copy. After Notify, the assembly does not load the stored route array/counter addresses, copy them, or pass an options-profile pointer in event 19. The one-byte event itself cannot carry route arrays. Raw assembly for this routine is preserved at `evidence/artist/0x82513EC0.json`; use the instructions around `0x82513FC4-0x82514024` for these stores and calls.

ARTIST xrefs show `NotifyOtherModulesLoadComplete` has two direct callers in this packet's symbol export set: `ReportTaskCompleted` (`0x82513EC0`) and `ScreenLoading::ApplyOptionsDataProfileSettings` (`0x824D0DC0`). The latter passes `mpGuiCache->GetOptionsDataProfile()`, the **live** object, while reapplying settings. Its function is not a stored-profile adoption path. The Notify body posts scalar/settings events (Trax availability/selection, volume, VOIP, play order, camera, controller flags, tips and camera feed); it does not post either saved-route array or either route count. See `evidence/artist/0x82511098.json` and `evidence/pc_d3ec/BrnGuiOptionsDataProfile.cpp`, lines 566-615.

The callback bodies do not fill this gap: ARTIST `BootProfile::HandleProfileTaskResult` (`0x82474468`) advances the boot-flow state, and `ProfileHost::HandleProfileTaskResult` (`0x827E21E0`) is logging-only. Current source snapshots are included for cross-checking (`BrnBootProfile.cpp` and `BrnGuiProfileHost.cpp`). Event 19 is the profile manager's one-byte completion broadcast; this packet does not claim to have enumerated every possible listener to that broadcast. No route-array receiver is established by the traced callback, the event payload, or the Notify call.

## 4. The route UI reads only the live cache; known writers are elsewhere

ARTIST `OnlineGameOptions::SetupHelpBar` (`0x82485C78`) and `HandleControllerInputCreateGame` (`0x824A7878`) read the created/received counts from GuiCache `+0x12B80/+0x12B84` (decimal 76,672/76,676). Helpbar adds Option0/Load only if either live count is positive. The Option0 handler has the same gate before calling `ShowLoadScreen` (`0x8249C760`). `ShowLoadOptions` (`0x8248C878`) selects a created/received family from those same live counts and reads the live route entries; `HandleControllerInputLoadOptions` (`0x824A7E48`) applies the selected route.

The current source snapshots make those gates easy to locate:

- `BrnOnlineGameOptions_wI_06.cpp`, lines 115-160: helpbar count gate;
- `BrnOnlineGameOptions_wI_09.cpp`, lines 396-408: Option0 count gate;
- `BrnOnlineGameOptions_wI_08.cpp`, lines 187-260: load-list family and first route reads;
- `BrnOnlineGameOptions_wS34_00.cpp`: selected-route handling.

ARTIST's known route-array writers are also accounted for:

- `SetCreatedOnlineGameOptions` (`0x824824A0`) is called by `OnlineGameOptionsSummary::HandleOverlayComplete` (`0x8249DB78`) and the save control `HandleControllerInputSaveOptions` (`0x824A8C58`).
- `AddReceivedOnlineGameOptions` (`0x82482690`) is called by `OnlineLoading::OnLeave` (`0x8249B070`) after network receipt.

Those are live route creation/save and network-receipt writers. No stored-profile result callback is among these direct callers. This bounded xref check does not prove no arbitrary whole-image writer exists elsewhere in the executable.

## 5. Retained case and exact evidentiary limit

The retained case B artifacts are from source `af18caf8a9e02428cfaa4705599e2b1ca9ea7377`, binary `e9fc6246dece`; original full-log SHA-256 is in `bindings.json`.

`native_acceptance.json` records the copied profile's `created_count=1`, `options_base=148080`, count offset `177528` (= base + 29,448), created-slot offset `148088` (= base + 8), slot size 1,472, and matching copied/disk slot hashes. The excerpted original log records boot read `OK`, all profile validation segments passing, `ON_GAME_OPT`, helpbar `used=2` observations, then `ON_SEL_ROUTE`; the selected route readiness was `count=1, landmarks[4671]`, unlike the saved route's `count=8` and its recorded landmarks.

The run is consistent with a loaded stored profile whose route list never becomes visible in the live cache. It does not directly read live-cache counters, so that last step is an inference from the source gate plus the helpbar count and the later selected-route payload. The harness `saved_route_list_visible` field is a tap/sleep marker only, not an observed UI state. See `evidence/retained_case_b/REPORT.md`, `native_acceptance.json`, and the line-numbered `BrnGame_excerpt.txt`.

## 6. Boundary

Evidence proves the direction of the `ReadProfileData` copy, the stored object passed on successful completion, the one-byte event 19 payload, the separate live object read by the route UI, and the known route-array writers. It does not prove a whole-program absence of every possible event-19 subscriber or hidden/global alias. No original owner has been found that transfers stored route arrays/counts to the live profile. Therefore there is no faithful C++ patch to propose from this evidence alone. Keep the route-load behavior unresolved until an ARTIST caller/receiver or other original ownership path is identified; do not add a guessed `memcpy` or event-specific bridge.
