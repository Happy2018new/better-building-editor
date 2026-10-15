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

The provisional pose is a half-block cube centered at `(0,0,0.1875)` relative
to the item slot. This is an unmeasured starting value. Native six-face,
eight-rotation, thickness and frame-body depth controls must establish its
actual scale, center, axes and occlusion. It is not the previously measured
flat-icon front plane.

Every candidate records `fixed_default_item_axes`. Tall bitmap strips freeze
the source's top square, explicitly recorded as
`animated_texture_frozen_first_frame`. Flipbook declarations are also recorded,
including square source images; those are labeled
`animated_texture_frozen_source_snapshot`. This does not assert their native
animation starts at that snapshot. Grass-style alpha-mask overlay baking is
labeled `alpha_mask_overlay_pending_native_pixels` and remains unaccepted.
This initial static checkpoint does not yet route block enchantments. Artificially
enchanted ordinary blocks, especially quartz block, are requested follow-up work,
not a final exclusion. Arbitrary unknown item metadata still needs explicit
semantics. Shelf and campfire content are outside this frame adapter's scope.

## Verification and First Native Matrix

Current offline checks cover actual item/aux separation, atlas face interiors,
mesh winding/normals, all 48 frame facing/rotation codes, immutable source NBT,
frame-only ownership, unsupported metadata refusal, missing-target filtering,
independent qualification and material gates. The 24 UI/world GLES 2/3 shader
variants compile/link. These checks do not replace native pixel acceptance.

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
The ordinary block and empty-frame control preserve the native orientation
template. The native comparison inserts actual inventory items through
`PlayerUseItemToPos`, validates typed name/aux, then restores confirmed-air
test cells and the player. It does not write synthetic native item NBT.

After the first scale/center/thickness check, expand to all six frame faces
and eight rotations, oblique views, frame-body and shared editor depth,
world full/missing/occupied/restored, hidden-before/shown/hidden-after controls,
and resource cleanup. Keep the native thresholds unchanged. Any capture error,
missing side, alias mismatch, source drift or unsupported material leaves the
independent gate false.
