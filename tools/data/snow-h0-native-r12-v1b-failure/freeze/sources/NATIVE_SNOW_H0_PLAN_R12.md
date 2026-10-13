# Native Snow H0 Four-State Proposal

This is a concrete prospective control awaiting final source review and a
coordinated WGC slot. The V6 ready/world-frame prerequisite passed, but
resource health remains unaccepted. No additional launch, fixture mutation
or SDK request has been made for this preparation. The parent coordinator
authorized a separate finite 240/190/50/90 total/work/cleanup/launcher plan;
V6's immutable 150/110/40/90 startup receipts stay unchanged.

## Fixed Source And Destination

Use registered built-in `test.layers.snow`, metadata size `(64,8,64)`, visual
case schema 4. Extract the same `(3,3,3)` subfixture with focus `(1,1,1)` used
by `verify_snow_plant_visibility.LOAD`; retain the original built-in source
coordinate in every row. Offline `build` confirmed:

| Requested State | Built-In Source | Foreground | Background |
| --- | --- | --- | --- |
| Covered poppy h0 | `(18,1,9)` | `minecraft:snow_layer`, aux 8 | `minecraft:poppy`, aux 0 |
| Snow only h0 | `(18,1,9)` | Same snow, covered_bit false, aux 0 | air |
| Plant only | `(18,1,3)` | `minecraft:poppy`, aux 0 | air |
| Blank | `(18,1,3)` recorded; no block emitted | air | air |

The native destination is `(6,117,6)`, dirt support `(6,116,6)`, projection
origin `(5,116,5)` so extracted focus maps to that exact destination. The
extraction rebase is the existing document operation, not a new plant offset
correction. Preserve built-in source identity and actual native placement
coordinates; record the projection origin and both coordinates. Do not
enable a position profile, normalize random plant movement, correct offsets,
shift the destination, fit geometry, or adjust the camera after viewing a
result. `POSITION_PLANT_PROXIES` remains empty and unaccepted.

All target/support/control coordinates have Y in version 1.21 `[-64,320)`.
Startup-only allows valid player Y=-60. The fixed target must already be in
loaded terrain, with readable air front and air extra layers at target and
support. If unavailable or occupied, stop this condition. The earlier
`NATIVE_NEAR_PLAYER` platform/SetFootPos snippet is excluded: no teleport,
flight toggle, movement input, extra platform or target relocation. Record
player foot and flight state before and after; any drift invalidates the
fixed-player comparison and is reported, not silently corrected.

## Camera And Pixels

Use the public world offset `(-2.0,0.15,-2.5)` about target center
`(6.5,117.5,6.5)`, giving detached camera position `(4.5,117.65,4.0)`.
This is an owned SDK detached-camera route used by the existing
`native_capture`, independent of the player-follow view at Y=-60. Compute
rotation once from the existing public `GetRotFromDir(center-position)`
semantics plus yaw 180, preserve that pose across all captures, and record
position/rotation/FOV/screen readback before and after each state. No editor
preview is included; the built-in editor camera `(35,10,2.8)` is recorded only
as source metadata.

Predeclare physical PNG size 1994x1105, matching the observed V6 client. The
fixed central half crop is `(498,276,1495,828)` and must be identical for all
native/projection and original/marker captures. A changed client size fails
the condition; do not resize, switch to a new crop or interpolate frames.
Each capture is one owned direct-child native WGC call with bounded wait,
fresh compositor timestamp, PMv2 physical guard and before/after owned
creation/executable/readiness checks. Preserve the first capture outcome for
each requested row; failure cannot be replaced by a later frame.

Camera qualification must occur in the same owned session and actual game
version. The preferred route is an actual successful public
`WorldToScreenPoint` call for the eight fixed target-cell corners, checking
finite coordinates, positive depth, all points in screen and consistent
screen/FOV before deriving one fixed world-cell ROI. Documentation or a
tool's presence alone does not prove the route works in 1.21.120.

If that route is unavailable, a bounded stone/blank pair at the same
target/support/pose supplies a direct pixel ROI before any snow captures.
Require replicated native stone, an unchanged player/camera/FOV/screen and
at least 1000 pixels in the largest stone-minus-blank component; fill only
enclosed holes to obtain the cell silhouette. This measured native-cell ROI
qualifies where the target is visible at the fixed pose. It does not qualify
an analytical camera formula or FOV conversion. No FOV/offset search or
geometry fitting is permitted. Do not reuse another session's cube, 773c's
calibration, or the full `verify_camera_projection.py` CLI as proof.

## State Sequence And Controls

Each prospective texture condition has one cold start at most. Original
condition uses unchanged native `flower_rose.png` and own override absence.
Marker condition installs only the frozen own override preserving every
native alpha byte. Hashes and equal alpha SHA are in the machine plan. A
same-session atlas switch is excluded; cold-loading still requires positive
plant pixels and does not by itself prove the selected atlas content.

