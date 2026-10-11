# -*- coding: utf-8 -*-
"""Deterministic built-in documents for editor and projection acceptance."""
from __future__ import unicode_literals
from . import block_registry as registry
from .cell import AIR, make_cell
from .model import Document
from .block_groups import group_partner, hydrate_chest_actor
from .visible_actor import compose_actor
from .nbt_spatial import root_payload, scalar
from .debug_sign_blueprints import METADATA as SIGN_METADATA, VISUAL_CASE as SIGN_VISUAL_CASE
from .debug_water_blueprints import METADATA as WATER_METADATA, VISUAL_CASE as WATER_VISUAL_CASE
from .debug_pot_blueprints import METADATA as POT_METADATA, VISUAL_CASE as POT_VISUAL_CASE
from .debug_dripstone_blueprints import METADATA as DRIPSTONE_METADATA, VISUAL_CASE as DRIPSTONE_VISUAL_CASE
from .debug_snow_blueprints import METADATA as SNOW_METADATA, VISUAL_CASE as SNOW_VISUAL_CASE
from .debug_neighborhood_blueprints import METADATA as NEIGHBOR_METADATA, VISUAL_CASE as NEIGHBOR_VISUAL_CASE
from .debug_connection_blueprints import METADATA as CONNECTION_METADATA, VISUAL_CASE as CONNECTION_VISUAL_CASE
from .debug_liquid_blueprints import METADATA as LIQUID_METADATA, VISUAL_CASE as LIQUID_VISUAL_CASE

SCHEMA_VERSION = 1
CATEGORIES = (('layers', '双层'), ('groups', '多格'), ('connections', '连接'),
              ('transforms', '变换'), ('entities', '方块实体'), ('registry', '方块表'))
