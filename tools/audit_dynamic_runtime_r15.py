"""Run a bounded 3.10 dynamic ordinary-block appearance audit.

This intentionally writes only the owner-bound test world and captures the
project's editor/projection surfaces. It records pixel evidence separately
from SDK/model success and excludes particle effects.
"""
from __future__ import print_function

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".agents/skills/pyreact-debugging/scripts"

DYNAMIC = (
    "bubble_column", "fire", "soul_fire", "lantern", "soul_lantern",
    "copper_lantern", "exposed_copper_lantern", "weathered_copper_lantern",
    "oxidized_copper_lantern", "waxed_copper_lantern",
    "waxed_exposed_copper_lantern", "waxed_weathered_copper_lantern",
    "waxed_oxidized_copper_lantern", "sculk", "sculk_vein", "kelp",
    "seagrass", "firefly_bush", "prismarine", "prismarine_slab",
    "prismarine_double_slab", "prismarine_stairs", "prismarine_wall",
    "sea_lantern", "crimson_stem", "crimson_hyphae", "warped_stem",
    "warped_hyphae", "magma", "portal", "respawn_anchor",
    "stonecutter_block", "chemical_heat", "big_dripleaf", "end_portal",
    "end_gateway", "conduit",
)

GROUPS = {
    "portal_family": ("portal", "end_portal", "end_gateway"),
    "fire_family": ("fire", "soul_fire"),
    "lantern_family": tuple(x for x in DYNAMIC if "lantern" in x),
    "sculk_family": ("sculk", "sculk_vein"),
    "water_plants": ("kelp", "seagrass", "big_dripleaf"),
    "prismarine_family": ("prismarine", "prismarine_slab", "prismarine_double_slab", "prismarine_stairs", "prismarine_wall", "sea_lantern"),
    "nether_family": ("crimson_stem", "crimson_hyphae", "warped_stem", "warped_hyphae", "magma"),
}


def source_for_blocks(selected):
    names = tuple("minecraft:" + name for name in selected)
    return """import json\nimport mod.client.extraClientApi as api\nfrom modern_projection.projection.model import Document\nfrom modern_projection.projection import block_registry as registry\napi_system = api.GetSystem('ModernProjection','ModernProjectionClientSystem')\nassert api_system is not None and api_system.session is not None\ns = api_system.session\napi_system.open_workspace()\ndoc = Document((48, 8, 32), name='r15_dynamic_runtime_310')\nnames = %r\nrows = []\nfor index, name in enumerate(names):\n    x = 1 + (index %% 12) * 4\n    z = 1 + (index // 12) * 4\n    aux = registry.DEFAULT_AUX.get(name)\n    if aux is None:\n        aux = 0\n    doc.blocks[(x, 1, z)] = (name, aux)\n    rows.append({'name': name, 'pos': (x, 1, z), 'aux': aux})\ns._loaded(doc)\n_result = json.dumps({'rows': rows, 'size': doc.size, 'blocks': len(doc.blocks)})\n""" % (names,)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf8")


def execute(session, owner, code, client=True):
    args = ROOT / ".runtime/r15-dynamic-execute.json"
    write_json(args, {"code": code, "is_client": client, "direct_return": True})
    command = [sys.executable, "-X", "utf8", str(SCRIPTS / "instances.py"), "exec",
               "--session", session, "--owner", owner, "--", "mcdk.py", "call",
               "execute_code", "--args-file", str(args)]
    raw = subprocess.check_output(command, cwd=str(ROOT), text=True, encoding="utf8")
    return raw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"schema": 1, "engine": "3.10.0.420447", "minecraft": "1.21.130.0",
              "particles": "excluded", "groups": GROUPS, "candidates": DYNAMIC,
              "pixel_acceptance": False}
    try:
        result["document"] = execute(args.session, args.owner, source_for_blocks())
        result["captured_at"] = time.time()
        result["note"] = "Rows were submitted to editor preview; screenshots must be inspected independently."
    except Exception as error:
        result["error"] = "%s: %s" % (type(error).__name__, error)
    write_json(args.output, result)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
