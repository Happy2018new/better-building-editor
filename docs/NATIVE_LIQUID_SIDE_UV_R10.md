# Native Liquid Side UV And Cadence R10

## Result

The frozen native side-artwork/cadence measurement **failed**. No side UV,
replicate interpretation, animation cadence, full UV or production accuracy is
accepted. All 1,474,560 predeclared hypotheses were tested without adjusting
the sample grid, independent camera, candidate, roles, or numeric gates.

The best rejected fit was SW quadrant, stretched V, 90-degree rotation,
one tick per frame, no blending, phase 6.375, pixel centers. It is a rejected
model output, not a finding about the engine's native mapping.

| Scoring Scope | RGB RMSE | Explained Variance | Texture RMS |
| --- | ---: | ---: | ---: |
| Depth 0 training | 18.8797 | 0.0405 | 2.5999 |
| Depth 0 temporal holdout | 19.1577 | 0.0078 | 1.8592 |
| Depth 1 geometry/temporal holdout | 11.6346 | 0.0032 | 0.5240 |
| Depth 3 geometry/temporal holdout | 8.1877 | -0.0058 | 0.9399 |

Aggregate holdout RGB RMSE is 13.7770. Frozen gates require RMSE <= 3.0,
explained variance >= 0.9, texture RMS >= 2.0, and property margin >= 0.5.
V-basis, region-scale, and cadence margins are respectively 0.0203, 0.2926,
and 0.0729; all three remain unidentified. Rejection of incorrect alternatives
does not identify the best hypothesis when the best hypothesis also fails.

## Independent Prerequisites

Guarded startup and same-session stone calibration are documented separately
in `docs/GUARDED_BACKGROUND_STARTUP_R10.md`, commit `d7c13ad`. Calibration is
completed, passed and restored, common vertical FOV 66.6, no cleanup errors.

The exact `minecraft:water` / `SetBlockNew` source was captured with native
flow suppressed and exact foreground/background states verified before and
after every frame on both server and client. Three depths, 0/1/3, each have
four static controls and 16 temporal frames (4 calibration, 6 training, 6
holdout). Depth 0 selects hypotheses; depths 1 and 3 are geometry holdouts.

The independent frozen candidate outer-silhouette prerequisite passed:

| Depth | Native Pixels | Mask IoU | Outline Recall | Outline Precision |
| --- | ---: | ---: | ---: | ---: |
| 0 | 88,582 | 0.984128 | 1.0 | 1.0 |
| 1 | 61,210 | 0.983174 | 1.0 | 1.0 |
| 3 | 55,331 | 0.983464 | 1.0 | 1.0 |

The unchanged outline tolerance is 3 native pixels. This accepts only those
explicit pure-water outer silhouettes, not hidden faces, overlaid bodies,
other depths, a flowing alias, tint, alpha, or production geometry.

## Frozen Experiment And Audit

The first host attempt rejected a project-binding mismatch before environment
or world mutations. The second rejected deepslate in the old underground
reservation, restored all temporary editor/environment state, and made no
owned reservation or flow change. Both failure reports remain intact.

V3 translates the entire source/camera/background fixture to declared origin
`(6,96,6)`, with camera offset `(-2.5,2,-3.5)` and the same remote quartz board
at source Y-3. It does not change the source height neighborhood. The new air
reservation passed before any writes. Original R9 and R10 V1/V2 plans remain.

The hypotheses were full/NW/NE/SW/SE regions, bottom/top/stretched V, all eight
rotations/reflections, ticks 1/2/3/4/5/10, blended/unblended animation, pixel
centers/edges, and 16 phase steps per source frame. The native bitmap contains
32 square frames; installed metadata declares replicate 2 but no explicit
ticks per frame. Metadata is not used as proof of native cadence or UV.

All 60 captured water PNGs pass the independent audit: 1994x1105 PNG encoding,
SHA256, current owner/process binding, approved WGC helper, fresh frame QPC,
nonblank background capture and owned game remaining background. Every
foreground observation is unchanged. Native handle count peaked at 833.
Actual temporal spans are 85.647/119.907/161.385 seconds, using WGC frame QPC,
not requested delay durations. Fixed-grid overlays were generated and opened;
they do not move or fit any sampling point.

