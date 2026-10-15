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

The corrected blue-orchid matrix at heights 0, 4 and 7 completes and restores
the scene with no cleanup errors or changed product source. All shape, snow
burial/retention, inside-cell and full/missing equivalence checks pass. It still
fails acceptance because every full/missing backdrop check fails. For example,
the dry plant has editor expected/observed areas of 21,819/21,159 pixels and
world areas of 11,430/11,244 pixels; both shape recall and precision are 1.0
within the declared edge tolerance, and no world plant pixels lie outside the
calibrated cell. Of 100,325 tested background pixels, 32,843 are not dark wall.

Native palette readback reports the complete 1,025-block black-concrete wall,
and its projected top is above the viewport, but its visible pixels end across
the cell. A separate journaled `SetBlockNew(..., True, True)` control reproduces
that failure. The direct control reaches the 215,000-handle gate and restores
successfully. A native section visibility/update issue is a hypothesis, not an
established API defect. A follow-up isolated control lowers the unchanged fixture
from player Y+32 to Y+16, retaining the original background thresholds.

That Y+16 control now passes the complete single-blue-orchid height-0 matrix.
Its same-session front/right/tilted stone calibration passes and restores.
All 100,325 tested native background pixels are dark wall, in both full and
missing modes. Dry plant, pure snow, combined snow/plant and the cutaway control
all pass their original gates. The matrix completes in 160.3 seconds and
restores with no cleanup errors; frozen product source and host-data hashes
are unchanged. Independent replay of its 21 captures reproduces every pass.

This establishes a working lower fixture in this world and session. It does
not establish the precise native cause of the upper fixture failure or close
the remaining plant/height and runtime workflow coverage. No product source
or qualification was changed. The v2 engine/MCDK pair was then stopped normally.
Its portable package, `docs/evidence/snow-product-r20-lower-v1`, retains 1,646
manifested input files totaling 38,796,620 bytes. The standalone byte verifier
and pixel replay pass with `production_accepted=false`.

The next plant matrix revisits lily of the valley, bush and crimson roots.
Remaining work includes all 29 plant names and eight snow heights,
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
- `.runtime/snow-product-r20-targeted-v3`: corrected physical-pixel hull,
  complete blue-orchid h0/h4/h7 matrix, unchanged failed background gates and
  independent pixel replay.
- `.runtime/snow-product-r20-direct-backdrop-v1`: documented direct native wall
  setter control, original failure and successful restoration at handle gate.

The first snow engine and MCDK were stopped normally after these controls. A
second stop finalized the managed receipt after the first wait timed out while
the native process exited. No force termination was used.

## Portable Pixel Replay

`docs/evidence/snow-product-r20-v1` retains 1,656 files totaling 64,270,122 bytes,
including unmodified matrix/calibration reports, captures and receipts, frozen
acquisition tools/data, the complete cold business Python, and used plant
assets. The manifest verifies the latter against the original launch hashes.

```powershell
python -X utf8 docs/evidence/snow-product-r20-v1/verify_package.py --pixels
```

The independent verifier passes manifest byte checks and replays all 41
captures without a live game or original absolute paths. It reproduces
`non_background_checks_passed=true`, `background_checks_passed=false` and
`production_accepted=false`. The absent-plant negative control is rejected.
This is a portable pixel replay, not a complete executable acquisition replay:
unrelated full product media is pinned by hash rather than duplicated.

The runner also supports a row-boundary pause handshake. A root pause request
is acknowledged only after the current row's native captures drain, before
the next document mutation. Root can then reserve a short WGC window for
another owner without interrupting a six-second frame-response gate.

## Editing And Storage Coverage

`test_snow_edit_workflows_r20.py` exercises the actual `Session.point_action`,
`Session.action`, `Session.save` and `Session.load` entry points through an
in-memory persistence bridge. Across all 29 plants and eight snow heights it
checks 696 strict/automatic erase cases plus 232 add/remove/history/library
workflows. The checks include same-cell snow placement, selection position,
neighbor retention, both undo and redo directions, and exact complete-cell
round trips through the production storage codec. They pass without product
code changes. These are host behavior checks; native Scene hit testing and
rendered editing workflows still need their own runtime evidence.

The current pixel replayer also resolves a later plant's reused snow controls
only after the original source control was replayed and the editor/full/missing
capture hashes all match. Missing sources, changed heights and altered capture
hashes are rejected by a focused negative test. The already published v1
package retains its original verifier and bytes.

