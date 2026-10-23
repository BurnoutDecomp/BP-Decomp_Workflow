Traffic producer source byte-normalization addendum

This is metadata only; the original source review and its verdict remain unchanged.

The proposal packet's preimage file has SHA-256 `AE18398E0A6856F552056D961B471B3BCB81E107A2F0E6EBA48BF88860F62EFE` and uses CRLF on all 1,642 line endings. The private e8e4918 source file has SHA-256 `DB3B7AE2F2009526041BA896E469C428C28F3843012F1405A55B0A4EFCF697B7`, 1,642 LF line endings and no CRLF. Replacing each CRLF in the packet preimage with LF produces byte-for-byte equality with the e8e4918 source file. This is a newline-only representation difference; it does not change the source review finding.

The packet postimage hash remains SHA-256 `22D0B153B45F54362F9D213BBC4C63DA4CA7D155DF9E9DFDBF51C6F8739C8790` for the raw packet file. Root's integration preflight confirmed the composed source preserves the repository's LF convention.