All fixture, flow, player, camera, editor, capture options and environment
restoration gates passed. The owned instance was normally stopped around
09:13 Asia/Shanghai. No desktop input, activation, focus restoration, resource
edit, capture retry, or hibernation was used.

## Bounded Host Diagnostics

Two new offline reports reuse the exact frozen contract, PNGs, camera, grid,
QPC and frame roles. They do not change the original 1,474,560-hypothesis
failure, perform native calls, or add native captures. Only the frozen rejected
best and its original three property alternatives are considered.

The first report shows that the rejected shared photometric model already
fails its own calibration observations, with RGB RMSE 19.2960/11.6133/8.1193
for depths 0/1/3. Shared constant-background null training RMSE is
19.2736/11.6127/8.1619; separate north/west null fits only reduce it to
19.2248/11.5981/8.1565. A simple constant difference between side lighting
therefore does not explain the large residual.

The four static controls approximately satisfy
`supported_positive - liquid_only = transmission * (supported_negative - empty)`.
Fitted transmissions are 0.3381/0.3337/0.3294, with RGB RMSE
2.8394/2.5967/2.3751. This is a limited control comparison, not an accepted
opacity or tint model. Native per-point temporal RMS across the 16 captures is
only 1.9273/1.7258/1.5178. The static spatial residual dominates that signal.

The second report fits one constant RGB offset per point and one shared RGB
gain per sequence from the four calibration frames only. Gain keeps the
original [0,2] bounds. All fitted values are then frozen; only depth 0 training
selects among the four candidates, and all three temporal holdouts remain
untouched. Offsets remove static spatial discrimination, so this is a temporal
diagnostic and cannot identify complete UV.

| Holdout Depth | Calibration-Only Constant RMSE | Animated Diagnostic RMSE | Explained Variance Over Constant | Scaled Temporal RMS |
| --- | ---: | ---: | ---: | ---: |
| 0 | 2.2800 | 2.2811 | -0.0009 | 0.0160 |
| 1 | 1.7895 | 1.8214 | -0.0359 | 0.2688 |
| 3 | 1.5554 | 1.5576 | -0.0029 | 0.0534 |

The former region-scale alternative has the smallest diagnostic training RMSE
2.3810, versus constant-only 2.3815. The training explained variance is
0.000394 and runner-up margin is 0.000469, far below the unchanged 0.9 and
0.5 requirements. Its RGB gains are `[0,0.000355,0.002580]`,
`[0.002369,0.029964,0.035894]`, and `[0.000568,0.004140,0.008232]`.
Aggregate animated holdout RMSE is 1.9102, versus constant-only 1.8991.
Although absolute RMSE now meets 3.0, all held-out explained variances are
negative and scaled temporal RMS is below 2.0. The animated candidates explain
no held-out signal beyond the calibration-only baseline. These coupled
alternatives do not isolate individual UV or clock properties.

The frozen rejected best itself has zero fitted gain at depths 0/1 and tiny
gain at depth 3. This result locates a demonstrated failure in the shared
photometric assumption; it does not attribute the residual to native engine
UV, cadence, filtering, lighting, or another unmeasured mechanism.

### Sampling And Variance Limits

Under the original rejected SW mapping, the complete source strip has
per-point temporal RMS 11.0016. Calibration variance is 86.08%/84.38%/75.87%
of full-strip variance, so the fitted templates are not flat over calibration.
Across the four candidates, complete-strip RMS ranges from 10.3372 to 14.0334.
The available artwork has substantial variance, while captured native
holdout temporal RMS is only 1.7767/1.5533/1.2836.

Minimum distances between declared screen samples are 10.6605/4.5121/3.2160
native pixels. Under the rejected SW mapping, adjacent grid pairs imply at
least 4.7380/2.0054/1.4294 native pixels per source texel. The full-region
alternative can be smaller than a native pixel per texel on shallow rows,
with minima 0.9400/0.6700 at depths 1/3. These are camera/grid calculations
under rejected hypotheses, not a measurement of native texture filtering.

