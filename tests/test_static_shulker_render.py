"""Static shell geometry, native pose adapters and render-only data isolation."""
import json
import math
import sys
import unittest
from copy import deepcopy
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / 'tools'))
from projection.cell import actor_data, foreground
from projection.debug_blueprints import build, tag, VISUAL_CASES
from projection.entity_render import SHULKER_COLORS, SHULKER_PROXIES, static_proxy
from projection.geometry_palette import INTERNAL_RENDER_BLOCKS, prepare_palette
from projection.nbt_spatial import root_payload
from projection.visible_actor import entity_nbt, compose_actor
from generate_shulker_proxies import model, box_uv


def world_rotation(vector, rotation):
    # Bedrock's exported X/Y bone angles are opposite to the modeler's world
    # angles. This is independently specified by Blockbench's bedrock codec.
    result = list(vector)
    for axis, angle in enumerate((-rotation[0], -rotation[1], rotation[2])):
        cosine, sine = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        if axis == 0:
            result[1], result[2] = result[1] * cosine - result[2] * sine, result[1] * sine + result[2] * cosine
        elif axis == 1:
            result[0], result[2] = result[0] * cosine + result[2] * sine, -result[0] * sine + result[2] * cosine
        else:
            result[0], result[1] = result[0] * cosine - result[1] * sine, result[0] * sine + result[1] * cosine
    return result


class StaticShulkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads((ROOT / 'tools/data/shulker_static_model_v1.json').read_text(encoding='utf8'))

    def test_all_native_colors_and_six_independent_opening_vectors(self):
        from projection import block_registry
        native = {name for name in block_registry.BLOCKS if name.endswith('_shulker_box')}
        self.assertEqual(native, set(SHULKER_PROXIES))
        self.assertEqual(17, len(SHULKER_COLORS))
        for facing, expected in enumerate(((0, -1, 0), (0, 1, 0), (0, 0, -1),
                                          (0, 0, 1), (-1, 0, 0), (1, 0, 0))):
            generated = model(self.spec, 'purple', facing)['netease:block_geometry']
            for bone in generated['bones']:
                vector = world_rotation((0, 1, 0), bone['rotation'])
                for actual, wanted in zip(vector, expected):
                    self.assertAlmostEqual(wanted, actual)

    def test_every_rotated_shell_stays_inside_one_cell_and_preserves_source_uv(self):
        original = {bone['name']: bone for bone in self.spec['geometry']['bones']}
        for color in SHULKER_COLORS:
            for facing in range(6):
                identifier = SHULKER_PROXIES['minecraft:' + color + '_shulker_box'][facing]
                geometry = model(self.spec, color, facing)['netease:block_geometry']
                path = ROOT / 'resource_pack/models/netease_block' / (identifier.split(':')[1] + '.json')
                self.assertEqual(geometry, json.loads(path.read_text(encoding='utf8'))['netease:block_geometry'])
                self.assertEqual([{'width': 64, 'length': 64}], geometry['description']['textures_descriptions'])
                for bone in geometry['bones']:
                    self.assertEqual(1, len(bone['cubes']))
                    cube = bone['cubes'][0]
                    source = original[bone['name']]['cubes'][0]
                    self.assertEqual(box_uv(source['uv'], source['size']), cube['uv'])
                    self.assertEqual(source['size'], cube['size'])
                    for offsets in product((0, 1), repeat=3):
                        point = [cube['origin'][axis] + offsets[axis] * cube['size'][axis] for axis in range(3)]
                        point[0] *= -1
                        rotated = world_rotation([point[axis] - 8 for axis in range(3)], bone['rotation'])
                        self.assertTrue(all(-.00001 <= value + 8 <= 16.00001 for value in rotated),
                                        (color, facing, bone['name'], point, rotated))
                    for face in cube['uv'].values():
                        for origin, extent in zip(face['uv'], face['uv_size']):
                            self.assertTrue(0 <= origin <= 64 and 0 <= origin + extent <= 64)

    def test_box_uv_has_independent_known_lid_regions(self):
        faces = box_uv([0, 0], [16, 12, 16])
        self.assertEqual({'uv': [16, 16], 'uv_size': [16, 12]}, faces['north'])
        self.assertEqual({'uv': [32, 16], 'uv_size': [-16, -16]}, faces['up'])
        self.assertEqual({'uv': [48, 0], 'uv_size': [-16, 16]}, faces['down'])

    def test_builtin_source_and_full_actor_data_are_not_mutated_or_serialized_as_proxies(self):
        case = VISUAL_CASES['shulker_orientations']
        document = build(case['fixture'])
        before = document.to_data()
        source = document.palette_data()
        snapshot = deepcopy(source)
        rendered = prepare_palette(source)
        for facing, pos in enumerate(case['cells']):
            value = document.get(pos)
            self.assertEqual('minecraft:purple_shulker_box', foreground(value)[0])
            self.assertIn((SHULKER_PROXIES[foreground(value)[0]][facing], 0), rendered['common'])
            self.assertTrue(entity_nbt(actor_data(value)))
        self.assertNotIn('minecraft:purple_shulker_box', rendered['actor'])
        self.assertEqual(snapshot, source)
        self.assertEqual(before, document.to_data())
        self.assertNotIn('preview_shulker', json.dumps(document.to_data()))

    def test_authoritative_nbt_pose_wins_over_renderer_default_and_unknown_fields_survive(self):
        document = build('test.transforms.directions')
        value = document.get(VISUAL_CASES['shulker_orientations']['cells'][5])
        nbt = deepcopy(entity_nbt(actor_data(value)))
        root_payload(nbt)['FutureOpaquePayload'] = tag({'Direction': 'untouched'}, 10)
        actor = compose_actor({'facingDirection': 1}, nbt)
        before = deepcopy(actor)
        self.assertEqual(('modern_projection:preview_shulker_purple_5', 0),
                         static_proxy(foreground(value), actor))
        self.assertEqual(before, actor)
        self.assertEqual(('modern_projection:preview_shulker_purple_3', 0),
                         static_proxy(foreground(value), {'facingDirection': 3}))
        self.assertEqual(('modern_projection:preview_shulker_purple_1', 0),
                         static_proxy(foreground(value), {'facingDirection': True}))
        self.assertIsNone(static_proxy(('minecraft:stone', 0), actor))

    def test_all_proxy_blocks_are_hidden_from_both_engine_creative_and_material_picker(self):
        for names in SHULKER_PROXIES.values():
            for identifier in names:
                self.assertIn(identifier, INTERNAL_RENDER_BLOCKS)
                path = ROOT / 'behavior_pack/netease_blocks' / (identifier.split(':')[1] + '.json')
                behavior = json.loads(path.read_text(encoding='utf8'))['minecraft:block']
                self.assertFalse(behavior['description']['register_to_creative_menu'])
                self.assertEqual(0, behavior['components']['minecraft:block_light_absorption']['value'])


if __name__ == '__main__':
    unittest.main()
