# Frame Block Light Holdout: Incomplete Phase And Grass Overlay Failure

The first scheduled `noon-grass-log` phase did not complete. Its unchanged
candidate used the empirical 0.93 base-light experiment, clear frozen time
6000, grass block at -40 degrees and oak log at +35 degrees. All production,
appearance and general light-factor acceptance remain false.

## Actual Capture And Shutdown

Session `3c5e4322c1754a3ba47deafd63134878` used owner `item-r20`, game PID
12392 with creation identity `134365692453392148`, and MCDK PID 48596 with
identity `134365692451350981`. Launch preflight found no live game and
11371565056 bytes of available system commit, above the 9 GiB launch gate.

The original launcher failed after game readiness because it referenced a
nonexistent observer script inside the frozen project. This defect was
missed by preflight. Root explicitly authorized the existing external
`tools/watch_intrinsic_glint_exit_r21.py`, SHA256
`aa436ee9a0f496554c69330d8456fa21b6bb551b63032f0b5a453ad9748646aa`.
Both exact process handles were retained before captures. The original
failure and separate recovery amendment are preserved. A future launcher
must validate the observer path and dependencies before starting a game.

The independent setup readback recorded time 6000, no rain or thunder, and
both daylight and weather cycles false. Prior environment time 0 was saved
separately. After 105.448 seconds, the original 6 GiB runtime gate stopped
admitting work when available commit reached 5219196928 bytes. This was
before the 150-second cooperative admission cutoff and 180-second target.

Grass completed all editor/full/missing/native controls and restored its
native fixture. Oak log has only three editor controls and a full
hidden-before image. It has no full shown/hidden-after, missing triplet, or
native triplet. No native oak fixture was created. The host outcome's
aggregate `native_references_restored: false` also includes the unfinished
oak case; it does not negate the grass restoration receipt.

There are 18 ordinary capture receipts and six calibration PNGs. The report
has `completed: false`, unchanged source and empty cleanup errors. Original
environment restoration returned true. The phase remains incomplete and no
later phase or retry was run.

Normal stop first exceeded its ten-second wait. No force was used. The
retained observer subsequently recorded game exit `0xC0000409` and MCDK exit
0. The game exit is not clean; its cause is unresolved. Normal-only
finalization then returned 0 and the session became `stopped`. MC/WGC was
returned to root after capture, stop and observer execution finished.

## Raw Grass Findings

The raw native/full/missing and ROI montages were opened. Oak's existing
editor screenshot was also opened, but it cannot support native comparison.

| Grass Measurement | Result |
| --- | ---: |
| Filled native/full and native/missing IoU | 0.9995305164 |
| Unfilled IoU | 0.9995305164 |
| Paired edge p95 / maximum | 0 / 1 pixel |
| Pixels introduced by hole filling | 0 on all three routes |
| Top y+ ROI / product-to-native luma ratio | 190 / 0.99548697 |
| Side x- ROI / luma ratio / texture correlation | 1739 / 0.78216053 / 0.49000447 |
| Side z- ROI / luma ratio / texture correlation | 3329 / 0.78651348 / 0.47083896 |

No registration, RGB normalization or gain fitting was applied. The product
side visibly has a green dirt region and gray grass fringe; native has dirt
RGB and a green fringe. These texture differences confound side-face light
ratios. The top ROI alone cannot establish a universal 0.93 light factor.
Filled silhouettes and zero filled gaps do not validate texture or alpha.

## Overlay Diagnosis And Candidate

Installed 3.10.0.420447 `vanilla/blocks.json` selects `carried_textures` for
grass. Its side key is `grass_carried`; the terrain entry uses
`textures/blocks/grass_side` with `overlay_color: #79c05a`. The saved catalog
has the same metadata and bitmap identity. The source selection is correct.

The installed TGA has 211 alpha-zero pixels carrying hidden dirt RGB and 45
alpha-255 pixels carrying gray grass RGB. The original generator applied
`RGB * (alpha + (1-alpha) * overlay)`, tinting the dirt and leaving grass gray.
That recipe reproduces every original side atlas pixel. The shared
`bake_texture` formula now uses
`RGB * ((1-alpha) + alpha * overlay)` and forces output alpha to 255.
The focused regression fixture now uses the observed alpha polarity.

This is a generic overlay formula defect. The current catalog contains only
one resource, one item/aux and one profile with `overlay_color`:
`minecraft:grass_block`, aux 0, resource `fda002ddc43224a7`. Its four side
faces use the same entry. There is no separate grass-specific blend recipe.

`mc-search` retrieved `BedrockWiki/concepts/texture-atlases.md`. Its prose
states that overlay alpha controls tint intensity and makes output opaque,
and explicitly describes preserving hidden RGB for untinted areas. The
formula section writes `RGB*overlay + RGB*(1-alpha)`, omitting alpha from the
first term. That formula conflicts with the prose at alpha zero. The binary
endpoint correction here is supported by installed source pixels and the
raw native failure. Intermediate-alpha behavior remains unverified; no
universal fractional-alpha claim follows from this capture.

The independent candidate changes only
`resource_pack/textures/models/modern_projection/frame_block_items/fda002ddc43224a7.png`.
Its SHA256 is
`ab130fe030a9686eb0f5817b37a652535747d6ed22abc07c6741ed48a504dd8b`.
Top/down tiles, padding, UV rectangles, geometry, shaders, empirical 0.93,
independent glint and alpha behavior are unchanged. Production catalog,
profile and generated assets have not been regenerated. The override subset
is not a runnable project or a new resource qualification. Its profile and
resource contracts must be regenerated before any future scheduled runtime.

## Portable Evidence

The prepared bundle contains all 24 original capture PNG bytes, a report
with local image paths remapped to bundle paths, original private-report
SHA256, frozen capture and analysis dependencies, environment/outcome/exit
receipts, normal-stop journal, observer recovery amendment, captured resource
snapshots, and original/corrected overlay source assets and generators.
It preserves the incomplete phase and eight missing oak world/native
controls. Original private runtime records remain unchanged on disk.

The package needs Python 3.12+, NumPy, Pillow and SciPy. Replay is offline and
does not need an installed game, MCDK, WGC, repository checkout or older
evidence bundle. From its directory, run:

```powershell
python -I -B -X utf8 replay.py replay . ../frame-block-light-replay-v1
```

The output directory must be fresh. Replay verifies every file hash and all
24 WGC receipts, repeats three-view calibration, reproduces the grass ROI
numbers and all 11 montage/mask images, reconstructs the corrected atlas
from packaged native source bytes using the corrected shared generator, and
checks exact exit identities. Replay success is not phase or appearance
acceptance. The candidate has no corrected native screenshot.
