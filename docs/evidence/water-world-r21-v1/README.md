# World Water Geometry Diagnostics, R21

Production water remains unqualified and disabled. This package preserves a
19-case full-world matrix, its original falling failure, and a separate native
camera diagnostic. No product code, water resource, acceptance threshold, or
admission flag was changed for these measurements.

The full matrix has 92 original WGC PNGs. All 18 applicable visibility checks,
54 lifecycle checks, and two native side-UV controls passed. Fourteen of 15
geometry controls passed. The original falling result is retained with IoU
0.749558 and an 88-pixel bounding-edge error. The frozen analyzer also reports
the original failed analytic side-UV diagnostics.

The falling camera looks upward through opaque support blocks. Applying the
existing independent solid-depth rasterizer explains most of the difference,
but that diagnostic still fails the unchanged 6-pixel edge gate at 7 pixels.
The initial result and this failed support-depth result are both included.

An independent least-squares model uses only 24 native stone-cube corners from
the same session and source closure. The shared effective vertical FOV is
65.905387 degrees, with physical center (997.499804, 553.499993), for a
1994-by-1105 capture. The SDK-reported FOV is 60 degrees; the earlier silhouette
fit is 66.6 degrees. The shared native-point residual is below 0.0001 pixel;
leave-one-view-out residuals are below 0.00011 pixel. No water pixels are inputs
to this fit. Applying this stone model and support depth to the original
falling pixels gives IoU 0.982587 and a 2-pixel edge error. Blank and fixed
missing-water controls still fail.

Four additional original frames bind wet, hidden, restored, and dry falling
states to native water-face vertices and solid-box corners before and after
each capture. Their native depth replay is independent of the silhouette fit.
It gives IoU 0.982587 and a 2-pixel edge error, exactly matching the independent
stone-model depth result. Native points differ from the stone-only model by
at most 0.000149 pixel in every state. Omitting opaque occlusion still fails
at 90 pixels even with native projection. Both negative controls reject.
The original failures remain authoritative records of the original oracle;
the additional result diagnoses that oracle and does not qualify production.

The matrix includes a 49.029937-second suspension of its Python capture host.
The game was never suspended. The attempted pause did not allow the capture
child to finish, so the host was resumed and subsequent capture scheduling
uses natural batch boundaries. Both the initial raw record and the complete
intervention record are included. Every PNG is checked independently for
owner, session, identity, freshness, camera state, dimensions, and original
bytes. The matrix cannot replace an uninterrupted performance baseline.

The applicable world-owner maxima in this matrix are 19.999981 ms for
`LiquidProjection.advance` and 19.000053 ms for
`WorldLiquidRenderer.advance`. Editor owners have no samples here. Earlier
169/230/435/370 ms failures remain in the referenced UI and timing packages.
Aggregate timing results and diagnostics do not establish a performance fix.

`references.json` binds the exact 3093-file launch closure through the existing
base archive and two resource deltas. PNGs, receipts, raw reports, acquisition
hosts, analysis hosts, and derived masks are covered by `manifest.json`.

Run `python -X utf8 docs/evidence/water-world-r21-v1/verify_package.py` for
hashes, source reconstruction, bindings, and preserved failures. Add `--pixels`
to replay the frozen world analyzers and the native depth diagnostic without
a game or desktop input. Pixel replay uses temporary disk-backed copies of
the unchanged decoded int16 pixels to limit resident memory.
