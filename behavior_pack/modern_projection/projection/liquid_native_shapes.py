"""Versioned liquid neighborhood rules, independent of native model resources."""
from . import block_registry, block_traits_data, liquid_shape_data as source
from .block_traits import is_solid
from .cell import foreground, background
from .liquid_shape import DocumentLiquidShapes, LiquidHeightRule


def check_version():
    version, fingerprint = block_registry.source_version(), block_registry.fingerprint().lower()
    if (source.SCHEMA_VERSION != 1 or source.SOURCE_VERSION != version
            or source.PALETTE_SHA256.lower() != fingerprint
            or block_traits_data.SCHEMA_VERSION != 1 or block_traits_data.SOURCE_VERSION != version
            or block_traits_data.SOURCE_SHA256.lower() != fingerprint):
        raise ValueError('Native liquid shapes and block traits need regeneration for this registry')


def blocks_liquid(cell):
    return is_solid(foreground(cell)) or is_solid(background(cell))


def occludes_liquid(cell, unused_face):
    return blocks_liquid(cell)


def shape_provider(document, flow_uv=None, supported_names=None):
    """Build a source-owned provider; callers own resource and acceptance policy."""
    check_version()
    rules = dict((family, LiquidHeightRule(*row)) for family, row in source.HEIGHT_RULES.items())
    return DocumentLiquidShapes(document, rules, blocks_liquid, occludes_liquid,
                                source.SUPPORTED_NAMES if supported_names is None else supported_names, flow_uv)


def product_check_version():
    from . import liquid_product_shape_data as product
    version, fingerprint = block_registry.source_version(), block_registry.fingerprint().lower()
    if (product.SCHEMA_VERSION != 1 or product.PRODUCT_STYLE_VERSION != 'java_snapshot_water_v1'
            or product.SOURCE_VERSION != version or product.PALETTE_SHA256.lower() != fingerprint
            or product.HEIGHT_POLICY != 'conditional_diagonal_weighted_v1'
            or product.FLOW_POLICY != 'horizontal_and_below_snapshot_v1'
            or product.OCCLUSION_POLICY != 'opaque_full_cube_names_v1'
            or product.NATIVE_PARITY_CLAIMED is not False
            or product.ROTATION_STEPS != 256
            or block_traits_data.SCHEMA_VERSION != 1 or block_traits_data.SOURCE_VERSION != version
            or block_traits_data.SOURCE_SHA256.lower() != fingerprint):
        raise ValueError('Product water style and block traits need regeneration for this registry')


def product_shape_provider(document, supported_names=None):
    """Build the Java-style water snapshot policy, independently of native parity."""
    from . import liquid_product_shape_data as product
    from .liquid_product_flow_top import SnapshotFlowTop
    from .liquid_shape import ModernLiquidHeightRule, LiquidSnapshotFlowRule
    product_check_version()
    rules = {'water': ModernLiquidHeightRule(*product.HEIGHT_RULE)}
    flow = LiquidSnapshotFlowRule(product.FLOW_OWN_HEIGHTS, product.FLOW_BELOW_DROP)
    top = SnapshotFlowTop(product.TOP_TEMPLATE, product.TOP_ROTATION_OFFSET)
    names = product.SUPPORTED_NAMES if supported_names is None else frozenset(supported_names)
    if not names or not names.issubset(product.SUPPORTED_NAMES):
        raise ValueError('Product water names are outside this versioned style')
    return DocumentLiquidShapes(document, rules, blocks_liquid, occludes_liquid,
                                names, flow_rule=flow, flow_top=top)
