# Native Dripstone Boxes, Round Five

The native probe completed on 2026-10-11 at 02:58 Asia/Shanghai in owned
session `48e502a400fe44dc98c988ed24115c74`, owner `p0-neighbors-r5`, NEMC
3.9.0.401155, runtime Minecraft 1.21.120.0. World and player restoration
passed. Input release reported `held=[]`; owned game PID39968 was minimized,
and the desktop byte lock was available after the runner exited.

The preserved report is [native_dripstone_boxes_r5.json](../tools/data/native_dripstone_boxes_r5.json).
Its SHA-256 is
`f8e7f3aa07d3c94ee093c1fc818d532bfece75215f17bdc6cb82351389048429`.
`tools/verify_dripstone_native_boxes.py` generated these observations without
screen captures, fitted image offsets, or production renderer changes.

## Measurements

Client and server `GetBlockClip` and `GetBlockCollision` dictionaries are
exactly equal for all 19 cells. Ten dripstone samples retain aux 4 or 12 and
merged thickness. All have AABB extent `(0.375,1,0.375)` and no Y center
displacement. The following offsets are direct native box-center minus
cell-center arithmetic:

| Native X/Z | Native Y Samples | Center Offset X | Center Offset Z |
| --- | --- | --- | --- |
| 6 / 6 | -37, -36 | -0.041666507720947266 | 0.02500009536743164 |
| 7 / 8 | -37, -36 | -0.125 | 0.008333206176757812 |
| 45 / 9 | 13, 14, 16, 17 | 0.008335113525390625 | -0.09166622161865234 |
| 25 / 25 | 13, 14 | -0.024999618530273438 | -0.125 |

All nine stone support controls have exact unit-cell boxes. The client's
unmodified native palette header is `volume=(20,40,57)`, `void=false`, and
`eliminateAir=false`; no coordinate-seed field was observed.

## Interpretation

The measurements confirm native horizontal boxes depend on coordinates,
and that offsets are equal at the tested Y values. This is independent
evidence for the coordinate-sensitive behavior seen in the existing native
world and packed palette image controls.

The probe does not establish a geometry-generation seed contract, the
general offset hash, or accepted projection pixels. Raw AABB observations
are diagnostic evidence; they are not a new production correction or an
empirical lookup table. The standing and hanging merged-tip image failures
remain failures under their existing thresholds.

## Reproduction

Run the probe through `tools/run_live_check.py` with a validated owned
session whose project matches the checkout. It verifies the reserved cells
are air, installs ten merged-tip dripstone samples and nine stone supports,
waits for native client replication, records both sides' raw box returns,
and restores cells and player position in `finally`.

```powershell
python -X utf8 tools/run_live_check.py --session <session.json> --owner <owner> `
  verify_dripstone_native_boxes.py .runtime/dripstone-native-boxes.json
```
