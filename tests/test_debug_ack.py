"""A failed clipboard write must not lose the ack or repeat an edit."""
import importlib.util
import json
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript/pyreact/debug.py'


class DebugAckTests(unittest.TestCase):
    def test_transient_clipboard_lock_retries_only_response(self):
        spec = importlib.util.spec_from_file_location('isolated_pyreact_debug', PATH)
        debug = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(debug)
        effects = []
        debug.dispatch_pointer = lambda *args: effects.append('edit') or {'ok': True}

        class Game:
            content = json.dumps({'pyreact_debug': {'cmd': 'pointer', 'seq': 51, 'id': 'test', 'value': {}}})
            writes = 0

            def GetClipboardContent(self):
                return self.content

            def SetClipboardContent(self, value):
                self.writes += 1
                if self.writes == 1:
                    raise RuntimeError('clipboard temporarily locked')
                self.content = value

        class Host:
            _root_fiber = object()
            _debug_game = Game()

        host = Host()
        debug.poll_clipboard(host)
        debug.poll_clipboard(host)
        self.assertEqual(effects, ['edit'])
        self.assertEqual(host._debug_game.writes, 2)
        self.assertEqual(json.loads(host._debug_game.content)['seq'], 51)
        self.assertTrue(json.loads(host._debug_game.content)['result']['ok'])
