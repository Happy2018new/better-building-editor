"""The narrow cross fallback preserves source identity and unrelated resources."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import generate_ordinary_plant_proxies as generator


class OrdinaryPlantProxyTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads(generator.PROFILE.read_bytes())

    def test_twelve_legal_states_share_eleven_render_only_meshes(self):
        files = generator.outputs(self.profile)
        namespace = {}
        exec(files[generator.TABLE], namespace)
        mappings = namespace['ORDINARY_PLANT_PROXIES']
        corals = {'brain_coral', 'bubble_coral', 'fire_coral', 'horn_coral', 'tube_coral',
                  'dead_brain_coral', 'dead_bubble_coral', 'dead_fire_coral',
                  'dead_horn_coral', 'dead_tube_coral'}
        expected = {('minecraft:' + name, 0) for name in corals}
        expected.update({('minecraft:acacia_sapling', 0), ('minecraft:acacia_sapling', 1)})
        self.assertEqual(expected, set(mappings))
        self.assertEqual(mappings[('minecraft:acacia_sapling', 0)], mappings[('minecraft:acacia_sapling', 1)])
        self.assertFalse(namespace['SNOW_QUALIFIED'])
        self.assertFalse(namespace['NATIVE_MESH_AUTHORITY'])
        self.assertEqual(25, len(files))
        for identifier in set(mappings.values()):
            stem = identifier.split(':')[1]
            definition = files[ROOT / ('behavior_pack/netease_blocks/' + stem + '.json')]['minecraft:block']
            self.assertFalse(definition['description']['register_to_creative_menu'])
            model = files[ROOT / ('resource_pack/models/netease_block/' + stem + '.json')]['netease:block_geometry']
            self.assertEqual(identifier, model['description']['identifier'])
            self.assertEqual({45, -45}, {bone['rotation'][1] for bone in model['bones']})
            for bone in model['bones']:
                cube, = bone['cubes']
                self.assertEqual(16, cube['size'][1])
                self.assertEqual(0, cube['size'][2])
                self.assertEqual({'north', 'south'}, set(cube['uv']))
                self.assertEqual([16, 16], cube['uv']['north']['uv_size'])
                self.assertEqual([-16, 16], cube['uv']['south']['uv_size'])

    def test_coral_fixture_retains_ten_distinct_native_plants_with_support(self):
        from projection.cell import AIR, background, foreground
        from projection.debug_blueprints import build
        from projection.debug_ordinary_plant_blueprints import CORAL_METADATA
        document = build(CORAL_METADATA[0])
        plants = {position: foreground(value) for position, value in document.blocks.items()
                  if foreground(value)[0] != 'minecraft:stone'}
        self.assertEqual(10, len(plants))
        self.assertEqual({'minecraft:' + name for name in generator.CORALS},
                         {value[0] for value in plants.values()})
        for position, value in plants.items():
            self.assertEqual({}, generator.registry.states(value))
            self.assertEqual(AIR, background(document.get(position)))
            self.assertEqual('minecraft:stone', document.get((position[0], position[1]-1, position[2]))[0])

    def test_existing_atlas_and_blocks_are_preserved_including_firefly(self):
        files = generator.outputs(self.profile)
        for relative, key in (('resource_pack/blocks.json', None),
                              ('resource_pack/textures/terrain_texture.json', 'texture_data')):
            original = json.loads((ROOT / relative).read_bytes())
            actual = files[ROOT / relative]
            for name, value in (original[key] if key else original).items():
                if not name.startswith('modern_projection:ordinary_') and not name.startswith('modern_projection_ordinary_'):
                    self.assertEqual(value, (actual[key] if key else actual)[name], name)
        self.assertEqual('textures/blocks/modern_projection_r23_firefly_composited',
                         files[ROOT / 'resource_pack/textures/terrain_texture.json']['texture_data'][
                             'modern_projection_centered_firefly_bush']['textures'])

    def test_version_state_texture_and_style_drift_are_rejected(self):
        for change in ('registry', 'palette', 'resource', 'style', 'coverage', 'states', 'texture', 'alpha', 'template'):
            profile = deepcopy(self.profile)
            if change == 'registry': profile['registry_version'] = 'NEMC future'
            elif change == 'palette': profile['palette_sha256'] = '0' * 64
            elif change == 'resource': profile['resource_version'] = 'NEMC future'
            elif change == 'style': profile['style']['native_mesh_authority'] = True
            elif change == 'coverage': profile['plants'].pop('brain_coral')
            elif change == 'states': profile['plants']['acacia_sapling']['native_states'].pop()
            elif change == 'texture': profile['plants']['brain_coral']['native_atlas_record']['textures'] = 'other'
            elif change == 'alpha': profile['plants']['bubble_coral']['alpha_bounds'][1] += 1
            else: profile['template']['sha256'] = '0' * 64
            with self.subTest(change=change), self.assertRaises(ValueError):
                generator.validate(profile)


if __name__ == '__main__':
    unittest.main()
