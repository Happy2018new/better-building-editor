"""Execute with ACTION and INPUTS supplied by the owner-bound host."""
import copy
import json
import math
import sys
import time
import mod.server.extraServerApi as api
from modern_projection.projection.nbt_spatial import root_payload, scalar

factory = api.GetEngineCompFactory()
level = api.GetLevelId()
players = api.GetPlayerList()
assert len(players) == 1
player = players[0]
info = factory.CreateBlockInfo(player)
states = factory.CreateBlockState(level)
items = factory.CreateItem(player)
inventory_type = api.GetMinecraftEnum().ItemPosType.INVENTORY


def inventory():
    return [items.GetPlayerItem(inventory_type, slot, True) for slot in range(36)]


def cell(pos, dimension):
    return {'pos': pos, 'block': info.GetBlockNew(pos, dimension),
            'liquid': info.GetLiquidBlock(pos, dimension),
            'nbt': info.GetBlockEntityData(dimension, pos)}


def item_name(item):
    return None if not item else item.get('newItemName', item.get('itemName'))


def list_items(nbt):
    root = root_payload(nbt)
    assert root is not None and 'Items' in root, nbt
    value = root['Items']
    if isinstance(value, dict):
        assert value.get('__type__') == 9, value
        value = value['__value__']
    assert isinstance(value, list), value
    return value


def dropped():
    result = []
    for entity in factory.CreateEntityComponent(player).GetEntitiesBySelector('@e[type=item]') or []:
        result.append({'entity': entity, 'pos': factory.CreatePos(entity).GetPos(),
                       'dimension': factory.CreateDimension(entity).GetEntityDimensionId(),
                       'item': items.GetDroppedItem(entity, True)})
    return result


def inspect(saved):
    dimension, positions = saved['dimension'], saved['positions']
    chest = positions['chest']
    hopper = positions['hopper']
    return {'phase': saved['phase'], 'case': saved.get('case'),
            'blocks': dict((name, cell(pos, dimension)) for name, pos in positions.items()),
            'crafter_states': states.GetBlockStates(positions['crafter'], dimension),
            'chest_size': items.GetContainerSize(chest, dimension),
            'chest': [items.GetContainerItem(chest, slot, dimension, True) for slot in range(27)],
            'hopper': [items.GetContainerItem(hopper, slot, dimension, True) for slot in range(5)],
            'drops': dropped(), 'inventory_unchanged': inventory() == saved['inventory']}


if ACTION == 'journal':
    assert not hasattr(sys, '_shield_crafter_server_r20')
    dimension = factory.CreateDimension(player).GetEntityDimensionId()
    foot = factory.CreatePos(player).GetFootPos()
    assert dimension == 0 and foot is not None
    origin = (int(math.floor(foot[0])) + 4, int(math.floor(foot[1])) + 2,
              int(math.floor(foot[2])) + 4)
    offsets = {'crafter': (0, 0, 0), 'chest': (0, 0, -1),
               'hopper': (0, 1, 0), 'power': (1, 0, 0)}
    positions = dict((name, tuple(origin[i] + delta[i] for i in range(3)))
                     for name, delta in offsets.items())
    region = [tuple(origin[i] + delta[i] for i in range(3))
              for delta in [(x, y, z) for x in range(-1, 3)
                             for y in range(-1, 3) for z in range(-2, 2)]]
    journal = [cell(pos, dimension) for pos in region]
    for row in journal:
        assert row['block'] and row['block']['name'] == 'minecraft:air', row
        assert not row['liquid'] or row['liquid']['name'] == 'minecraft:air', row
        assert row['nbt'] is None, row
    saved = {'phase': 'journaled', 'player': player, 'dimension': dimension,
             'foot': foot, 'inventory': inventory(), 'selected': items.GetSelectSlotId(),
             'positions': positions, 'journal': copy.deepcopy(journal),
             'touched': [], 'drops_before': dropped(), 'started': time.time(),
             'config': INPUTS['blocks']}
    sys._shield_crafter_server_r20 = saved
    _result = json.dumps(saved)
