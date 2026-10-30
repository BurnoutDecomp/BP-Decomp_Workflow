# Corrected SatNav witness parser

Use this parser with the unchanged, reviewed temporary v2 old/fixed instrumentation patches and formatter. B5 remains pinned to 3f4f9c06. The v2 parser failure and review are preserved here and all v2 files remain unchanged.

The native log records examined in the baseline start at column one. Every line containing `[satnav-event-witness` must be exactly one complete witness record, with no prefix, extra marker or suffix; only CR/LF terminators are removed. Other lines without the marker are ignored. Unexpected logging prefixes are rejected rather than guessed. Within-run FIFO pairing, duplicate-prefix tail ambiguity, missing records and the 3000-record cap retain v2's conservative rules.

Run `python pair_witness.py ONE_RUN_LOG` separately for each run; nonzero exit means pairing or coverage is invalid. Tail mismatches are recorded separately in the JSON result. Verify scene coverage, timing, capture correlation and logging perturbation independently. Never compare pointer values across runs.

`python pair_test.py` exercises the review's concrete combined-two-senders and trailing-junk fixtures, an unexpected-prefix fixture, CRLF records and the earlier FIFO, ambiguity, missing and cap cases. parser_test_receipt.txt additionally records the old parser incorrectly returning success and this parser returning failure for both original counterexamples. receipt.json records input hashes. No game launch was performed.
