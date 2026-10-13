# -*- coding: utf-8 -*-
"""Transform semantic Bedrock states, independently of version-specific aux IDs.

Axes match Editor._transform: rotate_y90 maps (x,z) to (-z,x).
Rules are attached to state properties, not a whitelist of block names. Unknown
properties fail closed until the palette upgrade audit classifies them. Mirroring
reflects positions and expressible native states, not arbitrary render geometry:
blocks without an upside-down state retain their native upright appearance.
"""
from __future__ import unicode_literals
from . import block_registry as registry

OPERATIONS = ('rotate_y90', 'rotate_y180', 'rotate_y270',
              'mirror_x', 'mirror_y', 'mirror_z')
_HORIZONTAL = ('south', 'west', 'north', 'east')
_FACING = ('down', 'up', 'north', 'south', 'west', 'east')
_STAIRS = ('east', 'west', 'south', 'north')
_CORAL = ('west', 'east', 'north', 'south')
_FACES = ('down', 'up', 'south', 'west', 'north', 'east')
_MIRRORS = {'mirror_x': {'east': 'west', 'west': 'east'},
            'mirror_y': {'up': 'down', 'down': 'up'},
            'mirror_z': {'north': 'south', 'south': 'north'}}
_CONNECTIONS = ('wall_connection_type_', 'pale_moss_carpet_side_',
                'minecraft:connection_')
_STATE_VALUES = {
    'attachment': frozenset(('standing', 'hanging', 'side', 'multiple')),
    'books_stored': frozenset(range(64)),
    'coral_direction': frozenset(range(4)),
    'coral_fan_direction': frozenset(range(2)),
    'direction': frozenset(range(4)),
    'door_hinge_bit': frozenset((False, True)),
    'facing_direction': frozenset(range(6)),
    'ground_sign_direction': frozenset(range(16)),
    'hanging': frozenset((False, True)),
    'head_piece_bit': frozenset((False, True)),
    'huge_mushroom_bits': frozenset(range(16)),
    'lever_direction': frozenset(('down_east_west', 'down_north_south',
                                  'east', 'north', 'south', 'up_east_west',
                                  'up_north_south', 'west')),
    'minecraft:block_face': frozenset(_FACES),
    'minecraft:cardinal_direction': frozenset(_HORIZONTAL),
    'minecraft:corner': frozenset(('none', 'inner_left', 'inner_right',
                                   'outer_left', 'outer_right')),
    'minecraft:facing_direction': frozenset(_FACING),
    'minecraft:vertical_half': frozenset(('bottom', 'top')),
    'multi_face_direction_bits': frozenset(range(64)),
    'orientation': frozenset(('down_east', 'down_north', 'down_south', 'down_west',
                              'east_up', 'north_up', 'south_up', 'up_east',
                              'up_north', 'up_south', 'up_west', 'west_up')),
    'pillar_axis': frozenset(('x', 'y', 'z')),
    'portal_axis': frozenset(('unknown', 'x', 'z')),
    'powered_shelf_type': frozenset(range(4)),
    'rail_direction': frozenset(range(10)),
    'rotation': frozenset(range(4)),
    'sea_grass_type': frozenset(('default', 'double_bot', 'double_top')),
    'torch_facing_direction': frozenset(('east', 'north', 'south', 'top',
                                         'unknown', 'west')),
    'upper_block_bit': frozenset((False, True)),
    'upside_down_bit': frozenset((False, True)),
    'vine_direction_bits': frozenset(range(16)),
    'weirdo_direction': frozenset(range(4)),
}
_INT_STATES = frozenset(('books_stored', 'coral_direction', 'coral_fan_direction',
                         'direction', 'facing_direction', 'ground_sign_direction',
                         'huge_mushroom_bits', 'multi_face_direction_bits',
                         'powered_shelf_type', 'rail_direction', 'rotation',
                         'vine_direction_bits', 'weirdo_direction'))
_BOOL_STATES = frozenset(('door_hinge_bit', 'hanging', 'head_piece_bit',
                          'upper_block_bit', 'upside_down_bit'))

# Every non-geometric key is explicit. A version upgrade introducing *any*
# unclassified state therefore fails the offline audit, including keys whose
# names do not contain a convenient "direction" substring.
INVARIANT_STATES = frozenset('''active age age_bit attached_bit bamboo_leaf_size
bamboo_stalk_thickness big_dripleaf_head big_dripleaf_tilt bite_counter bloom
brewing_stand_slot_a_bit brewing_stand_slot_b_bit brewing_stand_slot_c_bit
brushed_progress button_pressed_bit can_summon candles cauldron_liquid
cluster_count composter_fill_level conditional_bit covered_bit cracked_state
crafting creaking_heart_state custom_appearance dead_bit deprecated disarmed_bit
drag_down dripstone_thickness end_portal_eye_bit explode_bit extinguished
fill_level growing_plant_age growth head_piece_bit height honey_level
in_wall_bit infiniburn_bit item_frame_map_bit item_frame_photo_bit kelp_age
liquid_depth lit moisturized_amount natural occupied_bit ominous open_bit
output_lit_bit output_subtract_bit persistent_bit powered_bit propagule_stage
rail_data_bit redstone_signal rehydration_level repeater_delay
respawn_anchor_charge sculk_sensor_phase stability stability_check
structure_block_type suspended_bit tip toggle_bit trial_spawner_state
triggered_bit turtle_egg_count twisting_vines_age update_bit vault_state
wall_post_bit weeping_vines_age'''.split())

