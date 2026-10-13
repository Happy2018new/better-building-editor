# NEMC 3.10 Projection Support Audit

Independent research branch: `codex/r14-nemc310`, based on
`f4b1a00c470c197ee54cd613245fceb7890205dd` (`dev`). This audit does not add 3.10
support to the shipping 3.9 runtime. Findings describe the observed beta build,
not all future 3.10 releases.

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

| Family | Observed 3.10 Actor Fields | Migration Boundary |
| --- | --- | --- |
| Standing / wall banners | Base, Type, direction, pattern count, bs/ts pattern/color fields | Preserve native actor data; do not replace supported appearance with a 3.9 proxy. Waving is not qualified. |
| Standing / wall / hanging signs | Two-sided real text, color, glow, geometry/pose fields | Native text/style data is present. Preserve unknown fields and native pose rather than reseeding a 3.9 template. |
| Flower pots | Empty actor or `flowerPotPlant=minecraft:poppy` | Official planted appearance data is present. Decorated-pot sherds are a separate family and were not exercised here. |
| Copper chests | Copper type, pair flags, direction, openness | Native shell/pair appearance is available; inventory contents remain typed NBT, and live opening is not established. |
| Copper golem statues | Copper type, waxed flag, pose, direction | Native static appearance data is present. |
| Ordinary chest | Pair flags, direction, openness | Native renderer fields are present; preserve actual fields and qualify pose before retiring other adapters. |
| Frame: empty / normal / enchanted sword | All three actor entries are empty dictionaries | Real Item and enchant NBT exists on the source, but the serializer lacks displayed-item fields. Keep item-content fallback. Shelf was not exercised. |
| Purple shulker box | Empty dictionary | Color follows block name; this capture does not establish NBT-facing or opening support. Keep unqualified pose fallback. |
| Bell / conduit | Bell attachment/direction; empty conduit record | Official support is documented. Dynamic movement and active-state visuals are not qualified. |
| Water / falling water / lava / wet fence / cauldron | Native primary/extra water, depths and cauldron fill state | The user requires custom fluid adaptation despite official conversion support. Remove fluid contribution from the official route to avoid duplicate rendering. |
| Fire | Native fire cell | Official support is documented and accepted as a migration route by the user; full dynamic behavior still needs targeted validation. |

The official custom-block-entity limitation is explicit: conversion currently
uses a default pose without animation. This does not establish that every
vanilla texture, actor or shader is static. Banner waving, fire texture
animation, chest/shulker opening, bell swinging, conduit effects, enchanted
item glint, and all unexercised NBT types remain distinct qualification work.
There is no general claim that all NBT is displayable by Combine.

## Migration Scope

After observing the clean worlds, the user authorized development on NEMC
3.10, accepting official NBT and fire appearance where supported while
retaining custom water/lava/cauldron adaptation. Dump, rotation and mirror are
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
