"""Export all bed water states using native head-first paired placement."""
import json
import math
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry, block_groups

factory = api.GetEngineCompFactory()
player = api.GetPlayerList()[0]
dimension = factory.CreateDimension(player).GetEntityDimensionId()
info = factory.CreateBlockInfo(player)
blockstate = factory.CreateBlockState(api.GetLevelId())
foot = factory.CreatePos(player).GetFootPos()
target = (int(math.floor(foot[0])) + 24, int(math.floor(foot[1])) + 12,
          int(math.floor(foot[2])) + 5)
x, y, z = target
cells = ((x, y, z), (x - 1, y, z), (x + 1, y, z), (x, y, z - 1), (x, y, z + 1))
supports = tuple((pos[0], pos[1] - 1, pos[2]) for pos in cells)
AIR = {'name': 'minecraft:air', 'aux': 0}
WATER = {'name': 'minecraft:water', 'aux': 0}
for pos in cells + supports:
    value = info.GetBlockNew(pos, dimension)
    if not value or value.get('name') != 'minecraft:air':
        raise ValueError('Native paired bed water verification requires ten empty cells')


def clear():
    for unused in range(2):
        for pos in cells:
            info.SetLiquidBlock(pos, AIR, dimension)
            info.SetBlockNew(pos, AIR, 0, dimension, True, False)


def read(pos):
    return {'front': info.GetBlockNew(pos, dimension),
            'states': blockstate.GetBlockStates(pos, dimension),
            'liquid': info.GetLiquidBlock(pos, dimension)}


rows, accepted = {}, []
verified = 0
try:
    for pos in supports:
        info.SetBlockNew(pos, {'name': 'minecraft:stone', 'aux': 0},
                         0, dimension, True, False)
    for aux in block_registry.aux_values('minecraft:bed'):
        value = ('minecraft:bed', aux)
        offset, other = block_groups.group_partner(value)
        partner = tuple(target[i] + offset[i] for i in range(3))
        pair = [(target, value), (partner, other)]
        pair.sort(key=lambda row: not block_registry.states(row[1])['head_piece_bit'])
        result = {}
        for wet in (False, True):
            clear()
            if wet:
                info.SetBlockNew(target, WATER, 0, dimension, True, False)
            returns = []
            for pos, material in pair:
                native_aux = blockstate.GetBlockAuxValueFromStates(
                    material[0].encode('utf8'), block_registry.states(material))
                returns.append(info.SetBlockNew(pos, {
                    'name': material[0].encode('utf8'), 'aux': native_aux},
                    0, dimension, True, False))
            actual, other_actual = read(target), read(partner)
            matched = all(record['front'].get('name') == material[0] and
                          record['states'] == block_registry.states(material)
                          for record, material in ((actual, value), (other_actual, other)))
            result['wet' if wet else 'dry'] = actual
            result['wet_partner' if wet else 'dry_partner'] = other_actual
            result['wet_returns' if wet else 'dry_returns'] = returns
            if not wet and matched:
                verified += 1
            if wet and matched and actual['liquid'] and actual['liquid'].get('name') == 'minecraft:water':
                accepted.append(aux)
        result['native_aux'] = blockstate.GetBlockAuxValueFromStates(
            value[0].encode('utf8'), block_registry.states(value))
        result['fixture'] = {'support': 'minecraft:stone', 'paired': True, 'head_first': True}
        rows[str(aux)] = result
finally:
    clear()
    for pos in supports:
        info.SetBlockNew(pos, AIR, 0, dimension, True, False)

_result = json.dumps({'schema': 1, 'game_version': block_registry.source_version(),
                      'palette_sha256': block_registry.fingerprint(),
                      'method': 'native head-first exact-aux bed pair before/after over water',
                      'tested_states': len(rows), 'verified_states': verified,
                      'blocks': {'minecraft:bed': accepted},
                      'readback_states': {'minecraft:bed': rows}}, sort_keys=True)
