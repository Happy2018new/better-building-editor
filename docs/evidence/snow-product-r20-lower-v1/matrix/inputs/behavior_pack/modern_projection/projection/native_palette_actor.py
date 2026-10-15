"""Resolve observed native wet actor bucket names without changing payloads."""
from __future__ import unicode_literals
from . import block_registry as registry
from . import native_palette_actor_data as source


def resolve_name(name, front, back):
    if front[0] == name and front[0] != 'minecraft:air':
        return name
    if (source.SCHEMA_VERSION != 2 or source.SOURCE_VERSION != registry.source_version() or
            source.PALETTE_SHA256.lower() != registry.fingerprint().lower()):
        raise ValueError('Native palette actor rules need regeneration for this block registry')
    # Native serializer groups foreground actors by their background water,
    # including different actor types within the same bucket.
    if (name == 'minecraft:water' and back[0] == name and
            front[0] in source.WET_ACTOR_NAMES):
        return front[0]
    raise ValueError('Native palette actor does not match its foreground: %s' % name)
