# Temporary SatNav witness v4 — not shipping

The only instrumentation change from reviewed v2 patches is the per-side maximum of 20,000 records, replacing 3,000 in two places. Exact formatter, raw bytes, tuple shape and production source remain unchanged. This reduces premature cap exhaustion during the paired drive; it does not relax the 48 MiB log limit. Both patches require separate scratch diagnostic builds and must not ship.

The v4 parser preserves v3 line anchoring, FIFO and ambiguity behavior, and requires explicit `--cap 20000`. Counts of 20,000 or more per side invalidate coverage; 19,999 is accepted. Reproduce with `python pair_test.py` and `python pair_witness.py --cap 20000 ONE_RUN_LOG`; missing or another cap is rejected. RECEIPT.json records tests and input hashes. V2 and V3 remain unchanged; no live gameplay was run.
