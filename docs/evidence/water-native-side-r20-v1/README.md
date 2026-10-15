# Native Water Side Oracle, Round 20

This package records a fresh NEMC 3.10.0.420447 session with the unchanged
water shaders and original physical sampling grid and thresholds. It does
not qualify production water.

The six stone controls and twelve full/missing world-water controls were
captured in the same owner-bound session. Native `WorldToScreenPoint`
coordinates are physical pixels, even though `GetScreenSize` reports logical
UI dimensions. Native cube hull IoU is 0.9692-0.9745, so the API is a measured
oracle with a small raster discrepancy, not exact pixel truth.

Each opaque water PNG is bound to its source contract, session, physical
viewport, document origin, camera, dry control and two stable API point
readbacks. Independent wet/dry, section-hidden, section-restored and
opaque/default-restored image differences reject stale or absent water.
Full and missing south/east correlations are 0.949223/0.937050, with RGB RMSE
2.92809/3.14987. Mirrored, constant and wrong-phase negatives all fail. The
original analytic oracle still fails at 0.830878/0.644174 and remains in the
analysis as a diagnostic; no shader offset or threshold adjustment was used.

The subsequent six editor controls failed: the screenshots show stone
supports without water, and independently visible water pixels are zero.
Ready state, cleanup and source equality do not override this failure. These
captures and their failed analysis are retained explicitly. Four owner CPU
methods have enough combined samples and meet the existing limits, but CPU
results do not qualify the failed editor visuals.

A later 102-image core batch, retained under the local round-20 runtime
directory, also failed all applicable editor visibility controls and measured
a 169 ms `LiquidProjection.advance` maximum above the 100 ms limit. The
shorter pool CPU result in this package does not replace that later failure.

`launch-input-delta.zip` supplements the already published round-19 source
archive. Together they reproduce every byte of the 3,072-file launch snapshot,
without another copy of the common 47 MB archive. Raw session credentials and
launch responses are excluded.

Run `python -X utf8 verify_package.py --pixels` to check all archived hashes,
materialize the exact frozen Python sources in a temporary directory, replay
the native camera validation, and reproduce both the world passes and editor
failures. The verifier performs no game or desktop interaction.
