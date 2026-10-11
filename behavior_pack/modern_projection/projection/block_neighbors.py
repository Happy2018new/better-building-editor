# -*- coding: utf-8 -*-
"""Local native connection updates, staged with the edit that caused them.

Imported documents keep their supplied states. Only changed cells and native
connection blocks affected by them are considered. Scaffold support propagates
through its entire affected component. Families with stored states are detected
by their state schema; native geometry remains responsible for stair corners,
fence arms and pane arms which have no states.
"""
from __future__ import unicode_literals
from . import block_registry as registry
from .static_neighbor_data import HANGING_MOSS_NAMES
from .block_traits import is_solid
from .cell import actor_data, foreground, replace_layer
from .block_groups import (actor_pair_position, chest_pair_actor,
                           chest_render_pair_position, _adjacent_chest_position,
                           _chest_candidates, _CHESTS)
from .storage import Selection, integer_types, position

AIR = ('minecraft:air', 0)
FACES = ('north', 'east', 'south', 'west')
OFFSETS = {'north': (0, 0, -1), 'east': (1, 0, 0),
           'south': (0, 0, 1), 'west': (-1, 0, 0)}
OPPOSITE = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east'}
RAIL_ENDS = (('north', 'south'), ('east', 'west'), ('east', 'west'),
             ('east', 'west'), ('north', 'south'), ('north', 'south'),
             ('south', 'east'), ('south', 'west'), ('north', 'west'), ('north', 'east'))
RAIL_HIGH = {2: 'east', 3: 'west', 4: 'north', 5: 'south'}
_cache = {}
_STAIR_HALF = {'north': 3, 'east': 10, 'south': 12, 'west': 5}


class Neighborhood(object):
    def __init__(self, document, after, write, locked_layers, preserve):
        self.before, self.after, self.size = document.blocks, after, document.size
        self.write, self.locked_layers, self.preserve = write, locked_layers, preserve
        self.placed = Selection()

    def get_cell(self, pos):
        return self.after.get(pos, AIR) if self.contains(pos) else AIR

    def contains(self, pos):
        return all(0 <= pos[i] < self.size[i] for i in range(3))

    def can_change(self, pos):
        return self.contains(pos) and pos[1] not in self.locked_layers

    def changed(self, pos):
        return foreground(self.before.get(pos, AIR)) != foreground(self.get_cell(pos))

    def wall_neighbor_changed(self, pos):
        if self.changed(pos):
            return True
        value = self.get_cell(pos)
        if 'weirdo_direction' not in _properties(value):
            return False
        before_cell = lambda target: self.before.get(target, AIR)
        return _stair_mask(before_cell, pos, value) != _stair_mask(self.get_cell, pos, value)


def _add(pos, offset, height=0):
    return pos[0] + offset[0], pos[1] + offset[1] + height, pos[2] + offset[2]


def _record(value):
    value = foreground(value)
    if value not in _cache:
        native = registry.try_canonical(value)
        _cache[value] = native, (registry.states(native) or {}) if native is not None else {}
    return _cache[value]


def _properties(value):
    return _record(value)[1]


def _kind(value):
    properties = _properties(value)
    if 'rail_direction' in properties:
        return 'rail'
    if 'wall_post_bit' in properties:
        return 'wall'
    if 'in_wall_bit' in properties:
        return 'gate'
    if 'dripstone_thickness' in properties:
        return 'dripstone'
    if 'stability' in properties and 'stability_check' in properties:
        return 'scaffold'
    if foreground(value)[0] in HANGING_MOSS_NAMES:
        return 'hanging_moss'
    return 'chest' if properties and foreground(value)[0] in _CHESTS else None


def _with_properties(value, changes):
    front = registry.canonical(foreground(value))
    properties = dict(_properties(value))
    properties.update(changes)
    result = registry.from_states(front[0], properties)
    if result is None:
        raise ValueError('Native palette cannot represent connection states: %s' % front[0])
    return replace_layer(value, result)


def _thin(value):
    name = foreground(value)[0]
    return (name.endswith('_glass_pane') or name.endswith('copper_bars') or
            name in ('minecraft:glass_pane', 'minecraft:iron_bars'))


def _full_cube(value):
    name = foreground(value)[0]
    return (is_solid(_record(value)[0] or foreground(value)) or
            name.endswith('_stained_glass') or name in ('minecraft:glass', 'minecraft:tinted_glass'))