Only three or four primary source-frame indices are represented by the four
calibration captures under these clocks, and four to six primary indices by
each six-frame holdout. Blended alternatives can contribute adjacent frames,
but the capture set is not complete 32-frame coverage. There are no repeat
captures at a verified native phase, so the native noise floor and animation
amplitude cannot be separated. Sample spacing and source variance alone do
not establish sufficient native cadence discrimination.

Both diagnostic arithmetic checks recover injected source-artwork hypotheses
and gains on the same grid/QPC. The first keeps the original measurement core
and recovers gain `[0.25,0.3,0.4]`, bias `[4,7,3]`, opacity 0.6, with training
RMSE 3.53e-11 and holdout 1.32e-10. The second injects the same gains with a
varying static per-point baseline and recovers them using calibration only,
with training RMSE 1.57e-14 and holdout 1.44e-14. These synthetic checks reuse
template helpers and verify arithmetic and split isolation only; they are
not independent native evidence. All native acceptance flags remain false.

## Installed Source Audit

Read-only installed NEMC `3.9.0.401155` resources map both `water` and
`flowing_water` north/south/east/west faces to `flowing_water_grey`, resolved
through `terrain_texture.json` to `textures/blocks/water_flow_grey.png` with
`quad: 1`. Up/down map to `still_water_grey` and
`textures/blocks/water_still_grey.png`. The still strip explicitly declares
two ticks per frame; the flow strip declares `replicate: 2` and omits cadence.
The snow project has no override for either native water alias, bitmap, or
flipbook. Its retained original world pack list contains the project resource
UUID only and points by junction to the frozen snow resource pack.

Root separately queried loaded initial textures in a later owned session:
`GetBlockTextures` exists and returns those same nominal names/paths for water
and flowing water, runtime `1.21.120.0`. `GetTextureAtlasUV` is unavailable.
This receipt is at
`D:/Happy2018newの个人文件/GitHub/better-building-editor/.runtime/scaffold-r10/loaded-water-textures-r10.json`,
SHA256 `4f120e26752b8f5263a03860be990cf23f8c53ffa5fe9cb3c9c40f2308db0034`.
It establishes initial lookup, not the original capture's active material or
the bitmap actually sampled by a specialized water renderer.

The installed `vanilla_netease` pack also defines `netease_water_texture` in
its terrain atlas, targeting an opaque 32x32 static PNG. Its
`materials/terrain.material` declares `netease_water_near` and
`netease_water_far`, both inheriting `terrain_blend`. The inherited material
enables BLEND/Blending and underwater/fog variants; precompile configuration
lists base, fading, fog, fog.underwater, and lit variants for both. Source
comments require `MATERIAL_ENABLE` to use/override these water materials,
with the local define commented out. File presence and precompile entries
therefore do not establish the active material or backend.

Both installed GLSL fragment shaders first sample `uv0`, then overwrite RGB
from `TEXTURE_0` using:

```text
u = range.x + (range.y - range.x) * mod(VertexWorldPos.x, 6) / 6
v = range.z + (range.w - range.z) * mod(VertexWorldPos.z, 6) / 6
diffuse.rgb = texture2D(TEXTURE_0, (u, v)).rgb
```

`WATER_TEXTURE_UV_RANGE` has Float4 declarations in `uniforms.json`,
`netease_editor_uniforms.json`, and the GLSL uniform header. No default value,
atlas-key assignment, or setter was found in installed text sources. The
matching vertex shaders assign `VertexWorldPos` from chunk-modulo position
plus two TIME-dependent wave displacements. Neither native TIME, the actual
uniform range, nor the active material was captured. Raw world X/Z modulo six
is consequently an incomplete conditional model of these shader sources.

One bounded offline report tests that exact raw-grid X/Z mapping against the
installed Netease bitmap, using normalized texture-edge coordinates and
bilinear edge-clamped sampling. It fits only the original shared photometric
coefficients on calibration frames; there is one mapping and no source,
rotation, phase, offset, or UV selection. This candidate also fails:

| Depth | Calibration RMSE | Holdout RMSE | Holdout Explained Variance |
| --- | ---: | ---: | ---: |
| 0 | 19.3583 | 19.1741 | 0.0061 |
| 1 | 11.5538 | 11.5675 | 0.0147 |
| 3 | 8.1484 | 8.1369 | 0.0066 |

