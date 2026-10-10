"""Native skull pose selection and preservation of stored block entity data."""
from copy import deepcopy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / 'tools'))
from projection.block_registry import from_states
from projection.cell import actor_data, make_cell
from projection.entity_defaults import nbt
from projection.geometry_palette import INTERNAL_RENDER_BLOCKS, prepare_palette
from projection.static_skull import SKULL_PROXIES, skull_proxy
from projection.visible_actor import compose_actor
from generate_skull_proxies import model


class StaticSkullTests(unittest.TestCase):
    def source(self, yaw, facing=1, name='minecraft:skeleton_skull'):
        material = from_states(name, {'facing_direction': facing})
        entity = nbt(material[0], (1, 1, 1))
        entity['Rotation']['__value__'] = yaw
        entity['unknown'] = {'value': 123}
        return material, compose_actor({'facingDirection': facing, 'rotation': yaw,
                                        'skullType': 255, 'progress': 0.}, entity)

    def test_native_floor_angles_select_exact_variants_in_both_turn_conventions(self):
        names = SKULL_PROXIES['minecraft:skeleton_skull']
        for step in range(16):
            for yaw in (step * 22.5, step * 22.5 - 360.):
                material, actor = self.source(yaw)
                self.assertEqual((names['floor_' + str(step)], 0), skull_proxy(material, actor))
        material, actor = self.source(23.)
        self.assertIsNone(skull_proxy(material, actor))
        actor['nbt']['Rotation']['__type__'] = 1
        self.assertIsNone(skull_proxy(material, actor))

    def test_wall_poses_ignore_unused_floor_yaw(self):
        names = SKULL_PROXIES['minecraft:skeleton_skull']
        for face in (2, 3, 4, 5):
            material, actor = self.source(13., face)
            self.assertEqual((names['wall_' + str(face)], 0), skull_proxy(material, actor))

    def test_named_mob_head_species_use_distinct_native_textures_and_materials(self):
        spec = json.loads((ROOT / 'tools/data/skull_static_model_v1.json').read_text(encoding='utf8'))
        textures = set()
        for name, variants in SKULL_PROXIES.items():
            material, actor = self.source(45., name=name)
            self.assertEqual((variants['floor_2'], 0), skull_proxy(material, actor))
            material, actor = self.source(13., facing=2, name=name)
            self.assertEqual((variants['wall_2'], 0), skull_proxy(material, actor))
            geometry = model(spec, name, 'floor_2')['netease:block_geometry']
            texture = geometry['description']['textures'][0]
            textures.add(texture)
            self.assertEqual('modern_projection_static_' + name.split(':')[1], texture)
            self.assertIn('texture_' + name.split(':')[1], spec['sha256'])
        self.assertEqual(4, len(textures))

    def test_static_render_consumes_only_renderer_slots_and_preserves_complete_document(self):
        material, actor = self.source(45.)
        value = make_cell(material, nbt=actor)
        source = {'common': {material: [13]}, 'actor': {material[0]: {13: actor_data(value)}},
                  'volume': (3, 3, 3)}
        saved = deepcopy(source)
        prepared = prepare_palette(source)
        proxy = skull_proxy(material, actor)
        self.assertEqual({proxy: [13]}, prepared['common'])
        self.assertEqual({}, prepared['actor'])
        self.assertEqual(saved, source)
        self.assertIn(proxy[0], INTERNAL_RENDER_BLOCKS)

    def test_source_cube_and_texel_dimensions_are_preserved(self):
        spec = json.loads((ROOT / 'tools/data/skull_static_model_v1.json').read_text(encoding='utf8'))
        saved = deepcopy(spec)
        for pose in SKULL_PROXIES['minecraft:skeleton_skull']:
            result = model(spec, 'minecraft:skeleton_skull', pose)['netease:block_geometry']
            self.assertEqual([8, 8, 8], result['bones'][0]['cubes'][0]['size'])
            self.assertEqual({'width': 64, 'length': 32}, result['description']['textures_descriptions'][0])
            identifier = result['description']['identifier']
            path = ROOT / 'resource_pack/models/netease_block' / (identifier.split(':')[1] + '.json')
            self.assertEqual(result, json.loads(path.read_text(encoding='utf8'))['netease:block_geometry'])
        self.assertEqual(saved, spec)


if __name__ == '__main__':
    unittest.main()
