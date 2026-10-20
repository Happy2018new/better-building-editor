# -*- coding: utf-8 -*-
"""Small editable transform candidates; loading does not imply visual acceptance."""
from __future__ import unicode_literals

SCHEMA_VERSION = 1
PREFIX = 'test.transforms.acceptance.'
METADATA = (
    (PREFIX + 't01', 'transforms', 'T01 · 不对称建筑与六种变换',
     (24, 10, 24), 'minecraft:oak_stairs'),
    (PREFIX + 't04', 'transforms', 'T04 · 跨格双箱与内容保真',
     (32, 10, 24), 'minecraft:chest'),
    (PREFIX + 't05', 'transforms', 'T05 · 四种铁轨与坡顶连接',
     (32, 8, 32), 'minecraft:rail'),
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
    PREFIX + 't08': {
        'selection': ((14, 14, 14), (18, 18, 18)), 'focus': (16, 16, 16),
        'door': ((15, 15, 15), (15, 16, 15)),
        'pair': ((15, 15, 18), (16, 15, 18)),
        'outside_marker': (3, 1, 3), 'locked_layer': 16,
        'message': 'T08：门跨Y=15/16、双箱跨X=15/16。先旋转并撤销/重做；锁定16层后的变换应整体拒绝。',
        'actions': ('rotate_y90', 'undo', 'redo', 'undo', 'lock_y16',
                    'rotate_y90_rejected', 'unlock_y16'),
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
    editor.select_box(*row['selection'])
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


def _chests(fixture, row):
    from .debug_blueprints import material
    _marked_base(fixture, (14, 1, 3), (18, 1, 8))
    for number, pair in enumerate(row['pairs']):
        _paired_chests(fixture, pair[0], pair[1], 'north')
        for pos in pair:
            fixture.put((pos[0], 1, pos[2]), material(
                'red_concrete' if number == 0 else 'blue_concrete'))


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


def populate(fixture, identity):
    row = CASES[identity]
    builders = {'t01': _asymmetric, 't04': _chests, 't05': _rails, 't08': _boundary}
    builders[identity[len(PREFIX):]](fixture, row)
    return fixture.finish()


def build(identity):
    """Independent loader used by offline and runtime probes before UI registration."""
    from .debug_blueprints import Fixture
    metadata = next(row for row in METADATA if row[0] == identity)
    return populate(Fixture(metadata), identity)
