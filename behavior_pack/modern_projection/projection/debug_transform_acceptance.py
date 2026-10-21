# -*- coding: utf-8 -*-
"""Small editable transform candidates; loading does not imply visual acceptance."""
from __future__ import unicode_literals

SCHEMA_VERSION = 1
PREFIX = 'test.transforms.acceptance.'
METADATA = (
    (PREFIX + 't01', 'transforms', 'T01 · 不对称建筑与六种变换',
     (24, 10, 24), 'minecraft:oak_stairs'),
    (PREFIX + 't02', 'transforms', 'T02 · 楼梯、半砖与附着方向',
     (32, 10, 32), 'minecraft:trapdoor'),
    (PREFIX + 't03', 'transforms', 'T03 · 门、床与双格植物整组',
     (32, 10, 32), 'minecraft:wooden_door'),
    (PREFIX + 't03_half', 'transforms', 'T03 · 只框门上半的伙伴边界',
     (32, 10, 32), 'minecraft:wooden_door'),
    (PREFIX + 't04', 'transforms', 'T04 · 跨格双箱与内容保真',
     (32, 10, 24), 'minecraft:chest'),
    (PREFIX + 't05', 'transforms', 'T05 · 四种铁轨与坡顶连接',
     (32, 8, 32), 'minecraft:rail'),
    (PREFIX + 't06', 'transforms', 'T06 · 楼梯转角与跨格连接',
     (32, 10, 32), 'minecraft:oak_fence'),
    (PREFIX + 't07', 'transforms', 'T07 · 水雪双层与告示牌文字',
     (32, 10, 32), 'minecraft:standing_sign'),
    (PREFIX + 't08', 'transforms', 'T08 · 跨16格、多格与原子撤销',
     (32, 36, 32), 'minecraft:wooden_door'),
)
CASES = {
    PREFIX + 't01': {
        'selection': ((2, 1, 2), (8, 5, 6)), 'focus': (5, 3, 4),
        'markers': (((2, 1, 2), 'red_concrete'), ((8, 1, 2), 'lime_concrete'),
                    ((2, 1, 6), 'blue_concrete'), ((8, 1, 6), 'yellow_concrete'),
                    ((2, 5, 2), 'magenta_concrete')),
        'message': 'T01：已选中7×5×5范围；红绿蓝黄为底角，紫为上角。先旋转90°，撤销，再看镜像。',
        'actions': ('rotate_y90', 'undo', 'mirror_x', 'undo', 'mirror_y',
                    'undo', 'mirror_z', 'undo'),
    },
    PREFIX + 't02': {
        'selection': ((1, 1, 1), (21, 6, 30)), 'focus': (11, 3, 15),
        'columns': (3, 8, 13, 18),
        'message': 'T02：从前到后为正倒楼梯、上下半砖、关闭/打开活板门、四向梯子、六面按钮。镜像Y看上下，旋转看朝向；每步可撤销。',
        'actions': ('mirror_y', 'undo', 'rotate_y90', 'undo', 'mirror_x',
                    'undo', 'mirror_z', 'undo'),
    },
    PREFIX + 't03': {
        'selection': ((2, 1, 2), (20, 5, 23)), 'focus': (10, 3, 12),
        'partial_targets': ((4, 3, 4), (4, 2, 11), (4, 3, 17)),
        'message': 'T03：前排两种铰链门，中排四向床，后排高草/向日葵。整组旋转或镜像后撤销；只框上半门请载入T03伙伴边界例。',
        'actions': ('rotate_y90', 'undo', 'mirror_x', 'undo', 'mirror_y',
                    'undo', 'mirror_z', 'undo'),
    },
    PREFIX + 't03_half': {
        'requested_selection': ((4, 3, 4), (4, 3, 4)),
        'selection': ((4, 2, 4), (4, 3, 4)), 'focus': (4, 3, 4),
        'partial_targets': ((4, 3, 4), (4, 2, 11), (4, 3, 17)),
        'message': 'T03伙伴边界：只请求门上半(4,3,4)，现有规则已补选下半。旋转后整门应保持完整，撤销恢复；其他门床植物不应变化。',
        'actions': ('rotate_y90', 'undo', 'mirror_x', 'undo', 'mirror_y', 'undo'),
    },
    PREFIX + 't04': {
        'selection': ((14, 1, 3), (18, 5, 8)), 'focus': (16, 3, 5),
        'pairs': (((15, 2, 4), (16, 2, 4)), ((15, 2, 7), (16, 2, 7))),
        'message': 'T04：两组双箱跨X=15/16；红/蓝台座区分两组。先旋转90°并撤销，再镜像X并撤销。',
        'actions': ('rotate_y90', 'undo', 'mirror_x', 'undo', 'save_reload'),
    },
    PREFIX + 't05': {
        'selection': ((2, 1, 2), (11, 5, 27)), 'focus': (6, 2, 14),
        'rail_names': ('rail', 'golden_rail', 'detector_rail', 'activator_rail'),
        'lanes': (3, 8, 13, 18),
        'slope_top_pairs': tuple(((4, 2, z), (5, 3, z)) for z in (3, 8, 13, 18)),
        'message': 'T05：四排依次为普通/动力/探测/激活铁轨，最末为普通轨转角。分别记录像素与投影接缝。',
        'actions': ('rotate_y90', 'undo', 'mirror_x', 'undo'),
    },
    PREFIX + 't06': {
        'selection': ((2, 1, 2), (20, 5, 27)), 'focus': (11, 3, 15),
        'stair_corners': (((4, 2, 4), (4, 2, 3), 'outer', False),
                          ((10, 2, 4), (10, 2, 5), 'inner', False),
                          ((4, 3, 9), (4, 3, 8), 'outer', True),
                          ((10, 3, 9), (10, 3, 10), 'inner', True)),
        'gate': (15, 2, 13), 'gate_neighbors': ((14, 2, 13), (16, 2, 13)),
        'wall': (15, 2, 16),
        'wall_neighbors': ((14, 2, 16), (16, 2, 16), (15, 2, 17)),
        'thin_runs': (('glass_pane', ((14, 2, 22), (15, 2, 22), (16, 2, 22), (15, 2, 23))),
                      ('iron_bars', ((14, 2, 26), (15, 2, 26), (16, 2, 26), (15, 2, 25)))),
        'message': 'T06：前两排为正倒楼梯外角/内角，后方为栅栏门、墙、玻璃板、铁栏杆；连接跨X或Z=15/16。整体旋转或镜像，检查接缝，再撤销。',
        'actions': ('rotate_y90', 'undo', 'mirror_x', 'undo', 'mirror_z', 'undo'),
    },
    PREFIX + 't08': {
        'selection': ((14, 14, 14), (18, 18, 18)), 'focus': (16, 16, 16),
        'door': ((15, 15, 15), (15, 16, 15)),
        'pair': ((15, 15, 18), (16, 15, 18)),
        'outside_marker': (3, 1, 3), 'locked_layer': 16,
        'message': 'T08：门跨Y=15/16、双箱跨X=15/16。先旋转并撤销/重做；锁定16层后的变换应整体拒绝。',
        'actions': ('rotate_y90', 'undo', 'redo', 'undo', 'lock_y16',
                    'rotate_y90_rejected', 'unlock_y16'),
    },
    PREFIX + 't07': {
        'selection': ((2, 1, 2), (14, 5, 18)), 'focus': (8, 2, 10),
        'subjects': (
            ('dry_stairs', 'test.layers.water', (18, 1, 3), (4, 2, 4)),
            ('wet_stairs', 'test.layers.water', (18, 1, 6), (8, 2, 4)),
            ('background_water', 'test.layers.water', (3, 1, 9), (12, 2, 4)),
            ('snow_h0', 'test.layers.snow', (18, 1, 9), (4, 2, 10)),
            ('snow_h5', 'test.layers.snow', (18, 1, 16), (8, 2, 10)),
            ('dry_poppy', 'test.layers.snow', (18, 1, 3), (12, 2, 10)),
            ('dry_sign', 'test.entities.signs', (5, 1, 7), (4, 2, 16)),
            ('wet_sign', 'test.entities.signs', (3, 1, 7), (10, 2, 16)),
        ),
        'outside_marker': (24, 1, 24),
        'message': 'T07：前排干/含水楼梯和仅背景水，中排薄雪/厚雪/干罂粟，后排干/含水双面告示牌。旋转或镜像后检查两层、朝向与文字，再撤销；区外紫标不应移动。',
        'actions': ('rotate_y90', 'undo', 'mirror_x', 'undo', 'mirror_z', 'undo'),
    },
}
VISUAL_CASES = dict((identity, dict(row, schema=SCHEMA_VERSION, fixture=identity,
    modes=('editor', 'full', 'missing'),
    camera={'editor': (35., 25., 2.), 'world_offset': (-7., 5., -10.)},
    acceptance={'data': 'pending', 'editor': 'pending', 'full': 'pending',
                'missing': 'pending'},
    restore='Undo the operation or reload this built-in fixture; loading replaces the draft.'))
    for identity, row in CASES.items())


