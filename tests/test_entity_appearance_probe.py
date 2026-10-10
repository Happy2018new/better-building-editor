"""Native fixture helpers restore resources even when a player placement fails."""
import json
import runpy
import sys
import types
import unittest
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_groups, block_registry
from projection.nbt_spatial import scalar


def tag(value, kind):
    return {'__type__': kind, '__value__': value}


class NativeFixture:
    def __init__(self, fail_placement=None):
        self.world, self.entities = {}, {}
        self.inventory = None
        self.rotation, self.original_rotation = (5., 12.), (5., 12.)
        self.placements = 0
        self.fail_placement = fail_placement
        self.enums = types.SimpleNamespace(ItemPosType=types.SimpleNamespace(INVENTORY=0),
                                           ItemColor=types.SimpleNamespace(Silver=7, LightBlue=12))

    def __getattr__(self, name):
        if name.startswith('Create'):
            return lambda unused: self
        raise AttributeError(name)

    def GetEntityDimensionId(self):
        return 0

    def GetFootPos(self):
        return (0., 64., 0.)

    def GetRot(self):
        return self.rotation

    def SetRot(self, rotation):
        self.rotation = tuple(rotation)
        return True

    def GetPlayerItem(self, unused_type, unused_slot, unused_flag):
        return deepcopy(self.inventory)

    def SetInvItemNum(self, unused_slot, count):
        self.inventory = None if not count else dict(self.inventory, count=count)
        return True

    def SpawnItemToPlayerInv(self, item, unused_player, unused_slot):
        self.inventory = dict(item)
        return False

    def GetBlockNew(self, pos, unused_dimension):
        return deepcopy(self.world.get(tuple(pos), {'name': 'minecraft:air', 'aux': 0}))

    def SetBlockNew(self, pos, block, *unused):
        self.world[tuple(pos)] = deepcopy(block)
        if block['name'] == 'minecraft:air':
            self.entities.pop(tuple(pos), None)
        return True

    def GetBlockEntityData(self, unused_dimension, pos):
        return deepcopy(self.entities.get(tuple(pos)))

    def SetBedColor(self, pos, color, unused_dimension):
        block = self.world[tuple(pos)]
        offset, unused = block_groups.group_partner((block['name'], block['aux']))
        partner = tuple(pos[axis] + offset[axis] for axis in range(3))
        for point in (tuple(pos), partner):
            self.entities[point]['color'] = tag(color, 1)
        return True

    def GetBedColor(self, pos, unused_dimension):
        return scalar(self.entities[tuple(pos)], 'color')

    def PlayerUseItemToPos(self, support, unused_type, unused_slot, face):
        if tuple(support) in self.entities and self.inventory['itemName'] == 'minecraft:diamond_sword':
            self.entities[tuple(support)]['Item'] = {'Name': tag('minecraft:diamond_sword', 8)}
            self.entities[tuple(support)]['ItemRotation'] = tag(0., 5)
            return True
        self.placements += 1
        if self.placements == self.fail_placement:
            raise RuntimeError('Injected native player placement failure')
        normal = ((0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0))[face]
        pos = tuple(support[axis] + normal[axis] for axis in range(3))
        name = self.inventory['itemName']
        identity = 'Skull'
        if name == 'minecraft:banner':
            name, identity = 'minecraft:standing_banner', 'Banner'
        elif name == 'minecraft:bed':
            identity = 'Bed'
        elif 'frame' in name:
            identity = 'GlowItemFrame' if 'glow' in name else 'ItemFrame'
        aux = block_registry.DEFAULT_AUX[name]
        if name == 'minecraft:bed':
            aux = block_registry.from_states(name, {'direction': 0, 'head_piece_bit': False,
                                                     'occupied_bit': False})[1]
        self.world[pos] = {'name': name, 'aux': aux}
        entity = {'id': tag(identity, 8), 'x': tag(pos[0], 3), 'y': tag(pos[1], 3), 'z': tag(pos[2], 3)}
        if identity == 'Skull':
            entity['Rotation'] = tag(self.rotation[1], 5)
        if identity == 'Banner':
            entity['Type'] = tag(self.inventory.get('userData', {}).get('Type', 0), 3)
        self.entities[pos] = entity
        if identity == 'Bed':
            offset, reciprocal = block_groups.group_partner((name, aux))
            partner = tuple(pos[axis] + offset[axis] for axis in range(3))
            self.world[partner] = {'name': name, 'aux': reciprocal[1]}
            self.entities[partner] = dict(deepcopy(entity), x=tag(partner[0], 3),
                                          y=tag(partner[1], 3), z=tag(partner[2], 3))
        return True


