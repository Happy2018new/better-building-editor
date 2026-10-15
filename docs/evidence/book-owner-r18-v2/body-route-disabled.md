# Default Table Body Candidate Disabled

The table body candidate is disabled independently of the book companion.
`projection/static_table_data.py` now has `PRODUCT_QUALIFIED=False`, and
`static_table.table_proxy` returns no proxy while that gate is closed.
Default palette and missing-context preparation therefore retain the native
enchanting-table identity, actor data, and background layer.

The independent flag does not read or reuse the book qualification gate.
Diagnostic tools can explicitly set `static_table.CANDIDATE_ENABLED=True`;
book candidate setup saves its prior value and restores it with the profile.
Ordinary default-profile capture does not perform that override. Generated
table resources also emit the closed flag, so regeneration cannot silently
enable this known-defective candidate.

This is a routing fallback, not a rendering repair or native qualification.
The native body's previously observed 0.125-block Combine offset remains an
open defect. The disabled candidate's occupied bottom and side residue also
remain unresolved. No shader/context behavior, geometry, engine version,
native texture, or model registration was changed to close this route.

Focused validation after the change:

- Five static-table tests passed, covering native default routing and actor
  preservation, independent body enablement, explicit candidate routing,
  source validation, hidden proxy assets, and the generated-data contract.
- All 34 book tests and three inset-boundary tests passed. The expected
  missing-book-model failure-path traceback is part of the passing book suite.
- Changed Python files compile and the scoped whitespace check passes.
- A fresh resource generation reproduced the checked-in closed data module
  byte-for-byte; its SHA256 is
  `70abfb0a8e26ddf3469e79c309f98e24531849222d98bd5d5e8c80b181a7c538`.
- `body-disabled-qualification-check.json` records all four enabled bundles
  (cauldron, banner, portal, spawner) still verified. Books remain disabled,
  and the verifier explicitly claims no pixel acceptance.

No Minecraft instance was started for this routing change. This validation
does not claim a new native visual result for the fallback.
