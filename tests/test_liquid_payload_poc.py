"""Carrier transport invariants, without claiming native liquid acceptance."""
import itertools
import json
import math
from pathlib import Path
import sys
import unittest
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import liquid_payload_poc as payload
import generate_liquid_payload_poc as generator

QUAD_CORNERS = ((0, 0), (1, 0), (1, 1), (0, 1))


class LiquidCarrierTests(unittest.TestCase):
    def test_four_nonplanar_heights_survive_two_independent_triangles(self):
        source = payload.LiquidSurface((1, 2, 3), (0.2, 0.8, 0.4, 0.6), faces=1)
        batch = payload.batches([source])[0]
        observed = {}
        for carrier, third in batch.carriers:
            points = [payload.decode_vertex(carrier, third, corner) for corner in QUAD_CORNERS]
            self.assertEqual(points[0], points[3])
            self.assertEqual(len(set(points)), 3)
            for x, y, z in points:
                observed[x - 1, z - 3] = y - 2
        expected = dict(zip(((0, 0), (1, 0), (1, 1), (0, 1)), source.heights))
        self.assertEqual(set(observed), set(expected))
        for corner, height in expected.items():
            self.assertAlmostEqual(observed[corner], height)

    def test_side_upper_edges_use_the_same_corner_heights_as_top(self):
        source = payload.LiquidSurface((0, 0, 0), (0.2, 0.8, 0.4, 0.6))
        batch = payload.batches([source])[0]
        top = {}
        sides = {}
        for carrier, third in batch.carriers:
            kind = carrier[1] // 64
            points = [payload.decode_vertex(carrier, third, corner) for corner in QUAD_CORNERS]
            if kind < 2:
                top.update(((x, z), y) for x, y, z in points)
            elif kind < 6:
                self.assertEqual(points[0][1], 0)
                self.assertEqual(points[1][1], 0)
                sides.update(((x, z), y) for x, y, z in points[2:])
            else:
                self.assertTrue(all(point[1] == 0 for point in points))
        self.assertEqual(top, sides)

    def test_face_mask_changes_only_carrier_presence(self):
        source = payload.LiquidSurface((0, 0, 0), (0.2, 0.8, 0.4, 0.6))
        full = {kind: (third, left, right) for kind, third, left, right in payload.face_payloads(source)}
        for face in range(6):
            partial = payload.LiquidSurface((0, 0, 0), source.heights, faces=1 << face)
            actual = {kind: (third, left, right) for kind, third, left, right in payload.face_payloads(partial)}
            kinds = (0, 1) if face == 0 else ((6,) if face == 1 else (face,))
            self.assertEqual(actual, {kind: full[kind] for kind in kinds})

    def test_full_batch_has_448_unique_native_indices(self):
        sources = [payload.LiquidSurface(pos, (1, 1, 1, 1))
                   for pos in itertools.product(range(4), repeat=3)]
        for bits, volume_count in ((6, 1835008), (8, 29360128)):
            batch = payload.batches(sources, bits)[0]
            indices = [index for rows in batch.palette()['common'].values() for index in rows]
            self.assertEqual(len(indices), 448)
            self.assertEqual(len(set(indices)), 448)
            diagnostic = batch.diagnostic()
            self.assertEqual(diagnostic['palette_volume_indices'], volume_count)
            self.assertFalse(diagnostic['production_memory_accepted'])
            self.assertFalse(diagnostic['native_geometry_accepted'])

    def test_chunk_and_family_boundaries_remain_independent(self):
        sources = [payload.LiquidSurface((-1, 0, 0), (0, 0, 0, 0)),
                   payload.LiquidSurface((0, 0, 0), (1, 1, 1, 1)),
                   payload.LiquidSurface((0, 0, 0), (0.5, 0.5, 0.5, 0.5), family='lava')]
        batches = payload.batches(sources)
        self.assertEqual({(item.origin, item.family) for item in batches},
                         {((-4, 0, 0), 'water'), ((0, 0, 0), 'water'), ((0, 0, 0), 'lava')})
        with self.assertRaises(ValueError):
            payload.batches([sources[1], sources[1]])

    def test_quantization_is_bounded_and_never_fills_missing_heights(self):
        for bits in (6, 8):
            denominator = (1 << bits) - 1
            for index in range(2049):
                height = index / 2048
                self.assertLessEqual(abs(height - payload.quantize(height, bits) / denominator),
                                     0.5 / denominator + 1e-15)
        for height in (None, math.nan, math.inf, -0.01, 1.01, True):
            with self.assertRaises(ValueError):
                payload.quantize(height)
        with self.assertRaises(ValueError):
            payload.LiquidSurface((0, 0, 0), (0, 0, 0))

    def test_model_metadata_is_constant_legal_integer_uv_and_y(self):
        for code in range(256):
            model = generator.model(code)['netease:block_geometry']
            cube = model['bones'][0]['cubes'][0]
            self.assertEqual(cube['origin'][1] + cube['size'][1], 8)
            self.assertEqual(cube['size'], [8, 1, 8])
            self.assertEqual(set(cube['uv']), {'up'})
            uv = cube['uv']['up']
            self.assertEqual(uv['uv_size'], [0, 0])
            self.assertEqual(uv['uv'][0] + uv['uv'][1] * 64, code)

    def test_overlay_install_preserves_metadata_material_fields_and_exact_backup(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            overlay, project, backup = root / 'overlay', root / 'project', root / 'backup'
            originals = {
                'resource_pack/blocks.json': {'format_version': [1, 1, 0], 'minecraft:stone': {'sound': 'stone'}},
                'resource_pack/textures/terrain_texture.json': {'resource_pack_name': 'original', 'texture_data': {'stone': {'textures': 'stone'}}},
                'resource_pack/materials/entity.material': {'materials': {'version': '1.0.0', 'existing:base': {'vertexShader': 'original'}}},
                'resource_pack/materials/terrain.material': {'materials': {'version': '1.0.0', 'blend:base': {'+states': ['Blending'], '+defines': ['BLEND'], 'depthFunc': 'LessEqual'}}}}
            patches = {
                'resource_pack/blocks.json': {'format_version': [1, 1, 0], 'modern_projection:experiment': {'sound': 'stone'}},
                'resource_pack/textures/terrain_texture.json': {'texture_data': {'experiment': {'textures': 'experiment'}}},
                'resource_pack/materials/entity.material': {'materials': {'version': '1.0.0', 'experiment:entity_static': {'vertexShader': 'new'}}},
                'resource_pack/materials/terrain.material': {'materials': {'version': '1.0.0', 'blend:base': {'vertexShader': 'new', '+states': ['DisableCulling']}}},
                'resource_pack/shaders/glsl/experiment.vertex': 'shader'}
            original_bytes = {}
            for relative, content in originals.items():
                target = project / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                original_bytes[relative] = (json.dumps(content, indent=4) + '\n').encode('ascii')
                target.write_bytes(original_bytes[relative])
            hashes = {}
            for relative, content in patches.items():
                target = overlay / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content if isinstance(content, str) else json.dumps(content), encoding='ascii')
                hashes[relative] = generator.digest(target.read_bytes())
            (overlay / 'contract.json').write_text(json.dumps({'output_sha256': hashes}), encoding='ascii')
            report = generator.install_overlay(overlay, project, backup)
            for relative, original in original_bytes.items():
                self.assertEqual((backup / relative).read_bytes(), original)
            atlas = json.loads((project / 'resource_pack/textures/terrain_texture.json').read_bytes())
            self.assertEqual(atlas['resource_pack_name'], 'original')
            self.assertEqual(set(atlas['texture_data']), {'stone', 'experiment'})
            material = json.loads((project / 'resource_pack/materials/terrain.material').read_bytes())['materials']['blend:base']
            self.assertEqual(material['+states'], ['Blending', 'DisableCulling'])
            self.assertEqual(material['+defines'], ['BLEND'])
            self.assertEqual(material['depthFunc'], 'LessEqual')
            entity_materials = json.loads((project / 'resource_pack/materials/entity.material').read_bytes())['materials']
            self.assertEqual(entity_materials['existing:base'], {'vertexShader': 'original'})
            self.assertEqual(entity_materials['experiment:entity_static'], {'vertexShader': 'new'})
            self.assertFalse(report['native_geometry_accepted'])
            after = {path: (project / path).read_bytes() for path in hashes}
            with self.assertRaises(ValueError):
                generator.install_overlay(overlay, project, root / 'second_backup')
            self.assertFalse((root / 'second_backup').exists())
            self.assertEqual(after, {path: (project / path).read_bytes() for path in hashes})

    def test_overlay_hash_failure_leaves_project_and_backup_untouched(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            overlay, project, backup = root / 'overlay', root / 'project', root / 'backup'
            source = overlay / 'resource_pack/shaders/glsl/experiment.vertex'
            source.parent.mkdir(parents=True)
            source.write_text('changed shader', encoding='ascii')
            (overlay / 'contract.json').write_text(json.dumps({'output_sha256': {
                'resource_pack/shaders/glsl/experiment.vertex': generator.digest(b'original shader')}}), encoding='ascii')
            project.mkdir()
            with self.assertRaises(ValueError):
                generator.install_overlay(overlay, project, backup)
            self.assertFalse(backup.exists())
            self.assertEqual(list(project.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
