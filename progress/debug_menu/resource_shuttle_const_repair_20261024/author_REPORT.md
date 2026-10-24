# Resource shuttle source repair

The hosted resource candidate40113375770 fails before its 14 numeric checks. The runner selects the two-input partial dispatcher, while the fixture calls the complete four-input dispatcher. Four fixture declarations also dropped the production input const qualifiers. The production response forwarder itself takes a const pool output and currently calls a non-const pointer helper.

The proposal selects the genuine const four-input dispatcher, matches the fixture parameter declarations, and makes the existing read-only pool-output helper accept const in its declaration and definition. That helper already obtains a const queue and only reads the supplied output. Mutable callers can pass their output unchanged. No const_cast, substitute provider, event change or additional dispatch is added.

All original test inputs, all 14 checks, fake boundaries, failure behavior, source/provider lists, and production method bodies remain unchanged. This is not a runtime pass. Hosted compilation, all selected gates and independent source review remain required. The normal game package is untouched.
