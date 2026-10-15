# Snow Product Verification R20

This lane continues F01-S / F04-M28 using a dedicated background instance of
NEMC 3.10.0.420447 / MCBE 1.21.130.0. Plants remain fixed at the cell center by
editor design. The work does not reproduce native world random offsets.

At the 2026-10-15 23:30 checkpoint, product acceptance remains open. No product
qualification flag or shared rendering behavior has changed in this lane.

## Inputs And First Results

- The existing 29 centered plant source profiles and 27 generated proxy meshes
  pass `generate_centered_plant_profiles.py --check` against the actual installed
  3.10 vanilla resources. The profile filename and registry source still name
  3.9. This is source compatibility evidence, not a version-wide acceptance.
- The existing centered profile, snow visibility, visual oracle and blueprint
  tests pass 37 focused tests.
- One owned cold project was launched at `.runtime/projects/snow-r20-v1`.
  Its first verified world screenshot is an actual 1.21.130 world, without a
  loading overlay. No activation, resize, desktop input or z-order request was
  used. User foregrounding is allowed.
- Same-session stone calibration passes front, right and tilted views, including
  native `WorldToScreenPoint` hulls against visible stone pixels. Calibration and
  camera, world settings, projection and workspace restoration all pass.
  The effective analytical vertical FOV is 66.6 degrees.
- The first targeted command failed before fixture creation because a host-data
  copy exclusion accidentally matched `plant` as well as `plan`. Its failure is
  retained. The missing read-only host JSON inputs were subsequently copied.

## First Real Matrix Failure

The original snow QA helper `world_cell_roi` treats native camera points as
logical screen coordinates and multiplies them by screenshot size divided by
`GetScreenSize`. In 3.10 the observed native points are already physical pixels,
as established independently by the stone calibration. Applying the roughly
fourfold scale again places the complete cell hull outside the screenshot.

The unchanged first 3.10 matrix therefore records real blue-orchid editor
pixels with a passing editor shape, while full/missing cell masks are empty
despite the plant being visible in the saved world screenshots. These failed
reports are not rewritten as passes. The first failed world row has 11,244
actual difference pixels outside its erroneous empty hull.

After identifying the systematic QA error, only the suite's own native render
observer was unregistered to stop further redundant captures. The next bounded
frame-response wait failed, and the original `finally` restored the backdrop,
environment, capture options, camera and workspace with no cleanup errors.
The explicit cancellation receipt is retained separately.

## Corrected Verification

`probe_snow_product_r20.py` freezes the acquisition tools and host data alongside
the unchanged cold product source contract. `run_snow_matrix_r20.py` uses the
established product matrix with a separate, calibrated physical-pixel cell hull.
It requires the complete same-session stone calibration and rejects changed
source bindings, changed camera poses, native assertions, a 215,000-handle
budget or its elapsed-time budget before taking another capture.

`snow_native_projection_r20.py` does not infer scale from the observed plant.
It uses the native eight unit-cell corners in calibrated physical pixels and
rejects empty, offscreen, nonfinite or undersized hulls. Focused negative
controls reject the old double scaling and logical coordinates cropped as
physical pixels.

The next matrix first revisits blue orchid, lily of the valley, bush and crimson
roots. Remaining work includes all 29 plant names and eight snow heights,
different document/world cells, neighboring faces and seams, automatic/strict
editing, adding/removing snow while retaining plants, undo/redo, saved document
round trips, and separate editor/full/missing visual behavior. Existing limited
mushroom/fungus evidence does not close this complete work package.

## Retained Runtime Evidence

The current raw, unmodified runs are:

- `.runtime/snow-r20-v1-control`: frozen launch source manifest and startup.
- `.runtime/snow-product-r20-ready-v1`: first actual-world picture.
- `.runtime/snow-product-r20-calibration-v1`: passing stone and native camera
  calibration, original screenshots and independent restoration.
- `.runtime/snow-product-r20-targeted-v1`: host-data failure before fixtures.
- `.runtime/snow-product-r20-targeted-v2`: original double-scale failures,
  explicit controlled cancellation, successful restoration and stable sources.

Portable evidence publication and corrected pixel qualification are pending.
