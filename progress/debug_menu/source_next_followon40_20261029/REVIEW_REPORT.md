# Fresh source review: SoundDebug 31–40 and ArbStateTestbed camera

Reviewed from B5 HEAD `abbc9047d850a4665d959993012261c55205e5`. This report covers only the two requested frozen candidates. No shared source, ledger, canonical status, or prior review artifact was changed.

## SoundDebug 31–40 revision03

**VERDICT: pass** for the final `DualGinsuExhaustEffect::ProcessUpdate` source.

ARTIST `0x826FCDA0` loads the dynamic-mix pointer at `this+0x30`, calls `GetDMixOutput(6, 0)` when present, and selects zero when absent. It tests the reverse voice separately at the wrapper at `this+0x2EC` plus `0x38`, guards each setter, and always reaches `VoiceWrapper::Update`. ARTIST `EffectBase::GetRWACMixerOutputValue` has the same `+0x30` null check and volume conversion. B5 and DecFIGS name this pointer `mpDynamicMixIo`; `mCarSubmix` is a separate `Voice` field. The final source therefore removes the unsupported mCarSubmix gate and early returns and uses `HasLiveVoice()` for the two setter guards.

The sealed five-case control has a meaningful negative: revision02 produces zero in the dynamic-mixer-present / car-submix-absent / reverse-voice-live case where ARTIST expects `0.750022877`; revision03 matches ARTIST. Null mixer and absent reverse voice cases also agree. The actual owning-TU compile receipt reports pass for input SHA `23d98d7271429f40dd5ea2624a531c14b79453615f1a5b5b7842f740bdbd617b` with B5 environment HEAD `abbc9047d850a4665d959993012261c55205e5e5`.

The packet's canonical patch is CRLF and represents revision02 blob `e91299fb0c8910bb14b661717b3ce2f8eb07fd94` to post blob `fe4ae449b52a81a1c62d72336055a36a9d95c2b7`. It passes forward and reverse `git apply --check`. I derived a complete LF patch directly from exact B5 pre/post at [sound_baseline_to_post_lf.patch](/D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/review_source_leafbatch_20261029/sound_baseline_to_post_lf.patch). It has no CR bytes and applies against the pinned B5 source: pre blob `a9e594f927a94486547aaee4bbbbdeedd0992cef` equals the file blob at both the packet baseline and requested B5 HEAD; reverse apply-check against exact post also passes. Its SHA-256 is `1fab34c32ada3dc625074805f6126f44214292e5a3996d208d20da6e0fe53b78`.

Author packet: `scratch/DEBUG_MENU_1011/swarm_sound_debug_controls_31_40_source_recovery_20261029_revision03`. `SEAL.json` SHA-256 `0fc9e024051014369ecebb669e70a9fa0618963d5f4b33824c5eabc50420ff3b`; `MANIFEST.sha256` SHA-256 `a57a87458c91a4a876b1a69666c9f4c5aa9458e33e51088bd72a2e52b8c6b141`, with all 125 entries verified. The revision01/02 FAIL records remain preserved. No audio, PCM, or native runtime was checked.

## ArbStateTestbed camera three-file candidate

**VERDICT: pass** for the private candidate at `scratch/DEBUG_MENU_1011/swarm_arb_state_testbed_ice_anims_recovery_20261029`.

ARTIST `GetNormalCamera` and `CycleNormalCamera` both test `Arbitrator+0x2EC == 2`. Testbed Construct puts its camera at testbed `+0x10`, matching Arbitrator `+0x40`; testbed Update writes state value `2` at testbed `+0x2BC`, which is the same absolute `+0x2EC`. DecFIGS identifies `meState`, `E_STATE_GENERIC_UPDATE=2`, the declared `IsActive()` helper, and `Arbitrator::mArbStateTestbed`. Baseline `miDebugCameraMode` has only its declaration and the two reads, no writer. Candidate `IsActive()` tests exactly GENERIC_UPDATE; both readers call it and the phantom field is removed.

The LF candidate patch [candidate.patch](/D:/Reverse/BP-Decomp_Workflow/scratch/DEBUG_MENU_1011/swarm_arb_state_testbed_ice_anims_recovery_20261029/candidate.patch) SHA-256 is `4ec24a3ac65f892c44cc3fa039b062800607ac8279bd6057655c4bef99f7ce8a`; it passes `git apply --check` against the exact clean B5 target files at `abbc9047d850a4665d959993012261c55205e5e5`. Their source blobs match the pin. Actual owner-TU compile logs both exit 0 with canonical flags and private candidate headers. The omission negative control fails two routes on baseline and passes all four testbed lifecycle states on candidate.

`recovery_report.json` records author status `private_candidate_compile_control_pass_pending_review_native`. No `SEAL.json` exists for this packet. Integrity files: `manifest.json` SHA-256 `580535f67ff0ee65dc0f1c56071bc54dfdb9a6eda5d1d8f3847b2373e2dcd19b`; `source_integrity.json` SHA-256 `72ff35800856d0b94e875a30b62db6a9a6e2d769f1521597ec8150b8c346fa64`; `candidate_tree_integrity.json` SHA-256 `f8d544bd2481fb49e6f37b91afc4190b42e49296458ba686b78e0c1c96af5248`; `validation/result.json` SHA-256 `da0aa8175702534b6f88eba07f5bed3644d872737bc405eaaa278547c3955e7f`. No native camera playback, asset presence, or pixels were checked.