For each condition, capture native states in the frozen order covered,
snow-only, plant-only, blank. Keep dirt support throughout. For covered,
clear target, place native poppy, then call `SetSnowBlock(..., height=1)`;
require successful result, front snow states height 0/covered_bit true and
replicated extra poppy. For snow-only, place snow height 0/covered_bit false
and require no replicated extra plant. Plant-only requires poppy with air
extra; blank requires air in common and extra. Use both server state and
client replicated palette evidence, with finite waits and no blind replay
of a timed-out mutation.

After the native blank is verified, load the four extracted built-in
documents and capture actual projection at the same target/pose/crop in the
same order. Native target stays air during projection. Require exact current
document/editor/nonce/source submission, registry/render-layout/runtime
versions, ready actor/mesh for nonblank states, opacity 1, missing/outline
false, and declared origin. Blank requires no projected target contribution.
No native plant or snow may remain behind the projection actor.

Retain all eight raw images. Native plant-minus-blank and projection
plant-minus-blank are separate positive controls. Require at least 80
observable plant pixels inside the same qualified ROI before interpreting
covered-minus-snow. Covered-minus-snow measures visible plant contribution;
do not assume it must be positive without a passing plant control. Reuse
the existing 20-channel-difference threshold, minimum 80 baseline pixels
and 3-pixel comparison tolerance as frozen diagnostic parameters. Report
raw differences, masks/counts/bounds, native/projection consistency and any
ambiguous background changes. Do not derive native mesh authority or random
offset formulas from one cell.

## Finite Feasibility Gate

The narrow adapter is `supervise_snow_h0.py` with
`verify_snow_h0_phase.py`. It reuses frozen existing snippet semantics, the
V6 same-handle host cleanup, launcher and PMv2 background observer. A
prospective reservation after ready is 83 seconds: 10 setup/state save, 12 same-session camera
qualification, 24 for four native rows (6 each), 32 for four projection rows
(8 each), and 5 nominal SDK state restoration. SDK restoration is allowed
through T0+210, leaving 30 seconds for exact process stop and byte restoration
inside the 50-second cleanup reserve. Every SDK request is capped at 3
seconds, every WGC wait at 5, additionally clamped to its stage/parent
remaining time. No timed-out mutation is replayed. These are prospective
caps, not observed runtimes. Synchronous host WinAPI/filesystem operations
remain outside an independent OS hard-watchdog guarantee; a measured work
or total deadline overrun fails the diagnostic.

Under V6 observation end T0+110 the matrix would have needed ready by T0+27;
its final ready result at T0+90.755 left only 19.245 seconds. The separate
240/190 plan requires final readiness plus a passing first post-ready world
frame by T0+107, retaining all 83 seconds through work cutoff. At the observed
V6 ready time, about 99.245 seconds would remain under that contract. The
full existing snow/camera/SignCheck paths have unbounded outer waits and are
unsuitable. A slow fixture stage fails and proceeds to cleanup instead of
borrowing an implicit longer deadline or replacing the first capture.

Loaded fixed terrain, same-session camera capability, final reviewed frozen
adapter, full budget reservation, and a separately coordinated runtime slot
remain prerequisites. Host-only owned process handle counts are sampled on
the first published binding and every 15 seconds between bounded requests,
at most 18 samples. Pre-ready handle growth is observation-only; reaching
100000 game handles stops work throughout the run. The first ready sample
starts a new baseline. Only two consecutive wholly post-ready intervals,
each with delta >=5000 and rate >=200 handles/second, trigger a growth stop
and cleanup of exact owned identities. Actual sample timing is retained;
no continuous monitoring or causality is
claimed. SDK restoration still runs after a resource stop. Lack of a trigger
does not accept resource health. If any gate fails, retain the first failure
and clean up; no retry/relaunch or implicit longer deadline.

## Restoration And Acceptance

Before mutation journal exact target/support front+extra, camera attachment,
locks/pose/FOV, editor/document/projection state, player foot/flight,
biome/time/daylight and own texture/config/script bytes. The fresh cold
session's initial camera follows the player; restore that mode and compare
original position, rotation, pitch/yaw locks and FOV using actual readback.
Save each resource
before changing it; on partial setup retain the journal. Restore owned
fixture cells/layers and camera/projection/UI/world state using bounded
requests, verify readback, then close only the exact owned game/MCDK
identities and restore exact host bytes/original absence. Restore time as
saved with its original daylight-cycle setting; record any unsuccessful
readback. Keep total measured elapsed and cleanup failures separate from
pixel outcomes. Avoid deleting or editing previous evidence.

This proposal can only add narrowly scoped h0 diagnostics at one native
coordinate/public view after both original and alpha-preserved cold controls
complete. It cannot expand accepted heights, other plants/views, opaque
markers, holdout cells, production geometry or the position registry. The
existing 29 positive /232 height /8 actual-negative evidence stays unchanged.
