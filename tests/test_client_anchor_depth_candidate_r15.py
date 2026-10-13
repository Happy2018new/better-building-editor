"""Exercise the candidate's generated state transitions with native-call fakes."""
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('depth_candidate', ROOT / 'tools/prepare_client_anchor_depth_candidate_r15.py')
candidate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(candidate)


class NativeItem:
    def __init__(self, bind_result=7, remove_result=True):
        self.bind_result, self.remove_result = bind_result, remove_result
        self.binds, self.removes = [], []

    def BindItemToMinecraftModel(self, *args):
        self.binds.append(args)
        return self.bind_result

    def SetBindBoneForBindItem(self, *args):
        self.removes.append(args)
        return self.remove_result

    def GetBindItemOffset(self, *args):
        return (0., 0., 0.)

    def GetBindItemRotation(self, *args):
        return (0., 0., 0.)

    def GetBindItemScale(self, *args):
        return 1.


class CandidateStateTransitions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nonce = 'a' * 32
        cls.programs = candidate.snippets(cls.nonce)

    def environment(self, native=None, nonce=None):
        native = native or NativeItem()
        submitted = []
        doll = SimpleNamespace(RenderEntity=lambda value: submitted.append(dict(value)) or True)
        root = SimpleNamespace(SetVisible=lambda value: None, GetVisible=lambda: True)
        saved = {'nonce': nonce or self.nonce, 'key': 'owned-page', 'actor': 'owned-actor',
                 'root_ref': SimpleNamespace(current=root),
                 'ref': SimpleNamespace(current=SimpleNamespace(asNeteasePaperDoll=lambda: doll)),
                 'plain': {'newItemName': 'minecraft:diamond_sword', 'newAuxValue': 0,
                           'isEnchanted': False, 'userData': {}},
                 'ui_params': dict(candidate.UI, entity_id='owned-actor'),
                 'attachments': [], 'current': None, 'journal': []}
        fake_sys = SimpleNamespace(**{candidate.ATTRIBUTE: saved})
        bridge = ModuleType('modern_projection.projection.bridge')
        bridge._stable_palette = lambda value: json.dumps(value, sort_keys=True)
        env = {'sys': fake_sys, 'json': json, 'time': SimpleNamespace(time=lambda: 123.),
               'long': int, 'b': SimpleNamespace(level='owned-level', factory=SimpleNamespace(CreateItem=lambda _: native)),
               'navigator': SimpleNamespace(is_transitioning=False, top=SimpleNamespace(key=saved['key']))}
        return env, saved, native, submitted, bridge

    def execute(self, label, env, bridge):
        with patch.dict(sys.modules, {'modern_projection.projection.bridge': bridge}):
            exec(self.programs[label + '_client.py'], env)

    def test_depth_pair_retains_one_binding_and_restores_documented_depth(self):
        env, saved, native, submitted, bridge = self.environment()
        for label in candidate.STATES:
            self.execute(label, env, bridge)
        self.assertEqual(len(native.binds), 1)
        self.assertEqual(len(native.removes), 1)
        self.assertEqual(native.binds[0][0], 'owned-actor')
        self.assertEqual(native.binds[0][2:], ('root', True, (0., 0., 0.), (0., 0., 0.), 1.))
        self.assertEqual(native.removes[0], ('owned-actor', 7, '', True))
        self.assertEqual([row['render_depth'] for row in submitted], [-15, -15, -15, -50, -15, -15, -15])
        for row in submitted[1:-1]:
            self.assertEqual(row, dict(candidate.UI, entity_id='owned-actor', render_depth=row['render_depth']))
        for row in (submitted[0], submitted[-1]):
            self.assertNotIn('entity_id', row)
            self.assertEqual(row['entity_identifier'], 'minecraft:cow')
        self.assertEqual(saved['attachments'][0]['state'], 'removed')
        self.assertEqual(saved['attachments'][0]['id'], 7)

    def test_wrong_nonce_stops_before_native_calls(self):
        env, _, native, submitted, bridge = self.environment(nonce='b' * 32)
        with self.assertRaises(AssertionError):
            self.execute('ui_plain_depth15', env, bridge)
        self.assertEqual(native.binds, [])
        self.assertEqual(submitted, [])

    def test_rejected_binding_is_recorded_and_not_rendered(self):
        env, saved, _, submitted, bridge = self.environment(NativeItem(bind_result=-1))
        with self.assertRaises(AssertionError):
            self.execute('ui_plain_depth15', env, bridge)
        self.assertEqual(saved['attachments'][0]['state'], 'rejected')
        self.assertEqual(submitted, [])

    def test_uncertain_removal_cannot_be_replayed_by_control(self):
        env, saved, native, _, bridge = self.environment(NativeItem(remove_result=False))
        self.execute('ui_plain_depth15', env, bridge)
        for _ in range(2):
            with self.assertRaises(AssertionError):
                self.execute('ui_empty_restored', env, bridge)
        self.assertEqual(len(native.removes), 1)
        self.assertTrue(saved['attachments'][0]['remove_attempted'])

    def test_bundle_rejects_changed_generated_code(self):
        with TemporaryDirectory() as directory:
            bundle = Path(directory) / 'bundle'
            candidate.prepare(bundle)
            program = bundle / 'ui_plain_depth15_client.py'
            program.write_bytes(program.read_bytes() + b'\n_result=True\n')
            with self.assertRaises(ValueError):
                candidate.verify(bundle)


if __name__ == '__main__':
    unittest.main()
