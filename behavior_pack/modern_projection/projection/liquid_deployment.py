"""Select the versioned resource profile only after visible native qualification."""
from . import liquid_resource_data as source
from .liquid_profile import NativeLiquidProfile


def ui_pose(unit, pitch, yaw, size):
    return unit / min(size), pitch - 90., 0., yaw


def ui_offset(size):
    return 0., min(size) / 4.


def candidate_profile(frozen=False):
    """Explicit diagnostic entry; it does not change the production gate."""
    resources = dict(source.RESOURCES)
    if frozen:
        resources['models'] = source.FROZEN_MODELS
    return NativeLiquidProfile(resources, ui_pose, ui_offset)


def production_profile():
    if not source.PRODUCTION_QUALIFIED:
        return None
    evidence = source.QUALIFICATION_SHA256
    if (not isinstance(evidence, str) or len(evidence) != 64
            or any(value not in '0123456789abcdef' for value in evidence)):
        raise ValueError('Liquid deployment needs its visible native qualification fingerprint')
    if source.QUALIFICATION_RESOURCE_CONTRACT_SHA256 != source.RESOURCE_CONTRACT_SHA256:
        raise ValueError('Liquid deployment qualification belongs to a different resource bundle')
    return candidate_profile()
