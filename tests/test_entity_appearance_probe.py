"""Native fixture helpers restore resources even when a player placement fails."""
import json
import runpy
import sys
import types
import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
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

    def GetFrameRotation(self, pos, unused_dimension):
        return scalar(self.entities[tuple(pos)], 'ItemRotation')

    def SetFrameRotation(self, pos, unused_dimension, angle):
        self.entities[tuple(pos)]['ItemRotation'] = tag(angle, 5)
        return True

    def GetBlockPaletteBetweenPos(self, unused_dimension, pos, unused_hi, unused_flag):
        value = self.world[tuple(pos)]
        return types.SimpleNamespace(SerializeBlockPalette=lambda: {
            'common': {(value['name'], value['aux']): [0]}, 'actor': {value['name']: {0: {}}}})

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

    def test_selected_case_ignores_unrelated_occupied_fixture_cells(self):
        fixture = NativeFixture()
        fixture.world[(41, 80, -20)] = {'name': 'minecraft:oak_leaves', 'aux': 0}
        with fake_api(fixture):
            sys._p0_entity_appearance_selected = ('bed_silver',)
            result = json.loads(self.helper('setup')['_result'])
            self.assertEqual([row['case'] for row in result['rows']], ['bed_silver'])
            self.assertFalse(hasattr(sys, '_p0_entity_appearance_selected'))
            self.helper('cleanup')
            self.assertEqual(fixture.world[(41, 80, -20)]['name'], 'minecraft:oak_leaves')

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

    def test_inventory_cleanup_exception_keeps_primary_failure_and_still_restores_rotation(self):
        fixture = NativeFixture(fail_placement=4)
        clear = fixture.SetInvItemNum
        calls = [0]

        def fail_once(slot, count):
            calls[0] += 1
            if calls[0] == 5:
                raise RuntimeError('Injected inventory cleanup failure')
            return clear(slot, count)

        fixture.SetInvItemNum = fail_once
        with fake_api(fixture):
            with self.assertRaisesRegex(RuntimeError, 'Injected native player placement'):
                self.helper('setup')
            self.assertEqual(fixture.original_rotation, fixture.rotation)
            self.assertIn('inventory cleanup failure', sys._p0_entity_appearances['setup_cleanup_errors'][0])
            self.helper('cleanup')
            self.assertIsNone(fixture.inventory)

    def test_world_cleanup_api_failure_still_clears_inventory_and_restores_rotation(self):
        fixture = NativeFixture()
        with fake_api(fixture):
            self.helper('setup')
            failed = tuple(sys._p0_entity_appearances['reserved'][0])
            write = fixture.SetBlockNew

            def fail_one_position(pos, value, *args):
                if tuple(pos) == failed:
                    raise RuntimeError('Injected world cleanup failure')
                return write(pos, value, *args)

            fixture.SetBlockNew = fail_one_position
            fixture.rotation = (80., 90.)
            fixture.inventory = {'itemName': 'minecraft:diamond_sword', 'count': 1}
            with self.assertRaisesRegex(AssertionError, 'Native appearance cleanup failed'):
                self.helper('cleanup')
            self.assertIsNone(fixture.inventory)
            self.assertEqual(fixture.original_rotation, fixture.rotation)
            self.assertTrue(hasattr(sys, '_p0_entity_appearances'))
            fixture.SetBlockNew = write
            self.helper('cleanup')
            self.assertFalse(hasattr(sys, '_p0_entity_appearances'))

    def test_item_component_failure_does_not_prevent_rotation_cleanup(self):
        fixture = NativeFixture()
        with fake_api(fixture):
            self.helper('setup')
            fixture.rotation = (80., 90.)
            with patch.object(fixture, 'CreateItem', side_effect=RuntimeError('Injected component failure')):
                with self.assertRaisesRegex(AssertionError, 'component failure'):
                    self.helper('cleanup')
            self.assertEqual(fixture.original_rotation, fixture.rotation)
            self.assertTrue(all(row['name'] == 'minecraft:air' for row in fixture.world.values()))
            self.helper('cleanup')

    def test_documented_frame_rotations_capture_raw_tags_and_restore_original_angles(self):
        fixture = NativeFixture()
        with fake_api(fixture):
            self.helper('setup')
            self.helper('fill')
            data = json.loads(self.helper('rotations')['_result'])
            self.assertEqual(16, len(data['samples']))
            self.assertTrue(data['rotations_restored'])
            for row in data['samples']:
                self.assertEqual(row['api_requested_degrees'], row['api_observed_degrees'])
                self.assertEqual(tag(row['api_requested_degrees'], 5), row['nbt_item_rotation'])
            for row in sys._p0_entity_appearances['rows']:
                if row.get('fill_item'):
                    self.assertEqual(0., fixture.GetFrameRotation(tuple(row['pos']), 0))
            self.helper('cleanup')

    def test_frame_rotation_api_failure_retains_partial_evidence_and_restores_original(self):
        fixture = NativeFixture()
        with fake_api(fixture):
            self.helper('setup')
            self.helper('fill')
            setter = fixture.SetFrameRotation

            def fail_at_ninety(pos, dimension, angle):
                if angle == 90.:
                    raise RuntimeError('Injected frame rotation failure')
                return setter(pos, dimension, angle)

            fixture.SetFrameRotation = fail_at_ninety
            with self.assertRaisesRegex(RuntimeError, 'frame rotation failure'):
                self.helper('rotations')
            self.assertEqual(2, len(sys._p0_entity_appearances['frame_rotation_samples']))
            self.assertEqual([], sys._p0_entity_appearances['frame_rotation_cleanup_errors'])
            first_frame = next(row for row in sys._p0_entity_appearances['rows'] if row.get('fill_item'))
            self.assertEqual(0., fixture.GetFrameRotation(tuple(first_frame['pos']), 0))
            self.helper('cleanup')


