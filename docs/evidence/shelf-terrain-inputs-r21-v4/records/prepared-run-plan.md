# Native Shelf Terrain Input Readback V4

Prepared and checked offline only. No game launch or capture by this worker.
Owner: `root-shelf-r20-terrain-inputs-v4`.

The clone is an exact frozen v3 copy with exactly one existing terrain fragment
changed. Native vertex, material registry, fields, discard, BYPASS and final
alpha remain unchanged. This diagnostic declares no TILE_LIGHT_COLOR uniform.

Eight 16px strips repeat every 128px in framebuffer x:

| Slot | Output |
| --- | --- |
| 0 | Yellow COLOR positive control |
| 1 | Actual interpolated native color.rgb |
| 2 | Magenta lightmap positive control |
| 3 | Actual texture2D(TEXTURE_1,uv1).rgb; effective white under ALWAYS_LIT |
| 4 | Cyan flag positive control |
| 5 | Flag encoding below |
| 6 | White final-RGB positive control |
| 7 | Original final diffuse.rgb |

Each flag channel is four bits divided by 15, hence byte steps of 17:
R = FANCY, FOG, ALWAYS_LIT, ALPHA_TEST;
G = BLEND, SEASONS, SEASONS_FAR, ALLOW_FADE;
B = TEXEL_AA, ATLAS_TEXTURE, TEXEL_AA_FEATURE, AS_ENTITY_RENDERER.
The order within each channel is bits 1, 2, 4 and 8. Use actual marker/data
pairs on the shelf body, not unsegmented projected-cell background counts.

Six focused tests pass. `compile.json` binds the exact frozen manifest and
expanded shader hashes: 26 native/candidate pairs, 52 programs, 832 pixel
checks. Synthetic fixtures exercise non-white COLOR and lightmap, all four
marker/data pairs, native final RGB and native alpha/discard/BYPASS under
GLES100/300. This does not qualify runtime input values or product appearance.

The `route-evidence` directory preserves both original v3 raw images, unchanged
acquisition report and independent strict shelf-body sky-ROI analysis. Native
south oak unpowered shelf selection of terrain_base is established for that
draw only; no other wood/state/UI inference follows.

Root schedules the minimum south native/empty run after reviewing this plan:

```powershell
python -B -X utf8 .runtime/shelf-terrain-inputs-r21-v4/run.py preflight
python -B -X utf8 .runtime/shelf-terrain-inputs-r21-v4/run.py start --scheduled-by-root
python -B -X utf8 .runtime/shelf-terrain-inputs-r21-v4/run.py capture
```

Start blocks unless zero live MC processes and at least 6 GiB available commit.
Keep its exact-exit watcher alive; capture runs separately after ready. Output
is `captures/south-inputs`. No proxy, AO, UI or west expansion is supported.
The acquisition restores fixture, environment, camera and workspace in finally.
New phases stop after 150 seconds, without a force process deadline.

```powershell
python -B -X utf8 .runtime/shelf-terrain-inputs-r21-v4/run.py stop
python -B -X utf8 .runtime/shelf-terrain-inputs-r21-v4/run.py finalize
```

Stop is force=False. Preserve a normal-close timeout, wait for both exact
identities to exit, then finalize. No live process or window mutation beyond
the normal owned-instance lifecycle is authorized by this preparation.
