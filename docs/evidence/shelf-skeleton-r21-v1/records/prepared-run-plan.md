# Shelf Skeleton World Probe R21 V1

Prepared offline only. No launch, capture, stage, or production behavior change
has occurred. This owner is covered by the existing `root-shelf-r20-*` assertion
watcher. Do not start a duplicate watcher.

- Owner: `root-shelf-r20-skeleton-world-v1`.
- Cold clone: `.runtime/projects/shelf-r21-skeleton-world-v1`.
- Source commit: `fd71754ed21d5dae7dc9aae1115b834ecf04bbcb`.
- Source: committed behavior/resource packs from that exact Git archive, plus
  the separately hashed local `.mcdev.json` with all four auto-reload flags false.
- Frozen files: 3150.
- Frozen digest: `283f4a732c9a737f7a313dae4690718317e6ce1ff987ebb0054ff038eb86ca8b`.
- Resource-only overlay: 8 paths; zero behavior changes.
- Frozen manifest: `frozen.json` in this directory. It includes host source
  hashes, WGC executable identity and the complete cold project manifest.
- Native probe: `tools/probe_shelf_skeleton_world_r21.py`.

The first stage is one oak/unpowered shelf facing south, native aux 0. It
captures exactly three full-resolution images: `native.png`, `empty.png`, and
`selector.png`. The cyan support remains the same across these captures. The
candidate uses the existing `WorldLiquidRenderer` with scale16, rotation0 and a
single owned group; no direct parallel model owner was added.

The host checks native state and client replication, records absolute native
cell corners with `WorldToScreenPoint` screen/depth values, and checks camera
state before/after every background WGC frame. Model center/scale/anchor fields
are explicitly submitted owner state, not an invented native model-position
getter. The existing SDK docs search did not expose `GetFreeModelPos`.

Selector reception requires at least 24 magenta pixels in the actual projected
native-cell rectangle. Magenta elsewhere is reported separately and cannot
pass. Failed selection stops later modes and executes all cleanup actions.
Successful selection still requires root to open the full native, empty and
selector images before creating the visual review receipt.

The second stage repeats native/empty/selector and adds document normal, world
normal, intensity, TILE light, unlit artwork, and candidate light: nine images.
Thus completing both south stages produces 12 images, including the deliberate
three repeated controls. Shape, absolute light, UV, depth and lifecycle product
qualification stay false. There is no UI probe in this plan.

## Commands

First confirm the current runtime owner has completed normal close and exact
exit/finalize. Preflight is read-only and may run while another owner is active:

```powershell
python -B -X utf8 .runtime/shelf-skeleton-r21-native-v1/run.py preflight
```

After an explicit root runtime grant, start in a retained exec session. This
command keeps exact game and MCDK process handles until both exit:

```powershell
python -B -X utf8 .runtime/shelf-skeleton-r21-native-v1/run.py start --scheduled-by-root
```

When `launch/start-summary.json` reports `ready`, use another exec session:

```powershell
python -B -X utf8 .runtime/shelf-skeleton-r21-native-v1/run.py capture --phase selection --direction south
```

Open the full images at `captures/south-selection/{native,empty,selector}.png`.
If selector/placement is wrong, stop and preserve them; do not generate a review
receipt. After actual root visual review, admit further modes explicitly:

```powershell
python -B -X utf8 .runtime/shelf-skeleton-r21-native-v1/run.py review --direction south --report .runtime/shelf-skeleton-r21-native-v1/captures/south-selection/report.json --i-opened-native-empty-selector
python -B -X utf8 .runtime/shelf-skeleton-r21-native-v1/run.py capture --phase details --direction south
```

West is not automatic. Only a root-reviewed south receipt permits its separate
three-image selection stage; west detail modes require their own raw-image
review receipt:

```powershell
python -B -X utf8 .runtime/shelf-skeleton-r21-native-v1/run.py capture --phase selection --direction west
```

Normal lifecycle completion uses only the existing normal `instances.stop` path:

```powershell
python -B -X utf8 .runtime/shelf-skeleton-r21-native-v1/run.py stop
```

If normal close times out, preserve `normal-stop.json`; do not force or retry
launch. Let the retained exact observer report original game/MCDK exits. Once
`launch/exact-exit.json` is completed, finalize with a second normal-only call:

```powershell
python -B -X utf8 .runtime/shelf-skeleton-r21-native-v1/run.py finalize
```

Launch requires zero live MC games and at least6 GiB available commit from
`GetPerformanceInfo`; runtime checks the same6 GiB at each phase boundary.
Capture stops admitting new phases after150 seconds and restores in `finally`.
It does not claim a strict native-call timeout or forcibly stop processes.
The launcher allows only one start attempt. No window activation, resizing,
desktop input, z-order changes, forced termination, or automatic reload occurs.

## Offline Checks

Twelve focused tests pass, including raw selector ROI rejection, offscreen
projection rejection, formatted game-template compilation, staged mode counts,
and direction/report/raw-image hash binding of review receipts. The prior
candidate resource report still records18 GLES programs,192 real-pair synthetic
pixel checks and144 turn/axis pixel checks, all passing. These are offline
checks and do not substitute for native screenshots.
