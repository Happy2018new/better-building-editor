"""Build a deterministic offline inventory of native block-entity appearance data.

This audit deliberately uses only checked-in JSON/evidence and the installed 3.10
resource pack.  It does not import the projection runtime, call ModSDK, or start
Minecraft.  The output keeps source hashes and explicit coverage boundaries so a
resource existing on disk is never confused with a runtime support claim.
"""

from __future__ import print_function

import argparse
import ast
import fnmatch
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "tools/data/native_nbt_inventory_nemc_3.10.0.420447.json"
RESOURCE_ROOT = Path(
    "D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data/resource_packs"
)

DEFAULTS = ROOT / "tools/data/native_block_entity_defaults_nemc_3.9.0.401155.json"
REGISTRY = ROOT / "docs/reference/block_palettes/nemc_3.9.0.401155.json"
REGISTRY_MANIFEST = ROOT / "tools/data/block_registry_manifest.json"
RENDERERS = ROOT / "tools/data/native_entity_renderers_nemc_3.9.0.401155.json"
APPEARANCES = ROOT / "tools/data/native_entity_appearances_nemc_3.9.0.401155.json"
PALETTE_ACTORS = ROOT / "tools/data/native_palette_actors_nemc_3.9.0.401155.json"
WATER_OVERLAYS = ROOT / "tools/data/native_water_overlays_nemc_3.9.0.401155.json"
ITEM_CONTENTS = ROOT / "tools/data/native_item_contents_nemc_3.9.0.401155.json"
POT_SHERDS = ROOT / "tools/data/native_pot_sherds_nemc_3.9.0.401155.json"
BED_CAPTURE = ROOT / "tools/data/native_bed_capture_nemc_3.9.0.401155.json"
CLEAN_310 = ROOT / "docs/evidence/nemc-clean-r14/310/project-refreshed/result.json"
CLEAN_310_CONTENT = ROOT / "docs/evidence/nemc-clean-r14/310/content/result.json"
CLEAN_310_REPAIR = ROOT / "docs/evidence/nemc-clean-r14/310/repair/result.json"


def read_json(path):
    text = path.read_text(encoding="utf-8-sig")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # A few installed Netease resource files are JSON-with-comments/trailing
        # commas.  Keep the source hash exact while accepting that asset syntax.
        import json5
        return json5.loads(text)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_record(path, data=None, **extra):
    result = {"path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix(),
              "sha256": sha256(path)}
    result.update(extra)
    return result


def scalar(value):
    if isinstance(value, dict) and "__value__" in value:
        return value["__value__"]
    return value


def typed_fields(nbt):
    fields = {}
    for key, value in sorted(nbt.items()):
        if key in ("id", "x", "y", "z", "isMovable"):
            continue
        if isinstance(value, dict) and "__type__" in value:
            fields[key] = {"sdk_tag": value["__type__"], "value": scalar(value)}
        elif isinstance(value, dict):
            fields[key] = {"nested": typed_fields(value)}
        elif isinstance(value, list):
            fields[key] = {"list_length": len(value)}
        else:
            fields[key] = {"python_type": type(value).__name__}
    return fields


def classify(entity_id):
    if entity_id in ("MobSpawner", "TrialSpawner"):
        return "configured_creature_presence_marker"
    if entity_id == "MovingBlock":
        return "excluded_moving_block"
    if entity_id == "PistonArm":
        return "transient_piston_animation"
    if entity_id in ("EndPortal", "EndGateway"):
        return "portal_gateway_unsupported_by_combine"
    if entity_id in ("Sign", "HangingSign"):
        return "visible_text_color_and_pose"
    if entity_id == "Banner":
        return "visible_pattern_color_and_pose"
    if entity_id in ("ItemFrame", "GlowItemFrame"):
        return "visible_item_content_and_pose"
    if entity_id in ("FlowerPot", "DecoratedPot"):
        return "visible_plant_or_sherd_content"
    if entity_id == "Skull":
        return "visible_skull_type_and_pose"
    if entity_id == "Bed":
        return "visible_color_and_paired_geometry"
    if entity_id in ("Shelf", "ChiseledBookshelf"):
        return "visible_items" if entity_id == "Shelf" else "state_driven_slot_occupancy"
    if entity_id in ("Chest", "Barrel", "ShulkerBox", "Furnace", "BlastFurnace",
                     "Smoker", "BrewingStand", "Dispenser", "Dropper", "Hopper",
                     "Crafter", "EnderChest"):
        return "container_static_shell_open_state_only"
    if entity_id == "Beacon":
        return "native_static_or_state_only"
    if entity_id == "Conduit":
        return "native_static_or_state_only"
    if entity_id == "EnchantTable":
        return "visible_idle_book_animation"
    if entity_id == "Bell":
        return "visible_model_animation"
    if entity_id == "Campfire":
        return "visible_cooking_items_and_animated_texture"
    if entity_id in ("SculkSensor", "CalibratedSculkSensor", "SculkCatalyst",
                     "SculkShrieker", "CreakingHeart"):
        return "state_driven_animated_texture"
    if entity_id in ("Cauldron",):
        return "visible_liquid_custom_route"
    if entity_id == "Vault":
        return "state_driven_animated_texture"
    if entity_id in ("CopperGolemStatue",):
        return "visible_copper_variant_and_pose"
    if entity_id == "Lectern":
        return "visible_book_and_model_pose"
    if entity_id in ("CommandBlock", "JigsawBlock", "StructureBlock"):
        return "editor_metadata_or_overlay_not_mesh_content"
    if entity_id in ("ChemistryTable",):
        return "excluded_education_content"
    if entity_id in ("BrushableBlock",):
        return "transient_brushing_and_hidden_loot"
    if entity_id in ("NetherReactor",):
        return "legacy_education_state"
    return "native_static_or_state_only"


