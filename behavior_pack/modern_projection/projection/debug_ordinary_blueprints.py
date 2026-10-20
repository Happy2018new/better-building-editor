# -*- coding: utf-8 -*-
"""Bounded manual-review galleries; inclusion is not an acceptance claim."""
from __future__ import unicode_literals

from . import block_registry as registry
from .block_groups import group_partner
from .debug_compatibility_blueprints import DYNAMIC_FAMILIES
from .entity_defaults_data import DEFAULTS

PAGE_CAPACITY = 24
PAGE_SIZE = (26, 8, 38)
SECTIONS = (('dynamic', '动态优先'), ('catalogue', '方块全览'),
            ('states', '其余状态'), ('context', '组合场景'))
INTERNAL_NAMES = frozenset(('air', 'allow', 'deny', 'border_block', 'camera',
                            'info_update', 'info_update2', 'invisible_bedrock',
                            'reserved6', 'structure_void', 'unknown', 'moving_block',
                            'client_request_placeholder_block'))
EDUCATION_NAMES = frozenset(('chemical_heat', 'underwater_tnt', 'underwater_torch'))


def exclusion(name):
    """Explicit scope reasons, independent of whether a block renders well."""
    if not name.startswith('minecraft:'):
        return 'custom'
    if name in DEFAULTS:
        return 'block_entity'
    short = name.split(':', 1)[1]
    if short in INTERNAL_NAMES:
        return 'internal_or_invisible'
    if (short in EDUCATION_NAMES or short.startswith(('element_', 'colored_torch_', 'hard_'))
            or '_hard_stained_glass' in short):
        return 'education'
    return None


NAMES = tuple(sorted(name for name in registry.BLOCKS if exclusion(name) is None))
_DYNAMIC = frozenset('minecraft:' + short for unused, unused_title, names in DYNAMIC_FAMILIES
                     for short in names if short not in ('big_dripleaf', 'end_portal_frame'))
DYNAMIC_NAMES = tuple(name for name in NAMES if name in _DYNAMIC)


def _pages(section, values):
    result = []
    title = dict(SECTIONS)[section]
    for start in range(0, len(values), PAGE_CAPACITY):
        number = start // PAGE_CAPACITY + 1
        page = values[start:start + PAGE_CAPACITY]
        identity = 'test.ordinary.%s.%03d' % (section, number)
        rows = tuple({'id': '%s:%d' % value, 'material': value,
                      'anchor': (3 + index % 4 * 6, 3, 3 + index // 4 * 6),
                      'ordinal': index + 1, 'status': 'pending_manual_review'}
                     for index, value in enumerate(page))
        metadata = (identity, 'manual', '%s · %03d · %s' % (
            title, number, page[0][0].split(':', 1)[1]), PAGE_SIZE, page[0][0])
        result.append((metadata, rows))
    return tuple(result)


def _catalogue():
    defaults = tuple((name, registry.DEFAULT_AUX[name]) for name in NAMES)
    dynamic = tuple((name, aux) for name in DYNAMIC_NAMES for aux in registry.aux_values(name))
    variants = tuple((name, aux) for name in NAMES if name not in _DYNAMIC
                     for aux in registry.aux_values(name) if aux != registry.DEFAULT_AUX[name])
    return _pages('dynamic', dynamic) + _pages('catalogue', defaults) + _pages('states', variants)


CATALOGUE = _catalogue()
METADATA = tuple(metadata for metadata, unused in CATALOGUE)
CASES = dict((metadata[0], rows) for metadata, rows in CATALOGUE)


def context_metadata(blueprints):
    """Expose existing supported neighborhoods without duplicating their builders."""
    sources = ('test.layers.water', 'test.layers.snow', 'test.groups.parts',
               'test.groups.slabs', 'test.connections.static',
               'test.connections.extended', 'test.connections.product',
               'test.transforms.directions')
    return tuple(('test.ordinary.context.' + row[0], 'manual', '组合 · ' + row[2],
                  row[3], row[4]) for row in blueprints if row[0] in sources)


def search_text(identity):
    rows = CASES.get(identity, ())
    return ' '.join(row['material'][0] for row in rows)


def populate(fixture, identity):
    for row in CASES[identity]:
        anchor, value = row['anchor'], row['material']
        support = anchor
        relationship = group_partner(value)
        if relationship is not None and relationship[0][1] < 0:
            support = (anchor[0], anchor[1] + relationship[0][1], anchor[2])
        # A small plinth leaves the sides visible and does not erase lower halves.
        fixture.plinth(support, 'light_gray_concrete')
        fixture.group(anchor, value)
    return fixture.finish()
