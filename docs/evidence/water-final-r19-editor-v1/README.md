# Final-Source Editor Water, R19

This is a narrow cold-start editor result for the current product sources.
It does not reproduce or explain the historical invisible-pool failure, and
it does not claim a product fix. All production qualification gates remain false.

The nine original editor cases were captured through the public source-document
and Scene paths: source, low, four flow directions, pool, falling and wet oak fence.
The candidate uses frozen animation; animation was not tested in this batch.
There are 48 guarded native-resolution captures with no activation, resizing or
desktop input. The batch completed and restored in 169.50 seconds, with no cleanup
errors and unchanged source hashes.

| Applicable Check | Result |
| --- | --- |
| Eight independent-water geometry cases | All pass; IoU 0.9553 to 0.9898, boundary error 1 to 3 pixels |
| Nine section hide/restore controls | All pass; exact restoration RGB RMSE 0 |
| Pool independently visible pixels removed | 96,000 |
| Fence body and rear contribution | Both pass; eligible fractions 1.0 |
| Fence fixed-geometry alpha endpoints and intermediate values | Pass; default restoration RMSE 0 |
| Pool south opaque side | Correlation 0.963751; RGB RMSE 2.586847 |
| Pool east opaque side | Correlation 0.982906; RGB RMSE 1.817854 |
| Mirrored, constant and wrong-phase UV negatives | All rejected |
| Editor owner CPU maxima | LiquidControls.update 4.00 ms; LiquidPreview.advance 8.00 ms |
| Actual native IDs | Match cached IDs for all 104 allocated banks in 48 readbacks |
| Actual native uniforms | Exactly match IEEE754 float32 conversion of cached values |

The side thresholds are unchanged: correlation >= 0.85, RGB RMSE <= 8 and
contrast >= 1, with all three negative controls required to fail. Two raw alpha
0.45 uniform comparisons differ only because the native float32 readback is
0.44999998807907104; raw values are preserved.

The acceptance analyzer's overall result is false because this editor-only
batch contains no world-owner CPU samples or world stop lifecycle. This does
not turn the passing editor checks into full product acceptance.

The product/source/resource/tools freeze contains 3,060 files with contract:

`20ab6570d676d884753b89ca2d6f35508e17e7dfac47909c245e26e86a5cf272`

At sync time, every hashed input matched the main workspace. The cold project's
MCDev configuration disables hot reload and fixes world seed/type/mode;
`sync.json` records both configurations. Later host-only book/item tool changes
are listed in `editor-readback-verification.json`; product sources/resources
still matched at that readback check. This result must not be applied to changed
product sources without comparing their hashes. The generated water owner
contract was refreshed to include the finalized shared files; this updates
provenance only and does not enable any gate.

The same session subsequently completed and restored an independent stone
camera calibration. A world pool attempt then stopped before its first capture
because it measured 387,060 handles against the unchanged 250,000 ceiling.
That attempt has completed=false, restored=true and no cleanup errors. It is
not world UV evidence. Handle growth is not attributed to the mod by this package.
The normal stop command returned that the game had not closed; a subsequent
process lookup found both owned PIDs absent, and no forced stop was issued.

`editor-contact.png` contains original, section-hidden, restored and dry views.
Raw reports retain original paths; the verifier rebases only a temporary replay.
`launch-inputs.zip` contains every frozen input. The retained host wrapper is
the final orchestration revision, including later independent-batch support;
the product runner and analyzers actually used are preserved in the source zip.
No managed session token file is included.

Verify hashes, complete frozen inputs, captures and exact native readbacks:

```powershell
python -X utf8 docs/evidence/water-final-r19-editor-v1/verify_package.py
```

Replay editor pixels with the frozen analyzers (Pillow, NumPy and SciPy required):

```powershell
python -X utf8 docs/evidence/water-final-r19-editor-v1/verify_package.py --pixels
```
