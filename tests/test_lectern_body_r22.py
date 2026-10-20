"""Native lectern bodies own their overhang; book data stays logical."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection import block_registry, lectern_body
from projection.book_profile import production_profile
from projection.book_render_plan import iter_render_steps
from projection.cell import AIR, make_cell, rebase as rebase_cell
from projection.debug_item_blueprints import slot_document
from projection.model import Document
from projection.nbt_spatial import rebase
from projection.render_context import (ContextPaletteBuilder,
    prepare_context_batches, prepare_context_palette)
from projection.render_layout import CONTEXT_BASE, OVERLAY_BASE
from unittest.mock import patch
import test_book_owner

LECTERN = ('minecraft:lectern', 2)
STONE = ('minecraft:stone', 0)
WATER = ('minecraft:water', 0)
CENTER = (16, 16, 16)
NEIGHBORS = tuple(tuple(CENTER[i] + delta[i] for i in range(3))
                  for delta in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                                (0, -1, 0), (0, 0, 1), (0, 0, -1)))


def build(document, targets, route, visible_layer=None):
    if route == 'palette':
        return [(None, None, prepare_context_palette(document.palette_data(), targets))]
    if route == 'document':
        builder = ContextPaletteBuilder(document, targets, visible_layer=visible_layer)
        list(builder.prepare())
        return [(None, None, builder.data)]
    return prepare_context_batches(document, targets, visible_layer=visible_layer)['_context_batches']


def bodies(rows):
    result = []
    for origin, packed, palette in rows:
        for material, indices in palette['common'].items():
            if material[0] != 'minecraft:lectern':
                continue
            for index in indices:
                zsize, xsize, unused = palette['volume']
                local = (index // zsize % xsize, index // (zsize*xsize), index % zsize)
                if origin is None:
                    assert local[1] < CONTEXT_BASE, 'Lectern leaked into packed context'
                    logical = (local[0], local[1]-OVERLAY_BASE, local[2])
                    delta = (0, OVERLAY_BASE, 0)
                else:
                    assert not packed, 'Lectern leaked into packed context'
                    logical = tuple(origin[i]+local[i] for i in range(3))
                    delta = tuple(-value for value in origin)
                actor = palette['actor'].get('minecraft:lectern', {}).get(index)
                result.append((logical, material, actor, delta))
        if packed:
            assert not palette['actor'].get('minecraft:lectern'), 'Actor leaked into neighbor tile'
    return result


class LecternBodyDefaultTests(unittest.TestCase):
    ROUTES = ('palette', 'document', 'batch')

    def test_default_preserves_registry_identity_including_powered_metadata(self):
        self.assertEqual({False, True}, {block_registry.states(value)['powered_bit']
                                       for value in lectern_body.MATERIALS})
        self.assertFalse(lectern_body.independent_body(('minecraft:lectern', 999)))
        self.assertFalse(lectern_body.independent_body(STONE))
        for material in lectern_body.MATERIALS:
            document = Document((32, 32, 32), {CENTER: make_cell(material, nbt={})})
            for route in self.ROUTES:
                with self.subTest(material=material, route=route):
                    records = bodies(build(document, document.palette_data(), route))
                    self.assertEqual(1, len(records))
                    self.assertEqual((CENTER, material, {}), records[0][:3])

    def test_body_is_selected_once_and_does_not_leak_to_six_neighbor_targets(self):
        for wet in (False, True):
            cells = dict.fromkeys(NEIGHBORS, STONE)
            cells[CENTER] = make_cell(LECTERN, WATER if wet else AIR, {})
            document = Document((32, 32, 32), cells)
            before = copy.deepcopy(document.to_data())
            for route in self.ROUTES:
                selected = build(document, document.palette_data(), route)
                self.assertEqual(1, len(bodies(selected)))
                present = build(document, document.palette_data(lambda p: p != CENTER), route)
                self.assertEqual([], bodies(present))
                if wet:
                    self.assertTrue(any(WATER in palette['extra'] or WATER in palette['common']
                                        for unused, unused2, palette in present))
            self.assertEqual(before, document.to_data())

    def test_render_actor_rebases_with_body_and_leaves_opaque_nested_values(self):
        actor = {'x': 16, 'y': 16, 'z': 16, 'opaque': {'x': 700, 'values': [1, 2]}}
        document = Document((32, 32, 32), {CENTER: make_cell(LECTERN, WATER, actor)})
        before = copy.deepcopy(document.to_data())
        for route in self.ROUTES:
            record = bodies(build(document, document.palette_data(), route))[0]
            self.assertEqual(rebase(actor, record[3]), record[2])
            self.assertEqual(700, record[2]['opaque']['x'])
        self.assertEqual(before, document.to_data())

    def test_default_book_and_native_body_share_only_selected_logical_targets(self):
        source = slot_document('lectern.book').get((3, 3, 3))
        source = rebase_cell(source, (13, 13, 13))
        document = Document((32, 32, 32), {CENTER: source, (16, 15, 16): STONE})
        before = copy.deepcopy(document.to_data())
        profile = production_profile('3.10.0.420447')
        self.assertIsNotNone(profile)
        for route in self.ROUTES:
            for select, count in ((lambda p: True, 1), (lambda p: p == CENTER, 1),
                                  (lambda p: p != CENTER, 0)):
                targets = document.palette_data(select)
                records = bodies(build(document, targets, route))
                groups = [group for group in iter_render_steps(document, profile, targets) if group]
                self.assertEqual(count, len(records))
                self.assertEqual(count, len(groups))
                if count:
                    self.assertEqual({}, records[0][2])
        self.assertEqual(before, document.to_data())

    def test_hidden_layer_removes_body_and_its_native_actor_from_neighbor_context(self):
        document = Document((32, 32, 32), {CENTER: make_cell(LECTERN, nbt={}),
                                          (16, 15, 16): STONE, (16, 17, 16): STONE})
        for route in ('document', 'batch'):
            for hidden, count in ((False, 1), (True, 0), (False, 1)):
                targets = document.palette_data(lambda p: not hidden or p[1] != 16)
                rows = build(document, targets, route, lambda y: not hidden or y != 16)
                self.assertEqual(count, len(bodies(rows)))
                self.assertTrue(any(STONE in palette['common'] for unused, unused2, palette in rows))

    def test_existing_table_body_keeps_actor_suppressed_and_one_logical_book(self):
        from projection.static_table import TABLE_PROXY
        actor = {'id': {'__type__': 8, '__value__': 'EnchantTable'}}
        document = Document((32, 32, 32), {
            CENTER: make_cell(('minecraft:enchanting_table', 0), nbt=actor),
            (16, 15, 16): STONE})
        before = copy.deepcopy(document.to_data())
        for route in self.ROUTES:
            rows = build(document, document.palette_data(), route)
            self.assertEqual(1, sum(len(palette['common'].get((TABLE_PROXY, 0), ()))
                                    for unused, unused2, palette in rows))
            self.assertTrue(all(not palette['actor'] for unused, unused2, palette in rows))
            groups = [value for value in iter_render_steps(document,
                production_profile('3.10.0.420447'), document.palette_data()) if value]
            self.assertEqual(1, len(groups))
        self.assertEqual(before, document.to_data())


class LecternWorldDefaultTests(unittest.TestCase):
    def setUp(self):
        test_book_owner.BookWorldIntegrationTests.setUp(self)
        self.bridge.session.portal_profile = None
        self.bridge.session.book_profile = production_profile('3.10.0.420447')
        source = slot_document('lectern.book').get((3, 3, 3))
        self.document = Document((3, 3, 3), {
            (1, 1, 1): rebase_cell(source, (-2, -2, -2)), (1, 0, 1): STONE})
        from projection.model import Editor
        self.bridge.session.editor = Editor(self.document)
        self.prepared = None

        def geometry(document, visible=None, name=None, prepared=None, **kwargs):
            if prepared is not None:
                self.prepared = copy.deepcopy(prepared)
            return name or 'native_lectern'
        self.bridge.geometry = geometry

    def tearDown(self):
        test_book_owner.BookWorldIntegrationTests.tearDown(self)

    def drain(self):
        test_book_owner.BookWorldIntegrationTests.drain(self)

    def assert_owners(self, expected):
        self.assertTrue(self.bridge.projection_work.ready, self.bridge.projection_work.error)
        self.assertEqual(expected, len(bodies(self.prepared['_context_batches'])))
        book = self.bridge.projection_liquid
        self.assertEqual('BookProjection', type(book).__name__)
        self.assertEqual(expected, len(book.renderer.active))

    def test_public_full_missing_and_initial_occupancy_keep_body_and_book_paired(self):
        before = copy.deepcopy(self.document.to_data())
        origin = (10, 64, 20)
        for missing, present, expected in ((False, False, 1), (True, False, 1),
                                           (True, True, 0)):
            self.bridge.session.projection_missing = missing
            if present:
                self.runtime.world[(11, 65, 21)] = self.document.get_layer((1, 1, 1), 0)
            self.bridge.project_large(origin)
            self.drain()
            self.assert_owners(expected)
            self.bridge.stop_projection()
            self.drain()
        self.assertEqual(before, self.document.to_data())

    def test_public_hidden_and_shown_preserve_lower_support_and_full_logical_nbt(self):
        before = copy.deepcopy(self.document.to_data())
        for hidden, expected in (((1,), 0), ((), 1)):
            with patch.object(self.bridge.session, 'preview_hidden', return_value=hidden):
                self.bridge.session.projection_missing = False
                self.bridge.project_large((10, 64, 20))
                self.drain()
                self.assert_owners(expected)
                self.assertTrue(any(STONE in palette['common'] for unused, unused2, palette
                                    in self.prepared['_context_batches']))
                self.bridge.stop_projection()
                self.drain()
        self.assertEqual(before, self.document.to_data())


if __name__ == '__main__':
    unittest.main()
