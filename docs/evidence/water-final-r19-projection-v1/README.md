# Water r19 projection-oracle diagnostic

The apparent one-texel error in east cell `(4,3,3)` is strongly explained by the
analytical projection used by the sampling oracle. No shader, UV formula,
texture, product gate, or acceptance threshold was changed. This package is
diagnostic evidence and does not qualify production water.

The original valid v4 captures and failed original `18 x 14` checks remain in
`../water-final-r19-world-v1/`. This package retains the exact v4 opaque frame
used by the offline cross-check. The declared physical side formulas agree
with the frozen shader: east `(x+1,y+h,z+u)`, south `(x+1-u,y+h,z+1)` and texture
pixel centers `u*15+0.5`, `(1-h)*15+0.5`.

`v5/plan.json` and its receipt were written before the short v5 session. That
plan fixes the original physical grid, texel-center grid, pixel-center
conventions, and mirrored/constant/wrong-phase/wrong-UI-scaling negatives.
`v5/calibration-native.json` records public `WorldToScreenPoint` outputs on
three independent stone views. Its coordinates are physical pixels. A
numerical fit of those API values alone gives center `(997.4998,553.5000)` and
focal length `852.3152 px`, with residual below `0.00006 px`. This fit is a
diagnostic, never acceptance. The native API hull itself differs from the
stone raster by about two vertical pixels and has IoU `0.9692-0.9745`; it must
not be described as exact pixel truth.

The v5 world batch completed and restored without source changes, but all six
world screenshots are **invalid**: their SHA-256 values are identical and the
viewport still shows the preceding stone calibration. Each WGC receipt has a
fresh compositor timestamp. That timing does not prove fresh game rendering.
`v5/invalid-stale-capture-audit.json` retains the rejection, and the contact
image makes the error visible. Apparent texture correlations in
`v5/native-projection-analysis.json` were generated before visual inspection
and are rejected along with the v5 pixels. Sky gradients produced those
misleading correlations. Any subsequent verifier must require independent
nonzero wet/dry and section-hidden contributions before assessing UV.

The v5 numerical camera and native uniform observations are retained
separately. All 256 native uniform vectors match their expected float32
values. The public native projection differs from the old analytical oracle
by up to about 4.46 physical pixels over the declared water samples. Replaying
the fixed native coordinates over the old **valid v4 water frame**, under the
identical declared camera/viewport/document origin, gives original-grid south
correlation `0.94922`, RMSE `2.92809`, and east correlation `0.93705`, RMSE
`3.14987`; all erroneous controls reject. Both fixed texel-center side pairs
are exactly equal, RGB RMSE `0`, and all four cells match the frozen artwork
with luminance correlation `0.99990063`. These are cross-session diagnostics;
they do not replace the failed original v4 acceptance result.

The appropriate next step is a fresh same-session capture with public native
points, independent stone controls, verified changing water pixels, and the
unchanged grid and thresholds. The evidence does not support adding a
cell-specific UV offset or changing the water shader.

Run `python -X utf8 verify_package.py --pixels` to verify hashes, frozen
source inputs, rejected stale frames, native uniforms, and offline pixel
diagnostics. No game or desktop interaction is performed by the verifier.
