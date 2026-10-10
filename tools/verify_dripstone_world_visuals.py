"""Compare the public vertical dripstone fixture with supported native blocks.

Use a horizontal side camera and exact one-block cell hulls. Native supports
remain in every shown/hidden capture, so subtraction isolates dripstone pixels.
"""
import verify_neighbor_world_visuals as world
from projection import block_registry as registry
from projection.debug_blueprints import VISUAL_CASES

metadata = VISUAL_CASES['dripstone_neighbors']
chain = metadata['chains'][-1]
native = world.native
native.FIXTURE = metadata['fixture']
native.VIEWS = ('side',)
native.VISUAL_CASES = {
    'standing': (chain['standing'][-2], chain['standing'][-1]),
    'hanging_cross_chunk': metadata['vertical_chunk_cells'],
    'merged_tips': metadata['merged_tips'],
}
world.CASES = tuple(native.VISUAL_CASES)
world.CELL_HEIGHT = 1.
native.CELL_ROIS = native.CELL_ROIS.replace('(0.,1.6)', '(0.,1.)')
original_offset = native.view_offset


def side_offset(keep, occupied, view, override=None):
    if override is None and view == 'side':
        return (0., 0., 8.)
    return original_offset(keep, occupied, view, override)


def supports(cells):
    occupied = set(pos for pos, value in cells)
    result = []
    for pos, value in cells:
        properties = registry.states(value)
        direction = 1 if properties['hanging'] else -1
        target = (pos[0], pos[1] + direction, pos[2])
        if target not in occupied:
            result.append((target, ('minecraft:stone', 0)))
    return result


native.view_offset = side_offset
world.native_supports = supports


if __name__ == '__main__':
    raise SystemExit(world.main())
