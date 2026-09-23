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


class GameDict(dict):
    iteritems = dict.items


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
            _pyreact_commit = self.host.PyreactScreenNode._pyreact_commit

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

    def test_callback_update_uses_latest_handler_without_native_commit(self):
        from unittest.mock import Mock
        handler = Mock()
        builder = Mock()
        style = self.style.Style(width=100, height=32)
        first = self.primitives.Button(onClick=lambda: None, buttonBuilder=builder, style=style)
        fiber = self.reconciler.create_fiber(first, self.runtime)
        fiber.last_props, fiber.last_style = GameDict(fiber.props), fiber.style
        fiber.primitive_state['_visible'] = True
        fiber.native_path = '/root/button'
        self.runtime.pyreact_register_button = Mock()
        with patch.object(self.reconciler.native, 'get_control', return_value=Mock()):
            self.reconciler.update_fiber(fiber, self.primitives.Button(onClick=handler, buttonBuilder=builder, style=style), self.runtime)
        self.assertFalse(self.runtime._commit_native_dirty)
        self.assertFalse(self.runtime._commit_layout_dirty)
        self.runtime.pyreact_register_button.call_args.args[-1]()
        handler.assert_called_once_with()
        builder.assert_not_called()

    def test_props_fast_path_keeps_visibility_and_layout_commits(self):
        from unittest.mock import Mock
        first = self.primitives.Panel(cacheLayout=True, style=self.style.Style(width=100,height=32))
        fiber = self.reconciler.create_fiber(first, self.runtime)
        fiber.last_props, fiber.last_style = GameDict(fiber.props), fiber.style
        fiber.primitive_state['_visible'] = True
        fiber.native_path = '/root/panel'
        with patch.object(self.reconciler.native, 'get_control', return_value=Mock()):
            self.reconciler.update_fiber(fiber, self.primitives.Panel(cacheLayout=False,
                style=self.style.Style(width=120,height=32,visible=False)), self.runtime)
        self.assertTrue(self.runtime._commit_native_dirty)
        self.assertTrue(self.runtime._commit_layout_dirty)

    def test_fixed_leaf_skips_native_measurement_but_auto_text_still_measures(self):
        for primitive in (self.primitives.Label, self.primitives.Item):
            fiber = self.reconciler.create_fiber(primitive(content='label', style=self.style.Style(width=100,height=32)),self.runtime)
            fiber.last_props = fiber.props
            node = self.layout.build_layout_tree(fiber)[0]
            with patch.object(self.layout.native,'get_size',side_effect=AssertionError('fixed leaf native read')), \
                 patch.object(self.layout.native,'measure_text',side_effect=AssertionError('fixed text measured')):
                self.layout.measure(node,self.runtime,True)
            self.assertEqual((100.,32.),(node.measured_w,node.measured_h))
        fiber = self.reconciler.create_fiber(self.primitives.Label(content='wrap', style=self.style.Style(width=100)),self.runtime)
        fiber.last_props = fiber.props
        node = self.layout.build_layout_tree(fiber)[0]
        with patch.object(self.layout.native,'measure_text',return_value=(80.,42.)) as measure:
            self.layout.measure(node,self.runtime,True)
        measure.assert_called_once()
        self.assertEqual(42.,node.measured_h)

    def test_anchored_image_needs_no_second_measure_but_auto_image_does(self):
        absolute = self.constants.Position.absolute
        for props, expected in ((dict(position=absolute, left=0, right=0, height=2), False),
                                (dict(position=absolute, top=0, bottom=0, width=2), False),
                                (dict(position=absolute, left=0, right=0, top=0, bottom=0), False),
                                (dict(position=absolute, left=0, height=2), True),
                                (dict(left=0, right=0, height=2), True),
                                (dict(width='100%', height=2), False),
                                (dict(width=40), True)):
            fiber = self.reconciler.create_fiber(self.primitives.Image(style=self.style.Style(**props)), self.runtime)
            fiber.last_props = fiber.props
            node = self.layout.build_layout_tree(fiber)[0]
            self.assertEqual(expected, self.layout._needs_post_measure(node), props)

    def test_native_route_batch_keeps_distinct_modes_and_nested_writes(self):
        native = self.reconciler.native
        gui = types.ModuleType('gui')
        routes, writes = [], []
        def route(*args, **kwargs):
            routes.append((args, kwargs, len(writes)))
        gui.handle_input_mode_change = route
        class Control:
            def SetLayer(self, *args):
                writes.append(args)
                gui.handle_input_mode_change()
        with patch.dict(sys.modules, gui=gui):
            with native.batch_input_routes():
                for i in range(104):
                    native.set_layer(Control(), i)
                with native.batch_input_routes():
                    gui.handle_input_mode_change()
                    gui.handle_input_mode_change(mode='touch')
                self.assertEqual([], routes)
                gui.handle_input_mode_change(mode='touch')
            self.assertIs(gui.handle_input_mode_change, route)
        self.assertEqual(104, len(writes))
        self.assertEqual([((), {}, 104), ((), {'mode': 'touch'}, 104)], routes)

    def test_empty_panel_subclass_does_not_force_second_layout(self):
        class FadePrimitive(self.primitives.PanelPrimitive):
            pass
        parent = self.reconciler.create_fiber(FadePrimitive()(), self.runtime)
        self.assertFalse(self.layout._needs_post_measure(self.layout.build_layout_tree(parent)[0]))
        # A custom panel with an auto-size native child still needs remeasurement.
        child = self.reconciler.create_fiber(self.primitives.Image(), self.runtime)
        child.parent_fiber = parent
        parent.child_fibers = [child]
        self.assertTrue(self.layout._needs_post_measure(self.layout.build_layout_tree(parent)[0]))

    def test_native_route_batch_restores_on_commit_or_routing_exception(self):
        native = self.reconciler.native
        gui = types.ModuleType('gui')
        from unittest.mock import Mock
        for fail_route in (False, True):
            original = Mock(side_effect=ValueError('route failed') if fail_route else None)
            gui.handle_input_mode_change = original
            with patch.dict(sys.modules, gui=gui):
                with self.assertRaises(ValueError):
                    with native.batch_input_routes():
                        gui.handle_input_mode_change()
                        raise ValueError('commit failed')
                self.assertIs(gui.handle_input_mode_change, original)
            original.assert_called_once_with()
        with patch.dict(sys.modules, gui=types.ModuleType('gui')):
            with native.batch_input_routes():
                pass  # other SDK versions retain their public API path

    def test_host_flush_batches_routes_until_effects_are_applied(self):
        gui = types.ModuleType('gui')
        events = []
        gui.handle_input_mode_change = lambda: events.append('route')
        @self.component.Component
        def Child():
            value, setter = self.hooks.use_state(0)
            self.setter = setter
            if value:
                gui.handle_input_mode_change()
                gui.handle_input_mode_change()
            self.hooks.use_effect(lambda: events.append('effect'), [value])
        self.mount(Child())
        self.runtime.flush()
        events[:] = []
        self.setter(1)
        with patch.dict(sys.modules, gui=gui):
            self.runtime.flush()
        self.assertEqual(['effect', 'route'], events)

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
