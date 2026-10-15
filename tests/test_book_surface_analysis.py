"""Cover raster corruption must be detected without flagging texture edges."""
from pathlib import Path
from copy import deepcopy
from contextlib import redirect_stdout
import hashlib
import io
import json
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_book_surface_r17 import (analyze, artwork_distribution, isolated_cover_pixels,
                                     owner_matrix, MAX_ISOLATED_PIXELS)


def independent_report(path):
    receipt = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
               'reliable': True, 'frame': {'frame_qpc_100ns': 1}}
    result = dict(schema_version=2, engine='3.10.0.420447', owner_path='independent_book',
                  owner_matrix=True, model_prefix='', stage='candidate_adapter', completed=True,
                  restored=True, source_unchanged=True, candidate_setup=True,
                  candidate_restoration=True, cleanup_errors=[], rows={}, captures={})
    for case, family in (('enchanting_table', 'enchanting_table'),
                         ('lectern.book', 'lectern'), ('lectern.empty', None)):
        model = 'modern_projection_book_'+family if family else None
        result['rows'][case] = {'ready': {'book': dict(owned=True, ready=True, pending=False,
            error='', groups=[['key', model]] if model else [])}}
        suffixes = ['yaw35', 'yaw215']
        if model:
            suffixes += ['yaw35_pitch75_zoom3', 'yaw215_pitch25_zoom1', 'yaw35_pitch25_zoom2',
                         'section_layer2', 'section_layer3', 'single_layer2', 'single_layer3',
                         'full_layer3', 'hidden', 'restored']
        for suffix in suffixes:
            visible = model is not None and suffix not in ('section_layer2', 'single_layer2', 'hidden')
            result['captures']['editor_'+case+'_'+suffix] = {'capture': deepcopy(receipt),
                'book_models': dict(active=False, preview_owned=True, models=[], preview_groups=int(visible))}
        for route in ('full', 'missing'):
            suffixes = ['motion0', 'opacity0.35', 'opacity0.7', 'opacity1.0']
            if family == 'enchanting_table': suffixes += ['motion1', 'motion2']
            for suffix in suffixes:
                opacity = float(suffix[7:]) if suffix.startswith('opacity') else 1.
                result['captures'][route+'_'+case+'_'+suffix] = {'capture': deepcopy(receipt),
                    'book_models': dict(active=True, preview_owned=False, preview_groups=0,
                        models=[model+'_world'] if model else [], world_opacity=[opacity] if model else [])}
    for index, row in enumerate(result['captures'].values()):
        row['capture']['frame']['frame_qpc_100ns'] = int((index+1)*2e7)
    return result


