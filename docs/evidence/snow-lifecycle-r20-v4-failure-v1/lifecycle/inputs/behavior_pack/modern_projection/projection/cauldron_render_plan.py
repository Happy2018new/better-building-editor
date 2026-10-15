"""Finite cauldron tops over immutable source cells and measured appearances.

The cauldron shader interprets the shared liquid payload with its own finite
footprint. Texture keys below are transport family codes, not asset names.
Only the cauldron profile selects the dedicated cauldron-water/lava models.
"""
from collections import namedtuple

from .cauldron_appearance import CAULDRON_MATERIALS
from .cell import actor_data, foreground, integer_types
from .liquid_render_plan import LiquidSurface
from .liquid_transport import RenderGroup, pack_group

CauldronTop = namedtuple('CauldronTop', 'height texture color opacity')


def _selected(document, targets):
    if targets is None:
        return None
    sx, sy, sz = document.size
    if tuple(targets.get('volume', ())) != (sz, sx, sy):
        raise ValueError('Cauldron targets need the complete native document volume')
    selected = set()
    for material, indices in targets.get('common', {}).items():
        if material[0] not in CAULDRON_MATERIALS:
            continue
        for index in indices:
            if (type(index) is bool or not isinstance(index, integer_types) or
                    not 0 <= index < sx * sy * sz):
                raise ValueError('Cauldron target lies outside its document')
            position = (index // sz % sx, index // (sx * sz), index % sz)
            if position in selected:
                raise ValueError('Cauldron targets repeat a foreground position')
            if document.get_layer(position, 0) != material:
                raise ValueError('Cauldron target differs from the immutable source')
            selected.add(position)
    return selected


def iter_render_steps(document, profile, targets=None, visible=None,
                      world=False, opacity=1.):
    """Use complete source NBT while targeting only requested visible cells."""
    selected = _selected(document, targets)
    pending, slots, count = {}, {}, 0
    models = profile.world_models if world else profile.models

    def render(key, surfaces):
        origin, texture, color, alpha = key
        slot = slots.get(key, 0)
        slots[key] = slot + 1
        model = models[texture]
        payload = pack_group(origin, tuple(surfaces), color, alpha, opacity)
        return RenderGroup((origin, ('cauldron', texture, color, alpha), slot),
                           model, origin, payload)

    for position, cell in document.blocks.items():
        # Preserve scheduling progress even for documents without cauldrons.
        yield None
        material = foreground(cell)
        if (material[0] not in CAULDRON_MATERIALS or
                selected is not None and position not in selected or
                visible is not None and not visible(position)):
            continue
        top = profile.top(material, actor_data(cell), document.biome)
        if top is None:
            continue
        origin = tuple(axis // 4 * 4 for axis in position)
        key = origin, top.texture, top.color, top.opacity
        surface = LiquidSurface(position, 0, (top.height,) * 4, 1,
                                'still_lava' if top.texture == 'lava' else 'still_water_grey')
        group = pending.setdefault(key, [])
        group.append(surface)
        if len(group) == 4:
            count += 1
            if count > profile.max_groups:
                raise ValueError('Cauldron surface plan exceeds its owned model budget')
            del pending[key]
            yield render(key, group)
    for key in sorted(pending):
        count += 1
        if count > profile.max_groups:
            raise ValueError('Cauldron surface plan exceeds its owned model budget')
        yield render(key, pending[key])


def prepare_shells(common, states, actors, profile, biome):
    """Return render-only empty shells for exactly the supported liquid tops.

    Call before native geometry creation. Source cells and actor payloads are
    retained by the caller; only these detached palette dictionaries change.
    Unsupported appearances keep their previous native route.
    """
    result, records = {}, {}
    for material, indices in common.items():
        name = material[0]
        payloads = actors.get(name, actors.get(name.encode('utf8'), {}))
        for index in indices:
            rendered = material
            if (material[0] in CAULDRON_MATERIALS and
                    profile.top(material, payloads.get(index), biome) is not None):
                rendered = profile.empty_shell
            result.setdefault(rendered, []).append(index)
            record = profile.empty_states if rendered != material else states.get(material)
            if record is not None:
                records[rendered] = dict(record)
    return result, records
