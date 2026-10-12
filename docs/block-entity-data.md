# Block Entity Data Coverage

This document separates the numeric entity reference, preservation of available
payloads, and spatial field transformations. The reference is not a list of
allowed runtime entities. Unknown identifiers and unknown fields remain data.

## Versioned Entity Reference

`reference/block_entities/nemc_3.9_reference.json` has `schema_version=1` and
contains all 59 numeric IDs and names provided by the user on 2026-10-10.
Its source is `user_provided`; its NEMC version remains unconfirmed until native
observations provide independent evidence. Unlisted numeric IDs are not declared
invalid or reserved.

Numeric enum IDs, NBT root `id` strings, block identifiers such as
`minecraft:chest`, and client renderer fields belong to different interfaces.
The presence of a block name in the block registry does not prove that it has a
block entity, and an observed NBT name does not verify its numeric enum ID.

## Payload Preservation

The versioned actor envelope retains separate client renderer data and tagged
NBT when those are available. Cell storage and serialization preserve both
without requiring an identifier from the reference. Coordinates and recognized
spatial fields can be transformed while tags, key types and unrelated metadata
are retained. Nested item data, commands and unknown fields remain opaque.

Production world import combines client renderer data with authoritative server
NBT for the survey wand's registered selection. The server captures full entity
payloads, including available container `Items`, and locks the selection for the
transfer. Out-of-scope or invalid requests are rejected silently; registration
and transfer state are cleared after completion or cancellation. This keeps NBT
capture tied to the selected import rather than exposing arbitrary coordinate
reads. The actor envelope and versioned saved formats preserve both sources.
Reference entries are still not proof that a native renderer can display every
entity or that every enum exists in the current game version.

## Spatial Field Adapters

The adapter schema in `projection/nbt_spatial.py` is version 3. Its field rules
are independent of the numeric reference. A field is rewritten only when its
type and range are valid; missing fields are not added and invalid fields are
preserved.

Client field rules apply only to the renderer branch of the actor envelope or
an identified standalone renderer payload. The NBT branch uses known native
entity adapters; matching client field names in unknown native NBT remain
opaque. Typed standalone NBT follows the same boundary. Root coordinates still
rebase independently of renderer direction rules.

| Payload Scope | Fields | Behavior | Evidence And Limits |
| --- | --- | --- | --- |
| Root entity coordinates | `x`, `y`, `z` | Translate by cell displacement | Root integer coordinates only; nested fields remain opaque |
| Root chest pairing | `pairx`, `pairz` | Translate with the cell, rotate or mirror pair offset | Valid integer pairs only; Y mirror preserves horizontal offset |
| Client renderer direction | `facingDirection` | Transform six face directions | Uses the same geometric direction transform as native block states |
| Client standing sign | `signStandingRotation` | Transform 16 horizontal angles | Renderer convention is the native `ground_sign_direction` convention |
| Client double chest | `chestMainSubChest`, `chestModelOffset` | Swap halves and update model offset on X/Z mirrors | Requires `chestIsLargeChest=true`; rotations and Y mirror preserve role |
| NBT `ShulkerBox` | `facing` | Transform six face directions | Native NEMC diagnostic confirmed Byte values 0..5 |
| NBT `ItemFrame`, `GlowItemFrame` | `ItemRotation` | Transform clockwise Float degrees in the frame's local plane | The native eight-angle API probe confirmed Float degrees; top/bottom frames also change their local angle on Y rotations, walls retain it; all six face normals transform with their block state |
| NBT `Chest` | `pairlead`, `renderlead` | Flip each valid Boolean/Byte 0..1 on X/Z mirrors | Requires valid pairing coordinates; native main half has `pairlead=1`, `renderlead=0`, and sub half has the opposite; rotations and Y mirror preserve both |
| Any other root or nested fields | All unrecognized fields | Preserve exactly | An enum reference entry does not create a spatial adapter |

Native ordinary and copper double chest diagnostics expose the same `Chest`
NBT identifier and complementary lead fields. The rule therefore follows the
observed entity schema rather than a separate copper block-name list.

Pure geometry tests check all six Shulker faces, pair coordinate offsets, both
chest lead fields, Byte/Boolean and byte-key preservation, inverse operations,
four-turn closure, and unchanged inventories or nested custom fields.

