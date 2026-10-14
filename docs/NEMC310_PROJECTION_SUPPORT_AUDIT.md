# NEMC 3.10 Projection Support Audit

Round-15 final checkpoint (2026-10-14 17:15): biome-bound cauldron surfaces are now enabled only for exact build `3.10.0.420447`. Ten independent near-view cases cover editor/full/missing, six lava levels, water/potion/RGB/snow, animation, occupancy, cutaway and restoration. A default-path cold launch also verifies plain-water plains/swamp/plains changes in all three paths. Plain water uses the document water preset; potion and custom RGB remain independent. The public 33-case cauldron gallery and 14 new dynamic/NBT catalogue pages are available to ordinary players; catalogue coverage is not per-family pixel acceptance.

Custom-water fixed-phase transparency (36 captures), biome colors (three paths), pure-water publication/occupancy and changed-owner world motion have accepted candidate evidence. The latest frozen biome archive exactly matches all 35 current water owners and dedicated resources. Production water remains disabled pending default cold startup, side-UV continuity, cutaway/neighborhood and budget checks. Static patterned world banners are admitted in a limited `model_local` route; the successful banner-only editor depth v6b remains isolated. No claim of waving or generic-actor depth compatibility follows from it. Full UTF-8 repository regression passed 2,719 tests; subsequent focused cauldron and host negative controls also passed. Current status is authoritative over the retained historical checkpoints below.

Round-15 resumed checkpoint (2026-10-14 15:30): fixed-phase, independently named Combine controls confirmed duplicate native water as the transparency regression. With custom alpha zero, the original route still draws blue water; removing native water exposes the fence and rear gold, while custom default .45 blends and alpha1 is opaque. Native draw preparation now suppresses only liquids owned by the injected custom profile; source layers/NBT/targets remain intact and official lava stays enabled. Fresh editor/full/missing acceptance is in progress. Cauldron surfaces are integrated with a versioned measured candidate, separate plain-water/potion/lava/snow resources and a public test blueprint; production default remains disabled pending visual qualification. Static patterned world-banner poses and occupancy have scoped positive results; waving and editor depth remain pending. This supersedes the pause status below, not the retained raw failure reports.

Round-15 afternoon checkpoint (2026-10-14 14:05): the measured native profile now admits single ordinary/copper/ender chests only in world projections and flower pots on the context route. Editor chest proxies remain because native bodies fail shared depth at oblique angles. Final scoped frames 69/71/74/76 were inspected by the root reviewer. Banners and beds remain candidates. Custom-water direction passes all 15 production path/direction combinations, but its transparency is **not accepted**: animated control differences caused the earlier analyzer to pass despite nearly invisible submerged objects. The retained raw `true` is superseded by visual review. Cauldron dedicated geometry/color measurement is in progress and has no integrated three-path acceptance. The user requested a model-switch pause; see the current [handoff](CONVERSATION_HANDOFF.md).

The archived clean comparison originated on independent research branch
`codex/r14-nemc310`, based on `f4b1a00c470c197ee54cd613245fceb7890205dd`
(`dev`). Development has since been authorized on NEMC 3.10 in `dev`, but
the comparison itself does not implement the production migration. Findings
describe installed build `3.10.0.420447`, not every 3.10 release. Current work
and acceptance status are maintained in [IMPLEMENTATION_GAPS.md](IMPLEMENTATION_GAPS.md);
the complete family classification and revised estimate are in
[NEMC310_RENDER_COMPATIBILITY_INVENTORY.md](NEMC310_RENDER_COMPATIBILITY_INVENTORY.md).

## Sources And Actual Installation

