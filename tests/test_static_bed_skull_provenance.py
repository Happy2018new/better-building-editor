"""Native bed and skull resources are independently pinned to the block dump."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / 'tools'))
from projection import static_bed_data, static_skull_data, block_registry
from projection.block_registry import from_states
from projection.cell import make_cell
from projection.geometry_palette import prepare_palette
from projection.model import Document
from projection.static_bed import bed_proxy
from projection.static_skull import skull_proxy
from generate_bed_proxies import outputs as bed_outputs
from generate_skull_proxies import outputs as skull_outputs


class BedSkullProvenanceTests(unittest.TestCase):
    def test_stale_bed_schema_refuses_rendering_without_modifying_actor(self):
        material = from_states('minecraft:bed', {
            'direction': 0, 'head_piece_bit': True, 'occupied_bit': False})
        actor = {'color': 8}
        before = deepcopy(actor)
        with patch.object(static_bed_data, 'SCHEMA_VERSION', 99):
            with self.assertRaisesRegex(ValueError, 'bed models'):
                bed_proxy(material, actor)
        self.assertEqual(before, actor)

    def test_skull_drift_refuses_both_floor_and_wall_without_modifying_document(self):
        for facing in (1, 2):
            material = from_states('minecraft:skeleton_skull', {'facing_direction': facing})
            document = Document((3, 3, 3), {(1, 1, 1): make_cell(material, nbt={'rotation': 0.})})
            before = document.to_data()
            for field, value in (('SCHEMA_VERSION', 99), ('SOURCE_VERSION', 'NEMC future'),
                                 ('PALETTE_SHA256', '0' * 64)):
                with self.subTest(facing=facing, field=field), patch.object(static_skull_data, field, value):
                    with self.assertRaisesRegex(ValueError, 'regeneration'):
                        prepare_palette(document.palette_data())
                    self.assertEqual(before, document.to_data())

    def test_registry_change_independently_refuses_skull_resource(self):
        material = from_states('minecraft:skeleton_skull', {'facing_direction': 2})
        with patch.object(block_registry, 'fingerprint', return_value='0' * 64):
            with self.assertRaisesRegex(ValueError, 'skull models'):
                skull_proxy(material, None)

    def test_stale_sources_do_not_block_unrelated_materials(self):
        with patch.object(static_bed_data, 'SCHEMA_VERSION', 99), \
                patch.object(static_skull_data, 'SOURCE_VERSION', 'NEMC future'):
            self.assertIsNone(bed_proxy(('minecraft:stone', 0), None))
            self.assertIsNone(skull_proxy(('minecraft:stone', 0), None))

    def test_generators_reject_stale_metadata_before_producing_assets(self):
        for filename, generate, schema in (('bed_static_model_v1.json', bed_outputs, 1),
                                           ('skull_static_model_v1.json', skull_outputs, 3)):
            spec = json.loads((ROOT / 'tools/data' / filename).read_text(encoding='utf8'))
            self.assertEqual(schema, spec['schema'])
            for field, value in (('game_version', 'NEMC future'), ('palette_sha256', '0' * 64),
                                 ('schema', 99)):
                changed = deepcopy(spec)
                changed[field] = value
                with self.subTest(filename=filename, field=field), self.assertRaises(ValueError):
                    generate(changed)
                self.assertEqual(value, changed[field])


if __name__ == '__main__':
    unittest.main()
