# Original renderer base-initialization order correction

This corrects one sentence in the immutable integration analysis sealed by SHA256 `947022bd09d00ca392a4368ddebc8ae349a98061aed732fcf15f5ad450a2caad`. Its REPORT says that ARTIST's first operation calls ModuleSingleBuffered::Construct. The base call exists, but it is later in the original sequence:

| Primary instruction | Operation |
|---|---|
| 8240A7A0 | shared empty ICF target, not module base Construct |
| 8240A7A4..7C0 | load the actual GlobalGraphics wrapper address and store mpGraphicsAllocator |
| 8240A7C8 | EffectsArbitrator::Construct with that wrapper |
| 8240A7D0 /7D8 | both shader-constant frame Constructs |
| 8240A7DC..7FC | shader/frame index and writable-state stores |
| 8240A800 | actual ModuleSingleBuffered::Construct call |
| 8240A808..830 | original renderer-specific stage/display stores |

The earlier analysis's missing base initialization and missing typed graphics binding findings remain valid. The word **first** is withdrawn. Adding a base call at the native function entry and describing that as exact original order would be incorrect. Any future owner recovery must preserve this actual order or explicitly account for a reviewed PC platform ordering difference.

The full primary8240A778 export is copied here; it is byte-identical to the previous analysis's evidence. No sealed earlier file or production source is modified. No source proposal, activation, build, test or run is included.
