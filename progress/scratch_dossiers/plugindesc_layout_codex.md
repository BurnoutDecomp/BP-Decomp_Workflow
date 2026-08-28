# `rw::audio::core::PlugInDescRunTime` console layout and RWAC factory records

This is a read-only decode of the X360 ARTIST image. All record words below were read from `IDA Files/BURNOUT_X360_ARTIST_Decrypted_Uncompressed.xex` with `file_offset = 0x3000 + (vaddr - 0x82000000)` and big-endian 32-bit decoding. Assembly, not pseudocode, is used for consumer evidence. The 22 standard record addresses come from their getter dossiers; the three custom addresses come directly from `GenericRwacFactory::GenericRwacFactory` at `0x826C1984..0x826C19B0`.

## 1. PlugInDescRunTime field table (offset, width, meaning, proving consumer)

The console record is **0x34 bytes (52 bytes)**. This agrees with the already-established PC/PDB annotation in `b5-decomp/vendor/renderware/include/rw/audio/core/PlugIn.h`; the last live byte is `+0x32`, written by `RegisterPlugInRunTime`, followed by the zero `+0x33` pad byte. The important host trap in `PlugInRegistry.cpp` remains exactly as documented: console `mpNext` is `+0x24`, but host `offsetof(PlugInDescRunTime, mpNext)` is not necessarily `0x24` after pointer widening/alignment.

| Console offset | Width | Recovered meaning | Proving consumer/evidence |
|---:|---:|---|---|
| `+0x00` | 4 | `char *name` | No direct X360 consumer was found. Strong rodata proof: every one of the 25 words points to the exact registered plug-in name string (for example Gain `0x821625E8 -> "Gain"`). Meaning is therefore rodata-proven, not consumer-read-proven. |
| `+0x04` | 4 | `GetSize(PlugInConfig *)` callback; returns the instance allocation size | `Voice::CreateInstance` loads descriptor `+0x04` and calls it at `0x82B6ECA0..0x82B6ECA8`, adds the return into total allocation at `0x82B6ECAC..0x82B6ECBC`, then calls it again at `0x82B6EDE0..0x82B6EDEC` and stores the low 16 bits as the stage instance size at `0x82B6EDF0..0x82B6EE08`. Callback target dossiers are named `GetSize`. |
| `+0x08` | 4 | `CreateInstance(PlugIn *, void *)` callback | `PlugIn::CreateInstance` loads descriptor `+0x08` at `0x82B6A868`, calls it at `0x82B6A86C..0x82B6A870`, and treats the byte result as success/failure at `0x82B6A874`. Target dossiers are named `CreateInstance`. |
| `+0x0C` | 4 | `PreProcess` callback, nullable | `Voice::CreateInstance` loads descriptor `+0x0C` at `0x82B6EE44` and stores it into stage slot `+0x00` at `0x82B6EE48`; all non-null targets with dossiers are named `PreProcess`. (This is X360-specific; the DecFIGS PS3 shape uses the corresponding platform slots for SPU metadata.) |
| `+0x10` | 4 | `Process` callback | `Voice::CreateInstance` loads descriptor `+0x10` at `0x82B6EE28` and stores it into stage slot `+0x04` at `0x82B6EE40`; target dossiers/xrefs are named `Process`. |
| `+0x14` | 4 | Current PC/PDB shape label: `ChannelMapPair *pChannelMaps` | **UNPROVEN on X360 by a direct consumer read.** No additional reader appeared when all 25 descriptor labels/addresses were grepped across the dossier tree. Values are exact XEX words. |
| `+0x18` | 4 | Current PC/PDB shape label: `ParameterDescRunTime *pParameterDescRunTime` | **UNPROVEN on X360 by a direct consumer read.** Values are exact XEX words. |
| `+0x1C` | 4 | Current PC/PDB shape label: `EventDescRunTime *pEventDescRunTime`, nullable | **UNPROVEN on X360 by a direct consumer read.** Values are exact XEX words. This is metadata, not itself a callback field. |
| `+0x20` | 4 | Current PC/PDB shape label: `PlugInDescToolSide *pPlugInDescToolSide` | **UNPROVEN on X360 by a direct consumer read.** It is zero in all 25 console records. |
| `+0x24` | 4 | Intrusive `mpNext` / list-node link | `RegisterPlugInRunTime` forms `desc+0x24` at `0x82B6A968`, stores the old head through it at `0x82B6A96C`, and makes that link-slot address the registry head at `0x82B6A990`. `GetPlugInHandle` converts a link back to its owner with `link-0x24` at `0x82B6A914`. |
| `+0x28` | 4 | `muId` / GUID fourcc | `GetPlugInHandle` reads `owner+0x28` at `0x82B6A91C` and compares it with the requested id at `0x82B6A920`; `RegisterPlugInRunTime` reads incoming `desc+0x28` at `0x82B6A948` and existing `owner+0x28` at `0x82B6A954` for duplicate detection. |
| `+0x2C` | 1 | `plugInType` / stage classification byte | `Voice::CreateInstance` reads it with `lbz 0x2C(r28)` at `0x82B6EDD0`, compares it with 3, and records that stage as the source stage when `<=3` at `0x82B6EDD4..0x82B6EDDC`. |
| `+0x2D` | 1 | Current PC/PDB shape label: `numConstructorParameters` | **UNPROVEN on X360 by a direct consumer read.** Exact byte values are reported below. |
| `+0x2E` | 1 | Current PC/PDB shape label: `numAttributes` | **UNPROVEN on X360 by a direct consumer read.** Exact byte values are reported below. |
| `+0x2F` | 1 | Current PC/PDB shape label: `numEvents` | **UNPROVEN on X360 by a direct consumer read.** Exact byte values are reported below. |
| `+0x30` | 1 | Current PC/PDB shape label: `isVariableInputChannels` | **UNPROVEN on X360 by a direct consumer read.** Exact byte values are reported below. |
| `+0x31` | 1 | Current PC/PDB shape label: `isVariableOutputChannels` | **UNPROVEN on X360 by a direct consumer read.** Exact byte values are reported below. |
| `+0x32` | 1 | `registryIndex` / registration sequence byte | `RegisterPlugInRunTime` loads the registry sequence byte at `0x82B6A988` and stores it to descriptor `+0x32` at `0x82B6A998`, then increments the registry byte at `0x82B6A99C..0x82B6A9A4`. |
| `+0x33` | 1 | Reserved/padding byte | **UNPROVEN/UNKNOWN.** No consumer was found; it is zero in all 25 dumped records and completes the established 52-byte record. |