BLUEPRINTS = (
    ('test.layers.water', 'layers', '含水方块', (32, 8, 24), 'minecraft:oak_fence'),
    LIQUID_METADATA,
    SNOW_METADATA,
    ('test.groups.parts', 'groups', '门、床与高植物', (32, 8, 24), 'minecraft:wooden_door'),
    ('test.connections.context', 'connections', '楼梯、铁轨、墙与双箱', (32, 12, 32), 'minecraft:rail'),
    ('test.transforms.directions', 'transforms', '方向与镜像', (32, 12, 32), 'minecraft:oak_stairs'),
    ('test.entities.classic', 'entities', '方块实体 · 基础', (40, 10, 36), 'minecraft:chest'),
    ('test.entities.mechanisms', 'entities', '方块实体 · 机关', (32, 10, 28), 'minecraft:structure_block'),
    ('test.entities.recent', 'entities', '方块实体 · 新版本', (32, 10, 28), 'minecraft:trial_spawner'),
    ('test.entities.appearances', 'entities', '方块实体 · 非默认外观', (40, 12, 44), 'minecraft:skeleton_skull'),
    ('test.registry.vanilla', 'registry', '原版方块全览', (64, 64, 64), 'minecraft:stone'),
    SIGN_METADATA,
    WATER_METADATA,
    POT_METADATA,
    DRIPSTONE_METADATA,
    CONNECTION_METADATA,
    NEIGHBOR_METADATA,
)
VISUAL_CASES = {
    'water_behaviors': WATER_VISUAL_CASE,
    'pure_liquids': LIQUID_VISUAL_CASE,
    'sign_styles': SIGN_VISUAL_CASE,
    'pot_artwork': POT_VISUAL_CASE,
    'dripstone_neighbors': DRIPSTONE_VISUAL_CASE,
    'static_neighbors': CONNECTION_VISUAL_CASE,
    'extended_neighbors': NEIGHBOR_VISUAL_CASE,
    'neighbor_context': {
        'schema': 1, 'fixture': 'test.connections.context',
        'cells': {
            'stairs': ((3, 1, 23), (4, 1, 23)),
            'rail': ((3, 1, 3), (4, 1, 3)),
            'wall': ((7, 1, 17), (7, 1, 16)),
            'fence': ((17, 1, 17), (18, 1, 17)),
            'pane': ((17, 1, 20), (17, 1, 21)),
            'iron_bars': ((22, 1, 20), (22, 1, 21)),
        },
        'cross_chunk_cells': {
            'stairs': ((15, 1, 23), (16, 1, 23)),
            'rail': ((15, 1, 3), (16, 1, 3)),
            'wall': ((7, 1, 16), (7, 1, 15)),
            'fence': ((15, 1, 17), (16, 1, 17)),
            'pane': ((17, 1, 15), (17, 1, 16)),
            'iron_bars': ((22, 1, 15), (22, 1, 16)),
        },
        'camera': {'distance': 6., 'side_height': -2.4},
        'projection_height': 24,
    },
    'snow_plant_visibility': SNOW_VISUAL_CASE,
    'entity_appearances': {
        'schema': 2, 'fixture': 'test.entities.appearances',
        'size': (40, 12, 44),
        'camera': {'editor': (35., 25., 4.), 'world_offset': (-3.5, -3., -5.)},
        'isolated_size': (8, 8, 8), 'focus': (3, 3, 3),
        'projection_height': 20,
        'isolated_camera': {'editor': (35., 25., 3.), 'world_offset': (-2., -.8, -3.)},
        'acceptance_cases': ('skull_floor_yaw_0', 'skull_floor_yaw_45',
                             'skull_floor_yaw_90', 'skull_wall_face2',
                             'skull_wall_face5', 'dragon_floor_yaw45',
                             'bed_silver', 'bed_light_blue',
                             'wither_skeleton_skull_floor_yaw45', 'wither_skeleton_skull_wall_face2',
                             'zombie_head_floor_yaw45', 'zombie_head_wall_face2',
                             'creeper_head_floor_yaw45', 'creeper_head_wall_face2'),
    },
    'chest_top': {
        'schema': 1, 'isolated_size': (4, 3, 4), 'target_height_offset': 8,
        'camera': {'editor': (0., 90., 1.), 'world_offset': (0., 6., .15)},
        'registration': {'material': 'minecraft:stone', 'focus': (1, 1, 1),
                         'scope': 'Independent unit cube before chest captures'},
        'native_background': {'material': 'minecraft:quartz_block', 'offset_y': -4, 'radius': 3},
        'cases': (
            {'id': 'normal_single_south', 'name': 'minecraft:chest',
             'direction': 'south', 'paired': False, 'fixture': 'test.entities.classic',
             'cells': ((9, 1, 3),)},
            {'id': 'normal_double_north', 'name': 'minecraft:chest',
             'direction': 'north', 'paired': True, 'fixture': 'test.connections.context',
             'cells': ((26, 1, 5), (27, 1, 5))},
            {'id': 'copper_double_north', 'name': 'minecraft:copper_chest',
             'direction': 'north', 'paired': True, 'fixture': 'test.connections.context',
             'cells': ((26, 1, 10), (27, 1, 10))},
        ),
    },
    'shulker_orientations': {
        'schema': 2, 'fixture': 'test.transforms.directions',
        'cells': tuple((3 + index * 5, 3, 28) for index in range(6)),
        'size': (8, 8, 8), 'focus': (3, 3, 3),
        'projection_height': 20,
        'camera': {'editor': (35., 25., 2.8), 'world_offset': (-3.5, 3., -5.)},
    },
}


def entries(category=None):
    return tuple(row for row in BLUEPRINTS if category is None or row[1] == category)


def material(name, properties=None):
    """Resolve complete legal native states; never manufacture an aux value."""
    name = name if ':' in name else 'minecraft:' + name
    if name not in registry.DEFAULT_AUX:
        raise ValueError('当前方块表没有测试材质：%s' % name)
    value = (name, registry.DEFAULT_AUX[name])
    if not properties:
        return value
    wanted = registry.states(value)
    wanted.update(properties)
    result = registry.from_states(name, wanted)
    if result is None:
        raise ValueError('当前方块表没有测试状态：%s %r' % (name, properties))
    return result


def tag(value, kind):
    return {'__type__': kind, '__value__': value}


