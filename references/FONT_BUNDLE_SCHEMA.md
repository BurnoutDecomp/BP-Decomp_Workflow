# Font bundle on-disk schema (our x64 PC format, platform 4)

This is the exact layout the reconstructed loader (`CgsResource::BundleLoader::LoadBundle` →
`CgsResource::Pool` → `RwRasterResourceType`/`FontResourceType` fix-up) consumes to produce a usable
`CgsResource::Font`, which `CgsDev::LoadAndSetDebugFont` then hands to the debug renderers. Produce a
file called `Default.font` matching this and drop it in the game's working directory; the boot chain
loads it automatically (absent/invalid → the built-in vector font is used instead).

## Ground rules

- **Container:** Bundle 2, version 2 (`bnd2`), **platform = 4** (our marker — see below).
- **Endianness:** little-endian. **Word size:** 64-bit. Resource payloads are *verbatim x64 struct
  images* — the loader `memcpy`s them into place and then rebases pointer fields in situ.
- **Pointers on disk are byte OFFSETS** from the start of that resource's main-memory block. Fix-up
  adds the runtime base to each (`offset → absolute`). Store the offset; the loader does the rest.
- **Uncompressed.** Set the compressed flag off (or pre-decompress). The loader assumes the on-disk
  bytes are the final uncompressed bytes; 360-style decompress + endian-swap is *not* applied.
- All offsets/sizes below were dumped with `offsetof`/`sizeof` from the actual headers
  (`tools/assets/fonts/dump_offsets.cpp`), so they are authoritative for this build's x64 layout.

### Why platform 4

Stock Burnout bundles tag `muPlatform` 1=PC(x86), 2=X360, 3=PS3 — all with layouts whose pointer
widths/endianness don't match our x64 structs. **4** marks "resource payloads are this build's native
little-endian x64 images." `BundleLoader::LoadBundle` *requires* version 2 **and** platform 4, so it
refuses stock bundles it can't safely fix up. (`CgsResource::BundleV2::KU_PLATFORM = 4`.)

---

## 1. Bundle container

### 1.1 Header — 40 bytes (`BundleV2`)

| off  | type      | field                      | value for our font bundle |
|------|-----------|----------------------------|---------------------------|
| 0x00 | char[4]   | `macMagicNumber`           | `"bnd2"`                  |
| 0x04 | u32       | `muVersion`                | `2`                       |
| 0x08 | u32       | `muPlatform`               | `4`                       |
| 0x0C | u32       | `muDebugDataOffset`        | `0x30` (no debug data)    |
| 0x10 | u32       | `muResourceEntriesCount`   | `1 + N` (font + N pages)  |
| 0x14 | u32       | `muResourceEntriesOffset`  | file offset of the entry array |
| 0x18 | u32[3]    | `mauResourceDataOffset[3]` | file offset of each mem-pool's data region (0=main, 1=graphics-system, 2=graphics-local) |
| 0x24 | u32       | `muFlags`                  | `0` (uncompressed)        |

### 1.2 Resource entry — 64 bytes each (`BundleV2::ResourceEntry`), at `muResourceEntriesOffset`

One per resource, **sorted ascending by `mResourceId`**.

| off  | type   | field                              | notes |
|------|--------|------------------------------------|-------|
| 0x00 | u64    | `mResourceId`                      | unique 64-bit id (low 32 bits non-zero; high 32 bits 0) |
| 0x08 | u64    | `muImportHash`                     | OR of all imported ids (informational; 0 if no imports) |
| 0x10 | u32[3] | `mauUncompressedSizeAndAlignment`  | per mem-pool: `(log2(align) << 28) \| (size & 0x0FFFFFFF)` |
| 0x1C | u32[3] | `mauSizeAndAlignmentOnDisk`        | uncompressed ⇒ equal to the above |
| 0x28 | u32[3] | `mauDiskOffset[3]`                 | per mem-pool: byte offset of this resource's bytes *within* that region |
| 0x34 | u32    | `muImportOffset`                   | byte offset of the import table within this resource's MAIN block (0 if none) |
| 0x38 | u32    | `muResourceTypeId`                 | `0x21` Font / `0x00` Texture |
| 0x3C | u16    | `muImportCount`                    | number of imports (Font: N pages; Texture: 0) |
| 0x3E | u8     | `muFlags`                          | 0 |
| 0x3F | u8     | `muStreamIndex`                    | 0 |

