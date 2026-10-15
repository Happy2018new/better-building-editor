# Final-Source World Pool, R19

The current frozen water candidate still fails the unchanged south/east side-UV
gate. No product fix or qualification is claimed, and all production gates remain
false. This package preserves a narrow full/missing pool batch and its controls.

| Check | Full | Missing |
| --- | --- | --- |
| South side correlation / RGB RMSE | 0.830878 / 5.540395, fail | Same, fail |
| East side correlation / RGB RMSE | 0.644174 / 7.875123, fail | Same, fail |
| Mirrored, constant, wrong-phase negatives | All rejected | All rejected |
| Pool geometry | Pass | Pass |
| Section hides/restores independent water | Pass, RGB restoration RMSE 0 | Pass, RGB restoration RMSE 0 |
| Independent water pixels removed | 114,976 | 114,976 |
| Wet and dry owner stop lifecycle | Both pass | Both pass |

Thresholds remain correlation >= 0.85, RGB RMSE <= 8, contrast >= 1, with all
three negative controls required to fail. The original physical 18 x 14 grid is
unchanged. The independent same-session stone camera calibration passed all
three views, completed/restored, and fitted vertical FOV 66.6 degrees. The pool
uses the old half-distance camera and a 64-block fixture lift, preserving the
source geometry and moving the actual player near the fixture with restoration.

The successful batch has 12 world captures and 6 calibration captures, with
completed=true, restored=true, source_unchanged=true and no cleanup errors.
Business readiness was awaited for 9.58 seconds before calibration. Handles
were 100,022 at business readiness and 125,189 at the last world capture;
the existing 250,000 ceiling was unchanged. The two world CPU method budgets
pass, with maximum 86.00 ms. Editor CPU methods have no samples in this
world-only batch, so the overall acceptance also remains false on that scope.
Normal finally cleanup stopped the owned instance; subsequent lookup found
both owned PIDs absent. No forced stop was issued.

This is the same 3,060-file source/resource/tools freeze as the editor package:

`20ab6570d676d884753b89ca2d6f35508e17e7dfac47909c245e26e86a5cf272`

Every frozen input is retained in `launch-inputs.zip`. The product candidate is
explicitly installed for the test; ordinary production admission is still closed.
No activation, resizing or desktop input was used.

`side-texel-samples.png` and `side-texel-artwork.json` are diagnostic only.
They use an existing predeclared physical texel-center grid, without fitting
geometry to the image. The south pair repeats exactly and matches the frozen
artwork with correlation 0.999901. East cell (4,3,4) matches at 0.979452,
while east cell (4,3,3) matches at -0.035722. An explicitly exploratory artwork
window search finds that a one-texel horizontal offset matches the latter at
0.976054. That search is fitted diagnostic evidence, cannot qualify UV, and
does not establish whether shader/native mapping or the physical sampling
oracle is responsible. The original four UV failures remain failures.

Two preceding cold preparation attempts are recorded separately. V2 exceeded
its 90-second managed readiness deadline; V3 became managed-ready but the
business workspace was not initialized when calibration began. Neither wrote
world cells or captured water. Both owned process pairs were subsequently
absent after normal stop. V4 added the existing repository's bounded read-only
business-ready wait before calibration. These are host preparation corrections;
product sources and thresholds were unchanged. The earlier long editor session
also aborted its first world capture at 387,060 handles and restored; that
attempt is preserved in the separate editor package and is not UV evidence.

Raw reports retain original paths; verification rebases only a temporary replay.
Start receipts include only the owned identity and noactivation fields needed
for review; no managed session token file is included.

```powershell
python -X utf8 docs/evidence/water-final-r19-world-v1/verify_package.py --pixels
```

The optional pixel replay requires Pillow, NumPy and SciPy and uses the exact
frozen analyzers. A verified failure means the evidence and expected failing
UV measurements reproduced; it does not mean the product gate passed.