## Observed Native Defaults

`tools/data/native_block_entity_defaults_nemc_3.9.0.401155.json` retains the
versioned default NBT snapshot from the 2026-10-10 disposable native probe. It
contains 155 block payloads and 57 distinct root identifiers. The original probe
SHA-256 and native version/palette hash are retained. All payloads were captured
after individual block states matched the native table. The complete combined
water probe verified 15,831 of 15,839 states; its eight bed state mismatches are
recorded separately from these successfully observed defaults.

The native default field audit is
`reference/block_entities/nemc_3.9_default_fields.json`. The adjacent observed
reference diff confirms 57 names, including native `CraftingTable`, and leaves
`NeteaseContainer` and `ModBlock` unobserved in this vanilla sample. Numeric enum
IDs remain unverified. `PistonArm` is observed on `piston` / `sticky_piston`,
rather than inferred from the `piston_arm_collision` helper block.

The public entity blueprints use these complete tagged payloads. The generator
preserves unknown fields and lazily compressed templates; it never fabricates a
missing entity identity. See [Built-In Test Blueprints](debug-blueprints.md) for
fixture coordinates and regeneration commands.

`projection/entity_defaults.py` and its generated `entity_defaults_data.py`
share the same native snapshot between production editing and those fixtures.
Before a rotation or mirror, a cell without complete NBT may acquire a native
template only when its observed entity has a verified actor-only direction rule.
This currently applies to all 17 Shulker colours. The template is rebased to the
cell, and a valid old client `facingDirection` initializes native Byte `facing`.
Existing complete NBT, inventories and unknown envelope fields are preserved.
The snapshot version and registry fingerprint must match before initialization;
stale templates fail the editor operation before any document change.

## Fields Awaiting Native Evidence

The adjacent `bedrock-world-operator` checkout stores and encodes arbitrary
block entity NBT but contains no entity-specific direction schemas. It is a
reference for lossless tagged data and disk encoding, not evidence for direction
semantics. Its `world/standard_nbt.go` and Python NBT codecs do not define
`Skull.Rot`, `ItemFrame.ItemRotation`, or `StructureBlock` transformations.

The PowerNukkitX source supplies the following leads. They are not sufficient
to change NEMC runtime behavior without native observations:

| Entity | Candidate Fields | Current Handling | Evidence Needed |
| --- | --- | --- | --- |
| `Skull` | `Rotation` | Transform floor yaw | Native nondefault player placements confirm Float degrees matching visible `rotation`, zero along +Z and the [-180,180) convention; wall yaw stays unchanged and the block face transforms |
| `ItemFrame`, `GlowItemFrame` | `ItemRotation` | Transform typed Float clockwise degrees | NEMC `SetFrameRotation` / `GetFrameRotation` confirmed eight angles 0..315; independent 3D-vector tests cover six local face planes and mirrors; native six-face GPU validation remains required |
| `StructureBlock` | `rotation`, `mirror`, `x/y/zStructureOffset`, `x/y/zStructureSize` | Preserve | Native defaults confirm Byte rotation/mirror and Int offsets/sizes; nondefault value meanings, anchor coordinates and transform composition still need observations |
| `PistonArm`, `MovingBlock`, `EndGateway` and other spatial entities | Entity-specific coordinates or directions | Preserve | Native data and rules separating world coordinates from opaque saved payloads |

Block-state rotation and mirroring continue to use the native registry for all
vanilla blocks. These pending NBT-specific adapters do not restrict that
block-state support.

The official `SetBlockEntityData` documentation states that changing facing or
state fields affects entity data without changing rendering. Therefore six
NBT `facing` values do not establish six native visual poses. Shulker acceptance
uses actual player placement on each support face, client palette export and
fixed-camera pixel comparisons. `CombineBlockPaletteToGeometry` also documents
static default poses and no animation support, so successful submissions alone
do not establish that the client's block entity pose has been reproduced. See
the six-face regression in [Built-In Test Blueprints](debug-blueprints.md).

