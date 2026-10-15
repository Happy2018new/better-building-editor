"""Extend the unchanged v7 owner session with bounded world-route controls."""
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('water_v2_host', ROOT / '.runtime/water-r20-v2.py')
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)
host.OUTPUT = ROOT / '.runtime/water-r20-state-v7'
host.OWNER = 'water-r20-v7'

mode = sys.argv[1]
route, matrix = mode.split('-', 1)
assert route in ('full', 'missing') and matrix in ('public19', 'alpha4')
name = 'world-' + mode
assert not (host.OUTPUT / (name + '.json')).exists()
options = ['--frozen', '--visibility-controls', '--measure-budgets', '--route', route,
           '--max-handles', '210000', '--falling-skyward']
if matrix == 'public19':
    cases = ('source', 'low', 'diagonal', 'drop_north', 'pool', 'falling',
             'flow_east', 'flow_south', 'flow_west', 'flow_north',
             'wet_oak_fence', 'wet_glass_pane', 'wet_oak_slab', 'wet_oak_stairs',
             'neighbor_oak_slab', 'neighbor_oak_stairs', 'neighbor_glass_pane',
             'neighbor_stone', 'transparent_overlap')
    options.extend(('--opaque-side-controls', '--native-side-projection'))
else:
    cases = ('wet_oak_fence', 'wet_glass_pane', 'wet_oak_slab', 'wet_oak_stairs')
    options.append('--alpha-controls')
for case in cases:
    options.extend(('--case', case))
raise SystemExit(host.probe(name, options))
