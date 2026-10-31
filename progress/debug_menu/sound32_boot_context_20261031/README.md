# Sound32: early activation failure retained

The first private Sound32 run stopped at BOOT after19s, with zero target phases
and zero captures. Its Sound config entry activated the page before the RWAC
system existed. The original Sound update calls the audition update, which
requires that system even when audition is off: `mpSystem` asserts, then the
system lock reads null. [State and source hashes](STATE.json).

This exposes a PC config autoactivation dependency. It is not an original broken
menu-row disposition, and no speculative guard was added to the original body.
The supporting PC startup issue remains open.

The next test will activate Sound through the original script path after actual
RWAC LIVE, profile loading, car-selection exit and motion. Its Console table has
a real null sentinel, so a numeric2 setter takes the original conversion/callback
path and installs logging. Console2 is an explicit test precondition, kept
read-only during the32 target phases; no prior0 restore claim is made.

The original failed report, cleanup and normal-file preservation receipts remain
unchanged. The private profile was restored, but this failed run did not prove
profile loading. The lossless [archive](ARCHIVE.json) contains the failed run,
static inputs and crash image, excluding save bytes. No new site credit.
