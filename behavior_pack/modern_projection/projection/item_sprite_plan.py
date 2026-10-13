"""Pure plans for icon-backed frame contents; typed document data is immutable."""
from collections import namedtuple
import math

from . import block_registry
from .cell import actor_data, foreground, integer_types
from .entity_overlays import frame_item
from .native_appearance import FRAME_NAMES, angle
from .nbt_spatial import field_key, root_payload, scalar
from .visible_actor import entity_nbt

PAYLOAD_VERSION = 1
WORLD_TAG = 39687.
PREVIEW_BYTE = 135
SLOTS = 4
SpriteGroup = namedtuple('SpriteGroup', 'key model_name origin uniforms')


def preview_tag(distance):
    if (isinstance(distance, bool) or not isinstance(distance, integer_types + (float,))
            or not -512. <= distance <= 511.984375):
        raise ValueError('Item preview depth exceeds its signed16 range')
    return float((int(math.floor(distance * 64. + 32768.5)) << 8) | PREVIEW_BYTE)


def validate_uniforms(uniforms):
    if (not isinstance(uniforms, tuple) or len(uniforms) != 4 or
            any(not isinstance(row, tuple) or len(row) != 4 for row in uniforms)):
        raise ValueError('Item sprites require exactly four vec4 uniforms')
    if any(isinstance(value, bool) or not isinstance(value, integer_types + (float,))
           or not -16777215. <= value <= 16777215. for row in uniforms for value in row):
        raise ValueError('Item sprite uniforms must be finite float-exact numbers')
    if any(value != int(value) or not 0 <= value < 8192 for value in uniforms[0]):
        raise ValueError('Item codes require address6, facing3, rotation3 and enchantment1')
    if any(row != (0., 0., 0., 0.) for row in uniforms[1:3]):
        raise ValueError('Reserved item sprite uniforms must stay zero')
    tag, slots, unused_tint, opacity = uniforms[3]
    if (tag != WORLD_TAG and not (tag == int(tag) and 0 <= tag <= 16777215
                                 and int(tag) % 256 == PREVIEW_BYTE)):
        raise ValueError('Item sprite payload belongs to a different material')
    if slots != int(slots) or not 1 <= slots <= SLOTS or unused_tint != 0. or not 0. <= opacity <= 1.:
        raise ValueError('Invalid item sprite opacity or reserved appearance fields')
    for code in uniforms[0]:
        if code and int(code) // 64 % 8 not in range(6):
            raise ValueError('Item sprite facing is outside the six block faces')
    return uniforms


def with_preview_distance(group, distance):
    validate_uniforms(group.uniforms)
    return group._replace(uniforms=group.uniforms[:3] +
                         ((preview_tag(distance),) + group.uniforms[3][1:],))


def sprite_content(material, actor, profiles):
    """Only fields proven irrelevant to a static item silhouette are ignored."""
    item = frame_item(material, actor)
    if item is None:
        return None
    name = item['newItemName']
    if isinstance(name, bytes):
        name = name.decode('utf8')
    key = (name, item['newAuxValue'])
    profile = profiles.get(key)
    if profile is None:
        return None
    # Arbitrary userData can change maps, banners, potions or custom models.
    if any(field not in ('ench', b'ench') for field in item['userData']):
        return None
    root = root_payload(entity_nbt(actor))
    rotation = scalar(root, 'ItemRotation')
    tag = root.get(field_key(root, 'ItemRotation'))
    if not isinstance(tag, dict) or scalar(tag, '__type__') != 5 or not angle(rotation):
        return None
    step = rotation % 360. / 45.
    rounded = int(round(step))
    record = block_registry.states(material)
    facing = record.get('facing_direction') if record is not None else None
    if abs(step - rounded) > .00001 or facing not in range(6):
        return None
    return key, facing, rounded % 8, item['isEnchanted']


def iter_render_steps(document, profile, visible=None, world=False, opacity=1.):
    """Build target-only batches; neighboring frames never leak their contents."""
    if isinstance(opacity, bool) or not isinstance(opacity, integer_types + (float,)) or not 0. <= opacity <= 1.:
        raise ValueError('Item projection opacity must be between zero and one')
    groups = {}
    for position, cell in document.blocks.items():
        if visible is not None and not visible(position):
            continue
        material = foreground(cell)
        if material[0] not in FRAME_NAMES:
            continue
        content = sprite_content(material, actor_data(cell), profile.items)
        if content is not None:
            item, facing, rotation, enchanted = content
            origin = tuple(axis // 4 * 4 for axis in position)
            groups.setdefault((origin, item), []).append((position, facing, rotation, enchanted))
        yield None
    count = 0
    for (origin, item), rows in sorted(groups.items()):
        for start in range(0, len(rows), SLOTS):
            count += 1
            if count > profile.max_groups:
                raise ValueError('Item sprite plan exceeds its owned model budget')
            codes = []
            for position, facing, rotation, enchanted in sorted(rows)[start:start + SLOTS]:
                x, y, z = tuple(position[axis] - origin[axis] for axis in range(3))
                code = x + z * 4 + y * 16 + facing * 64 + rotation * 512
                codes.append(float(code + (4096 if enchanted else 0)))
            visible_slots = len(codes)
            codes.extend((0.,) * (SLOTS - visible_slots))
            # Number of valid slots is encoded in the reserved appearance field.
            uniforms = (tuple(codes), (0.,) * 4, (0.,) * 4,
                        (WORLD_TAG, float(visible_slots), 0., float(opacity)))
            model = profile.items[item]['world_model' if world else 'ui_model']
            yield SpriteGroup((origin, item, start // SLOTS), model, origin, uniforms)
