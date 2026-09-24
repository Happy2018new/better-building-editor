"""Tool help survives status timers and follows native input/workspace state."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


def load_hud():
    package = '_hud_test'
    names = ('mod', 'mod.client', 'mod.client.extraClientApi', package,
             package + '.projection', package + '.projection.tool_items',
             package + '.projection.bridge', package + '.projection.input_mode',
             package + '.pyreact')
    modules = {name: types.ModuleType(name) for name in names}
    modules['mod.client.extraClientApi'].GetScreenNodeCls = lambda: object
    items = modules[package + '.projection.tool_items']
    items.SURVEY_WAND, items.TERMINAL = 'wand', 'terminal'
    items.item_name = lambda value: value
    modules[package + '.projection.bridge'].native = lambda value: value
    modules[package + '.projection.input_mode'].is_touch = lambda: False
    modules[package + '.pyreact'].navigator = types.SimpleNamespace(contains=lambda key: False)
    module = types.ModuleType(package + '.projection.tool_hud')
    module.__package__ = package + '.projection'
    path = Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript/projection/tool_hud.py'
    with patch.dict(sys.modules, modules):
        exec(compile(path.read_text(encoding='utf8'), str(path), 'exec'), module.__dict__)
    return module


class ToolHudTests(unittest.TestCase):
    def setUp(self):
        self.module = load_hud()
        self.hud = self.module.TerminalHud.__new__(self.module.TerminalHud)
        self.hud.screen = Mock()
        self.timers = []
        self.hud.owner = types.SimpleNamespace(bridge=types.SimpleNamespace(
            later=lambda delay, callback: self.timers.append(callback)))
        self.hud.carried = 'wand'
        self.hud.shown = None
        self.hud.tip_sequence = 0
        self.hud.update()

    def test_status_expiry_preserves_pc_shortcuts(self):
        self.hud.show_tip('selected')
        self.assertTrue(self.hud.tip_shown.startswith('selected\n'))
        self.timers.pop()()
        self.assertNotIn('selected', self.hud.tip_shown)
        self.assertIn('右键选点', self.hud.tip_shown)
        self.assertIn('左键导入', self.hud.tip_shown)
        self.assertIn('潜行＋右键清除', self.hud.tip_shown)

    def test_old_timer_cannot_clear_new_status(self):
        self.hud.show_tip('first')
        self.hud.show_tip('second')
        self.timers[0]()
        self.assertTrue(self.hud.tip_shown.startswith('second\n'))

    def test_input_switch_keeps_status_and_updates_help(self):
        self.hud.show_tip('selected')
        self.module.is_touch = lambda: True
        self.hud.update()
        self.assertEqual('selected', self.hud.tip_shown)
        self.module.is_touch = lambda: False
        self.hud.update()
        self.assertIn('右键选点', self.hud.tip_shown)

    def test_tool_change_clears_status_and_uses_terminal_help(self):
        self.hud.show_tip('selected')
        self.hud.carried = 'terminal'
        self.hud.update()
        self.assertEqual('右键或点击按钮打开工作台', self.hud.tip_shown)
        self.hud.carried = None
        self.hud.update()
        self.assertEqual('', self.hud.tip_shown)

    def test_workspace_hides_tip_without_redundant_screen_writes(self):
        self.hud.screen.reset_mock()
        self.hud.update()
        self.hud.screen.set_tip.assert_not_called()
        self.module.navigator.contains = lambda key: True
        self.hud.update()
        self.assertEqual('', self.hud.tip_shown)


if __name__ == '__main__':
    unittest.main()
