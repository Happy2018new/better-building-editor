# -*- coding: utf-8 -*-
"""One small asymmetric public fixture for projection settings and placement."""
from __future__ import unicode_literals

METADATA = ('test.transforms.projection_small', 'transforms',
            '投影旋转／镜像 · 小型对照', (7, 4, 5), 'minecraft:oak_stairs')
MARKERS = (((0, 0, 0), 'red_concrete'), ((6, 0, 0), 'lime_concrete'),
           ((0, 0, 4), 'blue_concrete'), ((6, 0, 4), 'yellow_concrete'),
           ((0, 3, 0), 'magenta_concrete'))
MESSAGE = ('投影页设置旋转或镜像，再生成／更新；看红绿蓝黄四角、紫色高角与楼梯。'
           '真实写入请用独立测试世界。')
VISUAL_CASE = {
    'schema': 1, 'fixture': METADATA[0], 'size': METADATA[3],
    'focus': (3.5, 2., 2.5), 'markers': MARKERS,
    'modes': ('editor', 'full', 'missing', 'world_apply'),
    'manual_acceptance': 'pending', 'GPU_qualified': False,
    'expected': {
        'rotate_y90': {
            'size': (5, 4, 7),
            'markers': (((4, 0, 0), 'red_concrete'), ((4, 0, 6), 'lime_concrete'),
                        ((0, 0, 0), 'blue_concrete'), ((0, 0, 6), 'yellow_concrete'),
                        ((4, 3, 0), 'magenta_concrete')),
        },
        'mirror_x': {
            'size': (7, 4, 5),
            'markers': (((6, 0, 0), 'red_concrete'), ((0, 0, 0), 'lime_concrete'),
                        ((6, 0, 4), 'blue_concrete'), ((0, 0, 4), 'yellow_concrete'),
                        ((6, 3, 0), 'magenta_concrete')),
        },
        'mirror_y': {
            'size': (7, 4, 5),
            'markers': (((0, 3, 0), 'red_concrete'), ((6, 3, 0), 'lime_concrete'),
                        ((0, 3, 4), 'blue_concrete'), ((6, 3, 4), 'yellow_concrete'),
                        ((0, 0, 0), 'magenta_concrete')),
        },
    },
    'world_comparison': 'Use a separate empty test world; apply the confirmed '
                        'projection settings, compare full and missing views, '
                        'and keep the editing document unchanged.',
}


def populate(fixture):
    from .debug_blueprints import material
    for position, color in MARKERS:
        fixture.put(position, material(color))
    for position in ((1, 0, 1), (2, 0, 1), (3, 0, 1), (4, 0, 1),
                     (5, 0, 1), (1, 0, 2), (1, 0, 3)):
        fixture.put(position, material('white_concrete'))
    fixture.put((2, 1, 1), material('oak_stairs', {
        'weirdo_direction': 0, 'upside_down_bit': False}))
    fixture.put((4, 2, 3), material('oak_stairs', {
        'weirdo_direction': 3, 'upside_down_bit': True}))
    for x, axis in ((1, 'x'), (3, 'y'), (5, 'z')):
        fixture.put((x, 1, 2), material('oak_log', {'pillar_axis': axis}))
    return fixture.finish()
