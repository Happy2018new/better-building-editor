# Native banner editor depth diagnostic

Updated: 2026-10-14 17:13 Asia/Shanghai. Runtime: `3.10.0.420447`.

## Result and admission boundary

The isolated v6b banner/pole candidate fixes the observed editor depth mismatch
for the measured fixtures. Standing and wall banners retain their real-item
colors and patterns, wall supports occlude correctly from opposite views, and
the view-depth cut plane removes and restores banner geometry with terrain.
This is a successful candidate diagnostic, **not production editor admission**.
Production `scene_names` still contains only the previously qualified flower
pot. No banner shader or material from this diagnostic was copied into the
production resource pack.

World-only standing/wall banner admission and render-only direction adaptation
are separate, documented in `BANNER_WORLD_QUALIFICATION.md`. The adapter changes
the render actor copy and preserves the saved NBT and typed pattern payload.

## Why earlier candidates failed

The v3 local-position expression discarded the per-cell actor translation in
`WORLDVIEW`. Occlusion then depended incorrectly on where a banner was placed.
The v4 expression retained that translation but assumed the terrain's camera
origin and native-to-block scale. It still gave incorrect front occlusion.

We encoded the actual native shader matrix translation and view-axis length as
numeric colors, captured them through Windows Graphics Capture, and decoded
the samples offline. `native-banner-depth-measurements.json` preserves the
sample pixels, screenshot hashes, cameras, quantization, and derived values.
`tools/analyze_native_preview_depth_r15.py` reproduces the calculation.

The wall samples at zoom 1 and 2 give an intercept of -100 for
`WORLDVIEW[3][2]+350`, so the banner family's view origin is 450. Standing
samples at x=1,6,11 give two equal five-block steps. Their matrix scale yields
native-to-block scale approximately 0.6399078. The candidate uses 0.64, within
the measured matrix/pixel quantization.

These values belong to the **native banner/pole family on this runtime**. They
must not be applied to chests, beds, heads, generic actors, or a newer runtime
without an independent measurement and qualification.

## Candidate implementation

`tools/generate_native_preview_depth_r15.py` generated the candidate in the
isolated project `D:/bbe-r15-native-production` with:

```powershell
python tools/generate_native_preview_depth_r15.py --output D:/bbe-r15-native-production --depth-mode worldview --block-scale 0.64 --view-origin 450
```

The tagged orthographic editor branch reconstructs actor view depth as
`((WORLDVIEW*localPosition).z+450)/length(viewZ)*0.64+packetDistance` and uses
the existing terrain depth affine mapping. The native fragment discards only
when this editor clip value is nonnegative; other branches initialize it to
-1. The generic actor override was explicitly removed from v6b. All new
float precision and varyings use `highp`.

Candidate SHA-256:

| Source | SHA-256 |
| --- | --- |
| Banner vertex | `20656dc740939393e69199846f10011c93a43639c97528fc4c8c67bc31e2c738` |
| Banner fragment | `1737573e3092d66cf148557ee7b8d9d3f7a9a6ffe0c132ded9d06c488ff2cb6e` |
| Installed native banner vertex, normalized UTF-8/LF | `6bb2d84bfdb07bae48e297a631d3b2d139ffea1c8745d4e8ea1becf9c88136e2` |

`depth-candidate-v6b-sources/` preserves the candidate vertex/fragment, native
baseline diffs, source receipt, and sanitized owner-stop receipt. The copied
source snapshots normalize line endings/trailing whitespace; their hashes are
recorded separately and their normalized text was checked equal to the live
candidate. The generator reproduces the raw tested source.

`depth-candidate-v6b-compile/compile.json` records GLSL100/300 compile checks.
GLSL100 skinned vertices retain the installed native header's unsupported
`mat3x4` failure, with an identical failing baseline. This inherited variant
was not fixed or declared passing. GLSL300 variants and unskinned GLSL100
variants compiled; the Windows game rendered the candidate.

## Opened live screenshots

All listed frames were actually opened and inspected. Their reports bind each
capture to the owner/session and geometry upload. Uploads use unique geometry
names to prevent stale native GPU-cache results. The source is the genuine
inventory-placed payload from `102-real-banner-payloads/report.json`: base 4,
with 0, 3, and 6 real patterns.

| Evidence directory | Observation |
| --- | --- |
| `159-depth-v6b-wall-back-frame` | All three rear-view supports correctly occlude the upper cloth. |
| `161-depth-v6b-wall-front-frame` | All three opposite-view cloth bodies and patterns appear in front of their supports. |
| `166-depth-v6b-wall-cut-plane` | Yaw35/pitch25/zoom3, depth12.5: left retained, middle cloth cut to a triangle, right removed. Settled plane recorded. |
| `168-depth-v6b-wall-restored-frame` | Depth0 restores all wall cloth/supports; settled plane is null. |
| `170-depth-v6b-standing-frame` | Three standing banners, poles and supports at yaw35/pitch25/zoom2; all three pattern cases visible. |
| `172-depth-v6b-standing-opposite-frame` | Opposite yaw215/pitch25/zoom3; all banners appear, but the zoom clips part of the row at the viewport edge. |
| `174-depth-v6b-standing-cut-frame` | Depth12.5 hides all standing fixture geometry, consistent with the recorded plane. |
| `176-depth-v6b-standing-partial-frame` | Depth17.5 also hides all geometry; this was an exploratory plane position, not a partial-cut acceptance case. |
| `178-depth-v6b-standing-partial-frame` | Depth7.5 retains one banner and removes the other two. |
| `180-depth-v6b-standing-cross-frame` | Depth8.5 cuts the retained cloth/pole diagonally while retaining lower support geometry. |
| `182-depth-v6b-standing-restored-frame` | Depth0 restores the opposite-view standing fixture. |

`audit_native_coordinates_r15.py` now records settled `editor_depth` and
`editor_depth_plane`. Immediate setter receipts can contain the old plane
because view interpolation has not advanced; acceptance uses the later capture
receipts. The candidate did not require desktop input, activation, resizing,
or an in-game focus pause.

## Remaining work

1. Independently review the measured constants and candidate shader before
   production integration. Store runtime/source identity with the family
   adapter so a version update fails closed rather than silently reusing it.
2. Run the exact v6b material in world full/missing/occupied/restored modes.
   Earlier world qualification used the production baseline, not this shader.
3. Qualify editor rotations/mirrors, layer modes and zoom controls with the
   production material. Data/actor direction tests do not replace these pixels.
4. Check temporal banner motion separately. Static frames do not establish
   waving, and source-world banner visibility was unreliable in earlier runs.
5. Keep generic-actor families on their current qualified routes until each
   family's depth contract is measured independently.

The v6b session `24ab046fdeca42e0a8bb417cc42cad5e` (owner
`native-render310-r15`, game PID46684) was stopped normally at approximately
17:12. Its last observed handle count was 274022, below the 400000 ceiling. This
fresh session only loaded documents; no source-world or occupancy journal
needed restoration. All earlier owned banner/head source journals had already
been restored before retiring their corresponding sessions.
