# Neighbor Cold Calibration R6

The 2026-10-11 cold neighbor run did not produce accepted static or dripstone
evidence. Both camera calibration attempts completed and restored every
saved field, but failed the unchanged silhouette contract. The dependent
direct-world seed diagnostic, static core and 92-pair AABB holdout were
therefore not run. Existing merged-tip image failures remain failures;
this run does not change the previous standalone dripstone results.

## Frozen Source And Instance

The cold launch used clean source `4698c082a226e136f47954811ef5af4c80c1af2e`,
including calibration environment/cleanup commit `ffb11eb` and the native
AABB validity guard `4698c08`. The unaccepted liquid material candidate
was not imported. No resource files were edited during the run.

The immutable source archive SHA-256 is
`c93ab47244a413f12c55ce7a814a614f9bf8a872fc8c71a3b5e9d2031da2f174`.
Provenance records raw and `sha256_utf8_lf_v1` hashes for all 21 shader,
material and anchor files before launch, after readiness and after capture;
every recorded source/resource hash remained unchanged.

Owned instance: `09316aafbc764f559427efee8f12fd25`, owner `p0-neighbors-r5`.
Game PID `27644`, creation identity `134361408484005147`.
MCDK PID `40668`, creation identity `134361408482010439`, MCP port `60219`.
Native runtime: NEMC `3.9.0.401155`, Minecraft `1.21.120.0`.
Native camera screen: `(499,277)`, reported FOV `60`.

All reports, original JPEG captures, signal masks, outline comparisons,
source archive, capture helper and provenance are preserved outside the
worktree in:

`C:/Users/Happy2018new/.pyreact-debug/instances/09316aafbc764f559427efee8f12fd25/artifacts/`

## Results

Both attempts used clear noon, clouds disabled during capture and a
10-second weather settle. Both report `completed=true`, `passed=false`,
`restored=true`, and `cleanup_errors=[]`. Front passed; right and tilted
failed. The common fitted vertical FOV was `67.1` in both attempts.

| Attempt/View | Boundary RMS | Mask IoU | Outline Recall 2px | Outline Precision 2px |
| --- | ---: | ---: | ---: | ---: |
| r6/front | 0.5 | 0.973865 | 1.0 | 1.0 |
| r6/right | 3.122499 | 0.961607 | 0.939597 | 0.996154 |
| r6/tilted | 5.074446 | 0.939770 | 0.903448 | 0.969697 |
| r6b/front | 0.5 | 0.973865 | 1.0 | 1.0 |
| r6b/right | 2.783882 | 0.967583 | 0.955479 | 0.996154 |
| r6b/tilted | 5.074446 | 0.939770 | 0.903448 | 0.969697 |

The contract remains RMS `<=2`, IoU `>=0.95`, and outline recall/precision
`>=0.985`. No thresholds, camera corrections or image translations changed.
Signal/outline images were visually inspected; the failed masks have edge
notches or protrusions relative to the projected cube. Their cause is not
established by this run, and no shared-cache or geometry claim is accepted.

Report SHA-256:

- `camera-calibration-r6.json`: `a0502195d1428aadccba95cf0804e40a9539514c63867a2c1ff1191e1eeb6cdd`
- `camera-calibration-r6b.json`: `11adfaca5d62a99e0aa9faedf43d3fb1912030dcee0f4dab2002e7d9325afa57`

The new instance stopped normally after the failed retry. A subsequent
identity-aware status confirmed both owned processes absent. The previous
`48e502a400fe44dc98c988ed24115c74` instance was also stopped; its normal
close timed out, followed by inspection and identity-verified owned force
stop. The desktop was released before further diagnosis.