class BookSurfaceAnalysisTests(unittest.TestCase):
    def analyze_report(self, directory, report):
        source, output = directory/'report.json', directory/'analysis.json'
        source.write_text(json.dumps(report), encoding='ascii')
        with redirect_stdout(io.StringIO()):
            return analyze(source, output)

    def test_independent_labels_measure_surface_without_inventing_native_artwork(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            path = directory/'book.png'
            Image.new('RGB', (500, 400), (129, 86, 37)).save(path)
            report = independent_report(path)
            result = self.analyze_report(directory, report)
            for gate in ('owner_matrix_passed', 'timeline_valid', 'scale_valid', 'surface_regression_passed'):
                self.assertTrue(result[gate], gate)
            self.assertFalse(result['artwork_reference_valid'])
            self.assertFalse(result['raster_regression_passed'])
            self.assertGreaterEqual(result['candidate_count'], 16)
            report['captures']['full_lectern.empty_motion0']['book_models']['models'] = ['invented_book']
            self.assertFalse(self.analyze_report(directory, report)['owner_matrix_passed'])

    def test_owner_readback_rejects_wrong_model_opacity_hidden_and_missing_receipts(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'book.png'
            Image.new('RGB', (500, 400), (129, 86, 37)).save(path)
            original = independent_report(path)
            for label, key, value in (
                    ('full_enchanting_table_motion0', 'models', ['wrong_model']),
                    ('missing_lectern.book_opacity0.35', 'world_opacity', [1.]),
                    ('editor_lectern.book_hidden', 'preview_groups', 1)):
                report = deepcopy(original)
                report['captures'][label]['book_models'][key] = value
                self.assertFalse(owner_matrix(report)['passed'])
            report = deepcopy(original)
            del report['captures']['editor_lectern.book_restored']
            self.assertFalse(owner_matrix(report)['passed'])
            original['captures']['editor_lectern.empty_yaw35']['capture']['sha256'] = '0'*64
            with self.assertRaisesRegex(ValueError, 'receipt'):
                owner_matrix(original)

    def test_legacy_native_candidate_report_still_passes_both_raster_checks(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            path = directory/'book.png'
            Image.new('RGB', (500, 400), (129, 86, 37)).save(path)
            receipt = independent_report(path)['captures']['editor_enchanting_table_yaw35']['capture']
            report = dict(completed=True, restored=True, source_unchanged=True, cleanup_errors=[], captures={})
            for prefix, count in (('native', 2), ('candidate', 16)):
                for index in range(count):
                    row = {'capture': deepcopy(receipt)}
                    row['capture']['frame']['frame_qpc_100ns'] = int((index+1)*2e7)
                    report['captures'][prefix+'_enchanting_table_motion'+str(index)] = row
            result = self.analyze_report(directory, report)
            self.assertIsNone(result['owner_matrix_passed'])
            self.assertTrue(result['artwork_reference_valid'])
            self.assertTrue(result['raster_regression_passed'])

    def test_real_occupancy_evidence_requires_air_restore_and_an_unchanged_document(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'book.png'
            Image.new('RGB', (500, 400), (129, 86, 37)).save(path)
            report = independent_report(path)
            report['occupancy_matrix'] = True
            for case, family in (('enchanting_table', 'enchanting_table'), ('lectern.book', 'lectern')):
                source = {'volume':[8,8,8], 'logical':'original typed NBT'}
                report['rows'][case]['source_document'] = source
                occupancy = report['rows'][case]['occupancy'] = {}
                for suffix, material in (('occupied','minecraft:stone'), ('restored','minecraft:air')):
                    row = deepcopy(report['captures']['missing_'+case+'_motion0'])
                    if suffix == 'occupied':row['book_models']['models'] = []
                    report['captures']['missing_'+case+'_'+suffix] = row
                    occupancy[suffix] = [{'after':{'name':material}}]
                    occupancy[suffix+'_source_document'] = deepcopy(source)
            self.assertTrue(owner_matrix(report)['passed'])
            report['rows']['lectern.book']['occupancy']['restored_source_document']['size'] = {
                '__type__':'tuple', '__repr__':'(8, 8, 8)'}
            report['rows']['lectern.book']['source_document']['size'] = [8,8,8]
            report['rows']['lectern.book']['occupancy']['occupied_source_document']['size'] = [8,8,8]
            self.assertTrue(owner_matrix(report)['passed'])
            report['rows']['lectern.book']['occupancy']['restored'][0]['after']['name'] = 'minecraft:stone'
            self.assertFalse(owner_matrix(report)['passed'])
            report['rows']['lectern.book']['occupancy']['restored'][0]['after']['name'] = 'minecraft:air'
            report['rows']['lectern.book']['occupancy']['restored_source_document']['logical'] = 'changed'
            self.assertFalse(owner_matrix(report)['passed'])
    def test_artwork_detects_inside_face_without_confusing_exposure(self):
        outside = np.full((100, 100, 3), (129., 86., 37.))
        outside[:20] = (78., 51., 22.)
        inside = np.full((100, 100, 3), (78., 51., 22.))
        inside[:40] = (129., 86., 37.)
        self.assertAlmostEqual(.2, artwork_distribution(outside))
        self.assertAlmostEqual(.2, artwork_distribution(outside*.8))
        self.assertAlmostEqual(.6, artwork_distribution(inside))

    def test_narrow_cover_does_not_grant_artwork_acceptance(self):
        image = np.full((60, 80, 3), (129., 86., 37.))
        self.assertIsNone(artwork_distribution(image))

    def test_uniform_and_artwork_regions_do_not_report_speckles(self):
        image = np.full((60, 80, 3), (77, 51, 22), dtype=np.int16)
        image[10:40, 15:60] = (106, 71, 30)
        self.assertEqual(0, isolated_cover_pixels(image).sum())

    def test_isolated_corrupted_fragments_exceed_noise_limit(self):
        image = np.full((60, 80, 3), (77, 51, 22), dtype=np.int16)
        image[5:55:5, 5:75:5] = (106, 71, 30)
        self.assertGreater(isolated_cover_pixels(image).sum(), MAX_ISOLATED_PIXELS)

    def test_white_page_fragments_inside_uniform_cover_are_not_filtered_out(self):
        image = np.full((60, 80, 3), (129, 86, 37), dtype=np.int16)
        image[5:55:5, 5:75:5] = (220, 220, 210)
        self.assertGreater(isolated_cover_pixels(image).sum(), MAX_ISOLATED_PIXELS)

    def test_foliage_and_crosshair_are_not_book_cover_corruption(self):
        image = np.full((60, 80, 3), (18, 65, 12), dtype=np.int16)
        image[5:55:5, 5:75:5] = (77, 51, 22)
        image[25:30, 20:50] = (200, 220, 240)
        self.assertEqual(0, isolated_cover_pixels(image).sum())