The descriptor-address grep found only the 22 one-line getters plus `GenericRwacFactory` registration references; it did not expose another direct metadata reader. Accordingly, the metadata-only labels above are retained from the current PC/PDB shape but explicitly not promoted to X360 consumer proof.

## 2. Per-plugin record dump and interpretation

For compactness, each 13-word raw dump is ordered `+0x00, +0x04, ... +0x30`. `meta` always lists `+0x14 channel maps`, `+0x18 parameter descriptors`, `+0x1C event descriptors`, and `+0x20 tool-side descriptor` in that order. `tail` lists the eight bytes `type, ctorParams, attributes, events, variableInput, variableOutput, registryIndex, pad` at `+0x2C..+0x33`. Metadata labels/count semantics carry the UNPROVEN caveat from section 1; addresses, bytes, strings, callback targets, and fourcc values are direct XEX/dossier results.

### AiffWriter

Record address: `0x82F8C228` (getter `0x82B968B0`).

Raw words: `8215A988 82B96838 82B9D488 00000000 82BA2168 82F8C1F4 82F8C1F8 82F8C218 00000000 00000000 41695730 04000002 00000000`.

Interpretation: name `0x8215A988 -> "AiffWriter"`; callbacks `GetSize=0x82B96838 rw::audio::core::AiffWriter::GetSize`, `Create=0x82B9D488 rw::audio::core::AiffWriter::CreateInstance`, `PreProcess=null`, `Process=0x82BA2168 rw::audio::core::AiffWriter::Process`; meta `82F8C1F4, 82F8C1F8, 82F8C218, 00000000`; `mpNext=00000000`; `muId=0x41695730 -> "AiW0"`; tail `4,0,0,2,0,0,0,0`. No address-resolution blocker.

### BandPassIir2

Record address: `0x82F8C3D0` (getter `0x82B96A40`).

Raw words: `8215B844 82B96A38 82BA2398 00000000 82B9D778 82F8C38C 82F8C390 00000000 00000000 00000000 42493230 04000200 00000000`.

Interpretation: name `0x8215B844 -> "BandPassIir2"`; callbacks `GetSize=0x82B96A38 rw::audio::core::Delay::GetSize` (folded/shared target), `Create=0x82BA2398 rw::audio::core::BandPassIir2::CreateInstance`, `PreProcess=null`, `Process=0x82B9D778 rw::audio::core::BandPassIir2::Process`; meta `82F8C38C, 82F8C390, 00000000, 00000000`; `mpNext=00000000`; `muId=0x42493230 -> "BI20"`; tail `4,0,2,0,0,0,0,0`. No blocker.

### Dac

Record address: `0x82F8C7A8` (getter `0x82B96DB8`).

Raw words: `8215D080 82B96CB0 82BA24A0 00000000 82B97250 82F8C67C 82F8C680 82F8C780 00000000 00000000 44616330 04000305 00000000`.

Interpretation: name `0x8215D080 -> "Dac"`; callbacks `GetSize=0x82B96CB0 rw::audio::core::Dac::GetSize`, `Create=0x82BA24A0 rw::audio::core::Dac::CreateInstance`, `PreProcess=null`, `Process=0x82B97250 rw::audio::core::Dac::Process`; meta `82F8C67C, 82F8C680, 82F8C780, 00000000`; `mpNext=00000000`; `muId=0x44616330 -> "Dac0"`; tail `4,0,3,5,0,0,0,0`. No blocker.

### Gain

Record address: `0x82F8CB70` (getter `0x82B97350`).

Raw words: `821625E8 82B97348 82BA2BD0 00000000 82B97600 82F8CB4C 82F8CB50 00000000 00000000 00000000 47616930 04000100 00000000`.

Interpretation: name `0x821625E8 -> "Gain"`; callbacks `GetSize=0x82B97348 rw::audio::core::RawPuller2::GetSize` (folded/shared target), `Create=0x82BA2BD0 rw::audio::core::Gain::CreateInstance`, `PreProcess=null`, `Process=0x82B97600 rw::audio::core::Gain::Process`; meta `82F8CB4C, 82F8CB50, 00000000, 00000000`; `mpNext=00000000`; `muId=0x47616930 -> "Gai0"`; tail `4,0,1,0,0,0,0,0`. Calibration: all three non-null callbacks already have PC bodies.

### GainFader

Record address: `0x82F8CC50` (getter `0x82B97368`).

Raw words: `821625F0 82B97360 82BA2C08 00000000 82B97378 82F8CBA4 82F8CBA8 82F8CC48 00000000 00000000 47614630 04000101 00000000`.

