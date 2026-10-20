# Centered Snow Plant Product Profile

**2026-10-19 scope update:** the static implementation described below remains
the current baseline. The user's explicit OB-01 requirement now includes firefly
bush animation in the editor and projection. The historical exclusion below
does not close or remove that requirement. Texture animation and independent
fireflies are tracked separately in [the R23 investigation](FIREFLY_BUSH_R23.md);
its offline resource candidates have not acquired runtime acceptance.

The product's declared plant position is fixed at the cell center. Native
random offsets are not part of this snapshot editor's design. The earlier
native-coordinate and silhouette comparisons remain intact diagnostics; their
random-offset disagreement does not decide whether the centered product works.

## Responsibilities

- `centered_plant_data.py` owns the versioned product mapping and opaque alpha
  top of all 29 supported snow plant names, including grass and fern.
- The existing short grass / fern and tall-half meshes keep their established
  centered geometry. The schema-2 source profile fingerprints grass / fern's
  original model bytes and original atlas textures; their alpha tops account
  for the retained 0.8-block mesh height. The other 27 names use generated
  unit-height meshes. Native snow capability remains the separately measured table.
- `geometry_palette.py` only selects these render proxies and temporary snow
  overlays. It does not change document foreground, background, actor data or
  saved material identity. Burial uses `(snow height + 1) / 8 >= alpha top`.
- `generate_centered_plant_profiles.py` owns vanilla resource collection and
  regeneration. Its input path follows the registry manifest's NEMC version.
  It checks the dump fingerprint, source atlas, texture bytes, texture alpha,
  fixed-centered style, cross template and retained original mesh metadata.
- `plant_proxy_data.py` and the four historical `preview_*` mushroom/fungus
  resources remain untouched for old native diagnostics. Their historical
  acceptance version no longer blocks current product rendering. Both old and
  current render-only identifiers stay excluded from the material picker.

The 27 generated crosses reuse the established centered template with unit
height, no X/Z translation, an X/Z span of 0.1..0.9 and the original vanilla
texture alpha. There is no coordinate-offset table or per-position fitted mesh.
Bush retains the grass colormap. Open eyeblossom and firefly bush use the
vanilla carried texture, which is the static combined visual of their multiple
atlas layers. The snapshot does not simulate day/night state changes, particles
or firefly animation. This scope does not claim separate animated emissive
material acceptance.

## Validation

The new offline tests cover all 29 supported names in strict and automatic
layer erasure, undo preservation, all eight snow heights for all 27 generated
plants and the two retained original meshes, layer-order normalization,
positive/negative render origins, geometry containment and stale source
rejection. The visual alpha source contract covers all 29 names, including
grass / fern; neither can silently fall back to an unversioned texture path.
The existing geometry, editor,
render-context, native-source diagnostic and bridge tests continue to run.

`verify_centered_snow_profiles.py` is the separate product visual suite. It
extracts individual cells from the existing public `test.layers.snow` blueprint
and verifies:

- Dry plants against the actual mesh and pinned original texture alpha,
  independently projected into the editor and calibrated world camera.
- Thin snow, immediately before/at alpha burial, and complete snow coverage.
- Independent full and missing projection captures in empty world cells.
- Snow retained at its own control position, visible plant retained above
  snow, buried plant absent, and no extra geometry outside the unit cell.
- Editor cutaway against an independently captured empty editor control.

All visual calls are SDK-only. Capture is owner-bound WGC at native resolution;
there is no window activation, resizing or desktop input. The suite reserves
625 preflight-verified air cells for a black concrete background, at least
12 blocks from the tested cell. Each attempted write is journaled beforehand;
cleanup restores air and verifies both native palette layers and actor absence.
The background does not alter the tested cell's native neighbor relationships.
The suite requires a passing stone camera calibration from the
same managed game. Missing, tiny or shifted plant masks fail its controls.

`native_draw_response.py` observes actual `GameRenderTickEvent` callbacks and
requires visible pixel responses as well as the pictured native debug clock
to advance. The ordinary inspector header must visibly hide and return to its
original pixels before the matrix can start. Every full/missing projection
hide control has a six-second response bound. Only read-only frame/capture
polls repeat; native visibility mutations are not replayed. A compositor's
fresh frame timestamp or a successful API return alone cannot pass these gates.

**Live acceptance is pending.** The first guarded startup on 2026-10-13 exited
before the game/session binding at 41.516 seconds. No product screenshot or
visual gate was obtained. The owned game and MCDK identities were recovered
and removed with no cleanup errors, and the other application's foreground
was unchanged. Other lanes reported the same full-resource startup failure;
repeating equivalent launches was paused for shared diagnosis.

