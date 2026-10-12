"""Appearance provenance failures leave caller-owned state unchanged."""
from copy import deepcopy
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import appearance_defaults_data, native_appearance, static_frame_item_data
from projection.block_registry import from_states
from projection.cell import actor_data, make_cell
from projection.debug_appearance_blueprints import populate
from projection.debug_blueprints import BLUEPRINTS, Fixture
from projection.entity_render import native_actor
from projection.geometry_palette import prepare_palette
from projection.model import Document, Editor
from projection.static_frame_item import frame_item_proxy
from projection.visible_actor import compose_actor


DRIFT = (('SCHEMA_VERSION', 99), ('SOURCE_VERSION', 'NEMC future'),
         ('PALETTE_SHA256', '0' * 64))


class RuntimeAppearanceProvenanceTests(unittest.TestCase):
    def test_appearance_source_drift_rejects_before_any_fixture_write(self):
        for source in (appearance_defaults_data, native_appearance):
            for field, value in DRIFT:
                fixture = Mock()
                with self.subTest(source=source.__name__, field=field), patch.object(source, field, value):
                    with self.assertRaisesRegex(ValueError, 'appearance'):
                        populate(fixture)
                fixture.floor.assert_not_called()
                fixture.plinth.assert_not_called()
                fixture.put.assert_not_called()
                fixture.finish.assert_not_called()

    def test_appearance_drift_preserves_existing_fixture_document(self):
        metadata = next(row for row in BLUEPRINTS if row[0] == 'test.entities.appearances')
        fixture = Fixture(metadata)
        fixture.document.blocks[(1, 2, 3)] = make_cell(('minecraft:stone', 0),
            nbt={'future_metadata': {'value': 41}})
        before = deepcopy(fixture.document.to_data())
        for field, value in DRIFT:
            with self.subTest(field=field), patch.object(appearance_defaults_data, field, value):
                with self.assertRaises(ValueError):
                    populate(fixture)
            self.assertEqual(before, fixture.document.to_data())

    def test_renderer_only_bed_drift_preserves_actor_cell_palette_and_history(self):
        material = from_states('minecraft:bed', {'direction': 2, 'head_piece_bit': False,
                                                'occupied_bit': False})
        for renderer in ({'direction': 0, 'future': {'value': 71}},
                         {b'direction': 0, 'future': {'value': 71}}):
            actor = compose_actor(renderer, None)
            actor['future_metadata'] = {'value': 81}
            cell = make_cell(material, nbt=actor)
            editor = Editor(Document((3, 3, 3), {(1, 1, 1): cell}))
            editor._commit('Place', {(0, 2, 0): ('minecraft:stone', 0)})
            editor._commit('Place again', {(2, 2, 2): ('minecraft:stone', 0)})
            editor.undo()
            before_actor, before_document = deepcopy(actor), deepcopy(editor.document.to_data())
            before_cell = editor.document.get((1, 1, 1))
            before_undo, before_redo = editor.undo_stack[:], editor.redo_stack[:]
            for field, value in DRIFT:
                palette = editor.document.palette_data()
                before_palette = deepcopy(palette)
                with self.subTest(field=field, byte_key=b'direction' in renderer), \
                        patch.object(native_appearance, field, value):
                    with self.assertRaisesRegex(ValueError, 'appearance'):
                        native_actor(material, actor)
                    with self.assertRaisesRegex(ValueError, 'appearance'):
                        prepare_palette(palette)
                self.assertEqual(before_actor, actor)
                self.assertEqual(before_palette, palette)
                self.assertEqual(before_document, editor.document.to_data())
                self.assertEqual(before_cell, editor.document.get((1, 1, 1)))
                self.assertEqual(before_undo, editor.undo_stack)
                self.assertEqual(before_redo, editor.redo_stack)
                self.assertEqual(before_actor, actor_data(before_cell))

    def test_renderer_only_bed_still_refreshes_valid_native_direction_in_a_copy(self):
        material = from_states('minecraft:bed', {'direction': 2, 'head_piece_bit': False,
                                                'occupied_bit': False})
        actor = {'direction': 0, 'future': {'value': 71}}
        before = deepcopy(actor)
        result = native_actor(material, actor)
        self.assertEqual(2, result['direction'])
        result['future']['value'] = 99
        self.assertEqual(before, actor)

    def test_disabled_frame_profile_does_not_claim_acceptance_when_metadata_drifts(self):
        material = from_states('minecraft:frame', {'facing_direction': 2,
            'item_frame_map_bit': False, 'item_frame_photo_bit': False})
        actor = {'id': {'__type__': 8, '__value__': 'ItemFrame'},
                 'Item': {'__type__': 10, '__value__': {
                     'Name': {'__type__': 8, '__value__': 'minecraft:diamond_sword'},
                     'Damage': {'__type__': 2, '__value__': 0},
                     'Count': {'__type__': 1, '__value__': 1}}},
                 'ItemRotation': {'__type__': 5, '__value__': 0.}}
        before = deepcopy(actor)
        self.assertFalse(static_frame_item_data.FRAME_ITEMS[('minecraft:diamond_sword', 0)]['accepted'])
        for field, value in DRIFT:
            with self.subTest(field=field), patch.object(static_frame_item_data, field, value):
                self.assertIsNone(frame_item_proxy(material, actor))
            self.assertEqual(before, actor)


if __name__ == '__main__':
    unittest.main()
