"""Technical block labels must not turn orientation aux into item variants."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.materials import DISPLAY_NAMES, display_name
from projection.model import Document


class BlockDisplayNameTests(unittest.TestCase):
    def test_reported_technical_ids_keep_chinese_labels_in_every_orientation(self):
        expected = {'minecraft:birch_double_slab': '双层白桦木台阶',
                    'minecraft:double_cut_copper_slab': '双层切制铜台阶',
                    'minecraft:bubble_coral_wall_fan': '气泡珊瑚扇'}
        for name, label in expected.items():
            for aux in registry.aux_values(name):
                with self.subTest(name=name, aux=aux):
                    self.assertEqual(label, display_name((name, aux)))

    def test_native_coral_direction_metadata_cannot_change_species_or_block_data(self):
        blocks = {(i, 0, 0): ('minecraft:bubble_coral_wall_fan', aux)
                  for i, aux in enumerate(registry.aux_values('minecraft:bubble_coral_wall_fan'))}
        document = Document((4, 1, 1), blocks)
        before = copy.deepcopy(document.to_data())
        for value in blocks.values():
            saved = DISPLAY_NAMES.get(value)
            # In 3.10, the item resolver can report fire/dead coral when the
            # block's facing index is mistakenly used as an inventory aux.
            try:
                DISPLAY_NAMES[value] = '火珊瑚扇'
                self.assertEqual('气泡珊瑚扇', display_name(value))
            finally:
                if saved is None:
                    DISPLAY_NAMES.pop(value, None)
                else:
                    DISPLAY_NAMES[value] = saved
        self.assertEqual(before, document.to_data())

    def test_legacy_identity_and_unrelated_custom_labels_keep_their_contract(self):
        self.assertEqual('双层白桦木台阶', display_name(('minecraft:double_wooden_slab', 2)))
        value = ('other:unusual_block', 7)
        try:
            DISPLAY_NAMES[value] = '自定义名称'
            self.assertEqual('自定义名称', display_name(value))
        finally:
            DISPLAY_NAMES.pop(value, None)


if __name__ == '__main__':
    unittest.main()