The retained first attempt is in the specialist's ignored
`.runtime/snow-centered-r14-product-v1/` directory. Its supervisor bound exactly
one launch, approved MCDK / guard / WGC hashes, a 2700-second total cap and
0.5-second background checks. Old native failure captures and acceptance
manifests have not been rewritten as product passes.

Subsequent attempts retain their original failure reports:

| Attempt | Observed Result | Interpretation |
| --- | --- | --- |
| v2 | Minimal short grass shape, thin snow and cutaway passed; outside-cell gate failed | 2,379 full-mode difference pixels were a changing distant terrain edge and 485 a moving pig; original FAIL remains |
| v3 | 30 boundary rows completed; fern h5 world upper retention failed | Camera eye was below the snow surface; the Y-only alpha oracle could not represent foreground snow occlusion from below |
| v4 | Above-snow view had poor dry grass contrast; one missing-mode hidden screenshot retained the object | Compositor receipt was fresh but the pictured native debug time was unchanged; reliable native draw response was not proved |
| v5 | Front and tilted cube calibration passed, right calibration failed | A moving horse behind the cube touched the extracted right edge; strict outline thresholds were retained |
| v6 | All elevated skyward calibration views passed; backdrop setup rejected the palette | Host tool incorrectly assumed XYZ volume order; actual SDK contract is ZXY. No block writes occurred, cleanup succeeded |

v7 uses the elevated skyward cube calibration, above-snow plant camera and
distant contrast background. Its minimal short-grass h0 suite passed in the
editor, full and missing projections, including independent native UI and
projection response gates. The 30-row short-grass / fern / poppy boundary
matrix also passed with zero failed rows, including fern at h5 and complete
burial. Its editor cutaway had exactly zero residual object pixels. Both
stages restored all settings and their 625-cell distant background. The
all-eight-height matrix then passed all 54 rows for the same three plants,
again with zero failed rows and successful restoration. The 29-name catalogue
completed 141 rows with six failed rows before a read-only native render-frame
query timed out through IPC. Its report is incomplete and failed. Background,
navigation, weather and time restoration succeeded; the exact owned game and
MCDK identities were removed with no cleanup errors. The earlier failures do
not become passes when their causes are understood.

The retained v7 reports and representative exact native screenshots are in
`docs/evidence/centered-snow-product-r14-v7/`. Its manifest fingerprints the
original reports; the full original captures remain in the specialist's
ignored runtime directory. Three follow-ups are required before acceptance:

- Blue orchid and lily-of-the-valley use asymmetric texture alpha. The current
  oracle incorrectly unions each front-face alpha with a mirrored copy. The
  actual signed south UV and opposite geometric winding make the two faces
  coincide. A model-derived signed-UV oracle must replace this union, with
  asymmetric and cropped-UV negative controls. Derived reanalysis must retain
  the original failed reports and cannot select a mapping from observed pixels.
- Bush at snow h4 passes the cell hull and upper-retention checks, but some dry
  leaf tips project above the distant black background onto green terrain.
  Their contrast is below the existing difference threshold, so the dry control
  misses pixels made visible by white snow. Raise the background and validate
  its full projected cell coverage; retain the original threshold and FAIL.
- Crimson roots' first editor display is actually blank even though its source
  reports one block. Later snow controls show the roots. Require a bounded real
  native Scene response after source readiness, then run a targeted editor and
  independent full/missing projection retest. Source state alone is not visual
  acceptance. The original blank screenshot remains a failed result.

Only read-only frame observations may retry an IPC timeout. Visibility changes,
world writes and launch operations must never be replayed by that retry path.
The targeted corrected matrix and the remaining catalogue are still pending.

## Version Updates

After updating the block registry and native snow capability sources, point
the generator at the new installed `data/resource_packs/vanilla` directory:

```powershell
python -X utf8 tools/generate_centered_plant_profiles.py `
  --native-resource-root '<new vanilla resource directory>' --refresh-source
python -X utf8 tools/generate_centered_plant_profiles.py `
  --native-resource-root '<new vanilla resource directory>' --check
```

The versioned source JSON, generated table and assets are reviewable diffs.
Unexpected texture variants, non-static texture dimensions or atlas changes
fail collection instead of guessing a mesh. Run the offline tests, then the
built-in editor product suite and its separate full/missing projection matrix.
Historical native jitter measurements do not need to be re-qualified to
regenerate the current centered plant profile.
