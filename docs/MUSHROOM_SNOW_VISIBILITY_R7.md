# Mushroom Snow Visibility R7

Brown and red mushroom proxies, including the alpha-derived burial cutoff, are
accepted for the measured dry controls and all snow heights h0..h7 on NEMC
3.9.0.401155 / runtime 1.21.120.0. This closes only these two plants. The complete
29-plant catalogue is not accepted; poppy and the remaining plant gaps retain
their previous status.

The machine-readable acceptance record is
[`snow-mushroom-acceptance-r7.json`](snow-mushroom-acceptance-r7.json).
Its paths refer to immutable local artifacts, not files copied into the repo.

## Final Live Batch

Artifact directory:
`C:/Users/Happy2018new/.pyreact-debug/instances/db8bd4ce225d4b6d8c29c25e8f9104c2/artifacts`.

- Report: `snow-mushrooms-all8-r7-lift16-near.json`.
- SHA256: `9dbfa77aeefb0eec30feb8085b49ecad52c9e417160b92f910a6ef663df03b91`.
- `completed`, `restored`, `passed` and `source_assets_stable` are true.
- Full, missing and independent editor scopes pass, with zero failures.
- 34 nonblank comparison rows; 26 independent captures; 16 independently
  captured covered editor cases; 8 reused identical snow-only controls.
- An independent read-only audit verified all 190 unique native PNG references:
  hashes unchanged, reliable native-resolution WGC captures, background only,
  foreground unchanged, and frame QPC strictly later than each request.
- All 954 prelaunch runtime/resource hashes still match. Cleanup errors are
  empty and every native cleanup entry reports clean.

The six exposed-plant cases pass the original recall/precision gates of .75/.75
with the unchanged three-pixel edge tolerance. These are independent plant
masks after the native snow-only control, not a combined snow/plant silhouette.
Full and missing give identical values for these cases.

| Plant | Height | Expected Pixels | Observed Pixels | Recall | Precision |
|---|---:|---:|---:|---:|---:|
| brown_mushroom | h0 | 9337 | 8257 | .933169 | 1.000000 |
| brown_mushroom | h1 | 5987 | 5205 | .927343 | 1.000000 |
| brown_mushroom | h2 | 1686 | 1460 | .945433 | 1.000000 |
| red_mushroom | h0 | 7849 | 6866 | .925086 | .997961 |
| red_mushroom | h1 | 3103 | 2693 | .932001 | .994801 |
| red_mushroom | h2 | 117 | 112 | .914530 | .883929 |

At h3..h7, both plants have **zero expected and zero observed exposed plant
pixels** in full and missing, and **zero editor plant contribution**. Both dry
controls pass too: brown recall .948408 / precision 1; red recall .945044 /
precision .998575.

The original native, full, missing and editor images were actually inspected
through hash-validated contact sheets, including h1/h5/h6/h7 and the h2/h3
transition. Inspection crops are display-only and do not modify the report,
verdict masks or comparison ROI.

Offline replay independently recomputed every comparison from the saved PNGs
and masks and passed all three scopes. Its separate report is
`snow-mushrooms-all8-r7-lift16-near-replay.json`, SHA256
`92a07cac381510910e144a5d69194dfef0366dbf3fb1767a0897034babd4116e`.
The original live report is unchanged.

## Calibration and Fixture

The accepted calibration is `snow-camera-calibration-r7-lift64-skyward.json`,
SHA256 `e812f845206ac99857f1b439914a8aca52462880b781a48f576ba6d2f341e16b`.
Front, right and tilted views pass the original complete eight-corner convex
hull gates: RMS <=2 pixels, IoU >=.95 and two-pixel outline recall/precision
>=.985. The effective vertical FOV is 66.6. All three fresh native PNGs were
opened; the calibration is complete/restored with no cleanup errors.

Only the calibration tilted pose uses the authorized skyward `(0,-3,6)` view.
The snow comparison retains the public world camera offset `(-2,.15,-2.5)`,
original editor camera, fixed calibrated cell ROI and all original thresholds.
The lifted plant/reference/camera fixture is +16, chosen before capture.

The native-world target `(-47,117,-70)` stays fixed when the player moves to an
air-verified temporary stone platform nearby. This ensures native section
rendering; palette readback alone did not establish that rendering in earlier
failed attempts. The player settles for three seconds before capture, and
each native shown/cleared pair settles for two seconds.

The player foot was restored from `(-50.5,117,-73.5)` to
`(-52.5,93,-75.5)`. Flight was never modified and remained false. Native target,
support and player platform were cleared back to verified air. Biome, time,
daylight cycle, navigation, projection options and camera were restored through
the existing cleanup checks. The assigned instance remains running for root
to reclaim; this work did not stop it or activate/resize its window.

## Preserved Binding Condition

The final report preserves one failed read-only fixed session-marker attempt:
`Code execution failed: list assignment index out of range`. The authorized
limited reread then obtained the correct owned token. The marker has at most
two rereads; a wrong token is refused immediately. Business, world mutation,
camera and capture requests remain single-shot. Four regression tests cover
these rules. This diagnostic is retained in `binding_read_failures`, not
removed to make the report appear error-free.

## Production and Offline Evidence

The two proxy models retain origin Y 0, height 16, full V 0..16 and their
original rotations, XZ spans and mirrored UV. The highest opaque Y is derived
from the installed versioned native alpha bounds: brown .5 and red .4375.
When the snow surface is at or above that bound, `prepare_palette` omits only
the renderer overlay. Logical native layers, states, source documents and
actor payloads remain intact. No fitted position, model translation or texture
shift was introduced.

`.runtime/version-bundle-snow-r7-final-near.json` passes all 1,167 tests, 40
provenance files, 15,858 states under six transforms and every generator check.
SHA256: `89d89f34171a0474cb4112abe37ce18c210a366efbd83ccf2fda4832bf9a2b44`.
The prelaunch source snapshot is
`.runtime/snow-r7-prelaunch-source-hashes.json`, SHA256
`53a6120dcb5679ad60c429bb874c98ba8eb2ea8c1eec9770291f3f09fcf62ca9`.

The boundary batch h0/h2/h3/h4 also passed independently before all-eight:
`snow-mushrooms-boundary-r7-lift16-near-v2.json`, SHA256
`0b0e4e6ad7f2f95d85723a6362a38e94a3d6eda3e21ea672bcbb59b34d934a3c`.
The brown positive control is `snow-brown-positive-r7-lift16-near-v2.json`,
SHA256 `3400a2873da03afee530365c720ef860a24f7e141f483b11fc0241c3fc046f65`.

## Earlier Failures Remain Failed

The R5 all-eight batch remains failed because brown h3 contributed 26 editor
pixels; [its original evidence](MUSHROOM_SNOW_VISIBILITY_R5.md) is preserved.
R7 lift16/lift64 downward calibrations still fail their outline gates, and the
lift64 native-world boundary attempt remains incomplete/restored with missing
native plant references. Their immutable hashes are listed in the acceptance
manifest. The two pre-retry near-player attempts remain interrupted/restored.
The first all-eight launch timed out acquiring the shared capture lock before
fixture mutation; the successful batch followed root's explicit lock release.

Poppy remains unaccepted. Its existing native/proxy horizontal mismatch and the
absence of a documented source-position random-offset hash are not resolved by
this mushroom result. The manifest explicitly records
`all_current_plants_and_heights_sampled=false`.