def prepare(editor, identity):
    """Select the bounded subject so references and empty canvas are not transformed."""
    row = CASES.get(identity)
    if row is None:
        return False
    editor.select_box(*row.get('requested_selection', row['selection']))
    editor.message = row['message']
    return True


def _marked_base(fixture, lo, hi, color='light_gray_concrete'):
    from .debug_blueprints import material
    for x in range(lo[0], hi[0] + 1):
        for z in range(lo[2], hi[2] + 1):
            fixture.put((x, lo[1], z), material(color))


def _asymmetric(fixture, row):
    from .debug_blueprints import material
    _marked_base(fixture, (2, 1, 2), (8, 1, 6))
    for pos, name in row['markers']:
        fixture.put(pos, material(name))
    for y in range(2, 5):
        fixture.put((2, y, 2), material('red_concrete'))
    fixture.put((3, 2, 3), material('oak_stairs', {'weirdo_direction': 0}))
    fixture.put((4, 2, 3), material('oak_stairs', {
        'weirdo_direction': 3, 'upside_down_bit': True}))
    fixture.put((6, 2, 5), material('oak_log', {'pillar_axis': 'x'}))
    fixture.put((7, 3, 4), material('dispenser', {'facing_direction': 5}))


def _paired_chests(fixture, left, right, direction):
    from .block_groups import hydrate_chest_actor
    from .debug_blueprints import material, tag
    from .debug_entity_defaults import nbt
    from .cell import make_cell
    from .nbt_spatial import root_payload
    from .visible_actor import compose_actor
    value = material('chest', {'minecraft:cardinal_direction': direction})
    for index, pos in enumerate((left, right)):
        partner = right if index == 0 else left
        actor = nbt(value[0], pos)
        root_payload(actor).update({
            'pairx': tag(partner[0], 3), 'pairz': tag(partner[2], 3),
            'pairlead': tag(1 - index, 1), 'renderlead': tag(index, 1),
            # Keyword argument names are bytes in Python 2 despite
            # unicode_literals; literal keys keep both fixture hosts identical.
            'Items': [{'Name': tag('minecraft:diamond' if index == 0 else
                                   'minecraft:emerald', 8), 'Count': tag(7 + index, 1),
                       'Damage': tag(0, 2), 'Slot': tag(0, 1)}],
        })
        cell = make_cell(value, nbt=compose_actor({}, actor))
        fixture.document.blocks[pos] = hydrate_chest_actor(cell, pos)


