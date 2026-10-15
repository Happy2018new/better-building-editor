"""Render-only table body; logical cells and stored actors remain unchanged."""
from . import block_registry, static_table_data

TABLE_PROXY = static_table_data.PROXY
CANDIDATE_ENABLED = False


def table_proxy(material):
    # The current registry has one stateless enchanting-table appearance.
    # Unknown future states retain their native path until requalified.
    if material != ('minecraft:enchanting_table', 0):
        return None
    # Occupied neighbor tiles retain this candidate's boundary faces.
    # Keep the native body until its independent body gate is qualified.
    if static_table_data.PRODUCT_QUALIFIED is not True and CANDIDATE_ENABLED is not True:
        return None
    if (static_table_data.SCHEMA_VERSION != 1 or
            static_table_data.SOURCE_VERSION != block_registry.source_version() or
            static_table_data.PALETTE_SHA256 != block_registry.fingerprint().lower()):
        raise ValueError('Table body sources differ from the current block registry')
    return (TABLE_PROXY, 0)
