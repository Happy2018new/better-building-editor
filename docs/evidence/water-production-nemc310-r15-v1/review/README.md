# Compact water review package

Stage only this `review/` directory plus the changed tools/tests. It is about
17 MB and contains exact original capture reports, the analysis
metrics, source snapshots, camera calibration, and six contact sheets. The
538 MB full native-frame archive remains local in the parent directory and in
the original `.runtime/water-production-r15-310` capture directory. Do not stage
the parent raw archive or package it into a large zip.

`summary.json` selects all 15 accepted direction rows across editor, full-world
and missing-only-world owners. Each uses the original 0.45 alpha and public F01
blueprint with production meshes/shaders. All measurable movements follow the
declared physical slope, and all reversed-time controls are rejected. The
initial full/missing capture reports retain their failed sparse falling rows;
`world-falling-sky-v1.json` provides the accepted falling rechecks. Original
report bytes are unchanged.

**Current review: geometry and direction pass; transparency is false and was
manually rejected.** `review-assessment.json` supersedes the transparency
acceptance conclusions in the preserved original reports and `summary.json`.
Wet fence body and rear gold are almost invisible beneath the water. The old
contribution gate compares different animation phases, so water texture changes
alone can satisfy its RGB-delta/pixel-fraction thresholds. The original numerical
`true` is not valid evidence of transparency. See
`transparency-six-controls-recheck.png` and `transparency-visual-recheck.json`.
A fixed-time or same-frame control experiment remains required before acceptance.

The three original style analyses retain their geometry (source/low/pool) and
animation observations. Missing pool occupancy hides and restores correctly.
Camera, world and source restoration pass. No production shader, UV, artwork or
resource alpha was changed by the water work. Native pixel parity and arbitrary
later main-workspace edits are outside this scope.

`correct_pair_fraction` remains the original ratio over all eligible pairs.
Metric version 2 adds a separate ratio over sign-independently measurable
displacements, requiring at least seven moves, 70% agreement, 60% time span and
three of four temporal quarters, with unchanged 150 ms interval, 0.50
correlation, 0.05 polarity and 0.3 signal thresholds. Forty actual host-shader
phase cases pass; eight available old NEMC 3.9 product bursts remain rejected.

The direction contact sheets mark the actual physical sampling footprint in
red. The style sheets show wet, dry and independently projected expected water
mask crops. These images are review aids; metrics were measured from untouched
full native frames. Exact crop boxes and original image hashes are recorded in
`contact-sheet-provenance.json`.

`local-raw-archive-index.json` maps the complete local archive's relative files,
sizes and SHA-256 hashes to original absolute capture paths. The compact
`artifact-index.json` covers this directory alone. Original JSON reports may
refer to local full-frame paths; a clean Git checkout contains their receipts
and contact sheets, not every raw image needed to repeat pixel measurement.

The final owned runtime was stopped before further reuse. Its last preclose
observation was 391,410 handles. The owned WM_CLOSE resulted in natural client
and server destruction; both processes were absent before the session was
finalized as stopped. See `final-runtime-stopped.json`; the retained original
`summary.json` describes the earlier evidence state and is intentionally not
rewritten.
