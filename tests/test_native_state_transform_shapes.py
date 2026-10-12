"""Native transform evidence must distinguish shapes and reject stale captures."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from capture_native_state_transform_shapes import (DEFAULT_NAMES, WRITE_CELLS, door_pair_palettes,
                                                   matrix, rays, reserve_positions, states_exact)
import analyze_native_state_transform_shapes as analyzer


def cube_hit(pos, ray):
    position = list(ray['start'])
    axis = next(index for index, value in enumerate(ray['direction']) if value)
    position[axis] = 0. if ray['direction'][axis] > 0 else 1.
    return [{'type': 'Block', 'pos': list(pos), 'identifier': 'minecraft:stone',
             'hitPos': [pos[index] + position[index] for index in range(3)]}]


def enclosing_cube_capture():
    sampling = rays()
    requested, supports = matrix(('minecraft:oak_stairs',), (4, 100, 4))
    observed = []
    for row in requested:
        pos = row['pos']
        air = row['value'][0] == 'minecraft:air'
        unit = {'min': list(pos), 'max': [axis + 1 for axis in pos]}
        observed.append({'pos': list(pos), 'value': list(row['value']), 'states': row['states'],
                         'clip': None if air else unit, 'collision': None if air else unit,
                         'rays': [None if air else cube_hit(pos, ray) for ray in sampling]})
    snapshot = {'runtime': '1.21.120.0', 'rows': observed}
    return {'schema': 1, 'completed': True, 'restored': True, 'cleanup': {'restored': True},
            'setup': {'reserved': [list(row['pos']) for row in requested]},
            'client_air_after_cleanup': [{'pos': list(row['pos']), 'value': ['minecraft:air', 0]}
                                         for row in requested],
            'game_version': analyzer.registry.source_version(),
            'palette_sha256': analyzer.registry.fingerprint(),
            'preflight': {'runtime': snapshot['runtime']},
            'names': ['minecraft:oak_stairs'], 'requested': requested, 'supports': supports,
            'rays': sampling, **{key: copy.deepcopy(snapshot) for key in
             ('server_first', 'client_first', 'server_later', 'client_later')}}


def first_box_hit(pos, ray, boxes):
    axis = next(index for index, value in enumerate(ray['direction']) if value)
    sign = ray['direction'][axis]
    candidates = []
    for low, high in boxes:
        if not all(low[index] <= ray['start'][index] <= high[index]
                   for index in range(3) if index != axis):
            continue
        near = low[axis] if sign > 0 else high[axis]
        distance = (near - ray['start'][axis]) / sign
        if 0 <= distance <= ray['distance']:
            hit = list(ray['start'])
            hit[axis] = near
            candidates.append((distance, hit))
    if not candidates:
        return None
    hit = min(candidates)[1]
    return [{'type': 'Block', 'pos': list(pos), 'identifier': 'minecraft:oak_stairs',
             'hitPos': [pos[index] + hit[index] for index in range(3)]}]


def synthetic_stair_capture():
    raw = enclosing_cube_capture()
    # Explicit primitive boxes exercise the evidence parser, not native acceptance.
    steps = {0: ((.5, 0., 0.), (1., 1., 1.)),
             1: ((0., 0., 0.), (.5, 1., 1.)),
             2: ((0., 0., .5), (1., 1., 1.)),
             3: ((0., 0., 0.), (1., 1., .5))}
    for snapshot in ('server_first', 'client_first', 'server_later', 'client_later'):
        for row in raw[snapshot]['rows']:
            if row['value'][0] != 'minecraft:oak_stairs':
                continue
            upper = row['states']['upside_down_bit']
            full_half = ((0., .5, 0.), (1., 1., 1.)) if upper else ((0., 0., 0.), (1., .5, 1.))
            low, high = steps[row['states']['weirdo_direction']]
            half_step = ((low[0], 0. if upper else .5, low[2]),
                         (high[0], .5 if upper else 1., high[2]))
            row['rays'] = [first_box_hit(row['pos'], ray, (full_half, half_step)) for ray in rays()]
    return raw


class NativeStateTransformShapeTests(unittest.TestCase):
    def test_atomic_door_palette_preserves_both_native_half_records(self):
        rows, unused = matrix(('minecraft:wooden_door',), (4, 100, 4))
        paired = door_pair_palettes(rows)
        self.assertEqual(16, len(paired))
        by_position = {tuple(row['pos']): row for row in rows}
        for origin, data in paired:
            self.assertEqual((1, 1, 2), data['volume'])
            for index in range(2):
                row = by_position[(origin[0], origin[1] + index, origin[2])]
                value = tuple(row['value'])
                self.assertEqual([index], data['common'][value])
                self.assertEqual(row['states'], data['states'][value])
        rows[1]['states'] = dict(rows[1]['states'], door_hinge_bit=True)
        with self.assertRaisesRegex(ValueError, 'matching upper half'):
            door_pair_palettes(rows)

    def test_restored_failed_native_door_setup_cannot_be_accepted(self):
        path = ROOT / 'tools/data/native_state_transform_shapes_r11.door-failed.json'
        raw = json.loads(path.read_bytes())
        self.assertTrue(raw['restored'])
        self.assertEqual(574, len(raw['client_air_after_cleanup']))
        with self.assertRaisesRegex(ValueError, 'complete and restored'):
            analyzer.analyze(raw)

    def test_frozen_native_capture_verifies_current_targets_and_probe_bytes(self):
        source = ROOT / 'tools/data/native_state_transform_shapes_r11.raw.json'
        raw_bytes = source.read_bytes()
        self.assertEqual('1625d5598300f74c9f83530628a9cecf69b663da6edbbe563946f33220e8e970',
                         hashlib.sha256(raw_bytes).hexdigest())
        raw = json.loads(raw_bytes)
        probe = ROOT / 'tools/data/native_state_transform_shapes_r11.probe.py'
        self.assertEqual(raw['probe_source_sha256'], hashlib.sha256(probe.read_bytes()).hexdigest())
        report = analyzer.analyze(raw)
        self.assertEqual(144, report['checks'])
        self.assertEqual([], report['mismatches'])
        self.assertTrue(report['physical_orientation_accepted'])
        self.assertEqual({'minecraft:oak_stairs': 8, 'minecraft:trapdoor': 6},
                         {row['name']: row['distinct_native_shapes'] for row in report['discrimination']})

    def test_frozen_native_rays_refuse_wrong_stair_mirror_targets(self):
        raw = json.loads((ROOT / 'tools/data/native_state_transform_shapes_r11.raw.json').read_bytes())
        def incorrect(source, operation):
            if source[0] == 'minecraft:oak_stairs' and operation in ('mirror_x', 'mirror_y'):
                return source
            return analyzer.state_transform.transform(source, operation)
        report = analyzer.analyze(raw, incorrect)
        self.assertFalse(report['native_shape_consistency'])
        self.assertFalse(report['physical_orientation_accepted'])
        self.assertEqual({'mirror_x', 'mirror_y'}, {row['operation'] for row in report['mismatches']})

    def test_only_empty_native_state_spellings_are_equivalent(self):
        self.assertTrue(states_exact(None, {}))
        self.assertFalse(states_exact(None, {'open_bit': False}))
        self.assertFalse(states_exact({'open_bit': False}, {'open_bit': 0}))

    def test_native_auto_created_door_half_is_reused_only_when_exact(self):
        lower, upper = ('minecraft:wooden_door', 0), ('minecraft:wooden_door', 8)
        cells = [((4, 100, 4), lower), ((4, 101, 4), upper)]
        values, properties, writes = {}, {}, []
        class Adapter:
            @staticmethod
            def _native_tree(value):
                return value
            def read(self, pos):
                return values.get(pos)
            def write(self, pos, value):
                writes.append((pos, value))
                values.update(cells)
                properties.update((p, analyzer.registry.states(v)) for p, v in cells)
                return value == lower
        class State:
            def GetBlockStates(self, pos, dimension):
                return properties.get(pos)
        namespace = dict(cells=cells, adapter=Adapter(), state=State(), dimension=0,
                         registry=analyzer.registry)
        exec(WRITE_CELLS, namespace)
        self.assertEqual([cells[0]], writes)
        self.assertEqual([cells[1][0]], namespace['reused'])
        properties[cells[1][0]] = dict(properties[cells[1][0]], upper_block_bit=1)
        with self.assertRaisesRegex(AssertionError, 'write failed'):
            exec(WRITE_CELLS, namespace)

    def test_reserve_plan_exists_before_native_setup_can_fail(self):
        rows, supports = matrix(DEFAULT_NAMES, (4, 100, 4))
        reserved = reserve_positions(rows, supports)
        self.assertEqual(574, len(reserved))
        for pos, value in supports + [(row['pos'], row['value']) for row in rows]:
            self.assertIn(pos, reserved)
            for axis in range(3):
                for sign in (-1, 1):
                    neighbor = tuple(pos[i] + (sign if i == axis else 0) for i in range(3))
                    self.assertIn(neighbor, reserved)

    def test_first_fixture_covers_every_selected_native_record(self):
        requested, supports = matrix(DEFAULT_NAMES, (4, 100, 4))
        values = [tuple(row['value']) for row in requested if not row['control']]
        expected = {(name, aux) for name in DEFAULT_NAMES for aux in analyzer.registry.aux_values(name)}
        self.assertEqual(expected, set(values))
        self.assertEqual(len(values), len(set(values)))
        self.assertEqual(58, len(requested))
        self.assertEqual(40, len(supports))
        self.assertFalse({tuple(row['pos']) for row in requested}.intersection(dict(supports)))

    def test_symmetrical_ray_plan_closes_under_every_coordinate_operation(self):
        sampling = rays()
        self.assertEqual(16, len(sampling))
        native = {'clip': ((0., 0., 0.), (1., 1., 1.)), 'collision': None,
                  'rays': tuple(tuple(hit[0]['hitPos']) for hit in
                                (cube_hit((0, 0, 0), ray) for ray in sampling))}
        for operation in analyzer.OPERATIONS:
            self.assertEqual(native, analyzer.reflected_shape(native, sampling, operation))

    def test_enclosing_aabbs_cannot_accept_stair_physical_orientation(self):
        report = analyzer.analyze(enclosing_cube_capture())
        self.assertEqual(48, report['checks'])
        self.assertTrue(report['native_shape_consistency'])
        self.assertFalse(report['physical_orientation_accepted'])
        self.assertEqual(1, report['discrimination'][0]['distinct_native_shapes'])

    def test_native_float_noise_does_not_invent_discriminating_shapes(self):
        raw = enclosing_cube_capture()
        for key in ('server_first', 'client_first', 'server_later', 'client_later'):
            for index, row in enumerate(raw[key]['rows']):
                if row['value'][0] == 'minecraft:oak_stairs':
                    row['clip']['max'][0] += index * .0000003
                    for hit in row['rays']:
                        hit[0]['hitPos'][0] += index * .0000003
        report = analyzer.analyze(raw)
        self.assertTrue(report['native_shape_consistency'])
        self.assertEqual(1, report['discrimination'][0]['distinct_native_shapes'])
        self.assertFalse(report['physical_orientation_accepted'])
        self.assertFalse(analyzer.coordinates_equal((0.,), (.00002,)))
        self.assertFalse(analyzer.coordinates_equal(None, (0.,)))

    def test_discriminating_rays_detect_wrong_stair_mirror_and_half(self):
        raw = synthetic_stair_capture()
        report = analyzer.analyze(raw)
        self.assertTrue(report['physical_orientation_accepted'])
        self.assertEqual(8, report['discrimination'][0]['distinct_native_shapes'])
        def incorrect(source, operation):
            if operation in ('mirror_x', 'mirror_y'):
                return source
            return analyzer.state_transform.transform(source, operation)
        failed = analyzer.analyze(raw, incorrect)
        self.assertFalse(failed['native_shape_consistency'])
        self.assertFalse(failed['physical_orientation_accepted'])
        self.assertEqual({'mirror_x', 'mirror_y'}, {row['operation'] for row in failed['mismatches']})
        self.assertTrue(all(row['different'] == ['rays'] for row in failed['mismatches']))

    def test_native_side_time_state_type_change_is_rejected(self):
        raw = enclosing_cube_capture()
        raw['client_later']['rows'][0]['states']['upside_down_bit'] = 0
        with self.assertRaisesRegex(ValueError, 'typed states differ'):
            analyzer.analyze(raw)

    def test_native_ray_hit_change_is_rejected(self):
        raw = enclosing_cube_capture()
        raw['server_later']['rows'][0]['rays'][0][0]['hitPos'][0] += .125
        with self.assertRaisesRegex(ValueError, 'changed across side/time'):
            analyzer.analyze(raw)

    def test_native_external_hit_and_invalid_coordinates_are_rejected(self):
        raw = enclosing_cube_capture()
        raw['server_first']['rows'][0]['rays'][0][0]['pos'][0] += 1
        with self.assertRaisesRegex(ValueError, 'external block'):
            analyzer.analyze(raw)
        with self.assertRaises(ValueError):
            analyzer.box({'min': [0, 0, 0], 'max': [1, float('nan'), 1]}, (0, 0, 0))

    def test_stale_incomplete_unrestored_and_duplicate_records_are_rejected(self):
        for kind in ('stale', 'incomplete', 'unrestored', 'duplicate', 'client_residue'):
            raw = enclosing_cube_capture()
            if kind == 'stale':
                raw['palette_sha256'] = '0' * 64
            elif kind == 'incomplete':
                raw['requested'].pop(0)
            elif kind == 'unrestored':
                raw['cleanup']['restored'] = False
            elif kind == 'duplicate':
                raw['requested'].append(raw['requested'][0])
            else:
                raw['client_air_after_cleanup'][0]['value'] = ['minecraft:stone', 0]
            with self.assertRaises(ValueError, msg=kind):
                analyzer.analyze(raw)

    def test_native_asymmetric_slab_reflection_differs_from_quarter_turn(self):
        north = ((0., 0., 0.), (1., 1., .1875))
        self.assertEqual(north, analyzer.reflected_box(north, 'mirror_x'))
        self.assertEqual(((0., 0., .8125), (1., 1., 1.)),
                         analyzer.reflected_box(north, 'mirror_z'))
        self.assertEqual(((.8125, 0., 0.), (1., 1., 1.)),
                         analyzer.reflected_box(north, 'rotate_y90'))


if __name__ == '__main__':
    unittest.main()
