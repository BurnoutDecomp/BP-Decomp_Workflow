# Source self-review

Primary821F0EC8 is the u32 insertion contract: r3=this, r4=value, unsigned mode comparisons, literal `%u`/`0x%X`, reload after AppendFormat and clear only a live HEXONCE mode. The decompiler's extra r5..r7 parameters are vararg residue; the assembly and DecFIGS uint32_t overload agree on one explicit value. The source keeps the existing per-thread print-mode reference while recovering those original decisions.

The pointer body is attested inlined at828E0A90..AC and declared asvoid* by DecFIGS h625. It changes the stream mode temporarily and restores the saved mode after inserting a u32 address. The current implementation already projected pointers tou32, so that width behavior is retained rather than introduced here. Both actual overloads remain in their canonical CPP, with no synthetic Entry-only formatter or raw-offset field access.

Replacing just the two proposed bodies with their exact preimage text reproduces the entire source2ce file. No header, field, vtable, thread leaf, source mount or other formatting body changes. No compilation or runtime behavior is claimed; Root owns source review and all integration gates.
