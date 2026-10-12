"""Composed host workflows retain complete cells across editor and storage APIs."""
import base64
import copy
import json
import struct
import sys
import unittest
import zlib
from collections import Counter, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.cell import actor_data, background, foreground, make_cell
from projection.debug_blueprints import material
from projection.model import AIR, Document, Editor
from projection.session import Session
from projection.sharing_codec import split_text
from projection.visible_actor import entity_nbt


SIZES = ((32, 32, 32), (64, 128, 64))


class WorkflowBridge:
    """Config/clipboard boundary with real serialization and queued callbacks."""
    def __init__(self):
        self.queue = deque()
        self.index = None
        self.pages = {}
        self.preferences = None
        self.clipboard = ''
        self.fail_index = False

    def later(self, delay, callback):
        self.queue.append(callback)

    def geometry(self, document, *args, **kwargs):
        # Host data tests acknowledge preview uploads without a game renderer.
        return kwargs.get('name', 'host_workflow_preview')

    def player_origin(self):
        return (100, 64, -100)

    def save_library(self, data):
        if self.fail_index:
            return False
        self.index = json.loads(json.dumps(data))
        return True

    def load_library(self):
        return copy.deepcopy(self.index)

    def save_archive_page(self, identity, page, data):
        self.pages[identity, page] = json.loads(json.dumps(data))
        return True

    def load_archive_page(self, identity, page):
        return copy.deepcopy(self.pages.get((identity, page)))

    def save_preferences(self, data):
        self.preferences = json.loads(json.dumps(data))
        return True

    def load_preferences(self):
        return copy.deepcopy(self.preferences)

    def set_clipboard(self, text):
        self.clipboard = text
        return True

    def get_clipboard(self):
        return self.clipboard

    def settle(self):
        for unused in range(10000):
            if not self.queue:
                return
            self.queue.popleft()()
        raise AssertionError('host workflow callbacks did not settle')


def inventory_actor(pos, marker='original'):
    return {'__type__': 'TAG_Compound', '__value__': {
        'id': {'__type__': 8, '__value__': 'Chest'},
        'x': {'__type__': 3, '__value__': pos[0]},
        'y': {'__type__': 3, '__value__': pos[1]},
        'z': {'__type__': 3, '__value__': pos[2]},
        'Items': [{'Name': {'__type__': 8, '__value__': 'minecraft:diamond'},
                   'Count': {'__type__': 1, '__value__': 7},
                   'tag': {'x': 900, 'y': 901, 'z': 902,
                           'pairx': 903, 'pairz': 904, 'marker': marker}}],
        'future_data': {'binary': b'\x00\xff', 'tuple': (True, 1 << 40),
                        'nested': [{'x': -123, 'y': 999, 'z': 321}]},
        'facingDirection': {'__type__': 3, '__value__': 2},
    }}


def selection_state(editor):
    return set(editor.selection), editor.start, editor.end


def box(lo, hi):
    return {(x, y, z) for x in range(lo[0], hi[0] + 1)
            for y in range(lo[1], hi[1] + 1) for z in range(lo[2], hi[2] + 1)}


