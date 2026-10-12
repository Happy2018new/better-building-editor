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
| `snow-r10-restored.png` | `87a182cfb1fe1b93ee51b10763b6081f1edc76ea3e06803207fbc999bd5cf5db` |

Frozen V3 plan:
`D:/Happy2018newの个人文件/GitHub/better-building-editor/.runtime/r9-snow/.runtime/native-water-side-preflight-r10-v3.json`,
SHA256 `13f1847e7437b1a1ce8363cd32927f9e5b6b41ffedfdac591ad729de6c7600c0`.
Frozen candidate SHA256 is
`6382af0b7014cad5fc6e8358bd04f5f6a629e20839befc738380e16e8e72deb5`.

The failed photometric/clock assumptions require further diagnosis. No
production correction is justified by the rejected best fit.
