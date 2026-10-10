# Built-In Test Blueprints

The public `测试蓝图` navigation tab is independent of the saved building library
and needs no operator permission. Loading uses the normal draft replacement
confirmation and returns to the workspace. Every load builds a fresh document;
edits, undo history and saves cannot change the next copy of a fixture.

## Stable Identities

Blueprint metadata and entity fixture metadata each use schema version 1.
The category identity, blueprint identity and card `key` are stable automation
targets. Categories are separate pages within the test tab.

| Blueprint Identity | Category | Size | Coverage |
| --- | --- | --- | --- |
| `test.layers.water` | `layers` | 32 × 8 × 24 | Dry, waterlogged and background-only comparisons for twelve materials |
| `test.layers.snow` | `layers` | 32 × 8 × 24 | Six measured coverable plants, two snow depths and snow above leaves |
| `test.groups.parts` | `groups` | 32 × 8 × 24 | Wood/iron doors, beds in four directions and tall plants |
| `test.entities.appearances` | `entities` | 40 × 12 × 36 | 19 actual native nondefault Skull/Bed/Frame/Banner observations |
| `test.entities.signs` | `entities` | 16 × 8 × 10 | Observed two-sided standing and hanging sign text, colour and glow |
| `test.connections.context` | `connections` | 32 × 12 × 32 | Closed rail loop, sloping rails, walls, fence/gate, panes/bars, eight stair corners and ordinary/copper double chests |
| `test.transforms.directions` | `transforms` | 32 × 12 × 32 | Stair facing, log axes, six dispenser faces, lever facing, all ten rail shapes, six Shulker faces and door hinges |
| `test.entities.classic` | `entities` | 40 × 10 × 36 | Classic native entity associations |
| `test.entities.mechanisms` | `entities` | 32 × 10 × 28 | Structure/logic and utility entity associations |
| `test.entities.recent` | `entities` | 32 × 10 × 28 | Recent entity associations available in the current registry |
| `test.registry.vanilla` | `registry` | 64 × 64 × 64 | Every vanilla block type in the current inventory catalogue, with complete grouped parts |

The grey/white floor has grid lines every four cells. Cyan and magenta plinths
provide a visible placement reference. The fixtures are regular editor documents
and can be copied, transformed, exported, shared and projected.

## Coordinates For Acceptance

All coordinates are local to the document, with X/Y/Z in editor order.

- Water fixtures use X `3 + 5 × column`, with six columns. The first row's dry,
  waterlogged and background-only copies are at Z 3, 6 and 9; the second row
  uses Z 13, 16 and 19. The first material is an oak fence at X 3.
- Snow fixtures use X 3, 8, 13, 18, 23 and 28 for short grass, fern, dandelion,
  poppy, blue orchid and allium. Dry copies use Z 3, one-layer snow uses Z 9
  and six-layer snow uses Z 16. The covered cell is at Y 1. Native storage is
  foreground covered snow plus background plant.
- The rail loop covers X/Z 3..11 at Y 1. Its four corners have shapes 6, 7, 8
  and 9. Sloping rails are at X 17, Z 3..8 and Y 1..3.
- The wall cross is centred on `(7,1,17)`. Panes and bars run along Z 19..25 at
  X 17 and 22. Fences and the gate occupy X 17..26 at Z 17.
- Bottom stair corners are centred at `(3,1,23)`, `(8,1,23)`, `(3,1,28)` and
  `(8,1,28)`. The front-adjacent pairs form outer corners; the back-adjacent
  pairs form inner corners. Their top-half equivalents are offset +12 on X.
- Double chests occupy `(26,1,5)` / `(27,1,5)` and the copper equivalents use
  Z 10. Both halves contain reciprocal local pairing coordinates and native
  complementary `pairlead` / `renderlead` fields.
- The vanilla gallery has fourteen columns and rows per level, four cells
  between plinth centres and eight cells between levels. Its order is the
  sorted native catalogue order, so a registry update produces a deterministic
  new gallery.

In automatic edit mode, erasing a wet fence removes the fence first and leaves
ordinary foreground water. Erasing covered snow removes the snow first and
restores the plant to the foreground; the next erase removes the plant.
Explicit foreground/background modes act on the chosen
layer. Undo restores the complete cells and grouped parts.

## Native Evidence And Limitations

Materials and all requested properties resolve through the checked-in native
registry. No fixture constructs aux values by arithmetic. Missing required
materials or states fail before replacing the draft. Newer optional entity
associations absent from the registry are omitted and reported by `coverage()`.

Entity metadata covers the user's 59-entry reference through 57 native-observed
test associations and two exclusions: `NeteaseContainer` and `ModBlock`, which
need real registered definitions. Actual NEMC observations confirm
`CraftingTable` on `minecraft:crafting_table` and `PistonArm` on the piston body.
The exclusions and unavailable associations remain visible in the coverage
report and are not runtime allowlists.