# Each note distinguishes visible surface content from hidden gameplay inventory.
APPEARANCE_NOTES = {
    "Banner": "Base, Type and nondefault Patterns alter the visible textile; native pose fields do not qualify waving animation.",
    "Barrel": "Contents are hidden. Facing and open_bit select the shell appearance; do not draw stored Items.",
    "Beacon": "Keep the native static shell. Activated beam and particles are excluded by the current user scope; primary/secondary and inventory remain preserved data.",
    "Bed": "color alters the paired bed textile; direction/head_piece_bit/occupied_bit live in states. Two-cell reconstruction and boundary context matter.",
    "Beehive": "Stored bees and spawn timers are hidden. Facing/honey_level select the block surface. Bees leaving the hive are entity gameplay, not NBT mesh content.",
    "Bell": "Direction and attachment select the static bell; Ringing/Ticks are a transient swing. Resonance particles are excluded.",
    "BlastFurnace": "Items and timers are hidden. Lit/unlit block/state selects the visible face; no inventory item overlay.",
    "BrewingStand": "Three bottle silhouettes are controlled by brewing_stand_slot_a/b/c_bit. Fuel and ingredient inventory remain hidden; do not render every stored ItemDict.",
    "BrushableBlock": "brushed_progress changes the surface. A partially revealed archaeological item is transient content; LootTable is hidden until resolved. Filled-item NBT and pose require a nondefault capture.",
    "CalibratedSculkSensor": "sculk_sensor_phase selects visible tendril texture state; VibrationListener is gameplay metadata. Vibration particles are excluded.",
    "Campfire": "extinguished controls visible fire texture. Up to four cooking items are surface content, although empty default NBT only exposes ItemTime1..4. Smoke/sparks are excluded.",
    "Cauldron": "cauldron_liquid/fill_level and PotionId/PotionType alter the visible fill. All cauldron liquid, including lava, keeps the custom route; stored Items are not a general item overlay.",
    "ChemistryTable": "Education block appearance is excluded by user scope. Preserve inventory/default evidence as reference, without treating it as an adaptation target.",
    "Chest": "Items are hidden. Single/double pairing, direction, copper oxidation and lid openness alter the exterior. Native clean capture contains chest actor fields, not a lid-animation qualification.",
    "ChiseledBookshelf": "books_stored (0..63) selects six occupied-slot texture bits. Stored books need not become separate item meshes; native state reconstruction is the primary route.",
    "CommandBlock": "Command/output/timing metadata is not a permanent mesh overlay. Type and conditional/direction states choose the shell.",
    "Conduit": "Only the inactive static native body is in scope. Activated core, frame, wind, rotation and persistent effects are excluded; Target remains preserved gameplay data.",
    "CopperGolemStatue": "Eight oxidation/wax names plus Pose and cardinal direction choose the visible statue. The default clean capture does not cover all poses or transition behavior.",
    "Crafter": "Inventory and disabled_slots are hidden/GUI content. orientation/crafting/triggered_bit select visible block state; no general stored-item overlay.",
    "CraftingTable": "Native NBT identity is observed, but its empty default adds no exterior content; static block acceptance only.",
    "CreakingHeart": "creaking_heart_state/natural/axis select visible surface state. Cooldown is gameplay metadata; connection particles and the creaking entity are excluded.",
    "DaylightDetector": "Signal metadata is not visible content; inverted name and states select the block surface.",
    "DecoratedPot": "Nondefault sherds select four visible face patterns. Stored item is hidden inside the pot; animation is a transient wobble. Do not display the whole inventory.",
    "Dispenser": "Items are hidden; facing and triggered state choose the exterior. No inventory item overlay.",
    "Dropper": "Items are hidden; facing and triggered state choose the exterior. No inventory item overlay.",
    "EnchantTable": "Implement the always-present idle hovering book and its motion. Player proximity opening/page reactions and particles are excluded; rott alone is not a complete animation state.",
    "EndGateway": "Official Combine docs exclude this type. Portal surface and gateway beam geometry need a separate route; Age/ExitPortal are not ordinary item content.",
    "EndPortal": "Official Combine docs exclude this type. The animated portal surface needs a separate route; no default visible NBT inventory.",
    "EnderChest": "Contents are hidden and player-specific. Exterior lid openness is visible; purple particles are excluded.",
    "FlowerPot": "Nondefault PlantBlock selects a visible plant; default empty NBT cannot describe filled-pot capability. 3.10 clean client actor exposes flowerPotPlant for a poppy.",
    "Furnace": "Items and burn/cook timers are hidden; lit/unlit face is selected by native state/name. No inventory item overlay.",
    "GlowItemFrame": "Nondefault Item/ItemRotation/ItemDropChance are surface content. Native empty default actor does not prove filled-item rendering. Item atlas/model/map/glint needs separate qualification.",
    "HangingSign": "FrontText/BackText contain visible text, color, glow and formatting. Hanging/attached pose is state/runtime context; full text and all wood variants need qualification.",
    "Hopper": "Stored Items and TransferCooldown are hidden. Native exterior and facing use the static route.",
    "ItemFrame": "Nondefault Item/ItemRotation/ItemDropChance are surface content. Clean 3.10 real item+enchantment NBT exists while the raw frame actor remains empty; no visual filled-item pass is claimed.",
    "JigsawBlock": "Pools/priorities/final_state configure generation, not exterior content. Orientation state selects the shell.",
    "Jukebox": "A stored disc is internal content; playback gameplay and note particles are excluded. Default block shell has no extra visible NBT content.",
    "Lectern": "A nondefault Book is visible as a book on the stand; page/open pose may matter. Empty default NBT does not establish book reconstruction or animation support.",
    "Lodestone": "Binding metadata does not add an exterior mesh; static block acceptance only.",
    "MobSpawner": "Preserve the native cage and show present/empty/unknown configuration badges from exact-version EntityIdentifier data. Internal creature models and particles are excluded; partial NBT must never mean empty.",
    "MovingBlock": "Appearance adaptation is excluded by user scope. Preserve movingBlock/movingBlockExtra and all transient metadata as data; do not claim an exterior qualification.",
    "Music": "note is audible gameplay metadata. Note particles are excluded; no extra exterior item or text layer.",
    "NetherReactor": "Legacy Progress/IsInitialized/HasFinished behavior has no verified additional exterior pose. Keep a static baseline and classify legacy activation as unknown.",
    "PistonArm": "Progress/LastProgress/State/NewState animate a moving arm; AttachedBlocks/BreakBlocks affect transient context. Closed default geometry is distinct from movement support.",
    "Comparator": "OutputSignal is gameplay data. powered/unpowered names and output bits select the visible shell; no extra NBT inventory overlay.",
    "SculkCatalyst": "bloom selects visible animated surface texture. Bloom particles are excluded.",
    "SculkSensor": "sculk_sensor_phase selects visible animated tendril texture. VibrationListener is gameplay data; vibration particles are excluded.",
    "SculkShrieker": "active/can_summon select animated visible surface state. VibrationListener is gameplay data; shriek/warden particles and entities are excluded.",
    "Shelf": "A shelf shows actual slot items. Native empty default has no Item field and no actor data; a plan exists but no successful nondefault content capture is present. Three-slot mapping, direction and item/glint rendering remain unknown.",
    "ShulkerBox": "Items are hidden; color, stored facing and animated lid are visible. Default actor fields may exist in 3.9 while 3.10 clean purple-shulker actor is empty; dynamic lid support is unqualified.",
    "Sign": "FrontText/BackText contain visible text, color, glow and formatting. Standing/wall direction is state/runtime context; all woods and text variants still need qualification.",
    "Skull": "Named skull type, Rotation and optional DoingAnimation/MouthTickCount alter visible model pose. Player custom skin ownership fields are not observed in the empty defaults. Powered dragon/piglin motion is unqualified.",
    "Smoker": "Items and timers are hidden. Lit/unlit shell is a state/name variant; no inventory item overlay.",
    "SporeBlossom": "With particles excluded, the static blossom has no observed visible NBT content or separate adaptation target.",
    "StructureBlock": "showBoundingBox/offset/size configure an editor visualization; structure metadata is not block mesh content. A structure bounding box is a separate editor feature.",
    "TrialSpawner": "Native states choose the shell; show a present/empty/unknown configuration badge from observed spawn_data and selected normal/ominous configuration. current_mobs is not configuration. Internal creature models and particles are excluded.",
    "Vault": "Native vault_state/ominous choose the shell. Internal display-item effects and particles are excluded by user scope; visible shell/state qualification remains separate.",
}


