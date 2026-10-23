# Native repair checkpoint

Road Rage count and countdown acceptance is retained separately in `../road_rage_output_retirement_20261023/countdown_native/`.

On af18, the original GUI saves a new custom route, then overwrites that slot after moving one checkpoint. Both natural autosave requests complete and read back count1 with the expected payload; the original owned game exits0. Root inspected the empty Save, overwrite question and final route frames.

Cold launch B FAILS: the saved-route list never opens, and later inputs select the default route. The script mark named saved_route_list_visible was only a fixed-sleep mark. Its trace comparison catches the mismatch; the pair remains FAIL. No full persistence claim is made.

On exact hosted AA6, the original one-player host leave request reaches network departure, CNONLLVGGAME completion and IGO_WAIT exit. Two later original frames show offline world/HUD without Leaving. There are zero assertions/exceptions and the owned game exits0. Joined-peer departure is untested.

Original receipts are retained. Compact copies omit the multi-megabyte writer_lines arrays only; INPUTS.json pins originals, private profile outputs and viewed BMPs. Source review, native supporting-flow checks and debug-control dispositions stay distinct.
