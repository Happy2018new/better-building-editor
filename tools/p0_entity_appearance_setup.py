"""Owned native fixtures for floor skull yaw, bed colours, frames and banners."""
import json
import math
import sys
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry, block_groups
from modern_projection.projection.nbt_spatial import root_payload, scalar

assert not hasattr(sys, '_p0_entity_appearances'), 'Clean up the previous entity appearances first'
factory = api.GetEngineCompFactory()
player = api.GetPlayerList()[0]
dimension = factory.CreateDimension(player).GetEntityDimensionId()
info, items, rotation = factory.CreateBlockInfo(player), factory.CreateItem(player), factory.CreateRot(player)
item_type = api.GetMinecraftEnum().ItemPosType.INVENTORY
integer_types = (int, long) if sys.version_info[0] == 2 else (int,)
saved_rotation = rotation.GetRot()
assert (isinstance(saved_rotation, (tuple, list)) and len(saved_rotation) == 2 and
        all(isinstance(value, integer_types + (float,)) and type(value) is not bool and
            not math.isnan(value) and not math.isinf(value) for value in saved_rotation)), (
    'Player rotation readback failed', saved_rotation)
slot = None
for candidate in range(36):
    existing = items.GetPlayerItem(item_type, candidate, True)
    assert existing is None or isinstance(existing, dict), ('Malformed inventory readback', candidate, existing)
    if existing:
        count = existing.get('count')
        assert (isinstance(count, integer_types) and type(count) is not bool and count >= 0), (
            'Malformed inventory count', candidate, existing)
    if not existing or existing['count'] == 0:
        slot = candidate
        break
assert slot is not None, 'Entity appearance fixtures need one empty inventory slot'
foot = factory.CreatePos(player).GetFootPos()
origin = (int(math.floor(foot[0])) + 20, int(math.floor(foot[1])) + 16,
          int(math.floor(foot[2])) - 20)
normals = ((0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0))
plans = [{'case': 'skull_floor_yaw_%g' % yaw, 'name': 'minecraft:skeleton_skull',
          'yaw': yaw, 'face': 1} for yaw in (0., 22.5, 45., 90., 135., 180., 225., 270.)]
plans.extend({'case': 'skull_wall_face%d' % face, 'name': 'minecraft:skeleton_skull',
              'yaw': 0., 'face': face} for face in (2, 3, 4, 5))
plans.extend((
    {'case': 'dragon_floor_yaw45', 'name': 'minecraft:dragon_head', 'yaw': 45., 'face': 1},
    {'case': 'bed_silver', 'name': 'minecraft:bed', 'yaw': 0., 'face': 1,
     'color': api.GetMinecraftEnum().ItemColor.Silver},
    {'case': 'bed_light_blue', 'name': 'minecraft:bed', 'yaw': 0., 'face': 1,
     'color': api.GetMinecraftEnum().ItemColor.LightBlue},
    {'case': 'frame_filled', 'name': 'minecraft:frame', 'yaw': 0., 'face': 2,
     'fill_item': 'minecraft:diamond_sword'},
    {'case': 'glow_frame_filled', 'name': 'minecraft:glow_frame', 'yaw': 0., 'face': 2,
     'fill_item': 'minecraft:diamond_sword'},
    {'case': 'banner_base1', 'name': 'minecraft:banner', 'yaw': 0., 'face': 1, 'aux': 1},
    {'case': 'banner_ominous', 'name': 'minecraft:banner', 'yaw': 0., 'face': 1,
     'aux': 15, 'userData': {'Type': 1}},
))
for name in ('wither_skeleton_skull', 'zombie_head', 'creeper_head'):
    plans.extend(({'case': name + '_floor_yaw45', 'name': 'minecraft:' + name, 'yaw': 45., 'face': 1},
                  {'case': name + '_wall_face2', 'name': 'minecraft:' + name, 'yaw': 0., 'face': 2}))
public_plans = getattr(sys, '_p0_entity_appearance_public_plans', None)
if public_plans is not None:
    del sys._p0_entity_appearance_public_plans
    assert len(public_plans) == 1 and public_plans[0].get('public_fixture'), public_plans
    plans = public_plans
selected = getattr(sys, '_p0_entity_appearance_selected', None)
if selected is not None:
    del sys._p0_entity_appearance_selected
    assert set(selected).issubset(set(plan['case'] for plan in plans)), selected
    plans = [plan for plan in plans if plan['case'] in selected]
    assert plans, 'At least one native appearance case is required'
