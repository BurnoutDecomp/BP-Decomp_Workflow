// Dev tool: print the x64 on-disk offsets/sizes of the font bundle structs (authoritative, via
// offsetof) so references/FONT_BUNDLE_SCHEMA.md stays exact if these structs change. Re-run after
// editing CgsFont.h / texture.h / CgsResourceBundle2.h.
//
// Build (from repo root) with the same include dirs the compile gate uses
// (progress/verify.config.json -> include_dirs), e.g. under an MSVC dev shell:
//   cl /nologo /EHsc /std:c++17 /I b5-decomp/src ^
//      /I b5-decomp/vendor/EABase/include/Common /I b5-decomp/vendor/renderware/include ^
//      tools/_dump_font_offsets.cpp && _dump_font_offsets.exe
#include <cstddef>
#include <cstdio>

#include "GameShared/GameClasses/Fonts/CgsFont.h"
#include "GameShared/GameClasses/System/Resource/CgsResourceBundle2.h"
#include "GameShared/GameClasses/System/Resource/CgsResourceID.h"
#include "pc/gcm/renderengine/texture.h"

#define OFF(T, F) printf("  +0x%02zX  %s\n", offsetof(T, F), #F)
#define SZ(T)     printf("sizeof(%s) = %zu (0x%zX)\n", #T, sizeof(T), sizeof(T))

int main()
{
    printf("sizeof(void*) = %zu\n\n", sizeof(void*));

    SZ(CgsResource::Font);
    OFF(CgsResource::Font, muVersionId);
    OFF(CgsResource::Font, mSizeOfFont);
    OFF(CgsResource::Font, mScaleUV);
    OFF(CgsResource::Font, mfLowerCaseScale);
    OFF(CgsResource::Font, mfBaseLine);
    OFF(CgsResource::Font, mfXHeight);
    OFF(CgsResource::Font, muNumChars);
    OFF(CgsResource::Font, mpaFontChars);
    OFF(CgsResource::Font, mpaFontCharIds);
    OFF(CgsResource::Font, mauHashOffsets);
    OFF(CgsResource::Font, muNumTexturePages);
    OFF(CgsResource::Font, mpapTextures);
    OFF(CgsResource::Font, mpTextureState);
    OFF(CgsResource::Font, mTextureStateResource);
    OFF(CgsResource::Font, muFontHeightInPixels);
    OFF(CgsResource::Font, macTypefaceFamilyName);
    OFF(CgsResource::Font, macTypefaceStyleName);
    printf("\n");

    SZ(CgsResource::FontChar);
    OFF(CgsResource::FontChar, mTopLeftUV);
    OFF(CgsResource::FontChar, mDimensionsUV);
    OFF(CgsResource::FontChar, mStart);
    OFF(CgsResource::FontChar, mfAdvance);
    OFF(CgsResource::FontChar, mu16TexturePageId);
    OFF(CgsResource::FontChar, mbIsLowerCaseScale);
    OFF(CgsResource::FontChar, mbIsRenderable);
    printf("\n");

    SZ(renderengine::Texture);
    OFF(renderengine::Texture, mpD3DTexture);
    OFF(renderengine::Texture, mpTextureDataStruct);
    OFF(renderengine::Texture, mpReserved8);
    OFF(renderengine::Texture, mbFlagC);
    OFF(renderengine::Texture, miFormat);
    OFF(renderengine::Texture, muWidth);
    OFF(renderengine::Texture, muHeight);
    OFF(renderengine::Texture, muDepth);
    OFF(renderengine::Texture, muNumMipLevels);
    OFF(renderengine::Texture, muFlags);
    printf("\n");

    SZ(CgsResource::BundleV2);
    OFF(CgsResource::BundleV2, macMagicNumber);
    OFF(CgsResource::BundleV2, muVersion);
    OFF(CgsResource::BundleV2, muPlatform);
    OFF(CgsResource::BundleV2, muDebugDataOffset);
    OFF(CgsResource::BundleV2, muResourceEntriesCount);
    OFF(CgsResource::BundleV2, muResourceEntriesOffset);
    OFF(CgsResource::BundleV2, mauResourceDataOffset);
    OFF(CgsResource::BundleV2, muFlags);
    printf("\n");

    SZ(CgsResource::BundleV2::ResourceEntry);
    OFF(CgsResource::BundleV2::ResourceEntry, mResourceId);
    OFF(CgsResource::BundleV2::ResourceEntry, muImportHash);
    OFF(CgsResource::BundleV2::ResourceEntry, mauUncompressedSizeAndAlignment);
    OFF(CgsResource::BundleV2::ResourceEntry, mauSizeAndAlignmentOnDisk);
    OFF(CgsResource::BundleV2::ResourceEntry, mauDiskOffset);
    OFF(CgsResource::BundleV2::ResourceEntry, muImportOffset);
    OFF(CgsResource::BundleV2::ResourceEntry, muResourceTypeId);
    OFF(CgsResource::BundleV2::ResourceEntry, muImportCount);
    OFF(CgsResource::BundleV2::ResourceEntry, muFlags);
    OFF(CgsResource::BundleV2::ResourceEntry, muStreamIndex);
    printf("\n");

    SZ(CgsResource::BundleV2::ImportEntry);
    OFF(CgsResource::BundleV2::ImportEntry, mResourceId);
    OFF(CgsResource::BundleV2::ImportEntry, muOffset);
    printf("\n");

    SZ(CgsResource::ID);
    return 0;
}
