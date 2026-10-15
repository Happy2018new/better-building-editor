# -*- coding: utf-8 -*-
"""Public configured, empty and unknown spawners from native round-16 samples."""
import base64
import json
import zlib
from . import spawner_marker_data as source
from .cell import make_cell
from .nbt_spatial import rebase
from .visible_actor import compose_actor

METADATA = ('test.entities.spawners', 'entities', u'刷怪笼 · 配置与未知',
            (32, 6, 16), 'minecraft:mob_spawner')
POSITIONS = tuple((3 + index % 4 * 7, 1, 3 + index // 4 * 5) for index in range(8))
CASE_IDS = ('mob_spawner_empty', 'mob_spawner_pig_spawn_egg', 'mob_spawner_zombie_spawn_egg',
            'trial_spawner_empty', 'trial_spawner_pig_spawn_egg', 'trial_spawner_zombie_spawn_egg',
            'mob_spawner_unknown', 'trial_spawner_unknown')
VISUAL_CASE = {'schema': 1, 'fixture': METADATA[0], 'positions': POSITIONS,
               'cases': CASE_IDS, 'source_engine': source.ENGINE_VERSION,
               'isolated_size': (8, 6, 8), 'focus': (3, 2, 3),
               'camera': {'editor': (35., 20., 3.), 'world_offset': (-2., 1.5, -3.)}}


def observations():
    if source.SCHEMA_VERSION != 1 or source.ENGINE_VERSION != '3.10.0.420447':
        raise ValueError('Spawner observations need version-specific regeneration')
    return json.loads(zlib.decompress(base64.b64decode(source.SAMPLE_ROWS)))


def populate(fixture):
    from .debug_blueprints import material
    rows = dict((row['id'], row) for row in observations())
    for identity, position in zip(CASE_IDS, POSITIONS):
        row = rows.get(identity)
        if row is None:
            name = 'mob_spawner' if identity.startswith('mob_') else 'trial_spawner'
            value, actor = material(name), None
        else:
            value = material(row['name'], row['states'])
            delta = tuple(position[axis] - row['pos'][axis] for axis in range(3))
            actor = compose_actor({}, rebase(row['after_delayed'], delta))
        fixture.document.blocks[position] = make_cell(value, nbt=actor)
        fixture.plinth(position, 'cyan_concrete' if row is not None else 'yellow_concrete')
    return fixture.finish()


def source_document(identity):
    """Extract one public gallery cell and its support without changing its NBT."""
    from .cell import rebase as rebase_cell
    from .debug_blueprints import build
    from .model import Document
    if identity not in CASE_IDS:
        raise ValueError('Unknown public spawner case')
    source_document = build(METADATA[0])
    position = POSITIONS[CASE_IDS.index(identity)]
    target = (3, 3, 3)
    delta = tuple(target[axis] - position[axis] for axis in range(3))
    result = Document((8, 8, 8), name=source_document.name, biome=source_document.biome)
    for shift in ((0, 0, 0), (0, -1, 0)):
        original = tuple(position[axis] + shift[axis] for axis in range(3))
        destination = tuple(target[axis] + shift[axis] for axis in range(3))
        result.set_cell(destination, rebase_cell(source_document.get(original), delta))
    return result
