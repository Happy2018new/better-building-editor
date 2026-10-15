# Native Shelf Route Selector V3

Prepared only. No MC launch or WGC capture has been attempted by this worker.
Owner: `root-shelf-r20-native-routes-v3`.
Clone: `.runtime/projects/shelf-r21-native-routes-v3`.

## Frozen Scope

The complete source is the exact frozen
`.runtime/projects/shelf-r21-native-light-v2` copy, verified against
`.runtime/shelf-native-light-r21-start-v2/frozen-project.json` before and after
preparation. Its failed native-light experiment remains intact. V3 contains
3115 frozen files, digest
`6d0ff299679f3fe42d5f45fc89b1edf1c65ad30b6e6935c982200a582997c7ae`.

Exactly four resource paths differ: `materials/entity.material`,
`materials/terrain.material`, and two new route-selector fragments. The material
objects have only one new fragmentShader entry each. No vertex, vertex fields,
states, defines, samplers, model registrations or behavior files change.
The `diffs` directory contains exact before/after bytes and unified patches.
All four automatic reload options remain false.

`entity_static_netease` marks alternate 16px strips cyan. `terrain_base` marks
them yellow. Other 16px strips retain original native final RGB. Native alpha,
alpha discard and terrain BYPASS behavior survive all strips. The previous v2
entity_static diagnostic remains in the clone as part of its frozen source.

The root overrides do not cover child fragment overrides:
`netease_entity_outline`, `netease_block_as_entity_transparency`, or
`netease_micro_block`. The separate `netease_block_as_entity_mesh` root is also
outside this experiment. No-hit results cannot exclude those routes.

## Offline Checks

Five focused tests passed. `compile.json` contains 40 native/selector pairs:
78 programs compile/link; the two programs of one GLES100 skinning pair fail
with the same inherited native error. All 608 RGB/native-strip/alpha/discard/
BYPASS pixel comparisons pass. These are synthetic GLES checks, not native
route or appearance acceptance.

Preflight verifies the source v2 copy, both freeze manifests, the v3 clone,
native shader/material sources, every host source, exact diff bytes and WGC
executable. Keep those source files in place until this experiment concludes.

## Root-Scheduled Run

```powershell
python -B -X utf8 .runtime/shelf-native-routes-r21-v3/run.py preflight
python -B -X utf8 .runtime/shelf-native-routes-r21-v3/run.py start --scheduled-by-root
```

Start requires zero live MC processes and at least 6 GiB available commit. It
keeps exact MC/MCDK process exit observation alive through the established
watcher. Run capture in a separate command after the launch summary is ready:

```powershell
python -B -X utf8 .runtime/shelf-native-routes-r21-v3/run.py capture
```

Capture is fixed to south and exactly two raw images, `native.png` and
`empty.png`, with replication, fixed-camera checks and finally restoration.
It uses no proxy geometry, AO, UI or other direction. Each phase requires the
6 GiB margin and no new phase is admitted after 150 seconds; native calls keep
their existing timeout, so this is not a hard process deadline.

Root must open both raw images and separate the visible shelf body from support
and background before interpreting a route. Marker counts are observations
only, and native_route_qualified remains false. In particular, yellow terrain
in the cell ROI is not proof that the shelf uses terrain_base. Matching colors
may conceal the silhouette; record uncertainty rather than expanding. No west
or further diagnostic mode is implemented in this runner.

```powershell
python -B -X utf8 .runtime/shelf-native-routes-r21-v3/run.py stop
python -B -X utf8 .runtime/shelf-native-routes-r21-v3/run.py finalize
```

Stop uses force=False only. On a normal-close timeout, keep the error and wait
for exact-exit observation. Finalize requires both exact identities to be gone.
Never use force termination or alter the frozen clone to recover a failed run.
