import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))

from projection.cauldron_appearance import (CauldronAppearance,
                                             decode_cauldron_appearance,
                                             nbt_snapshot)
from projection.visible_actor import compose_actor


def tag(kind, value):
    return {'__type__': kind, '__value__': value}


def cauldron_nbt(**fields):
    root = {'id': tag(8, 'Cauldron'), 'unknown': tag(3, 77)}
    root.update(fields)
    return root


class CauldronAppearanceTests(unittest.TestCase):
    def test_non_cauldron_and_unverified_states_are_rejected(self):
        self.assertIsNone(decode_cauldron_appearance(
            ('minecraft:stone', 0), {'cauldron_liquid': 'water', 'fill_level': 3}))
        for states in ({}, {'cauldron_liquid': 'water'},
                       {'cauldron_liquid': 'water', 'fill_level': 7},
                       {'cauldron_liquid': 'unknown', 'fill_level': 1},
                       {'cauldron_liquid': 'water', 'fill_level': True}):
            with self.subTest(states=states):
                self.assertIsNone(decode_cauldron_appearance(
                    ('minecraft:cauldron', 0), states))

    def test_shell_and_overlay_keep_liquid_and_six_step_fill(self):
        for liquid in ('water', 'lava', 'powder_snow'):
            for level in range(7):
                appearance = decode_cauldron_appearance(
                    ('minecraft:cauldron', 0),
                    {'cauldron_liquid': liquid, 'fill_level': level})
                self.assertIsInstance(appearance, CauldronAppearance)
                self.assertEqual(('minecraft:cauldron', 0), appearance.shell.material)
                self.assertEqual('native', appearance.shell.renderer)
                self.assertEqual((liquid, level),
                                 (appearance.overlay.liquid, appearance.overlay.fill_level))

    def test_potion_and_custom_color_are_metadata_only_and_custom_wins(self):
        payload = cauldron_nbt(PotionId=tag(3, 42), PotionType=tag(3, 99),
                               CustomColor=tag(3, -65536))
        before = copy.deepcopy(payload)
        appearance = decode_cauldron_appearance(
            ('minecraft:water_cauldron', 0),
            {'cauldron_liquid': 'water', 'fill_level': 5}, payload)
        self.assertEqual('custom_color', appearance.overlay.color_source)
        self.assertEqual((42, 99, -65536),
                         (appearance.overlay.potion_id,
                          appearance.overlay.potion_type,
                          appearance.overlay.custom_color))
        self.assertEqual(before, payload)
        self.assertEqual(before, nbt_snapshot(appearance))

    def test_actor_envelope_and_unknown_tags_are_preserved(self):
        nbt = cauldron_nbt(PotionId=tag(3, 11), FutureOpaque=tag(10, {'x': tag(3, 1)}))
        actor = compose_actor({'nativeShellField': tag(3, 1)}, nbt)
        appearance = decode_cauldron_appearance(
            ('minecraft:cauldron', 0),
            {'cauldron_liquid': 'water', 'fill_level': 2}, actor)
        self.assertEqual('potion', appearance.overlay.color_source)
        self.assertEqual(actor, nbt_snapshot(appearance))
        detached = nbt_snapshot(appearance)
        detached['nbt']['FutureOpaque']['__value__']['x']['__value__'] = 9
        self.assertEqual(1, nbt['FutureOpaque']['__value__']['x']['__value__'])

    def test_invalid_optional_fields_do_not_create_a_guessed_color(self):
        payload = cauldron_nbt(PotionId=tag(8, 'not-an-int'), CustomColor=tag(8, 'red'))
        appearance = decode_cauldron_appearance(
            ('minecraft:cauldron', 0),
            {'cauldron_liquid': 'water', 'fill_level': 1}, payload)
        self.assertEqual('none', appearance.overlay.color_source)
        self.assertEqual((None, None, None),
                         (appearance.overlay.potion_id,
                          appearance.overlay.potion_type,
                          appearance.overlay.custom_color))


if __name__ == '__main__':
    unittest.main()