DIFFICULTY = {
    "native_static_or_state_only": (0, "native_static_acceptance", [0.25, 0.5]),
    "education_static_block_content": (0, "native_static_acceptance", [0.25, 0.5]),
    "legacy_education_state": (0, "native_static_acceptance", [0.25, 0.5]),
    "editor_metadata_or_overlay_not_mesh_content": (0, "native_static_acceptance", [0.25, 0.5]),
    "excluded_moving_block": (0, "excluded_by_user_scope", [0.0, 0.0]),
    "excluded_education_content": (0, "excluded_by_user_scope", [0.0, 0.0]),
    "configured_creature_presence_marker": (2, "shared_configuration_marker", [0.25, 0.75]),
    "visible_idle_book_animation": (4, "shared_book_idle_pose", [1.0, 2.5]),
    "container_static_shell_open_state_only": (1, "native_state_and_optional_lid", [0.5, 1.5]),
    "state_driven_slot_occupancy": (1, "native_state_acceptance", [0.25, 0.75]),
    "state_driven_animated_texture": (1, "native_state_texture_acceptance", [0.5, 1.0]),
    "visible_copper_variant_and_pose": (2, "native_actor_nbt_pose", [0.5, 1.5]),
    "visible_color_and_paired_geometry": (2, "paired_nbt_geometry", [0.75, 2.0]),
    "visible_skull_type_and_pose": (2, "native_actor_nbt_pose", [1.0, 2.5]),
    "visible_text_color_and_pose": (2, "native_actor_nbt_content", [0.5, 1.5]),
    "visible_pattern_color_and_pose": (2, "native_actor_nbt_content", [0.5, 1.5]),
    "visible_plant_or_sherd_content": (2, "native_actor_nbt_content", [0.5, 1.5]),
    "visible_liquid_custom_route": (3, "custom_liquid_surface", [1.0, 3.0]),
    "visible_item_content_and_pose": (3, "shared_item_renderer", [2.0, 5.0]),
    "visible_items": (3, "shared_item_renderer_and_slot_mapping", [1.5, 4.0]),
    "visible_cooking_items_and_animated_texture": (3, "shared_item_renderer_and_slot_mapping", [1.0, 3.0]),
    "visible_book_and_model_pose": (4, "custom_book_pose", [1.5, 4.0]),
    "visible_model_animation": (4, "model_animation", [2.0, 5.0]),
    "visible_beam_geometry": (4, "world_context_beam_geometry", [2.0, 4.0]),
    "visible_state_effect_and_animation": (4, "special_display_or_model_animation", [2.0, 5.0]),
    "transient_brushing_and_hidden_loot": (4, "transient_item_pose", [1.5, 4.0]),
    "portal_gateway_unsupported_by_combine": (5, "custom_surface_material_or_beam", [3.0, 7.0]),
    "transient_piston_animation": (5, "transient_nested_geometry", [3.0, 6.0]),
    "transient_moving_nested_block": (5, "transient_nested_geometry", [4.0, 8.0]),
}


