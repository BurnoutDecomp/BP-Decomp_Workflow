# Replay private composition hosted checkpoint

The exact source c1b0e7ef and workflow d27c8ceb pass hosted run
39864612826 on Windows 2022 with four compiler jobs. All 3,002 selected
translation units compile, the executable links, and nine requested regression
groups pass. Root checked 65 input paths against the exact Git objects and all
twelve downloaded output hashes. Existing compiler warnings remain in the X360
input-device handle conversion; there are no compile or link errors.

The old TextFormat setter failure control still fails its 57 checks as intended;
the recovered setter passes all 78. RWAC capacity passes 16,427 checks and six
first-pass checks, with the retained original-source control failing six checks.
These focused checks establish neither long-session audio stability nor Replay
behavior. Eleven explicitly expected failing regression-driver commands remain
recorded as such, rather than being misreported as unexpected build failures.

The active PC frame loop still needs the original GUI model pre-world output and
the Replay output consumers. Recording/playback behavior has not been run. The
normal playable package remains the separately accepted 91a0ed56 build, and no
debug-site disposition is added by this supporting build checkpoint.
