"""Visible product-style acceptance; exact-native evidence remains independent."""
SCHEMA_VERSION = 2
PRODUCT_QUALIFIED = False
QUALIFICATION_ENGINE_VERSION = None
QUALIFICATION_SHA256 = None
QUALIFICATION_RESOURCE_CONTRACT_SHA256 = None
QUALIFICATION_RULES_SHA256 = None
QUALIFICATION_STYLE_VERSION = None
QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256 = None
GATES = dict((name, False) for name in (
    'editor', 'projection_full', 'projection_missing', 'transparency',
    'geometry', 'animation', 'biome', 'lifecycle', 'side_uv',
    'visibility', 'neighbors', 'occupancy', 'budgets', 'default_path',
    'transparent_overlap', 'public_gallery'))