def registry_inventory(registry):
    names = defaultdict(list)
    for row in registry["blocks"]:
        names[row["name"]].append(row)
    return names


def state_summary(rows):
    values = defaultdict(set)
    for row in rows:
        for state in row.get("states", []):
            values[state["name"]].add(state["value"])
    return {
        "state_count": len(rows),
        "state_values": {key: sorted(entries, key=lambda item: (str(type(item)), item))
                         for key, entries in sorted(values.items())},
    }


def clean_actor_observations(path):
    if not path.exists():
        return {"available": False, "reason": "clean 3.10 evidence missing"}
    source = read_json(path)
    actors = source.get("result", {}).get("source", {}).get("actor", {})
    result = {}
    for name, variants in sorted(actors.items()):
        fields = set()
        variant_ids = []
        for variant, actor in sorted(variants.items(), key=lambda item: item[0]):
            variant_ids.append(variant)
            if isinstance(actor, dict):
                fields.update(actor.keys())
        result[name] = {"variant_ids": variant_ids, "actor_fields": sorted(fields),
                        "actors": variants}
    common = source["result"]["source"].get("common", {})
    observed_materials = []
    for key, indices in common.items():
        name, aux = ast.literal_eval(key)
        if name != "minecraft:air":
            observed_materials.append({"name": name, "aux": aux, "cell_count": len(indices)})
    return {
        "available": True,
        "source": path.relative_to(ROOT).as_posix(),
        "sha256": sha256(path),
        "names": result,
        "observed_materials": sorted(observed_materials, key=lambda row: (row["name"], row["aux"])),
        "qualification": "raw serialized client palette only; no animation or pixel pass",
    }


