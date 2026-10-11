# Native Plant Diagnostics, Round 9

Checkpoint at 2026-10-11 23:23 Shanghai, before the formal R8 cutoff.
No new plant rendering candidate is accepted. The existing R8 root/sprout
failures remain failures, and production BP/RP assets are unchanged.
Later capability probes, startup failures and final restoration are recorded
in `docs/BUILTIN_PLANT_CAPABILITY_R9.md`. This document retains the original
23:23 checkpoint and its immutable report hashes.

## Owned Runtime And Calibration

The R9 worktree is `.runtime/r9-snow`, branch `codex/r9-snow`, based on
`c249b23`. Its owner is `p0-snow-r9`; the session is
`dc4e2d971694496a98eed39eb01ccdca`, game PID 46460, identity
`134362042163509708`. NEMC is 3.9.0.401155, runtime 1.21.120.0.

All evidence below is retained under:

`C:/Users/Happy2018new/.pyreact-debug/instances/dc4e2d971694496a98eed39eb01ccdca/artifacts/`

`snow-camera-r9-v1-skyward.json` completed, restored and passed at common
vertical FOV 66.6. Reported FOV remains 60. The native stone cube was measured
from the complete eight-corner hull in front, right and tilted views. Original
PNGs and outline comparisons remain preserved. The tilted outline comparison
was opened during the evidence audit.

Report SHA256:
`87719fe09609e080a9cb5613f634d1736db2d4c97a0a571f64a0f4f1376355ca`

## Isolated Native Boxes

`tools/verify_native_plant_boxes.py` queries documented server/client
`GetBlockClip` and `GetBlockCollision`. It does not install the projection
probe or allocate any mesh/actor/entity. It reads dry and covered h0 states for
nine plants at eight declared cells: short grass, fern, poppy, torchflower,
crimson roots, warped roots, nether sprouts, crimson fungus and warped fungus.

The new world's player origin is `(0,64,0)`. Fixed offsets are
`(6,24,6)`, `(7,24,6)`, `(6,24,7)`, `(7,24,7)`, `(8,24,6)`, `(6,25,6)`,
`(6,40,6)` and `(-6,24,-6)`. The resulting 72 rows have matching server/client
clip boxes. The checked second run verifies native dry readback, successful
snow placement, exact `{height:0, covered_bit:true}` state, and the correct
plant in the client's extra layer. All eight fixtures, player positions,
biomes, world time and daylight rules were restored; sources stayed stable.

Grass/fern clip boxes vary on X/Z and Y. Poppy, torchflower, roots and sprouts
vary on X/Z; fungi remain centered. The same X/Z at Y88, Y89 and Y104 gives
the same relative box in these samples. These are independent box clues only.
A selection-box centroid is not a proven mesh pivot, an asymmetric default
box is possible, and no native geometry or random-offset contract is accepted.

At `(6,88,6)`, grass/fern clip min is approximately
`(6.0166664,87.800003,6.1500001)`, max
`(6.8166666,88.600006,6.9500003)`. Poppy, torchflower and roots min is
`(6.0666666,88,6.2000003)`, max `(6.6166663,88.599998,6.75)`.
Sprout max is `(6.7666664,88.300003,6.9000001)`.
Fungi have centered X/Z bounds `[6.27,6.73]`; crimson top is 88.75 and warped
top is 88.58. Full raw values are retained, not rounded in the reports.

Original report: `native-plant-boxes-r9-v1.json`, SHA256
`02701223fe377cea28729380449666610ab2f05eda4c751a88241d925500596c`.

Checked report: `native-plant-boxes-r9-v2-checked.json`, SHA256
`8ac66f6f562c90bfaaf16bb4517ec81e8327be98e0727f447e991a4545515a89`.

The tool now registers pending cleanup before setup and checks for the saved
fixture marker when setup fails. Focused host tests prove partial setup
restoration, absent-fixture nonmutation, and rejection of stale extra-layer
replication. All three tests pass via
`python -X utf8 tests/test_native_plant_boxes_tool.py`.

