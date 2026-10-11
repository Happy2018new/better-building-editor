"""Ensure the diagnostic exercises distinct native submission paths."""
import json
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import probe_liquid_geometry_paths as probe


class LiquidGeometryProbeTests(unittest.TestCase):
    def evaluate(self, mode, prepared):
        calls = []
        def original(*args, **kwargs):
            calls.append((args, kwargs))
            return 'mesh'
        bridge = types.SimpleNamespace(geometry=original, context_models={'old': 'layout'})
        state = types.SimpleNamespace()
        namespace = {'sys': state, 'b': bridge, 'json': json}
        exec(probe.INSTALL_PATH % mode, namespace)
        document = types.SimpleNamespace(palette_data=lambda visible: {'common': 'raw'})
        bridge.geometry(document, name='test', prepared=prepared)
        return calls, bridge, state, namespace, original

    def test_raw_bypasses_prebuilt_context(self):
        calls, *_ = self.evaluate('raw', {'_context_batches': ['native']})
        self.assertEqual(calls[0][1]['prepared'], {'common': 'raw'})

    def test_prepared_uses_normal_preparation(self):
        calls, *_ = self.evaluate('prepared', {'_context_batches': ['native']})
        self.assertEqual(len(calls[0][0]), 3)
        self.assertEqual(calls[0][1], {})

    def test_context_preserves_native_batches(self):
        source = {'_context_batches': ['native']}
        calls, *_ = self.evaluate('context', source)
        self.assertIs(calls[0][0][-1], source)

    def test_recursive_chunk_submission_is_not_readapted(self):
        source = {'volume': (64, 64, 64), 'common': {}}
        calls, *_ = self.evaluate('raw', source)
        self.assertIs(calls[0][0][-1], source)

    def test_restore_stops_projection_before_replacing_method(self):
        calls, bridge, state, namespace, original = self.evaluate('raw', {'_context_batches': []})
        bridge.stop_projection = lambda: calls.append(('stopped', bridge.geometry is original))
        exec(probe.RESTORE_PATH, namespace)
        self.assertEqual(calls[-1], ('stopped', False))
        self.assertIs(bridge.geometry, original)
        self.assertEqual(bridge.context_models, {'old': 'layout'})
        self.assertFalse(hasattr(state, '_liquid_path_geometry_saved'))


if __name__ == '__main__':
    unittest.main()
