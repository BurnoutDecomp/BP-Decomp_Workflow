# Replay GameModule serialiser link integration

The exact c1b0e7ef source compiles 3,001 translation units without a compile failure,
then fails to link the original GameModuleSerialiser::Construct. Its implementation
already exists but was omitted from the shipping source list.

The sole build change mounts that implementation beside DirectorBridgeSerialiser.
Its existing tail call agrees with ARTIST 8264C6A0: channel 5, flags 0, both buffer
sizes 0x400, GameModule name, final flag 0. No source body or normal package changes.

Root mechanical review: PASS. A fresh hosted link is still required. This records
no Replay runtime or debug behavior completion.
