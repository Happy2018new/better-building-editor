"""The public peony gallery retains native typed halves and isolated controls."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.cell import AIR, actor_data, background, foreground
from projection.debug_blueprints import BLUEPRINTS, build, entries
from projection.debug_ordinary_plant_blueprints import PEONY_CASES, PEONY_METADATA
from projection.geometry_palette import prepare_palette
from projection.model import Document
from projection.render_context import prepare_context_batches
from projection.sharing_codec import decode_steps, encode_steps


class PeonyBlueprintTests(unittest.TestCase):
    def test_distinct_registry_entry_and_sparse_bounded_composition(self):
        identity, category, unused_title, size, icon = PEONY_METADATA
        self.assertEqual('test.blocks.peony_visibility', identity)
        self.assertEqual('registry', category)
        self.assertEqual((16, 6, 8), size)
        self.assertEqual('minecraft:peony', icon)
        self.assertEqual(1, sum(row[0] == identity for row in BLUEPRINTS))
        self.assertIn(PEONY_METADATA, entries('registry'))
        document = build(identity)
        self.assertEqual(size, document.size)
        self.assertEqual(7, len(document.blocks))
        for position, value in document.blocks.items():
            self.assertTrue(all(1 <= position[axis] < size[axis] - 1 for axis in range(3)))
            self.assertEqual(AIR, background(value))
            self.assertIsNone(actor_data(value))
            self.assertTrue(foreground(value)[0].startswith('minecraft:'))
        self.assertEqual(3, sum(foreground(v)[0] == 'minecraft:stone'
                                for v in document.blocks.values()))

    def test_complete_pair_and_isolated_halves_keep_legal_typed_native_states(self):
        document = build(PEONY_METADATA[0])
        expected = {(3, 2, 3): False, (3, 3, 3): True,
                    (8, 2, 3): False, (12, 3, 3): True}
        actual = {pos: foreground(value) for pos, value in document.blocks.items()
                  if foreground(value)[0] == 'minecraft:peony'}
        self.assertEqual(set(expected), set(actual))
        for position, upper in expected.items():
            value = actual[position]
            self.assertEqual(('minecraft:peony', int(upper)), value)
            state = registry.states(value)
            self.assertEqual({'upper_block_bit': upper}, state)
            self.assertIs(type(state['upper_block_bit']), bool)
            self.assertIs(state['upper_block_bit'], upper)
            self.assertEqual(value, registry.from_states(value[0], state))
        self.assertEqual(AIR, document.get((8, 3, 3)))
        self.assertEqual(AIR, document.get((12, 2, 3)))
        self.assertEqual(('complete_pair', 'isolated_lower', 'isolated_upper'),
                         tuple(row[0] for row in PEONY_CASES))

    def test_serialized_and_shared_documents_preserve_orphans_without_repair(self):
        document = build(PEONY_METADATA[0])
        saved = deepcopy(document.to_data())
        native = Document.from_data(json.loads(json.dumps(saved)))
        shared = list(decode_steps(list(encode_steps(document))[-1]['text']))[-1]['document']
        for restored in (native, shared, build(PEONY_METADATA[0])):
            self.assertEqual(document.blocks, restored.blocks)
            self.assertEqual(document.size, restored.size)
            self.assertEqual(AIR, restored.get((8, 3, 3)))
            self.assertEqual(AIR, restored.get((12, 2, 3)))
        self.assertEqual(saved, document.to_data())

    def test_native_document_survives_full_and_missing_render_preparation(self):
        document = build(PEONY_METADATA[0])
        saved = deepcopy(document.to_data())
        prepared = prepare_palette(document.palette_data())
        counts = {value[0]: len(positions) for value, positions in prepared['common'].items()}
        self.assertEqual({'minecraft:stone': 3,
                          'modern_projection:ordinary_peony_bottom': 2,
                          'modern_projection:ordinary_peony_top': 2}, counts)
        targets = document.palette_data(lambda pos: pos in ((3, 2, 3), (12, 3, 3)))
        result = prepare_context_batches(document, targets)
        self.assertTrue(result['_context_batches'])
        self.assertEqual(saved, document.to_data())

    def test_historical_two_gallery_ids_sizes_and_contents_remain_intact(self):
        ordinary = build('test.blocks.ordinary_plant_visibility')
        corals = build('test.blocks.coral_plant_visibility')
        self.assertEqual((16, 5, 8), ordinary.size)
        self.assertEqual(8, len(ordinary.blocks))
        self.assertEqual((18, 5, 11), corals.size)
        self.assertEqual(20, len(corals.blocks))
        self.assertNotIn('minecraft:peony', {foreground(v)[0] for d in (ordinary, corals)
                                           for v in d.blocks.values()})


if __name__ == '__main__':
    unittest.main()