The render adapter in `projection/entity_render.py` schema 3 resolves closed
Shulker poses from the complete tagged NBT already captured for the registered
selection, falling back to an observed client renderer direction and finally
the native up default. It changes only native geometry input to a hidden static
model. The saved/native block identifier, full NBT and world-writing data stay
intact. No extra coordinate-read channel is introduced. Its generated closed
lid/base geometry covers all 17 colours and six faces; cold-resource native
visual acceptance is required separately from pure data and geometry tests.

The same production adapter now refreshes observed sign front/back text, colour,
glow and rotation fields, and decorated-pot cardinal direction. Their matching
versioned observations and palette tests verify the reconstructed input, while
glyph pixels and mirrored four-face pot decorations remain separate acceptance
requirements. Ordinary, trapped, ender and copper chest static adapters use
64x64 packed face textures and retain the complete saved/native payloads.

## Visual Coverage Boundaries

The native snapshot is evidence of available data and field types. It is not
proof that `CombineBlockPaletteToGeometry` displays every nondefault appearance.
The current fixture and adapter audit leaves the following concrete checks open:

| Entity | Available Native Evidence | Remaining Appearance Or Direction Check |
| --- | --- | --- |
| `ShulkerBox` | All 17 block names, native default Byte `facing=1`, actual player placement on six support faces | Compare actual native MC blocks with editor/projection static meshes; also check that real-world generated boxes show their written orientation, because an NBT setter alone does not guarantee a pose update |
| `Bed` | Default Byte `color=14`; production writer readback checks `color=7`, both halves, all 16 states and both write orders | Nondefault colours in client palettes and actual editor/projection pixels; correct server readback does not establish displayed colour |
| `Skull` | Seven modern block names, Float degree `Rotation`, matching client `rotation`, Byte `SkullType=255`; eight native floor yaw samples and four wall faces | Floor yaw transforms and native field adapter have independent-vector tests; editor and projection GPU appearance remain separately pending |
| `Banner` | Default Int `Base=0`, `Type=0` | Nondefault base colours and pattern-bearing native client palettes; empty/default samples do not cover patterns |
| `ItemFrame`, `GlowItemFrame` | Native default payload has no displayed item or item rotation | Filled frame item appearance and local rotation, including mirrors; no default field value establishes their semantics |
| `DecoratedPot`, `FlowerPot` | Native empty/default payloads; decorated pot records an empty `item` compound | Nonempty decoration or plant appearance; preservation of future fields is separate from render support |
| `MobSpawner`, `TrialSpawner`, `Vault`, `Lectern` and other contents-driven entities | Complete available native default payloads | Nondefault displayed contents; a successfully combined static default pose does not certify the displayed item/entity or animation |

No new runtime allowlist follows from this table. Unknown entity payloads still
round-trip. Any additional appearance adapter must use a matching versioned
native observation, retain native saved/world identities, and have editor and
actual projection evidence recorded separately.

`tools/verify_native_entity_appearances.py` captures 19 owned native cases in one
batch: eight floor skull yaw samples, four wall faces, one nondefault dragon
head yaw, two paired beds with `SetBedColor`, filled ordinary/glowing frames,
and ordinary/ominous native banners. It preserves the actual item readbacks,
player angles, server NBT and client palette actor dictionaries before and after
filling frames. Frame interaction waits for client replication first. Banners
use the documented native `userData.Type=1` ominous item, so this does not invent
pattern field names. Failed frame fills remain explicit observations.

The native area consists only of cells checked empty at the beginning. A finally
block clears all reserved positions in two passes, clears the originally empty
inventory slot and restores player rotation. The host saves a final partial
server snapshot before cleanup even if placement or replication fails.
Each resource restore is attempted independently if an API raises, including
when the final snapshot itself fails. Errors retain the saved fixture state for
a subsequent cleanup attempt; a cleanup failure cannot be marked completed.
Client replication is polled until all observed block names are present before
frame filling, with a bounded timeout listing the missing cases.
Run it through the owned development instance:

```powershell
python tools/verify_native_entity_appearances.py entity-appearances.json
```

This captures nondefault field evidence, not successful editor/projection
rendering. Retain the resulting report with its game version and palette hash
before defining units, direction conventions or additional render adapters.