Interpretation: name `0x821625F0 -> "GainFader"`; callbacks `GetSize=0x82B97360 rw::audio::core::GainFader::GetSize`, `Create=0x82BA2C08 rw::audio::core::GainFader::CreateInstance`, `PreProcess=null`, `Process=0x82B97378 rw::audio::core::GainFader::Process`; meta `82F8CBA4, 82F8CBA8, 82F8CC48, 00000000`; `mpNext=00000000`; `muId=0x47614630 -> "GaF0"`; tail `4,0,1,1,0,0,0,0`. No blocker.

### HighPassIir2

Record address: `0x82F8CFA8` (getter `0x82B978B0`).

Raw words: `82164A5C 82B97DA8 82BA2E40 00000000 82B9E0A0 82F8CF84 82F8CF88 00000000 00000000 00000000 48493230 04000100 00000000`.

Interpretation: name `0x82164A5C -> "HighPassIir2"`; callbacks `GetSize=0x82B97DA8 rw::audio::core::Limiter1::GetSize` (folded/shared target), `Create=0x82BA2E40 rw::audio::core::HighPassIir2::CreateInstance` (name comes from the xref in dossier `0x82BA1358`; exact-address dossier missing), `PreProcess=null`, `Process=0x82B9E0A0 rw::audio::core::HighPassIir2::Process`; meta `82F8CF84, 82F8CF88, 00000000, 00000000`; `mpNext=00000000`; `muId=0x48493230 -> "HI20"`; tail `4,0,1,0,0,0,0,0`. The record is recovered; only the exact callback dossier for `0x82BA2E40` is absent.

### HighPassButterworth

Record address: `0x82F8CE60` (getter `0x82B976D0`).

Raw words: `82163924 82B9DF88 82BA2CB0 00000000 82B976E0 82F8CDFC 82F8CE00 00000000 00000000 00000000 48504230 04000300 00000000`.

Interpretation: name `0x82163924 -> "HighPassButterworth"`; callbacks `GetSize=0x82B9DF88 rw::audio::core::HighPassButterworth::GetSize`, `Create=0x82BA2CB0 rw::audio::core::HighPassButterworth::CreateInstance`, `PreProcess=null`, `Process=0x82B976E0 rw::audio::core::HighPassButterworth::Process`; meta `82F8CDFC, 82F8CE00, 00000000, 00000000`; `mpNext=00000000`; `muId=0x48504230 -> "HPB0"`; tail `4,0,3,0,0,0,0,0`. No blocker.

### HighShelfIir2

Record address: `0x82F8D014` (getter `0x82B97978`).

Raw words: `82164F24 82B96A38 82BA2EA8 00000000 82B9E1F8 82F8D010 82F8D048 00000000 00000000 00000000 48533230 04000200 00000000`.

Interpretation: name `0x82164F24 -> "HighShelfIir2"`; callbacks `GetSize=0x82B96A38 rw::audio::core::Delay::GetSize` (folded/shared), `Create=0x82BA2EA8 rw::audio::core::HighShelfIir2::CreateInstance`, `PreProcess=null`, `Process=0x82B9E1F8 rw::audio::core::HighShelfIir2::Process`; meta `82F8D010, 82F8D048, 00000000, 00000000`; `mpNext=00000000`; `muId=0x48533230 -> "HS20"`; tail `4,0,2,0,0,0,0,0`. No blocker.

### Limiter1

Record address: `0x82F8D150` (getter `0x82B97AA0`).

Raw words: `82165614 82B97DA8 82BA2F28 00000000 82B9E3A0 82F8D0EC 82F8D0F0 00000000 00000000 00000000 4C693130 04000300 00000000`.

Interpretation: name `0x82165614 -> "Limiter1"`; callbacks `GetSize=0x82B97DA8 rw::audio::core::Limiter1::GetSize`, `Create=0x82BA2F28 rw::audio::core::Limiter1::CreateInstance`, `PreProcess=null`, `Process=0x82B9E3A0 rw::audio::core::Limiter1::Process` (named by xrefs in dossiers `0x82B64DB0`, `0x82B671F0`, and `0x82B97AB0`; exact-address dossier missing); meta `82F8D0EC, 82F8D0F0, 00000000, 00000000`; `mpNext=00000000`; `muId=0x4C693130 -> "Li10"`; tail `4,0,3,0,0,0,0,0`. Record recovered; exact Process dossier absent.

### LowPassIir2

Record address: `0x82F8D3D4` (getter `0x82B97DB0`).

Raw words: `82167558 82B97DA8 82BA3130 00000000 82B9E5C8 82F8D3D0 82F8D408 00000000 00000000 00000000 4C493230 04000100 00000000`.

Interpretation: name `0x82167558 -> "LowPassIir2"`; callbacks `GetSize=0x82B97DA8 rw::audio::core::Limiter1::GetSize` (folded/shared), `Create=0x82BA3130 rw::audio::core::LowPassIir2::CreateInstance`, `PreProcess=null`, `Process=0x82B9E5C8 rw::audio::core::LowPassIir2::Process`; meta `82F8D3D0, 82F8D408, 00000000, 00000000`; `mpNext=00000000`; `muId=0x4C493230 -> "LI20"`; tail `4,0,1,0,0,0,0,0`. No blocker.

### LowPassButterworth

Record address: `0x82F8D24C` (getter `0x82B97BF0`).

Raw words: `82165FDC 82B9E4B0 82BA2FA0 00000000 82B97C00 82F8D248 82F8D280 00000000 00000000 00000000 4C504230 04000300 00000000`.