The complete-pair snow probe confirmed that native `SetSnow` rejects tall grass,
large fern and the other two-cell plants even with valid upper halves and soil.
Their grouped editing cases remain in `test.groups.parts`. Imported background
data can still be preserved and erased independently of new placement traits.

The versioned default snapshot retains actual NBT from 155 native blocks and
57 observed root identifiers. `entity_defaults_data.py` stores compact
frozen templates, which decode lazily and rebase into local fixture coordinates.
The editor shares this versioned snapshot when a newly created cell needs an
actor-only direction before rotation or mirroring. Existing complete NBT remains
authoritative; old renderer-only Shulker directions become native typed `facing`
fields while retaining their renderer payload. This prevents a new upward-facing
Shulker from remaining upward after a vertical mirror and makes the resulting
direction available to sharing, clipboard imports and world writes.
Every fixture and every vanilla-gallery entry with an observed native default
uses the complete payload. The three entity pages include all 57 observed
identifiers. Signs use matching NBT and renderer text/colour/glow fields, while
Shulker and chest variations use the independently observed direction and pair
fields. Fixture state aux values are the observed native ones.

The snapshot records its game version, palette hash, original probe hash and
tested/verified state counts. The underlying combined water probe completed
15,839 states, with eight unrelated bed state mismatches; these do not invalidate
the individually verified default payloads. The checked-in field audit records
the observed root fields and SDK tag types. Default scalar values do not prove
direction semantics for entities such as skulls or structure blocks.

A successful pure-Python fixture test verifies data preservation and legal
states; it does not certify the native renderer for every entity.
See [Block Entity Data Coverage](block-entity-data.md) for adapter evidence and
pending native-specific fields.

## Version Updates And Verification

Regenerate the native registry from the new game's dump using the normal block
registry workflow, retain the old versioned source and inspect its diff. Capture
the new native entity defaults and run the matching generator and audit:

```powershell
python tools/generate_entity_blueprints.py native-probe.json `
  --snapshot tools/data/native_block_entity_defaults_nemc_<version>.json `
  --audit docs/reference/block_entities/nemc_<version>_default_fields.json
python tools/diff_block_entities.py `
  --observed tools/data/native_block_entity_defaults_nemc_<version>.json `
  --output docs/reference/block_entities/nemc_<version>_observed_default_diff.json
```

The generator checks the game version, block table hash, exact native aux,
observed entity identifier and root coordinate types. Generation is deterministic
and has `--check` support. The template snapshot fingerprint uses canonical JSON
so checkout line endings do not change it; the original native probe retains its
exact byte hash separately. The public fixtures reject stale templates before
replacing the current draft. Run:

```powershell
python -X utf8 -m unittest discover -s tests -p test_debug_blueprints.py
python -X utf8 -m unittest discover -s tests -p test_entity_blueprint_generator.py
```

The tests verify legal foreground/background states, palette preparation,
independent loads, config/MP4 round trips, reciprocal groups, rail corners,
double-chest fields, automatic erase history and all six whole-document
transform inverses. The catalogue fixture expands automatically from the
regenerated registry. Real-game acceptance should load these same fixture keys
once and inspect both the workspace preview and world projection, then exercise
placement and erasure at the listed coordinates.

### Six-Face Shulker Pixel Regression

`tools/verify_shulker_orientations.py` captures each of six orientations at the
same single-cell position, with the same document size and camera. Input cells
are extracted from `build('test.transforms.directions')`; no independent
synthetic fixture is constructed. `VISUAL_CASES['shulker_orientations']` records
the source cells, clip size, focus and both camera poses with schema version 2.
The built-in fixture checks only the editor preview. The separate world
projection path uses actual native player placements, their client palettes
and complete entity payloads. Their same-direction editor pixel differences
are retained. All six visually identical poses fail even
when the native geometry submission and source data are valid. The image check
rejects missing/too-small models and saves masked images and six-image sheets.
The world check also photographs the six actual MC blocks, using the same
camera offset as each matching projection. All pairs use one low side view;
the tool records the measured camera rather than assuming it views the opening
face. Supports are removed before capture to avoid hiding native shell faces.
The central purple connected component
excludes adjacent fixtures and HUD pixels. A schema-1 image comparison records
each same-face silhouette IoU, relative size error and a six-by-six local
texture-contrast correlation matrix. A mismatched face, missing texture evidence
or wrong dimensions fails. Tied symmetric textures remain visible in the
evidence; inspect the saved real-native/projection sheets before certifying
engine-specific geometry and UV conventions.

Run through an owned development instance with `run_live_check.py`:

```powershell
python tools/verify_shulker_orientations.py shulker-orientations.json --setup-native
python tools/verify_shulker_orientations.py unused.json --self-test
```