Synthetic shared-model prediction and raw-grid six-block periodicity checks
pass. Raw template shifts by one X/Z block differ by RMS 18.8395/20.7617;
six-block shifts agree to numerical precision. These are conditional template
properties only. Native wave displacement itself need not repeat at six
blocks, so a future translation experiment must account for the actual
vertex inputs before interpreting this periodicity as a native prediction.

All installed source paths and SHA256 values are preserved in that report's
`source_files`. Principal hashes, under
`D:/MCStudioDownload/game/MinecraftPE_Netease/3.9.0.401155/data/resource_packs/vanilla_netease/`,
are:

| Installed Source | SHA256 |
| --- | --- |
| `textures/terrain_texture.json` | `2a49e7d28d5df7e460cb129d050a2adc60e29c92615c19a14893ab95a6722ae0` |
| `textures/blocks/netease_water_texture.png` | `3dda145367c3aa66631875553caf7d65edbd7d4bbdcd1809cac3f0dc3695d975` |
| `materials/terrain.material` | `9c481e542404f4a1fecbc5ddec3e7073e5e36a3e9edfd149180ecc9eb2bafb66` |
| `shaders/glsl/renderchunk_water_near.fragment` and `far.fragment` | `584da4f8176795d1be37cf0e053a5f9a76069e523055121ed0ea409ab4f2026e` |
| `shaders/glsl/renderchunk_water_near.vertex` and `far.vertex` | `e6c494cf485f4fd3221d482d2d0cbdd07c8027c764de8b3bac73e8f7c5154a0a` |

## Cold Source Marker Checkpoint

Root authorized one cold bitmap-source diagnostic after releasing the shared
snow project. Private assets preserve native image dimensions and opaque
alpha: still-water 16x512 pure red, flow-water 32x1024 pure green, and Netease
water 32x32 pure blue. Only these three project PNG paths were temporarily
installed; no shader, atlas, flipbook, resource-pack manifest, or `.mcdev.json`
was edited. Original project absence and the full resource manifest were
recorded before installation. Generated assets and the exact plan remain in
`D:/Happy2018newの个人文件/GitHub/better-building-editor/.runtime/r9-snow/.runtime/water-cold-r10/`.

The frozen plan requires same-session independent stone calibration and one
depth-zero four-control capture at `(6,96,6)`, camera offset `(-2.5,2,-3.5)`,
exact source/neighborhood gates, and background-only WGC. Its declared liquid
ROI excludes dilated support hulls; fixed inset side samples are also scored.
Source-channel attribution requires agreeing background-subtracted control
contributions, dominant-channel fraction >= 0.75, channel margin >= 20 RGB,
and at least 80 identifiable pixels. Ambiguous channels or unverified cold
loading reject the diagnostic. Native calls/capture end by 11:10 and
restoration/stop by 11:20 Asia/Shanghai.

The single guarded cold startup **failed before readiness**, reporting
`Focus guard module snapshot failed`. Session
`416c9f540db9431fadf9307fbfa42a78`, owner `water-r10-cold-rgb`, never established
a game PID binding. There were zero calibration calls, native fixture calls,
or source-channel captures and no retry. This is a startup blocker; it provides
no sampled-bitmap evidence.

All three marker files were removed back to their original absence. The full
resource manifest, pack manifest, and `.mcdev.json` match the recorded
baseline. Normal managed stop succeeded; the manifest is stopped/not ready,
owned MCDK PID 29520 is absent, and no Minecraft child of that owned MCDK is
observable. A local wrapper raised KeyError while formatting the post-stop
summary for missing `game_pid`; its original stderr is preserved and the
summary getter was corrected. No unrelated processes were stopped. Raw
historical Minecraft PID entries are not treated as a live-instance count.

| Cold Evidence | SHA256 |
| --- | --- |
| `asset-plan.json` | `121f8fea489aaae05ab21c97d6b3f77d11432733bcfae918c00e41999e15dda6` |
| `installed.json` | `aa9002e3be3e883ea71c89f7a3a3fce1ade48377d002c7e5007136449b10fa2b` |
| `restored.json` | `6b2189d090a699104c62e05e83686f6f561c75d3c58dbf68183fc34e6bdbf608` |
| `final-audit.json` | `c527548fbf64cda58fe514204e8f042773812a341d22ae0a02cff753b6d1bceb` |

