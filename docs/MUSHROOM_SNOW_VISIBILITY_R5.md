# Mushroom Snow Visibility R5

This is historical failed-batch evidence. Fresh R7 acceptance of the revised
alpha-derived cutoff is recorded in [MUSHROOM_SNOW_VISIBILITY_R7.md](MUSHROOM_SNOW_VISIBILITY_R7.md).
The original R5 report and failure below remain unchanged.

## Immutable Live Batch

The original height-16 candidate was captured on NEMC 3.9.0.401155, runtime
1.21.120.0, in owned instance `e383e9833f774a648c94de9c620c28f6`.

- Report: `C:/Users/Happy2018new/.pyreact-debug/instances/e383e9833f774a648c94de9c620c28f6/artifacts/snow-mushrooms-all8-height16-r5.json`
- SHA256: `95e84ff62478cfe5db11d533e04866a01c0a98804168ca7cbfc9f5686a2dacc8`
- Completed, restored and source assets stable; no cleanup errors.
- Brown and red mushroom heights h0..h7: 16 independently captured covered cases.
- 34 nonblank comparison rows, including 26 independent captures and 8 reused
  snow-only controls with identical source, support, camera and daylight identity.
- Full and missing world projections: both scopes pass all rows. The exposed
  plant mask has recall 0.926471..0.945433 and precision 1.0 for the six visible
  h0..h2 cases. At h3..h7, native and projected exposed plant masks contain no pixels.
- Editor: 15/16 covered cases pass. Brown h3 fails
  `fully_covered_plant_stays_occluded` with 26 brown contribution pixels.
- Overall original batch: **failed**. This report is not overwritten by later fixes.

Fresh brown h2/h3 and red h2/h3 images were opened and inspected. Brown h3 shows
thin brown lines on the snow surface, absent from its snow-only editor control.
The 26 pixels occupy editor-crop bounds `[514, 236, 583, 252]`, inside crop
`[470, 355, 1540, 846]`. They contain mushroom colors `[145, 109, 85]` or
`[204, 153, 120]`, replacing white/cyan snow pixels. This is a visible artifact,
not a relaxed threshold or an accepted failure.

## Source-Derived Burial

The mushroom candidate models have origin Y 0, height 16 and full V 0..16 UVs.
Cross rotations, XZ span and mirrored UVs are unchanged. The installed native
textures and mappings are fingerprinted in
`tools/data/static_plant_sources_nemc_3.9.0.401155.json`.

| Plant | Native Alpha Bounds | Highest Opaque Y | h2 Snow | h3 Snow |
|---|---|---|---|---|
| brown_mushroom | `[4, 8, 12, 16]` | `1 - 8/16 = 0.5` | `0.375` | `0.5` |
| red_mushroom | `[4, 9, 12, 16]` | `1 - 9/16 = 0.4375` | `0.375` | `0.5` |

The brown texture SHA256 is
`f433e450abb552e61e2694caabad2eaa9f194419ad1e386967960d05850dff7d`.
Brown's highest occupied edge and h3 snow are exactly coplanar. The independent
alpha-derived h3 exposed geometry mask is empty, while the full crossed overlay
can still rasterize brown pixels at that surface in the editor.

The generator derives `STATIC_PLANT_MAX_Y` directly from native alpha top rows
and texture height. `prepare_palette` omits an additional renderer-only overlay
when the snow surface is at or above this bound. Native extra layers, state
records and the source document, including actor payloads, remain intact.
No model translation, texture shift, fitted offset, ROI expansion or threshold
change is involved.

The generator now emits only the two measured mushroom candidates. Its broader
source survey certifies native file identities and does not activate other
plant proxies. Unaccepted model/definition files are retained under this
worktree's `.runtime/unaccepted-static-plants-r5`, with the original 24-species
checkpoint preserved separately. Poppy remains unaccepted.

## Current Validation

Focused offline checks cover thin snow, the last exposed h2 layer, exact brown
h3 equality, red h3 above its alpha bound, higher snow, preserved layers/state
records and unchanged document actor payloads. The version bundle and generator
checks pass. Both mushroom models and block definitions are byte-identical to
the original batch's candidate checkpoint.

The cutoff change still requires fresh live captures of brown h0/h2/h3/h4 and
the red h2/h3 transition. The original batch does not certify this revised
rendering behavior; brown is not promoted on offline results alone.

## Native Box Probe

`tools/verify_native_plant_boxes.py` performs explicit session-bound raw clip and
collision reads without window, input, camera or screenshot calls. Its first
attempt after desktop handoff failed during `Client.__enter__` binding
verification while the owned game was minimized. It did not read the player,
reserve fixture cells or mutate the world. The preserved report is
`artifacts/native-plant-boxes-r5.json` in the same instance and has no native box
rows. It supplies no box comparison or random-offset acceptance evidence.
