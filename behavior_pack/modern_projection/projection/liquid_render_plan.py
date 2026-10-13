"""Shared liquid draw inputs; shape rules and native resources live elsewhere."""
import math

from . import biomes
from .cell import background, foreground, text_type
from .storage import integer_types, position
from .liquid_transport import RenderGroup, pack_group

CHUNK_SIDE = 4
CELLS_PER_GROUP = 4
FACE_NAMES = ('top', 'north', 'south', 'west', 'east', 'bottom')
ALL_FACES = (1 << len(FACE_NAMES)) - 1
WATER_NAMES = frozenset(('minecraft:water', 'minecraft:flowing_water'))
LAVA_NAMES = frozenset(('minecraft:lava', 'minecraft:flowing_lava'))
LIQUID_NAMES = WATER_NAMES | LAVA_NAMES
WATER_TEXTURES = frozenset(('still_water_grey', 'flowing_water_grey'))
LAVA_TEXTURES = frozenset(('still_lava', 'flowing_lava'))
TEXTURES = WATER_TEXTURES | LAVA_TEXTURES


def _integer(value):
    return isinstance(value, integer_types) and not isinstance(value, bool)


def _unit(value):
    return (not isinstance(value, bool) and isinstance(value, integer_types + (float,))
            and not math.isnan(value) and not math.isinf(value) and 0 <= value <= 1)


class LiquidSurface(object):
    """An explicit shape in (00,10,11,01) order; no default liquid height."""
    def __init__(self, position, layer, heights, faces, texture_key, flow_uv=None):
        if (not isinstance(position, (tuple, list)) or len(position) != 3 or
                any(not _integer(axis) or axis < 0 for axis in position)):
            raise ValueError('Liquid surface position must contain nonnegative integers')
        if not _integer(layer) or layer not in (0, 1):
            raise ValueError('Liquid surfaces retain their explicit logical layer')
        if (not isinstance(heights, (tuple, list)) or len(heights) != 4 or
                any(not _unit(height) for height in heights)):
            raise ValueError('Four explicit finite unit liquid heights are required')
        if not _integer(faces) or not 0 <= faces <= ALL_FACES or texture_key not in TEXTURES:
            raise ValueError('Liquid surface has an invalid face mask or native texture key')
        if flow_uv is not None:
            if (not isinstance(flow_uv, (tuple, list)) or len(flow_uv) != 2 or
                    not isinstance(flow_uv[0], (bytes, text_type)) or not 0 < len(flow_uv[0]) <= 160 or
                    not _integer(flow_uv[1]) or not 0 <= flow_uv[1] <= 255):
                raise ValueError('Flow UVs need an explicit template and eight-bit rotation code')
            flow_uv = tuple(flow_uv)
        if texture_key.startswith('flowing_') and flow_uv is None:
            raise ValueError('Flowing textures require an explicit native UV template')
        self.position, self.layer = tuple(position), layer
        self.heights, self.faces = tuple(heights), faces
        self.texture_key, self.flow_uv = texture_key, flow_uv


class LiquidGroup(object):
    """At most four shapes sharing one texture, UV template and local origin."""
    def __init__(self, origin, surfaces, biome, tint, opacity):
        surfaces = tuple(surfaces)
        if (not isinstance(origin, (tuple, list)) or len(origin) != 3 or
                any(not _integer(axis) or axis < 0 or axis % CHUNK_SIDE for axis in origin)):
            raise ValueError('Liquid group origin must align with a four-cubed logical batch')
        if (not surfaces or len(surfaces) > CELLS_PER_GROUP or
                any(not isinstance(surface, LiquidSurface) for surface in surfaces)):
            raise ValueError('Liquid transport groups contain one to four surfaces')
        if (len(tint) != 3 or any(not _integer(channel) or not 0 <= channel <= 255 for channel in tint) or
                opacity is not None and not _unit(opacity)):
            raise ValueError('Liquid appearance needs RGB bytes and optional unit opacity')
        self.origin, self.surfaces = tuple(origin), surfaces
        self.texture_key = surfaces[0].texture_key
        self.flow_template = None if surfaces[0].flow_uv is None else surfaces[0].flow_uv[0]
        identities = set()
        for surface in surfaces:
            template = None if surface.flow_uv is None else surface.flow_uv[0]
            identity = surface.position, surface.layer
            if (surface.texture_key != self.texture_key or template != self.flow_template or
                    any(not 0 <= surface.position[axis] - origin[axis] < CHUNK_SIDE for axis in range(3)) or
                    identity in identities):
                raise ValueError('Liquid group mixes templates, repeats layers or exceeds its local batch')
            identities.add(identity)
        self.biome, self.tint, self.opacity = biome, tuple(tint), opacity


