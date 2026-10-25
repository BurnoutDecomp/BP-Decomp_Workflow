Allocator trace regression checks

Preserve the existing eighteen real allocator checks and add eight trace/format/ownership cases. The candidate must pass all26. The unchanged production control runs22 available checks and must show exactly three callback failures; direct calls to absent formatters are excluded rather than replaced. The separate hosted step fetches the exact control and pins the runner. Existing shipping gates are unchanged. Hosted and native results remain pending.
