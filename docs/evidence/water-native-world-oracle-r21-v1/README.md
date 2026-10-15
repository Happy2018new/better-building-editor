# Native World Water Oracle, R21

Production water remains unqualified and disabled. This additional analysis
applies an explicitly requested native stone-camera model to the existing
92-image full-world matrix. The original report, images, source closure,
analytic failures, and capture-host intervention remain preserved in
`../water-world-r21-v1`.

The default analyzer continues to reproduce the original 14/15 geometry
result, including the falling failure at 88 pixels. The new optional
`--native-world-geometry` mode independently derives a shared focal scale and
physical center from 24 native stone corners. It validates the calibration
file hash, owner/session identity, launch-source contract, native point
readbacks, all six original stone frames, and held-out view predictions.
The model contains no water-pixel fit. World falling geometry also uses the
existing solid-depth rasterizer for its two opaque support blocks.

The additional result has 15/15 geometry checks passing at the unchanged
thresholds. Fourteen bounding-edge errors are 2 pixels; transparent overlap
has a 3-pixel error. Falling has IoU 0.9825865574 and a 2-pixel error, matching
both the stone-only diagnostic and the separate direct-native-corner replay.
The body/rear contribution checks still pass. Animation remains untested in
this frozen matrix. The independent native-corner package also retains blank
and fixed missing-water controls that reject.

These measurements do not qualify alpha, animation, all world routes, dense
scenes, biome/occupancy combinations, true cold default behavior, or owner
performance. The matrix had a 49.029937-second Python host pause, so it does
not replace an uninterrupted performance baseline. Earlier long-call failures
of 169/230/435/370 ms remain recorded in the UI and timing evidence packages.

This package adds frozen analysis tools to the original launch closure. It
does not represent those newer tools as bytes loaded by the captured game.
`analysis.json` binds the original report, calibration, analyzer, helper, host,
session, and product source contract. `references.json` binds the existing
world package, and `manifest.json` covers every additional file.

The two relevant test modules are included. All 98 water-related tests passed
in the repository after the change. Run this package's `verify_package.py`
for hashes and references, or add `--pixels` to reconstruct the original
launch sources, layer the two frozen analysis overrides, and replay the
additional result with disk-backed exact int16 pixels. No game or desktop
input is required.