def clean_content_observations(path):
    if not path.exists():
        return {"available": False}
    data = read_json(path).get("result", {})
    rows = data.get("rows", [])
    repaired = {row["id"]: row for row in read_json(CLEAN_310_REPAIR)["result"]["rows"]}
    actual_rows = []
    for row in rows:
        repair = repaired.get(row["id"], {})
        nbt = repair.get("nbt", row.get("actual_nbt"))
        actual_rows.append({"case": row["id"],
                            "block": repair.get("actual", row.get("actual")),
                            "states": repair.get("states", row.get("actual_states")),
                            "nbt": {key: value for key, value in (nbt or {}).items()
                                    if key not in ("x", "y", "z")},
                            "repaired": bool(repair)})
    return {
        "available": True,
        "source": path.relative_to(ROOT).as_posix(),
        "sha256": sha256(path),
        "row_ids": [row.get("id") for row in rows],
        "row_count": len(rows),
        "repair_source": source_record(CLEAN_310_REPAIR),
        "rows": actual_rows,
        "qualification": "native item placement/content readback; not visual animation certification",
    }


ASSET_SELECTORS = {
    "Banner": ("textures/entity/banner/*", "models/blocks/*banner*", "materials/banner*"),
    "Sign": ("textures/entity/*sign*", "models/blocks/*sign*"),
    "HangingSign": ("textures/entity/*hanging_sign*", "models/blocks/*sign*"),
    "Bed": ("textures/entity/bed/*", "textures/blocks/bed_*", "models/blocks/*bed*"),
    "Skull": ("entity/skull.entity.json", "textures/entity/skulls/*", "textures/entity/steve.*", "models/blocks/*head*"),
    "Chest": ("textures/entity/chest/*", "models/blocks/*chest*"),
    "EnderChest": ("textures/entity/chest/ender*", "models/blocks/*chest*"),
    "ShulkerBox": ("textures/entity/shulker/*", "models/blocks/*shulker*"),
    "Conduit": ("textures/blocks/conduit_*", "textures/entity/conduit/*", "models/blocks/*conduit*", "materials/conduit*", "materials/entity.material"),
    "Bell": ("textures/entity/bell/*", "models/blocks/*bell*"),
    "Beacon": ("textures/entity/beacon*", "textures/blocks/beacon*", "models/blocks/*beacon*", "materials/beacon*", "materials/entity.material"),
    "DecoratedPot": ("textures/entity/decorated_pot/*", "textures/blocks/decorated_pot*", "textures/blocks/*_pottery_pattern*", "models/blocks/*pot*"),
    "FlowerPot": ("textures/blocks/flower_pot*", "textures/blocks/potted_*", "textures/blocks/*_roots_pot*", "models/blocks/*pot*"),
    "EnchantTable": ("textures/entity/enchanting_table_book*", "models/blocks/*enchant*"),
    "Lectern": ("textures/entity/enchanting_table_book*", "models/blocks/*lectern*"),
    "CopperGolemStatue": ("textures/entity/copper_golem/*", "models/blocks/*statue*"),
    "MovingBlock": ("materials/moving_block*", "materials/entity.material"),
    "EndGateway": ("materials/portal*", "textures/environment/end_*", "textures/entity/end_portal*", "materials/portal.material"),
    "EndPortal": ("materials/portal*", "textures/environment/end_*", "textures/entity/end_portal*", "materials/portal.material"),
    "Cauldron": ("textures/blocks/cauldron_*", "textures/blocks/water*", "textures/blocks/lava*"),
}


def texture_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for entry in value:
            yield from texture_strings(entry)
    elif isinstance(value, dict):
        for entry in value.values():
            yield from texture_strings(entry)


