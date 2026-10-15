"""Summarize auditable NEMC 3.10 NBT/appearance evidence by family.

This is an evidence indexer. It deliberately does not turn native NBT fields,
palette actor names, or CombineBlockPaletteToGeometry results into a pixel pass.
The source bundle was collected in a clean 3.10.0.420447 instance and its
capture is retained as a separate, explicitly obscured visual control.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SOURCE_ROOT = Path("D:/bbe-r14-nemc310/docs/evidence/nemc-clean-r14/310")
OUTPUT_DEFAULT = Path("docs/evidence/nemc-nbt-r15/runtime-family-results.json")


FAMILIES = {
    "enchant_table": {
        "ids": ["EnchantTable"],
        "materials": ["minecraft:enchanting_table"],
        "scope": "special book model, NBT-free default and animated visible model",
    },
    "beacon": {
        "ids": ["Beacon"],
        "materials": ["minecraft:beacon"],
        "scope": "beam geometry; particles excluded",
    },
    "conduit": {
        "ids": ["Conduit"],
        "materials": ["minecraft:conduit"],
        "scope": "inactive/active core and wind geometry; particles excluded",
    },
    "banner": {
        "ids": ["Banner"],
        "materials": ["minecraft:standing_banner", "minecraft:wall_banner"],
        "scope": "base color, patterns, ominous variant, orientation",
    },
    "sign": {
        "ids": ["Sign", "HangingSign"],
        "materials": [
            "minecraft:standing_sign",
            "minecraft:wall_sign",
            "minecraft:oak_hanging_sign",
        ],
        "scope": "front/back text, colors, glow flags, orientation",
    },
    "flower_pot": {
        "ids": ["FlowerPot"],
        "materials": ["minecraft:flower_pot"],
        "scope": "empty and visible plant content",
    },
    "decorated_pot": {
        "ids": ["DecoratedPot"], "materials": ["minecraft:decorated_pot"],
        "scope": "four sherd faces and facing; hidden inventory excluded",
    },
    "item_frames": {
        "ids": ["ItemFrame", "GlowItemFrame"],
        "materials": ["minecraft:frame", "minecraft:glow_frame"],
        "scope": "native frame shell; visible item and glint require separate observation",
    },
    "shelf": {
        "ids": ["Shelf"], "materials": [],
        "scope": "shelf shell and nonempty visible item slots",
    },
    "lectern": {
        "ids": ["Lectern"], "materials": ["minecraft:lectern"],
        "scope": "empty lectern and visible book",
    },
    "brushable": {
        "ids": ["BrushableBlock"],
        "materials": ["minecraft:suspicious_sand", "minecraft:suspicious_gravel"],
        "scope": "brush progress and exposed item; particles excluded",
    },
    "brewing_stand": {
        "ids": ["BrewingStand"], "materials": ["minecraft:brewing_stand"],
        "scope": "native shell and three bottle occupancy states",
    },
    "chiseled_bookshelf": {
        "ids": ["ChiseledBookshelf"], "materials": ["minecraft:chiseled_bookshelf"],
        "scope": "six occupied-slot textures and facing",
    },
    "copper_statue": {
        "ids": ["CopperGolemStatue"], "materials": [],
        "scope": "statue pose, facing, oxidation and wax; not a live mob",
    },
    "chest": {
        "ids": ["Chest"],
        "materials": ["minecraft:chest", "minecraft:copper_chest"],
        "scope": "empty/content NBT, pair state, opening fields",
    },
    "ender_chest": {
        "ids": ["EnderChest"],
        "materials": ["minecraft:ender_chest"],
        "scope": "native ender chest shell and state",
    },
    "shulker": {
        "ids": ["ShulkerBox"],
        "materials": ["minecraft:purple_shulker_box"],
        "scope": "color, facing, empty/content NBT",
    },
    "bed": {
        "ids": ["Bed"],
        "materials": ["minecraft:bed"],
        "scope": "paired head/foot and color state",
    },
    "skull": {
        "ids": ["Skull"],
        "materials": ["minecraft:skull", "minecraft:player_head"],
        "scope": "dragon, piglin, player and orientation variants",
    },
    "cauldron": {
        "ids": ["Cauldron"],
        "materials": ["minecraft:cauldron", "minecraft:lava_cauldron"],
        "scope": "empty/water levels and visible liquid content; no particles",
    },
    "bell": {
        "ids": ["Bell"],
        "materials": ["minecraft:bell"],
        "scope": "idle shell and ringing pose/action",
    },
    "campfire": {
        "ids": ["Campfire"],
        "materials": ["minecraft:campfire", "minecraft:soul_campfire"],
        "scope": "flame texture and visible cooking items; smoke excluded",
    },
    "moving_piston": {
        "ids": ["PistonArm", "MovingBlock"],
        "materials": ["minecraft:piston", "minecraft:sticky_piston", "minecraft:moving_block"],
        "scope": "moving head/arm and embedded block snapshot",
    },
    "vault_trial": {
        "ids": ["Vault", "TrialSpawner"],
        "materials": ["minecraft:vault", "minecraft:trial_spawner"],
        "scope": "exterior/state-driven model; internal mobs excluded",
    },
    "sculk_dynamic": {
        "ids": ["SculkSensor", "CalibratedSculkSensor", "SculkCatalyst", "SculkShrieker"],
        "materials": [
            "minecraft:sculk_sensor",
            "minecraft:calibrated_sculk_sensor",
            "minecraft:sculk_catalyst",
            "minecraft:sculk_shrieker",
        ],
        "scope": "state-driven animated textures and visible shell",
    },
    "simple_static_nbt": {
        "ids": [
            "Barrel", "Beehive", "BlastFurnace", "ChemistryTable", "CommandBlock",
            "Comparator", "Crafter", "CraftingTable", "CreakingHeart", "DaylightDetector",
            "Dispenser", "Dropper", "Furnace", "Hopper", "JigsawBlock", "Jukebox",
            "Lodestone", "Music", "NetherReactor", "Smoker", "StructureBlock", "SporeBlossom",
        ],
        "materials": [],
        "scope": "preserve native NBT/state; no hidden inventory overlay",
    },
    "mob_spawner_shell": {
        "ids": ["MobSpawner", "TrialSpawner"],
        "materials": ["minecraft:mob_spawner", "minecraft:trial_spawner"],
        "scope": "shell/state only; internal creature rendering excluded",
    },
    "end_portal_gateway": {
        "ids": ["EndPortal", "EndGateway"],
        "materials": ["minecraft:end_portal", "minecraft:end_gateway"],
        "scope": "official Combine exclusion; dedicated surface route required",
    },
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def result_rows(path: Path) -> list[dict[str, Any]]:
    value = load_json(path)
    rows = value.get("result", {}).get("rows", [])
    return rows if isinstance(rows, list) else []


def source_actor_names(project: dict[str, Any]) -> list[str]:
    source = project.get("result", {}).get("source", {})
    actors = source.get("actor", {})
    return sorted(str(name) for name in actors)


def family_matches(row: dict[str, Any], family: dict[str, Any]) -> bool:
    block = row.get("block", {}) or row.get("actual", {}) or {}
    material = block.get("name")
    nbt = row.get("nbt", {}) or row.get("actual_nbt", {}) or {}
    nbt_id = (nbt.get("id") or {}).get("__value__") if isinstance(nbt, dict) else None
    return material in family["materials"] or nbt_id in family["ids"]


def select_rows(rows: list[dict[str, Any]], family: dict[str, Any]) -> list[dict[str, Any]]:
    selected = []
    for row in rows:
        if family_matches(row, family):
            block = row.get("block", {}) or row.get("actual", {}) or {}
            nbt = row.get("nbt", {}) or row.get("actual_nbt", {}) or {}
            states = row.get("states")
            if states is None:
                states = row.get("actual_states")
            selected.append({
                "case": row.get("case") or row.get("id"),
                "block": block,
                "states": states,
                "nbt": nbt,
                "repaired": row.get("repaired", False),
                "readback_source": row.get("readback_source"),
            })
    return selected


def build_report() -> dict[str, Any]:
    files = {
        "admission": SOURCE_ROOT / "admission/result.json",
        "mounted_packs": SOURCE_ROOT / "admission/mounted-packs.json",
        "content": SOURCE_ROOT / "content/result.json",
        "repair": SOURCE_ROOT / "repair/result.json",
        "project": SOURCE_ROOT / "project-refreshed/result.json",
        "capture": SOURCE_ROOT / "overview.capture.json",
        "screenshot": SOURCE_ROOT / "overview.png",
        "index": SOURCE_ROOT / "index.json",
        "capacity": SOURCE_ROOT / "prelaunch-capacity.json",
        "exit": SOURCE_ROOT / "independent-exit.json",
    }
    missing = [str(path) for path in files.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing source evidence: " + ", ".join(missing))

    admission = load_json(files["admission"])
    content = load_json(files["content"])
    project = load_json(files["project"])
    capture = load_json(files["capture"])
    index = load_json(files["index"])
    # Preserve broad coverage, then replace only cases actually reread after
    # repair. Ignoring this later evidence incorrectly reported lost Patterns.
    indexed_rows = {}
    for source_name in ("content", "repair"):
        for row in result_rows(files[source_name]):
            key = row.get("id") or row.get("case")
            if not isinstance(key, str):
                raise ValueError("Readback row requires a stable case identifier")
            indexed_rows[key] = dict(row, readback_source=str(files[source_name]),
                                    repaired=source_name == "repair")
    content_rows = list(indexed_rows.values())
    actor_names = source_actor_names(project)
    capture_obscured = True
    source_manifest = {
        key: {
            "path": str(path),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
        for key, path in files.items()
    }

    rows = []
    for name, family in FAMILIES.items():
        selected = select_rows(content_rows, family)
        observed_materials = sorted({
            row.get("block", {}).get("name")
            for row in selected
            if row.get("block", {}).get("name")
        })
        palette_materials = sorted(set(family["materials"]).intersection(actor_names))
        raw_status = "observed" if selected else "unavailable"
        nondefault = [
            row for row in selected
            if str(row.get("case") or "").endswith(("_content", "_patterns", "_text", "_ominous"))
            or row.get("case") in {"frame_enchanted_sword", "cauldron_water"}
        ]
        nondefault_status = "observed" if nondefault else ("not_applicable" if not selected else "unavailable")
        limitations: list[str] = []
        if name == "banner" and nondefault:
            pattern_rows = [
                row for row in nondefault
                if str(row.get("case") or "").endswith("_patterns")
            ]
            missing_patterns = [
                row.get("case") for row in pattern_rows
                if not isinstance(row.get("nbt"), dict) or "Patterns" not in row["nbt"]
            ]
            if missing_patterns:
                nondefault_status = "observed_partial"
                limitations.append(
                    "Requested pattern cases were placed and base/type read back, "
                    f"but final content NBT omitted nested Patterns ({', '.join(missing_patterns)})."
                )
        if name == "cauldron" and nondefault:
            nondefault_status = "observed_partial"
            limitations.append(
                "Only empty and ordinary-water levels were observed; potion, lava, "
                "powder-snow, and custom-color variants are not covered by this run."
            )
        if name == "conduit":
            nondefault_status = "unavailable" if selected else "not_applicable"
            if selected:
                limitations.append("Only the inactive/default state was observed; active-frame behavior was not exercised.")
        if name == "bell":
            nondefault_status = "unavailable" if selected else "not_applicable"
            if selected:
                limitations.append("Only the idle/default state was observed; ringing action/pose was not exercised.")
        native_call = "observed" if palette_materials else ("unavailable" if not selected else "no_actor_submission")
        if selected or palette_materials:
            pixel_status = "unknown_obscured"
            pixel_reason = "Reliable WGC frame exists, but the only 3.10 overview is obscured by pause/menu UI and is not a family-isolated pixel acceptance frame."
        else:
            pixel_status = "unavailable"
            pixel_reason = "No isolated 3.10 capture for this family in the source bundle."
        action_status = "unknown"
        if name in {"conduit", "bell"}:
            action_status = "unavailable" if selected else "not_observed"
        if name in {"end_portal_gateway"}:
            action_status = "not_applicable"
            pixel_status = "unsupported_by_combine"
            pixel_reason = "Official CombineBlockPaletteToGeometry documentation excludes EndPortal and EndGateway; no support claim is made."
        rows.append({
            "family": name,
            "scope": family["scope"],
            "materials": family["materials"],
            "native_ids": family["ids"],
            "default": raw_status,
            "nondefault": nondefault_status,
            "action": action_status,
            "raw_nbt": {
                "status": raw_status,
                "rows": selected,
                "source": str(files["content"]),
                "supplemental_repair_source": str(files["repair"]),
            },
            "project_palette": {
                "status": "observed" if palette_materials else "unavailable",
                "actor_materials": palette_materials,
                "source": str(files["project"]),
            },
            "native_call": {
                "status": native_call,
                "actor_names": palette_materials,
                "combine_result_present": bool(palette_materials),
                "source": str(files["project"]),
            },
            "pixel_status": pixel_status,
            "pixel_reason": pixel_reason,
            "limitations": limitations,
            "capture": {
                "status": "reliable_but_obscured" if capture_obscured else "reliable",
                "path": capture.get("path"),
                "metadata": str(files["capture"]),
                "sha256": capture.get("sha256"),
            },
            "observed_materials": observed_materials,
        })

    runtime = {
        "engine": admission.get("result", {}).get("engine"),
        "minecraft": admission.get("result", {}).get("runtime"),
        "ui_initialized": admission.get("result", {}).get("ui_initialized"),
        "admission_pixel_acceptance": admission.get("pixel_acceptance", False),
        "source_index": index,
    }
    return {
        "schema": 2,
        "audit": "nemc310-nbt-r15",
        "created_from": "nemc-clean-r14 3.10 clean runtime evidence",
        "qualification": "Structural/NBT and palette evidence are recorded separately from pixel acceptance.",
        "runtime": runtime,
        "capture_control": {
            "reliable": bool(capture.get("reliable")),
            "background_only": bool(capture.get("background_only")),
            "foreground_unchanged": bool(capture.get("foreground_unchanged")),
            "window": capture.get("window"),
            "obscured": capture_obscured,
            "obscured_reason": "Pause/menu UI and a large gray panel cover the world in overview.png.",
        },
        "source_manifest": source_manifest,
        "family_results": rows,
        "policy": {
            "particles": "excluded",
            "internal_spawner_mobs": "excluded",
            "end_portal_gateway": "unsupported_by_combine; no support claim",
            "api_or_nbt_is_not_pixel_acceptance": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output.resolve()), "families": len(report["family_results"]), "runtime": report["runtime"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
