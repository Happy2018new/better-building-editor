# Private Item Sprite Integration, Round 14

Status: candidate implementation, production disabled until actual editor and
world projection pixels are accepted. This does not establish support for all
vanilla item families or shelf contents.

## Scope and Ownership

The native private actor can display a bound sword in the world but its
RenderEntity PaperDoll is blank. A server-created actor has visible UI contents,
but privacy, world calibration and restoration remain unaccepted. This
implementation therefore creates no new server actor or item/inventory RPC.

`item_sprite_plan` reads immutable typed frame NBT, accepts only the already
versioned diamond sword icon and its observed enchantment tag, and encodes four
items per private skeleton mesh. `item_sprite_preview` owns revision snapshots;
`item_sprite_render` owns only SDK model lifetimes; `item_sprite_projection`
selects target/occupancy masks without changing stored NBT. The model/material
generator owns versioned resources and the acceptance fingerprint.

Items use independent UI and world shaders, while the minimal optional
validator/renderer/plan parameters of the existing liquid lifecycle retain
water defaults. `ProjectionCompanions` publishes item and water owners with one
occupancy transaction. Rejected or superseded requests cannot publish a partial
pair. Failed destruction remains owned and retryable. Body and moving highlight
are one payload and are removed together by layer, cutaway and missing masks.

Maps, block items, unknown sprites and arbitrary visual userData remain
unrendered and unchanged. Existing native/3D paths stay available. The fallback
is a purple analytic moving highlight within an extruded source bitmap, not an
exact copy of the vanilla glint texture/material.

## Compatibility

The source profile checks game build, block palette SHA-256 and payload version.
The resource contract hashes the owned mesh, source PNG, UI/world shaders,
registry and material entries. Production deployment requires both accepted
visible evidence and a matching resource hash. Updating a game build requires
regenerating observed item resources and repeating the bounded acceptance
matrix, not editing each frame orientation by hand.

## Verification

- 14 pure item plan/resource/lifecycle tests cover all 48 facing/rotation poses,
  enchanted and ordinary payloads, valid zero codes, unknown/malformed visual
  data, target boundaries, batching limits and UI/world tags.
- Companion tests cover joint hidden staging, publication failure restoration,
  superseded occupancy, cleanup retries, rejected provider requests, deferred
  biome rescheduling and closed/finalized candidate rejection.
- Existing liquid render/projection/viewport/preview, occupancy and bridge
  suites passed before integration; the optional defaults preserve those paths.
- `generate_item_sprite_resources.py --check` and `git diff --check` pass.
- Native editor/shared-depth/cutaway and full/missing world pixels are pending.
  `test.entities.item_contents` is the public built-in fixture association. Its
  native ordinary/enchanted/empty frames are the baseline, not synthetic item
  tag guesses. Shelf filled-slot NBT is unobserved; default Shelf NBT is not a
  filled-slot schema.

## Next Acceptance

Use one owner-bound background instance with the approved noactivation guard
and native WGC capture. Inspect ordinary body scale/pose against a source
oracle, moving highlight inside the same silhouette, blank empty controls,
depth occlusion, cutaway, removal/replacement and full/missing projection
separately. Unreliable background capture remains an explicit pending result;
no foreground, resize or desktop-input fallback is authorized for this task.
