# Font contract and workflow binding repair

Run40549542681 compiled and linked the combined candidate, completed the selected build/regression step and the circle/screenshot/gameplay steps, then failed before font/Buddy execution because its workflow still expected the previous contract hash. The run remains FAIL. The new contract and all20 unchanged font/Buddy definitions had already passed independent composition review.

Replace only that one64-character workflow SHA256 with the exact reviewed source-contract hash. No source, fixture, expected value, old control, input selector or check is disabled. A new run is required; no result from the failed font step is claimed. Original metadata and complete failed-step output remain in the scratch publication record. The playable build is unchanged.
