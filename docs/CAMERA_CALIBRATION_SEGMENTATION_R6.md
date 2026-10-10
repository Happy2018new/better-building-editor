# Camera Calibration Segmentation R6

The r6 and r6b cold reports remain failed and unmodified. A separate offline
replay demonstrates that the neutral-color extractor attached background to
the native stone cube. This change corrects extraction; it does not create
new native captures or accept the dependent neighbor checks that were skipped.

## Extraction Evidence

The old `stone_signal` selected neutral pixels (`RGB spread <13`, red `>50`)
inside the central rectangle. It only asserted that at least 1000 selected
pixels had shown/hidden maximum-channel difference `>20`; it did not require
that contribution for each candidate pixel.

Visual inspection of the original shown/hidden pairs and diagnostic masks
found the tilted mask joined neutral birch bark below the stone. Its lower
bound reached y288. The corrected mask ends at y278 without moving pixels.
In both tilted pairs, pixel `(411,285)` is `(106,108,97)` in both images;
pixel `(415,280)` is `(133,130,125)` in both images. These pixels were selected
by the original mask although their exact native visibility-toggle difference
is zero. The r6b right exterior also includes unchanged pixel `(466,273)`,
RGB `(96,102,92)` in both images.

Intersecting color candidates with the existing difference `>20` rejects the
background protrusions. That intersection leaves internal holes around the
cursor and texture/color coincidences. Filling only zero regions disconnected
from the image boundary by four-neighbor paths restores the opaque cube's
silhouette. It fills 19/front, 109/r6 right, 112/r6b right and 87/tilted pixels
before the existing cleanup. Open notches remain connected to the exterior.

The implemented sequence is color/brightness and central rectangle, existing
contribution threshold, largest four-connected component, enclosed-hole fill,
then the unchanged median/minimum/maximum 3px cleanup and 1000-pixel
observability assertion. It performs no convex-hull fill, geometry-based crop,
camera offset, image translation, threshold relaxation or FOV adjustment.

Pure difference extraction is insufficient: the r6 right largest difference
component joins foliage changes above the cube and has boundary RMS 14.10px
after hole filling/cleanup. The color intersection is necessary for these
preserved native visibility-toggle pairs.

## Fixed-FOV Replay

All six views use the original poses and original common vertical FOV `67.1`.
No new FOV search is performed. The original limits remain RMS `<=2`, IoU
`>=0.95`, outline recall/precision `>=0.985`.

| View | Original RMS | Corrected RMS | Corrected IoU | Recall 2px | Precision 2px |
| --- | ---: | ---: | ---: | ---: | ---: |
| r6/front | 0.500000 | 0.500000 | 0.972260 | 1.0 | 1.0 |
| r6/right | 3.122499 | 1.500000 | 0.969901 | 1.0 | 1.0 |
| r6/tilted | 5.074446 | 0.866025 | 0.962680 | 1.0 | 1.0 |
| r6b/front | 0.500000 | 0.500000 | 0.972260 | 1.0 | 1.0 |
| r6b/right | 2.783882 | 0.707107 | 0.975351 | 1.0 | 1.0 |
| r6b/tilted | 5.074446 | 0.866025 | 0.962680 | 1.0 | 1.0 |

The implemented extractor is pixel-equal to the preimplementation diagnostic
for every view. The separate replay reports `diagnostic_passed=true` and
`accepted_calibration=false`. Fingerprints match before/after for 26 original
files: both reports, twelve JPEG captures, six masks and six outline images.

Original report SHA-256 values remain:

- r6: `a0502195d1428aadccba95cf0804e40a9539514c63867a2c1ff1191e1eeb6cdd`
- r6b: `11adfaca5d62a99e0aa9faedf43d3fb1912030dcee0f4dab2002e7d9325afa57`

## Preserved Artifacts And Tests

Artifacts are outside the worktree under
`C:/Users/Happy2018new/.pyreact-debug/instances/09316aafbc764f559427efee8f12fd25/artifacts/`.

- `segmentation-r6/`: initial five-method diagnostic, retained unchanged.
- `segmentation-r6-outer/`: six-method diagnostic and visually reviewed sheet.
  JSON SHA-256: `b1211acd96d792b0956264722d19429e8d0bc7ea4d38c44fb0b37710bafca992`.
  Sheet SHA-256: `6ba586dea579d4c4598168312578f7c30b783ae98292b894d7edf59ae2532031`.
- `segmentation-r6-replay/`: implemented-extractor masks, outline comparisons,
  replay script, checker, tests and full before/after original fingerprints.
  JSON SHA-256: `a16ab9fa617cdb18e783d63194ec61523dbec00bb7a2deb05b10059dea326cf8`.

The preserved replay script can be run with `--repo-root` pointing to this
checkout. It imports only host-side tools and writes only its separate replay
directory; it asserts pixel equality with the prior diagnostic and checks
original capture hashes before extraction.

`python -X utf8 -m unittest discover -s tests -p test_camera_projection_tool.py`
passes all 19 tests, including three new extraction regressions: unchanged
connected neutral background is rejected, enclosed cursor/texture holes are
filled, and an open missing-edge notch remains visible. No live game calls or
resource edits were made during this diagnosis or implementation.
