"""Versioned liquid render target and capability manifest.

The block registry and captured liquid artwork intentionally come from the
retained NEMC 3.9 snapshot.  This manifest records the separate game target so
that a future registry migration cannot silently make a 3.9 resource look like
an unversioned 3.10 capability.
"""
from __future__ import unicode_literals

from .cell import text_type


SCHEMA_VERSION = 1

# Registry/source provenance remains the 3.9 snapshot until a new palette is
# captured and reviewed.  Keep these names aligned with generated liquid data.
SOURCE_VERSION = 'NEMC 3.9.0.401155'
PALETTE_SHA256 = '6B2D9E961E934A745F5AB30D697CF22FB463FD3792D371A6DD42CB4342062F01'

# The installed development runtime is intentionally independent of the
# retained registry.  Update this module and tools/data/runtime_target_manifest.json
# together when the development target changes.
TARGET_ENGINE_VERSION = '3.10.0.420447'
TARGET_MINECRAFT_VERSION = '1.21.130.0'
TARGET_RESOURCE_VERSION = 'NEMC 3.10.0.420447'
TARGET_MANIFEST_SHA256 = '21a20d05d92a0e98d1e2e96cdbadf64b7b5ec9c7a615779f34e372271fac3416'

CAPABILITY_SCHEMA_VERSION = 1
CAPABILITIES = {
    'world_water': 'custom',
    'world_lava': 'native',
    'cauldron_contents': 'custom',
    'native_nbt': 'prefer_supported_appearance',
    'native_fire': 'accepted',
}


def check_version(registry_version, registry_fingerprint):
    """Reject a profile assembled from a different registry/target pair."""
    if (SCHEMA_VERSION != 1 or CAPABILITY_SCHEMA_VERSION != 1
            or TARGET_ENGINE_VERSION != '3.10.0.420447'
            or TARGET_MINECRAFT_VERSION != '1.21.130.0'
            or TARGET_RESOURCE_VERSION != 'NEMC ' + TARGET_ENGINE_VERSION
            or not isinstance(registry_version, text_type)
            or registry_version != SOURCE_VERSION
            or not isinstance(registry_fingerprint, text_type)
            or registry_fingerprint.lower() != PALETTE_SHA256.lower()
            or CAPABILITIES != {
                'world_water': 'custom',
                'world_lava': 'native',
                'cauldron_contents': 'custom',
                'native_nbt': 'prefer_supported_appearance',
                'native_fire': 'accepted',
            }):
        raise ValueError('Liquid render target and retained registry are inconsistent')