else:
    saved = getattr(sys, '_shield_crafter_server_r20', None)
    if ACTION == 'restore' and saved is None:
        _result = json.dumps({'present': False, 'no_fixture_mutations': True})
    else:
        assert saved is not None and saved['player'] == player
        dimension, positions = saved['dimension'], saved['positions']
        assert factory.CreateDimension(player).GetEntityDimensionId() == dimension
        if ACTION == 'place':
            assert saved['phase'] == 'journaled'
            for name in ('chest', 'crafter', 'hopper'):
                spec = saved['config'][name]
                aux = states.GetBlockAuxValueFromStates(spec['name'], spec['states'])
                assert aux == spec['aux'], (spec, aux)
                saved['touched'].append(name)
                assert info.SetBlockNew(positions[name], {'name': spec['name'], 'aux': aux},
                                        0, dimension, True, True)
                assert states.GetBlockStates(positions[name], dimension) == spec['states']
            root = root_payload(info.GetBlockEntityData(dimension, positions['crafter']))
            assert root is not None and scalar(root, 'id') == 'Crafter'
            assert scalar(root, 'disabled_slots') == 0
            assert not list_items(root)
            saved['phase'] = 'placed'
            _result = json.dumps(inspect(saved))
        elif ACTION in ('feed_positive', 'feed_target'):
            assert saved['phase'] in ('placed', 'cleared')
            for name in ('crafter', 'hopper', 'chest'):
                assert not list_items(info.GetBlockEntityData(dimension, positions[name])), name
            payload = INPUTS['positive'] if ACTION == 'feed_positive' else INPUTS['target']
            saved['case'] = 'positive' if ACTION == 'feed_positive' else 'target'
            saved['phase'] = 'feeding'
            filled = []
            for slot, item in enumerate(payload):
                assert items.SpawnItemToContainer(item, slot, positions['hopper'], dimension)
                actual = items.GetContainerItem(positions['hopper'], slot, dimension, True)
                assert actual and item_name(actual) == item_name(item), actual
                assert actual.get('count') == 1
                filled.append({'slot': slot, 'input': item, 'readback': actual})
            _result = json.dumps({'case': saved['case'], 'filled': filled,
                                  'snapshot': inspect(saved)})
        elif ACTION == 'inspect':
            _result = json.dumps(inspect(saved))
        elif ACTION == 'pulse_on':
            assert saved['phase'] == 'feeding'
            assert all(not items.GetContainerItem(positions['hopper'], slot, dimension, True)
                       for slot in range(5))
            nbt = info.GetBlockEntityData(dimension, positions['crafter'])
            entries = list_items(nbt)
            expected = INPUTS['positive'] if saved['case'] == 'positive' else INPUTS['target']
            assert sorted(scalar(root_payload(row), 'Name') for row in entries) == sorted(item_name(row) for row in expected)
            assert all(scalar(root_payload(row), 'Count') == 1 for row in entries)
            if saved['case'] == 'target':
                banner = next(row for row in entries if scalar(root_payload(row), 'Name') == 'minecraft:banner')
                banner = root_payload(banner)
                assert scalar(banner, 'Damage') == 4
                tag = root_payload(banner.get('tag'))
                assert tag is not None
                patterns = tag.get('Patterns')
                if isinstance(patterns, dict):
                    assert patterns.get('__type__') == 9
                    patterns = patterns['__value__']
                assert [(scalar(root_payload(row), 'Color'), scalar(root_payload(row), 'Pattern'))
                        for row in patterns] == [(1, 'bo'), (14, 'cr'), (11, 'mc')]
            before = inspect(saved)
            assert before['chest_size'] == 27 and not any(before['chest'])
            saved['touched'].append('power')
            assert info.SetBlockNew(positions['power'], {'name': 'minecraft:redstone_block', 'aux': 0},
                                    0, dimension, True, True)
            saved['phase'] = 'pulse_on'
            _result = json.dumps({'before': before, 'power': info.GetBlockNew(positions['power'], dimension)})
        elif ACTION == 'pulse_off':
            assert saved['phase'] == 'pulse_on'
            info.SetBlockNew(positions['power'], {'name': 'minecraft:air', 'aux': 0},
                             0, dimension, True, True)
            assert info.GetBlockNew(positions['power'], dimension)['name'] == 'minecraft:air'
            saved['phase'] = 'pulsed'
            _result = json.dumps(inspect(saved))
        elif ACTION == 'clear_output':
            assert saved['phase'] == 'pulsed' and saved['case'] == 'positive'
            assert not list_items(info.GetBlockEntityData(dimension, positions['crafter']))
            assert all(not items.GetContainerItem(positions['hopper'], slot, dimension, True)
                       for slot in range(5))
            before = inspect(saved)
            output = [row for row in before['chest'] if row]
            assert len(output) == 1 and item_name(output[0]) == 'minecraft:oak_planks'
            assert output[0]['count'] == 4
            assert items.SpawnItemToContainer({}, 0, positions['chest'], dimension)
            assert all(not items.GetContainerItem(positions['chest'], slot, dimension, True)
                       for slot in range(27))
            saved['phase'] = 'cleared'
            _result = json.dumps({'positive_verified': True, 'before': before})
        elif ACTION == 'restore':
            errors = []
            for name in ('power', 'hopper', 'crafter', 'chest'):
                try:
                    info.SetBlockNew(positions[name], {'name': 'minecraft:air', 'aux': 0},
                                     0, dimension, True, False)
                except Exception as exc:
                    errors.append({'stage': name, 'error': repr(exc)})
            removed = []
            original_ids = set(row['entity'] for row in saved['drops_before'])
            allowed = set(('minecraft:oak_log', 'minecraft:oak_planks', 'minecraft:shield', 'minecraft:banner'))
            owner = api.GetSystem('ModernProjection', 'ModernProjectionServerSystem')
            for row in dropped():
                if row['entity'] in original_ids or row['dimension'] != dimension or not row['pos']:
                    continue
                if max(abs(row['pos'][i] - positions['crafter'][i]) for i in range(3)) > 8.:
                    continue
                if item_name(row['item']) not in allowed:
                    errors.append({'stage': 'unidentified_new_drop', 'evidence': row})
                    continue
                same = items.GetDroppedItem(row['entity'], True) == row['item']
                assert same, row
                returned = owner.DestroyEntity(row['entity'])
                removed.append({'evidence': row, 'destroyed': returned})
                if not returned:
                    errors.append({'stage': 'owned_drop_cleanup', 'entity': row['entity']})
            current = inventory()
            for slot, before in enumerate(saved['inventory']):
                if current[slot] != before:
                    assert items.SetInvItemNum(slot, 0)
                    if before:
                        assert items.SpawnItemToPlayerInv(before, player, slot)
            actual = [cell(tuple(row['pos']), dimension) for row in saved['journal']]
            for before, after in zip(saved['journal'], actual):
                assert before == after, (before, after)
            assert inventory() == saved['inventory']
            assert items.GetSelectSlotId() == saved['selected']
            assert not errors, errors
            _result = json.dumps({'restored': True, 'guard_cells_verified': len(actual),
                                  'inventory_restored': True, 'selected_restored': True,
                                  'player_position_written': False, 'drop_cleanup': removed,
                                  'foot_before': saved['foot'],
                                  'foot_after': factory.CreatePos(player).GetFootPos()})
            del sys._shield_crafter_server_r20
        else:
            raise ValueError('Unknown fixture action: ' + ACTION)
