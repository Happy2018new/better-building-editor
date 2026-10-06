import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHADER = ROOT / 'resource_pack/shaders/glsl/modern_projection_biome_blocks.fragment'
VERTEX = SHADER.with_suffix('.vertex')
MATERIALS = ROOT / 'resource_pack/materials/terrain.material'


class BiomeShaderContractTests(unittest.TestCase):
    def test_new_tints_have_shader_entries_and_ui_depth_tags(self):
        fragment = SHADER.read_text(encoding='utf8')
        vertex = VERTEX.read_text(encoding='utf8')
        for grass, foliage in (((119, 130, 114), (135, 141, 118)),
                               ((182, 219, 97), (182, 219, 97)),
                               ((144, 129, 77), (174, 164, 42)),
                               ((80, 122, 50), (89, 174, 48))):
            self.assertIn('grass=vec3(%s); foliage=vec3(%s)' %
                          (','.join('%s.0' % v for v in grass),
                           ','.join('%s.0' % v for v in foliage)), fragment)
        self.assertIn('previewTag <= 222.0', fragment)
        self.assertIn('tag <= 222.0', vertex)

    def test_vertex_preservation_and_fragment_tint_recognize_the_same_colors(self):
        # A fragment-only fix still fails when preview lighting clamps the
        # blue channel before interpolation. Both stages must agree.
        bodies = []
        for path in (VERTEX, SHADER):
            source = path.read_text(encoding='utf8')
            helper = re.search(r'bool grassVertexTint\(vec3 tint\)\s*\{([^}]+)\}',
                               source, re.S)
            self.assertIsNotNone(helper, str(path))
            bodies.append(' '.join(helper.group(1).split()))
        self.assertEqual(bodies[0], bodies[1])
        self.assertIn('grassVertexTint(COLOR.rgb)', VERTEX.read_text(encoding='utf8'))
        self.assertIn('grassVertexTint(inColor.rgb)', SHADER.read_text(encoding='utf8'))

    def test_world_projection_material_uses_the_biome_shader(self):
        materials = json.loads(MATERIALS.read_text(encoding='utf8'))['materials']
        material = materials['netease_block_as_entity_mesh']
        self.assertIn('Blending', material['+states'])
        self.assertEqual('shaders/glsl/modern_projection_biome_blocks.fragment',
                         material['fragmentShader'])

    def test_grass_side_recovery_covers_transparent_world_projection(self):
        source = SHADER.read_text(encoding='utf8')
        self.assertIn('#if !USE_ALPHA_TEST', source)
        self.assertIn('grassSideSource(diffuse.rgb)', source)
        self.assertIn('buildingBiomeTint(biomeIndex, false) / source', source)

    def test_foliage_cutout_variants_retain_native_cutout_and_culling(self):
        materials = json.loads(MATERIALS.read_text(encoding='utf8'))['materials']
        by_name = dict((key.split(':', 1)[0], value) for key, value in materials.items())
        self.assertNotIn('PROJECTION_FIXED_CUTOUT', repr(materials))
        # Explicit native parents preserve ALPHA_TEST and the appropriate
        # single/double-sided geometry while the projection adds blending.
        parents = {
            'netease_block_as_mesh_blend_alphatest': 'netease_block_as_mesh_alpha',
            'netease_block_as_mesh_blend_alphatest_seasons': 'netease_block_as_mesh_alpha_seasons',
            'netease_block_as_mesh_blend_alphatest_singleside': 'netease_block_as_mesh_alpha_single_side',
        }
        for child, parent in parents.items():
            with self.subTest(material=child):
                override = materials[child + ':' + parent]
                self.assertIn('Blending', override['+states'])
                self.assertIn('DisableDepthWrite', override['+states'])
                for layer in (by_name.get(parent, {}), override):
                    # Replacing these lists would erase native definitions.
                    self.assertNotIn('defines', layer)
                    self.assertNotIn('states', layer)
                    self.assertNotIn('ALPHA_TEST', layer.get('-defines', []))
                    self.assertNotIn('DisableCulling', layer.get('-states', []))
                    self.assertNotIn('InvertCulling', layer.get('+states', []))
                    if child.endswith('_singleside'):
                        self.assertNotIn('DisableCulling', layer.get('+states', []))
                self.assertIn('EnableAlphaToCoverage', by_name[parent]['-states'])

    def test_projection_materials_explicitly_support_msaa_targets(self):
        materials = json.loads(MATERIALS.read_text(encoding='utf8'))['materials']
        # In the 3.9 client, inheriting this alone still produced a first-draw
        # "Late creating a PSO" assertion for blend_alphatest after cold start.
        names = []
        for key, material in materials.items():
            if key == 'version':
                continue
            names.append(key.split(':', 1)[0])
            self.assertEqual(material.get('msaaSupport'), 'Both', key)
        self.assertEqual(len(names), len(set(names)))

    def test_cutout_overrides_keep_explicit_native_parent_chains(self):
        materials = json.loads(MATERIALS.read_text(encoding='utf8'))['materials']
        # Name-only state patches made the UI cutouts disappear in the native
        # client even though the transparent world children still rendered.
        single = materials['netease_block_as_mesh_alpha_single_side:netease_block_as_entity_mesh']
        double = materials['netease_block_as_mesh_alpha:netease_block_as_mesh_alpha_single_side']
        seasons = materials['netease_block_as_mesh_alpha_seasons:netease_block_as_entity_mesh']
        self.assertIn('ALPHA_TEST', single['+defines'])
        self.assertIn('DisableCulling', double['+states'])
        self.assertIn('ALPHA_TEST', seasons['+defines'])
        self.assertIn('SEASONS', seasons['+defines'])


if __name__ == '__main__':
    unittest.main()
