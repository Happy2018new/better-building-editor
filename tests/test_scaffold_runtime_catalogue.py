"""Real semantic readbacks survive aux differences; unknown is never negative."""
import copy
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import probe_scaffold_runtime_catalogue as probe
import derive_scaffold_runtime_support as derive
import test_scaffold_runtime_lifecycle as harness


class RuntimeCatalogueTests(harness.RuntimeLifecycleTests):
    def setUp(self):
        super().setUp()
        self.native.GetBlockStatesFromAuxValue = lambda name, aux: probe.common.registry.states((name, aux))
        self.addCleanup(lambda: vars(sys).pop(probe.MARKER, None))

    def start(self, start=0, count=24):
        return self.execute(probe.start_payload(start, count, self.identity, 'a' * 64, True, harness.AIR_ENCODING))

    def restore(self):
        return self.execute(probe.restore_payload(self.identity))

    def complete(self, start=0, count=24):
        initial = self.start(start, count)
        while self.native.timers:
            self.native.timers.pop(0)()
        native = self.execute(probe.STATUS % (probe.MARKER, self.identity))
        cleanup = self.restore()
        return {'schema': probe.SCHEMA, 'method': probe.METHOD, 'game_version': probe.common.registry.SOURCE_VERSION,
                'palette_sha256': probe.common.registry.SOURCE_SHA256, 'completed': True,
                'restored': cleanup['restored'], 'source_sha256': 'a' * 64, 'identity': self.identity,
                'start': initial, 'native': native, 'cleanup': cleanup, 'range': [start, start + count],
                'plans': probe.plans(start, count), 'air_encoding': harness.AIR_ENCODING,
                'acceptance': derive.ACCEPTANCE, 'payload_sha256': {name: probe.common.digest(code.encode('utf8'))
                    for name, code in (('start', probe.start_payload(start, count, self.identity, 'a' * 64, True, harness.AIR_ENCODING)),
                        ('status', probe.STATUS % (probe.MARKER, self.identity)), ('restore', probe.restore_payload(self.identity)))}}

    def test_eight_slots_are_reused_in_bounded_callbacks_and_both_layers_reset(self):
        report = self.complete()
        rows = derive.validate_segment(report, 'a' * 64)
        self.assertEqual(24, len(rows))
        self.assertEqual(3, len(report['native']['batches']))
        self.assertEqual(8, len(report['start']['slots']))
        self.assertEqual(136, report['start']['reserved'])
        self.assertEqual(1, self.native.max_pending_timers)
        self.assertTrue(report['cleanup']['restored'])
        self.assertTrue(all(row['states'] is None for row in report['cleanup']['air_readbacks']))
        self.assertTrue(any(row['returned'] is False for row in report['cleanup']['air_reset_returns']))
        self.assertFalse(hasattr(sys, probe.MARKER))

    def test_changed_support_and_missing_native_scaffold_states_remain_unknown(self):
        pair = probe.common.registry.from_states('minecraft:oak_stairs', {'weirdo_direction': 0, 'upside_down_bit': True})
        expected = probe.common.registry.states(pair)
        material = {'front': {'name': pair[0], 'aux': 999}, 'states': copy.deepcopy(expected)}
        scaffold_states = {'stability': 0, 'stability_check': True}
        row = {'requested': list(pair), 'expected_states': expected, 'converted_aux': 999,
               'conversion_states': expected, 'semantic_set_returned': True, 'support_written': material,
               'scaffold_written': {'support': material}, 'upper_before_scaffold': {'front': {'name': 'minecraft:air', 'aux': 0}, 'liquid': None},
               'delayed': {'support': material, 'scaffold': {'front': {'name': 'minecraft:scaffolding', 'aux': 999}, 'states': scaffold_states}}}
        self.assertTrue(derive.classify(row))
        for change in ('different_support', 'missing', 'typed', 'conversion', 'door_upper'):
            altered = copy.deepcopy(row)
            if change == 'different_support':
                altered['delayed']['support']['states']['upside_down_bit'] = False
            elif change == 'missing':
                altered['delayed']['scaffold']['states'] = None
            elif change == 'typed':
                altered['delayed']['scaffold']['states']['stability'] = False
            elif change == 'conversion':
                altered['converted_aux'] = -1
            else:
                altered['upper_before_scaffold']['front']['name'] = 'minecraft:oak_door'
            with self.subTest(change=change):
                self.assertIsNone(derive.classify(altered))
        row['delayed']['scaffold']['states']['stability'] = 7
        self.assertFalse(derive.classify(row))

    def test_segments_need_real_layer_proof_typed_plans_and_no_overlap(self):
        original = self.complete()
        for change in ('palette', 'source', 'state_type', 'incomplete', 'policy'):
            report = copy.deepcopy(original)
            if change == 'palette':
                report['native']['batches'][0]['after']['readbacks'][0]['palette']['extra'] = [[['minecraft:stone', 0], [0]]]
            elif change == 'source':
                report['payload_sha256']['start'] = 'b' * 64
            elif change == 'state_type':
                report['plans'][0]['expected_states']['button_pressed_bit'] = 0
            elif change == 'incomplete':
                report['native']['rows'].pop()
            else:
                report['cleanup']['flow_restored'] = False
            with self.subTest(change=change), self.assertRaises(ValueError):
                derive.validate_segment(report)
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            derive.capabilities([original, original])
        with self.assertRaisesRegex(ValueError, 'every dumped'):
            derive.capabilities([original], require_full=True)

    def test_namespace_collision_and_late_timer_do_not_leak_world_writes(self):
        self.start(count=16)
        callback = self.native.timers.pop()
        self.scope.update(block=None, state=None, info=None, game=None, probe=None, read=None, observe=None)
        callback()
        self.assertEqual(1, len(self.native.timers))
        late = self.native.timers.pop()
        self.assertTrue(self.restore()['restored'])
        writes = len(self.native.writes)
        late()
        self.assertEqual(writes, len(self.native.writes))

    def test_payloads_compile_for_native_python2(self):
        pypy = Path('C:/Users/Happy2018new/Desktop/PyPy/pypy2.exe')
        if not pypy.is_file():
            self.skipTest('Game Python2 unavailable')
        for code in (probe.start_payload(0, 24, self.identity, 'a' * 64, True, harness.AIR_ENCODING),
                     probe.STATUS % (probe.MARKER, self.identity), probe.restore_payload(self.identity)):
            result = subprocess.run([str(pypy), '-c', 'compile(%r,"semantic-catalogue","exec")' % code],
                                    capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
