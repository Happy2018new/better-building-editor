# Block State Transforms

The projection editor rotates and mirrors native Bedrock block states using the
name/aux/state table generated from the NEMC palette export. Direction rules
are property-based. An unreviewed state key or directional value fails the
audit, and an orientation missing from the native palette raises
`UnrepresentableTransform`.

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
types. Review the palette diff and add geometric fixtures when a new
directional property or value appears.

## Audit Coverage and Limits

The checked-in palette has 15,858 name/aux records. The audit resolves 15,849
records for each horizontal rotation and horizontal mirror. The remaining nine
are `huge_mushroom_bits` values 11, 12, and 13 for brown mushroom blocks, red
mushroom blocks, and mushroom stems; the native table has no reviewed mapping
for those codes.

Vertical reflection resolves 9,353 records and rejects 6,505 because a native
opposite orientation is missing. The failures are 6,248 horizontal-only
`minecraft:cardinal_direction` records, 162 pale moss carpet states, 27
mushroom cap states, 26 top-facing torch states, 24 side-attached bell states,
eight wall-lever states, one single seagrass state, and the same nine
unmapped mushroom codes. These are per-record counts for this palette version.
An unsupported transform raises `UnrepresentableTransform`; callers must not
silently retain the source orientation.

Several state names need context rather than a generic numeric remap. For
example, `direction` is interpreted with the other states to distinguish beds,
trapdoors, bells, and repeaters; `hanging` has block-specific vertical behavior;
and jigsaw `rotation` depends on its `facing_direction`. Directional values
are explicitly enumerated and checked during the audit. Other known states are
treated as invariant under geometric transforms.
