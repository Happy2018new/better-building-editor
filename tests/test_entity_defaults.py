"""Editor-created and old renderer-only Shulkers acquire real native directions."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.cell import actor_data, make_cell, transform
from projection.entity_defaults import direction_actor, nbt as default_nbt
from projection.entity_render import SHULKER_PROXIES, static_proxy
from projection.model import Document, Editor
from projection.nbt_spatial import root_payload, scalar
from projection.storage import Selection
from projection.visible_actor import compose_actor, entity_nbt, render_actor

FACES = ((0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0))


class EntityDefaultTests(unittest.TestCase):
    def test_plain_editor_placement_mirror_undo_and_redo_for_every_native_color(self):
        pos = (2, 3, 4)
        for name in SHULKER_PROXIES:
            editor = Editor(Document((8, 8, 8)))
            editor.material = (name, 0)
            editor.selection = Selection((pos,))
            editor._commit('Place', {pos: editor.material})
            original = editor.document.get(pos)
            self.assertIsNone(actor_data(original))
            self.assertEqual(1, editor._transform('mirror_y'))
            mirrored = editor.document.get(pos)
            native = root_payload(entity_nbt(actor_data(mirrored)))
            self.assertEqual('ShulkerBox', scalar(native, 'id'))
            self.assertEqual(0, scalar(native, 'facing'))
            self.assertEqual(pos, tuple(scalar(native, axis) for axis in ('x', 'y', 'z')))
            self.assertEqual((SHULKER_PROXIES[name][0], 0), static_proxy(mirrored, actor_data(mirrored)))
            editor.undo()
            self.assertEqual(original, editor.document.get(pos))
            editor.redo()
            self.assertEqual(mirrored, editor.document.get(pos))
            editor._transform('mirror_y')
            self.assertEqual(1, scalar(entity_nbt(actor_data(editor.document.get(pos))), 'facing'))

    def test_old_renderer_directions_become_native_tags_and_follow_independent_vectors(self):
        name = 'minecraft:purple_shulker_box'
        for facing, normal in enumerate(FACES):
            renderer = {'facingDirection': facing, 'future_field': {'x': 41}}
            original = copy.deepcopy(renderer)
            value = make_cell((name, 0), nbt=renderer)
            rotated = transform(value, 'rotate_y90', (4, 5, 6))
            expected = FACES.index((-normal[2], normal[1], normal[0]))
            actor = actor_data(rotated)
            self.assertEqual(expected, scalar(entity_nbt(actor), 'facing'))
            self.assertEqual(expected, render_actor(actor)['facingDirection'])
            self.assertEqual(original['future_field'], render_actor(actor)['future_field'])
            self.assertEqual(1, root_payload(entity_nbt(actor))['facing']['__type__'])
            self.assertEqual(original, renderer)

    def test_existing_complete_inventory_and_unknown_envelope_fields_are_preserved(self):
        name = 'minecraft:purple_shulker_box'
        native = default_nbt(name, (3, 2, 1))
        native['Items'] = [{'id': 'minecraft:diamond', 'Count': 7}]
        actor = compose_actor({'facingDirection': 1}, native)
        actor['future_metadata'] = {'id': 71}
        before = copy.deepcopy(actor)
        self.assertIs(actor, direction_actor((name, 0), actor, (3, 2, 1)))
        changed = actor_data(transform(make_cell((name, 0), nbt=actor), 'mirror_y', (3, 2, 1)))
        self.assertEqual(0, scalar(entity_nbt(changed), 'facing'))
        self.assertEqual(native['Items'], entity_nbt(changed)['Items'])
        self.assertEqual(actor['future_metadata'], changed['future_metadata'])
        self.assertEqual(before, actor)

    def test_shared_and_config_formats_keep_hydrated_native_direction(self):
        from projection.sharing_codec import encode_steps, decode_steps
        value = transform(('minecraft:purple_shulker_box', 0), 'mirror_y')
        doc = Document((1, 1, 1), {(0, 0, 0): value})
        restored = Document.from_data(json.loads(json.dumps(doc.to_data())))
        self.assertEqual(value, restored.get((0, 0, 0)))
        shared = list(encode_steps(doc))[-1]['text']
        restored = list(decode_steps(shared))[-1]['document']
        self.assertEqual(value, restored.get((0, 0, 0)))

    def test_renderer_only_envelope_keeps_future_metadata_when_native_defaults_are_added(self):
        actor = {'__modern_projection_actor__': 1, 'render': {'facingDirection': 4},
                 'nbt': None, 'future_metadata': {'x': 81}}
        before = copy.deepcopy(actor)
        cell = make_cell(('minecraft:purple_shulker_box', 0), nbt=actor)
        changed = actor_data(transform(cell, 'mirror_x', (3, 4, 5)))
        self.assertEqual(5, scalar(entity_nbt(changed), 'facing'))
        self.assertEqual(actor['future_metadata'], changed['future_metadata'])
        self.assertEqual(before, actor)
    def test_other_materials_and_non_direction_operations_do_not_add_defaults(self):
        for name in ('minecraft:stone', 'minecraft:chest', 'minecraft:standing_sign'):
            self.assertIsNone(direction_actor((name, 0), None, (1, 2, 3)))
        plain = ('minecraft:purple_shulker_box', 0)
        self.assertEqual(plain, transform(plain, 'move_xp', (1, 2, 3)))

    def test_stale_default_snapshot_rejects_mirror_without_modifying_document(self):
        from projection import entity_defaults_data as source
        editor = Editor(Document((1, 1, 1), {(0, 0, 0): ('minecraft:purple_shulker_box', 0)}))
        editor.selection = Selection(((0, 0, 0),))
        before = editor.document.to_data()
        version = source.SOURCE_VERSION
        try:
            source.SOURCE_VERSION = 'future'
            with self.assertRaises(ValueError):
                editor._transform('mirror_y')
        finally:
            source.SOURCE_VERSION = version
        self.assertEqual(before, editor.document.to_data())
        self.assertEqual([], editor.undo_stack)


if __name__ == '__main__':
    unittest.main()
