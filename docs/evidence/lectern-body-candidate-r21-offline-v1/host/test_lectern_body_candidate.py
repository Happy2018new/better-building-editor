"""Offline candidate ownership checks; these do not qualify native pixels."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
CLONE = ROOT / '.runtime/projects/book-r20'
sys.path.insert(0, str(CLONE / 'behavior_pack/modern_projection'))
from projection import block_registry, lectern_body
from projection.book_profile import candidate_profile
from projection.book_render_plan import iter_render_steps
from projection.cell import AIR, actor_data, foreground, make_cell, rebase as rebase_cell
from projection.debug_item_blueprints import slot_document
from projection.geometry_palette import prepare_palette
from projection.model import Document
from projection.nbt_spatial import rebase
from projection.render_context import ContextPaletteBuilder, prepare_context_batches, prepare_context_palette
from projection.render_layout import CONTEXT_BASE, OVERLAY_BASE

LECTERN = ('minecraft:lectern', 1)
STONE = ('minecraft:stone', 0)
WATER = ('minecraft:water', 0)
DIRECTIONS = ((0, -1, 0), (0, 1, 0), (-1, 0, 0),
              (1, 0, 0), (0, 0, -1), (0, 0, 1))


def index(position, volume):
    x, y, z = position
    return (y * volume[1] + x) * volume[0] + z


def position(value, volume):
    return (value // volume[0] % volume[1],
            value // (volume[0] * volume[1]), value % volume[0])


def build(document, targets, route):
    if route == 'palette':
        return [(None, None, prepare_context_palette(document.palette_data(), targets))]
    if route == 'document':
        builder = ContextPaletteBuilder(document, targets)
        for unused in builder.prepare():
            pass
        return [(None, None, builder.data)]
    return prepare_context_batches(document, targets)['_context_batches']


def bodies(rows):
    records = []
    for origin, packed, palette in rows:
        for material, indices in palette['common'].items():
            if material[0] != LECTERN[0]:
                continue
            for value in indices:
                local = position(value, palette['volume'])
                if origin is None:
                    if local[1] >= CONTEXT_BASE:
                        raise AssertionError('Lectern leaked into packed context')
                    logical = (local[0], local[1] - OVERLAY_BASE, local[2])
                    delta = (0, OVERLAY_BASE, 0)
                else:
                    if packed:
                        raise AssertionError('Lectern leaked into packed context')
                    logical = tuple(origin[axis] + local[axis] for axis in range(3))
                    delta = tuple(-value for value in origin)
                actor = palette['actor'].get(LECTERN[0], {}).get(value)
                records.append((logical, material, actor, delta))
        context_actors = (origin is None or packed)
        if context_actors:
            for value in palette['actor'].get(LECTERN[0], {}):
                if origin is not None or position(value, palette['volume'])[1] >= CONTEXT_BASE:
                    raise AssertionError('Lectern actor leaked into packed context')
    return records


class LecternBodyCandidateTests(unittest.TestCase):
    ROUTES = ('palette', 'document', 'batch')

    def setUp(self):
        self.gate = patch.object(lectern_body, 'CANDIDATE_ENABLED', True)
        self.gate.start()
        self.addCleanup(self.gate.stop)

    def test_candidate_is_closed_and_keeps_both_powered_values_in_scope(self):
        with patch.object(lectern_body, 'CANDIDATE_ENABLED', False):
            self.assertFalse(any(lectern_body.independent_body(value) for value in lectern_body.MATERIALS))
            document = Document((4, 4, 4), {(1, 1, 1): make_cell(LECTERN, nbt={})})
            for route in self.ROUTES:
                rows = build(document, document.palette_data(), route)
                self.assertTrue(any(LECTERN in data['common'] for unused, unused2, data in rows))
        self.assertEqual({False, True}, {block_registry.states(value)['powered_bit']
                                       for value in lectern_body.MATERIALS})
        self.assertTrue(all(lectern_body.independent_body(value) for value in lectern_body.MATERIALS))
        self.assertFalse(lectern_body.independent_body(('minecraft:lectern', 999)))
        self.assertFalse(lectern_body.independent_body(('minecraft:oak_shelf', 0)))

    def test_all_native_states_preserve_identity_and_empty_actor_across_three_routes(self):
        for material in sorted(lectern_body.MATERIALS):
            for route in self.ROUTES:
                with self.subTest(material=material, route=route):
                    target = (16, 16, 16)
                    document = Document((32, 32, 32), {target: make_cell(material, nbt={})})
                    before = copy.deepcopy(document.to_data())
                    rows = build(document, document.palette_data(), route)
                    records = bodies(rows)
                    self.assertEqual(1, len(records))
                    self.assertEqual((target, material, {}), records[0][:3])
                    self.assertEqual(before, document.to_data())

    def test_present_lectern_cannot_leak_into_six_neighbor_target_tiles(self):
        center = (16, 16, 16)
        neighbors = [tuple(center[axis] + shift[axis] for axis in range(3))
                     for shift in DIRECTIONS]
        for wet in (False, True):
            cells = dict((target, STONE) for target in neighbors)
            cells[center] = make_cell(LECTERN, WATER if wet else AIR, {})
            document = Document((32, 32, 32), cells)
            source_before = copy.deepcopy(document.to_data())
            targets = document.palette_data(lambda pos: pos != center)
            targets_before = copy.deepcopy(targets)
            for route in self.ROUTES:
                with self.subTest(wet=wet, route=route):
                    rows = build(document, targets, route)
                    self.assertEqual([], bodies(rows))
                    self.assertTrue(any(STONE in palette['common'] for unused, unused2, palette in rows))
                    if wet:
                        self.assertTrue(any(WATER in palette['common'] or WATER in palette['extra']
                                            for unused, unused2, palette in rows))
            self.assertEqual(source_before, document.to_data())
            self.assertEqual(targets_before, targets)

    def test_missing_body_is_emitted_once_with_all_six_logical_neighbors(self):
        center = (16, 16, 16)
        neighbors = [tuple(center[axis] + shift[axis] for axis in range(3))
                     for shift in DIRECTIONS]
        cells = dict((target, STONE) for target in neighbors)
        actor = {'x': 16, 'y': 16, 'z': 16, 'opaque': {'x': 700, 'values': [1, 2]}}
        cells[center] = make_cell(LECTERN, WATER, actor)
        document = Document((32, 32, 32), cells)
        before = copy.deepcopy(document.to_data())
        for route in self.ROUTES:
            for center_only in (False, True):
                with self.subTest(route=route, center_only=center_only):
                    targets = document.palette_data(lambda pos: pos == center) if center_only else document.palette_data()
                    rows = build(document, targets, route)
                    self.assert_body_and_neighbors(rows, center, actor, center_only)
        self.assertEqual(before, document.to_data())

    def assert_body_and_neighbors(self, rows, center, actor, center_only):
        records = bodies(rows)
        self.assertEqual(1, len(records))
        logical, material, rendered_actor, delta = records[0]
        self.assertEqual(center, logical)
        self.assertEqual(LECTERN, material)
        self.assertEqual(rebase(actor, delta), rendered_actor)
        self.assertEqual(700, rendered_actor['opaque']['x'])
        self.assertTrue(any(WATER in palette['common'] or WATER in palette['extra']
                            for unused, unused2, palette in rows))
        self.assertTrue(any(STONE in palette['common'] for unused, unused2, palette in rows))
        if center_only:
            self.assertEqual(6, sum(len(palette['common'].get(STONE, ()))
                                    for unused, unused2, palette in rows))

    def test_support_occupancy_and_restoration_do_not_change_body_ownership(self):
        center, below = (16, 16, 16), (16, 15, 16)
        document = Document((32, 32, 32), {center: make_cell(LECTERN, nbt={}), below: STONE})
        before = copy.deepcopy(document.to_data())
        for route in self.ROUTES:
            sequence = []
            for visible in (lambda pos: True, lambda pos: pos == center,
                            lambda pos: pos == below, lambda pos: True):
                sequence.append(bodies(build(document, document.palette_data(visible), route)))
            self.assertEqual([1, 1, 0, 1], list(map(len, sequence)))
            self.assertEqual(sequence[0], sequence[-1])
        self.assertEqual(before, document.to_data())

    def test_logical_support_removal_and_restoration_leave_native_identity_intact(self):
        center, below = (16, 16, 16), (16, 15, 16)
        document = Document((32, 32, 32), {center: make_cell(LECTERN, nbt={}), below: STONE})
        original = copy.deepcopy(document.to_data())
        for route in self.ROUTES:
            complete = bodies(build(document, document.palette_data(), route))
            document.set_cell(below, AIR)
            unsupported = bodies(build(document, document.palette_data(), route))
            self.assertEqual(complete, unsupported)
            document.set_cell(below, STONE)
            self.assertEqual(complete, bodies(build(document, document.palette_data(), route)))
        self.assertEqual(original, document.to_data())

    def test_book_payload_stays_logical_while_body_keeps_render_actor_only(self):
        public = slot_document('lectern.book')
        source = rebase_cell(public.get((3, 3, 3)), (13, 13, 13))
        material = foreground(source)
        document = Document((32, 32, 32), {(16, 16, 16): source, (16, 15, 16): STONE})
        before = copy.deepcopy(document.to_data())
        profile = candidate_profile()
        for route in self.ROUTES:
            for selected, expected in ((None, 1), ((16, 15, 16), 0), ((16, 16, 16), 1)):
                with self.subTest(route=route, selected=selected):
                    targets = document.palette_data(None if selected is None else lambda pos: pos == selected)
                    rows = build(document, targets, route)
                    records = bodies(rows)
                    groups = [group for group in iter_render_steps(document, profile, targets) if group]
                    self.assertEqual(expected, len(records))
                    self.assertEqual(expected, len(groups))
                    if records:
                        self.assertEqual({}, records[0][2])
                        self.assertEqual(material, records[0][1])
        self.assertEqual(before, document.to_data())
        self.assertIsNotNone(actor_data(document.get((16, 16, 16))))
        logical = document.palette_data()
        prepared = prepare_palette(logical)
        self.assertIn(LECTERN[0], prepared['actor'])
        self.assertEqual(before, document.to_data())


if __name__ == '__main__':
    unittest.main(verbosity=2)
