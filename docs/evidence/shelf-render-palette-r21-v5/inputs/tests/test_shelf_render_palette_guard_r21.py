"""Explicit semantic states survive preparation and bound the narrow proxy."""
import copy
import inspect
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'behavior_pack/modern_projection')]

from projection.block_registry import states
from projection.geometry_palette import prepare_palette
from shelf_render_palette_candidate_r21 import SOURCE, PROXY, replace_body_palette

EXPECTED_STATES = {'minecraft:cardinal_direction': 'south',
                   'powered_bit': False, 'powered_shelf_type': 0}


class ShelfRenderPaletteGuardTests(unittest.TestCase):
    def palette(self, record):
        return {'volume': (1, 1, 1), 'common': {SOURCE: [0]}, 'extra': {},
                'states': {SOURCE: record},
                'actor': {SOURCE[0]: {0: {'Items': ['opaque inventory payload']}}}}

    def test_supplied_north_state_is_legal_prepared_input_and_keeps_body_actor_and_nbt(self):
        record = dict(EXPECTED_STATES, **{'minecraft:cardinal_direction': 'north'})
        raw = self.palette(record)
        before = copy.deepcopy(raw)
        prepared = prepare_palette(raw)
        self.assertEqual(record, prepared['states'][SOURCE])
        result = replace_body_palette(prepared)
        self.assertIs(prepared, result)
        self.assertEqual([0], result['common'][SOURCE])
        self.assertNotIn(PROXY, result['common'])
        self.assertEqual(raw['actor'], result['actor'])
        self.assertEqual(before, raw)

    def test_unknown_powered_partial_and_wrong_nbt_scalar_types_are_preserved(self):
        records = [dict(EXPECTED_STATES, powered_bit=True),
                   dict(EXPECTED_STATES, powered_shelf_type=1),
                   dict(EXPECTED_STATES, powered_bit=0),
                   dict(EXPECTED_STATES, powered_shelf_type=False),
                   {'minecraft:cardinal_direction': 'south'},
                   dict(EXPECTED_STATES, charged=True), None]
        for record in records:
            with self.subTest(record=record):
                source = self.palette(record)
                before = copy.deepcopy(source)
                self.assertIs(source, replace_body_palette(source))
                self.assertEqual(before, source)

    def test_empty_missing_and_exact_canonical_states_accept_the_measured_candidate(self):
        self.assertEqual(EXPECTED_STATES, states(SOURCE))
        for record in ({}, states(SOURCE)):
            source = self.palette(record)
            before = copy.deepcopy(source)
            result = replace_body_palette(source)
            self.assertEqual([0], result['common'][PROXY])
            self.assertNotIn(SOURCE, result['states'])
            self.assertEqual({}, result['actor'])
            self.assertEqual(before, source)
        source = self.palette({})
        del source['states']
        self.assertEqual([0], replace_body_palette(source)['common'][PROXY])

    def test_context_batches_guard_each_palette_without_losing_the_other_target(self):
        south = self.palette(dict(EXPECTED_STATES))
        north = self.palette(dict(EXPECTED_STATES, **{'minecraft:cardinal_direction': 'north'}))
        source = {'volume': (2, 1, 1), '_context_schema': 2,
                  '_context_batches': [((0, 0, 0), True, south), ((16, 0, 0), False, north)]}
        before = copy.deepcopy(source)
        result = replace_body_palette(source)
        self.assertEqual(source['volume'], result['volume'])
        self.assertEqual(source['_context_schema'], result['_context_schema'])
        self.assertEqual([row[:2] for row in source['_context_batches']],
                         [row[:2] for row in result['_context_batches']])
        self.assertIn(PROXY, result['_context_batches'][0][2]['common'])
        self.assertIs(north, result['_context_batches'][1][2])
        self.assertEqual(before, source)

    def test_runtime_probe_embeds_the_guard_without_additional_module_globals(self):
        namespace = {'SOURCE': SOURCE, 'PROXY': PROXY}
        exec(inspect.getsource(replace_body_palette), namespace)
        runtime = namespace['replace_body_palette']
        self.assertIn(PROXY, runtime(self.palette(dict(EXPECTED_STATES)))['common'])
        north = self.palette(dict(EXPECTED_STATES, **{'minecraft:cardinal_direction': 'north'}))
        self.assertIs(north, runtime(north))


if __name__ == '__main__':
    unittest.main()
