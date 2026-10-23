# Route-transfer self-review

ARTIST82507448 pins this/cache/params in r3/r4/r5 and round stride44 vs saved stride144. Each live landmark is read by Event::GetLandmark, resolved through GetLandmarkInfoFromIndex, and its full64bit ID is copied. The light-trigger lookup824F8838 returns junction word+14. Round event ID is read after lookup and the landmark count before it, as in the source. No new bound/null guard or identity truncation is introduced.

ARTIST82507570 reverses stable IDs through GetLandmarkInfoFromID; its halfword+20 is returned as the typed LandmarkIndex. Lookup824F8988 resolves junction to light-trigger word+10. Existing Event::Construct receives eventID, light-trigger, landmark array and count in original order. Three existing declared accessors receive inline bodies matching the saved event+80/+84/+88 loads; DecFIGS names/types/const agree.

The two transfer tails copy exactly ten fields in original load/store order. Previous mode, security and ranked remain outside this format. No record-size or persistent format change is made.

ARTIST824FF7AC..824FF868 initializes ten events in each of twenty saved slots: only eventID, junction and count are zeroed; landmark arrays remain untouched. Defaults are mode10, rounds1, class9, crashes3, boost/choice/time0 and three bools true. The existing DWARF-declared OnlineSaveRoute::Construct provides this inlined helper; original824FF86C/870 clear the two counts. Existing table layout/stride is retained. Header field shapes and six signatures match DecFIGS. No Feb2007 source used.

Hosted compile, independent source review, focused actual-body tests and native GUI save/overwrite/reload remain pending. The supplied user crash matches the installed image int3 at the same reported RVA; the other PC exact commit is not logged and is not inferred.
