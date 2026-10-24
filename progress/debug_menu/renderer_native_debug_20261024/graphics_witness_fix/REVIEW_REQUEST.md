Review this separate one-path correction against exact55eaf3b09ff617604503c801732619d19f14d7fc. The original frozen startup packet remains immutable.

Verify the private-access defect is removed without changing visibility/friendship; the exact raw getter's concrete return object at both sites; the related-base conversion; publication after wrapper initialization; actual object/arena lifetime; and both existing GetLinearHeapBase implementations returning/delegating the backing's own Resource reference. Confirm the address comparison proves exact backing ownership and retains substantive null/capacity checks.

No compilation, successful build, registration or runtime/site credit is claimed. Root owns fresh review, composition and validation.
