"""Native scaffold evidence must not silently widen to unmeasured states."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from generate_scaffold_support import capabilities, CATALOGUE_METHOD, generate


class ScaffoldSupportTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
        self.report = json.loads((ROOT / 'tools/data/native_scaffold_supports_nemc_3.9.0.401155.json').read_text(encoding='utf8'))

    def test_generated_table_matches_frozen_partial_evidence(self):
        result = generate(check=True)
        self.assertEqual('measured_samples', result['scope'])
        self.assertEqual(14, result['observed_states'])
        self.assertEqual(15844, result['unobserved_states'])
        data = capabilities(self.report, self.manifest)
        self.assertEqual((1,), data['partial']['minecraft:oak_slab'])
        self.assertEqual((0,), data['nonsupporting']['minecraft:oak_slab'])
        self.assertEqual((0,), data['unknown']['minecraft:cobblestone_wall'])

    def test_different_version_or_unrestored_world_cannot_generate_capabilities(self):
        for name, value in (('completed', False), ('restored', False),
                            ('palette_sha256', '0' * 64), ('game_version', 'NEMC next')):
            report = copy.deepcopy(self.report)
            report[name] = value
            with self.subTest(name=name), self.assertRaises(ValueError):
                capabilities(report, self.manifest)

    def test_changed_support_does_not_classify_requested_snapshot(self):
        report = copy.deepcopy(self.report)
        row = report['native']['rows'][0]
        support = next(cell for cell in row['cells'] if cell['pos'] == [0, 1, 0])
        support['value'] = {'name': 'minecraft:glass', 'aux': 0}
        data = capabilities(report, self.manifest)
        self.assertNotIn('minecraft:stone', data['blocks'])
        self.assertEqual((0,), data['unknown']['minecraft:stone'])

    def test_partial_evidence_cannot_be_relabelled_as_a_complete_catalogue(self):
        report = copy.deepcopy(self.report)
        report['method'] = CATALOGUE_METHOD
        report['native']['rows'] = [{'requested': ['minecraft:stone', 0]}]
        report['native']['states'] = 1
        with self.assertRaisesRegex(ValueError, 'does not cover'):
            capabilities(report, self.manifest)

    def test_duplicate_measurements_are_rejected(self):
        self.report['native']['rows'].append(copy.deepcopy(self.report['native']['rows'][0]))
        self.report['native']['cases'] += 1
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            capabilities(self.report, self.manifest)

    def test_boolean_stability_or_aux_cannot_classify_a_requested_support(self):
        for mutation in ('stability', 'support_aux', 'scaffold_aux'):
            report = copy.deepcopy(self.report)
            row = report['native']['rows'][0]
            support = next(cell for cell in row['cells'] if cell['pos'] == [0, 1, 0])
            scaffold = next(cell for cell in row['cells'] if cell['pos'] == [0, 2, 0])
            if mutation == 'stability':
                scaffold['states']['stability'] = False
            elif mutation == 'support_aux':
                support['value']['aux'] = False
            else:
                scaffold['value']['aux'] = True
            with self.subTest(mutation=mutation):
                data = capabilities(report, self.manifest)
                self.assertNotIn('minecraft:stone', data['blocks'])
                self.assertEqual((0,), data['unknown']['minecraft:stone'])

    def test_boolean_requested_aux_and_integer_native_byte_are_rejected(self):
        report = copy.deepcopy(self.report)
        report['native']['rows'][0]['metadata']['support'][1] = False
        with self.assertRaisesRegex(ValueError, 'unknown scaffold support states'):
            capabilities(report, self.manifest)
        report = copy.deepcopy(self.report)
        scaffold = next(cell for cell in report['native']['rows'][0]['cells'] if cell['pos'] == [0, 2, 0])
        self.assertIs(scaffold['states']['stability_check'], True)
        scaffold['states']['stability_check'] = 1
        with self.assertRaisesRegex(ValueError, 'Native scaffold state'):
            capabilities(report, self.manifest)


if __name__ == '__main__':
    unittest.main()
