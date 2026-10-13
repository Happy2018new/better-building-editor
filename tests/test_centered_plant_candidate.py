import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from generate_centered_plant_candidate import candidate
from generate_static_plant_proxies import SOURCE, outputs
from projection.cell import make_cell
from projection.model import Document
from projection.plant_position import POSITION_PLANT_PROXIES
from projection.render_context import prepare_context_batches
from verify_snow_h0_phase import PLANT_PROFILE_RESTORE, candidate_profile_install_code


class CenteredPlantCandidateTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads(SOURCE.read_bytes())

    def test_candidate_preserves_native_texture_and_disabled_default(self):
        original = copy.deepcopy(self.spec)
        generated = candidate(self.spec, 'poppy')
        registration = generated['registration.json']
        self.assertEqual(self.spec, original)
        self.assertFalse(registration['production_default_enabled'])
        self.assertFalse(registration['position_contract']['geometry_fit_allowed'])
        self.assertEqual([0., 0.], registration['position_contract']['xz_translation'])
        self.assertEqual('textures/blocks/flower_rose', registration['texture_entry']['textures'])
        self.assertEqual(.6875, registration['alpha_top_height'])
        self.assertFalse(POSITION_PLANT_PROXIES)

    def test_rotated_cross_stays_centered_inside_unit_cell(self):
        model = candidate(self.spec, 'poppy')['model.json']['netease:block_geometry']
        for bone in model['bones']:
            self.assertEqual([-8, 8, 8], bone['pivot'])
            cube, = bone['cubes']
            self.assertEqual(16, cube['size'][1])
            angle = math.radians(bone['rotation'][1])
            for edge in (0, cube['size'][0]):
                dx = cube['origin'][0] + edge - bone['pivot'][0]
                x = (bone['pivot'][0] + math.cos(angle) * dx) / -16.
                z = (bone['pivot'][2] - math.sin(angle) * dx) / 16.
                self.assertGreaterEqual(x, .1 - 1e-7)
                self.assertLessEqual(x, .9 + 1e-7)
                self.assertGreaterEqual(z, .1 - 1e-7)
                self.assertLessEqual(z, .9 + 1e-7)

    def test_refactor_preserves_every_existing_generated_model(self):
        for path, value in outputs(self.spec).items():
            if path.parent.name == 'netease_block':
                self.assertEqual(json.loads(path.read_bytes()), value)

    def test_opt_in_prepares_dry_and_snow_overlay_without_mutating_document(self):
        registration = candidate(self.spec, 'poppy')['registration.json']
        proxy, top = registration['identifier'], registration['alpha_top_height']
        flower = ('minecraft:poppy', 0)
        for covered in (False, True):
            value = make_cell(('minecraft:snow_layer', 8), flower) if covered else flower
            doc = Document((3, 3, 3), {(1, 1, 1): value})
            saved = copy.deepcopy(doc.to_data())
            with patch.dict(POSITION_PLANT_PROXIES, {flower: lambda position: (proxy, top)}):
                result = prepare_context_batches(doc, doc.palette_data(), render_origin=(5, -49, 5))
            batches = result['_context_batches']
            self.assertEqual(saved, doc.to_data())
            layer = next(data for origin, context, data in batches if context != covered)
            self.assertIn((proxy, 0), layer['common'])
            self.assertEqual([273 if covered else 20805], layer['common'][(proxy, 0)])
        self.assertFalse(POSITION_PLANT_PROXIES)

    def test_retained_artifact_matches_generator_and_hashes_without_host_paths(self):
        directory = ROOT / 'tools/data/centered-plant-candidate-r12-v1'
        index = json.loads((directory / 'index.json').read_bytes())
        generated = candidate(self.spec, 'poppy')
        for name, value in generated.items():
            raw = (directory / name).read_bytes()
            self.assertEqual(index['files'][name]['sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(index['files'][name]['bytes'], len(raw))
            self.assertEqual(value, json.loads(raw))
        source = generated['registration.json']['source']
        for key in ('manifest', 'template'):
            self.assertFalse(Path(source[key]).is_absolute())
            self.assertEqual(source[key + '_sha256'], hashlib.sha256((ROOT / source[key]).read_bytes()).hexdigest())

    def test_runtime_opt_in_restores_default_after_interrupted_observation(self):
        registration = candidate(self.spec, 'poppy')['registration.json']
        contract = dict(registration['position_contract'], identifier=registration['identifier'],
                        alpha_top_height=registration['alpha_top_height'], production_default_enabled=False)
        runtime = SimpleNamespace()
        module = ModuleType('modern_projection.projection.plant_position')
        profiles = module.POSITION_PLANT_PROXIES = {}
        context = {'sys': runtime, 'json': json}
        with patch.dict(sys.modules, {module.__name__: module}):
            exec(candidate_profile_install_code(contract), context)
            self.assertEqual((registration['identifier'], .6875), profiles[('minecraft:poppy', 0)]((6, -48, 6)))
            exec(PLANT_PROFILE_RESTORE, context)
            exec(PLANT_PROFILE_RESTORE, context)
        self.assertFalse(profiles)
        self.assertFalse(hasattr(runtime, '_snow_h0_plant_profiles'))
        self.assertEqual({'default_empty': True, 'journal_absent': True}, json.loads(context['_result']))

    def test_runtime_candidate_rejects_offset_fit_and_enabled_default(self):
        registration = candidate(self.spec, 'poppy')['registration.json']
        contract = dict(registration['position_contract'], identifier=registration['identifier'],
                        alpha_top_height=registration['alpha_top_height'], production_default_enabled=False)
        for key, value in (('xz_translation', [-.116666, 0.]), ('geometry_fit_allowed', True),
                           ('production_default_enabled', True), ('unit_cross_height', .8),
                           ('native_random_offset_applied', True)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                candidate_profile_install_code(dict(contract, **{key: value}))
        self.assertIsNone(candidate_profile_install_code(None))


if __name__ == '__main__':
    unittest.main()
