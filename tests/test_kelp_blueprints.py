# -*- coding: utf-8 -*-
"""The public kelp card preserves native source identity and full-source parts."""
import copy
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'behavior_pack', 'modern_projection'))
from projection import block_registry as registry
from projection.cell import AIR, actor_data, background, foreground
from projection.debug_blueprints import BLUEPRINTS, build, entries
from projection.debug_ordinary_plant_blueprints import KELP_CASES, KELP_METADATA
from projection.kelp_render import PROXIES, document_part
from projection.model import Document, Editor
from projection.render_context import ContextPaletteBuilder
from projection.sharing_codec import decode_steps, encode_steps


class KelpBlueprintTests(unittest.TestCase):
    def test_reachable_sparse_native_card_and_typed_age_controls(self):
        self.assertEqual('test.blocks.kelp_visibility', KELP_METADATA[0])
        self.assertEqual('registry', KELP_METADATA[1])
        self.assertIn(KELP_METADATA, entries('registry'))
        self.assertEqual(1, sum(row[0] == KELP_METADATA[0] for row in BLUEPRINTS))
        document = build(KELP_METADATA[0])
        self.assertEqual((16, 18, 8), document.size)
        self.assertEqual(8, len(document.blocks))
        expected = dict((pos, age) for unused, unused_support, chain in KELP_CASES for pos, age in chain)
        self.assertEqual({(3, 2, 3): 0, (3, 3, 3): 0, (8, 2, 3): 25,
                          (12, 15, 3): 0, (12, 16, 3): 0}, expected)
        self.assertEqual(3, sum(foreground(cell)[0] == 'minecraft:stone'
                                for cell in document.blocks.values()))
        for position, value in document.blocks.items():
            self.assertTrue(all(1 <= position[axis] < document.size[axis] - 1 for axis in range(3)))
            self.assertTrue(foreground(value)[0].startswith('minecraft:'))
            self.assertEqual(AIR, background(value))
            self.assertIsNone(actor_data(value))
        for position, age in expected.items():
            value = foreground(document.get(position))
            self.assertEqual(('minecraft:kelp', age), value)
            state = registry.states(value)
            self.assertEqual({'kelp_age': age}, state)
            self.assertIs(type(state['kelp_age']), int)

    def test_full_and_missing_preparation_keep_source_neighbor_parts(self):
        document = build(KELP_METADATA[0])
        before = copy.deepcopy(document.to_data())
        expected = {(3, 2, 3): 'stem', (3, 3, 3): 'top', (8, 2, 3): 'top',
                    (12, 15, 3): 'stem', (12, 16, 3): 'top'}
        builder = ContextPaletteBuilder(document, document.palette_data())
        for position, part in expected.items():
            self.assertEqual(part, document_part(document, position))
            self.assertEqual((PROXIES[part], 0), builder.material(*position)[0]['common'])
        lower_positions = ((3, 2, 3), (12, 15, 3))
        targets = document.palette_data(lambda position: position in lower_positions)
        missing = ContextPaletteBuilder(document, targets)
        for position in lower_positions:
            self.assertEqual((PROXIES['stem'], 0), missing.material(*position)[0]['common'])
        for unused in missing.prepare():
            pass
        self.assertTrue(missing.data)
        self.assertEqual(before, document.to_data())

    def test_native_save_share_and_independent_opens_preserve_cross_chunk_column(self):
        document = build(KELP_METADATA[0])
        saved = copy.deepcopy(document.to_data())
        local = Document.from_data(json.loads(json.dumps(saved)))
        shared = list(decode_steps(list(encode_steps(document))[-1]['text']))[-1]['document']
        for restored in (local, shared, build(KELP_METADATA[0])):
            self.assertEqual(document.blocks, restored.blocks)
            self.assertEqual(document.size, restored.size)
            self.assertIsNot(document.blocks, restored.blocks)
            self.assertEqual('stem', document_part(restored, (12, 15, 3)))
            self.assertEqual('top', document_part(restored, (12, 16, 3)))
        self.assertEqual(saved, document.to_data())

    def test_native_editor_cross_chunk_delete_and_undo(self):
        document = build(KELP_METADATA[0])
        original = document.blocks.copy()
        editor = Editor(document)
        self.assertEqual(1, editor._commit('remove upper kelp', {(12, 16, 3): AIR}, whole=True))
        self.assertEqual(AIR, document.get((12, 16, 3)))
        self.assertEqual('top', document_part(document, (12, 15, 3)))
        self.assertTrue(editor.undo())
        self.assertEqual(original, document.blocks)
        self.assertEqual('stem', document_part(document, (12, 15, 3)))
        self.assertEqual('top', document_part(document, (12, 16, 3)))

    def test_existing_plant_galleries_keep_sizes_and_contents(self):
        expected = (('test.blocks.ordinary_plant_visibility', (16, 5, 8), 8),
                    ('test.blocks.coral_plant_visibility', (18, 5, 11), 20),
                    ('test.blocks.peony_visibility', (16, 6, 8), 7))
        for identity, size, count in expected:
            document = build(identity)
            self.assertEqual(size, document.size)
            self.assertEqual(count, len(document.blocks))
            self.assertNotIn('minecraft:kelp', set(foreground(cell)[0]
                                                  for cell in document.blocks.values()))


if __name__ == '__main__':
    unittest.main()