class NativeAppearanceHostCleanupTests(unittest.TestCase):
    def test_replication_waits_for_actual_palette_instead_of_one_fixed_sleep(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        import verify_native_entity_appearances as host
        ready = {'ready': True, 'rows': [{'case': 'frame_filled'}]}
        with patch.object(host, 'execute', side_effect=[{'ready': False, 'pending': ['frame_filled']}, ready]) as execute, \
                patch.object(host.time, 'monotonic', side_effect=[0., 1.]), patch.object(host.time, 'sleep') as sleep:
            self.assertEqual(ready, host.replicated_palettes(object(), 'read'))
        self.assertEqual(2, execute.call_count)
        self.assertTrue(all(call.args[2] for call in execute.call_args_list))
        sleep.assert_called_once_with(.15)

    def test_replication_timeout_records_the_specific_missing_case(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        import verify_native_entity_appearances as host
        with patch.object(host, 'execute', return_value={'ready': False, 'pending': ['frame_filled']}), \
                patch.object(host.time, 'monotonic', side_effect=[0., 13.]):
            with self.assertRaisesRegex(RuntimeError, 'frame_filled'):
                host.replicated_palettes(object(), 'read')

    def host(self, initial_failure=False):
        sys.path.insert(0, str(ROOT / 'tools'))
        import verify_native_entity_appearances as host
        actions = []

        def execute(unused_client, code, client_side=False):
            if 'Owned native fixtures' in code:
                if initial_failure:
                    raise RuntimeError('Primary setup failure')
                return {'rows': []}
            if 'json.dumps(getattr(sys' in code:
                raise RuntimeError('Snapshot unavailable')
            if 'hasattr(sys,"_p0_entity_appearances")' in code:
                return True
            if 'Restore all temporary native' in code:
                actions.append('native_cleanup')
                return True
            if 'for name in (' in code:
                actions.append('client_cleanup')
                return True
            return {'ready': True, 'rows': []}

        with TemporaryDirectory() as temporary:
            output = Path(temporary) / 'evidence.json'
            with patch.object(sys, 'argv', ['verify', str(output)]), \
                    patch.object(host, 'Client'), patch.object(host, 'execute', side_effect=execute), \
                    patch.object(host.time, 'sleep'):
                with self.assertRaisesRegex(RuntimeError, 'Primary setup failure' if initial_failure else 'Snapshot unavailable'):
                    host.main()
            evidence = json.loads(output.read_text())
        return actions, evidence

    def test_partial_snapshot_failure_never_skips_native_or_client_cleanup(self):
        actions, evidence = self.host()
        self.assertEqual(['native_cleanup', 'client_cleanup'], actions)
        self.assertTrue(evidence['native_cleaned'])
        self.assertTrue(evidence['client_cleaned'])
        self.assertFalse(evidence['completed'])

    def test_cleanup_snapshot_failure_preserves_primary_error_and_attempts_all_restoration(self):
        actions, evidence = self.host(initial_failure=True)
        self.assertEqual(['native_cleanup', 'client_cleanup'], actions)
        self.assertIn('Primary setup failure', evidence['error'])
        self.assertIn('Snapshot unavailable', evidence['cleanup_errors'][0])


if __name__ == '__main__':
    unittest.main()
