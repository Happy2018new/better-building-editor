# Final Ordinary Sword Glint Measurement

The unchanged final `096a1bda` candidate, including the item-frame glint color
multiplier `.75`, passed the original direction, speed and dynamic red/green
brightness measurement gates on all three product routes against an
independently measured native diamond sword. This is narrow glint evidence;
`production_qualified` remains false.

| Route | Dense Frames | Duration (s) | Actual Max Gap (ms) | Fit NRMSE |
| --- | ---: | ---: | ---: | ---: |
| Native | 73 | 7.9210 | 224.2332 | 0.05318 |
| World | 100 | 7.9150 | 103.0290 | 0.03244 |
| World Missing | 94 | 7.9514 | 139.4008 | 0.03179 |
| Editor | 218 | 7.9817 | 48.4887 | 0.03632 |

Every route also retains twenty original sparse images and an eight-second
dense request. Maximum layer direction error is `0.118432` degrees; speed
ratios are `1.000288-1.014178`. Dynamic red/green amplitude ratios are
`0.998051-1.001407`. The unchanged limits are in `summary.json` and the exact
original analyzer output in `direction-analysis.json`.

Both direction negative controls reject the deliberately reversed time
direction and wrong UV rotation. Sparse evidence is valid, every measured
body passes, the native reference is valid, and capture failures are empty.
The original `static_pose_accepted`, `all_native_bodies_passed` and
`all_native_edges_passed` flags remain false: this closeup-only run has no
general case matrix. No full static-pose or product qualification is claimed.

The 314.460-second capture completed and restored through the original host's
`finally` paths, with unchanged sources and empty cleanup errors. All 201
resource boundary samples passed. Minimum available commit was
`7,053,856,768` bytes and maximum game handles were `847`. Sampling was before
and after screenshots and bursts; there was no continuous in-burst sampler.
The game was retained for the next owner after the explicit runtime handoff.

## Retained Evidence

`direction-analysis.json` preserves all eight independent fitted parameters
for every route, including initial-phase parameters 3 and 7, signed layer
velocities, RGB temporal gains, residuals, comparisons and negative controls.
`raw-timelines.json` preserves every attempted dense frame record and its raw
receipt, including rejected records, original QPC timestamps and hashes. Each
route has one rejected attempt, retained in the original timeline. The
canonical capture-valid/temporal-complete receipts and actual gaps determine
cadence validity. The acceptance frames, order, times and colors were not
changed, and the candidate was not tuned on these measurements.

`samples/` contains byte-identical extracted sample arrays and pixel-source
bindings. `images/` contains byte-identical representative full native frames
and first-frame dense crops. The full-resolution capture, all raw receipts,
all crops and frozen source clone remain in their original `.runtime`
directories. The compact package records their complete SHA-256 inventory
instead of duplicating 367 MB of raw capture data. It is a local replay
package and requires those retained runtime inputs for full reanalysis.

Independent nuisance initial phases are estimated within each route; no
cross-route phase alignment, recoloring, interpolation or retiming is used.
Brightness scope is dynamic additive red/green amplitude. Static base
brightness and saturated blue are outside that amplitude claim. Artificial
block-item glint and broad item/aux/pose coverage remain open.

## Offline Replay

From the repository root, verify every retained file, original evidence file,
frozen source and dependency before replay:

```powershell
python -B -X utf8 docs/evidence/item-glint-final-r21-sword-v1/replay.py check
```

To rerun the exact frozen sparse and dense analyzers into new output paths:

```powershell
python -B -X utf8 docs/evidence/item-glint-final-r21-sword-v1/replay.py analyze --output .runtime/item-glint-final-r21-replay-v1
```

Replay is offline and sets `OPENBLAS_NUM_THREADS=1` in analyzer children before
NumPy import. It has no game, capture, start, stop or activation operation.
Existing outputs cannot be overwritten.