- [Official 3.10 changelog](https://mc.163.com/dev/mcmanual/mc-dev/mcdocs/1-ModAPI-beta/%E6%9B%B4%E6%96%B0%E4%BF%A1%E6%81%AF/3.10.html), retrieved 2026-10-13.
- MCP documentation: `api CombineBlockPaletteToGeometry`,
  `api CombineBlockBetweenPosToGeometry`, `api CombineBlockFromPosListToGeometry`,
  `api AddActorBlockGeometry`, `api RenderBlockGeometryModel`, and
  `api SetActorBlockGeometryRotationQuat`.
- Installed executable:
  `D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/Minecraft.Windows.exe`.
  FileVersion and ProductVersion both read `1.21.130.0`; size is 126251024 bytes.
  Native client/server version probes are required after world readiness.
- Other installations include 3.8.0.313229 (`1.21.90.1`), 3.9.0.401155
  (`1.21.120.0`), and PCLauncher_x64 (`1.21.50.0`). None is 3.10 evidence.

The changelog dates the first beta to 2026-09-23, the second beta to 2026-10-14,
stable to 2026-10-28, and player rollout to 2026-10-30. These are published
schedules, not observations of installed future builds. Since 3.9 beta the
OpenGL and RenderDragon packages are combined; OpenGL is the default. The
changelog says the rendering engine should be selected when creating a world
in MCS. This audit must record its actual engine rather than infer it from the
combined executable.

## What The Documentation Changes

All three Combine methods now document support for custom block-entity
appearance, international `minecraft:geometry` block appearance, flower pots,
bells, conduits, banners, copper chests, copper golem statues, water, and fire.
This is a change to existing conversion methods. `AddActorBlockGeometry` and
`RenderBlockGeometryModel` are existing render destinations; calling either
successfully does not prove all source content was drawn.

The newly added `SetActorBlockGeometryRotationQuat(name, (x,y,z,w))` sets an
attached block geometry rotation without Euler gimbal lock. New camera APIs
include `GetWorldRayFromScreenPoint`, `WorldToScreenPoint`, `GetViewMatrix`,
`GetProjectionMatrix`, `GetNearFarPlane`, and `GetAspectRatio`; new atlas APIs
include `GetTextureAtlasUV` and `GetIconInfo`. These are related capabilities,
not automatic proof of pixel-correct projection.

The Combine API notes impose these limits:

1. Custom block-entity render/offset/rotation/scale/multipass depend on client
   runtime. Their converted appearance currently has the default pose without
   animation.
2. Server-produced serialized palette data degrades those custom appearances
   to the default pose. Prefer client `GetBlockPaletteBetweenPos` or
   `GetBlockPaletteFromPosList` serialization when auditing this distinction.
3. Unsupported types still include miniature blocks, barriers, end portals,
   and end gateways. With `unsupportedMode=0` unsupported cells are skipped;
   with `1` generation stops. A nonempty model name can still hide skipped
   cells in the first mode.
4. Geometry names overwrite existing models; every different audit source
   needs an owner/run-specific name. Conversion success, NBT readback, and
   attachment success are structural evidence only.

The changelog explicitly lists water and fire. It does not promise animated
water/lava/fire or complete contents of item frames, containers, and nested
NBT. Those require separate live evidence.

## Clean Demonstration

The final demonstration used two fresh flat worlds, with no editor behavior
or resource pack mounted. `tools/run_nemc_clean_projection_demo.py` generated
the same four-file minimal behavior pack in `.runtime/nemc-clean-39` and
`.runtime/nemc-clean-310`. Their only additional behavior packs were the MCDK
debug pack and managed session probe. Both `world_resource_packs.json` lists
are empty; both Netease resource-pack lists are null. Resolved junction
targets, manifests, UUIDs and file hashes are preserved under
`docs/evidence/nemc-clean-r14`.

The 36-case shared fixture is
`tools/data/nemc_clean_projection_fixture_r14.json`, final SHA256
`381e951a01d141d4948776775d0e2e02c21788a0c88a346e426ecd6f84c3fba9`.
The currently checked-in fixture file has SHA256
`75a1d13561deeca7747a40b40fc6798d150615d7a530f7b894b0cdfb7b5795bf`, so it
does not reproduce that archived clean capture byte-for-byte. Until the two
sources are reconciled, this report's PNGs and raw receipts remain tied to the
archived hash above; the current fixture must not be presented as their input.
Each world resolves semantic block states independently and uses native item
interactions for banners, flower pots, frames and cauldron filling. Sign
front/back text is written through the native typed block-entity interface.
The projected area uses an unmodified client palette, the official
`CombineBlockPaletteToGeometry`, and `AddActorBlockGeometry` on a vanilla
client armor stand. No compatibility models, materials, item sprites, water
proxies, custom shader uniforms, or editor Python modules were used.

| World | Owner | Native Version | Session ID | Game / MCDK PID |
| --- | --- | --- | --- | --- |
| 3.9 | `nemc-clean-39-r14` | `1.21.120.0` | `aa900647f9f942b0a8b478bc18e18f34` | 43152 / 45308 |
| 3.10 | `nemc-clean-310-r14` | `1.21.130.0` | `ca7587fe60f5439680ecacc705b220e0` | 22040 / 48916 |

Both clients reported an empty `modern_projection` module list. The 3.9
server readback also reported an empty list. The 3.10 server content readback
confirmed `1.21.130.0`, but its server module-list observation was not captured
before the user closed the game; this gap is not silently inferred away.
The actual mounted 3.10 behavior-pack files contain no editor package.

No activation, resizing, restoration, desktop input or fallback capture was
performed. Process-local `MCDEV_ALLOW_USER_FOREGROUND=1` let the user select
the protected games manually. Both final `free/result.json` receipts report
movement and jump enabled, movement lock released, first-person selected,
and pitch/yaw locks false. Both creative-mode calls succeeded.

The first 3.10 screenshot, `310/overview.png`, is a preserved **obstructed
capture**: the pause menu covers most of the scene. It is not a pixel pass or
evidence that geometry is missing. The 3.9 original `39/overview.png` is
unobstructed and was inspected; both areas are visible. No broad rendering
comparison or animation score was completed or claimed.

The first attempt at flowing water disappeared under native liquid updates.
The final fixture places a contained native source above a falling-water
cell; 3.10 repair and 3.9 final readback report `liquid_depth=8`. JSON-derived
banner pattern strings were converted to the byte strings required by the
native item interface. Both versions then read back real `Patterns` entries
`bs`/Color 1 and `ts`/Color 14. The 3.10 mesh was rebuilt from the corrected
client palette, after destroying its old owned client actor.

The user confirmed that observation was complete and manually closed both
games. `independent-exit.json` and each archive index independently record
null current identities for the exact game and MCDK PIDs. There was no agent
stop, relaunch, branch merge, or push.

## Native Boundary

`310/project-refreshed/result.json` preserves the actual client palette.
Its actor records establish the following structural capabilities; they do
not establish complete pixel or animation behavior.

`NATIVE` below is a route/field capability label. Documentation, actual
typed NBT and palette fields, inspected clean Combine pixels, and acceptance
of editor/full/missing projection are four separate evidence levels.
An attachment success or a nonempty generated model name does not advance
the latter two levels. A missing projected stone positive control makes
the capture fixture invalid; it cannot establish that the target family is
unsupported.

| Family | 3.10 native status | Observed 3.10 Actor Fields | Migration Boundary |
| --- | --- | --- |
| Standing / wall banners | `NATIVE` | Base, Type, direction, pattern count, bs/ts pattern/color fields | Preserve native actor data; do not replace supported appearance with a 3.9 proxy. Waving is not qualified. |
| Standing / wall / hanging signs | `NATIVE` | Two-sided real text, color, glow, geometry/pose fields | Native text/style data is present. Preserve unknown fields and native pose rather than reseeding a 3.9 template. |
| Flower pots | `NATIVE` | Empty actor or `flowerPotPlant=minecraft:poppy` | Official planted appearance data is present. Decorated-pot sherds are a separate family and were not exercised here. |
| Copper chests | `NATIVE` | Copper type, pair flags, direction, openness | Native shell/pair appearance is available; inventory contents remain typed NBT, and live opening is not established. |
| Copper golem statues | `NATIVE` | Copper type, waxed flag, pose, direction | Native static appearance data is present. |
| Ordinary chest | `NATIVE-PARTIAL` | Pair flags, direction, openness | Native renderer fields are present; preserve actual fields and qualify pose before retiring other adapters. |
| Frame: empty / normal / enchanted sword | `NATIVE-PARTIAL` | All three actor entries are empty dictionaries | Real Item and enchant NBT exists on the source, but the serializer lacks displayed-item fields. Keep item-content fallback. Shelf was not exercised. |
| Purple shulker box | `NATIVE-PARTIAL` | Empty dictionary | Color follows block name; this capture does not establish NBT-facing or opening support. Keep unqualified pose fallback. |
| Bell | `NATIVE` | Bell attachment/direction | Official support is documented; dynamic movement still needs qualification. |
| Conduit | `NATIVE-PARTIAL` | Empty conduit record | Official support is documented and the family is on the native route, but active-state model, rotation and animation are not qualified. |
| Water / falling water / wet fence | `CUSTOM` | Native primary/extra water and depths | The user requires custom world water despite official conversion support. Remove its contribution from the official route to avoid duplicate geometry. |
| World lava / flowing lava | `NATIVE-PARTIAL` | Native lava cells | The user permits the official world-lava route; level, flow direction, slow animation and all product paths require qualification. |
| Cauldron contents | `CUSTOM` | Native cauldron shell and fill state | Preserve the shell and typed NBT; use a bounded project surface for water, lava, powder snow, potions and custom colors. World-lava permission does not apply to the cauldron. |
| Fire | `NATIVE-PARTIAL` | Native fire cell | Official support is documented and accepted as a migration route by the user; full dynamic behavior still needs targeted validation. |
| `portal` | `NATIVE-PARTIAL` | Not included in this clean actor sample | Ordinary Nether portal may use the native transparent/flipbook route, but axis, depth and animation still require a dedicated sample. |
| `end_portal` / `end_gateway` | `CUSTOM` | Combine documentation explicitly excludes both types | Implement dedicated dynamic surface/beam geometry; no claim of native Combine support and no portal behavior simulation. |

The official custom-block-entity limitation is explicit: conversion currently
uses a default pose without animation. This does not establish that every
vanilla texture, actor or shader is static. Banner waving, fire texture
animation, chest/shulker opening, bell swinging, conduit effects, enchanted
item glint, and all unexercised NBT types remain distinct qualification work.
There is no general claim that all NBT is displayable by Combine.

## Round 15 Evidence Reconciliation

[`nemc-nbt-r15/runtime-family-results.json`](evidence/nemc-nbt-r15/runtime-family-results.json)
reanalyzes the archived round 14 receipts; it is not a new 57-family live run.
Its 28 work groups now index all 57 captured NBT root IDs, including groups
with no sample. The supplemental `repair/result.json` is part of the input:
real banners contain `bs/Color 1` followed by `ts/Color 14`, and the rebuilt
client palette contains the corresponding pattern fields. The initial
missing-pattern observation must not override this later readback. The
archived 3.10 overview remains obscured and adds no family pixel passes.

The separate [round 15 cauldron audit](evidence/cauldron-runtime-r15/README.md)
contains 60 native interactions and all water/lava/powder-snow
`fill_level=0..6` states. Item aux `0` is a water bottle: it fills levels
`2/4/6` with `PotionId=-1`; aux `1..4` leaves the cauldron empty; aux
`5..46` reads back the requested potion ID. Two typed `CustomColor` integers
also read back exactly. These establish data and storage boundaries;
channel interpretation, actual color, inset surface height and production
overlay pixels remain unqualified.

The old dynamic gallery covers only 33 of the 37 ordinary resource-animation
names. It omits all four world-water/lava names and all 12 NBT animation
names; its four additional special samples do not fill these omissions.
Identical editor/projection image bytes and insufficient block scale leave
`pixel_acceptance=false`. It cannot support a blanket conclusion that every
vanilla animation is either working or frozen. New close captures must have
an inspected projected-stone positive control and a fixed camera before
target differences are interpreted.

### Inspected Close Captures At 11:25, 2026-10-14

The main session inspected the new PNGs under
[`r15-solo-runtime`](evidence/r15-solo-runtime/). In the separate `fire-v2`
and `lantern-v3` captures the real-world samples and clean Combine models
are both visible. The fire group changes between frames while the static
stone control remains unchanged; the lantern group establishes body
visibility. These are limited clean-route observations, not product
editor/full/missing acceptance.

The subsequent `batch-v2` uses origin `(0,-58,0)` with a projected-stone
positive control. Inspected projection images show red front text on the
standing/wall signs and green back text on the oak hanging sign; ordinary,
copper and ender chest shells; a purple shulker and bed; a poppy in its pot
and a decorated-pot shell; enchanting-table, beacon and inactive-conduit
bodies; a purple Nether portal surface; ordinary/glow frame bodies; lectern
and chiseled-bookshelf bodies; bell, copper statue, piston and sticky-piston
bodies. The observations are limited to the displayed samples and do not
qualify all variants, contents, pose, animation or product routes.

The same inspected images do not show a book, beacon beam, displayed sword,
shelf, head samples, moving block or the two End portal types. Those
absences are **not new unsupported-family findings**: from the signs group
onward the real-world reference row is also blank despite valid state
readbacks, leaving client synchronization/display unsettled. The banner
sample exposes this mismatch directly: its raw NBT has `Base=4` and two
patterns, while the captured palette has `Base=0` and zero patterns. That
fixture cannot negate the earlier repaired banner-palette evidence.
The End portal types remain on the custom route because of the official
API exclusion, independently of these unsettled captures.

The `plants` group failed projected-stone visibility and stopped the batch.
Its capture is invalid for capability decisions. Other generated reports
that have not been inspected are not promoted to pixel observations, and
all batch reports retain `pixel_acceptance=false`. Before interpreting
missing content, restore the visible world reference and match the actual
client palette to the intended typed NBT/state sample. The Chinese
[inventory's close-capture table](NEMC310_RENDER_COMPATIBILITY_INVENTORY.md#1125新增近景观察与夹具限制)
records the per-group boundaries.

Subsequent inspection adds all eight copper-lantern bodies, the prismarine
shapes, sculk and sensor bodies. Their temporal crops have not yet been
inspected; numerical differences alone do not qualify their animation.
A vanilla `/setblock dirt` at the missing-world-control ROI immediately
became visible. The fixture's `SetBlockNew(updateNeighbors=False)` is now
a synchronization hypothesis under test, not an established renderer
failure. Negative qualification remains blocked until the actual fixture
source snapshot and client NBT/palette agree.

At 11:50 the main session inspected
[`banners-v4/rois.png`](evidence/r15-solo-runtime/banners-v4/rois.png).
Genuine `PlayerUseItemToPos` placement with item `userData` produced a
client palette matching `Base=4` and two real patterns, `bs/Color 1` then
`ts/Color 14`. Standing and wall banner projections visibly show those
colored patterns. The earlier direct raw-NBT write had not refreshed the
palette appearance. This is new round 15 evidence for those two projected
pattern samples, separate from the archived round 14 fields.
All three inspected temporal samples have `changed_gt12=0`; no waving was
seen in this short sample, and no general animation claim follows.
The real-world stone is visible after enabling neighbor updates, but the
real-world banners remain absent. World-reference and product-path
qualification are therefore still open. Further `batch-v3` captures are
not accepted before inspection.

### Independent 3.10 Clock Measurement

The textureless `TOTAL_REAL_WORLD_TIME` diagnostic
[`clock310-v2.json`](evidence/water-clock-nemc310-r15-v1/clock310-v2.json) measured
`clock_direction=+1` over 13 valid frames with 11 changing intervals. Its
red-channel rate is 31.596 units/second against an expected 31.875, while
the support area remains exactly 12,584 pixels. Completion, full temporal
capture, restoration and unchanged source checks passed;
`product_acceptance_claimed=false`. The durable archive preserves the original bytes, 13 frames and diagnostic
sources; its [relative artifact index](evidence/water-clock-nemc310-r15-v1/artifact-index.json)
records hashes and byte lengths.
This constrains the clock used by that diagnostic shader, not water UV
orientation or texture-frame order. The earlier 3.9 `-1` clock observation
must not be used to prescribe a 3.10 direction fix.

## Migration Scope

After observing the clean worlds, the user authorized development on NEMC
3.10, accepting official NBT, fire and world-lava appearance where supported
while retaining custom world water and cauldron contents. Dump, rotation and mirror are
explicitly deferred. The existing 3.9 registry is not evidence for 3.10 and
must not be relabeled as a regenerated 3.10 dump.

The runtime adapters currently needing selective policy are
`geometry_palette.prepare_palette`, `entity_render.prepare_static_entities`,
`entity_render.native_actor`, and `render_context._native_actor_mesh`.
The latter originally recognizes only sign and decorated-pot actors; newly
supported native actor meshes must use the model-local overlay path rather
than the packed 27-neighbor coordinate decoder. `visible_actor.compose_actor`
already preserves typed NBT separately from native renderer fields and should
continue to do so. Unknown NBT and unknown renderer fields must survive.

The new `native_render_profile` candidate is wired through palette
preparation, actor coordinate routing, the editor/full/missing paths and
cache identity. It explicitly permits validated payloads for ordinary,
copper and ender single chests, beds and flower pots. The caller must choose
`model_local` or `context` from live evidence; paired chests, empty shulker
actors, heads and stale banner payloads are outside this initial set.
The 168 relevant offline tests pass, but `Session.native_render_profile`
still defaults to `None` and no production native route is automatically
enabled by a version string. Live route selection and product qualification
remain pending. Existing fallback and unknown fields survive, and body
ownership remains separate from item/liquid overlays. The item sprite
resource still covers `diamond_sword` only; its animated-glint diagnostic
is not evidence for a general displayed-item renderer.

The candidate now has a separate 3.10 product run under
[`native-render-profile-r15`](evidence/native-render-profile-r15/).
The specialist inspected the full `model_local` and restored-missing images:
the three single chests, bed and poppy pot align. The occupied image hides
bodies at the occupied positions, while the remaining bed-head half still
needs review. The `context` comparison shows misplaced/duplicated single
chests and a misplaced bed; the pot remains aligned. The oblique editor
image exposes bodies incorrectly occluded by their supports, so shared-depth
integration is still under repair. These observations distinguish a working
world candidate from its failed controls and unfinished editor path;
production qualification is incomplete and the default remains disabled.
