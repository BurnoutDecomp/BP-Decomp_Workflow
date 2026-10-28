# Binding revision01

This supersedes the original packet for review. The original sealed directory is untouched.

The original prose joined the label `b5` to the valid40-character source commit, creating the invalid token `b599c...`. Structured records and compile commands already selected `99c668c13ed446691dd9b8dababdb676d4470b9e`. The report and its prose generator now separate the repository label from the commit.

The original compile receipt patch hash `bc1a451e...` is not an unidentified source candidate: it matches exactly the canonical patch with LF converted to CRLF. The later sealed LF artifact is `dcb38cbe...`. The compiler never consumes the unified patch; its actual C++ input still hashes `5b602957...` and the retained compiled object still hashes `0627e61b...`, exactly as the original receipt records. The revised receipt binds the canonical reviewed patch and separately preserves the original compile-time patch hash and this relationship.

Full hashes and byte-level proof are in BINDING_PROVENANCE.json. provenance/ contains the untouched original receipt/report/manifest/seal, reconstructed exact compile-time CRLF patch, and unchanged compiled object. No source edit, new source patch, build, fixture run, game or native-evidence change occurred. Existing source/native/fixture evidence is byte-identical. Independent source review remains pending; this is still diagnostic-only.
