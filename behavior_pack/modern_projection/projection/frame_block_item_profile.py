"""Frame-only cube resources have acceptance separate from flat item icons."""
from . import block_registry
from . import frame_block_item_data as source

MATERIALS = ('opaque', 'cutout', 'translucent')


def candidate_items(engine_version, materials=MATERIALS):
    if (source.SCHEMA_VERSION != 1 or source.LAYOUT_VERSION != 1 or
            source.ENGINE_VERSION != engine_version or
            source.PALETTE_SHA256 != block_registry.fingerprint()):
        raise ValueError('Frame block items need regeneration for this engine and palette')
    if (not isinstance(materials, tuple) or
            any(material not in MATERIALS for material in materials)):
        raise ValueError('Frame block items require explicit known material families')
    rows = {}
    for key, row in source.ITEMS.items():
        if (row.get('family') != 'frame_block_cube' or
                row.get('content_families') != ('frame',) or
                row.get('supports_enchantment') is not True or
                row.get('material') not in MATERIALS):
            raise ValueError('Frame block resources exceed their independent content scope')
        if row['material'] in materials:
            rows[key] = row
    return rows


def production_items(engine_version):
    if engine_version != source.ENGINE_VERSION or not source.PRODUCTION_QUALIFIED:
        return {}
    digest = source.QUALIFICATION_SHA256
    if (not isinstance(digest, str) or len(digest) != 64 or
            any(value not in '0123456789abcdef' for value in digest) or
            source.QUALIFICATION_RESOURCE_SHA256 != source.RESOURCE_SHA256 or
            source.POSE.get('accepted') is not True):
        raise ValueError('Frame block deployment needs matching native pose and pixel acceptance')
    if not source.QUALIFIED_MATERIALS:
        raise ValueError('Frame block deployment requires material-specific native acceptance')
    return candidate_items(engine_version, source.QUALIFIED_MATERIALS)
