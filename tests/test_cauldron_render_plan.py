"""Target selection and shared-liquid integration; supplied colors are fixtures."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.cauldron_render_plan import CauldronTop, iter_render_steps, prepare_shells
from projection.cell import make_cell
from projection.liquid_transport import validate_uniforms
from projection.model import Document


class SuppliedProfile(object):
    max_groups = 32
    empty_shell = ('minecraft:cauldron', 0)
    empty_states = {'cauldron_liquid': 'water', 'fill_level': 0}
    models = {'water': 'cauldron_water_ui', 'lava': 'cauldron_lava_ui'}
    world_models = {'water': 'cauldron_water_world', 'lava': 'cauldron_lava_world'}

    def top(self, material, actor, biome):
        if material[1] == 0 or actor and actor.get('unsupported'):
            return None
        color = tuple(actor.get('color', (20, 40, 80))) if actor else (20, 40, 80)
        return CauldronTop(.6, 'lava' if material[1] > 7 else 'water', color, None)


def groups(document, profile=None, **kwargs):
    return [group for group in iter_render_steps(document, profile or SuppliedProfile(), **kwargs)
            if group is not None]


class CauldronRenderPlanTests(unittest.TestCase):
    def test_colors_partition_uniform_groups_and_source_is_immutable(self):
        cells = {(x, 0, 0): make_cell(('minecraft:cauldron', 6),
                 nbt={'color': color, 'unknown': {'retained': 9}})
                 for x, color in enumerate(((255, 0, 0), (0, 0, 255), (255, 0, 0)))}
        document = Document((4, 1, 1), cells)
        before = deepcopy(document.to_data())
        result = groups(document)
        self.assertEqual(2, len(result))
        self.assertEqual({float(0xff0000), float(0x0000ff)}, {r.uniforms[3][2] for r in result})
        self.assertEqual(before, document.to_data())
        for group in result:
            validate_uniforms(group.uniforms)
            self.assertEqual('cauldron_water_ui', group.model_name)

    def test_target_and_visibility_filters_keep_unselected_native_contents_out(self):
        document = Document((4, 2, 1), {(x, 0, 0): ('minecraft:cauldron', 6) for x in range(4)})
        targets = document.palette_data(lambda pos: pos[0] in (1, 2))
        result = groups(document, targets=targets, visible=lambda pos: pos[0] != 2, world=True)
        self.assertEqual(1, len(result))
        self.assertEqual('cauldron_water_world', result[0].model_name)
        # Address6 stores x + 4*z + 16*y, face bit0 contributes 64.
        self.assertEqual((65., 0., 0., 0.), result[0].uniforms[0])

    def test_empty_unsupported_and_background_cauldron_are_not_fabricated(self):
        document = Document((4, 1, 1), {
            (0, 0, 0): ('minecraft:cauldron', 0),
            (1, 0, 0): make_cell(('minecraft:cauldron', 6), nbt={'unsupported': True}),
            (2, 0, 0): make_cell(('minecraft:stone', 0), ('minecraft:cauldron', 6)),
        })
        self.assertEqual([], groups(document))

    def test_four_cell_payload_limits_and_separate_world_texture(self):
        document = Document((8, 1, 2), {(x, 0, z): ('minecraft:cauldron', 14)
                                       for x in range(8) for z in range(2)})
        result = groups(document, world=True, opacity=.25)
        self.assertEqual(4, len(result))
        self.assertTrue(all(group.model_name == 'cauldron_lava_world' for group in result))
        self.assertTrue(all(group.uniforms[3][3] == .25 for group in result))
        profile = SuppliedProfile()
        profile.max_groups = 3
        with self.assertRaisesRegex(ValueError, 'budget'):
            groups(document, profile)

    def test_targets_reject_stale_duplicate_and_outside_indices(self):
        document = Document((2, 1, 1), {(0, 0, 0): ('minecraft:cauldron', 6)})
        for targets in (
            {'volume': (1, 2, 1), 'common': {('minecraft:cauldron', 6): [2]}},
            {'volume': (1, 2, 1), 'common': {('minecraft:cauldron', 6): [0, 0]}},
            {'volume': (1, 2, 1), 'common': {('minecraft:cauldron', 5): [0]}},
            {'volume': (2, 1, 1), 'common': {}},
        ):
            with self.subTest(targets=targets), self.assertRaises(ValueError):
                groups(document, targets=targets)

    def test_empty_shell_replaces_only_supported_draw_and_preserves_actors(self):
        common = {('minecraft:cauldron', 6): [0, 1], ('minecraft:stone', 0): [2]}
        states = {('minecraft:cauldron', 6): {'cauldron_liquid': 'water', 'fill_level': 6}}
        document = Document((3, 1, 1), {
            (0, 0, 0): make_cell(('minecraft:cauldron', 6), nbt={'unknown': 1}),
            (1, 0, 0): make_cell(('minecraft:cauldron', 6), nbt={'unsupported': True}),
            (2, 0, 0): ('minecraft:stone', 0),
        })
        actors = document.palette_data()['actor']
        before = deepcopy((common, states, actors))
        rendered, records = prepare_shells(common, states, actors, SuppliedProfile(), 'plains')
        self.assertEqual([0], rendered[('minecraft:cauldron', 0)])
        self.assertEqual([1], rendered[('minecraft:cauldron', 6)])
        self.assertEqual(0, records[('minecraft:cauldron', 0)]['fill_level'])
        self.assertEqual(before, (common, states, actors))

    def test_other_actor_index_cannot_override_the_cauldron_actor(self):
        common = {('minecraft:cauldron', 6): [0]}
        actors = {'minecraft:cauldron': {0: {'color': (1,2,3)}},
                  'minecraft:chest': {0: {'unsupported': True}}}
        rendered, unused = prepare_shells(common, {}, actors, SuppliedProfile(), 'plains')
        self.assertEqual({('minecraft:cauldron',0):[0]}, rendered)


if __name__ == '__main__':
    unittest.main()
