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

## V5 Empty-Scene Reference Contamination

The v5 cold run keeps the same 3,116-file product source contract and all four
reload settings disabled. Its ready image shows the actual loaded world.
The lifecycle ends after 35.57 seconds at the snow control, before any editing
step, with `completed=false`, `passed=false`, `restored=true` and no cleanup
errors. All 55 commit samples exceed the 6 GiB execution gate, with a minimum
of 7,378,378,752 bytes. Product and host-data hashes remain unchanged.

Both fresh native snow captures contain 22,503 changed pixels, side recall
1.0, and hull precision 0.909567613207128 against the unchanged 0.98 gate.
All 2,035 pixels outside the three-pixel hull tolerance are ink visible in
the blank reference and replaced by the ordinary viewport background in the
snow image. Actual original images and unshifted ROI crops show the removed
empty-scene cube and text. The change detector counted that disappearing
placeholder as object pixels. No unexplained outside pixels remain, but this
diagnosis does not accept or repair the failed original acquisition.

The failed snow control did not persist its own source/state/camera observation.
The preceding plant camera exactly replays the recorded snow metrics; it is
explicitly labeled as a prior observation, not a newly measured snow camera.
`docs/evidence/snow-control-r20-v5-failure-v1` preserves 58 manifested files,
3,959,614 bytes, including all seven original lifecycle captures, ready image,
reports, clocks, original pure geometry inputs and exact process exits.
Its standalone replay also succeeds after relocation and rejects raw-byte
tampering:

```powershell
python -X utf8 docs/evidence/snow-control-r20-v5-failure-v1/verify_package.py --pixels
```

The next probe uniformly hides only the existing native `empty_model` node
before every capture. It dynamically finds the current owned fiber and records
the original visibility, fiber identity, native path and hide readback. Cleanup
restores only the same still-mounted fiber/path; removed nodes are recorded as
removed, and reused paths are never written through old references. Actual
source, preview state and camera are persisted before every capture and pixel
validation, including failed controls. Host checks cover repeated captures,
initially hidden nodes, remount, path reuse, changed host, failed hiding, and
native-capture abort. The exact main `finally` also restores placeholder
visibility and the existing factory/editor/library/options/listener/navigation
state under success and injected acquisition failure. This is probe-only work;
the product source, image coordinates and acceptance thresholds are unchanged.
Native verification of both the new reference isolation and the earlier camera
recovery remains open.

## V6 Minimal Native Lifecycle Accepted

The frozen v6 run completes the single `blue_orchid h0` editor lifecycle on
NEMC 3.10.0.420447 / Minecraft 1.21.130.0. The child process exits 0 after
107.56971399999748 seconds. The original report records `completed=true`,
`passed=true`, `restored=true`, all nine steps passed, and no cleanup errors.
All four independent controls pass. Snow-side recall and complete-hull precision
are both 1.0. The final saved-library-load mask has recall and precision 1.0
against its combined control, and both original images were independently
opened by the coordinating agent. This verifies the probe's placeholder
isolation and ordered camera recovery for this one native lifecycle.

The actual wrapper `receipt.json`, rather than the report's top level, retains
`process_completed=true`, exit 0, `source_unchanged=true`,
`host_data_unchanged=true`, and the original report SHA256. A post-close source
audit verifies the same 3,116-file product contract
`342accbbbded82443a1341dab92553435b6a9d3b596be15df87052e364d0a466`.
All four reload settings remain false. All 210 canonical execution-boundary
commit samples exceed 6 GiB; the minimum is 7,127,699,456 bytes. Persistent
library writes and product qualification changes remain false.

The original 16 captures retain actual source, preview state, camera and
placeholder observations before pixel validation. The empty-scene placeholder
is hidden and read back uniformly; its original fiber is later unmounted, so
cleanup records it as removed without writing through an obsolete native path.
The first ordinary close times out. The exact owned game and MCDK handles then
report exit codes `0xC0000409` and `0`, respectively; the code alone does not
establish cause. A later ordinary stop finalizes stopped metadata. Both exact
identities and the observer are absent before the MC/WGC slot is returned.
No force stop is used.

`docs/evidence/snow-lifecycle-r20-v6-subset-v1` preserves the original raw report,
receipt, captures, masks, ready image, exact process exits, frozen plan and its
explicit launcher-only amendment. It binds the full source inventory while
retaining only used assets and pure replay inputs. Its standalone replay runs
the unchanged pinned AST definitions of the existing lifecycle analyzer and
geometry helpers without importing game-facing modules:

