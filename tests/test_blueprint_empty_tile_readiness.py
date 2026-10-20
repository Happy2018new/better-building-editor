"""Exercise the QA readiness snippet against real retained preview tiles."""
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack'))
from verify_debug_blueprints import STATUS, editor_preview_ready
from modern_projection.projection.cell import AIR, make_cell
from modern_projection.projection.debug_blueprints import build
from modern_projection.projection.debug_transform_acceptance import PREFIX, prepare
from modern_projection.projection.session import Session


class QueuedGeometryBridge:
    def __init__(self):
        self.queue = []

    def later(self, delay, callback):
        self.queue.append(callback)

    def geometry(self, palette, name=None, render_origin=(0, 0, 0)):
        return name

    def settle(self, session):
        for unused in range(10000):
            for part in session.tiles.parts.values():
                part['pending'] = False
            if not self.queue:
                return
            self.queue.pop(0)()
        raise AssertionError('Real tiled preview did not settle')


class EmptyTileReadinessTests(unittest.TestCase):
    def setUp(self):
        bridge = QueuedGeometryBridge()
        self.session = Session(bridge)
        self.session._loaded(build(PREFIX + 't01'))
        bridge.settle(self.session)
        prepare(self.session.editor, PREFIX + 't01')
        self.session.action(self.session.editor.run, 'rotate_y90')
        bridge.settle(self.session)
        self.session.page = 'workspace'
        self.session.tiles.renderer_active = True
        self.empty_key = (1, 0, 1)

    def status(self):
        session = self.session
        doc = session.editor.document
        session.tiles.last_render = time.time()
        metadata = {'name': doc.name, 'size': doc.size, 'blocks': len(doc.blocks)}
        probe = SimpleNamespace(
            _blueprint_qa_expected={'metadata': metadata, 'document_id': id(doc),
                                    'editor_id': id(session.editor)},
            _blueprint_qa_records=[], _blueprint_qa_nonce=1)
        scope = {'s': session, 'b': SimpleNamespace(model_layouts={}, projection_entities=[], entity=None),
                 'sys': probe, 'time': time, 'json': json}
        exec(compile(STATUS, '<real-session-qa-status>', 'exec'), scope)
        return json.loads(scope['_result'])

    def empty_row(self, state):
        return next(row for row in state['parts'] if tuple(row['key']) == self.empty_key)

    def ready(self, state):
        return editor_preview_ready(state, state['metadata'],
                                    id(self.session.editor), id(self.session.editor.document))

    def test_real_t01_rotation_retains_empty_tile_signature_without_retaining_a_mesh(self):
        state = self.status()
        row = self.empty_row(state)
        self.assertFalse(state['all_parts_current'])
        self.assertFalse(row['current_signature'])
        self.assertEqual(0, row['signature'][1])
        self.assertEqual(1, self.session.editor.revision)
        self.assertIsNone(row['name'])
        self.assertTrue(row['cache_current'])
        self.assertEqual([[16, 0, 16], [8, 10, 8]], row['source_region'])
        self.assertTrue(row['empty_source_current'])
        self.assertTrue(state['all_parts_ready'])
        self.assertTrue(self.ready(state))
        self.assertTrue(all(part['current_signature'] for part in state['parts'] if part['name']))

    def test_current_foreground_background_or_actor_cell_blocks_empty_cache_exemption(self):
        values = (('minecraft:stone', 0), make_cell(AIR, ('minecraft:water', 0)),
                  make_cell(('minecraft:chest', 2), nbt={'id': 'Chest', 'Items': []}))
        for value in values:
            with self.subTest(value=value):
                self.session.editor.document.blocks[(17, 0, 17)] = value
                self.assertIn((17, 0, 17), dict(self.session.editor.document.blocks.items()))
                state = self.status()
                self.assertFalse(self.empty_row(state)['empty_source_current'])
                self.assertFalse(state['all_parts_ready'])
                self.assertFalse(self.ready(state))

    def test_actual_region_bounds_are_used_instead_of_fixed_tile_bounds(self):
        tiles = self.session.tiles
        tiles.regions[self.empty_key] = (self.empty_key, (0, 0, 0), (24, 10, 24),
                                        (self.empty_key,))
        row = self.empty_row(self.status())
        self.assertEqual([[0, 0, 0], [24, 10, 24]], row['source_region'])
        self.assertFalse(row['ready'])

    def test_nonempty_stale_signature_is_always_rejected(self):
        part = self.session.tiles.parts[(0, 0, 0)]
        self.assertTrue(part['name'])
        part['signature'] = (part['signature'][0], 0) + part['signature'][2:]
        state = self.status()
        row = next(row for row in state['parts'] if row['name'])
        self.assertFalse(row['current_signature'])
        self.assertFalse(row['ready'])
        self.assertFalse(self.ready(state))

    def test_pending_invalid_cache_or_retained_name_blocks_empty_exemption(self):
        part = self.session.tiles.parts[self.empty_key]
        for field, value in (('pending', True), ('bank', 99), ('name', 'old_mesh'), ('count', 1)):
            with self.subTest(field=field):
                previous = part[field]
                part[field] = value
                state = self.status()
                self.assertFalse(self.empty_row(state)['ready'])
                self.assertFalse(self.ready(state))
                part[field] = previous

    def test_each_nonzero_layer_or_actor_count_blocks_empty_exemption(self):
        part = self.session.tiles.parts[self.empty_key]
        for layer in range(3):
            with self.subTest(layer=layer):
                previous = part['data']
                changed = list(previous)
                changed[layer] = {('minecraft:stone', 0): {0: {}} if layer == 2 else [0]}
                part['data'] = tuple(changed)
                part['cache'][part['bank']] = (part['data'], None, (part['source'],), 0)
                state = self.status()
                row = self.empty_row(state)
                self.assertTrue(row['cache_current'])
                self.assertFalse(row['ready'])
                part['data'] = previous
                part['cache'][part['bank']] = (previous, None, (part['source'],), 0)

    def test_global_busy_or_wrong_source_still_blocks_ready_empty_tile(self):
        state = self.status()
        for key, value in (('dirty', 1), ('running', True), ('preview_pending', True),
                           ('mounting', True), ('current_source', False),
                           ('model_revision_current', False)):
            with self.subTest(key=key):
                changed = dict(state, **{key: value})
                self.assertFalse(self.ready(changed))


if __name__ == '__main__':
    unittest.main()
