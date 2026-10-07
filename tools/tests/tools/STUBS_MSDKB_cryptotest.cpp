// MSDKB known-answer test for the MassiveAd hashing helpers (SHA-1, HMAC-SHA1, MD5 hex digest,
// MT19937). Built and run by STUBS_MSDKB_cryptotest.py; links the real SDK TUs.

#include "SDKs/Packages/MassiveAd/MassiveAdClient3Crypto.h"
#include "SDKs/Packages/MassiveAd/LibTomCrypt/tomcrypt_massive.h"
#include "SDKs/Packages/MassiveAd/MassiveAdClient3.h"
#include "SDKs/Packages/MassiveAd/MassiveAdClient3ClientCore.h"

#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>

// Test-only providers for the SDK hooks the hashing TUs call.
namespace MassiveAdClient3
{
static void* TestMalloc(unsigned int nSize) { return std::malloc(nSize); }
static void TestFree(void* p) { std::free(p); }
void* (*MassiveMalloc)(unsigned int) = TestMalloc;
void (*MassiveFree)(void*) = TestFree;
int MassiveFormatString(char* pcBuffer, unsigned int nCount, const char* pcFormat, ...)
{
    va_list a;
    va_start(a, pcFormat);
    int n = _vsnprintf(pcBuffer, nCount, pcFormat, a);
    va_end(a);
    return n;
}
CMassiveClientCore* CMassiveClientCore::Instance() { return 0; }
long long CMassiveClientCore::GetTime() { return 0; }
CMassiveSystem* CMassiveSystem::Instance() { return 0; }
int CMassiveSystem::GetServerTimeFormatted(unsigned long long, char* pcBuffer, unsigned int)
{
    std::strcpy(pcBuffer, "2008-01-01 00:00:00,000");
    return 23;
}
}

static int gnFail = 0;

static void Hex(const unsigned char* p, int n, char* out)
{
    for (int i = 0; i < n; ++i)
        std::sprintf(out + 2 * i, "%02x", p[i]);
}

static void Check(const char* name, const char* got, const char* want)
{
    bool ok = std::strcmp(got, want) == 0;
    if (!ok)
        ++gnFail;
    std::printf("%s %-28s %s%s%s\n", ok ? "PASS" : "FAIL", name, got, ok ? "" : " want ", ok ? "" : want);
}

static void Sha1(const char* name, const unsigned char* msg, unsigned int len, int repeat, const char* want)
{
    SHA1Context c;
    unsigned char d[20];
    char h[41];
    SHA1Reset(&c);
    for (int i = 0; i < repeat; ++i)
        SHA1Input(&c, msg, len);
    SHA1Result(&c, d);
    Hex(d, 20, h);
    Check(name, h, want);
}

static void Hmac(const char* name, const void* key, int klen, const void* msg, int mlen, const char* want)
{
    void* d = MassiveAdClient3::CalculateSHA1HMac(msg, mlen, static_cast<const char*>(key), klen);
    char h[41];
    Hex(static_cast<unsigned char*>(d), 20, h);
    std::free(d);
    Check(name, h, want);
}

int main()
{
    const char* abc = "abc";
    const char* abq = "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq";
    Sha1("sha1 abc", (const unsigned char*)abc, 3, 1, "a9993e364706816aba3e25717850c26c9cd0d89d");
    Sha1("sha1 abcdbcde...", (const unsigned char*)abq, (unsigned)std::strlen(abq), 1,
         "84983e441c3bd26ebaae4aa1f95129e5e54670f1");
    unsigned char a1000[1000];
    std::memset(a1000, 'a', sizeof(a1000));
    Sha1("sha1 1e6 x 'a'", a1000, 1000, 1000, "34aa973cd4c4daa4f61eeb2bdbad27316534016f");
    const char* rep = "0123456701234567012345670123456701234567012345670123456701234567";
    Sha1("sha1 rfc3174 #4 (x10)", (const unsigned char*)rep, 64, 10, "dea356a2cddd90c7a7ecedc5ebb563934f460452");

    unsigned char k1[20];
    std::memset(k1, 0x0b, 20);
    Hmac("hmac rfc2202 #1", k1, 20, "Hi There", 8, "b617318655057264e28bc0b6fb378c8ef146be00");
    Hmac("hmac rfc2202 #2", "Jefe", 4, "what do ya want for nothing?", 28, "effcdf6ae5eb2fa2d27416d5f184df9c259a7c79");
    unsigned char k3[20], m3[50];
    std::memset(k3, 0xaa, 20);
    std::memset(m3, 0xdd, 50);
    Hmac("hmac rfc2202 #3", k3, 20, m3, 50, "125d7342b9ac11cd91a39af48aa17b4f63f175d3");
    unsigned char k6[80];
    std::memset(k6, 0xaa, 80);
    const char* m6 = "Test Using Larger Than Block-Size Key - Hash Key First";
    Hmac("hmac rfc2202 #6 (80B key)", k6, 80, m6, (int)std::strlen(m6), "aa4ae5e15272d00e95705637ce8a3b55ed402112");
    const char* m7 = "Test Using Larger Than Block-Size Key and Larger Than One Block-Size Data";
    Hmac("hmac rfc2202 #7", k6, 80, m7, (int)std::strlen(m7), "e8e99d0f45237d786d6bbaa7965c7808bbff1a91");

    struct { const char* m; const char* d; } md5v[] = {
        { "", "d41d8cd98f00b204e9800998ecf8427e" },
        { "a", "0cc175b9c0f1b6a831c399e269772661" },
        { "abc", "900150983cd24fb0d6963f7d28e17f72" },
        { "message digest", "f96b697d7cb7938d525a2f31aaf161d0" },
        { "abcdefghijklmnopqrstuvwxyz", "c3fcd3d76192e4007dfb496cca67e13b" },
        { "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", "d174ab98d277d9f5a5611c2c9f419d9f" },
        { "12345678901234567890123456789012345678901234567890123456789012345678901234567890",
          "57edf4a22be3c955ac49da2e2107b67a" },
    };
    for (auto& v : md5v)
    {
        char name[64];
        std::sprintf(name, "md5 rfc1321 len %u", (unsigned)std::strlen(v.m));
        Check(name, MassiveAdClient3::CalculateMD5Hash(v.m, (int)std::strlen(v.m)), v.d);
    }

    // MT19937: the reference first draw for the default seed, then the mt19937ar.out vector.
    char buf[128];
    std::sprintf(buf, "%lu", genrand_int32());
    Check("mt default seed draw 0", buf, "3499211612");
    unsigned long key[4] = { 0x123, 0x234, 0x345, 0x456 };
    init_by_array(key, 4);
    unsigned long d[5];
    for (int i = 0; i < 5; ++i)
        d[i] = genrand_int32();
    std::sprintf(buf, "%lu %lu %lu %lu %lu", d[0], d[1], d[2], d[3], d[4]);
    Check("mt init_by_array draws 0-4", buf, "1067595299 955945823 477289528 4107218783 4228976476");
    for (int i = 5; i < 1000; ++i)
        d[0] = genrand_int32();
    std::sprintf(buf, "%lu", d[0]);
    Check("mt init_by_array draw 999", buf, "3460025646");

    std::printf("RESULT %s (%d failures)\n", gnFail ? "FAIL" : "PASS", gnFail);
    return gnFail ? 1 : 0;
}
