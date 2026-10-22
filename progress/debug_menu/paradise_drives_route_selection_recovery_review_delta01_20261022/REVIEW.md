# Paradise Drives route-selection source review

VERDICT: pass

Reviewed the one-path proposal against immutable B5 `5093cdb07f74fe0cfa6a6a32283fb6195be790ab` (tree `684d10b1b878200cdebf1b6fab29ce03646ea828`), the exact ARTIST exports, and the recorded DecFIGS declaration shape. The proposed preimage matches the 5093 source object; the current b6 checkout has the same object for this path.

The three hunks match the original source sequence. `ShowPresetEvents` now makes the first custom zoom request after resolving the current preset and before activating the cursor: ARTIST `0x8249339C..0x824933AC` calls `CalculateZoomFactor`, passes mode 3 and false, then calls `MainMapComponent::SetZoom`. The later map/icon activation order and second guarded zoom request also match `0x82493468..0x824934C0`: activate the map, latch the icon-manager flag when present, then choose custom zoom for a non-null cache and substate above loading, otherwise low/zero zoom. The enum values and `CalculateZoomFactor` float declaration agree with the source and DecFIGS type shape.

`Update` now stores the result of `MainMapComponent::Update` before clearing the input queue, matching ARTIST `0x824B0394..0x824B03A8`. The rest of the changed methods and the Select/Back/controller paths are unchanged in the proposal. The user freeze report remains separate from this source-parity finding; no cause or runtime repair is established.

Exact source preimage SHA-256: `b5d457ee290405c973dbe79cb0819eb9432016868fc09d601ae25df10f071ef0` (80894 bytes). Exact full postimage SHA-256: `9473822d565ec2e63f2f991b8089e7da0c4c5929c51eabaa1d0a34eaa1299e44` (81321 bytes). Patch SHA-256: `4c104cea26760398e539d0e4e43e95c3fa15f5c942a0b14039ea0878c1e8d464`.

Source/design review only. No runtime behavior credit is granted; no build, fixture, game, CI or IDA action was run.