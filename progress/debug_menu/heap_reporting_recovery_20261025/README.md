Recover allocation reports

The old trace function discarded its callback and the game log sink was empty. This batch restores original live-report traversal, chunk text, byte previews, the default Windows sink and the GLOBAL-filtered game-log callback. It reuses the actual allocator report engine and retains both original newlines.

Independent review passes after correcting the one-byte, no-delimiter buffer behavior; the failed proposal remains preserved. Native address formatting follows the 64-bit vendor reference. Invalid short-buffer cases have explicit bounded PC adaptations. Only CRLF-to-LF normalization rebinds the sink postimages. Hosted and native checks are pending; the original arena and normal build are unchanged.
