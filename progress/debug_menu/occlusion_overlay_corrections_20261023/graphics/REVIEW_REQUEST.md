# Review request: getter/cursor correction

Review this new immutable composition against `bindings.json`; the previous friend-based packet remains untouched. Base: private b5-decomp `9cbefd173085312ebaee5bab4875b8492fc292cb`. The reviewed blobby Render body and five GUI posts are present in that base.

1. Confirm DecFIGS `BrnDispatchThreadInputBuffer.h:160` declares the public `const Matrix44& GetOcclusionViewProjectionMatrix() const` and h:79 names the private member. Check that the inline return body matches ARTIST Render's locked four-row loads at `0x8240C1C0..C220`, without adding an accessor lock assert.
2. Confirm both the base blobby Render read and new occlusion setup use that getter, with no friend workaround left.
3. Recheck the preserved dispatcher cursor return against ARTIST `0x827F2718` and the list-19/list-11 continuation loops.
4. Return `VERDICT: pass|fail` with source-level findings. No compile, runtime, native, or debug-menu site credit is requested or claimed.
