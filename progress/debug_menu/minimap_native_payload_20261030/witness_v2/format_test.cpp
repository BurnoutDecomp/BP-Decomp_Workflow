#include "GameSource/Gui/SatNav/SatNavWitnessFormat.h"
#include "GameShared/GameClasses/Development/CgsStrStream.h"
#include <cstdio>
#include <cstring>
#include <cstdlib>
namespace CgsDev { namespace Assert {
int BeginAssert(){return 0;} int FireAssert(const char*,const char*,int){std::abort();} void* EndAssert(){return nullptr;}
}}
int main() {
    BrnGui::GuiEventRenderSatNav a{}, b{};
    a.mpMapTexture = reinterpret_cast<void*>(0x11111111ABCDEF01ull);
    b.mpMapTexture = reinterpret_cast<void*>(0x22222222ABCDEF01ull);
    std::uint32_t aBits=0x3f800000, bBits=0x3f800001;
    std::memcpy(&a.mv3CarPosition.x,&aBits,4); std::memcpy(&b.mv3CarPosition.x,&bBits,4);
    char oldA[256]={}, oldB[256]={};
    CgsDev::StrStream streamA(oldA,sizeof oldA), streamB(oldB,sizeof oldB);
    streamA << a.mpMapTexture << " " << a.mv3CarPosition.x;
    streamB << b.mpMapTexture << " " << b.mv3CarPosition.x;
    char newA[256],newB[256];
    if(!SatNavWitness::Format(a,newA,sizeof newA) || !SatNavWitness::Format(b,newB,sizeof newB)) return 1;
    std::printf("old A: %s\nold B: %s\nnew A: %s\nnew B: %s\n",oldA,oldB,newA,newB);
    if(std::strcmp(oldA,oldB)!=0 || std::strcmp(newA,newB)==0) return 2;
    if(!std::strstr(newA,"11111111ABCDEF01") || !std::strstr(newB,"22222222ABCDEF01") ||
       !std::strstr(newA,"3F800000") || !std::strstr(newB,"3F800001")) return 3;
    BrnGui::GuiEventRenderSatNav pointerOnly=a, floatOnly=a;
    pointerOnly.mpMapTexture=b.mpMapTexture;
    std::memcpy(&floatOnly.mv3CarPosition.x,&bBits,4);
    char pointerText[256],floatText[256];
    if(!SatNavWitness::Format(pointerOnly,pointerText,sizeof pointerText) ||
       !SatNavWitness::Format(floatOnly,floatText,sizeof floatText) ||
       std::strcmp(newA,pointerText)==0 || std::strcmp(newA,floatText)==0) return 4;
    unsigned char raw=0xFE; std::memcpy(&floatOnly.mbRotateMap,&raw,1);
    if(!SatNavWitness::Format(floatOnly,floatText,sizeof floatText) ||
       !std::strstr(floatText,",FE,00")) return 5;
    std::puts("PASS: old formatter collides; exact formatter distinguishes each pointer/float and preserves raw flag byte");
}
