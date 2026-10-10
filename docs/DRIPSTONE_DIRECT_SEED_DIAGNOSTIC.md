# Native Dripstone Direct-World Diagnostic

`tools/verify_dripstone_direct_seed.py` compares native geometry-generation
paths at identical positions. This is a diagnostic, not projection acceptance
or a production offset correction. Every comparison records translation
`(0,0)` and uses the existing threshold 16, minimum 80 pixels per cell,
one-pixel shape recall/precision 0.93 and RGB channel error 20.

## Inputs And Paths

The scene contains standing/hanging merged-tip cells at `(6,-37,6)` and
`(6,-36,6)`, with stone supports immediately below and above. These are the
same X/Z coordinates as the existing native AABB probe. All four scene
cells are placed in verified air, replicated to the client, and read through
native clip/collision APIs on both sides before generation.

While that native scene still exists, the tool generates four models:

1. `CombineBlockFromPosListToGeometry` from the four real world positions.
2. `CombineBlockPaletteToGeometry` from the palette returned by path 1.
3. `CombineBlockPaletteToGeometry` from `GetBlockPaletteBetweenPos`.
4. `CombineBlockPaletteToGeometry` from a blank palette deserialized from
   path 3's unmodified serialized data.

The native scene is captured, then all four cells are cleared and replicated
as air. Each model is attached in turn to the same temporary anchor at the
selection minimum `(6,-38,6)`, using the established attachment offset
`(-0.5,0,-0.5)`, rotation `(0,180,0)`, unit native scale and uniform 4
`(19487,0,0,0)`. The anchor does not use the packed-context shader marker.

A fixed horizontal camera views the scene from nine blocks along negative Z. Native
PNG captures are taken before and after `SetNotRenderAtAll` hides the whole
temporary actor, using the existing native capture pattern. Camera poses and
viewport sizes are checked around every capture. Comparison masks come
from the calibrated camera and complete cell hulls; they are not fitted to
any of the four model images. The two stone supports are separate geometric
positive controls for the deterministic origin and attachment convention.

## Preserved Evidence

The report retains native AABBs, world seed, runtime version, lossless tagged
palette trees including tuple keys and byte/unicode string distinctions,
serialization equality, fixed transforms, all native captures with SHA-256,
world comparisons and every pairwise model comparison. It associates the
run with the hash of `tools/data/native_dripstone_boxes_r5.json` and records
camera-helper, calibration, material, shader and anchor resource hashes.

A result is inconclusive about coordinate seeds if the support controls
fail or the native baseline is insufficient. If two live palettes differ
after serialization, their raw trees must be examined before attributing a
geometry difference to hidden metadata. API success and a completed probe
are not pixel acceptance. The command returns success for a fully completed
and restored diagnostic even if the strict image comparisons fail; those
failures remain explicit in the JSON.

## Reproduction

Run through the validated instance's desktop-owning runner. Use a preserved
native PNG `SignCheck` helper and a passing camera calibration from that
same session. The tool restores temporary cells, player, camera, options,
probe and environment in `finally`, then releases input and minimizes only
the owned game window.

Before activating the window or changing the world, the tool requires a
completed, passing calibration from the validated session's exact manifest
path and project. When the calibration records instance ID, owner, process
PID or process creation identity, those fields must also match. A recorded
failed calibration restoration is rejected. Runtime version, reported FOV
and viewport aspect are checked again by the shared ROI projection logic.

```powershell
python -X utf8 tools/run_live_check.py --session <session.json> --owner <owner> `
  verify_dripstone_direct_seed.py .runtime/dripstone-direct-seed.json `
  --capture-helper <preserved-capture-helper.py> `
  --camera-calibration <same-session-calibration.json>
```

The ModSDK documentation exposes no origin/seed argument for palette
Combine or Deserialize. Whether either native palette object preserves
additional coordinate context remains a question for this diagnostic.
