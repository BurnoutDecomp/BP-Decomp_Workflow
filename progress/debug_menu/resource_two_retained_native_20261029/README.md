# Two retained Resource D12 sites

**Approved dispositions:** `CgsResource::DebugComponent::InitWindows#0003` (Heap Window) and `#0010` (Bundle Window). Both are verified only for the retained private D12 candidate (source00830, slot62144/PID21792).

Root checked 48 typed raw triplets, 33 captured-frame hashes with unique owner ACKs, and ten same-run restores, then inspected five actual frames. The retained outer D12 postcheck/phase-stop remains FAIL/incomplete. The separate D13 concurrency failure remains separate. No whole-suite or current normal-build result is claimed.

## Heap Window

The sampled selector transition `<none> -> OpenWorldGr -> <none>` opens and removes the original heap window. The reviewed frame shows 6,432 used and 2,068 free resources, size/used/free/fragmentation labels, and two colored MM/PY heap maps. This does not establish exhaustive accounting, zoom, or scroll behavior.

## Bundle Window

SET true/false and INCREMENT/DECREMENT reach the original change callback, add/remove the base-only blank Bundle Files window, and restore FALSE. The original constructor installs vtable `0x820CE014` at member `0x4DE8`; render slot `+4` targets base `Window::Render` (`0x82828F20`). The original has no listing override.

## Limits and counts

Hist/Type are visually obscured and the remaining 21 Resource sites stay pending. No current-build, full-menu, numeric-domain, exhaustive-resource-accounting, or hardware certification is implied. The installed normal executable remains 58d; the newer cf7 build remains private.

Canonical totals move from 111 verified / 28 original no-ops / 1,216 pending to **113 / 28 / 1,214**. The 141/1,355 final site dispositions do not measure full implementation.

## Preserved evidence

- Root decision: `ROOT_DECISION.json` (SHA-256 `dbddf9e6dd6bbad4601dd155ec7b0d3becc123ff30d3326c7a806df9b3b069e8`).
- Raw review: `RAW_REVIEW.json` (SHA-256 `ccff48dd25a08f45bad2a0cda7ba5268dfb2f8957cef03831d56bc696838a558`); frame pixels and raw execution logs remain at their source locations and are not copied here.
- Five immutable peer proofs are copied under `peer_proofs/`; their original paths and hashes are recorded in `PEER_PROOF_MANIFEST.json`.
