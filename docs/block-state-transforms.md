# Block State Transforms

The projection editor rotates and mirrors native Bedrock block states using the
name/aux/state table generated from the NEMC palette export. Direction rules
are property-based, with no block-name allowlist. Every exported block can use
the six editor operations. An unreviewed state key or directional value fails
the audit, and an unexpected target missing from the native palette still
raises `UnrepresentableTransform` rather than quietly keeping the old state.

## Mirror Semantics

The editor mirrors cell coordinates and native block states. It does not
reflect arbitrary meshes or textures. Where Minecraft exposes opposite native
states, those states change; a block that has no upside-down form keeps its
legal upright appearance at the mirrored cell position. This definition makes
all six operations usable, reversible, and closed over the game's state table.

| State or Shape | Horizontal Rotation and Mirrors | Y Mirror |
| --- | --- | --- |
| Stairs and trapdoors | Transform their east/west/south/north encoding | Swap `upside_down_bit` |
| Slabs and upper/lower block halves | Preserve half; transform other direction states | Swap half |
| Doors | Transform cardinal direction; mirrors swap hinge | Swap upper/lower half; retain horizontal hinge side |
| Six-way facing and multi-face attachments | Transform each face | Swap up/down faces |
| Walls, vines, and side connections | Transform individual side keys or bits | Preserve horizontal connections |
| Rails | Transform both endpoints; retain straight/curve/slope kind | Swap high end of slopes |
| Jigsaws | Transform facing and vertical blocks' secondary axis | Swap up/down facing and remap secondary axis |
| Crafters | Transform both orientation axes | Swap `up_*` / `down_*`; keep horizontal `*_up` upright |
| Bookshelf contents | Horizontal mirrors reverse each row's slots | Swap upper/lower content rows, retaining native upright housing |
| Standing/hanging bell or grindstone; lanterns; pointed dripstone | Transform available direction states | Swap native standing/hanging pair |
| Side-attached bells, wall levers, hanging signs | Transform available horizontal states | Keep legal side/suspension state; transform any expressible facing |
| Beds, chests, furnaces, ground signs, ground torches, single seagrass | Transform expressible direction states | Keep native upright appearance |
| Mushroom caps | Transform textured side faces | Keep native cap orientation; no underside cap state exists |

State mirroring does not promise a geometrically upside-down bed, furnace,
standing sign, torch, or mushroom cap. In particular it never invents a
`torch_facing_direction=bottom` or a crafter `east_down` state. Similarly,
standing/hanging transitions describe native attachment semantics, not an
exact reflection of decorations in the native model.

Mushroom codes 11, 12, and 13 appear in the exported palette but are reserved:
the reviewed native mappings define directional cap codes 1 through 9,
stem code 10, and invariant codes 0, 14, and 15. Reserved codes remain byte-for-byte
unchanged in every operation; they are not guessed or converted into a
different mushroom variant.

The checked-in 3.9.0.401155 source dump is
[`nemc_3.9.0.401155.json`](reference/block_palettes/nemc_3.9.0.401155.json).
Its SHA-256, export timestamp, record/name counts, and state-key count are in
[`block_registry_manifest.json`](../tools/data/block_registry_manifest.json).

For a later export, keep the versioned dump under
`docs/reference/block_palettes/nemc_<version>.json`, then run:

```powershell
python tools/generate_block_registry.py docs/reference/block_palettes/nemc_<version>.json
python tools/check_block_registry.py docs/reference/block_palettes/nemc_<version>.json
python tools/diff_block_palettes.py docs/reference/block_palettes/nemc_3.9.0.401155.json docs/reference/block_palettes/nemc_<version>.json
python -m unittest discover -s tests
```

The registry generator preserves each block's native aux IDs and state value
types. Existing property rules apply automatically to newly added materials
and names. Review the palette diff and add geometric fixtures when a new
directional property or value appears. The audit rejects unknown properties,
unknown directional values, missing native targets, and broken transform laws;
adding an invariant classification is an explicit review decision, not an
automatic fallback based on a property's spelling.

## Audit Coverage and Limits

The checked-in palette has 15,858 name/aux records. All 15,858 records resolve
to a native target for each horizontal rotation and each X/Y/Z mirror under
the state semantics above. The audit checks every record, including exported
reserved codes, with zero unsupported transforms.

The audit's geometric fixtures decode states into independent world-space
directions and points, then apply coordinate matrices rather than calling the
transformer's remapping helpers. They cover stair occupancy in all eight
half/direction combinations, door hinge sides, rail endpoints and slopes,
bookshelf slot positions, mushroom cap sides, axis alignment, signs, face masks,
attachment pairs, jigsaw secondary axes, and wall/carpet connections.

Every record also passes these group-law checks:

- An operation followed by its inverse restores the original typed states.
- Four 90-degree turns restore the original typed states.
- X followed by Z mirroring equals a 180-degree turn.
- X mirror, 90-degree turn, X mirror equals a 270-degree turn.
- Y mirroring commutes with horizontal rotation and X/Z mirroring.

These offline checks establish legal and coherent state transforms. They do
not replace the integrated game check of neighbor-derived stair corners,
rail/wall connections, paired actors, editor preview, or projection preview.

Several state names need context rather than a generic numeric remap. For
example, `direction` is interpreted with the other states to distinguish beds,
trapdoors, bells, and repeaters; `hanging` has block-specific vertical behavior;
and jigsaw `rotation` depends on its `facing_direction`. Directional values
are explicitly enumerated and checked during the audit. Other known states are
treated as invariant under geometric transforms.

## Reviewed References

The versioned NEMC dump is authoritative for name/aux availability and state
types. Semantic direction fixtures were additionally checked against Bedrock
Wiki's [orientation categories](https://wiki.bedrock.dev/blocks/block-orientation)
and Amulet's Bedrock 1.21.80 conversion mappings for
[stairs](https://github.com/Amulet-Team/PyMCTranslate/blob/main/PyMCTranslate/json/versions/bedrock_1_21_80/block/blockstate/to_universal/minecraft/vanilla/oak_stairs.json),
[trapdoors](https://github.com/Amulet-Team/PyMCTranslate/blob/main/PyMCTranslate/json/versions/bedrock_1_21_80/block/blockstate/to_universal/minecraft/vanilla/trapdoor.json),
[beds](https://github.com/Amulet-Team/PyMCTranslate/blob/main/PyMCTranslate/json/versions/bedrock_1_21_80/block/blockstate/to_universal/minecraft/vanilla/bed.json),
[jigsaws](https://github.com/Amulet-Team/PyMCTranslate/blob/main/PyMCTranslate/json/versions/bedrock_1_21_80/block/blockstate/to_universal/minecraft/vanilla/jigsaw.json),
[crafters](https://github.com/Amulet-Team/PyMCTranslate/blob/main/PyMCTranslate/json/versions/bedrock_1_21_80/block/blockstate/to_universal/minecraft/vanilla/crafter.json),
and [mushroom cap faces](https://github.com/Amulet-Team/PyMCTranslate/blob/main/PyMCTranslate/json/versions/bedrock_1_21_80/block/blockstate/to_universal/minecraft/vanilla/brown_mushroom_block.json).
These references support the geometric fixtures; the game-specific palette
continues to determine the actual target aux, never the external version's
numeric IDs.
