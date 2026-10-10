"""Fixed-coordinate documents for observed nondefault native entity appearances."""
from __future__ import unicode_literals
import base64
import json
import zlib
from . import appearance_defaults_data as source
from .cell import make_cell
from .native_appearance import validate_source
from .nbt_spatial import rebase
from .visible_actor import compose_actor

SCHEMA_VERSION = 1
IDENTITY = 'test.entities.appearances'
CASE_NAMES = (
    'skull_floor_yaw_0', 'skull_floor_yaw_22.5', 'skull_floor_yaw_45',
    'skull_floor_yaw_90', 'skull_floor_yaw_135', 'skull_floor_yaw_180',
    'skull_floor_yaw_225', 'skull_floor_yaw_270', 'skull_wall_face2',
    'skull_wall_face3', 'skull_wall_face4', 'skull_wall_face5',
    'dragon_floor_yaw45', 'bed_silver', 'bed_light_blue',
    'frame_filled', 'glow_frame_filled', 'banner_base1', 'banner_ominous')
CASE_POSITIONS = dict((name, (3 + index % 6 * 6, 1, 3 + index // 6 * 8))
                      for index, name in enumerate(CASE_NAMES))


def observations():
    from . import block_registry as registry
    validate_source()
    if (source.SCHEMA_VERSION != 1 or source.SOURCE_VERSION != registry.source_version() or
            source.PALETTE_SHA256 != registry.fingerprint()):
        raise ValueError('Native appearance fixtures need regeneration for this registry')
    rows = json.loads(zlib.decompress(base64.b64decode(source.ROWS)))
    if tuple(row['case'] for row in rows) != CASE_NAMES:
        raise ValueError('Native appearance case associations need updating')
    return rows


def populate(fixture):
    from .block_groups import group_partner
    from .debug_blueprints import material
    fixture.floor()
    normals = ((0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0))
    for row in observations():
        target = CASE_POSITIONS[row['case']]
        fixture.plinth(target)
        source_pos = row['cell_nbt'][0]['pos']
        first = (row['block']['name'], row['block']['aux'])
        relationship = group_partner(first)
        if row['face'] != 1:
            support = tuple(target[axis] - normals[row['face']][axis] for axis in range(3))
            fixture.put(support, material('stone'))
        for index, cell in enumerate(row['cell_nbt']):
            delta = tuple(target[axis] - source_pos[axis] for axis in range(3))
            pos = tuple(cell['pos'][axis] + delta[axis] for axis in range(3))
            value = first if index == 0 else relationship[1]
            palette_index = index if relationship is not None else 0
            renderer = row['palette'].get('actor', {}).get(value[0], {}).get(str(palette_index))
            actor = compose_actor(renderer, rebase(cell['nbt'], delta))
            if not fixture.document.contains(pos):
                raise ValueError('Native appearance fixture exceeds the document')
            fixture.document.blocks[pos] = make_cell(value, nbt=actor)
    return fixture.finish()