def _directions(fixture, row):
    from .debug_blueprints import material
    directions = ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1))
    facings = ((0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1),
               (-1, 0, 0), (1, 0, 0))
    stone = material('stone')
    for direction, x in enumerate(row['columns']):
        for upper, z in ((False, 3), (True, 7)):
            fixture.put((x, 2, z), stone)
            fixture.put((x, 3, z), material('oak_stairs', {
                'weirdo_direction': direction, 'upside_down_bit': upper}))
        for opened, z in ((False, 15), (True, 19)):
            fixture.put((x, 3, z), material('trapdoor', {
                'direction': direction, 'upside_down_bit': bool(direction % 2),
                'open_bit': opened}))
            normal = directions[direction]
            fixture.put((x - normal[0], 3, z - normal[2]), stone)
        normal = facings[direction + 2]
        fixture.put((x, 3, 23), material('ladder', {'facing_direction': direction + 2}))
        fixture.put((x - normal[0], 3, 23 - normal[2]), stone)
    for x, half in zip(row['columns'][:2], ('bottom', 'top')):
        fixture.put((x, 2, 11), stone)
        fixture.put((x, 3, 11), material('oak_slab', {'minecraft:vertical_half': half}))
    for direction, normal in enumerate(facings):
        x, z = row['columns'][direction % 4], 27 if direction < 4 else 29
        fixture.put((x, 3, z), material('stone_button', {
            'facing_direction': direction, 'button_pressed_bit': False}))
        fixture.put((x - normal[0], 3 - normal[1], z - normal[2]), stone)
    for pos, color in (((1, 1, 1), 'red_concrete'), ((21, 1, 1), 'lime_concrete'),
                       ((1, 1, 30), 'blue_concrete'), ((21, 6, 30), 'magenta_concrete')):
        fixture.put(pos, material(color))


