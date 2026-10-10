"""Compare complete native bed placement and explicit two-half state repair."""
import json
import math
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry, block_groups

factory = api.GetEngineCompFactory()
player = api.GetPlayerList()[0]
dimension = factory.CreateDimension(player).GetEntityDimensionId()
info = factory.CreateBlockInfo(player)
blockstate = factory.CreateBlockState(api.GetLevelId())
blocks = factory.CreateBlock(api.GetLevelId())
foot = factory.CreatePos(player).GetFootPos()
target = (int(math.floor(foot[0])) + 24, int(math.floor(foot[1])) + 12,
          int(math.floor(foot[2])) + 5)
x, y, z = target
cells = ((x, y, z), (x - 1, y, z), (x + 1, y, z), (x, y, z - 1), (x, y, z + 1))
supports = tuple((pos[0], pos[1] - 1, pos[2]) for pos in cells)
AIR = {'name': 'minecraft:air', 'aux': 0}
for pos in cells + supports:
    value = info.GetBlockNew(pos, dimension)
    if not value or value.get('name') != 'minecraft:air':
        raise ValueError('Native bed verification requires ten empty protected cells')


def clear():
    for pos in cells:
        info.SetLiquidBlock(pos, AIR, dimension)
        info.SetBlockNew(pos, AIR, 0, dimension, True, False)


def read(pos):
    return {'front': info.GetBlockNew(pos, dimension),
            'states': blockstate.GetBlockStates(pos, dimension)}


rows = []
try:
    for pos in supports:
        info.SetBlockNew(pos, {'name': 'minecraft:stone', 'aux': 0},
                         0, dimension, True, False)
    for aux in block_registry.aux_values('minecraft:bed'):
        value = ('minecraft:bed', aux)
        offset, other = block_groups.group_partner(value)
        for sign in (1, -1):
            clear()
            partner = tuple(target[i] + sign * offset[i] for i in range(3))
            origin = tuple(min(target[i], partner[i]) for i in range(3))
            size = tuple(abs(offset[i]) + 1 for i in range(3))
            common, records = {}, {}
            for pos, material in ((target, value), (partner, other)):
                local = tuple(pos[i] - origin[i] for i in range(3))
                index = local[1] * size[0] * size[2] + local[0] * size[2] + local[2]
                key = (material[0].encode('utf8'), material[1])
                common[key] = [index]
                records[key] = dict((name.encode('utf8'), item)
                                    for name, item in block_registry.states(material).items())
            palette = blocks.GetBlankBlockPalette()
            data = {'volume': (size[2], size[0], size[1]), 'common': common,
                    'states': records, 'extra': {}, 'extraStates': {},
                    'actor': {}, 'void': False, 'eliminateAir': False}
            if palette is None or not palette.DeserializeBlockPalette(data):
                raise ValueError('Could not deserialize exact native bed pair')
            placed = blocks.SetBlockByBlockPalette(palette, dimension, origin, 0, 0)
            before = (read(target), read(partner))
            repairs = []
            for pos, material in ((partner, other), (target, value)):
                repairs.append(blockstate.SetBlockStates(pos, block_registry.states(material), dimension))
            after = (read(target), read(partner))
            rows.append({'aux': aux, 'sign': sign, 'offset': offset, 'placed': placed,
                         'expected': (block_registry.states(value), block_registry.states(other)),
                         'before': before, 'repair_returns': repairs, 'after': after})
finally:
    clear()
    for pos in supports:
        info.SetBlockNew(pos, AIR, 0, dimension, True, False)

_result = json.dumps({'schema': 1, 'game_version': block_registry.source_version(),
                      'palette_sha256': block_registry.fingerprint(), 'rows': rows}, sort_keys=True)
