# GUI62162 Flapt native allocation prerequisite - fresh source review

VERDICT: pass

Approve the exact two source postimages below for checkpoint/build. No blocking allocation-bound or source finding remains. This is a narrow PC capacity projection for bank66; the console memory-map data and all engine consumers remain unchanged.

Source base: `e2ca9665933ef5faa186e4cec0cb2e341c21abd2`.
Workflow base: `f55c3add636d8652a8a508c88e1880feda546dc5`.
Native failure evidence:62162, executable SHA256 `068f07d8cca637d10d294c99a99e9d7737563af7a1c3b1bf852c5f0c4e984446`.

## Exact approved postimages

- `src/GameSource/Resource/BrnGameDataModule.cpp`: `9646904b0ce9dc0b59abff9aef03ac7d16331e644f5259421f429caa54b3dc65`.
- New `src/pc/gui/FlaptAllocatorCapacity.h`: `a3f069d1180cd9c473332bc3b387f639d35f93b2ca9929793a39767e72d6dead` (genuine absent preimage).

Author patch SHA256: `2e865042cbd985eef6e26184b73cd7137efa0fedef92c7122d03a2c8e7348ca9`.
Final author SEALED.json SHA256: `6220a11e0b3bd0dda08cb6ec2bd73905d50387cc3a576fa82b811023f1759cfe`; all217 members authenticate. The unchanged75-member source chunk independently authenticates as well. The old GameDataModule prefile exactly matches its actual e2ca Git blob.

## Independently recovered allocation failure

Both actual native-stage HUD bundles match the sealed asset pins. A separate resource-table parser and recursive traversal reproduce HD460 definitions instantiated as1748 clips,725 texts and7367 transforms; depth reaches11. Original allocation ordering and16-byte alignment consume858176 bytes at console56/388/64 strides, and948656 at native96/424/64. The first native request past921600 is transforms for clip39, depth6, child path[2,1,1,1,0,0], counts0/13/2: begin920656 plus960 equals921616,16 bytes over. SD independently reproduces1776 clips,725 texts,7471 transforms and958000 native bytes, with the first old-capacity text request reaching922096.

The full native failure executable hash was independently checked and its PE code decoded directly. Its child allocation is96*count, transforms64*count and text allocation424*count. Its CgsAptString constructor begins with the retained write through RCX+98, consistent with the observed null text-array path. This corroborates the allocator-capacity diagnosis; the total948656/958000 values are asset/typed-construction measurements, not an invented claim that the failed game completed those allocations.

Original raw ARTIST824700DC,82470148,82470194 and82471724 independently attest56-byte clip objects,64-byte transforms,388-byte text objects and the56-byte root. The original binary memory-map header/linear-record stride was independently followed to bank66: record82F2C120 names FLAPT_Allocator, bank66, original request0xE1000=921600. GUI configuration selects GetLinearAllocator(66) and sets its alignment16. Actual registry/FileInstance/manager ownership leads to this same allocator.

## Why the projection is bounded

R=max(align16(96)/56, align16(64)/64, align16(424)/388)=max(12/7,1,108/97)=12/7. The helper therefore returns align16(ceil(921600*12/7))=1579888. This derives from actual type widths and original attested strides, independently of one asset's literal count or failure offset.

For each allocation of n items, ceil16(n*N)<=n*ceil16(N)<=R*n*C<=R*ceil16(n*C). The allocator aligns allocation starts; the original bank begins aligned and its capacity is a multiple of16. Thus an original fitting trace implies the sum of rounded console charges is at most that capacity, including the final alignment rounding. Summing the inequality and rounding the new capacity up16 bounds every corresponding native prefix. The current typed fixture also checks all1275 valid per-family counts (255 clips,765 transforms,255 text entries).

Only the existing linear-family row with bank ID66 receives the projection. The same luNativeSize is passed to the physical backing carve and LinearMalloc::Create. All other six linear capacities retain their literal original values. Backing still comes through the existing root debug resource allocator's DoAllocate path; this does not enlarge a fixed shared parent-pool subregion, rewrite map data, redirect consumers or add another allocator. The runtime graph allocation remains the original root/child/transform/text path. No counts, layouts, queues, assertions, null handling, loader offsets or lifecycle gates are altered.

## Real typed controls and production compilation

An independent rerun in this reviewer's own pinned source overlay reproduces corrected21 checks/0 failures, exit0, and a genuine old e2ca creation-loop control13 checks/3 failures, exit1. Both compile successfully. The old control reproduces exactly HD mpaTransforms usage921616/capacity921600 and SD mpaTextFieldInstances usage922096/capacity921600; it does not earn a pass from compiler or linker failure.

The fixture retains actual registry and LinearMalloc code, manager/file/root/movie/text constructors, real CgsAptString/TextObject Construct, real file FixUp, actual typed arrays and real assets. Corrected HD/SD usage is948656/958000, every owned array is in range, other six allocator capacities remain original and backing canaries pass. Its OS backing, text-layout/render and root rewind endpoints are explicit. Its assertion observer stops the old negative control at the genuine failed allocation before the known invalid write; no such guard is shipped. No text readiness, font layout or timeline correctness is inferred.

The rerun script is the retained author logic with only PACK/ROOT/OVERLAY path constants relocated to this review directory; generated C++ and exact old/new loop hashes match the original fixture. No author output or shared source is modified. The four retained actual production TU compiles authenticate, with canonical f55 flags/include order,175 exact source/header pins, zero diagnostics and no physical source fallback. Compiler/SDK/vendor inputs remain host dependencies; there was no fresh shipping link here.

## Scope

This PASS covers the two source postimages, allocation bound and typed source controls. It does not certify the subsequent native62163 case, successful normal GUI boot, DRIVING/motion, rendered pixels, text layout, natural exit or any debug-site credit. No game was launched, no shared source/ref/index/profile/package was edited, and the original62162 failure remains a failure. Root owns publication, shipping and fresh native attribution.