`run_snow_scene_lifecycle_r20.py` is prepared for a separate native editor run.
It follows nine real command/history/library steps, waits for current native
tiles after each command, and compares fresh captures with plant-alpha,
snow side-face/hull and combined burial controls. Its declared small upward
editor pan keeps the low snow's side faces clear of the floating Scene toolbar.
White top texels can match the editor background, so snow controls require
visible side-face recall and complete-hull precision rather than whole-hull
difference recall. Old toolbar-obscured h0 controls are rejected by this new
gate; unobscured h4/h7 controls and absent/stale-plant negatives behave as
expected. A forwarding bridge redirects only
library/preferences persistence into memory and restores the original bridge,
library, editor and navigation in `finally`. Generated command execution and
zero persistent library writes pass a host check. Native acceptance of this
new probe remains pending. The frozen v3 clone cold-started with all four
reload settings disabled and its owner/runtime/noactivation handshake verified.
Its ready image shows the actual world. The first lifecycle attempt stopped
before native mutations because the host runner omitted the frozen SDK scripts
from its import path; that host path is now fixed and the failed receipt is
retained.

The next run, `.runtime/snow-lifecycle-r20-blue-orchid-v2`, passes all four
independent controls and the strict foreground erase/undo captures. Height-0
snow has side-face recall 1.0 and complete-hull precision 1.0, with no toolbar
occlusion in the inspected combined image. The owned game and MCDK then exit
before the third edit step. The report honestly remains incomplete and
`restored=false`: all four cleanup callbacks encounter the exited process.
The wrapper retains unchanged frozen product and host-data hashes. This run
does not close native editing or storage acceptance, and its process-exit
cause has not been established.

Offline replay verifies all nine retained native capture hashes, owner and
process identities, compositor freshness, native clock/tick responses, and
the inspector header's actual hide/show pixel counts. This failed acquisition
omitted its Scene crop from the report, so its independent Scene geometry
replay remains unavailable. The replayer reports that missing field and keeps
`pixels_replayed=false`, `workflow_accepted=false` and the original incomplete
and unrestored state. The next probe now retains the crop and a before/after
command phase receipt without changing the frozen v3 clone or old evidence.
Replay tests use the immutable original h4 captures, explicitly labeled as a
control adapter rather than a native workflow, and reject changed owner,
render ticks, clock, response screenshot and expected alpha.

## V4 Lifecycle Failure And Camera Recovery

The frozen v4 run uses source contract
`342accbbbded82443a1341dab92553435b6a9d3b596be15df87052e364d0a466`.
Its owned 3.10/1.21.130 instance completes all four controls and the first eight
editing steps. The independent h0 snow side recall and hull precision are both
1.0; strict erase/undo/redo, background erase/undo, and automatic snow removal
and addition all meet their recorded pixel gates. The final saved-library-load
capture contains the snow and plant but is displaced downward by about 46
physical pixels. Three fresh attempts repeat the mismatch, with shape recall
0.21238 and precision 0.21045. The original report remains `completed=false`,
`passed=false`, `restored=true`, with no cleanup errors or persistent library
writes. Its 120 resource samples retain at least 8.0488 GiB available system
commit. Frozen product and host-data hashes remain unchanged.

The original outer receipt's `completed=true` meant only that its child process
terminated; the child exited 1. New wrapper receipts separate `process_completed`
from the actual report's `completed`, `passed` and `restored`, and bind that report
by hash. The old receipt is preserved without rewriting its fields.

An offline replay of the real Scene `aim` and camera-update AST fragments
reproduces a probe recovery race. When pan is set before the restored zoom has
converged, a frame before the zoom effect makes that effect rebase an unfinished
pan, producing roughly 46 pixels of displacement at a 5 ms frame interval.
The generated storage commands retain exact document cells, scene origin and
size, so no coordinate import change is established. The failed acquisition did
not retain the actual final Scene camera, so the offline reproduction explains
a matching mechanism without establishing the precise live scheduling order.

The next probe restores and waits for actual rotation/zoom first, then restores
pan and waits for its actual convergence. A read-only, session-bound inspection
of the registered Scene tick closure records the real OrbitCamera pose, target,
pan, pan target, pivot/center, native viewport, scene bounds and tile centers.
It rejects absent or duplicate owned Scene callbacks. Each step persists these
observations and source state before capture, including when its pixel gate
fails. No product camera implementation, image position, acceptance threshold
or rendering qualification is changed. AST regression covers both tick/effect
orders and explicitly reproduces the old failure. Native verification of this
recovery change is still pending.

`docs/evidence/snow-lifecycle-r20-v4-failure-v1` retains 972 manifested files
totaling 15,967,362 bytes, including original capture/report/receipt bytes,
acquisition inputs, cold business Python, used assets and exact process-exit
observations. Its standalone replay checks all 18 original native captures,
including the three rejected final attempts, and reproduces the failed shape
metrics without accepting the workflow:

```powershell
python -X utf8 docs/evidence/snow-lifecycle-r20-v4-failure-v1/verify_package.py --pixels
```

During the first ordinary stop wait, the exact owned game handle reports exit
`0xC0000409` and the exact MCDK handle reports exit `0`. This records the exit
codes, not a proven exit cause. A second ordinary stop finalizes stale instance
metadata. No force termination or window mutation is used. Full snow acceptance
remains open, including the complete nine-step native workflow and broader
plant/height/position/neighborhood coverage.
