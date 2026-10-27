# Screenshot run 40502046827 retained-data review

**VERDICT: pass — hosted-data acceptance only.** I independently checked the retained run files, source/Git bindings, generated inputs, and owned-job cleanup. This does not credit native screenshot behavior; no game or D3D9 readback was executed.

## Run and source binding

- The run input receipt identifies run `40502046827`, attempt `1`, hosted Windows 2022, workflow `649841a0491cac03e506b8cfc9fefa9da22785e9`, and B5 `1161949b8d049814e2e3bfeeb425861456d27661`. The B5 head equals the parent gitlink, with no override and empty recorded worktree status.
- I joined all **13** screenshot worker source/test input hashes to the exact B5 Git objects after normalizing Windows CRLF to Git LF: **13/13 matched**. I independently matched all **eight** screenshot source-definition hashes in `source_contract.json` to those source definitions.
- The unchanged-source control is bound to `0117424f57852e7244a91c9664a6ac8a48c7b2b3`. Its retained handoff, normal-present terminal, and overlay predicate exactly match the old Git source slices; that source has no `TakeScreenshot` writer definition. The test does not inject a dummy old writer.
- The worker receipt's `candidate_sha_metadata` is null. The run-level input receipt supplies the exact B5 commit, and the worker's source hash joins confirm the compiled source content against it.

## Retained results

- All **21/21** screenshot artifact files listed in `RECEIPT.json` match their recorded sizes and SHA-256 hashes. All **14/14** top-level build outputs match `input-receipt.json`.
- The actual candidate stdout contains 33 checks, 0 failures, exit 0. The unchanged-source stdout contains 33 checks, 20 failures, exit 1. Both ordered check lists and the 20 control failures match the pinned test plan; both stderr files are empty. Result JSONs and executables match their retained hashes.
- The owned worker exited 0 without timeout. Its cleanup receipt reports zero active descendants, closed job/process/stdio handles, and a matching retained worker-log hash.
- The two generated TGA data files are each 30 bytes and have matching contents: an 18-byte 2×2, 24-bit TGA header followed by the fixture's 12 synthetic pixel bytes. They are test-writer data outputs, not captured game pixels.

## Exact boundary

This run accepts the retained source-slice fixture data for the screenshot writer, formatter, request handoff, present order, and overlay predicate. The test simulates the front buffer and verifies generated file bytes. It does not verify native D3D9 locking/readback, actual menu input, actual overlay pixels, a rendered frame, or whole-render concurrency. `native_screenshot_executed` is false and no native or debug-site disposition is requested. The existing eleven-group/circle evidence and prior failed run were left untouched and are outside this review.

No fixture/runner/case/checker was imported or evaluated; no compiler or game was run during this review. The only execution evidence cited above is read from the retained hosted artifacts.
