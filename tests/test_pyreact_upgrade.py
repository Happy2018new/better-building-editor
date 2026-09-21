"""Exercise upstream lifecycle changes together with the retained local fast path."""
import builtins
import importlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        aliases = patch.dict(builtins.__dict__, long=int, basestring=str, unicode=str)
        aliases.start()
        self.addCleanup(aliases.stop)
        package = types.ModuleType('upgrade_pyreact')
        package.__path__ = [str(ROOT / 'behavior_pack/HelloScript/pyreact')]
        api = types.ModuleType('mod.client.extraClientApi')
        api.GetScreenNodeCls = api.GetViewBinderCls = api.GetViewViewRequestCls = lambda: object
        modules = {'upgrade_pyreact': package, 'mod': types.ModuleType('mod'),
                   'mod.client': types.ModuleType('mod.client'), 'mod.client.extraClientApi': api}
        isolate = patch.dict(sys.modules, modules)
        isolate.start()
        self.addCleanup(isolate.stop)
        for name in ('hooks', 'reconciler', 'host', 'element', 'component', 'primitives', 'layout', 'style', 'constants', 'debug'):
            setattr(self, name, importlib.import_module('upgrade_pyreact.' + name))

        class Host:
            schedule_render = self.host.PyreactScreenNode.schedule_render
            flush = self.host.PyreactScreenNode._pyreact_flush

        self.runtime = Host()
        self.runtime._dirty = set()
        self.runtime._pending_effects = set()
        self.runtime._needs_layout = False
        self.runtime._commit_native_dirty = False
        self.runtime._commit_layout_dirty = False
        self.runtime._root_fiber = None

    def mount(self, component):
        fiber = self.reconciler.create_fiber(component, self.runtime)
        self.reconciler.mount_fiber(fiber, '/root', self.runtime)
        return fiber

    def test_dirty_retained_child_updates_once_after_parent(self):
        renders, setters = [], []
        @self.component.Component
        def Child():
            value, setter = self.hooks.use_state(0)
            setters.append(setter)
            renders.append(value)
        retained = Child()
        @self.component.Component
        def Parent():
            return retained
        parent = self.mount(Parent())
        setters[0](1)
        self.runtime.schedule_render(parent)
        self.runtime.flush()
        self.assertEqual(renders, [0, 1])
        self.assertIs(setters[0], setters[1])
        self.runtime.schedule_render(parent)
        self.runtime.flush()
        self.assertEqual(renders, [0, 1])

    def test_state_requested_during_render_survives_mount(self):
        renders = []
        @self.component.Component
        def Child():
            value, setter = self.hooks.use_state(0)
            renders.append(value)
            if value == 0:
                setter(1)
        fiber = self.mount(Child())
        self.assertTrue(fiber.dirty)
        self.runtime.flush()
        self.assertEqual(renders, [0, 1])

    def test_nested_unmount_cleans_effects_once_and_ignores_stale_setter(self):
        cleanup, setters = [], []
        @self.component.Component
        def Child():
            _, setter = self.hooks.use_state(0)
            setters.append(setter)
            self.hooks.use_effect(lambda: lambda: cleanup.append('child'), [])
        @self.component.Component
        def Parent():
            self.hooks.use_effect(lambda: lambda: cleanup.append('parent'), [])
            return Child()
        fiber = self.mount(Parent())
        self.runtime.flush()  # pending-effects-only commits must run
        self.reconciler.unmount_fiber(fiber, self.runtime)
        setters[0](3)
        self.assertEqual(sorted(cleanup), ['child', 'parent'])
        self.assertFalse(self.runtime._dirty)
        self.assertFalse(self.runtime._pending_effects)

    def test_changed_ref_detaches_then_attaches_without_remount(self):
        calls = []
        old = self.primitives.Panel(ref=lambda value: calls.append(('old', value)))
        new = self.primitives.Panel(ref=lambda value: calls.append(('new', value)))
        fiber = self.reconciler.create_fiber(old, self.runtime)
        fiber.native_path = '/root/test'
        control = object()
        with patch.object(self.reconciler, '_update_primitive'), patch.object(self.reconciler.native, 'get_control', return_value=control):
            self.reconciler.update_fiber(fiber, new, self.runtime)
        self.assertEqual(calls, [('old', None), ('new', control)])

    def test_explicit_integer_key_does_not_collide_with_unkeyed_position(self):
        @self.component.Component
        def Child():
            return None
        children = [Child(key=1), Child(key=2), Child()]
        @self.component.Component
        def Parent():
            return children
        parent = self.mount(Parent())
        first, second, positional = parent.child_fibers
        self.reconciler.reconcile_children(parent, [children[1], children[0], children[2]], self.runtime)
        self.assertIs(parent.child_fibers[0], second)
        self.assertIs(parent.child_fibers[1], first)
        self.assertIs(parent.child_fibers[2], positional)

    def test_unicode_keys_produce_ascii_native_control_names(self):
        native = self.reconciler.native
        for key, expected in (('view_navigation', 'view_navigation'),
                              ('选区_一', '____'), ('12/区域', '_12___'),
                              ('a-b', 'a_b'), (7, '_7')):
            with self.subTest(key=key):
                name = native.sanitize_name(key)
                self.assertIs(type(name), str)
                self.assertEqual(expected, name)
                self.assertEqual(name, name.encode('ascii').decode('ascii'))
        self.assertIsNone(native.sanitize_name(''))
        self.assertIsNone(native.sanitize_name(None))

    def test_hidden_primitive_root_does_not_measure_native_text(self):
        element = self.primitives.Label(content='hidden', style=self.style.Style(display=self.constants.Display.none))
        fiber = self.reconciler.create_fiber(element, self.runtime)
        nodes = self.layout.build_layout_tree(fiber)
        self.assertEqual(len(nodes), 1)
        self.assertIs(nodes[0].fiber, fiber)
        with patch.object(self.layout.native, 'get_size', side_effect=AssertionError('hidden text measured')):
            self.assertFalse(self.layout.measure(nodes[0], self.runtime))
        self.assertEqual((nodes[0].measured_w, nodes[0].measured_h), (0, 0))

    def test_display_none_skips_layout_descendants_without_unmounting(self):
        root = self.reconciler.create_fiber(self.primitives.Panel(style=self.style.Style(display=self.constants.Display.none)),self.runtime)
        child = self.reconciler.create_fiber(self.primitives.Label(content='hidden'),self.runtime)
        root.child_fibers=[child];child.parent_fiber=root
        self.assertEqual([],self.layout.build_layout_tree(root)[0].children)
        self.assertEqual([child],root.child_fibers)
        root.style=self.style.Style(display=self.constants.Display.flex)
        self.assertIs(child,self.layout.build_layout_tree(root)[0].children[0].fiber)

    def test_fixed_layout_boundary_reuses_only_unchanged_geometry(self):
        p = self.primitives.Panel
        root = self.reconciler.create_fiber(p(), self.runtime)
        child = self.reconciler.create_fiber(p(cacheLayout=True, style=self.style.Style(width=200, height=100)), self.runtime)
        root.child_fibers = [child]
        child.parent_fiber = root
        self.runtime._layout_cache_viewport = (800, 600)
        first = self.layout.build_layout_tree(root)[0].children[0]
        first.cache_ready = True
        first.last_box = (0, 0, 200, 100)
        first.apply_context = (0, 0, 1, 1)
        second = self.layout.build_layout_tree(root)[0].children[0]
        self.assertIs(first, second)
        with patch.object(self.layout.native, 'get_size', side_effect=AssertionError('cached measurement')):
            self.assertFalse(self.layout.measure(second, self.runtime, True))
        self.layout.layout(second, (0, 0, 200, 100), self.runtime)
        self.assertTrue(second.reuse_geometry)
        self.layout.layout(second, (0, 30, 200, 100), self.runtime)
        self.assertFalse(second.reuse_geometry)
        self.assertEqual(second.frame_y, 30)
        self.reconciler.invalidate_layout_cache(child)
        third = self.layout.build_layout_tree(root)[0].children[0]
        self.assertIsNot(second, third)
        third.cache_ready = True
        self.runtime._layout_cache_viewport = (1200, 600)
        self.assertIsNot(third, self.layout.build_layout_tree(root)[0].children[0])

    def test_nested_boundary_invalidates_through_component_and_parent_opacity(self):
        p = self.primitives.Panel
        root = self.reconciler.create_fiber(p(), self.runtime)
        boundary = self.reconciler.create_fiber(p(cacheLayout=True, style=self.style.Style(width=200,height=100)), self.runtime)
        @self.component.Component
        def Child():
            return None
        component = self.reconciler.create_fiber(Child(), self.runtime)
        leaf = self.reconciler.create_fiber(p(), self.runtime)
        root.child_fibers = [boundary]; boundary.parent_fiber = root
        boundary.child_fibers = [component]; component.parent_fiber = boundary
        component.child_fibers = [leaf]; leaf.parent_fiber = component
        first = self.layout.build_layout_tree(root)[0].children[0]
        first.cache_ready = True
        self.reconciler.invalidate_layout_cache(leaf)
        second = self.layout.build_layout_tree(root)[0].children[0]
        self.assertIsNot(first, second)
        second.cache_ready = True
        root.style = self.style.Style(opacity=.5)
        third = self.layout.build_layout_tree(root)[0].children[0]
        self.assertIsNot(second, third)
        self.assertEqual(third.inherited_opacity,.5)
        boundary.style = self.style.Style(width='100%',height=100)
        self.assertIsNone(self.layout._boundary_key(boundary,1.))

    def test_safe_area_receives_resize_until_unsubscribed(self):
        values = []
        unsubscribe = self.host._subscribe_safe_area(values.append)
        self.host._publish_safe_area((800, 600), (0, 0, 0, 0))
        self.host._publish_safe_area((1200, 600), (0, 0, 0, 0))
        unsubscribe()
        self.host._publish_safe_area((1600, 600), (10, 0, 0, 0))
        self.assertEqual(values, [(0, 0, 0, 0), (0, 0, 0, 0)])

    def test_component_dump_id_roundtrips_to_same_fiber(self):
        @self.component.Component
        def Child():
            return None
        fiber = self.mount(Child())
        snapshot = self.debug.serialize_fiber(fiber, {})
        self.assertIs(self.debug.find_fiber_by_id(fiber, snapshot['id']), fiber)

    def test_mcdk_bridge_dispatches_project_diagnostics_without_clipboard(self):
        path = ROOT / '.agents/skills/pyreact-debugging/scripts/_game_bridge.py'
        spec = importlib.util.spec_from_file_location('upgrade_game_bridge', path)
        bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bridge)
        self.host._RUNTIME_DEBUG[0] = True
        self.host._ACTIVE_HOST[0] = self.runtime
        self.runtime._root_fiber = object()
        request = {'cmd': 'debug_component', 'id': 'scene', 'seq': 'unique', 'value': {'inspect': True}}
        with patch.object(self.debug, 'dispatch_editor_command', return_value={'blocks': 7}) as dispatch:
            result = bridge.pyreact_request(request, 'upgrade_pyreact')
        dispatch.assert_called_once_with(self.runtime, 'debug_component', 'scene', {'inspect': True})
        self.assertEqual(result, {'pyreact_ack': True, 'seq': 'unique', 'result': {'blocks': 7}})
