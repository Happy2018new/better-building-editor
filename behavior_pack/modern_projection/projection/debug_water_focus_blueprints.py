"""Small public views reuse the qualified water gallery's exact source cells."""
from __future__ import unicode_literals

METADATA = (
    ('test.layers.water_source', 'layers', '\u6c34\u2460\u00b7\u5355\u6c34\u683c',
     (10, 8, 10), 'minecraft:water'),
    ('test.layers.water_pool', 'layers', '\u6c34\u2461\u00b7\u56db\u683c\u6c34\u6c60',
     (10, 8, 10), 'minecraft:water'),
    ('test.layers.water_fence', 'layers', '\u6c34\u2462\u00b7\u542b\u6c34\u6805\u680f',
     (10, 8, 10), 'minecraft:oak_fence'),
)
CASES = {
    METADATA[0][0]: {'case': 'source', 'focus': (3.5, 3.5, 3.5)},
    METADATA[1][0]: {'case': 'pool', 'focus': (4., 3.5, 4.)},
    METADATA[2][0]: {'case': 'wet_oak_fence', 'focus': (3.5, 3.5, 3.5)},
}


def build(identity):
    from .debug_product_water_blueprints import source_document
    document = source_document(CASES[identity]['case'])
    document.name = next(row[2] for row in METADATA if row[0] == identity)
    return document
