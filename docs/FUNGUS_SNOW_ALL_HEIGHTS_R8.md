# Fungus Snow Visibility, Round 8

Crimson fungus and warped fungus now pass dry controls and all eight snow
heights at the two predefined views, in full and missing modes, with independent
editor plant-contribution controls. This extends the limited R7 boundary
acceptance using the existing centered-cross assets, whose four behavior/model
SHA256 values remain byte-identical. It does not establish an authoritative
native mesh or position-dependent random-offset algorithm.

The versioned acceptance manifest is
`tools/data/snow-fungus-all-height-acceptance-r8.json`. Its evidence partitions
preserve R7 boundary and R8 remaining-height provenance separately:

| Partition | Crimson Fungus Heights | Warped Fungus Heights | Nonblank Rows | Covered Editor Cases | Native PNGs |
| --- | --- | --- | --- | --- | --- |
| R7 boundary | 4, 5 | 3, 4 | 20 | 8 | 150 |
| R8 remaining | 0, 1, 2, 3, 6, 7 | 0, 1, 2, 5, 6, 7 | 52 | 24 | 374 |

Both partitions include their own dry controls. Together they provide 144
full/missing comparisons and 32 covered editor controls; every comparison
passes. Four R8 seven-row contact sheets were actually opened, and all four
reports were independently replayed from their original PNGs. The independent
capture audit found no integrity, cleanup, or binding-read failures.

The native cell remains `(-47, 117, -70)`. Public camera offset remains
`(-2, .15, -2.5)` and right offset `(2, .15, -2.5)`, with VFOV 66.6,
editor pose `(35, 10, 2.8)`, nominal fixture lift 16 and separate skyward
calibration lift 64. Recall/precision remain `.75/.75`, with the unchanged
three-pixel edge tolerance, fixed calibrated cell ROI, and independent native
snow masks for exposed-plant comparison. Acceptance is restricted to these
measured views and cell on NEMC 3.9.0.401155, runtime Minecraft 1.21.120.0.

The R8 audit preserves 18 ordinary switches between other applications. Every
affected frame is fresh, reliable, nonblank and owned-session-bound, and the
owned game remains background before and after. Foreground equality is a
diagnostic observation, not an added capture gate. No activation, resize,
desktop input, focus handoff or guard bypass was used. The guarded game and
MCDK processes exited normally through owned WM_CLOSE after capture.

The original R7 raw Combine omission report remains failed and unchanged:
native crimson fungus dry/h0 is visible while raw full/missing and independent
editor plant contribution are zero. Proxy acceptance does not reclassify this
unsupported native Combine behavior.

`tools/build_fungus_acceptance_r8.py` reproduces the acceptance manifest from the
unchanged versioned R7 acceptance manifest, R8 fixed matrix and independent
audit. It verifies original referenced artifacts, height partitions, views,
pixel gates, native cell, report cleanup, four independent replays and the
unchanged fungus render assets before writing the derived manifest.
