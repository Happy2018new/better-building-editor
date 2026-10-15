# Frame block item candidates R21

Status: unqualified, frame only. Neither the existing flat icon gate nor the
independent frame block gate is enabled. This implements offline candidates;
the counts below are not accepted native shape or production coverage.

## Exact target and source selection

Target engine is NEMC `3.10.0.420447`. The generator reads that installed
engine's `blocks.json`, terrain atlas and flipbook declarations from
`vanilla_base`, `vanilla`, then `vanilla_netease`. It prefers
`carried_textures`, resolves all six faces, and records source pack, relative
path, raw bitmap hash, selected atlas record and explicit image operations.
PNG and TGA are decoded rather than replacing missing assets with icons.

The two complete native observation catalogs in `.runtime/item-catalog-r16/`
and `.runtime/item-catalog-info-r16/` bind actual item names, auxiliary values,
native item type and `GetItemTexture` paths to the exact engine. Existing
palette canonicalization resolves legacy aliases such as `log:1`; the observed
texture must match a resolved face source. Unknown auxiliary values, ambiguous
atlas arrays and unknown texture modifiers are rejected.

The retained generated catalog is
`tools/data/frame_block_item_catalog_nemc_3.10.0.420447.json`. It records all
854 candidate item/aux pairs, 376 item IDs, 342 resources, supported item rows,
the complete native block-item census and rejection reasons. Of 1338 observed
block-item IDs, 962 have no admitted candidate pair; 366 admitted IDs also have
rejected auxiliary observations. These counts describe source candidates only.

## Shape Evidence and Exclusions

| Candidate family | Shape sieve | Current acceptance |
| --- | --- | --- |
| Ordinary opaque cube candidates | Prior 3.9 native `solid=True`, exact 3.10 block item and six-face texture mapping | No 3.10 shape or pose acceptance |
| Glass and stained glass | Explicit cube candidate exception plus exact 3.10 face mapping | Separate cutout/translucent acceptance required |
| Stairs and slabs | Excluded pending their own geometry adapters | No candidate |
| Chests, heads and other special geometry | Excluded by shape sieve or explicit deny list | No candidate |

`native_block_metadata_nemc_3.9.0.401155.json` is a conservative candidate
input, not proof that every selected 3.10 item is a full cube. Its version and
hash are recorded. Six texture faces alone also do not prove native geometry.
No shape becomes supported solely because `solid` is true. The initial native
controls prioritize stone, grass block, oak log and oak planks. Glass is measured
separately. Known special cases including beacon, spawners, vault, honey block,
camera, barrier, education and hidden internals are excluded explicitly.

## Resources and Degradations

Every mesh has six cube faces, real normals, nonzero XYZ extent and four stable
item transport slots. Each face occupies a padded cell in a six-face atlas.
There are 324 opaque, one cutout and 17 translucent resource candidates, with
684 independent UI/world model registrations and six material registrations.
Translucent fragments preserve fractional source alpha. Material admission is
independent, so opaque acceptance cannot admit glass automatically.

The generated catalog still retains the provisional half-block cube centered
at `(0,0,0.1875)` relative to the item slot. The first actual stone comparison
disproved this pose: product bounds are 171 by 179 pixels, versus native
75 by 78 pixels at the same calibrated camera. The corrected isolated two-item
candidate is described below; shared production resources have not adopted it.

Every candidate records `fixed_default_item_axes`. Tall bitmap strips freeze
the source's top square, explicitly recorded as
`animated_texture_frozen_first_frame`. Flipbook declarations are also recorded,
including square source images; those are labeled
`animated_texture_frozen_source_snapshot`. This does not assert their native
animation starts at that snapshot. Grass-style alpha-mask overlay baking is
labeled `alpha_mask_overlay_pending_native_pixels` and remains unaccepted.
Artificially enchanted ordinary blocks, including quartz block, retain their
real `ench` payload and route the glint bit through the existing transport.
Ordinary quartz is still owned by the flat icon adapter; `quartz_block` uses
six-face geometry. Each cube face computes independent unit-square glint UV
from its local geometry and normal, so atlas padding and neighboring faces do
not compress the glint pattern. GLES 2/3 GPU readback verifies all 96 mesh
vertices, including all four transport slots. Native glint direction, phase,
brightness and occlusion remain unaccepted; the inherited flat-item candidate
is not native block glint evidence. Arbitrary unknown item metadata still needs
explicit semantics. Shelf and campfire are outside this frame adapter's scope.

## Verification and First Native Matrix

