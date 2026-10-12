"""Run unchanged full/missing image contracts for declared dry plant snapshots."""
import verify_extended_neighbor_world_visuals as source_suite
from projection.debug_botanical_blueprints import VISUAL_CASE

DRY_CASES = tuple(row for row in VISUAL_CASE['cases'] if not row['water'] and
                  not any(name in ('water', 'flowing_water', 'lava', 'flowing_lava')
                          for pos, name, states in row['supports'] + row['blocks']))
METADATA = dict(VISUAL_CASE, cases=DRY_CASES)
source_suite.VISUAL_CASE = METADATA
source_suite.suite.configure(METADATA)
world = source_suite.world
supports = source_suite.supports
world.native_supports = supports


if __name__ == '__main__':
    raise SystemExit(world.main())
