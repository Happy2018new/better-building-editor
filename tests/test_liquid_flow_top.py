"""Flow-top candidate math, opt-in ownership and version boundaries; no native claims."""
import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / 'tools'))
from projection import liquid_deployment, liquid_flow_top_data, liquid_resource_data, liquid_shape_data
from projection.liquid_flow_top import candidate_flow_uv, rotation_code, top_uv, check_version
from projection.cell import make_cell
from projection.debug_blueprints import material
from projection.model import Document
from projection.liquid_render_plan import iter_groups
from projection.liquid_transport import pack_group
from generate_liquid_flow_top import DEFAULT_SOURCE, validate, verify_native, runtime_source
from generate_liquid_deployment import resource_profile
from generate_liquid_skeleton_resources import mesh, top_vertex, VERTEX


class FlowTopCandidateTests(unittest.TestCase):
    def setUp(self):
        self.water = material('flowing_water', {'liquid_depth': 3})
        self.document = Document((4, 3, 4), {(1, 1, 1): self.water})

    def choice(self, heights):
        return candidate_flow_uv(self.document, (1, 1, 1), 0, self.water, heights)

    def test_axis_diagonal_and_all_256_turn_codes_have_explicit_meanings(self):
        for expected in range(256):
            angle = expected * 2. * math.pi / 256.
            self.assertEqual(expected, rotation_code(math.cos(angle), math.sin(angle)))
        for x, z, expected in ((1, 0, 0), (0, 1, 64), (-1, 0, 128), (0, -1, 192),
                                (1, 1, 32), (-1, 1, 96), (-1, -1, 160), (1, -1, 224)):
            self.assertEqual(expected, rotation_code(x, z))
        self.assertIsNone(rotation_code(0, 0))

    def test_corner_gradient_turns_and_mirrors_with_the_snapshot(self):
        heights = (.89, .43, .17, .64)
        code = self.choice(heights)[1][1]
        # Quarter turn (x,z)->(-z,x): new NW,NE,SE,SW = old SW,NW,NE,SE.
        self.assertEqual((code + 64) % 256, self.choice((heights[3],) + heights[:3])[1][1])
        # Reflect x: NW,NE,SE,SW = old NE,NW,SW,SE.
        self.assertEqual((128 - code) % 256, self.choice((heights[1], heights[0], heights[3], heights[2]))[1][1])
        self.assertEqual((-code) % 256, self.choice((heights[3], heights[2], heights[1], heights[0]))[1][1])

    def test_uv_inverse_rotation_is_equivariant_and_stays_inside_full_frame(self):
        for code in range(256):
            for u, v in ((0., 0.), (1., 0.), (1., 1.), (0., 1.), (.137, .269), (.5, .5)):
                actual = top_uv(u, v, code)
                rotated = top_uv(1. - v, u, (code + 64) % 256)
                reflected = top_uv(1. - u, v, (128 - code) % 256)
                self.assertTrue(all(.146 <= axis <= .854 for axis in actual))
                for a, b in zip(actual, rotated):
                    self.assertAlmostEqual(a, b, places=12)
                self.assertAlmostEqual(actual[0], reflected[0], places=12)
                self.assertAlmostEqual(1. - actual[1], reflected[1], places=12)
        self.assertEqual((.25, .25), top_uv(0., 0., 0))
        self.assertEqual((.75, .75), top_uv(1., 1., 0))

    def test_flat_saddle_and_every_saved_depth_keep_unknown_direction_candidate_still(self):
        for name in ('water', 'flowing_water'):
            for depth in range(16):
                value = material(name, {'liquid_depth': depth})
                document = Document((3, 3, 3), {(1, 1, 1): value})
                for heights in ((.5,) * 4, (.7, .3, .7, .3), (1.,) * 4):
                    self.assertEqual(('still_water_grey', None),
                                     candidate_flow_uv(document, (1, 1, 1), 0, value, heights))
        self.assertFalse(liquid_flow_top_data.NATIVE_DIRECTION_VERIFIED)
        self.assertFalse(liquid_flow_top_data.NATIVE_UV_ACCEPTED)
        self.assertFalse(liquid_flow_top_data.PRODUCTION_ACCEPTED)

    def test_opt_in_routes_top_and_side_separately_without_changing_complete_input(self):
        values = {(1, 1, 1): make_cell(material('oak_fence'), self.water, {'tag': [1, 2]}),
                  (0, 1, 1): material('water', {'liquid_depth': 0}),
                  (2, 1, 1): material('water', {'liquid_depth': 7}),
                  (1, 1, 2): material('stone')}
        document = Document((4, 3, 4), values)
        before = copy.deepcopy(document.to_data())
        default = liquid_deployment.candidate_profile()
        candidate = liquid_deployment.candidate_profile(flowing_top=True)
        default_parts = default.provider_factory(document).surface(document, (1, 1, 1), 1, self.water)
        parts = candidate.provider_factory(document).surface(document, (1, 1, 1), 1, self.water)
        self.assertIsNone(default.flow_uv)
        self.assertEqual(liquid_resource_data.RESOURCES['models'],
                         tuple((key[0], key[1], value, default.world_models[key]) for key, value in default.models.items()))
        flowing = next(part for part in parts if part.faces == 1)
        self.assertEqual('flowing_water_grey', flowing.texture_key)
        self.assertEqual(liquid_flow_top_data.TEMPLATE, flowing.flow_uv[0])
        signature = lambda part, mask=63: (part.position, part.layer, part.heights,
                                           part.faces & mask, part.texture_key, part.flow_uv)
        self.assertEqual([signature(part, 62) for part in default_parts if part.faces & 62],
                         [signature(part, 62) for part in parts if part.faces & 62])
        self.assertEqual(default_parts[0].heights, flowing.heights)
        full = list(iter_groups(document, candidate.provider_factory(document)))
        targets = document.palette_data(lambda pos: pos == (1, 1, 1))
        selected = list(iter_groups(document, candidate.provider_factory(document), targets))
        selected_shapes = [shape for group in selected for shape in group.surfaces]
        self.assertEqual([signature(shape) for group in full for shape in group.surfaces
                          if shape.position == (1, 1, 1)], [signature(shape) for shape in selected_shapes])
        packed = pack_group((0, 0, 0), (flowing,), (255, 255, 255), None, 1.)
        self.assertEqual(flowing.flow_uv[1], int(packed[0][0]) // 4096)
        self.assertEqual(before, document.to_data())
        self.assertIsNone(liquid_deployment.production_profile())

    def test_source_document_and_invalid_numbers_are_rejected(self):
        for heights in ((.5,) * 3, (True,) * 4, (float('nan'),) * 4, (float('inf'),) * 4, (1.1,) * 4):
            with self.assertRaises(ValueError):
                self.choice(heights)
        for code in (-1, 256, True, .5):
            with self.assertRaises(ValueError):
                top_uv(.5, .5, code)
        with self.assertRaises(ValueError):
            candidate_flow_uv(self.document, (1, 1, 1), 1, self.water, (.8, .2, .2, .8))
        with patch.object(liquid_flow_top_data, 'SHAPE_CANDIDATE_SHA256', '0' * 64):
            with self.assertRaisesRegex(ValueError, 'regeneration'):
                check_version()

    def test_top_model_mesh_decoder_and_resource_contract_are_distinct(self):
        value = mesh('test', top_only=True)['mesh'][0]
        self.assertEqual(16, len(value['vertices']))
        self.assertEqual(8, len(value['indices']))
        self.assertTrue(all(vertex['normal'] == (0., 1., 0.) for vertex in value['vertices']))
        self.assertIn('floor(code/4096.0)>0.5', VERTEX)
        self.assertNotIn('floor(code/4096.0)>0.5', top_vertex(VERTEX))
        contract = json.loads((ROOT / 'tools/data/liquid_deployment_r12_contract.json').read_bytes())
        profile = resource_profile(contract, flowing_top=True)
        self.assertEqual(tuple(range(256)), profile['uv_rotations'][-1][-1])
        self.assertNotEqual(profile['models'][-1][1], profile['side_templates']['flowing_water_grey'][0])
        contract['model_options']['modern_projection_liquid_flowing_water_grey_top']['sampling']['region'] = 'nw'
        with self.assertRaisesRegex(ValueError, 'sampling differs'):
            resource_profile(contract, flowing_top=True)

    def test_regeneration_binds_version_rule_flags_and_installed_metadata(self):
        source = json.loads(DEFAULT_SOURCE.read_bytes())
        manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_bytes())
        self.assertEqual(runtime_source(validate(source, manifest)),
                         (ROOT / 'behavior_pack/modern_projection/projection/liquid_flow_top_data.py').read_text(encoding='ascii'))
        for field, value in (('game_version', 'future'), ('shape_candidate_sha256', '0' * 64),
                              ('native_direction_verified', True), ('native_uv_accepted', True),
                              ('production_accepted', True), ('rotation_codes', [0])):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate(dict(source, **{field: value}), manifest)
        with tempfile.TemporaryDirectory() as temporary:
            native = Path(temporary)
            sample = copy.deepcopy(source)
            import hashlib
            for relative in sample['native_source_sha256']:
                path = native / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(relative.encode())
                sample['native_source_sha256'][relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            verify_native(sample, native)
            path.write_bytes(b'drift')
            with self.assertRaisesRegex(ValueError, 'regenerate and requalify'):
                verify_native(sample, native)

    def test_host_pixel_report_binds_candidate_and_independent_verifier(self):
        import hashlib
        report = json.loads((ROOT / 'tools/data/liquid_flow_top_host_gles_r12.json').read_bytes())
        self.assertTrue(report['passed'])
        self.assertEqual(28512, report['checks'])
        self.assertEqual(56, len(report['results']))
        self.assertEqual(hashlib.sha256((ROOT / 'tools/data/liquid_deployment_r12_contract.json').read_bytes()).hexdigest(),
                         report['contract_sha256'])
        self.assertEqual(hashlib.sha256((ROOT / 'tools/verify_liquid_skeleton_resources.py').read_bytes()).hexdigest(),
                         report['verifier_sha256'])
        self.assertTrue(all(row['passed'] and not row['failures'] for row in report['results']))


if __name__ == '__main__':
    unittest.main()
