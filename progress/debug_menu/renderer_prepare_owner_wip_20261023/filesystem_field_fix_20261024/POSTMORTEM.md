# F1 self-review

The author misread an untyped pseudocode store as a count reset. The earlier sealed packet is preserved; this exact785 delta corrects that interpretation.

| Evidence | Mapping |
|---|---|
| ARTIST829033FC | First file's lock is FileSystem+0x438; the first File begins after the1024-byte prefix at+0x400. |
|82903464–6C | File stride0x180, sixteen files: end of file array+0x1C00. |
| DecFIGS FileSystem.h249–252 | Prefix1024, File[16], system buffer20480, then bool mbPrepared. The buffer ends at+0x6C00. |
|82903470–7C | First stream's owner field is+0x6C28; its own block pointer is that address minus0x20, so stream base+0x6C08. |
|829034A4–B0 | Eight stream records, stride0x5A0: stream extent ends at+0x9908. This is the later u32 used-stream count, followed by allocator+0x990C/debug+0x9910/log+0x9914/layout+0x9918. |
|82903664 | One byte store of zero at+0x6C00. It writes mbPrepared=false, not the later count. |
|82903668–6C | Separate pointer-width target store of the supplied DiskLayout at+0x9918; this remains unchanged. |

The candidate removes the incorrect count store and adds only the correct bool store. It does not add both. Every byte outside the original four-input Construct is unchanged, including native no-argument Construct's existing count reset and all Prepare/Release/Destruct bodies.

`build_proposal.py` verifies a whole-TU reverse replacement against the exact Git preimage and records both full hashes. This is source integrity verification, not a C++ compile or gameplay test. Root reports the completed original-batch review has no other changed-path blocker; fresh correction review remains pending.
