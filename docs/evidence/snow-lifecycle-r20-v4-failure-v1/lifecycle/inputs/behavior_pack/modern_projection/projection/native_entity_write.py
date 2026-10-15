"""Select version-bound native tile rebuilds for typed entity writes."""
from __future__ import unicode_literals
from . import block_registry as registry
from . import native_entity_write_data as source


def tile_rebuild_stages(material, back, nbt):
    if (nbt is None or material[0] not in source.TILE_REBUILD_STAGES or
            material[1] not in source.OBSERVED_AUX_VALUES or
            back not in (('minecraft:air', 0), ('minecraft:water', 0))):
        return ()
    if (source.SCHEMA_VERSION != 1 or source.SOURCE_VERSION != registry.source_version() or
            source.PALETTE_SHA256.lower() != registry.fingerprint().lower()):
        raise ValueError('Native entity write rules need observations for this block registry')
    return source.TILE_REBUILD_STAGES[material[0]]['dry' if back[0] == 'minecraft:air' else 'wet']