def _chests(fixture, row):
    from .debug_blueprints import material
    _marked_base(fixture, (14, 1, 3), (18, 1, 8))
    for number, pair in enumerate(row['pairs']):
        _paired_chests(fixture, pair[0], pair[1], 'north')
        for pos in pair:
            fixture.put((pos[0], 1, pos[2]), material(
                'red_concrete' if number == 0 else 'blue_concrete'))


def _parts(fixture, row):
    from .debug_blueprints import material
    from .cell import foreground
    for x, direction, opened, hinge in ((4, 'north', False, False),
                                        (10, 'east', True, True)):
        fixture.group((x, 2, 4), material('wooden_door', {
            'minecraft:cardinal_direction': direction, 'open_bit': opened,
            'door_hinge_bit': hinge, 'upper_block_bit': False}))
        fixture.put((x, 1, 4), material('stone'))
    for x, direction in ((4, 0), (9, 1), (14, 2), (19, 3)):
        fixture.group((x, 2, 10), material('bed', {
            'direction': direction, 'head_piece_bit': False}), entity='Bed')
    for x, name in ((4, 'tall_grass'), (10, 'sunflower')):
        fixture.group((x, 2, 17), material(name, {'upper_block_bit': False}))
        fixture.put((x, 1, 17), material('grass_block'))
    # Beds have horizontal partners; provide a support below both native halves.
    for pos in tuple(fixture.document.blocks):
        if foreground(fixture.document.get(pos))[0] == 'minecraft:bed':
            fixture.put((pos[0], pos[1] - 1, pos[2]), material('stone'))
    for pos, name in (((2, 1, 2), 'red_concrete'), ((20, 5, 23), 'blue_concrete')):
        fixture.put(pos, material(name))


