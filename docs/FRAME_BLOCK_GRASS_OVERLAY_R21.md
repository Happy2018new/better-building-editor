# Grass Overlay Native Holdouts

The corrected binary-alpha recipe preserves the hidden dirt RGB where source
alpha is zero, multiplies the opaque gray grass fringe by the native overlay
color, and produces opaque carried faces. Fresh native/full/missing captures at
0, -75 and +75 degrees support this correction for grass block aux 0 in the
frozen quarter-cube diagnostic clone. All three raw route images and the montage
were opened per angle. No registration, recoloring or fitted color correction
was applied to the captured pixels.

| View | Filled IoU, full/missing | Unfilled IoU | Main side ROI | Side luma ratio | Side P95 channel delta |
| --- | --- | --- | --- | --- | --- |
| 0 | 1.000000 | 1.000000 | z-, 4590 px | 1.001734 | 1 |
| -75 | 0.999158 | 0.997473 | x-, 2750 px | 1.000672 | 1 |
| +75 | 0.998311 | 0.997465 | x+, 2668 px | 1.001419 | 1 |

Top ROIs contain 268, 178 and 172 pixels; their luma ratios are 0.997433,
0.999118 and 1.002266. The oblique narrow z- ROIs retain P95 channel deltas
11.7 and 17.1 and luma correlations 0.939140 and 0.914073. The +75 silhouette
has a maximum edge distance of 4.123106 pixels, despite P95 zero and high IoU.
These residuals are retained rather than hidden by filling, alignment or a new
acceptance threshold.

Each phase used fresh three-view camera calibration, 20 raw PNG receipts,
time-of-day 6000, clear weather and disabled daylight/weather cycles. Capture
times were 96.408, 93.395 and 95.298 seconds. Every phase completed its matrix,
restored the native fixture and original environment, matched all 3828 frozen
source paths, and reported no cleanup errors before close.

The clone retains the prior `.93` empirical light factor. This batch supports
the overlay correction at its exact frozen settings; it does not qualify that
factor universally. Pose is `.25` cube / Z `.4375`, unaccepted. Direction,
all rotations, independent absolute thickness, frame/editor shared depth,
broader lighting, intermediate alpha and special geometry remain gated.
No grass enchantment was requested; ordinary sword glint results do not qualify
quartz block glint. `production_qualified=false` and `appearance_accepted=false`.

One normal close request timed out after ten seconds. The retained exact
observer later recorded game PID 3388 / identity 134365774254541407 exiting with
`0xC0000409` at 06:57:15.981 +08:00, followed by MCDK PID 3908 / identity
134365774248978715 with code 0 at 06:57:16.983. No force or repeated close was
used. Metadata finalization ran after both exact processes were absent and
returned `stopped`; the observer also exited. This is an abnormal game exit
after completed restoration, not a clean game exit or an established cause.

The independent incomplete/failed batch remains in
`docs/evidence/frame-block-light-holdout-r21-v1`. Its pixels and failure history
are unchanged. The new bundle contains all 60 fresh PNGs, sanitized reports,
calibration and unfilled-mask results, source-bound capture resources, native
bitmap inputs, frozen analysis helpers, runtime amendments and exact exits.
Replay needs Python, NumPy, SciPy and Pillow, with no installed game or session:

```powershell
python -B -I docs/evidence/frame-block-grass-overlay-r21-v1/replay.py replay docs/evidence/frame-block-grass-overlay-r21-v1 .runtime/frame-block-grass-overlay-replay
```

Replay checks every archived SHA256, all receipt timestamps and identities,
the 3828-path source digest, fresh calibration, raw/filled masks, geometry and
color statistics, all 50 derived PNGs, the corrected atlas, and exit metadata.
It performs no game, process or window mutation. The separately reusable
three-item generation entry is documented in `FRAME_BLOCK_MEASURED_CANDIDATE_R21.md`.
