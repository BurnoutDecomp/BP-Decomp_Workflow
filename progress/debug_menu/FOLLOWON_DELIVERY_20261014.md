# Follow-on delivery

The normal executable is delivered from clean, pushed **`ac3f202d6`**, SHA256
`6a6ff89b5e76678414dd679c9846c0c57715e7368cee2288fa7892a13c6dea5b`.
All 2,974 shipping TUs compile and link. Start/GPU/Traffic cases pass 34 checks;
Road Rules login/save/cold-restart cases pass 26 more. All have zero assertions
and exceptions. Normal user profiles, configuration and logs retain their hashes
and modification times through the isolated tests.

Actual frame inspection caught the earlier5ad magenta regression despite its
passing automated checks. TextureState copied parameter bytes where restored
readers expected the SDK's packed runtime state. It now invokes the canonical
SDK producer; the Font caller initializes the five flags that producer reads.
The native fixture passes 16 checks, while exact5ad fails five with SDK-green
versus production-magenta pixels. Inspected normal GPU/Traffic/Road Rules frames
show the corruption repaired. The old failure and baseline/depth comparisons
remain preserved.

Four Traffic Stats sites now receive final verified verdicts: active parameters,
free parameters, purgatory parameters and active hulls. Their actual 56 reads
span 14 phases, include four nonempty-purgatory phases and end at 0/400/0/0.
Totals are **35 verified, 7 original no-ops, 1,313 pending / 1,355 static sites**.
The complete 108-site Traffic page remains partial.

Road Rules had a separate late-login reset bug: missing native service config
was parsed as the current epoch, triggering the original score-reset policy.
The PC boundary now omits reset-info only when the key is absent/empty. Actual
saved Time3933/Silver/Driver Details1/64 and Showtime16550 survive login,
completed saves and cold restart with epoch1791996687 and other progression
retained. No newly earned Showtime medal is claimed. See
[the fix receipt](../road_rules_persistence_20261014.md).

The next 40-path GameState/Pool/ImmediateMode/Traffic source integration is pushed
separately at `599809110`. Its first full build finds two integration issues:
an unmounted online Flyby TU and a VehicleList class/struct declaration mismatch.
Root is repairing those; original full startup remains unactivated. Pool's four
earlier findings are repaired and pass source review plus 41 focused checks.
Selected GameState debug consumers and 23 Traffic reader sites continue in
parallel source branches.

Earlier C4661 warnings were described incorrectly as missing bodies. They arose
from cross-TU whole-class instantiation requests and an unattested overload.
ImmediateMode's separate checkpoint fixes their ownership; the delivered AC3
build still records eight warnings. Original logs/reviews remain immutable.

Exact source/build/run hashes, reviews and visual receipts are in
[the delivery receipt](native_delivery_20261014.json).