def installed_assets(root, entity_groups):
    if not root.exists():
        return {"available": False, "root": root.as_posix(), "files": {}, "by_native_id": {}}
    file_manifest = {}
    by_id = {key: {"files": [], "block_definitions": [], "flipbooks": []} for key in entity_groups}
    json_sources = []
    packs = sorted(path for path in root.iterdir() if path.is_dir() and
                   (path.name in ("vanilla", "vanilla_base", "experimental_vanilla_block_geometry")
                    or path.name.startswith("chemistry")))

    def register(path):
        key = path.relative_to(root).as_posix()
        if key not in file_manifest:
            file_manifest[key] = {"sha256": sha256(path), "bytes": path.stat().st_size}
        return key

    for pack in packs:
        blocks_path = pack / "blocks.json"
        terrain_path = pack / "textures/terrain_texture.json"
        flipbook_path = pack / "textures/flipbook_textures.json"
        blocks = read_json(blocks_path) if blocks_path.exists() else {}
        terrain = read_json(terrain_path).get("texture_data", {}) if terrain_path.exists() else {}
        flipbooks = read_json(flipbook_path) if flipbook_path.exists() else []
        for path in (blocks_path, terrain_path, flipbook_path):
            if path.exists():
                json_sources.append(register(path))
        # This index intentionally excludes particles, sound, UI and unrelated entity cosmetics.
        candidates = []
        for folder in ("textures/blocks", "textures/entity", "textures/environment", "models/blocks", "materials"):
            candidate_root = pack / folder
            if candidate_root.exists():
                candidates.extend(path for path in candidate_root.rglob("*") if path.is_file())
        skull_entity = pack / "entity/skull.entity.json"
        skull_description = {}
        if skull_entity.exists():
            candidates.append(skull_entity)
            skull_description = read_json(skull_entity)["minecraft:client_entity"]["description"]

        for ident, names in sorted(entity_groups.items()):
            record = by_id[ident]
            stems = [name.split(":", 1)[1] for name in names]
            selectors = list(ASSET_SELECTORS.get(ident, ()))
            if ident == "Skull":
                selectors.extend(base + ".*" for base in skull_description.get("textures", {}).values())
            selectors.extend("textures/blocks/%s.*" % stem for stem in stems)
            selectors.extend("textures/blocks/%s_*" % stem for stem in stems)
            selectors.extend("models/blocks/%s*" % stem for stem in stems)
            atlas_names = set()
            texture_bases = set()
            for name in names:
                slug = name.split(":", 1)[1]
                definition = blocks.get(name, blocks.get(slug))
                if definition is not None:
                    record["block_definitions"].append({"source": blocks_path.relative_to(root).as_posix(),
                                                        "name": name, "definition": definition})
                    for field in ("textures", "carried_textures"):
                        atlas_names.update(texture_strings(definition.get(field, {})))
            for atlas in sorted(atlas_names):
                entry = terrain.get(atlas)
                if entry:
                    texture_bases.update(path for path in texture_strings(entry.get("textures", {}))
                                         if path.startswith("textures/"))
            selectors.extend(base + ".*" for base in texture_bases)
            for flipbook in flipbooks:
                if (flipbook.get("atlas_tile") in atlas_names or
                        any(re.search(r"(^|/)%s(?:_|$)" % re.escape(stem),
                                      flipbook.get("flipbook_texture", "")) for stem in stems)):
                    record["flipbooks"].append({"source": flipbook_path.relative_to(root).as_posix(),
                                                "entry": flipbook})
            for path in candidates:
                rel = path.relative_to(pack).as_posix()
                if any(fnmatch.fnmatchcase(rel, pattern) for pattern in selectors):
                    record["files"].append(register(path))

    skull = root / "vanilla/entity/skull.entity.json"
    if skull.exists():
        by_id["Skull"]["client_entity_description"] = read_json(skull)["minecraft:client_entity"]["description"]
    entity_material = root / "vanilla/materials/entity.material"
    if entity_material.exists():
        definitions = read_json(entity_material).get("materials", {})
        for ident, prefix in (("Beacon", "beacon_beam"), ("Conduit", "conduit_wind"),
                              ("MovingBlock", "moving_block")):
            key = register(entity_material)
            by_id[ident]["material_definitions"] = {
                "source": key,
                "entries": {name: value for name, value in definitions.items()
                            if name.split(":", 1)[0].startswith(prefix)},
            }
    for record in by_id.values():
        record["files"] = sorted(set(record["files"]))
    return {"available": True, "root": root.as_posix(),
            "packs_scanned": [path.name for path in packs], "json_sources": sorted(set(json_sources)),
            "files": file_manifest, "by_native_id": by_id,
            "qualification": "installed file evidence only; pack precedence, native renderer behavior and animation are not certified",
            "excluded_assets": ["particles", "sound", "UI", "unrelated entity cosmetics", "Netease cosmetic packs"],
            "geometry_boundary": "Several vanilla block entity models are engine-built; missing JSON geometry does not establish absent rendering."}


