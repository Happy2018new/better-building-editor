"""Exercise rollback and target guards with a fake SDK; no MC is started."""
import copy
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack'))
from modern_projection.projection import block_registry as registry


class Backend:
    def __init__(self):
        self.cells = {}
        self.nbts = {}
        self.calls = 0
        self.fail_at = None
        self.content = {}
        self.inv = [None] * 36

    def GetBlockNew(self, pos, dimension):
        return copy.deepcopy(self.cells.get(tuple(pos), {'name': 'minecraft:air', 'aux': 0}))

    def GetLiquidBlock(self, pos, dimension):
        return None

    def GetBlockEntityData(self, dimension, pos):
        return copy.deepcopy(self.nbts.get(tuple(pos)))

    def SetBlockNew(self, pos, block, *args):
        self.calls += 1
        if self.calls == self.fail_at:
            return False
        pos = tuple(pos)
        self.cells[pos] = copy.deepcopy(block)
        name = block['name']
        if name == 'minecraft:air':
            self.cells.pop(pos, None)
            self.nbts.pop(pos, None)
            self.content.pop(pos, None)
        elif name in ('minecraft:crafter', 'minecraft:hopper', 'minecraft:chest'):
            self.nbts[pos] = {'id': {'__type__': 8, '__value__': 'Crafter' if name.endswith('crafter') else 'Container'},
                              'Items': [], 'disabled_slots': {'__type__': 2, '__value__': 0}}
            self.content[pos] = {}
        return True

    def GetBlockAuxValueFromStates(self, name, states):
        return registry.from_states(name, states)[1]

    def GetBlockStates(self, pos, dimension):
        block = self.GetBlockNew(pos, dimension)
        return registry.states((block['name'], block['aux']))

    def GetPlayerItem(self, kind, slot, userdata):
        return copy.deepcopy(self.inv[slot])

    def GetSelectSlotId(self):
        return 0

    def GetContainerSize(self, pos, dimension):
        return 27

    def GetContainerItem(self, pos, slot, dimension, userdata):
        return copy.deepcopy(self.content.get(tuple(pos), {}).get(slot))

    def SpawnItemToContainer(self, item, slot, pos, dimension):
        pos = tuple(pos)
        if item:
            self.content[pos][slot] = copy.deepcopy(item)
        else:
            self.content[pos].pop(slot, None)
        return True

    def GetEntityDimensionId(self):
        return 0

    def GetFootPos(self):
        return (0., -60., 0.)

    def GetEntitiesBySelector(self, selector):
        return []

    def DestroyEntity(self, entity):
        raise AssertionError('No fake drops expected')

    def factory(self):
        return SimpleNamespace(**{name: lambda *args: self for name in
            ('CreateBlockInfo', 'CreateBlockState', 'CreateItem', 'CreatePos',
             'CreateDimension', 'CreateEntityComponent')})


class FixtureChecks(unittest.TestCase):
    def setUp(self):
        self.sdk = Backend()
        api = ModuleType('mod.server.extraServerApi')
        api.GetEngineCompFactory = self.sdk.factory
        api.GetLevelId = lambda: 'level'
        api.GetPlayerList = lambda: ['player']
        api.GetMinecraftEnum = lambda: SimpleNamespace(ItemPosType=SimpleNamespace(INVENTORY=0))
        api.GetSystem = lambda *args: self.sdk
        for name in ('mod', 'mod.server'):
            sys.modules[name] = ModuleType(name)
        sys.modules['mod.server.extraServerApi'] = api
        self.inputs = {'blocks': {}}
        for label, name, states in (
                ('crafter', 'minecraft:crafter', {'crafting': False, 'orientation': 'north_up', 'triggered_bit': False}),
                ('hopper', 'minecraft:hopper', {'facing_direction': 0, 'toggle_bit': False}),
                ('chest', 'minecraft:chest', {'minecraft:cardinal_direction': 'north'})):
            self.inputs['blocks'][label] = {'name': name, 'states': states,
                                           'aux': registry.from_states(name, states)[1]}
        self.inputs.update(positive=[{'itemName': 'minecraft:oak_log', 'auxValue': 0, 'count': 1}],
                           target=[{'itemName': 'minecraft:shield', 'count': 1},
                                   {'itemName': 'minecraft:banner', 'count': 1}])
        self.source = compile((HERE / 'server_fixture.py').read_bytes(), 'server_fixture.py', 'exec')

    def tearDown(self):
        if hasattr(sys, '_shield_crafter_server_r20'):
            del sys._shield_crafter_server_r20

    def action(self, action):
        scope = {'ACTION': action, 'INPUTS': self.inputs}
        exec(self.source, scope)
        return json.loads(scope['_result'])

    def assert_restored(self):
        result = self.action('restore')
        self.assertTrue(result['restored'])
        self.assertEqual(result['guard_cells_verified'], 64)
        self.assertFalse(self.sdk.cells)
        self.assertFalse(self.sdk.nbts)
        self.assertFalse(hasattr(sys, '_shield_crafter_server_r20'))

    def test_guard_refuses_existing_world_without_mutation(self):
        self.sdk.cells[(4, -58, 4)] = {'name': 'minecraft:stone', 'aux': 0}
        with self.assertRaises(AssertionError):
            self.action('journal')
        self.assertEqual(self.sdk.calls, 0)
        self.assertFalse(hasattr(sys, '_shield_crafter_server_r20'))

    def test_partial_placement_failures_restore_every_cell(self):
        for index in (1, 2, 3):
            with self.subTest(failing_mutation=index):
                self.action('journal')
                self.sdk.calls = 0
                self.sdk.fail_at = index
                with self.assertRaises(AssertionError):
                    self.action('place')
                self.sdk.fail_at = None
                self.assert_restored()

    def test_hopper_not_drained_blocks_redstone(self):
        self.action('journal')
        self.action('place')
        self.action('feed_positive')
        calls = self.sdk.calls
        with self.assertRaises(AssertionError):
            self.action('pulse_on')
        self.assertEqual(self.sdk.calls, calls)
        self.assert_restored()

    def test_wrong_target_patterns_block_redstone(self):
        self.action('journal')
        self.action('place')
        saved = sys._shield_crafter_server_r20
        saved.update(phase='feeding', case='target')
        self.sdk.nbts[saved['positions']['crafter']]['Items'] = [
            {'Name': {'__type__': 8, '__value__': 'minecraft:shield'},
             'Count': {'__type__': 1, '__value__': 1}},
            {'Name': {'__type__': 8, '__value__': 'minecraft:banner'},
             'Count': {'__type__': 1, '__value__': 1},
             'Damage': {'__type__': 2, '__value__': 4}, 'tag': {'Patterns': []}}]
        calls = self.sdk.calls
        with self.assertRaises(AssertionError):
            self.action('pulse_on')
        self.assertEqual(self.sdk.calls, calls)
        self.assert_restored()

    def test_restore_without_fixture_is_idempotent(self):
        self.assertTrue(self.action('restore')['no_fixture_mutations'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
