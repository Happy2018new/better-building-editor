import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHADER = ROOT / 'resource_pack/shaders/glsl/modern_projection_biome_blocks.fragment'
MATERIALS = ROOT / 'resource_pack/materials/terrain.material'


class BiomeShaderContractTests(unittest.TestCase):
    def test_world_projection_material_uses_the_biome_shader(self):
        materials = json.loads(MATERIALS.read_text(encoding='utf8'))['materials']
        material = materials['netease_block_as_entity_mesh']
        self.assertIn('Blending', material['+states'])
        self.assertEqual('shaders/glsl/modern_projection_biome_blocks.fragment',
                         material['fragmentShader'])

    def test_grass_side_recovery_covers_transparent_world_projection(self):
        source = SHADER.read_text(encoding='utf8')
        self.assertIn('#if !USE_ALPHA_TEST || defined(BLEND)', source)
        self.assertIn('grassSideSource(diffuse.rgb)', source)
        self.assertIn('buildingBiomeTint(biomeIndex, false) / source', source)


if __name__ == '__main__':
    unittest.main()
