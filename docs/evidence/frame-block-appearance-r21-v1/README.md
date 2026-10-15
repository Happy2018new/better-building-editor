# Frame-block appearance diagnostics R21

Status: unqualified. The paired native/full/missing visible silhouettes pass,
but raw stone face interiors are consistently brighter in the projection.
Geometry agreement does not accept thickness, lighting, texture, glint or
production appearance. All production and native appearance gates stay false.

## Reproduce

`docs/evidence/frame-block-appearance-r21-v1/` preserves the unchanged raw
appearance report, eight ROI masks, three nearest-neighbor montages, an isolated
0.93 base-light experiment, frozen installed native sources, exact transitive
shader headers and offline tools. It binds the unchanged sibling
`frame-block-holdouts-r21-v1` manifest containing all 80 original PNGs.
No original runtime directory, game, MCDK session or credential is needed.

Requires Python, NumPy, SciPy and Pillow. Choose a fresh output directory:

```powershell
python -B -X utf8 docs/evidence/frame-block-appearance-r21-v1/replay.py replay docs/evidence/frame-block-appearance-r21-v1 .runtime/frame-block-appearance-replay-new
```

The replay checks every indexed byte in both bundles, the exact candidate
transformation and source bindings, recomputes all eight raw face metrics,
and compares every ROI and montage pixel. Add `--browser` with a Chromium or
Edge executable to repeat compilation using frozen headers and verifier:

```powershell
python -B -X utf8 docs/evidence/frame-block-appearance-r21-v1/replay.py replay docs/evidence/frame-block-appearance-r21-v1 .runtime/frame-block-appearance-replay-browser --browser "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
```

## Unchanged Appearance Failure

ROIs use predeclared quarter-cube face polygons intersected with the common
independently differenced native/full/missing silhouette. Both the face mask
and common silhouette are eroded two pixels, excluding frame-board/support
occlusion and face edges. All eight areas exceed 64 pixels. Comparisons use
the same screen pixels without registration, gain fitting or normalization.
The rows below are full/native; missing/native measurements are identical.
R, G and B are equal in this stone sample, so each mean/MAE applies to all
three channels. Luma is descriptive encoded Rec.709 weighting.

| Angle | Face | Pixels | Native mean | Product mean | MAE | Max delta | Texture correlation |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | y+ | 268 | 119.74627 | 128.68284 | 8.99627 | 19 | 0.98060 |
| 0 | z- | 4590 | 96.47146 | 103.38083 | 7.18998 | 24 | 0.96451 |
| -75 | x- | 2754 | 73.05374 | 78.19898 | 5.31373 | 22 | 0.95484 |
| -75 | y+ | 178 | 117.98315 | 126.52247 | 8.84270 | 19 | 0.95936 |
| -75 | z- | 803 | 96.47696 | 103.42092 | 7.21295 | 24 | 0.95149 |
| +75 | x+ | 2686 | 72.74572 | 77.89092 | 5.18764 | 28 | 0.98136 |
| +75 | y+ | 172 | 117.12209 | 126.20930 | 9.08721 | 25 | 0.98386 |
| +75 | z- | 815 | 96.63681 | 103.72883 | 7.35460 | 25 | 0.95386 |

Product/native mean gains span 1.0704-1.0776, and no ROI has identical pixels.
Manual stone montage inspection finds broadly corresponding texture patterns
and a clear brightness difference. Correlation 0.951-0.984 and maximum raw
differences up to 28 do not establish exact texture or UV fidelity.
Different source texels also prevent using face mean ratios as independent
measurements of directional shading coefficients.

All nine enchanted-quartz shown images visibly contain pink/purple glint on
the volumetric top and lateral faces. Native and candidate stills have
different patterns, particularly at -75 degrees. These sequential captures
have different animation phases; they do not accept absolute static color,
glint brightness, direction, motion or UV mapping. Ordinary `minecraft:quartz`
remains a distinct flat item.

## Lighting Source Trace

The exact installed 3.10.0.420447 `entityVertexUtil.h` standard FANCY branch
has the same directional expression as candidate `frameIntensity`:

```glsl
(1.0 + Ny*TILE_LIGHT_COLOR.w)*0.275
    - Nx*Nx*0.1 + Nz*Nz*0.1 + 0.45
```

When TILE_LIGHT_COLOR.w is one, top/bottom/x-side/z-side factors are
1/0.45/0.625/0.825. Native RNGL_UNLIT or non-FANCY instead returns one;
RNGL_LIGHT uses another directional expression. FLIP_BACKFACES and
USE_OVERLAY can also affect native results. The actual ordinary stone
item-frame material route and flags were not recorded, so source similarity
does not prove the branch executed during capture.

Native `getLightColor` multiplies TILE_LIGHT_COLOR.xyz. `entityCommonFrag`
also multiplies vertex color under COLOR_BASED and has ITEM_IN_HAND tint
routes; installed `item_in_hand:entity` declares COLOR_BASED, NO_TEXTURE,
ITEM_IN_HAND and a Color vertex field. `entity.fragment` applies fog before
glint. The specialized candidate fragment has no corresponding vertex COLOR
term or explicit fog multiplication. Actual native vertex colors, uniforms,
fog and route were not observed. The cause of the stable brightness surplus
is unresolved; no native 0.93 constant was discovered.

Setup source asserts clear weather and frozen time 6000. The capture report's
environment is the saved prior state, not an independent setup readback.
This one asserted noon condition does not establish other lighting states.
The packaged native files are later source snapshots, not original runtime
uniform or material observations.

## Isolated Empirical Candidate

`candidate/` is a resource override subset, not a runnable prepared project.
Its metadata identifies generator v2 and the original unchanged frozen source
digest 36d897c8bd8e190c83d117b2c5ddc3c9feb454092b0e7f0a145c061c410c2c49.
Only `modern_projection_frame_block_opaque.fragment` differs:

```glsl
float frameBlockBaseLight=itemFrame>0.5 ? 0.93 : 1.0;
vec3 rgb=texel.rgb*itemLight*frameBlockBaseLight;
```

0.93 is a rounded empirical inverse suggested by the current eight ROI
brightness gains and the earlier flat-item gain approximately 1.0763. It is
an experiment, not a native constant or accepted correction. All eight ROIs
are training diagnostics. The independent glint term, alpha, positions,
normals, fixed scale 0.25 and center Z 0.4375 remain byte-identical. No
production shader, frame-body, flat-item or Shelf resource was modified.
The old raw failure measurements have not been postprocessed or replaced.

The original candidate-v2 compile report was independently reproduced using
the packaged candidate, frozen verifier/import closure and frozen transitive
engine headers. All 30 GLES2/3 variants compile and link; each version passes
96 UV samples and 4608 position plus 4608 normal samples over 48 poses.
Installed skeletal headers require GLES3 non-square matrices; GLES2 skinning
remains outside this verification. These checks do not accept native pixels.

## Required Holdouts

Use different ordinary items and new camera angles with same-session actual
native references and unchanged raw RGB thresholds. Keep source texture
samples, native frame-body controls and unchanged Shelf controls. Repeat
changed world-light conditions and separately compare artificial block glint
animation. Capture native material/vertex/light factors where observable.
No current ROI may be reused as held-out acceptance evidence.

Frame-backboard occlusion still confounds ideal absolute-depth fitting.
Six frame faces, eight rotations, editor pixels and world lifecycle remain
open. Production admission also needs an explicit validated `(name, aux)`
whitelist; opaque material support alone must not admit all 324 candidates.