Interpretation: name `0x82165FDC -> "LowPassButterworth"`; callbacks `GetSize=0x82B9E4B0 rw::audio::core::LowPassButterworth::GetSize`, `Create=0x82BA2FA0 rw::audio::core::LowPassButterworth::CreateInstance`, `PreProcess=null`, `Process=0x82B97C00 rw::audio::core::LowPassButterworth::Process`; meta `82F8D248, 82F8D280, 00000000, 00000000`; `mpNext=00000000`; `muId=0x4C504230 -> "LPB0"`; tail `4,0,3,0,0,0,0,0`. No blocker.

### LowShelfIir2

Record address: `0x82F8D4A0` (getter `0x82B97E70`).

Raw words: `82167A00 82B96A38 82BA3198 00000000 82B9E720 82F8D45C 82F8D460 00000000 00000000 00000000 4C533230 04000200 00000000`.

Interpretation: name `0x82167A00 -> "LowShelfIir2"`; callbacks `GetSize=0x82B96A38 rw::audio::core::Delay::GetSize` (folded/shared), `Create=0x82BA3198 rw::audio::core::LowShelfIir2::CreateInstance`, `PreProcess=null`, `Process=0x82B9E720 rw::audio::core::LowShelfIir2::Process`; meta `82F8D45C, 82F8D460, 00000000, 00000000`; `mpNext=00000000`; `muId=0x4C533230 -> "LS20"`; tail `4,0,2,0,0,0,0,0`. No blocker.

### Pan2D

Record address: `0x82F8EFB8` (getter `0x82B984E8`).

Raw words: `8216AB9C 82B982C0 82BA34A0 00000000 82B99ED8 82F8EED0 82F8EED8 00000000 00000000 00000000 506E3230 04020500 00000000`.

Interpretation: name `0x8216AB9C -> "Pan2D"`; callbacks `GetSize=0x82B982C0 rw::audio::core::Pan2D::GetSize`, `Create=0x82BA34A0 rw::audio::core::Pan2D::CreateInstance`, `PreProcess=null`, `Process=0x82B99ED8 rw::audio::core::Pan2D::Process`; meta `82F8EED0, 82F8EED8, 00000000, 00000000`; `mpNext=00000000`; `muId=0x506E3230 -> "Pn20"`; tail `4,2,5,0,0,0,0,0`. No blocker.

### Pan2D1

Record address: `0x82F8F140` (getter `0x82B98748`).

Raw words: `8216ABA4 82B982C8 82BA3540 00000000 82B997C8 82F8EFF8 82F8F000 00000000 00000000 00000000 506E3231 04030700 00000000`.

Interpretation: name `0x8216ABA4 -> "Pan2D1"`; callbacks `GetSize=0x82B982C8 rw::audio::core::Pan2D1::GetSize`, `Create=0x82BA3540 rw::audio::core::Pan2D1::CreateInstance` (named by xref in dossier `0x82B98758`; exact-address dossier missing), `PreProcess=null`, `Process=0x82B997C8 rw::audio::core::Pan2D1::Process`; meta `82F8EFF8, 82F8F000, 00000000, 00000000`; `mpNext=00000000`; `muId=0x506E3231 -> "Pn21"`; tail `4,3,7,0,0,0,0,0`. Record recovered; exact Create dossier absent.

### Pause

Record address: `0x82F8F510` (getter `0x82B9A130`).

Raw words: `8216CC3C 82B982D0 82BA36B8 82B9A140 82B9A218 82F8F4EC 82F8F4F0 00000000 00000000 00000000 50617530 03000100 00000000`.

Interpretation: name `0x8216CC3C -> "Pause"`; callbacks `GetSize=0x82B982D0 rw::audio::core::Pause::GetSize`, `Create=0x82BA36B8 rw::audio::core::Pause::CreateInstance`, `PreProcess=0x82B9A140 rw::audio::core::Pause::PreProcess`, `Process=0x82B9A218 rw::audio::core::Pause::Process` (named by xref in dossier `0x82926FD0`; exact-address dossier missing); meta `82F8F4EC, 82F8F4F0, 00000000, 00000000`; `mpNext=00000000`; `muId=0x50617530 -> "Pau0"`; tail `3,0,1,0,0,0,0,0`. Record recovered; exact Process dossier absent.

### PeakingIir2

Record address: `0x82F8F5AC` (getter `0x82B9A460`).

Raw words: `8216CF20 82B982D8 82BA3708 00000000 82B9F168 82F8F5A8 82F8F5E0 00000000 00000000 00000000 50493230 04000300 00000000`.

Interpretation: name `0x8216CF20 -> "PeakingIir2"`; callbacks `GetSize=0x82B982D8 rw::audio::core::PeakingIir2::GetSize`, `Create=0x82BA3708 rw::audio::core::PeakingIir2::CreateInstance`, `PreProcess=null`, `Process=0x82B9F168 rw::audio::core::PeakingIir2::Process`; meta `82F8F5A8, 82F8F5E0, 00000000, 00000000`; `mpNext=00000000`; `muId=0x50493230 -> "PI20"`; tail `4,0,3,0,0,0,0,0`. No blocker.

### Rechannel

Record address: `0x82F8F884` (getter `0x82B9A718`).

Raw words: `8216E11C 82B982E0 82BA37D0 82B97F98 82B9A728 82F8F880 00000000 00000000 00000000 00000000 52636830 01000000 01000000`.

