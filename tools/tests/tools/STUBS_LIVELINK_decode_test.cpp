// STUBS_LIVELINK_decode_test.cpp -- unit test for the AttribSys live-link decoder
// (b5-decomp/src/SDKs/Packages/AttribSys/1.2.1.2/AttribSys/runtime/common/attriblivelink.cpp).
//
// The decoder TU is compiled INTO this test (it keeps EditSpecifier / ModifyMemory internal),
// linked with the real attribute hash (attribhash64.cpp) and the vendor EASTL red-black tree.
// Every other external the TU references is stubbed below: the attribute database reports
// "no such class", so DecodeLiveLinkMessage runs its parse + edit-table path and stops at
// kDecodeCannotFindObject. Build + run: STUBS_LIVELINK_decode_test.ps1.
#include "SDKs/Packages/AttribSys/1.2.1.2/AttribSys/runtime/common/attriblivelink.cpp"

#include <cstdarg>
#include <cstdio>

// ---- stubs for the decoder's externals --------------------------------------------------------
static int siAssertCount = 0;
static int siMallocCount = 0;

namespace CgsDev { namespace Assert {
    int   BeginAssert() { return 0; }
    int   FireAssert(const char* lpcExpression, const char*, int) { ++siAssertCount; printf("  [assert] %s", lpcExpression); return 0; }
    void* EndAssert() { return NULL; }
} }

namespace CgsCore {
    void SPrintf(char* lpBuffer, u32 luLength, const char* lpcFormat, ...)
    {
        va_list lArgs;
        va_start(lArgs, lpcFormat);
        vsnprintf(lpBuffer, luLength, lpcFormat, lArgs);
        va_end(lArgs);
    }
}

namespace CgsAttribSys {
    static AttribSysPackageAllocator sTestAllocator;
    AttribSysPackageAllocator* AttribSysMemoryManager::GetAttribSysAllocator() { return &sTestAllocator; }
    AttribSysPackageAllocator* AttribSysMemoryManager::GetEaStlAllocator() { return &sTestAllocator; }
    void* AttribSysPackageAllocator::Malloc(size_t lnSize, int) { ++siMallocCount; return malloc(lnSize); }
    void  AttribSysPackageAllocator::Free(void* lpBlock, s32, const char*) { free(lpBlock); }
}

static unsigned char saFakeDatabasePrivate[4096];
Attrib::Class* VecHashMap_Attrib_Class_TablePolicy_0_16::Find(u64) const { return NULL; }

namespace Attrib {
    DatabasePrivate* GetDatabasePrivate() { return reinterpret_cast<DatabasePrivate*>(saFakeDatabasePrivate); }
    Collection* FindCollection(u64, u64) { return NULL; }

    // Unreachable while the class lookup misses.
    Database& Database::Get() { abort(); }
    const TypeDesc& Database::GetTypeDesc(u64) const { abort(); }
    Instance::Instance(Collection*, void*) { abort(); }
    Instance::~Instance() { abort(); }
    void* Instance::Get(AttributeValue*, int*, u64) { abort(); }
    int   Attribute::GetLength() { abort(); }
    bool  Attribute::IsInherited() { abort(); }
    void* Attribute::GetInternalPointer(u32) { abort(); }
    const TypeDesc* Node::GetTypeDesc() const { abort(); }
    void* Array::GetData(unsigned int) { abort(); }
    const ClassStaticDesc* ClassStaticDesc::GetStatic(::Attribute::Key) { abort(); }
}

// ---- test cases -------------------------------------------------------------------------------
static int siFailures = 0;
#define CHECK(cond) do { if (!(cond)) { ++siFailures; printf("  FAIL line %d: %s\n", __LINE__, #cond); } } while (0)

static u64 KeyOf(const char* lpcName)
{
    return Attrib::StringToKey(lpcName, static_cast<u32>(strlen(lpcName)), Attrib::KU_ATTRIB_STRING_TO_KEY_SEED);
}

