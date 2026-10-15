# Missing-World Water Controls, R21

Production water remains unqualified and disabled. This package preserves the
completed 19-case `missing` world route, with 92 original WGC PNGs and 54 base
state records. The batch completed in 339.625479 seconds, restored its camera,
world, visual state, environment, HUD, capture settings, and timing hooks, and
reported no cleanup errors. No capture host or game was suspended. The agent
did not activate, move, resize, or reorder any window.

All 92 capture receipts are reliable and prohibit agent activation. Ninety-one
are background-safe. The restored wet-slab visibility control at 01:08:03-04
has the owned game already foreground before and after capture, with the
foreground unchanged and the window still marked no-activate. Its receipt
uses the explicitly enabled `allow_user_foreground` policy. That one original
foreground observation is retained; this is not an all-background matrix.

All 18 applicable visibility controls, 54 lifecycle checks, and two independent
native side-UV checks passed. The maximum observed group count was eight. The
side correlation is 0.949223 south and 0.937050 east; RGB RMSE is 2.928092 and
3.149873 respectively. Constant, mirrored, and wrong-phase controls reject.
Original analytic side-UV failures are retained separately.

The default geometry analyzer retains its 14/15 result. Falling still fails
with IoU 0.749558 and an 88-pixel bounding-edge error. Explicit native geometry
uses the independently measured stone-camera model from the same session and
launch closure, including opaque support depth for falling. This additional
result has 15/15 passing geometry controls at the unchanged thresholds, with
fourteen 2-pixel boundaries and one 3-pixel transparent-overlap boundary.
Falling has IoU 0.9825865574 and a 2-pixel boundary. No water pixels were fitted
to obtain the native stone model. Frozen body/rear contribution checks pass.
Animation is not measured by this frozen batch.

The timing hooks are installed afresh for each probe and restored afterward.
This batch records 522936 `LiquidProjection.advance` calls with maximum
10.000229 ms and 522928 `WorldLiquidRenderer.advance` calls with maximum
4.999876 ms. These are elapsed wall times and can include thread scheduling.
The two editor owners have no samples in this world batch; the generic
acceptance aggregate therefore remains false. This observed timing window
does not establish a performance fix or erase the earlier 169/230/435/370 ms
failures preserved in the referenced UI and timing packages.

After the complete batch restored its state, a normal stop request timed out.
The game subsequently exited with a WER BEX64 report for `ucrtbase.dll`,
exception `c0000409`, at 2026-10-16 01:10:40.2406387 Shanghai time. Both owned
processes were absent when checked at 01:11:43.4497094. No forced termination
was used. A second normal stop only finalized the already-exited session.
The original timeout, final session cleanup, WER bytes, and exit observation
are retained. Successful batch cleanup does not establish a clean game exit.

`references.json` binds the previously archived calibration and exact 3093-file
launch closure. Four offline analyzer files are frozen as analysis overrides;
they are not represented as files loaded by the captured game. The earlier
full-route package retains its separate 49.029937-second host intervention,
original failures, and native diagnostic. Nothing in this package replaces
those records or changes product code, resources, thresholds, or admission.

Run `python -X utf8 docs/evidence/water-missing-world-r21-v1/verify_package.py`
to check hashes, source reconstruction, receipts, identities, and exit evidence.
Add `--pixels` to replay all three analysis results using exact disk-backed
int16 pixels, without a game or desktop input. Alpha matrices, animation,
biome and occupancy combinations, dense scenes, true cold default behavior,
and full product admission remain incomplete.