@contextmanager
def fake_api(fixture):
    modules = {}
    for name in ('mod', 'mod.server', 'mod.server.extraServerApi', 'modern_projection',
                 'modern_projection.projection', 'modern_projection.projection.block_registry',
                 'modern_projection.projection.block_groups', 'modern_projection.projection.nbt_spatial'):
        modules[name] = sys.modules.get(name)
        sys.modules[name] = types.ModuleType(name)
    import projection.nbt_spatial as nbt_spatial
    sys.modules['modern_projection.projection.block_registry'] = block_registry
    sys.modules['modern_projection.projection.block_groups'] = block_groups
    sys.modules['modern_projection.projection.nbt_spatial'] = nbt_spatial
    api = sys.modules['mod.server.extraServerApi']
    api.GetEngineCompFactory = lambda: fixture
    api.GetPlayerList = lambda: ['player']
    api.GetLevelId = lambda: 'level'
    api.GetMinecraftEnum = lambda: fixture.enums
    try:
        yield
    finally:
        for name, original in modules.items():
            if original is None:
                del sys.modules[name]
            else:
                sys.modules[name] = original
        if hasattr(sys, '_p0_entity_appearances'):
            del sys._p0_entity_appearances


class NativeAppearanceProbeTests(unittest.TestCase):
    def helper(self, phase):
        return runpy.run_path(str(ROOT / ('tools/p0_entity_appearance_' + phase + '.py')))

    def test_complete_batch_uses_native_items_colors_and_preserves_raw_frame_compounds(self):
        fixture = NativeFixture()
        with fake_api(fixture):
            data = json.loads(self.helper('setup')['_result'])
            self.assertEqual(19, len(data['rows']))
            self.assertEqual(fixture.original_rotation, fixture.rotation)
            self.assertIsNone(fixture.inventory)
            native = [row for row in data['rows'] if row['case'].startswith('skull_floor')]
            self.assertEqual(8, len(native))
            self.assertTrue(all(row['observed_rotation'] == row['yaw'] for row in native))
            filled = json.loads(self.helper('fill')['_result'])
            frames = [row for row in filled['rows'] if row.get('fill_item')]
            self.assertTrue(all(row['fill_observed'] for row in frames))
            self.assertTrue(all(row['filled_item']['Name']['__value__'] == 'minecraft:diamond_sword' for row in frames))
            self.helper('cleanup')
            self.assertTrue(all(row['name'] == 'minecraft:air' for row in fixture.world.values()))
            self.assertIsNone(fixture.inventory)

    def test_primary_failure_restores_rotation_inventory_and_cleanup_removes_partial_fixture(self):
        fixture = NativeFixture(fail_placement=4)
        with fake_api(fixture):
            with self.assertRaisesRegex(RuntimeError, 'Injected'):
                self.helper('setup')
            self.assertEqual(fixture.original_rotation, fixture.rotation)
            self.assertIsNone(fixture.inventory)
            self.helper('cleanup')
            self.assertTrue(all(row['name'] == 'minecraft:air' for row in fixture.world.values()))


if __name__ == '__main__':
    unittest.main()
