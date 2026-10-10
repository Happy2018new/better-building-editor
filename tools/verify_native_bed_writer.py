"""Assert production bed writes, layers and typed entity color in a disposable native area."""
import json
import math
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
from modern_projection.projection import block_registry, block_groups
from modern_projection.projection.cell import make_cell
from modern_projection.projection.debug_entity_defaults import nbt as default_nbt, evidence
from modern_projection.projection.nbt_spatial import root_payload, scalar
from modern_projection.projection.visible_actor import compose_actor

factory = api.GetEngineCompFactory()
player = api.GetPlayerList()[0]
dimension = factory.CreateDimension(player).GetEntityDimensionId()
info = factory.CreateBlockInfo(player)
blockstate = factory.CreateBlockState(api.GetLevelId())
foot = factory.CreatePos(player).GetFootPos()
target = (int(math.floor(foot[0])) + 14, int(math.floor(foot[1])) + 16,
          int(math.floor(foot[2])) - 7)
x, y, z = target
cells = ((x, y, z), (x - 1, y, z), (x + 1, y, z), (x, y, z - 1), (x, y, z + 1))
supports = tuple((pos[0], pos[1] - 1, pos[2]) for pos in cells)
AIR = {'name': 'minecraft:air', 'aux': 0}
WATER = ('minecraft:water', 0)
for pos in cells + supports:
    value = info.GetBlockNew(pos, dimension)
    if not value or value.get('name') != 'minecraft:air':
        raise ValueError('Native production bed verification requires ten empty cells')


def clear():
    # Removing one half can promote the reciprocal half's water after it
    # was cleared; a second pass removes that native paired side effect.
    for unused in range(2):
        for pos in cells:
            info.SetLiquidBlock(pos, AIR, dimension)
            info.SetBlockNew(pos, AIR, 0, dimension, True, False)


def payload(pos):
    nbt = default_nbt('minecraft:bed', (0, 0, 0))
    if nbt is None:
        raise ValueError('Observed native Bed fixture is unavailable')
    root = root_payload(nbt)
    for axis, coord in zip(('x', 'y', 'z'), pos):
        root[axis] = {'__type__': 3, '__value__': coord}
    root['color'] = {'__type__': 1, '__value__': 7}
    return compose_actor({}, nbt)


rows = []
try:
    for pos in supports:
        info.SetBlockNew(pos, {'name': 'minecraft:stone', 'aux': 0},
                         0, dimension, True, False)
    for aux in block_registry.aux_values('minecraft:bed'):
        value = ('minecraft:bed', aux)
        offset, other = block_groups.group_partner(value)
        partner = tuple(target[i] + offset[i] for i in range(3))
        pair = [(target, value), (partner, other)]
        for head_first in (True, False):
            clear()
            ordered = sorted(pair, key=lambda row:
                             block_registry.states(row[1])['head_piece_bit'] != head_first)
            adapter = WorldAdapter(player)
            # Any production target read during write is a regression; only
            # this test's separate components inspect the native result.
            def unexpected_read(*args):
                raise AssertionError('Production write attempted a target read')
            adapter.info.GetBlockNew = unexpected_read
            adapter.info.GetLiquidBlock = unexpected_read
            returns = []
            for pos, material in ordered:
                returns.append(adapter.write(pos, make_cell(material, WATER, payload(pos))))
            actual = []
            for pos, material in pair:
                record = {'pos': pos, 'front': info.GetBlockNew(pos, dimension),
                          'states': blockstate.GetBlockStates(pos, dimension),
                          'liquid': info.GetLiquidBlock(pos, dimension)}
                nbt = info.GetBlockEntityData(dimension, pos)
                record['color'] = scalar(root_payload(nbt), 'color') if nbt else None
                record['id'] = scalar(root_payload(nbt), 'id') if nbt else None
                record['coordinates'] = [scalar(root_payload(nbt), axis)
                                         for axis in ('x', 'y', 'z')] if nbt else None
                if (record['front'].get('name') != material[0] or
                        record['states'] != block_registry.states(material) or
                        not record['liquid'] or record['liquid'].get('name') != WATER[0] or
                        record['color'] != 7 or record['id'] != 'Bed' or
                        tuple(record['coordinates']) != pos):
                    raise AssertionError('Native bed write mismatch aux=%d head_first=%s: %r' %
                                         (aux, head_first, record))
                actual.append(record)
            if returns != [True, True]:
                raise AssertionError('Native bed write reported a false failure: %r' % returns)
            rows.append({'aux': aux, 'head_first': head_first, 'returns': returns, 'actual': actual})
finally:
    clear()
    for pos in supports:
        info.SetBlockNew(pos, AIR, 0, dimension, True, False)

_result = json.dumps({'passed': len(rows) == 32, 'checks': len(rows),
                      'schema': 1, 'game_version': block_registry.source_version(),
                      'palette_sha256': block_registry.fingerprint(),
                      'entity_evidence': evidence(), 'rows': rows}, sort_keys=True)
