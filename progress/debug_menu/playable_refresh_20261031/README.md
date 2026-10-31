# October 31 playable build refresh

Installed `build/game/Burnout_PC.exe`: **052112a5aa52**, B5 dev **ca8027774**, clean build workflow **71be01e0c**. The recovered thirteen-body jump-filming source and current upstream changes are included. The separate diagnostic executable is not installed.

The full 3,019-TU build passed with zero errors and 86 warnings outside the recovered jump code. A private copy of the latest user save passed all 12 startup/current-profile/driving checks: 235.1 m travel, one gameplay wreck, zero assertions/exceptions, exact owned cleanup/input reset and five attributed captures. Root inspected the first normal driving frame and the later real wreck frame. The EA/Criterion sequence completed with SkipIntro absent; intro-video pixels are not separately certified. Audio was muted for the test.

All 15 runtime payloads are verified after installation. Old payloads are backed up; 21 existing save/config/log files and five shared work files retain their exact hashes. No assets were reconverted, and no normal game/profile launch was performed. [Installation receipt](NORMAL_INSTALL_EXECUTION.json), [native proof](NATIVE_VERIFICATION.json), [archive](ARCHIVE_RECEIPT.json).

**Jump behavior remains pending.** The diagnostic disabled run reached the requested area, but the authored trigger-centre height 20.007740 placed its seed 7.14 m above the actual stationary road seat 12.863944. The protocol rejected the measured shot; no original jump producer or enabled camera result is credited. A genuine 0.866666 s flight occurred only during cleanup after that rejection and is not accepted as the measured scene. The original case FAIL, raw log and scoped cleanup receipts are preserved. Next: place the reverse approach on the physically measured road, retain every original producer/camera/release gate, then re-run disabled/enabled/restored.

The first clean native attempt was closed by a helper-name mismatch. The succeeding case calls the pinned helper's actual name and omits false-valued SkipIntro/Audio switches, whose presence the pinned wrapper serializes as true. Failed attempts and build preflight newline corrections are retained. These test fixes change no game code.

This baseline does not certify enabled-jump behavior, full menus, online events, hardware input/audio or long-session stability. Canonical debug counts remain 167 verified, 28 original no-ops, 1,160 pending.