Current offline checks cover actual item/aux separation, atlas face interiors,
mesh winding/normals, all 48 frame facing/rotation codes, immutable source NBT,
frame-only ownership, unsupported metadata refusal, missing-target filtering,
independent qualification and material gates. All 108 `test_item*.py` and
22 frame-block checks pass, including bounded capture rows, three-view pose
recovery and budget-abort restoration. Thirty shader variants compile/link: UI/world GLES
2/3 and the GLES3 world skinning/instance paths. GLES2 skeletal headers use
unsupported non-square matrices, so that path is explicitly outside this test.
GPU pixel readback covers 96 face-local UVs and 4608 position/normal samples
each for all 48 frame poses in both GLES versions. These checks do not replace
native pixel acceptance.

Rebuild candidates and verify generated outputs with:

```powershell
python -B -X utf8 tools/generate_frame_block_items.py --install D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447 --texture-observations .runtime/item-catalog-r16/catalog.json --basic-observations .runtime/item-catalog-info-r16/catalog.json
python -B -X utf8 tools/generate_frame_block_items.py --install D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447 --check
python -B -X utf8 -m unittest discover -s tests -p test_frame_block_items.py
```

Use a new isolated cold clone with all four automatic reload options false.
The first bounded capture uses `run_visible_items_r16.py` with
`--frame-block-item stone --frame-block-aux 0 --orientation-matrix --icons-only
--skip-closeup --orientation-cases frame_f2_r0 --near-distance 3 --editor-zoom 5`.
Repeat with `--frame-block-item quartz_block --frame-block-enchanted` for the
artificial-enchantment comparison. The first attempt created the native quartz
inventory item but failed at `AddEnchantToInvItem(9,3)`, before frame insertion.
A separate owned inventory probe found that `SpawnItemToPlayerInv` with
`enchantData=[(9,3)]` also returns false for both stone and quartz block. All
inventory slots were checked and restored. These public API limitations do not
exclude artificial enchantment support.
The ordinary block and empty-frame control preserve the native orientation
template. The native comparison inserts actual inventory items through
`PlayerUseItemToPos`, validates typed name/aux, then restores confirmed-air
test cells and the player. Plain comparisons use no synthetic frame item NBT.
The revised artificial comparison first inserts an ordinary inventory block,
keeps its actual typed `Item.Block` compound, then copies only the previously
observed native sword enchant tag through `SetBlockEntityData`. Its report
explicitly labels this synthetic enchantment write. It requires server and
client enchantment readback before capture. This revised runtime route has not
yet been executed or visually accepted.

## First Native Evidence and Corrected Candidate

`docs/evidence/frame-block-candidate-r21-v1/manifest.json` binds ten sanitized
artifacts. `stone-comparison.png` contains equal-camera crops. The original
stone case completed calibration, editor/full/missing captures, actual native
inventory insertion and typed name/aux/NBT readback, then restored the test
cells and player. Both capture cases retained stable source snapshots and
reported no native item shader compiler errors. The quartz case failed and
was restored; it produced no enchanted native block-frame pixels.

The independent hull analyzer uses hidden-before/shown/hidden-after pixels,
all 360 support directions and calibrated vertical FOV 66.6 degrees. A
frame-centered fit gives scale 0.248083 and center Z 0.440248. The grid-aligned
candidate scale 0.25 / center Z 0.4375 has support RMS 0.915 pixels and maximum
1.519 pixels; the old pose has RMS 60.642 pixels. A free four-parameter fit has
a near-zero Jacobian singular value: this single camera cannot independently
establish scale, center and absolute depth. Six-face, oblique and support-depth
holdouts remain necessary. Quartz block transfers the candidate pose and has
no independent native geometry acceptance yet.

`tools/prepare_frame_block_pose_r21.py` creates only stone/quartz meshes, two
matching vertex shaders, three unchanged fragments and a two-item candidate
profile in a separate output directory. All qualification fields remain false.
It does not alter the shared model/material registrations or generated catalog.
Its immutable output is `.runtime/frame-block-r21-pose-candidate-v2/`.

```powershell
python -B -X utf8 tools/analyze_frame_block_pose_r21.py .runtime/frame-block-r21-stone-front-v1/report.json .runtime/frame-block-r21-stone-fit-new
python -B -X utf8 tools/prepare_frame_block_pose_r21.py --fit .runtime/frame-block-r21-stone-fit-new/fit.json --output .runtime/frame-block-r21-pose-candidate-new
```

After both cases restored, the owner-bound close used `WM_CLOSE` without force.
The first stop timed out; later both process identities were absent and the
managed session was recorded stopped. Windows Application Error 1000 records
PID 5172, matching its exact creation identity, crashing in `ucrtbase.dll` with
`c0000409` at 2026-10-16 00:55:23 +08:00. This is a shutdown crash, not a clean
normal exit. The exact close-request timestamp was not persisted, and its
cause remains unresolved. Maximum observed handles before close were 182168.
No new game was launched during this offline follow-up.