def _stair_direction(value):
    properties = _properties(value)
    direction = properties.get('weirdo_direction')
    return ('east', 'west', 'south', 'north')[direction] if direction is not None else None


def _same_stair(value, direction, upside_down):
    return (_stair_direction(value) == direction and
            _properties(value).get('upside_down_bit') == upside_down)


def _stair_mask(get_cell, pos, value):
    """Four step quadrants account for native inner/outer stair corners."""
    direction = _stair_direction(value)
    if direction is None:
        return 0
    half = _STAIR_HALF[direction]
    upside_down = _properties(value)['upside_down_bit']
    for front in (True, False):
        face = direction if front else OPPOSITE[direction]
        other = get_cell(_add(pos, OFFSETS[face]))
        other_direction = _stair_direction(other)
        if (other_direction is None or
                _properties(other).get('upside_down_bit') != upside_down or
                (direction in ('north', 'south')) == (other_direction in ('north', 'south'))):
            continue
        side = OPPOSITE[other_direction] if front else other_direction
        if _same_stair(get_cell(_add(pos, OFFSETS[side])), direction, upside_down):
            continue
        return half & _STAIR_HALF[other_direction] if front else half | _STAIR_HALF[other_direction]
    return half


def _solid_face(value, face, get_cell, pos):
    if _full_cube(value):
        return True
    properties = _properties(value)
    if 'weirdo_direction' in properties:
        mask = _stair_mask(get_cell, pos, value)
        return mask & _STAIR_HALF[face] == _STAIR_HALF[face]
    return False


def _wall_connects(value, face, get_cell, pos):
    kind = _kind(value)
    if kind == 'wall' or _thin(value):
        return True
    if kind == 'gate':
        direction = _properties(value).get('minecraft:cardinal_direction')
        return direction is not None and (direction in ('north', 'south')) != (face in ('north', 'south'))
    return _solid_face(value, OPPOSITE[face], get_cell, pos)


def _covers_wall_arm(above, face, get_cell, pos):
    properties = _properties(above)
    if _full_cube(above):
        return True
    if 'wall_post_bit' in properties:
        return properties.get('wall_connection_type_' + face, 'none') != 'none'
    if 'minecraft:vertical_half' in properties:
        return properties['minecraft:vertical_half'] == 'bottom'
    if 'weirdo_direction' in properties:
        if not properties.get('upside_down_bit'):
            return True
        mask = _stair_mask(get_cell, pos, above)
        return mask & _STAIR_HALF[face] == _STAIR_HALF[face]
    return False


def _wall(value, pos, context):
    get_cell, changed, placed = context.get_cell, context.wall_neighbor_changed, pos in context.placed
    properties = _properties(value)
    above_pos = _add(pos, (0, 1, 0))
    above = get_cell(above_pos)
    above_changed = changed(above_pos)
    updates = {}
    for face in FACES:
        target = _add(pos, OFFSETS[face])
        key = 'wall_connection_type_' + face
        connection = properties[key]
        if placed or changed(target):
            connection = 'short' if _wall_connects(get_cell(target), face, get_cell, target) else 'none'
        if connection != 'none' and (placed or changed(target) or above_changed):
            connection = 'tall' if _covers_wall_arm(above, face, get_cell, above_pos) else 'short'
        updates[key] = connection
    connected = frozenset(face for face in FACES if updates['wall_connection_type_' + face] != 'none')
    straight = connected in (frozenset(('north', 'south')), frozenset(('east', 'west')))
    above_states = _properties(above)
    post_above = (above_states.get('wall_post_bit') is True or
                  above_states.get('torch_facing_direction') == 'top' or
                  'ground_sign_direction' in above_states or
                  above_states.get('hanging') is False)
    updates['wall_post_bit'] = not straight or post_above
    return _with_properties(value, updates)


def _gate(value, pos, get_cell):
    properties = _properties(value)
    direction = properties.get('minecraft:cardinal_direction')
    faces = ('east', 'west') if direction in ('north', 'south') else ('north', 'south')
    in_wall = any(_kind(get_cell(_add(pos, OFFSETS[face]))) == 'wall' for face in faces)
    return _with_properties(value, {'in_wall_bit': in_wall})


def _rail_at(get_cell, pos, face):
    offset = OFFSETS[face]
    for height in (0, 1, -1):
        target = _add(pos, offset, height)
        value = get_cell(target)
        if _kind(value) == 'rail':
            return target, value
    return None


