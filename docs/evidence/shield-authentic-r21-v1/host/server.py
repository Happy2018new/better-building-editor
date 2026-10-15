"""Owned actors and two real shield frames; all native item userdata is frozen."""
import copy
import json
import math
import sys
import mod.server.extraServerApi as api
from modern_projection.projection.nbt_spatial import root_payload, scalar

KEY = '_shield_authentic_server_r21'
factory = api.GetEngineCompFactory()
level = api.GetLevelId()
players = api.GetPlayerList()
assert len(players) == 1
player = players[0]
owner = api.GetSystem('ModernProjection', 'ModernProjectionServerSystem')
info, items = factory.CreateBlockInfo(player), factory.CreateItem(player)
inventory_type = api.GetMinecraftEnum().ItemPosType.INVENTORY


def inventory():
    return [items.GetPlayerItem(inventory_type, slot, True) for slot in range(36)]


def cell(pos, dimension):
    return {'pos': pos, 'block': info.GetBlockNew(pos, dimension),
            'liquid': info.GetLiquidBlock(pos, dimension),
            'nbt': info.GetBlockEntityData(dimension, pos)}


def drops():
    result = []
    for entity in factory.CreateEntityComponent(player).GetEntitiesBySelector('@e[type=item]') or []:
        result.append({'entity': entity, 'item': items.GetDroppedItem(entity, True),
            'pos': factory.CreatePos(entity).GetPos(),
            'dimension': factory.CreateDimension(entity).GetEntityDimensionId()})
    return result


if ACTION == 'journal':
    assert not hasattr(sys, KEY)
    foot = factory.CreatePos(player).GetFootPos()
    dimension = factory.CreateDimension(player).GetEntityDimensionId()
    assert dimension == 0
    origin = (int(math.floor(foot[0])) + 2, int(math.floor(foot[1])) + 2,
              int(math.floor(foot[2])) + 3)
    region = [(origin[0] + x, origin[1] + y, origin[2] + z)
              for x in range(-1, 5) for y in range(-1, 3) for z in range(-1, 3)]
    journal = [cell(pos, dimension) for pos in region]
    for row in journal:
        assert row['block'] and row['block']['name'] == 'minecraft:air'
        assert not row['liquid'] or row['liquid']['name'] == 'minecraft:air'
        assert row['nbt'] is None
    saved = {'player': player, 'dimension': dimension, 'foot': foot, 'origin': origin,
             'inventory': inventory(), 'selected': items.GetSelectSlotId(),
             'journal': copy.deepcopy(journal), 'actors': {}, 'touched': [],
             'frames': [], 'drops_before': drops()}
    setattr(sys, KEY, saved)
    for index, label in enumerate(('plain', 'authentic', 'sword')):
        position = (foot[0] + 16. + index * 2., foot[1] + 2., foot[2] + 4.)
        entity = owner.CreateEngineEntityByTypeStr('modern_projection:anchor', position,
                                                  (0., 0.), dimension, True, False)
        assert entity
        saved['actors'][label] = entity
    _result = json.dumps({'journaled': True, 'guard_cells': len(journal),
                          'origin': origin, 'actors': saved['actors'], 'foot': foot})
else:
    saved = getattr(sys, KEY, None)
    if ACTION == 'restore' and saved is None:
        _result = json.dumps({'restored': True, 'already_absent': True})
    else:
        assert saved is not None and saved['player'] == player
        dimension = saved['dimension']
        assert factory.CreateDimension(player).GetEntityDimensionId() == dimension
        if ACTION == 'frames':
            assert not saved['touched']
            origin = saved['origin']
            for index, label in enumerate(('plain', 'authentic')):
                pos = (origin[0] + index * 2, origin[1], origin[2])
                support = (pos[0], pos[1], pos[2] + 1)
                saved['touched'].append(support)
                assert info.SetBlockNew(support, {'name': 'minecraft:cyan_concrete', 'aux': 0},
                                        0, dimension, True, True)
                saved['touched'].append(pos)
                assert items.SetInvItemNum(35, 0)
                assert items.SpawnItemToPlayerInv({'itemName': 'minecraft:frame', 'count': 1,
                                                   'auxValue': 0}, player, 35)
                assert info.PlayerUseItemToPos(support, inventory_type, 35, 2)
                assert info.GetBlockNew(pos, dimension)['name'] == 'minecraft:frame'
                item = INPUTS['items'][label]
                source = {'itemName': item['newItemName'], 'count': 1,
                          'auxValue': item['newAuxValue']}
                if item.get('userData') is not None:
                    source['userData'] = copy.deepcopy(item['userData'])
                assert items.SetInvItemNum(35, 0)
                assert items.SpawnItemToPlayerInv(source, player, 35)
                before = items.GetPlayerItem(inventory_type, 35, True)
                assert info.PlayerUseItemToPos(pos, inventory_type, 35, 2)
                nbt = info.GetBlockEntityData(dimension, pos)
                entry = root_payload(nbt)['Item']
                assert scalar(entry, 'Name') == 'minecraft:shield'
                assert scalar(entry, 'Damage') == 0
                if label == 'authentic':
                    assert root_payload(entry.get('tag')) == item['userData']
                saved['frames'].append({'label': label, 'pos': pos,
                    'item_requested': source, 'inventory_before_insert': before, 'nbt': nbt})
            assert items.SetInvItemNum(35, 0)
            if saved['inventory'][35]:
                assert items.SpawnItemToPlayerInv(saved['inventory'][35], player, 35)
            assert inventory() == saved['inventory']
            _result = json.dumps({'frames': saved['frames'], 'origin': origin,
                                  'inventory_restored': True})
        elif ACTION == 'restore':
            for pos in reversed(saved['touched']):
                info.SetBlockNew(pos, {'name': 'minecraft:air', 'aux': 0},
                                 0, dimension, True, False)
                assert info.GetBlockNew(pos, dimension)['name'] == 'minecraft:air'
            removed = []
            original = set(row['entity'] for row in saved['drops_before'])
            for row in drops():
                if row['entity'] in original or row['dimension'] != dimension or not row['pos']:
                    continue
                if max(abs(row['pos'][i] - saved['origin'][i]) for i in range(3)) > 8.:
                    continue
                name = row['item'].get('newItemName', row['item'].get('itemName'))
                assert name in ('minecraft:frame', 'minecraft:shield'), row
                assert items.GetDroppedItem(row['entity'], True) == row['item']
                assert owner.DestroyEntity(row['entity'])
                removed.append(row)
            for label, entity in list(saved['actors'].items()):
                assert owner.DestroyEntity(entity)
                del saved['actors'][label]
            current = inventory()
            for slot, before in enumerate(saved['inventory']):
                if current[slot] != before:
                    assert items.SetInvItemNum(slot, 0)
                    if before:
                        assert items.SpawnItemToPlayerInv(before, player, slot)
            assert inventory() == saved['inventory']
            assert items.GetSelectSlotId() == saved['selected']
            actual = [cell(tuple(row['pos']), dimension) for row in saved['journal']]
            assert actual == saved['journal']
            _result = json.dumps({'restored': True, 'guard_cells_restored': len(actual),
                'inventory_restored': True, 'selected_restored': True, 'actors_removed': True,
                'foot_before': saved['foot'], 'foot_after': factory.CreatePos(player).GetFootPos(),
                'removed_fixture_drops': removed})
            delattr(sys, KEY)
        else:
            raise ValueError(ACTION)