class Fixture(object):
    def __init__(self, metadata):
        self.document = Document(metadata[3], name=metadata[2])

    def put(self, pos, value, back=AIR, entity=None, render=None, fields=None):
        if not self.document.contains(pos):
            raise ValueError('测试场景超出蓝图范围')
        actor = None
        from .debug_entity_defaults import nbt as native_nbt
        nbt = native_nbt(value[0], pos)
        if entity is not None:
            if nbt is None:
                raise ValueError('Native default entity payload is unavailable: ' + value[0])
            if scalar(root_payload(nbt), 'id') != entity:
                raise ValueError('Native fixture entity association needs updating: ' + value[0])
            root_payload(nbt).update(fields or {})
        if nbt is not None:
            actor = compose_actor({} if render is None else render, nbt)
        self.document.blocks[pos] = make_cell(value, back, actor)

    def group(self, pos, value, back=AIR, entity=None):
        self.put(pos, value, back, entity)
        relationship = group_partner(value)
        if relationship is not None:
            offset, reciprocal = relationship
            partner = tuple(pos[index] + offset[index] for index in range(3))
            self.put(partner, reciprocal, back, entity)

    def floor(self):
        size = self.document.size
        light, dark = material('light_gray_concrete'), material('white_concrete')
        for x in range(size[0]):
            for z in range(size[2]):
                self.put((x, 0, z), light if x % 4 == 0 or z % 4 == 0 else dark)

    def plinth(self, pos, color='cyan_concrete'):
        for x in range(pos[0] - 1, pos[0] + 2):
            for z in range(pos[2] - 1, pos[2] + 2):
                self.put((x, pos[1] - 1, z), material(color))

    def finish(self, reconnect=False):
        if reconnect:
            from .block_neighbors import reconcile_steps
            before = Document(self.document.size)
            for unused in reconcile_steps(before, self.document.blocks,
                                           self.document.blocks.__setitem__, set()):
                pass
        return self.document


