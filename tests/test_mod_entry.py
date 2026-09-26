"""Keep the engine-discovered entry point and registered class paths in sync."""
import ast
import contextlib
import io
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'behavior_pack'


class ModEntryTests(unittest.TestCase):
    def test_decorated_entry_registers_existing_system_classes(self):
        names = ('mod', 'mod.common', 'mod.common.mod', 'mod.client',
                 'mod.client.extraClientApi', 'mod.server', 'mod.server.extraServerApi')
        modules = {name: types.ModuleType(name) for name in names}
        hooks = {}
        bindings = []

        def binding(**metadata):
            def decorate(cls):
                bindings.append((metadata, cls))
                return cls
            return decorate

        def hook(event):
            def decorate(method):
                hooks[event] = method
                return method
            return decorate

        modules['mod.common.mod'].Mod = types.SimpleNamespace(
            Binding=binding,
            InitClient=lambda: hook('client_init'),
            DestroyClient=lambda: hook('client_destroy'),
            InitServer=lambda: hook('server_init'),
            DestroyServer=lambda: hook('server_destroy'))
        client = modules['mod.client.extraClientApi']
        server = modules['mod.server.extraServerApi']
        client.RegisterSystem = Mock()
        server.RegisterSystem = Mock()
        path = PACK / 'modern_projection/modMain.py'
        module = types.ModuleType('_mod_entry_test')
        with patch.dict(sys.modules, modules):
            exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
            self.assertEqual(1, len(bindings))
            self.assertEqual('ModernProjection', bindings[0][0]['name'])
            self.assertEqual({'client_init', 'server_init', 'client_destroy', 'server_destroy'}, set(hooks))
            entry = bindings[0][1]()
            with contextlib.redirect_stdout(io.StringIO()):
                for method in hooks.values():
                    method(entry)

        for api in (client, server):
            with self.subTest(side=api.__name__):
                api.RegisterSystem.assert_called_once()
                namespace, system_name, class_path = api.RegisterSystem.call_args.args
                self.assertEqual('ModernProjection', namespace)
                parts = class_path.split('.')
                self.assertEqual('modern_projection', parts[0])
                self.assertEqual(system_name, parts[-1])
                source = PACK.joinpath(*parts[:-1]).with_suffix('.py')
                tree = ast.parse(source.read_bytes())
                self.assertIn(parts[-1], [node.name for node in tree.body if isinstance(node, ast.ClassDef)])


if __name__ == '__main__':
    unittest.main()
