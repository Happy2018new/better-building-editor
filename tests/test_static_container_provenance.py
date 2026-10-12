"""Container rendering refuses adapters captured for another version or dump."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / 'tools'))
from projection import block_registry, static_chest_data, static_shulker_data
from projection.entity_render import static_proxy
from projection.geometry_palette import prepare_palette
from projection.model import Document
from generate_copper_chest_proxies import outputs as chest_outputs
from generate_shulker_proxies import outputs as shulker_outputs


class ContainerProvenanceTests(unittest.TestCase):
    def test_registry_change_refuses_both_containers_without_modifying_document(self):
        for name in ('minecraft:chest', 'minecraft:undyed_shulker_box'):
            with self.subTest(name=name):
                material = (name, 0)
                document = Document((2, 2, 2), {(1, 1, 1): material})
                before = document.to_data()
                with patch.object(block_registry, 'fingerprint', return_value='0' * 64):
                    with self.assertRaisesRegex(ValueError, 'regeneration'):
                        prepare_palette(document.palette_data())
                self.assertEqual(before, document.to_data())

    def test_runtime_adapter_schema_or_version_change_is_rejected(self):
        for data, material in ((static_chest_data, ('minecraft:chest', 0)),
                               (static_shulker_data, ('minecraft:undyed_shulker_box', 0))):
            for field, value in (('SCHEMA_VERSION', 99), ('SOURCE_VERSION', 'NEMC future')):
                with self.subTest(material=material, field=field):
                    with patch.object(data, field, value):
                        with self.assertRaisesRegex(ValueError, 'regeneration'):
                            static_proxy(material, None)

    def test_stale_container_tables_do_not_block_unrelated_materials(self):
        with patch.object(static_chest_data, 'SOURCE_VERSION', 'NEMC future'), \
                patch.object(static_shulker_data, 'SOURCE_VERSION', 'NEMC future'):
            self.assertIsNone(static_proxy(('minecraft:stone', 0), None))

    def test_generators_reject_sources_from_a_different_dump_or_version(self):
        for filename, generate in (('copper_chest_static_model_v1.json', chest_outputs),
                                   ('shulker_static_model_v1.json', shulker_outputs)):
            spec = json.loads((ROOT / 'tools/data' / filename).read_text(encoding='utf8'))
            for field, value in (('game_version', 'NEMC future'), ('palette_sha256', '0' * 64)):
                with self.subTest(filename=filename, field=field):
                    changed = deepcopy(spec)
                    changed[field] = value
                    with self.assertRaisesRegex(ValueError, 'current block registry'):
                        generate(changed)


if __name__ == '__main__':
    unittest.main()
