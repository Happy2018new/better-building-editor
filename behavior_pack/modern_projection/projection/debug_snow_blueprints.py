# -*- coding: utf-8 -*-
"""Measured snow plants and all heights, with stable historical probe cells."""
from __future__ import unicode_literals
from . import block_registry as registry
from .block_traits_data import SNOW_COVERABLE_BLOCKS
from .cell import _covered_snow

METADATA = ('test.layers.snow', 'layers', '含雪方块', (64, 8, 64), 'minecraft:snow_layer')
_LEGACY = ('short_grass', 'fern', 'dandelion', 'poppy', 'blue_orchid', 'allium')
NAMES = _LEGACY + tuple(name.split(':', 1)[1] for name in sorted(SNOW_COVERABLE_BLOCKS)
                        if name.split(':', 1)[1] not in _LEGACY)


def _cells():
    # The right and lower bands leave the old six dry/thin/thick cells intact.
    free = iter(tuple((x, 1, z) for z in range(3, 63, 3) for x in range(34, 63, 3)) +
                tuple((x, 1, z) for z in range(25, 63, 3) for x in range(3, 32, 3)))
    rows = []
    for index, name in enumerate(NAMES):
        old = index < len(_LEGACY)
        standalone = (3 + index * 5, 1, 3) if old else next(free)
        covered = tuple((height, ((3 + index * 5, 1, 9 if height == 0 else 16)
                                  if old and height in (0, 5) else next(free)))
                        for height in range(8))
        rows.append({'plant': name, 'standalone': standalone, 'covered': covered,
                     'support': 'podzol' if name in ('brown_mushroom', 'red_mushroom') else 'dirt'})
    return tuple(rows)


VISUAL_CASE = {
    'schema': 4, 'fixture': METADATA[0], 'cells': _cells(),
    'size': (3, 3, 3), 'focus': (1, 1, 1), 'heights': tuple(range(8)),
    'camera': {'editor': (35., 10., 2.8), 'world_offset': (-2., .15, -2.5)},
    'native_biome': 'minecraft:ice_plains',
    'fungus_boundary': {
        'schema': 1,
        'geometry_status': 'Centered cross measured at two fixed views; authoritative native mesh unverified',
        'views': {'public': (-2., .15, -2.5), 'right': (2., .15, -2.5)},
        'heights': {'crimson_fungus': (4, 5), 'warped_fungus': (3, 4)},
        'scope': 'Dry and immediately before/at the alpha-derived candidate burial boundary, both modes and both fixed views',
        'all_eight_snow_heights_accepted': False,
    },
    'fungus_remaining': {
        'schema': 1,
        'geometry_status': 'R7 centered cross; remaining-height acceptance pending independent native pixels',
        'native_target': (-47, 117, -70),
        'views': {'public': (-2., .15, -2.5), 'right': (2., .15, -2.5)},
        'heights': {'crimson_fungus': (0, 1, 2, 3, 6, 7),
                    'warped_fungus': (0, 1, 2, 5, 6, 7)},
        'scope': 'Dry control and the six heights absent from the R7 boundary matrix, both modes and both fixed views',
        'all_eight_snow_heights_accepted': False,
    },
}


def populate(fixture):
    fixture.floor()
    for row in VISUAL_CASE['cells']:
        name = 'minecraft:' + row['plant']
        plant = (name, registry.DEFAULT_AUX[name])
        support_name = 'minecraft:' + row['support']
        support = (support_name, registry.DEFAULT_AUX[support_name])
        for height, pos in ((None, row['standalone']),) + row['covered']:
            fixture.put((pos[0], pos[1] - 1, pos[2]), support)
            if height is None:
                fixture.put(pos, plant)
            else:
                snow = registry.from_states('minecraft:snow_layer', {'height': height, 'covered_bit': True})
                if snow is None:
                    raise ValueError('Missing native covered snow height: %d' % height)
                fixture.put(pos, _covered_snow(snow, True), plant)
    for x, species in ((5, 'oak_leaves'), (11, 'spruce_leaves'), (17, 'cherry_leaves')):
        name = 'minecraft:' + species
        fixture.put((x, 3, 21), (name, registry.DEFAULT_AUX[name]))
        snow = registry.from_states('minecraft:snow_layer', {'height': 2, 'covered_bit': False})
        fixture.put((x, 4, 21), snow)
    return fixture.finish()