The completed 2026-10-10 batch is retained in
`tools/data/native_entity_appearances_nemc_3.9.0.401155.json`. Regenerate it with
`tools/generate_native_appearances.py <report> --check` to verify the report hash,
game version, palette fingerprint and all 19 field observations. Player inventory
readbacks are omitted; actual per-cell NBT and visible palette data remain.
`native_appearance.py` rejects a different game version or registry fingerprint.
The Skull adapter supplies only observed Float rotation and Byte skull type to
the native renderer, with the face taken from the actual material state. Saved
payloads, nested unknown data and wall-only unused yaw remain intact.

The batch also found that `SetBedColor` changes the head entity to colours 8/3,
while the foot NBT remains colour 0 and the sampled client palette exposes only
the head. Filled frame and banner actor dictionaries are empty. These samples
are not evidence that Items, banner Base/Type or bed foot colours are obtainable
through the ordinary client import path. The authorized server capture path
preserves their complete typed NBT independently of the client render schema.
The Bed adapter converts the observed Byte colour and current material direction
to native actor fields; visible bed direction now follows rotations and mirrors.
This conversion still needs separate GPU verification for its two physical halves.

`test.entities.appearances` retains all 19 sample cases. Their stable coordinates
are defined by `debug_appearance_blueprints.CASE_POSITIONS`: columns advance six
blocks and rows advance eight blocks, starting at `(3, 1, 3)`. The silver and
light-blue bed feet are `(9, 1, 19)` and `(15, 1, 19)`, with heads one block along
+Z. Filled ordinary/glowing frames are `(21, 1, 19)` / `(27, 1, 19)`; ordinary and
ominous banners are `(33, 1, 19)` / `(3, 1, 27)`. The blueprint uses the actual
typed payloads and observed visible fields, rebasing coordinates without
inventing render fields for Frame or Banner.

`tools/data/native_frame_rotations_nemc_3.9.0.401155.json` retains the native
16-sample frame rotation batch, including both ordinary and glowing frame
server palettes. Both native palettes expose empty actor dictionaries even for
filled frames; they are not a usable item-render schema. Its source report hash,
native version and palette fingerprint are linked by `frame_rotation_data.py`.
Regenerate or verify the snapshot with:

```powershell
python tools/generate_native_frame_rotations.py <report.json> --check
```

Frame angles are rewritten only for original frame materials, recognized root
entity IDs and existing Float tags in the observed range. Byte rotation schemes,
unknown entities, nested item tags and future fields remain unchanged. Local
planes use world up for wall frames and north/south for floor/ceiling frames.
Rotations and mirrors transform the item's top vector into the new frame plane;
they preserve representable native item orientation rather than reflecting
asymmetric item artwork. This geometric rule is distinct from GPU proof of its
native face-plane basis and from displaying the saved Item contents.

The second real Shulker comparison observed all six native boxes from a low
side camera, but no native boxes from an upper detached camera, despite intact
support cells and server readbacks. The acceptance tool now uses one matching
low side camera for every direction and waits for two settled camera samples.
If its native reference is invisible, the proxy comparison is indeterminate.
The tool does not claim opening-face coverage or correct upper-camera native
visibility from these samples.

## Native Observation Diff

`tools/diff_block_entities.py` compares the reference with an explicit entity
list, the native placement report, or a versioned native default probe:

```powershell
python tools/diff_block_entities.py `
  --observed native-player-placement.json `
  --output native-block-entity-diff.json
```

The native report paths use `actors[].cells[].nbt` or `block_entities.*.nbt`
root string IDs. Typed
compounds and typed ID tags are supported; block names and case labels are
never interpreted as entity identifiers. A client palette stored as a Python
`repr` string is not parsed or executed.

An explicit numeric observation uses this input schema:

```json
{
  "schema_version": 1,
  "entities": [
    {"name": "Chest", "enum_id": 2},
    {"name": "ShulkerBox", "enum_id": 25}
  ]
}
```

The versioned diff records input hashes, matched names, numeric conflicts,
unknown observed names and names unobserved in the sample. Name-only
observations never confirm numeric IDs. Unobserved names are coverage gaps in
the sample, not proof of missing native support. New versions should retain
the old reference and compare independently captured observations before
updating source/version confirmation or adding a proven spatial field adapter.
