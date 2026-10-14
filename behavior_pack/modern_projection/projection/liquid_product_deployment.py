"""Select explicitly accepted water visuals without claiming native parity."""
from . import liquid_product_qualification_data as qualification
from .liquid_render_target_data import TARGET_ENGINE_VERSION

REQUIRED_GATES = frozenset(('editor', 'projection_full', 'projection_missing', 'transparency',
                            'geometry', 'animation', 'biome', 'lifecycle'))


def candidate_profile(frozen=False):
    """Explicit diagnostic entry; it never changes the production acceptance data."""
    from .liquid_deployment import ui_pose, ui_offset
    from .liquid_product_profile import ProductLiquidProfile
    from . import liquid_product_resource_data as resources
    selected = dict(resources.PRODUCT_RESOURCES)
    if frozen:
        selected['models'] = resources.FROZEN_PRODUCT_MODELS
    return ProductLiquidProfile(selected, ui_pose, ui_offset)


def production_profile(engine_version=None):
    if not qualification.PRODUCT_QUALIFIED:
        return None
    if engine_version != TARGET_ENGINE_VERSION:
        return None
    from . import liquid_product_resource_data as resources, liquid_product_shape_data as rules
    from . import liquid_product_owner_data as owners
    evidence = qualification.QUALIFICATION_SHA256
    if (qualification.SCHEMA_VERSION != 1
            or qualification.QUALIFICATION_ENGINE_VERSION != TARGET_ENGINE_VERSION
            or not isinstance(evidence, str) or len(evidence) != 64
            or any(value not in '0123456789abcdef' for value in evidence)
            or qualification.QUALIFICATION_RESOURCE_CONTRACT_SHA256 != resources.PRODUCT_RESOURCE_CONTRACT_SHA256
            or qualification.QUALIFICATION_RULES_SHA256 != rules.PRODUCT_RULES_SHA256
            or qualification.QUALIFICATION_STYLE_VERSION != rules.PRODUCT_STYLE_VERSION
            or owners.SCHEMA_VERSION != 1
            or qualification.QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256 != owners.IMPLEMENTATION_CONTRACT_SHA256
            or not isinstance(qualification.GATES, dict) or set(qualification.GATES) != REQUIRED_GATES
            or any(value is not True for value in qualification.GATES.values())):
        raise ValueError('Product water needs complete visible acceptance for these exact rules and resources')
    return candidate_profile()
