# -*- coding: utf-8 -*-
"""Deterministic built-in documents for editor and projection acceptance."""
from __future__ import unicode_literals
from . import block_registry as registry
from .cell import AIR, _covered_snow, make_cell
from .model import Document
from .block_groups import group_partner, hydrate_chest_actor
from .visible_actor import compose_actor

SCHEMA_VERSION = 1
CATEGORIES = (('layers', '双层'), ('groups', '多格'), ('connections', '连接'),
              ('transforms', '变换'), ('entities', '方块实体'), ('registry', '方块表'))
BLUEPRINTS = (
    ('test.layers.water', 'layers', '含水方块', (32, 8, 24), 'minecraft:oak_fence'),
    ('test.layers.snow', 'layers', '含雪方块', (32, 8, 24), 'minecraft:snow_layer'),
    ('test.groups.parts', 'groups', '门、床与高植物', (32, 8, 24), 'minecraft:wooden_door'),
    ('test.connections.context', 'connections', '楼梯、铁轨、墙与双箱', (32, 12, 32), 'minecraft:rail'),
    ('test.transforms.directions', 'transforms', '方向与镜像', (32, 12, 32), 'minecraft:oak_stairs'),
    ('test.entities.classic', 'entities', '方块实体 · 基础', (40, 10, 36), 'minecraft:chest'),
    ('test.entities.mechanisms', 'entities', '方块实体 · 机关', (32, 10, 28), 'minecraft:structure_block'),
    ('test.entities.recent', 'entities', '方块实体 · 新版本', (32, 10, 28), 'minecraft:trial_spawner'),
    ('test.registry.vanilla', 'registry', '原版方块全览', (64, 64, 64), 'minecraft:stone'),
)


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
        if entity is not None:
            nbt = {'id': tag(entity, 8)}
            nbt.update((axis, tag(pos[index], 3)) for index, axis in enumerate(('x', 'y', 'z')))
            nbt.update(fields or {})
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


def _snow(fixture):
    fixture.floor()
    names = ('short_grass', 'fern', 'dandelion', 'poppy', 'blue_orchid', 'allium')
    for index, name in enumerate(names):
        x = 3 + index * 5
        value = material(name)
        fixture.group((x, 1, 3), value)
        fixture.group((x, 1, 9), value)
        fixture.group((x, 1, 16), value)
        for z, height in ((9, 0), (16, 5)):
            pos = (x, 1, z)
            snow = _covered_snow(material('snow_layer', {'height': height}), True)
            fixture.put(pos, snow, value)
    for x, species in ((5, 'oak_leaves'), (11, 'spruce_leaves'), (17, 'cherry_leaves')):
        fixture.put((x, 3, 21), material(species))
        fixture.put((x, 4, 21), material('snow_layer', {'height': 2}))
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
    for index, facing in enumerate(range(6)):
        fixture.put((3 + index * 5, 3, 28), material('purple_shulker_box'),
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
    builders = {'test.layers.water': _water, 'test.layers.snow': _snow,
                'test.groups.parts': _groups, 'test.connections.context': _connections,
                'test.transforms.directions': _directions, 'test.registry.vanilla': _vanilla}
    if metadata[1] == 'entities':
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
