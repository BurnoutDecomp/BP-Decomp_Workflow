# Review shipping math type correction

Base829305f8 and full pre/post/diff are pinned in BINDING.json. Hosted40026988508 compiled4/cached2997/failed1; Traffic used constructors from SDK mirror rather than actual canonical vendor headers. No executable or native success is claimed.

Review the actual include order: vendor/renderware/include/rw/math/vpu/types.h defines aggregateVector4 and Matrix44Affine's fourVector3 rows. GlobalVecFloat is the existingVector4 broadcast alias; confirm that alias from BrnCommonTypes. The vendorCross operation is ordinary xyz with W=0, and Mult(Vector3,Vector4) multiplies all four lanes. The delta broadcasts original width/height to all four lanes and writes named affine rows instead of unavailable constructors. Position subtracts the existing all-lane up*height vector; it does not replace zero-times-height with literalzero. No new normalization, clamps, gates, allocation or call order. Check matrixWlanes and width/height against the original raw-bound matrix decode packet and prior traffic review.

Do not edit vendor math types or include order to make this callsite compile. No local compilation or test was run. Return source verdict only; a fresh hosted build is required.
