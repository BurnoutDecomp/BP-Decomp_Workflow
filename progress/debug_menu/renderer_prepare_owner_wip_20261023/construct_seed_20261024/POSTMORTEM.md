# Source self-review

The primary value is proven from actual register flow, not decompiler initial values: r29=1 at8240BB9C, then only source-operand stores/callee-preserved use until stb r29,4(r31) at8240BF90. The owning Module bool is selected by declaration shape and original base Construct/Prepare consumers; no literal-offset access is added to C++.

The store is placed at the current Construct's normal completion after its original initialization and retained PC-only diagnostics. Existing allocation-failure early returns stay unchanged. It does not mark any prepare stage complete, skip a required resource, create buffers, call original Prepare or register a component. The constructor's current differing allocation policy/order remains a disclosed native integration boundary.

Removing the one added payload reproduces the full exact source702 CPP byte for byte. No preexisting field, method, constant, allocation, sky-dome or thread-owner byte changes. The original field can alter inherited lifecycle dispatch when this source is composed, which is intended and requires fresh review. Source recovery is not native readiness evidence.