Interpretation: name `0x8216E11C -> "Rechannel"`; callbacks `GetSize=0x82B982E0 rw::audio::core::Rechannel::GetSize`, `Create=0x82BA37D0 rw::audio::core::Rechannel::CreateInstance`, `PreProcess=0x82B97F98 rw::audio::core::Rechannel::PreProcess`, `Process=0x82B9A728 rw::audio::core::Rechannel::Process`; meta `82F8F880, 00000000, 00000000, 00000000`; `mpNext=00000000`; `muId=0x52636830 -> "Rch0"`; tail `1,0,0,0,1,0,0,0`. No blocker.

### Resample

Record address: `0x82F8F8E0` (getter `0x82B9A850`).

Raw words: `8216E558 82B9F3D8 82BA37F0 82B9AC10 82B9F3E8 82F8F8BC 82F8F8C0 00000000 00000000 00000000 52737030 02000100 00000000`.

Interpretation: name `0x8216E558 -> "Resample"`; callbacks `GetSize=0x82B9F3D8 rw::audio::core::Resample::GetSize`, `Create=0x82BA37F0 rw::audio::core::Resample::CreateInstance`, `PreProcess=0x82B9AC10 rw::audio::core::Resample::PreProcess`, `Process=0x82B9F3E8 rw::audio::core::Resample::Process` (named by xrefs in dossiers `0x82926BA0`, `0x82B9A8D0`, `0x82C0AAB8`; exact-address dossier missing); meta `82F8F8BC, 82F8F8C0, 00000000, 00000000`; `mpNext=00000000`; `muId=0x52737030 -> "Rsp0"`; tail `2,0,1,0,0,0,0,0`. Record recovered; exact Process dossier absent.

### ReverbModel1

Record address: `0x82F8FA14` (getter `0x82B9AD98`).

Raw words: `82170618 82B9ADA8 82BA67F8 00000000 82B9F7D0 82F8FA10 82F8FA48 00000000 00000000 00000000 524D3130 04000300 00000000`.

Interpretation: name `0x82170618 -> "ReverbModel1"`; callbacks `GetSize=0x82B9ADA8 rw::audio::core::ReverbModel1::GetSize`, `Create=0x82BA67F8 rw::audio::core::ReverbModel1::CreateInstance`, `PreProcess=null`, `Process=0x82B9F7D0 rw::audio::core::ReverbModel1::Process`; meta `82F8FA10, 82F8FA48, 00000000, 00000000`; `mpNext=00000000`; `muId=0x524D3130 -> "RM10"`; tail `4,0,3,0,0,0,0,0`. No blocker.

### Send

Record address: `0x82F8FF60` (getter `0x82B9B798`).

Raw words: `82173600 82B98300 82BA3E98 00000000 82B9B7A8 82F8FEEC 82F8FEF0 82F8FF50 00000000 00000000 53656E30 04000102 00000000`.

Interpretation: name `0x82173600 -> "Send"`; callbacks `GetSize=0x82B98300 rw::audio::core::Send::GetSize`, `Create=0x82BA3E98 rw::audio::core::Send::CreateInstance`, `PreProcess=null`, `Process=0x82B9B7A8 rw::audio::core::Send::Process`; meta `82F8FEEC, 82F8FEF0, 82F8FF50, 00000000`; `mpNext=00000000`; `muId=0x53656E30 -> "Sen0"`; tail `4,0,1,2,0,0,0,0`. No blocker.

### SndPlayer1

Record address: `0x82F901C4` (getter `0x82B9BE60`).

Raw words: `821744E4 82BA0220 82BA6C80 82B9C2D8 82BA0568 82F90190 82F910E0 82F90194 00000000 00000000 536E5031 00010306 00010000`.

Interpretation: name `0x821744E4 -> "SndPlayer1"`; callbacks `GetSize=0x82BA0220 rw::audio::core::SndPlayer1::GetSize`, `Create=0x82BA6C80 rw::audio::core::SndPlayer1::CreateInstance`, `PreProcess=0x82B9C2D8 UNPROVEN/UNKNOWN exact function name` (no exact dossier and no named xref found), `Process=0x82BA0568 rw::audio::core::SndPlayer1::Process`; meta `82F90190, 82F910E0, 82F90194, 00000000`; `mpNext=00000000`; `muId=0x536E5031 -> "SnP1"`; tail `0,1,3,6,0,1,0,0`. Record recovered; callback address `0x82B9C2D8` is the sole unresolved callback identity.

### SubMix

Record address: `0x82F902E0` (getter `0x82B9C370`).

Raw words: `8217B090 82B982F0 82BA4680 00000000 82B9C480 82F902BC 82F902C0 00000000 00000000 00000000 53756230 04010000 00000000`.

Interpretation: name `0x8217B090 -> "SubMix"`; callbacks `GetSize=0x82B982F0 rw::audio::core::SubMix::GetSize`, `Create=0x82BA4680 rw::audio::core::SubMix::CreateInstance` (named by xrefs in dossiers `0x82926FD0` and `0x82C08EEC`; exact-address dossier missing), `PreProcess=null`, `Process=0x82B9C480 rw::audio::core::SubMix::Process`; meta `82F902BC, 82F902C0, 00000000, 00000000`; `mpNext=00000000`; `muId=0x53756230 -> "Sub0"`; tail `4,1,0,0,0,0,0,0`. Record recovered; exact Create dossier absent.

### GinsuPlayer

Record address: `0x82F2D094` (direct factory reference at `0x826C1984..0x826C1990`).

Raw words: `820A91F0 826A40B8 826C3418 8268C1D8 8268C1E8 82F2D02C 82F2E158 82FFB9F8 00000000 00000000 476E7330 00010502 00000000`.

