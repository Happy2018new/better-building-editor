"""Use the shared native full/missing contracts for fixed extended cases."""
import verify_static_neighbor_world_visuals as suite
from projection.debug_blueprints import material
from projection.debug_neighborhood_blueprints import VISUAL_CASE

world = suite.world
suite.configure(VISUAL_CASE)


def supports(cells):
    actual = dict(cells)
    assert len(actual) == len(cells) and actual, 'Duplicate or empty extended source'
    low = tuple(min(pos[i] for pos in actual) for i in range(3))
    for row in VISUAL_CASE['cases']:
        expected = dict((pos, material(name, properties)) for pos, name, properties in row['blocks'])
        source_low = tuple(min(pos[i] for pos in expected) for i in range(3))
        delta = tuple(low[i] - source_low[i] for i in range(3))

        def translated(pos):
            return tuple(pos[i] + delta[i] for i in range(3))

        if dict((translated(pos), value) for pos, value in expected.items()) != actual:
            continue
        return [(translated(pos), material(name, properties)) for pos, name, properties in row['supports']]
    raise ValueError('Source does not match an original public extended connection case')


world.native_supports = supports


if __name__ == '__main__':
    raise SystemExit(world.main())