reserved, rows = set(), []
for index, plan in enumerate(plans):
    target = (origin[0] + index % 5 * 7, origin[1], origin[2] + index // 5 * 7)
    support = tuple(target[axis] - normals[plan['face']][axis] for axis in range(3))
    needed = {target, support}
    if plan.get('content_probe'):
        needed.update(tuple(target[axis] + normal[axis] for axis in range(3))
                      for normal in normals)
    if plan['name'] == 'minecraft:bed':
        needed.update((target[0] + dx, target[1], target[2] + dz)
                      for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        needed.update((pos[0], pos[1] - 1, pos[2]) for pos in tuple(needed))
    assert not needed.intersection(reserved), ('Overlapping native fixtures', target)
    for pos in needed:
        before = info.GetBlockNew(pos, dimension)
        assert before and before.get('name') == 'minecraft:air', (pos, before)
    reserved.update(needed)
    row = dict(plan, pos=target, support=support)
    rows.append(row)
sys._p0_entity_appearances = {'schema': 1, 'player': player, 'dimension': dimension,
                             'slot': slot, 'rotation': saved_rotation,
                             'reserved': sorted(reserved), 'rows': rows,
                             'game_version': block_registry.source_version(),
                             'palette_sha256': block_registry.fingerprint(),
                             'placement': 'native PlayerUseItemToPos; bed colour uses SetBedColor'}


def spawn(row):
    items.SetInvItemNum(slot, 0)
    row['spawn_return'] = items.SpawnItemToPlayerInv(
        {'itemName': row.get('placement_item', row['name']), 'auxValue': row.get('aux', 0), 'count': 1,
         'userData': row.get('userData', {})}, player, slot)
    row['temporary_item'] = items.GetPlayerItem(item_type, slot, True)
    assert row['temporary_item'] and row['temporary_item'].get('count', 0) >= 1, row


try:
    for row in rows:
        supports = [tuple(row['support'])]
        if row['name'] == 'minecraft:bed':
            supports = [(row['pos'][0] + dx, row['pos'][1] - 1, row['pos'][2] + dz)
                        for dx, dz in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))]
        for pos in supports:
            assert info.SetBlockNew(pos, {'name': 'minecraft:stone', 'aux': 0},
                                    0, dimension, True, False)
        assert rotation.SetRot((0., row['yaw']))
        row['player_rotation'] = rotation.GetRot()
        spawn(row)
        row['placed'] = info.PlayerUseItemToPos(tuple(row['support']), item_type, slot, row['face'])
        row['block'] = info.GetBlockNew(tuple(row['pos']), dimension)
        expected = row.get('expected_block',
                           'minecraft:standing_banner' if row['name'] == 'minecraft:banner' else row['name'])
        assert row['placed'] and row['block']['name'] == expected, row
        row['cells'] = [row['pos']]
        if row['name'] == 'minecraft:bed':
            relationship = block_groups.group_partner((expected, row['block']['aux']))
            assert relationship is not None, row
            offset, unused_reciprocal = relationship
            partner = tuple(row['pos'][axis] + offset[axis] for axis in range(3))
            assert partner in reserved, row
            row['cells'].append(partner)
            row['color_set'] = info.SetBedColor(tuple(row['pos']), row['color'], dimension)
            assert row['color_set'] and info.GetBedColor(partner, dimension) == row['color'], row
        row['entity_nbt'] = info.GetBlockEntityData(dimension, tuple(row['pos']))
        row['cell_nbt'] = [{'pos': pos, 'nbt': info.GetBlockEntityData(dimension, tuple(pos))}
                           for pos in row['cells']]
        root = root_payload(row['entity_nbt'])
        row['observed_id'] = scalar(root, 'id')
        row['observed_rotation'] = scalar(root, 'Rotation')
        row['observed_color'] = scalar(root, 'color')
        row['observed_type'] = scalar(root, 'Type')
finally:
    prior_error = sys.exc_info()[0]
    cleanup_errors = []
    try:
        items.SetInvItemNum(slot, 0)
        remaining = items.GetPlayerItem(item_type, slot, True)
        if remaining and remaining.get('count'):
            cleanup_errors.append('Temporary inventory item was not cleared')
    except Exception as error:
        cleanup_errors.append('Inventory restore: ' + str(error))
    try:
        if not rotation.SetRot(saved_rotation):
            cleanup_errors.append('Player rotation did not restore')
    except Exception as error:
        cleanup_errors.append('Rotation restore: ' + str(error))
    sys._p0_entity_appearances['setup_cleanup_errors'] = cleanup_errors
    if cleanup_errors and prior_error is None:
        raise AssertionError(cleanup_errors)
_result = json.dumps(sys._p0_entity_appearances)
