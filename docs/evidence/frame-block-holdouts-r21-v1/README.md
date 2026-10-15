# Native frame-block holdouts R21

Status: unqualified. This restored six-case run compares the fixed quarter-cube
candidate with independently inserted native stone and artificially enchanted
quartz block. The production gates remain false.

## Reproduce

Requires Python, NumPy, SciPy and Pillow. No game, MCDK connection, credentials
or original runtime directory is needed. From the repository root, choose a new
output directory:

```powershell
python -B -X utf8 docs/evidence/frame-block-holdouts-r21-v1/replay.py replay docs/evidence/frame-block-holdouts-r21-v1 .runtime/frame-block-replay-new
```

The frozen replayer checks every manifest byte and all 80 original PNG receipts,
recomputes independent three-view stone calibration, runs the original analyzer,
and compares its full numerical output with the preserved analysis. It also
checks native Item.Block preservation, enchantment readbacks, restoration,
retained process identities and matching exported WER events. Output goes into
the new directory. `replay-result.json` records the first successful replay.

## Observed Results

All 12 full/missing versus native silhouette comparisons pass the unchanged
thresholds. Five cases have IoU 1.0, edge P95 0 and maximum edge error 0.
Stone -75 degrees has IoU 0.9991575400168492, P95 0 and maximum error 1 pixel
on both routes: 4748 native pixels and 4744 product pixels. Native masks are
identical between stone and enchanted quartz at each view angle.

| View | Native pixels | Native bounds | Ideal-model RMS / max pixels |
| --- | ---: | --- | --- |
| 0 degrees | 5693 | [960,515,1035,593] | 0.86861649 / 1.51850453 |
| -75 degrees | 4748 | [955,512,1016,595] | 3.97533451 / 8.22946059 |
| +75 degrees | 4737 | [979,512,1040,595] | 4.51406 / 9.22902 |

Independent camera calibration passes at vertical FOV 66.6 degrees; individual
fits are 66.3, 66.3 and 66.6. The 74 main captures and six calibration captures
retain original PNG bytes, owner/PID/creation identity, QPC freshness and strict
schema-3 foreground guard records. Unrelated foreground titles are omitted.

`analysis-v1/multiview.json` is unchanged and keeps
`geometry_holdouts_passed=false`. Its support-only model fails on oblique native
silhouettes by the same 8-9 pixels as product silhouettes. Hull images show the
cyan model extending into the brown frame backboard while the green observed
outline is occluded. The native frame backboard is absent from the ideal model.
Its fitted scale 0.24000481 and depth 0.42508008 are consequently diagnostics,
not accepted dimensions. Keep the declared scale 0.25 and center Z 0.4375.

## Artificial Enchantment Chain

`artificial-enchantment-probe.json` retains the full actual typed Item compound,
server GetFrameItem result, client readback and restoration. Each of three
quartz matrix cases independently repeats the same native insertion chain in
`report.json`. A plain inventory quartz block is inserted by PlayerUseItemToPos;
only the observed native sword enchantment tag is then copied through
SetBlockEntityData. The original Item.Block is preserved, not synthesized.
Both server and client read Name minecraft:quartz_block, Damage 0, Count 1,
enchantment (9,3), Block name minecraft:quartz_block, pillar_axis y, val 0 and
version 18168865. This explicit synthetic enchantment write does not convert
the earlier public manufacturing API failures into success.

Actual native and product screenshots visibly contain pink/purple glint.
Single shown frames do not accept glint direction, time, phase or brightness.
Ordinary minecraft:quartz remains a distinct flat item.

## Source And Exit Bindings

`report.json` retains equal complete launch/before-after source hash maps and
their digest 36d897c8bd8e190c83d117b2c5ddc3c9feb454092b0e7f0a145c061c410c2c49.
`candidate.json` preserves original pre-run candidate metadata unchanged;
its old pending limitations are historical. Exact candidate resource bytes,
capture host tools and an offline analysis import closure are in `sources/`.
Manifest per-file bindings distinguish actual launch/capture hashes from
additional analysis dependencies recorded retrospectively. The original
analyzer recorded its own hash but not every dependency hash. This package
replays the pixels independently; it does not include every launch file byte
or claim to recreate a complete game installation.

`normal-stop.json` retains the 2026-10-15 18:14:12.268872 UTC normal-only close
request, initial timeout, successful prior fixture restoration and eventual
stopped registration. `exact-exit.json` retains handles opened before capture:
game PID 15144 / creation identity 134365611080856581 exited 0xC0000409 at
18:14:41.838365 UTC; MCDK PID 52476 / identity 134365611078631953 exited 0.
WER record 80432 matches both game PID and creation time, reporting
ucrtbase.dll / c0000409 at 18:14:17.8046502 UTC. Record 80433 has the same report
ID. XML files are UTF-8 EventLogRecord.ToXml exports, not original EVTX bytes.
No force stop was used. This was an abnormal exit; its cause is unresolved.

## Remaining Work

Model the independently measured frame backboard before interpreting absolute
depth fits. Repeat unchanged candidates for grass, log and planks; measure
glass separately. Cover six frame faces, eight rotations, editor pixels,
lighting, native glint timing and world lifecycle before production admission.
Production admission needs an explicit validated (name, aux) whitelist; material
acceptance alone must not admit all 324 opaque resource candidates.