The checkpoint manifest `tools/data/native_water_source_r10_checkpoint.json`
links the frozen rejection, all bounded reports, loaded nominal lookup, and
cold cleanup audit. The earliest prerequisite is reliable guarded cold startup
and demonstrably loaded marker bitmaps. Active water material/backend, actual
uniform target, and native wave inputs remain unresolved. No expanded UV
search, native translation test, or production correction follows from the
failed source candidate or failed startup.

## Evidence

All artifact paths below share this absolute directory:
`C:/Users/Happy2018new/.pyreact-debug/instances/78a2769a6c8946989c1e42bdac3e66a8/artifacts/`

| Artifact | SHA256 |
| --- | --- |
| `camera-native-r10-v1.json` | `0164703d28e1694c0a73194ccac9ffb1e304816a85b23c31c865dc4c3ac41783` |
| `native-water-side-r10-v3.json` | `4b2a260946dbfa165c102300ad37049a234d658e3ee856e6270636a2db228e88` |
| `native-water-side-r10-v3_preflight.json` | `eb51d4ad0c7fcf748e167ca7ecd77085acdf155b28dd0c317f02b34049c5c32b` |
| `native-water-side-shape-r10-v3/report.json` | `32b5552df5c6deeeb38f1b9ce0ffa6ff558bc5a99f936d2c55911daf2cb2d217` |
| `native-water-side-contract-r10-v3.json` | `fd5cbf5a42b08206b2c4acdf2abc7eba394bf1af10191d425b1f26f5142b5109` |
| `native-water-side-uv-r10-v3.json` | `6bfb288b20d60dc330c3e179d917bde9b6e6c5578a3813932b25429831ec3deb` |
| `native-water-side-audit-r10-v3.json` | `cc496b56f734f898f4a24f0f48b96a4b1d522c634bdeabb362620a3633c99f31` |
| `native-water-side-grids-r10-v3/report.json` | `7cc11a127d83936d64a984405410dfc9c2930eab861983aff3401382a68d8b1d` |
| `native-water-side-diagnostic-r10-v3.json` | `0a2578b128eea84d9329dae51abee7b8e01b52c812f2ff68981a095d8a31a52b` |
| `native-water-temporal-baseline-diagnostic-r10-v3.json` | `619efe801ae160d94b81763340672ffeaec090a63c579024c4c4ab9de45e96d1` |
| `native-water-netease-xz-source-diagnostic-r10-v3.json` | `d6ac1ef93f5d0faa9ec1c18247f853d9131b81d1cb41b51f6f159ac69d40a94e` |
| `snow-r10-restored.png` | `87a182cfb1fe1b93ee51b10763b6081f1edc76ea3e06803207fbc999bd5cf5db` |

Frozen V3 plan:
`D:/Happy2018newの个人文件/GitHub/better-building-editor/.runtime/r9-snow/.runtime/native-water-side-preflight-r10-v3.json`,
SHA256 `13f1847e7437b1a1ce8363cd32927f9e5b6b41ffedfdac591ad729de6c7600c0`.
Frozen candidate SHA256 is
`6382af0b7014cad5fc6e8358bd04f5f6a629e20839befc738380e16e8e72deb5`.

Preserved host-only diagnostic sources are in
`D:/Happy2018newの个人文件/GitHub/better-building-editor/.runtime/r9-snow/.runtime/`:

| Source | SHA256 |
| --- | --- |
| `diagnose_water_side_r10.py` | `c57ad5a5748e18aaae99f4af7e51ba9ed45155d8296bde4ced26c159ffc516d5` |
| `diagnose_water_temporal_baseline_r10.py` | `d1fd59b94d7b81d6701b8b202acd1e185db995cd97084d383e2ff63e73d7a53f` |
| `diagnose_netease_water_source_r10.py` | `d834c884baf5397495c93082cfab3981dce4231e4c977418d34acfd6f09d7ac2` |

The failed photometric/clock assumptions require further diagnosis. No
production correction is justified by the rejected best fit.
