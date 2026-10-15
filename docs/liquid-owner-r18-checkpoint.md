# Product Water Owner R18 Checkpoint

The product owner is implemented, but product water remains disabled.
`liquid_product_qualification_data.PRODUCT_QUALIFIED` is still `False`.
No qualification command, commit, or push was performed.

The current product profile selects `ProductLiquidProjection`, which selects
`ProductWorldLiquidRenderer`. The renderer creates at most one new model per
frame and uses a product-only bounding box of +/-4. Shared owners retain their
legacy +/-2 default. Shared world wiring consumes `profile.projection_factory`.

The dedicated copy `D:/bbe-r18-water-production` was synchronized with the
complete projection Python directory before the final cold launch. Frozen v6
contract is `4c2309a150fcffed31a45504ef77c80404e007f698b8857b9a3e0a832af74678`.
The old mixed-copy synchronous `b.project()` list-assignment error did not
recur after synchronization, but no full traceback identified its cause.
Candidate success does not qualify the closed production-default entry.

| Fixed Work Item | Implementation / Effective Evidence | Missing Check Or Known Failure |
| --- | --- | --- |
| Dedicated product owner and factory isolation | Implemented; 24 focused tests pass; owner contract generator check passes | Final default-entry integration still unqualified |
| Distant x=63 world visibility | Cold product +/-4 visible; changing only bounds to +/-2 removes pixels; default bounds restored after near/return | Narrow fixture result, not the complete matrix |
| Frame and cleanup policy | One create/frame; final cold owner types checked; active/staging/retired all zero on close | Configured 256-group stress not established |
| Frozen public 19-case matrix | 57 route-case pairs, 162 rows, 348 captures; completed/restored/source unchanged | Editor pixels fail despite ready controls |
| Full/missing geometry and alpha | Core and supplement geometry, applicable visibility, and alpha checks pass | Side UV south .8143/east .6827 below .85 |
| CPU budget and stop lifecycle | Four methods pass each report; all 108 stop lifecycle readbacks pass | Candidate fixtures only, not final default path |
| Biome tint and occupancy | Existing probe supports frozen return and occupancy mutation/restore | Final owner run not performed |
| Animated physical flow | Existing pinned burst helper and analyzer available | Five flow/falling cases across all routes not performed |
| Reverse neighbors | Existing reverse-view probe available | Five neighbor/overlap cases across all routes not performed |
| Public gallery | Existing gallery fixture and normal editor entry available | Final owner gallery capture not performed |
| Production default | Closed by design while qualification is incomplete | Must cold-start without candidate assignment after isolated acceptance |
| Final qualification | Source/resource hashing and analyzers available | Explicit review and all gates required; no gate was opened |

The new first task is a single editor positive-control diagnostic, rather than
a full rerun: read actual PaperDoll model IDs, native visible state, depth and
layout, and compare with a matched hidden control. `editor_pool_wet` currently
has eight ready groups and bank `[false,true]` with product frozen model names,
but its screenshot shows only the native stone fixture. Keep that failure
distinct from the world-side UV numeric threshold failures.

Evidence is durable in:

- `docs/evidence/liquid-owner-r18-bounds-v1/README.md`: 44 native captures,
  exact +/-2 versus +/-4 controls, near/return with camera correction.
- `docs/evidence/liquid-owner-r18-matrix-v1/README.md`: all 348 matrix PNGs,
  raw reports, both analysis families, the 3011-file cold source archive,
  representative pool contact sheet, and an offline verifier.

All water test instances are stopped. Final session
`a06f540e21c1466b803d28e2b676a01c`, game PID 19636, MCDK PID 52380 was reclaimed
after state restoration. The water copy was not updated after its v6 freeze.
