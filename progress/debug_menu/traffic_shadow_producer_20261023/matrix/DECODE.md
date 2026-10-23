# Traffic physical blobby-shadow transform

Root assistance for the graphics recovery agent, not an independent review or runtime verdict.

ARTIST export `0x82728B08.json`, SHA-256 `4c16f1cbcf2a36a4459c7432c2622055dff6cc7c922c4bcaf03def0478e5bf61`. Exact assembly excerpts are saved separately.

Use the repository decoder documentation in `tools/re/vmx128.py` and `tools/re/ppcdis.py`: classic `vnmsubfp D,A,B,C` is printed in raw field order and means `D=B-A*C`. Its syntax differs from the phantom fourth operand of some VMX128 fused forms. These two instructions are classic, not fused128.

Let F be original transform row2, loaded at 0x82729374 (or reloaded after the assertion at 0x82729488). Let N be the complete road normal/height vector at PhysicsInfo+0x520. Let S(v) mean the perm63 result `[v.y,v.z,v.x,v.w]`. The physical block stores:

- row1 = N at 0x827294EC.
- row0 = S(F*S(N)-S(F)*N), from 0x827294FC/2950C/29518/29524. Its xyz is Cross(F,N), with ordinary cross convention.
- row2 = S(N*S(row0)-S(N)*row0), from 0x82729528/29530/29534/29538/2953C. Its xyz is Cross(N,row0).
- translation = P-UP*N.w at 0x827294F8/29500/29508/29510. UP is the vector at r28, initialized from 0x82181510.
- height argument is N.w, splatted at 0x827294E8.
- width is BBoxHalfSize.x, loaded at 0x82729544 and splatted at 0x82729550.

No normalization occurs. For F=+Z and N=+Y, row0 is -X under ordinary cross convention; preserve the original signs rather than replacing them with a conventional right-handed basis. Check the actual Cross helper and typed matrix setters, including W-lane behavior, before publishing source. The packed extents decode and traffic gate remain owned by the graphics agent.