`--setup-native` temporarily uses a previously empty inventory slot and twelve
previously empty debug-world cells, restores the slot and removes the fixtures
after capture. The native setup uses `PlayerUseItemToPos` on six support faces,
not NBT direction setters. The server reads NBT only for those debug-created
fixtures; the client exports their actual palettes. NEMC can export an empty
Shulker renderer payload, so the sample explicitly records the missing client
field and the authoritative fixture NBT direction. The tool removes supporting
stones, waits for replication and checks both server and client block readback
before photography. A missing native model invalidates the reference and cannot
be accepted as a proxy failure or pass. It sorts the samples by
that observed direction before comparing blueprint inputs. Native render input
uses the actual client payload plus complete tagged fixture NBT, matching the
ordinary registered-selection capture envelope. These debug helpers do not
create a new production read channel or bypass selection registration.
`--synthetic-only` checks the blueprint editor poses when no native sample is
available; it does not run or certify projection/native agreement. No persistent
draft is saved.

### Static Shulker Render Adapter

`entity_render.py` schema 3 substitutes render-only static meshes for all
17 vanilla colours and six directions. Complete tagged `ShulkerBox.facing`
has priority over a client's `facingDirection`; absent or invalid direction
uses the observed native default, up. Only the render palette changes, and
consumed actor slots are omitted from the SDK input. Documents, clipboard,
sharing and real-world placement retain native identities, states and complete
tagged entity data. The 102 internal identifiers are excluded from the picker
and creative registration.

`tools/data/shulker_static_model_v1.json` keeps the official closed lid/base
geometry, original box UVs and all texture paths, including light gray's native
`silver` texture name. The head is fully enclosed in a closed box and omitted.
`tools/generate_shulker_proxies.py` generates block definitions, models and
terrain aliases; `--check` verifies deterministic output. Face UV expansion is
based on Blockbench's box-UV layout. Models use documented 64x64 texture
descriptions, alpha rendering and individual baked bone rotations.

Pure tests independently check six opening vectors, all rotated cube bounds,
all 17 colour associations, original UV regions, internal identifier exclusion
and unchanged source documents/NBT. Bone angle conventions and native appearance
still require the cold-resource visual check. Adding asset definitions requires
a fresh game load; Python hot refresh alone does not register those blocks.

```powershell
python tools/generate_shulker_proxies.py --check
python -X utf8 -m unittest discover -s tests -p test_static_shulker_render.py
```

### Chest And Sign Adapters

The same schema-3 adapter covers ordinary, trapped and ender chests, plus all
copper and waxed stages. Double-chest face rectangles are packed without
resampling into 64x64 textures, matching the custom block model texture limit.
`tools/data/copper_chest_static_model_v1.json` schema 2 records original geometry,
UVs and source hashes. `tools/generate_copper_chest_proxies.py --check` verifies
checked-in derivatives; regeneration additionally takes `--native-resource-root`.
The complete logical document supplies pairing context even when an occupied
projection cell hides the other half. Editor appearance, world alignment and
initial/dynamic projection occupancy need independent visual evidence.

`VISUAL_CASES['sign_styles']` references `test.entities.signs` and its observed
front/back text styles. Saved tagged NBT supplies both text sides to the native
render adapter. Successful field reconstruction or a visible board does not
establish glyph rendering; `tools/verify_sign_visuals.py` checks coloured glyph
pixels for each measured side and saves both editor and projection evidence.

The schema-3 sign visual case includes a complete text ROI and tolerances for
glyph position and size relative to the wooden panel. The image oracle rejects
identical glyphs that have moved or changed size; a normalized glyph match alone
is insufficient. Native non-glowing back text remains an unaccepted sample until
its independent pixel checks pass.

`tools/verify_pot_visuals.py` uses the public `pot_artwork` case for four native
directions at two camera sides. `--operation mirror_x` or `mirror_z` transforms
the actual blueprint cell, while an independent world-face calculation supplies
the expected native pot direction and artwork. It checks body, texture and
absolute alignment. Editor captures are diagnostic and do not certify world
projection, or vice versa.

Wet sign and pot scenes live in each public fixture's `WET_VISUAL_CASE`: a wet
actor with an independent dry control, adjacent water, and a wet fence. Glass
containment and stone supports are retained in both the native world and the
projection context. The wet harness requires observable native water and actor
pixels separately, then compares the full projection and the dynamic/initial
hidden actor cases. Calibrate the currently owned instance first:

```powershell
python -X utf8 tools/run_live_check.py --session <session.json> --owner <owner> verify_camera_projection.py .runtime/camera.json
python -X utf8 tools/run_live_check.py --session <session.json> --owner <owner> verify_wet_actor_visuals.py .runtime/wet-actors.json --camera-calibration .runtime/camera.json
```

These commands operate only the validated test instance and restore their
temporary world, editor, camera and player state. A failed cleanup or missing
native component prevents acceptance. Preserved captures can be reanalyzed
without launching another game using `--replay <report.json>` with the matching
calibration. Keep the current P0 status in `IMPLEMENTATION_GAPS.md`.
