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
from projection.render_context import (ContextPaletteBuilder, prepare_context_batches,
                                       prepare_context_palette)
from projection.render_layout import OVERLAY_BASE
from projection.static_table import TABLE_PROXY, table_proxy
from projection import static_table, static_table_data, book_qualification_data


class StaticTableTests(unittest.TestCase):
    @patch.object(static_table_data, 'PRODUCT_QUALIFIED', False)
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
    @patch.object(book_qualification_data, 'PRODUCT_QUALIFIED', False)
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

    @patch.object(static_table, 'CANDIDATE_ENABLED', True)
    def test_target_body_is_owned_once_outside_every_neighbor_context(self):
        table = ('minecraft:enchanting_table', 0)
        water = ('minecraft:water', 0)
        target = (16, 16, 16)
        support = (16, 15, 16)
        occupied_table = (17, 16, 16)
        doc = Document((32, 32, 32), {
            target: make_cell(table, water, {'id': 'EnchantTable'}),
            occupied_table: table, support: ('minecraft:stone', 0)})
        saved = copy.deepcopy(doc.to_data())
        targets = doc.palette_data(lambda pos: pos != occupied_table)
        source = doc.palette_data()
        reference = prepare_context_palette(source, targets)
        builder = ContextPaletteBuilder(doc, targets)
        for unused in builder.prepare():
            pass
        for prepared in (reference, builder.data):
            volume = prepared['volume']
            expected = ((target[1]+OVERLAY_BASE)*volume[1]+target[0])*volume[0]+target[2]
            self.assertEqual([expected], prepared['common'][(TABLE_PROXY, 0)])
            self.assertTrue(prepared['extra'][water])
            self.assertNotIn('minecraft:enchanting_table', prepared['actor'])
        batches = prepare_context_batches(doc, targets)['_context_batches']
        bodies = [(origin, packed, palette['common'][(TABLE_PROXY, 0)])
                  for origin, packed, palette in batches if (TABLE_PROXY, 0) in palette['common']]
        self.assertEqual([((16, 16, 16), False, [0])], bodies)
        contexts = [palette for origin, packed, palette in batches if packed]
        self.assertTrue(any(palette['extra'].get(water) or palette['common'].get(water)
                            for palette in contexts))
        self.assertTrue(any(('minecraft:stone', 0) in palette['common'] for palette in contexts))
        self.assertEqual(saved, doc.to_data())

    @patch.object(static_table, 'CANDIDATE_ENABLED', True)
    def test_occupied_body_cannot_enter_any_of_five_neighbor_target_tiles(self):
        table = (3, 3, 3)
        neighbors = ((3, 2, 3), (2, 3, 3), (4, 3, 3), (3, 3, 2), (3, 3, 4))
        doc = Document((7, 7, 7), dict([(table, ('minecraft:enchanting_table', 0))]+
            [(pos, ('minecraft:stone', 0)) for pos in neighbors]))
        targets = doc.palette_data(lambda pos: pos != table)
        builder = ContextPaletteBuilder(doc, targets)
        for unused in builder.prepare():
            pass
        palettes = [prepare_context_palette(doc.palette_data(), targets), builder.data]
        palettes += [palette for unused_origin, unused_packed, palette in
                     prepare_context_batches(doc, targets)['_context_batches']]
        for palette in palettes:
            self.assertNotIn((TABLE_PROXY, 0), palette['common'])
            self.assertTrue(palette['common'][('minecraft:stone', 0)])

    @patch.object(static_table_data, 'PRODUCT_QUALIFIED', False)
    def test_closed_candidate_does_not_change_any_context_routing(self):
        doc = Document((4, 4, 4), {(1, 1, 1): ('minecraft:enchanting_table', 0),
                                  (1, 0, 1): ('minecraft:stone', 0)})
        result = prepare_context_batches(doc, doc.palette_data())['_context_batches']
        self.assertEqual(1, len(result))
        self.assertTrue(result[0][1])
        self.assertIn(('minecraft:enchanting_table', 0), result[0][2]['common'])

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
        current = hashlib.sha256((ROOT / data_path).read_bytes()).hexdigest()
        if static_table_data.PRODUCT_QUALIFIED:
            admitted = json.loads((ROOT / 'docs/evidence/table-body-product-r20/qualification.json').read_bytes())
            self.assertEqual('product', admitted['stage'])
            self.assertTrue(admitted['product_qualified'])
            self.assertTrue(admitted['reviewed'])
            self.assertTrue(all(admitted['gates'].values()))
            self.assertEqual(current, admitted['qualified_sources']['body_files'][data_path])
            self.assertEqual(contract['output_sha256'][data_path],
                             admitted['source_before']['body_files'][data_path])
        else:
            self.assertEqual(current, contract['output_sha256'][data_path])


if __name__ == '__main__':
    unittest.main()
