import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.cell import actor_data, make_cell, transform
from projection.nbt_spatial import rebase
from projection.visible_actor import compose_actor, entity_nbt, render_actor


class VisibleActorTransformTests(unittest.TestCase):
    def test_envelope_keeps_render_fields_and_full_inventory_independent(self):
        render = {'facingDirection': 2}
        nbt = {'x': {'__type__': 3, '__value__': 8},
               'Items': {'__type__': 9, '__value__': [
                   {'tag': {'x': 91}, 'Slot': 0}]}}
        payload = compose_actor(render, nbt)
        moved = rebase(payload, (-8, -64, -5))
        self.assertEqual(0, entity_nbt(moved)['x']['__value__'])
        self.assertEqual(nbt['Items'], entity_nbt(moved)['Items'])
        self.assertEqual(render, render_actor(moved))
        cell = make_cell(('minecraft:chest', 2), nbt=payload)
        rotated = transform(cell, 'rotate_y90', (0, 0, 0))
        self.assertEqual(5, render_actor(actor_data(rotated))['facingDirection'])
        self.assertEqual(nbt, entity_nbt(actor_data(rotated)))
        self.assertEqual(8, nbt['x']['__value__'])

    def test_empty_render_actor_is_distinct_from_missing_render_actor(self):
        nbt = {'Items': {'__type__': 9, '__value__': []}}
        self.assertEqual({}, render_actor(compose_actor({}, nbt)))
        self.assertIsNone(render_actor(compose_actor(None, nbt)))
        self.assertIsNone(render_actor(nbt))

    def test_native_mixed_tagged_root_and_plain_inventory_is_nbt(self):
        nbt = {'id':{'__type__':8, '__value__':'ShulkerBox'},
               'facing':{'__type__':1, '__value__':1}, 'Items':[]}
        self.assertEqual(nbt, entity_nbt(nbt))
        self.assertIsNone(render_actor(nbt))
        self.assertIsNone(render_actor({'__modern_projection_actor__':2,
                                        'render':{}, 'nbt':nbt}))

    def test_double_chest_horizontal_mirror_swaps_render_roles_and_is_reversible(self):
        payload = {'facingDirection': 2, 'chestIsLargeChest': True,
                   'chestMainSubChest': True, 'chestModelOffset': 0.0,
                   'chestOpenness': 0.0, 'chestOldOpenness': 0.0}
        value = make_cell(('minecraft:chest', 2), nbt=payload)
        mirrored = transform(value, 'mirror_x', (0, 0, 0))
        self.assertEqual(2, actor_data(mirrored)['facingDirection'])
        self.assertFalse(actor_data(mirrored)['chestMainSubChest'])
        self.assertEqual(-0.5, actor_data(mirrored)['chestModelOffset'])
        self.assertEqual(value, transform(mirrored, 'mirror_x', (0, 0, 0)))
        rotated = transform(value, 'rotate_y90', (0, 0, 0))
        self.assertEqual(5, actor_data(rotated)['facingDirection'])
        self.assertTrue(actor_data(rotated)['chestMainSubChest'])
        self.assertEqual(payload, actor_data(value))

    def test_sign_text_is_unchanged_while_its_visible_rotation_tracks_the_block(self):
        value = make_cell(('minecraft:standing_sign', 0), nbt={
            'signStandingRotation': 0, 'signRealText': 'Front P0',
            'signRealTextBack': 'Back P0'})
        rotated = transform(value, 'rotate_y90', (0, 0, 0))
        self.assertEqual(4, actor_data(rotated)['signStandingRotation'])
        self.assertEqual('Front P0', actor_data(rotated)['signRealText'])
        self.assertEqual('Back P0', actor_data(rotated)['signRealTextBack'])
        self.assertEqual(value, transform(value, 'mirror_y', (0, 0, 0)))


if __name__ == '__main__':
    unittest.main()
