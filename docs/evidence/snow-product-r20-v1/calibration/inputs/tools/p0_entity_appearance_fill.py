"""Fill native frames after the host has verified client block replication."""
import json
import sys
import mod.server.extraServerApi as api
from modern_projection.projection.nbt_spatial import root_payload, scalar

saved = sys._p0_entity_appearances
factory = api.GetEngineCompFactory()
items, info = factory.CreateItem(saved['player']), factory.CreateBlockInfo(saved['player'])
item_type = api.GetMinecraftEnum().ItemPosType.INVENTORY
try:
    for row in saved['rows']:
        if not row.get('fill_item'):
            continue
        items.SetInvItemNum(saved['slot'], 0)
        row['fill_spawn_return'] = items.SpawnItemToPlayerInv(
            {'itemName': row['fill_item'], 'count': 1, 'auxValue': 0}, saved['player'], saved['slot'])
        temporary = items.GetPlayerItem(item_type, saved['slot'], True)
        assert temporary and temporary.get('count'), row
        row['fill_return'] = info.PlayerUseItemToPos(tuple(row['pos']), item_type, saved['slot'], row['face'])
        row['entity_nbt'] = info.GetBlockEntityData(saved['dimension'], tuple(row['pos']))
        root = root_payload(row['entity_nbt'])
        row['fill_nbt_fields'] = sorted(root)
        row['filled_item'] = root.get('Item', root.get('item'))
        row['observed_item_rotation'] = scalar(root, 'ItemRotation')
        row['fill_observed'] = bool(row['filled_item'])
        row['cell_nbt'] = [{'pos': row['pos'], 'nbt': row['entity_nbt']}]
finally:
    prior_error = sys.exc_info()[0]
    cleanup_errors = []
    try:
        items.SetInvItemNum(saved['slot'], 0)
        remaining = items.GetPlayerItem(item_type, saved['slot'], True)
        if remaining and remaining.get('count'):
            cleanup_errors.append('Temporary frame-fill item was not cleared')
    except Exception as error:
        cleanup_errors.append('Inventory restore: ' + str(error))
    saved['fill_cleanup_errors'] = cleanup_errors
    if cleanup_errors and prior_error is None:
        raise AssertionError(cleanup_errors)
_result = json.dumps(saved)