def _connections(fixture, row):
    from .debug_blueprints import material
    for center, neighbor, unused, upper in row['stair_corners']:
        for pos, direction in ((center, 3), (neighbor, 0)):
            fixture.put(pos, material('oak_stairs', {
                'weirdo_direction': direction, 'upside_down_bit': upper}))
    fixture.put(row['gate'], material('fence_gate', {
        'minecraft:cardinal_direction': 'north', 'open_bit': False}))
    for pos in row['gate_neighbors']:
        fixture.put(pos, material('oak_fence'))
    for pos in (row['wall'],) + row['wall_neighbors']:
        fixture.put(pos, material('cobblestone_wall'))
    for name, positions in row['thin_runs']:
        for pos in positions:
            fixture.put(pos, material(name))
    for pos in tuple(fixture.document.blocks):
        fixture.put((pos[0], pos[1] - 1, pos[2]), material('stone'))
    for pos, name in (((2, 1, 2), 'red_concrete'), ((20, 5, 27), 'blue_concrete')):
        fixture.put(pos, material(name))


def _rails(fixture, row):
    from .debug_blueprints import material
    for name, z in zip(row['rail_names'], row['lanes']):
        points = ((3, 2, 1), (4, 2, 2), (5, 3, 1), (6, 3, 1),
                  (7, 3, 1), (8, 2, 3), (9, 2, 1))
        for x, y, shape in points:
            fixture.put((x, y - 1, z), material('stone'))
            fixture.put((x, y, z), material(name, {'rail_direction': shape}))
    for x in range(3, 10):
        for z in (23, 26):
            shape = (6 if x == 3 else 7) if z == 23 else (9 if x == 3 else 8)
            if x not in (3, 9):
                shape = 1
            fixture.put((x, 1, z), material('stone'))
            fixture.put((x, 2, z), material('rail', {'rail_direction': shape}))
    for x in (3, 9):
        for z in (24, 25):
            fixture.put((x, 1, z), material('stone'))
            fixture.put((x, 2, z), material('rail', {'rail_direction': 0}))


def _boundary(fixture, row):
    from .debug_blueprints import material
    _marked_base(fixture, (14, 14, 14), (18, 14, 18))
    fixture.group(row['door'][0], material('wooden_door', {
        'minecraft:cardinal_direction': 'north'}))
    _paired_chests(fixture, row['pair'][0], row['pair'][1], 'north')
    fixture.put(row['outside_marker'], material('magenta_concrete'))
    fixture.put((18, 18, 14), material('lime_concrete'))


def _layers(fixture, row):
    from .debug_blueprints import build as build_source, material
    from .cell import actor_data, background, foreground, make_cell
    from .nbt_spatial import rebase
    # Read the established samples verbatim; only tagged root positions move.
    sources = dict((identity, build_source(identity)) for identity in
                   ('test.layers.water', 'test.layers.snow', 'test.entities.signs'))
    for unused, identity, source, target in row['subjects']:
        document = sources[identity]
        if source not in document.blocks:
            raise ValueError('Missing source cell for layered transform fixture')
        value = document.get(source)
        delta = tuple(target[axis] - source[axis] for axis in range(3))
        fixture.document.blocks[target] = make_cell(
            foreground(value), background(value), rebase(actor_data(value), delta))
        fixture.put((target[0], target[1] - 1, target[2]), material(
            'dirt' if identity == 'test.layers.snow' else 'stone'))
    for pos, name in (((2, 1, 2), 'red_concrete'), ((14, 5, 18), 'blue_concrete'),
                      (row['outside_marker'], 'magenta_concrete')):
        fixture.put(pos, material(name))


def populate(fixture, identity):
    row = CASES[identity]
    builders = {'t01': _asymmetric, 't02': _directions, 't03': _parts,
                't03_half': _parts, 't04': _chests, 't05': _rails,
                't06': _connections, 't07': _layers, 't08': _boundary}
    builders[identity[len(PREFIX):]](fixture, row)
    return fixture.finish(reconnect=identity == PREFIX + 't06')


def build(identity):
    """Independent loader used by offline and runtime probes before UI registration."""
    from .debug_blueprints import Fixture
    metadata = next(row for row in METADATA if row[0] == identity)
    return populate(Fixture(metadata), identity)
