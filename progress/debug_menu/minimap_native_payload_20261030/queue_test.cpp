#include "GameSource/Gui/SatNav/BrnSatNavComponent.h"
#include "GameShared/GameClasses/Gui/CgsGuiEvent.h"
#include <cstdio>
#include <cstring>
#include <cstddef>
#include <cstdlib>
namespace CgsDev { namespace Log { StrStreamBase* gpDebugPrint = nullptr; } namespace Message { u64 gxMessageFilterFlags = 0; } namespace Assert {
int BeginAssert(){return 0;} int FireAssert(const char*,const char*,int){std::abort();} void* EndAssert(){return nullptr;}
}}
using Payload=BrnGui::GuiEventRenderSatNav;
using Wrapper=CgsGui::GuiEventWrapper<Payload,41>;
using Queue=CgsModule::VariableEventQueue<4096,16>;
struct OldWrapper : CgsGui::GuiEvent<212> { Payload mPayload; explicit OldWrapper(const Payload& p):CgsGui::GuiEvent<212>(48,16),mPayload(p){} };
static bool same(const Payload& a,const Payload& b) {
 return a.mv3CarPosition.x==b.mv3CarPosition.x && a.mv3CarPosition.y==b.mv3CarPosition.y && a.mv3CarPosition.z==b.mv3CarPosition.z && a.mv3CarPosition.w==b.mv3CarPosition.w && a.mfCarOrientation==b.mfCarOrientation && a.mfCarSpeedMph==b.mfCarSpeedMph && a.miZoomLevel==b.miZoomLevel && a.mpMapTexture==b.mpMapTexture && a.mpMaskTexture==b.mpMaskTexture && a.mpRouteSegmentTexture==b.mpRouteSegmentTexture && a.mbRotateMap==b.mbRotateMap && a.mbUseTrajectory==b.mbUseTrajectory;
}
template<class W> static bool roundtrip(W& w,const Payload& expected,bool wantPass,unsigned char poison) {
 Queue outer,view; std::memset(&outer,0xA5,sizeof outer); std::memset(&view,poison,sizeof view); outer.Construct(); view.Construct();
 if(!outer.AddEvent(reinterpret_cast<const CgsModule::Event*>(&w),41,sizeof w)) return false;
 const CgsModule::Event* boxed=nullptr; s32 size=0; if(outer.GetFirstEvent(&boxed,&size)!=41 || size!=sizeof w) return false;
 const s32* h=reinterpret_cast<const s32*>(boxed); const auto* raw=reinterpret_cast<const CgsModule::Event*>(reinterpret_cast<const char*>(boxed)+h[2]);
 if(!view.AddEvent(raw,h[1],h[0])) return false;
 const unsigned char next[16]={}; if (!view.AddEvent(reinterpret_cast<const CgsModule::Event*>(next),777,sizeof next)) return false;
 const CgsModule::Event* received=nullptr; if(view.GetFirstEvent(&received,&size)!=212) return false;
 Payload observed; std::memcpy(&observed,received,sizeof observed);
 bool equal=same(observed,expected);
 std::printf("forwarded=%d equal=%d route=%p rotate=%u trajectory=%u\n",size,equal,observed.mpRouteSegmentTexture,(unsigned)observed.mbRotateMap,(unsigned)observed.mbUseTrajectory);
 return equal==wantPass && size==(wantPass?sizeof(Payload):48);
}
int main() {
 Payload p{}; p.mv3CarPosition.x=123.0f;p.mv3CarPosition.y=-3.0f;p.mv3CarPosition.z=456.0f;p.mv3CarPosition.w=7.0f;p.mfCarOrientation=1.25f;p.mfCarSpeedMph=74.0f;p.miZoomLevel=1;
 p.mpMapTexture=reinterpret_cast<void*>(0x1122334455667788ull);p.mpMaskTexture=reinterpret_cast<void*>(0x2233445566778899ull);p.mpRouteSegmentTexture=reinterpret_cast<void*>(0x33445566778899AAull);p.mbRotateMap=true;p.mbUseTrajectory=true;
 std::printf("payload=%zu align=%zu wrapper=%zu payload-offset=%zu map=%zu mask=%zu route=%zu rotate=%zu trajectory=%zu\n",sizeof(Payload),alignof(Payload),sizeof(Wrapper),offsetof(Wrapper,mOutEvent),offsetof(Payload,mpMapTexture),offsetof(Payload,mpMaskTexture),offsetof(Payload,mpRouteSegmentTexture),offsetof(Payload,mbRotateMap),offsetof(Payload,mbUseTrajectory));
 OldWrapper old(p); Wrapper fixed(p); if(!roundtrip(old,p,false,0) || !roundtrip(fixed,p,true,0)) return 1;
 p.mbRotateMap=false; p.mbUseTrajectory=false; OldWrapper old2(p); Wrapper fixed2(p); if(!roundtrip(old2,p,false,1) || !roundtrip(fixed2,p,true,1)) return 1; std::puts("PASS");
}