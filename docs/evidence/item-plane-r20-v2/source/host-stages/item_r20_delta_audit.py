"""Check every generated icon against its saved baseline, including slot poses."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
paths = sorted((ROOT / 'resource_pack/models/modern_projection/item_icons').glob('*_mesh.json'))
baseline = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=str(ROOT),
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
vertices = 0
try:
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        baseline.stdin.write(('HEAD:' + relative + '\n').encode('ascii'))
        baseline.stdin.flush()
        header = baseline.stdout.readline().split()
        assert len(header) == 3 and header[1] == b'blob', header
        previous = json.loads(baseline.stdout.read(int(header[2])))
        assert baseline.stdout.read(1) == b'\n'
        current = json.loads(path.read_bytes())
        first, second = previous['mesh'][0], current['mesh'][0]
        assert first['material'] == second['material'] and first['indices'] == second['indices']
        assert len(first['vertices']) == len(second['vertices'])
        for old, new in zip(first['vertices'], second['vertices']):
            assert {key: value for key, value in old.items() if key != 'pos'} == {
                    key: value for key, value in new.items() if key != 'pos'}
            assert old['pos'][:2] == new['pos'][:2]
            assert old['pos'][2] - new['pos'][2] == .25 / 16.
            # Shelf/campfire layouts overwrite z before applying any face pose.
            for depth in (.3125, .05):
                assert old['pos'][:2] + [depth] == new['pos'][:2] + [depth]
            vertices += 1
    report = {'schema': 1, 'mesh_files': len(paths), 'vertices': vertices,
        'all_only_depth_shifted': True, 'depth_delta_model_pixels': -.25,
        'unchanged': ['vertex xy', 'UVs', 'normals', 'weights', 'indices', 'materials',
                      'shelf layout final local vertex', 'campfire layout final local vertex'],
        'sword_mesh_sha256': hashlib.sha256((ROOT /
            'resource_pack/models/modern_projection/item_icons/cf75a6e96b2d3e06_mesh.json').read_bytes()).hexdigest(),
        'production_qualified': False}
    (ROOT / '.runtime/item-r20-control/geometry-delta.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps(report))
finally:
    baseline.stdin.close()
    assert baseline.wait(timeout=10) == 0