int main()
{
    using namespace Attrib;

    printf("[1] EditSpecifier::Decode, well-formed name\n");
    {
        const char* lpcMessage = "physicsvehiclehandling.ALIEN.TopSpeed.3=[4:0:]00004842";
        EditSpecifier lSpec(0, 0, 0, 0);
        const char* lpcEnd = lSpec.Decode(lpcMessage);
        CHECK(lpcEnd == strchr(lpcMessage, '='));
        EditSpecifier lExpected(KeyOf("physicsvehiclehandling"), KeyOf("ALIEN"), KeyOf("TopSpeed"), 3);
        CHECK(!(lSpec < lExpected) && !(lExpected < lSpec));
        CHECK(lSpec.GetCollectionKey() == KeyOf("ALIEN"));
        CHECK(lSpec.GetAttribKey() == KeyOf("TopSpeed"));
        CHECK(lSpec.GetIndex() == 3);
    }

    printf("[2] EditSpecifier::Decode, edge cases\n");
    {
        EditSpecifier lSpec(0, 0, 0, 0);
        CHECK(lSpec.Decode("class.collection") == NULL);                 // missing third '.'
        CHECK(lSpec.Decode("noDotsAtAll") == NULL);
        const char* lpcEmpty = ".coll.attr.12:";                          // empty class name -> key 0
        CHECK(lSpec.Decode(lpcEmpty) == lpcEmpty + 13);
        EditSpecifier lExpected(0, KeyOf("coll"), KeyOf("attr"), 12);
        CHECK(!(lSpec < lExpected) && !(lExpected < lSpec));
        const char* lpcNoOp = "a.b.c.7";                                  // index ends at NUL
        CHECK(lSpec.Decode(lpcNoOp) == lpcNoOp + 7);
        CHECK(lSpec.GetIndex() == 7);
        CHECK(lSpec.Decode("a.b.c.123456789012345=") != NULL);           // 15-char index fits
        CHECK(lSpec.Decode("a.b.c.1234567890123456=") == NULL);          // 16 chars does not
    }

    printf("[3] CharToEditOpCodeLabel\n");
    {
        CHECK(CharToEditOpCodeLabel('=') == kReplaceLoopOp);
        CHECK(CharToEditOpCodeLabel(':') == kReplaceDataOp);
        CHECK(CharToEditOpCodeLabel('+') == kAddObjectOp);
        CHECK(CharToEditOpCodeLabel('-') == kRemoveObjectOp);
        CHECK(CharToEditOpCodeLabel('#') == kShapeObjectOp);
        CHECK(CharToEditOpCodeLabel(0) == kTerminatorOp);
        CHECK(CharToEditOpCodeLabel('x') == kInvalidOp);
    }

    printf("[4] ModifyMemory\n");
    {
        unsigned char lacBytes[4] = { 0x11, 0x22, 0x33, 0x44 };
        const int liAssertsBefore = siAssertCount;
        ModifyMemory(lacBytes, 3, "0aFFz1");
        CHECK(lacBytes[0] == 0x0A && lacBytes[1] == 0xFF && lacBytes[2] == 0x01 && lacBytes[3] == 0x44);
        CHECK(siAssertCount == liAssertsBefore);
        ModifyMemory(lacBytes, 2, "AB");                                  // too short: asserts
        CHECK(siAssertCount == liAssertsBefore + 1);
        printf("\n");
    }

    printf("[5] DecodeLiveLinkMessage results + edit table\n");
    {
        CHECK(DecodeLiveLinkMessage("garbage") == kDecodeMalformedObjectName);
        CHECK(gLiveLinkEditTable == NULL);
        CHECK(DecodeLiveLinkMessage("a.b.c.0=0000") == kDecodeCannotFindObject);
        CHECK(gLiveLinkEditTable != NULL && gLiveLinkEditTable->size() == 1);
        CHECK(DecodeLiveLinkMessage("a.b.c.0+") == kDecodeInvalidOperation);
        CHECK(gLiveLinkEditTable->size() == 1);                           // same specifier, same record
        CHECK(DecodeLiveLinkMessage("a.b.c.1:00") == kDecodeCannotFindObject);
        CHECK(gLiveLinkEditTable->size() == 2);
        const EditTable::iterator lIt = gLiveLinkEditTable->find(EditSpecifier(KeyOf("a"), KeyOf("b"), KeyOf("c"), 1));
        CHECK(lIt != gLiveLinkEditTable->end());
        CHECK(lIt != gLiveLinkEditTable->end() && &lIt->second.GetEditSpecifier() == &lIt->first);
        CHECK(lIt != gLiveLinkEditTable->end() && !lIt->second.IsLoopEdit());   // ':' is a data edit
        CHECK(siMallocCount == 3);                                        // table + two nodes
    }

    printf(siFailures == 0 ? "LIVELINK decode test: PASS\n" : "LIVELINK decode test: FAIL (%d)\n", siFailures);
    return siFailures == 0 ? 0 : 1;
}
