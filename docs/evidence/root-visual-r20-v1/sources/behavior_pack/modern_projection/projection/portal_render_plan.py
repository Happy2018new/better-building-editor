"""End portal surface shapes over the full immutable neighboring document."""
from .cell import foreground, background, integer_types
from .liquid_render_plan import LiquidSurface
from .liquid_transport import RenderGroup, pack_group
from .portal_profile import PORTAL_NAMES

NEIGHBORS = ((0, 1, 0), (0, 0, -1), (0, 0, 1),
             (-1, 0, 0), (1, 0, 0), (0, -1, 0))


def _requests(document, targets):
    if targets is None:
        for position, cell in document.blocks.items():
            yield None
            for layer, value in enumerate((foreground(cell), background(cell))):
                if value[0] in PORTAL_NAMES:
                    yield position, layer, value
        return
    sx, sy, sz = document.size
    if tuple(targets.get('volume', ())) != (sz, sx, sy):
        raise ValueError('Portal targets need the complete logical volume')
    seen = set()
    for layer, key in enumerate(('common', 'extra')):
        for value, indices in targets.get(key, {}).items():
            yield None
            if value[0] not in PORTAL_NAMES:
                continue
            for index in indices:
                if (type(index) is bool or not isinstance(index, integer_types) or
                        not 0 <= index < sx * sy * sz):
                    raise ValueError('Portal target lies outside its source document')
                position = (index // sz % sx, index // (sx * sz), index % sz)
                identity = position, layer
                if identity in seen or document.get_layer(position, layer) != value:
                    raise ValueError('Portal target repeats or differs from its immutable source')
                seen.add(identity)
                yield position, layer, value


def _faces(document, position, layer, name):
    if name == 'minecraft:end_portal':
        return 1
    faces = 63
    for face, delta in enumerate(NEIGHBORS):
        neighbor = tuple(position[axis] + delta[axis] for axis in range(3))
        if document.get_layer(neighbor, layer)[0] == name:
            faces &= ~(1 << face)
    return faces


def iter_render_steps(document, profile, targets=None, visible=None,
                      world=False, opacity=1.):
    """Visibility chooses cells, while neighbor connections retain source data."""
    pending, slots, count = {}, {}, 0
    models = profile.world_models if world else profile.models

    def render(key, surfaces):
        origin, family = key
        slot = slots.get(key, 0)
        slots[key] = slot + 1
        uniforms = pack_group(origin, tuple(surfaces), (255, 255, 255), 1., opacity)
        return RenderGroup((origin, ('portal', family, 1.), slot),
                           models[family], origin, uniforms)

    for request in _requests(document, targets):
        if request is None:
            yield None
            continue
        position, layer, value = request
        if visible is not None and not visible(position):
            continue
        faces = _faces(document, position, layer, value[0])
        if not faces:
            continue
        family = value[0].split(':', 1)[1]
        # Transport texture code selects no artwork; the portal profile owns it.
        height = .75 if family == 'end_portal' else 1.
        surface = LiquidSurface(position, layer, (height,) * 4, faces, 'still_water_grey')
        origin = tuple(axis // 4 * 4 for axis in position)
        key = origin, family
        group = pending.setdefault(key, [])
        if any(other.position == position and other.layer == layer for other in group):
            raise ValueError('Portal plan repeats one logical layer')
        group.append(surface)
        if len(group) == 4:
            count += 1
            if count > profile.max_groups:
                raise ValueError('Portal surface plan exceeds its owned model budget')
            del pending[key]
            yield render(key, group)
    for key in sorted(pending):
        count += 1
        if count > profile.max_groups:
            raise ValueError('Portal surface plan exceeds its owned model budget')
        yield render(key, pending[key])
