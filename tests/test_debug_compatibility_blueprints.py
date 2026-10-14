"""Public inspection pages cover the inventory's independent source snapshots."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.cell import actor_data, foreground
from projection.debug_blueprints import BLUEPRINTS, VISUAL_CASES, build
from projection.debug_compatibility_blueprints import CASES, FOCUS, METADATA, source_document
from projection.nbt_spatial import root_payload, scalar
from projection.visible_actor import entity_nbt


class CompatibilityBlueprintTests(unittest.TestCase):
    def test_every_resource_linked_dynamic_name_has_a_small_public_gallery(self):
        audit = json.loads((ROOT / 'tools/data/native_animated_blocks_nemc_3.9.0.401155.json').read_bytes())
        expected = {row['name'] for row in audit['rows']}
        actual = {row['name'] for identity, rows in CASES.items()
                  if identity.startswith('test.dynamic.') for row in rows}
        self.assertFalse(expected - actual)
        self.assertTrue({'minecraft:portal', 'minecraft:end_portal', 'minecraft:end_gateway'} <= actual)
        for metadata in METADATA:
            self.assertIn(metadata, BLUEPRINTS)
            self.assertEqual(metadata[0], VISUAL_CASES[metadata[0]]['fixture'])

    def test_all_captured_nbt_names_and_payloads_are_publicly_inspectable(self):
        snapshot = json.loads((ROOT / 'tools/data/native_block_entity_defaults_nemc_3.9.0.401155.json').read_bytes())
        expected = snapshot['block_entities']
        actual = set()
        for identity, rows in CASES.items():
            if not identity.startswith('test.entities.catalogue.'):
                continue
            document = build(identity)
            self.assertLessEqual(len(rows), 24)
            for row in rows:
                cell = document.get(row['anchor'])
                actual.add(foreground(cell)[0])
                payload = root_payload(entity_nbt(actor_data(cell)))
                self.assertEqual(scalar(root_payload(expected[row['name']]['nbt']), 'id'), scalar(payload, 'id'))
                self.assertEqual(row['anchor'], tuple(scalar(payload, axis) for axis in ('x', 'y', 'z')))
        self.assertEqual(set(expected), actual)

    def test_isolated_cases_keep_layers_groups_and_rebase_only_spatial_actor_fields(self):
        identity = 'test.entities.catalogue.01'
        for row in CASES[identity]:
            gallery = build(identity)
            before = deepcopy(gallery.to_data())
            isolated = source_document(identity, row['id'])
            cell = isolated.get(FOCUS)
            self.assertEqual(row['material'], foreground(cell))
            original = root_payload(entity_nbt(actor_data(gallery.get(row['anchor']))))
            moved = root_payload(entity_nbt(actor_data(cell)))
            self.assertEqual(FOCUS, tuple(scalar(moved, axis) for axis in ('x', 'y', 'z')))
            for key in original:
                if key not in ('x', 'y', 'z', 'pairx', 'pairz'):
                    self.assertEqual(original[key], moved[key])
            self.assertEqual(before, gallery.to_data())
        with self.assertRaises(ValueError):
            source_document(identity, 'nonexistent')


if __name__ == '__main__':
    unittest.main()