```powershell
python -I -X utf8 docs/evidence/snow-lifecycle-r20-v6-subset-v1/verify_package.py --pixels
```

Independent replay after relocation to Temp passes all 16 original native
captures. Targeted negative checks reject changed process identity, pictured
native clock, control camera, actual camera observation, missing capture
observation, visible empty placeholder and modified raw image bytes.

Only the `blue_orchid h0` nine-step editor subset is accepted. Full snow
acceptance remains open, including other plants and snow heights, positions,
neighborhoods, and complete editor/full/missing projection integration. Native
random plant placement offsets are outside the declared centered style.

## V7 Two Native Holdouts Prepared For R22

The existing v7 freeze remains unchanged for the round ending
`2026-10-16T13:30:00+08:00`: 921 host files and the same 3,116-file cold product
source contract. Its only new plant/height pairs are `lily_of_the_valley h4`
and `crimson_roots h7`, each through editor/full/missing routes. The original
two-case driver rejects crossed pairs before session access. Actual installed
3.10 texture alpha predicts 3,260 exposed pixels out of 26,635 dry pixels for
the lily, and zero exposed pixels out of 48,250 for the roots in the declared
offline camera. These values select useful partial/full burial cases; they
are not acquired native acceptance results.

The current-round entry point is `.runtime/snow_v7_r22.py`, defaulting to
offline `check`. It verifies the unchanged v7 launcher, plan, full host and
cold product inventories, and the independent watcher sidecar in
`.runtime/snow-r20-v7-r22-control`. The sidecar retains the current assertion
watcher and four dependencies without modifying the old frozen host or cold
product. Its original watcher root is explicitly rebound in memory to the
repository so its project restriction still targets the owned cold clones.

Only after Root assigns the MC/WGC window:

```powershell
python -B -X utf8 .runtime/snow_v7_r22.py start --scheduled-by-root
python -B -X utf8 .runtime/snow_v7_r22.py ready --scheduled-by-root
python -B -X utf8 .runtime/snow_v7_r22.py calibrate --scheduled-by-root
python -B -X utf8 .runtime/snow_v7_r22.py lily --scheduled-by-root
python -B -X utf8 .runtime/snow_v7_r22.py crimson --scheduled-by-root
```

The assertion watcher starts before game launch, is restricted to the exact
`snow-r20-v7` owner, and runs until 13:30. Each phase requires two advancing,
fresh heartbeats covering the exact session and a live exact-exit observer
identity. All earlier read errors, recoveries and other assertions remain in
the cumulative watcher record and block clean acquisition. The original
exact-handle observer covers ready through both actual process exits, not the
spawn-to-ready interval. Twelve offline checks verify the default path with
live subprocess/identity access denied, deadline admission and watcher
negative controls. The original nine probe restoration tests also passed.

This run needs one owned game and at least 6 GiB of available system commit,
using `(CommitLimit - CommitTotal) * PageSize`; physical availability is not
the gate. It retains the single operational-engine limit, aggregate five-game
limit, four reload settings false, `OPENBLAS_NUM_THREADS=1`, and no activation,
resize, desktop input or force stop. A new same-session stone calibration
precedes both holdouts; neither old calibration bindings nor pixel thresholds
are changed. The matrix uses the approved Y+16 fixture, physical pixel ROI,
blank/plant/snow/covered controls and a same-plant cutaway. These two matrix
holdouts do not extend the nine-step lifecycle claim to either new plant.

The expected complete wall time remains 12–16 minutes, with 20–25 minutes
reserved for slow acquisition or restoration. Admission requires at least
30 minutes before start and 15 before calibration or either holdout. Those
reserves are not a finite hard restoration bound; the original cleanup is
allowed to finish. After one ordinary close request, wait for both exact
exits and for the exit observer to finish before metadata finalization:

```powershell
python -B -X utf8 .runtime/snow_v7_r22.py stop --scheduled-by-root
python -B -X utf8 .runtime/snow_v7_r22.py finalize --scheduled-by-root
```

No v7 game was launched during this preparation. Native stone calibration,
both holdout reports and original-image review, unchanged-source receipts,
and exact exits remain required. Product and full-snow qualification remain
false. Any later accepted range must name the acquired plant/height pairs,
centered placement, routes and workflow explicitly; the `blue_orchid h0`
single lifecycle cannot establish broader default support.
