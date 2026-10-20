"""Public product cases have independent state, closure and visibility gates."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.cell import AIR, foreground, make_cell
import check_blueprint_neighbor_context as context_audit
from projection.debug_blueprints import BLUEPRINTS, VISUAL_CASES, build, material
from projection.debug_product_connections import METADATA, VISUAL_CASE, source_document
from projection.model import Document, Editor
from verify_product_connection_matrix import CENTER_BODY, LOAD_BODY, body_presence, offline_report
from verify_product_connection_matrix import finalize_report
from verify_chest_occupied_frozen_holdout import occupancy_plan


def normalized(blocks):
    low = tuple(min(pos[i] for pos in blocks) for i in range(3))
    return dict((tuple(pos[i] - low[i] for i in range(3)), value)
                for pos, value in blocks.items() if foreground(value) != AIR)


class PublicConnectionMatrixTests(unittest.TestCase):
    def test_registered_public_fixture_has_independent_supported_cases(self):
        self.assertIn(METADATA, BLUEPRINTS)
        self.assertIs(VISUAL_CASES['product_connections'], VISUAL_CASE)
        document = build(METADATA[0])
        self.assertEqual(19, len(VISUAL_CASE['cases']))
        body_positions = set()
        for row in VISUAL_CASE['cases']:
            supports = set(pos for pos, unused, states in row['supports'])
            self.assertTrue(supports)
            self.assertTrue(supports.isdisjoint(row['cells']))
            self.assertTrue(body_positions.isdisjoint(row['cells']))
            body_positions.update(row['cells'])
            for pos, name, states in row['supports'] + row['blocks']:
                self.assertTrue(document.contains(pos), row['id'])
                self.assertEqual(material(name, states), document.get(pos), row['id'])
                actual = registry.states(document.get(pos))
                for key, expected in states.items():
                    self.assertEqual(expected, actual[key], (row['id'], key))
            self.assertEqual({'editor_presence': 'pending', 'editor_shape': 'pending',
                              'full': 'pending', 'missing': 'pending'}, row['acceptance'])

    def test_stair_literals_match_public_rotation_and_mirror_transactions(self):
        expected_directions = {
            'stairs_outer_turn90': (2, 0), 'stairs_outer_mirror_x': (1, 3),
            'stairs_inner_mirror_z': (0, 2), 'stairs_inner_inverted_turn90': (2, 0)}
        for row in VISUAL_CASE['cases'][:4]:
            with self.subTest(case=row['id']):
                self.assertEqual(expected_directions[row['id']],
                                 tuple(states['weirdo_direction'] for pos, name, states in row['blocks']))
                separation = tuple(row['occupied'][i] - row['keep'][i] for i in range(3))
                offset = row['camera']['offset']
                self.assertEqual(0., separation[0]*offset[0] + separation[2]*offset[2])
                blocks = dict((pos, material(name, states)) for pos, name, states in row['source_blocks'])
                document = Document(VISUAL_CASE['size'], blocks)
                editor = Editor(document)
                positions = tuple(blocks)
                editor.select_box(tuple(min(pos[i] for pos in positions) for i in range(3)),
                                  tuple(max(pos[i] for pos in positions) for i in range(3)))
                before = document.blocks.copy()
                self.assertGreater(editor.run(row['operation']), 0)
                expected = dict((pos, material(name, states)) for pos, name, states in row['blocks'])
                self.assertEqual(normalized(expected), normalized(document.blocks))
                after = document.blocks.copy()
                self.assertTrue(editor.undo())
                self.assertEqual(before, document.blocks)
                self.assertTrue(editor.redo())
                self.assertEqual(after, document.blocks)

    def test_body_documents_exclude_supports_without_mutating_public_source(self):
        public = build(METADATA[0])
        before = public.blocks.copy()
        for row in VISUAL_CASE['cases']:
            body = source_document(row['id'], False)
            self.assertEqual(set(row['cells']), set(body.blocks))
            self.assertEqual(dict((pos, public.get(pos)) for pos in row['cells']), body.blocks)
            body.blocks[row['keep']] = AIR
        self.assertEqual(before, public.blocks)

    def test_only_normal_rail_curves_and_every_slope_is_supported(self):
        rows = dict((row['id'], row) for row in VISUAL_CASE['cases'])
        self.assertEqual(6, rows['rail_supported_curve']['blocks'][0][2]['rail_direction'])
        for name in ('rail', 'golden_rail', 'detector_rail', 'activator_rail'):
            row = rows[name + '_supported_slope']
            self.assertEqual((1, 2, 1), tuple(states['rail_direction'] for pos, name, states in row['blocks']))
            self.assertEqual(1, row['occupied'][1] - row['keep'][1])
            supports = set(pos for pos, name, states in row['supports'])
            self.assertIn((row['occupied'][0], row['occupied'][1] - 1, row['occupied'][2]), supports)

    def test_context_erase_history_pass_but_never_claim_native_pixels(self):
        report = offline_report()
        self.assertTrue(report['passed'])
        self.assertEqual(19, len(report['rows']))
        self.assertTrue(report['palette_sha256'])
        self.assertTrue(report['source_fingerprints'])
        for row in report['rows']:
            self.assertTrue(row['erased_group'] and row['retained_other_bodies'])
            self.assertEqual({'editor': None, 'full': None, 'missing': None}, row['visual_acceptance'])

    def test_wrong_group_closure_cannot_pass_cpu_acceptance(self):
        row = VISUAL_CASE['cases'][-1]
        with patch.dict(row, {'group_closure': (row['keep'],)}):
            report = offline_report()
        self.assertFalse(report['passed'])
        self.assertFalse(report['rows'][-1]['passed'])

    def test_independent_slope_oracle_rejects_missing_wrong_and_duplicated_bodies(self):
        source = source_document('rail_supported_slope')
        case = next(row for row in VISUAL_CASE['cases'] if row['id'] == 'rail_supported_slope')
        target = case['keep']
        prepare = context_audit.prepare_document_context
        for fault in ('missing', 'wrong_material', 'context_duplicate', 'duplicate_slot', 'conflicting_slot'):
            def damaged(document, targets, fault=fault):
                data = prepare(document, targets)
                body_slot = context_audit.index(context_audit.overlay_position(target), data['volume'])
                value = next(value for value, slots in data['common'].items() if body_slot in slots)
                if fault == 'missing':
                    data['common'][value].remove(body_slot)
                elif fault == 'wrong_material':
                    data['common'][value].remove(body_slot)
                    data['common'].setdefault(material('stone'), []).append(body_slot)
                elif fault == 'context_duplicate':
                    context_slot = context_audit.index(context_audit.context_position(target), data['volume'])
                    data['common'][value].append(context_slot)
                elif fault == 'duplicate_slot':
                    data['common'][value].append(body_slot)
                else:
                    data['common'].setdefault(material('stone'), []).append(body_slot)
                return data
            with self.subTest(fault=fault), patch.object(context_audit, 'prepare_document_context', damaged):
                self.assertFalse(context_audit.compare_target(source, target)['passed'])

    def test_slope_secondary_layer_and_neighbor_slope_omission_are_both_checked(self):
        case = next(row for row in VISUAL_CASE['cases'] if row['id'] == 'rail_supported_slope')
        source = source_document(case['id'])
        slope, flat = case['keep'], case['occupied']
        self.assertTrue(context_audit.compare_target(source, slope)['passed'])
        self.assertTrue(context_audit.compare_target(source, flat)['passed'])
        source.blocks[slope] = make_cell(foreground(source.get(slope)), material('water'))
        self.assertTrue(context_audit.compare_target(source, slope)['passed'])
        self.assertTrue(context_audit.compare_target(source, flat)['passed'])
        prepare = context_audit.prepare_document_context
        def missing_secondary(document, targets):
            data = prepare(document, targets)
            data['extra'] = {}
            return data
        with patch.object(context_audit, 'prepare_document_context', missing_secondary):
            self.assertFalse(context_audit.compare_target(source, slope)['passed'])
            self.assertFalse(context_audit.compare_target(source, flat)['passed'])

    def test_editor_camera_uses_scene_relative_coordinates(self):
        emitted = []
        session = SimpleNamespace(scene_origin=(16, 0, 32),
                                  camera_view=lambda *view: setattr(session, 'camera_pose', view),
                                  emit=lambda: emitted.append(True))
        scope = {'s': session, 'json': json}
        exec(CENTER_BODY % ((20.5, 2.5, 36.5), (35., 25., 3.)), scope)
        self.assertEqual((4.5, 2.5, 4.5), session.camera_pivot)
        self.assertEqual((35., 25., 3.), session.camera_pose)
        self.assertEqual([True], emitted)
        compile(LOAD_BODY % 'stairs_outer_turn90', '<public-body-load>', 'exec')


class ProductBodyPixelTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.shown, self.hidden, self.output = (self.root / name for name in ('shown.png', 'hidden.png', 'diff.png'))
        Image.new('RGB', (120, 80)).save(self.hidden)

    def tearDown(self):
        self.directory.cleanup()

    def test_disconnected_halves_are_counted_together(self):
        image = Image.new('RGB', (120, 80))
        draw = ImageDraw.Draw(image)
        draw.rectangle((10, 10, 15, 17), fill='white')
        draw.rectangle((40, 10, 45, 17), fill='white')
        image.save(self.shown)
        result = body_presence(self.shown, self.hidden, (0, 0, 100, 70), self.output)
        self.assertEqual(96, result['pixels'])
        self.assertTrue(result['passed'])
        self.assertIsNone(result['independent_shape_acceptance'])

    def test_blank_weak_and_outside_viewport_signals_fail(self):
        for fill, rectangle in (('black', (10, 10, 40, 40)),
                                ((15, 15, 15), (10, 10, 40, 40)),
                                ('white', (105, 5, 119, 50))):
            image = Image.new('RGB', (120, 80))
            ImageDraw.Draw(image).rectangle(rectangle, fill=fill)
            image.save(self.shown)
            self.assertFalse(body_presence(self.shown, self.hidden, (0, 0, 100, 70), self.output)['passed'])

    def test_dimension_and_crop_changes_are_rejected(self):
        Image.new('RGB', (120, 80)).save(self.shown)
        with self.assertRaises(ValueError):
            body_presence(self.shown, self.hidden, (-1, 0, 100, 70), self.output)
        Image.new('RGB', (120, 81)).save(self.shown)
        with self.assertRaises(ValueError):
            body_presence(self.shown, self.hidden, (0, 0, 100, 70), self.output)


class ChestOccupancyPlanTests(unittest.TestCase):
    def test_either_half_reserves_only_that_world_cell_and_measures_the_other(self):
        cells = ((-20, 10, 40), (-19, 10, 40))
        for half, index in (('main', 0), ('sub', 1)):
            plan = occupancy_plan(cells, half)
            self.assertEqual(cells[index], plan['occupied_world'])
            self.assertEqual(cells[1-index], plan['remaining_world'])
            self.assertEqual((2, 1) if index == 0 else (1, 2), plan['expected'])
            self.assertEqual(((2, 1, 1) if index == 0 else (1, 1, 1)), plan['remaining_focus'])

    def test_nonpair_or_unknown_half_is_rejected(self):
        for cells, half in ((((0, 0, 0),), 'main'),
                            (((0, 0, 0), (0, 0, 0)), 'sub'),
                            (((0, 0, 0), (1, 0, 0)), 'all')):
            with self.assertRaises(ValueError):
                occupancy_plan(cells, half)


class ProductFinalReportTests(unittest.TestCase):
    def test_grid_restore_failure_overrides_a_previous_success_and_keeps_fingerprints(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'report.json'
            output.write_text(json.dumps({'completed': True, 'passed': True, 'restored': True,
                                          'cleanup_errors': []}), encoding='utf8')
            with patch('verify_product_connection_matrix.source_fingerprints', return_value=['frozen']), \
                 patch('verify_product_connection_matrix.production_fingerprint', return_value={'sha256': 'fixed'}):
                passed = finalize_report(output, ['frozen'], {'sha256': 'fixed'}, 'grid: ConnectionError: gone')
            report = json.loads(output.read_text(encoding='utf8'))
            self.assertFalse(passed)
            self.assertFalse(report['passed'])
            self.assertFalse(report['restored'])
            self.assertEqual(['grid: ConnectionError: gone'], report['cleanup_errors'])
            self.assertTrue(report['source_unchanged'] and report['production_unchanged'])

    def test_source_or_production_drift_rejects_a_previous_success(self):
        for tools, production in ((['changed'], {'sha256': 'fixed'}),
                                  (['frozen'], {'sha256': 'changed'})):
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / 'report.json'
                output.write_text(json.dumps({'completed': True, 'passed': True, 'restored': True}), encoding='utf8')
                with patch('verify_product_connection_matrix.source_fingerprints', return_value=tools), \
                     patch('verify_product_connection_matrix.production_fingerprint', return_value=production):
                    self.assertFalse(finalize_report(output, ['frozen'], {'sha256': 'fixed'}))

    def test_failure_before_first_report_still_leaves_an_explicit_failed_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'new' / 'report.json'
            with patch('verify_product_connection_matrix.source_fingerprints', return_value=['frozen']), \
                 patch('verify_product_connection_matrix.production_fingerprint', return_value={'sha256': 'fixed'}):
                self.assertFalse(finalize_report(output, ['frozen'], {'sha256': 'fixed'}))
            report = json.loads(output.read_text(encoding='utf8'))
            self.assertFalse(report['completed'] or report['passed'] or report['restored'])


if __name__ == '__main__':
    unittest.main()