## Four Unmodified Mesh Sources

`tools/verify_native_plant_mesh_paths.py` reuses the established direct-seed
mesh generation and actor attachment contract. It compares dry native plants
at the original R8 public cell `(-47,117,-70)` and original public/right camera
offsets against four engine paths: `direct_world`, `direct_palette`,
`captured_palette` and `roundtrip`. No fitted offset or mesh edit is applied.

The stone positive control has object recall/precision 1.0/1.0 in both views
for all four paths. Overall stone verdicts remain false because the fixed
plant ROI clips the cube. The ROI-boundary gate was preserved.

Crimson roots fails every path with identical per-view masks:

| View | Native Pixels | Mesh Difference Pixels | Object Recall | Object Precision | ROI Boundary |
| --- | --- | --- | --- | --- | --- |
| Public | 36,928 | 3,065 | .0039807 | .1030995 | Pass |
| Right | 32,358 | 2,100 | .0261141 | .4290476 | Fail |

Original native/direct-world PNGs and the derived inspection sheet were
opened. Native roots are clearly visible; the mesh frames contain support
and sky with no visible roots. Nonzero difference pixels are support or
background differences. This is source-path diagnosis, not the independent
exposed-plant acceptance oracle. No h0 extension or remaining-height matrix
was started. Recall/precision gates stay .75/.75, edge tolerance stays 3px,
and no editor/full/missing acceptance claim is made.

`native-plant-four-mesh-paths-r9-v1.json` completed and restored, with no
cleanup errors and stable capture-time source. Its overall verdict is false.

Report SHA256:
`040cdfd4f55fe8e03dab60d6f75205e7fada755ad0b91297e44c2ded9a3229e4`

Frozen source: `native-plant-four-mesh-paths-r9-v1_source.json`, SHA256
`d0194f24fa72ac7f072dbaff8e97e6ec1024773a5fdf8205f79686c4eaf06a90`.
The report also preserves capture-time hashes of the diagnostic tool itself.
Subsequent host-tool safety changes are not edits to this original report.

## Background Evidence Audit

`tools/audit_native_plant_diagnostics.py` verifies original report-linked
hashes, masks, source freeze and the existing guarded background capture
contract. `native-plant-diagnostic-audit-r9-v1.json` passes integrity for 46
unique native PNGs and 71 hashed artifacts. Every PNG is fresh, reliable,
nonblank, owner/session-bound and native-resolution; the owned game stays
background before and after capture. One switch between other applications
is retained as an allowed diagnostic. Failed mesh verdicts remain false.

Audit SHA256:
`79d2e221ae29a40cb9b8a562e94c2db14cca0a9f81b89a1dc3e5cd4fc722e356`

Inspection-only sheet:
`native-plant-four-mesh-paths-r9-v1_inspection.png`, SHA256
`f736718ca929cdace6e88fc3a73624dfa54990e1d6f1e1935c86d5acc434898d`.

The process was observed around 818-832 handles and 2.57-2.74 GB private memory
with automatic hot reload disabled. This is a diagnostic observation, not a
resource-limit acceptance or a causal explanation of historic handle growth.

## Remaining Work

No authoritative plant mesh/jitter contract is established. The next bounded
probe is cold-start support for documented `minecraft:geometry.cross` and
`minecraft:random_offset` in this runtime, with experimental assets kept
isolated and rejected bytes preserved. Documentation does not establish
the native hash or whether NEMC parses these components. Roots/sprouts,
flowers, grass/fern, torchflower and high-coordinate acceptance remain open.
Automatic snow-first erasure and explicit-layer independence remain required.

At the 23:23 checkpoint the owned game remained ready and all completed
fixtures were restored. Later R9 fixtures and resources are also restored;
owned games/MCDK are stopped, as recorded in the capability checkpoint.
Cleanup finished before 06:30 Shanghai on 2026-10-12, before parent integration
and 07:00 hibernation.