Interpretation: name `0x820A91F0 -> "GinsuPlayer"`; callbacks `GetSize=0x826A40B8 rw::audio::core::GinsuPlayer::GetSize`, `Create=0x826C3418 rw::audio::core::GinsuPlayer::CreateInstance`, `PreProcess=0x8268C1D8 rw::audio::core::GinsuPlayer::PreProcess`, `Process=0x8268C1E8 rw::audio::core::GinsuPlayer::Process`; meta `82F2D02C, 82F2E158, 82FFB9F8, 00000000`; `mpNext=00000000`; `muId=0x476E7330 -> "Gns0"`; tail `0,1,5,2,0,0,0,0`. No blocker.

### SndPlayer1_CgsStreamMod

Record address: `0x82F2E124` (direct factory reference at `0x826C1994..0x826C19A0`).

Raw words: `820A91D8 826A4210 826EA508 8268CD10 826A46B0 82F2D91C 82F2FAB0 82F2E638 00000000 00000000 4A537472 00010305 00010000`.

Interpretation: name `0x820A91D8 -> "SndPlayer1_CgsStreamMod"`; callbacks `GetSize=0x826A4210 rw::audio::core::SndPlayer1_CgsStreamMod::GetSize`, `Create=0x826EA508 rw::audio::core::SndPlayer1_CgsStreamMod::CreateInstance`, `PreProcess=0x8268CD10 rw::audio::core::SndPlayer1_CgsStreamMod::PreProcess`, `Process=0x826A46B0 rw::audio::core::SndPlayer1_CgsStreamMod::Process`; meta `82F2D91C, 82F2FAB0, 82F2E638, 00000000`; `mpNext=00000000`; `muId=0x4A537472 -> "JStr"`; tail `0,1,3,5,0,1,0,0`. No blocker.

### GainArray

Record address: `0x82F2E664` (direct factory reference at `0x826C19A4..0x826C19B0`).

Raw words: `820A91CC 82689E08 826C3A10 00000000 8268CDB0 82F2E660 82F2E698 00000000 00000000 00000000 4A474130 04000600 00000000`.

Interpretation: name `0x820A91CC -> "GainArray"`; callbacks `GetSize=0x82689E08 CgsSound::Playback::Plugins::GainArray::GetSize`, `Create=0x826C3A10 CgsSound::Playback::Plugins::GainArray::CreateInstance`, `PreProcess=null`, `Process=0x8268CDB0 CgsSound::Playback::Plugins::GainArray::Process`; meta `82F2E660, 82F2E698, 00000000, 00000000`; `mpNext=00000000`; `muId=0x4A474130 -> "JGA0"`; tail `4,0,6,0,0,0,0,0`. No blocker.

## 3. Callback readiness matrix

“PC body exists” is scoped exactly to `b5-decomp/vendor/renderware/src/rw/audio/core/`, as requested. A source comment merely mentioning a still-todo SubMix function was not counted as a body. The folded `GetSize` targets retain the exact dossier symbol and are counted ready when that exact PC body exists.

