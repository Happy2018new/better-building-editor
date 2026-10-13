# Supported product connection matrix handoff

## Status and Scope

The public blueprint `test.connections.product` adds nineteen supported dry
cases. CPU state/context/edit/history checks pass; all new native editor shape,
full projection and missing projection acceptance remains pending. This task
has not launched Minecraft. The root currently holds new launches while the
shared full-resource-pack startup failure is investigated.

Existing accepted native ordinary and cross-chunk cases remain in
`tools/data/neighbor_world_evidence_r4.json` and are not replayed by this matrix.
The new report binds that inventory's bytes, the block dump version/fingerprint,
the matrix/tool sources and the complete behavior/resource source fingerprint.

| Family | New Cases |
| --- | --- |
| Stairs | Outer quarter-turn, outer X mirror, inner Z mirror, inverted inner quarter-turn |
| Fence/gate | Mixed oak/spruce with bamboo gate closed and open |
| Pane/bars | Clear/red pane, hardened mixed pane, mixed copper/iron bars |
| Wall | Mixed wall beneath bottom slab and normal stair |
| Rail | Supported normal curve; normal, powered, detector and activator ascending rails |
| Fixed group | Open east-facing hinged door, tall fern, mature two-part pitcher crop |

The fixture declares stair state expectations independently from production
transforms. Tests exercise the public editor transaction and exact undo/redo.
The CPU report checks declared group closure and both target neighbor contexts,
then erases the group and requires the other body cells to survive.

Editor captures open the public blueprint, load an isolated body-only case,
disable grid/overlays and freeze the camera relative to the actual scene origin.
Geometry-hidden captures detect missing bodies without counting stone supports.
This is aggregate visibility only. It **does not** certify each cell's shape;
`editor.image_acceptance.passed` and `independent_shape_acceptance` stay null.

Full/missing use the existing native-world visual pipeline. Exact public
name/aux must survive world readback before state substitution. Each case has
a fixed side/top camera; turned stairs use a perpendicular side camera to
avoid completely overlapping target hulls. Full, all-air missing, dynamically
occupied and initially occupied pixels are checked separately. Missing uses
the existing temporary client occupancy observer; actual-world occupancy is
covered separately for double chests. No survival/fluid simulation is claimed.

## Checks Completed

The fifteen new test methods in `tests/test_product_connection_matrix.py`
pass, including corrupted closure, invisible/out-of-viewport pixels, camera
origin offsets, both chest halves, cleanup failure and source drift. The
seventeen existing public blueprint methods and seven static-probe methods
also pass. Host Python 3 compilation, MCDK Python 2 parsing/import review and
`git diff --check` pass. MCDK review reports only an existing argument-count
hint in `debug_blueprints.py`.

There is no standalone Python 2 interpreter on PATH or in the common/runtime
locations inspected. Historical `.runtime/compile_runtime.py` is a game
`execute_code` payload, not a host interpreter. Actual Python 2 compilation
must be performed after a valid owner-bound runtime becomes available:

```python
import os
root = u'D:/bbe-r13e-groups/behavior_pack/modern_projection/projection'
checked = []
for name in ('debug_product_connections.py', 'debug_blueprints.py'):
    path = os.path.join(root, name)
    with open(path, 'rb') as source:
        compile(source.read(), path, 'exec')
    checked.append(name)
_result = {'python2_compiled': checked}
```

Use the actual loaded project path if integrated into the root checkout.

## Native Run Prerequisites

Use one newly verified owner-bound private flat creative session from this
source tree with automatic hot reload disabled. Background startup must use
the pinned MCDK and noactivation DLL described in
`docs/BACKGROUND_RUNTIME_ADMISSION_R13E.md`; at most five MC instances are
permitted. The root allocates the fifth slot. No foreground, resize, input or
silent unreliable-capture fallback is allowed. Do not reuse an old ready
manifest or calibrate against another session.

Set `MCDEV_NATIVE_CAPTURE_HELPER` to the loaded project's
`tools/capture_native_window.py` and `MCDEV_NATIVE_CAPTURE_EXE` to the pinned
single-WGC executable. `SignCheck` uses background-only native-resolution
captures in these routes. Run a fresh same-session stone camera calibration
first. It requires `passed=true`, `completed=true`, the same runtime version,
reported FOV and aspect ratio. The matrix lowers its placement from foot+24
to foot+2; `--fixture-lift-y -5` lowers the calibration's usual foot+7 origin
to foot+2 as well.

Commands below use `run_live_check.py` to validate session ownership; it also
serializes the existing desktop lock, but these particular routes use SDK
commands and background captures and do not activate or resize the game.
Use fresh report paths and allow each suite's restoration to finish.

```powershell
python -X utf8 tools/run_live_check.py --session '<fresh session>' --owner '<owner>' `
  verify_camera_projection.py .runtime/product-camera-r14-v1.json `
  --native-resolution --fixture-lift-y -5

python -X utf8 tools/run_live_check.py --session '<same session>' --owner '<owner>' `
  verify_product_connection_matrix.py .runtime/product-native-r14-v1.json `
  --live --camera-calibration .runtime/product-camera-r14-v1.json
```

Start with `--case stairs_outer_turn90 --case rail_supported_curve` for a
bounded admission to the unchanged camera/pixel gates, then run remaining
cases. The matrix automatically uses each declared camera view; `--view`
does not change those fixed per-case views. Current matrix replay is rejected
because no product-specific body-capture replay gate exists. Do not rerun
already accepted unchanged cases simply to create newer evidence.

## Actual Double-Chest Occupancy

The existing frozen chest holdout now accepts `--occupied-half main|sub`.
For either choice it independently calibrates the **remaining** cell with a
stone cube before chest captures, writes a real stone only at the selected
occupied half, and measures dynamic/initial/recovered virtual geometry.
The native single and real-single-plus-ghost comparisons remain diagnostics.
The native single is always at the first world cell; its diagnostic extraction
uses the full declared crop so main-half occupancy cannot yield an empty
single diagnostic by measuring the other cell's earlier half crop.

```powershell
python -X utf8 tools/run_live_check.py --session '<same session>' --owner '<owner>' `
  verify_chest_occupied_frozen_holdout.py .runtime/chest-main-r14-v1 --occupied-half main

python -X utf8 tools/run_live_check.py --session '<same session>' --owner '<owner>' `
  verify_chest_occupied_frozen_holdout.py .runtime/chest-sub-r14-v1 --occupied-half sub
```

Each run covers normal and copper double chests. This task does not certify
new colored-bed, NBT or dual-layer visual cases; those retain their separate
actor-aware routes and pending acceptance records.