TRANSFORMED_STATES = frozenset('''attachment books_stored coral_direction
coral_fan_direction direction door_hinge_bit facing_direction
ground_sign_direction hanging huge_mushroom_bits lever_direction
minecraft:block_face minecraft:cardinal_direction minecraft:corner
minecraft:facing_direction minecraft:vertical_half multi_face_direction_bits
orientation pillar_axis portal_axis powered_shelf_type rail_direction rotation
sea_grass_type upper_block_bit upside_down_bit vine_direction_bits
torch_facing_direction weirdo_direction'''.split())
_cache = {}


class UnrepresentableTransform(ValueError):
    """The native palette has no state for the requested orientation."""


def direction(value, operation):
    if operation.startswith('rotate_y') and value in _HORIZONTAL:
        return _HORIZONTAL[(_HORIZONTAL.index(value) + int(operation[8:]) // 90) % 4]
    return _MIRRORS.get(operation, {}).get(value, value)


def _number(value, order, operation):
    return order.index(direction(order[value], operation))


def _axis(value, operation):
    if operation in ('rotate_y90', 'rotate_y270'):
        return {'x': 'z', 'z': 'x'}.get(value, value)
    return value


def _bits(value, order, operation):
    result = 0
    for bit, face in enumerate(order):
        if value & (1 << bit):
            result |= 1 << order.index(direction(face, operation))
    return result


def _sign(value, operation):
    if operation.startswith('rotate_y'):
        return (value + int(operation[8:]) // 90 * 4) % 16
    if operation == 'mirror_x':
        return -value % 16
    if operation == 'mirror_z':
        return (8 - value) % 16
    return value


def _rail(value, operation):
    # Slopes are named by their high end; curves by their two open ends.
    if value < 2:
        return 1 - value if operation in ('rotate_y90', 'rotate_y270') else value
    if operation == 'mirror_y' and value < 6:
        return {2: 3, 3: 2, 4: 5, 5: 4}[value]
    if value < 6:
        order = ('east', 'west', 'north', 'south')
        return 2 + _number(value - 2, order, operation)
    curves = (frozenset(('south', 'east')), frozenset(('south', 'west')),
              frozenset(('north', 'west')), frozenset(('north', 'east')))
    result = frozenset(direction(face, operation) for face in curves[value - 6])
    return 6 + curves.index(result)


def _lever(value, operation):
    if value in _HORIZONTAL:
        return direction(value, operation)
    face, axis = value.split('_', 1)
    if operation in ('rotate_y90', 'rotate_y270'):
        axis = 'north_south' if axis == 'east_west' else 'east_west'
    return direction(face, operation) + '_' + axis


def _mushroom(value, operation):
    # 1..9 encode NW,N,NE,W,centre,E,SW,S,SE top-cap positions.
    # 11..13 are reserved palette codes with no named directional semantics.
    # Preserve them, just as all-inside/all-outside/all-stem variants are kept.
    if not 1 <= value <= 9 or operation == 'mirror_y':
        return value
    x, z = (value - 1) % 3 - 1, (value - 1) // 3 - 1
    if operation.startswith('rotate_y'):
        for unused in range(int(operation[8:]) // 90):
            x, z = -z, x
    elif operation == 'mirror_x':
        x = -x
    elif operation == 'mirror_z':
        z = -z
    return (z + 1) * 3 + x + 2


def _books(value, operation):
    slots = range(6)
    if operation in ('mirror_x', 'mirror_z'):
        slots = (2, 1, 0, 5, 4, 3)
    elif operation == 'mirror_y':
        slots = (3, 4, 5, 0, 1, 2)
    return sum(1 << slots[i] for i in range(6) if value & (1 << i))


def _jigsaw(properties, result, operation):
    # The secondary axis is only meaningful for vertical jigsaws. Up and down
    # count rotation in opposite directions (native Bedrock convention).
    facing = properties['facing_direction']
    if facing > 1:
        return properties['rotation']
    order = ('north', 'west', 'south', 'east') if facing == 0 else ('north', 'east', 'south', 'west')
    target_order = (('north', 'west', 'south', 'east') if result['facing_direction'] == 0
                    else ('north', 'east', 'south', 'west'))
    return target_order.index(direction(order[properties['rotation']], operation))


def known_property(key):
    if key in INVARIANT_STATES or key in TRANSFORMED_STATES:
        return True
    return any(key == prefix + face for prefix in _CONNECTIONS for face in _HORIZONTAL)


def transform_states(properties, operation):
    """Return a new state mapping; inputs are never mutated."""
    if operation not in OPERATIONS:
        raise ValueError('未知方块状态变换：%s' % operation)
    unknown = sorted(key for key in properties if not known_property(key))
    if unknown:
        raise ValueError('方块表包含尚未审查的状态，请更新适配规则：%s' % ', '.join(unknown))
    for key, value in properties.items():
        _validate_value(key, value)
    result = dict(properties)
    for key, value in properties.items():
        if key in INVARIANT_STATES:
            continue
        if any(key.startswith(prefix) and key[len(prefix):] in _HORIZONTAL
               for prefix in _CONNECTIONS):
            del result[key]
            continue
        result[key] = _property(key, value, properties, operation)
    for prefix in _CONNECTIONS:
        for face in _HORIZONTAL:
            key = prefix + face
            if key in properties:
                result[prefix + direction(face, operation)] = properties[key]
    if 'rotation' in properties:
        result['rotation'] = _jigsaw(properties, result, operation)
    return result


def _validate_value(key, value):
    allowed = _STATE_VALUES.get(key)
    if allowed is not None:
        expected = int if key in _INT_STATES else bool if key in _BOOL_STATES else None
        if value not in allowed or (expected is not None and type(value) is not expected):
            raise ValueError('尚未审查的方向状态值：%s=%r' % (key, value))
        return
    if any(key.startswith(prefix) and key[len(prefix):] in _HORIZONTAL
           for prefix in _CONNECTIONS):
        if value not in ('none', 'short', 'tall'):
            raise ValueError('尚未审查的连接状态值：%s=%r' % (key, value))


def _property(key, value, properties, operation):
    horizontal_mirror = operation in ('mirror_x', 'mirror_z')
    vertical_mirror = operation == 'mirror_y'
    if key in ('minecraft:block_face', 'minecraft:cardinal_direction',
               'minecraft:facing_direction', 'torch_facing_direction'):
        return direction(value, operation)
    if key == 'facing_direction':
        return _number(value, _FACING, operation)
    if key == 'direction':
        # Trapdoors share the stair encoding, unlike beds/repeaters. Their
        # semantic signature is stable across every wood/copper material.
        order = _STAIRS if 'upside_down_bit' in properties else _HORIZONTAL
        return _number(value, order, operation)
    if key == 'weirdo_direction':
        return _number(value, _STAIRS, operation)
    if key == 'coral_direction':
        return _number(value, _CORAL, operation)
    if key == 'ground_sign_direction':
        return _sign(value, operation)
    if key in ('pillar_axis', 'portal_axis'):
        return _axis(value, operation)
    if key == 'coral_fan_direction':
        return 1 - value if operation in ('rotate_y90', 'rotate_y270') else value
    if key in ('upside_down_bit', 'upper_block_bit'):
        return not value if vertical_mirror else value
    if key == 'door_hinge_bit':
        return not value if horizontal_mirror else value
    if key == 'minecraft:vertical_half' and vertical_mirror:
        return 'top' if value == 'bottom' else 'bottom'
    if key == 'hanging' and vertical_mirror:
        if 'brushed_progress' in properties:
            return value
        if (len(properties) == 1 or 'dripstone_thickness' in properties or
                'propagule_stage' in properties):
            return not value
        return value
    if key == 'attachment' and vertical_mirror:
        if value in ('standing', 'hanging'):
            return {'standing': 'hanging', 'hanging': 'standing'}[value]
        return value
    if key == 'sea_grass_type' and vertical_mirror:
        if value in ('double_bot', 'double_top'):
            return {'double_bot': 'double_top', 'double_top': 'double_bot'}[value]
    if key == 'multi_face_direction_bits':
        return _bits(value, _FACES, operation)
    if key == 'vine_direction_bits':
        return _bits(value, _HORIZONTAL, operation)
    if key == 'rail_direction':
        return _rail(value, operation)
    if key == 'lever_direction':
        return _lever(value, operation)
    if key == 'huge_mushroom_bits':
        return _mushroom(value, operation)
    if key == 'books_stored':
        return _books(value, operation)
    if key == 'powered_shelf_type' and horizontal_mirror:
        return {1: 3, 3: 1}.get(value, value)
    if key == 'minecraft:corner' and horizontal_mirror:
        return value.replace('left', 'RIGHT').replace('right', 'left').replace('RIGHT', 'right')
    if key == 'orientation':
        result = '_'.join(direction(face, operation) for face in value.split('_'))
        # Crafters have down_* / up_* pairs but no horizontal *_down variants.
        return result if result in _STATE_VALUES[key] else value
    return value


def transform(value, operation):
    """Transform one name/aux pair; moves and stacks preserve its state."""
    if operation.startswith(('move_', 'stack_')):
        return value
    original = value
    value = registry.canonical(value)
    properties = registry.states(value)
    if properties is None:
        raise ValueError('方块不在状态表中，无法安全转换朝向：%s' % value[0])
    result_states = transform_states(properties, operation)
    if result_states == properties:
        return original
    key = (value, operation)
    if key in _cache:
        return _cache[key]
    result = registry.from_states(value[0], result_states)
    if result is None:
        raise UnrepresentableTransform('原版没有所需的方块朝向：%s / %s' % (value[0], operation))
    _cache[key] = result
    return result
