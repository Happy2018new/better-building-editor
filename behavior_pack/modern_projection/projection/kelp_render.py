"""Resolve render-only kelp parts from complete logical source neighbors."""
from .block_registry import canonical, states
from .cell import foreground, background

PROXIES = {'stem': 'modern_projection:ordinary_kelp_stem',
           'top': 'modern_projection:ordinary_kelp_top'}


def is_kelp(value):
    return canonical(value)[0] == 'minecraft:kelp'


def has_kelp(value):
    return is_kelp(foreground(value)) or is_kelp(background(value))


def document_part(document, position, value=None):
    """Visibility, native age and target-world occupancy never choose the tip."""
    if not document.contains(position):
        return None
    if not has_kelp(document.get(position) if value is None else value):
        return None
    above = (position[0], position[1] + 1, position[2])
    return ('stem' if document.contains(above) and has_kelp(document.get(above))
            else 'top')


def _indices(source):
    return set(index for layer in ('common', 'extra')
               for value, positions in source.get(layer, {}).items()
               if is_kelp(value) for index in positions)


def complete_source_parts(source):
    """Reference API only: source must cover the whole declared logical volume.

    Production views call palette_parts with their complete source Document.
    This preserves the existing synchronous context API's full-source contract.
    """
    indices = _indices(source)
    if not indices:
        return {}
    volume = source.get('volume')
    if volume is None or len(volume) != 3 or min(volume) <= 0:
        raise ValueError('Complete kelp source needs its logical volume')
    plane, total = volume[0] * volume[1], volume[0] * volume[1] * volume[2]
    if any(index < 0 or index >= total for index in indices):
        raise ValueError('Kelp cell is outside its complete logical source')
    return dict((index, 'stem' if index + plane in indices else 'top') for index in indices)


def palette_parts(source, document, logical_origin=(0, 0, 0)):
    """Classify only submitted kelp cells, using the unsliced source document."""
    indices = _indices(source)
    if not indices:
        return {}
    if document is None:
        raise ValueError('Kelp render parts require the complete source document')
    volume = source.get('volume')
    if volume is None or len(volume) != 3 or min(volume) <= 0:
        raise ValueError('Kelp render parts require a supported logical palette volume')
    plane, total = volume[0] * volume[1], volume[0] * volume[1] * volume[2]
    parts = {}
    for index in indices:
        if not 0 <= index < total:
            raise ValueError('Kelp cell is outside its logical palette volume')
        position = (logical_origin[0] + index // volume[0] % volume[1],
                    logical_origin[1] + index // plane,
                    logical_origin[2] + index % volume[0])
        part = document_part(document, position)
        if part is None:
            raise ValueError('Kelp render target is absent from the complete source document')
        parts[index] = part
    return parts


def prepare_layer(entries, records, parts):
    """Replace copied render maps only; omitted parts retain the native baseline."""
    if parts is None:
        return entries, records
    result, state_records = {}, {}
    for value, positions in entries.items():
        if not is_kelp(value):
            result[value] = positions
            if value in records:
                state_records[value] = records[value]
            continue
        for index in positions:
            part = parts.get(index)
            if part not in PROXIES:
                raise ValueError('Kelp render target has no complete source part')
            rendered = (PROXIES[part], 0)
            result.setdefault(rendered, []).append(index)
            record = states(rendered)
            if record:
                state_records[rendered] = record
    return result, state_records