| Console address | Dossier function name | Plugin(s) using it | PC body exists |
|---|---|---|---|
| `0x82689E08` | `CgsSound::Playback::Plugins::GainArray::GetSize` | GainArray | no |
| `0x8268C1D8` | `rw::audio::core::GinsuPlayer::PreProcess` | GinsuPlayer | no |
| `0x8268C1E8` | `rw::audio::core::GinsuPlayer::Process` | GinsuPlayer | no |
| `0x8268CD10` | `rw::audio::core::SndPlayer1_CgsStreamMod::PreProcess` | SndPlayer1_CgsStreamMod | no |
| `0x8268CDB0` | `CgsSound::Playback::Plugins::GainArray::Process` | GainArray | no |
| `0x826A40B8` | `rw::audio::core::GinsuPlayer::GetSize` | GinsuPlayer | no |
| `0x826A4210` | `rw::audio::core::SndPlayer1_CgsStreamMod::GetSize` | SndPlayer1_CgsStreamMod | no |
| `0x826A46B0` | `rw::audio::core::SndPlayer1_CgsStreamMod::Process` | SndPlayer1_CgsStreamMod | no |
| `0x826C3418` | `rw::audio::core::GinsuPlayer::CreateInstance` | GinsuPlayer | no |
| `0x826C3A10` | `CgsSound::Playback::Plugins::GainArray::CreateInstance` | GainArray | no |
| `0x826EA508` | `rw::audio::core::SndPlayer1_CgsStreamMod::CreateInstance` | SndPlayer1_CgsStreamMod | no |
| `0x82B96838` | `rw::audio::core::AiffWriter::GetSize` | AiffWriter | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/AiffWriter.cpp` |
| `0x82B96A38` | `rw::audio::core::Delay::GetSize` | BandPassIir2, HighShelfIir2, LowShelfIir2 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/plugins/Delay.cpp` |
| `0x82B96CB0` | `rw::audio::core::Dac::GetSize` | Dac | no |
| `0x82B97250` | `rw::audio::core::Dac::Process` | Dac | no |
| `0x82B97348` | `rw::audio::core::RawPuller2::GetSize` | Gain | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/RawPuller2.cpp` |
| `0x82B97360` | `rw::audio::core::GainFader::GetSize` | GainFader | no |
| `0x82B97378` | `rw::audio::core::GainFader::Process` | GainFader | no |
| `0x82B97600` | `rw::audio::core::Gain::Process` | Gain | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/Gain.cpp` |
| `0x82B976E0` | `rw::audio::core::HighPassButterworth::Process` | HighPassButterworth | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/plugins/HighPassButterworth.cpp` |
| `0x82B97C00` | `rw::audio::core::LowPassButterworth::Process` | LowPassButterworth | no |
| `0x82B97DA8` | `rw::audio::core::Limiter1::GetSize` | HighPassIir2, Limiter1, LowPassIir2 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/plugins/Limiter1.cpp` |
| `0x82B97F98` | `rw::audio::core::Rechannel::PreProcess` | Rechannel | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/Rechannel.cpp` |
| `0x82B982C0` | `rw::audio::core::Pan2D::GetSize` | Pan2D | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/plugins/Pan2D.cpp` |
| `0x82B982C8` | `rw::audio::core::Pan2D1::GetSize` | Pan2D1 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/plugins/Pan2D1.cpp` |
| `0x82B982D0` | `rw::audio::core::Pause::GetSize` | Pause | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/plugins/Pause.cpp` |
| `0x82B982D8` | `rw::audio::core::PeakingIir2::GetSize` | PeakingIir2 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/PeakingIir2.cpp` |
| `0x82B982E0` | `rw::audio::core::Rechannel::GetSize` | Rechannel | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/Rechannel.cpp` |
| `0x82B982F0` | `rw::audio::core::SubMix::GetSize` | SubMix | no |
| `0x82B98300` | `rw::audio::core::Send::GetSize` | Send | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/Send.cpp` |
| `0x82B997C8` | `rw::audio::core::Pan2D1::Process` | Pan2D1 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/plugins/Pan2D1.cpp` |
| `0x82B99ED8` | `rw::audio::core::Pan2D::Process` | Pan2D | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/plugins/Pan2D.cpp` |
| `0x82B9A140` | `rw::audio::core::Pause::PreProcess` | Pause | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/plugins/Pause.cpp` |
| `0x82B9A218` | `rw::audio::core::Pause::Process` (named xref in `0x82926FD0`; exact dossier absent) | Pause | no |
| `0x82B9A728` | `rw::audio::core::Rechannel::Process` | Rechannel | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/Rechannel.cpp` |
| `0x82B9AC10` | `rw::audio::core::Resample::PreProcess` | Resample | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/Resample.cpp` |
| `0x82B9ADA8` | `rw::audio::core::ReverbModel1::GetSize` | ReverbModel1 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/plugins/ReverbModel1.cpp` |
| `0x82B9B7A8` | `rw::audio::core::Send::Process` | Send | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/Send.cpp` |
| `0x82B9C2D8` | **UNPROVEN/UNKNOWN** (no exact dossier or named xref; descriptor slot is `PreProcess`) | SndPlayer1 | no |
| `0x82B9C480` | `rw::audio::core::SubMix::Process` | SubMix | no |
| `0x82B9D488` | `rw::audio::core::AiffWriter::CreateInstance` | AiffWriter | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/AiffWriter.cpp` |
| `0x82B9D778` | `rw::audio::core::BandPassIir2::Process` | BandPassIir2 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/BandPassIir2.cpp` |
| `0x82B9DF88` | `rw::audio::core::HighPassButterworth::GetSize` | HighPassButterworth | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/plugins/HighPassButterworth.cpp` |
| `0x82B9E0A0` | `rw::audio::core::HighPassIir2::Process` | HighPassIir2 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/HighPassIir2.cpp` |
| `0x82B9E1F8` | `rw::audio::core::HighShelfIir2::Process` | HighShelfIir2 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/HighShelfIir2.cpp` |
| `0x82B9E3A0` | `rw::audio::core::Limiter1::Process` (named xrefs; exact dossier absent) | Limiter1 | no |
| `0x82B9E4B0` | `rw::audio::core::LowPassButterworth::GetSize` | LowPassButterworth | no |
| `0x82B9E5C8` | `rw::audio::core::LowPassIir2::Process` | LowPassIir2 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/LowPassIir2.cpp` |
| `0x82B9E720` | `rw::audio::core::LowShelfIir2::Process` | LowShelfIir2 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/LowShelfIir2.cpp` |
| `0x82B9F168` | `rw::audio::core::PeakingIir2::Process` | PeakingIir2 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/PeakingIir2.cpp` |
| `0x82B9F3D8` | `rw::audio::core::Resample::GetSize` | Resample | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/Resample.cpp` |
| `0x82B9F3E8` | `rw::audio::core::Resample::Process` (named xrefs; exact dossier absent) | Resample | no |
| `0x82B9F7D0` | `rw::audio::core::ReverbModel1::Process` | ReverbModel1 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/plugins/ReverbModel1.cpp` |
| `0x82BA0220` | `rw::audio::core::SndPlayer1::GetSize` | SndPlayer1 | no |
| `0x82BA0568` | `rw::audio::core::SndPlayer1::Process` | SndPlayer1 | no |
| `0x82BA2168` | `rw::audio::core::AiffWriter::Process` | AiffWriter | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/AiffWriter.cpp` |
| `0x82BA2398` | `rw::audio::core::BandPassIir2::CreateInstance` | BandPassIir2 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/BandPassIir2.cpp` |
| `0x82BA24A0` | `rw::audio::core::Dac::CreateInstance` | Dac | no |
| `0x82BA2BD0` | `rw::audio::core::Gain::CreateInstance` | Gain | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/Gain.cpp` |
| `0x82BA2C08` | `rw::audio::core::GainFader::CreateInstance` | GainFader | no |
| `0x82BA2CB0` | `rw::audio::core::HighPassButterworth::CreateInstance` | HighPassButterworth | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/plugins/HighPassButterworth.cpp` |
| `0x82BA2E40` | `rw::audio::core::HighPassIir2::CreateInstance` (named xref; exact dossier absent) | HighPassIir2 | no |
| `0x82BA2EA8` | `rw::audio::core::HighShelfIir2::CreateInstance` | HighShelfIir2 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/HighShelfIir2.cpp` |
| `0x82BA2F28` | `rw::audio::core::Limiter1::CreateInstance` | Limiter1 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/plugins/Limiter1.cpp` |
| `0x82BA2FA0` | `rw::audio::core::LowPassButterworth::CreateInstance` | LowPassButterworth | no |
| `0x82BA3130` | `rw::audio::core::LowPassIir2::CreateInstance` | LowPassIir2 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/LowPassIir2.cpp` |
| `0x82BA3198` | `rw::audio::core::LowShelfIir2::CreateInstance` | LowShelfIir2 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/LowShelfIir2.cpp` |
| `0x82BA34A0` | `rw::audio::core::Pan2D::CreateInstance` | Pan2D | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/plugins/Pan2D.cpp` |
| `0x82BA3540` | `rw::audio::core::Pan2D1::CreateInstance` (named xref; exact dossier absent) | Pan2D1 | no |
| `0x82BA36B8` | `rw::audio::core::Pause::CreateInstance` | Pause | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/plugins/Pause.cpp` |
| `0x82BA3708` | `rw::audio::core::PeakingIir2::CreateInstance` | PeakingIir2 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/PeakingIir2.cpp` |
| `0x82BA37D0` | `rw::audio::core::Rechannel::CreateInstance` | Rechannel | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/Rechannel.cpp` |
| `0x82BA37F0` | `rw::audio::core::Resample::CreateInstance` | Resample | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/Resample.cpp` |
| `0x82BA3E98` | `rw::audio::core::Send::CreateInstance` | Send | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/Send.cpp` |
| `0x82BA4680` | `rw::audio::core::SubMix::CreateInstance` (named xrefs; exact dossier absent) | SubMix | no |
| `0x82BA67F8` | `rw::audio::core::ReverbModel1::CreateInstance` | ReverbModel1 | yes — `b5-decomp/vendor/renderware/src/rw/audio/core/plugins/ReverbModel1.cpp` |
| `0x82BA6C80` | `rw::audio::core::SndPlayer1::CreateInstance` | SndPlayer1 | no |

