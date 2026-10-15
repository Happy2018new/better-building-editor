"""Exercise owned frame rollback and guard failures without launching Minecraft."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('crafter_checks', ROOT / '.runtime/shield-crafter-r20/check_fixture_offline.py')
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)


class Backend(common.Backend):
    def __init__(self):
        super().__init__()
        self.actors = set()

    def CreateEngineEntityByTypeStr(self, *args):
        entity = 'owned-' + str(len(self.actors))
        self.actors.add(entity)
        return entity

    def DestroyEntity(self, entity):
        self.actors.remove(entity)
        return True

    def SetInvItemNum(self, slot, count):
        assert count == 0
        self.inv[slot] = None
        return True

    def SpawnItemToPlayerInv(self, item, player, slot):
        self.inv[slot] = copy.deepcopy(item)
        return True

    def PlayerUseItemToPos(self, pos, kind, slot, face):
        item = self.inv[slot]
        name = item.get('newItemName', item.get('itemName'))
        if name == 'minecraft:frame':
            return self.SetBlockNew((pos[0], pos[1], pos[2] - 1), {'name': name, 'aux': 2})
        assert name == 'minecraft:shield'
        self.nbts[tuple(pos)] = {'Item': {'Name': name, 'Damage': 0,
            'tag': copy.deepcopy(item.get('userData', {}))}}
        self.inv[slot] = None
        return True


class RollbackChecks(unittest.TestCase):
    def setUp(self):
        self.sdk = Backend()
        self.sdk.inv[35] = {'itemName': 'minecraft:diamond', 'count': 7, 'auxValue': 0}
        self.initial_inventory = copy.deepcopy(self.sdk.inv)
        api = ModuleType('mod.server.extraServerApi')
        api.GetEngineCompFactory = self.sdk.factory
        api.GetLevelId = lambda: 'level'
        api.GetPlayerList = lambda: ['player']
        api.GetMinecraftEnum = lambda: SimpleNamespace(ItemPosType=SimpleNamespace(INVENTORY=0))
        api.GetSystem = lambda *args: self.sdk
        for name in ('mod', 'mod.server'):
            sys.modules[name] = ModuleType(name)
        sys.modules['mod.server.extraServerApi'] = api
        raw = json.loads((ROOT / 'docs/evidence/shield-native-crafter-r21-v1/records/authentic-shield.json').read_bytes())
        self.inputs = {'items': {'plain': {'newItemName': 'minecraft:shield', 'newAuxValue': 0},
                                 'authentic': raw['item']}}
        self.source = compile((HERE / 'server.py').read_bytes(), 'server.py', 'exec')

    def tearDown(self):
        if hasattr(sys, '_shield_authentic_server_r21'):
            del sys._shield_authentic_server_r21

    def action(self, action):
        scope = {'ACTION': action, 'INPUTS': self.inputs}
        exec(self.source, scope)
        return json.loads(scope['_result'])

    def assert_restored(self):
        result = self.action('restore')
        self.assertTrue(result['restored'])
        self.assertEqual(result['guard_cells_restored'], 96)
        self.assertFalse(self.sdk.cells)
        self.assertFalse(self.sdk.nbts)
        self.assertFalse(self.sdk.actors)
        self.assertEqual(self.sdk.inv, self.initial_inventory)

    def test_native_frame_insertion_and_exact_userdata_restore(self):
        self.action('journal')
        result = self.action('frames')
        self.assertEqual(result['frames'][1]['nbt']['Item']['tag'], self.inputs['items']['authentic']['userData'])
        self.assert_restored()

    def test_each_failed_placement_restores_world_inventory_and_actors(self):
        for mutation in range(1, 5):
            with self.subTest(mutation=mutation):
                self.action('journal')
                self.sdk.calls = 0
                self.sdk.fail_at = mutation
                with self.assertRaises(AssertionError):
                    self.action('frames')
                self.sdk.fail_at = None
                self.assert_restored()

    def test_existing_block_guard_prevents_actor_or_cell_mutation(self):
        self.sdk.cells[(2, -58, 3)] = {'name': 'minecraft:stone', 'aux': 0}
        with self.assertRaises(AssertionError):
            self.action('journal')
        self.assertEqual(self.sdk.calls, 0)
        self.assertFalse(self.sdk.actors)
        self.assertFalse(hasattr(sys, '_shield_authentic_server_r21'))
        self.assertEqual(self.sdk.inv, self.initial_inventory)

    def test_absent_fixture_restore_is_idempotent(self):
        self.assertTrue(self.action('restore')['already_absent'])
        self.assertTrue(self.action('restore')['already_absent'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
