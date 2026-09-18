"""Retained animation children may be skipped, but their own dirty state must render."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


class IdentityTests(unittest.TestCase):
    def test_immutable_element_skip_does_not_swallow_local_state(self):
        package = types.ModuleType('isolated_reconciler')
        package.__path__ = []
        modules = {'isolated_reconciler': package}
        for name in ('hooks', 'native', 'element', 'primitives'):
            modules['isolated_reconciler.' + name] = types.ModuleType('isolated_reconciler.' + name)
        modules['isolated_reconciler.element'].Element = object
        modules['isolated_reconciler.element'].normalize_children = lambda x: x
        modules['isolated_reconciler.primitives'].Primitive = type('Primitive', (), {})
        sys.modules.update(modules)
        try:
            path = Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript/pyreact/reconciler.py'
            spec = importlib.util.spec_from_file_location('isolated_reconciler.reconciler', path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            commits = []
            module._update_component = lambda fiber, host: commits.append(fiber)
            element = types.SimpleNamespace(props={}, style=None, children=[], key=None)
            fiber = types.SimpleNamespace(element=element, dirty=False, is_component=True)
            module.update_fiber(fiber, element, None)
            self.assertEqual(commits, [])
            fiber.dirty = True
            module.update_fiber(fiber, element, None)
            self.assertEqual(commits, [fiber])
            fiber.dirty = False
            next_element = types.SimpleNamespace(props={'value': 3}, style=None, children=[], key=None)
            module.update_fiber(fiber, next_element, None)
            self.assertEqual(len(commits), 2)
        finally:
            for name in modules:
                sys.modules.pop(name, None)
