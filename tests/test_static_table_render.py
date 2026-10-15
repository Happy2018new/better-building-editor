"""Table body routing must never alter blueprint layers or saved actor data."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.cell import make_cell
from projection.entity_render import static_proxy
from projection.geometry_palette import INTERNAL_RENDER_BLOCKS, prepare_palette
from projection.model import Document
from projection.render_context import prepare_context_palette
from projection.static_table import TABLE_PROXY, table_proxy
from projection import static_table, static_table_data, book_qualification_data


class StaticTableTests(unittest.TestCase):
    def test_default_gate_preserves_native_identity_layers_and_actor(self):
        self.assertIs(static_table_data.PRODUCT_QUALIFIED, False)
        self.assertIs(static_table.CANDIDATE_ENABLED, False)
        actor = {'id': 'EnchantTable', 'custom': {'future': [1, 2, 3]}}
        doc = Document((4, 4, 4), {
            (1, 1, 1): make_cell(('minecraft:enchanting_table', 0),
                                  ('minecraft:water', 0), actor)})
        saved = copy.deepcopy(doc.to_data())
        source = doc.palette_data()
        for prepared in (prepare_palette(source), prepare_context_palette(source, source)):
            self.assertIn(('minecraft:enchanting_table', 0), prepared['common'])
            self.assertNotIn((TABLE_PROXY, 0), prepared['common'])
            self.assertIn('minecraft:enchanting_table', prepared['actor'])
            self.assertTrue(prepared['extra'])
        self.assertEqual(saved, doc.to_data())
        with patch.object(book_qualification_data, 'PRODUCT_QUALIFIED', True):
            self.assertIsNone(table_proxy(('minecraft:enchanting_table', 0)))
        with patch.object(static_table_data, 'PALETTE_SHA256', 'stale'):
            self.assertIsNone(table_proxy(('minecraft:enchanting_table', 0)))

    @patch.object(static_table_data, 'PRODUCT_QUALIFIED', True)
    def test_independent_body_gate_can_select_the_proxy(self):
        self.assertIs(book_qualification_data.PRODUCT_QUALIFIED, False)
        self.assertEqual((TABLE_PROXY, 0), table_proxy(('minecraft:enchanting_table', 0)))

    @patch.object(static_table, 'CANDIDATE_ENABLED', True)
    def test_palette_and_missing_context_preserve_logical_layers_and_actor(self):
        actor = {'id': 'EnchantTable', 'custom': {'future': [1, 2, 3]}}
        doc = Document((4, 4, 4), {
            (1, 1, 1): make_cell(('minecraft:enchanting_table', 0),
                                  ('minecraft:water', 0), actor),
            (1, 0, 1): ('minecraft:cyan_concrete', 0)})
        saved = copy.deepcopy(doc.to_data())
        source = doc.palette_data()
        snapshot = copy.deepcopy(source)
        prepared = prepare_palette(source)
        self.assertIn((TABLE_PROXY, 0), prepared['common'])
        self.assertNotIn(('minecraft:enchanting_table', 0), prepared['common'])
        self.assertNotIn('minecraft:enchanting_table', prepared['actor'])
        self.assertEqual(source['extra'], prepared['extra'])
        targets = copy.deepcopy(source)
        targets['common'] = {('minecraft:enchanting_table', 0):
                             source['common'][('minecraft:enchanting_table', 0)]}
        targets['extra'] = {}
        context = prepare_context_palette(source, targets)
        self.assertIn((TABLE_PROXY, 0), context['common'])
        self.assertNotIn('minecraft:enchanting_table', context['actor'])
        self.assertEqual(snapshot, source)
        self.assertEqual(saved, doc.to_data())
        self.assertNotIn('preview_enchanting', json.dumps(doc.to_data()))

    @patch.object(static_table, 'CANDIDATE_ENABLED', True)
    def test_unknown_state_retains_native_identity_and_bad_candidate_source_is_rejected(self):
        self.assertEqual((TABLE_PROXY, 0), static_proxy(('minecraft:enchanting_table', 0), None))
        self.assertIsNone(table_proxy(('minecraft:enchanting_table', 1)))
        self.assertIsNone(table_proxy(('custom:enchanting_table', 0)))
        with patch.object(static_table_data, 'PALETTE_SHA256', 'stale'):
            with self.assertRaisesRegex(ValueError, 'sources differ'):
                table_proxy(('minecraft:enchanting_table', 0))
            self.assertIsNone(table_proxy(('minecraft:stone', 0)))

    def test_internal_proxy_is_hidden_and_does_not_extend_below_logical_cell(self):
        self.assertIn(TABLE_PROXY, INTERNAL_RENDER_BLOCKS)
        block = json.loads((ROOT / 'behavior_pack/netease_blocks/preview_enchanting_body.json').read_bytes())
        self.assertFalse(block['minecraft:block']['description']['register_to_creative_menu'])
        model = json.loads((ROOT / 'resource_pack/models/netease_block/preview_enchanting_body.json').read_bytes())
        cube = model['netease:block_geometry']['bones'][0]['cubes'][0]
        self.assertEqual(0, cube['origin'][1])
        self.assertEqual(12, cube['size'][1])
        self.assertEqual({'up', 'down', 'north', 'south', 'east', 'west'}, set(cube['uv']))
        contract = json.loads((ROOT / 'tools/data/enchanting_body_candidate_r17.json').read_bytes())
        self.assertFalse(contract['product_qualified'])
        data_path = 'behavior_pack/modern_projection/projection/static_table_data.py'
        self.assertEqual(hashlib.sha256((ROOT / data_path).read_bytes()).hexdigest(),
                         contract['output_sha256'][data_path])


if __name__ == '__main__':
    unittest.main()
