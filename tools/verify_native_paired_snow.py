"""Verify native snow over complete tall-plant fixtures in protected empty cells."""
import json
import math
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry, block_groups

NAMES = ('short_grass', 'tall_grass', 'large_fern', 'lilac', 'sunflower',
         'rose_bush', 'peony', 'pitcher_plant', 'pitcher_crop', 'tall_dry_grass')
AIR = {'name': 'minecraft:air', 'aux': 0}
try:
    text_types = (str, unicode)
except NameError:
    text_types = (str,)


def native_tree(value):
    if isinstance(value, text_types):
        return value.encode('utf8')
    if isinstance(value, dict):
        return dict((native_tree(key), native_tree(item)) for key, item in value.items())
    return value


factory = api.GetEngineCompFactory()
player = api.GetPlayerList()[0]
dimension = factory.CreateDimension(player).GetEntityDimensionId()
info = factory.CreateBlockInfo(api.GetLevelId())
blockstate = factory.CreateBlockState(api.GetLevelId())
blocks = factory.CreateBlock(api.GetLevelId())
foot = factory.CreatePos(player).GetFootPos()
base = (int(math.floor(foot[0])) + 24, int(math.floor(foot[1])) + 12,
        int(math.floor(foot[2])) - 5)
upper = (base[0], base[1] + 1, base[2])
support = (base[0], base[1] - 1, base[2])
for pos in (support, base, upper):
    value = info.GetBlockNew(pos, dimension)
    if not value or value.get('name') != 'minecraft:air':
        raise ValueError('Paired snow verification requires three empty protected cells')


def clear():
    for pos in (upper, base, support):
        info.SetLiquidBlock(pos, AIR, dimension)
        info.SetBlockNew(pos, AIR, 0, dimension, True, False)


def read():
    result = []
    for pos in (base, upper):
        palette = blocks.GetBlockPaletteBetweenPos(dimension, pos, pos, False)
        data = palette.SerializeBlockPalette() if palette is not None else None
        layers = {}
        if data is not None:
            for key in ('common', 'extra'):
                layers[key] = [[value[0], value[1], indices]
                               for value, indices in data.get(key, {}).items()]
        result.append({'pos': pos, 'front': info.GetBlockNew(pos, dimension),
                       'states': blockstate.GetBlockStates(pos, dimension),
                       'layers': layers})
    return result


rows = []
try:
    for short_name in NAMES:
        name = 'minecraft:' + short_name
        aux = block_registry.DEFAULT_AUX[name]
        if short_name == 'pitcher_crop':
            aux = block_registry.from_states(name, {'growth': 7, 'upper_block_bit': False})[1]
        value = (name, aux)
        relationship = block_groups.group_partner(value)
        pairs = [value]
        if relationship is not None:
            offset, partner = relationship
            if offset != (0, 1, 0):
                raise ValueError('Tall fixture is not a supported lower half: ' + name)
            pairs.append(partner)
        clear()
        support_name = 'minecraft:farmland' if short_name == 'pitcher_crop' else 'minecraft:dirt'
        if not info.SetBlockNew(support, {'name': support_name, 'aux': 0},
                                0, dimension, True, False):
            raise ValueError('Could not place paired snow support')
        common, records = {}, {}
        # Each pair has different states but the same native name, so preserve
        # each explicit aux key rather than collapsing both halves to key 0.
        for index, material in enumerate(pairs):
            key = (material[0].encode('utf8'), material[1])
            common[key] = [index]
            records[key] = native_tree(block_registry.states(material))
        data = {'volume': (1, 1, len(pairs)), 'common': common, 'states': records,
                'extra': {}, 'extraStates': {}, 'actor': {},
                'void': False, 'eliminateAir': False}
        palette = blocks.GetBlankBlockPalette()
        if palette is None or not palette.DeserializeBlockPalette(data):
            raise ValueError('Could not deserialize complete tall-plant fixture')
        if not blocks.SetBlockByBlockPalette(palette, dimension, base, 0, 0):
            raise ValueError('Could not place complete tall-plant fixture')
        dry = read()
        verified = all(row['front'].get('name') == material[0] and
                       row['states'] == block_registry.states(material)
                       for row, material in zip(dry, pairs))
        result = bool(info.SetSnowBlock(base, dimension, 1)) if verified else None
        rows.append({'name': name, 'aux': aux, 'paired': len(pairs) == 2,
                     'dry_verified': verified, 'set_snow': result,
                     'dry': dry, 'snowy': read()})
finally:
    clear()

_result = json.dumps({'schema': 1, 'game_version': block_registry.source_version(),
                      'palette_sha256': block_registry.fingerprint(),
                      'method': 'complete supported tall-plant palette then SetSnowBlock bottom',
                      'rows': rows}, sort_keys=True)
