import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from generate_centered_plant_candidate import candidate
from generate_static_plant_proxies import SOURCE, outputs
from isolated_centered_plant import install, restore
from projection.cell import make_cell
from projection.model import Document
from projection.plant_position import POSITION_PLANT_PROXIES
from projection.render_context import prepare_context_batches
from verify_snow_h0_phase import (CROP, PLANT_PROFILE_RESTORE, candidate_profile_install_code,
                                  capture_schedule, plant_positive_controls)
from verify_snow_h0_phase import clear_native_for_projection
from PIL import Image, ImageDraw
from supervise_snow_h0 import COPY_TARGETS, validate_preparation_sources


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


class IsolatedCandidateResourcesTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name)
        self.output = self.project / 'run'
        self.output.mkdir()
        self.directory = ROOT / 'tools/data/centered-plant-candidate-r12-v1'
        self.original = {}
        for relative in ('resource_pack/blocks.json', 'resource_pack/textures/terrain_texture.json'):
            target = self.project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = (ROOT / relative).read_bytes()
            target.write_bytes(raw)
            self.original[relative] = raw

    def test_resource_install_and_repeat_restore_preserve_exact_original_bytes_and_absence(self):
        value = install(self.project, self.directory, self.output)
        self.assertFalse(value['production_acceptance'])
        self.assertTrue(all(row['attempted'] for row in value['rows']))
        for unused in range(2):
            self.assertTrue(restore(self.project, self.output)['restored'])
            for relative, raw in self.original.items():
                self.assertEqual(raw, (self.project / relative).read_bytes())
            self.assertFalse((self.project / 'behavior_pack/netease_blocks/diagnostic_centered_poppy.json').exists())
            self.assertFalse((self.project / 'resource_pack/models/netease_block/diagnostic_centered_poppy.json').exists())

    def test_partial_install_failure_keeps_prewrite_journal_and_restores_prior_writes(self):
        original_replace = Path.replace
        def replace(path, destination):
            if Path(destination).name == 'diagnostic_centered_poppy.json' and 'models' in Path(destination).parts:
                raise OSError('injected resource publication failure')
            return original_replace(path, destination)
        with patch.object(Path, 'replace', replace), self.assertRaises(OSError):
            install(self.project, self.directory, self.output)
        self.assertTrue(restore(self.project, self.output)['restored'])
        for relative, raw in self.original.items():
            self.assertEqual(raw, (self.project / relative).read_bytes())
        self.assertFalse(list(self.output.glob('centered-install-*.bin')))

    def test_external_resource_change_is_reported_and_preserved_while_other_resources_restore(self):
        install(self.project, self.directory, self.output)
        altered = self.project / 'resource_pack/blocks.json'
        altered.write_bytes(b'External write must be preserved')
        value = restore(self.project, self.output)
        self.assertFalse(value['restored'])
        self.assertIn('External resource change: resource_pack/blocks.json', value['errors'])
        self.assertEqual(b'External write must be preserved', altered.read_bytes())
        other = 'resource_pack/textures/terrain_texture.json'
        self.assertEqual(self.original[other], (self.project / other).read_bytes())

    def test_candidate_schedule_establishes_both_plant_controls_before_any_snow_capture(self):
        plan = {'plant_candidate': {'identifier': 'diagnostic'}, 'capture_schedule': 'candidate_positive_first'}
        schedule = capture_schedule(plan)
        self.assertEqual([('native', 'plant'), ('native', 'blank'), ('projection', 'plant'), ('projection', 'blank')], schedule[:4])
        self.assertEqual(8, len(set(schedule)))
        with self.assertRaises(ValueError):
            capture_schedule({'plant_candidate': {}})

    def test_early_positive_controls_reject_missing_projection_without_granting_geometry_acceptance(self):
        paths = {'native': {}, 'projection': {}}
        for mode in paths:
            for kind in ('plant', 'blank'):
                image = Image.new('RGB', (1994, 1105))
                if mode == 'native' and kind == 'plant':
                    ImageDraw.Draw(image).rectangle((600, 400, 619, 419), fill=(255, 0, 0))
                path = self.output / (mode + '-' + kind + '.png')
                image.save(path)
                paths[mode][kind] = path
        roi = Image.new('L', (CROP[2] - CROP[0], CROP[3] - CROP[1]), 255)
        result = plant_positive_controls(paths, roi, self.output)
        self.assertEqual(400, result['modes']['native']['plant_pixels'])
        self.assertEqual(0, result['modes']['projection']['plant_pixels'])
        self.assertFalse(result['passed'])
        self.assertFalse(result['geometry_fidelity_accepted'])
        self.assertFalse(result['production_acceptance'])

    def test_projection_controls_clear_real_target_after_any_native_state_order(self):
        reference = {'NATIVE_MUTATE': 'mutate(%r,%r,%r)'}
        for order in (('covered', 'snow', 'plant'), ('plant', 'snow', 'covered'), ('snow', 'covered', 'plant')):
            state = {'target': 'covered', 'support': 'minecraft:stone'}
            calls = []
            def run(code, server=False):
                calls.append((code, server))
                if server:
                    self.assertEqual("mutate('poppy','blank',0)", code)
                    state['target'] = 'minecraft:air'
                    return {'front': {'name': 'minecraft:air'}, 'back': {'name': 'minecraft:air'}}
                return {'common': [[state['target'], 0]], 'extra': [['minecraft:air', 0]]}
            def wait(label, predicate, read):
                value = read()
                self.assertTrue(predicate(value))
                return value
            for kind in order:
                state['target'] = 'minecraft:poppy' if kind == 'plant' else 'minecraft:snow_layer'
                result = clear_native_for_projection(run, wait, reference, 'palette')
                self.assertEqual('minecraft:air', state['target'])
                self.assertEqual('minecraft:stone', state['support'])
                self.assertEqual([['minecraft:air', 0]], result['palette_before']['common'])
            self.assertEqual(3, len([row for row in calls if row[1]]))

    def test_same_file_cold_copy_input_is_refused_before_preparation(self):
        keys = ('instances', 'mcdk_client', 'config')
        files = {key: {'path': str(self.output / (key + '.input'))} for key in keys}
        validate_preparation_sources(self.project, files)
        for target, key in zip(COPY_TARGETS, keys):
            altered = dict(files, **{key: {'path': str(self.project / target)}})
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'frozen separately'):
                validate_preparation_sources(self.project, altered)


if __name__ == '__main__':
    unittest.main()