The loader reads `size = word & 0x0FFFFFFF` and `alignment = 1 << (word >> 28)`. So size lives in the
low 28 bits and **log2(alignment)** in the high 4 bits. Examples: align 16 → `0x40000000 | size`;
align 4096 → `0xC0000000 | size`.

A resource's bytes for mem-pool *m* live at file offset `mauResourceDataOffset[m] + mauDiskOffset[m]`,
length `GetUncompressedSize(m)`. A mem-pool with size 0 is absent for that resource.

### 1.3 Import entry — 16 bytes each (`BundleV2::ImportEntry`)

The import table is a run of these inside the importing resource's **main block** at `muImportOffset`.

| off  | type | field          | notes |
|------|------|----------------|-------|
| 0x00 | u64  | `mResourceId`  | id of the resource to point at |
| 0x08 | u32  | `muOffset`     | byte offset within this resource's main block to overwrite with the target's main pointer |
| 0x0C | u32  | (pad)          | 0 |

At load, for each import the loader finds the target by id and writes its main pointer into
`this_resource_main + muOffset`.

---

## 2. The font bundle's resources

A debug font is **one Font resource (type 0x21)** that imports **N atlas-page Texture resources
(type 0x00)**, one per texture page (`N == muNumTexturePages`). Typically N = 1.

### 2.1 Font resource (type 0x21)

- **Main pool (mem-pool 0):** the `Font` struct, then its three arrays, packed in one block.
  *(The import table is appended after these by the packer — see §4.)*
- **No secondary pools.**

#### `Font` struct — 632 bytes (0x278)