def build_inventory():
    defaults = read_json(DEFAULTS)
    registry = read_json(REGISTRY)
    manifest = read_json(REGISTRY_MANIFEST)
    renderers = read_json(RENDERERS)
    appearances = read_json(APPEARANCES)
    actors = read_json(PALETTE_ACTORS)
    water = read_json(WATER_OVERLAYS)

    registry_by_name = registry_inventory(registry)
    registry_state_count = sum(len(rows) for rows in registry_by_name.values())
    entity_groups = defaultdict(list)
    for name, row in sorted(defaults["block_entities"].items()):
        nbt = row["nbt"]
        entity_id = scalar(nbt.get("id"))
        fields = typed_fields(nbt)
        entity_groups[entity_id].append(name)
    if set(entity_groups) != set(APPEARANCE_NOTES):
        raise ValueError("Every observed native ID must have exactly one explicit appearance note")
    if not (sha256(REGISTRY) == manifest["source_sha256"].lower() == defaults["palette_sha256"].lower()):
        raise ValueError("Registry/default palette provenance does not match")
    if any(name not in registry_by_name for name in defaults["block_entities"]):
        raise ValueError("An observed native entity block is absent from the registry")

    renderer_by_name = defaultdict(list)
    for row in renderers.get("records", []):
        material = row.get("material", [None, None])
        renderer_by_name[material[0]].append({
            "entity": row.get("entity"),
            "actor_fields": sorted((row.get("actor") or {}).keys()),
            "verified_material_and_states": row.get("verified_material_and_states", False),
        })

    entities = []
    for entity_id in sorted(entity_groups):
        names = sorted(entity_groups[entity_id])
        sample = defaults["block_entities"][names[0]]
        nbt = sample["nbt"]
        fields = typed_fields(nbt)
        entities.append({
            "id": entity_id,
            "block_names": names,
            "block_count": len(names),
            "aux_samples": {name: defaults["block_entities"][name]["aux"] for name in names},
            "default_fields": fields,
            "classification": classify(entity_id),
            "appearance_note": APPEARANCE_NOTES.get(entity_id, "No explicit appearance note recorded; treat as native static acceptance pending a targeted nondefault probe."),
            "difficulty": {
                "order": DIFFICULTY.get(classify(entity_id), (5, "unclassified", [2.0, 6.0]))[0],
                "work_item": DIFFICULTY.get(classify(entity_id), (5, "unclassified", [2.0, 6.0]))[1],
                "estimate_person_days": DIFFICULTY.get(classify(entity_id), (5, "unclassified", [2.0, 6.0]))[2],
            },
            "renderer_evidence": {name: renderer_by_name.get(name, []) for name in names},
            "registry_state_summary": {
                name: state_summary(registry_by_name.get(name, [])) for name in names
            },
        })

    registry_names = set(registry_by_name)
    probe_names = set(defaults.get("block_entity_names", []))
    editor_names = sorted(name for name in registry_names - probe_names if name.startswith("modern_projection:"))
    native_entity_names = set(defaults["block_entities"])
    missing_probe_names = sorted(registry_names - probe_names)
    state_mismatches = defaults["tested_states"] - defaults["verified_states"]

    sources = {
        "native_defaults": source_record(DEFAULTS, defaults, game_version=defaults["game_version"],
                                          method=defaults["method"], tested_states=defaults["tested_states"],
                                          verified_states=defaults["verified_states"],
                                          native_probe_sha256=defaults["native_probe_sha256"],
                                          palette_sha256=defaults["palette_sha256"]),
        "registry": source_record(REGISTRY, registry, game_version=manifest["game_version"],
                                   source_sha256=manifest["source_sha256"], record_count=registry_state_count),
        "registry_manifest": source_record(REGISTRY_MANIFEST, manifest),
        "renderers": source_record(RENDERERS, renderers, total_records=renderers.get("total_records"),
                                    verified_records=renderers.get("verified_records")),
        "appearances": source_record(APPEARANCES, appearances, row_count=len(appearances.get("rows", []))),
        "palette_actors": source_record(PALETTE_ACTORS, actors, row_count=len(actors.get("rows", []))),
        "water_overlays": source_record(WATER_OVERLAYS, water, tested_states=water.get("tested_states"),
                                         verified_states=water.get("verified_states")),
        "item_contents": source_record(ITEM_CONTENTS, read_json(ITEM_CONTENTS), scope="3.9 native frame item readback"),
        "pot_sherds": source_record(POT_SHERDS, read_json(POT_SHERDS), scope="3.9 decorated pot sherd readback"),
        "bed_capture": source_record(BED_CAPTURE, read_json(BED_CAPTURE), scope="3.9 native bed paired capture"),
        "clean_310_palette": source_record(CLEAN_310, read_json(CLEAN_310), scope="3.10 raw client palette"),
    }

    return {
        "schema": 1,
        "target_engine": "3.10.0.420447",
        "target_minecraft": "1.21.130.0",
        "scope": "offline native NBT and dynamic appearance inventory; no runtime launch",
        "sources": sources,
        "registry": {
            "game_version": manifest["game_version"],
            "name_count": manifest["name_count"],
            "state_count": registry_state_count,
            "state_key_count": manifest["state_key_count"],
            "names": sorted(registry_names),
            "source_contains_complete_state_records": True,
        },
        "native_id_to_block_names": entities,
        "coverage": {
            "native_id_count": len(entities),
            "native_block_name_count": len(defaults["block_entities"]),
            "probe_name_count": len(probe_names),
            "registry_name_count": len(registry_names),
            "tested_states": defaults["tested_states"],
            "verified_states": defaults["verified_states"],
            "state_mismatch_count": state_mismatches,
            "later_merged_native_state_evidence": {
                "source": WATER_OVERLAYS.relative_to(ROOT).as_posix(),
                "sha256": sha256(WATER_OVERLAYS),
                "tested_states": water["tested_states"],
                "verified_states": water["verified_states"],
                "state_mismatches": water["state_mismatches"],
                "evidence_sources": water["evidence_sources"],
                "note": "The immutable NBT defaults snapshot retains the pre-repair counters; paired bed evidence later repaired the eight placement mismatches. This is placement evidence, not 3.10 visual coverage.",
            },
            "editor_preview_names_excluded_from_probe": editor_names,
            "registry_names_not_probed": missing_probe_names,
            "probed_names_with_no_default_nbt": sorted(probe_names - native_entity_names),
            "boundaries": [
                "3.9 native defaults are the complete identity/field source; this is not a fresh 3.10 NBT dump.",
                "3.10 clean evidence contains raw client actor fields for 14 names only and no animation/pixel qualification.",
                "MobSpawner and TrialSpawner internal creature models are excluded; present/empty/unknown configuration markers remain required.",
                "Particles, education, MovingBlock, activated conduit effects, beacon beams and vault internal-item effects are excluded by current user scope.",
                "EnchantTable requires an idle book only, without player proximity reactions.",
                "World lava may use official 3.10 rendering; water and cauldron liquid remain custom routes.",
                "CombineBlockPaletteToGeometry official docs exclude end portals, end gateways, miniature blocks and animated custom appearance.",
            ],
        },
        "runtime_3_10_clean_observations": clean_actor_observations(CLEAN_310),
        "runtime_3_10_content_observations": clean_content_observations(CLEAN_310_CONTENT),
        "installed_3_10_assets": installed_assets(RESOURCE_ROOT, entity_groups),
        "education_and_custom_boundary": {
            "education_registry_names": sorted(name for name in registry_names if
                re.fullmatch(r"minecraft:(element_[0-9]+|compound_creator|element_constructor|lab_table|material_reducer|camera|chemical_heat|colored_torch_[a-z_]+|underwater_tnt|underwater_torch|allow|deny|border_block|hard_[a-z_]+)", name)),
            "native_education_nbt_id": "ChemistryTable",
            "names_not_in_registry": [name for name in ("minecraft:balloon", "minecraft:chalkboard", "minecraft:spawn_agent", "minecraft:npc") if name not in registry_names],
            "editor_custom_registry_names": sorted(name for name in registry_names if not name.startswith("minecraft:")),
            "unknown_custom_content": "Arbitrary addon block entities are not closed by this vanilla/3.9 registry. Client runtime render/pose and foreign geometry require separate fixtures; no invented NBT IDs are assigned.",
        },
        "effort_estimate_boundary": {
            "unit": "person-days of one engineer after access to working native fixtures",
            "purpose": "ordering and conditional planning, not a measured schedule or completed implementation",
            "not_additive": "Ranges are per representative family; shared item rendering, animation scheduling, palette context and native capture costs must be counted once, not per wood/color/oxidation name.",
            "excluded": ["particles", "MobSpawner/TrialSpawner internal creature models", "education appearance", "MovingBlock appearance", "activated conduit effects", "beacon beams", "vault internal-item effects", "EnchantTable player proximity reactions", "fresh dump update", "rotation/mirror table updates"],
            "uncertainty": "Empty defaults and installed assets do not qualify populated contents or animation. Native static success can reduce work; missing native support can increase these estimates.",
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="compare the checked-in inventory without writing")
    args = parser.parse_args()
    data = build_inventory()
    output_text = json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="ascii") != output_text:
            raise ValueError("The offline inventory is stale")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_text, encoding="ascii")
    print("native IDs: %d; native block names: %d; registry states: %d; assets: %d" % (
        data["coverage"]["native_id_count"],
        data["coverage"]["native_block_name_count"],
        data["registry"]["state_count"],
        len(data["installed_3_10_assets"].get("files", {})),
    ))


if __name__ == "__main__":
    main()
