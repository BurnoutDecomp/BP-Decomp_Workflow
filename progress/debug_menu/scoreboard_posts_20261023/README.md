# Scoreboard channel-40 record posts

This source-only proposal is based on B5 commit `e306dbd2a266a53b77cfb8ccbc86e01726dc5395`. It changes five live call sites across three translation units: the index, variation, and table requests in `OnlineScoreboards::HandleLeaderboardRequestState`, plus two gamercard requests in the table UI and CrashNav map.

These event objects already contain the exact ARTIST channel-40 records: `{4,111,12}+4`, `{4,112,12}+4`, `{4,113,12}+4`, and `{16,120,12}+16`. The current generic PC template queues each whole object on its inner event id (111/112/113/120), which misses the flow-output drain’s channel-40 path. The patch queues the same bytes and size under channel 40, without adding another wrapper.

The real receiver path is already present. The channel-40 drain unwraps each record and sends the typed events through the GUI output queue; `GameBridgeGUIToX` handles 111/112/113 as category/index/variation/table requests and 120 as a gamercard request. A separate event-120 producer in `BrnOnlineGameRoomPlayerInfo_wN3_03.cpp` already queues a channel-40 record and is unchanged. The event-121 score-target post is inside the current source’s literal-false gate, so it is excluded from the five live posts and from this patch.

The exact patch from `e306dbd2` is in [proposal.patch](proposal.patch); full source postimages are under [composed_postimage](composed_postimage/). [site_map.tsv](site_map.tsv) records the five source and ARTIST caller sites, while [artist_scoreboard_wires.tsv](artist_scoreboard_wires.tsv) and [bindings.json](bindings.json) bind the wire dimensions, original exports, DecFIGS types, and receiver cases.

No production files, shared publisher, GUI module, decoder, 508/509 path, refs, index, or campaign inventory were changed. No compile, test, CI, native/game, Stage, Run, or input action was performed; this is source-only evidence.