After the first scale/center/thickness check, expand to all six frame faces
and eight rotations, oblique views, frame-body and shared editor depth,
world full/missing/occupied/restored, hidden-before/shown/hidden-after controls,
and resource cleanup. Keep the native thresholds unchanged. Any capture error,
missing side, alias mismatch, source drift or unsupported material leaves the
independent gate false.

## Bounded Depth Holdouts

The next offline frozen clone is `.runtime/projects/frame-block-r21-pose-v3`,
owner `item-r20`, source digest
`36d897c8bd8e190c83d117b2c5ddc3c9feb454092b0e7f0a145c061c410c2c49`.
It contains the quarter-cube candidate for only stone and quartz block, with
all four reload settings false. Its six declared cases use each item at
0 and +/-75 degrees. Quartz block cases explicitly request the synthetic
enchantment route. Preparation does not launch a game.

`probe_frame_block_enchantment_r21.py` performs a small owner-bound no-screenshot
probe before this matrix. It must confirm actual preserved `Item.Block`,
name/aux/count, and `[(9,3)]` enchantments on server and client, then restore
the air cells, inventory slot, player foot position and rotation. Its result
never constitutes pixel acceptance. Public enchant API rejection evidence is
retained separately.

`frame_block_capture_matrix_r21.py` bounds rows and preserves the orientation
templates. `run_visible_items_r16.py --frame-block-batch <manifest>` shares
one independent camera calibration across those rows. The optional budget
callback now checks all six calibration WGC captures, and the runner checks
its budget before fixture setup and every later screenshot. The planned
limits are 200000 owned handles and at least 6 GiB of system commit reserve.
Cold launch also reserves 3 GiB above that runtime minimum. At most two live
MC games, including any user game, may coexist.

`analyze_frame_block_multiview_r21.py` compares independent native and product
silhouettes, reports joint pose conditioning, and scores the predeclared
candidate without substituting its fitted parameters. A full cube in one
camera retains the scale/depth degeneracy. A clipped model introduces an
additional known support plane; every discarded vertex ray must intersect
the actual solid support. The diagnostic still requires all three camera
angles for each item. Blank and shifted silhouettes are negative controls.
This north-facing rotation-zero batch does not accept UI pixels, materials,
textures, glint, the remaining frame poses, or production use.

## Restored Native Holdout Results

The frozen v3 run completed its independent no-screenshot enchantment probe,
six-case matrix, all fixture restoration and unchanged-source checks. The
replayable evidence is `docs/evidence/frame-block-holdouts-r21-v1/`. Its 80
unaltered PNGs include 74 main captures and six independent camera calibration
captures. Calibration passes at vertical FOV 66.6 degrees. Every one of the
12 native/full-or-missing silhouette pairs passes unchanged thresholds:
five cases are pixel-identical; stone -75 degrees differs by four pixels,
IoU 0.99915754, maximum edge distance one pixel and P95 zero.

The original support-only analytic model still fails its oblique holdouts,
including the native references themselves. Its 8-9 pixel overprediction
extends into the native frame backboard. This missing occluder biases its
joint fit; do not replace the fixed scale 0.25 and center Z 0.4375 from that
fit. Paired visible geometry agrees, while absolute-depth certification and
the aggregate `geometry_holdouts_passed` remain false. The original failed
result and thresholds are preserved in the bundle.

The independent probe and all three quartz cases preserve actual native
`Item.Block` through plain inventory insertion and explicitly synthetic
enchant-tag application. Server and client agree on name, auxiliary value,
count, block state/version and enchantment (9,3). Native and product quartz
screenshots visibly show glint. These shown frames do not accept glint motion,
direction, phase or brightness. Public enchant-manufacturing API failures
remain separate evidence.

The normal-only close request followed successful restoration, but the game
eventually exited `0xC0000409`; MCDK exited zero. Retained process handles and
WER record 80432 match game PID 15144 and exact creation identity
134365611080856581. Event 80433 correlates by report ID. The fault module is
`ucrtbase.dll`; no root cause or clean-exit claim is inferred.

Next, include independently measured frame-backboard geometry in pose
diagnostics, then measure grass, log and planks with glass separate. Keep the
existing six-face/eight-rotation and lifecycle gates. Production admission
also needs an explicit validated `(name, aux)` whitelist; an opaque-material
toggle must not admit all 324 opaque resource candidates.
