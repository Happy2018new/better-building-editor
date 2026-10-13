# Native poppy coordinate result R13 V3

The four predeclared native-only coordinates completed successfully in one
172.46311239997158-second launch. All four full stone-cell visual controls
and all four native poppy controls passed, with stable client/server raw
selection and collision observations. This supplies a native comparison
baseline for coordinate-dependent rendering. It does not establish a mesh
pivot, random-position hash, correction formula or production acceptance.
`POSITION_PLANT_PROXIES` remains empty; the separate centered poppy
native/projection fidelity comparison remains failed.

The executed plan SHA256 is
`7c47e75bc5b9021fd6d40416d4e783832c3b8bf428f6c6d694770aa713ac8101`.
Source baseline is `a025905`. Independent QA reviewed all 26 pinned inputs
and the native-only phase before launch; 17 focused host tests passed.
Unlaunched V1/V2 plans retain their original bytes. The complete V3 result
archive is `tools/data/native-plant-coordinates-result-r13-v3/`, containing
89 indexed files and 14,351,076 bytes, plus its index. This includes all
15 original PNGs, raw SDK observations, first-capture receipts, derived
masks, frozen source/input copies, project inventory, startup logs and
independent post-run restoration receipt.

## Observed native cells

Every coordinate used dirt one block below the target, the same fixed
relative camera `(-2,.15,-2.5)`, actual `GetForward` alignment greater than
.99, FOV getter 60 and screen 499 by 277. The physical capture stayed
1994 by 1105 with crop `(498,276,1495,828)`. The first stone/blank captures
had to match the previously frozen V3 full stone ROI before poppy could be
placed. Three-pixel recall/precision against that 113,706-pixel reference
are 1.0/1.0 for all four targets. The stone bounds are identical
`[306,115,683,455]`; the small area differences are retained unmodified.

| Target | Stone ROI pixels | Poppy pixels | Poppy image bounds |
| --- | ---: | ---: | --- |
| `(6,-48,6)` | 113,706 | 12,370 | `[462,225,608,416]` |
| `(7,-48,6)` | 113,701 | 11,388 | `[502,225,641,408]` |
| `(6,-48,7)` | 113,704 | 12,626 | `[339,225,490,410]` |
| `(-6,-48,-6)` | 113,705 | 12,351 | `[461,225,607,417]` |

Those image bounds describe the measured samples only; they do not feed
any geometry or translation fit. The four original poppy images visibly
show changing position relative to the unchanged stone-cell/camera frame.
These native images and API observations were acquired together rather
than inferring visible geometry from a successful palette read.

Raw server/client poppy selection clips agree before and after each capture:

| Target | Clip minimum | Clip maximum |
| --- | --- | --- |
| `(6,-48,6)` | `(6.066666603088379,-48,6.200000286102295)` | `(6.616666316986084,-47.400001525878906,6.75)` |
| `(7,-48,6)` | `(7.0333333015441895,-48,6.400000095367432)` | `(7.5833330154418945,-47.400001525878906,6.949999809265137)` |
| `(6,-48,7)` | `(6.400000095367432,-48,6.900000095367432)` | `(6.949999809265137,-47.400001525878906,7.449999809265137)` |
| `(-6,-48,-6)` | `(-5.933333396911621,-48,-5.799999713897705)` | `(-5.383333683013916,-47.400001525878906,-5.25)` |

All four collision boxes have both min/max `(0,0,0)`. This differs from
the nonempty ray-selection clips and is preserved as returned; collision
boxes and selection-box centers are not claimed to represent mesh pivots.
The sampled relative clip values reproduce the historical R9 poppy
observations at the corresponding X/Z coordinates, within original float
precision. That is a finite repetition observation, not a universal hash
or a supported native mesh offset API.

## Direct original-image inspection

All 15 original PNGs were opened directly: three startup images and all
four sets of stone, blank and poppy. The first scheduled startup image is
black/rejected; first SDK-ready shows loading; the separate application-ready
image shows the live grass world and HUD. Those first attempts remain
archived. The four stone images contain full visible cubes, the four blank
images contain only the separate dirt support at the target, and all four
poppy images visibly contain the native flower. Animals move elsewhere in
the grass world, outside the frozen target ROI; a small moving actor could
not meet the full stone coverage gate. Negative-coordinate outer terrain
is partly absent at the far image edge, while its entire target stone,
support and poppy remain visible and pass the same fixed ROI checks.

## Restoration, ownership and next boundary

Session `0b4a74d36e5c43369d64d80acd3a04a6`, owner
`snow-r13-centered-native`, used game PID 61716 creation identity
`134363486311636280` and MCDK PID 7940 identity
`134363486309359218`. All images used background WGC with no desktop
input, activation, resize or foreground fallback. The supervisor confirms
the exact owned processes dead and no cleanup errors; subsequent passive
host reads independently find both PIDs absent. The full 1,436-file BP/RP
inventory matches its original hashes, and all three host adapter/config
backup hashes are restored.

All four target/support pairs are verified air in both server and client
palettes, with actual client palette availability required. Each coordinate
restored its biome, time and daylight rule. Player position remains
`(.5,-60,.5)`, flight false. The original follow camera, FOV, locks and
position match after actual render events, the camera journal is removed
only after that readback and the render observer is removed. Both phase
and supervisor have empty cleanup error lists. The diagnostic completed
within its frozen 240-second total/190-second work bounds.

The next change needs a source-derived or documented geometry/position
contract frozen before independent holdout images. These results must not
be used to fit a screenshot translation or elevate AABB centers to mesh
pivots. Four native poppy samples cannot qualify arbitrary coordinates,
other plant families, snow heights, editor rendering or missing-mode
boundaries. No further cold launch is needed to preserve this checkpoint.