| off    | type        | field                    | what to write |
|--------|-------------|--------------------------|---------------|
| 0x000  | u32         | `muVersionId`            | **`10`** (fix-up asserts this) |
| 0x004  | u32         | `mSizeOfFont`            | total main-block size (informational on PC; set to block size incl. imports) |
| 0x008  | f32         | `mScaleUV.mX`            | UV→em horizontal scale (see §3) |
| 0x00C  | f32         | `mScaleUV.mY`            | UV→em vertical scale |
| 0x010  | f32         | `mfLowerCaseScale`       | font metric |
| 0x014  | f32         | `mfBaseLine`             | font metric |
| 0x018  | f32         | `mfXHeight`              | font metric |
| 0x01C  | u32         | `muNumChars`             | glyph count (= length of both arrays below) |
| 0x020  | u64(offset) | `mpaFontChars`           | **offset** of the `FontChar[]` array |
| 0x028  | u64(offset) | `mpaFontCharIds`         | **offset** of the `u16[]` id array |
| 0x030  | u16[129]    | `mauHashOffsets`         | glyph-hash bucket prefix sums (see §3.2) |
| 0x134  | u32         | `muNumTexturePages`      | N (atlas pages = import count) |
| 0x138  | u64(offset) | `mpapTextures`           | **offset** of the page-pointer array (N × 8B, zero-filled; imports fill it) |
| 0x140  | u64         | `mpTextureState`         | **0** (fix-up nulls it; created at runtime) |
| 0x148  | 40 bytes    | `mTextureStateResource`  | **0** (runtime; Paradise's five resource lanes widened to x64 pointers) |
| 0x170  | u32         | `muFontHeightInPixels`   | nominal pixel height |
| 0x174  | char[128]   | `macTypefaceFamilyName`  | NUL-terminated; fix-up lowercases it |
| 0x1F4  | char[128]   | `macTypefaceStyleName`   | NUL-terminated |

#### `FontChar` — 32 bytes, the `mpaFontChars[]` element

| off  | type | field               | meaning |
|------|------|---------------------|---------|
| 0x00 | f32  | `mTopLeftUV.x`      | glyph top-left U in the atlas (0..1) |
| 0x04 | f32  | `mTopLeftUV.y`      | glyph top-left V |
| 0x08 | f32  | `mDimensionsUV.x`   | glyph width in atlas UV (also the on-screen width source) |
| 0x0C | f32  | `mDimensionsUV.y`   | glyph height in atlas UV |
| 0x10 | f32  | `mStart.x`          | pen bearing X (UV units) |
| 0x14 | f32  | `mStart.y`          | pen bearing Y (UV units) |
| 0x18 | f32  | `mfAdvance`         | pen advance (UV units; see §3 for the scale) |
| 0x1C | u16  | `mu16TexturePageId` | which atlas page (index into `mpapTextures`) |
| 0x1E | u8   | `mbIsLowerCaseScale`| 0/1 |
| 0x1F | u8   | `mbIsRenderable`    | **0 = no quad emitted** (space etc.), 1 = drawn |

`mpaFontCharIds[i]` is the UTF-16 code of `mpaFontChars[i]` — the two arrays are parallel and ordered
as §3.2 requires.

### 2.2 Atlas-page Texture resource (type 0x00), ×N

> Full details: [TEXTURE_RESOURCE_SCHEMA.md](TEXTURE_RESOURCE_SCHEMA.md). Summary below.

- **Main pool (mem-pool 0):** the `Texture` header (40 bytes) — pointers/flags zeroed, format+size set.
- **Graphics-system pool (mem-pool 1):** the raw pixel data (the mip chain). *Use mem-pool 1, not 2:*
  the loader maps bundle mem-pool 1 → rw slot 2, which is what the raster fix-up reads pixels from.
- No imports.

#### `Texture` header — 40 bytes (0x28)

| off  | type | field                 | what to write |
|------|------|-----------------------|---------------|
| 0x00 | u64  | `mpD3DTexture`        | 0 |
| 0x08 | u64  | `mpTextureDataStruct` | 0 |
| 0x10 | u64  | `mpReserved8`         | 0 |
| 0x18 | 4×u8 | `mbFlagC..mbFlagF`    | 0 |
| 0x1C | s32  | `miFormat`            | **D3DFORMAT** (e.g. 21 = `D3DFMT_A8R8G8B8`) |
| 0x20 | u16  | `muWidth`             | atlas width (px) |
| 0x22 | u16  | `muHeight`            | atlas height (px) |
| 0x24 | u8   | `muDepth`             | 1 |
| 0x25 | u8   | `muNumMipLevels`      | mip count (1 if no mips) |
| 0x26 | u16  | `muFlags`             | 0 |

#### Pixel data (mem-pool 1)

The mip chain, **tightly packed**, level 0 first, in `miFormat`'s byte layout. For `A8R8G8B8` (21)
each pixel is 4 bytes **B,G,R,A** and each level is `width*4*height` bytes; level *k* is
`max(1,W>>k) × max(1,H>>k)`. Block formats (DXT1=827611204, DXT3=861165636, DXT5=894720068) are
`ceil(W/4)*ceil(H/4)*blockBytes` per level (8 bytes/block DXT1, 16 DXT3/5). For a one-page,
one-mip 32-bit atlas this is simply `width*height*4` bytes of BGRA.

---

## 3. Glyph metrics & the hash table

### 3.1 How the renderer uses the metrics (so you can calibrate)

For a draw at text height `H` (px), per glyph `fc`:

```
glyphW_px = mScaleUV.x * H            // pen→glyph scale, X
glyphH_px = mScaleUV.y * H            //                  Y
advance_px = fc.mfAdvance * fabs( (H / mScaleUV.y) * 0.73 )
left   = penX + fc.mStart.x * glyphW_px
top    = penY + fc.mStart.y * glyphH_px
right  = left + fc.mDimensionsUV.x * glyphW_px
bottom = top  + fc.mDimensionsUV.y * glyphH_px
UV rect = [mTopLeftUV , mTopLeftUV + mDimensionsUV]   // atlas coords, 0..1
penX += advance_px
```

So `mTopLeftUV`/`mDimensionsUV`/`mStart` are all in normalised atlas-UV units, and `mScaleUV` converts
UV units to em (text-height-relative) units. Pick `mScaleUV` so a glyph that is `mDimensionsUV` wide in
the atlas renders at the size you want; calibrate `mfAdvance` against the `*(H/mScaleUV.y)*0.73` factor.

### 3.2 `mauHashOffsets` (128-bucket hash, 129 entries)

Glyph lookup (`FindFontChar`) does: `bucket = code & 127`; binary-search `mpaFontCharIds` over
`[mauHashOffsets[bucket] , mauHashOffsets[bucket+1])`. Therefore:

1. Bucket every glyph by `code & 127`.
2. Lay the glyphs out **bucket 0 first, then 1, … then 127**, contiguously, and **within each bucket
   sort ascending by code**. `mpaFontChars[i]` and `mpaFontCharIds[i]` follow this same order.
3. `mauHashOffsets[b]` = index of the first glyph in bucket `b` (i.e. the running total of all earlier
   buckets' sizes). `mauHashOffsets[0] = 0`; `mauHashOffsets[128] = muNumChars` (the end sentinel).

Include a `'-'` glyph (U+002D, code 45): it's the missing-character fallback.

---

## 4. Authoring it with YAP

YAP (`tools/YAP`) packs/extracts exactly this container and now understands platform 4. It is
content-agnostic: it copies each resource's `.dat` bytes verbatim and appends the import table itself,
so **you build the binary `.dat` payloads to §2 and YAP assembles the bundle.**

Lay out an input folder:

```
fontsrc/
  .meta.yaml
  <FONTID>.dat                 # the Font struct + FontChar[] + id[] + page-ptr[N] (zeroed)
  <FONTID>.imports.yaml        # or per-resource <FONTID>_imports.yaml
  <PAGEID>_primary.dat         # the 40-byte Texture header (primary / mem-pool 0)
  <PAGEID>_secondary.dat       # the pixel data (secondary / mem-pool 1)
```

`.meta.yaml`:

```yaml
bundle:
  platform: 4          # our x64 PC format
  compressed: false
  mainMemOptimised: false
  graphicsMemOptimised: false
resources:
  0x000000aa:          # the Font  (FONTID)
    type: 0x21
    alignment: [0x10]
  0x000000bb:          # atlas page (PAGEID)
    type: 0x0
    secondaryMemoryType: 1     # pixels go in mem-pool 1
    alignment: [0x10, 0x80]
```

`.imports.yaml` (the font's page references; `offset` is the byte offset of `mpapTextures[i]` *within
the font's main block* = `page_ptr_array_offset + i*8`, where the page-pointer array lives **after** the
`Font` struct (0x278) + the `FontChar[]` and id[] arrays — i.e. it is always ≥ 0x278, never inside the
struct). Set `mpapTextures` (Font +0x138) to that same `page_ptr_array_offset`):

```yaml
0x000000aa:                 # FONTID
  # one page, laid out at e.g. 0x2C0 (= after Font + FontChar[] + id[], 8-aligned):
  - 0x000002c0: 0x000000bb  # mpapTextures[0] -> PAGEID  (and Font.mpapTextures = 0x2C0)
```

Build it:

```
YAP c fontsrc Default.font
```

YAP appends the 16-byte import entries to the font's main block, sets `muImportOffset`, packs the
mem-pool data regions, and writes the platform-4 header. The result loads through `LoadBundle`.

> Note: in the font `.dat`, `mpapTextures[i]` slots are zero-filled — the loader's import resolution
> writes the real page pointers there. `mpTextureState`/`mTextureStateResource` are also zero; the
> runtime builds the texture state after load (`Font::CreateTextureState`).

---

## 5. What happens at load (for reference)

1. `LoadBundle` validates `bnd2`/v2/**platform 4**, then per entry: allocate in the Pool, `memcpy`
   each mem-pool's bytes into place.
2. **Texture fix-up** (`RwRasterResourceType::FixUp`): reads the header, creates a managed D3D9 texture
   in `miFormat`, uploads the mem-pool-1 mip chain.
3. **Font fix-up** (`FontResourceType::FixUp`): asserts `muVersionId==10`; rebases `mpaFontChars`,
   `mpaFontCharIds`, `mpapTextures` (offset→absolute); nulls `mpTextureState`; lowercases the family
   name.
4. **Import resolution**: writes each atlas page's pointer into `mpapTextures[i]`.
5. `LoadAndSetDebugFont` finds the Font, calls `Font::CreateTextureState` (binds page 0), and hands the
   handle to the debug renderers — after which `DrawText` renders bitmap glyphs.