def _rail_connections(get_cell, pos, value):
    shape = _properties(value)['rail_direction']
    result = []
    for face in RAIL_ENDS[shape]:
        height = 1 if RAIL_HIGH.get(shape) == face else 0
        target = _add(pos, OFFSETS[face], height)
        other = get_cell(target)
        if _kind(other) != 'rail' and not height:
            target = _add(target, (0, -1, 0))
            other = get_cell(target)
        if _kind(other) != 'rail':
            continue
        other_shape = _properties(other)['rail_direction']
        reciprocal = OPPOSITE[face]
        if reciprocal not in RAIL_ENDS[other_shape]:
            continue
        other_height = 1 if RAIL_HIGH.get(other_shape) == reciprocal else 0
        if _add(target, OFFSETS[reciprocal], other_height) == pos:
            result.append((face, target))
    return result


def _rail_shape(value, pos, connections):
    properties = _properties(value)
    shape = properties['rail_direction']
    if not connections:
        return shape if shape < 2 else 0 if RAIL_ENDS[shape][0] in ('north', 'south') else 1
    faces = frozenset(face for face, unused in connections)
    if len(faces) == 1:
        face = connections[0][0]
        faces = frozenset((face, OPPOSITE[face]))
    if len(faces) != 2:
        return None
    high = [face for face, target in connections if target[1] > pos[1]]
    if high:
        if len(high) != 1 or faces != frozenset((high[0], OPPOSITE[high[0]])):
            return None
        desired = dict((face, key) for key, face in RAIL_HIGH.items())[high[0]]
    else:
        desired = next((i for i in (0, 1, 6, 7, 8, 9) if frozenset(RAIL_ENDS[i]) == faces), None)
    if desired is None:
        return None
    new = dict(properties, rail_direction=desired)
    front = registry.canonical(foreground(value))
    return desired if registry.from_states(front[0], new) is not None else None


def _rail(value, pos, context):
    get_cell, write = context.get_cell, context.write
    connections = _rail_connections(get_cell, pos, value)
    if len(connections) == 2:
        return value
    used = set(face for face, unused in connections)
    for face in ('south', 'east', 'west', 'north'):
        if face in used:
            continue
        candidate = _rail_at(get_cell, pos, face)
        if candidate is None:
            continue
        target, other = candidate
        existing = _rail_connections(get_cell, target, other)
        if len(existing) == 2 or any(partner == pos for unused, partner in existing):
            continue
        own_shape = _rail_shape(value, pos, connections + [(face, target)])
        other_shape = _rail_shape(other, target, existing + [(OPPOSITE[face], pos)])
        if own_shape is None or other_shape is None:
            continue
        if other_shape != _properties(other)['rail_direction']:
            if target in context.preserve or not context.can_change(target):
                continue
            write(target, _with_properties(other, {'rail_direction': other_shape}))
        connections.append((face, target))
        used.add(face)
        if len(connections) == 2:
            break
    shape = _rail_shape(value, pos, connections)
    return _with_properties(value, {'rail_direction': shape}) if shape is not None else value


def _chest(value, pos, context):
    get_cell, write, can_change = context.get_cell, context.write, context.can_change
    partner = actor_pair_position(value, pos) or chest_render_pair_position(value, pos)
    if partner is not None:
        other = get_cell(partner)
        offset = tuple(partner[i] - pos[i] for i in range(3))
        direction = _properties(value).get('minecraft:cardinal_direction')
        side = (offset[2] == 0 if direction in ('north', 'south') else offset[0] == 0)
        if (sum(abs(v) for v in offset) != 1 or offset[1] or not side or
                foreground(other)[0] != foreground(value)[0] or
                _properties(other).get('minecraft:cardinal_direction') != direction):
            partner = None
    if partner is None:
        value = chest_pair_actor(value, pos)
        partner = _adjacent_chest_position(get_cell, value, pos)
        if partner is None and pos in context.placed:
            candidates = _chest_candidates(get_cell, value, pos)
            partner = next((target for target in candidates if can_change(target)), None)
    if partner is None or not can_change(partner):
        return chest_pair_actor(value, pos)
    write(partner, chest_pair_actor(get_cell(partner), partner, pos))
    return chest_pair_actor(value, pos, partner)


