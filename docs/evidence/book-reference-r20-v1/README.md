# Native Book Reference and Lectern Back-View Failure

NEMC 3.10.0.420447, 2026-10-15. This managed candidate run used final model
names in `.runtime/projects/book-r20`, session
`986474a049464e2c9ad026350b288539`, owner `book-r20-reference-v1`.
It completed all 28 captures and restored world cells, inventory, player foot
and rotation, UI, camera, temporary candidate assignments, and clear-noon
environment. Sources stayed unchanged and cleanup errors are empty.

The controlled empty arena and three-block observation platform provide actual
native item placement and real book NBT. Native and candidate use the same
physical player view. All five review sheets were actually inspected.

The enchanting table has six native and sixteen candidate motion close-ups,
plus the attached native view. The unchanged cover-artwork distribution and
isolated-fragment checks both pass; the combined raster gate passes. The raw
source report and repeated close-ups remain valid for that limited gate.

The lectern page comparison fails and is deliberately retained. This native
placement produces aux 1, west-facing, while the fixed observation platform is
north of the lectern. The view exposes the page back/edge rather than the broad
front page. The page-color mask selects brown lectern material in this view:
native median RGB is (134,108,70), versus the earlier frontal native page
(211,200,157). Measured precision is 0.96143, recall 0.81714 and maximum color
difference 34. The candidate left cover also protrudes differently in this side
view. It is not accepted as pixel parity or used to enable production.

The probe formerly placed the real lectern before aiming the player, so it
inherited an unrelated prior player direction. The controlled-arena probe now
aims at the target before native placement and records that placement view.
The fixed frontal page check is repeated separately. This failure is not
discarded, and no all-direction lectern pixel-parity claim is made.

`crops.json` binds exact, unscaled crops to their original full-resolution
captures under `.runtime/book-r20-final-reference-v1`. The managed session was
subsequently stopped and both owned processes were confirmed absent.