## 4. Summary

The recovered console layout is `name, GetSize, CreateInstance, PreProcess, Process, channel-map metadata, parameter metadata, event metadata, tool-side metadata, mpNext, muId`, followed by eight one-byte fields `plugInType, ctor-count, attribute-count, event-count, variable-input, variable-output, registryIndex, pad`. Consumer assembly directly proves the four callback slots, list link, id, type classification, and registry index; name is proven by all 25 XEX string targets. The remaining metadata/count/flag names are the current PC/PDB shape and remain explicitly UNPROVEN by an X360 consumer read.

All 25 requested records were recovered. Four callback addresses lack exact-address dossiers but have names in other dossiers' xrefs (`Pause::Process`, `Limiter1::Process`, `Resample::Process`, and three Create callbacks as detailed above); `0x82B9C2D8` is the only callback whose exact function name remains UNKNOWN. Readiness counts include every non-null descriptor callback at `+0x04/+0x08/+0x0C/+0x10`.

| Plugin | Record | Fourcc | Record recovered | PC callbacks existing / total |
|---|---:|---|---|---:|
| AiffWriter | `0x82F8C228` | `AiW0` | yes | 3 / 3 |
| BandPassIir2 | `0x82F8C3D0` | `BI20` | yes | 3 / 3 |
| Dac | `0x82F8C7A8` | `Dac0` | yes | 0 / 3 |
| Gain | `0x82F8CB70` | `Gai0` | yes | 3 / 3 |
| GainFader | `0x82F8CC50` | `GaF0` | yes | 0 / 3 |
| HighPassIir2 | `0x82F8CFA8` | `HI20` | yes | 2 / 3 |
| HighPassButterworth | `0x82F8CE60` | `HPB0` | yes | 3 / 3 |
| HighShelfIir2 | `0x82F8D014` | `HS20` | yes | 3 / 3 |
| Limiter1 | `0x82F8D150` | `Li10` | yes | 2 / 3 |
| LowPassIir2 | `0x82F8D3D4` | `LI20` | yes | 3 / 3 |
| LowPassButterworth | `0x82F8D24C` | `LPB0` | yes | 0 / 3 |
| LowShelfIir2 | `0x82F8D4A0` | `LS20` | yes | 3 / 3 |
| Pan2D | `0x82F8EFB8` | `Pn20` | yes | 3 / 3 |
| Pan2D1 | `0x82F8F140` | `Pn21` | yes | 2 / 3 |
| Pause | `0x82F8F510` | `Pau0` | yes | 3 / 4 |
| PeakingIir2 | `0x82F8F5AC` | `PI20` | yes | 3 / 3 |
| Rechannel | `0x82F8F884` | `Rch0` | yes | 4 / 4 |
| Resample | `0x82F8F8E0` | `Rsp0` | yes | 3 / 4 |
| ReverbModel1 | `0x82F8FA14` | `RM10` | yes | 3 / 3 |
| Send | `0x82F8FF60` | `Sen0` | yes | 3 / 3 |
| SndPlayer1 | `0x82F901C4` | `SnP1` | yes | 0 / 4 |
| SubMix | `0x82F902E0` | `Sub0` | yes | 0 / 3 |
| GinsuPlayer | `0x82F2D094` | `Gns0` | yes | 0 / 4 |
| SndPlayer1_CgsStreamMod | `0x82F2E124` | `JStr` | yes | 0 / 4 |
| GainArray | `0x82F2E664` | `JGA0` | yes | 0 / 3 |