def _same_dripstone(value, hanging):
    properties = _properties(value)
    return 'dripstone_thickness' in properties and properties.get('hanging') == hanging


def _dripstone(value, pos, get_cell):
    properties = _properties(value)
    hanging = properties['hanging']
    direction = -1 if hanging else 1
    next_pos = _add(pos, (0, direction, 0))
    following = get_cell(next_pos)
    if _same_dripstone(following, hanging):
        if _same_dripstone(get_cell(_add(next_pos, (0, direction, 0))), hanging):
            thickness = ('middle' if _same_dripstone(get_cell(_add(pos, (0, -direction, 0))), hanging)
                         else 'base')
        else:
            thickness = 'frustum'
    else:
        paired_merge = (properties['dripstone_thickness'] == 'merge' and
                        _same_dripstone(following, not hanging) and
                        _properties(following)['dripstone_thickness'] == 'merge')
        thickness = 'merge' if paired_merge else 'tip'
    return _with_properties(value, {'dripstone_thickness': thickness})


def _context_offsets(kind):
    if kind == 'rail':
        return tuple((offset[0], height, offset[2]) for offset in OFFSETS.values() for height in (0, 1, -1))
    if kind == 'dripstone':
        return tuple((0, height, 0) for height in (-2, -1, 1, 2))
    if kind == 'hanging_moss':
        return ((0, -1, 0),)
    if kind == 'scaffold':
        return tuple(OFFSETS.values()) + ((0, -1, 0), (0, 1, 0))
    offsets = tuple(OFFSETS.values())
    return offsets + ((0, 1, 0),) if kind == 'wall' else offsets


def _affected_chunks(before, after):
    keys = set(before.chunks) | set(after.chunks)
    changed = [key for key in keys if before.chunks.get(key, 0) != after.chunks.get(key, 0)]
    return set((key[0] + x, key[1] + y, key[2] + z)
               for key in changed for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1))


def _candidate_steps(store, chunk_keys):
    kinds = [_kind(value) for value in store.palette]
    for key in sorted(set(store.chunks) & chunk_keys):
        chunk = store.chunks[key]
        if isinstance(chunk, integer_types):
            if not kinds[chunk]:
                continue
            entries = ((index, chunk) for index in range(4096))
        else:
            entries = enumerate(chunk)
        for index, identity in entries:
            if kinds[identity]:
                yield position(key, index)
            elif index % 256 == 0:
                yield None


def reconcile_steps(document, after, write, locked_layers, preserve=()):
    """Yield bounded work while writing connection changes into ``after``.

    ``write`` updates the staged store and its transaction count. ``preserve``
    contains explicit whole-cell placements, whose rail/wall states are already
    transformed or supplied by an import. Passive neighbors still reconnect.
    """
    context = Neighborhood(document, after, write, locked_layers, preserve)
    get_cell, changed = context.get_cell, context.changed
    candidates = Selection()
    for pos in _candidate_steps(after, _affected_chunks(document.blocks, after)):
        if pos is None:
            yield None
            continue
        value = get_cell(pos)
        kind = _kind(value)
        if changed(pos):
            context.placed.add(pos)
        context_changed = context.wall_neighbor_changed if kind == 'wall' else changed
        if (changed(pos) or any(context_changed(_add(pos, offset)) for offset in _context_offsets(kind)) or
                (kind == 'chest' and actor_data(document.get(pos)) != actor_data(value))):
            candidates.add(pos)
        yield None
    for pos in candidates:
        if not context.can_change(pos):
            continue
        value = get_cell(pos)
        kind = _kind(value)
        if kind == 'scaffold':
            continue
        elif kind == 'chest':
            updated = _chest(value, pos, context)
        elif pos in preserve:
            continue
        elif kind == 'wall':
            updated = _wall(value, pos, context)
        elif kind == 'gate':
            updated = _gate(value, pos, get_cell)
        elif kind == 'dripstone':
            updated = _dripstone(value, pos, get_cell)
        elif kind == 'hanging_moss':
            below = foreground(get_cell(_add(pos, (0, -1, 0))))[0]
            updated = _with_properties(value, {'tip': below != foreground(value)[0]})
        else:
            updated = _rail(value, pos, context)
        if updated != value:
            write(pos, updated)
        yield None
    from .scaffold_neighbors import reconcile_steps as scaffold_steps
    for step in scaffold_steps(context, candidates, _properties, _with_properties):
        yield step