def _water(fixture):
    fixture.floor()
    water = material('water')
    names = ('oak_fence', 'iron_bars', 'glass_pane', 'oak_stairs', 'oak_slab',
             'trapdoor', 'chest', 'mangrove_roots', 'sea_pickle',
             'standing_sign', 'ladder', 'rail')
    for index, name in enumerate(names):
        x, z = 3 + (index % 6) * 5, 3 + (index // 6) * 10
        value = material(name)
        fixture.plinth((x, 1, z))
        fixture.put((x, 1, z), value)
        fixture.put((x, 1, z + 3), value, water)
        fixture.put((x, 1, z + 6), AIR, water)
    return fixture.finish()


def _groups(fixture):
    fixture.floor()
    names = ('wooden_door', 'iron_door', 'mangrove_door', 'bed', 'tall_grass',
             'large_fern', 'sunflower', 'rose_bush', 'peony', 'lilac')
    for index, name in enumerate(names):
        pos = (3 + (index % 5) * 6, 1, 3 + (index // 5) * 8)
        fixture.plinth(pos)
        fixture.group(pos, material(name))
    for x, direction in ((3, 0), (9, 1), (15, 2), (21, 3)):
        fixture.group((x, 1, 20), material('bed', {'direction': direction}), entity='Bed')
    return fixture.finish()


def _chest_pair(fixture, name, left, right):
    value = material(name, {'minecraft:cardinal_direction': 'north'})
    for pos, partner, lead in ((left, right, 1), (right, left, 0)):
        fixture.put(pos, value, entity='Chest', fields={
            'pairx': tag(partner[0], 3), 'pairz': tag(partner[2], 3),
            'pairlead': tag(lead, 1), 'renderlead': tag(1 - lead, 1)})
        fixture.document.blocks[pos] = hydrate_chest_actor(fixture.document.get(pos), pos)


def _connections(fixture):
    fixture.floor()
    rail = material('rail')
    for x in range(3, 12):
        for z in (3, 11):
            fixture.put((x, 1, z), rail)
    for z in range(4, 11):
        for x in (3, 11):
            fixture.put((x, 1, z), rail)
    for z, y in ((3, 1), (4, 1), (5, 2), (6, 2), (7, 3), (8, 3)):
        fixture.put((17, y - 1, z), material('stone'))
        fixture.put((17, y, z), rail)
    for x in range(3, 12):
        fixture.put((x, 1, 17), material('cobblestone_wall'))
    fixture.put((7, 1, 16), material('cobblestone_wall'))
    fixture.put((7, 1, 18), material('cobblestone_wall'))
    fixture.put((11, 2, 17), material('stone'))
    for x in range(17, 27):
        fixture.put((x, 1, 17), material('oak_fence'))
    fixture.put((21, 1, 17), material('fence_gate'))
    for z in range(19, 26):
        fixture.put((17, 1, z), material('glass_pane'))
        fixture.put((22, 1, z), material('iron_bars'))
    stairs = ((3, 1, 23, 0), (4, 1, 23, 3), (8, 1, 23, 0), (9, 1, 23, 2),
              (3, 1, 28, 0), (2, 1, 28, 3), (8, 1, 28, 0), (7, 1, 28, 2))
    for x, y, z, direction in stairs:
        fixture.put((x, y, z), material('oak_stairs', {'weirdo_direction': direction}))
        fixture.put((x + 12, y, z), material('oak_stairs', {
            'weirdo_direction': direction, 'upside_down_bit': True}))
    _chest_pair(fixture, 'chest', (26, 1, 5), (27, 1, 5))
    if 'minecraft:copper_chest' in registry.BLOCKS:
        _chest_pair(fixture, 'copper_chest', (26, 1, 10), (27, 1, 10))
    return fixture.finish(reconnect=True)


def _directions(fixture):
    fixture.floor()
    rows = (('oak_stairs', 'weirdo_direction', range(4)),
            ('oak_log', 'pillar_axis', ('x', 'y', 'z')),
            ('dispenser', 'facing_direction', range(6)),
            ('lever', 'lever_direction', ('north', 'south', 'east', 'west')),
            ('rail', 'rail_direction', range(10)))
    for row, (name, key, values) in enumerate(rows):
        for index, value in enumerate(values):
            fixture.put((2 + index * 3, 1, 2 + row * 5), material(name, {key: value}))
    for facing, pos in enumerate(VISUAL_CASES['shulker_orientations']['cells']):
        fixture.put(pos, material('purple_shulker_box'),
                    entity='ShulkerBox', render={'facingDirection': facing},
                    fields={'facing': tag(facing, 1)})
    for index in range(4):
        fixture.group((3 + index * 6, 1, 24), material('wooden_door', {
            'minecraft:cardinal_direction': ('north', 'east', 'south', 'west')[index],
            'door_hinge_bit': bool(index % 2)}))
    return fixture.finish()


def _vanilla(fixture):
    values = registry.catalogue_values()
    values = [value for value in values if value[0].startswith('minecraft:') and value != AIR]
    for index, value in enumerate(values):
        column, level = index % 196, index // 196
        pos = (3 + (column % 14) * 4, 1 + level * 8, 3 + (column // 14) * 4)
        fixture.plinth(pos, 'light_gray_concrete' if level % 2 else 'cyan_concrete')
        fixture.group(pos, value)
    return fixture.finish()


def build(identity):
    metadata = next((row for row in BLUEPRINTS if row[0] == identity), None)
    if metadata is None:
        raise ValueError('找不到这份测试蓝图')
    fixture = Fixture(metadata)
    if identity == LIQUID_METADATA[0]:
        from .debug_liquid_blueprints import populate
        return populate(fixture)
    if identity == WATER_METADATA[0]:
        from .debug_water_blueprints import populate
        return populate(fixture)
    if identity == DRIPSTONE_METADATA[0]:
        from .debug_dripstone_blueprints import populate
        return populate(fixture)
    if identity == SNOW_METADATA[0]:
        from .debug_snow_blueprints import populate
        return populate(fixture)
    if identity == CONNECTION_METADATA[0]:
        from .debug_connection_blueprints import populate
        return populate(fixture)
    if identity == NEIGHBOR_METADATA[0]:
        from .debug_neighborhood_blueprints import populate
        return populate(fixture)
    builders = {'test.layers.water': _water,
                'test.groups.parts': _groups, 'test.connections.context': _connections,
                'test.transforms.directions': _directions, 'test.registry.vanilla': _vanilla}
    if metadata[1] == 'entities':
        if identity == POT_METADATA[0]:
            from .debug_pot_blueprints import populate
            return populate(fixture)
        if identity == SIGN_METADATA[0]:
            from .debug_sign_blueprints import populate
            return populate(fixture)
        if identity == 'test.entities.appearances':
            from .debug_appearance_blueprints import populate
            return populate(fixture)
        from .debug_entity_blueprints import populate
        return populate(fixture, identity)
    return builders[identity](fixture)


def open_blueprint(session, identity):
    if session.busy or session.io_job is not None or session.edit_job is not None:
        raise ValueError('请等待当前操作完成')
    document = build(identity)
    session._loaded(document)
    session.progress = None
    session.editor.message = '已载入测试蓝图'