def _liquid_layers(value):
    return tuple((index, material) for index, material in enumerate((foreground(value), background(value)))
                 if material[0] in LIQUID_NAMES)


def _document_requests(document):
    store = document.blocks
    layers = {}
    for scanned, (value, count) in enumerate(store.counts.items(), 1):
        selected = _liquid_layers(value) if count > 0 else ()
        if selected:
            layers[store.palette_ids[value]] = selected
        if scanned % 128 == 0:
            yield None
    if not layers:
        return
    for scanned, key in enumerate(sorted(store.chunks), 1):
        if scanned % 128 == 0:
            yield None
        chunk = store.chunks[key]
        if isinstance(chunk, integer_types):
            if chunk not in layers:
                continue
            entries = ((index, chunk) for index in range(4096))
        else:
            entries = enumerate(chunk)
        for index, identity in entries:
            if index % 128 == 0:
                yield None
            selected = layers.get(identity)
            if not selected:
                continue
            pos = position(key, index)
            for layer, value in selected:
                yield pos, layer, value


def _target_requests(document, targets):
    sx, sy, sz = document.size
    if tuple(targets.get('volume', ())) != (sz, sx, sy):
        raise ValueError('Liquid targets must use the complete logical document volume')
    total, seen = sx * sy * sz, set()
    for layer, name in enumerate(('common', 'extra')):
        for scanned, (value, indices) in enumerate(targets.get(name, {}).items(), 1):
            if scanned % 128 == 0:
                yield None
            if value[0] not in LIQUID_NAMES:
                continue
            for scanned, index in enumerate(indices, 1):
                if scanned % 128 == 0:
                    yield None
                if not _integer(index) or not 0 <= index < total:
                    raise ValueError('Liquid target is outside the logical document')
                pos = (index // sz % sx, index // (sx * sz), index % sz)
                identity = pos, layer
                if identity in seen:
                    raise ValueError('Liquid targets repeat a logical layer position')
                seen.add(identity)
                if document.get_layer(pos, layer) != value:
                    raise ValueError('Liquid target differs from the complete source document')
                yield pos, layer, value


def _surface_parts(result, pos, layer, value):
    parts = (result,) if isinstance(result, LiquidSurface) else result
    if not isinstance(parts, (tuple, list)) or not 1 <= len(parts) <= len(FACE_NAMES):
        raise ValueError('Liquid provider must return one to six explicit surface parts')
    textures = WATER_TEXTURES if value[0] in WATER_NAMES else LAVA_TEXTURES
    covered, heights = 0, None
    for surface in parts:
        if not isinstance(surface, LiquidSurface):
            raise ValueError('Liquid shape provider did not return an explicit surface')
        if surface.position != pos or surface.layer != layer:
            raise ValueError('Liquid shape provider changed the requested position or logical layer')
        if surface.texture_key not in textures:
            raise ValueError('Liquid shape texture does not match its logical liquid family')
        if surface.faces & covered or heights is not None and surface.heights != heights:
            raise ValueError('Liquid surface parts must share corners and use disjoint faces')
        covered |= surface.faces
        heights = surface.heights
    return parts


def iter_group_steps(document, shape_provider, targets=None, visible=None):
    """Resolve shapes against the full document, including occupied neighbors.

    ``targets`` is an optional unprepared native palette selecting logical
    layers in the document's original (z,x,y) volume. It changes which cells
    are drawn; it never replaces the source supplied to the shape provider.
    A missing shape raises instead of introducing an unverified height fallback.
    None checkpoints bound scans even when every liquid face is concealed.
    Visibility filters draws only; the provider still reads the complete source.
    A provider may split one cell into disjoint parts for native face textures.
    """
    requests = _document_requests(document) if targets is None else _target_requests(document, targets)
    pending, appearance = {}, {}
    coincident = {} if getattr(shape_provider, 'coalesce_coincident_layers', False) else None

    def group(key, surfaces):
        origin, texture, unused_template = key
        if texture not in appearance:
            appearance[texture] = (biomes.water_appearance(document.biome) if texture in WATER_TEXTURES
                                   else ((255, 255, 255), None))
        tint, opacity = appearance[texture]
        return LiquidGroup(origin, surfaces, document.biome, tint, opacity)

    for request in requests:
        if request is None:
            yield None
            continue
        pos, layer, value = request
        if visible is not None and not visible(pos):
            continue
        parts = _surface_parts(shape_provider.surface(document, pos, layer, value), pos, layer, value)
        if (coincident is not None and any(part.faces for part in parts)
                and foreground(document.get(pos))[0] in WATER_NAMES
                and background(document.get(pos))[0] in WATER_NAMES):
            # Logical layers stay in the snapshot. Draw one identical surface,
            # including when targets select only the normally secondary layer.
            identity = tuple((part.heights, part.faces, part.texture_key, part.flow_uv) for part in parts)
            if coincident.get(pos) == identity:
                continue
            coincident[pos] = identity
        for surface in parts:
            if not surface.faces:
                continue
            origin = tuple(axis // CHUNK_SIDE * CHUNK_SIDE for axis in pos)
            template = None if surface.flow_uv is None else surface.flow_uv[0]
            key = origin, surface.texture_key, template
            surfaces = pending.setdefault(key, [])
            if any(other.position == pos and other.layer == layer for other in surfaces):
                yield group(key, surfaces)
                surfaces = pending[key] = []
            surfaces.append(surface)
            if len(surfaces) == CELLS_PER_GROUP:
                del pending[key]
                yield group(key, surfaces)
    for key in sorted(pending, key=lambda item: (item[0], item[1], repr(item[2]))):
        yield group(key, pending[key])


def iter_groups(document, shape_provider, targets=None, visible=None):
    """Synchronous convenience iterator; frame-budgeted callers use steps."""
    for group in iter_group_steps(document, shape_provider, targets, visible):
        if group is not None:
            yield group


def render_steps(groups, models, projection_opacity, max_groups):
    """Pack explicit shapes into stable caller-owned model slots.

    Resource keys are (texture, UV-template) pairs. Model names come from the
    validated resource profile, never from a guessed path or fallback texture.
    Checkpoints pass through for incremental UI/world preparation.
    """
    if not _integer(max_groups) or max_groups < 1:
        raise ValueError('Liquid rendering requires a positive model budget')
    if not _unit(projection_opacity):
        raise ValueError('Liquid projection opacity must be a finite unit value')
    slots, count = {}, 0
    for group in groups:
        if group is None:
            yield None
            continue
        resource = group.texture_key, group.flow_template
        model = models.get(resource)
        if not isinstance(model, (bytes, text_type)) or not 0 < len(model) <= 160:
            raise ValueError('Liquid texture/UV template has no registered model: ' + repr(resource))
        key = group.origin, resource
        slot = slots.get(key, 0)
        slots[key] = slot + 1
        count += 1
        if count > max_groups:
            raise ValueError('Liquid model budget exceeded; the complete source is retained')
        uniforms = pack_group(group.origin, group.surfaces, group.tint,
                              group.opacity, projection_opacity)
        yield RenderGroup((group.origin, resource, slot), model, group.origin, uniforms)
