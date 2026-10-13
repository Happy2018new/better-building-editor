# Centered Snow Plant Product Profile

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
there is no window activation, resizing, desktop input or real-world block
placement. The suite requires a passing stone camera calibration from the
same managed game. Missing, tiny or shifted plant masks fail its controls.

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
