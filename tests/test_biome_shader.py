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

    def test_foliage_cutout_variants_keep_vanilla_material_definitions(self):
        materials = json.loads(MATERIALS.read_text(encoding='utf8'))['materials']
        self.assertNotIn('PROJECTION_FIXED_CUTOUT', repr(materials))
        self.assertFalse(any('blend_alphatest' in name and 'seasons' not in name
                             for name in materials))


if __name__ == '__main__':
    unittest.main()
