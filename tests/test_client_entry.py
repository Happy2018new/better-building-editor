"""World entry requires a terminal; no global P shortcut is registered."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


def load_client():
    package = '_entry_test'
    names = ('mod', 'mod.client', 'mod.client.extraClientApi', package,
             package + '.projection', package + '.projection.bridge',
             package + '.projection.session', package + '.projection.ui',
             package + '.projection.tool_hud', package + '.projection.tool_items',
             package + '.projection.input_mode', package + '.pyreact')
    modules = {name: types.ModuleType(name) for name in names}

    class System:
        def __init__(self, namespace, name):
            self.events = {}

        def ListenForEvent(self, namespace, system, event, owner, callback):
            self.events[event] = callback

        def UnListenAllEvents(self):
            self.events.clear()

    api = modules['mod.client.extraClientApi']
    api.GetClientSystemCls = lambda: System
    api.GetEngineNamespace = lambda: 'engine'
    api.GetEngineSystemName = lambda: 'engine'
    for name, attribute in [('bridge', 'ClientBridge'), ('session', 'Session'),
                            ('ui', 'Workspace'), ('tool_hud', 'TerminalHud')]:
        setattr(modules[package + '.projection.' + name], attribute, Mock())
    items = modules[package + '.projection.tool_items']
    items.TERMINAL, items.SURVEY_WAND = 'terminal', 'wand'
    items.item_name = lambda item: item
    modules[package + '.projection.input_mode'].is_touch = lambda: False
    react = modules[package + '.pyreact']
    react.runtime_init = Mock()
    react.navigator = types.SimpleNamespace(contains=Mock(return_value=False), push=Mock())
    module = types.ModuleType(package + '.client_system')
    module.__package__ = package
    path = Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection/client_system.py'
    with patch.dict(sys.modules, modules):
        exec(compile(path.read_text(encoding='utf8'), str(path), 'exec'), module.__dict__)
    return module


class ClientEntryTests(unittest.TestCase):
    def setUp(self):
        self.module = load_client()
        self.owner = self.module.ModernProjectionClientSystem('ModernProjection', 'ModernProjectionClientSystem')
        self.owner.session = object()

    def test_no_world_keyboard_subscription(self):
        self.assertNotIn('OnKeyPressInGame', self.owner.events)
        self.assertIn('OpenProjectionUi', self.owner.events)
        self.assertIn('RightClickBeforeClientEvent', self.owner.events)

    def test_chunk_registry_tracks_load_unload_before_ui_initialization(self):
        point = {'dimension': 0, 'chunkPosX': -2, 'chunkPosZ': 3}
        self.owner.events['ChunkLoadedClientEvent'](point)
        self.assertIn((0, -2, 3), self.owner.projection_loaded_chunks)
        self.owner.events['ChunkAcquireDiscardedClientEvent'](point)
        self.assertFalse(self.owner.projection_loaded_chunks)

    def test_terminal_right_click_opens_once_and_cancels_use(self):
        self.owner.hud = types.SimpleNamespace(carried='terminal')
        event = {}
        self.owner.tool_use(event)
        self.assertTrue(event['cancel'])
        self.module.navigator.push.assert_called_once()
        self.module.navigator.contains.return_value = True
        self.owner.tool_use({})
        self.module.navigator.push.assert_called_once()

    def test_empty_hand_cannot_use_terminal_entry(self):
        self.owner.hud = types.SimpleNamespace(carried=None)
        self.owner.open_from_terminal()
        self.owner.tool_use({})
        self.module.navigator.push.assert_not_called()
        self.owner.hud.carried = 'terminal'
        self.owner.open_from_terminal()
        self.module.navigator.push.assert_called_once()

    def test_projection_uses_existing_client_interactions_without_network_listener(self):
        self.assertNotIn('ProjectionDirty', self.owner.events)
        self.owner.hud = types.SimpleNamespace(carried='minecraft:stone')
        self.owner.bridge = Mock()
        for event in ('RightClickBeforeClientEvent', 'LeftClickBeforeClientEvent',
                      'TapBeforeClientEvent', 'StartDestroyBlockClientEvent',
                      'PlayerTryDestroyBlockClientEvent'):
            with self.subTest(event=event):
                args = ({'pos': (10., 64., 20.)} if event == 'StartDestroyBlockClientEvent'
                        else {'x': 10, 'y': 64, 'z': 20})
                self.owner.bridge.reset_mock()
                self.owner.events[event](args)
                self.owner.bridge.projection_interaction.assert_called_once()
                if event in ('StartDestroyBlockClientEvent', 'PlayerTryDestroyBlockClientEvent'):
                    self.owner.bridge.projection_interaction.assert_called_once_with((10, 64, 20))
                self.assertNotIn('cancel', args)
        self.owner.bridge.projection_interaction.assert_called_once_with((10, 64, 20))

    def test_break_without_position_does_not_fall_back_to_camera(self):
        self.owner.bridge = Mock()
        self.owner.tool_prevent_break({})
        self.owner.bridge.projection_interaction.assert_not_called()

    def test_system_destruction_unregisters_listeners_and_stops_projection(self):
        self.owner.bridge = Mock()
        self.owner.bridge.destroy.side_effect = lambda: self.assertFalse(self.owner.events)
        self.assertIn('GameRenderTickEvent', self.owner.events)
        self.owner.Destroy()
        self.assertFalse(self.owner.events)
        self.owner.bridge.destroy.assert_called_once_with()

    def test_tool_cancel_does_not_enqueue_occupancy_hints(self):
        self.owner.hud = types.SimpleNamespace(carried='terminal')
        self.owner.bridge = Mock()
        event = {'x': 10, 'y': 64, 'z': 20}
        self.owner.events['StartDestroyBlockClientEvent'](event)
        self.assertTrue(event['cancel'])
        self.owner.events['RightClickBeforeClientEvent']({})
        self.owner.bridge.projection_interaction.assert_not_called()


if __name__ == '__main__':
    unittest.main()
