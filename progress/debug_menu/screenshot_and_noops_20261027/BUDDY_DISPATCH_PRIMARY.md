# Buddy dispatch correction and explicit original drop paths

F002 repairs the real shared consumer reached by selected `BuddyManagerDebugComponent::OnActivate#0008` (Join Buddy). It does not translate the caption into a new game-join behavior.

The original callback `JoinBuddy@825949F8` copies the selected real16-byte `PlayerName` and appends tag12/size16 to its actual queue. `BuddyManagerBase::ProcessDebugEvents@82554890` reads that queue, calls the real manager's virtual slot`+0x84` at `825548CC..DC`, then clears the same queue at `825548E4` before processing outgoing notifications. The retained original leaf table at **820D0170** has `+0x84=8256C8E0`, the exact `BuddyManagerX360::ProcessNetworkQueue` body.

The leaf iterates the actual queue, retains the original event pointer, and forwards it unchanged in r4 to `ProcessEvent@8256B6C0` (`8256C9B0..BC`). The base switch dispatches:

| Tag | Original slot selection | Actual named virtual | Current source before repair |
|---:|---|---|---|
|9|`8256B7BC/C0`, slot`+0x20`|RevokeInvite|SendInvite(NULL)|
|10|`8256B7A4/A8`, slot`+0x1C`|AcceptInvite|AcceptInvite(NULL)|
|11|`8256B7B0/B4`, slot`+0x28`|DeclineInvite|JoinBuddy(NULL)|
|12|`8256B7C8/CC`, slot`+0x10`|JoinBuddy|CancelInvites()|

`8256B7D0..D8` sets r3 but never overwrites incoming r4 before `bctrl`. The bare leading `PlayerName` is therefore a load-bearing actual argument, not null or omitted. The DecFIGS virtual declarations attest `const PlayerName*` signatures and virtual ordering. The physical table independently pins `+0x10=8288CE30` (Join), `+0x14=8287FDE8` (Send), `+0x18=8287FF18` (Cancel), `+0x1C=8287FF68` (Accept), with the Revoke/Decline slots sharing the original Join/Accept bodies. Exact table bytes/hash and all slots are in `BUDDY_VTABLE_PRIMARY.json`.

The proposed source uses those actual named virtuals and the same typed leading `PlayerName*`; all other cases, queue clearing, allocation, guards and error behavior stay unchanged. In particular no NULL replacement, new event ID/header, fake client success, direct game join or external send is introduced.

The original X360 Join implementation leads through `ShowProfile` to the gamercard interface. The current PC platform implementation/backend remains a separate dependency; this packet does not claim a working PC gamercard, peer session or native result.

Four other selected callbacks have **positive original drop paths**, rather than inferred missing reads:

- Print Next Unread Message posts5.
- Send Test Message posts4, including the exact original fixed200-byte text buffer.
- Leave Feedback posts7.
- Print Message posts3.

For each, the original leaf's only special tags are8/9/11 (buddy-list notification) and13 (profile). Tags3/4/5/7 take its actual default tail into `ProcessEvent`; the original base switch sends those same tags to its explicit default epilogue/BLR (`8256B7DC..F0`). `ProcessDebugEvents` then clears that queue. No platform operation or payload consumer occurs in this complete traversed path. The packet records these as original-noop **candidates requiring independent queue/vtable/path review**, under the normal original successfully activated queue lifetime. Original activation/allocation failures are preserved and are not used as no-op evidence.

`BUDDY_DISPATCH_TABLES_PRIMARY.json` retains the actual address-producing instructions and raw table bytes at `8256B6FC` (12 words) and `8256C950` (6 words). The leaf subtracts 8 and uses an unsigned bounds check, so tags 3/4/5/7 branch directly to `8256C9B0`. The base's actual table maps each of those tags to `8256B7DC`. This proves the selected destinations from original bytes, independently of decompiler case comments.

Send Invite/tag8 is different: the original leaf posts a buddy-list-updated notification. This unusual original behavior is preserved; it is not changed to a caption-inspired direct invite. The selected sliders remain unresolved at their other alias/lifetime frontiers; no no-op is inferred for a variable merely because one known callback drops its record.
