import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase, mock


class InputModeTests(TestCase):
    def setUp(self):
        self.mode, self.platform, self.simulated = 0, 0, False
        api = ModuleType('mod.client.extraClientApi')
        enum = SimpleNamespace(OptionId=SimpleNamespace(INPUT_MODE='input'),
                               InputMode=SimpleNamespace(Undefined=-1, Mouse=0, Touch=1))
        view = SimpleNamespace(GetToggleOption=lambda option: self.mode)
        api.GetEngineCompFactory = lambda: SimpleNamespace(CreatePlayerView=lambda level: view)
        api.GetLevelId = lambda: 'level'
        api.GetMinecraftEnum = lambda: enum
        api.GetPlatform = lambda: self.platform
        api.IsTouchWithMouse = lambda: self.simulated
        parent = ModuleType('mod'); parent.client = ModuleType('mod.client'); parent.client.extraClientApi = api
        spec = importlib.util.spec_from_file_location('_test_input_mode',
            Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript/projection/input_mode.py')
        self.module = importlib.util.module_from_spec(spec)
        with mock.patch.dict('sys.modules', {'mod': parent, 'mod.client': parent.client, 'mod.client.extraClientApi': api}):
            spec.loader.exec_module(self.module)

    def test_f11_is_recognized_before_the_first_contact_changes_input_mode(self):
        self.assertFalse(self.module.is_touch())
        self.simulated = True
        self.assertTrue(self.module.is_touch())
        self.mode = 1
        self.assertTrue(self.module.is_touch())
        self.simulated, self.mode = False, 0
        self.assertFalse(self.module.is_touch())

    def test_phone_uses_native_mode_and_undefined_platform_fallback(self):
        for self.platform in (1, 2):
            self.mode = 1
            self.assertTrue(self.module.is_touch())
            self.mode = -1
            self.assertTrue(self.module.is_touch())
            self.mode = 0  # A phone can also have an actual external mouse.
            self.assertFalse(self.module.is_touch())
