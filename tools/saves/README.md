# Xenia save converter

Convert an extracted Xbox 360 Burnout Paradise save into the decomp's
`Memcard/Profile.sav`. Requires Python 3.10 or newer, with no extra packages.
The source is read only and an existing output file is never overwritten.

From the workflow repository root:

```powershell
python tools/saves/convert_xenia_save.py "D:\Emulation\Emulators\Xenia\Xenia Burnout 5 v6" --check
python tools/saves/convert_xenia_save.py "D:\Emulation\Emulators\Xenia\Xenia Burnout 5 v6" --output "scratch/xenia_save_conversion/Memcard/Profile.sav"
```

`source` accepts the Xenia installation directory, the save directory, or its
extracted `Profile` file. The sibling `Mugshots` file is included when present.
Discovery prefers `content/45410806/00000001/Profile/Profile`; it also supports
the user-ID directory used by newer Xenia builds. Multiple user saves require
an explicit file path. Backup and `Profile_unlocked` directories are never
chosen automatically. Use `--json` for paths, hashes and preserved statistics.

To use the result, close the decomp, back up its existing
`build/game/Memcard/Profile.sav`, and copy the converted file into that location.
This is a decomp save, not a retail PC/Ultimate Box/Remastered save.

## Supported format

The supported payload is the 256 KiB ARTIST layout: progression version 28,
live revenge 6, options 12, DLC progression 6 and DLC options 1. These are
internal structure versions, not the version displayed by the game. The
provided Xenia installation's original-game save uses this layout. Other
layouts, older uninitialised DLC segments, raw STFS `CON` packages and retail
PC saves are rejected. This tool does not upgrade another layout into this one.

The converter validates MC02 lengths and both checksums, checks versions and
array bounds, converts numeric fields according to their actual widths, and
builds the decomp's version-1 B5SV container with its FNV-1a checksum. Names,
byte flags, padding and unused data remain byte-preserved. Dates need a full
64-bit swap because Xbox FILETIME stores the high half first. It checks an
exact inverse of all profile scalar conversions before writing.

Licence and valid mugshot pixels use linear DXT1 with Xenos 8IN16 byte order;
they are converted to PC BC1 and valid mugshot hashes are recalculated. A
mugshot whose stored checksum fails the decomp's hash check stays unreadable,
with its original pixels and checksum preserved, and its slot is reported.
This handles the blank, zero-checksum `MUGS` records present in the supplied
Xenia save. The console's hash implementation has a signed-byte indexing bug;
photos carrying a nonstandard hash from that bug are also retained as unreadable.
There is no fabricated photo or silent checksum repair. Missing mugshot files
are allowed only when no gallery records refer to them.

Game content must still match the save: the decomp checks event IDs against
its progression data. Conversion cannot create missing cars, DLC or events.

## Evidence

Offsets and record widths come from these files under `b5-decomp/src/`:

- `GameSource/Gui/BrnGuiProfile.h`: five segments and 256 KiB payload.
- `GameSource/GameState/Progression/BrnProfile_SaveImage.cpp`: base/DLC field offsets.
- `GameSource/GameState/Progression/BrnProgression{Car,Livery,Rival}Data.h`:
  mixed-width records; `BrnProfile.h` supplies events, galleries and sets.
- `GameSource/Gui/BrnGuiOptionsDataProfile.h`: routes, track bitsets and options.
- `GameSource/Network/Managers/BrnNetworkLiveRevenge{Manager,Relationship}.h`:
  saved relationships and identities.
- `GameSource/Network/BrnNetworkOutEventTypeDefs.h`: target-score identity.
- `GameShared/GameClasses/Gui/PC/CgsSaveLoadPC.cpp`: output header and FNV-1a.
- `SDKs/Realmc/RealmcXenonUtil.cpp`: 28-byte MC02 framing.

Additional ARTIST assembly checks:

- `Crc32 @0x82C44850`: first-word seed, non-reflected byte recurrence, final
  complement. All 256 table entries at `0x82FA7C88` matched polynomial
  `0x04C11DB7`. Both source files' header and payload checksums were verified.
- `DateAndTime::GetRawTimeValue @0x828D6F68`: high 32-bit word at +4, low at +8.
- `GameStateModule::ProcessGameEvents @0x823A0A18`, case 152, forwards the
  `NetworkOutTargetScoreEvent` identity into `Profile::SetTargetEventScore
  @0x823714F8`: name[16], XUID[8], event ID[8], score[4].
- `NetworkImageConverter::UnpackFromNetworkTexture @0x8288F498`: linear DXT1
  rows, no tiled allocation; `PIXELFORMAT_LIN_DXT1=0x1A200052` carries 8IN16.

## Tests

```powershell
python -m unittest discover -s tools/saves/tests -v
```

Tests cover independent console checksum vectors, mixed-width values, date
half ordering, strings/flags/padding, photos, malformed input, capacity
overflow, exact source selection and overwrite protection. No personal save
files are committed.

`tests/check_container.cpp` is an additional integration probe. Compile it with
the actual `CgsSaveLoadPC.cpp`, using MSVC and the `b5-decomp/src` include
directory. Run it with `BRN_HARNESS_SLOT` unset in a test working directory that
contains `Memcard/Profile.sav`. It exercises the real reader and writer, reports
key progression values and decodes the licence date through Windows. Compare
`Memcard/NativeRoundtrip.sav` byte-for-byte with the converted input.
