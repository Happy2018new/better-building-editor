# -*- coding: utf-8 -*-
"""Public banner patterns and wall/standing supports from native observations."""
import base64
import json
import zlib
from . import banner_fixture_data as source
from .cell import make_cell
from .nbt_spatial import rebase
from .visible_actor import compose_actor

METADATA = ('test.entities.banners', 'entities', u'旗帜 · 原生图案与遮挡',
            (16, 4, 16), 'minecraft:standing_banner')
POSITIONS = ((1, 1, 1), (6, 1, 1), (11, 1, 1),
             (1, 2, 7), (6, 2, 7), (11, 2, 7))
VISUAL_CASE = {'schema': 1, 'fixture': METADATA[0], 'positions': POSITIONS,
               'pattern_counts': (0, 3, 6, 0, 3, 6),
               'camera': {'editor': (35., 25., 2.)},
               'source_engine': source.ENGINE_VERSION}


def observations():
    if source.SCHEMA_VERSION != 1 or source.ENGINE_VERSION != '3.10.0.420447':
        raise ValueError('Banner observations need version-specific regeneration')
    rows = json.loads(zlib.decompress(base64.b64decode(source.ROWS)))
    if len(rows) != len(POSITIONS):
        raise ValueError('Banner gallery observation count changed')
    return rows


def populate(fixture):
    from .debug_blueprints import material
    for row, pos in zip(observations(), POSITIONS):
        delta = tuple(pos[axis] - row['pos'][axis] for axis in range(3))
        actor = compose_actor(row['actor'], rebase(row['nbt'], delta))
        fixture.document.blocks[pos] = make_cell(material(row['name'], row['states']), nbt=actor)
        support = ((pos[0], pos[1], pos[2] + 1) if row['name'].endswith('wall_banner')
                   else (pos[0], 0, pos[2]))
        fixture.document.blocks[support] = material('stone')
    return fixture.finish()
