# Native poppy coordinate control R13

This is a native-only diagnostic at four predeclared physical coordinates:
`(6,-48,6)`, `(7,-48,6)`, `(6,-48,7)` and `(-6,-48,-6)`. The three adjacent
cells vary X and Z separately; the fourth observes negative coordinates.
R9 already contains equal-X/Z observations across Y, so this control does
not repeat that dimension. It does not fit a mesh, pivot, translation or
coordinate hash, and cannot enable a production profile.

`tools/run_native_plant_positions.py` reuses the independently reviewed
owned-startup, background WGC, protected-session, handle-health and cleanup
contract. It passes the separate native-only phase from
`tools/verify_native_plant_positions_phase.py`; the ordinary h0 matrix does
not run. The reused frozen plan's status describes the startup contract,
while `native_coordinate_control` and its pinned runner/phase define the
native-only amendment. There are no isolated candidate resources, marker
textures, blueprint/editor changes or virtual projection submissions.

The first frozen V1 plan is
`.runtime/native-plant-positions-r13-v1/plan.json`, SHA256
`5115f2efd574f11a92d7dbf6f55a0878bcb2af3c102593ca0cadf75c2d9796df`.
Its review-only CLI succeeds with zero launches. The source and exact plan
must receive independent QA before a single cold launch; a reviewed-plan
change requires a new version and hash. Root coordinates the slot and cold
start timing, with at most five live Minecraft processes. This document is
preparation evidence, not a runtime success receipt.

V1 was not launched. V2 added an explicit client palette availability gate,
preventing an unavailable palette from being mistaken for empty air. V3 adds
strict integer aux checks (so `False == 0` cannot pass), and allows matching
absent native collision boxes while still requiring a selection clip for
non-air blocks. The actual R9 poppy collision observations are zero-size
boxes; this control does not force a solid plant collision shape. V2 was
also not launched. The current V3 frozen plan is
`.runtime/native-plant-positions-r13-v3/plan.json`, SHA256
`7c47e75bc5b9021fd6d40416d4e783832c3b8bf428f6c6d694770aa713ac8101`.
Both earlier plans and their original source bytes remain archived.

## Native observations and visual positive controls

The server first requires all eight target/support cells to be loaded air
in both palette layers, preserving the one-player private-world requirement.
Each coordinate then temporarily gets a dirt support. Client replication
must confirm that support before the camera or block captures begin.

Every target uses the fixed relative camera offset `(-2,.15,-2.5)` and actual
SDK direction readback. Only the two existing predeclared yaw semantics
`180` and `0` may be tried; selection occurs before images, using actual
`GetForward` cosine greater than .99. Camera/player position and rotation,
screen, FOV and direction are checked before/after each capture. At least
two real `GameRenderTickEvent` events precede each image. Physical images
must remain 1994 by 1105 with the existing crop `(498,276,1495,828)`; no
activation, input, resize, recrop or foreground fallback is permitted.

Every coordinate captures native stone, native blank and then native poppy.
The first attempt for each image is retained. Poppy placement is conditional
on the preceding full stone/blank qualification. The largest connected
component of their unchanged threshold-20 difference is filled to recover
the solid cell silhouette. It must match the independently observed V3
native stone cell ROI with the existing three-pixel tolerance, .75 recall,
.75 precision and .5–2 area ratio. This prevents a moving animal or unrelated
region with more than 1,000 changed pixels from qualifying as a stone cell.
The expected ROI is never moved, expanded or regenerated from this run.

The frozen external reference is
`tools/data/snow-centered-r13-v3-result/run/qualified-cell-roi.png`, SHA256
`ba7ccbb82bc5126b69ce5217e61826febe35356821160926de03c18c5018d0cb`,
with 113,706 pixels. It describes an already observed native stone cell at
the same physical image dimensions and relative camera. It supplies only
a stone visibility qualification, and does not establish plant geometry.
A failed stone qualification preserves the first images and terminates
before placing poppy at that coordinate. Visible native poppy must then
contribute at least 80 pixels inside the qualified cell ROI.

Both server and client `GetBlockClip` and `GetBlockCollision`, block identity
and client foreground/background palette are recorded before and after
every image. Server/client box observations and aux values must agree and
remain unchanged across capture. Matched absent boxes are allowed for air.
Selection boxes describe ray selection; they are not established mesh
pivots. Neither screenshots nor AABB centroids are used to adjust a model.

## Restoration and cost

Each native target, dirt support, time, daylight rule and biome is restored
before moving to the next coordinate. Attempted fixture writes are journaled
before the SDK request; cleanup also runs after a failed acknowledgment.
The original follow camera, player position, pitch/yaw locks and FOV are
verified after render events before clearing its journal. An interrupted
save acknowledgment recovers the existing remote journal before restoring.
Render listeners are removed, all eight server/client cells must again be
air, and player position/flight must match the initial preflight. Cleanup
errors prevent diagnostic completion; production acceptance always remains
false. Owned process identity and host-file restoration follow the unchanged
supervisor contract.

Preparation has 17 focused host tests, including moving-actor and wrong-region
stone rejection, client/server aux mismatch, stale boxes/coordinates, absent
air/collision boxes, missing client palettes and changed frozen scope/reference.
The existing 28 finite h0
supervisor tests pass. The MOD review tool parses zero host-tool files, so
its empty finding list is not counted as source review; these host tools
require manual independent review. One launch has total/work/cleanup/startup
bounds 240/190/50/90 seconds, retaining startup failures with no retry.
Complete images remain a finite diagnostic and do not qualify arbitrary
coordinates, other plants, editor rendering or missing-mode rendering.
