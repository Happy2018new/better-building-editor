"""Barrier visibility is a render-palette substitution, never a document edit."""

NATIVE_NAME = 'minecraft:barrier'
MARKER_NAME = 'modern_projection:preview_barrier_marker'
TEXTURE_KEY = 'modern_projection_barrier_marker'
PROXIES = {NATIVE_NAME: MARKER_NAME}
INTERNAL_BLOCKS = frozenset((MARKER_NAME,))
STYLE_VERSION = 1
STYLE = 'three_axis_double_sided_native_sprite'
