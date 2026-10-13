"""Air None is evidence; missing nonair states cannot become inferred states."""
import copy
from pathlib import Path
import subprocess
import sys
import unittest
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import probe_scaffold_state_lifecycle as base
import probe_scaffold_runtime_lifecycle as probe
import test_scaffold_state_lifecycle as legacy_tests

AIR_ENCODING = {'common': [[['minecraft:air', 0], [0]]], 'extra': []}


class RuntimeLifecycleTests(legacy_tests.ScaffoldStateLifecycleTests):
    # Use the native stub wiring, without inheriting the v1 acceptance tests.
    def setUp(self):
        super().setUp()
        self.addCleanup(lambda: vars(sys).pop(probe.MARKER, None))
        native = self.native
        previous = native.GetBlockStates
        def raw(pos, dimension):
            if native.GetBlockNew(pos, dimension)['name'] == 'minecraft:air':
                return None
            return previous(pos, dimension)
        native.GetBlockStates = raw
        def palette(dimension, low, high, eliminate):
            self.assertEqual(low, high)
            self.assertFalse(eliminate)
            value = native.GetBlockNew(low, dimension)
            return types.SimpleNamespace(SerializeBlockPalette=lambda: {
                'volume': (1, 1, 1), 'common': {(value['name'], value['aux']): [0]},
                'extra': {}, 'states': {}, 'extraStates': {}, 'actor': {}, 'void': False, 'eliminateAir': False})
        native.GetBlockPaletteBetweenPos = palette
        previous_clear = native.SetBlockByBlockPalette
        def clear(*args):
            was_air = native.GetBlockNew(args[2], args[1])['name'] == 'minecraft:air'
            previous_clear(*args)
            return not was_air
        native.SetBlockByBlockPalette = clear

    def start(self, allowed=True):
        return self.execute(probe.start_payload(self.identity, 'a' * 64, allowed, AIR_ENCODING))

    def restore(self, identity=None):
        return self.execute(probe.native_restore() % (probe.MARKER, identity or self.identity))

    def complete(self):
        start = self.start()
        while self.native.timers:
            self.native.timers.pop(0)()
        native = self.execute(base.STATUS % (probe.MARKER, self.identity))
        cleanup = self.restore()
        return {'schema': 2, 'kind': probe.KIND, 'method': probe.METHOD, 'source_sha256': 'a' * 64,
                'template_sha256': 'b' * 64, 'identity': self.identity, 'completed': True,
                'air_encoding': AIR_ENCODING, 'air_observation_sha256': 'd' * 64,
                'restored': cleanup['restored'], 'start': start, 'native': native, 'cleanup': cleanup,
                'actor_data': base.ACTOR_SCOPE, 'acceptance': probe.ACCEPTANCE,
                'game_executable_sha256': 'c' * 64,
                'payload_sha256': {name: base.digest(code.encode('utf8')) for name, code in
                    (('start', probe.start_payload(self.identity, 'a' * 64, True, AIR_ENCODING)),
                     ('status', base.STATUS % (probe.MARKER, self.identity)),
                     ('restore', probe.native_restore() % (probe.MARKER, self.identity)))}}


# Only the v2 cases below run against the common stub harness.
for _name in list(vars(legacy_tests.ScaffoldStateLifecycleTests)):
    if _name.startswith('test_'):
        setattr(RuntimeLifecycleTests, _name, None)


def valid(report):
    return probe.validate_report(report, 'a' * 64, 'b' * 64)


class RuntimeLifecycleCases(RuntimeLifecycleTests):
    def test_raw_air_none_survives_both_cleanup_and_all_lifecycle_phases(self):
        report = self.complete()
        result = valid(report)
        self.assertTrue(result['positive_control_matched'])
        self.assertEqual((4, 66, 4), tuple(report['start']['origin']))
        self.assertTrue(all(row['states'] is None for row in report['start']['baseline']))
        self.assertTrue(all(row['states'] is None for row in report['start']['setup']['explicit_air_readbacks']))
        self.assertTrue(all(row['states'] is None for row in report['cleanup']['air_readbacks']))
        self.assertEqual(19 * 17, len(self.native.clears))
        self.assertTrue(all(row['returned'] is False for row in report['start']['setup']['explicit_air_resets']))
        self.assertEqual({}, base.cell_at(report['native']['rows'][-1]['samples'][2], (0, 0, 0))['states'])
        self.assertEqual(probe.ACCEPTANCE, result['acceptance'])
        self.assertFalse(hasattr(sys, probe.MARKER))

    def test_missing_nonair_states_stops_and_keeps_raw_value(self):
        read = self.native.GetBlockStates
        self.native.GetBlockStates = lambda pos, dim: None if self.native.GetBlockNew(pos, dim)['name'] == 'minecraft:stone' else read(pos, dim)
        self.start()
        native = self.execute(base.STATUS % (probe.MARKER, self.identity))
        self.assertFalse(native['done'])
        self.assertEqual('support_written', native['error']['stage'])
        actual = base.cell_at(native['rows'][0]['samples'][0], (0, 0, 0))
        self.assertIsNone(actual['states'])
        self.assertEqual('minecraft:stone', actual['front']['name'])
        self.assertEqual([], self.native.timers)
        self.assertTrue(self.restore()['restored'])

    def test_typed_state_and_source_tampering_cannot_classify_or_accept(self):
        original = self.complete()
        for change in ('nonair_none', 'bool_int', 'reset_missing', 'template', 'method', 'payload', 'wet'):
            report = copy.deepcopy(original)
            cell = base.cell_at(report['native']['rows'][-1]['samples'][-1], (0, 1, 0))
            if change == 'nonair_none':
                cell['states'] = None
            elif change == 'bool_int':
                cell['states']['stability'] = False
                self.assertFalse(valid(report)['positive_control_matched'])
                continue
            elif change == 'reset_missing':
                report['start']['setup']['explicit_air_resets'].pop()
            elif change == 'template':
                report['template_sha256'] = 'd' * 64
            elif change == 'method':
                report['method'] = base.METHOD
            elif change == 'payload':
                report['payload_sha256']['start'] = 'd' * 64
            else:
                report['cleanup']['air_readbacks'][0]['liquid'] = {'name': 'minecraft:water', 'aux': 0}
            with self.subTest(change=change), self.assertRaises(ValueError):
                valid(report)

    def test_local_callbacks_ignore_namespace_collision_and_cannot_write_after_cleanup(self):
        self.start()
        self.scope.update(info=None, block=None, state=None, game=None, probe=None, begin=None, read=None)
        while self.native.timers:
            self.native.timers.pop(0)()
        report = self.execute(base.STATUS % (probe.MARKER, self.identity))
        self.assertTrue(report['done'])
        self.assertTrue(self.restore()['restored'])
        self.start()
        timer = self.native.timers.pop()
        self.assertTrue(self.restore()['restored'])
        writes = len(self.native.writes)
        timer()
        self.assertEqual(writes, len(self.native.writes))

    def test_native_code_compiles_for_game_python2(self):
        pypy = Path('C:/Users/Happy2018new/Desktop/PyPy/pypy2.exe')
        if not pypy.is_file():
            self.skipTest('Game-compatible Python2 unavailable')
        for code in (probe.start_payload(self.identity, 'a' * 64, True, AIR_ENCODING),
                     base.STATUS % (probe.MARKER, self.identity), probe.native_restore() % (probe.MARKER, self.identity)):
            result = subprocess.run([str(pypy), '-c', 'compile(%r,"runtime-lifecycle","exec")' % code],
                                    capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
