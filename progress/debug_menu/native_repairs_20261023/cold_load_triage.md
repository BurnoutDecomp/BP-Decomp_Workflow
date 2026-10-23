# Case B cold route load: Option0/profile triage

Scope: static af18 source and the retained Case B JSON/log artifacts only. No native run, input, build, compiler/test, CI, Git mutation, or shared-source change was made. Root performed the visual review of the Case B frames.

## Finding

The Case B evidence supports that the saved-options list never opened. The script's `saved_route_list_visible` is a mark after `tap:Option0; sleep:3`, not a wait for a UI signal. Its `ordinary_option0_list_select` check only tests those scripted marks. Case B's log reports the options page in substate 2 (`E_SUBSTATE_SELECTING_PARAMS`) and helpbar `used=2`, consistent with Continue/Back only. Root's frame review likewise saw CREATE EVENT with A Continue/B Back, then SELECT ROUTE. The first Accept advances the create page; the summary contains the default one-route payload (event 481033/count 1), not the persisted eight-route payload. These observations do not by themselves identify why Option0 did nothing.

## Input and UI path

At af18, `CgsInputPadsPC.cpp` maps controller Square to GUI action 51 and the named PC `Option0` channel to the same action. `OnlineGameOptions::HandleControllerInput` dispatches action input to `HandleControllerInputCreateGame` while substate is `E_SUBSTATE_SELECTING_PARAMS` (value 2). Its action-51 arm calls `ShowLoadScreen()` only if `GetNumCreatedOnlineGameOptions()` or `GetNumReceivedOnlineGameOptions()` is positive; otherwise it has no effect. `SetupHelpBar` uses the same count guard to add the Option0/load prompt. Thus the observed missing prompt points to an unavailable live list at screen entry; it does not prove whether action 51 arrived.

If the load page is entered, its load substate handles Accept by reading the selected list entry through `OptionsDataProfile::GetCreatedOnlineGameOptions` or `GetReceivedOnlineGameOptions`, copying that route into `mGameOptions`, and returning to the create page. A subsequent Accept advances to route selection. Case B's first Accept moved straight from ON_GAME_OPT to ON_SEL_ROUTE, matching the no-list path.

## Profile read path

The staged Case B profile-copy receipt reports an exact copy of Case A's `Profile.sav.after`, with `created_count=1` at file offset 177528, and no differences. The run log reports `[SaveLoadPC] bootup read: OK`.

At af18, `ProfileManager::Bootup` calls `ReadProfileData()` before storage boot. That method copies the live GuiCache options profile into the separate `mStoredData.mOptionsDataProfile` segment. `CgsSaveLoadPS3.cpp`'s PC `BootupStart` then reads the container into the stored-data view. On successful load, `ReportTaskCompleted` validates the stored segments, deserializes progression, copies the live-revenge segment, and calls `NotifyOtherModulesLoadComplete` on the stored OptionsDataProfile. That notification publishes scalar settings to other modules; the load-completion body does not copy the stored online-route arrays/counts into `mpGuiCache->GetOptionsDataProfile()`. GuiCache's embedded OptionsDataProfile is separately constructed with defaults.

ARTIST export `0x82513EC0` confirms the same sequence: NotifyOtherModulesLoadComplete uses the stored segment at `this+0x25530`, then event 19 is posted and the progression new-profile byte is mirrored to GuiCache. There is no full stored-options-to-GuiCache copy in that function. This makes a missing live-list handoff a strong explanation for the absent Option0 prompt, while the current evidence does not directly witness the live count at the moment of SetupHelpBar.

## Disposition

The Option0 action mapping and consumer guard are present in af18. The saved file is intact and the storage layer reports a successful read into the stored segment. The likely break is between the stored OptionsDataProfile and the live GuiCache list. The same absence appears in the ARTIST ReportTaskCompleted export, so a transfer fix would add behavior beyond that body; this triage does not propose or apply such a patch. Confirm the intended cold-load contract and capture the live created-count at SetupHelpBar before choosing a code change.