def legacy_fixture(size, rich):
    """Old readers receive literal wire rows, never a current writer's output."""
    actor = {'__type__': 10, '__value__': {
        'id': 'Chest', 'x': 16, 'y': 16, 'z': 16,
        'Items': [{'tag': {'x': 900}}], 'future': (b'\x00\xff', True, 1 << 40)}}
    actor_tree = ['dict', [
        [['text', '__type__'], ['int', '10']],
        [['text', '__value__'], ['dict', [
            [['text', 'id'], ['text', 'Chest']],
            [['text', 'x'], ['int', '16']],
            [['text', 'y'], ['int', '16']],
            [['text', 'z'], ['int', '16']],
            [['text', 'Items'], ['list', [
                ['dict', [[['text', 'tag'], ['dict', [
                    [['text', 'x'], ['int', '900']]]]]]]]]],
            [['text', 'future'], ['tuple', [
                ['bytes', 'AP8='], ['bool', True], ['int', '1099511627776']]]],
        ]]],
    ]]
    if rich:
        palette = [['minecraft:air', 0],
                   [['minecraft:oak_fence', 0], ['minecraft:water', 0], ['null']],
                   [['minecraft:chest', 0], ['minecraft:water', 0], actor_tree]]
        expected = {(15, 15, 15): make_cell(('minecraft:oak_fence', 0), ('minecraft:water', 0)),
                    (16, 16, 16): make_cell(('minecraft:chest', 0), ('minecraft:water', 0), actor)}
    else:
        palette = [['minecraft:air', 0], ['minecraft:stone', 0], ['minecraft:glass', 0]]
        expected = {(15, 15, 15): ('minecraft:stone', 0), (16, 16, 16): ('minecraft:glass', 0)}
    chunks = []
    for key, slot, identity in (((0, 0, 0), 4095, 1), ((1, 1, 1), 0, 2)):
        values = [0] * 4096
        values[slot] = identity
        payload = base64.b64encode(zlib.compress(struct.pack('<4096H', *values))).decode('ascii')
        chunks.append(list(key) + [payload])
    data = {'version': 4 if rich else 2, 'name': 'legacy workflow', 'size': list(size),
            'biome': 'roofed_forest', 'blockCount': 2, 'palette': palette, 'chunks': chunks}
    packets = [
        {'seq': 0, 'kind': 'begin', 'version': 3 if rich else 2,
         'name': data['name'], 'size': list(size), 'biome': data['biome'],
         'paletteCount': 3, 'chunkCount': 2, 'blockCount': 2},
        {'seq': 1, 'kind': 'palette', 'rows': palette},
        {'seq': 2, 'kind': 'chunks', 'rows': chunks},
        {'seq': 3, 'kind': 'end'},
    ]
    return data, expected, packets


class CompleteCellWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fence = material('oak_fence')
        cls.water = material('water')
        cls.snow = material('snow_layer', {'height': 4, 'covered_bit': True})
        cls.fern = material('fern')
        cls.stone = material('stone')
        cls.chests = {direction: material('chest', {'minecraft:cardinal_direction': direction})
                      for direction in ('north', 'east', 'west')}

    def cells_at(self, positions, direction='north'):
        fence, snow, chest, water, stone = positions
        return {fence: make_cell(self.fence, self.water),
                snow: make_cell(self.snow, self.fern),
                chest: make_cell(self.chests[direction], self.water, inventory_actor(chest)),
                water: make_cell(AIR, self.water), stone: self.stone}

    def assert_cells(self, document, expected):
        self.assertEqual(set(expected), set(document.blocks))
        for pos, value in expected.items():
            with self.subTest(cell=pos):
                actual = document.get(pos)
                self.assertEqual(foreground(value), foreground(actual))
                self.assertEqual(background(value), background(actual))
                expected_actor = actor_data(value)
                actual_actor = actor_data(actual)
                # Chest connection rendering metadata is derived by reconciliation.
                self.assertEqual(entity_nbt(expected_actor) or expected_actor,
                                 entity_nbt(actual_actor) or actual_actor)
        materials = Counter(part for value in expected.values()
                            for part in (foreground(value), background(value)) if part != AIR)
        self.assertEqual(materials, Counter(dict(document.materials())))
        occupied_layers = Counter(pos[1] for pos in expected)
        for y in range(document.size[1]):
            self.assertEqual(occupied_layers[y], document.layer_count(y))

    def run_tool(self, session, tool, origin=None):
        session.choose_tool(tool)
        if origin is not None:
            session.set_paste_origin(origin)
        result = session.run()
        self.assertIsNot(result, False, session.editor.message)
        job = session.edit_job
        session.bridge.settle()
        if job is not None:
            self.assertFalse(job.error, job.error)
        self.assertIsNone(session.edit_job)
        self.assertIsNone(session.io_job)

    def assert_history(self, editor, before, after, before_selection, after_selection):
        self.assertTrue(editor.undo())
        self.assert_cells(editor.document, before)
        self.assertEqual(before_selection, selection_state(editor))
        self.assertTrue(editor.redo())
        self.assert_cells(editor.document, after)
        self.assertEqual(after_selection, selection_state(editor))

    def test_layered_patch_survives_transform_cut_restart_and_segmented_share(self):
        original_positions = ((14, 15, 14), (16, 15, 14), (15, 16, 16),
                              (16, 16, 15), (14, 16, 16))
        # Literal destinations form an oracle independent of transform/rebase code.
        stages = (
            ('paste', (8, 15, 22), 'north',
             ((8, 15, 22), (10, 15, 22), (9, 16, 24), (10, 16, 23), (8, 16, 24)),
             (8, 15, 22), (10, 16, 24)),
            ('rotate_y90', None, 'east',
             ((10, 15, 22), (10, 15, 24), (8, 16, 23), (9, 16, 24), (8, 16, 22)),
             (8, 15, 22), (10, 16, 24)),
            ('mirror_x', None, 'west',
             ((8, 15, 22), (8, 15, 24), (10, 16, 23), (9, 16, 24), (10, 16, 22)),
             (8, 15, 22), (10, 16, 24)),
            ('move_xp', None, 'west',
             ((15, 15, 22), (15, 15, 24), (17, 16, 23), (16, 16, 24), (17, 16, 22)),
             (15, 15, 22), (17, 16, 24)),
        )
        final_positions = ((0, 15, 0), (0, 15, 2), (2, 16, 1), (1, 16, 2), (2, 16, 0))
        for size in SIZES:
            for edit_layer in (0, 1, 2):
                with self.subTest(size=size, edit_layer=edit_layer):
                    original = self.cells_at(original_positions)
                    bridge = WorkflowBridge()
                    session = Session(bridge)
                    session.editor = Editor(Document(size, original, 'complete workflow', 'swampland'))
                    session.name = session.editor.document.name
                    session.set_editor('edit_layer', edit_layer)
                    editor = session.editor
                    editor.select_box((14, 15, 14), (16, 16, 16))
                    editor.step = 7
                    self.run_tool(session, 'copy')
                    self.assert_cells(editor.document, original)
                    previous = original
                    history = []
                    for tool, origin, direction, positions, lo, hi in stages:
                        with self.subTest(stage=tool):
                            if origin is not None:
                                session.choose_tool(tool)
                                session.set_paste_origin(origin)
                                editor.start = origin
                            before_selection = selection_state(editor)
                            self.run_tool(session, tool, origin)
                            expected = dict(original)
                            expected.update(self.cells_at(positions, direction))
                            self.assert_cells(editor.document, expected)
                            self.assertEqual((box(lo, hi), lo, hi), selection_state(editor))
                            self.assert_history(editor, previous, expected, before_selection,
                                                selection_state(editor))
                            history.append((previous, expected, before_selection, selection_state(editor)))
                            previous = expected

                    before_selection = selection_state(editor)
                    self.run_tool(session, 'cut')
                    self.assert_cells(editor.document, original)
                    self.assert_history(editor, previous, original, before_selection, selection_state(editor))
                    history.append((previous, original, before_selection, selection_state(editor)))
                    editor.start = (0, 15, 0)
                    before_selection = selection_state(editor)
                    self.run_tool(session, 'paste', (0, 15, 0))
                    final = dict(original)
                    final.update(self.cells_at(final_positions, 'west'))
                    self.assert_cells(editor.document, final)
                    self.assertEqual((box((0, 15, 0), (2, 16, 2)), (0, 15, 0), (2, 16, 2)),
                                     selection_state(editor))
                    self.assert_history(editor, original, final, before_selection, selection_state(editor))
                    history.append((original, final, before_selection, selection_state(editor)))
                    for old, new, old_selection, new_selection in reversed(history):
                        self.assertTrue(editor.undo())
                        self.assert_cells(editor.document, old)
                        self.assertEqual(old_selection[0], set(editor.selection))
                        if old_selection != new_selection:
                            self.assertEqual(old_selection, selection_state(editor))
                    for old, new, old_selection, new_selection in history:
                        self.assertTrue(editor.redo())
                        self.assert_cells(editor.document, new)
                        self.assertEqual(new_selection[0], set(editor.selection))
                        if old_selection != new_selection:
                            self.assertEqual(new_selection, selection_state(editor))

                    config = json.loads(json.dumps(editor.document.to_data()))
                    self.assertTrue(all(isinstance(row[3], str) and row[3].startswith('1')
                                        for row in config['chunks']))
                    self.assert_cells(Document.from_data(config), final)
                    session.save_preferences()
                    session.save()
                    bridge.settle()
                    self.assertEqual(1, len(session.library))
                    identity = session.library[0]['id']
                    restarted = Session(bridge)
                    restarted.initialize()
                    restarted.load(identity)
                    bridge.settle()
                    self.assert_cells(restarted.editor.document, final)
                    self.assertEqual((size, 'swampland', 'complete workflow'),
                                     (restarted.editor.document.size, restarted.editor.document.biome,
                                      restarted.editor.document.name))
                    self.assertEqual(edit_layer, restarted.editor.edit_layer)
                    self.assertFalse(restarted.editor.undo_stack)
                    restarted.sharing.open_export(identity)
                    bridge.settle()
                    restarted.sharing.copy()
                    self.assertTrue(bridge.clipboard.startswith('MP4:'))
                    self.assert_cells(restarted.editor.document, final)

                    receiver_bridge = WorkflowBridge()
                    receiver = Session(receiver_bridge)
                    draft = receiver.editor
                    draft_before = dict(draft.document.blocks.items())
                    receiver.sharing.open_import()
                    parts = split_text(bridge.clipboard, 256)
                    self.assertGreater(len(parts), 1)
                    for part in [parts[-1]] + list(reversed(parts)):
                        receiver_bridge.clipboard = part
                        receiver.sharing.paste()
                        receiver_bridge.settle()
                    self.assertFalse(receiver.sharing.error, receiver.sharing.message)
                    self.assert_cells(receiver.sharing.document, final)
                    self.assertIs(draft, receiver.editor)
                    self.assertEqual(draft_before, dict(draft.document.blocks.items()))
                    receiver.sharing.accept()
                    receiver_bridge.settle()
                    self.assertTrue(receiver.sharing.saved, receiver.sharing.message)
                    self.assertIs(draft, receiver.editor)
                    receiver.load(receiver.library[0]['id'])
                    receiver_bridge.settle()
                    self.assert_cells(receiver.editor.document, final)
                    self.assertEqual('swampland', receiver.editor.document.biome)

    def grouped_destination(self, name, index):
        bottom = (15, 15, 15)
        if name == 'bed':
            partner = (15, 15, 16)
            base = material('bed', {'direction': 0, 'head_piece_bit': False})
            other = material('bed', {'direction': 0, 'head_piece_bit': True})
        elif name == 'wooden_door':
            partner = (15, 16, 15)
            base = material(name, {'upper_block_bit': False})
            other = material(name, {'upper_block_bit': True})
        elif name == 'tall_grass':
            partner = (15, 16, 15)
            base = material(name, {'upper_block_bit': False})
            other = material(name, {'upper_block_bit': True})
        else:
            partner = (16, 15, 15)
            actors = [inventory_actor(pos, marker) for pos, marker in
                      ((bottom, 'replaced'), (partner, 'survivor'))]
            for actor, linked in zip(actors, (partner, bottom)):
                actor['__value__'].update({
                    'pairx': {'__type__': 3, '__value__': linked[0]},
                    'pairz': {'__type__': 3, '__value__': linked[2]},
                })
            cells = {pos: make_cell(self.chests['north'], self.water, actor)
                     for pos, actor in zip((bottom, partner), actors)}
            # Replacing one chest detaches the survivor and retains its inventory.
            survivor = make_cell(self.chests['north'], self.water,
                                 inventory_actor(partner, 'survivor'))
            return bottom, partner, cells, survivor
        if index == 1:
            actor = inventory_actor(partner, 'survivor')
            cells = {bottom: make_cell(self.stone, base),
                     partner: make_cell(self.chests['north'], other, actor)}
            return bottom, partner, cells, make_cell(self.chests['north'], AIR, actor)
        if name == 'tall_grass':
            # Covered upper plants can occupy a different layer from their base.
            cells = {bottom: make_cell(base, self.water), partner: make_cell(self.snow, other)}
            return bottom, partner, cells, self.snow
        cells = {bottom: make_cell(base, self.water), partner: make_cell(other, self.water)}
        return bottom, partner, cells, make_cell(AIR, self.water)

    def cancel_after_progress(self, session, tool, expected):
        editor = session.editor
        selection = selection_state(editor)
        revision = editor.revision
        undo, redo = list(editor.undo_stack), list(editor.redo_stack)
        clipboard = editor.clipboard
        self.assertTrue(session.start_edit(tool))
        job = session.edit_job
        job.step(budget=1, seconds=1)
        self.assertFalse(job.done)
        self.assertGreater(job.changed, 0)
        session.cancel_edit()
        session.bridge.settle()
        self.assertTrue(job.cancelled)
        self.assert_cells(editor.document, expected)
        self.assertEqual(selection, selection_state(editor))
        self.assertEqual((revision, undo, redo), (editor.revision, editor.undo_stack, editor.redo_stack))
        self.assertIs(clipboard, editor.clipboard)

    def test_group_overwrite_cancel_retry_and_failed_save_preserve_survivors(self):
        cases = [(name, index) for name in ('wooden_door', 'bed', 'tall_grass') for index in (0, 1)]
        cases.append(('chest', 0))
        donor = (1, 1, 1)
        for size in SIZES:
            for name, index in cases:
                with self.subTest(size=size, group=name, group_layer=index):
                    bottom, partner, grouped, survivor = self.grouped_destination(name, index)
                    incoming = (make_cell(self.snow, self.fern) if name == 'chest' else
                                make_cell(self.chests['north'], self.water, inventory_actor(donor)))
                    original = dict(grouped)
                    original[donor] = incoming
                    bridge = WorkflowBridge()
                    session = Session(bridge)
                    session.editor = Editor(Document(size, original, 'grouped workflow', 'ice_plains'))
                    session.name = session.editor.document.name
                    editor = session.editor
                    editor.edit_layer = 1
                    editor.select_box(donor, donor)
                    self.run_tool(session, 'copy')
                    editor.start = bottom
                    self.cancel_after_progress(session, 'paste', original)

                    session.choose_tool('paste')
                    session.set_paste_origin((size[0], 15, 15))
                    before = selection_state(editor)
                    self.assertIs(session.run(), False)
                    self.assert_cells(editor.document, original)
                    self.assertEqual(before, selection_state(editor))
                    self.assertFalse(editor.undo_stack)

                    if partner[1] != bottom[1]:
                        editor.locked_layers.add(partner[1])
                        session.set_paste_origin(bottom)
                        editor.start = bottom
                        before = selection_state(editor)
                        session.run()
                        bridge.settle()
                        self.assertIn('\u9501\u5b9a', editor.message)
                        self.assert_cells(editor.document, original)
                        self.assertEqual(before, selection_state(editor))
                        self.assertFalse(editor.undo_stack)
                        editor.locked_layers.clear()

                    editor.start = bottom
                    before = selection_state(editor)
                    self.run_tool(session, 'paste', bottom)
                    expected = {donor: incoming, bottom: incoming, partner: survivor}
                    if name != 'chest':
                        expected[bottom] = make_cell(self.chests['north'], self.water, inventory_actor(bottom))
                    self.assert_cells(editor.document, expected)
                    after = selection_state(editor)
                    self.assertEqual(({bottom}, bottom, bottom), after)
                    self.assert_history(editor, original, expected, before, after)

                    # Cancellation while redo is available must retain that branch and clipboard.
                    self.assertTrue(editor.undo())
                    editor.select_box(donor, donor)
                    self.cancel_after_progress(session, 'cut', original)
                    self.assertTrue(editor.redo())
                    self.assert_cells(editor.document, expected)
                    self.assertEqual(after, selection_state(editor))
                    editor.select_box(partner, partner)
                    self.assertEqual({partner}, set(editor.selection))
                    self.run_tool(session, 'copy')
                    self.assert_cells(editor.document, expected)

                    bridge.fail_index = True
                    if size == SIZES[0]:
                        with self.assertRaises(ValueError):
                            session.save()
                    else:
                        session.save()
                        bridge.settle()
                    self.assert_cells(editor.document, expected)
                    self.assertFalse(session.library)
                    self.assertEqual(0, session.library_serial)
                    self.assertIsNone(session.io_job)
                    self.assertEqual(0, editor.saved_revision)
                    bridge.fail_index = False
                    session.save()
                    bridge.settle()
                    self.assertEqual(1, len(session.library))
                    session.load(session.library[0]['id'])
                    bridge.settle()
                    self.assert_cells(session.editor.document, expected)
                    self.assertEqual('ice_plains', session.editor.document.biome)

    def test_legacy_library_and_share_inputs_upgrade_after_complete_cell_edits(self):
        cases = ('sparse_v1', 'unversioned_v1', 'chunk_v2', 'cell_v4', 'archive_v3', 'archive_v5')
        for size in SIZES:
            for case in cases:
                with self.subTest(size=size, legacy=case):
                    rich = case in ('cell_v4', 'archive_v5')
                    old_data, original, packets = legacy_fixture(size, rich)
                    if case.endswith('_v1'):
                        old_data = {'name': old_data['name'], 'size': list(size), 'biome': old_data['biome'],
                                    'blocks': [[15, 15, 15, 'minecraft:stone', 0],
                                               [16, 16, 16, 'minecraft:glass', 0]]}
                        if case == 'sparse_v1':
                            old_data['version'] = 1
                    elif case.startswith('archive_'):
                        old_data = {'version': 5 if rich else 3, 'name': old_data['name'],
                                    'size': list(size), 'biome': old_data['biome'],
                                    'blockCount': 2, 'parts': 2}
                    bridge = WorkflowBridge()
                    bridge.index = {'version': 1, 'serial': 1, 'buildings': [{'id': 1, 'data': old_data}]}
                    if case.startswith('archive_'):
                        bridge.pages[1, 0] = {'packets': copy.deepcopy(packets[:2])}
                        bridge.pages[1, 1] = {'packets': copy.deepcopy(packets[2:])}
                    saved_old_data = copy.deepcopy(old_data)
                    session = Session(bridge)
                    session.initialize()
                    if case.startswith('archive_'):
                        draft = session.editor
                        draft_before = dict(draft.document.blocks.items())
                        missing_page = bridge.pages.pop((1, 1))
                        session.load(1)
                        bridge.settle()
                        self.assertIs(draft, session.editor)
                        self.assertEqual(draft_before, dict(draft.document.blocks.items()))
                        self.assertIsNone(session.io_job)
                        self.assertIn('\u7f3a\u5931', draft.message)
                        bridge.pages[1, 1] = missing_page
                    session.load(1)
                    bridge.settle()
                    editor = session.editor
                    self.assert_cells(editor.document, original)
                    editor.select_box((15, 15, 15), (16, 16, 16))
                    self.run_tool(session, 'copy')
                    editor.start = (1, 1, 1)
                    before = selection_state(editor)
                    self.run_tool(session, 'paste', (1, 1, 1))
                    expected = dict(original)
                    expected[(1, 1, 1)] = original[(15, 15, 15)]
                    if rich:
                        moved_actor = actor_data(original[(16, 16, 16)])
                        moved_actor['__value__'].update({'x': 2, 'y': 2, 'z': 2})
                        expected[(2, 2, 2)] = make_cell(('minecraft:chest', 0), self.water, moved_actor)
                    else:
                        expected[(2, 2, 2)] = original[(16, 16, 16)]
                    self.assert_cells(editor.document, expected)
                    self.assert_history(editor, original, expected, before, selection_state(editor))

                    session.set_editor('edit_layer', 2)
                    editor.material = self.fence
                    self.assertEqual(1, editor.paint_at((3, 3, 3), respect_selection=False))
                    editor.material = self.water
                    self.assertEqual(1, editor.paint_at((3, 3, 3), respect_selection=False))
                    expected[(3, 3, 3)] = make_cell(self.fence, self.water)
                    self.assert_cells(editor.document, expected)
                    session.save()
                    bridge.settle()
                    self.assertEqual(saved_old_data, session.library[0]['data'])
                    self.assertEqual(saved_old_data, bridge.index['buildings'][0]['data'])
                    restarted = Session(bridge)
                    restarted.initialize()
                    restarted.load(2)
                    bridge.settle()
                    self.assert_cells(restarted.editor.document, expected)
                    self.assertEqual('roofed_forest', restarted.editor.document.biome)
                    restarted.load(1)
                    bridge.settle()
                    self.assert_cells(restarted.editor.document, original)

                    if not case.startswith('archive_'):
                        continue
                    # v2 can also have an unversioned begin record in existing MP2 shares.
                    legacy_packets = copy.deepcopy(packets)
                    if not rich:
                        legacy_packets[0].pop('version')
                    raw = ''.join(json.dumps(packet, separators=(',', ':')) + '\n'
                                  for packet in legacy_packets).encode('ascii')
                    bridge.clipboard = 'MP%d:%s:%08x' % (
                        3 if rich else 2, base64.b64encode(zlib.compress(raw)).decode('ascii'),
                        zlib.crc32(raw) & 0xffffffff)
                    restarted.sharing.open_import()
                    restarted.sharing.paste()
                    bridge.settle()
                    self.assertFalse(restarted.sharing.error, restarted.sharing.message)
                    self.assert_cells(restarted.sharing.document, original)
                    restarted.sharing.accept()
                    bridge.settle()
                    self.assertTrue(restarted.sharing.saved, restarted.sharing.message)
                    restarted.load(3)
                    bridge.settle()
                    self.assert_cells(restarted.editor.document, original)

    def linked_chests(self, positions, direction, mirrored=False):
        cells = {}
        for role, pos in enumerate(positions):
            partner = positions[1 - role]
            actor = inventory_actor(pos, 'left inventory' if role == 0 else 'right inventory')
            actor['__value__'].update({
                'pairx': {'__type__': 3, '__value__': partner[0]},
                'pairz': {'__type__': 3, '__value__': partner[2]},
                'pairlead': {'__type__': 1, '__value__': role if mirrored else 1 - role},
            })
            cells[pos] = make_cell(self.chests[direction], self.water, actor)
        return cells

    def test_linked_inventories_survive_cut_rotation_reflection_and_chunk_crossing(self):
        source_positions = ((15, 15, 15), (16, 15, 15))
        stages = (
            ('paste', (14, 15, 14), ((14, 15, 14), (15, 15, 14)), 'north', False),
            ('rotate_y90', None, ((14, 15, 14), (14, 15, 15)), 'east', False),
            ('mirror_z', None, ((14, 15, 15), (14, 15, 14)), 'east', True),
            ('move_zp', None, ((14, 15, 16), (14, 15, 15)), 'east', True),
        )
        sentinel = {(0, 0, 0): make_cell(self.snow, self.fern)}
        for size in SIZES:
            with self.subTest(size=size):
                original = dict(sentinel)
                original.update(self.linked_chests(source_positions, 'north'))
                bridge = WorkflowBridge()
                session = Session(bridge)
                session.editor = Editor(Document(size, original, 'linked inventories', 'pale_garden'))
                session.name = session.editor.document.name
                editor = session.editor
                editor.step = 1
                editor.select_box(source_positions[0], source_positions[0])
                self.assertEqual(set(source_positions), set(editor.selection))
                before = selection_state(editor)
                self.run_tool(session, 'cut')
                self.assert_cells(editor.document, sentinel)
                self.assert_history(editor, original, sentinel, before, selection_state(editor))
                previous = sentinel
                for tool, origin, positions, direction, mirrored in stages:
                    with self.subTest(stage=tool):
                        if origin is not None:
                            editor.start = origin
                        before = selection_state(editor)
                        self.run_tool(session, tool, origin)
                        expected = dict(sentinel)
                        expected.update(self.linked_chests(positions, direction, mirrored))
                        self.assert_cells(editor.document, expected)
                        self.assertEqual(set(positions), set(editor.selection))
                        self.assert_history(editor, previous, expected, before, selection_state(editor))
                        previous = expected
                editor.select_box(positions[0], positions[0])
                self.assertEqual(set(positions), set(editor.selection))
                session.save()
                bridge.settle()
                restarted = Session(bridge)
                restarted.initialize()
                restarted.load(1)
                bridge.settle()
                self.assert_cells(restarted.editor.document, previous)
                restarted.editor.select_box(positions[0], positions[0])
                self.assertEqual(set(positions), set(restarted.editor.selection))
                self.assertEqual('pale_garden', restarted.editor.document.biome)

if __name__ == '__main__':
    unittest.main()
